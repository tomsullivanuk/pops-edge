"""Typed, offline report-local Analysis of a verified frozen MLB source graph.

No archive writes, operational report delivery, baseline or renderer. Legacy
calculation records are reconstructed as internal arithmetic witnesses, never
accepted as post-cutoff source authority or dispatched as successor references.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any, Callable
from zoneinfo import ZoneInfo

from event_contracts import SerializableContract, _register
from forecast_research_contracts import ResearchContractProvenance
import forecast_standalone_research as legacy
from forecast_reporting_source import (
    FrozenReportingSource, verify_reporting_source,
)
from forecast_standalone_operations import NamespaceArchive, ScientificArchiveState

VERSION = "mlb-reporting-analysis-1"
SEED_VERSION = "mlb-reporting-bootstrap-seed-1"
BASELINE_REFERENCE = "constant-home-probability-0.5:1:adopted-2026-09-12:downstream"


def _fail(detail):
    legacy._fail("reporting Analysis: " + detail)


def _id(cls, material):
    return cls.__name__ + ":" + legacy._digest((VERSION, cls.__name__, material))


def _make(cls, **material):
    return cls(**material, object_id=_id(cls, material))


class _Contract(SerializableContract):
    def __post_init__(self):
        material = {f.name: getattr(self, f.name) for f in fields(self) if f.name != 'object_id'}
        if getattr(self, 'version', VERSION) != VERSION or self.object_id != _id(type(self), material):
            _fail('unknown version or analytical identity conflict')


@dataclass(frozen=True, slots=True)
class ReportEventScope(_Contract):
    name: str
    start: datetime | None
    end: datetime | None
    endpoint_semantics: str
    object_id: str


@dataclass(frozen=True, slots=True)
class StandaloneComputationSpecification(_Contract):
    version: str
    source_boundary_id: str
    protocol_id: str
    design_tag: legacy.StandaloneDesignTag
    source_id: str
    source_role: str
    domain: tuple[tuple[str, str], ...]
    evidence_cutoff_at: datetime
    cumulative_scope: ReportEventScope
    bounded_scopes: tuple[ReportEventScope, ...]
    computation_started_at: datetime
    rule_references: tuple[str, ...]
    software_revision: str
    object_id: str


@dataclass(frozen=True, slots=True)
class StandaloneReportContext(_Contract):
    version: str
    computation: StandaloneComputationSpecification
    computation_completed_at: datetime
    report_generated_at: datetime
    report_status: str
    closure_reference: str | None
    object_id: str

    def __post_init__(self):
        _Contract.__post_init__(self)
        if type(self.computation) is not StandaloneComputationSpecification:
            _fail('foreign computation specification')
        for at in (self.computation.computation_started_at,
                   self.computation_completed_at, self.report_generated_at):
            legacy._require_aware(at, 'actual reporting time')
        if not (self.computation.evidence_cutoff_at <= self.computation.computation_started_at
                <= self.computation_completed_at <= self.report_generated_at):
            _fail('reporting chronology is reversed')
        # Closure and historical correction publications are downstream authority.
        if self.report_status not in {'in-progress', 'interim'} or self.closure_reference is not None:
            _fail('this offline slice cannot infer final closure or correction authority')


@dataclass(frozen=True, slots=True)
class ReportLocalDerivation(_Contract):
    computation_id: str
    opportunity_id: str
    kind: legacy.DerivationKindV3
    calculation: legacy.HistoricalCandleProbabilityDerivation | legacy.MarketProbabilityDerivation
    object_id: str

    def __post_init__(self):
        _Contract.__post_init__(self)
        expected = (legacy.HistoricalCandleProbabilityDerivation
                    if self.kind is legacy.DerivationKindV3.HISTORICAL_CANDLE
                    else legacy.MarketProbabilityDerivation)
        if type(self.calculation) is not expected:
            _fail('derivation calculation has incompatible type')


@dataclass(frozen=True, slots=True)
class ReportLocalMeasurement(_Contract):
    computation_id: str
    derivation_id: str
    calculation: legacy.ProbabilitySourceMeasurementV3
    object_id: str

    def __post_init__(self):
        _Contract.__post_init__(self)
        if type(self.calculation) is not legacy.ProbabilitySourceMeasurementV3:
            _fail('measurement calculation has incompatible type')


@dataclass(frozen=True, slots=True)
class ReportCoverage(_Contract):
    computation_id: str
    scope: ReportEventScope
    coverage_universe_ids: tuple[str, ...]
    eligible_denominator_ids: tuple[str, ...]
    measured_opportunity_ids: tuple[str, ...]
    measurement_ids: tuple[str, ...]
    reconciliation: legacy.CoverageReconciliation
    coverage_rate: Decimal | None
    verified_calendar_dates: tuple[date, ...]
    unknown_calendar_dates: tuple[date, ...]
    limitations: tuple[str, ...]
    object_id: str


@dataclass(frozen=True, slots=True)
class ReportUncertainty(_Contract):
    seed_version: str
    seed_digest: str
    confidence_level: Decimal
    resample_count: int
    point_estimate: Decimal | None
    lower: Decimal | None
    upper: Decimal | None
    sample_size: int
    limitations: tuple[str, ...]
    object_id: str


@dataclass(frozen=True, slots=True)
class ReportPerformance(_Contract):
    computation_id: str
    scope_id: str
    coverage_id: str
    measurement_ids: tuple[str, ...]
    sample_size: int
    mean_brier_score: Decimal | None
    mean_log_loss: Decimal | None
    calibration: legacy.CalibrationV3
    uncertainty: ReportUncertainty
    object_id: str


@dataclass(frozen=True, slots=True)
class StandaloneAnalyticalReport(_Contract):
    version: str
    context: StandaloneReportContext
    derivations: tuple[ReportLocalDerivation, ...]
    measurements: tuple[ReportLocalMeasurement, ...]
    coverages: tuple[ReportCoverage, ...]
    performances: tuple[ReportPerformance, ...]
    cumulative_performance_id: str
    bounded_performance_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    object_id: str


@dataclass(frozen=True, slots=True)
class ReportVerificationReceipt:
    version: str
    report_id: str
    source_boundary_id: str
    verified_at: datetime


def _authority(state, protocol_id):
    protocols = tuple(x for x in state.bucket('protocols')
                      if x.standalone_probability_source_protocol_id == protocol_id)
    if len(protocols) != 1:
        _fail('exact Protocol authority required')
    protocol = protocols[0]
    from forecast_standalone_activation import canonical_retrospective_authority, canonical_prospective_authority
    canonical = (canonical_retrospective_authority() if protocol.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE
                 else canonical_prospective_authority())
    if protocol != canonical[1]:
        _fail('reporting supports the two existing canonical MLB studies only')
    activations = tuple(x for x in state.bucket('activation_boundaries')
                       if x.standalone_research_activation_boundary_id == protocol.activation_boundary_id)
    if len(activations) != 1:
        _fail('exact activation authority required')
    return activations[0], protocol


def _specification(source, state, protocol_id, started, software_revision):
    activation, protocol = _authority(state, protocol_id)
    legacy._require_aware(started, 'computation start')
    if started < source.frozen_at:
        _fail('new computation predates source freeze')
    if not isinstance(software_revision, str) or len(software_revision) != 40 or any(
            ch not in '0123456789abcdef' for ch in software_revision):
        _fail('exact software revision required')
    cutoff = source.evidence_cutoff_at
    windows = legacy._report_windows(protocol.report_rule)
    retrospective = protocol.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE
    bounded = []
    for duration in windows:
        end = activation.activation_at if retrospective else cutoff
        start = end - duration
        if retrospective:
            declared = dict(protocol.scope_rule.parameters).get('window_start')
            if declared is not None and datetime.fromisoformat(declared) != start:
                _fail('Protocol historical origin and required duration conflict')
        bounded.append(_make(ReportEventScope, name='time-bounded', start=start, end=end,
                             endpoint_semantics='open-left-closed-right'))
    cumulative = _make(ReportEventScope, name='cumulative',
        start=min(x.start for x in bounded) if retrospective else activation.activation_at,
        end=activation.activation_at if retrospective else None,
        endpoint_semantics='protocol-population-from-governed-origin')
    rules = [f'{getattr(protocol, name).rule_id}:{getattr(protocol, name).rule_version}'
             for name in ('scope_rule', 'representation_rule', 'scoring_rule',
                          'calibration_rule', 'uncertainty_rule', 'report_rule')]
    rules += [protocol.source.probability_representation_rule.rule_specification_id,
              protocol.source.transformation_rule.rule_specification_id,
              protocol.source.availability_rule.rule_specification_id, SEED_VERSION,
              VERSION, BASELINE_REFERENCE]
    return _make(StandaloneComputationSpecification, version=VERSION,
        source_boundary_id=source.boundary_id, protocol_id=protocol_id,
        design_tag=protocol.design_tag, source_id=protocol.source.probability_source_reference_id,
        source_role='standalone-probability-source',
        domain=tuple(sorted((key, dict(protocol.scope_rule.parameters)[key])
                            for key in ('sport', 'competition', 'season', 'event_phase'))),
        evidence_cutoff_at=cutoff, cumulative_scope=cumulative, bounded_scopes=tuple(bounded),
        computation_started_at=started, rule_references=tuple(sorted(rules)),
        software_revision=software_revision)


def _calendar_dates(source, scope, spec, histories):
    # Acquisition request coverage is independent of returned games. It is read
    # below from source-root bundles in _calculate, never inferred from game rows.
    start = scope.start.astimezone(ZoneInfo(legacy.TIMEZONE_NAME)).date()
    if scope.end is not None:
        end = scope.end
        if spec.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE:
            end -= timedelta(microseconds=1)  # independent strict pre-activation rule
    else:
        end = max((x.scheduled_start for history in histories for x in history.observations),
                  default=spec.evidence_cutoff_at)
        end = max(end, spec.evidence_cutoff_at)
    last = end.astimezone(ZoneInfo(legacy.TIMEZONE_NAME)).date()
    return tuple(start+timedelta(days=i) for i in range(max(0, (last-start).days+1)))


def _verified_dates(archive, source):
    from forecast_reporting_source import _ReportingArchiveView
    from forecast_standalone_operations import OperationsError, _is_supporting_session_authority_rejection
    from forecast_standalone_activation import verify_acquisition_bundle, verify_supporting_session_completion
    # Original replay already validated the frozen inventory, including acquisitions
    # with no new contracts. Such valid-empty receipts are not graph source roots.
    view = _ReportingArchiveView(archive, source.manifest_inventory)
    dates = set()
    for entry in view.entries():
        if not entry.get('normalized_object_id'):
            continue
        value = view.read_json_verified('normalized', entry['normalized_object_id'])
        if value.get('record_kind') != 'pr17c1-acquisition-bundle' or value.get('provider') != 'mlb-stats-api':
            continue
        if value.get('family') == 'refresh-retrospective-supporting' and value.get('page_record_kind') == 'pr17c2-supporting-session-page':
            session = value.get('supporting_session_id') or value.get('acquisition_id', '').rsplit(':', 1)[0]
            try:
                verified = verify_supporting_session_completion(view, session)
            except OperationsError as exc:
                if _is_supporting_session_authority_rejection(exc):
                    continue
                raise
            if entry['manifest_entry_id'] != verified['mlb_manifest_id']:
                continue
        verify_acquisition_bundle(view, value)
        dates.update(date.fromisoformat(page['request_identity']) for page in value['pages'])
    return dates


def _calculate(archive, source, state, spec):
    """Only invoked with a source graph reconstructed by the public verifier."""
    activation, protocol = _authority(state, spec.protocol_id)
    cutoff = spec.evidence_cutoff_at
    started = spec.computation_started_at
    provenance = ResearchContractProvenance('pops-edge:report-local-analysis', VERSION,
        additional_input_ids=(source.boundary_id, spec.object_id),
        notes=('new Analysis of frozen source Evidence; no source availability claim at K',),
        generated_at=started)
    opportunities = tuple(x for x in state.bucket('opportunities') if x.protocol_id == spec.protocol_id)
    ids = {x.research_capture_opportunity_id for x in opportunities}
    contexts = tuple(x for x in state.bucket('eligibility_contexts') if x.research_capture_opportunity_id in ids)
    results = tuple(x for x in state.bucket('eligibility_results') if x.research_capture_opportunity_id in ids)
    histories = state.bucket('outcome_histories')
    manifests = tuple(x for x in state.bucket('manifests') if x.protocol_id == spec.protocol_id)
    attempts = tuple(x for x in state.bucket('attempts') if x.protocol_id == spec.protocol_id)
    snapshots = tuple(x for x in state.bucket('snapshots') if x.protocol_id == spec.protocol_id)
    candles = state.bucket('candles')
    common = dict(protocol=protocol, activation=activation, analysis_boundary=cutoff,
        opportunities=opportunities, eligibility_contexts=contexts, eligibility_results=results,
        schedule_histories=histories, classifications=state.bucket('classifications'),
        manifests=manifests, candles=candles, attempts=attempts, snapshots=snapshots,
        market_observations=state.bucket('market_observations'), market_series=state.bucket('market_series'),
        provenance=provenance, analytical_boundary=started, eligible_due_only=True,
        cumulative_start=spec.cumulative_scope.start if spec.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE else None)
    # Complete Coverage is reconstructed before successful derivation selection.
    preliminary = legacy._coverage_material(**common)
    targets = set(preliminary['reconciliation'].derivation_unavailable)
    context_map = {x.research_capture_opportunity_id: x for x in contexts}
    result_map = {x.research_capture_opportunity_id: x for x in results}
    history_map = {x.canonical_event_id: x for x in histories}
    terminal = legacy.validate_manifest_lineage(manifests, cutoff) if manifests else ()
    selected_snapshots = legacy.select_authoritative_prospective_snapshots(snapshots, cutoff)
    derivations = []; measurements = []; failures = []
    hder = []; mder = []; raw_measurements = []
    for opportunity in opportunities:
        oid = opportunity.research_capture_opportunity_id
        if oid not in targets:
            continue
        context = context_map[oid]; result = result_map[oid]
        history = history_map[context.canonical_event_id]
        schedule = next(x for x in history.observations if x.observation_id == opportunity.schedule_observation_id)
        inputs = dict(protocol=protocol, activation=activation, opportunity=opportunity,
            eligibility_context=context, eligibility_result=result, schedule_history=history,
            effective_at=started, provenance=provenance)
        try:
            if spec.design_tag is legacy.StandaloneDesignTag.RETROSPECTIVE:
                matching = tuple(x for x in terminal if x.opportunity_id == oid)
                if len(matching) != 1:
                    _fail('ambiguous historical source selection')
                manifest = matching[0]
                calculation = legacy.create_historical_candle_probability_derivation(**inputs,
                    analysis_boundary=cutoff, manifest=manifest, manifests=manifests,
                    candles=tuple(x for x in candles if x.manifest_id == manifest.historical_candle_query_manifest_id),
                    home_participant_id=schedule.home_participant_id, complement_outcome_id=schedule.away_participant_id)
                hder.append(calculation); kind = legacy.DerivationKindV3.HISTORICAL_CANDLE
            else:
                matching = tuple(x for x in selected_snapshots if x.opportunity_id == oid)
                if len(matching) != 1:
                    _fail('ambiguous prospective source selection')
                snapshot = matching[0]
                observations = tuple(x for x in state.bucket('market_observations') if x.observation_id == snapshot.market_observation_id)
                if len(observations) != 1:
                    _fail('missing or ambiguous source observation')
                observation = observations[0]
                series = tuple(x for x in state.bucket('market_series') if x.series_id == observation.series_id)
                if len(series) != 1:
                    _fail('ambiguous market-series authority')
                calculation = legacy.create_standalone_market_probability_derivation(**inputs,
                    analysis_boundary=cutoff, snapshot=snapshot, snapshots=snapshots,
                    attempts=tuple(x for x in attempts if x.opportunity_id == oid),
                    observation=observation, market_observations=state.bucket('market_observations'), series=series[0])
                mder.append(calculation); kind = legacy.DerivationKindV3.PROSPECTIVE_MARKET
        except legacy.ContractError as exc:
            failures.append(f'derivation unavailable for {oid}: {exc}')
            continue
        derivation = _make(ReportLocalDerivation, computation_id=spec.object_id,
                           opportunity_id=oid, kind=kind, calculation=calculation)
        derivations.append(derivation)
        outcomes = tuple(x for x in history.observations if x.authoritative_final and x.collected_at <= cutoff)
        if outcomes:
            # Only verified K histories enter this original-domain calculator;
            # its effective_at=C selection cannot discover a later source fact.
            raw = legacy.create_probability_source_measurement_v3(**inputs,
                snapshots=snapshots, derivations=(calculation,), outcome=outcomes[-1], outcome_histories=histories)
            raw_measurements.append(raw)
            measurements.append(_make(ReportLocalMeasurement, computation_id=spec.object_id,
                                     derivation_id=derivation.object_id, calculation=raw))
    common.update(historical_derivations=tuple(hder), market_derivations=tuple(mder),
                  measurements=tuple(raw_measurements))
    derivations = tuple(sorted(derivations, key=lambda x: x.object_id))
    measurements = tuple(sorted(measurements, key=lambda x: x.object_id))
    verified_dates = _verified_dates(archive, source)
    coverages = []; performances = []
    for scope in (spec.cumulative_scope,) + spec.bounded_scopes:
        bounded = scope.name == 'time-bounded'
        material = legacy._coverage_material(**common, coverage_scope=scope.name,
            window_start=scope.start if bounded else None, window_end=scope.end)
        selected = tuple(x for x in measurements
                         if x.calculation.probability_source_measurement_v3_id in material['measurement_ids'])
        expected_ids = {x.calculation.probability_source_measurement_v3_id for x in selected}
        if expected_ids != set(material['measurement_ids']):
            _fail('Coverage references an incompatible Measurement')
        dates = _calendar_dates(source, scope, spec, histories)
        unknown = tuple(x for x in dates if x not in verified_dates)
        limitations = tuple(sorted(set(failures) | set(protocol.design.limitations) |
            ({'calendar acquisition is unverified for listed dates; no missing-game count inferred'} if unknown else set())))
        coverage = _make(ReportCoverage, computation_id=spec.object_id, scope=scope,
            coverage_universe_ids=material['coverage_universe_ids'], eligible_denominator_ids=material['eligible_denominator_ids'],
            measured_opportunity_ids=material['measured_opportunity_ids'], measurement_ids=tuple(x.object_id for x in selected),
            reconciliation=material['reconciliation'], coverage_rate=material['coverage_rate'],
            verified_calendar_dates=tuple(x for x in dates if x in verified_dates), unknown_calendar_dates=unknown,
            limitations=limitations)
        coverages.append(coverage)
        values = tuple(x.calculation for x in selected)  # already successor-ID ordered
        n, brier, log, calibration = legacy._performance_statistics(protocol, values)
        confidence = Decimal(legacy._rule_parameter(protocol.uncertainty_rule, 'confidence_level'))
        count = int(legacy._rule_parameter(protocol.uncertainty_rule, 'resamples'))
        seed = legacy._digest((SEED_VERSION, spec.object_id, spec.protocol_id, spec.domain,
            spec.source_id, spec.source_role, scope, coverage.measurement_ids,
            protocol.uncertainty_rule.rule_id, protocol.uncertainty_rule.rule_version, confidence, count))
        lower, upper, limits = legacy._one_sample_interval(tuple(x.brier_score for x in values), brier, confidence, count, seed)
        uncertainty = _make(ReportUncertainty, seed_version=SEED_VERSION, seed_digest=seed,
            confidence_level=confidence, resample_count=count, point_estimate=brier,
            lower=lower, upper=upper, sample_size=n, limitations=limits)
        performances.append(_make(ReportPerformance, computation_id=spec.object_id,
            scope_id=scope.object_id, coverage_id=coverage.object_id, measurement_ids=coverage.measurement_ids,
            sample_size=n, mean_brier_score=brier, mean_log_loss=log, calibration=calibration, uncertainty=uncertainty))
    return derivations, measurements, tuple(coverages), tuple(performances)


def _compose(context, calculated):
    derivations, measurements, coverages, performances = calculated
    return _make(StandaloneAnalyticalReport, version=VERSION, context=context,
        derivations=derivations, measurements=measurements, coverages=coverages, performances=performances,
        cumulative_performance_id=performances[0].object_id,
        bounded_performance_ids=tuple(x.object_id for x in performances[1:]),
        limitations=('offline analytical result; no operational publication or study closure',
                     'descriptive constant-0.5 reference is downstream and not computed in this slice'))


def create_standalone_report_analysis(*, archive: NamespaceArchive, source: FrozenReportingSource,
        expected_source_boundary_id: str, protocol_id: str, software_revision: str,
        clock: Callable[[], datetime], report_status: str = 'in-progress') -> StandaloneAnalyticalReport:
    state, source_receipt = verify_reporting_source(archive=archive, boundary=source,
        expected_boundary_id=expected_source_boundary_id, clock=clock)
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        spec = _specification(source, state, protocol_id, clock(), software_revision)
        if spec.computation_started_at < source_receipt.verified_at:
            _fail('computation clock precedes source verification')
        calculated = _calculate(archive, source, state, spec)
        completed = clock()
        context = _make(StandaloneReportContext, version=VERSION, computation=spec,
            computation_completed_at=completed, report_generated_at=clock(),
            report_status=report_status, closure_reference=None)
        return _compose(context, calculated)


def verify_standalone_report_analysis(*, archive: NamespaceArchive, source: FrozenReportingSource,
        expected_source_boundary_id: str, report: StandaloneAnalyticalReport,
        clock: Callable[[], datetime]) -> ReportVerificationReceipt:
    if type(report) is not StandaloneAnalyticalReport or type(report.context) is not StandaloneReportContext:
        _fail('foreign or legacy report type')
    state, source_receipt = verify_reporting_source(archive=archive, boundary=source,
        expected_boundary_id=expected_source_boundary_id, clock=clock)
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        context = report.context
        context.__post_init__()
        spec = context.computation
        expected = _specification(source, state, spec.protocol_id, spec.computation_started_at, spec.software_revision)
        if spec != expected:
            _fail('context source, Protocol, scope or rules do not reconstruct')
        reconstructed = _compose(context, _calculate(archive, source, state, expected))
        if report != reconstructed or report.to_json() != reconstructed.to_json():
            _fail('missing, extra, incompatible or altered report-local analytical references')
    verified = clock()
    legacy._require_aware(verified, 'verification time')
    if verified < max(context.report_generated_at, source_receipt.verified_at):
        _fail('verification receipt predates report')
    return ReportVerificationReceipt(VERSION, report.object_id, source.boundary_id, verified)


_TYPES = (ReportEventScope, StandaloneComputationSpecification, StandaloneReportContext,
          ReportLocalDerivation, ReportLocalMeasurement, ReportCoverage, ReportUncertainty,
          ReportPerformance, StandaloneAnalyticalReport)
_register(*_TYPES)


def deserialize_reporting_analysis(payload: str):
    """Explicit successor dispatch; decoding is not graph acceptance."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('duplicate JSON key')
            result[key] = value
        return result
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        raw = json.loads(payload, object_pairs_hook=pairs)
        cls = {item.__name__: item for item in _TYPES}.get(raw.get('__type__'))
        if cls is None:
            _fail('unknown or legacy analytical type')
        return cls.from_dict(raw)
