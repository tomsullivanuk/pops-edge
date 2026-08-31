"""PR17B1 standalone Kalshi MLB scientific contracts and deterministic replay.

This module is deliberately offline.  It owns the V3/PR17 contract family and
depends on, but never changes, the PR16B standalone-performance contracts.
Operational acquisition, persistence, scheduling, and activation belong to
PR17B2/PR17C.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from enum import Enum
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

from event_contracts import ContractError, ReasonCode, SerializableContract, _register, _require_aware, _require_identifier
from forecast_comparative_research import (
    EligibilityHistoryState, EventPhase,
    PopulationEligibilityDisposition, PopulationEligibilityResult,
    PopulationEligibilityValidationStatus, ResearchCaptureOpportunity,
    ResearchEventEligibilityContext,
)
from forecast_research_contracts import ProbabilitySourceReference, ResearchContractProvenance
from forecast_standalone_performance import (
    MarketProbabilityBound, MarketProbabilityDerivation, MarketProbabilityLevel,
)
from market_contracts import MarketObservation, MarketSide, ProviderMarketSeries
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


SCHEMA_VERSION = "3"
IDENTITY_VERSION = "1"
PROVIDER_ID = "kalshi"
TIMEZONE_NAME = "America/New_York"
PRECISION = 50
APPROVED_SCORING_RULE = ("binary-brier-log-loss", "1")
APPROVED_CALIBRATION_RULE = ("fixed-bin-wace", "1")
APPROVED_UNCERTAINTY_RULE = ("deterministic-one-sample-bootstrap", "1")
APPROVED_REPORT_RULE = ("separate-standalone-report", "1")


def _fail(detail: str, code: ReasonCode = ReasonCode.VALIDATION_FAILURE) -> None:
    raise ContractError(code, detail)


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        _require_aware(value, "scientific datetime")
        return {"datetime_utc": value.astimezone(timezone.utc).isoformat()}
    if isinstance(value, date): return {"date": value.isoformat()}
    if isinstance(value, Decimal):
        if value.is_nan(): _fail("NaN is not scientific material")
        return {"decimal": str(value)}
    if isinstance(value, Enum): return value.value
    if is_dataclass(value): return {item.name: _canonical(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, (tuple, list)): return [_canonical(item) for item in value]
    if isinstance(value, Mapping): return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, float): _fail("binary float cannot participate in scientific identity")
    if value is None or isinstance(value, (str, int, bool)): return value
    raise TypeError(type(value).__name__)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _unique(values: Iterable[Any], label: str, key=lambda item: item) -> tuple[Any, ...]:
    supplied = tuple(values); keys = tuple(key(item) for item in supplied)
    if len(keys) != len(set(keys)): _fail(f"{label} contains duplicates")
    return tuple(item for _, item in sorted(zip(keys, supplied), key=lambda pair: pair[0]))


def _identity(cls: type[Any], prefix: str, values: dict[str, Any], excluded: tuple[str, ...]) -> Any:
    material = tuple(values[name] for name in cls.__dataclass_fields__ if name not in excluded)
    digest = _digest(material)
    return cls(**{prefix + "_id": f"{prefix.replace('_', '-')}:{digest}", **values, "input_digest": digest})


def _check_identity(value: Any, prefix: str, excluded: tuple[str, ...]) -> None:
    material = tuple(getattr(value, name) for name in value.__dataclass_fields__ if name not in excluded)
    digest = _digest(material)
    if value.input_digest != digest or getattr(value, prefix + "_id") != f"{prefix.replace('_', '-')}:{digest}":
        _fail(f"{prefix.replace('_', ' ')} identity conflict", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


@dataclass(frozen=True, slots=True, order=True)
class StandaloneRule:
    rule_kind: str
    rule_id: str
    rule_version: str
    parameters: tuple[tuple[str, str], ...] = ()
    limitations: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        for value in (self.rule_kind, self.rule_id, self.rule_version): _require_identifier(value, "standalone rule material")
        object.__setattr__(self, "parameters", _unique(self.parameters, "rule parameters", lambda item: item[0]))
        object.__setattr__(self, "limitations", _unique(self.limitations, "rule limitations"))


@dataclass(frozen=True, slots=True)
class StandaloneResearchActivationBoundary:
    standalone_research_activation_boundary_id: str
    schema_version: str
    identity_algorithm_version: str
    approved_calendar_date: date
    activation_at: datetime
    timezone_name: str
    timezone_rule_version: str
    conversion_rule_version: str
    product_owner_decision_reference: str
    decision_effective_at: datetime
    provenance: ResearchContractProvenance
    input_digest: str
    @classmethod
    def create(cls, *, approved_calendar_date: date, activation_at: datetime,
               timezone_name: str, timezone_rule_version: str, conversion_rule_version: str,
               product_owner_decision_reference: str, decision_effective_at: datetime,
               provenance: ResearchContractProvenance) -> "StandaloneResearchActivationBoundary":
        values = dict(schema_version=SCHEMA_VERSION, identity_algorithm_version=IDENTITY_VERSION,
            approved_calendar_date=approved_calendar_date, activation_at=activation_at,
            timezone_name=timezone_name, timezone_rule_version=timezone_rule_version,
            conversion_rule_version=conversion_rule_version,
            product_owner_decision_reference=product_owner_decision_reference,
            decision_effective_at=decision_effective_at, provenance=provenance)
        return _identity(cls, "standalone_research_activation_boundary", values,
                         ("standalone_research_activation_boundary_id", "provenance", "input_digest"))
    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.identity_algorithm_version != IDENTITY_VERSION: _fail("unsupported activation-boundary version")
        if self.timezone_name != TIMEZONE_NAME: _fail("activation boundary requires America/New_York")
        for value in (self.activation_at, self.decision_effective_at): _require_aware(value, "activation chronology")
        expected = datetime.combine(self.approved_calendar_date, time.min, ZoneInfo(TIMEZONE_NAME))
        if self.activation_at != expected: _fail("activation instant is not exact New York start of approved day")
        if self.decision_effective_at >= self.activation_at: _fail("activation decision must be effective before approved day")
        for value in (self.timezone_rule_version, self.conversion_rule_version, self.product_owner_decision_reference): _require_identifier(value, "activation authority")
        _check_identity(self, "standalone_research_activation_boundary", ("standalone_research_activation_boundary_id", "provenance", "input_digest"))


class StandaloneDesignTag(str, Enum):
    RETROSPECTIVE = "retrospective"
    PROSPECTIVE = "prospective"


class EventClassificationValidationStatus(str,Enum):
    VALID="valid";AMBIGUOUS="ambiguous";INVALID="invalid"


@dataclass(frozen=True,slots=True)
class StandaloneEventClassificationEvidence:
    standalone_event_classification_evidence_id:str;schema_version:str;identity_algorithm_version:str
    authoritative_provider_id:str;provider_event_id:str;canonical_event_id:str;sport:str;competition:str;season:str
    event_phase:EventPhase;game_type:str;ordinary_game:bool;doubleheader_id:str|None;game_number:int|None
    participant_ids:tuple[str,...];home_participant_id:str;away_participant_id:str
    mapping_validation_status:EventClassificationValidationStatus;validation_reasons:tuple[str,...]
    collected_at:datetime;effective_at:datetime;supersedes_classification_id:str|None;correction_reason:str|None
    limitations:tuple[str,...];provenance:ResearchContractProvenance;input_digest:str
    @classmethod
    def create(cls,**kwargs:Any)->"StandaloneEventClassificationEvidence":
        values=dict(kwargs);values.setdefault("schema_version",SCHEMA_VERSION);values.setdefault("identity_algorithm_version",IDENTITY_VERSION)
        for key in ("participant_ids","validation_reasons","limitations"):values[key]=_unique(values.get(key,()),f"classification {key}")
        return _identity(cls,"standalone_event_classification_evidence",values,("standalone_event_classification_evidence_id","provenance","input_digest"))
    def __post_init__(self)->None:
        for value in (self.authoritative_provider_id,self.provider_event_id,self.canonical_event_id,self.sport,self.competition,self.season,self.game_type):_require_identifier(value,"event classification authority")
        for value in (self.collected_at,self.effective_at):_require_aware(value,"classification chronology")
        if self.effective_at<self.collected_at:_fail("classification effective time precedes collection")
        if tuple(sorted((self.away_participant_id,self.home_participant_id)))!=self.participant_ids:_fail("classification participant mapping is incomplete")
        if (self.doubleheader_id is None)!=(self.game_number is None):_fail("doubleheader identity and game number must appear together")
        if self.game_number is not None and self.game_number<1:_fail("doubleheader game number is invalid")
        if self.mapping_validation_status is EventClassificationValidationStatus.VALID and self.validation_reasons:_fail("valid classification cannot carry validation reasons")
        if self.mapping_validation_status is not EventClassificationValidationStatus.VALID and not self.validation_reasons:_fail("non-valid classification requires reasons")
        if (self.supersedes_classification_id is None)!=(self.correction_reason is None):_fail("classification correction predecessor and reason must appear together")
        _check_identity(self,"standalone_event_classification_evidence",("standalone_event_classification_evidence_id","provenance","input_digest"))


def select_authoritative_event_classifications(classifications:Iterable[StandaloneEventClassificationEvidence],boundary:datetime)->tuple[StandaloneEventClassificationEvidence,...]:
    _require_aware(boundary,"classification boundary");values=tuple(classifications);by_id={x.standalone_event_classification_evidence_id:x for x in values}
    if len(by_id)!=len(values):_fail("classification registry contains duplicate or conflicting identity")
    groups={(x.authoritative_provider_id,x.provider_event_id,x.canonical_event_id) for x in values};selected=[]
    members_by_group={group:[] for group in groups}
    for item in values:
        members_by_group[(item.authoritative_provider_id,item.provider_event_id,item.canonical_event_id)].append(item)
    for group in groups:
        members=members_by_group[group]
        member_ids={x.standalone_event_classification_evidence_id for x in members}
        children_by_parent={}
        for item in members:
            children_by_parent.setdefault(item.supersedes_classification_id,[]).append(item)
        # Validate the complete group, including corrections beyond the boundary.
        for item in members:
            if item.supersedes_classification_id:
                parent=by_id.get(item.supersedes_classification_id)
                if parent is None or parent.standalone_event_classification_evidence_id not in member_ids:_fail("orphaned or cross-event classification correction")
                if item.effective_at<=parent.effective_at:_fail("reversed classification correction chronology")
                if len(children_by_parent[parent.standalone_event_classification_evidence_id])>1:_fail("branched classification correction")
        visible=tuple(x for x in members if x.effective_at<=boundary)
        if not visible:continue
        roots=tuple(x for x in visible if x.supersedes_classification_id is None)
        if len(roots)!=1:_fail("classification lineage requires one root")
        current=roots[0];seen={current.standalone_event_classification_evidence_id}
        while True:
            children=tuple(x for x in children_by_parent.get(current.standalone_event_classification_evidence_id,()) if x.effective_at<=boundary)
            if len(children)>1:_fail("branched classification correction")
            if not children:break
            current=children[0];seen.add(current.standalone_event_classification_evidence_id)
        if len(seen)!=len(visible):_fail("disconnected classification correction lineage")
        selected.append(current)
    return tuple(sorted(selected,key=lambda x:(x.canonical_event_id,x.provider_event_id)))


@dataclass(frozen=True, slots=True)
class RetrospectiveStandaloneDesign:
    activation_boundary_id: str
    selection_rule: StandaloneRule
    manifest_rule: StandaloneRule
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        _require_identifier(self.activation_boundary_id, "activation boundary")
        if self.selection_rule.rule_id != "latest-real-one-minute-candle-before-target": _fail("retrospective design has unknown selection rule")
        object.__setattr__(self, "limitations", _unique(self.limitations, "design limitations"))


@dataclass(frozen=True, slots=True)
class ProspectiveStandaloneDesign:
    activation_boundary_id: str
    capture_rule: StandaloneRule
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        _require_identifier(self.activation_boundary_id, "activation boundary")
        if self.capture_rule.rule_id != "five-slot-inclusive-upper-endpoint": _fail("prospective design has unknown capture rule")
        object.__setattr__(self, "limitations", _unique(self.limitations, "design limitations"))


@dataclass(frozen=True, slots=True)
class StandaloneProbabilitySourceProtocol:
    standalone_probability_source_protocol_id: str
    schema_version: str
    identity_algorithm_version: str
    design_tag: StandaloneDesignTag
    design: RetrospectiveStandaloneDesign | ProspectiveStandaloneDesign
    source: ProbabilitySourceReference
    scope_rule: StandaloneRule
    representation_rule: StandaloneRule
    scoring_rule: StandaloneRule
    calibration_rule: StandaloneRule
    uncertainty_rule: StandaloneRule
    report_rule: StandaloneRule
    provenance: ResearchContractProvenance
    input_digest: str
    @classmethod
    def create(cls, *, design_tag: StandaloneDesignTag,
               design: RetrospectiveStandaloneDesign | ProspectiveStandaloneDesign,
               source: ProbabilitySourceReference, scope_rule: StandaloneRule,
               representation_rule: StandaloneRule, scoring_rule: StandaloneRule,
               calibration_rule: StandaloneRule, uncertainty_rule: StandaloneRule,
               report_rule: StandaloneRule, provenance: ResearchContractProvenance) -> "StandaloneProbabilitySourceProtocol":
        values = dict(schema_version=SCHEMA_VERSION, identity_algorithm_version=IDENTITY_VERSION,
            design_tag=design_tag, design=design, source=source, scope_rule=scope_rule,
            representation_rule=representation_rule, scoring_rule=scoring_rule,
            calibration_rule=calibration_rule, uncertainty_rule=uncertainty_rule,
            report_rule=report_rule, provenance=provenance)
        return _identity(cls, "standalone_probability_source_protocol", values,
                         ("standalone_probability_source_protocol_id", "provenance", "input_digest"))
    def __post_init__(self) -> None:
        expected = RetrospectiveStandaloneDesign if self.design_tag is StandaloneDesignTag.RETROSPECTIVE else ProspectiveStandaloneDesign
        if type(self.design) is not expected: _fail("Protocol requires exactly one matching closed tagged design")
        if self.source.provider_id != PROVIDER_ID: _fail("PR17 standalone Protocol requires Kalshi")
        if self.source.proposition_type != "winner": _fail("PR17 standalone Protocol requires game winner")
        if self.representation_rule.rule_id != "home-team-yes": _fail("Protocol requires home-team YES authority")
        if (self.scoring_rule.rule_id,self.scoring_rule.rule_version)!=APPROVED_SCORING_RULE:_fail("unsupported standalone scoring rule")
        if dict(self.scoring_rule.parameters)!={"distribution":"binary-complete","decimal_precision":str(PRECISION),"log_loss":"extended-real"}:_fail("incomplete standalone scoring rule parameters")
        if (self.calibration_rule.rule_id,self.calibration_rule.rule_version)!=APPROVED_CALIBRATION_RULE:_fail("unsupported standalone Calibration rule")
        _calibration_boundaries(self.calibration_rule)
        if (self.uncertainty_rule.rule_id,self.uncertainty_rule.rule_version)!=APPROVED_UNCERTAINTY_RULE:_fail("unsupported standalone uncertainty rule")
        if set(dict(self.uncertainty_rule.parameters))!={"confidence_level","resamples"}:_fail("incomplete or unsupported uncertainty parameters")
        confidence=Decimal(_rule_parameter(self.uncertainty_rule,"confidence_level"));resamples=int(_rule_parameter(self.uncertainty_rule,"resamples"))
        if not Decimal(0)<confidence<Decimal(1) or resamples<1:_fail("invalid Protocol uncertainty settings")
        if (self.report_rule.rule_id,self.report_rule.rule_version)!=APPROVED_REPORT_RULE:_fail("unsupported standalone report rule")
        _report_windows(self.report_rule)
        _check_identity(self, "standalone_probability_source_protocol", ("standalone_probability_source_protocol_id", "provenance", "input_digest"))
    @property
    def activation_boundary_id(self) -> str: return self.design.activation_boundary_id


def validate_population_side(protocol: StandaloneProbabilitySourceProtocol,
                             activation: StandaloneResearchActivationBoundary,
                             scheduled_start: datetime) -> None:
    _require_aware(scheduled_start, "scheduled start")
    if protocol.activation_boundary_id != activation.standalone_research_activation_boundary_id: _fail("mismatched activation-boundary reference")
    if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE and not scheduled_start < activation.activation_at: _fail("retrospective opportunity is not strictly before activation")
    if protocol.design_tag is StandaloneDesignTag.PROSPECTIVE and not scheduled_start >= activation.activation_at: _fail("prospective opportunity is before activation")


def _rule_parameter(rule: StandaloneRule, name: str) -> str:
    values=dict(rule.parameters)
    if name not in values:_fail(f"standalone rule lacks {name}")
    return values[name]


def _calibration_boundaries(rule:StandaloneRule)->tuple[Decimal,...]:
    if set(dict(rule.parameters))!={"boundaries","endpoint_semantics","weighting","empty_bins"}:_fail("incomplete or unsupported Calibration parameters")
    raw=_rule_parameter(rule,"boundaries")
    try: values=tuple(Decimal(item) for item in raw.split(","))
    except Exception as error:raise ContractError(ReasonCode.VALIDATION_FAILURE,"malformed Calibration boundaries") from error
    if len(values)<2 or values[0]!=0 or values[-1]!=1 or any(not value.is_finite() for value in values) or any(a>=b for a,b in zip(values,values[1:])):_fail("Calibration boundaries must be a complete ordered [0,1] partition")
    if dict(rule.parameters).get("endpoint_semantics")!="left-closed-right-open-final-closed" or dict(rule.parameters).get("weighting")!="sample-share-absolute-gap" or dict(rule.parameters).get("empty_bins")!="omit":_fail("unsupported Calibration semantics")
    return values


def _report_windows(rule:StandaloneRule)->tuple[timedelta,...]:
    if set(dict(rule.parameters))!={"bounded_window_durations"}:_fail("incomplete or unsupported report parameters")
    raw=dict(rule.parameters).get("bounded_window_durations")
    if raw is None:_fail("report rule lacks exact bounded-window specification")
    try: values=tuple(timedelta(seconds=int(item)) for item in raw.split(",") if item)
    except ValueError as error:raise ContractError(ReasonCode.VALIDATION_FAILURE,"malformed report-window specification") from error
    if not values or any(value<=timedelta(0) for value in values) or len(set(values))!=len(values):_fail("report windows must be positive and unique")
    return tuple(sorted(values))


def resolve_standalone_schedule_authority(*, protocol:StandaloneProbabilitySourceProtocol,
        activation:StandaloneResearchActivationBoundary, opportunity:ResearchCaptureOpportunity,
        eligibility_context:ResearchEventEligibilityContext, eligibility_result:PopulationEligibilityResult,
        outcome_history:OutcomeHistory, analysis_boundary:datetime)->tuple[OutcomeObservation,datetime]:
    """Resolve exact schedule/eligibility authority without comparative semantics."""
    _require_aware(analysis_boundary,"schedule analysis boundary")
    pid=protocol.standalone_probability_source_protocol_id
    if opportunity.protocol_id!=pid or opportunity.proposition_type!="winner":_fail("foreign or malformed standalone opportunity")
    if (eligibility_context.protocol_id,eligibility_context.research_capture_opportunity_id)!=(pid,opportunity.research_capture_opportunity_id):_fail("foreign eligibility context")
    if (eligibility_result.protocol_id,eligibility_result.research_capture_opportunity_id,
            eligibility_result.research_event_eligibility_context_id)!=(pid,opportunity.research_capture_opportunity_id,eligibility_context.research_event_eligibility_context_id):_fail("foreign eligibility result")
    if eligibility_result.disposition is not PopulationEligibilityDisposition.ELIGIBLE or eligibility_result.validation_status is not PopulationEligibilityValidationStatus.VALID:_fail("standalone opportunity is not validly eligible")
    if eligibility_context.analysis_boundary!=eligibility_result.analysis_boundary or eligibility_context.analysis_boundary>analysis_boundary:_fail("eligibility boundary is incompatible")
    if eligibility_context.canonical_event_id!=outcome_history.canonical_event_id or eligibility_context.outcome_history_provider_id!=outcome_history.authoritative_provider_id:_fail("eligibility Schedule history conflicts")
    visible=tuple(item for item in outcome_history.observations if item.collected_at<=analysis_boundary)
    if not visible:_fail("Schedule history is empty at analysis boundary")
    schedule=next((item for item in visible if item.observation_id==opportunity.schedule_observation_id),None)
    if schedule is None:_fail("opportunity Schedule Observation is absent at analysis boundary")
    context_ids=tuple(item.observation_id for item in eligibility_context.history_states)
    expected_ids=tuple(item.observation_id for item in visible if item.collected_at<=eligibility_context.analysis_boundary)
    if context_ids!=expected_ids:_fail("eligibility context omits or invents Schedule/status history")
    validate_population_side(protocol,activation,schedule.scheduled_start)
    try: offset=int(_rule_parameter(protocol.scope_rule,"target_offset_minutes"))
    except ValueError as error:raise ContractError(ReasonCode.VALIDATION_FAILURE,"target offset is not an integer") from error
    return schedule,schedule.scheduled_start+timedelta(minutes=offset)


def create_standalone_eligibility_authority(*,protocol:StandaloneProbabilitySourceProtocol,
        opportunity:ResearchCaptureOpportunity,outcome_history:OutcomeHistory,classification:StandaloneEventClassificationEvidence,
        classifications:Iterable[StandaloneEventClassificationEvidence],analysis_boundary:datetime,
        provenance:ResearchContractProvenance)->tuple[ResearchEventEligibilityContext,PopulationEligibilityResult]:
    """Build reused eligibility records without fabricating a comparative Protocol."""
    pid=protocol.standalone_probability_source_protocol_id
    if opportunity.protocol_id!=pid:_fail("eligibility opportunity conflicts with standalone Protocol")
    visible=tuple(x for x in outcome_history.observations if x.collected_at<=analysis_boundary)
    schedule=next((x for x in visible if x.observation_id==opportunity.schedule_observation_id),None)
    if schedule is None:_fail("eligibility lacks exact Schedule Observation")
    states=tuple(EligibilityHistoryState(x.observation_id,x.provider_status,x.scheduled_start,x.collected_at) for x in visible)
    selected=tuple(x for x in select_authoritative_event_classifications(classifications,analysis_boundary) if x.canonical_event_id==schedule.canonical_event_id)
    if selected!=(classification,):_fail("eligibility does not use authoritative classification Evidence")
    if (classification.authoritative_provider_id,classification.provider_event_id,classification.canonical_event_id)!=(outcome_history.authoritative_provider_id,schedule.provider_event_id,schedule.canonical_event_id):_fail("classification lacks exact Schedule provider lineage")
    participants=tuple(sorted((schedule.away_participant_id,schedule.home_participant_id)))
    if (classification.participant_ids,classification.home_participant_id,classification.away_participant_id)!=(participants,schedule.home_participant_id,schedule.away_participant_id):_fail("classification participant mapping conflicts with Schedule")
    scope=dict(protocol.scope_rule.parameters)
    sport=classification.sport;competition=classification.competition;season=classification.season;phase=classification.event_phase
    values=(opportunity.research_capture_opportunity_id,pid,schedule.canonical_event_id,sport,competition,season,
        participants,classification.standalone_event_classification_evidence_id,phase,outcome_history.authoritative_provider_id,states,analysis_boundary)
    digest=_digest(values)
    context=ResearchEventEligibilityContext(f"research-event-eligibility-context:{digest}",*values,digest)
    reasons=[];validation=[]
    if outcome_history.authoritative_provider_id!=scope.get("schedule_provider_id","mlb-stats-api"):validation.append("non-authoritative-schedule-provider")
    if schedule.validation_status.value!="valid":validation.append("invalid-schedule-observation")
    if classification.mapping_validation_status is not EventClassificationValidationStatus.VALID:validation.extend(classification.validation_reasons)
    if (sport,competition,season,phase.value)!=("baseball","mlb",scope.get("season","2026"),"regular-season"):reasons.append("outside-protocol-population")
    statuses=tuple(item.provider_status for item in visible)
    latest=visible[-1].provider_status
    if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE:
        if phase is EventPhase.POSTSEASON:reasons.append("postseason")
        if season!=scope.get("season","2026"):reasons.append("wrong-season")
        if classification.doubleheader_id is not None:reasons.append("doubleheader")
        if not classification.ordinary_game:reasons.append("non-ordinary-game")
        if classification.mapping_validation_status is not EventClassificationValidationStatus.VALID:reasons.append("ambiguous-mapping")
        if OutcomeStatus.CANCELLED in statuses:reasons.append("cancelled")
        if OutcomeStatus.POSTPONED in statuses:reasons.append("postponed")
        if OutcomeStatus.SUSPENDED in statuses:reasons.append("suspended")
        if OutcomeStatus.SUSPENDED in statuses and statuses[-1] is not OutcomeStatus.SUSPENDED:reasons.append("resumed")
        if "explicit-mlb-resume-lineage" in classification.limitations and "resumed" not in reasons:reasons.append("resumed")
        if len({item.scheduled_start for item in visible})>1 and "explicit-mlb-resume-lineage" not in classification.limitations:reasons.append("rescheduled")
        if scope.get("ordinary_game","required")!="required":validation.append("unsupported-ordinary-game-rule")
    else:
        if phase is not EventPhase.REGULAR_SEASON or season!=scope.get("season","2026"):reasons.append("outside-prospective-regular-season")
        if classification.mapping_validation_status is not EventClassificationValidationStatus.VALID:reasons.append("ambiguous-mapping")
        if latest is OutcomeStatus.CANCELLED:reasons.append("cancelled")
    disposition=PopulationEligibilityDisposition.ELIGIBLE if not reasons else PopulationEligibilityDisposition.EXCLUDED
    validation_status=PopulationEligibilityValidationStatus.VALID if not validation else PopulationEligibilityValidationStatus.INVALID
    result=PopulationEligibilityResult.create(research_capture_opportunity_id=opportunity.research_capture_opportunity_id,
        research_event_eligibility_context_id=context.research_event_eligibility_context_id,protocol_id=pid,
        research_population_id=protocol.scope_rule.rule_id,analysis_boundary=analysis_boundary,
        disposition=disposition,governing_rule_specification_ids=(f"{protocol.scope_rule.rule_id}:{protocol.scope_rule.rule_version}",),
        reason_codes=tuple(reasons),validation_status=validation_status,validation_reasons=tuple(validation),provenance=provenance)
    return context,result
def expected_schedule_opportunities(*,protocol:StandaloneProbabilitySourceProtocol,activation:StandaloneResearchActivationBoundary,schedule_histories:Iterable[OutcomeHistory],analysis_boundary:datetime)->tuple[ResearchCaptureOpportunity,...]:
    """Derive the complete opportunity universe from authoritative Schedule histories."""
    expected=[]
    provider=dict(protocol.scope_rule.parameters).get("schedule_provider_id","mlb-stats-api")
    for history in schedule_histories:
        if history.authoritative_provider_id!=provider:_fail("schedule universe contains a foreign authority")
        visible=tuple(item for item in history.observations if item.collected_at<=analysis_boundary)
        if not visible:continue
        first=visible[0];schedule_states=[first]
        for item in visible[1:]:
            if item.observation_id.startswith("outcome-resume-lineage:"):continue
            if item.scheduled_start!=schedule_states[-1].scheduled_start:schedule_states.append(item)
        for item in schedule_states:
            belongs=item.scheduled_start<activation.activation_at if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE else item.scheduled_start>=activation.activation_at
            if belongs:expected.append(ResearchCaptureOpportunity.create(protocol.standalone_probability_source_protocol_id,item.observation_id,"winner"))
    return _unique(expected,"schedule-derived opportunities",lambda item:item.research_capture_opportunity_id)


class ManifestValidationStatus(str, Enum): COMPLETE="complete"; INCOMPLETE="incomplete"; INVALID="invalid"


@dataclass(frozen=True,slots=True,order=True)
class HistoricalCandleRetrievalPage:
    request_cursor:str; position:int; next_cursor:str|None; terminal:bool
    raw_archive_reference:str; raw_archive_sha256:str; retrieved_at:datetime
    returned_candle_evidence_ids:tuple[str,...]; validation_status:ManifestValidationStatus
    limitations:tuple[str,...]=()
    def __post_init__(self)->None:
        _require_identifier(self.request_cursor,"page request cursor");_require_identifier(self.raw_archive_reference,"page archive reference")
        if self.position<0:_fail("page position must be non-negative")
        if len(self.raw_archive_sha256)!=64 or any(x not in "0123456789abcdef" for x in self.raw_archive_sha256):_fail("page archive digest must be SHA-256")
        _require_aware(self.retrieved_at,"page retrieval")
        if self.terminal!=(self.next_cursor is None):_fail("page terminal and next-cursor semantics conflict")
        if self.next_cursor is not None:_require_identifier(self.next_cursor,"page next cursor")
        object.__setattr__(self,"returned_candle_evidence_ids",_unique(self.returned_candle_evidence_ids,"page candle IDs"))
        object.__setattr__(self,"limitations",_unique(self.limitations,"page limitations"))


@dataclass(frozen=True, slots=True)
class HistoricalCandleQueryManifest:
    historical_candle_query_manifest_id: str; schema_version: str; identity_algorithm_version: str
    protocol_id: str; opportunity_id:str; canonical_event_id:str; proposition_id:str
    provider_id: str; endpoint: str; provider_market_id: str; interval: str
    requested_start_at: datetime; requested_end_at: datetime; pages: tuple[HistoricalCandleRetrievalPage,...]
    retrieval_started_at: datetime; retrieval_completed_at: datetime | None
    returned_candle_evidence_ids: tuple[str, ...]; validation_status: ManifestValidationStatus
    limitations: tuple[str, ...]; effective_at: datetime; supersedes_manifest_id: str | None
    correction_reason: str | None; provenance: ResearchContractProvenance; input_digest: str
    @classmethod
    def create(cls, **kwargs: Any) -> "HistoricalCandleQueryManifest":
        values=dict(kwargs); values.setdefault("schema_version",SCHEMA_VERSION); values.setdefault("identity_algorithm_version",IDENTITY_VERSION)
        values["pages"]=tuple(values.get("pages",()))
        for key in ("returned_candle_evidence_ids","limitations"):
            values[key]=_unique(values.get(key,()),f"manifest {key}")
        return _identity(cls,"historical_candle_query_manifest",values,("historical_candle_query_manifest_id","provenance","input_digest"))
    def __post_init__(self)->None:
        for value in (self.requested_start_at,self.requested_end_at,self.retrieval_started_at,self.effective_at):_require_aware(value,"manifest chronology")
        if self.retrieval_completed_at is not None:_require_aware(self.retrieval_completed_at,"manifest completion")
        if self.requested_start_at>=self.requested_end_at:_fail("manifest time range is empty or reversed")
        if self.provider_id!=PROVIDER_ID or self.interval!="1m":_fail("manifest requires Kalshi one-minute candles")
        pages=tuple(self.pages)
        if pages:
            if tuple(x.position for x in pages)!=tuple(range(len(pages))):_fail("manifest page positions are missing, repeated, or reordered")
            if pages[0].request_cursor!="initial":_fail("manifest pagination chain must begin at initial cursor")
            for left,right in zip(pages,pages[1:]):
                if left.next_cursor!=right.request_cursor:_fail("manifest pagination cursor chain is disconnected")
            if len({x.request_cursor for x in pages})!=len(pages):_fail("manifest pagination repeats a page")
            if tuple(sorted(pages,key=lambda x:x.retrieved_at))!=pages:_fail("manifest retrieval chronology is reversed")
        union=_unique((cid for page in pages for cid in page.returned_candle_evidence_ids),"manifest page candle union")
        if union!=self.returned_candle_evidence_ids:_fail("manifest candle set does not equal exact page union")
        if self.validation_status is ManifestValidationStatus.COMPLETE:
            if self.retrieval_completed_at is None or not pages or not pages[-1].terminal or any(x.validation_status is not ManifestValidationStatus.COMPLETE for x in pages):_fail("complete manifest requires one complete terminal pagination chain")
        if pages and self.retrieval_started_at>pages[0].retrieved_at:_fail("manifest retrieval start follows first page")
        if self.retrieval_completed_at is not None and pages and self.retrieval_completed_at<pages[-1].retrieved_at:_fail("manifest completion precedes terminal page")
        if (self.supersedes_manifest_id is None)!=(self.correction_reason is None):_fail("manifest correction predecessor and reason must appear together")
        if self.retrieval_completed_at is not None and self.effective_at<self.retrieval_completed_at:_fail("manifest effective time precedes retrieval")
        _check_identity(self,"historical_candle_query_manifest",("historical_candle_query_manifest_id","provenance","input_digest"))


@dataclass(frozen=True, slots=True)
class HistoricalMarketCandleObservation:
    historical_market_candle_observation_id: str; schema_version: str; identity_algorithm_version: str
    protocol_id: str; manifest_id: str; provider_id: str; provider_market_id: str
    canonical_event_id: str; proposition_id: str; home_participant_id: str; contract_side: str
    interval: str; candle_end_at: datetime; acquired_at: datetime; close_yes_bid: Decimal | None
    close_yes_ask: Decimal | None; is_real: bool; is_synthetic: bool; is_repaired: bool
    retrieval_page_position:int; raw_archive_reference: str; raw_archive_sha256: str; limitations: tuple[str,...]
    provenance: ResearchContractProvenance; input_digest: str
    @classmethod
    def create(cls,**kwargs:Any)->"HistoricalMarketCandleObservation":
        values=dict(kwargs);values.setdefault("schema_version",SCHEMA_VERSION);values.setdefault("identity_algorithm_version",IDENTITY_VERSION);values["limitations"]=_unique(values.get("limitations",()),"candle limitations")
        # The manifest owns the complete candle-ID set while each candle links back
        # to that manifest. Excluding only the backlink avoids a recursive content
        # address; all substantive candle material remains identity material.
        return _identity(cls,"historical_market_candle_observation",values,("historical_market_candle_observation_id","manifest_id","provenance","input_digest"))
    def __post_init__(self)->None:
        for value in (self.candle_end_at,self.acquired_at):_require_aware(value,"candle chronology")
        if self.acquired_at<=self.candle_end_at:_fail("historical candle must preserve later acquisition time")
        if self.provider_id!=PROVIDER_ID or self.interval!="1m" or self.contract_side!="yes":_fail("candle authority must be Kalshi home-team YES one-minute material")
        if self.retrieval_page_position<0:_fail("candle retrieval-page position is invalid")
        if not self.is_real or self.is_synthetic or self.is_repaired:_fail("synthetic or repaired candle is prohibited")
        for value in (self.close_yes_bid,self.close_yes_ask):
            if value is not None and (not isinstance(value,Decimal) or not value.is_finite() or not Decimal(0)<=value<=Decimal(1)):_fail("candle close is invalid")
        _check_identity(self,"historical_market_candle_observation",("historical_market_candle_observation_id","manifest_id","provenance","input_digest"))


def reconcile_manifest_candles(manifest:HistoricalCandleQueryManifest,candles:Iterable[HistoricalMarketCandleObservation])->tuple[HistoricalMarketCandleObservation,...]:
    values=_unique(candles,"manifest candle registry",lambda item:item.historical_market_candle_observation_id)
    if tuple(item.historical_market_candle_observation_id for item in values)!=manifest.returned_candle_evidence_ids:_fail("manifest candle registry is incomplete or foreign")
    memberships={item.historical_market_candle_observation_id:[] for item in values}
    for page in manifest.pages:
        for candle_id in page.returned_candle_evidence_ids:
            if candle_id in memberships:memberships[candle_id].append(page)
    for candle in values:
        if (candle.protocol_id,candle.manifest_id,candle.provider_id,candle.provider_market_id)!=(manifest.protocol_id,manifest.historical_candle_query_manifest_id,manifest.provider_id,manifest.provider_market_id):_fail("candle registry conflicts with manifest authority")
        pages=memberships[candle.historical_market_candle_observation_id]
        if len(pages)!=1:_fail("candle must resolve to exactly one retrieval page")
        page=pages[0]
        if (candle.retrieval_page_position,candle.raw_archive_reference,candle.raw_archive_sha256)!=(page.position,page.raw_archive_reference,page.raw_archive_sha256):_fail("candle archive provenance conflicts with retrieval page")
        if candle.acquired_at!=page.retrieved_at:_fail("candle acquisition chronology conflicts with retrieval page")
    return values


@dataclass(frozen=True, slots=True)
class HistoricalCandleProbabilityDerivation:
    historical_candle_probability_derivation_id: str; schema_version: str; identity_algorithm_version: str
    protocol_id: str; activation_boundary_id:str; opportunity_id:str; schedule_observation_id:str
    eligibility_context_id:str; eligibility_result_id:str; scheduled_start:datetime
    manifest_id: str; candle_observation_id: str; canonical_event_id: str
    proposition_id: str; home_participant_id: str; complement_outcome_id: str; target_at: datetime; bid: Decimal; ask: Decimal
    midpoint: Decimal; complement_probability: Decimal; probability_distribution: tuple[tuple[str,Decimal],...]
    effective_at: datetime; limitations: tuple[str,...]; provenance: ResearchContractProvenance; input_digest: str
    def __post_init__(self)->None:
        for value in (self.target_at,self.effective_at):_require_aware(value,"historical derivation chronology")
        if self.bid>self.ask or self.midpoint!=(self.bid+self.ask)/Decimal(2) or self.complement_probability!=Decimal(1)-self.midpoint:_fail("historical midpoint arithmetic conflict")
        if sum(dict(self.probability_distribution).values(),Decimal(0))!=1:_fail("historical derivation requires a complete distribution")
        _check_identity(self,"historical_candle_probability_derivation",("historical_candle_probability_derivation_id","provenance","input_digest"))


def validate_manifest_lineage(manifests:Iterable[HistoricalCandleQueryManifest],boundary:datetime)->tuple[HistoricalCandleQueryManifest,...]:
    _require_aware(boundary,"manifest analysis boundary");values=tuple(manifests);by_id={x.historical_candle_query_manifest_id:x for x in values}
    if len(by_id)!=len(values):_fail("duplicate or conflicting manifest identity")
    children={key:[] for key in by_id}
    for item in values:
        if item.supersedes_manifest_id:
            parent=by_id.get(item.supersedes_manifest_id)
            if parent is None:_fail("orphaned manifest correction")
            if (parent.protocol_id,parent.opportunity_id,parent.canonical_event_id,parent.proposition_id,parent.provider_market_id)!=(item.protocol_id,item.opportunity_id,item.canonical_event_id,item.proposition_id,item.provider_market_id):_fail("cross-authority manifest correction")
            if item.effective_at<=parent.effective_at:_fail("cyclic or reversed manifest correction")
            children[parent.historical_candle_query_manifest_id].append(item)
            if len(children[parent.historical_candle_query_manifest_id])>1:_fail("branched manifest correction")
    selected=[]
    groups={(x.protocol_id,x.opportunity_id,x.provider_market_id) for x in values}
    members_by_group={group:[] for group in groups}
    for item in values:
        members_by_group[(item.protocol_id,item.opportunity_id,item.provider_market_id)].append(item)
    for group in groups:
        visible=[x for x in members_by_group[group] if x.effective_at<=boundary]
        roots=[x for x in visible if x.supersedes_manifest_id is None]
        if len(roots)!=1:_fail("manifest lineage requires one unambiguous root")
        current=roots[0];seen={current.historical_candle_query_manifest_id}
        while True:
            nxt=[x for x in children[current.historical_candle_query_manifest_id] if x.effective_at<=boundary]
            if len(nxt)>1:_fail("branched manifest correction")
            if not nxt:break
            current=nxt[0]
            if current.historical_candle_query_manifest_id in seen:_fail("cyclic manifest correction")
            seen.add(current.historical_candle_query_manifest_id)
        if len(seen)!=len(visible):_fail("ambiguous or disconnected manifest lineage")
        selected.append(current)
    return tuple(sorted(selected,key=lambda x:(x.protocol_id,x.opportunity_id,x.provider_market_id)))


def create_historical_candle_probability_derivation(*,protocol:StandaloneProbabilitySourceProtocol,
        activation:StandaloneResearchActivationBoundary,opportunity:ResearchCaptureOpportunity,
        eligibility_context:ResearchEventEligibilityContext,eligibility_result:PopulationEligibilityResult,
        schedule_history:OutcomeHistory,analysis_boundary:datetime,
        manifest:HistoricalCandleQueryManifest,manifests:Iterable[HistoricalCandleQueryManifest],candles:Iterable[HistoricalMarketCandleObservation],
        home_participant_id:str,complement_outcome_id:str,
        effective_at:datetime,provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->HistoricalCandleProbabilityDerivation:
    if protocol.design_tag is not StandaloneDesignTag.RETROSPECTIVE:_fail("historical derivation requires retrospective Protocol")
    schedule,target_at=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,
        eligibility_context=eligibility_context,eligibility_result=eligibility_result,outcome_history=schedule_history,analysis_boundary=analysis_boundary)
    canonical_event_id=schedule.canonical_event_id;proposition_id=f"winner:{canonical_event_id}:{schedule.home_participant_id}"
    if home_participant_id!=schedule.home_participant_id or complement_outcome_id!=schedule.away_participant_id:_fail("historical home/away mapping conflicts with Schedule authority")
    if (manifest.protocol_id,manifest.opportunity_id,manifest.canonical_event_id,manifest.proposition_id)!=(protocol.standalone_probability_source_protocol_id,opportunity.research_capture_opportunity_id,canonical_event_id,proposition_id) or manifest.validation_status is not ManifestValidationStatus.COMPLETE:_fail("complete matching manifest authority is required")
    terminals=validate_manifest_lineage(manifests,analysis_boundary)
    matching=tuple(x for x in terminals if (x.protocol_id,x.opportunity_id,x.provider_market_id)==(manifest.protocol_id,manifest.opportunity_id,manifest.provider_market_id))
    if matching!=(manifest,):_fail("historical derivation does not use authoritative terminal manifest")
    if manifest.requested_start_at!=target_at-timedelta(minutes=5) or manifest.requested_end_at!=target_at:_fail("manifest request window conflicts with Schedule-derived target")
    values=reconcile_manifest_candles(manifest,candles)
    candidates=tuple(x for x in values if target_at-timedelta(minutes=5)<x.candle_end_at<=target_at)
    if not candidates:_fail("no real candle in exact selection window")
    latest=max(x.candle_end_at for x in candidates);selected=tuple(x for x in candidates if x.candle_end_at==latest)
    if len(selected)!=1:_fail("latest candle selection is ambiguous")
    candle=selected[0]
    if (candle.canonical_event_id,candle.proposition_id,candle.home_participant_id)!=(canonical_event_id,proposition_id,home_participant_id):_fail("historical event/proposition/home mapping conflict")
    if candle.close_yes_bid is None or candle.close_yes_ask is None:_fail("selected candle requires both closing YES bounds")
    if candle.close_yes_bid>candle.close_yes_ask:_fail("historical candle bounds are crossed")
    if effective_at<max(manifest.effective_at,candle.acquired_at):_fail("historical derivation is backdated")
    midpoint=(candle.close_yes_bid+candle.close_yes_ask)/Decimal(2);complement=Decimal(1)-midpoint
    if complement_outcome_id==home_participant_id:_fail("historical binary outcomes must be distinct")
    distribution=tuple(sorted(((home_participant_id,midpoint),(complement_outcome_id,complement))))
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=manifest.protocol_id,
        activation_boundary_id=activation.standalone_research_activation_boundary_id,opportunity_id=opportunity.research_capture_opportunity_id,
        schedule_observation_id=schedule.observation_id,eligibility_context_id=eligibility_context.research_event_eligibility_context_id,
        eligibility_result_id=eligibility_result.population_eligibility_result_id,scheduled_start=schedule.scheduled_start,
        manifest_id=manifest.historical_candle_query_manifest_id,candle_observation_id=candle.historical_market_candle_observation_id,
        canonical_event_id=canonical_event_id,proposition_id=proposition_id,home_participant_id=home_participant_id,complement_outcome_id=complement_outcome_id,target_at=target_at,
        bid=candle.close_yes_bid,ask=candle.close_yes_ask,midpoint=midpoint,complement_probability=complement,
        probability_distribution=distribution,effective_at=effective_at,limitations=_unique(limitations,"historical derivation limitations"),provenance=provenance)
    return _identity(HistoricalCandleProbabilityDerivation,"historical_candle_probability_derivation",vals,("historical_candle_probability_derivation_id","provenance","input_digest"))


class AttemptFailureCategory(str,Enum): TIMEOUT="timeout"; HTTP="http"; NETWORK="network"; PROVIDER="provider"; UNKNOWN="unknown"
class AttemptValidationFailure(str,Enum): INCOMPLETE="incomplete"; MALFORMED="malformed"; MAPPING="mapping"; DEPTH="depth"; CROSSED="crossed"

@dataclass(frozen=True,slots=True)
class CapturedValid:
    raw_acquisition_reference:str; raw_sha256:str; market_observation_id:str
@dataclass(frozen=True,slots=True)
class CapturedInvalid:
    raw_acquisition_reference:str; raw_sha256:str; validation_failures:tuple[AttemptValidationFailure,...]
    def __post_init__(self):
        if not self.validation_failures:_fail("invalid capture requires typed validation failures")
        object.__setattr__(self,"validation_failures",_unique(self.validation_failures,"validation failures",lambda x:x.value))
@dataclass(frozen=True,slots=True)
class AcquisitionFailed:
    failure_category:AttemptFailureCategory; provider_call_reference:str
@dataclass(frozen=True,slots=True)
class Missed:
    reason_code:str="elapsed-without-provider-call"
@dataclass(frozen=True,slots=True)
class SkippedAfterSuccess:
    successful_attempt_id:str

AttemptResult=CapturedValid|CapturedInvalid|AcquisitionFailed|Missed|SkippedAfterSuccess


def slot_for_time(target_at:datetime,at:datetime)->int:
    _require_aware(target_at,"target");_require_aware(at,"attempt time")
    delta=at-target_at
    if delta<timedelta(0) or delta>timedelta(minutes=5):_fail("attempt is backdated or later than inclusive window")
    seconds=Decimal(str(delta.total_seconds()))
    if seconds==Decimal(300):return 4
    slot=int(seconds//Decimal(60))
    if slot not in range(5):_fail("attempt would create a sixth slot")
    return slot


@dataclass(frozen=True,slots=True)
class ProspectiveCaptureAttempt:
    prospective_capture_attempt_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; opportunity_id:str; schedule_observation_id:str; canonical_event_id:str
    proposition_id:str; home_participant_id:str; provider_market_id:str; target_at:datetime
    slot:int; invocation_at:datetime; provider_call_occurred:bool; result:AttemptResult
    effective_at:datetime; diagnostics:tuple[str,...]; provenance:ResearchContractProvenance; input_digest:str
    @classmethod
    def create(cls,**kwargs:Any)->"ProspectiveCaptureAttempt":
        values=dict(kwargs);values.setdefault("schema_version",SCHEMA_VERSION);values.setdefault("identity_algorithm_version",IDENTITY_VERSION);values["diagnostics"]=_unique(values.get("diagnostics",()),"attempt diagnostics")
        return _identity(cls,"prospective_capture_attempt",values,("prospective_capture_attempt_id","provenance","input_digest"))
    def __post_init__(self)->None:
        for value in (self.target_at,self.invocation_at,self.effective_at):_require_aware(value,"attempt chronology")
        called=isinstance(self.result,(CapturedValid,CapturedInvalid,AcquisitionFailed))
        if self.provider_call_occurred!=called:_fail("typed result conflicts with provider-call authority")
        if called and self.slot!=slot_for_time(self.target_at,self.invocation_at):_fail("provider acquisition conflicts with exact slot interval")
        if not called:
            if self.slot not in range(5):_fail("non-acquisition disposition would create a sixth slot")
            if self.invocation_at<self.target_at+timedelta(minutes=self.slot):_fail("non-acquisition disposition predates its slot")
        if self.effective_at<self.invocation_at:_fail("attempt effective time is backdated")
        _check_identity(self,"prospective_capture_attempt",("prospective_capture_attempt_id","provenance","input_digest"))


class SnapshotTerminalDisposition(str,Enum): CAPTURED_VALID="captured-valid"; MISSED_WINDOW="missed-window"


@dataclass(frozen=True,slots=True)
class ProspectiveStandaloneSnapshot:
    prospective_standalone_snapshot_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; activation_boundary_id:str; opportunity_id:str; schedule_observation_id:str
    eligibility_context_id:str; eligibility_result_id:str; scheduled_start:datetime; canonical_event_id:str
    proposition_id:str; home_participant_id:str; provider_market_id:str; target_at:datetime
    attempt_ids:tuple[str,...]; terminal_disposition:SnapshotTerminalDisposition
    authoritative_attempt_id:str|None; market_observation_id:str|None; captured_at:datetime|None
    effective_at:datetime; limitations:tuple[str,...]; supersedes_snapshot_id:str|None
    correction_reason:str|None; provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        for value in (self.target_at,self.effective_at):_require_aware(value,"terminal Snapshot chronology")
        if self.captured_at is not None:_require_aware(self.captured_at,"Snapshot capture")
        if len(self.attempt_ids)!=5:_fail("terminal Snapshot requires exactly five canonical slot dispositions")
        if (self.supersedes_snapshot_id is None)!=(self.correction_reason is None):_fail("Snapshot correction metadata must appear together")
        if self.terminal_disposition is SnapshotTerminalDisposition.CAPTURED_VALID:
            if not all((self.authoritative_attempt_id,self.market_observation_id,self.captured_at)):_fail("successful Snapshot lacks capture authority")
        elif any(x is not None for x in (self.authoritative_attempt_id,self.market_observation_id,self.captured_at)):_fail("missed-window Snapshot cannot fabricate capture")
        _check_identity(self,"prospective_standalone_snapshot",("prospective_standalone_snapshot_id","provenance","input_digest"))


def reconcile_prospective_snapshot(*,protocol:StandaloneProbabilitySourceProtocol,opportunity:ResearchCaptureOpportunity,
        activation:StandaloneResearchActivationBoundary,eligibility_context:ResearchEventEligibilityContext,
        eligibility_result:PopulationEligibilityResult,schedule_history:OutcomeHistory,analysis_boundary:datetime,
        attempts:Iterable[ProspectiveCaptureAttempt],window_closed_at:datetime,provenance:ResearchContractProvenance,
        limitations:tuple[str,...]=())->ProspectiveStandaloneSnapshot:
    if protocol.design_tag is not StandaloneDesignTag.PROSPECTIVE:_fail("prospective Snapshot requires prospective Protocol")
    schedule,expected_target=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,
        eligibility_context=eligibility_context,eligibility_result=eligibility_result,outcome_history=schedule_history,analysis_boundary=analysis_boundary)
    supplied=tuple(attempts);by_id={x.prospective_capture_attempt_id:x for x in supplied}
    if any(by_id[x.prospective_capture_attempt_id]!=x for x in supplied):_fail("conflicting duplicate attempt identity")
    values=tuple(by_id.values())
    if opportunity.protocol_id!=protocol.standalone_probability_source_protocol_id:_fail("foreign-Protocol opportunity")
    if len(values)!=5 or {x.slot for x in values}!=set(range(5)):_fail("terminal Snapshot requires one disposition for every slot")
    if any(x.protocol_id!=protocol.standalone_probability_source_protocol_id or x.opportunity_id!=opportunity.research_capture_opportunity_id for x in values):_fail("attempt registry mixes authority")
    by_slot={x.slot:x for x in values}
    if any(by_slot[i].invocation_at>by_slot[i+1].invocation_at for i in range(4)):_fail("attempt chronology is reversed")
    valid=tuple(x for x in values if isinstance(x.result,CapturedValid))
    if len(valid)>1:_fail("multiple successful prospective captures")
    if valid:
        success=valid[0]
        if any(isinstance(by_slot[i].result,SkippedAfterSuccess) for i in range(success.slot)):_fail("pre-success slot cannot be skipped-after-success")
        for i in range(success.slot+1,5):
            if by_slot[i].result!=SkippedAfterSuccess(success.prospective_capture_attempt_id):_fail("later slot lacks exact skipped-after-success disposition")
        disposition=SnapshotTerminalDisposition.CAPTURED_VALID;auth=success.prospective_capture_attempt_id;obs=success.result.market_observation_id;captured=success.invocation_at
    else:
        if any(isinstance(x.result,SkippedAfterSuccess) for x in values):_fail("skipped disposition lacks successful attempt")
        if window_closed_at<by_slot[4].target_at+timedelta(minutes=5):_fail("missed-window Snapshot created before inclusive window closes")
        disposition=SnapshotTerminalDisposition.MISSED_WINDOW;auth=obs=captured=None
    first=by_slot[0]
    if any((x.schedule_observation_id,x.canonical_event_id,x.proposition_id,x.home_participant_id,x.provider_market_id,x.target_at)!=(first.schedule_observation_id,first.canonical_event_id,first.proposition_id,first.home_participant_id,first.provider_market_id,first.target_at) for x in values):_fail("attempt set mixes opportunity material")
    expected=(schedule.observation_id,schedule.canonical_event_id,f"winner:{schedule.canonical_event_id}:{schedule.home_participant_id}",schedule.home_participant_id,expected_target)
    if (first.schedule_observation_id,first.canonical_event_id,first.proposition_id,first.home_participant_id,first.target_at)!=expected:_fail("attempts conflict with authoritative Schedule-derived opportunity")
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=first.protocol_id,
        activation_boundary_id=activation.standalone_research_activation_boundary_id,opportunity_id=first.opportunity_id,
        schedule_observation_id=first.schedule_observation_id,eligibility_context_id=eligibility_context.research_event_eligibility_context_id,
        eligibility_result_id=eligibility_result.population_eligibility_result_id,scheduled_start=schedule.scheduled_start,canonical_event_id=first.canonical_event_id,
        proposition_id=first.proposition_id,home_participant_id=first.home_participant_id,provider_market_id=first.provider_market_id,target_at=first.target_at,
        attempt_ids=tuple(by_slot[i].prospective_capture_attempt_id for i in range(5)),terminal_disposition=disposition,
        authoritative_attempt_id=auth,market_observation_id=obs,captured_at=captured,effective_at=max(window_closed_at,max(x.effective_at for x in values)),
        limitations=_unique(limitations,"Snapshot limitations"),supersedes_snapshot_id=None,correction_reason=None,provenance=provenance)
    return _identity(ProspectiveStandaloneSnapshot,"prospective_standalone_snapshot",vals,("prospective_standalone_snapshot_id","provenance","input_digest"))


_SNAPSHOT_CORRECTION_FIELDS=frozenset(("prospective_standalone_snapshot_id","effective_at","supersedes_snapshot_id","correction_reason","provenance","input_digest"))


def select_authoritative_prospective_snapshots(snapshots:Iterable[ProspectiveStandaloneSnapshot],boundary:datetime)->tuple[ProspectiveStandaloneSnapshot,...]:
    _require_aware(boundary,"Snapshot replay boundary");values=tuple(snapshots);by_id={x.prospective_standalone_snapshot_id:x for x in values}
    if len(by_id)!=len(values):_fail("duplicate Snapshot authority")
    children={key:[] for key in by_id}
    for child in values:
        if child.supersedes_snapshot_id:
            parent=by_id.get(child.supersedes_snapshot_id)
            if parent is None:_fail("orphaned Snapshot correction")
            if (child.protocol_id,child.opportunity_id)!=(parent.protocol_id,parent.opportunity_id):_fail("Snapshot correction crosses authority")
            if child.effective_at<=parent.effective_at:_fail("Snapshot correction chronology is invalid")
            changed={name for name in child.__dataclass_fields__ if getattr(child,name)!=getattr(parent,name)}
            if not changed<=_SNAPSHOT_CORRECTION_FIELDS:_fail("Snapshot correction rewrites immutable capture material")
            children[parent.prospective_standalone_snapshot_id].append(child)
            if len(children[parent.prospective_standalone_snapshot_id])>1:_fail("Snapshot correction lineage branches")
    selected=[]
    for group in {(x.protocol_id,x.opportunity_id) for x in values}:
        visible=[x for x in values if (x.protocol_id,x.opportunity_id)==group and x.effective_at<=boundary]
        if not visible:continue
        roots=[x for x in visible if x.supersedes_snapshot_id is None]
        if len(roots)!=1:_fail("Snapshot lineage requires one root")
        current=roots[0];seen={current.prospective_standalone_snapshot_id}
        while True:
            nxt=[x for x in visible if x.supersedes_snapshot_id==current.prospective_standalone_snapshot_id]
            if len(nxt)>1:_fail("Snapshot correction lineage branches")
            if not nxt:break
            current=nxt[0]
            if current.prospective_standalone_snapshot_id in seen:_fail("Snapshot correction lineage cycles")
            seen.add(current.prospective_standalone_snapshot_id)
        if len(seen)!=len(visible):_fail("Snapshot correction lineage is disconnected")
        selected.append(current)
    return tuple(sorted(selected,key=lambda x:(x.protocol_id,x.opportunity_id)))


def create_standalone_market_probability_derivation(*,protocol:StandaloneProbabilitySourceProtocol,
        activation:StandaloneResearchActivationBoundary,opportunity:ResearchCaptureOpportunity,
        eligibility_context:ResearchEventEligibilityContext,eligibility_result:PopulationEligibilityResult,
        schedule_history:OutcomeHistory,analysis_boundary:datetime,
        snapshot:ProspectiveStandaloneSnapshot,snapshots:Iterable[ProspectiveStandaloneSnapshot],attempts:Iterable[ProspectiveCaptureAttempt],
        observation:MarketObservation,market_observations:Iterable[MarketObservation],series:ProviderMarketSeries,
        effective_at:datetime,provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->MarketProbabilityDerivation:
    if protocol.design_tag is not StandaloneDesignTag.PROSPECTIVE:_fail("market derivation requires prospective standalone Protocol")
    if snapshot.protocol_id!=protocol.standalone_probability_source_protocol_id or snapshot.terminal_disposition is not SnapshotTerminalDisposition.CAPTURED_VALID:_fail("complete successful Snapshot authority is required")
    selected=tuple(x for x in select_authoritative_prospective_snapshots(snapshots,analysis_boundary) if (x.protocol_id,x.opportunity_id)==(snapshot.protocol_id,snapshot.opportunity_id))
    if selected!=(snapshot,):_fail("market derivation does not reference authoritative terminal Snapshot")
    attempt_values=tuple(attempts);attempt_map={x.prospective_capture_attempt_id:x for x in attempt_values}
    if len(attempt_map)!=len(attempt_values) or set(attempt_map)!=set(snapshot.attempt_ids):_fail("incomplete or foreign attempt registry")
    replayed=reconcile_prospective_snapshot(protocol=protocol,opportunity=opportunity,activation=activation,
        eligibility_context=eligibility_context,eligibility_result=eligibility_result,schedule_history=schedule_history,
        analysis_boundary=analysis_boundary,attempts=attempt_values,window_closed_at=snapshot.target_at+timedelta(minutes=5),
        provenance=snapshot.provenance,limitations=snapshot.limitations)
    immutable=tuple(name for name in snapshot.__dataclass_fields__ if name not in _SNAPSHOT_CORRECTION_FIELDS)
    if any(getattr(snapshot,name)!=getattr(replayed,name) for name in immutable):_fail("terminal Snapshot fails deterministic attempt replay")
    obs_values=tuple(market_observations);obs_map={x.observation_id:x for x in obs_values}
    if len(obs_map)!=len(obs_values) or obs_map.get(observation.observation_id)!=observation or snapshot.market_observation_id not in obs_map:_fail("incomplete or foreign Market Evidence registry")
    success=attempt_map.get(snapshot.authoritative_attempt_id)
    if success is None or not isinstance(success.result,CapturedValid) or success.result.market_observation_id!=observation.observation_id:_fail("Snapshot successful attempt does not resolve")
    if observation.collected_at!=success.invocation_at or snapshot.captured_at!=success.invocation_at:_fail("actual capture chronology conflicts")
    if observation.series_id!=series.series_id or observation.provider_market_id!=snapshot.provider_market_id or series.provider_market_id!=snapshot.provider_market_id:_fail("provider-native market lineage conflicts")
    if observation.canonical_event_id!=snapshot.canonical_event_id or observation.proposition_id!=snapshot.proposition_id:_fail("event or proposition mapping conflict")
    if series.provider!=PROVIDER_ID or protocol.source.provider_id!=PROVIDER_ID or series.yes_semantic.participant_id!=snapshot.home_participant_id or not series.yes_semantic.affirms_proposition:_fail("home-team YES mapping conflict")
    yes=tuple(x for x in observation.order_book if x.acquisition_side is MarketSide.YES);no=tuple(x for x in observation.order_book if x.acquisition_side is MarketSide.NO)
    if not yes or not no:_fail("positive-depth two-sided order book is required")
    ask_price=min(x.acquisition_price for x in yes);no_offer=min(x.acquisition_price for x in no);bid_price=Decimal(1)-no_offer
    if bid_price>ask_price:_fail("market bounds are crossed")
    def bound(kind:str,price:Decimal,items:tuple[Any,...])->MarketProbabilityBound:
        selected=tuple(x for x in items if x.acquisition_price==(ask_price if kind=="offer" else no_offer))
        levels=tuple(MarketProbabilityLevel(price,x.quantity,x.acquisition_side,x.acquisition_price,x.provider_book_side,x.provider_price,x.evidence_kind,x.transformation,"canonical_bid = 1 - complementary_outcome_offer" if kind=="bid" else None,x.source_endpoint,x.collected_at) for x in selected)
        return MarketProbabilityBound(kind,price,sum((x.quantity for x in levels),Decimal(0)),max(x.collected_at for x in levels),levels)
    bid=bound("bid",bid_price,no);offer=bound("offer",ask_price,yes);mid=(bid_price+ask_price)/Decimal(2);comp=Decimal(1)-mid
    if effective_at<max(snapshot.effective_at,observation.collected_at):_fail("market derivation is backdated")
    distribution=tuple(sorted(((snapshot.home_participant_id,mid),(series.no_semantic.participant_id,comp))))
    vals=dict(schema_version="2",identity_algorithm_version="1",derivation_algorithm_version="1",protocol_id=protocol.standalone_probability_source_protocol_id,
        research_snapshot_id=snapshot.prospective_standalone_snapshot_id,source_reference_id=protocol.source.probability_source_reference_id,
        market_observation_id=observation.observation_id,market_series_id=series.series_id,canonical_event_id=snapshot.canonical_event_id,
        proposition_id=snapshot.proposition_id,canonical_outcome_id=snapshot.home_participant_id,bid=bid,offer=offer,midpoint=mid,
        complement_outcome_id=series.no_semantic.participant_id,complement_probability=comp,probability_distribution=distribution,
        representation_rule_id=protocol.source.probability_representation_rule.rule_specification_id,
        transformation_rule_id=protocol.source.transformation_rule.rule_specification_id,effective_at=effective_at,
        limitations=_unique(limitations,"market derivation limitations"),provenance=provenance)
    material=tuple(vals[name] for name in MarketProbabilityDerivation.__dataclass_fields__ if name not in ("market_probability_derivation_id","provenance","input_digest","limitations"))+(vals["limitations"],)
    digest=_digest(material)
    return MarketProbabilityDerivation(f"market-probability-derivation:{digest}",**vals,input_digest=digest)


class DerivationKindV3(str,Enum): HISTORICAL_CANDLE="historical-candle"; PROSPECTIVE_MARKET="prospective-market"


@dataclass(frozen=True,slots=True)
class ProbabilitySourceMeasurementV3:
    probability_source_measurement_v3_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; design_tag:StandaloneDesignTag; derivation_kind:DerivationKindV3; derivation_id:str
    opportunity_id:str; schedule_observation_id:str; canonical_event_id:str; proposition_id:str; canonical_proposition_outcome_id:str; source_reference_id:str
    outcome_observation_id:str; probability_distribution:tuple[tuple[str,Decimal],...]
    realized_outcome_id:str; brier_score:Decimal; log_loss:Decimal; calibration_probability:Decimal
    arithmetic_inputs:tuple[tuple[str,Decimal,int],...]; effective_at:datetime; limitations:tuple[str,...]
    provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        _require_aware(self.effective_at,"Measurement effective time");probs=dict(self.probability_distribution)
        if len(probs)!=2 or sum(probs.values(),Decimal(0))!=1:_fail("V3 Measurement requires complete binary distribution")
        p=probs.get(self.realized_outcome_id)
        if p is None:_fail("realized Outcome absent from distribution")
        with localcontext() as context:context.prec=PRECISION;brier=(p-1)**2;log=Decimal("Infinity") if p==0 else -p.ln()
        if self.brier_score!=brier or self.log_loss!=log:_fail("V3 scoring conflict")
        _check_identity(self,"probability_source_measurement_v3",("probability_source_measurement_v3_id","provenance","input_digest"))


def create_probability_source_measurement_v3(*,protocol:StandaloneProbabilitySourceProtocol,
        activation:StandaloneResearchActivationBoundary,opportunity:ResearchCaptureOpportunity,
        eligibility_context:ResearchEventEligibilityContext,eligibility_result:PopulationEligibilityResult,
        schedule_history:OutcomeHistory,snapshots:Iterable[ProspectiveStandaloneSnapshot]=(),
        derivations:Iterable[HistoricalCandleProbabilityDerivation|MarketProbabilityDerivation],outcome:OutcomeObservation,
        outcome_histories:Iterable[OutcomeHistory],effective_at:datetime,
        provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->ProbabilitySourceMeasurementV3:
    values=tuple(derivations)
    if len(values)!=1:_fail("V3 Measurement requires exactly one typed derivation")
    derivation=values[0]
    expected=HistoricalCandleProbabilityDerivation if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE else MarketProbabilityDerivation
    if type(derivation) is not expected:_fail("derivation kind and Protocol design mismatch")
    if derivation.protocol_id!=protocol.standalone_probability_source_protocol_id:_fail("foreign-Protocol derivation")
    schedule,_=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,
        eligibility_context=eligibility_context,eligibility_result=eligibility_result,outcome_history=schedule_history,analysis_boundary=effective_at)
    if isinstance(derivation,HistoricalCandleProbabilityDerivation):
        if (derivation.opportunity_id,derivation.schedule_observation_id)!=(opportunity.research_capture_opportunity_id,schedule.observation_id):_fail("historical Measurement derivation/opportunity mismatch")
    else:
        selected=select_authoritative_prospective_snapshots(snapshots,effective_at)
        matching=tuple(x for x in selected if x.prospective_standalone_snapshot_id==derivation.research_snapshot_id)
        if len(matching)!=1 or (matching[0].opportunity_id,matching[0].schedule_observation_id)!=(opportunity.research_capture_opportunity_id,schedule.observation_id):_fail("prospective Measurement Snapshot/opportunity mismatch")
    histories=tuple(outcome_histories);matches=tuple(x for x in histories if x.canonical_event_id==derivation.canonical_event_id)
    visible=() if len(matches)!=1 else tuple(x for x in matches[0].observations if x.authoritative_final and x.collected_at<=effective_at)
    if len(matches)!=1 or not visible or visible[-1]!=outcome:_fail("Outcome authority is missing, multiple, foreign, or not authoritative at boundary")
    if not outcome.authoritative_final or outcome.winning_participant_id not in dict(derivation.probability_distribution):_fail("authoritative binary Outcome is required")
    if effective_at<max(derivation.effective_at,outcome.collected_at):_fail("V3 Measurement is backdated")
    probs=tuple(sorted(derivation.probability_distribution));winner=outcome.winning_participant_id;p=dict(probs)[winner]
    with localcontext() as context:context.prec=PRECISION;brier=(p-1)**2;log=Decimal("Infinity") if p==0 else -p.ln()
    home=derivation.home_participant_id if isinstance(derivation,HistoricalCandleProbabilityDerivation) else derivation.canonical_outcome_id
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=protocol.standalone_probability_source_protocol_id,
        design_tag=protocol.design_tag,derivation_kind=DerivationKindV3.HISTORICAL_CANDLE if isinstance(derivation,HistoricalCandleProbabilityDerivation) else DerivationKindV3.PROSPECTIVE_MARKET,
        derivation_id=derivation.historical_candle_probability_derivation_id if isinstance(derivation,HistoricalCandleProbabilityDerivation) else derivation.market_probability_derivation_id,
        opportunity_id=opportunity.research_capture_opportunity_id,schedule_observation_id=schedule.observation_id,canonical_event_id=derivation.canonical_event_id,proposition_id=derivation.proposition_id,
        canonical_proposition_outcome_id=home,source_reference_id=protocol.source.probability_source_reference_id,outcome_observation_id=outcome.observation_id,
        probability_distribution=probs,realized_outcome_id=winner,brier_score=brier,log_loss=log,
        calibration_probability=dict(probs)[home],arithmetic_inputs=tuple((key,value,int(key==winner)) for key,value in probs),
        effective_at=effective_at,limitations=_unique(limitations,"Measurement limitations"),provenance=provenance)
    return _identity(ProbabilitySourceMeasurementV3,"probability_source_measurement_v3",vals,("probability_source_measurement_v3_id","provenance","input_digest"))


@dataclass(frozen=True,slots=True)
class RetrospectiveCoverageReconciliation:
    capture_not_yet_due:tuple[str,...]=(); protocol_ineligible:tuple[str,...]=(); archive_unavailable:tuple[str,...]=(); archive_invalid:tuple[str,...]=(); candle_unavailable:tuple[str,...]=(); candle_invalid:tuple[str,...]=(); derivation_unavailable:tuple[str,...]=(); outcome_unresolved:tuple[str,...]=(); measured:tuple[str,...]=()
@dataclass(frozen=True,slots=True)
class ProspectiveCoverageReconciliation:
    capture_not_yet_due:tuple[str,...]=(); protocol_ineligible:tuple[str,...]=(); missed_window:tuple[str,...]=(); acquisition_failed:tuple[str,...]=(); captured_invalid:tuple[str,...]=(); timing_invalid:tuple[str,...]=(); derivation_unavailable:tuple[str,...]=(); outcome_unresolved:tuple[str,...]=(); measured:tuple[str,...]=()


CoverageReconciliation=RetrospectiveCoverageReconciliation|ProspectiveCoverageReconciliation


@dataclass(frozen=True,slots=True)
class ProbabilitySourceCoverageV3:
    probability_source_coverage_v3_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; design_tag:StandaloneDesignTag; source_reference_id:str; coverage_scope:str
    window_start:datetime|None; analysis_boundary:datetime
    coverage_universe_ids:tuple[str,...]; eligible_denominator_ids:tuple[str,...]; measured_opportunity_ids:tuple[str,...]
    measurement_ids:tuple[str,...]; reconciliation:CoverageReconciliation; coverage_rate:Decimal|None
    limitations:tuple[str,...]; provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        _require_aware(self.analysis_boundary,"Coverage boundary")
        if self.window_start is not None:_require_aware(self.window_start,"Coverage window start")
        if self.coverage_scope=="cumulative" and self.window_start is not None:_fail("cumulative Coverage cannot have a window start")
        if self.coverage_scope=="time-bounded" and (self.window_start is None or self.window_start>=self.analysis_boundary):_fail("bounded Coverage requires (start,end] chronology")
        if self.coverage_scope not in ("cumulative","time-bounded"):_fail("unknown Coverage scope")
        if not set(self.eligible_denominator_ids)<=set(self.coverage_universe_ids) or not set(self.measured_opportunity_ids)<=set(self.eligible_denominator_ids):_fail("Coverage population hierarchy conflicts")
        categories=[]
        for field in fields(self.reconciliation):categories.extend(getattr(self.reconciliation,field.name))
        if len(categories)!=len(set(categories)):_fail("Coverage reconciliation categories overlap")
        expected=set(self.coverage_universe_ids)
        if set(categories)!=expected:_fail("Coverage reconciliation is not exhaustive")
        rate=None if not self.eligible_denominator_ids else Decimal(len(self.measured_opportunity_ids))/Decimal(len(self.eligible_denominator_ids))
        if self.coverage_rate!=rate:_fail("Coverage rate uses the wrong denominator")
        _check_identity(self,"probability_source_coverage_v3",("probability_source_coverage_v3_id","provenance","input_digest"))


def create_probability_source_coverage_v3(*,protocol:StandaloneProbabilitySourceProtocol,analysis_boundary:datetime,
        coverage_scope:str="cumulative",window_start:datetime|None=None,
        activation:StandaloneResearchActivationBoundary,opportunities:Iterable[ResearchCaptureOpportunity],
        eligibility_contexts:Iterable[ResearchEventEligibilityContext],eligibility_results:Iterable[PopulationEligibilityResult],
        schedule_histories:Iterable[OutcomeHistory],classifications:Iterable[StandaloneEventClassificationEvidence],manifests:Iterable[HistoricalCandleQueryManifest]=(),
        candles:Iterable[HistoricalMarketCandleObservation]=(),historical_derivations:Iterable[HistoricalCandleProbabilityDerivation]=(),
        attempts:Iterable[ProspectiveCaptureAttempt]=(),snapshots:Iterable[ProspectiveStandaloneSnapshot]=(),
        market_observations:Iterable[MarketObservation]=(),market_series:Iterable[ProviderMarketSeries]=(),
        market_derivations:Iterable[MarketProbabilityDerivation]=(),measurements:Iterable[ProbabilitySourceMeasurementV3]=(),
        provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->ProbabilitySourceCoverageV3:
    if coverage_scope=="cumulative" and window_start is not None:_fail("cumulative Coverage cannot have a window start")
    if coverage_scope=="time-bounded" and (window_start is None or window_start>=analysis_boundary):_fail("bounded Coverage requires (start,end]")
    pid=protocol.standalone_probability_source_protocol_id
    manifest_values=tuple(manifests);candle_values=tuple(candles);historical_derivation_values=tuple(historical_derivations)
    attempt_values=tuple(attempts);snapshot_values=tuple(snapshots);market_observation_values=tuple(market_observations)
    market_series_values=tuple(market_series);market_derivation_values=tuple(market_derivations)
    history_values=tuple(schedule_histories)
    expected_opps=expected_schedule_opportunities(protocol=protocol,activation=activation,schedule_histories=history_values,analysis_boundary=analysis_boundary)
    all_opps=_unique((x for x in opportunities if x.protocol_id==pid),"Coverage opportunity registry",lambda x:x.research_capture_opportunity_id)
    if all_opps!=expected_opps:_fail("Coverage opportunity registry omits or invents schedule-derived authority")
    context_values=tuple(eligibility_contexts);result_values=tuple(eligibility_results)
    classification_values=tuple(classifications);classification_map={x.standalone_event_classification_evidence_id:x for x in classification_values}
    if len(classification_map)!=len(classification_values):_fail("Coverage classification registry contains duplicates")
    context_map={x.research_capture_opportunity_id:x for x in context_values};result_map={x.research_capture_opportunity_id:x for x in result_values}
    if len(context_map)!=len(context_values) or len(result_map)!=len(result_values):_fail("Coverage eligibility registries contain duplicates")
    history_map={x.canonical_event_id:x for x in history_values}
    if len(history_map)!=len(history_values):_fail("Coverage Schedule registry contains duplicates")
    scheduled={};eligibility_by_opp={}
    for opportunity in all_opps:
        context=context_map.get(opportunity.research_capture_opportunity_id);result=result_map.get(opportunity.research_capture_opportunity_id)
        if context is None or result is None:_fail("Coverage lacks complete eligibility authority")
        history=history_map.get(context.canonical_event_id)
        if history is None:_fail("Coverage lacks complete Schedule history")
        classification=classification_map.get(context.event_stage_evidence_id)
        if classification is None:_fail("Coverage lacks event-classification Evidence")
        rebuilt_context,rebuilt_result=create_standalone_eligibility_authority(protocol=protocol,opportunity=opportunity,outcome_history=history,
            classification=classification,classifications=classification_values,
            analysis_boundary=result.analysis_boundary,provenance=result.provenance)
        if (rebuilt_context,rebuilt_result)!=(context,result):_fail("Coverage eligibility authority fails deterministic replay")
        schedule=next((item for item in history.observations if item.observation_id==opportunity.schedule_observation_id and item.collected_at<=analysis_boundary),None)
        if schedule is None:_fail("Coverage opportunity Schedule authority is incomplete")
        validate_population_side(protocol,activation,schedule.scheduled_start)
        scheduled[opportunity.research_capture_opportunity_id]=schedule.scheduled_start;eligibility_by_opp[opportunity.research_capture_opportunity_id]=result
    def in_scope(oid:str)->bool:
        if coverage_scope=="cumulative":return True
        return window_start<scheduled[oid]<=analysis_boundary
    opp_values=tuple(x for x in all_opps if in_scope(x.research_capture_opportunity_id))
    universe=_unique((x.research_capture_opportunity_id for x in opp_values),"Coverage universe")
    eligible_values=tuple(oid for oid,result in eligibility_by_opp.items() if result.disposition is PopulationEligibilityDisposition.ELIGIBLE and result.validation_status is PopulationEligibilityValidationStatus.VALID and in_scope(oid))
    eligible=_unique(eligible_values,"eligible denominator")
    all_measurements=tuple(measurements);measurement_candidates=tuple(x for x in all_measurements if x.protocol_id==pid and x.effective_at<=analysis_boundary and x.opportunity_id in set(universe))
    measurement_values=[]
    for measurement in measurement_candidates:
        context=context_map.get(measurement.opportunity_id);history=None if context is None else history_map.get(context.canonical_event_id)
        finals=() if history is None else tuple(x for x in history.observations if x.authoritative_final and x.collected_at<=analysis_boundary)
        if finals and measurement.outcome_observation_id==finals[-1].observation_id:measurement_values.append(measurement)
    measurement_values=tuple(measurement_values)
    mids=_unique((x.probability_source_measurement_v3_id for x in measurement_values),"Measurement registry")
    measured=_unique((x.opportunity_id for x in measurement_values),"measured opportunity mapping")
    if len(measured)!=len(measurement_values):_fail("Coverage requires exactly one Measurement per measured opportunity")
    by_opp={x.research_capture_opportunity_id:x for x in opp_values}
    for measurement in measurement_values:
        opportunity=by_opp.get(measurement.opportunity_id)
        if opportunity is None or opportunity.schedule_observation_id!=measurement.schedule_observation_id:_fail("Measurement is unrelated to measured opportunity")
    if not set(measured)<=set(eligible):_fail("measured population is outside eligible denominator")
    manifests_by_opp={oid:tuple(x for x in manifest_values if x.protocol_id==pid and x.opportunity_id==oid) for oid in universe}
    visible_hder=tuple(x for x in historical_derivation_values if x.protocol_id==pid and x.effective_at<=analysis_boundary)
    hder_registry={x.historical_candle_probability_derivation_id:x for x in visible_hder}
    if any(hder_registry[x.historical_candle_probability_derivation_id]!=x for x in visible_hder):_fail("conflicting historical derivation identity")
    hder_by_opp={oid:tuple(x for x in hder_registry.values() if x.opportunity_id==oid) for oid in universe}
    attempts_by_opp={oid:tuple(x for x in attempt_values if x.protocol_id==pid and x.opportunity_id==oid) for oid in universe}
    selected_snapshots=select_authoritative_prospective_snapshots(tuple(x for x in snapshot_values if x.protocol_id==pid),analysis_boundary) if protocol.design_tag is StandaloneDesignTag.PROSPECTIVE and snapshot_values else ()
    snapshots_by_opp={oid:tuple(x for x in selected_snapshots if x.opportunity_id==oid) for oid in universe}
    visible_mder=tuple(x for x in market_derivation_values if x.protocol_id==pid and x.effective_at<=analysis_boundary)
    mder_registry={x.market_probability_derivation_id:x for x in visible_mder}
    if any(mder_registry[x.market_probability_derivation_id]!=x for x in visible_mder):_fail("conflicting market derivation identity")
    mder_by_snapshot={}
    for snapshot_id in {x.research_snapshot_id for x in mder_registry.values()}:
        candidates=tuple(x for x in mder_registry.values() if x.research_snapshot_id==snapshot_id)
        if len(candidates)>1:_fail("ambiguous prospective derivation authority")
        mder_by_snapshot[snapshot_id]=candidates[0]
    measurement_by_opp={x.opportunity_id:x for x in measurement_values}
    observation_map={x.observation_id:x for x in market_observation_values};series_map={x.series_id:x for x in market_series_values}
    categories={item.name:[] for item in fields(RetrospectiveCoverageReconciliation if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE else ProspectiveCoverageReconciliation)}
    protocol_manifests=tuple(x for x in manifest_values if x.protocol_id==pid)
    terminal_manifests=validate_manifest_lineage(protocol_manifests,analysis_boundary) if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE and protocol_manifests else ()
    for oid in universe:
        result=eligibility_by_opp[oid];target=scheduled[oid]+timedelta(minutes=int(_rule_parameter(protocol.scope_rule,"target_offset_minutes")))
        if target>analysis_boundary:category="capture_not_yet_due"
        elif result.disposition is not PopulationEligibilityDisposition.ELIGIBLE or result.validation_status is not PopulationEligibilityValidationStatus.VALID:category="protocol_ineligible"
        elif protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE:
            lineage=manifests_by_opp[oid];terminal=tuple(x for x in terminal_manifests if x.opportunity_id==oid)
            if not lineage:category="archive_unavailable"
            elif len(terminal)!=1 or terminal[0].validation_status is not ManifestValidationStatus.COMPLETE:category="archive_invalid"
            else:
                manifest=terminal[0]
                owned=tuple(x for x in candle_values if x.manifest_id==manifest.historical_candle_query_manifest_id)
                try:owned=reconcile_manifest_candles(manifest,owned)
                except ContractError:category="candle_invalid"
                else:
                    candidates=tuple(x for x in owned if target-timedelta(minutes=5)<x.candle_end_at<=target)
                    if not candidates:category="candle_unavailable"
                    elif any(x.close_yes_bid is None or x.close_yes_ask is None or x.canonical_event_id!=manifest.canonical_event_id or x.proposition_id!=manifest.proposition_id for x in candidates):category="candle_invalid"
                    elif len(tuple(x for x in hder_by_opp[oid] if x.manifest_id==manifest.historical_candle_query_manifest_id))>1:_fail("ambiguous historical derivation authority")
                    elif len(tuple(x for x in hder_by_opp[oid] if x.manifest_id==manifest.historical_candle_query_manifest_id))!=1:category="derivation_unavailable"
                    else:
                        derivation=next(x for x in hder_by_opp[oid] if x.manifest_id==manifest.historical_candle_query_manifest_id);opportunity=by_opp[oid];context=context_map[oid];result=eligibility_by_opp[oid];history=history_map[context.canonical_event_id]
                        try:rebuilt=create_historical_candle_probability_derivation(protocol=protocol,activation=activation,opportunity=opportunity,
                            eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,
                            manifest=manifest,manifests=protocol_manifests,candles=owned,
                            home_participant_id=derivation.home_participant_id,complement_outcome_id=derivation.complement_outcome_id,
                            effective_at=derivation.effective_at,provenance=derivation.provenance,limitations=derivation.limitations)
                        except ContractError:category="derivation_unavailable"
                        else:
                            measurement=measurement_by_opp.get(oid)
                            category="measured" if rebuilt==derivation and measurement is not None and measurement.derivation_id==derivation.historical_candle_probability_derivation_id else "outcome_unresolved" if rebuilt==derivation else "derivation_unavailable"
        else:
            owned_attempts=attempts_by_opp[oid];terminal=snapshots_by_opp[oid]
            if len(terminal)!=1:category="timing_invalid"
            elif terminal[0].terminal_disposition is SnapshotTerminalDisposition.CAPTURED_VALID:
                selected=next((x for x in owned_attempts if isinstance(x.result,CapturedValid)),None)
                if selected is None:category="timing_invalid"
                elif terminal[0].prospective_standalone_snapshot_id not in mder_by_snapshot:category="derivation_unavailable"
                else:
                    snapshot=terminal[0];derivation=mder_by_snapshot[snapshot.prospective_standalone_snapshot_id];opportunity=by_opp[oid]
                    context=context_map[oid];result=eligibility_by_opp[oid];history=history_map[context.canonical_event_id]
                    observation=observation_map.get(derivation.market_observation_id);series=series_map.get(derivation.market_series_id)
                    if observation is None or series is None:category="derivation_unavailable"
                    else:
                        try:
                            replayed_snapshot=reconcile_prospective_snapshot(protocol=protocol,opportunity=opportunity,activation=activation,
                                eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,
                                attempts=owned_attempts,window_closed_at=snapshot.target_at+timedelta(minutes=5),provenance=snapshot.provenance,limitations=snapshot.limitations)
                            immutable=tuple(name for name in snapshot.__dataclass_fields__ if name not in _SNAPSHOT_CORRECTION_FIELDS)
                            if any(getattr(snapshot,name)!=getattr(replayed_snapshot,name) for name in immutable):_fail("Snapshot replay conflict")
                            rebuilt=create_standalone_market_probability_derivation(protocol=protocol,activation=activation,opportunity=opportunity,
                                eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,
                                snapshot=snapshot,snapshots=snapshot_values,attempts=owned_attempts,observation=observation,
                                market_observations=market_observation_values,series=series,effective_at=derivation.effective_at,
                                provenance=derivation.provenance,limitations=derivation.limitations)
                        except ContractError:category="derivation_unavailable"
                        else:
                            measurement=measurement_by_opp.get(oid)
                            category="measured" if rebuilt==derivation and measurement is not None and measurement.derivation_id==derivation.market_probability_derivation_id else "outcome_unresolved" if rebuilt==derivation else "derivation_unavailable"
            else:
                try:
                    opportunity=by_opp[oid];context=context_map[oid];result=eligibility_by_opp[oid];history=history_map[context.canonical_event_id]
                    replayed=reconcile_prospective_snapshot(protocol=protocol,opportunity=opportunity,activation=activation,
                        eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,
                        attempts=owned_attempts,window_closed_at=terminal[0].target_at+timedelta(minutes=5),provenance=terminal[0].provenance,limitations=terminal[0].limitations)
                    immutable=tuple(name for name in terminal[0].__dataclass_fields__ if name not in _SNAPSHOT_CORRECTION_FIELDS)
                    if any(getattr(terminal[0],name)!=getattr(replayed,name) for name in immutable):_fail("Snapshot replay conflict")
                except ContractError:category="timing_invalid"
                else:
                    # Explicit precedence when no valid success exists: acquired-invalid,
                    # provider-call failure, then pure non-acquisition missed window.
                    if any(isinstance(x.result,CapturedInvalid) for x in owned_attempts):category="captured_invalid"
                    elif any(isinstance(x.result,AcquisitionFailed) for x in owned_attempts):category="acquisition_failed"
                    elif owned_attempts and all(isinstance(x.result,Missed) for x in owned_attempts):category="missed_window"
                    else:category="timing_invalid"
        categories[category].append(oid)
    reconciliation_type=RetrospectiveCoverageReconciliation if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE else ProspectiveCoverageReconciliation
    reconciliation=reconciliation_type(**{key:tuple(sorted(value)) for key,value in categories.items()})
    derived_measured=tuple(sorted(categories["measured"]))
    if measured!=derived_measured:_fail("Coverage Measurement registry does not equal replayed successful population")
    rate=None if not eligible else Decimal(len(measured))/Decimal(len(eligible))
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=protocol.standalone_probability_source_protocol_id,
        design_tag=protocol.design_tag,source_reference_id=protocol.source.probability_source_reference_id,coverage_scope=coverage_scope,
        window_start=window_start,analysis_boundary=analysis_boundary,
        coverage_universe_ids=universe,eligible_denominator_ids=eligible,measured_opportunity_ids=measured,measurement_ids=mids,
        reconciliation=reconciliation,coverage_rate=rate,limitations=_unique(limitations,"Coverage limitations"),provenance=provenance)
    return _identity(ProbabilitySourceCoverageV3,"probability_source_coverage_v3",vals,("probability_source_coverage_v3_id","provenance","input_digest"))


class PerformanceScope(str,Enum): CUMULATIVE="cumulative"; TIME_BOUNDED="time-bounded"
@dataclass(frozen=True,slots=True)
class OneSampleUncertaintyV3:
    scope:PerformanceScope; point_estimate:Decimal|None; sample_size:int; lower:Decimal|None; upper:Decimal|None
    confidence_level:Decimal; resample_count:int; statistical_rule_id:str; statistical_rule_version:str
    analysis_algorithm_version:str; seed_digest:str; limitations:tuple[str,...]
@dataclass(frozen=True,slots=True)
class CalibrationV3:
    rule_id:str;rule_version:str;boundaries:tuple[Decimal,...];endpoint_semantics:str
    weighting_rule:str;empty_bin_rule:str;sample_size:int;bin_counts:tuple[int,...];wace:Decimal|None


def create_one_sample_uncertainty_v3(*,protocol:StandaloneProbabilitySourceProtocol,scope:PerformanceScope,
        analysis_boundary:datetime,analysis_start:datetime|None,measurements:Iterable[ProbabilitySourceMeasurementV3],
        algorithm_version:str="3")->OneSampleUncertaintyV3:
    ordered=_unique(measurements,"uncertainty Measurements",lambda x:x.probability_source_measurement_v3_id)
    scores=tuple(x.brier_score for x in ordered);n=len(scores)
    with localcontext() as context:context.prec=PRECISION;point=None if not n else sum(scores,Decimal(0))/n
    confidence=Decimal(_rule_parameter(protocol.uncertainty_rule,"confidence_level"));count=int(_rule_parameter(protocol.uncertainty_rule,"resamples"))
    if not Decimal(0)<confidence<Decimal(1) or count<1:_fail("invalid Protocol uncertainty settings")
    ids=tuple(x.probability_source_measurement_v3_id for x in ordered)
    seed_material=(protocol.standalone_probability_source_protocol_id,protocol.source.probability_source_reference_id,
        protocol.design_tag,scope,analysis_boundary,analysis_start,analysis_boundary if scope is PerformanceScope.TIME_BOUNDED else None,
        ids,protocol.uncertainty_rule.rule_id,protocol.uncertainty_rule.rule_version,confidence,count,algorithm_version)
    seed=_digest(seed_material);limits=[]
    if not n:lower=upper=None
    elif n==1:lower=upper=point;limits.append("single observation; interval is deterministically degenerate")
    elif len(set(scores))==1:lower=upper=point;limits.append("no observed score variation; interval has zero width")
    else:
        rng=random.Random(int(seed,16));replicates=[]
        for _ in range(count):
            sample=tuple(scores[rng.randrange(n)] for __ in range(n))
            with localcontext() as context:context.prec=PRECISION;replicates.append(sum(sample,Decimal(0))/n)
        replicates.sort();alpha=(Decimal(1)-confidence)/2;lo=int(alpha*count);hi=min(count-1,int((Decimal(1)-alpha)*count));lower,upper=replicates[lo],replicates[hi]
    return OneSampleUncertaintyV3(scope,point,n,lower,upper,confidence,count,protocol.uncertainty_rule.rule_id,
        protocol.uncertainty_rule.rule_version,algorithm_version,seed,tuple(limits))


@dataclass(frozen=True,slots=True)
class ProbabilitySourcePerformanceV3:
    probability_source_performance_v3_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; design_tag:StandaloneDesignTag; derivation_kind:DerivationKindV3; source_reference_id:str
    scope:PerformanceScope; analysis_start:datetime|None; analysis_boundary:datetime
    measurement_ids:tuple[str,...]; coverage_id:str; sample_size:int; mean_brier_score:Decimal|None
    mean_log_loss:Decimal|None; calibration:CalibrationV3; uncertainty:OneSampleUncertaintyV3
    limitations:tuple[str,...]; provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        _require_aware(self.analysis_boundary,"performance boundary")
        if self.analysis_start is not None:_require_aware(self.analysis_start,"performance start")
        if self.scope is PerformanceScope.CUMULATIVE and self.analysis_start is not None:_fail("cumulative performance cannot have a selective start")
        if self.scope is PerformanceScope.TIME_BOUNDED and (self.analysis_start is None or self.analysis_start>=self.analysis_boundary):_fail("time-bounded performance requires a valid interval")
        if self.sample_size!=len(self.measurement_ids):_fail("performance sample size conflicts")
        _check_identity(self,"probability_source_performance_v3",("probability_source_performance_v3_id","provenance","input_digest"))


def create_probability_source_performance_v3(*,protocol:StandaloneProbabilitySourceProtocol,coverage:ProbabilitySourceCoverageV3,
        measurements:Iterable[ProbabilitySourceMeasurementV3],scope:PerformanceScope,analysis_boundary:datetime,
        analysis_start:datetime|None,provenance:ResearchContractProvenance,limitations:tuple[str,...]=())->ProbabilitySourcePerformanceV3:
    values=tuple(measurements);ids=_unique((x.probability_source_measurement_v3_id for x in values),"performance Measurements")
    if coverage.protocol_id!=protocol.standalone_probability_source_protocol_id or ids!=coverage.measurement_ids:_fail("performance must use exact matching Coverage population")
    if (scope is PerformanceScope.CUMULATIVE)!=(coverage.coverage_scope=="cumulative"):_fail("performance scope requires matching Coverage scope")
    if scope is PerformanceScope.TIME_BOUNDED and (coverage.window_start,coverage.analysis_boundary)!=(analysis_start,analysis_boundary):_fail("bounded performance requires matching bounded Coverage")
    if scope is PerformanceScope.CUMULATIVE and coverage.analysis_boundary!=analysis_boundary:_fail("cumulative performance boundary conflicts with Coverage")
    if any(x.protocol_id!=coverage.protocol_id or x.design_tag is not protocol.design_tag for x in values):_fail("performance population mixes Protocols")
    kinds={x.derivation_kind for x in values};expected=DerivationKindV3.HISTORICAL_CANDLE if protocol.design_tag is StandaloneDesignTag.RETROSPECTIVE else DerivationKindV3.PROSPECTIVE_MARKET
    if kinds and kinds!={expected}:_fail("performance mixes derivation kinds")
    n=len(values);logs=tuple(x.log_loss for x in values)
    with localcontext() as context:
        context.prec=PRECISION;mean_b=None if not n else sum((x.brier_score for x in values),Decimal(0))/n
        mean_l=None if not n else Decimal("Infinity") if Decimal("Infinity") in logs else sum(logs,Decimal(0))/n
    uncertainty=create_one_sample_uncertainty_v3(protocol=protocol,scope=scope,analysis_boundary=analysis_boundary,
        analysis_start=analysis_start,measurements=values)
    # Protocol-governed fixed-bin WACE; empty bins do not contribute.
    gaps=[];bin_counts=[]
    boundaries=_calibration_boundaries(protocol.calibration_rule)
    for i,(lo,hi) in enumerate(zip(boundaries,boundaries[1:])):
        bucket=tuple(x for x in values if lo<=x.calibration_probability and (x.calibration_probability<=hi if i==len(boundaries)-2 else x.calibration_probability<hi))
        bin_counts.append(len(bucket))
        if bucket:
            with localcontext() as context:
                context.prec=PRECISION;forecast=sum((x.calibration_probability for x in bucket),Decimal(0))/len(bucket)
                observed=Decimal(sum(int(x.realized_outcome_id==x.canonical_proposition_outcome_id) for x in bucket))/len(bucket)
                gaps.append(Decimal(len(bucket))/n*abs(observed-forecast))
    with localcontext() as context:context.prec=PRECISION;wace=None if not n else sum(gaps,Decimal(0))
    calibration=CalibrationV3(protocol.calibration_rule.rule_id,protocol.calibration_rule.rule_version,boundaries,
        _rule_parameter(protocol.calibration_rule,"endpoint_semantics"),_rule_parameter(protocol.calibration_rule,"weighting"),
        _rule_parameter(protocol.calibration_rule,"empty_bins"),n,tuple(bin_counts),wace)
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=coverage.protocol_id,design_tag=protocol.design_tag,
        derivation_kind=expected,source_reference_id=coverage.source_reference_id,scope=scope,analysis_start=analysis_start,analysis_boundary=analysis_boundary,
        measurement_ids=ids,coverage_id=coverage.probability_source_coverage_v3_id,sample_size=n,mean_brier_score=mean_b,mean_log_loss=mean_l,
        calibration=calibration,uncertainty=uncertainty,limitations=_unique(limitations,"performance limitations"),provenance=provenance)
    return _identity(ProbabilitySourcePerformanceV3,"probability_source_performance_v3",vals,("probability_source_performance_v3_id","provenance","input_digest"))


@dataclass(frozen=True,slots=True)
class ProbabilitySourcePerformanceReport:
    probability_source_performance_report_id:str; schema_version:str; identity_algorithm_version:str
    protocol_id:str; design_tag:StandaloneDesignTag; source_reference_id:str; cumulative_performance_id:str
    time_bounded_performance_ids:tuple[str,...]; coverage_ids:tuple[str,...]; analysis_boundary:datetime; report_boundary:datetime
    descriptive_findings:tuple[str,...]; limitations:tuple[str,...]; provenance:ResearchContractProvenance; input_digest:str
    def __post_init__(self)->None:
        for value in (self.analysis_boundary,self.report_boundary):_require_aware(value,"report boundary")
        if self.report_boundary<self.analysis_boundary:_fail("report is backdated")
        _check_identity(self,"probability_source_performance_report",("probability_source_performance_report_id","provenance","input_digest"))


def create_probability_source_performance_report(*,protocol:StandaloneProbabilitySourceProtocol,
        cumulative:ProbabilitySourcePerformanceV3,time_bounded:Iterable[ProbabilitySourcePerformanceV3],
        performances:Iterable[ProbabilitySourcePerformanceV3],coverages:Iterable[ProbabilitySourceCoverageV3],
        analysis_boundary:datetime,report_boundary:datetime,descriptive_findings:tuple[str,...],limitations:tuple[str,...],
        provenance:ResearchContractProvenance)->ProbabilitySourcePerformanceReport:
    registry=tuple(performances);by_id={x.probability_source_performance_v3_id:x for x in registry}
    if len(by_id)!=len(registry):_fail("performance report registry contains duplicates")
    bounded=_unique(tuple(time_bounded),"time-bounded report references",lambda x:x.probability_source_performance_v3_id)
    supplied={cumulative.probability_source_performance_v3_id}|{x.probability_source_performance_v3_id for x in bounded}
    if set(by_id)!=supplied:_fail("report has missing, extra, or selectively supplied performance authority")
    if cumulative.scope is not PerformanceScope.CUMULATIVE or any(x.scope is not PerformanceScope.TIME_BOUNDED for x in bounded):_fail("report performance scope conflict")
    coverage_values=tuple(coverages);coverage_map={x.probability_source_coverage_v3_id:x for x in coverage_values}
    if len(coverage_map)!=len(coverage_values):_fail("report Coverage registry contains duplicates")
    if set(coverage_map)!={x.coverage_id for x in registry}:_fail("report has missing, extra, or selectively supplied Coverage authority")
    if any(x.protocol_id!=protocol.standalone_probability_source_protocol_id or x.analysis_boundary!=analysis_boundary for x in registry):_fail("report references foreign or incompatible performance authority")
    for performance in registry:
        coverage=coverage_map[performance.coverage_id]
        expected_scope="cumulative" if performance.scope is PerformanceScope.CUMULATIVE else "time-bounded"
        if coverage.protocol_id!=performance.protocol_id or coverage.coverage_scope!=expected_scope or coverage.measurement_ids!=performance.measurement_ids:_fail("report performance/Coverage compatibility conflict")
    required=_report_windows(protocol.report_rule)
    actual=tuple(sorted(x.analysis_boundary-x.analysis_start for x in bounded))
    if actual!=required:_fail("report lacks exact Protocol-required bounded-window set")
    if len({(x.analysis_start,x.analysis_boundary) for x in bounded})!=len(bounded):_fail("report contains duplicate bounded windows")
    vals=dict(schema_version=SCHEMA_VERSION,identity_algorithm_version=IDENTITY_VERSION,protocol_id=protocol.standalone_probability_source_protocol_id,
        design_tag=protocol.design_tag,source_reference_id=protocol.source.probability_source_reference_id,
        cumulative_performance_id=cumulative.probability_source_performance_v3_id,
        time_bounded_performance_ids=tuple(x.probability_source_performance_v3_id for x in bounded),coverage_ids=tuple(sorted(coverage_map)),
        analysis_boundary=analysis_boundary,report_boundary=report_boundary,descriptive_findings=_unique(descriptive_findings,"descriptive findings"),
        limitations=_unique(limitations,"report limitations"),provenance=provenance)
    return _identity(ProbabilitySourcePerformanceReport,"probability_source_performance_report",vals,("probability_source_performance_report_id","provenance","input_digest"))


def validate_standalone_research_graph(*,activation_boundaries:Iterable[StandaloneResearchActivationBoundary],
        protocols:Iterable[StandaloneProbabilitySourceProtocol],opportunities:Iterable[ResearchCaptureOpportunity]=(),
        classifications:Iterable[StandaloneEventClassificationEvidence]=(),
        eligibility_contexts:Iterable[ResearchEventEligibilityContext]=(),eligibility_results:Iterable[PopulationEligibilityResult]=(),
        manifests:Iterable[HistoricalCandleQueryManifest]=(),candles:Iterable[HistoricalMarketCandleObservation]=(),
        historical_derivations:Iterable[HistoricalCandleProbabilityDerivation]=(),attempts:Iterable[ProspectiveCaptureAttempt]=(),
        snapshots:Iterable[ProspectiveStandaloneSnapshot]=(),market_observations:Iterable[MarketObservation]=(),
        market_series:Iterable[ProviderMarketSeries]=(),market_derivations:Iterable[MarketProbabilityDerivation]=(),
        outcome_histories:Iterable[OutcomeHistory]=(),measurements:Iterable[ProbabilitySourceMeasurementV3]=(),
        coverages:Iterable[ProbabilitySourceCoverageV3]=(),performances:Iterable[ProbabilitySourcePerformanceV3]=(),
        reports:Iterable[ProbabilitySourcePerformanceReport]=(),analysis_boundary:datetime)->tuple[ProbabilitySourcePerformanceReport,...]:
    """Rebuild every supplied downstream artifact from exact upstream authority."""
    _require_aware(analysis_boundary,"graph boundary")
    def reg(values,label,key):
        vals=tuple(values);result={key(x):x for x in vals}
        if len(result)!=len(vals):_fail(f"{label} contains duplicate or conflicting authority")
        return vals,result
    activation_values,activation_map=reg(activation_boundaries,"activation registry",lambda x:x.standalone_research_activation_boundary_id)
    protocol_values,protocol_map=reg(protocols,"Protocol registry",lambda x:x.standalone_probability_source_protocol_id)
    if not protocol_values:_fail("graph requires at least one standalone Protocol")
    if len({x.design_tag for x in protocol_values})!=len(protocol_values):_fail("graph contains duplicate study-family Protocol authority")
    for protocol in protocol_values:
        if protocol.activation_boundary_id not in activation_map:_fail("Protocol activation authority does not resolve")
    opp_values,opp_map=reg(opportunities,"opportunity registry",lambda x:x.research_capture_opportunity_id)
    classification_values,classification_map=reg(classifications,"classification registry",lambda x:x.standalone_event_classification_evidence_id)
    select_authoritative_event_classifications(classification_values,analysis_boundary)
    context_values,context_map=reg(eligibility_contexts,"eligibility context registry",lambda x:x.research_capture_opportunity_id)
    result_values,result_map=reg(eligibility_results,"eligibility result registry",lambda x:x.research_capture_opportunity_id)
    history_values,history_map=reg(outcome_histories,"Schedule/Outcome registry",lambda x:x.canonical_event_id)
    for protocol in protocol_values:
        expected=expected_schedule_opportunities(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],schedule_histories=history_values,analysis_boundary=analysis_boundary)
        supplied=tuple(sorted((x for x in opp_values if x.protocol_id==protocol.standalone_probability_source_protocol_id),key=lambda x:x.research_capture_opportunity_id))
        if supplied!=expected:_fail("graph opportunity registry omits or invents Schedule authority")
    for opportunity in opp_values:
        protocol=protocol_map.get(opportunity.protocol_id);context=context_map.get(opportunity.research_capture_opportunity_id);result=result_map.get(opportunity.research_capture_opportunity_id)
        if protocol is None or context is None or result is None:_fail("opportunity lacks complete standalone authority")
        history=history_map.get(context.canonical_event_id)
        if history is None:_fail("opportunity lacks Schedule history")
        classification=classification_map.get(context.event_stage_evidence_id)
        if classification is None:_fail("opportunity lacks classification Evidence")
        rebuilt_context,rebuilt_result=create_standalone_eligibility_authority(protocol=protocol,opportunity=opportunity,outcome_history=history,
            classification=classification,classifications=classification_values,
            analysis_boundary=result.analysis_boundary,provenance=result.provenance)
        if (rebuilt_context,rebuilt_result)!=(context,result):_fail("eligibility authority fails deterministic replay")
        if result.disposition is PopulationEligibilityDisposition.ELIGIBLE and result.validation_status is PopulationEligibilityValidationStatus.VALID:
            resolve_standalone_schedule_authority(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],opportunity=opportunity,
                eligibility_context=context,eligibility_result=result,outcome_history=history,analysis_boundary=analysis_boundary)
    manifest_values,manifest_map=reg(manifests,"manifest registry",lambda x:x.historical_candle_query_manifest_id)
    terminals=validate_manifest_lineage(manifest_values,analysis_boundary) if manifest_values else ()
    candle_values,candle_map=reg(candles,"candle registry",lambda x:x.historical_market_candle_observation_id)
    for manifest in manifest_values:
        if manifest.protocol_id not in protocol_map or protocol_map[manifest.protocol_id].design_tag is not StandaloneDesignTag.RETROSPECTIVE:_fail("manifest lacks retrospective Protocol")
        owned=tuple(x for x in candle_values if x.manifest_id==manifest.historical_candle_query_manifest_id)
        reconcile_manifest_candles(manifest,owned)
    hder_values,hder_map=reg(historical_derivations,"historical derivation registry",lambda x:x.historical_candle_probability_derivation_id)
    for derivation in hder_values:
        protocol=protocol_map.get(derivation.protocol_id);opportunity=opp_map.get(derivation.opportunity_id);manifest=manifest_map.get(derivation.manifest_id)
        if protocol is None or opportunity is None or manifest is None:_fail("historical derivation upstream authority does not resolve")
        context=context_map[opportunity.research_capture_opportunity_id];result=result_map[opportunity.research_capture_opportunity_id];history=history_map[context.canonical_event_id]
        rebuilt=create_historical_candle_probability_derivation(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],opportunity=opportunity,
            eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,manifest=manifest,
            manifests=manifest_values,candles=tuple(x for x in candle_values if x.manifest_id==manifest.historical_candle_query_manifest_id),
            home_participant_id=derivation.home_participant_id,complement_outcome_id=derivation.complement_outcome_id,
            effective_at=derivation.effective_at,provenance=derivation.provenance,limitations=derivation.limitations)
        if rebuilt!=derivation:_fail("historical derivation fails deterministic replay")
    attempt_values,attempt_map=reg(attempts,"attempt registry",lambda x:x.prospective_capture_attempt_id)
    snapshot_values,snapshot_map=reg(snapshots,"Snapshot registry",lambda x:x.prospective_standalone_snapshot_id)
    selected_snapshots=select_authoritative_prospective_snapshots(snapshot_values,analysis_boundary) if snapshot_values else ()
    for snapshot in selected_snapshots:
        protocol=protocol_map.get(snapshot.protocol_id);opportunity=opp_map.get(snapshot.opportunity_id)
        if protocol is None or opportunity is None:_fail("Snapshot upstream authority does not resolve")
        context=context_map[snapshot.opportunity_id];result=result_map[snapshot.opportunity_id];history=history_map[context.canonical_event_id]
        owned=tuple(x for x in attempt_values if x.opportunity_id==snapshot.opportunity_id)
        rebuilt=reconcile_prospective_snapshot(protocol=protocol,opportunity=opportunity,activation=activation_map[protocol.activation_boundary_id],
            eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,attempts=owned,
            window_closed_at=snapshot.target_at+timedelta(minutes=5),provenance=snapshot.provenance,limitations=snapshot.limitations)
        immutable=tuple(name for name in snapshot.__dataclass_fields__ if name not in _SNAPSHOT_CORRECTION_FIELDS)
        if any(getattr(snapshot,name)!=getattr(rebuilt,name) for name in immutable):_fail("Snapshot fails deterministic replay")
    observation_values,observation_map=reg(market_observations,"Market Evidence registry",lambda x:x.observation_id)
    series_values,series_map=reg(market_series,"Market Series registry",lambda x:x.series_id)
    mder_values,mder_map=reg(market_derivations,"market derivation registry",lambda x:x.market_probability_derivation_id)
    for derivation in mder_values:
        protocol=protocol_map.get(derivation.protocol_id);snapshot=snapshot_map.get(derivation.research_snapshot_id);observation=observation_map.get(derivation.market_observation_id);series=series_map.get(derivation.market_series_id)
        if None in (protocol,snapshot,observation,series):_fail("market derivation upstream authority does not resolve")
        opportunity=opp_map[snapshot.opportunity_id];context=context_map[snapshot.opportunity_id];result=result_map[snapshot.opportunity_id];history=history_map[context.canonical_event_id]
        rebuilt=create_standalone_market_probability_derivation(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],opportunity=opportunity,
            eligibility_context=context,eligibility_result=result,schedule_history=history,analysis_boundary=analysis_boundary,snapshot=snapshot,
            snapshots=snapshot_values,attempts=tuple(x for x in attempt_values if x.opportunity_id==snapshot.opportunity_id),observation=observation,
            market_observations=observation_values,series=series,effective_at=derivation.effective_at,provenance=derivation.provenance,limitations=derivation.limitations)
        if rebuilt!=derivation:_fail("market derivation fails deterministic replay")
    measurement_values,measurement_map=reg(measurements,"Measurement registry",lambda x:x.probability_source_measurement_v3_id)
    for measurement in measurement_values:
        protocol=protocol_map.get(measurement.protocol_id);opportunity=opp_map.get(measurement.opportunity_id)
        if protocol is None or opportunity is None:_fail("Measurement opportunity authority does not resolve")
        context=context_map[measurement.opportunity_id];result=result_map[measurement.opportunity_id];history=history_map[context.canonical_event_id]
        derivation=(hder_map if measurement.derivation_kind is DerivationKindV3.HISTORICAL_CANDLE else mder_map).get(measurement.derivation_id)
        outcome_history=history_map.get(measurement.canonical_event_id);outcome=next((x for x in outcome_history.observations if x.observation_id==measurement.outcome_observation_id),None) if outcome_history else None
        if derivation is None or outcome is None:_fail("Measurement derivation or Outcome does not resolve")
        rebuilt=create_probability_source_measurement_v3(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],opportunity=opportunity,
            eligibility_context=context,eligibility_result=result,schedule_history=history,snapshots=snapshot_values,derivations=(derivation,),outcome=outcome,
            outcome_histories=history_values,effective_at=measurement.effective_at,provenance=measurement.provenance,limitations=measurement.limitations)
        if rebuilt!=measurement:_fail("Measurement fails deterministic replay")
    coverage_values,coverage_map=reg(coverages,"Coverage registry",lambda x:x.probability_source_coverage_v3_id)
    for coverage in coverage_values:
        protocol=protocol_map.get(coverage.protocol_id)
        if protocol is None:_fail("Coverage Protocol does not resolve")
        coverage_opportunities=expected_schedule_opportunities(protocol=protocol,activation=activation_map[protocol.activation_boundary_id],schedule_histories=history_values,analysis_boundary=coverage.analysis_boundary)
        rebuilt=create_probability_source_coverage_v3(protocol=protocol,analysis_boundary=coverage.analysis_boundary,coverage_scope=coverage.coverage_scope,
            window_start=coverage.window_start,activation=activation_map[protocol.activation_boundary_id],opportunities=coverage_opportunities,
            eligibility_contexts=context_values,eligibility_results=result_values,schedule_histories=history_values,classifications=classification_values,
            manifests=manifest_values,candles=candle_values,historical_derivations=hder_values,attempts=attempt_values,snapshots=snapshot_values,
            market_observations=observation_values,market_series=series_values,market_derivations=mder_values,
            measurements=measurement_values,
            provenance=coverage.provenance,limitations=coverage.limitations)
        if rebuilt!=coverage:_fail("Coverage fails deterministic replay")
    performance_values,performance_map=reg(performances,"performance registry",lambda x:x.probability_source_performance_v3_id)
    for performance in performance_values:
        protocol=protocol_map.get(performance.protocol_id);coverage=coverage_map.get(performance.coverage_id)
        if protocol is None or coverage is None:_fail("performance Protocol or Coverage does not resolve")
        rebuilt=create_probability_source_performance_v3(protocol=protocol,coverage=coverage,measurements=tuple(measurement_map[x] for x in performance.measurement_ids),
            scope=performance.scope,analysis_boundary=performance.analysis_boundary,analysis_start=performance.analysis_start,
            provenance=performance.provenance,limitations=performance.limitations)
        if rebuilt!=performance:_fail("performance fails deterministic replay")
    report_values,report_map=reg(reports,"report registry",lambda x:x.probability_source_performance_report_id)
    for report in report_values:
        protocol=protocol_map.get(report.protocol_id);cumulative=performance_map.get(report.cumulative_performance_id)
        if protocol is None or cumulative is None:_fail("report Protocol or cumulative performance does not resolve")
        bounded=tuple(performance_map[x] for x in report.time_bounded_performance_ids if x in performance_map)
        if len(bounded)!=len(report.time_bounded_performance_ids):_fail("report bounded performance does not resolve")
        rebuilt=create_probability_source_performance_report(protocol=protocol,cumulative=cumulative,time_bounded=bounded,
            performances=(cumulative,)+bounded,coverages=tuple(coverage_map[x] for x in report.coverage_ids),analysis_boundary=report.analysis_boundary,
            report_boundary=report.report_boundary,descriptive_findings=report.descriptive_findings,limitations=report.limitations,provenance=report.provenance)
        if rebuilt!=report:_fail("report fails deterministic replay")
    if len({x.protocol_id for x in report_values})!=len(report_values):_fail("graph pools or duplicates study report roots")
    return tuple(sorted(report_values,key=lambda x:x.design_tag.value))


_LOCAL_CONTRACTS=(StandaloneRule,StandaloneResearchActivationBoundary,StandaloneEventClassificationEvidence,RetrospectiveStandaloneDesign,ProspectiveStandaloneDesign,
    StandaloneProbabilitySourceProtocol,HistoricalCandleRetrievalPage,HistoricalCandleQueryManifest,HistoricalMarketCandleObservation,
    HistoricalCandleProbabilityDerivation,CapturedValid,CapturedInvalid,AcquisitionFailed,Missed,SkippedAfterSuccess,
    ProspectiveCaptureAttempt,ProspectiveStandaloneSnapshot,ProbabilitySourceMeasurementV3,
    RetrospectiveCoverageReconciliation,ProspectiveCoverageReconciliation,ProbabilitySourceCoverageV3,
    OneSampleUncertaintyV3,CalibrationV3,ProbabilitySourcePerformanceV3,ProbabilitySourcePerformanceReport)
_LOCAL_ENUMS=(StandaloneDesignTag,EventClassificationValidationStatus,ManifestValidationStatus,AttemptFailureCategory,AttemptValidationFailure,
              SnapshotTerminalDisposition,DerivationKindV3,PerformanceScope)
for _contract in _LOCAL_CONTRACTS:
    _prior=SerializableContract._serialization_registry.get(_contract.__name__)
    if _prior is not None and _prior is not _contract:_fail(f"V3 type-tag collision: {_contract.__name__}")
for _contract in _LOCAL_CONTRACTS:
    _contract.to_dict=SerializableContract.to_dict;_contract.to_json=SerializableContract.to_json
    _contract.from_dict=SerializableContract.__dict__["from_dict"];_contract.from_json=SerializableContract.__dict__["from_json"]
_register(*_LOCAL_CONTRACTS,enums=_LOCAL_ENUMS)


V3_TYPE_REGISTRY={item.__name__:item for item in _LOCAL_CONTRACTS}
if len(V3_TYPE_REGISTRY)!=len(_LOCAL_CONTRACTS):_fail("V3 type-tag collision")

_DELEGATED_LEGACY_TYPES=(ResearchCaptureOpportunity,ResearchEventEligibilityContext,PopulationEligibilityResult,
    MarketObservation,ProviderMarketSeries,MarketProbabilityDerivation,OutcomeObservation,OutcomeHistory,
    ProbabilitySourceReference,ResearchContractProvenance,MarketProbabilityBound,MarketProbabilityLevel)
V3_DELEGATED_REGISTRY={item.__name__:item for item in _DELEGATED_LEGACY_TYPES}
if set(V3_TYPE_REGISTRY)&set(V3_DELEGATED_REGISTRY):_fail("V3/legacy type-tag collision")
for _name,_contract in V3_DELEGATED_REGISTRY.items():
    if SerializableContract._serialization_registry.get(_name) is not _contract:_fail(f"legacy delegation collision: {_name}")


def deserialize_v3(payload:str)->Any:
    raw=json.loads(payload)
    if not isinstance(raw,dict) or "__type__" not in raw:_fail("V3 payload lacks declared type")
    type_name=raw["__type__"]
    contract=V3_TYPE_REGISTRY.get(type_name)
    local=contract is not None
    if contract is None:contract=V3_DELEGATED_REGISTRY.get(type_name)
    if contract is None:_fail("unknown successor type tag")
    value=contract.from_dict(raw)
    if local and getattr(value,"schema_version",SCHEMA_VERSION)!=SCHEMA_VERSION:_fail("unknown V3 schema version")
    return value
