"""Deterministic PR15 bounded performance, Drift analysis, and reporting."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from typing import Any, Iterable

from event_contracts import ContractError, ReasonCode, SerializableContract, _register, _require_aware
from forecast_comparative_research import (
    DECIMAL_PRECISION, SCIENTIFIC_ROUNDING, CalibrationResult, ComparativeCoverage,
    ComparativeMeasurement, ComparativePerformance, PairedUncertainty,
    PopulationEligibilityResult, ResearchCaptureOpportunity, ResearchEventEligibilityContext,
    ResearchSnapshot, _digest, _mean, _parameter, _unique, create_comparative_performance,
)
from forecast_research_contracts import (
    ComparativePerformanceReportReference, DriftDisposition, DriftSurveillance, EdgeClaim,
    ProtocolClaimSet, ResearchContractProvenance, ResearchDomain, ResearchProtocol,
    replay_protocol_claim_set, validate_research_contracts,
)
from outcome_contracts import OutcomeHistory, OutcomeStatus


REPORTING_SCHEMA_VERSION = "1"
REPORTING_IDENTITY_VERSION = "1"
TIME_BOUNDED_ANALYSIS_ALGORITHM_VERSION = "1"
DRIFT_ANALYSIS_ALGORITHM_VERSION = "two-population-bootstrap-1"
REPORT_CONTRACT_VERSION = "1"
REPORT_ALGORITHM_VERSION = "1"


def _fail(detail: str, code: ReasonCode = ReasonCode.VALIDATION_FAILURE) -> None:
    raise ContractError(code, detail)


def _versions(schema: str, identity: str) -> None:
    if schema != REPORTING_SCHEMA_VERSION or identity != REPORTING_IDENTITY_VERSION:
        _fail("unsupported comparative reporting contract version")


def _material(item: Any, *, nonmaterial: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(item, field.name) for field in fields(item)
                 if field.name not in nonmaterial)


def _strict_registry(values: Iterable[Any], label: str, key) -> tuple[tuple[Any, ...], dict[str, Any]]:
    supplied = tuple(values)
    result: dict[str, Any] = {}
    for item in supplied:
        identity = key(item)
        if identity in result:
            detail = "conflicting content" if result[identity] != item else "duplicate entry"
            _fail(f"{label} contains {detail} for {identity}", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        result[identity] = item
    return supplied, result


def _single_v2_rules(protocol: ResearchProtocol) -> tuple[Any, Any]:
    if len(protocol.surveillance_window_rules) != 1:
        _fail("PR15 requires exactly one surveillance-window rule")
    window = protocol.surveillance_window_rules[0]
    drift = protocol.drift_classification_rule
    if (window.rule_id, window.rule_version) != ("rolling-days", "2"):
        _fail("PR15 requires rolling-days version 2")
    if (drift.rule_id, drift.rule_version) != ("brier-deterioration", "2"):
        _fail("PR15 requires brier-deterioration version 2")
    return window, drift


@dataclass(frozen=True, slots=True)
class TimeBoundedComparativePerformance:
    time_bounded_comparative_performance_id: str
    schema_version: str
    identity_algorithm_version: str
    analysis_algorithm_version: str
    protocol_id: str
    edge_claim_id: str
    research_domain_id: str
    benchmark_source_reference_id: str
    challenger_source_reference_id: str
    surveillance_window_rule_specification_id: str
    surveillance_window_rule_version: str
    window_start_at: datetime
    window_end_at: datetime
    analysis_boundary: datetime
    comparative_measurement_ids: tuple[str, ...]
    coverage: ComparativeCoverage
    paired_sample_size: int
    benchmark_mean_brier_score: Decimal | None
    challenger_mean_brier_score: Decimal | None
    mean_paired_brier_improvement: Decimal | None
    primary_uncertainty: PairedUncertainty
    practical_significance_threshold: Decimal
    benchmark_mean_log_loss: Decimal | None
    challenger_mean_log_loss: Decimal | None
    mean_log_loss_improvement: Decimal | None
    benchmark_calibration: CalibrationResult
    challenger_calibration: CalibrationResult
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        if self.analysis_algorithm_version != TIME_BOUNDED_ANALYSIS_ALGORITHM_VERSION:
            _fail("unsupported time-bounded analysis algorithm")
        for value in (self.window_start_at, self.window_end_at, self.analysis_boundary):
            _require_aware(value, "time-bounded scientific time")
        if not self.window_start_at < self.window_end_at == self.analysis_boundary:
            _fail("time-bounded interval must be (window_start_at, analysis_boundary]")
        measurements = _unique(self.comparative_measurement_ids, "bounded Measurements")
        limits = _unique(self.limitations, "time-bounded limitations")
        if self.coverage.comparative_measurement_ids != measurements or len(measurements) != self.paired_sample_size:
            _fail("time-bounded population conflicts with Coverage")
        material = _material(self, nonmaterial=("time_bounded_comparative_performance_id", "provenance", "input_digest", "limitations")) + (limits,)
        digest = _digest(material)
        if self.input_digest != digest or self.time_bounded_comparative_performance_id != f"time-bounded-comparative-performance:{digest}":
            _fail("Time-Bounded Comparative Performance identity conflicts with material")
        object.__setattr__(self, "comparative_measurement_ids", measurements)
        object.__setattr__(self, "limitations", limits)


def create_time_bounded_comparative_performance(*, protocol: ResearchProtocol, edge_claim: EdgeClaim,
        research_domain: ResearchDomain, analysis_boundary: datetime,
        opportunities: Iterable[ResearchCaptureOpportunity],
        eligibility_contexts: Iterable[ResearchEventEligibilityContext],
        eligibility_results: Iterable[PopulationEligibilityResult], snapshots: Iterable[ResearchSnapshot],
        measurements: Iterable[ComparativeMeasurement], outcome_histories: Iterable[OutcomeHistory],
        provenance: ResearchContractProvenance, limitations: tuple[str, ...] = ()) -> TimeBoundedComparativePerformance:
    _require_aware(analysis_boundary, "analysis_boundary")
    window_rule, _ = _single_v2_rules(protocol)
    days = _parameter(window_rule, "days")
    window_start = analysis_boundary - timedelta(days=days)
    supplied, opportunity_by_id = _strict_registry(
        opportunities, "Research Capture Opportunity registry",
        lambda item: item.research_capture_opportunity_id)
    contexts, _ = _strict_registry(
        eligibility_contexts, "eligibility-context registry",
        lambda item: item.research_event_eligibility_context_id)
    results, _ = _strict_registry(
        eligibility_results, "eligibility-result registry",
        lambda item: item.population_eligibility_result_id)
    snapshot_values, _ = _strict_registry(
        snapshots, "Research Snapshot registry", lambda item: item.research_snapshot_id)
    measurement_values, _ = _strict_registry(
        measurements, "Comparative Measurement registry", lambda item: item.comparative_measurement_id)
    histories, _ = _strict_registry(
        outcome_histories, "Outcome History registry", lambda item: item.canonical_event_id)
    authoritative_provider = _parameter(protocol.outcome_resolution_rule, "source_id")
    authoritative_histories = tuple(
        history for history in histories
        if history.authoritative_provider_id == authoritative_provider)
    schedule_by_id = {}
    for history in authoritative_histories:
        for observation in history.observations:
            prior = schedule_by_id.get(observation.observation_id)
            if prior is not None and prior != observation:
                _fail("same Schedule Evidence identity has conflicting content")
            schedule_by_id[observation.observation_id] = observation
    visible_schedule_ids = {
        observation.observation_id
        for observation in schedule_by_id.values()
        if observation.provider_status is OutcomeStatus.SCHEDULED
        and observation.collected_at <= analysis_boundary
    }
    expected_opportunity_ids = {
        ResearchCaptureOpportunity.create(
            protocol.research_protocol_id, schedule_id,
            protocol.research_population.proposition_type).research_capture_opportunity_id
        for schedule_id in visible_schedule_ids
    }
    supplied_protocol_ids = {
        item.research_capture_opportunity_id for item in supplied
        if item.protocol_id == protocol.research_protocol_id
    }
    if not expected_opportunity_ids <= supplied_protocol_ids:
        _fail(f"authoritative Schedule Evidence identifies omitted opportunities: "
              f"{sorted(expected_opportunity_ids - supplied_protocol_ids)}")
    boundary_contexts = tuple(item for item in contexts
                              if item.protocol_id == protocol.research_protocol_id
                              and item.analysis_boundary == analysis_boundary)
    boundary_results = tuple(item for item in results
                             if item.protocol_id == protocol.research_protocol_id
                             and item.analysis_boundary == analysis_boundary)
    referenced_opportunities = ({item.research_capture_opportunity_id for item in boundary_contexts}
                                | {item.research_capture_opportunity_id for item in boundary_results})
    missing = referenced_opportunities - set(opportunity_by_id)
    if missing:
        _fail(f"authoritative population references omitted opportunities: {sorted(missing)}")
    protocol_opportunities = tuple(item for item in supplied
                                   if item.protocol_id == protocol.research_protocol_id)
    foreign_contexts = tuple(item for item in boundary_contexts
                             if item.research_capture_opportunity_id not in opportunity_by_id)
    if foreign_contexts:
        _fail("eligibility context references unknown opportunity")
    for opportunity_id in expected_opportunity_ids:
        matching_contexts = tuple(item for item in boundary_contexts
                                  if item.research_capture_opportunity_id == opportunity_id)
        matching_results = tuple(item for item in boundary_results
                                 if item.research_capture_opportunity_id == opportunity_id)
        if (len(matching_contexts), len(matching_results)) != (1, 1):
            _fail("every boundary-applicable opportunity requires exactly one eligibility context and result")
        if matching_results[0].research_event_eligibility_context_id != matching_contexts[0].research_event_eligibility_context_id:
            _fail("eligibility result does not reference its authoritative context")
    bounded = []
    for opportunity in protocol_opportunities:
        schedule = schedule_by_id.get(opportunity.schedule_observation_id)
        if schedule is None:
            _fail("capture opportunity lacks authoritative Schedule Evidence")
        if schedule.collected_at > analysis_boundary:
            continue
        if window_start < schedule.scheduled_start <= analysis_boundary:
            bounded.append(opportunity)
    bounded_ids = {item.research_capture_opportunity_id for item in bounded}
    base = create_comparative_performance(
        protocol=protocol, edge_claim=edge_claim, research_domain=research_domain,
        analysis_boundary=analysis_boundary, opportunities=tuple(bounded),
        eligibility_contexts=tuple(item for item in contexts
                                   if item.research_capture_opportunity_id in bounded_ids),
        eligibility_results=tuple(item for item in results
                                  if item.research_capture_opportunity_id in bounded_ids),
        snapshots=snapshot_values, measurements=measurement_values, outcome_histories=histories,
        provenance=provenance, limitations=limitations)
    values = dict(
        schema_version=REPORTING_SCHEMA_VERSION, identity_algorithm_version=REPORTING_IDENTITY_VERSION,
        analysis_algorithm_version=TIME_BOUNDED_ANALYSIS_ALGORITHM_VERSION,
        protocol_id=base.protocol_id, edge_claim_id=base.edge_claim_id,
        research_domain_id=base.research_domain_id,
        benchmark_source_reference_id=base.benchmark_source_reference_id,
        challenger_source_reference_id=base.challenger_source_reference_id,
        surveillance_window_rule_specification_id=window_rule.rule_specification_id,
        surveillance_window_rule_version=window_rule.rule_version,
        window_start_at=window_start, window_end_at=analysis_boundary,
        analysis_boundary=analysis_boundary, comparative_measurement_ids=base.comparative_measurement_ids,
        coverage=base.coverage, paired_sample_size=base.paired_sample_size,
        benchmark_mean_brier_score=base.benchmark_mean_brier_score,
        challenger_mean_brier_score=base.challenger_mean_brier_score,
        mean_paired_brier_improvement=base.mean_paired_brier_improvement,
        primary_uncertainty=base.primary_uncertainty,
        practical_significance_threshold=base.practical_significance_threshold,
        benchmark_mean_log_loss=base.benchmark_mean_log_loss,
        challenger_mean_log_loss=base.challenger_mean_log_loss,
        mean_log_loss_improvement=base.mean_log_loss_improvement,
        benchmark_calibration=base.benchmark_calibration,
        challenger_calibration=base.challenger_calibration,
        limitations=_unique(limitations, "time-bounded limitations"), provenance=provenance)
    material = tuple(values[field.name] for field in fields(TimeBoundedComparativePerformance)
                     if field.name not in ("time_bounded_comparative_performance_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return TimeBoundedComparativePerformance(f"time-bounded-comparative-performance:{digest}", **values, input_digest=digest)


def replay_historical_comparative_performance(*, window_start_at: datetime, **kwargs: Any) -> ComparativePerformance:
    """Replay cumulative PR14 authority exactly at the surveillance-window start."""
    return create_comparative_performance(analysis_boundary=window_start_at, **kwargs)


@dataclass(frozen=True, slots=True)
class DriftUncertainty:
    point_estimate: Decimal | None
    historical_sample_size: int
    current_sample_size: int
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    confidence_level: Decimal
    statistical_rule_specification_id: str
    statistical_rule_version: str
    resample_count: int
    analysis_algorithm_version: str


@dataclass(frozen=True, slots=True)
class ComparativeDriftAnalysis:
    comparative_drift_analysis_id: str
    schema_version: str
    identity_algorithm_version: str
    analysis_algorithm_version: str
    protocol_id: str
    edge_claim_id: str
    research_domain_id: str
    benchmark_source_reference_id: str
    challenger_source_reference_id: str
    surveillance_window_rule_specification_id: str
    drift_rule_specification_id: str
    drift_rule_id: str
    drift_rule_version: str
    historical_comparative_performance_id: str
    current_time_bounded_comparative_performance_id: str
    analysis_boundary: datetime
    measured_deterioration: Decimal | None
    uncertainty: DriftUncertainty
    material_deterioration_threshold: Decimal
    disposition: DriftDisposition
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        _require_aware(self.analysis_boundary, "Drift analysis boundary")
        if self.analysis_algorithm_version != DRIFT_ANALYSIS_ALGORITHM_VERSION:
            _fail("unsupported Drift analysis algorithm")
        limits = _unique(self.limitations, "Drift limitations")
        estimable = self.measured_deterioration is not None
        if estimable != (self.uncertainty.lower_bound is not None and self.uncertainty.upper_bound is not None):
            _fail("Drift estimate and uncertainty presence conflict")
        if not estimable and self.disposition is not DriftDisposition.INSUFFICIENT_EVIDENCE:
            _fail("non-estimable Drift must be insufficient Evidence")
        material = _material(self, nonmaterial=("comparative_drift_analysis_id", "provenance", "input_digest", "limitations")) + (limits,)
        digest = _digest(material)
        if self.input_digest != digest or self.comparative_drift_analysis_id != f"comparative-drift-analysis:{digest}":
            _fail("Comparative Drift Analysis identity conflicts with material")
        object.__setattr__(self, "limitations", limits)


def _classify_drift(lower_bound: Decimal | None, upper_bound: Decimal | None,
                    threshold: Decimal) -> DriftDisposition:
    if lower_bound is None or upper_bound is None:
        return DriftDisposition.INSUFFICIENT_EVIDENCE
    if lower_bound >= threshold:
        return DriftDisposition.MATERIAL_DRIFT
    if upper_bound < threshold:
        return DriftDisposition.NO_MATERIAL_DRIFT
    return DriftDisposition.INSUFFICIENT_EVIDENCE


def _two_population_bootstrap(historical: tuple[ComparativeMeasurement, ...], current: tuple[ComparativeMeasurement, ...],
                              *, protocol: ResearchProtocol, claim_id: str, domain_id: str,
                              historical_id: str, current_id: str, boundary: datetime) -> DriftUncertainty:
    rule = protocol.statistical_method_rule
    confidence, resamples = _parameter(rule, "confidence_level"), _parameter(rule, "resamples")
    if not historical or not current:
        return DriftUncertainty(None, len(historical), len(current), None, None, confidence,
                                rule.rule_specification_id, rule.rule_version, resamples,
                                DRIFT_ANALYSIS_ALGORITHM_VERSION)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        point = (_mean(tuple(item.brier_improvement for item in historical))
                 - _mean(tuple(item.brier_improvement for item in current)))  # type: ignore[operator]
    seed = _digest((protocol.research_protocol_id, claim_id, domain_id, historical_id, current_id,
                    boundary, rule.rule_specification_id, DRIFT_ANALYSIS_ALGORITHM_VERSION))
    samples = []
    for sample_index in range(resamples):
        populations = []
        for stream, source in (("historical", historical), ("current", current)):
            draws = []
            for draw_index in range(len(source)):
                token = f"{seed}:{stream}:{sample_index}:{draw_index}".encode()
                draws.append(source[int.from_bytes(hashlib.sha256(token).digest(), "big") % len(source)].brier_improvement)
            populations.append(_mean(tuple(draws)))
        with localcontext() as context:
            context.prec = DECIMAL_PRECISION
            context.rounding = SCIENTIFIC_ROUNDING
            samples.append(populations[0] - populations[1])  # type: ignore[operator]
    ordered = tuple(sorted(samples))
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        tail = (Decimal(1) - confidence) / Decimal(2)
        lo = int((tail * (resamples - 1)).to_integral_value(rounding=ROUND_FLOOR))
        hi = int(((Decimal(1) - tail) * (resamples - 1)).to_integral_value(rounding=ROUND_CEILING))
    return DriftUncertainty(point, len(historical), len(current), ordered[lo], ordered[hi], confidence,
                            rule.rule_specification_id, rule.rule_version, resamples,
                            DRIFT_ANALYSIS_ALGORITHM_VERSION)


def create_comparative_drift_analysis(*, protocol: ResearchProtocol, historical: ComparativePerformance,
        current: TimeBoundedComparativePerformance, measurements: Iterable[ComparativeMeasurement],
        provenance: ResearchContractProvenance, limitations: tuple[str, ...] = ()) -> ComparativeDriftAnalysis:
    window_rule, drift_rule = _single_v2_rules(protocol)
    common = ("protocol_id", "edge_claim_id", "research_domain_id", "benchmark_source_reference_id", "challenger_source_reference_id")
    if any(getattr(historical, name) != getattr(current, name) for name in common):
        _fail("historical and current Drift populations are incompatible")
    if historical.analysis_boundary != current.window_start_at or current.window_end_at != current.analysis_boundary:
        _fail("Drift chronology conflicts with surveillance window")
    _, by_id = _strict_registry(measurements, "Drift Measurement registry",
                                lambda item: item.comparative_measurement_id)
    try:
        historical_population = tuple(by_id[item] for item in historical.comparative_measurement_ids)
        current_population = tuple(by_id[item] for item in current.comparative_measurement_ids)
    except KeyError as error:
        _fail(f"Drift population references unknown Measurement {error.args[0]}")
    uncertainty = _two_population_bootstrap(historical_population, current_population, protocol=protocol,
        claim_id=current.edge_claim_id, domain_id=current.research_domain_id,
        historical_id=historical.comparative_performance_id,
        current_id=current.time_bounded_comparative_performance_id, boundary=current.analysis_boundary)
    threshold = _parameter(drift_rule, "threshold")
    disposition = _classify_drift(uncertainty.lower_bound, uncertainty.upper_bound, threshold)
    values = dict(schema_version=REPORTING_SCHEMA_VERSION, identity_algorithm_version=REPORTING_IDENTITY_VERSION,
        analysis_algorithm_version=DRIFT_ANALYSIS_ALGORITHM_VERSION, protocol_id=current.protocol_id,
        edge_claim_id=current.edge_claim_id, research_domain_id=current.research_domain_id,
        benchmark_source_reference_id=current.benchmark_source_reference_id,
        challenger_source_reference_id=current.challenger_source_reference_id,
        surveillance_window_rule_specification_id=window_rule.rule_specification_id,
        drift_rule_specification_id=drift_rule.rule_specification_id, drift_rule_id=drift_rule.rule_id,
        drift_rule_version=drift_rule.rule_version,
        historical_comparative_performance_id=historical.comparative_performance_id,
        current_time_bounded_comparative_performance_id=current.time_bounded_comparative_performance_id,
        analysis_boundary=current.analysis_boundary, measured_deterioration=uncertainty.point_estimate,
        uncertainty=uncertainty, material_deterioration_threshold=threshold, disposition=disposition,
        limitations=_unique(limitations, "Drift limitations"), provenance=provenance)
    material = tuple(values[field.name] for field in fields(ComparativeDriftAnalysis)
                     if field.name not in ("comparative_drift_analysis_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return ComparativeDriftAnalysis(f"comparative-drift-analysis:{digest}", **values, input_digest=digest)


@dataclass(frozen=True, slots=True, order=True)
class ReportSurveillanceFinding:
    surveillance_window_rule_specification_id: str
    time_bounded_comparative_performance_id: str
    comparative_drift_analysis_id: str


@dataclass(frozen=True, slots=True, order=True)
class ReportClaimFinding:
    edge_claim_id: str
    cumulative_comparative_performance_id: str
    surveillance_finding: ReportSurveillanceFinding


@dataclass(frozen=True, slots=True)
class ComparativePerformanceReport:
    comparative_performance_report_id: str
    schema_version: str
    identity_algorithm_version: str
    contract_version: str
    report_algorithm_version: str
    protocol_id: str
    protocol_claim_set_id: str
    analysis_boundary: datetime
    claim_findings: tuple[ReportClaimFinding, ...]
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        _require_aware(self.analysis_boundary, "report analysis boundary")
        if (self.contract_version, self.report_algorithm_version) != (REPORT_CONTRACT_VERSION, REPORT_ALGORITHM_VERSION):
            _fail("unsupported Comparative Performance Report version")
        findings = _unique(self.claim_findings, "report claim findings", lambda item: item.edge_claim_id)
        limits = _unique(self.limitations, "report limitations")
        if not findings:
            _fail("report requires complete nonempty claim findings")
        material = _material(self, nonmaterial=("comparative_performance_report_id", "provenance", "input_digest", "limitations")) + (limits,)
        digest = _digest(material)
        if self.input_digest != digest or self.comparative_performance_report_id != f"comparative-performance-report:{digest}":
            _fail("Comparative Performance Report identity conflicts with material")
        object.__setattr__(self, "claim_findings", findings)
        object.__setattr__(self, "limitations", limits)

    def to_reference(self) -> ComparativePerformanceReportReference:
        return ComparativePerformanceReportReference(
            self.schema_version, self.identity_algorithm_version,
            self.comparative_performance_report_id, self.contract_version,
            self.protocol_id, self.analysis_boundary,
            tuple(item.edge_claim_id for item in self.claim_findings))


def create_comparative_performance_report(*, protocol: ResearchProtocol, claims: Iterable[EdgeClaim],
        protocol_claim_sets: Iterable[ProtocolClaimSet],
        cumulative_performances: Iterable[ComparativePerformance],
        bounded_performances: Iterable[TimeBoundedComparativePerformance],
        drift_analyses: Iterable[ComparativeDriftAnalysis], provenance: ResearchContractProvenance,
        analysis_boundary: datetime, limitations: tuple[str, ...] = ()) -> ComparativePerformanceReport:
    _single_v2_rules(protocol)
    claim_values, claim_by_id = _strict_registry(claims, "Edge Claim registry", lambda item: item.edge_claim_id)
    claim_set_values, _ = _strict_registry(
        protocol_claim_sets, "Protocol Claim Set registry",
        lambda item: item.protocol_claim_set_id)
    validate_research_contracts(
        protocols=(protocol,), claims=claim_values,
        protocol_claim_sets=claim_set_values, reviews=(), market_edges=(),
        drift_surveillance=())
    authoritative_claim_set = replay_protocol_claim_set(
        protocol_id=protocol.research_protocol_id, analysis_boundary=analysis_boundary,
        protocol_claim_sets=claim_set_values)
    if authoritative_claim_set is None:
        _fail("canonical report requires an authoritative Protocol Claim Set")
    authoritative = []
    for claim_id in authoritative_claim_set.edge_claim_ids:
        claim = claim_by_id.get(claim_id)
        if claim is None:
            _fail("authoritative Protocol Claim Set references unknown Edge Claim")
        if claim.protocol_id != protocol.research_protocol_id:
            _fail("authoritative Protocol Claim Set contains a foreign-Protocol claim")
        authoritative.append(claim)
    authoritative = tuple(authoritative)
    cumulative_values, _ = _strict_registry(
        cumulative_performances, "cumulative Comparative Performance registry",
        lambda item: item.comparative_performance_id)
    bounded_values, _ = _strict_registry(
        bounded_performances, "Time-Bounded Comparative Performance registry",
        lambda item: item.time_bounded_comparative_performance_id)
    drift_values, _ = _strict_registry(
        drift_analyses, "Comparative Drift Analysis registry",
        lambda item: item.comparative_drift_analysis_id)
    authoritative_ids = {item.edge_claim_id for item in authoritative}
    graph_claim_ids = ({item.edge_claim_id for item in cumulative_values
                        if item.protocol_id == protocol.research_protocol_id and item.analysis_boundary == analysis_boundary}
                       | {item.edge_claim_id for item in bounded_values
                          if item.protocol_id == protocol.research_protocol_id and item.analysis_boundary == analysis_boundary}
                       | {item.edge_claim_id for item in drift_values
                          if item.protocol_id == protocol.research_protocol_id and item.analysis_boundary == analysis_boundary})
    if graph_claim_ids != authoritative_ids:
        _fail("report claim registry is not the complete authoritative analytical claim set")
    findings = []
    for claim in authoritative:
        cumulative = tuple(item for item in cumulative_values
                           if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == analysis_boundary)
        bounded = tuple(item for item in bounded_values
                        if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == analysis_boundary)
        drift = tuple(item for item in drift_values
                      if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == analysis_boundary)
        if (len(cumulative), len(bounded), len(drift)) != (1, 1, 1):
            _fail("report requires exactly one cumulative, bounded, and Drift artifact per claim")
        c, b, d = cumulative[0], bounded[0], drift[0]
        common = ("protocol_id", "edge_claim_id", "research_domain_id", "benchmark_source_reference_id", "challenger_source_reference_id", "analysis_boundary")
        if any(getattr(c, name) != getattr(b, name) or getattr(b, name) != getattr(d, name) for name in common):
            _fail("report claim analytical artifacts are incompatible")
        if d.current_time_bounded_comparative_performance_id != b.time_bounded_comparative_performance_id:
            _fail("report Drift does not reuse its bounded artifact")
        window_rule, drift_rule = _single_v2_rules(protocol)
        if (b.surveillance_window_rule_specification_id != window_rule.rule_specification_id
                or d.surveillance_window_rule_specification_id != window_rule.rule_specification_id
                or d.drift_rule_specification_id != drift_rule.rule_specification_id):
            _fail("report analytical package conflicts with Protocol surveillance/Drift rules")
        findings.append(ReportClaimFinding(claim.edge_claim_id, c.comparative_performance_id,
            ReportSurveillanceFinding(b.surveillance_window_rule_specification_id,
                                      b.time_bounded_comparative_performance_id,
                                      d.comparative_drift_analysis_id)))
    values = dict(schema_version=REPORTING_SCHEMA_VERSION, identity_algorithm_version=REPORTING_IDENTITY_VERSION,
        contract_version=REPORT_CONTRACT_VERSION, report_algorithm_version=REPORT_ALGORITHM_VERSION,
        protocol_id=protocol.research_protocol_id,
        protocol_claim_set_id=authoritative_claim_set.protocol_claim_set_id,
        analysis_boundary=analysis_boundary,
        claim_findings=tuple(findings), limitations=_unique(limitations, "report limitations"), provenance=provenance)
    material = tuple(values[field.name] for field in fields(ComparativePerformanceReport)
                     if field.name not in ("comparative_performance_report_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return ComparativePerformanceReport(f"comparative-performance-report:{digest}", **values, input_digest=digest)


def validate_comparative_reporting_contracts(*, protocols: Iterable[ResearchProtocol], claims: Iterable[EdgeClaim],
        protocol_claim_sets: Iterable[ProtocolClaimSet],
        cumulative_performances: Iterable[ComparativePerformance],
        bounded_performances: Iterable[TimeBoundedComparativePerformance],
        drift_analyses: Iterable[ComparativeDriftAnalysis], reports: Iterable[ComparativePerformanceReport],
        opportunities: Iterable[ResearchCaptureOpportunity] = (),
        eligibility_contexts: Iterable[ResearchEventEligibilityContext] = (),
        eligibility_results: Iterable[PopulationEligibilityResult] = (),
        snapshots: Iterable[ResearchSnapshot] = (),
        measurements: Iterable[ComparativeMeasurement] = (),
        outcome_histories: Iterable[OutcomeHistory] = (),
        drift_surveillance: Iterable[DriftSurveillance] = ()) -> None:
    _, protocol_by_id = _strict_registry(protocols, "Research Protocol registry",
                                         lambda item: item.research_protocol_id)
    claim_values, _ = _strict_registry(claims, "Edge Claim registry", lambda item: item.edge_claim_id)
    claim_set_values, _ = _strict_registry(
        protocol_claim_sets, "Protocol Claim Set registry",
        lambda item: item.protocol_claim_set_id)
    cumulative, _ = _strict_registry(cumulative_performances, "cumulative performance registry",
                                     lambda item: item.comparative_performance_id)
    bounded, _ = _strict_registry(bounded_performances, "bounded performance registry",
                                  lambda item: item.time_bounded_comparative_performance_id)
    drift, _ = _strict_registry(drift_analyses, "Drift analysis registry",
                                lambda item: item.comparative_drift_analysis_id)
    report_values, _ = _strict_registry(reports, "report registry",
                                        lambda item: item.comparative_performance_report_id)
    opportunity_values, _ = _strict_registry(opportunities, "opportunity registry",
                                             lambda item: item.research_capture_opportunity_id)
    context_values, _ = _strict_registry(eligibility_contexts, "eligibility-context registry",
                                         lambda item: item.research_event_eligibility_context_id)
    result_values, _ = _strict_registry(eligibility_results, "eligibility-result registry",
                                        lambda item: item.population_eligibility_result_id)
    snapshot_values, _ = _strict_registry(snapshots, "Snapshot registry", lambda item: item.research_snapshot_id)
    measurement_values, _ = _strict_registry(measurements, "Measurement registry",
                                              lambda item: item.comparative_measurement_id)
    history_values, _ = _strict_registry(outcome_histories, "Outcome History registry",
                                         lambda item: item.canonical_event_id)
    validate_research_contracts(
        protocols=protocol_by_id.values(), claims=claim_values,
        protocol_claim_sets=claim_set_values, reviews=(), market_edges=(),
        drift_surveillance=())
    for protocol in protocol_by_id.values():
        _single_v2_rules(protocol)
    cumulative_by_id = {item.comparative_performance_id: item for item in cumulative}
    bounded_by_id = {item.time_bounded_comparative_performance_id: item for item in bounded}
    claim_by_id = {item.edge_claim_id: item for item in claim_values}
    for item in cumulative:
        protocol = protocol_by_id.get(item.protocol_id)
        claim = claim_by_id.get(item.edge_claim_id)
        if protocol is None or claim is None:
            _fail("cumulative performance references unknown Protocol or claim")
        domain = next((value for value in protocol.research_domains
                       if value.research_domain_id == item.research_domain_id), None)
        if domain is None:
            _fail("cumulative performance references unknown Research Domain")
        recreated = create_comparative_performance(
            protocol=protocol, edge_claim=claim, research_domain=domain,
            analysis_boundary=item.analysis_boundary, opportunities=opportunity_values,
            eligibility_contexts=context_values, eligibility_results=result_values,
            snapshots=snapshot_values, measurements=measurement_values,
            outcome_histories=history_values, provenance=item.provenance,
            limitations=item.limitations)
        if recreated != item:
            _fail("cumulative performance does not reproduce from authoritative PR14 inputs")
    for item in bounded:
        protocol = protocol_by_id.get(item.protocol_id)
        claim = next((value for value in claim_values if value.edge_claim_id == item.edge_claim_id), None)
        if protocol is None or claim is None:
            _fail("bounded performance references unknown Protocol or claim")
        domain = next((value for value in protocol.research_domains
                       if value.research_domain_id == item.research_domain_id), None)
        if domain is None:
            _fail("bounded performance references unknown Research Domain")
        recreated = create_time_bounded_comparative_performance(
            protocol=protocol, edge_claim=claim, research_domain=domain,
            analysis_boundary=item.analysis_boundary, opportunities=opportunity_values,
            eligibility_contexts=context_values, eligibility_results=result_values,
            snapshots=snapshot_values, measurements=measurement_values,
            outcome_histories=history_values, provenance=item.provenance,
            limitations=item.limitations)
        if recreated != item:
            _fail("bounded performance does not reproduce from authoritative inputs")
    for item in drift:
        protocol = protocol_by_id.get(item.protocol_id)
        historical = cumulative_by_id.get(item.historical_comparative_performance_id)
        current = bounded_by_id.get(item.current_time_bounded_comparative_performance_id)
        if protocol is None or historical is None or current is None:
            _fail("Drift analysis references unknown authoritative input")
        recreated = create_comparative_drift_analysis(
            protocol=protocol, historical=historical, current=current,
            measurements=measurement_values, provenance=item.provenance,
            limitations=item.limitations)
        if recreated != item:
            _fail("Drift analysis does not reproduce from authoritative inputs")
    for report in report_values:
        protocol = protocol_by_id.get(report.protocol_id)
        if protocol is None:
            _fail("report references unknown Protocol")
        recreated = create_comparative_performance_report(
            protocol=protocol,
            claims=claim_values, protocol_claim_sets=claim_set_values,
            cumulative_performances=cumulative,
            bounded_performances=bounded, drift_analyses=drift, provenance=report.provenance,
            analysis_boundary=report.analysis_boundary, limitations=report.limitations)
        if recreated != report:
            _fail("report does not reproduce from authoritative analytical inputs")
    report_by_id = {item.comparative_performance_report_id: item for item in report_values}
    drift_by_key = {(item.edge_claim_id, item.analysis_boundary): item for item in drift}
    for surveillance in drift_surveillance:
        report = report_by_id.get(surveillance.report_reference.report_id)
        if report is None or surveillance.report_reference != report.to_reference():
            _fail("Drift Surveillance report reference does not project from canonical report")
        analysis = drift_by_key.get((surveillance.edge_claim_id, report.analysis_boundary))
        if analysis is None or (surveillance.protocol_id, surveillance.drift_rule_id,
                                surveillance.drift_rule_version, surveillance.disposition) != (
                                analysis.protocol_id, analysis.drift_rule_id,
                                analysis.drift_rule_version, analysis.disposition):
            _fail("Drift Surveillance conflicts with corresponding Drift analysis")


_CONTRACTS = (TimeBoundedComparativePerformance, DriftUncertainty, ComparativeDriftAnalysis,
              ReportSurveillanceFinding, ReportClaimFinding, ComparativePerformanceReport)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]
_register(*_CONTRACTS)
