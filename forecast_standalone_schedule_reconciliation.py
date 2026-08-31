"""Explicit, bounded MLB calendar reconciliation; never reconstructs quotes."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from forecast_standalone_activation import (
    APPROVED_EASTERN_DATE, APPROVED_TIMEZONE, MAX_RESPONSE_BYTES,
    ProviderPageAcquisition, _unique_object, canonical_mlb_schedule_request,
    merge_mlb_schedule_responses, publish_verified_acquisition,
    refresh_supporting_from_raw, resolve_activated_authority,
    verify_acquisition_bundle,
)
from forecast_standalone_operations import (
    DesignAuthority, Disposition, NamespaceArchive, OperationsError, _entry_values,
    authoritative_entries, replay_pr17_archive, request_identity,
)

COMMAND = "reconcile-prospective-schedule"
MAX_DATES = 31
RECEIPT_COMMAND = COMMAND + "-receipt"
LIMITATION = "Later schedule retrieval cannot reconstruct unobserved historical schedule states or missed quotes."


def validate_date_page(raw: bytes, day: date) -> None:
    """Require explicit complete date material, including provider-declared emptiness."""
    if len(raw) > MAX_RESPONSE_BYTES:
        raise OperationsError("transport-oversized", "MLB date response exceeds the bound")
    try:
        value = json.loads(raw, object_pairs_hook=lambda pairs: _unique_object(pairs, "MLB"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise OperationsError("malformed-response", "MLB date response is malformed") from exc
    records = value.get("dates") if isinstance(value, dict) else None
    if not isinstance(records, list) or len(records) > 1:
        raise OperationsError("schedule-date-incomplete", "Expected one requested MLB date or explicit empty response")
    count = 0
    for record in records:
        if not isinstance(record, dict) or record.get("date") != day.isoformat() or not isinstance(record.get("games"), list):
            raise OperationsError("schedule-date-conflict", "MLB response does not match requested date")
        count += len(record["games"])
        if any(not isinstance(game, dict) for game in record["games"]):
            raise OperationsError("schedule-date-incomplete", "MLB game record is malformed")
        if "totalGames" in record and (type(record["totalGames"]) is not int or record["totalGames"] != count):
            raise OperationsError("schedule-date-incomplete", "MLB date total conflicts with records")
    if "totalGames" in value and (type(value["totalGames"]) is not int or value["totalGames"] != count):
        raise OperationsError("schedule-date-incomplete", "MLB response total conflicts with records")
    if not count and (type(value.get("totalGames")) is not int or value["totalGames"] != 0):
        raise OperationsError("schedule-date-incomplete", "Empty MLB date requires explicit zero totalGames")
    # Reject malformed declarations before recording a reusable calendar receipt.
    # Reciprocal completeness is checked only against the related-page union.
    from forecast_standalone_activation import _mlb_lineage_value
    for record in records:
        for game in record["games"]:
            for field in ("resumeDate","resumeGameDate","resumedFrom","resumedFromDate",
                          "rescheduleDate","rescheduleGameDate","rescheduledFrom","rescheduledFromDate"):
                if game.get(field) is not None:_mlb_lineage_value(game[field],field)
    merge_mlb_schedule_responses((raw,))


def schedule_contracts(*, union: bytes, started: datetime, prior_state, union_rule: str):
    if json.loads(union) == {"dates": []}:
        return ()
    require_complete_lineage(union)
    return refresh_supporting_from_raw(
        archive=None, mlb_raw=union, kalshi_raw=b'{"cursor":"","markets":[]}',
        collected_at=started, prior_state=prior_state, derive_only=True,
        acquisition_command=COMMAND, union_rule=union_rule,
    )


def require_complete_lineage(union):
    payload = json.loads(union)
    fields = ("resumeDate", "resumeGameDate", "resumedFrom", "resumedFromDate",
              "rescheduleDate", "rescheduleGameDate", "rescheduledFrom", "rescheduledFromDate")
    declared = {game["gamePk"] for day in payload["dates"] for game in day["games"]
                if any(game.get(field) is not None for field in fields)}
    verified = {item["gamePk"] for item in payload.get("_popsEdgeMlbLineages", ())}
    if not declared <= verified:
        raise OperationsError("schedule-lineage-incomplete", "Related MLB observations are required; calendar receipt is not scientific completeness")


def validate_supporting_addition(state, contracts, at):
    """Validate the proposed supporting graph before publishing any authority."""
    from forecast_standalone_operations import PR17_GRAPH_BUCKETS
    from forecast_standalone_research import validate_standalone_research_graph
    graph = {name:list(values) for name,values in state.graph}
    for contract in contracts:
        bucket = PR17_GRAPH_BUCKETS[type(contract).__name__]
        if bucket == "outcome_histories":
            prior = next((x for x in graph[bucket] if x.canonical_event_id == contract.canonical_event_id), None)
            if prior is not None:
                if contract.observations[:len(prior.observations)] != prior.observations:
                    raise OperationsError("outcome-history-conflict", "Supporting history is not append-only")
                graph[bucket].remove(prior)
        if contract not in graph[bucket]:graph[bucket].append(contract)
    validate_standalone_research_graph(**graph, analysis_boundary=at)


def _dt(value):
    return datetime.fromisoformat(value["datetime_utc"] if isinstance(value,dict) else value)


def verify_schedule_bundle(archive, value, raw_pages):
    """Receipts certify acquisition only; a completion binds exact receipt pages."""
    pages = value["pages"]
    receipt = value["family"] == RECEIPT_COMMAND
    if value["provider"] != "mlb-stats-api" or not 1 <= len(pages) <= MAX_DATES:
        raise OperationsError("schedule-date-conflict", "Invalid bounded MLB calendar envelope")
    for page,raw in zip(pages,raw_pages):
        day = date.fromisoformat(page["request_identity"])
        if day < APPROVED_EASTERN_DATE or day.year != 2026 or day >= _dt(page["started_at"]).astimezone(ZoneInfo(APPROVED_TIMEZONE)).date():
            raise OperationsError("schedule-date-bound-invalid", "Schedule receipt is outside completed prospective dates")
        validate_date_page(raw, day)
    if receipt:
        if len(pages) != 1 or value.get("dependencies") != [] or value.get("contracts") != []:
            raise OperationsError("schedule-date-conflict", "Calendar receipt cannot grant scientific authority")
        return
    if _dt(value["schedule_reconciled_at"]) < _dt(value["acquisition_completed_at"]):
        raise OperationsError("trusted-clock-reversed", "Schedule reconciliation precedes receipt completion")
    dependencies = value.get("dependencies")
    if not isinstance(dependencies,list) or len(dependencies) != len(pages) or len(set(dependencies)) != len(pages):
        raise OperationsError("schedule-date-conflict", "Schedule completion requires exact date receipts")
    receipts = {}
    for entry in authoritative_entries(archive):
        if entry.get("command") != RECEIPT_COMMAND:continue
        candidate = json.loads(archive.read_verified("normalized",entry["normalized_object_id"]))
        if candidate.get("acquisition_id") in dependencies:
            if candidate["acquisition_id"] in receipts:raise OperationsError("schedule-date-conflict", "Duplicate calendar receipt")
            verify_acquisition_bundle(archive,candidate)
            receipts[candidate["acquisition_id"]] = candidate["pages"][0]
    fields = ("request_identity","endpoint","raw_sha256","started_at","completed_at")
    expected = sorted(tuple(str(page[key]) for key in fields) for page in receipts.values())
    if len(receipts) != len(pages) or expected != sorted(tuple(str(page[key]) for key in fields) for page in pages):
        raise OperationsError("schedule-date-conflict", "Schedule completion substitutes or omits receipt material")
    require_complete_lineage(merge_mlb_schedule_responses(raw_pages))


def _receipts(archive):
    result = {}
    for entry in authoritative_entries(archive):
        if entry.get("command") != RECEIPT_COMMAND:continue
        value = json.loads(archive.read_verified("normalized",entry["normalized_object_id"]))
        verify_acquisition_bundle(archive,value)
        page = value["pages"][0];day = date.fromisoformat(page["request_identity"])
        if day in result:raise OperationsError("schedule-date-conflict", "Multiple preserved receipts for one calendar date")
        result[day] = (value["acquisition_id"], (page["request_identity"],page["endpoint"],
            archive.read_verified("raw",page["raw_sha256"]),_dt(page["started_at"]),_dt(page["completed_at"])))
    return result


def _related_component(day, receipts):
    from forecast_standalone_activation import _mlb_lineage_value
    fields = ("resumeDate","resumeGameDate","resumedFrom","resumedFromDate",
              "rescheduleDate","rescheduleGameDate","rescheduledFrom","rescheduledFromDate")
    links = {}
    # Incoming declarations matter too: a counterpart lacking reciprocal fields
    # must not be mistaken for an unrelated ordinary-game page.
    for current in receipts:
        for item in json.loads(receipts[current][1][2])["dates"]:
            for game in item["games"]:
                for field in fields:
                    if game.get(field) is None:continue
                    target,instant = _mlb_lineage_value(game[field],field)
                    if instant is not None:target = instant.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date()
                    links.setdefault(current,set()).add(target)
                    links.setdefault(target,set()).add(current)
    required = {day};pending = [day]
    while pending:
        current = pending.pop()
        for target in links.get(current,()):
            if target not in required:required.add(target);pending.append(target)
        if len(required) > MAX_DATES:
            raise OperationsError("schedule-date-bound-invalid", "Related lineage exceeds 31 preserved calendar dates")
    return required


def reconciliation_dates(*, archive: NamespaceArchive, started: datetime,
                         start_date: date, end_date: date) -> tuple[date, ...]:
    if started.tzinfo is None or started.utcoffset() is None:
        raise OperationsError("trusted-clock-invalid", "Reconciliation requires an aware clock")
    today = started.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date()
    if (start_date < APPROVED_EASTERN_DATE or end_date < start_date
            or (end_date-start_date).days >= MAX_DATES or end_date >= today
            or end_date.year != APPROVED_EASTERN_DATE.year):
        raise OperationsError("schedule-date-bound-invalid", "Require 1–31 completed Eastern dates in the prospective 2026 window")
    resolve_activated_authority(archive, started)  # complete graph/integrity replay
    completed = set()
    for entry in authoritative_entries(archive):
        if not entry.get("normalized_object_id"):
            continue
        value = json.loads(archive.read_verified("normalized", entry["normalized_object_id"]))
        if (value.get("record_kind") != "pr17c1-acquisition-bundle"
                or value.get("provider") != "mlb-stats-api"
                or value.get("family") not in {COMMAND, "refresh-supporting"}):
            continue
        if datetime.fromisoformat(entry["acquired_at"]["datetime_utc"]) > started:
            continue
        union,_ = verify_acquisition_bundle(archive, value, include_union=True)
        try:require_complete_lineage(union)
        except OperationsError as exc:
            if exc.code != "schedule-lineage-incomplete":raise
            # An older supporting read can be valid archived material without
            # certifying the required reciprocal calendar lineage.
            continue
        for page in value["pages"]:
            day = date.fromisoformat(page["request_identity"])
            page_start = datetime.fromisoformat(page["started_at"]["datetime_utc"])
            if start_date <= day <= end_date and page_start.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date() > day:
                # Legacy empty/malformed pages cannot certify a completed calendar date.
                raw = archive.read_verified("raw", page["raw_sha256"])
                try:
                    validate_date_page(raw, day)
                except OperationsError:
                    # Preserve legacy authority, but do not certify this date.
                    continue
                completed.add(day)
    return tuple(start_date+timedelta(days=i) for i in range((end_date-start_date).days+1)
                 if start_date+timedelta(days=i) not in completed)


def reconcile_schedule(*, archive: NamespaceArchive, started: datetime,
                       start_date: date, end_date: date, public_get: Callable,
                       clock: Callable) -> dict:
    from forecast_standalone_activation import ACQUISITION_UNION_RULE_VERSION
    missing = reconciliation_dates(archive=archive, started=started, start_date=start_date, end_date=end_date)
    calls = 0
    manifests = []
    contracts_count = 0
    receipts = _receipts(archive)
    prior_receipt_dates = set(receipts)
    resolved = set()
    requested = []
    # Calendar receipts survive independently; only closed lineage admits science.
    try:
        for day in missing:
            if day in resolved:continue
            began = clock()
            if began < started:
                raise OperationsError("trusted-clock-reversed", "Schedule request precedes command start")
            path, endpoint = canonical_mlb_schedule_request(day)
            raw = None
            phase = "request"
            try:
                if day not in receipts:
                    calls += 1;requested.append(day)
                    raw = public_get("https://statsapi.mlb.com", path)
                    phase = "validation"
                    completed = clock()
                    validate_date_page(raw, day)
                    page = (day.isoformat(),endpoint,raw,began,completed)
                    with archive.mutation_lock():
                        phase = "publication"
                        publish_verified_acquisition(archive=archive,provider="mlb-stats-api",
                            union_raw=merge_mlb_schedule_responses((raw,)),pages=(page,),contracts=(),
                            collected_at=began,protocol_id=None,command=RECEIPT_COMMAND)
                    receipts = _receipts(archive)
                phase = "validation"
                raw = receipts[day][1][2]
                component = _related_component(day,receipts)
                if not component <= receipts.keys():continue
                selected = sorted((receipts[item] for item in component),key=lambda item:(item[1][3],item[1][0]))
                pages = tuple(item[1] for item in selected)
                union = merge_mlb_schedule_responses(tuple(page[2] for page in pages))
                reconciled_at = clock()
                if reconciled_at < started or reconciled_at < pages[-1][4]:
                    raise OperationsError("trusted-clock-reversed", "Schedule completion precedes receipt acquisition")
                with archive.mutation_lock():
                    prior = replay_pr17_archive(archive, analysis_boundary=reconciled_at)
                    contracts = schedule_contracts(union=union, started=reconciled_at, prior_state=prior,
                                                   union_rule=ACQUISITION_UNION_RULE_VERSION)
                    validate_supporting_addition(prior,contracts,reconciled_at)
                    phase = "publication"
                    result = publish_verified_acquisition(
                        archive=archive, provider="mlb-stats-api", union_raw=union, pages=pages,
                        contracts=contracts, collected_at=pages[0][3], protocol_id=None, command=COMMAND,
                        dependencies=tuple(item[0] for item in selected),schedule_reconciled_at=reconciled_at)
            except Exception as exc:
                if phase == "publication":raise  # retain existing partial-publication handling
                failed_at = clock()
                disposition = (Disposition.TIMEOUT if phase == "request" and isinstance(exc, TimeoutError)
                    else Disposition.CONNECTION_FAILURE if phase == "request" and isinstance(exc, OSError)
                    else Disposition.PROVIDER_ERROR if isinstance(exc, OperationsError) and exc.code == "transport-status"
                    else Disposition.VALIDATION_FAILURE)
                values = _entry_values(archive=archive, command=COMMAND+"-failure",
                    request_id=request_identity({"date":day.isoformat(),"request_started_at":began}),
                    invoked_at=failed_at, endpoint=endpoint, disposition=disposition,
                    protocol_id=None, design=DesignAuthority.SUPPORTING,
                    diagnostics=("requested-date:"+day.isoformat(),"non-authoritative schedule acquisition failure"))
                values["provider_id"] = "mlb-stats-api"
                archive.record_failure(entry_values=values, raw_body=raw)
                if phase == "request" and isinstance(exc, TimeoutError):
                    raise OperationsError("transport-timeout", "MLB schedule request timed out") from exc
                if phase == "request" and isinstance(exc, OSError):
                    raise OperationsError("transport-connection-failure", "MLB schedule request failed") from exc
                raise
            manifests.append(result["manifest_entry_id"])
            contracts_count += len(contracts)
            resolved.update(component)
        unresolved = set(missing)-resolved
        if unresolved:
            needed = set().union(*(_related_component(day,receipts) for day in unresolved))-receipts.keys()
            detail = ("Preserved calendar receipts await related dates: " + ",".join(day.isoformat() for day in sorted(needed))
                if needed else "Preserved calendar receipts lack verified reciprocal lineage") + "; no requests outside explicit bounds were made"
            values = _entry_values(archive=archive,command=COMMAND+"-failure",
                request_id=request_identity({"pending_dates":tuple(day.isoformat() for day in sorted(unresolved)),"started":started}),
                invoked_at=clock(),endpoint="derived://mlb-stats-api/pending-lineage",disposition=Disposition.VALIDATION_FAILURE,
                protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=(detail,))
            values["provider_id"]="mlb-stats-api"
            archive.record_failure(entry_values=values,raw_body=None)
            raise OperationsError("schedule-lineage-incomplete",detail)
    except Exception as exc:
        if isinstance(exc, OperationsError):
            failure = exc
        else:
            failure = OperationsError("internal-error", "Schedule reconciliation failed; completed dates remain preserved")
        failure.provider_calls = calls
        if failure is exc:raise
        raise failure from exc
    return {"disposition": "success" if missing else "unchanged", "provider_calls": calls,
            "requested_dates": tuple(day.isoformat() for day in requested),
            "reused_dates": tuple(day.isoformat() for day in sorted(resolved & prior_receipt_dates)),
            "scientifically_completed_dates": tuple(day.isoformat() for day in sorted(resolved)),
            "completed_manifest_ids": tuple(manifests), "contracts": contracts_count,
            "limitations": (LIMITATION,)}
