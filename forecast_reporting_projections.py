"""Versioned descriptive projections of independently verified reporting Analysis.

No new Evidence, scoring engine, population selection or publication authority.
"""
from dataclasses import fields
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

import forecast_reporting_analysis as analysis
import forecast_standalone_research as legacy
from forecast_reporting_source import verify_reporting_source
from forecast_standalone_operations import canonical_bytes, sha256_bytes

VERSION = 'mlb-reporting-projections-1'
REFERENCE = 'constant-home-probability-0.5:1'


def _number(value):
    return None if value is None else str(value)


def _identified(material):
    return {**material, 'object_id': VERSION + ':' + sha256_bytes(canonical_bytes(material))}


def _captures(state, report):
    """Use original validation stages, independently of successful Analysis rows."""
    spec = report.context.computation
    activation, protocol = analysis._authority(state, spec.protocol_id)
    eligible = set(report.coverages[0].eligible_denominator_ids)
    contexts = {x.research_capture_opportunity_id: x for x in state.bucket('eligibility_contexts')}
    results = {x.research_capture_opportunity_id: x for x in state.bucket('eligibility_results')}
    histories = {x.canonical_event_id: x for x in state.bucket('outcome_histories')}
    manifests = tuple(x for x in state.bucket('manifests') if x.protocol_id == spec.protocol_id)
    terminals = legacy.validate_manifest_lineage(manifests, spec.evidence_cutoff_at) if manifests else ()
    snapshots = tuple(x for x in state.bucket('snapshots') if x.protocol_id == spec.protocol_id)
    selected = legacy.select_authoritative_prospective_snapshots(snapshots, spec.evidence_cutoff_at)
    captured = {}; failures = {}; offered = {}; unknown = []
    for opportunity in state.bucket('opportunities'):
        oid = opportunity.research_capture_opportunity_id
        if oid not in eligible:
            continue
        context = contexts[oid]; history = histories[context.canonical_event_id]
        schedule = next(x for x in history.observations if x.observation_id == opportunity.schedule_observation_id)
        inputs = dict(protocol=protocol, activation=activation, opportunity=opportunity,
            eligibility_context=context, eligibility_result=results[oid], schedule_history=history,
            analysis_boundary=spec.evidence_cutoff_at)
        if spec.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE:
            # The frozen graph's original mapping authority proves positive membership.
            # Absence from that graph does not prove the provider offered no market.
            proposition = f'winner:{schedule.canonical_event_id}:{schedule.home_participant_id}'
            matching = tuple(x for x in state.bucket('market_series')
                             if x.provider == legacy.PROVIDER_ID and x.proposition_id == proposition)
            if len(matching) > 1:
                legacy._fail('reporting projection: ambiguous historical market mapping')
            if matching:
                series = matching[0]
                if (series.provenance.canonical_event_id != schedule.canonical_event_id or
                    series.yes_semantic.participant_id != schedule.home_participant_id or
                    series.no_semantic.participant_id != schedule.away_participant_id or
                    not series.yes_semantic.affirms_proposition):
                    legacy._fail('reporting projection: conflicting historical home-market mapping')
                offered[oid] = series.series_id
            else:
                unknown.append(oid)
        try:
            if spec.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE:
                owned = tuple(x for x in terminals if x.opportunity_id == oid)
                if len(owned) != 1:
                    legacy._fail('capture requires one complete terminal manifest')
                manifest = owned[0]
                _, _, candle = legacy._validated_historical_capture(**inputs, manifest=manifest,
                    manifests=manifests, candles=tuple(x for x in state.bucket('candles')
                        if x.manifest_id == manifest.historical_candle_query_manifest_id),
                    home_participant_id=schedule.home_participant_id, complement_outcome_id=schedule.away_participant_id)
                captured[oid] = [manifest.historical_candle_query_manifest_id, candle.historical_market_candle_observation_id]
            else:
                owned = tuple(x for x in selected if x.opportunity_id == oid)
                if len(owned) != 1:
                    legacy._fail('capture requires one terminal Snapshot')
                snapshot = owned[0]
                observations = tuple(x for x in state.bucket('market_observations') if x.observation_id == snapshot.market_observation_id)
                if len(observations) != 1:
                    legacy._fail('capture has no authoritative MarketObservation')
                observation = observations[0]
                series = tuple(x for x in state.bucket('market_series') if x.series_id == observation.series_id)
                if len(series) != 1:
                    legacy._fail('capture has no unique market mapping')
                legacy._validated_prospective_capture(**inputs, snapshot=snapshot, snapshots=snapshots,
                    attempts=tuple(x for x in state.bucket('attempts') if x.opportunity_id == oid),
                    observation=observation, market_observations=state.bucket('market_observations'), series=series[0])
                captured[oid] = [snapshot.prospective_standalone_snapshot_id, observation.observation_id]
        except legacy.ContractError as exc:
            failures[oid] = str(exc)
    return captured, failures, offered, unknown


def _project(state, report):
    """Internal: only a graph/report admitted by the public verifiers may enter."""
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        captured, failures, offered, unknown = _captures(state, report)
        scopes = []
        for coverage, performance in zip(report.coverages, report.performances, strict=True):
            eligible = set(coverage.eligible_denominator_ids)
            scored = set(coverage.measured_opportunity_ids)
            valid = {x.opportunity_id for x in report.derivations} & eligible
            cap = set(captured) & eligible
            if not scored <= valid <= cap <= eligible:
                legacy._fail('reporting projection population hierarchy conflicts')
            values = tuple(x for x in report.measurements if x.object_id in performance.measurement_ids)
            reference = _identified(dict(rule=REFERENCE, adopted_on='2026-09-12',
                status='descriptive addition after study commencement', performance_id=performance.object_id,
                measurement_ids=list(performance.measurement_ids), sample_size=performance.sample_size,
                mean_brier_score='0.25' if values else None,
                mean_log_loss=str(Decimal(2).ln()) if values else None))
            bins = []
            bounds = performance.calibration.boundaries
            for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
                bucket = tuple(x for x in values if lo <= x.calculation.calibration_probability and
                    (x.calculation.calibration_probability <= hi if i == len(bounds)-2 else x.calculation.calibration_probability < hi))
                n = len(bucket)
                mean = sum((x.calculation.calibration_probability for x in bucket), Decimal(0))/n if n else None
                frequency = Decimal(sum(x.calculation.realized_outcome_id == x.calculation.canonical_proposition_outcome_id for x in bucket))/n if n else None
                bins.append(dict(lower=str(lo), upper=str(hi), upper_inclusive=i == len(bounds)-2,
                    measurement_ids=[x.object_id for x in bucket], count=n,
                    mean_home_probability=_number(mean), home_win_frequency=_number(frequency)))
            if tuple(x['count'] for x in bins) != performance.calibration.bin_counts:
                legacy._fail('projection calibration membership conflicts')
            calibration = _identified(dict(rule=f'{performance.calibration.rule_id}:{performance.calibration.rule_version}',
                performance_id=performance.object_id, measurement_ids=list(performance.measurement_ids),
                endpoint_semantics=performance.calibration.endpoint_semantics, bins=bins,
                wace=_number(performance.calibration.wace)))
            historical = None
            if report.context.computation.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE:
                off = set(offered) & eligible; unverified = set(unknown) & eligible
                historical = dict(offered_ids=sorted(off), mapping_references={x:offered[x] for x in sorted(off)},
                    unknown_membership_ids=sorted(unverified), scored_offered_ids=sorted(scored & off),
                    offered_over_eligible=_number(Decimal(len(off))/len(eligible)) if eligible and not unverified else None,
                    scored_over_offered=_number(Decimal(len(scored & off))/len(off)) if off and not unverified else None,
                    limitation='Missing mapping is unknown membership, not evidence of no market. Rates require complete verified membership; numerator is scored opportunities, not captures.')
            scopes.append(_identified(dict(coverage_id=coverage.object_id, performance_id=performance.object_id,
                scope_id=coverage.scope.object_id, captured_ids=sorted(cap), valid_probability_ids=sorted(valid),
                scored_ids=sorted(scored), eligible_ids=sorted(eligible), unscored_ids=sorted(eligible-scored),
                capture_references={x:captured[x] for x in sorted(cap)},
                capture_validation_failures={x:failures[x] for x in sorted(eligible & set(failures))},
                derivation_ids=sorted(x.object_id for x in report.derivations if x.opportunity_id in valid),
                reconciliation={f.name:list(getattr(coverage.reconciliation,f.name)) for f in fields(coverage.reconciliation)},
                scored_over_eligible=_number(coverage.coverage_rate), historical_markets=historical,
                reference=reference, calibration=calibration)))
        return _identified(dict(version=VERSION, report_id=report.object_id,
            source_boundary_id=report.context.computation.source_boundary_id, scopes=scopes))


def create_reporting_projections(*, archive, source, expected_source_boundary_id, report, clock):
    analysis.verify_standalone_report_analysis(archive=archive, source=source,
        expected_source_boundary_id=expected_source_boundary_id, report=report, clock=clock)
    state, _ = verify_reporting_source(archive=archive, boundary=source,
        expected_boundary_id=expected_source_boundary_id, clock=clock)
    return _project(state, report)


def verify_reporting_projections(*, projections, **inputs):
    expected = create_reporting_projections(**inputs)
    if canonical_bytes(projections) != canonical_bytes(expected):
        legacy._fail('reporting projections do not reconstruct exactly')
