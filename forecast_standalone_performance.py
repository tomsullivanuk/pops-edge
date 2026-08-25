"""PR16B standalone Probability Source Measurement and performance contracts.

All contracts in this module are explicit successors or new authorities.  They
never mutate PR9/PR13/PR14/PR15 artifacts and perform no provider I/O.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from enum import Enum
from typing import Any, Iterable, Mapping

from event_contracts import ContractError, ReasonCode, SerializableContract, _register, _require_aware, _require_identifier
from forecast_evaluation import (ForecastEvaluation,EvaluationEligibilityDecision,
    EVALUATION_ALGORITHM_ID,EVALUATION_ALGORITHM_VERSION,create_forecast_evaluation,
    decide_evaluation_eligibility)
from forecast_research_contracts import (
    ProbabilitySourceReference, ResearchContractProvenance, ResearchDomain,
    ResearchProtocol, RulePurpose, VersionedRuleSpecification, ProtocolClaimSet,EdgeClaim,DriftDisposition,
)
from forecast_comparative_research import (
    CALIBRATION_BOUNDARIES, CalibrationBin, CalibrationResult,PairedUncertainty,
    PairwiseSynchronization, ResearchCaptureOpportunity, ResearchEventEligibilityContext,
    PopulationEligibilityDisposition, evaluate_population_eligibility,
    SnapshotDimensionClassification, SnapshotValidationStatus,
)
from market_contracts import MarketObservation, MarketSide, PriceEvidenceKind, ProviderMarketSeries
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus
from forecast_comparative_reporting import DriftUncertainty


SCHEMA_VERSION = "2"
IDENTITY_VERSION = "1"
SNAPSHOT_ALGORITHM_VERSION = "2"
DERIVATION_ALGORITHM_VERSION = "1"
MEASUREMENT_ALGORITHM_VERSION = "2"
COMPARATIVE_MEASUREMENT_ALGORITHM_VERSION = "2"
PERFORMANCE_ALGORITHM_VERSION = "2"
TIME_BOUNDED_PERFORMANCE_ALGORITHM_VERSION = "2"
REPORT_CONTRACT_VERSION = "2"
REPORT_ALGORITHM_VERSION = "2"
PRECISION = 50


def _fail(detail: str, code: ReasonCode = ReasonCode.VALIDATION_FAILURE) -> None:
    raise ContractError(code, detail)


def _utc(value: datetime) -> str:
    _require_aware(value, "scientific datetime")
    return value.astimezone(timezone.utc).isoformat()


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime): return {"datetime_utc": _utc(value)}
    if isinstance(value, Decimal):
        if value.is_nan(): _fail("NaN is not scientific material")
        return {"decimal": str(value)}
    if isinstance(value, Enum): return value.value
    if is_dataclass(value): return {item.name: _canonical(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, (tuple, list)): return [_canonical(item) for item in value]
    if isinstance(value, Mapping): return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, float): _fail("binary float cannot participate in scientific identity")
    if value is None or isinstance(value, (str, int, bool)): return value
    raise TypeError(type(value).__name__)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _unique(values: Iterable[Any], label: str, key=lambda item: item) -> tuple[Any, ...]:
    supplied = tuple(values); keys = tuple(key(item) for item in supplied)
    if len(keys) != len(set(keys)): _fail(f"{label} contains duplicates")
    return tuple(item for _, item in sorted(zip(keys, supplied), key=lambda pair: pair[0]))


def _parameter(rule: VersionedRuleSpecification, name: str) -> Any:
    values = {item.name: item.value for item in rule.parameters}
    if name not in values: _fail(f"rule lacks {name}")
    return values[name]


def _broad(protocol: "ResearchProtocolV2") -> ResearchDomain:
    domains = tuple(item for item in protocol.base_protocol.research_domains if not item.partition_selections)
    if len(domains) != 1: _fail("PR16B requires exactly one broad Research Domain")
    return domains[0]


@dataclass(frozen=True, slots=True)
class ResearchProtocolV2:
    research_protocol_id: str
    schema_version: str
    identity_algorithm_version: str
    base_protocol: ResearchProtocol
    standalone_primary_measure_rule: VersionedRuleSpecification
    standalone_statistical_method_rule: VersionedRuleSpecification
    input_digest: str

    @classmethod
    def create(cls, *, base_protocol: ResearchProtocol,
               standalone_primary_measure_rule: VersionedRuleSpecification,
               standalone_statistical_method_rule: VersionedRuleSpecification) -> "ResearchProtocolV2":
        material = (SCHEMA_VERSION, IDENTITY_VERSION, base_protocol.research_protocol_id,
                    standalone_primary_measure_rule, standalone_statistical_method_rule)
        digest = _digest(material)
        return cls(f"research-protocol-v2:{digest}", SCHEMA_VERSION, IDENTITY_VERSION,
                   base_protocol, standalone_primary_measure_rule,
                   standalone_statistical_method_rule, digest)

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.identity_algorithm_version != IDENTITY_VERSION:
            _fail("unsupported Research Protocol v2 version")
        primary = self.standalone_primary_measure_rule
        statistical = self.standalone_statistical_method_rule
        if (primary.purpose, primary.rule_id, primary.rule_version) != (
                RulePurpose.STANDALONE_PRIMARY_MEASURE, "mean-brier-score", "1"):
            _fail("Protocol v2 requires mean-brier-score v1 standalone primary rule")
        if (statistical.purpose, statistical.rule_id, statistical.rule_version) != (
                RulePurpose.STANDALONE_STATISTICAL_METHOD, "one-sample-brier-bootstrap", "1"):
            _fail("Protocol v2 requires one-sample-brier-bootstrap v1")
        confidence = _parameter(statistical, "confidence_level")
        if confidence <= 0 or confidence >= 1: _fail("standalone confidence level must be in (0,1)")
        _broad(self)
        benchmark = self.base_protocol.market_benchmark
        if (benchmark.probability_representation_rule.rule_id,
                benchmark.probability_representation_rule.rule_version) != ("positive-depth-two-sided-quote", "1"):
            _fail("Protocol v2 Market Benchmark requires positive-depth-two-sided-quote v1")
        if (benchmark.transformation_rule.rule_id, benchmark.transformation_rule.rule_version) != (
                "bid-offer-midpoint-complement", "1"):
            _fail("Protocol v2 Market Benchmark requires midpoint-complement v1")
        digest = _digest((self.schema_version, self.identity_algorithm_version,
                          self.base_protocol.research_protocol_id, primary, statistical))
        if self.input_digest != digest or self.research_protocol_id != f"research-protocol-v2:{digest}":
            _fail("Research Protocol v2 identity conflict", ReasonCode.CONFLICTING_NATIVE_IDENTITY)

    @property
    def market_benchmark(self): return self.base_protocol.market_benchmark
    @property
    def alternative_sources(self): return self.base_protocol.alternative_sources
    @property
    def capture_tolerance_rule(self): return self.base_protocol.capture_tolerance_rule
    @property
    def synchronization_rule(self): return self.base_protocol.synchronization_rule
    @property
    def supporting_measure_rules(self): return self.base_protocol.supporting_measure_rules
    @property
    def surveillance_window_rules(self): return self.base_protocol.surveillance_window_rules
    @property
    def research_population(self): return self.base_protocol.research_population
    @property
    def snapshot_timing_rule(self): return self.base_protocol.snapshot_timing_rule
    @property
    def outcome_resolution_rule(self): return self.base_protocol.outcome_resolution_rule


class SourceEvidenceKind(str, Enum):
    FORECAST_OBSERVATION = "forecast-observation"
    MARKET_OBSERVATION = "market-observation"


@dataclass(frozen=True, slots=True, order=True)
class SourceEvidenceReference:
    evidence_kind: SourceEvidenceKind
    evidence_id: str
    def __post_init__(self) -> None: _require_identifier(self.evidence_id, "source Evidence ID")


class SourceCaptureDispositionV2(str, Enum):
    MISSING = "missing"
    CAPTURED_VALID = "captured-valid"
    CAPTURED_INVALID = "captured-invalid"
    OUTSIDE_CAPTURE_TOLERANCE = "outside-capture-tolerance"


@dataclass(frozen=True, slots=True, order=True)
class SourceCaptureV2:
    probability_source_reference_id: str
    disposition: SourceCaptureDispositionV2
    evidence_reference: SourceEvidenceReference | None
    observed_at: datetime | None
    reasons: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        _require_identifier(self.probability_source_reference_id, "source reference")
        if self.disposition is SourceCaptureDispositionV2.MISSING:
            if self.evidence_reference is not None or self.observed_at is not None: _fail("missing capture cannot fabricate Evidence")
        else:
            if self.evidence_reference is None or self.observed_at is None: _fail("captured source requires typed Evidence and chronology")
            _require_aware(self.observed_at, "source observed_at")
        if (self.disposition is SourceCaptureDispositionV2.CAPTURED_VALID) == bool(self.reasons):
            _fail("capture reasons conflict with disposition")
        object.__setattr__(self, "reasons", _unique(self.reasons, "capture reasons"))


def validate_source_evidence_reference(reference: SourceEvidenceReference,
                                       *, forecast_observations: Iterable[Any] = (),
                                       market_observations: Iterable[MarketObservation] = ()) -> Any:
    registry_values = tuple(forecast_observations if reference.evidence_kind is SourceEvidenceKind.FORECAST_OBSERVATION else market_observations)
    attribute = "observation_id"
    matches = tuple(item for item in registry_values if getattr(item, attribute) == reference.evidence_id)
    if len(matches) != 1: _fail("typed Evidence reference must resolve exactly once")
    canonical = {getattr(item, attribute): item for item in registry_values}
    if len(canonical) != len(registry_values): _fail("Evidence registry contains duplicate or conflicting identity")
    return matches[0]


@dataclass(frozen=True, slots=True)
class ResearchSnapshotV2:
    research_snapshot_id: str; schema_version: str; identity_algorithm_version: str
    snapshot_algorithm_version: str; research_capture_opportunity_id: str; protocol_id: str
    effective_at: datetime; supersedes_snapshot_id: str | None; correction_reason: str | None
    canonical_event_id: str; proposition_type: str; canonical_proposition_outcome_id: str
    scheduled_start: datetime; target_capture_at: datetime; capture_started_at: datetime; capture_completed_at: datetime
    source_captures: tuple[SourceCaptureV2, ...]; pairwise_synchronization: tuple[PairwiseSynchronization, ...]
    dimension_classifications: tuple[SnapshotDimensionClassification, ...]
    validation_status: SnapshotValidationStatus; validation_reasons: tuple[str, ...]; limitations: tuple[str, ...]
    provenance: ResearchContractProvenance; input_digest: str

    @classmethod
    def create(cls, **kwargs: Any) -> "ResearchSnapshotV2":
        values = dict(kwargs); values.setdefault("schema_version", SCHEMA_VERSION); values.setdefault("identity_algorithm_version", IDENTITY_VERSION)
        values.setdefault("snapshot_algorithm_version", SNAPSHOT_ALGORITHM_VERSION)
        values["source_captures"] = _unique(values["source_captures"], "v2 captures", lambda item: item.probability_source_reference_id)
        values["pairwise_synchronization"] = _unique(values.get("pairwise_synchronization", ()), "v2 synchronization", lambda item: item.challenger_source_reference_id)
        values["dimension_classifications"] = _unique(values.get("dimension_classifications", ()), "v2 dimensions", lambda item: item.approved_dimension_id)
        values["validation_reasons"] = _unique(values.get("validation_reasons", ()), "v2 validation reasons")
        values["limitations"] = _unique(values.get("limitations", ()), "v2 limitations")
        material = tuple(values[name] for name in cls.__dataclass_fields__ if name not in ("research_snapshot_id", "provenance", "input_digest"))
        digest = _digest(material)
        return cls(research_snapshot_id=f"research-snapshot-v2:{digest}", **values, input_digest=digest)

    def __post_init__(self) -> None:
        for value in (self.effective_at, self.scheduled_start, self.target_capture_at, self.capture_started_at, self.capture_completed_at): _require_aware(value, "Snapshot v2 chronology")
        if not self.capture_started_at <= self.capture_completed_at: _fail("Snapshot v2 capture chronology is reversed")
        if self.effective_at<self.capture_completed_at:_fail("Snapshot v2 cannot be effective before capture completion")
        if (self.supersedes_snapshot_id is None) != (self.correction_reason is None):
            _fail("Snapshot v2 correction predecessor and reason must appear together")
        if self.correction_reason is not None:
            _require_identifier(self.supersedes_snapshot_id, "superseded Snapshot v2")
            if not self.correction_reason.strip(): _fail("Snapshot v2 correction reason cannot be empty")
        if self.schema_version != SCHEMA_VERSION or self.snapshot_algorithm_version != SNAPSHOT_ALGORITHM_VERSION: _fail("unsupported Snapshot generation")
        captures = _unique(self.source_captures, "v2 captures", lambda item: item.probability_source_reference_id)
        if any(item.observed_at is not None and not self.capture_started_at<=item.observed_at<=self.capture_completed_at for item in captures):
            _fail("source Evidence chronology falls outside Snapshot capture")
        if self.validation_status is SnapshotValidationStatus.VALID and self.validation_reasons: _fail("valid Snapshot v2 cannot carry validation reasons")
        if self.validation_status is SnapshotValidationStatus.INVALID and not self.validation_reasons: _fail("invalid Snapshot v2 requires reasons")
        material = tuple(getattr(self, name) for name in self.__dataclass_fields__ if name not in ("research_snapshot_id", "provenance", "input_digest"))
        digest = _digest(material)
        if self.input_digest != digest or self.research_snapshot_id != f"research-snapshot-v2:{digest}": _fail("Snapshot v2 identity conflict")
        object.__setattr__(self, "source_captures", captures)


_SNAPSHOT_CORRECTION_METADATA_FIELDS = frozenset((
    "research_snapshot_id", "effective_at", "supersedes_snapshot_id",
    "correction_reason", "provenance", "input_digest",
))


def validate_snapshot_lineages_v2(snapshots: Iterable[ResearchSnapshotV2]) -> None:
    """Validate complete, conservative append-only v2 Snapshot correction lineages."""
    supplied=tuple(snapshots);by_id={item.research_snapshot_id:item for item in supplied}
    if len(by_id)!=len(supplied):_fail("duplicate Snapshot v2 authority")
    children:dict[str,list[ResearchSnapshotV2]]={identity:[] for identity in by_id}
    for child in supplied:
        if child.supersedes_snapshot_id is None:continue
        parent=by_id.get(child.supersedes_snapshot_id)
        if parent is None:_fail("Snapshot v2 correction references unknown predecessor")
        children[parent.research_snapshot_id].append(child)
        if len(children[parent.research_snapshot_id])>1:_fail("Snapshot v2 lineage branches")
        common=("protocol_id","research_capture_opportunity_id","canonical_event_id",
                "proposition_type","canonical_proposition_outcome_id")
        if any(getattr(child,name)!=getattr(parent,name) for name in common):
            _fail("Snapshot v2 correction crosses immutable authority")
        if child.effective_at<=parent.effective_at:_fail("invalid Snapshot v2 correction chronology")
        changed={name for name in child.__dataclass_fields__
                 if getattr(child,name)!=getattr(parent,name)}
        if not changed<=_SNAPSHOT_CORRECTION_METADATA_FIELDS:
            _fail("Snapshot v2 correction rewrites immutable scientific capture history")
    by_opportunity:dict[tuple[str,str],list[ResearchSnapshotV2]]={}
    for item in supplied:by_opportunity.setdefault((item.protocol_id,item.research_capture_opportunity_id),[]).append(item)
    for values in by_opportunity.values():
        roots=tuple(item for item in values if item.supersedes_snapshot_id is None)
        if len(roots)!=1:_fail("Snapshot v2 lineage requires one root")
        seen=set();current=roots[0]
        while True:
            if current.research_snapshot_id in seen:_fail("Snapshot v2 lineage cycles")
            seen.add(current.research_snapshot_id)
            descendants=children[current.research_snapshot_id]
            if not descendants:break
            current=descendants[0]
        if len(seen)!=len(values):_fail("Snapshot v2 lineage is disconnected")


def select_authoritative_snapshots_v2(snapshots: Iterable[ResearchSnapshotV2], boundary: datetime) -> tuple[ResearchSnapshotV2, ...]:
    _require_aware(boundary, "Snapshot replay boundary")
    supplied=tuple(snapshots);validate_snapshot_lineages_v2(supplied)
    visible = tuple(item for item in supplied if item.effective_at <= boundary)
    by_id = {item.research_snapshot_id: item for item in visible}
    if len(by_id) != len(visible): _fail("duplicate Snapshot v2 authority")
    by_opportunity: dict[str, list[ResearchSnapshotV2]] = {}
    for item in visible: by_opportunity.setdefault(item.research_capture_opportunity_id, []).append(item)
    selected = []
    for values in by_opportunity.values():
        roots = tuple(item for item in values if item.supersedes_snapshot_id is None)
        if len(roots) != 1: _fail("Snapshot v2 lineage requires one root")
        current = roots[0]; seen = {current.research_snapshot_id}
        while True:
            children = tuple(item for item in values if item.supersedes_snapshot_id == current.research_snapshot_id)
            if len(children) > 1: _fail("Snapshot v2 lineage branches")
            if not children: break
            child = children[0]
            if child.effective_at <= current.effective_at or child.research_snapshot_id in seen: _fail("invalid Snapshot v2 correction chronology")
            seen.add(child.research_snapshot_id); current = child
        if len(seen) != len(values): _fail("Snapshot v2 lineage is disconnected")
        selected.append(current)
    return tuple(sorted(selected, key=lambda item: item.research_capture_opportunity_id))


class CaptureBoundaryDisposition(str, Enum):
    CAPTURE_NOT_YET_DUE = "capture-not-yet-due"
    PROTOCOL_INELIGIBLE = "protocol-ineligible"
    DUE_AND_ELIGIBLE = "due-and-prospectively-eligible"


@dataclass(frozen=True, slots=True)
class CaptureBoundaryEligibility:
    capture_boundary_eligibility_id: str; protocol_id: str; research_capture_opportunity_id: str
    eligibility_boundary: datetime; research_population_id: str; governing_rule_specification_ids: tuple[str, ...]
    context_evidence_ids: tuple[str, ...]; disposition: CaptureBoundaryDisposition; reason_codes: tuple[str, ...]
    provenance: ResearchContractProvenance; input_digest: str
    @classmethod
    def _create_derived(cls, *, protocol_id: str, opportunity_id: str, eligibility_boundary: datetime,
               research_population_id: str, governing_rule_specification_ids: tuple[str, ...],
               context_evidence_ids: tuple[str, ...], disposition: CaptureBoundaryDisposition,
               reason_codes: tuple[str, ...], provenance: ResearchContractProvenance) -> "CaptureBoundaryEligibility":
        rules = _unique(governing_rule_specification_ids, "capture eligibility rules"); context = _unique(context_evidence_ids, "capture context")
        reasons = _unique(reason_codes, "capture eligibility reasons")
        if disposition is CaptureBoundaryDisposition.DUE_AND_ELIGIBLE and reasons: _fail("eligible capture boundary cannot carry exclusion reasons")
        if disposition is not CaptureBoundaryDisposition.DUE_AND_ELIGIBLE and not reasons: _fail("noneligible capture boundary requires reasons")
        material = (protocol_id, opportunity_id, eligibility_boundary, research_population_id, rules, context, disposition, reasons)
        digest = _digest(material)
        return cls(f"capture-boundary-eligibility:{digest}", protocol_id, opportunity_id, eligibility_boundary,
                   research_population_id, rules, context, disposition, reasons, provenance, digest)
    def __post_init__(self) -> None:
        _require_aware(self.eligibility_boundary, "capture eligibility boundary")
        digest = _digest((self.protocol_id, self.research_capture_opportunity_id, self.eligibility_boundary,
                          self.research_population_id, self.governing_rule_specification_ids,
                          self.context_evidence_ids, self.disposition, self.reason_codes))
        if self.input_digest != digest or self.capture_boundary_eligibility_id != f"capture-boundary-eligibility:{digest}": _fail("capture eligibility identity conflict")


def evaluate_capture_boundary_eligibility(*,protocol:ResearchProtocolV2,
        opportunity:ResearchCaptureOpportunity,context:ResearchEventEligibilityContext,
        provenance:ResearchContractProvenance)->CaptureBoundaryEligibility:
    """Derive capture-time membership from complete prospective v1 population authority."""
    if opportunity.protocol_id!=protocol.research_protocol_id:_fail("capture opportunity conflicts with Protocol v2")
    base_opportunity=ResearchCaptureOpportunity.create(protocol.base_protocol.research_protocol_id,
        opportunity.schedule_observation_id,opportunity.proposition_type)
    if context.research_capture_opportunity_id!=base_opportunity.research_capture_opportunity_id or context.protocol_id!=protocol.base_protocol.research_protocol_id:
        _fail("capture eligibility context does not resolve the v2 opportunity through base population authority")
    if any(item.collected_at>context.analysis_boundary for item in context.history_states):
        _fail("capture eligibility context contains future Evidence")
    base_result=evaluate_population_eligibility(protocol=protocol.base_protocol,opportunity=base_opportunity,
        context=context,provenance=provenance)
    scheduled=next(item.scheduled_start for item in context.history_states
                   if item.observation_id==opportunity.schedule_observation_id)
    offset=_parameter(protocol.snapshot_timing_rule,"seconds_before_start")
    target=scheduled-timedelta(seconds=offset)
    if context.analysis_boundary!=target:_fail("prospective population eligibility must be evaluated exactly at the capture boundary")
    if base_result.disposition is PopulationEligibilityDisposition.EXCLUDED:
        disposition=CaptureBoundaryDisposition.PROTOCOL_INELIGIBLE;reasons=base_result.reason_codes
    else: disposition=CaptureBoundaryDisposition.DUE_AND_ELIGIBLE;reasons=()
    return CaptureBoundaryEligibility._create_derived(protocol_id=protocol.research_protocol_id,
        opportunity_id=opportunity.research_capture_opportunity_id,eligibility_boundary=context.analysis_boundary,
        research_population_id=protocol.research_population.research_population_id,
        governing_rule_specification_ids=base_result.governing_rule_specification_ids,
        context_evidence_ids=(context.research_event_eligibility_context_id,),disposition=disposition,
        reason_codes=reasons,provenance=provenance)


@dataclass(frozen=True, slots=True, order=True)
class MarketProbabilityLevel:
    canonical_price:Decimal;quantity:Decimal;acquisition_side:MarketSide;acquisition_price:Decimal;provider_book_side:MarketSide
    provider_price:Decimal;evidence_kind:PriceEvidenceKind;evidence_transformation:str|None;canonical_transformation:str|None;source_endpoint:str;collected_at:datetime
    def __post_init__(self):
        if self.quantity<=0 or not self.quantity.is_finite() or not self.canonical_price.is_finite() or not self.provider_price.is_finite():_fail("market supporting level requires positive finite material")
        _require_aware(self.collected_at,"market supporting level chronology")
        if self.evidence_kind is PriceEvidenceKind.DIRECT_ASK:
            if self.provider_book_side is not self.acquisition_side or self.provider_price!=self.acquisition_price or self.evidence_transformation is not None:_fail("direct supporting level provenance conflict")
        elif self.provider_book_side is self.acquisition_side or self.acquisition_price!=Decimal(1)-self.provider_price or not self.evidence_transformation:_fail("derived supporting level provenance conflict")


@dataclass(frozen=True, slots=True, order=True)
class MarketProbabilityBound:
    kind:str;canonical_price:Decimal;quantity:Decimal;collected_at:datetime
    contributing_levels:tuple[MarketProbabilityLevel,...]
    def __post_init__(self) -> None:
        if self.kind not in ("bid", "offer"): _fail("market bound kind is invalid")
        if any(not isinstance(value,Decimal) or not value.is_finite() for value in (self.canonical_price,self.quantity)):_fail("market bound requires finite Decimal")
        if not 0 <= self.canonical_price <= 1 or self.quantity <= 0: _fail("market bound price/depth invalid")
        _require_aware(self.collected_at, "market bound collected_at")
        levels=tuple(sorted(self.contributing_levels,key=lambda item:json.dumps(_canonical(item),sort_keys=True,separators=(",",":"))))
        if not levels or any(item.canonical_price!=self.canonical_price for item in levels) or sum((item.quantity for item in levels),Decimal(0))!=self.quantity:_fail("market bound does not reconcile complete contributing depth")
        if self.collected_at!=max(item.collected_at for item in levels):_fail("market bound chronology does not represent all contributing levels")
        if self.kind=="bid" and any(item.canonical_price!=Decimal(1)-item.acquisition_price or item.canonical_transformation!="canonical_bid = 1 - complementary_outcome_offer" for item in levels):_fail("canonical bid supporting transformation conflict")
        if self.kind=="offer" and any(item.canonical_price!=item.acquisition_price or item.canonical_transformation is not None for item in levels):_fail("canonical offer supporting transformation conflict")
        object.__setattr__(self,"contributing_levels",levels)


@dataclass(frozen=True, slots=True)
class MarketProbabilityDerivation:
    market_probability_derivation_id: str; schema_version: str; identity_algorithm_version: str
    derivation_algorithm_version: str; protocol_id: str; research_snapshot_id: str
    source_reference_id: str; market_observation_id: str; market_series_id: str
    canonical_event_id: str; proposition_id: str; canonical_outcome_id: str
    bid: MarketProbabilityBound; offer: MarketProbabilityBound; midpoint: Decimal
    complement_outcome_id: str; complement_probability: Decimal; probability_distribution: tuple[tuple[str, Decimal], ...]
    representation_rule_id: str; transformation_rule_id: str; effective_at: datetime
    limitations: tuple[str, ...]; provenance: ResearchContractProvenance; input_digest: str

    def __post_init__(self) -> None:
        _require_aware(self.effective_at, "derivation effective_at")
        if self.schema_version != SCHEMA_VERSION or self.derivation_algorithm_version != DERIVATION_ALGORITHM_VERSION: _fail("unsupported market derivation generation")
        if self.bid.canonical_price > self.offer.canonical_price: _fail("market probability interval is crossed")
        with localcontext() as context:
            context.prec = PRECISION; context.rounding = ROUND_HALF_EVEN
            midpoint = (self.bid.canonical_price + self.offer.canonical_price) / Decimal(2)
            complement = Decimal(1) - midpoint
        if self.midpoint != midpoint or self.complement_probability != complement: _fail("midpoint arithmetic conflict")
        if tuple(sorted(self.probability_distribution)) != tuple(sorted(((self.canonical_outcome_id, midpoint), (self.complement_outcome_id, complement)))): _fail("market distribution conflict")
        material = tuple(getattr(self, name) for name in self.__dataclass_fields__ if name not in ("market_probability_derivation_id", "provenance", "input_digest", "limitations")) + (_unique(self.limitations, "derivation limitations"),)
        digest = _digest(material)
        if self.input_digest != digest or self.market_probability_derivation_id != f"market-probability-derivation:{digest}": _fail("market derivation identity conflict")


def create_market_probability_derivation(*, protocol: ResearchProtocolV2, snapshot: ResearchSnapshotV2,
        opportunity:ResearchCaptureOpportunity,schedule_evidence:OutcomeObservation,
        forecast_observations:Iterable[Any],market_observations:Iterable[MarketObservation],
        observation: MarketObservation, series: ProviderMarketSeries, effective_at: datetime,
        provenance: ResearchContractProvenance, limitations: tuple[str, ...] = ()) -> MarketProbabilityDerivation:
    _require_aware(effective_at,"derivation effective_at")
    forecast_values=tuple(forecast_observations);market_values=tuple(market_observations)
    forecast_map={item.observation_id:item for item in forecast_values};market_map={item.observation_id:item for item in market_values}
    if len(forecast_map)!=len(forecast_values) or len(market_map)!=len(market_values):
        _fail("market derivation Snapshot Evidence registry contains duplicate or conflicting authority")
    validate_research_snapshot_v2_authority(snapshot=snapshot,protocol=protocol,opportunity=opportunity,
        schedule=schedule_evidence,forecast_observations=forecast_map,market_observations=market_map)
    if market_map.get(observation.observation_id)!=observation:
        _fail("market derivation observation is absent from exact Evidence authority")
    benchmark = protocol.market_benchmark
    capture = next((item for item in snapshot.source_captures if item.probability_source_reference_id == benchmark.probability_source_reference_id), None)
    if capture is None or capture.disposition is not SourceCaptureDispositionV2.CAPTURED_VALID or capture.evidence_reference != SourceEvidenceReference(SourceEvidenceKind.MARKET_OBSERVATION, observation.observation_id): _fail("derivation requires exact valid Market Evidence capture")
    if snapshot.protocol_id != protocol.research_protocol_id or observation.canonical_event_id != snapshot.canonical_event_id: _fail("derivation Protocol/event mismatch")
    if observation.series_id != series.series_id or observation.proposition_id != series.proposition_id: _fail("derivation Market Series mismatch")
    if (observation.provenance.provider!=benchmark.provider_id or series.provider!=benchmark.provider_id
            or observation.provider_market_id!=series.provider_market_id):
        _fail("derivation Market provider or native market authority conflicts with Protocol")
    if snapshot.canonical_proposition_outcome_id not in (series.yes_semantic.participant_id, series.no_semantic.participant_id): _fail("canonical outcome is not represented by market semantics")
    tolerance = _parameter(protocol.capture_tolerance_rule, "seconds")
    if abs((observation.collected_at - snapshot.target_capture_at).total_seconds()) > tolerance: _fail("Market Evidence is outside capture tolerance")
    if any(item.collected_at < observation.collected_at or item.collected_at > snapshot.capture_completed_at for item in observation.component_evidence): _fail("Market component chronology is incompatible")
    material_available=max((snapshot.effective_at,observation.collected_at,*(item.collected_at for item in observation.component_evidence)))
    if effective_at<material_available:_fail("market derivation is backdated before material Evidence")
    outcome = snapshot.canonical_proposition_outcome_id
    yes = outcome == series.yes_semantic.participant_id
    offer_side = MarketSide.YES if yes else MarketSide.NO
    opposite = MarketSide.NO if yes else MarketSide.YES
    offer_levels = tuple(item for item in observation.order_book if item.acquisition_side is offer_side)
    opposite_offers = tuple(item for item in observation.order_book if item.acquisition_side is opposite)
    if not offer_levels or not opposite_offers: _fail("two positive-depth market bounds are required")
    best_offer_price = min(item.acquisition_price for item in offer_levels)
    offer_candidates = tuple(item for item in offer_levels if item.acquisition_price == best_offer_price)
    opposite_best = min(item.acquisition_price for item in opposite_offers)
    bid_price = Decimal(1) - opposite_best
    bid_candidates = tuple(item for item in opposite_offers if item.acquisition_price == opposite_best)
    def combined(kind:str,price:Decimal,items:tuple[Any,...])->MarketProbabilityBound:
        # Equal-price levels are canonical scientific support; quantity is additive and order is nonmaterial.
        contributors=tuple(MarketProbabilityLevel(price,item.quantity,item.acquisition_side,item.acquisition_price,item.provider_book_side,item.provider_price,
            item.evidence_kind,item.transformation,"canonical_bid = 1 - complementary_outcome_offer" if kind=="bid" else None,
            item.source_endpoint,item.collected_at) for item in items)
        quantity=sum((item.quantity for item in contributors),Decimal(0))
        return MarketProbabilityBound(kind,price,quantity,max(item.collected_at for item in contributors),contributors)
    offer=combined("offer",best_offer_price,offer_candidates)
    bid=combined("bid",bid_price,bid_candidates)
    if bid.canonical_price > offer.canonical_price: _fail("canonical market interval is crossed")
    complement_id = series.no_semantic.participant_id if yes else series.yes_semantic.participant_id
    with localcontext() as context:
        context.prec = PRECISION; context.rounding = ROUND_HALF_EVEN
        midpoint = (bid.canonical_price + offer.canonical_price) / Decimal(2); complement = Decimal(1) - midpoint
    values = dict(schema_version=SCHEMA_VERSION, identity_algorithm_version=IDENTITY_VERSION,
        derivation_algorithm_version=DERIVATION_ALGORITHM_VERSION, protocol_id=protocol.research_protocol_id,
        research_snapshot_id=snapshot.research_snapshot_id, source_reference_id=benchmark.probability_source_reference_id,
        market_observation_id=observation.observation_id, market_series_id=series.series_id,
        canonical_event_id=snapshot.canonical_event_id, proposition_id=series.proposition_id,
        canonical_outcome_id=outcome, bid=bid, offer=offer, midpoint=midpoint,
        complement_outcome_id=complement_id, complement_probability=complement,
        probability_distribution=tuple(sorted(((outcome, midpoint), (complement_id, complement)))),
        representation_rule_id=benchmark.probability_representation_rule.rule_specification_id,
        transformation_rule_id=benchmark.transformation_rule.rule_specification_id,
        effective_at=effective_at, limitations=_unique(limitations, "derivation limitations"), provenance=provenance)
    material = tuple(values[name] for name in MarketProbabilityDerivation.__dataclass_fields__ if name not in ("market_probability_derivation_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return MarketProbabilityDerivation(f"market-probability-derivation:{digest}", **values, input_digest=digest)


class ProbabilitySourceRole(str, Enum): MARKET_BENCHMARK="market-benchmark"; ALTERNATIVE="alternative-probability-source"
class SourceMeasurementInputKind(str, Enum): FORECAST_EVALUATION="forecast-evaluation"; MARKET_PROBABILITY_DERIVATION="market-probability-derivation"


def _role(protocol: ResearchProtocolV2, source_id: str) -> ProbabilitySourceRole:
    if source_id == protocol.market_benchmark.probability_source_reference_id: return ProbabilitySourceRole.MARKET_BENCHMARK
    if source_id in {item.probability_source_reference_id for item in protocol.alternative_sources}: return ProbabilitySourceRole.ALTERNATIVE
    _fail("Probability Source is not Protocol-authorized")


@dataclass(frozen=True, slots=True)
class ProbabilitySourceMeasurement:
    probability_source_measurement_id: str; schema_version: str; identity_algorithm_version: str
    measurement_algorithm_version: str; protocol_id: str; research_snapshot_id: str
    source_reference_id: str; source_role: ProbabilitySourceRole; canonical_event_id: str
    proposition_type: str; canonical_proposition_outcome_id: str; source_input_kind: SourceMeasurementInputKind
    source_input_id: str; outcome_observation_id: str; effective_at: datetime
    probability_distribution: tuple[tuple[str, Decimal], ...]; realized_outcome_id: str
    realized_outcome: int; brier_score: Decimal; log_loss: Decimal; calibration_probability: Decimal
    arithmetic_inputs: tuple[tuple[str, Decimal, int], ...]
    dimension_classifications: tuple[SnapshotDimensionClassification, ...]; limitations: tuple[str, ...]
    provenance: ResearchContractProvenance; input_digest: str
    def __post_init__(self) -> None:
        _require_aware(self.effective_at, "source Measurement effective_at")
        if self.measurement_algorithm_version != MEASUREMENT_ALGORITHM_VERSION: _fail("unsupported source Measurement generation")
        probabilities = dict(self.probability_distribution)
        if len(probabilities) != 2 or sum(probabilities.values(), Decimal(0)) != 1: _fail("source Measurement requires complete binary distribution")
        p = probabilities.get(self.realized_outcome_id)
        if p is None or self.realized_outcome != 1 or self.calibration_probability != probabilities[self.canonical_proposition_outcome_id]: _fail("source Measurement outcome/calibration input conflict")
        with localcontext() as context:
            context.prec = PRECISION; context.rounding = ROUND_HALF_EVEN
            brier = (p - 1) ** 2; log_loss = Decimal("Infinity") if p == 0 else -p.ln()
        if self.brier_score != brier or self.log_loss != log_loss: _fail("source Measurement scoring conflict")
        material = tuple(getattr(self, name) for name in self.__dataclass_fields__ if name not in ("probability_source_measurement_id", "provenance", "input_digest", "limitations")) + (_unique(self.limitations, "Measurement limitations"),)
        digest = _digest(material)
        if self.input_digest != digest or self.probability_source_measurement_id != f"probability-source-measurement:{digest}": _fail("source Measurement identity conflict")


def _measurement(protocol: ResearchProtocolV2, snapshot: ResearchSnapshotV2, source_id: str,
                 input_kind: SourceMeasurementInputKind, input_id: str, outcome: OutcomeObservation,
                 effective_at: datetime, distribution: tuple[tuple[str, Decimal], ...],
                 brier: Decimal, log_loss: Decimal, limitations: tuple[str, ...],
                 provenance: ResearchContractProvenance) -> ProbabilitySourceMeasurement:
    if snapshot.protocol_id != protocol.research_protocol_id or snapshot.canonical_event_id != outcome.canonical_event_id: _fail("source Measurement lineage mismatch")
    if effective_at<max(snapshot.effective_at,outcome.collected_at):_fail("source Measurement is backdated before material authority")
    if not outcome.authoritative_final or outcome.winning_participant_id is None or outcome.provider_status not in (OutcomeStatus.FINAL, OutcomeStatus.FORFEIT): _fail("eligible authoritative outcome is required")
    probabilities = tuple(sorted(distribution)); probability_map = dict(probabilities); winner = outcome.winning_participant_id
    if winner not in probability_map: _fail("realized outcome absent from source distribution")
    inputs = tuple((key, value, int(key == winner)) for key, value in probabilities)
    values = dict(schema_version=SCHEMA_VERSION, identity_algorithm_version=IDENTITY_VERSION,
        measurement_algorithm_version=MEASUREMENT_ALGORITHM_VERSION, protocol_id=protocol.research_protocol_id,
        research_snapshot_id=snapshot.research_snapshot_id, source_reference_id=source_id,
        source_role=_role(protocol, source_id), canonical_event_id=snapshot.canonical_event_id,
        proposition_type=snapshot.proposition_type, canonical_proposition_outcome_id=snapshot.canonical_proposition_outcome_id,
        source_input_kind=input_kind, source_input_id=input_id, outcome_observation_id=outcome.observation_id,
        effective_at=effective_at, probability_distribution=probabilities, realized_outcome_id=winner,
        realized_outcome=1, brier_score=brier, log_loss=log_loss,
        calibration_probability=probability_map[snapshot.canonical_proposition_outcome_id], arithmetic_inputs=inputs,
        dimension_classifications=snapshot.dimension_classifications,
        limitations=_unique(limitations, "Measurement limitations"), provenance=provenance)
    material = tuple(values[name] for name in ProbabilitySourceMeasurement.__dataclass_fields__ if name not in ("probability_source_measurement_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return ProbabilitySourceMeasurement(f"probability-source-measurement:{digest}", **values, input_digest=digest)


def create_forecast_backed_source_measurement(*, protocol: ResearchProtocolV2, snapshot: ResearchSnapshotV2,
        source_reference: ProbabilitySourceReference, evaluation: ForecastEvaluation, outcome: OutcomeObservation,
        effective_at: datetime, provenance: ResearchContractProvenance) -> ProbabilitySourceMeasurement:
    capture = next((item for item in snapshot.source_captures if item.probability_source_reference_id == source_reference.probability_source_reference_id), None)
    expected_ref = SourceEvidenceReference(SourceEvidenceKind.FORECAST_OBSERVATION, evaluation.forecast_observation_id)
    if capture is None or capture.disposition is not SourceCaptureDispositionV2.CAPTURED_VALID or capture.evidence_reference != expected_ref: _fail("Forecast Evaluation is not exact Snapshot Evidence")
    if capture.observed_at!=evaluation.forecast_collected_at:_fail("Forecast Evaluation chronology conflicts with Snapshot capture")
    if (evaluation.algorithm_id,evaluation.algorithm_version)!=(EVALUATION_ALGORITHM_ID,EVALUATION_ALGORITHM_VERSION):
        _fail("unsupported historical Forecast Evaluation scoring generation")
    if evaluation.outcome_observation_id != outcome.observation_id or evaluation.canonical_event_id != snapshot.canonical_event_id: _fail("Forecast Evaluation lineage mismatch")
    return _measurement(protocol, snapshot, source_reference.probability_source_reference_id,
        SourceMeasurementInputKind.FORECAST_EVALUATION, evaluation.evaluation_id, outcome, effective_at,
        evaluation.probability_distribution, evaluation.brier_score, evaluation.log_loss,
        evaluation.limitations, provenance)


def create_market_backed_source_measurement(*, protocol: ResearchProtocolV2, snapshot: ResearchSnapshotV2,
        derivation: MarketProbabilityDerivation, outcome: OutcomeObservation, effective_at: datetime,
        provenance: ResearchContractProvenance) -> ProbabilitySourceMeasurement:
    if derivation.protocol_id != protocol.research_protocol_id or derivation.research_snapshot_id != snapshot.research_snapshot_id: _fail("market derivation lineage mismatch")
    if effective_at<derivation.effective_at:_fail("market-backed Measurement precedes its derivation")
    probabilities = dict(derivation.probability_distribution); winner = outcome.winning_participant_id
    if winner not in probabilities: _fail("Outcome is incompatible with market distribution")
    with localcontext() as context:
        context.prec = PRECISION; context.rounding = ROUND_HALF_EVEN
        p = probabilities[winner]; brier = (p - 1) ** 2; log_loss = Decimal("Infinity") if p == 0 else -p.ln()
    return _measurement(protocol, snapshot, derivation.source_reference_id,
        SourceMeasurementInputKind.MARKET_PROBABILITY_DERIVATION,
        derivation.market_probability_derivation_id, outcome, effective_at,
        derivation.probability_distribution, brier, log_loss, derivation.limitations, provenance)


def _difference(left: Decimal, right: Decimal) -> Decimal | None:
    if left == Decimal("Infinity") and right == Decimal("Infinity"): return None
    with localcontext() as context:
        context.prec = PRECISION; context.rounding = ROUND_HALF_EVEN
        return left - right


@dataclass(frozen=True, slots=True)
class ComparativeMeasurementV2:
    comparative_measurement_id: str; schema_version: str; identity_algorithm_version: str
    measurement_algorithm_version: str; protocol_id: str; research_snapshot_id: str; effective_at: datetime
    benchmark_source_reference_id:str;challenger_source_reference_id:str
    benchmark_measurement_id: str; challenger_measurement_id: str; canonical_event_id: str
    proposition_type: str; outcome_observation_id: str; benchmark_probability: Decimal; challenger_probability: Decimal
    benchmark_brier_score: Decimal; challenger_brier_score: Decimal; brier_improvement: Decimal
    benchmark_log_loss: Decimal; challenger_log_loss: Decimal; log_loss_improvement: Decimal | None
    dimension_classifications:tuple[SnapshotDimensionClassification,...]
    limitations: tuple[str, ...]; provenance: ResearchContractProvenance; input_digest: str
    def __post_init__(self) -> None:
        _require_aware(self.effective_at, "Comparative Measurement v2 effective_at")
        if self.measurement_algorithm_version != COMPARATIVE_MEASUREMENT_ALGORITHM_VERSION: _fail("unsupported paired generation")
        if self.brier_improvement != _difference(self.benchmark_brier_score, self.challenger_brier_score) or self.log_loss_improvement != _difference(self.benchmark_log_loss, self.challenger_log_loss): _fail("Comparative Measurement v2 arithmetic conflict")
        material = tuple(getattr(self, name) for name in self.__dataclass_fields__ if name not in ("comparative_measurement_id", "provenance", "input_digest", "limitations")) + (_unique(self.limitations, "paired limitations"),)
        digest = _digest(material)
        if self.input_digest != digest or self.comparative_measurement_id != f"comparative-measurement-v2:{digest}": _fail("Comparative Measurement v2 identity conflict")


def create_comparative_measurement_v2(*, protocol: ResearchProtocolV2,
        benchmark: ProbabilitySourceMeasurement, challenger: ProbabilitySourceMeasurement,
        snapshot: ResearchSnapshotV2, opportunity:ResearchCaptureOpportunity,
        schedule_evidence:OutcomeObservation,forecast_observations:Iterable[Any],
        market_observations:Iterable[MarketObservation],effective_at: datetime,
        provenance: ResearchContractProvenance, limitations: tuple[str, ...] = ()) -> ComparativeMeasurementV2:
    if benchmark.source_role is not ProbabilitySourceRole.MARKET_BENCHMARK or challenger.source_role is not ProbabilitySourceRole.ALTERNATIVE: _fail("paired source roles are invalid")
    if effective_at<max(benchmark.effective_at,challenger.effective_at):_fail("Comparative Measurement v2 is backdated")
    common = ("protocol_id", "research_snapshot_id", "canonical_event_id", "proposition_type", "outcome_observation_id", "realized_outcome_id")
    if any(getattr(benchmark, name) != getattr(challenger, name) for name in common): _fail("paired source Measurements are incompatible")
    if snapshot.protocol_id != protocol.research_protocol_id or snapshot.research_snapshot_id != benchmark.research_snapshot_id:
        _fail("paired source Measurements require their exact Protocol Snapshot")
    forecast_values=tuple(forecast_observations);market_values=tuple(market_observations)
    forecast_map={item.observation_id:item for item in forecast_values};market_map={item.observation_id:item for item in market_values}
    if len(forecast_map)!=len(forecast_values) or len(market_map)!=len(market_values):
        _fail("comparative Snapshot Evidence registry contains duplicate or conflicting authority")
    validate_research_snapshot_v2_authority(snapshot=snapshot,protocol=protocol,opportunity=opportunity,
        schedule=schedule_evidence,forecast_observations=forecast_map,market_observations=market_map)
    expected=create_pairwise_synchronization_v2(protocol=protocol,snapshot=snapshot,opportunity=opportunity,
        challenger_source_reference_id=challenger.source_reference_id,forecast_observations=forecast_values,
        market_observations=market_values)
    stored=tuple(item for item in snapshot.pairwise_synchronization
                 if item.challenger_source_reference_id==challenger.source_reference_id)
    if len(stored)!=1 or stored[0]!=expected or not expected.synchronized:
        _fail("paired source captures are not authoritatively synchronized")
    bp = dict(benchmark.probability_distribution)[benchmark.canonical_proposition_outcome_id]
    cp = dict(challenger.probability_distribution)[challenger.canonical_proposition_outcome_id]
    values = dict(schema_version=SCHEMA_VERSION, identity_algorithm_version=IDENTITY_VERSION,
        measurement_algorithm_version=COMPARATIVE_MEASUREMENT_ALGORITHM_VERSION, protocol_id=protocol.research_protocol_id,
        research_snapshot_id=benchmark.research_snapshot_id, effective_at=effective_at,
        benchmark_source_reference_id=benchmark.source_reference_id,challenger_source_reference_id=challenger.source_reference_id,
        benchmark_measurement_id=benchmark.probability_source_measurement_id,
        challenger_measurement_id=challenger.probability_source_measurement_id,
        canonical_event_id=benchmark.canonical_event_id, proposition_type=benchmark.proposition_type,
        outcome_observation_id=benchmark.outcome_observation_id, benchmark_probability=bp,
        challenger_probability=cp, benchmark_brier_score=benchmark.brier_score,
        challenger_brier_score=challenger.brier_score,
        brier_improvement=_difference(benchmark.brier_score, challenger.brier_score),
        benchmark_log_loss=benchmark.log_loss, challenger_log_loss=challenger.log_loss,
        log_loss_improvement=_difference(benchmark.log_loss, challenger.log_loss),
        dimension_classifications=benchmark.dimension_classifications,
        limitations=_unique(tuple(set(benchmark.limitations) | set(challenger.limitations) | set(limitations)), "paired limitations"), provenance=provenance)
    material = tuple(values[name] for name in ComparativeMeasurementV2.__dataclass_fields__ if name not in ("comparative_measurement_id", "provenance", "input_digest", "limitations")) + (values["limitations"],)
    digest = _digest(material)
    return ComparativeMeasurementV2(f"comparative-measurement-v2:{digest}", **values, input_digest=digest)


def create_pairwise_synchronization_v2(*,protocol:ResearchProtocolV2,snapshot:ResearchSnapshotV2,
        opportunity:ResearchCaptureOpportunity,challenger_source_reference_id:str,
        forecast_observations:Iterable[Any]=(),market_observations:Iterable[MarketObservation]=())->PairwiseSynchronization:
    if snapshot.protocol_id!=protocol.research_protocol_id or opportunity.protocol_id!=protocol.research_protocol_id:
        _fail("synchronization crosses Protocol authority")
    if snapshot.research_capture_opportunity_id!=opportunity.research_capture_opportunity_id:
        _fail("synchronization crosses Snapshot opportunity authority")
    captures={item.probability_source_reference_id:item for item in snapshot.source_captures}
    if len(captures)!=len(snapshot.source_captures):_fail("Snapshot contains duplicate source capture authority")
    benchmark_capture=captures.get(protocol.market_benchmark.probability_source_reference_id)
    challenger_capture=captures.get(challenger_source_reference_id)
    if benchmark_capture is None or challenger_capture is None:_fail("synchronization capture authority is incomplete")
    rule=protocol.synchronization_rule
    if (rule.rule_id,rule.rule_version)!=("maximum-pair-separation","1"):_fail("unsupported synchronization rule mechanics")
    if benchmark_capture.probability_source_reference_id!=protocol.market_benchmark.probability_source_reference_id:
        _fail("synchronization benchmark conflicts with Protocol")
    challenger_source=next((item for item in protocol.alternative_sources
                            if item.probability_source_reference_id==challenger_capture.probability_source_reference_id),None)
    if challenger_source is None:
        _fail("synchronization challenger conflicts with Protocol")
    valid=(benchmark_capture.disposition is SourceCaptureDispositionV2.CAPTURED_VALID
           and challenger_capture.disposition is SourceCaptureDispositionV2.CAPTURED_VALID)
    if valid:
        assert benchmark_capture.evidence_reference is not None and challenger_capture.evidence_reference is not None
        benchmark_evidence=validate_source_evidence_reference(benchmark_capture.evidence_reference,
            forecast_observations=forecast_observations,market_observations=market_observations)
        challenger_evidence=validate_source_evidence_reference(challenger_capture.evidence_reference,
            forecast_observations=forecast_observations,market_observations=market_observations)
        if benchmark_capture.evidence_reference.evidence_kind is not SourceEvidenceKind.MARKET_OBSERVATION:
            _fail("benchmark synchronization requires Market Evidence")
        if challenger_capture.evidence_reference.evidence_kind is not SourceEvidenceKind.FORECAST_OBSERVATION:
            _fail("challenger synchronization requires Forecast Evidence")
        if (benchmark_evidence.canonical_event_id!=snapshot.canonical_event_id
                or benchmark_evidence.provenance.provider!=protocol.market_benchmark.provider_id
                or challenger_evidence.distribution.canonical_event_id!=snapshot.canonical_event_id
                or challenger_evidence.schedule_observation_id!=opportunity.schedule_observation_id
                or challenger_evidence.provenance.provider!=challenger_source.provider_id
                or challenger_evidence.version_id!=challenger_source.model_or_product_version):
            _fail("synchronization Evidence lineage is incompatible")
        if benchmark_capture.observed_at!=benchmark_evidence.collected_at or challenger_capture.observed_at!=challenger_evidence.collected_at:
            _fail("synchronization capture timestamp conflicts with immutable Evidence")
        delta=abs(benchmark_evidence.collected_at-challenger_evidence.collected_at)
        separation=((delta.days*86400+delta.seconds)*1_000_000+delta.microseconds)
        synchronized=delta<=timedelta(seconds=_parameter(rule,"seconds"))
        reasons=() if synchronized else ("capture-separation-exceeds-protocol-maximum",)
    else:
        separation=None;synchronized=False;reasons=("source-capture-not-valid",)
    return PairwiseSynchronization(benchmark_capture.probability_source_reference_id,
        challenger_capture.probability_source_reference_id,synchronized,separation,rule.rule_id,rule.rule_version,reasons)


PAIRED_PERFORMANCE_ALGORITHM_VERSION="2"
PAIRED_TIME_BOUNDED_ALGORITHM_VERSION="2"
PAIRED_DRIFT_ALGORITHM_VERSION="2"


def _paired_uncertainty(protocol:ResearchProtocolV2,claim_id:str,domain_id:str,boundary:datetime,
        values:tuple[ComparativeMeasurementV2,...],algorithm:str)->PairedUncertainty:
    rule=protocol.base_protocol.statistical_method_rule
    if (rule.rule_id,rule.rule_version)!=("paired-bootstrap","1"):_fail("paired v2 aggregation requires paired-bootstrap v1")
    confidence=_parameter(rule,"confidence_level");count=_parameter(rule,"resamples")
    improvements=tuple(item.brier_improvement for item in values)
    point=_mean(improvements)
    if not values:return PairedUncertainty(None,0,None,None,confidence,rule.rule_specification_id,rule.rule_version,count,algorithm)
    seed=_digest((protocol.research_protocol_id,claim_id,domain_id,boundary,tuple(item.comparative_measurement_id for item in values),rule.rule_specification_id,algorithm))
    rng=random.Random(int(seed,16));samples=[]
    for _ in range(count):samples.append(_mean(tuple(improvements[rng.randrange(len(values))] for __ in values)))
    ordered=tuple(sorted(samples));alpha=(Decimal(1)-confidence)/2
    return PairedUncertainty(point,len(values),ordered[int(alpha*count)],ordered[min(count-1,int((Decimal(1)-alpha)*count))],confidence,rule.rule_specification_id,rule.rule_version,count,algorithm)


def _paired_calibration(values:tuple[ComparativeMeasurementV2,...],source_measurements:Mapping[str,ProbabilitySourceMeasurement],source:str,rule:VersionedRuleSpecification)->CalibrationResult:
    ids=tuple(getattr(item,f"{source}_measurement_id") for item in values)
    selected=tuple(source_measurements[item] for item in ids)
    return _calibration(selected,rule)


@dataclass(frozen=True,slots=True)
class ComparativePerformanceV2:
    comparative_performance_id:str;schema_version:str;analysis_algorithm_version:str;protocol_id:str;claim_protocol_id:str
    edge_claim_id:str;research_domain_id:str;analysis_boundary:datetime;benchmark_source_reference_id:str;challenger_source_reference_id:str
    comparative_measurement_ids:tuple[str,...];population_digest:str;paired_sample_size:int
    benchmark_mean_brier_score:Decimal|None;challenger_mean_brier_score:Decimal|None;mean_paired_brier_improvement:Decimal|None
    primary_uncertainty:PairedUncertainty;benchmark_mean_log_loss:Decimal|None;challenger_mean_log_loss:Decimal|None
    mean_log_loss_improvement:Decimal|None;benchmark_calibration:CalibrationResult;challenger_calibration:CalibrationResult
    limitations:tuple[str,...];provenance:ResearchContractProvenance;input_digest:str
    def __post_init__(self):
        _require_aware(self.analysis_boundary,"paired performance boundary")
        if self.schema_version!=SCHEMA_VERSION or self.analysis_algorithm_version!=PAIRED_PERFORMANCE_ALGORITHM_VERSION:_fail("unsupported paired Performance generation")
        mids=_unique(self.comparative_measurement_ids,"paired v2 population")
        if self.paired_sample_size!=len(mids) or self.primary_uncertainty.paired_sample_size!=len(mids) or self.population_digest!=_digest(mids):_fail("paired Performance population conflict")
        material=tuple(getattr(self,f.name) for f in fields(self) if f.name not in ("comparative_performance_id","provenance","input_digest","limitations"))+(_unique(self.limitations,"paired performance limitations"),);digest=_digest(material)
        if self.input_digest!=digest or self.comparative_performance_id!=f"comparative-performance-v2:{digest}":_fail("paired Performance v2 identity conflict")


def create_comparative_performance_v2(*,protocol:ResearchProtocolV2,edge_claim:EdgeClaim,domain:ResearchDomain,
        analysis_boundary:datetime,measurements:Iterable[ComparativeMeasurementV2],source_measurements:Iterable[ProbabilitySourceMeasurement],
        provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->ComparativePerformanceV2:
    if domain!=_broad(protocol):_fail("paired v2 segmented domain is unsupported")
    if edge_claim.protocol_id!=protocol.base_protocol.research_protocol_id or edge_claim.research_domain_id!=domain.research_domain_id:_fail("paired v2 claim authority is incompatible")
    if edge_claim.benchmark_source_reference_id!=protocol.market_benchmark.probability_source_reference_id:_fail("paired v2 benchmark authority conflict")
    def domain_matches(item):
        available={(value.approved_dimension_id,value.partition_key) for value in item.dimension_classifications}
        return all((value.approved_dimension_id,value.partition_key) in available for value in domain.partition_selections)
    population=tuple(sorted((item for item in measurements if item.protocol_id==protocol.research_protocol_id
        and item.benchmark_source_reference_id==edge_claim.benchmark_source_reference_id
        and item.challenger_source_reference_id==edge_claim.challenger_source_reference_id
        and item.proposition_type==domain.proposition_type and domain_matches(item)
        and item.effective_at<=analysis_boundary),key=lambda item:item.comparative_measurement_id))
    if any(item.measurement_algorithm_version!=COMPARATIVE_MEASUREMENT_ALGORITHM_VERSION for item in population):_fail("paired population mixes generations")
    source_values=tuple(source_measurements);source_by_id={item.probability_source_measurement_id:item for item in source_values}
    if len(source_by_id)!=len(source_values):_fail("duplicate source Measurement authority in paired aggregation")
    for item in population:
        if item.benchmark_measurement_id not in source_by_id or item.challenger_measurement_id not in source_by_id:_fail("paired aggregation references unknown source Measurement")
        if source_by_id[item.challenger_measurement_id].source_reference_id!=edge_claim.challenger_source_reference_id:_fail("paired aggregation challenger conflicts with claim")
    calibration_rule=next((item for item in protocol.supporting_measure_rules if (item.rule_id,item.rule_version)==("calibration-safeguard","2")),None)
    if calibration_rule is None:_fail("paired v2 requires Calibration v2")
    mids=tuple(item.comparative_measurement_id for item in population);limits=_unique(limitations,"paired performance limitations")
    values=dict(schema_version=SCHEMA_VERSION,analysis_algorithm_version=PAIRED_PERFORMANCE_ALGORITHM_VERSION,protocol_id=protocol.research_protocol_id,claim_protocol_id=protocol.base_protocol.research_protocol_id,edge_claim_id=edge_claim.edge_claim_id,research_domain_id=domain.research_domain_id,analysis_boundary=analysis_boundary,benchmark_source_reference_id=edge_claim.benchmark_source_reference_id,challenger_source_reference_id=edge_claim.challenger_source_reference_id,comparative_measurement_ids=mids,population_digest=_digest(mids),paired_sample_size=len(population),benchmark_mean_brier_score=_mean(tuple(item.benchmark_brier_score for item in population)),challenger_mean_brier_score=_mean(tuple(item.challenger_brier_score for item in population)),mean_paired_brier_improvement=_mean(tuple(item.brier_improvement for item in population)),primary_uncertainty=_paired_uncertainty(protocol,edge_claim.edge_claim_id,domain.research_domain_id,analysis_boundary,population,PAIRED_PERFORMANCE_ALGORITHM_VERSION),benchmark_mean_log_loss=_mean(tuple(item.benchmark_log_loss for item in population)),challenger_mean_log_loss=_mean(tuple(item.challenger_log_loss for item in population)),mean_log_loss_improvement=_mean(tuple(item.log_loss_improvement for item in population if item.log_loss_improvement is not None)) if all(item.log_loss_improvement is not None for item in population) else None,benchmark_calibration=_paired_calibration(population,source_by_id,"benchmark",calibration_rule),challenger_calibration=_paired_calibration(population,source_by_id,"challenger",calibration_rule),limitations=limits,provenance=provenance)
    material=tuple(values[f.name] for f in fields(ComparativePerformanceV2) if f.name not in ("comparative_performance_id","provenance","input_digest","limitations"))+(limits,);digest=_digest(material)
    return ComparativePerformanceV2(f"comparative-performance-v2:{digest}",**values,input_digest=digest)


@dataclass(frozen=True,slots=True)
class TimeBoundedComparativePerformanceV2:
    time_bounded_comparative_performance_id:str;schema_version:str;analysis_algorithm_version:str;protocol_id:str;claim_protocol_id:str;edge_claim_id:str;research_domain_id:str
    analysis_boundary:datetime;benchmark_source_reference_id:str;challenger_source_reference_id:str;surveillance_window_rule_id:str;window_start:datetime;window_end:datetime
    comparative_measurement_ids:tuple[str,...];population_digest:str;performance:ComparativePerformanceV2;provenance:ResearchContractProvenance;input_digest:str
    def __post_init__(self):
        if self.schema_version!=SCHEMA_VERSION or self.analysis_algorithm_version!=PAIRED_TIME_BOUNDED_ALGORITHM_VERSION or not self.window_start<self.window_end==self.analysis_boundary:_fail("unsupported bounded paired generation")
        if self.performance.comparative_measurement_ids!=self.comparative_measurement_ids or self.population_digest!=self.performance.population_digest:_fail("bounded paired population conflict")
        material=tuple(getattr(self,f.name) for f in fields(self) if f.name not in ("time_bounded_comparative_performance_id","provenance","input_digest"));digest=_digest(material)
        if self.input_digest!=digest or self.time_bounded_comparative_performance_id!=f"time-bounded-comparative-performance-v2:{digest}":_fail("bounded paired identity conflict")


def create_time_bounded_comparative_performance_v2(*,protocol:ResearchProtocolV2,edge_claim:EdgeClaim,domain:ResearchDomain,analysis_boundary:datetime,
        measurements:Iterable[ComparativeMeasurementV2],source_measurements:Iterable[ProbabilitySourceMeasurement],scheduled_start_by_snapshot:Mapping[str,datetime],provenance:ResearchContractProvenance)->TimeBoundedComparativePerformanceV2:
    all_values=tuple(measurements);snapshot_ids={item.research_snapshot_id for item in all_values}
    if set(scheduled_start_by_snapshot)!=snapshot_ids or any(value.tzinfo is None or value.utcoffset() is None for value in scheduled_start_by_snapshot.values()):_fail("bounded paired performance requires complete schedule authority")
    rule=next((item for item in protocol.surveillance_window_rules if (item.rule_id,item.rule_version)==("rolling-days","2")),None)
    if rule is None:_fail("bounded paired performance requires rolling-days v2")
    start=analysis_boundary-timedelta(days=_parameter(rule,"days"));selected=tuple(item for item in all_values if start<scheduled_start_by_snapshot[item.research_snapshot_id]<=analysis_boundary)
    performance=create_comparative_performance_v2(protocol=protocol,edge_claim=edge_claim,domain=domain,analysis_boundary=analysis_boundary,measurements=selected,source_measurements=source_measurements,provenance=provenance)
    values=dict(schema_version=SCHEMA_VERSION,analysis_algorithm_version=PAIRED_TIME_BOUNDED_ALGORITHM_VERSION,protocol_id=performance.protocol_id,claim_protocol_id=performance.claim_protocol_id,edge_claim_id=performance.edge_claim_id,research_domain_id=performance.research_domain_id,analysis_boundary=analysis_boundary,benchmark_source_reference_id=performance.benchmark_source_reference_id,challenger_source_reference_id=performance.challenger_source_reference_id,surveillance_window_rule_id=rule.rule_specification_id,window_start=start,window_end=analysis_boundary,comparative_measurement_ids=performance.comparative_measurement_ids,population_digest=performance.population_digest,performance=performance,provenance=provenance)
    material=tuple(values[f.name] for f in fields(TimeBoundedComparativePerformanceV2) if f.name not in ("time_bounded_comparative_performance_id","provenance","input_digest"));digest=_digest(material)
    return TimeBoundedComparativePerformanceV2(f"time-bounded-comparative-performance-v2:{digest}",**values,input_digest=digest)


@dataclass(frozen=True,slots=True)
class ComparativeDriftAnalysisV2:
    comparative_drift_analysis_id:str;schema_version:str;analysis_algorithm_version:str;protocol_id:str;claim_protocol_id:str;edge_claim_id:str;research_domain_id:str;analysis_boundary:datetime
    historical_performance_id:str;current_bounded_performance_id:str;historical_population_digest:str;current_population_digest:str;measured_deterioration:Decimal|None;uncertainty:DriftUncertainty;material_deterioration_threshold:Decimal;disposition:DriftDisposition;provenance:ResearchContractProvenance;input_digest:str
    def __post_init__(self):
        _require_aware(self.analysis_boundary,"paired Drift boundary")
        if self.schema_version!=SCHEMA_VERSION or self.analysis_algorithm_version!=PAIRED_DRIFT_ALGORITHM_VERSION:_fail("unsupported paired Drift generation")
        material=tuple(getattr(self,f.name) for f in fields(self) if f.name not in ("comparative_drift_analysis_id","provenance","input_digest"));digest=_digest(material)
        if self.input_digest!=digest or self.comparative_drift_analysis_id!=f"comparative-drift-analysis-v2:{digest}":_fail("paired Drift identity conflict")


def create_comparative_drift_analysis_v2(*,protocol:ResearchProtocolV2,historical:ComparativePerformanceV2,current:TimeBoundedComparativePerformanceV2,
        measurements:Iterable[ComparativeMeasurementV2],provenance:ResearchContractProvenance)->ComparativeDriftAnalysisV2:
    common=("protocol_id","claim_protocol_id","edge_claim_id","research_domain_id","benchmark_source_reference_id","challenger_source_reference_id")
    if any(getattr(historical,name)!=getattr(current,name) for name in common) or historical.analysis_boundary!=current.window_start:_fail("paired Drift inputs are incompatible")
    measured=None if historical.mean_paired_brier_improvement is None or current.performance.mean_paired_brier_improvement is None else _difference(historical.mean_paired_brier_improvement,current.performance.mean_paired_brier_improvement)
    rule=protocol.base_protocol.statistical_method_rule;confidence=_parameter(rule,"confidence_level");count=_parameter(rule,"resamples")
    measurement_values=tuple(measurements);by_id={item.comparative_measurement_id:item for item in measurement_values}
    if len(by_id)!=len(measurement_values):_fail("paired Drift Measurement registry contains duplicate authority")
    try:historical_values=tuple(by_id[item].brier_improvement for item in historical.comparative_measurement_ids);current_values=tuple(by_id[item].brier_improvement for item in current.comparative_measurement_ids)
    except KeyError as error:_fail(f"paired Drift references unknown Measurement {error.args[0]}")
    if measured is None:lower=upper=None
    else:
        seed=_digest((protocol.research_protocol_id,historical.comparative_performance_id,current.time_bounded_comparative_performance_id,current.analysis_boundary,rule.rule_specification_id,PAIRED_DRIFT_ALGORITHM_VERSION));rng=random.Random(int(seed,16));samples=[]
        for _ in range(count):
            h=_mean(tuple(historical_values[rng.randrange(len(historical_values))] for __ in historical_values));c=_mean(tuple(current_values[rng.randrange(len(current_values))] for __ in current_values));samples.append(_difference(h,c))
        ordered=tuple(sorted(samples));alpha=(Decimal(1)-confidence)/2;lower=ordered[int(alpha*count)];upper=ordered[min(count-1,int((Decimal(1)-alpha)*count))]
    uncertainty=DriftUncertainty(measured,historical.paired_sample_size,current.performance.paired_sample_size,lower,upper,confidence,rule.rule_specification_id,rule.rule_version,count,PAIRED_DRIFT_ALGORITHM_VERSION)
    drift_rule=protocol.base_protocol.drift_classification_rule
    if (drift_rule.rule_id,drift_rule.rule_version)!=("brier-deterioration","2"):_fail("paired v2 Drift requires brier-deterioration v2")
    threshold=_parameter(drift_rule,"threshold")
    disposition=DriftDisposition.INSUFFICIENT_EVIDENCE if lower is None else (DriftDisposition.MATERIAL_DRIFT if lower>=threshold else DriftDisposition.NO_MATERIAL_DRIFT if upper<threshold else DriftDisposition.INSUFFICIENT_EVIDENCE)
    values=dict(schema_version=SCHEMA_VERSION,analysis_algorithm_version=PAIRED_DRIFT_ALGORITHM_VERSION,protocol_id=current.protocol_id,claim_protocol_id=current.claim_protocol_id,edge_claim_id=current.edge_claim_id,research_domain_id=current.research_domain_id,analysis_boundary=current.analysis_boundary,historical_performance_id=historical.comparative_performance_id,current_bounded_performance_id=current.time_bounded_comparative_performance_id,historical_population_digest=historical.population_digest,current_population_digest=current.population_digest,measured_deterioration=measured,uncertainty=uncertainty,material_deterioration_threshold=threshold,disposition=disposition,provenance=provenance)
    material=tuple(values[f.name] for f in fields(ComparativeDriftAnalysisV2) if f.name not in ("comparative_drift_analysis_id","provenance","input_digest"));digest=_digest(material)
    return ComparativeDriftAnalysisV2(f"comparative-drift-analysis-v2:{digest}",**values,input_digest=digest)


class CoverageCategory(str, Enum):
    SOURCE_CAPTURE_MISSING="source-capture-missing"; SOURCE_CAPTURE_INVALID="source-capture-invalid"
    OUTSIDE_CAPTURE_TOLERANCE="outside-capture-tolerance"; DERIVATION_INVALID="probability-derivation-unavailable-or-invalid"
    OUTCOME_INELIGIBLE="outcome-unresolved-or-ineligible"; MEASURED="successfully-measured"


@dataclass(frozen=True, slots=True)
class ProbabilitySourceCoverage:
    probability_source_coverage_id:str;schema_version:str;coverage_algorithm_version:str
    protocol_id:str;source_reference_id:str;analysis_boundary:datetime
    universe_opportunity_ids: tuple[str, ...]; capture_not_yet_due_opportunity_ids: tuple[str, ...]
    protocol_ineligible_opportunity_ids: tuple[str, ...]; eligible_denominator_opportunity_ids: tuple[str, ...]
    source_capture_missing_opportunity_ids: tuple[str, ...]; source_capture_invalid_opportunity_ids: tuple[str, ...]
    outside_capture_tolerance_opportunity_ids: tuple[str, ...]; derivation_invalid_opportunity_ids: tuple[str, ...]
    outcome_ineligible_opportunity_ids: tuple[str, ...]; measured_opportunity_ids: tuple[str, ...]
    measurement_ids: tuple[str, ...]; reason_codes: tuple[tuple[str, tuple[str, ...]], ...]
    provenance:ResearchContractProvenance;input_digest:str
    def __post_init__(self) -> None:
        _require_aware(self.analysis_boundary,"Coverage analysis boundary")
        if self.schema_version!=SCHEMA_VERSION or self.coverage_algorithm_version!="2":_fail("unsupported Coverage generation")
        for field in fields(self):
            if field.name.endswith("_ids"):
                values=getattr(self,field.name)
                if field.name=="measurement_ids":
                    if len(values)!=len(set(values)):_fail("measurement_ids contains duplicate authority")
                else: object.__setattr__(self, field.name, _unique(values, field.name))
        universe=set(self.universe_opportunity_ids); top=(set(self.capture_not_yet_due_opportunity_ids),set(self.protocol_ineligible_opportunity_ids),set(self.eligible_denominator_opportunity_ids))
        if any(top[i]&top[j] for i in range(3) for j in range(i+1,3)) or set().union(*top)!=universe: _fail("Coverage universe does not reconcile")
        eligible=set(self.eligible_denominator_opportunity_ids); categories=tuple(set(getattr(self,name)) for name in (
            "source_capture_missing_opportunity_ids","source_capture_invalid_opportunity_ids","outside_capture_tolerance_opportunity_ids","derivation_invalid_opportunity_ids","outcome_ineligible_opportunity_ids","measured_opportunity_ids"))
        if any(categories[i]&categories[j] for i in range(6) for j in range(i+1,6)) or set().union(*categories)!=eligible: _fail("eligible standalone denominator does not reconcile")
        if len(self.measurement_ids)!=len(self.measured_opportunity_ids): _fail("measured population and Measurement IDs conflict")
        material=tuple(getattr(self,item.name) for item in fields(self) if item.name not in ("probability_source_coverage_id","provenance","input_digest"));digest=_digest(material)
        if self.input_digest!=digest or self.probability_source_coverage_id!=f"probability-source-coverage:{digest}":_fail("Coverage identity conflict")
    @property
    def coverage_rate(self) -> Decimal | None:
        if not self.eligible_denominator_opportunity_ids: return None
        with localcontext() as context:
            context.prec=PRECISION; return Decimal(len(self.measured_opportunity_ids))/len(self.eligible_denominator_opportunity_ids)


def _make_coverage(*,protocol_id:str,source_reference_id:str,analysis_boundary:datetime,
        memberships:tuple[Any,...],provenance:ResearchContractProvenance)->ProbabilitySourceCoverage:
    values=(SCHEMA_VERSION,"2",protocol_id,source_reference_id,analysis_boundary,*memberships,provenance)
    material=values[:-1];digest=_digest(material)
    return ProbabilitySourceCoverage(f"probability-source-coverage:{digest}",*values,input_digest=digest)


def create_probability_source_coverage(*, protocol: ResearchProtocolV2, source_reference_id: str,
        analysis_boundary: datetime, opportunities: Iterable[ResearchCaptureOpportunity],
        eligibility_results: Iterable[CaptureBoundaryEligibility],eligibility_contexts:Iterable[ResearchEventEligibilityContext],
        snapshots: Iterable[ResearchSnapshotV2],market_observations:Iterable[MarketObservation]=(),
        market_series:Iterable[ProviderMarketSeries]=(),forecast_observations:Iterable[Any]=(),
        evaluation_eligibility_decisions:Iterable[EvaluationEligibilityDecision]=(),
        forecast_evaluations:Iterable[ForecastEvaluation]=(),derivations: Iterable[MarketProbabilityDerivation],
        outcome_histories:Iterable[OutcomeHistory],
        measurements: Iterable[ProbabilitySourceMeasurement]) -> ProbabilitySourceCoverage:
    _require_aware(analysis_boundary,"Coverage boundary")
    opportunity_values=tuple(opportunities); eligibility_values=tuple(eligibility_results); context_values=tuple(eligibility_contexts);snapshot_values=tuple(snapshots)
    derivation_values=tuple(derivations); history_values=tuple(outcome_histories);measurement_values=tuple(measurements)
    def exact_registry(values:Iterable[Any],label:str,key:str)->dict[str,Any]:
        supplied=tuple(values);result={getattr(item,key):item for item in supplied}
        if len(result)!=len(supplied):_fail(f"{label} contains duplicate or conflicting authority")
        return result
    market_observation_map=exact_registry(market_observations,"Coverage Market Evidence registry","observation_id")
    market_series_map=exact_registry(market_series,"Coverage Market Series registry","series_id")
    forecast_map=exact_registry(forecast_observations,"Coverage Forecast Evidence registry","observation_id")
    decision_map=exact_registry(evaluation_eligibility_decisions,"Coverage evaluation eligibility registry","decision_id")
    evaluation_map=exact_registry(forecast_evaluations,"Coverage Forecast Evaluation registry","evaluation_id")
    incompatible_opportunities=tuple(item for item in opportunity_values if item.protocol_id!=protocol.research_protocol_id)
    if incompatible_opportunities:_fail("Coverage opportunity registry mixes Protocol authority")
    opps={item.research_capture_opportunity_id:item for item in opportunity_values}
    if len(opps)!=len(opportunity_values):_fail("Coverage opportunity registry contains duplicate authority")
    provider=_parameter(protocol.outcome_resolution_rule,"source_id")
    schedule_by_id={}
    for history in history_values:
        if history.authoritative_provider_id!=provider:continue
        for observation in history.observations:
            prior=schedule_by_id.get(observation.observation_id)
            if prior is not None and prior!=observation:_fail("conflicting Schedule Evidence authority")
            schedule_by_id[observation.observation_id]=observation
    targets={}
    offset=_parameter(protocol.snapshot_timing_rule,"seconds_before_start")
    for oid,opportunity in opps.items():
        schedule=schedule_by_id.get(opportunity.schedule_observation_id)
        if schedule is None or schedule.collected_at>analysis_boundary:_fail("Coverage opportunity lacks boundary-visible Schedule Evidence")
        targets[oid]=schedule.scheduled_start-timedelta(seconds=offset)
    due_ids={oid for oid,target in targets.items() if analysis_boundary>=target}
    selected_eligibility=tuple(item for item in eligibility_values if item.protocol_id==protocol.research_protocol_id and item.eligibility_boundary<=analysis_boundary)
    eligibility={item.research_capture_opportunity_id:item for item in selected_eligibility}
    if len(eligibility)!=len(selected_eligibility):_fail("Coverage requires exactly one eligibility authority per opportunity")
    if set(eligibility)!=due_ids:_fail("Coverage requires exact prospective eligibility authority for every due opportunity")
    contexts={item.research_event_eligibility_context_id:item for item in context_values}
    if len(contexts)!=len(context_values):_fail("duplicate capture eligibility context authority")
    for oid,result in eligibility.items():
        if len(result.context_evidence_ids)!=1 or result.context_evidence_ids[0] not in contexts:_fail("eligibility result lacks exact prospective context authority")
        recreated=evaluate_capture_boundary_eligibility(protocol=protocol,opportunity=opps[oid],context=contexts[result.context_evidence_ids[0]],provenance=result.provenance)
        if recreated!=result:_fail("capture eligibility result does not reproduce from governing authority")
    if any(item.protocol_id!=protocol.research_protocol_id for item in snapshot_values):_fail("Coverage Snapshot registry mixes Protocol authority")
    if any(item.protocol_id!=protocol.research_protocol_id for item in derivation_values):_fail("Coverage derivation registry mixes Protocol authority")
    if any(item.protocol_id!=protocol.research_protocol_id for item in measurement_values):_fail("Coverage Measurement registry mixes Protocol authority")
    authoritative={item.research_capture_opportunity_id:item for item in select_authoritative_snapshots_v2(snapshot_values,analysis_boundary)}
    selected_derivations=tuple(item for item in derivation_values if item.effective_at<=analysis_boundary and item.source_reference_id==source_reference_id)
    selected_measurements=tuple(item for item in measurement_values if item.effective_at<=analysis_boundary and item.source_reference_id==source_reference_id)
    deriv_by_snapshot={item.research_snapshot_id:item for item in selected_derivations}
    measurement_by_authority={(item.research_snapshot_id,item.outcome_observation_id):item for item in selected_measurements}
    if len(deriv_by_snapshot)!=len(selected_derivations): _fail("duplicate derivation authority")
    if len(measurement_by_authority)!=len(selected_measurements): _fail("duplicate source Measurement authority")
    source=next((item for item in (protocol.market_benchmark,)+protocol.alternative_sources
                 if item.probability_source_reference_id==source_reference_id),None)
    if source is None:_fail("Coverage source is not Protocol-authorized")
    history_by_event={}
    for history in history_values:
        if history.authoritative_provider_id!=provider:continue
        if history.canonical_event_id in history_by_event:_fail("duplicate Outcome History authority")
        history_by_event[history.canonical_event_id]=history
    buckets={name:[] for name in ("not_due","ineligible","missing","invalid","outside","derivation","outcome","measured")}; reasons=[]; mids=[]
    for oid in sorted(opps):
        if oid not in due_ids:buckets["not_due"].append(oid);continue
        result=eligibility[oid]
        if result.disposition is CaptureBoundaryDisposition.PROTOCOL_INELIGIBLE: buckets["ineligible"].append(oid); continue
        snapshot=authoritative.get(oid)
        if snapshot is None: buckets["missing"].append(oid); reasons.append((oid,("snapshot-missing",))); continue
        if snapshot.protocol_id!=protocol.research_protocol_id or snapshot.research_capture_opportunity_id!=oid:_fail("Coverage Snapshot authority is incompatible")
        schedule=schedule_by_id.get(opps[oid].schedule_observation_id)
        if schedule is None:_fail("Coverage Snapshot lacks exact Schedule Evidence authority")
        validate_research_snapshot_v2_authority(snapshot=snapshot,protocol=protocol,opportunity=opps[oid],
            schedule=schedule,forecast_observations=forecast_map,market_observations=market_observation_map)
        capture=next((item for item in snapshot.source_captures if item.probability_source_reference_id==source_reference_id),None)
        if capture is None or capture.disposition is SourceCaptureDispositionV2.MISSING: buckets["missing"].append(oid); continue
        if capture.disposition is SourceCaptureDispositionV2.CAPTURED_INVALID or snapshot.validation_status is SnapshotValidationStatus.INVALID: buckets["invalid"].append(oid); continue
        if capture.disposition is SourceCaptureDispositionV2.OUTSIDE_CAPTURE_TOLERANCE: buckets["outside"].append(oid); continue
        assert capture.evidence_reference is not None
        captured_evidence=validate_source_evidence_reference(capture.evidence_reference,
            forecast_observations=forecast_map.values(),market_observations=market_observation_map.values())
        if capture.observed_at!=captured_evidence.collected_at:_fail("Coverage capture timestamp conflicts with immutable Evidence")
        derivation=deriv_by_snapshot.get(snapshot.research_snapshot_id)
        is_market=source_reference_id==protocol.market_benchmark.probability_source_reference_id
        if is_market:
            if capture.evidence_reference.evidence_kind is not SourceEvidenceKind.MARKET_OBSERVATION:
                _fail("Coverage Market Benchmark capture has wrong typed Evidence")
            if derivation is None:buckets["derivation"].append(oid);continue
            observation=market_observation_map.get(derivation.market_observation_id);series=market_series_map.get(derivation.market_series_id)
            if observation is None or series is None or derivation.market_observation_id!=capture.evidence_reference.evidence_id:
                _fail("Coverage derivation does not use the exact captured Market Evidence")
            recreated_derivation=create_market_probability_derivation(protocol=protocol,snapshot=snapshot,
                opportunity=opps[oid],schedule_evidence=schedule,forecast_observations=forecast_map.values(),
                market_observations=market_observation_map.values(),observation=observation,series=series,effective_at=derivation.effective_at,
                provenance=derivation.provenance,limitations=derivation.limitations)
            if recreated_derivation!=derivation:_fail("Coverage market derivation fails authoritative replay")
        elif capture.evidence_reference.evidence_kind is not SourceEvidenceKind.FORECAST_OBSERVATION:
            _fail("Coverage alternative source capture has wrong typed Evidence")
        history=history_by_event.get(snapshot.canonical_event_id)
        visible=() if history is None else tuple(item for item in history.observations if item.collected_at<=analysis_boundary)
        if not visible: buckets["outcome"].append(oid);continue
        visible_history=OutcomeHistory(history.canonical_event_id,history.authoritative_provider_id,visible)
        outcome=visible_history.latest_authoritative_final
        if outcome is None:buckets["outcome"].append(oid);continue
        evaluation=None
        if not is_market:
            candidates=tuple(item for item in evaluation_map.values()
                if item.forecast_observation_id==capture.evidence_reference.evidence_id
                and item.outcome_observation_id==outcome.observation_id)
            if len(candidates)>1:_fail("Coverage contains duplicate Forecast Evaluation authority")
            if not candidates:buckets["derivation"].append(oid);continue
            evaluation=candidates[0];decision=decision_map.get(evaluation.eligibility_decision_id)
            if decision is None:_fail("Coverage Forecast Evaluation lacks eligibility authority")
            recreated_decision=decide_evaluation_eligibility(captured_evidence,outcome,outcome_history=visible_history)
            if recreated_decision!=decision:_fail("Coverage Forecast eligibility fails authoritative replay")
            recreated_evaluation=create_forecast_evaluation(captured_evidence,outcome,decision,
                provider_id=source.provider_id,model_id=source.model_or_product_id,
                model_version_id=source.model_or_product_version)
            if recreated_evaluation!=evaluation:_fail("Coverage Forecast Evaluation fails authoritative replay")
        measurement=measurement_by_authority.get((snapshot.research_snapshot_id,outcome.observation_id))
        if measurement is None: buckets["outcome"].append(oid); continue
        if measurement.protocol_id!=protocol.research_protocol_id or measurement.source_reference_id!=source_reference_id:_fail("Coverage Measurement authority is incompatible")
        if is_market:
            if measurement.source_input_kind is not SourceMeasurementInputKind.MARKET_PROBABILITY_DERIVATION or measurement.source_input_id!=derivation.market_probability_derivation_id:
                _fail("Coverage Measurement does not reference the exact Market derivation")
            recreated_measurement=create_market_backed_source_measurement(protocol=protocol,snapshot=snapshot,
                derivation=derivation,outcome=outcome,effective_at=measurement.effective_at,provenance=measurement.provenance)
        else:
            assert evaluation is not None
            if measurement.source_input_kind is not SourceMeasurementInputKind.FORECAST_EVALUATION or measurement.source_input_id!=evaluation.evaluation_id:
                _fail("Coverage Measurement does not reference the exact Forecast Evaluation")
            recreated_measurement=create_forecast_backed_source_measurement(protocol=protocol,snapshot=snapshot,
                source_reference=source,evaluation=evaluation,outcome=outcome,effective_at=measurement.effective_at,
                provenance=measurement.provenance)
        if recreated_measurement!=measurement:_fail("Coverage Measurement fails authoritative replay")
        buckets["measured"].append(oid); mids.append(measurement.probability_source_measurement_id)
    eligible=tuple(sorted(sum((buckets[name] for name in ("missing","invalid","outside","derivation","outcome","measured")),[])))
    memberships=(tuple(sorted(opps)),tuple(buckets["not_due"]),tuple(buckets["ineligible"]),eligible,
        tuple(buckets["missing"]),tuple(buckets["invalid"]),tuple(buckets["outside"]),tuple(buckets["derivation"]),
        tuple(buckets["outcome"]),tuple(buckets["measured"]),tuple(mids),tuple(reasons))
    return _make_coverage(protocol_id=protocol.research_protocol_id,source_reference_id=source_reference_id,
        analysis_boundary=analysis_boundary,memberships=memberships,
        provenance=next(iter(eligibility.values())).provenance if eligibility else protocol.base_protocol.provenance)


@dataclass(frozen=True, slots=True)
class SourcePerformanceUncertainty:
    scope: str; point_estimate: Decimal | None; sample_size: int; lower_bound: Decimal | None; upper_bound: Decimal | None
    confidence_level: Decimal; resample_count: int; statistical_rule_id: str; statistical_rule_version: str
    analysis_algorithm_version: str; seed_digest: str; limitations: tuple[str, ...]


def create_source_performance_uncertainty(*, protocol: ResearchProtocolV2, domain: ResearchDomain,
        source_reference_id: str, role: ProbabilitySourceRole, scope: str, analysis_boundary: datetime,
        measurements: tuple[ProbabilitySourceMeasurement,...], window_start: datetime|None=None,
        window_end: datetime|None=None, algorithm_version: str=PERFORMANCE_ALGORITHM_VERSION) -> SourcePerformanceUncertainty:
    if scope not in ("cumulative","time-bounded"): _fail("uncertainty scope is unsupported")
    rule=protocol.standalone_statistical_method_rule; confidence=_parameter(rule,"confidence_level"); count=_parameter(rule,"resamples")
    ordered=_unique(measurements,"uncertainty Measurements",lambda item:item.probability_source_measurement_id); scores=tuple(item.brier_score for item in ordered)
    seed_material=(protocol.research_protocol_id,domain.research_domain_id,source_reference_id,role,scope,analysis_boundary,window_start,window_end,tuple(item.probability_source_measurement_id for item in ordered),rule.rule_specification_id,rule.rule_version,confidence,count,algorithm_version)
    seed_digest=_digest(seed_material); limits=[]
    if not scores: return SourcePerformanceUncertainty(scope,None,0,None,None,confidence,count,rule.rule_specification_id,rule.rule_version,algorithm_version,seed_digest,())
    with localcontext() as context: context.prec=PRECISION; point=sum(scores,Decimal(0))/len(scores)
    if len(scores)==1: limits.append("single observation; interval is deterministically degenerate"); lower=upper=point
    elif len(set(scores))==1: limits.append("no observed score variation; interval has zero width"); lower=upper=point
    else:
        rng=random.Random(int(seed_digest,16)); replicates=[]
        for _ in range(count):
            sample=tuple(scores[rng.randrange(len(scores))] for __ in range(len(scores)))
            with localcontext() as context: context.prec=PRECISION; replicates.append(sum(sample,Decimal(0))/len(sample))
        replicates.sort(); alpha=(Decimal(1)-confidence)/2
        lo=int(alpha*count); hi=min(count-1,int((Decimal(1)-alpha)*count))
        lower,upper=replicates[lo],replicates[hi]
    return SourcePerformanceUncertainty(scope,point,len(scores),lower,upper,confidence,count,rule.rule_specification_id,rule.rule_version,algorithm_version,seed_digest,tuple(limits))


def _mean(values: tuple[Decimal,...]) -> Decimal|None:
    if not values:return None
    if Decimal("Infinity") in values:return Decimal("Infinity")
    with localcontext() as context: context.prec=PRECISION; return sum(values,Decimal(0))/len(values)


def _calibration(measurements: tuple[ProbabilitySourceMeasurement,...], rule: VersionedRuleSpecification) -> CalibrationResult:
    if (rule.rule_id,rule.rule_version)!=("calibration-safeguard","2"): _fail("standalone performance requires Calibration v2")
    boundaries=_parameter(rule,"bin_boundaries"); bins=[]
    for index,(lower,upper) in enumerate(zip(boundaries,boundaries[1:])):
        selected=tuple(item for item in measurements if lower<=item.calibration_probability and (item.calibration_probability<=upper if index==9 else item.calibration_probability<upper))
        if selected:
            with localcontext() as context:
                context.prec=PRECISION; mean=sum((item.calibration_probability for item in selected),Decimal(0))/len(selected); observed=Decimal(sum(int(item.realized_outcome_id==item.canonical_proposition_outcome_id) for item in selected))/len(selected); gap=observed-mean
        else:mean=observed=gap=None
        bins.append(CalibrationBin(lower,upper,index==9,len(selected),mean,observed,gap))
    with localcontext() as context: context.prec=PRECISION; wace=None if not measurements else sum((Decimal(item.count)/len(measurements))*abs(item.calibration_gap) for item in bins if item.count and item.calibration_gap is not None)
    return CalibrationResult(rule.rule_specification_id,rule.rule_version,len(measurements),tuple(bins),wace)


@dataclass(frozen=True, slots=True)
class ProbabilitySourcePerformance:
    probability_source_performance_id: str; schema_version: str; identity_algorithm_version: str; analysis_algorithm_version: str
    protocol_id: str; research_domain_id: str; source_reference_id: str; source_role: ProbabilitySourceRole
    analysis_boundary: datetime; measurement_ids: tuple[str,...]; coverage: ProbabilitySourceCoverage; sample_size: int
    mean_brier_score: Decimal|None; mean_log_loss: Decimal|None; calibration: CalibrationResult
    uncertainty: SourcePerformanceUncertainty; limitations: tuple[str,...]; provenance: ResearchContractProvenance; input_digest: str
    def __post_init__(self)->None:
        if self.analysis_algorithm_version!=PERFORMANCE_ALGORITHM_VERSION:_fail("unsupported standalone performance algorithm")
        if self.sample_size!=len(self.measurement_ids) or self.coverage.measurement_ids!=self.measurement_ids:_fail("standalone performance population conflicts with Coverage")
        material=tuple(getattr(self,name) for name in self.__dataclass_fields__ if name not in ("probability_source_performance_id","provenance","input_digest","limitations"))+(_unique(self.limitations,"performance limitations"),)
        digest=_digest(material)
        if self.input_digest!=digest or self.probability_source_performance_id!=f"probability-source-performance:{digest}":_fail("standalone performance identity conflict")


def create_probability_source_performance(*,protocol:ResearchProtocolV2,domain:ResearchDomain,source_reference_id:str,
        analysis_boundary:datetime,measurements:Iterable[ProbabilitySourceMeasurement],coverage:ProbabilitySourceCoverage,
        provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->ProbabilitySourcePerformance:
    if domain!=_broad(protocol):_fail("segmented standalone performance is unsupported",ReasonCode.UNSUPPORTED_STATUS)
    if (coverage.protocol_id,coverage.source_reference_id,coverage.analysis_boundary)!=(protocol.research_protocol_id,source_reference_id,analysis_boundary):_fail("cumulative Coverage authority is incompatible")
    selected=tuple(sorted((item for item in measurements if item.probability_source_measurement_id in set(coverage.measurement_ids) and item.effective_at<=analysis_boundary),key=lambda item:item.probability_source_measurement_id))
    if len(selected)!=len(coverage.measurement_ids):_fail("Coverage references unknown source Measurements")
    role=_role(protocol,source_reference_id); calibration_rule=next((item for item in protocol.supporting_measure_rules if (item.rule_id,item.rule_version)==("calibration-safeguard","2")),None)
    if calibration_rule is None:_fail("Protocol lacks Calibration v2")
    uncertainty=create_source_performance_uncertainty(protocol=protocol,domain=domain,source_reference_id=source_reference_id,role=role,scope="cumulative",analysis_boundary=analysis_boundary,measurements=selected)
    values=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,analysis_algorithm_version=PERFORMANCE_ALGORITHM_VERSION,protocol_id=protocol.research_protocol_id,research_domain_id=domain.research_domain_id,source_reference_id=source_reference_id,source_role=role,analysis_boundary=analysis_boundary,measurement_ids=tuple(item.probability_source_measurement_id for item in selected),coverage=coverage,sample_size=len(selected),mean_brier_score=_mean(tuple(item.brier_score for item in selected)),mean_log_loss=_mean(tuple(item.log_loss for item in selected)),calibration=_calibration(selected,calibration_rule),uncertainty=uncertainty,limitations=_unique(limitations,"performance limitations"),provenance=provenance)
    material=tuple(values[name] for name in ProbabilitySourcePerformance.__dataclass_fields__ if name not in ("probability_source_performance_id","provenance","input_digest","limitations"))+(values["limitations"],);digest=_digest(material)
    return ProbabilitySourcePerformance(f"probability-source-performance:{digest}",**values,input_digest=digest)


@dataclass(frozen=True, slots=True)
class TimeBoundedProbabilitySourcePerformance:
    time_bounded_probability_source_performance_id:str; schema_version:str; identity_algorithm_version:str; analysis_algorithm_version:str
    protocol_id:str; research_domain_id:str; source_reference_id:str; source_role:ProbabilitySourceRole; analysis_boundary:datetime
    surveillance_window_rule_id:str; window_start:datetime; window_end:datetime; measurement_ids:tuple[str,...]
    coverage:ProbabilitySourceCoverage; sample_size:int; mean_brier_score:Decimal|None; mean_log_loss:Decimal|None
    calibration:CalibrationResult; uncertainty:SourcePerformanceUncertainty; limitations:tuple[str,...]; provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        for value in (self.analysis_boundary,self.window_start,self.window_end):_require_aware(value,"time-bounded performance chronology")
        if not self.window_start<self.window_end==self.analysis_boundary:_fail("time-bounded performance requires (start,end] chronology")
        if self.analysis_algorithm_version!=TIME_BOUNDED_PERFORMANCE_ALGORITHM_VERSION:_fail("unsupported time-bounded performance algorithm")
        if self.sample_size!=len(self.measurement_ids) or self.coverage.measurement_ids!=self.measurement_ids:_fail("time-bounded population conflicts with Coverage")
        material=tuple(getattr(self,name) for name in self.__dataclass_fields__ if name not in ("time_bounded_probability_source_performance_id","provenance","input_digest","limitations"))+(_unique(self.limitations,"bounded limitations"),);digest=_digest(material)
        if self.input_digest!=digest or self.time_bounded_probability_source_performance_id!=f"time-bounded-probability-source-performance:{digest}":_fail("time-bounded performance identity conflict")


def create_time_bounded_probability_source_performance(*,protocol:ResearchProtocolV2,domain:ResearchDomain,source_reference_id:str,
        analysis_boundary:datetime,scheduled_start_by_opportunity:Mapping[str,datetime],measurements:Iterable[ProbabilitySourceMeasurement],
        coverage:ProbabilitySourceCoverage,provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->TimeBoundedProbabilitySourcePerformance:
    if domain!=_broad(protocol):_fail("segmented standalone performance is unsupported",ReasonCode.UNSUPPORTED_STATUS)
    rules=tuple(item for item in protocol.surveillance_window_rules if (item.rule_id,item.rule_version)==("rolling-days","2"))
    if len(rules)!=1:_fail("exactly one rolling-days v2 rule is required")
    if coverage.protocol_id!=protocol.research_protocol_id or coverage.source_reference_id!=source_reference_id or coverage.analysis_boundary!=analysis_boundary:_fail("bounded Coverage authority is incompatible")
    if set(scheduled_start_by_opportunity)!=set(coverage.universe_opportunity_ids):_fail("time-bounded performance requires complete exact schedule authority")
    if any(not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None for value in scheduled_start_by_opportunity.values()):_fail("time-bounded schedule authority requires timezone-aware timestamps")
    rule=rules[0];end=analysis_boundary;start=end-timedelta(days=_parameter(rule,"days"))
    bounded_opps={oid for oid in coverage.universe_opportunity_ids if start<scheduled_start_by_opportunity[oid]<=end}
    def subset(values):return tuple(item for item in values if item in bounded_opps)
    memberships=(subset(coverage.universe_opportunity_ids),subset(coverage.capture_not_yet_due_opportunity_ids),subset(coverage.protocol_ineligible_opportunity_ids),subset(coverage.eligible_denominator_opportunity_ids),subset(coverage.source_capture_missing_opportunity_ids),subset(coverage.source_capture_invalid_opportunity_ids),subset(coverage.outside_capture_tolerance_opportunity_ids),subset(coverage.derivation_invalid_opportunity_ids),subset(coverage.outcome_ineligible_opportunity_ids),subset(coverage.measured_opportunity_ids),tuple(mid for oid,mid in zip(coverage.measured_opportunity_ids,coverage.measurement_ids) if oid in bounded_opps),tuple(item for item in coverage.reason_codes if item[0] in bounded_opps))
    bounded=_make_coverage(protocol_id=protocol.research_protocol_id,source_reference_id=source_reference_id,
        analysis_boundary=analysis_boundary,memberships=memberships,provenance=provenance)
    selected=tuple(sorted((item for item in measurements if item.probability_source_measurement_id in set(bounded.measurement_ids) and item.effective_at<=analysis_boundary),key=lambda item:item.probability_source_measurement_id));role=_role(protocol,source_reference_id)
    calibration_rule=next(item for item in protocol.supporting_measure_rules if (item.rule_id,item.rule_version)==("calibration-safeguard","2"))
    uncertainty=create_source_performance_uncertainty(protocol=protocol,domain=domain,source_reference_id=source_reference_id,role=role,scope="time-bounded",analysis_boundary=analysis_boundary,window_start=start,window_end=end,measurements=selected,algorithm_version=TIME_BOUNDED_PERFORMANCE_ALGORITHM_VERSION)
    values=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,analysis_algorithm_version=TIME_BOUNDED_PERFORMANCE_ALGORITHM_VERSION,protocol_id=protocol.research_protocol_id,research_domain_id=domain.research_domain_id,source_reference_id=source_reference_id,source_role=role,analysis_boundary=analysis_boundary,surveillance_window_rule_id=rule.rule_specification_id,window_start=start,window_end=end,measurement_ids=tuple(item.probability_source_measurement_id for item in selected),coverage=bounded,sample_size=len(selected),mean_brier_score=_mean(tuple(item.brier_score for item in selected)),mean_log_loss=_mean(tuple(item.log_loss for item in selected)),calibration=_calibration(selected,calibration_rule),uncertainty=uncertainty,limitations=_unique(limitations,"bounded limitations"),provenance=provenance)
    material=tuple(values[name] for name in TimeBoundedProbabilitySourcePerformance.__dataclass_fields__ if name not in ("time_bounded_probability_source_performance_id","provenance","input_digest","limitations"))+(values["limitations"],);digest=_digest(material)
    return TimeBoundedProbabilitySourcePerformance(f"time-bounded-probability-source-performance:{digest}",**values,input_digest=digest)


@dataclass(frozen=True,slots=True,order=True)
class ProbabilitySourcePerformanceReference:
    performance_id:str;contract_version:str;protocol_id:str;research_domain_id:str;source_reference_id:str;source_role:ProbabilitySourceRole;analysis_boundary:datetime
    @classmethod
    def from_performance(cls,item:ProbabilitySourcePerformance):return cls(item.probability_source_performance_id,"2",item.protocol_id,item.research_domain_id,item.source_reference_id,item.source_role,item.analysis_boundary)
    def __post_init__(self):
        if self.contract_version!="2":_fail("unsupported standalone performance reference")
        _require_aware(self.analysis_boundary,"performance reference boundary")


@dataclass(frozen=True,slots=True,order=True)
class TimeBoundedProbabilitySourcePerformanceReference:
    performance_id:str;contract_version:str;protocol_id:str;research_domain_id:str;source_reference_id:str;source_role:ProbabilitySourceRole;analysis_boundary:datetime;surveillance_window_rule_id:str;window_start:datetime;window_end:datetime
    @classmethod
    def from_performance(cls,item:TimeBoundedProbabilitySourcePerformance):return cls(item.time_bounded_probability_source_performance_id,"2",item.protocol_id,item.research_domain_id,item.source_reference_id,item.source_role,item.analysis_boundary,item.surveillance_window_rule_id,item.window_start,item.window_end)
    def __post_init__(self):
        if self.contract_version!="2":_fail("unsupported bounded performance reference")
        if not self.window_start<self.window_end==self.analysis_boundary:_fail("bounded performance reference chronology conflict")


@dataclass(frozen=True,slots=True,order=True)
class ComparativePerformanceReferenceV2:
    performance_id:str;contract_version:str;protocol_id:str;claim_protocol_id:str;edge_claim_id:str;research_domain_id:str
    benchmark_source_reference_id:str;challenger_source_reference_id:str;analysis_boundary:datetime;algorithm_version:str;population_digest:str
    @classmethod
    def from_performance(cls,item:ComparativePerformanceV2):return cls(item.comparative_performance_id,"2",item.protocol_id,item.claim_protocol_id,item.edge_claim_id,item.research_domain_id,item.benchmark_source_reference_id,item.challenger_source_reference_id,item.analysis_boundary,item.analysis_algorithm_version,item.population_digest)
    def __post_init__(self):
        if self.contract_version!="2" or self.algorithm_version!=PAIRED_PERFORMANCE_ALGORITHM_VERSION:_fail("unsupported paired cumulative reference generation")
        _require_aware(self.analysis_boundary,"paired cumulative reference boundary")


@dataclass(frozen=True,slots=True,order=True)
class TimeBoundedComparativePerformanceReferenceV2:
    performance_id:str;contract_version:str;protocol_id:str;claim_protocol_id:str;edge_claim_id:str;research_domain_id:str
    benchmark_source_reference_id:str;challenger_source_reference_id:str;analysis_boundary:datetime;algorithm_version:str;population_digest:str
    surveillance_window_rule_id:str;window_start:datetime;window_end:datetime
    @classmethod
    def from_performance(cls,item:TimeBoundedComparativePerformanceV2):return cls(item.time_bounded_comparative_performance_id,"2",item.protocol_id,item.claim_protocol_id,item.edge_claim_id,item.research_domain_id,item.benchmark_source_reference_id,item.challenger_source_reference_id,item.analysis_boundary,item.analysis_algorithm_version,item.population_digest,item.surveillance_window_rule_id,item.window_start,item.window_end)
    def __post_init__(self):
        if self.contract_version!="2" or self.algorithm_version!=PAIRED_TIME_BOUNDED_ALGORITHM_VERSION or not self.window_start<self.window_end==self.analysis_boundary:_fail("unsupported paired bounded reference generation")


@dataclass(frozen=True,slots=True,order=True)
class ComparativeDriftAnalysisReferenceV2:
    drift_id:str;contract_version:str;protocol_id:str;claim_protocol_id:str;edge_claim_id:str;research_domain_id:str;analysis_boundary:datetime
    algorithm_version:str;historical_performance_id:str;current_bounded_performance_id:str;historical_population_digest:str;current_population_digest:str
    @classmethod
    def from_analysis(cls,item:ComparativeDriftAnalysisV2):return cls(item.comparative_drift_analysis_id,"2",item.protocol_id,item.claim_protocol_id,item.edge_claim_id,item.research_domain_id,item.analysis_boundary,item.analysis_algorithm_version,item.historical_performance_id,item.current_bounded_performance_id,item.historical_population_digest,item.current_population_digest)
    def __post_init__(self):
        if self.contract_version!="2" or self.algorithm_version!=PAIRED_DRIFT_ALGORITHM_VERSION:_fail("unsupported paired Drift reference generation")
        _require_aware(self.analysis_boundary,"paired Drift reference boundary")


@dataclass(frozen=True,slots=True,order=True)
class ReportClaimFindingV2:
    edge_claim_id:str;cumulative:ComparativePerformanceReferenceV2
    time_bounded:TimeBoundedComparativePerformanceReferenceV2;drift:ComparativeDriftAnalysisReferenceV2
    def __post_init__(self):
        if self.edge_claim_id!=self.cumulative.edge_claim_id or self.edge_claim_id!=self.time_bounded.edge_claim_id or self.edge_claim_id!=self.drift.edge_claim_id:_fail("report finding claim references conflict")
        if self.drift.current_bounded_performance_id!=self.time_bounded.performance_id or self.drift.current_population_digest!=self.time_bounded.population_digest:_fail("report finding Drift population conflict")
@dataclass(frozen=True,slots=True)
class ComparativePerformanceReportV2:
    comparative_performance_report_id:str;schema_version:str;identity_algorithm_version:str;contract_version:str;report_algorithm_version:str
    protocol_id:str;protocol_claim_set_id:str;analysis_boundary:datetime
    cumulative_benchmark_reference:ProbabilitySourcePerformanceReference
    time_bounded_benchmark_reference:TimeBoundedProbabilitySourcePerformanceReference
    claim_findings:tuple[ReportClaimFindingV2,...];limitations:tuple[str,...];provenance:ResearchContractProvenance;input_digest:str
    @classmethod
    def create(cls,*,protocol:ResearchProtocolV2,protocol_claim_set:ProtocolClaimSet,analysis_boundary:datetime,
            cumulative:ProbabilitySourcePerformance,time_bounded:TimeBoundedProbabilitySourcePerformance,
            claims:Iterable[EdgeClaim],paired_cumulative:Iterable[ComparativePerformanceV2],
            paired_time_bounded:Iterable[TimeBoundedComparativePerformanceV2],paired_drift:Iterable[ComparativeDriftAnalysisV2],
            provenance:ResearchContractProvenance,limitations:tuple[str,...]=()):
        c=ProbabilitySourcePerformanceReference.from_performance(cumulative);b=TimeBoundedProbabilitySourcePerformanceReference.from_performance(time_bounded)
        common=(protocol.research_protocol_id,_broad(protocol).research_domain_id,protocol.market_benchmark.probability_source_reference_id,ProbabilitySourceRole.MARKET_BENCHMARK,analysis_boundary)
        if (c.protocol_id,c.research_domain_id,c.source_reference_id,c.source_role,c.analysis_boundary)!=common or (b.protocol_id,b.research_domain_id,b.source_reference_id,b.source_role,b.analysis_boundary)!=common:_fail("report v2 standalone references are incompatible")
        if protocol_claim_set.protocol_id!=protocol.base_protocol.research_protocol_id or protocol_claim_set.effective_at>analysis_boundary:_fail("report v2 Claim Set authority is incompatible")
        claim_values=tuple(claims);claim_by_id={item.edge_claim_id:item for item in claim_values}
        if len(claim_by_id)!=len(claim_values) or set(claim_by_id)!=set(protocol_claim_set.edge_claim_ids):_fail("report v2 claims must equal authoritative Claim Set")
        pc=tuple(paired_cumulative);pb=tuple(paired_time_bounded);pd=tuple(paired_drift)
        if len({item.comparative_performance_id for item in pc})!=len(pc) or len({item.time_bounded_comparative_performance_id for item in pb})!=len(pb) or len({item.comparative_drift_analysis_id for item in pd})!=len(pd):_fail("report v2 paired registries contain duplicate authority")
        findings=[]
        for claim_id in protocol_claim_set.edge_claim_ids:
            claim=claim_by_id[claim_id]
            cs=tuple(item for item in pc if item.edge_claim_id==claim_id and item.analysis_boundary==analysis_boundary)
            bs=tuple(item for item in pb if item.edge_claim_id==claim_id and item.analysis_boundary==analysis_boundary)
            ds=tuple(item for item in pd if item.edge_claim_id==claim_id and item.analysis_boundary==analysis_boundary)
            if (len(cs),len(bs),len(ds))!=(1,1,1):_fail("report v2 requires one paired cumulative, bounded, and Drift authority per claim")
            cp,bp,dp=cs[0],bs[0],ds[0]
            expected=(protocol.research_protocol_id,protocol.base_protocol.research_protocol_id,claim_id,claim.research_domain_id,claim.benchmark_source_reference_id,claim.challenger_source_reference_id,analysis_boundary)
            if (cp.protocol_id,cp.claim_protocol_id,cp.edge_claim_id,cp.research_domain_id,cp.benchmark_source_reference_id,cp.challenger_source_reference_id,cp.analysis_boundary)!=expected or (bp.protocol_id,bp.claim_protocol_id,bp.edge_claim_id,bp.research_domain_id,bp.benchmark_source_reference_id,bp.challenger_source_reference_id,bp.analysis_boundary)!=expected:_fail("report v2 paired authority compatibility conflict")
            historical=next((item for item in pc if item.comparative_performance_id==dp.historical_performance_id),None)
            if dp.protocol_id!=protocol.research_protocol_id or dp.claim_protocol_id!=protocol.base_protocol.research_protocol_id or dp.edge_claim_id!=claim_id or dp.research_domain_id!=claim.research_domain_id or historical is None or historical.analysis_boundary!=bp.window_start or dp.current_bounded_performance_id!=bp.time_bounded_comparative_performance_id:_fail("report v2 Drift authority conflict")
            findings.append(ReportClaimFindingV2(claim_id,ComparativePerformanceReferenceV2.from_performance(cp),TimeBoundedComparativePerformanceReferenceV2.from_performance(bp),ComparativeDriftAnalysisReferenceV2.from_analysis(dp)))
        findings=tuple(findings);limits=_unique(limitations,"report v2 limitations")
        values=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,contract_version=REPORT_CONTRACT_VERSION,report_algorithm_version=REPORT_ALGORITHM_VERSION,protocol_id=protocol.research_protocol_id,protocol_claim_set_id=protocol_claim_set.protocol_claim_set_id,analysis_boundary=analysis_boundary,cumulative_benchmark_reference=c,time_bounded_benchmark_reference=b,claim_findings=findings,limitations=limits,provenance=provenance)
        material=tuple(values[name] for name in cls.__dataclass_fields__ if name not in ("comparative_performance_report_id","provenance","input_digest","limitations"))+(limits,);digest=_digest(material)
        return cls(f"comparative-performance-report-v2:{digest}",**values,input_digest=digest)
    def __post_init__(self):
        if self.contract_version!="2" or self.report_algorithm_version!="2":_fail("unsupported report v2 generation")
        material=tuple(getattr(self,name) for name in self.__dataclass_fields__ if name not in ("comparative_performance_report_id","provenance","input_digest","limitations"))+(_unique(self.limitations,"report v2 limitations"),);digest=_digest(material)
        if self.input_digest!=digest or self.comparative_performance_report_id!=f"comparative-performance-report-v2:{digest}":_fail("report v2 identity conflict")


def validate_research_snapshot_v2_authority(*,snapshot:ResearchSnapshotV2,protocol:ResearchProtocolV2,
        opportunity:ResearchCaptureOpportunity,schedule:OutcomeObservation,
        forecast_observations:Mapping[str,Any],market_observations:Mapping[str,MarketObservation])->None:
    """Reproduce v2 Snapshot schedule, capture, and synchronization authority."""
    if snapshot.protocol_id!=protocol.research_protocol_id or opportunity.protocol_id!=protocol.research_protocol_id:
        _fail("Snapshot references cross-Protocol opportunity authority")
    if snapshot.research_capture_opportunity_id!=opportunity.research_capture_opportunity_id:
        _fail("Snapshot references incompatible capture opportunity")
    if schedule.observation_id!=opportunity.schedule_observation_id or schedule.canonical_event_id!=snapshot.canonical_event_id:
        _fail("Snapshot schedule lineage conflicts with capture opportunity")
    if schedule.authoritative_provider_id!=_parameter(protocol.outcome_resolution_rule,"source_id"):
        _fail("Snapshot Schedule Evidence is not Protocol-authoritative")
    if schedule.collected_at>snapshot.target_capture_at:_fail("Snapshot uses Schedule Evidence unavailable at its capture boundary")
    if snapshot.proposition_type!=opportunity.proposition_type or snapshot.scheduled_start!=schedule.scheduled_start:
        _fail("Snapshot interpretation conflicts with Schedule Evidence")
    offset=_parameter(protocol.snapshot_timing_rule,"seconds_before_start")
    if snapshot.target_capture_at!=schedule.scheduled_start-timedelta(seconds=offset):
        _fail("Snapshot target capture time conflicts with Protocol")
    authorized={protocol.market_benchmark.probability_source_reference_id,
                *(item.probability_source_reference_id for item in protocol.alternative_sources)}
    captures={item.probability_source_reference_id:item for item in snapshot.source_captures}
    if len(captures)!=len(snapshot.source_captures) or set(captures)!=authorized:
        _fail("Snapshot must preserve exactly one capture result for every Protocol source")
    sources={item.probability_source_reference_id:item for item in (protocol.market_benchmark,)+protocol.alternative_sources}
    tolerance=timedelta(seconds=_parameter(protocol.capture_tolerance_rule,"seconds"))
    for source_id,capture in captures.items():
        if capture.disposition is SourceCaptureDispositionV2.MISSING:continue
        assert capture.evidence_reference is not None and capture.observed_at is not None
        outside=abs(capture.observed_at-snapshot.target_capture_at)>tolerance
        if outside!=(capture.disposition is SourceCaptureDispositionV2.OUTSIDE_CAPTURE_TOLERANCE):
            _fail("source capture disposition conflicts with Protocol tolerance")
        if capture.evidence_reference.evidence_kind is SourceEvidenceKind.MARKET_OBSERVATION:
            evidence=market_observations.get(capture.evidence_reference.evidence_id)
            if source_id!=protocol.market_benchmark.probability_source_reference_id or evidence is None:
                _fail("Snapshot Market capture references incompatible Evidence")
            if (evidence.canonical_event_id,evidence.collected_at,evidence.provenance.provider)!=(
                    snapshot.canonical_event_id,capture.observed_at,protocol.market_benchmark.provider_id):
                _fail("Market Evidence lineage conflicts with Snapshot capture")
        else:
            evidence=forecast_observations.get(capture.evidence_reference.evidence_id);source=sources[source_id]
            if evidence is None or source_id==protocol.market_benchmark.probability_source_reference_id:
                _fail("Snapshot Forecast capture references incompatible Evidence")
            if (evidence.provenance.provider,evidence.version_id,evidence.distribution.canonical_event_id,
                    evidence.schedule_observation_id,evidence.collected_at)!=(source.provider_id,source.model_or_product_version,
                    snapshot.canonical_event_id,opportunity.schedule_observation_id,capture.observed_at):
                _fail("Forecast Evidence lineage conflicts with Snapshot capture")
    expected_challengers={item.probability_source_reference_id for item in protocol.alternative_sources}
    pairs={item.challenger_source_reference_id:item for item in snapshot.pairwise_synchronization}
    if len(pairs)!=len(snapshot.pairwise_synchronization) or set(pairs)!=expected_challengers:
        _fail("Snapshot requires exactly one synchronization result for every challenger")
    for challenger_id,pair in pairs.items():
        expected=create_pairwise_synchronization_v2(protocol=protocol,snapshot=snapshot,opportunity=opportunity,
            challenger_source_reference_id=challenger_id,forecast_observations=forecast_observations.values(),
            market_observations=market_observations.values())
        if pair!=expected:_fail("Snapshot synchronization does not reproduce from captured Evidence")


def validate_standalone_research_graph(*, protocols:Iterable[ResearchProtocolV2],
        opportunities:Iterable[ResearchCaptureOpportunity],eligibility_results:Iterable[CaptureBoundaryEligibility],
        eligibility_contexts:Iterable[ResearchEventEligibilityContext],
        snapshots:Iterable[ResearchSnapshotV2],market_observations:Iterable[MarketObservation],
        forecast_observations:Iterable[Any],evaluation_eligibility_decisions:Iterable[EvaluationEligibilityDecision],
        forecast_evaluations:Iterable[ForecastEvaluation],
        market_series:Iterable[ProviderMarketSeries],derivations:Iterable[MarketProbabilityDerivation],
        outcome_histories:Iterable[OutcomeHistory],measurements:Iterable[ProbabilitySourceMeasurement],
        comparative_measurements:Iterable[ComparativeMeasurementV2]=(),
        coverages:Iterable[ProbabilitySourceCoverage],cumulative_performances:Iterable[ProbabilitySourcePerformance],
        bounded_performances:Iterable[TimeBoundedProbabilitySourcePerformance],claims:Iterable[EdgeClaim]=(),
        protocol_claim_sets:Iterable[ProtocolClaimSet]=(),paired_cumulative:Iterable[ComparativePerformanceV2]=(),
        paired_bounded:Iterable[TimeBoundedComparativePerformanceV2]=(),paired_drift:Iterable[ComparativeDriftAnalysisV2]=(),
        scheduled_start_by_opportunity:Mapping[str,datetime],scheduled_start_by_snapshot:Mapping[str,datetime],
        reports:Iterable[ComparativePerformanceReportV2]=())->None:
    """Pure fail-closed registry and lineage validation for the PR16B graph."""
    def registry(values,label,key):
        supplied=tuple(values);result={}
        for item in supplied:
            identity=key(item)
            if identity in result:_fail(f"{label} contains duplicate or conflicting authority")
            result[identity]=item
        return result
    protocol_map=registry(protocols,"Protocol v2 registry",lambda item:item.research_protocol_id)
    opportunity_map=registry(opportunities,"opportunity registry",lambda item:item.research_capture_opportunity_id)
    eligibility_map=registry(eligibility_results,"capture eligibility registry",lambda item:item.capture_boundary_eligibility_id)
    context_map=registry(eligibility_contexts,"capture eligibility context registry",lambda item:item.research_event_eligibility_context_id)
    snapshot_map=registry(snapshots,"Snapshot v2 registry",lambda item:item.research_snapshot_id)
    observation_map=registry(market_observations,"Market Observation registry",lambda item:item.observation_id)
    series_map=registry(market_series,"Market Series registry",lambda item:item.series_id)
    derivation_map=registry(derivations,"market derivation registry",lambda item:item.market_probability_derivation_id)
    forecast_map=registry(forecast_observations,"Forecast Observation registry",lambda item:item.observation_id)
    decision_map=registry(evaluation_eligibility_decisions,"Evaluation eligibility registry",lambda item:item.decision_id)
    evaluation_map=registry(forecast_evaluations,"Forecast Evaluation registry",lambda item:item.evaluation_id)
    history_map=registry(outcome_histories,"Outcome History registry",lambda item:item.canonical_event_id)
    outcome_map={item.observation_id:item for history in history_map.values() for item in history.observations}
    if len(outcome_map)!=sum(len(history.observations) for history in history_map.values()):_fail("Outcome histories contain conflicting observation authority")
    measurement_map=registry(measurements,"source Measurement registry",lambda item:item.probability_source_measurement_id)
    comparative_map=registry(comparative_measurements,"Comparative Measurement v2 registry",lambda item:item.comparative_measurement_id)
    performance_map=registry(cumulative_performances,"standalone performance registry",lambda item:item.probability_source_performance_id)
    bounded_map=registry(bounded_performances,"bounded standalone registry",lambda item:item.time_bounded_probability_source_performance_id)
    claim_map=registry(claims,"Edge Claim registry",lambda item:item.edge_claim_id);claim_set_map=registry(protocol_claim_sets,"Claim Set registry",lambda item:item.protocol_claim_set_id)
    paired_performance_map=registry(paired_cumulative,"paired cumulative registry",lambda item:item.comparative_performance_id)
    paired_bounded_map=registry(paired_bounded,"paired bounded registry",lambda item:item.time_bounded_comparative_performance_id)
    paired_drift_map=registry(paired_drift,"paired Drift registry",lambda item:item.comparative_drift_analysis_id)
    validate_snapshot_lineages_v2(snapshot_map.values())
    for snapshot in snapshot_map.values():
        if snapshot.protocol_id not in protocol_map or snapshot.research_capture_opportunity_id not in opportunity_map:_fail("Snapshot v2 references unknown Protocol or opportunity")
        opportunity=opportunity_map[snapshot.research_capture_opportunity_id]
        schedule=outcome_map.get(opportunity.schedule_observation_id)
        if schedule is None:_fail("Snapshot v2 references unknown Schedule Evidence")
        validate_research_snapshot_v2_authority(snapshot=snapshot,protocol=protocol_map[snapshot.protocol_id],
            opportunity=opportunity,schedule=schedule,forecast_observations=forecast_map,market_observations=observation_map)
        for capture in snapshot.source_captures:
            if capture.evidence_reference and capture.evidence_reference.evidence_kind is SourceEvidenceKind.MARKET_OBSERVATION:
                evidence=validate_source_evidence_reference(capture.evidence_reference,market_observations=observation_map.values())
                if capture.observed_at!=evidence.collected_at:_fail("Market Evidence chronology conflicts with source capture")
            if capture.evidence_reference and capture.evidence_reference.evidence_kind is SourceEvidenceKind.FORECAST_OBSERVATION:
                evidence=validate_source_evidence_reference(capture.evidence_reference,forecast_observations=forecast_map.values())
                if capture.observed_at!=evidence.collected_at:_fail("Forecast Evidence chronology conflicts with source capture")
    for derivation in derivation_map.values():
        if derivation.protocol_id not in protocol_map or derivation.research_snapshot_id not in snapshot_map or derivation.market_observation_id not in observation_map or derivation.market_series_id not in series_map:_fail("market derivation references unknown authority")
        snapshot=snapshot_map[derivation.research_snapshot_id];opportunity=opportunity_map.get(snapshot.research_capture_opportunity_id)
        schedule=None if opportunity is None else outcome_map.get(opportunity.schedule_observation_id)
        if opportunity is None or schedule is None:_fail("market derivation lacks Snapshot Schedule authority")
        recreated=create_market_probability_derivation(protocol=protocol_map[derivation.protocol_id],snapshot=snapshot,
            opportunity=opportunity,schedule_evidence=schedule,forecast_observations=forecast_map.values(),market_observations=observation_map.values(),
            observation=observation_map[derivation.market_observation_id],series=series_map[derivation.market_series_id],effective_at=derivation.effective_at,provenance=derivation.provenance,limitations=derivation.limitations)
        if recreated!=derivation:_fail("market derivation fails authoritative replay")
    for measurement in measurement_map.values():
        if measurement.protocol_id not in protocol_map or measurement.research_snapshot_id not in snapshot_map or measurement.outcome_observation_id not in outcome_map:_fail("source Measurement references unknown authority")
        if measurement.source_input_kind is SourceMeasurementInputKind.MARKET_PROBABILITY_DERIVATION and measurement.source_input_id not in derivation_map:_fail("source Measurement references unknown derivation")
        protocol=protocol_map[measurement.protocol_id];snapshot=snapshot_map[measurement.research_snapshot_id];outcome=outcome_map[measurement.outcome_observation_id]
        if measurement.source_input_kind is SourceMeasurementInputKind.MARKET_PROBABILITY_DERIVATION:
            recreated=create_market_backed_source_measurement(protocol=protocol,snapshot=snapshot,derivation=derivation_map[measurement.source_input_id],outcome=outcome,effective_at=measurement.effective_at,provenance=measurement.provenance)
        else:
            evaluation=evaluation_map.get(measurement.source_input_id)
            source=next((item for item in protocol.alternative_sources if item.probability_source_reference_id==measurement.source_reference_id),None)
            if evaluation is None or source is None:_fail("forecast-backed Measurement references unknown authority")
            forecast=forecast_map.get(evaluation.forecast_observation_id);decision=decision_map.get(evaluation.eligibility_decision_id);history=history_map.get(outcome.canonical_event_id)
            if forecast is None or decision is None or history is None:_fail("Forecast Evaluation lacks complete Evidence or eligibility authority")
            recreated_decision=decide_evaluation_eligibility(forecast,outcome,outcome_history=history)
            if recreated_decision!=decision:_fail("Evaluation eligibility decision fails authoritative replay")
            recreated_evaluation=create_forecast_evaluation(forecast,outcome,decision,provider_id=source.provider_id,
                model_id=source.model_or_product_id,model_version_id=source.model_or_product_version)
            if recreated_evaluation!=evaluation:_fail("Forecast Evaluation fails authoritative Evidence replay")
            recreated=create_forecast_backed_source_measurement(protocol=protocol,snapshot=snapshot,source_reference=source,evaluation=evaluation,outcome=outcome,effective_at=measurement.effective_at,provenance=measurement.provenance)
        if recreated!=measurement:_fail("source Measurement fails authoritative replay")
    for paired in comparative_map.values():
        if paired.protocol_id not in protocol_map or paired.benchmark_measurement_id not in measurement_map or paired.challenger_measurement_id not in measurement_map:_fail("Comparative Measurement v2 references unknown source authority")
        benchmark=measurement_map[paired.benchmark_measurement_id];challenger=measurement_map[paired.challenger_measurement_id]
        if paired.benchmark_probability!=dict(benchmark.probability_distribution)[benchmark.canonical_proposition_outcome_id] or paired.challenger_probability!=dict(challenger.probability_distribution)[challenger.canonical_proposition_outcome_id] or paired.benchmark_brier_score!=benchmark.brier_score or paired.challenger_brier_score!=challenger.brier_score:_fail("Comparative Measurement v2 does not project source authority exactly")
        snapshot=snapshot_map[paired.research_snapshot_id]
        synchronization=next((item for item in snapshot.pairwise_synchronization if item.challenger_source_reference_id==challenger.source_reference_id),None)
        opportunity=opportunity_map.get(snapshot.research_capture_opportunity_id)
        schedule=None if opportunity is None else outcome_map.get(opportunity.schedule_observation_id)
        if synchronization is None or opportunity is None or schedule is None or create_comparative_measurement_v2(
                protocol=protocol_map[paired.protocol_id],benchmark=benchmark,challenger=challenger,
                snapshot=snapshot,opportunity=opportunity,schedule_evidence=schedule,forecast_observations=forecast_map.values(),
                market_observations=observation_map.values(),effective_at=paired.effective_at,
                provenance=paired.provenance,limitations=paired.limitations)!=paired:
            _fail("Comparative Measurement v2 fails replay")
    for eligibility in eligibility_map.values():
        if eligibility.protocol_id not in protocol_map or eligibility.research_capture_opportunity_id not in opportunity_map:_fail("capture eligibility references unknown authority")
        if len(eligibility.context_evidence_ids)!=1 or eligibility.context_evidence_ids[0] not in context_map:_fail("capture eligibility references unknown context")
        recreated=evaluate_capture_boundary_eligibility(protocol=protocol_map[eligibility.protocol_id],opportunity=opportunity_map[eligibility.research_capture_opportunity_id],context=context_map[eligibility.context_evidence_ids[0]],provenance=eligibility.provenance)
        if recreated!=eligibility:_fail("capture eligibility fails deterministic replay")
    coverage_map=registry(coverages,"Coverage registry",lambda item:item.probability_source_coverage_id);coverage_values=tuple(coverage_map.values())
    for coverage in coverage_values:
        if not set(coverage.universe_opportunity_ids)<=set(opportunity_map) or not set(coverage.measurement_ids)<=set(measurement_map):_fail("Coverage references unknown population authority")
        protocol=protocol_map.get(coverage.protocol_id)
        if protocol is None:_fail("Coverage references unknown Protocol")
        recreated=create_probability_source_coverage(protocol=protocol,source_reference_id=coverage.source_reference_id,analysis_boundary=coverage.analysis_boundary,
            opportunities=tuple(item for item in opportunity_map.values() if item.protocol_id==protocol.research_protocol_id),
            eligibility_results=tuple(item for item in eligibility_map.values() if item.protocol_id==protocol.research_protocol_id),
            eligibility_contexts=context_map.values(),snapshots=tuple(item for item in snapshot_map.values() if item.protocol_id==protocol.research_protocol_id),
            market_observations=observation_map.values(),market_series=series_map.values(),forecast_observations=forecast_map.values(),
            evaluation_eligibility_decisions=decision_map.values(),forecast_evaluations=evaluation_map.values(),
            derivations=tuple(item for item in derivation_map.values() if item.protocol_id==protocol.research_protocol_id),outcome_histories=history_map.values(),
            measurements=tuple(item for item in measurement_map.values() if item.protocol_id==protocol.research_protocol_id))
        if recreated!=coverage:_fail("Coverage does not reproduce from complete graph authority")
    for performance in performance_map.values():
        if performance.protocol_id not in protocol_map or not set(performance.measurement_ids)<=set(measurement_map):_fail("standalone performance references unknown authority")
        protocol=protocol_map[performance.protocol_id];domain=next((item for item in protocol.base_protocol.research_domains if item.research_domain_id==performance.research_domain_id),None)
        coverage=next((item for item in coverage_values if item.probability_source_coverage_id==performance.coverage.probability_source_coverage_id),None)
        if domain is None or coverage is None:_fail("standalone performance lacks domain or Coverage authority")
        if create_probability_source_performance(protocol=protocol,domain=domain,source_reference_id=performance.source_reference_id,analysis_boundary=performance.analysis_boundary,measurements=measurement_map.values(),coverage=coverage,provenance=performance.provenance,limitations=performance.limitations)!=performance:_fail("standalone performance fails replay")
    for bounded in bounded_map.values():
        if bounded.protocol_id not in protocol_map or not set(bounded.measurement_ids)<=set(measurement_map):_fail("bounded standalone performance references unknown authority")
        protocol=protocol_map[bounded.protocol_id];domain=next((item for item in protocol.base_protocol.research_domains if item.research_domain_id==bounded.research_domain_id),None)
        if domain is None:_fail("bounded standalone performance references unknown domain")
        source_coverage=next((item for item in coverage_values if item.protocol_id==bounded.protocol_id and item.source_reference_id==bounded.source_reference_id and item.analysis_boundary==bounded.analysis_boundary),None)
        if source_coverage is None:_fail("bounded standalone performance lacks cumulative Coverage authority")
        recreated=create_time_bounded_probability_source_performance(protocol=protocol,domain=domain,source_reference_id=bounded.source_reference_id,analysis_boundary=bounded.analysis_boundary,scheduled_start_by_opportunity=scheduled_start_by_opportunity,measurements=measurement_map.values(),coverage=source_coverage,provenance=bounded.provenance,limitations=bounded.limitations)
        if recreated!=bounded:_fail("bounded standalone performance fails replay")
    for paired_performance in paired_performance_map.values():
        protocol=protocol_map.get(paired_performance.protocol_id);claim=claim_map.get(paired_performance.edge_claim_id)
        domain=None if protocol is None else next((item for item in protocol.base_protocol.research_domains if item.research_domain_id==paired_performance.research_domain_id),None)
        if protocol is None or claim is None or domain is None:_fail("paired cumulative references unknown authority")
        recreated=create_comparative_performance_v2(protocol=protocol,edge_claim=claim,domain=domain,analysis_boundary=paired_performance.analysis_boundary,measurements=comparative_map.values(),source_measurements=measurement_map.values(),provenance=paired_performance.provenance,limitations=paired_performance.limitations)
        if recreated!=paired_performance:_fail("paired cumulative Performance fails replay")
    for paired_window in paired_bounded_map.values():
        protocol=protocol_map.get(paired_window.protocol_id);claim=claim_map.get(paired_window.edge_claim_id)
        domain=None if protocol is None else next((item for item in protocol.base_protocol.research_domains if item.research_domain_id==paired_window.research_domain_id),None)
        if protocol is None or claim is None or domain is None:_fail("paired bounded references unknown authority")
        recreated=create_time_bounded_comparative_performance_v2(protocol=protocol,edge_claim=claim,domain=domain,analysis_boundary=paired_window.analysis_boundary,measurements=comparative_map.values(),source_measurements=measurement_map.values(),scheduled_start_by_snapshot=scheduled_start_by_snapshot,provenance=paired_window.provenance)
        if recreated!=paired_window:_fail("paired bounded Performance fails replay")
    for drift in paired_drift_map.values():
        historical=paired_performance_map.get(drift.historical_performance_id);current=paired_bounded_map.get(drift.current_bounded_performance_id)
        if historical is None or current is None or create_comparative_drift_analysis_v2(protocol=protocol_map[drift.protocol_id],historical=historical,current=current,measurements=comparative_map.values(),provenance=drift.provenance)!=drift:_fail("paired Drift fails authoritative replay")
    report_map=registry(reports,"report v2 registry",lambda item:item.comparative_performance_report_id)
    for report in report_map.values():
        if report.protocol_id not in protocol_map or report.cumulative_benchmark_reference.performance_id not in performance_map or report.time_bounded_benchmark_reference.performance_id not in bounded_map:_fail("report v2 references unknown standalone authority")
        claim_set=claim_set_map.get(report.protocol_claim_set_id)
        if claim_set is None:_fail("report v2 references unknown Claim Set")
        recreated=ComparativePerformanceReportV2.create(protocol=protocol_map[report.protocol_id],protocol_claim_set=claim_set,analysis_boundary=report.analysis_boundary,cumulative=performance_map[report.cumulative_benchmark_reference.performance_id],time_bounded=bounded_map[report.time_bounded_benchmark_reference.performance_id],claims=claim_map.values(),paired_cumulative=paired_performance_map.values(),paired_time_bounded=paired_bounded_map.values(),paired_drift=paired_drift_map.values(),provenance=report.provenance,limitations=report.limitations)
        if recreated!=report:_fail("report v2 fails complete typed-reference replay")


_CONTRACTS=(ResearchProtocolV2,SourceEvidenceReference,SourceCaptureV2,ResearchSnapshotV2,CaptureBoundaryEligibility,
MarketProbabilityLevel,MarketProbabilityBound,MarketProbabilityDerivation,ProbabilitySourceMeasurement,ComparativeMeasurementV2,
ComparativePerformanceV2,TimeBoundedComparativePerformanceV2,ComparativeDriftAnalysisV2,
ProbabilitySourceCoverage,SourcePerformanceUncertainty,ProbabilitySourcePerformance,TimeBoundedProbabilitySourcePerformance,
ProbabilitySourcePerformanceReference,TimeBoundedProbabilitySourcePerformanceReference,ComparativePerformanceReferenceV2,
TimeBoundedComparativePerformanceReferenceV2,ComparativeDriftAnalysisReferenceV2,ReportClaimFindingV2,ComparativePerformanceReportV2)
for _contract in _CONTRACTS:
    _contract.to_dict=SerializableContract.to_dict;_contract.to_json=SerializableContract.to_json
    _contract.from_dict=SerializableContract.__dict__["from_dict"];_contract.from_json=SerializableContract.__dict__["from_json"]
_register(*_CONTRACTS,enums=(SourceEvidenceKind,SourceCaptureDispositionV2,CaptureBoundaryDisposition,
                             ProbabilitySourceRole,SourceMeasurementInputKind,CoverageCategory))
