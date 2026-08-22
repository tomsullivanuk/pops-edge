"""Immutable PR14 Evidence, Measurement, and cumulative Forecast Intelligence.

This module is deliberately offline and provider-neutral.  It consumes PR13
Research Protocols plus authoritative schedule, forecast-evaluation, and
Outcome records; it creates no report, scientific conclusion, policy, or
operational authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext
from enum import Enum
from typing import Any, Iterable

from event_contracts import CanonicalEvent, ContractError, ReasonCode, SerializableContract, _register, _require_aware, _require_identifier
from forecast_contracts import ForecastObservation, ForecastValidationStatus, ReconciliationOutcome
from forecast_evaluation import ForecastEvaluation
from forecast_research_contracts import (
    EdgeClaim,
    ResearchContractProvenance,
    ResearchDomain,
    ResearchProtocol,
)
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


COMPARATIVE_RESEARCH_SCHEMA_VERSION = "1"
COMPARATIVE_RESEARCH_IDENTITY_VERSION = "1"
SNAPSHOT_ALGORITHM_VERSION = "1"
MEASUREMENT_ALGORITHM_VERSION = "1"
COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION = "1"
DECIMAL_PRECISION = 50
SCIENTIFIC_ROUNDING = ROUND_HALF_EVEN
CALIBRATION_BOUNDARIES = tuple(Decimal(f"{index / 10:.1f}") for index in range(11))


def _fail(detail: str, code: ReasonCode = ReasonCode.VALIDATION_FAILURE) -> None:
    raise ContractError(code, detail)


def _utc(value: datetime) -> str:
    _require_aware(value, "scientific datetime")
    return value.astimezone(timezone.utc).isoformat()


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"datetime_utc": _utc(value)}
    if isinstance(value, Decimal):
        if value.is_nan():
            _fail("scientific Decimal must not be NaN")
        if value == Decimal("Infinity"):
            return {"decimal_special": "positive-infinity"}
        if value == Decimal("-Infinity"):
            return {"decimal_special": "negative-infinity"}
        return {"decimal": str(value)}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, float):
        _fail("binary float cannot participate in comparative research")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported comparative research value: {type(value).__name__}")


def _digest(value: Any) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _versions(schema: str, identity: str) -> None:
    if schema != COMPARATIVE_RESEARCH_SCHEMA_VERSION or identity != COMPARATIVE_RESEARCH_IDENTITY_VERSION:
        _fail("unsupported comparative research contract version")


def _unique(values: Iterable[Any], label: str, key=lambda item: item) -> tuple[Any, ...]:
    supplied = tuple(values)
    keys = tuple(key(item) for item in supplied)
    if len(keys) != len(set(keys)):
        _fail(f"{label} contains duplicates", ReasonCode.CONTRADICTORY_LINEAGE)
    return tuple(item for _, item in sorted(zip(keys, supplied), key=lambda pair: pair[0]))


def _parameter(rule: Any, name: str) -> Any:
    matches = tuple(item.value for item in rule.parameters if item.name == name)
    if len(matches) != 1:
        _fail(f"rule {rule.rule_id} requires parameter {name}")
    return matches[0]


class SourceCaptureDisposition(str, Enum):
    CAPTURED_VALID = "captured-valid"
    MISSING = "missing"
    CAPTURED_INVALID = "captured-invalid"
    OUTSIDE_CAPTURE_TOLERANCE = "outside-capture-tolerance"


class SnapshotValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class EventPhase(str, Enum):
    REGULAR_SEASON = "regular-season"
    POSTSEASON = "postseason"
    OTHER = "other"


class PopulationEligibilityDisposition(str, Enum):
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"


class PopulationEligibilityValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class EventStageEvidence:
    event_stage_evidence_id: str
    canonical_event_id: str
    provider_id: str
    provider_event_id: str
    event_phase: EventPhase
    observed_at: datetime
    evidence_reference: str
    input_digest: str

    @classmethod
    def create(cls, *, canonical_event_id: str, provider_id: str, provider_event_id: str,
               event_phase: EventPhase, observed_at: datetime, evidence_reference: str) -> "EventStageEvidence":
        material = (canonical_event_id, provider_id, provider_event_id, event_phase, observed_at, evidence_reference)
        digest = _digest(material)
        return cls(f"event-stage-evidence:{digest}", *material, digest)

    def __post_init__(self) -> None:
        for value in (self.canonical_event_id, self.provider_id, self.provider_event_id, self.evidence_reference):
            _require_identifier(value, "event-stage Evidence material")
        _require_aware(self.observed_at, "event-stage observed_at")
        digest = _digest((self.canonical_event_id, self.provider_id, self.provider_event_id,
                          self.event_phase, self.observed_at, self.evidence_reference))
        if self.input_digest != digest or self.event_stage_evidence_id != f"event-stage-evidence:{digest}":
            _fail("event-stage Evidence identity conflicts with material")


@dataclass(frozen=True, slots=True, order=True)
class EligibilityHistoryState:
    observation_id: str
    provider_status: OutcomeStatus
    scheduled_start: datetime
    collected_at: datetime

    def __post_init__(self) -> None:
        _require_identifier(self.observation_id, "eligibility history observation")
        _require_aware(self.scheduled_start, "eligibility scheduled_start")
        _require_aware(self.collected_at, "eligibility collected_at")


@dataclass(frozen=True, slots=True)
class ResearchEventEligibilityContext:
    research_event_eligibility_context_id: str
    research_capture_opportunity_id: str
    protocol_id: str
    canonical_event_id: str
    sport: str
    competition: str
    season: str
    participant_ids: tuple[str, ...]
    event_stage_evidence_id: str
    event_phase: EventPhase
    outcome_history_provider_id: str
    history_states: tuple[EligibilityHistoryState, ...]
    analysis_boundary: datetime
    input_digest: str

    @classmethod
    def create(cls, *, opportunity: "ResearchCaptureOpportunity", protocol: ResearchProtocol,
               canonical_event: CanonicalEvent, stage_evidence: EventStageEvidence,
               outcome_history: OutcomeHistory, analysis_boundary: datetime) -> "ResearchEventEligibilityContext":
        _require_aware(analysis_boundary, "eligibility analysis_boundary")
        if opportunity.protocol_id != protocol.research_protocol_id:
            _fail("eligibility opportunity conflicts with Protocol")
        population = protocol.research_population
        if (canonical_event.sport, canonical_event.competition) != (population.sport, population.competition):
            _fail("Canonical Event conflicts with Research Population")
        if stage_evidence.canonical_event_id != canonical_event.canonical_event_id:
            _fail("event-stage Evidence conflicts with Canonical Event")
        if outcome_history.canonical_event_id != canonical_event.canonical_event_id:
            _fail("Outcome History conflicts with Canonical Event")
        authoritative_provider = _parameter(protocol.outcome_resolution_rule, "source_id")
        if outcome_history.authoritative_provider_id != authoritative_provider:
            _fail("Outcome History is not Protocol-authoritative")
        provider_event_ids = {item.provider_event_id for item in outcome_history.observations}
        if (stage_evidence.provider_id != outcome_history.authoritative_provider_id
                or stage_evidence.provider_event_id not in provider_event_ids):
            _fail("event-stage Evidence lacks authoritative sport-provider lineage")
        visible = tuple(item for item in outcome_history.observations if item.collected_at <= analysis_boundary)
        if not visible:
            _fail("eligibility context requires authoritative history through analysis boundary")
        if opportunity.schedule_observation_id not in {item.observation_id for item in visible}:
            _fail("capture opportunity Schedule Evidence is not available by analysis boundary")
        if stage_evidence.observed_at > analysis_boundary:
            _fail("event-stage Evidence is not available by analysis boundary")
        states = tuple(EligibilityHistoryState(item.observation_id, item.provider_status,
                                               item.scheduled_start, item.collected_at) for item in visible)
        participants = tuple(sorted(item.canonical_id for item in canonical_event.participants))
        values = (opportunity.research_capture_opportunity_id, protocol.research_protocol_id,
                  canonical_event.canonical_event_id, canonical_event.sport, canonical_event.competition,
                  canonical_event.season, participants, stage_evidence.event_stage_evidence_id,
                  stage_evidence.event_phase, outcome_history.authoritative_provider_id, states, analysis_boundary)
        digest = _digest(values)
        return cls(f"research-event-eligibility-context:{digest}", *values, digest)

    def __post_init__(self) -> None:
        _require_aware(self.analysis_boundary, "eligibility analysis_boundary")
        states = tuple(self.history_states)
        if len({item.observation_id for item in states}) != len(states):
            _fail("eligibility history contains duplicate observations")
        if tuple(sorted(states, key=lambda item: (item.collected_at, item.observation_id))) != states:
            _fail("eligibility history must use authoritative chronology")
        values = (self.research_capture_opportunity_id, self.protocol_id, self.canonical_event_id,
                  self.sport, self.competition, self.season, self.participant_ids,
                  self.event_stage_evidence_id, self.event_phase, self.outcome_history_provider_id,
                  states, self.analysis_boundary)
        digest = _digest(values)
        if self.input_digest != digest or self.research_event_eligibility_context_id != f"research-event-eligibility-context:{digest}":
            _fail("eligibility context identity conflicts with material")


@dataclass(frozen=True, slots=True)
class PopulationEligibilityResult:
    population_eligibility_result_id: str
    research_capture_opportunity_id: str
    research_event_eligibility_context_id: str
    protocol_id: str
    research_population_id: str
    analysis_boundary: datetime
    disposition: PopulationEligibilityDisposition
    governing_rule_specification_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    validation_status: PopulationEligibilityValidationStatus
    validation_reasons: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, research_capture_opportunity_id: str,
               research_event_eligibility_context_id: str, protocol_id: str,
               research_population_id: str, analysis_boundary: datetime,
               disposition: PopulationEligibilityDisposition,
               governing_rule_specification_ids: tuple[str, ...], reason_codes: tuple[str, ...],
               validation_status: PopulationEligibilityValidationStatus,
               validation_reasons: tuple[str, ...], provenance: ResearchContractProvenance) -> "PopulationEligibilityResult":
        rules = _unique(governing_rule_specification_ids, "eligibility governing rules")
        reasons = _unique(reason_codes, "eligibility reasons")
        validation = _unique(validation_reasons, "eligibility validation reasons")
        values = (research_capture_opportunity_id, research_event_eligibility_context_id,
                  protocol_id, research_population_id, analysis_boundary, disposition,
                  rules, reasons, validation_status, validation)
        digest = _digest(values)
        return cls(f"population-eligibility-result:{digest}", *values, provenance, digest)

    def __post_init__(self) -> None:
        _require_aware(self.analysis_boundary, "population eligibility analysis_boundary")
        rules = _unique(self.governing_rule_specification_ids, "eligibility governing rules")
        reasons = _unique(self.reason_codes, "eligibility reasons")
        validation = _unique(self.validation_reasons, "eligibility validation reasons")
        if self.disposition is PopulationEligibilityDisposition.ELIGIBLE and reasons:
            _fail("eligible population result cannot carry exclusion reasons")
        if self.disposition is PopulationEligibilityDisposition.EXCLUDED and not reasons:
            _fail("excluded population result requires deterministic reasons")
        if self.validation_status is PopulationEligibilityValidationStatus.VALID and validation:
            _fail("valid Population Eligibility Result cannot carry validation reasons")
        if self.validation_status is PopulationEligibilityValidationStatus.INVALID and not validation:
            _fail("invalid Population Eligibility Result requires validation reasons")
        values = (self.research_capture_opportunity_id, self.research_event_eligibility_context_id,
                  self.protocol_id, self.research_population_id, self.analysis_boundary,
                  self.disposition, rules, reasons, self.validation_status, validation)
        digest = _digest(values)
        if self.input_digest != digest or self.population_eligibility_result_id != f"population-eligibility-result:{digest}":
            _fail("Population Eligibility Result identity conflicts with material")
        object.__setattr__(self, "governing_rule_specification_ids", rules)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "validation_reasons", validation)


@dataclass(frozen=True, slots=True)
class ResearchCaptureOpportunity:
    research_capture_opportunity_id: str
    schema_version: str
    identity_algorithm_version: str
    protocol_id: str
    schedule_observation_id: str
    proposition_type: str
    input_digest: str

    @classmethod
    def create(cls, protocol_id: str, schedule_observation_id: str, proposition_type: str,
               *, schema_version: str = COMPARATIVE_RESEARCH_SCHEMA_VERSION,
               identity_algorithm_version: str = COMPARATIVE_RESEARCH_IDENTITY_VERSION) -> "ResearchCaptureOpportunity":
        material = (schema_version, identity_algorithm_version, protocol_id, schedule_observation_id, proposition_type)
        digest = _digest(material)
        return cls(f"research-capture-opportunity:{digest}", schema_version, identity_algorithm_version,
                   protocol_id, schedule_observation_id, proposition_type, digest)

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        for value in (self.protocol_id, self.schedule_observation_id, self.proposition_type):
            _require_identifier(value, "capture opportunity material")
        digest = _digest((self.schema_version, self.identity_algorithm_version, self.protocol_id,
                          self.schedule_observation_id, self.proposition_type))
        if self.input_digest != digest or self.research_capture_opportunity_id != f"research-capture-opportunity:{digest}":
            _fail("Research Capture Opportunity identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


def evaluate_population_eligibility(*, protocol: ResearchProtocol,
                                    opportunity: ResearchCaptureOpportunity,
                                    context: ResearchEventEligibilityContext,
                                    provenance: ResearchContractProvenance) -> PopulationEligibilityResult:
    if (opportunity.protocol_id, context.protocol_id, context.research_capture_opportunity_id) != (
            protocol.research_protocol_id, protocol.research_protocol_id,
            opportunity.research_capture_opportunity_id):
        _fail("Population eligibility inputs are incompatible")
    population = protocol.research_population
    if (context.sport, context.competition) != (population.sport, population.competition):
        _fail("eligibility context conflicts with Research Population")
    rules = (population.temporal_scope_rule, population.event_status_rule,
             population.postseason_treatment_rule, population.postponement_treatment_rule,
             population.cancellation_treatment_rule, population.rescheduling_treatment_rule,
             *population.inclusion_rules, *population.exclusion_rules)
    expected = (
        ("season-range", "1"), ("allowed-event-statuses", "1"),
        ("postseason-treatment", "1"), ("postponement-treatment", "1"),
        ("cancellation-treatment", "1"), ("rescheduling-treatment", "1"),
    )
    if tuple((rule.rule_id, rule.rule_version) for rule in rules[:6]) != expected:
        _fail("unsupported Research Population rule mechanics")
    if any((rule.rule_id, rule.rule_version) != ("include-all-otherwise-eligible", "1")
           for rule in population.inclusion_rules):
        _fail("unsupported population inclusion rule mechanics")
    if any((rule.rule_id, rule.rule_version) != ("exclude-none-additional", "1")
           for rule in population.exclusion_rules):
        _fail("unsupported population exclusion rule mechanics")
    reasons: list[str] = []
    first = _parameter(population.temporal_scope_rule, "first_season")
    last = _parameter(population.temporal_scope_rule, "last_season")
    if not first <= context.season <= last:
        reasons.append("outside-temporal-scope")
    latest = context.history_states[-1]
    allowed = set(_parameter(population.event_status_rule, "statuses"))
    if latest.provider_status.value not in allowed:
        reasons.append("event-status-not-eligible")
    include_postseason = _parameter(population.postseason_treatment_rule, "include")
    if context.event_phase is EventPhase.POSTSEASON and not include_postseason:
        reasons.append("postseason-excluded")
    statuses = tuple(item.provider_status for item in context.history_states)
    if OutcomeStatus.CANCELLED in statuses:
        if _parameter(population.cancellation_treatment_rule, "action") == "exclude":
            reasons.append("cancelled")
    if OutcomeStatus.POSTPONED in statuses:
        action = _parameter(population.postponement_treatment_rule, "action")
        if action == "exclude":
            reasons.append("postponed")
        elif action == "retain-if-rescheduled" and latest.provider_status is OutcomeStatus.POSTPONED:
            reasons.append("postponed-without-reschedule")
    schedule_state = next(item for item in context.history_states
                          if item.observation_id == opportunity.schedule_observation_id)
    schedule_starts = tuple(item.scheduled_start for item in context.history_states)
    rescheduled = len(set(schedule_starts)) > 1
    reschedule_action = _parameter(population.rescheduling_treatment_rule, "action")
    if rescheduled and reschedule_action == "exclude":
        reasons.append("rescheduled-event-excluded")
    elif rescheduled and reschedule_action == "use-current-schedule" and schedule_state.scheduled_start != latest.scheduled_start:
        reasons.append("superseded-schedule-opportunity")
    disposition = (PopulationEligibilityDisposition.ELIGIBLE if not reasons
                   else PopulationEligibilityDisposition.EXCLUDED)
    rule_ids = tuple(rule.rule_specification_id for rule in rules)
    ordered_reasons = tuple(sorted(set(reasons)))
    return PopulationEligibilityResult.create(
        research_capture_opportunity_id=opportunity.research_capture_opportunity_id,
        research_event_eligibility_context_id=context.research_event_eligibility_context_id,
        protocol_id=protocol.research_protocol_id,
        research_population_id=population.research_population_id,
        analysis_boundary=context.analysis_boundary,
        disposition=disposition,
        governing_rule_specification_ids=tuple(sorted(rule_ids)),
        reason_codes=ordered_reasons,
        validation_status=PopulationEligibilityValidationStatus.VALID,
        validation_reasons=(),
        provenance=provenance,
    )


@dataclass(frozen=True, slots=True, order=True)
class SourceCapture:
    probability_source_reference_id: str
    disposition: SourceCaptureDisposition
    forecast_observation_id: str | None = None
    observed_at: datetime | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.probability_source_reference_id, "capture source reference")
        if self.disposition is SourceCaptureDisposition.MISSING:
            if self.forecast_observation_id is not None or self.observed_at is not None:
                _fail("missing source capture cannot reference fabricated Evidence")
        else:
            if self.forecast_observation_id is None or self.observed_at is None:
                _fail("non-missing source capture requires observation identity and chronology")
            _require_identifier(self.forecast_observation_id, "captured forecast observation")
            _require_aware(self.observed_at, "source observed_at")
        if self.disposition is not SourceCaptureDisposition.CAPTURED_VALID and not self.reasons:
            _fail("unsuccessful source capture requires reasons")
        if self.disposition is SourceCaptureDisposition.CAPTURED_VALID and self.reasons:
            _fail("captured-valid source capture cannot carry failure reasons")
        object.__setattr__(self, "reasons", _unique(self.reasons, "capture reasons"))


@dataclass(frozen=True, slots=True, order=True)
class PairwiseSynchronization:
    benchmark_source_reference_id: str
    challenger_source_reference_id: str
    synchronized: bool
    separation_microseconds: int | None
    synchronization_rule_id: str
    synchronization_rule_version: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.benchmark_source_reference_id, self.challenger_source_reference_id,
                      self.synchronization_rule_id, self.synchronization_rule_version):
            _require_identifier(value, "synchronization material")
        if self.benchmark_source_reference_id == self.challenger_source_reference_id:
            _fail("synchronization pair requires distinct sources")
        if self.separation_microseconds is not None and (not isinstance(self.separation_microseconds, int)
                                                          or isinstance(self.separation_microseconds, bool)
                                                          or self.separation_microseconds < 0):
            _fail("synchronization separation must be non-negative integer microseconds")
        if self.synchronized and (self.separation_microseconds is None or self.reasons):
            _fail("synchronized pair requires separation and no failure reasons")
        if not self.synchronized and not self.reasons:
            _fail("unsynchronized pair requires reasons")
        object.__setattr__(self, "reasons", _unique(self.reasons, "synchronization reasons"))


def create_pairwise_synchronization(*, benchmark_capture: SourceCapture,
                                    challenger_capture: SourceCapture, synchronization_rule: Any) -> PairwiseSynchronization:
    if synchronization_rule.rule_id != "maximum-pair-separation" or synchronization_rule.rule_version != "1":
        _fail("unsupported synchronization rule mechanics")
    valid = (benchmark_capture.disposition is SourceCaptureDisposition.CAPTURED_VALID
             and challenger_capture.disposition is SourceCaptureDisposition.CAPTURED_VALID)
    if valid:
        assert benchmark_capture.observed_at is not None and challenger_capture.observed_at is not None
        delta = abs(benchmark_capture.observed_at - challenger_capture.observed_at)
        separation = ((delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds)
        synchronized = delta <= timedelta(seconds=_parameter(synchronization_rule, "seconds"))
        reasons = () if synchronized else ("capture-separation-exceeds-protocol-maximum",)
    else:
        separation = None
        synchronized = False
        reasons = ("source-capture-not-valid",)
    return PairwiseSynchronization(
        benchmark_capture.probability_source_reference_id,
        challenger_capture.probability_source_reference_id,
        synchronized, separation, synchronization_rule.rule_id,
        synchronization_rule.rule_version, reasons,
    )


def _outside_capture_tolerance(observed_at: datetime, target_capture_at: datetime,
                               maximum_seconds: int) -> bool:
    return abs(observed_at - target_capture_at) > timedelta(seconds=maximum_seconds)


@dataclass(frozen=True, slots=True, order=True)
class SnapshotDimensionClassification:
    approved_dimension_id: str
    partition_key: str
    classification_rule_id: str
    classification_rule_version: str

    def __post_init__(self) -> None:
        for value in (self.approved_dimension_id, self.partition_key,
                      self.classification_rule_id, self.classification_rule_version):
            _require_identifier(value, "Snapshot dimension classification")


@dataclass(frozen=True, slots=True)
class ResearchSnapshot:
    research_snapshot_id: str
    schema_version: str
    identity_algorithm_version: str
    snapshot_algorithm_version: str
    research_capture_opportunity_id: str
    protocol_id: str
    effective_at: datetime
    supersedes_snapshot_id: str | None
    correction_reason: str | None
    canonical_event_id: str
    proposition_type: str
    canonical_proposition_outcome_id: str
    scheduled_start: datetime
    target_capture_at: datetime
    capture_started_at: datetime
    capture_completed_at: datetime
    source_captures: tuple[SourceCapture, ...]
    pairwise_synchronization: tuple[PairwiseSynchronization, ...]
    dimension_classifications: tuple[SnapshotDimensionClassification, ...]
    validation_status: SnapshotValidationStatus
    validation_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, research_capture_opportunity_id: str, protocol_id: str, effective_at: datetime,
               canonical_event_id: str, proposition_type: str, canonical_proposition_outcome_id: str,
               scheduled_start: datetime, target_capture_at: datetime, capture_started_at: datetime,
               capture_completed_at: datetime, source_captures: tuple[SourceCapture, ...],
               pairwise_synchronization: tuple[PairwiseSynchronization, ...],
               dimension_classifications: tuple[SnapshotDimensionClassification, ...],
               validation_status: SnapshotValidationStatus, provenance: ResearchContractProvenance,
               supersedes_snapshot_id: str | None = None, correction_reason: str | None = None,
               validation_reasons: tuple[str, ...] = (), limitations: tuple[str, ...] = (),
               schema_version: str = COMPARATIVE_RESEARCH_SCHEMA_VERSION,
               identity_algorithm_version: str = COMPARATIVE_RESEARCH_IDENTITY_VERSION,
               snapshot_algorithm_version: str = SNAPSHOT_ALGORITHM_VERSION) -> "ResearchSnapshot":
        captures = _unique(source_captures, "Snapshot source captures", lambda item: item.probability_source_reference_id)
        pairs = _unique(pairwise_synchronization, "Snapshot synchronization pairs", lambda item: item.challenger_source_reference_id)
        dimensions = _unique(dimension_classifications, "Snapshot classifications", lambda item: item.approved_dimension_id)
        reasons = _unique(validation_reasons, "Snapshot validation reasons")
        limits = _unique(limitations, "Snapshot limitations")
        values = (schema_version, identity_algorithm_version, snapshot_algorithm_version,
                  research_capture_opportunity_id, protocol_id, effective_at, supersedes_snapshot_id,
                  correction_reason, canonical_event_id, proposition_type, canonical_proposition_outcome_id,
                  scheduled_start, target_capture_at, capture_started_at, capture_completed_at,
                  captures, pairs, dimensions, validation_status, reasons, limits)
        digest = _digest(values)
        return cls(f"research-snapshot:{digest}", *values[:15], captures, pairs, dimensions,
                   validation_status, reasons, limits, provenance, digest)

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        if self.snapshot_algorithm_version != SNAPSHOT_ALGORITHM_VERSION:
            _fail("unsupported Snapshot algorithm version")
        for value in (self.research_capture_opportunity_id, self.protocol_id, self.canonical_event_id,
                      self.proposition_type, self.canonical_proposition_outcome_id):
            _require_identifier(value, "Snapshot identity/reference")
        for value, label in ((self.effective_at, "effective_at"), (self.scheduled_start, "scheduled_start"),
                             (self.target_capture_at, "target_capture_at"), (self.capture_started_at, "capture_started_at"),
                             (self.capture_completed_at, "capture_completed_at")):
            _require_aware(value, label)
        if self.capture_started_at > self.capture_completed_at:
            _fail("Snapshot capture chronology is reversed")
        if (self.supersedes_snapshot_id is None) != (self.correction_reason is None):
            _fail("Snapshot correction reference and reason must be supplied together")
        if self.supersedes_snapshot_id is not None:
            _require_identifier(self.supersedes_snapshot_id, "superseded Snapshot")
            if not self.correction_reason or not self.correction_reason.strip():
                _fail("Snapshot correction reason is required")
        captures = _unique(self.source_captures, "Snapshot source captures", lambda item: item.probability_source_reference_id)
        pairs = _unique(self.pairwise_synchronization, "Snapshot synchronization pairs", lambda item: item.challenger_source_reference_id)
        dimensions = _unique(self.dimension_classifications, "Snapshot classifications", lambda item: item.approved_dimension_id)
        reasons = _unique(self.validation_reasons, "Snapshot validation reasons")
        limits = _unique(self.limitations, "Snapshot limitations")
        if self.validation_status is SnapshotValidationStatus.VALID and reasons:
            _fail("valid Snapshot cannot carry validation reasons")
        if self.validation_status is SnapshotValidationStatus.INVALID and not reasons:
            _fail("invalid Snapshot requires validation reasons")
        values = (self.schema_version, self.identity_algorithm_version, self.snapshot_algorithm_version,
                  self.research_capture_opportunity_id, self.protocol_id, self.effective_at,
                  self.supersedes_snapshot_id, self.correction_reason, self.canonical_event_id,
                  self.proposition_type, self.canonical_proposition_outcome_id, self.scheduled_start,
                  self.target_capture_at, self.capture_started_at, self.capture_completed_at,
                  captures, pairs, dimensions, self.validation_status, reasons, limits)
        digest = _digest(values)
        if self.input_digest != digest or self.research_snapshot_id != f"research-snapshot:{digest}":
            _fail("Research Snapshot identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "source_captures", captures)
        object.__setattr__(self, "pairwise_synchronization", pairs)
        object.__setattr__(self, "dimension_classifications", dimensions)
        object.__setattr__(self, "validation_reasons", reasons)
        object.__setattr__(self, "limitations", limits)


def select_authoritative_research_snapshots(snapshots: Iterable[ResearchSnapshot],
                                            analysis_boundary: datetime) -> tuple[ResearchSnapshot, ...]:
    _require_aware(analysis_boundary, "analysis_boundary")
    visible = tuple(item for item in snapshots if item.effective_at <= analysis_boundary)
    by_id = _registry(visible, "Research Snapshot", lambda item: item.research_snapshot_id)
    by_opportunity: dict[str, list[ResearchSnapshot]] = {}
    for item in by_id.values():
        by_opportunity.setdefault(item.research_capture_opportunity_id, []).append(item)
        if item.supersedes_snapshot_id is not None:
            prior = by_id.get(item.supersedes_snapshot_id)
            if prior is None:
                # A predecessor effective before the correction must be present in supplied history.
                _fail("Snapshot correction references unknown or future predecessor", ReasonCode.CONTRADICTORY_LINEAGE)
            if prior.research_capture_opportunity_id != item.research_capture_opportunity_id:
                _fail("Snapshot correction crosses capture opportunities", ReasonCode.CONTRADICTORY_LINEAGE)
            if prior.effective_at >= item.effective_at:
                _fail("Snapshot correction must become effective after its predecessor")
    selected = []
    for opportunity_id, values in by_opportunity.items():
        children: dict[str, list[str]] = {item.research_snapshot_id: [] for item in values}
        for item in values:
            if item.supersedes_snapshot_id is not None:
                children[item.supersedes_snapshot_id].append(item.research_snapshot_id)
        if any(len(items) > 1 for items in children.values()):
            _fail("Snapshot correction lineage branches", ReasonCode.CONTRADICTORY_LINEAGE)
        roots = tuple(item for item in values if item.supersedes_snapshot_id is None)
        terminals = tuple(item for item in values if not children[item.research_snapshot_id])
        if len(roots) != 1 or len(terminals) != 1:
            _fail(f"Snapshot history for {opportunity_id} is ambiguous", ReasonCode.CONTRADICTORY_LINEAGE)
        seen: set[str] = set()
        cursor = terminals[0]
        while True:
            if cursor.research_snapshot_id in seen:
                _fail("Snapshot correction lineage contains a cycle", ReasonCode.CONTRADICTORY_LINEAGE)
            seen.add(cursor.research_snapshot_id)
            if cursor.supersedes_snapshot_id is None:
                break
            cursor = by_id[cursor.supersedes_snapshot_id]
        if len(seen) != len(values):
            _fail("Snapshot history contains disconnected material versions", ReasonCode.CONTRADICTORY_LINEAGE)
        selected.append(terminals[0])
    return tuple(sorted(selected, key=lambda item: item.research_capture_opportunity_id))


@dataclass(frozen=True, slots=True)
class ComparativeMeasurement:
    comparative_measurement_id: str
    schema_version: str
    identity_algorithm_version: str
    measurement_algorithm_version: str
    protocol_id: str
    research_snapshot_id: str
    effective_at: datetime
    benchmark_source_reference_id: str
    challenger_source_reference_id: str
    outcome_observation_id: str
    canonical_event_id: str
    proposition_type: str
    canonical_proposition_outcome_id: str
    realized_outcome: int
    benchmark_evaluation_id: str
    challenger_evaluation_id: str
    benchmark_probability: Decimal
    challenger_probability: Decimal
    benchmark_brier_score: Decimal
    challenger_brier_score: Decimal
    brier_improvement: Decimal
    benchmark_log_loss: Decimal
    challenger_log_loss: Decimal
    log_loss_improvement: Decimal | None
    dimension_classifications: tuple[SnapshotDimensionClassification, ...]
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    def __post_init__(self) -> None:
        _versions(self.schema_version, self.identity_algorithm_version)
        if self.measurement_algorithm_version != MEASUREMENT_ALGORITHM_VERSION:
            _fail("unsupported Comparative Measurement algorithm version")
        for value in (self.protocol_id, self.research_snapshot_id, self.benchmark_source_reference_id,
                      self.challenger_source_reference_id, self.outcome_observation_id, self.canonical_event_id,
                      self.proposition_type, self.canonical_proposition_outcome_id,
                      self.benchmark_evaluation_id, self.challenger_evaluation_id):
            _require_identifier(value, "Comparative Measurement reference")
        _require_aware(self.effective_at, "Measurement effective_at")
        if self.realized_outcome not in (0, 1):
            _fail("Comparative Measurement Outcome must be binary")
        for value in (self.benchmark_probability, self.challenger_probability,
                      self.benchmark_brier_score, self.challenger_brier_score, self.brier_improvement):
            if not isinstance(value, Decimal) or not value.is_finite():
                _fail("Comparative Measurement probabilities and Brier values require finite Decimal")
        with localcontext() as context:
            context.prec = DECIMAL_PRECISION
            context.rounding = SCIENTIFIC_ROUNDING
            expected_brier = self.benchmark_brier_score - self.challenger_brier_score
        if self.brier_improvement != expected_brier:
            _fail("Brier improvement arithmetic conflicts with source evaluations")
        for value in (self.benchmark_log_loss, self.challenger_log_loss):
            if not isinstance(value, Decimal) or value.is_nan() or value == Decimal("-Infinity") or value < 0:
                _fail("source Log Loss must be in [0,+Infinity]")
        if self.log_loss_improvement is not None and (
                not isinstance(self.log_loss_improvement, Decimal) or self.log_loss_improvement.is_nan()):
            _fail("paired Log Loss improvement must be Decimal or absent")
        expected_log = _difference(self.benchmark_log_loss, self.challenger_log_loss)
        if self.log_loss_improvement != expected_log:
            _fail("Log Loss improvement arithmetic conflicts with source evaluations")
        dimensions = _unique(self.dimension_classifications, "Measurement classifications", lambda item: item.approved_dimension_id)
        limits = _unique(self.limitations, "Measurement limitations")
        material = _measurement_material(self, dimensions, limits)
        digest = _digest(material)
        if self.input_digest != digest or self.comparative_measurement_id != f"comparative-measurement:{digest}":
            _fail("Comparative Measurement identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "dimension_classifications", dimensions)
        object.__setattr__(self, "limitations", limits)


def _difference(left: Decimal, right: Decimal) -> Decimal | None:
    if left == Decimal("Infinity") and right == Decimal("Infinity"):
        return None
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        return left - right


def _measurement_material(item: ComparativeMeasurement, dimensions: tuple[Any, ...], limits: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(item, name) for name in (
        "schema_version", "identity_algorithm_version", "measurement_algorithm_version", "protocol_id",
        "research_snapshot_id", "effective_at", "benchmark_source_reference_id", "challenger_source_reference_id",
        "outcome_observation_id", "canonical_event_id", "proposition_type", "canonical_proposition_outcome_id",
        "realized_outcome", "benchmark_evaluation_id", "challenger_evaluation_id", "benchmark_probability",
        "challenger_probability", "benchmark_brier_score", "challenger_brier_score", "brier_improvement",
        "benchmark_log_loss", "challenger_log_loss", "log_loss_improvement")) + (dimensions, limits)


def create_comparative_measurement(*, protocol: ResearchProtocol, snapshot: ResearchSnapshot,
                                   benchmark_evaluation: ForecastEvaluation,
                                   challenger_evaluation: ForecastEvaluation, outcome: OutcomeObservation,
                                   effective_at: datetime, provenance: ResearchContractProvenance,
                                   limitations: tuple[str, ...] = ()) -> ComparativeMeasurement:
    _require_aware(effective_at, "Measurement effective_at")
    if snapshot.validation_status is not SnapshotValidationStatus.VALID:
        _fail("invalid Research Snapshot cannot produce Comparative Measurement")
    benchmark_id = protocol.market_benchmark.probability_source_reference_id
    capture_map = {item.probability_source_reference_id: item for item in snapshot.source_captures}
    evaluation_by_observation = {benchmark_evaluation.forecast_observation_id: benchmark_evaluation,
                                 challenger_evaluation.forecast_observation_id: challenger_evaluation}
    matched = []
    for source_id, capture in capture_map.items():
        evaluation = evaluation_by_observation.get(capture.forecast_observation_id or "")
        if evaluation is not None:
            matched.append((source_id, evaluation))
    benchmark_matches = tuple(item for item in matched if item[0] == benchmark_id and item[1] == benchmark_evaluation)
    challenger_matches = tuple(item for item in matched if item[1] == challenger_evaluation and item[0] != benchmark_id)
    if len(benchmark_matches) != 1 or len(challenger_matches) != 1:
        _fail("Evaluations do not match Snapshot source captures")
    challenger_id = challenger_matches[0][0]
    sources = {protocol.market_benchmark.probability_source_reference_id: protocol.market_benchmark,
               **{item.probability_source_reference_id: item for item in protocol.alternative_sources}}
    authorized = set(sources) - {benchmark_id}
    if challenger_id not in authorized:
        _fail("Comparative Measurement challenger is not Protocol-authorized")
    for source_id, evaluation in ((benchmark_id, benchmark_evaluation), (challenger_id, challenger_evaluation)):
        source = sources[source_id]
        if (evaluation.provider_id, evaluation.model_id, evaluation.model_version_id) != (
                source.provider_id, source.model_or_product_id, source.model_or_product_version):
            _fail("Evaluation source lineage conflicts with Protocol source reference")
    if any(capture_map[source].disposition is not SourceCaptureDisposition.CAPTURED_VALID
           for source in (benchmark_id, challenger_id)):
        _fail("Comparative Measurement requires valid benchmark and challenger captures")
    pair = tuple(item for item in snapshot.pairwise_synchronization if item.challenger_source_reference_id == challenger_id)
    if len(pair) != 1 or not pair[0].synchronized:
        _fail("Comparative Measurement requires a synchronized pair")
    if snapshot.protocol_id != protocol.research_protocol_id or snapshot.proposition_type != protocol.research_population.proposition_type:
        _fail("Snapshot conflicts with Research Protocol")
    evaluations = (benchmark_evaluation, challenger_evaluation)
    if any(item.canonical_event_id != snapshot.canonical_event_id or item.outcome_observation_id != outcome.observation_id for item in evaluations):
        _fail("Evaluation, Snapshot, and Outcome lineage conflict")
    authoritative_provider = _parameter(protocol.outcome_resolution_rule, "source_id")
    if (not outcome.authoritative_final or outcome.canonical_event_id != snapshot.canonical_event_id
            or outcome.authoritative_provider_id != authoritative_provider):
        _fail("Comparative Measurement requires compatible authoritative final Outcome")
    if effective_at < outcome.collected_at or effective_at < snapshot.effective_at:
        _fail("Comparative Measurement cannot be effective before its Evidence")
    outcome_id = snapshot.canonical_proposition_outcome_id
    try:
        benchmark_probability = dict(benchmark_evaluation.probability_distribution)[outcome_id]
        challenger_probability = dict(challenger_evaluation.probability_distribution)[outcome_id]
        realized = dict(benchmark_evaluation.realized_outcome_vector)[outcome_id]
    except KeyError as error:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                            "canonical proposition orientation is absent from Evaluation") from error
    if dict(challenger_evaluation.realized_outcome_vector).get(outcome_id) != realized:
        _fail("Evaluation Outcome orientations conflict")
    values = dict(
        schema_version=COMPARATIVE_RESEARCH_SCHEMA_VERSION,
        identity_algorithm_version=COMPARATIVE_RESEARCH_IDENTITY_VERSION,
        measurement_algorithm_version=MEASUREMENT_ALGORITHM_VERSION,
        protocol_id=protocol.research_protocol_id, research_snapshot_id=snapshot.research_snapshot_id,
        effective_at=effective_at, benchmark_source_reference_id=benchmark_id,
        challenger_source_reference_id=challenger_id, outcome_observation_id=outcome.observation_id,
        canonical_event_id=snapshot.canonical_event_id, proposition_type=snapshot.proposition_type,
        canonical_proposition_outcome_id=outcome_id, realized_outcome=realized,
        benchmark_evaluation_id=benchmark_evaluation.evaluation_id,
        challenger_evaluation_id=challenger_evaluation.evaluation_id,
        benchmark_probability=benchmark_probability, challenger_probability=challenger_probability,
        benchmark_brier_score=benchmark_evaluation.brier_score,
        challenger_brier_score=challenger_evaluation.brier_score,
        brier_improvement=_difference(benchmark_evaluation.brier_score, challenger_evaluation.brier_score),
        benchmark_log_loss=benchmark_evaluation.log_loss, challenger_log_loss=challenger_evaluation.log_loss,
        log_loss_improvement=_difference(benchmark_evaluation.log_loss, challenger_evaluation.log_loss),
        dimension_classifications=snapshot.dimension_classifications,
        limitations=tuple(sorted(set(benchmark_evaluation.limitations)
                                 | set(challenger_evaluation.limitations) | set(limitations))),
        provenance=provenance,
    )
    material = tuple(values[name] for name in (
        "schema_version", "identity_algorithm_version", "measurement_algorithm_version", "protocol_id",
        "research_snapshot_id", "effective_at", "benchmark_source_reference_id", "challenger_source_reference_id",
        "outcome_observation_id", "canonical_event_id", "proposition_type", "canonical_proposition_outcome_id",
        "realized_outcome", "benchmark_evaluation_id", "challenger_evaluation_id", "benchmark_probability",
        "challenger_probability", "benchmark_brier_score", "challenger_brier_score", "brier_improvement",
        "benchmark_log_loss", "challenger_log_loss", "log_loss_improvement")) + (
            values["dimension_classifications"], values["limitations"])
    digest = _digest(material)
    return ComparativeMeasurement(f"comparative-measurement:{digest}", **values, input_digest=digest)


@dataclass(frozen=True, slots=True, order=True)
class CalibrationBin:
    lower_bound: Decimal
    upper_bound: Decimal
    upper_inclusive: bool
    count: int
    mean_probability: Decimal | None
    observed_frequency: Decimal | None
    calibration_gap: Decimal | None

    def __post_init__(self) -> None:
        for value, label in ((self.lower_bound, "lower bound"), (self.upper_bound, "upper bound")):
            if not isinstance(value, Decimal) or not value.is_finite() or not Decimal(0) <= value <= Decimal(1):
                _fail(f"Calibration {label} must be finite in [0,1]")
        if self.lower_bound >= self.upper_bound:
            _fail("Calibration bin boundaries are reversed")
        if self.count < 0 or isinstance(self.count, bool):
            _fail("Calibration count must be non-negative")
        absent = (self.mean_probability, self.observed_frequency, self.calibration_gap)
        if self.count == 0 and any(value is not None for value in absent):
            _fail("empty Calibration bin statistics must be absent")
        if self.count > 0 and any(value is None for value in absent):
            _fail("nonempty Calibration bin statistics are required")
        if self.count > 0:
            assert self.mean_probability is not None and self.observed_frequency is not None and self.calibration_gap is not None
            if any(not isinstance(value, Decimal) or not value.is_finite()
                   for value in (self.mean_probability, self.observed_frequency, self.calibration_gap)):
                _fail("Calibration bin statistics require finite Decimal")
            if not Decimal(0) <= self.mean_probability <= Decimal(1) or not Decimal(0) <= self.observed_frequency <= Decimal(1):
                _fail("Calibration means and frequencies must be in [0,1]")
            with localcontext() as context:
                context.prec = DECIMAL_PRECISION
                context.rounding = SCIENTIFIC_ROUNDING
                expected_gap = self.observed_frequency - self.mean_probability
            if self.calibration_gap != expected_gap:
                _fail("Calibration gap conflicts with observed frequency and mean probability")


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    rule_specification_id: str
    rule_version: str
    sample_size: int
    bins: tuple[CalibrationBin, ...]
    weighted_absolute_calibration_error: Decimal | None

    def __post_init__(self) -> None:
        _require_identifier(self.rule_specification_id, "Calibration rule")
        if self.rule_version != "2" or len(self.bins) != 10:
            _fail("canonical Calibration requires rule version 2 and ten bins")
        for index, item in enumerate(self.bins):
            if (item.lower_bound, item.upper_bound, item.upper_inclusive) != (
                    CALIBRATION_BOUNDARIES[index], CALIBRATION_BOUNDARIES[index + 1], index == 9):
                _fail("Calibration bin boundaries conflict with canonical version 2")
        if sum(item.count for item in self.bins) != self.sample_size:
            _fail("Calibration counts conflict with paired sample size")
        if (self.sample_size == 0) != (self.weighted_absolute_calibration_error is None):
            _fail("WACE must be absent exactly when the paired population is empty")
        if self.sample_size > 0:
            with localcontext() as context:
                context.prec = DECIMAL_PRECISION
                context.rounding = SCIENTIFIC_ROUNDING
                expected = sum((Decimal(item.count) / self.sample_size) * abs(item.calibration_gap)
                               for item in self.bins if item.count and item.calibration_gap is not None)
            if self.weighted_absolute_calibration_error != expected:
                _fail("WACE conflicts with canonical Calibration bins")


@dataclass(frozen=True, slots=True)
class PairedUncertainty:
    point_estimate: Decimal | None
    paired_sample_size: int
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    confidence_level: Decimal
    statistical_rule_specification_id: str
    statistical_rule_version: str
    resample_count: int
    analysis_algorithm_version: str


@dataclass(frozen=True, slots=True)
class ComparativeCoverage:
    applicable_population_eligibility_result_ids: tuple[str, ...]
    eligible_population_eligibility_result_ids: tuple[str, ...]
    excluded_population_eligibility_result_ids: tuple[str, ...]
    eligible_capture_opportunity_ids: tuple[str, ...]
    authoritative_snapshot_ids: tuple[str, ...]
    benchmark_capture_failure_snapshot_ids: tuple[str, ...]
    challenger_capture_failure_snapshot_ids: tuple[str, ...]
    capture_timing_failure_snapshot_ids: tuple[str, ...]
    eligible_snapshot_ids: tuple[str, ...]
    benchmark_available_snapshot_ids: tuple[str, ...]
    challenger_available_snapshot_ids: tuple[str, ...]
    synchronized_pair_snapshot_ids: tuple[str, ...]
    unsynchronized_pair_snapshot_ids: tuple[str, ...]
    resolved_outcome_snapshot_ids: tuple[str, ...]
    protocol_excluded_opportunity_ids: tuple[str, ...]
    protocol_excluded_snapshot_ids: tuple[str, ...]
    comparative_measurement_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(self, field.name, _unique(getattr(self, field.name), f"Coverage {field.name}"))
        applicable = set(self.applicable_population_eligibility_result_ids)
        eligible = set(self.eligible_population_eligibility_result_ids)
        excluded = set(self.excluded_population_eligibility_result_ids)
        if eligible & excluded or eligible | excluded != applicable:
            _fail("Coverage eligibility-result categories must form a disjoint complete partition")
        authoritative = set(self.authoritative_snapshot_ids)
        for name in tuple(field.name for field in fields(self) if field.name.endswith("snapshot_ids")):
            if not set(getattr(self, name)) <= authoritative:
                _fail(f"Coverage {name} references a non-authoritative Snapshot")
        if set(self.synchronized_pair_snapshot_ids) & set(self.unsynchronized_pair_snapshot_ids):
            _fail("Coverage synchronized and unsynchronized categories overlap")


@dataclass(frozen=True, slots=True)
class ComparativePerformance:
    comparative_performance_id: str
    schema_version: str
    identity_algorithm_version: str
    analysis_algorithm_version: str
    protocol_id: str
    edge_claim_id: str
    research_domain_id: str
    analysis_boundary: datetime
    benchmark_source_reference_id: str
    challenger_source_reference_id: str
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
        if self.analysis_algorithm_version != COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION:
            _fail("unsupported Comparative Performance algorithm version")
        _require_aware(self.analysis_boundary, "Comparative Performance analysis_boundary")
        measurements = _unique(self.comparative_measurement_ids, "Comparative Performance Measurements")
        limits = _unique(self.limitations, "Comparative Performance limitations")
        if len(measurements) != self.paired_sample_size or self.primary_uncertainty.paired_sample_size != self.paired_sample_size:
            _fail("Comparative Performance paired sample sizes conflict")
        if self.coverage.comparative_measurement_ids != measurements:
            _fail("Comparative Performance population conflicts with Coverage")
        material = tuple(getattr(self, field.name) for field in fields(self)
                         if field.name not in ("comparative_performance_id", "provenance", "input_digest", "limitations")) + (limits,)
        digest = _digest(material)
        if self.input_digest != digest or self.comparative_performance_id != f"comparative-performance:{digest}":
            _fail("Comparative Performance identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "comparative_measurement_ids", measurements)
        object.__setattr__(self, "limitations", limits)


def _mean(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    if any(value == Decimal("Infinity") for value in values):
        return Decimal("Infinity")
    if any(value == Decimal("-Infinity") for value in values):
        return Decimal("-Infinity")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        return sum(values, Decimal(0)) / len(values)


def _mean_log_loss_improvement(values: tuple[Decimal | None, ...]) -> Decimal | None:
    if any(value is None for value in values):
        return None
    defined = tuple(value for value in values if value is not None)
    if Decimal("Infinity") in defined and Decimal("-Infinity") in defined:
        return None
    return _mean(defined)


def _calibration(measurements: tuple[ComparativeMeasurement, ...], source: str, rule: Any) -> CalibrationResult:
    if rule.rule_id != "calibration-safeguard" or rule.rule_version != "2":
        _fail("Comparative Performance requires calibration-safeguard version 2")
    boundaries = _parameter(rule, "bin_boundaries")
    if boundaries != CALIBRATION_BOUNDARIES:
        _fail("Calibration rule boundaries conflict with canonical version 2")
    probability_name = f"{source}_probability"
    bins = []
    for index, (lower, upper) in enumerate(zip(boundaries, boundaries[1:])):
        values = tuple(item for item in measurements
                       if lower <= getattr(item, probability_name)
                       and (getattr(item, probability_name) <= upper if index == 9 else getattr(item, probability_name) < upper))
        if values:
            probabilities = tuple(getattr(item, probability_name) for item in values)
            predicted = _mean(probabilities)
            with localcontext() as context:
                context.prec = DECIMAL_PRECISION
                context.rounding = SCIENTIFIC_ROUNDING
                observed = Decimal(sum(item.realized_outcome for item in values)) / len(values)
                assert predicted is not None
                gap = observed - predicted
        else:
            predicted = observed = gap = None
        bins.append(CalibrationBin(lower, upper, index == 9, len(values), predicted, observed, gap))
    sample_size = len(measurements)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        wace = None if not sample_size else sum(
            (Decimal(item.count) / sample_size) * abs(item.calibration_gap)
            for item in bins if item.count and item.calibration_gap is not None
        )
    return CalibrationResult(rule.rule_specification_id, rule.rule_version, sample_size, tuple(bins), wace)


def _bootstrap(values: tuple[Decimal, ...], *, protocol_id: str, claim_id: str, domain_id: str,
               boundary: datetime, measurement_ids: tuple[str, ...], rule: Any) -> PairedUncertainty:
    confidence = _parameter(rule, "confidence_level")
    resamples = _parameter(rule, "resamples")
    point = _mean(values)
    if not values:
        return PairedUncertainty(None, 0, None, None, confidence, rule.rule_specification_id,
                                 rule.rule_version, resamples, COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION)
    seed = _digest((protocol_id, claim_id, domain_id, boundary, measurement_ids,
                    rule.rule_specification_id, COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION))
    samples = []
    for sample_index in range(resamples):
        selected = []
        for draw_index in range(len(values)):
            material = f"{seed}:{sample_index}:{draw_index}".encode()
            selected.append(values[int.from_bytes(hashlib.sha256(material).digest(), "big") % len(values)])
        samples.append(_mean(tuple(selected)))
    ordered = tuple(sorted(item for item in samples if item is not None))
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = SCIENTIFIC_ROUNDING
        tail = (Decimal(1) - confidence) / Decimal(2)
        lower_index = int((tail * (resamples - 1)).to_integral_value(rounding=ROUND_FLOOR))
        upper_index = int(((Decimal(1) - tail) * (resamples - 1)).to_integral_value(rounding=ROUND_CEILING))
    return PairedUncertainty(point, len(values), ordered[lower_index], ordered[upper_index], confidence,
                             rule.rule_specification_id, rule.rule_version, resamples,
                             COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION)


def _domain_matches(domain: ResearchDomain, classifications: tuple[SnapshotDimensionClassification, ...]) -> bool:
    available = {(item.approved_dimension_id, item.partition_key) for item in classifications}
    return all((item.approved_dimension_id, item.partition_key) in available for item in domain.partition_selections)


def create_comparative_performance(*, protocol: ResearchProtocol, edge_claim: EdgeClaim,
                                   research_domain: ResearchDomain, analysis_boundary: datetime,
                                   opportunities: Iterable[ResearchCaptureOpportunity],
                                   eligibility_contexts: Iterable[ResearchEventEligibilityContext],
                                   eligibility_results: Iterable[PopulationEligibilityResult],
                                   snapshots: Iterable[ResearchSnapshot], measurements: Iterable[ComparativeMeasurement],
                                   outcome_histories: Iterable[OutcomeHistory],
                                   provenance: ResearchContractProvenance,
                                   limitations: tuple[str, ...] = ()) -> ComparativePerformance:
    _require_aware(analysis_boundary, "analysis_boundary")
    if (edge_claim.protocol_id, edge_claim.benchmark_source_reference_id,
        edge_claim.research_domain_id) != (protocol.research_protocol_id,
                                            protocol.market_benchmark.probability_source_reference_id,
                                            research_domain.research_domain_id):
        _fail("Edge Claim is incompatible with Comparative Performance")
    challenger_id = edge_claim.challenger_source_reference_id
    if challenger_id not in {item.probability_source_reference_id for item in protocol.alternative_sources}:
        _fail("Edge Claim challenger is not Protocol-authorized")
    opportunity_values = tuple(item for item in opportunities if item.protocol_id == protocol.research_protocol_id)
    opportunity_ids = {item.research_capture_opportunity_id for item in opportunity_values}
    authoritative_provider = _parameter(protocol.outcome_resolution_rule, "source_id")
    history_values = tuple(outcome_histories)
    schedule_observations: dict[str, OutcomeObservation] = {}
    for history in history_values:
        if history.authoritative_provider_id != authoritative_provider:
            continue
        for observation in history.observations:
            prior = schedule_observations.get(observation.observation_id)
            if prior is not None and prior != observation:
                _fail("same Schedule Evidence identity has conflicting content")
            schedule_observations[observation.observation_id] = observation
    unknown_schedule_ids = {item.schedule_observation_id for item in opportunity_values} - set(schedule_observations)
    if unknown_schedule_ids:
        _fail("capture opportunity lacks Protocol-authoritative Schedule Evidence")
    applicable_opportunity_ids = {
        item.research_capture_opportunity_id for item in opportunity_values
        if schedule_observations[item.schedule_observation_id].collected_at <= analysis_boundary
    }
    context_values = tuple(item for item in eligibility_contexts
                           if item.protocol_id == protocol.research_protocol_id
                           and item.analysis_boundary == analysis_boundary)
    if len(context_values) != len({item.research_capture_opportunity_id for item in context_values}):
        _fail("Comparative Performance requires exactly one eligibility context per opportunity")
    context_opportunity_ids = {item.research_capture_opportunity_id for item in context_values}
    if context_opportunity_ids != applicable_opportunity_ids:
        _fail("eligibility contexts do not completely enumerate boundary-applicable opportunities")
    result_values = tuple(item for item in eligibility_results
                          if item.protocol_id == protocol.research_protocol_id
                          and item.analysis_boundary == analysis_boundary)
    if len(result_values) != len({item.research_capture_opportunity_id for item in result_values}):
        _fail("Comparative Performance requires exactly one eligibility result per opportunity")
    by_opportunity = _registry(result_values, "Population Eligibility Result", lambda item: item.research_capture_opportunity_id)
    if set(by_opportunity) != applicable_opportunity_ids:
        _fail("eligibility results do not completely enumerate boundary-applicable opportunities")
    contexts_by_opportunity = {item.research_capture_opportunity_id: item for item in context_values}
    opportunities_by_id = {item.research_capture_opportunity_id: item for item in opportunity_values}
    for opportunity_id, result in by_opportunity.items():
        if result.validation_status is not PopulationEligibilityValidationStatus.VALID:
            _fail("invalid Population Eligibility Result cannot become Coverage authority")
        context = contexts_by_opportunity[opportunity_id]
        if result.research_event_eligibility_context_id != context.research_event_eligibility_context_id:
            _fail("Population Eligibility Result references the wrong eligibility context")
        if evaluate_population_eligibility(
                protocol=protocol, opportunity=opportunities_by_id[opportunity_id],
                context=context, provenance=result.provenance) != result:
            _fail("Population Eligibility Result does not reproduce from governing rules")
    eligible_opportunity_ids = {identity for identity, result in by_opportunity.items()
                                if result.disposition is PopulationEligibilityDisposition.ELIGIBLE}
    excluded_opportunity_ids = set(by_opportunity) - eligible_opportunity_ids
    all_selected = select_authoritative_research_snapshots(snapshots, analysis_boundary)
    all_selected = tuple(item for item in all_selected
                     if item.protocol_id == protocol.research_protocol_id
                     and _domain_matches(research_domain, item.dimension_classifications))
    selected = tuple(item for item in all_selected
                     if item.research_capture_opportunity_id in eligible_opportunity_ids)
    selected_by_id = {item.research_snapshot_id: item for item in selected}
    population = tuple(sorted((item for item in measurements
        if item.protocol_id == protocol.research_protocol_id
        and item.benchmark_source_reference_id == edge_claim.benchmark_source_reference_id
        and item.challenger_source_reference_id == challenger_id
        and item.effective_at <= analysis_boundary
        and item.research_snapshot_id in selected_by_id
        and _domain_matches(research_domain, item.dimension_classifications)),
        key=lambda item: item.comparative_measurement_id))
    benchmark_id = protocol.market_benchmark.probability_source_reference_id
    eligible_snapshots = selected
    def capture(snapshot: ResearchSnapshot, source_id: str) -> SourceCapture | None:
        return next((item for item in snapshot.source_captures if item.probability_source_reference_id == source_id), None)
    def pair(snapshot: ResearchSnapshot) -> PairwiseSynchronization | None:
        return next((item for item in snapshot.pairwise_synchronization if item.challenger_source_reference_id == challenger_id), None)
    benchmark_available = tuple(item.research_snapshot_id for item in eligible_snapshots
                                if capture(item, benchmark_id) is not None and capture(item, benchmark_id).disposition is SourceCaptureDisposition.CAPTURED_VALID)
    challenger_available = tuple(item.research_snapshot_id for item in eligible_snapshots
                                 if capture(item, challenger_id) is not None and capture(item, challenger_id).disposition is SourceCaptureDisposition.CAPTURED_VALID)
    synchronized = tuple(item.research_snapshot_id for item in eligible_snapshots if pair(item) is not None and pair(item).synchronized)
    unsynchronized = tuple(item.research_snapshot_id for item in eligible_snapshots if pair(item) is not None and not pair(item).synchronized)
    timing = tuple(item.research_snapshot_id for item in selected if any(
        capture.disposition is SourceCaptureDisposition.OUTSIDE_CAPTURE_TOLERANCE for capture in item.source_captures))
    resolved_events = {history.canonical_event_id for history in history_values
                       if any(item.authoritative_final and item.collected_at <= analysis_boundary
                              for item in history.observations)}
    resolved_snapshot_ids = tuple(item.research_snapshot_id for item in eligible_snapshots
                                  if item.canonical_event_id in resolved_events)
    measurement_snapshot_ids = {item.research_snapshot_id for item in population}
    excluded_snapshot_ids = tuple(item.research_snapshot_id for item in all_selected
                                  if item.research_capture_opportunity_id in excluded_opportunity_ids)
    applicable_result_ids = tuple(result.population_eligibility_result_id for result in by_opportunity.values())
    eligible_result_ids = tuple(by_opportunity[item].population_eligibility_result_id
                                for item in eligible_opportunity_ids)
    excluded_result_ids = tuple(by_opportunity[item].population_eligibility_result_id
                                for item in excluded_opportunity_ids)
    coverage = ComparativeCoverage(
        applicable_result_ids, eligible_result_ids, excluded_result_ids,
        tuple(sorted(eligible_opportunity_ids)),
        tuple(item.research_snapshot_id for item in all_selected),
        tuple(item.research_snapshot_id for item in selected if item.research_snapshot_id not in benchmark_available),
        tuple(item.research_snapshot_id for item in selected if item.research_snapshot_id not in challenger_available),
        timing, tuple(item.research_snapshot_id for item in eligible_snapshots), benchmark_available,
        challenger_available, synchronized, unsynchronized, resolved_snapshot_ids,
        tuple(sorted(excluded_opportunity_ids)), excluded_snapshot_ids,
        tuple(item.comparative_measurement_id for item in population),
    )
    b_brier = _mean(tuple(item.benchmark_brier_score for item in population))
    c_brier = _mean(tuple(item.challenger_brier_score for item in population))
    improvements = tuple(item.brier_improvement for item in population)
    mean_improvement = _mean(improvements)
    b_log = _mean(tuple(item.benchmark_log_loss for item in population))
    c_log = _mean(tuple(item.challenger_log_loss for item in population))
    log_improvements = tuple(item.log_loss_improvement for item in population)
    mean_log = _mean_log_loss_improvement(log_improvements)
    statistical = protocol.statistical_method_rule
    if statistical.rule_id != "paired-bootstrap" or statistical.rule_version != "1":
        _fail("unsupported Comparative Performance statistical method")
    calibration_rules = tuple(item for item in protocol.supporting_measure_rules if item.rule_id == "calibration-safeguard")
    if len(calibration_rules) != 1:
        _fail("Protocol requires exactly one Calibration safeguard")
    uncertainty = _bootstrap(improvements, protocol_id=protocol.research_protocol_id,
                             claim_id=edge_claim.edge_claim_id, domain_id=research_domain.research_domain_id,
                             boundary=analysis_boundary, measurement_ids=coverage.comparative_measurement_ids,
                             rule=statistical)
    practical = _parameter(protocol.practical_significance_rule, "minimum_improvement")
    values = dict(
        schema_version=COMPARATIVE_RESEARCH_SCHEMA_VERSION,
        identity_algorithm_version=COMPARATIVE_RESEARCH_IDENTITY_VERSION,
        analysis_algorithm_version=COMPARATIVE_PERFORMANCE_ALGORITHM_VERSION,
        protocol_id=protocol.research_protocol_id, edge_claim_id=edge_claim.edge_claim_id,
        research_domain_id=research_domain.research_domain_id, analysis_boundary=analysis_boundary,
        benchmark_source_reference_id=benchmark_id, challenger_source_reference_id=challenger_id,
        comparative_measurement_ids=coverage.comparative_measurement_ids, coverage=coverage,
        paired_sample_size=len(population), benchmark_mean_brier_score=b_brier,
        challenger_mean_brier_score=c_brier, mean_paired_brier_improvement=mean_improvement,
        primary_uncertainty=uncertainty, practical_significance_threshold=practical,
        benchmark_mean_log_loss=b_log, challenger_mean_log_loss=c_log,
        mean_log_loss_improvement=mean_log,
        benchmark_calibration=_calibration(population, "benchmark", calibration_rules[0]),
        challenger_calibration=_calibration(population, "challenger", calibration_rules[0]),
        limitations=_unique(limitations, "Comparative Performance limitations"), provenance=provenance,
    )
    material = tuple(values[field.name] for field in fields(ComparativePerformance)
                     if field.name not in ("comparative_performance_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return ComparativePerformance(f"comparative-performance:{digest}", **values, input_digest=digest)


def _registry(values: Iterable[Any], label: str, key) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in values:
        identity = key(item)
        if identity in result and result[identity] != item:
            _fail(f"same {label} ID has conflicting content", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        result[identity] = item
    return result


def _eligibility_registry(values: Iterable[Any], label: str, key) -> dict[str, Any]:
    """Build an eligibility registry while preserving exactly-one cardinality."""
    supplied = tuple(values)
    seen: dict[str, Any] = {}
    for item in supplied:
        identity = key(item)
        if identity in seen:
            if seen[identity] != item:
                _fail(f"same {label} ID has conflicting content",
                      ReasonCode.CONFLICTING_NATIVE_IDENTITY)
            _fail(f"duplicate {label} artifact violates exactly-one cardinality",
                  ReasonCode.CONTRADICTORY_LINEAGE)
        seen[identity] = item
    return seen


def validate_comparative_research_contracts(*, protocols: Iterable[ResearchProtocol],
                                            claims: Iterable[EdgeClaim],
                                            canonical_events: Iterable[CanonicalEvent],
                                            event_stage_evidence: Iterable[EventStageEvidence],
                                            schedule_observations: Iterable[OutcomeObservation],
                                            outcome_histories: Iterable[OutcomeHistory],
                                            opportunities: Iterable[ResearchCaptureOpportunity],
                                            eligibility_contexts: Iterable[ResearchEventEligibilityContext],
                                            eligibility_results: Iterable[PopulationEligibilityResult],
                                            snapshots: Iterable[ResearchSnapshot],
                                            forecast_observations: Iterable[ForecastObservation],
                                            forecast_evaluations: Iterable[ForecastEvaluation],
                                            outcome_observations: Iterable[OutcomeObservation],
                                            measurements: Iterable[ComparativeMeasurement],
                                            performances: Iterable[ComparativePerformance]) -> None:
    protocol_map = _registry(protocols, "Research Protocol", lambda item: item.research_protocol_id)
    claim_map = _registry(claims, "Edge Claim", lambda item: item.edge_claim_id)
    event_map = _registry(canonical_events, "Canonical Event", lambda item: item.canonical_event_id)
    stage_map = _registry(event_stage_evidence, "event-stage Evidence", lambda item: item.event_stage_evidence_id)
    schedule_map = _registry(schedule_observations, "schedule observation", lambda item: item.observation_id)
    history_map = _registry(outcome_histories, "Outcome History", lambda item: item.canonical_event_id)
    opportunity_map = _registry(opportunities, "capture opportunity", lambda item: item.research_capture_opportunity_id)
    context_map = _eligibility_registry(
        eligibility_contexts, "eligibility context",
        lambda item: item.research_event_eligibility_context_id)
    eligibility_map = _eligibility_registry(
        eligibility_results, "Population Eligibility Result",
        lambda item: item.population_eligibility_result_id)
    snapshot_values = tuple(snapshots)
    snapshot_map = _registry(snapshot_values, "Research Snapshot", lambda item: item.research_snapshot_id)
    forecast_map = _registry(forecast_observations, "Forecast Observation", lambda item: item.observation_id)
    evaluation_map = _registry(forecast_evaluations, "Forecast Evaluation", lambda item: item.evaluation_id)
    outcome_map = _registry(outcome_observations, "Outcome Observation", lambda item: item.observation_id)
    measurement_map = _registry(measurements, "Comparative Measurement", lambda item: item.comparative_measurement_id)
    performance_map = _registry(performances, "Comparative Performance", lambda item: item.comparative_performance_id)
    for opportunity in opportunity_map.values():
        protocol = protocol_map.get(opportunity.protocol_id)
        schedule = schedule_map.get(opportunity.schedule_observation_id)
        if protocol is None or schedule is None:
            _fail("capture opportunity references unknown Protocol or schedule Evidence")
        if opportunity.proposition_type != protocol.research_population.proposition_type:
            _fail("capture opportunity proposition conflicts with Protocol")
        source_id = _parameter(protocol.outcome_resolution_rule, "source_id")
        if schedule.authoritative_provider_id != source_id:
            _fail("schedule Evidence is not from the Protocol-authoritative provider")
    for context in context_map.values():
        protocol = protocol_map.get(context.protocol_id)
        opportunity = opportunity_map.get(context.research_capture_opportunity_id)
        event = event_map.get(context.canonical_event_id)
        stage = stage_map.get(context.event_stage_evidence_id)
        history = history_map.get(context.canonical_event_id)
        if None in (protocol, opportunity, event, stage, history):
            _fail("eligibility context references unknown authoritative Evidence")
        assert protocol is not None and opportunity is not None and event is not None and stage is not None and history is not None
        recreated = ResearchEventEligibilityContext.create(
            opportunity=opportunity, protocol=protocol, canonical_event=event,
            stage_evidence=stage, outcome_history=history,
            analysis_boundary=context.analysis_boundary)
        if recreated != context:
            _fail("eligibility context does not reproduce from authoritative Evidence")
    for result in eligibility_map.values():
        context = context_map.get(result.research_event_eligibility_context_id)
        protocol = protocol_map.get(result.protocol_id)
        opportunity = opportunity_map.get(result.research_capture_opportunity_id)
        if None in (context, protocol, opportunity):
            _fail("Population Eligibility Result references unknown input")
        assert context is not None and protocol is not None and opportunity is not None
        if evaluate_population_eligibility(protocol=protocol, opportunity=opportunity, context=context,
                                           provenance=result.provenance) != result:
            _fail("Population Eligibility Result does not reproduce from governing rules")
    for snapshot in snapshot_map.values():
        protocol = protocol_map.get(snapshot.protocol_id)
        opportunity = opportunity_map.get(snapshot.research_capture_opportunity_id)
        if protocol is None or opportunity is None or opportunity.protocol_id != snapshot.protocol_id:
            _fail("Snapshot references incompatible Protocol or opportunity")
        schedule = schedule_map[opportunity.schedule_observation_id]
        if snapshot.canonical_event_id != schedule.canonical_event_id or snapshot.proposition_type != opportunity.proposition_type:
            _fail("Snapshot interpretation conflicts with schedule Evidence")
        if snapshot.scheduled_start != schedule.scheduled_start:
            _fail("Snapshot scheduled start conflicts with schedule Evidence")
        offset = _parameter(protocol.snapshot_timing_rule, "seconds_before_start")
        if snapshot.target_capture_at != snapshot.scheduled_start - timedelta(seconds=offset):
            _fail("Snapshot target capture time conflicts with Protocol")
        authorized = {protocol.market_benchmark.probability_source_reference_id,
                      *(item.probability_source_reference_id for item in protocol.alternative_sources)}
        captures = {item.probability_source_reference_id: item for item in snapshot.source_captures}
        if set(captures) != authorized:
            _fail("Snapshot must preserve one capture result for every Protocol source")
        maximum_tolerance = _parameter(protocol.capture_tolerance_rule, "seconds")
        for capture in captures.values():
            if capture.observed_at is not None:
                outside = _outside_capture_tolerance(
                    capture.observed_at, snapshot.target_capture_at, maximum_tolerance)
                if outside != (capture.disposition is SourceCaptureDisposition.OUTSIDE_CAPTURE_TOLERANCE):
                    _fail("source capture disposition conflicts with Protocol tolerance")
            if capture.disposition is not SourceCaptureDisposition.MISSING:
                observation = forecast_map.get(capture.forecast_observation_id or "")
                source = next((item for item in (protocol.market_benchmark,) + protocol.alternative_sources
                               if item.probability_source_reference_id == capture.probability_source_reference_id), None)
                if observation is None or source is None:
                    _fail("source capture references unknown Forecast Evidence")
                if (observation.provenance.provider, observation.version_id,
                    observation.distribution.canonical_event_id, observation.collected_at) != (
                        source.provider_id, source.model_or_product_version,
                        snapshot.canonical_event_id, capture.observed_at):
                    _fail("Forecast Observation lineage conflicts with Snapshot source capture")
                if observation.schedule_observation_id != opportunity.schedule_observation_id:
                    _fail("Forecast Observation schedule lineage conflicts with capture opportunity")
                valid_observation = (observation.validation_status is ForecastValidationStatus.VALID
                                     and observation.reconciliation.outcome is ReconciliationOutcome.MATCHED)
                if (capture.disposition is SourceCaptureDisposition.CAPTURED_INVALID) == valid_observation:
                    _fail("capture disposition conflicts with Forecast Observation validation")
        expected_challengers = {item.probability_source_reference_id for item in protocol.alternative_sources}
        if {item.challenger_source_reference_id for item in snapshot.pairwise_synchronization} != expected_challengers:
            _fail("Snapshot requires independent synchronization for every challenger")
        for pair in snapshot.pairwise_synchronization:
            if pair.benchmark_source_reference_id != protocol.market_benchmark.probability_source_reference_id:
                _fail("Snapshot synchronization benchmark conflicts with Protocol")
            if (pair.synchronization_rule_id, pair.synchronization_rule_version) != (
                    protocol.synchronization_rule.rule_id, protocol.synchronization_rule.rule_version):
                _fail("Snapshot synchronization rule conflicts with Protocol")
            expected_pair = create_pairwise_synchronization(
                benchmark_capture=captures[pair.benchmark_source_reference_id],
                challenger_capture=captures[pair.challenger_source_reference_id],
                synchronization_rule=protocol.synchronization_rule)
            if pair != expected_pair:
                _fail("Snapshot synchronization does not derive from authoritative capture timestamps")
        dimensions = {item.approved_dimension_id: item for item in protocol.approved_dimensions}
        if {item.approved_dimension_id for item in snapshot.dimension_classifications} != set(dimensions):
            _fail("Snapshot must classify every approved Research Dimension exactly once")
        for classification in snapshot.dimension_classifications:
            dimension = dimensions.get(classification.approved_dimension_id)
            if dimension is None or classification.partition_key not in {item.partition_key for item in dimension.partitions}:
                _fail("Snapshot uses unauthorized Research Dimension partition")
            if (classification.classification_rule_id, classification.classification_rule_version) != (
                    dimension.classification_rule.rule_id, dimension.classification_rule.rule_version):
                _fail("Snapshot classification rule conflicts with Protocol")
        if snapshot.supersedes_snapshot_id is not None:
            prior = snapshot_map.get(snapshot.supersedes_snapshot_id)
            if prior is None:
                _fail("Snapshot correction references unknown predecessor", ReasonCode.CONTRADICTORY_LINEAGE)
            if (prior.research_capture_opportunity_id, prior.protocol_id, prior.target_capture_at,
                prior.capture_started_at, prior.capture_completed_at) != (
                    snapshot.research_capture_opportunity_id, snapshot.protocol_id, snapshot.target_capture_at,
                    snapshot.capture_started_at, snapshot.capture_completed_at):
                _fail("Snapshot correction changes scientific capture state")
            old = {item.probability_source_reference_id: item for item in prior.source_captures}
            new = {item.probability_source_reference_id: item for item in snapshot.source_captures}
            for key in old:
                if old[key].disposition is SourceCaptureDisposition.MISSING and new[key].disposition is not SourceCaptureDisposition.MISSING:
                    observation = forecast_map.get(new[key].forecast_observation_id or "")
                    if observation is None or observation.collected_at > prior.capture_completed_at:
                        _fail("Snapshot correction cannot reconstruct prospectively missing Evidence")
                elif old[key].forecast_observation_id != new[key].forecast_observation_id or old[key].observed_at != new[key].observed_at:
                    _fail("Snapshot correction substitutes later Forecast Evidence")
    # Every historical boundary induced by an effective_at must replay unambiguously.
    for boundary in sorted({item.effective_at for item in snapshot_values}):
        select_authoritative_research_snapshots(snapshot_values, boundary)
    for measurement in measurement_map.values():
        protocol = protocol_map.get(measurement.protocol_id)
        snapshot = snapshot_map.get(measurement.research_snapshot_id)
        benchmark = evaluation_map.get(measurement.benchmark_evaluation_id)
        challenger = evaluation_map.get(measurement.challenger_evaluation_id)
        outcome = outcome_map.get(measurement.outcome_observation_id)
        if None in (protocol, snapshot, benchmark, challenger, outcome):
            _fail("Comparative Measurement references unknown authoritative input")
        assert protocol is not None and snapshot is not None and benchmark is not None and challenger is not None and outcome is not None
        captures = {item.probability_source_reference_id: item for item in snapshot.source_captures}
        sources = {protocol.market_benchmark.probability_source_reference_id: protocol.market_benchmark,
                   **{item.probability_source_reference_id: item for item in protocol.alternative_sources}}
        for source_id, evaluation in ((measurement.benchmark_source_reference_id, benchmark),
                                      (measurement.challenger_source_reference_id, challenger)):
            capture = captures.get(source_id)
            observation = forecast_map.get(evaluation.forecast_observation_id)
            source = sources.get(source_id)
            if capture is None or observation is None or source is None or capture.forecast_observation_id != observation.observation_id:
                _fail("Forecast Evaluation does not reference exact Snapshot Forecast Evidence")
            authoritative_distribution = tuple(sorted(
                (item.outcome.outcome_id, item.probability) for item in observation.distribution.probabilities))
            if (tuple(sorted(evaluation.probability_distribution)) != authoritative_distribution
                    or evaluation.forecast_collected_at != observation.collected_at
                    or (evaluation.provider_id, evaluation.model_id, evaluation.model_version_id) != (
                        source.provider_id, source.model_or_product_id, source.model_or_product_version)):
                _fail("Forecast Evaluation lineage conflicts with authoritative Forecast Observation")
        recreated = create_comparative_measurement(protocol=protocol, snapshot=snapshot,
            benchmark_evaluation=benchmark, challenger_evaluation=challenger, outcome=outcome,
            effective_at=measurement.effective_at, provenance=measurement.provenance,
            limitations=measurement.limitations)
        if recreated != measurement:
            _fail("Comparative Measurement does not reproduce from authoritative inputs")
    for performance in performance_map.values():
        protocol = protocol_map.get(performance.protocol_id)
        claim = claim_map.get(performance.edge_claim_id)
        if protocol is None or claim is None:
            _fail("Comparative Performance references unknown Protocol or Edge Claim")
        domain = next((item for item in protocol.research_domains if item.research_domain_id == performance.research_domain_id), None)
        if domain is None:
            _fail("Comparative Performance references unauthorized Research Domain")
        referenced = tuple(measurement_map[item] for item in performance.comparative_measurement_ids)
        if any(item.effective_at > performance.analysis_boundary for item in referenced):
            _fail("Comparative Performance includes future Measurement")
        recreated = create_comparative_performance(
            protocol=protocol, edge_claim=claim, research_domain=domain,
            analysis_boundary=performance.analysis_boundary,
            opportunities=opportunity_map.values(), eligibility_contexts=context_map.values(),
            eligibility_results=eligibility_map.values(), snapshots=snapshot_map.values(),
            measurements=measurement_map.values(), outcome_histories=history_map.values(),
            provenance=performance.provenance,
            limitations=performance.limitations,
        )
        if recreated != performance:
            _fail("Comparative Performance does not reproduce from authoritative inputs")


_CONTRACTS = (
    EventStageEvidence, EligibilityHistoryState, ResearchEventEligibilityContext, PopulationEligibilityResult,
    ResearchCaptureOpportunity, SourceCapture, PairwiseSynchronization, SnapshotDimensionClassification,
    ResearchSnapshot, ComparativeMeasurement, CalibrationBin, CalibrationResult, PairedUncertainty,
    ComparativeCoverage, ComparativePerformance,
)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(EventPhase, PopulationEligibilityDisposition,
                             PopulationEligibilityValidationStatus,
                             SourceCaptureDisposition, SnapshotValidationStatus))
