"""Explicit manual workflow for the Pops' Edge Opportunity Board.

Consumes a local JSON evidence bundle and optional local position CSV. It does
not collect provider data, persist domain objects, or perform wagering actions.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from event_contracts import ContractError
from forecast_contracts import ForecastObservation
from market_contracts import MarketAdapterOutcome, MarketAdapterResult, MarketSide, MarketStatus
from market_valuation import FlatPerContractFeeModel, ZeroFeeModel, value_market
from opportunity_board import BoardEntry, OpportunityState, Position, _status_label, analyze_liquidation, build_opportunity, render_opportunity_board

BUNDLE_SCHEMA_VERSION = "pops-edge-opportunity-bundle-v1"


def read_positions(path: str | Path | None) -> tuple[Position, ...]:
    if path is None:
        raise ValueError("an explicit current-position summary CSV is required; an empty file represents no positions")
    positions: dict[tuple[str, MarketSide], Position] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            status = str(row.get("Status", "Open")).strip().lower()
            if status not in ("open", "partially closed", "active"):
                continue
            provider = str(row.get("Provider") or "").strip().lower()
            market_id = str(row.get("Provider Market ID") or "").strip()
            proposition_id = str(row.get("Proposition ID") or "").strip()
            event_id = str(row.get("Canonical Event ID") or "").strip()
            side_text = str(row.get("Side") or "").strip().lower()
            if provider != "kalshi" or not market_id or not proposition_id or not event_id:
                raise ValueError("each position summary requires Provider=kalshi, Provider Market ID, Proposition ID, and Canonical Event ID")
            try: side = MarketSide(side_text)
            except ValueError as error: raise ValueError("position Side must be yes or no") from error
            try:
                quantity = Decimal(str(row.get("Open Quantity") or "")); average = Decimal(str(row.get("Average Entry Cost") or ""))
            except InvalidOperation as error:
                raise ValueError("position Open Quantity and Average Entry Cost must be exact decimals") from error
            captured = datetime.fromisoformat(row["Captured At"]) if row.get("Captured At") else None
            try:
                entry_fees=Decimal(str(row.get("Entry Fees") or "0")); exit_fees=Decimal(str(row.get("Exit Fees") or "0"))
            except InvalidOperation as error: raise ValueError("position fees must be exact decimals") from error
            series_id = f"market-series:{provider}:{market_id}"; key = (series_id, side)
            if key in positions: raise ValueError(f"contradictory duplicate current-position summary for {series_id} {side.value}")
            positions[key] = Position(series_id, proposition_id, event_id, side, quantity, average, captured, str(row.get("Source Reference") or path),entry_fees,exit_fees,str(row.get("Evidence SHA256") or "").strip() or None)
    return tuple(positions[key] for key in sorted(positions, key=lambda item: (item[0], item[1].value)))


def validate_bundle(bundle: dict) -> dict:
    if not isinstance(bundle, dict) or set(bundle) != {"schema_version", "generated_at", "cases"}:
        raise ValueError("bundle requires exactly schema_version, generated_at, and cases")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION: raise ValueError("unsupported opportunity bundle schema version")
    datetime.fromisoformat(bundle["generated_at"])
    if not isinstance(bundle["cases"], list): raise ValueError("bundle cases must be a list")
    forbidden = ("credential", "password", "secret", "api_key", "authentication", "access_key")
    if any(term in str(bundle).lower() for term in forbidden): raise ValueError("bundle cannot contain credentials or authentication material")
    entry_ids=set(); combinations=set()
    for case in bundle["cases"]:
        if not isinstance(case,dict): raise ValueError("each bundle case must be an object")
        allowed={"entry_id","game","scheduled_start","proposition","side","quantity","fee_per_contract","forecast","market_result","market_results"}
        if not set(case).issubset(allowed) or not {"entry_id","game","scheduled_start","proposition","side","quantity","fee_per_contract"}.issubset(case): raise ValueError("bundle case has missing or unsupported fields")
        if case["entry_id"] in entry_ids: raise ValueError("duplicate bundle entry_id")
        entry_ids.add(case["entry_id"])
        forecast_value=_decode_forecast(case.get("forecast")); market_values=_decode_markets(case)
        combination=(forecast_value.observation_id if forecast_value else None,tuple(value.observation.observation_id if value.observation else value.provider_market_id for value in market_values),case["side"])
        if combination in combinations: raise ValueError("duplicate forecast/market/side bundle record")
        combinations.add(combination)
    return bundle


def _decode_forecast(payload) -> ForecastObservation | None:
    return ForecastObservation.from_dict(payload) if payload is not None else None


def _decode_market(payload) -> MarketAdapterResult | None:
    return MarketAdapterResult.from_dict(payload) if payload is not None else None


def _decode_markets(case: dict) -> tuple[MarketAdapterResult,...]:
    if "market_results" in case:
        values=case["market_results"]
        if not isinstance(values,list) or not values: raise ValueError("market_results must be a non-empty list")
        return tuple(_decode_market(value) for value in values)
    value=_decode_market(case.get("market_result"))
    return (value,) if value is not None else ()


def select_market_results(results: tuple[MarketAdapterResult,...], scheduled_start: datetime | None) -> tuple[MarketAdapterResult | None,MarketAdapterResult | None]:
    usable=tuple(result for result in results if result.observation and result.series and result.proposition and result.outcome in (MarketAdapterOutcome.COMPLETE,MarketAdapterOutcome.PARTIAL))
    if not usable: return None,None
    identities={(result.series.series_id,result.observation.canonical_event_id,result.proposition.proposition_id) for result in usable}
    if len(identities)!=1: raise ValueError("market observation history must share one Series, event, and proposition")
    latest=max(usable,key=lambda result:(result.observation.collected_at,result.observation.observation_id))
    if scheduled_start is None: return None,latest
    pregame=tuple(result for result in usable if result.observation.collected_at < scheduled_start)
    comparison=max(pregame,key=lambda result:(result.observation.collected_at,result.observation.observation_id)) if pregame else None
    return comparison,latest


def _state(value: str) -> OpportunityState:
    return OpportunityState(value)


def build_entries(bundle: dict, positions: tuple[Position, ...]) -> tuple[BoardEntry, ...]:
    position_by_claim = {(position.series_id, position.side): position for position in positions}
    if len(position_by_claim) != len(positions):
        raise ValueError(
            "Position evidence contains duplicate current summaries for the same "
            "provider market and side"
        )
    used_positions=set()
    entries = []
    for index, case in enumerate(bundle.get("cases", ())):
        entry_id = str(case.get("entry_id") or f"case:{index + 1}")
        game = str(case.get("game") or "Unknown game")
        scheduled = datetime.fromisoformat(case["scheduled_start"]) if case.get("scheduled_start") else None
        proposition_label = str(case.get("proposition") or "Unknown proposition")
        forecast = _decode_forecast(case.get("forecast"))
        market_results = _decode_markets(case)
        comparison_result,market_result = select_market_results(market_results,scheduled)
        display_case=dict(case)
        if market_result is not None: display_case["market_result"]=market_result.to_dict()
        diagnostics = (("Input", json.dumps(display_case, sort_keys=True, default=str)),)
        issues = []
        if forecast is None:
            issues.append("missing forecast observation")
        if not market_results:
            issues.append("missing market result")
        if issues:
            entries.append(BoardEntry(entry_id, OpportunityState.PARTIAL, game, scheduled, proposition_label, None, None, None, None, None, forecast.collected_at if forecast else None, market_result.observation.collected_at if market_result and market_result.observation else None, tuple(issues), diagnostics))
            continue
        unresolved=next((result for result in market_results if result.outcome in (MarketAdapterOutcome.AMBIGUOUS,MarketAdapterOutcome.REJECTED)),None)
        if market_result is None and unresolved is not None:
            state = OpportunityState.AMBIGUOUS if unresolved.outcome is MarketAdapterOutcome.AMBIGUOUS else OpportunityState.REJECTED
            entries.append(BoardEntry(entry_id,state,game,scheduled,proposition_label,unresolved.provider_market_id,None,None,None,None,forecast.collected_at,None,tuple(issue.detail for issue in unresolved.issues),diagnostics))
            continue
        series = market_result.series; observation = market_result.observation; proposition = market_result.proposition
        requested_side = MarketSide(str(case.get("side", "yes")).lower())
        position = position_by_claim.get((series.series_id, requested_side), Position.none(series.series_id, series.proposition_id, observation.canonical_event_id, requested_side))
        if position.exists: used_positions.add((position.series_id, position.side))
        if position.proposition_id != series.proposition_id or position.canonical_event_id != observation.canonical_event_id:
            raise ValueError("position summary proposition or event conflicts with the Market Series")
        if comparison_result is None and observation.status is MarketStatus.OPEN and observation.order_book:
            liquidation=analyze_liquidation(position,observation)
            timing_issue=("Event start chronology is unavailable. Forecast-versus-market valuation is not temporally comparable."
                          if scheduled is None else
                          "Forecast evidence is pregame. Market evidence was captured at or after the scheduled event start. Forecast-versus-market valuation is not temporally comparable.")
            entries.append(BoardEntry(entry_id,OpportunityState.NON_EXECUTABLE,game,scheduled,proposition_label,series.ticker,None,position,liquidation,liquidation.total_cost_basis,forecast.collected_at,observation.collected_at,(timing_issue,),(('Latest Market For Liquidation',observation.to_json()),('Input',diagnostics[0][1]))))
            continue
        if observation.status is not MarketStatus.OPEN or not observation.order_book:
            liquidation = analyze_liquidation(position, observation)
            reason = "market is not open" if observation.status is not MarketStatus.OPEN else "requested market has no executable depth"
            entries.append(BoardEntry(entry_id, OpportunityState.NON_EXECUTABLE, game, scheduled, proposition_label, series.ticker, None, position, liquidation, liquidation.total_cost_basis, forecast.collected_at, observation.collected_at, (reason,) + tuple(issue.detail for issue in observation.issues), (("Market", observation.to_json()), ("Input", diagnostics[0][1]))))
            continue
        fee_value = Decimal(str(case.get("fee_per_contract", "0")))
        fee_model = ZeroFeeModel() if fee_value == 0 else FlatPerContractFeeModel(fee_value)
        try:
            comparison=comparison_result.observation
            valuation = value_market(forecast=forecast, market=comparison, proposition=comparison_result.proposition, series=comparison_result.series,
                                     side=requested_side, quantity=Decimal(str(case.get("quantity", "1"))),
                                     fee_model=fee_model, event_scheduled_start=scheduled)
            opportunity = build_opportunity(forecast=forecast, observation=comparison, series=comparison_result.series,
                                            valuation=valuation, position=position, game=game, scheduled_start=scheduled,liquidation_observation=observation)
            opportunity=replace(opportunity,diagnostics=opportunity.diagnostics+diagnostics)
            entries.append(BoardEntry(entry_id, opportunity.state, game, scheduled, proposition_label, series.ticker, opportunity, position, analyze_liquidation(position, observation), opportunity.position_cost_basis, forecast.collected_at, observation.collected_at, opportunity.issues, opportunity.diagnostics))
        except (ContractError, ValueError) as error:
            entries.append(BoardEntry(entry_id, OpportunityState.NON_EXECUTABLE, game, scheduled, proposition_label, series.ticker, None, position, None, position.quantity * position.average_cost, forecast.collected_at, observation.collected_at, (str(error),), diagnostics))
    unused=set(position_by_claim)-used_positions
    if unused: raise ValueError("position summary references an unknown or unrepresented Market Series/side")
    return tuple(entries)


def notification_lines(entries: tuple[BoardEntry, ...]) -> tuple[str, ...]:
    existing = sum(1 for entry in entries if entry.position and entry.position.exists)
    positive = sum(1 for entry in entries if entry.opportunity and entry.opportunity.expected_value > 0)
    ambiguous = sum(1 for entry in entries if entry.state is OpportunityState.AMBIGUOUS)
    incomplete = sum(1 for entry in entries if entry.state in (OpportunityState.PARTIAL, OpportunityState.REJECTED, OpportunityState.NON_EXECUTABLE))
    groups={}
    for entry in entries: groups.setdefault((entry.game,entry.scheduled_start),[]).append(entry)
    statuses=[_status_label(tuple(group)) for group in groups.values()]
    return ("Forecast inputs processed", "Market inputs processed", f"{len(entries)} analyses processed", f"{existing} existing positions", f"{positive} positive gross-edge analyses", f"{ambiguous} ambiguous reconciliations", f"{incomplete} incomplete or non-executable analyses",f"{statuses.count('In Play')} in-play games",f"{statuses.count('Settled')} settled games")


def run(bundle_path: str | Path, output_path: str | Path, positions_path: str | Path) -> tuple[BoardEntry, ...]:
    bundle = validate_bundle(json.loads(Path(bundle_path).read_text(encoding="utf-8")))
    generated_at = datetime.fromisoformat(bundle["generated_at"])
    entries = build_entries(bundle, read_positions(positions_path))
    render_opportunity_board(entries, generated_at=generated_at, output_path=output_path)
    for line in notification_lines(entries):
        print(line)
    print(f"Opportunity Board: {output_path}")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="local JSON evidence bundle")
    parser.add_argument("--positions", required=True, help="authoritative current open-position summary CSV; headers-only means no positions")
    parser.add_argument("--output", default="Opportunity_Board.html")
    args = parser.parse_args()
    try:
        run(args.bundle, args.output, args.positions)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ContractError) as error:
        print(f"Opportunity Board failed: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
