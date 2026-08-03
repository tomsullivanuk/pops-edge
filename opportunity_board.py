"""Derived Opportunity presentation and sortable HTML board."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo

from event_contracts import ContractError, ReasonCode, _require_aware, _require_identifier
from forecast_contracts import ForecastObservation
from market_contracts import MarketObservation, MarketSide, MarketStatus, PriceEvidenceKind, ProviderMarketSeries
from market_valuation import MarketValuation


class OpportunityState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    NON_EXECUTABLE = "non-executable"


@dataclass(frozen=True, slots=True)
class Position:
    series_id: str
    proposition_id: str
    canonical_event_id: str
    side: MarketSide
    quantity: Decimal
    average_cost: Decimal
    captured_at: datetime | None = None
    source_reference: str = "manual-position-input"
    entry_fees: Decimal = Decimal(0)
    exit_fees: Decimal = Decimal(0)
    evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.series_id, "position series_id")
        _require_identifier(self.proposition_id, "position proposition_id")
        _require_identifier(self.canonical_event_id, "position canonical_event_id")
        if self.quantity < 0 or self.average_cost < 0 or self.average_cost > 1 or self.entry_fees < 0 or self.exit_fees < 0:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "position quantity or cost is outside its valid range")
        if self.captured_at is not None: _require_aware(self.captured_at, "position captured_at")
        if self.evidence_sha256 is not None and (len(self.evidence_sha256)!=64 or any(char not in "0123456789abcdef" for char in self.evidence_sha256)):
            raise ContractError(ReasonCode.VALIDATION_FAILURE,"position evidence_sha256 must be lowercase SHA-256")

    @classmethod
    def none(cls, series_id: str, proposition_id: str, canonical_event_id: str, side: MarketSide) -> "Position":
        return cls(series_id, proposition_id, canonical_event_id, side, Decimal(0), Decimal(0), None, "no-position")

    @property
    def exists(self) -> bool:
        return self.quantity > 0


@dataclass(frozen=True, slots=True)
class Opportunity:
    opportunity_id: str
    forecast_observation_id: str
    market_observation_id: str
    valuation_id: str
    position: Position
    series_id: str
    game: str
    scheduled_start: datetime
    proposition: str
    state: OpportunityState
    forecast_probability: Decimal
    acquisition_price: Decimal
    expected_value: Decimal
    expected_return: Decimal
    liquidity: Decimal
    position_quantity: Decimal
    executable_liquidation_quantity: Decimal
    unpriced_position_quantity: Decimal
    executable_liquidation_proceeds: Decimal | None
    average_executable_exit_price: Decimal | None
    marginal_executable_exit_price: Decimal | None
    position_cost_basis: Decimal
    executable_position_cost_basis: Decimal | None
    executable_position_profit_loss: Decimal | None
    executable_position_return: Decimal | None
    liquidation_levels: tuple[tuple[Decimal, Decimal, int], ...]
    status: str
    forecast_captured_at: datetime
    market_captured_at: datetime
    position_captured_at: datetime | None
    component_timing_spread_seconds: Decimal
    issues: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        for value, label in ((self.opportunity_id, "opportunity_id"), (self.series_id, "series_id")):
            _require_identifier(value, label)
        if self.position.series_id != self.series_id:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "position belongs to a different Market Series")


@dataclass(frozen=True, slots=True)
class BoardEntry:
    entry_id: str
    state: OpportunityState
    game: str
    scheduled_start: datetime | None
    proposition: str
    market_ticker: str | None
    opportunity: Opportunity | None
    display_position: Position | None
    display_liquidation: "LiquidationAnalysis | None"
    display_cost_basis: Decimal | None
    forecast_captured_at: datetime | None
    market_captured_at: datetime | None
    issues: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]

    @property
    def position(self) -> Position | None:
        return self.opportunity.position if self.opportunity else self.display_position


@dataclass(frozen=True, slots=True)
class LiquidationAnalysis:
    held_quantity: Decimal
    executable_quantity: Decimal
    unpriced_quantity: Decimal
    gross_proceeds: Decimal | None
    average_exit_price: Decimal | None
    marginal_exit_price: Decimal | None
    total_cost_basis: Decimal
    executable_cost_basis: Decimal | None
    executable_profit_loss: Decimal | None
    executable_return: Decimal | None
    levels: tuple[tuple[Decimal, Decimal, int], ...]
    fully_liquidatable: bool
    limitation: str | None


def analyze_liquidation(position: Position, observation: MarketObservation) -> LiquidationAnalysis:
    total_basis = position.quantity * position.average_cost
    if not position.exists:
        return LiquidationAnalysis(Decimal(0), Decimal(0), Decimal(0), Decimal(0), None, None, Decimal(0), Decimal(0), Decimal(0), None, (), True, None)
    if observation.status is not MarketStatus.OPEN:
        return LiquidationAnalysis(position.quantity, Decimal(0), position.quantity, None, None, None, total_basis, None, None, None, (), False, f"market status {observation.status.value} is not executable")
    # PR7 acquisition offers retain the opposing provider bid. Selling a held
    # side consumes the direct provider bids whose provider_book_side matches it.
    bids = sorted((level for level in observation.order_book if level.evidence_kind is PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID and level.provider_book_side is position.side), key=lambda level: (-level.provider_price, level.level))
    remaining = position.quantity; proceeds = Decimal(0); consumed = []
    for level in bids:
        take = min(remaining, level.quantity)
        if take > 0:
            consumed.append((level.provider_price, take, level.level)); proceeds += level.provider_price * take; remaining -= take
        if remaining == 0: break
    executed = position.quantity - remaining
    if executed == 0:
        return LiquidationAnalysis(position.quantity, Decimal(0), position.quantity, None, None, None, total_basis, None, None, None, (), False, "no visible executable liquidation depth")
    executable_basis = executed * position.average_cost
    profit_loss = proceeds - executable_basis
    return LiquidationAnalysis(position.quantity, executed, remaining, proceeds, proceeds / executed, consumed[-1][0], total_basis, executable_basis, profit_loss, profit_loss / executable_basis if executable_basis else None, tuple(consumed), remaining == 0, None if remaining == 0 else "P/L applies only to executable quantity; remaining quantity is unpriced")


def build_opportunity(*, forecast: ForecastObservation, observation: MarketObservation, series: ProviderMarketSeries,
                      valuation: MarketValuation, position: Position, game: str, scheduled_start: datetime,
                      liquidation_observation: MarketObservation | None = None) -> Opportunity:
    if valuation.forecast_observation_id != forecast.observation_id or valuation.market_observation_id != observation.observation_id:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "valuation references incompatible evidence")
    if observation.series_id != series.series_id or position.series_id != series.series_id:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "Opportunity inputs do not share one Market Series")
    if position.proposition_id != series.proposition_id or position.canonical_event_id != observation.canonical_event_id:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "position proposition or event is incompatible")
    if position.side is not valuation.side:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "position side does not match the valued claim side")
    state = OpportunityState.COMPLETE
    issues = tuple(issue.detail for issue in observation.issues) + valuation.issues
    if issues:
        state = OpportunityState.PARTIAL
    if observation.status is not MarketStatus.OPEN or valuation.executable_quantity <= 0:
        state = OpportunityState.NON_EXECUTABLE
    latest_observation=liquidation_observation or observation
    if latest_observation.series_id != series.series_id or latest_observation.canonical_event_id != observation.canonical_event_id:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"liquidation observation belongs to a different Market Series or event")
    liquidation = analyze_liquidation(position, latest_observation)
    if liquidation.limitation and state is OpportunityState.COMPLETE:
        state = OpportunityState.PARTIAL
    liquidity = sum((level.quantity for level in observation.order_book if level.acquisition_side is valuation.side), Decimal(0))
    diagnostics = (
        ("Forecast", forecast.to_json()),
        ("Market", observation.to_json()),
        ("Latest Market For Liquidation", latest_observation.to_json()),
        ("Valuation", valuation.to_json()),
        ("Reconciliation", forecast.reconciliation.to_json()),
        ("Provenance", json.dumps({"forecast": forecast.provenance.to_dict(), "market": observation.provenance.to_dict()}, sort_keys=True, default=str)),
    )
    diagnostics = diagnostics + (("Position Liquidation", json.dumps({
        "held_quantity": str(liquidation.held_quantity),
        "executable_quantity": str(liquidation.executable_quantity),
        "unpriced_quantity": str(liquidation.unpriced_quantity),
        "gross_proceeds": None if liquidation.gross_proceeds is None else str(liquidation.gross_proceeds),
        "average_exit_price": None if liquidation.average_exit_price is None else str(liquidation.average_exit_price),
        "marginal_exit_price": None if liquidation.marginal_exit_price is None else str(liquidation.marginal_exit_price),
        "levels": [[str(price), str(quantity), level] for price, quantity, level in liquidation.levels],
        "fully_liquidatable": liquidation.fully_liquidatable,
        "limitation": liquidation.limitation,
    }, sort_keys=True)),)
    return Opportunity(
        f"opportunity:{valuation.analysis_id}", forecast.observation_id, observation.observation_id,
        valuation.analysis_id, position, series.series_id, game, scheduled_start,
        (series.yes_semantic if valuation.side is MarketSide.YES else series.no_semantic).provider_label + " wins", state, valuation.forecast_probability,
        valuation.average_executable_price or Decimal(0), valuation.expected_value_per_contract or Decimal(0),
        valuation.expected_return_on_capital or Decimal(0), liquidity, position.quantity,
        liquidation.executable_quantity, liquidation.unpriced_quantity, liquidation.gross_proceeds,
        liquidation.average_exit_price, liquidation.marginal_exit_price, liquidation.total_cost_basis,
        liquidation.executable_cost_basis, liquidation.executable_profit_loss, liquidation.executable_return,
        liquidation.levels, observation.status.value, forecast.collected_at, observation.collected_at,
        position.captured_at, observation.component_timing_spread_seconds,
        issues + ((liquidation.limitation,) if liquidation.limitation else ()), diagnostics,
    )


def attention_key(entry: BoardEntry) -> tuple:
    opportunity = entry.opportunity
    position = entry.position
    if position and position.exists and not opportunity:
        liquidation = entry.display_liquidation
        adverse = liquidation and liquidation.executable_profit_loss is not None and liquidation.executable_profit_loss < 0
        constrained = not liquidation or liquidation.unpriced_quantity > 0
        return (0, 0 if constrained else 1, liquidation.executable_profit_loss if adverse else Decimal(0), -entry.display_cost_basis if entry.display_cost_basis else Decimal(0), entry.entry_id)
    if opportunity and position and position.exists:
        adverse = opportunity.executable_position_profit_loss is not None and opportunity.executable_position_profit_loss < 0
        constrained = opportunity.unpriced_position_quantity > 0
        if adverse or constrained or entry.state is OpportunityState.NON_EXECUTABLE:
            return (0, 0 if constrained else 1, opportunity.executable_position_profit_loss or Decimal(0), -opportunity.position_cost_basis, entry.entry_id)
    if entry.state in (OpportunityState.AMBIGUOUS, OpportunityState.REJECTED, OpportunityState.PARTIAL, OpportunityState.NON_EXECUTABLE):
        order = {OpportunityState.AMBIGUOUS: 0, OpportunityState.REJECTED: 1, OpportunityState.PARTIAL: 2, OpportunityState.NON_EXECUTABLE: 3}
        return (1, order[entry.state], entry.entry_id)
    if opportunity and position and position.exists:
        return (2, -opportunity.position_cost_basis, entry.entry_id)
    if opportunity and opportunity.expected_value > 0:
        return (3, -opportunity.expected_value, -opportunity.liquidity, entry.entry_id)
    return (4, entry.entry_id)


def sorted_entries(entries: tuple[BoardEntry, ...]) -> tuple[BoardEntry, ...]:
    return tuple(sorted(entries, key=attention_key))


def _money(value: Decimal | None) -> str:
    return "—" if value is None else f"${value:.2f}"


def _percent(value: Decimal | None) -> str:
    return "—" if value is None else f"{value * 100:.2f}%"


_DISPLAY_TIMEZONE = ZoneInfo("America/Chicago")


def _local_time(value: datetime | None, reference: datetime, *, long: bool = False) -> str:
    if value is None: return "Unknown"
    local=value.astimezone(_DISPLAY_TIMEZONE); today=reference.astimezone(_DISPLAY_TIMEZONE).date()
    clock=local.strftime("%I:%M %p").lstrip("0")
    if long: return f"{local.strftime('%B')} {local.day}, {local.year} {clock} {local.tzname()}"
    return f"Today {clock}" if local.date()==today else f"{local.strftime('%a %b')} {local.day} {clock}"


def _capture_range(values: set[datetime], reference: datetime) -> str:
    if not values: return "Unknown"
    first=min(values); last=max(values)
    if first==last: return _local_time(first,reference,long=True)
    start=first.astimezone(_DISPLAY_TIMEZONE); end=last.astimezone(_DISPLAY_TIMEZONE)
    if start.date()==end.date() and start.tzname()==end.tzname():
        start_clock=start.strftime("%I:%M:%S %p").lstrip("0")
        end_clock=end.strftime("%I:%M:%S %p").lstrip("0")
        return f"{start.strftime('%B')} {start.day}, {start.year} {start_clock}–{end_clock} {start.tzname()}"
    return f"{_local_time(first,reference,long=True)}–{_local_time(last,reference,long=True)}"


def _diagnostic_json(entry: BoardEntry, label: str):
    diagnostics=entry.opportunity.diagnostics if entry.opportunity else entry.diagnostics
    for name,value in diagnostics:
        if name==label:
            try: return json.loads(value)
            except (TypeError,json.JSONDecodeError): return None
    return None


def _input_payload(entry: BoardEntry) -> dict:
    value=_diagnostic_json(entry,"Input")
    return value if isinstance(value,dict) else {}


def _forecast_payload(entry: BoardEntry) -> dict:
    value=_input_payload(entry).get("forecast") or _diagnostic_json(entry,"Forecast")
    return value if isinstance(value,dict) else {}


def _market_payload(entry: BoardEntry) -> dict:
    source=_input_payload(entry)
    histories=source.get("market_results")
    value=histories[-1] if isinstance(histories,list) and histories else source.get("market_result")
    return value if isinstance(value,dict) else {}


def _decimal_payload(value) -> Decimal | None:
    try:
        if isinstance(value,dict) and "__decimal__" in value: return Decimal(value["__decimal__"])
        return Decimal(str(value)) if value is not None else None
    except Exception: return None


def _game_names(entries: tuple[BoardEntry,...]) -> tuple[str,str]:
    game=entries[0].game
    if " at " in game: return tuple(game.split(" at ",1))
    if " @ " in game: return tuple(game.split(" @ ",1))
    return (game,"")


def _participant_map(entry: BoardEntry) -> dict[str,str]:
    event=_forecast_payload(entry).get("reconciliation",{}).get("matched_event") or {}
    return {item.get("canonical_id"):item.get("display_name") for item in event.get("participants",[]) if item.get("canonical_id") and item.get("display_name")}


def _canonical_participant_order(entry: BoardEntry) -> tuple[int,str]:
    event=_forecast_payload(entry).get("reconciliation",{}).get("matched_event") or {}
    participant_ids=[item.get("canonical_id") for item in event.get("participants",[]) if item.get("canonical_id")]
    series=_market_payload(entry).get("series") or {}
    yes_id=(series.get("yes_semantic") or {}).get("participant_id")
    if not yes_id:
        claim=entry.proposition.removesuffix(" wins").strip().lower()
        for item in event.get("participants",[]):
            display=str(item.get("display_name") or "").lower()
            if claim and (claim in display or display in claim): yes_id=item.get("canonical_id"); break
    try: return (participant_ids.index(yes_id),entry.entry_id)
    except ValueError: return (len(participant_ids),entry.entry_id)


def _forecast_display(entries: tuple[BoardEntry,...]) -> str:
    forecast=_forecast_payload(entries[0]); probabilities=forecast.get("distribution",{}).get("probabilities",[])
    away,home=_game_names(entries)
    lines=[]
    probabilities=sorted(probabilities,key=lambda item: (0 if "away" in str(item.get("outcome",{}).get("semantic") or "") else 1 if "home" in str(item.get("outcome",{}).get("semantic") or "") else 2))
    for item in probabilities:
        outcome=item.get("outcome",{}); semantic=str(outcome.get("semantic") or "")
        label=outcome.get("provider_label") or (away if "away" in semantic else home if "home" in semantic else semantic) or "Team"
        source=item.get("source_representation")
        if not source:
            value=_decimal_payload(item.get("probability")); source=_percent(value)
        lines.append(f'<div class="metric-line"><span>{html.escape(str(label))}</span><strong>{html.escape(str(source))}</strong></div>')
    return "".join(lines) or '<span class="muted">Unavailable</span>'


def _market_line(entry: BoardEntry) -> tuple[str,str]:
    payload=_market_payload(entry); series=payload.get("series") or {}; observation=payload.get("observation") or {}
    yes=series.get("yes_semantic") or {}; participant_id=yes.get("participant_id")
    participants=_participant_map(entry); label=participants.get(participant_id)
    if not label:
        claim=entry.proposition.removesuffix(" wins").strip().lower()
        label=next((display for display in participants.values() if claim and (claim in display.lower() or display.lower() in claim)),None)
    label=label or yes.get("provider_label") or entry.proposition.removesuffix(" wins")
    ask=_decimal_payload((observation.get("quotes") or {}).get("yes_ask"))
    price=f"{ask*100:.1f}¢" if ask is not None else (f"{entry.opportunity.acquisition_price*100:.1f}¢" if entry.opportunity else "—")
    return str(label),price


def _status_label(entries: tuple[BoardEntry,...]) -> str:
    issues=" ".join(issue.lower() for entry in entries for issue in entry.issues)
    if any(entry.state is OpportunityState.REJECTED for entry in entries): return "Rejected"
    if any(entry.state is OpportunityState.AMBIGUOUS for entry in entries): return "Ambiguous"
    statuses={str((_market_payload(entry).get("observation") or {}).get("status",{}).get("__enum__","")).split(":")[-1] for entry in entries}
    for value,label in (("settled","Settled"),("cancelled","Cancelled"),("suspended","Suspended")):
        if value in statuses: return label
    if "event start chronology is unavailable" in issues: return "Timing Incompatible"
    if "forecast-versus-market valuation is not temporally comparable" in issues: return "In Play"
    if any(entry.state is OpportunityState.PARTIAL for entry in entries): return "Partial"
    if "depth" in issues: return "Missing Depth"
    if any(entry.state is OpportunityState.NON_EXECUTABLE for entry in entries): return "Non-executable"
    return "Complete"


def _entry_details(entry: BoardEntry, reference: datetime) -> str:
    item=entry.opportunity; position=entry.position; payload=_market_payload(entry); observation=payload.get("observation") or {}; forecast=_forecast_payload(entry)
    event_id=observation.get("canonical_event_id") or (forecast.get("provenance") or {}).get("canonical_event_id") or "Unavailable"
    market_id=observation.get("provider_market_id") or entry.market_ticker or "Unavailable"
    game_id=str(event_id).split(":",1)[1] if str(event_id).startswith("mlb:") else "Unavailable"
    timing=item.component_timing_spread_seconds if item else "Unavailable"
    position_capture=item.position_captured_at if item else position.captured_at if position else None
    identity=f'''<div class="identity-grid"><span>Canonical Event ID<strong>{html.escape(str(event_id))}</strong></span><span>MLB Game ID<strong>{html.escape(game_id)}</strong></span><span>Provider Market ID<strong>{html.escape(str(market_id))}</strong></span></div>'''
    captures=f'''<div class="identity-grid"><span>Event Start<strong>{html.escape(_local_time(entry.scheduled_start,reference,long=True))}</strong></span><span>Forecast Capture<strong>{html.escape(_local_time(entry.forecast_captured_at,reference,long=True))}</strong></span><span>Latest Market / Liquidation Capture<strong>{html.escape(_local_time(entry.market_captured_at,reference,long=True))}</strong></span><span>Position Capture<strong>{html.escape(_local_time(position_capture,reference,long=True))}</strong></span><span>Timing Spread<strong>{html.escape(str(timing))} seconds</strong></span><span>Temporal Compatibility<strong>{"Pregame comparison" if item else "Not comparable"}</strong></span></div>'''
    valuation=_diagnostic_json(entry,"Valuation") or {}; comparison_market=_diagnostic_json(entry,"Market") or {}; latest_market=_diagnostic_json(entry,"Latest Market For Liquidation") or {}
    comparison_id=comparison_market.get("observation_id") or "Unavailable"; latest_id=latest_market.get("observation_id") or observation.get("observation_id") or "Unavailable"
    gross_profit=_decimal_payload(valuation.get("expected_profit")); gross_return=_decimal_payload(valuation.get("expected_return_on_capital"))
    analysis_evidence=f'''<div class="identity-grid"><span>Pregame Comparison Observation<strong>{html.escape(str(comparison_id))}</strong></span><span>Latest Liquidation Observation<strong>{html.escape(str(latest_id))}</strong></span><span>Gross Expected Profit<strong>{html.escape(_money(gross_profit))}</strong></span><span>Gross Return<strong>{html.escape(_percent(gross_return))}</strong></span><span>Fee Model<strong>{html.escape(str(valuation.get("fee_model_id") or "Not applied"))}</strong></span><span>Fee Limitation<strong>Gross before Kalshi fees; production net EV unavailable</strong></span><span>Provider Source Order<strong>Preserved in evidence</strong></span><span>Presentation Order<strong>Away team, then home team</strong></span></div>'''
    position_evidence=f'''<div class="identity-grid"><span>Position Source<strong>{html.escape(position.source_reference if position else "No position")}</strong></span><span>Entry Fees<strong>{html.escape(_money(position.entry_fees) if position else "—")}</strong></span><span>Exit Fees<strong>{html.escape(_money(position.exit_fees) if position else "—")}</strong></span><span>Evidence SHA-256<strong>{html.escape(position.evidence_sha256 if position and position.evidence_sha256 else "Unavailable")}</strong></span></div>'''
    issues='<div class="issue-box"><strong>Validation issues</strong><br>'+html.escape("; ".join(entry.issues) or "None")+'</div>'
    diagnostics=item.diagnostics if item else entry.diagnostics
    raw="".join(f'<details class="diagnostic"><summary>{html.escape(label)}</summary><pre>{html.escape(value)}</pre></details>' for label,value in diagnostics)
    return f'<section class="proposition-detail"><h3>{html.escape(entry.proposition)}</h3>{identity}{captures}{analysis_evidence}{position_evidence}{issues}{raw}</section>'


def render_opportunity_board(entries: tuple[BoardEntry, ...], *, generated_at: datetime, output_path: str | Path) -> str:
    ordered=sorted_entries(entries); groups=[]; positions={}
    for entry in ordered:
        key=(entry.game,entry.scheduled_start)
        if key not in positions: positions[key]=len(groups); groups.append([])
        groups[positions[key]].append(entry)
    rows=[]
    for rank,raw_group in enumerate(groups,1):
        group=tuple(sorted(raw_group,key=_canonical_participant_order)); away,home=_game_names(group); status=_status_label(group)
        market="".join(f'<div class="metric-line"><span>{html.escape(label)}</span><strong>{html.escape(price)}</strong></div>' for label,price in (_market_line(entry) for entry in group))
        edge="".join(f'<div class="metric-line"><span>{html.escape(_market_line(entry)[0])}</span><strong class="edge">{html.escape(_money(entry.opportunity.expected_value) if entry.opportunity else "—")}</strong></div>' for entry in group)
        held=[entry for entry in group if entry.position and entry.position.exists]
        position_html="".join(f'<span class="position-chip">● {html.escape(_market_line(entry)[0])} {entry.position.side.value.upper()}</span>' for entry in held) or '<span class="muted">None</span>'
        shares=sum((entry.position.quantity for entry in held),Decimal(0)); costs=sum((entry.position.quantity*entry.position.average_cost for entry in held),Decimal(0))
        average=costs/shares if shares else None
        current_values=[entry.opportunity.executable_liquidation_proceeds if entry.opportunity else entry.display_liquidation.gross_proceeds if entry.display_liquidation else None for entry in held]
        profit_values=[entry.opportunity.executable_position_profit_loss if entry.opportunity else entry.display_liquidation.executable_profit_loss if entry.display_liquidation else None for entry in held]
        current=sum(current_values,Decimal(0)) if held and all(value is not None for value in current_values) else None
        profit=sum(profit_values,Decimal(0)) if held and all(value is not None for value in profit_values) else None
        details="".join(_entry_details(entry,generated_at) for entry in group)
        game_name=f"{away} @ {home}" if home else away
        game_cell=f'<div class="game-title">{html.escape(game_name)}</div><details class="game-details"><summary>View details</summary>{details}</details>'
        values=(rank,game_cell,_local_time(group[0].scheduled_start,generated_at),_forecast_display(group),market,edge,position_html,str(shares) if shares else "—",_money(average),_money(current),_money(profit),f'<span class="status status-{status.lower().replace(" ","-")}">{html.escape(status)}</span>')
        cells="".join(f'<td>{value if i in (1,3,4,5,6,11) else html.escape(str(value))}</td>' for i,value in enumerate(values))
        rows.append(f'<tr class="game-row {"has-position" if held else ""}">{cells}</tr>')
    headers=("#","Game","Scheduled Time","DRatings","Kalshi","Gross Edge","Position","Shares","Average Cost","Current Value","Unrealized P/L","Status")
    head = "".join(f"<th>{html.escape(column)}</th>" for column in headers)
    forecast_times={entry.forecast_captured_at for entry in entries if entry.forecast_captured_at}; market_times={entry.market_captured_at for entry in entries if entry.market_captured_at}
    forecast_header=_capture_range(forecast_times,generated_at)
    market_header=_capture_range(market_times,generated_at)
    document = f'''<!doctype html><html><head><meta charset="utf-8"><title>Pops' Edge Opportunity Board</title>
<style>:root{{--ink:#172033;--muted:#667085;--line:#e6eaf0;--navy:#18243a;--blue:#2864dc;--green:#087a55;--amber:#9a6700}}*{{box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f3f6fa;color:var(--ink)}}.shell{{max-width:1600px;margin:0 auto;padding:32px}}header{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:22px}}h1{{font-size:28px;margin:0 0 5px}}.subtitle,.muted{{color:var(--muted)}}.captures{{display:flex;gap:24px;font-size:12px;color:var(--muted)}}.captures strong{{display:block;color:var(--ink);font-size:13px;margin-top:3px}}.table-wrap{{background:white;border:1px solid var(--line);border-radius:14px;overflow:auto;box-shadow:0 8px 28px #1b294508}}table{{border-collapse:separate;border-spacing:0;width:100%;min-width:1200px;font-size:13px}}th{{background:var(--navy);color:white;padding:12px;text-align:left;cursor:pointer;position:sticky;top:0;z-index:2;font-size:11px;text-transform:uppercase;letter-spacing:.05em}}td{{padding:14px 12px;border-bottom:1px solid var(--line);vertical-align:top}}tr:last-child td{{border-bottom:0}}tr:hover td{{background:#f8faff}}tr.has-position td{{background:#f0fbf7}}.game-title{{font-weight:700;font-size:14px;white-space:nowrap}}.metric-line{{display:flex;justify-content:space-between;gap:18px;min-width:165px;margin-bottom:5px}}.metric-line strong{{font-variant-numeric:tabular-nums}}.edge{{color:var(--green)}}.position-chip{{display:block;background:#dff7ed;color:#08654a;border-radius:999px;padding:4px 8px;margin-bottom:4px;font-weight:700;white-space:nowrap}}.status{{display:inline-block;border-radius:999px;padding:5px 9px;font-weight:700;white-space:nowrap;background:#edf1f6}}.status-complete{{background:#dcfce7;color:#166534}}.status-partial,.status-missing-depth,.status-suspended{{background:#fff3cd;color:#805b00}}.status-ambiguous,.status-rejected{{background:#fee2e2;color:#991b1b}}.status-in-play{{background:#dbeafe;color:#1e40af}}.status-settled{{background:#ede9fe;color:#5b21b6}}.game-details{{margin-top:8px;min-width:310px}}.game-details>summary{{color:var(--blue);cursor:pointer;font-weight:600}}.proposition-detail{{margin:14px 0;padding:16px;background:#f8fafc;border:1px solid var(--line);border-radius:10px}}.proposition-detail h3{{margin:0 0 12px}}.identity-grid{{display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:8px;margin:10px 0}}.identity-grid span{{font-size:11px;color:var(--muted)}}.identity-grid strong{{display:block;color:var(--ink);font-size:12px;margin-top:3px;word-break:break-word}}.issue-box{{border-left:3px solid #e0a100;padding:8px 10px;margin:10px 0;background:#fffaf0}}.diagnostic{{margin:7px 0}}.diagnostic summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;max-height:300px;overflow:auto;background:#111827;color:#e5e7eb;padding:12px;border-radius:7px;font-size:11px}}</style></head>
<body><div class="shell"><header><div><h1>Pops' Edge Opportunity Board</h1><div class="subtitle">Attention-ranked game dashboard • Generated {html.escape(_local_time(generated_at,generated_at,long=True))}<br>Analysis basis: 1 contract, gross before Kalshi fees. Production net EV is not yet available.</div></div><div class="captures"><span>Forecast captured<strong>{html.escape(forecast_header)}</strong></span><span>Market books captured<strong>{html.escape(market_header)}</strong></span></div></header><div class="table-wrap"><table id="board"><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>
<script>const parse=v=>{{v=v.trim();if(v==='—')return Number.NEGATIVE_INFINITY;if(v.endsWith('%'))return parseFloat(v);const n=Number(v.replace(/[$,]/g,''));return Number.isNaN(n)?v.toLowerCase():n}};document.querySelectorAll('th').forEach((h,i)=>{{let asc=true;h.onclick=()=>{{const b=document.querySelector('tbody'),r=[...b.rows];r.sort((a,c)=>{{const x=parse(a.cells[i].innerText),y=parse(c.cells[i].innerText);return(x<y?-1:x>y?1:0)*(asc?1:-1)}});r.forEach(x=>b.appendChild(x));asc=!asc}}}});</script></body></html>'''
    Path(output_path).write_text(document, encoding="utf-8")
    return document
