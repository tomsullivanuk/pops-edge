"""Canonical Protocols with entirely synthetic, offline reporting Evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import forecast_standalone_research as r
from forecast_standalone_activation import canonical_prospective_authority, canonical_retrospective_authority
from forecast_standalone_operations import archive_pr17_authority
from inspect_forecast_standalone_research import build_synthetic_bundle, _classification
from outcome_contracts import OutcomeHistory


def at(value):
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def event_sources(*, design='retrospective', name='game', start='2026-08-20T20:00:00-04:00',
                  acquired='2026-09-10T12:00:00Z', final=True, capture=True, missed=False,
                  probability=Decimal('0.5'), final_at=None):
    g = build_synthetic_bundle()
    activation, protocol = (canonical_retrospective_authority() if design == 'retrospective'
                            else canonical_prospective_authority())
    start = at(start); acquired = at(acquired); target = start-timedelta(hours=6)
    pid = protocol.standalone_probability_source_protocol_id
    event = 'synthetic-event:' + name; native = 'synthetic-native:' + name
    home = 'synthetic-home:' + name; away = 'synthetic-away:' + name
    proposition = f'winner:{event}:{home}'
    # Historical acquisition retains its later retrieval time; prospective schedule
    # knowledge predates capture. Nothing is a provider reconstruction of a missed quote.
    known = acquired if design == 'retrospective' else min(acquired, target-timedelta(days=1))
    template = g['retro_history'].observations[0]
    schedule = replace(template, observation_id='synthetic-schedule:' + name,
        canonical_event_id=event, provider_event_id=native, scheduled_start=start,
        home_participant_id=home, away_participant_id=away, collected_at=known)
    observations = [schedule]
    if final:
        ended = at(final_at) if final_at else max(acquired+timedelta(seconds=1), start+timedelta(hours=4))
        observations.append(replace(g['retro_history'].observations[-1],
            observation_id='synthetic-final:' + name, canonical_event_id=event,
            provider_event_id=native, scheduled_start=start, home_participant_id=home,
            away_participant_id=away, winning_participant_id=home, losing_participant_id=away, collected_at=ended))
    history = OutcomeHistory(event, 'mlb-stats-api', tuple(observations))
    opportunity = r.ResearchCaptureOpportunity.create(pid, schedule.observation_id, 'winner')
    provenance = replace(g['provenance'], generated_at=known)
    classification = _classification(schedule, provenance)
    context, result = r.create_standalone_eligibility_authority(protocol=protocol,
        opportunity=opportunity, outcome_history=history, classification=classification,
        classifications=(classification,), analysis_boundary=known, provenance=provenance)
    sources = [activation, protocol, opportunity, classification, context, result, history]
    if design == 'retrospective' and capture:
        seed = {key:getattr(g['candle'], key) for key in g['candle'].__dataclass_fields__
                if key not in {'historical_market_candle_observation_id', 'input_digest'}}
        seed.update(protocol_id=pid, manifest_id='pending', provider_market_id=native,
            canonical_event_id=event, proposition_id=proposition, home_participant_id=home,
            candle_end_at=target, acquired_at=acquired, close_yes_bid=probability,
            close_yes_ask=probability, provenance=provenance)
        provisional = r.HistoricalMarketCandleObservation.create(**seed)
        values = {key:getattr(g['manifest'], key) for key in g['manifest'].__dataclass_fields__
                  if key not in {'historical_candle_query_manifest_id', 'input_digest'}}
        values.update(protocol_id=pid, opportunity_id=opportunity.research_capture_opportunity_id,
            canonical_event_id=event, proposition_id=proposition, provider_market_id=native,
            requested_start_at=target-timedelta(minutes=5), requested_end_at=target,
            retrieval_started_at=acquired, retrieval_completed_at=acquired, effective_at=acquired,
            pages=(replace(g['manifest'].pages[0], retrieved_at=acquired,
                           returned_candle_evidence_ids=(provisional.historical_market_candle_observation_id,)),),
            returned_candle_evidence_ids=(provisional.historical_market_candle_observation_id,), provenance=provenance)
        manifest = r.HistoricalCandleQueryManifest.create(**values)
        candle = r.HistoricalMarketCandleObservation.create(**{**seed, 'manifest_id':manifest.historical_candle_query_manifest_id})
        sources.extend((manifest, candle))
    elif design == 'prospective' and capture:
        captured = target+timedelta(minutes=1)
        oldseries = g['series']; oldobs = g['observation']
        market_provenance = replace(oldseries.provenance, source_record_id=native,
                                    canonical_event_id=event, collected_at=known)
        series = replace(oldseries, series_id='market-series:kalshi:' + native,
            provider_market_id=native, proposition_id=proposition,
            yes_semantic=replace(oldseries.yes_semantic, proposition_id=proposition, participant_id=home),
            no_semantic=replace(oldseries.no_semantic, proposition_id=proposition, participant_id=away),
            provenance=market_provenance)
        observation = replace(oldobs, observation_id='synthetic-quote:' + name,
            series_id=series.series_id, provider_market_id=native, canonical_event_id=event,
            proposition_id=proposition, collected_at=captured,
            order_book=tuple(replace(x, collected_at=captured) for x in oldobs.order_book),
            component_evidence=tuple(replace(x, provider_market_id=native, collected_at=captured)
                                     for x in oldobs.component_evidence),
            provenance=replace(market_provenance, collected_at=captured))
        attempts = []
        success_id = None
        for index in range(5):
            result_value = (r.Missed() if missed or index == 0 else
                r.CapturedValid('synthetic-raw:' + name, 'e'*64, observation.observation_id)
                if index == 1 else r.SkippedAfterSuccess(success_id))
            attempt = r.ProspectiveCaptureAttempt.create(protocol_id=pid,
                opportunity_id=opportunity.research_capture_opportunity_id,
                schedule_observation_id=schedule.observation_id, canonical_event_id=event,
                proposition_id=proposition, home_participant_id=home, provider_market_id=native,
                target_at=target, slot=index, invocation_at=target+timedelta(minutes=index),
                provider_call_occurred=isinstance(result_value, r.CapturedValid), result=result_value,
                effective_at=target+timedelta(minutes=index), diagnostics=(), provenance=provenance)
            attempts.append(attempt)
            if index == 1:
                success_id = attempt.prospective_capture_attempt_id
        snapshot = r.reconcile_prospective_snapshot(protocol=protocol, activation=activation,
            opportunity=opportunity, eligibility_context=context, eligibility_result=result,
            schedule_history=history, analysis_boundary=target+timedelta(minutes=5),
            attempts=attempts, window_closed_at=target+timedelta(minutes=5), provenance=provenance)
        sources.extend((*attempts, snapshot))
        if not missed:
            sources.extend((series, observation))
    return tuple(sources), protocol, history


def archive_events(archive, events, recorded_at):
    # Shared activation/Protocol authority is archived once, preserving exact bytes.
    unique = {x.to_json():x for event in events for x in event}
    archive_pr17_authority(archive, unique.values(), recorded_at=recorded_at)
