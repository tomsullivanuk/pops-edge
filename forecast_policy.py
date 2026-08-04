"""Provider-neutral immutable PR11 Forecast Policy execution contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from event_contracts import (
    ContractError,
    ReasonCode,
    ReconciliationOutcome,
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
)
from forecast_contracts import (
    ForecastObservation,
    ForecastValidationStatus,
    ProviderDisposition,
)


POLICY_CONTRACT_VERSION = "1"
EXECUTION_ALGORITHM_ID = "forecast-policy-batch-execution"
EXECUTION_ALGORITHM_VERSION = "1"
POLICY_FORECAST_ALGORITHM_ID = "policy-forecast-derivation"
POLICY_FORECAST_ALGORITHM_VERSION = "1"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class EligibilityOutcome(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    INDETERMINATE = "indeterminate"


class ExecutionReasonCode(str, Enum):
    ANALYSIS_AS_OF_EXCEEDED = "analysis-as-of-exceeded"
    AT_OR_AFTER_EVENT_START = "at-or-after-event-start"
    DISTRIBUTION_INCOMPLETE = "distribution-incomplete"
    DISTRIBUTION_INVALID = "distribution-invalid"
    DISTRIBUTION_TOTAL_INVALID = "distribution-total-invalid"
    EVENT_IDENTITY_MISMATCH = "event-identity-mismatch"
    EVENT_NOT_IN_SCOPE = "event-not-in-scope"
    EVENT_CONTEXT_CONFLICT = "event-context-conflict"
    FALLBACK_UNAVAILABLE = "fallback-unavailable"
    LATEST_OBSERVATION_AMBIGUOUS = "latest-observation-ambiguous"
    MISSING_CHRONOLOGY = "missing-chronology"
    MISSING_EVENT_CONTEXT = "missing-event-context"
    MISSING_REQUIRED_PROVIDER = "missing-required-provider"
    MODEL_MISMATCH = "model-mismatch"
    NOT_SELECTED_LATEST = "not-selected-latest"
    OBSERVATION_INVALID = "observation-invalid"
    OUTPUT_INVALID = "output-invalid"
    PROPOSITION_MISMATCH = "proposition-mismatch"
    PARTICIPANT_ORIENTATION_MISMATCH = "participant-orientation-mismatch"
    PROVIDER_DISPOSITION_UNSUPPORTED = "provider-disposition-unsupported"
    PROVIDER_MISMATCH = "provider-mismatch"
    RECONCILIATION_UNRESOLVED = "reconciliation-unresolved"
    UNSUPPORTED_COMPONENT = "unsupported-component"
    VERSION_MISMATCH = "version-mismatch"
    WEIGHT_INVALID = "weight-invalid"


class StageStatus(str, Enum):
    APPLIED = "applied"
    FAILED = "failed"
    NOT_INVOKED = "not-invoked"


class ConstraintMode(str, Enum):
    EXACT = "exact"
    ALLOWED_SET = "allowed-set"


@dataclass(frozen=True, slots=True, order=True)
class RuleComponentSpec:
    component_id: str
    version: str
    parameters: tuple[tuple[str, str], ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.component_id, "component_id")
        _require_identifier(self.version, "component version")
        keys = [key for key, _ in self.parameters]
        if len(keys) != len(set(keys)):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "component parameters must have unique keys")
        for key, value in self.parameters:
            _require_identifier(key, "component parameter key")
            if not isinstance(value, str) or not value:
                raise ContractError(ReasonCode.VALIDATION_FAILURE, "component parameter values must be non-empty text")
        object.__setattr__(self, "parameters", tuple(sorted(self.parameters)))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))


@dataclass(frozen=True, slots=True, order=True)
class ProviderModelConstraint:
    provider_id: str
    model_ids: tuple[str, ...]
    version_ids: tuple[str, ...]
    mode: ConstraintMode

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "constraint provider_id")
        if not self.model_ids or not self.version_ids:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "provider constraints require model and version identities")
        for value in self.model_ids + self.version_ids:
            _require_identifier(value, "constraint identity")
        if self.mode is ConstraintMode.EXACT and (len(set(self.model_ids)) != 1 or len(set(self.version_ids)) != 1):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "exact constraints require one model and one version")
        object.__setattr__(self, "model_ids", tuple(sorted(set(self.model_ids))))
        object.__setattr__(self, "version_ids", tuple(sorted(set(self.version_ids))))


@dataclass(frozen=True, slots=True, order=True)
class PolicyProviderWeight:
    provider_id: str
    weight: Decimal

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "weight provider_id")
        if not isinstance(self.weight, Decimal) or not self.weight.is_finite() or self.weight < 0:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "provider weight must be a finite nonnegative Decimal")


_SUPPORTED_COMPONENTS = {
    "mlb-winner-input-compatibility": "1",
    "validated-strictly-pregame-eligibility": "1",
    "unique-latest-before-as-of": "1",
    "required-provider-selection": "1",
    "identity-probability-transformation": "1",
    "fixed-provider-weighting": "1",
    "validate-complete-distribution": "1",
    "fail-closed-missing-provider": "1",
    "no-fallback": "1",
    "complete-two-outcome-validation": "1",
}


@dataclass(frozen=True, slots=True)
class ForecastPolicy:
    policy_id: str
    policy_version: str
    contract_version: str
    sport: str
    competition: str
    proposition_type: str
    provider_constraints: tuple[ProviderModelConstraint, ...]
    provider_weights: tuple[PolicyProviderWeight, ...]
    input_compatibility_rule: RuleComponentSpec
    observation_eligibility_rule: RuleComponentSpec
    observation_selection_rule: RuleComponentSpec
    provider_selection_rule: RuleComponentSpec
    transformation_rule: RuleComponentSpec
    weighting_rule: RuleComponentSpec
    normalization_rule: RuleComponentSpec
    missing_provider_rule: RuleComponentSpec
    fallback_rule: RuleComponentSpec
    output_validation_rule: RuleComponentSpec
    implementation_version: str
    limitations: tuple[str, ...]
    specification_digest: str

    @classmethod
    def create(
        cls,
        *,
        policy_version: str,
        sport: str,
        competition: str,
        proposition_type: str,
        provider_constraints: tuple[ProviderModelConstraint, ...],
        provider_weights: tuple[PolicyProviderWeight, ...],
        input_compatibility_rule: RuleComponentSpec,
        observation_eligibility_rule: RuleComponentSpec,
        observation_selection_rule: RuleComponentSpec,
        provider_selection_rule: RuleComponentSpec,
        transformation_rule: RuleComponentSpec,
        weighting_rule: RuleComponentSpec,
        normalization_rule: RuleComponentSpec,
        missing_provider_rule: RuleComponentSpec,
        fallback_rule: RuleComponentSpec,
        output_validation_rule: RuleComponentSpec,
        implementation_version: str,
        limitations: tuple[str, ...] = (),
    ) -> "ForecastPolicy":
        components = (
            input_compatibility_rule, observation_eligibility_rule,
            observation_selection_rule, provider_selection_rule,
            transformation_rule, weighting_rule, normalization_rule,
            missing_provider_rule, fallback_rule, output_validation_rule,
        )
        _validate_components(components)
        constraints = tuple(sorted(provider_constraints))
        weights = tuple(sorted(provider_weights))
        material = _policy_material(
            policy_version, sport, competition, proposition_type, constraints,
            weights, components, implementation_version, tuple(sorted(set(limitations))),
        )
        digest = _digest(material)
        return cls(
            f"forecast-policy:{digest}", policy_version, POLICY_CONTRACT_VERSION,
            sport, competition, proposition_type, constraints, weights,
            *components, implementation_version, tuple(sorted(set(limitations))), digest,
        )

    def __post_init__(self) -> None:
        for value, label in (
            (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
            (self.contract_version, "contract_version"), (self.sport, "sport"),
            (self.competition, "competition"), (self.proposition_type, "proposition_type"),
            (self.implementation_version, "implementation_version"),
            (self.specification_digest, "specification_digest"),
        ):
            _require_identifier(value, label)
        if self.contract_version != POLICY_CONTRACT_VERSION:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "unsupported Forecast Policy contract version")
        if not self.provider_constraints or not self.provider_weights:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Forecast Policy requires provider constraints and weights")
        constrained = {item.provider_id for item in self.provider_constraints}
        weighted = {item.provider_id for item in self.provider_weights}
        if constrained != weighted:
            raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "weights must exactly cover constrained providers")
        if sum((item.weight for item in self.provider_weights), Decimal(0)) != Decimal(1):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "initial policy provider weights must sum exactly to one")
        _validate_components(self.components)
        expected_digest = _digest(_policy_material(
            self.policy_version, self.sport, self.competition, self.proposition_type,
            tuple(sorted(self.provider_constraints)), tuple(sorted(self.provider_weights)),
            self.components, self.implementation_version,
            tuple(sorted(set(self.limitations))),
        ))
        if self.specification_digest != expected_digest or self.policy_id != f"forecast-policy:{expected_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "policy identity conflicts with specification digest")

    @property
    def components(self) -> tuple[RuleComponentSpec, ...]:
        return (
            self.input_compatibility_rule, self.observation_eligibility_rule,
            self.observation_selection_rule, self.provider_selection_rule,
            self.transformation_rule, self.weighting_rule, self.normalization_rule,
            self.missing_provider_rule, self.fallback_rule, self.output_validation_rule,
        )


def _validate_components(components: tuple[RuleComponentSpec, ...]) -> None:
    for component in components:
        if _SUPPORTED_COMPONENTS.get(component.component_id) != component.version:
            raise ContractError(ReasonCode.UNSUPPORTED_STATUS, f"unsupported component {component.component_id}:{component.version}")


def _policy_material(
    policy_version: str,
    sport: str,
    competition: str,
    proposition_type: str,
    constraints: tuple[ProviderModelConstraint, ...],
    weights: tuple[PolicyProviderWeight, ...],
    components: tuple[RuleComponentSpec, ...],
    implementation_version: str,
    limitations: tuple[str, ...],
) -> dict[str, object]:
    return {
        "contract_version": POLICY_CONTRACT_VERSION,
        "policy_version": policy_version,
        "domain": [sport, competition, proposition_type],
        "constraints": [
            [item.provider_id, item.mode.value, list(item.model_ids), list(item.version_ids)]
            for item in constraints
        ],
        "weights": [[item.provider_id, str(item.weight)] for item in weights],
        "components": [
            [item.component_id, item.version, list(item.parameters), list(item.limitations)]
            for item in components
        ],
        "implementation_version": implementation_version,
        "limitations": list(limitations),
    }


def create_dratings_mlb_winner_policy() -> ForecastPolicy:
    """Create the bounded supplied PR11 demonstration policy."""
    component = lambda name: RuleComponentSpec(name, "1")
    return ForecastPolicy.create(
        policy_version="1", sport="baseball", competition="MLB",
        proposition_type="winner",
        provider_constraints=(ProviderModelConstraint(
            "dratings", ("dratings-mlb",), ("dratings-mlb-undisclosed",), ConstraintMode.EXACT,
        ),),
        provider_weights=(PolicyProviderWeight("dratings", Decimal("1.0")),),
        input_compatibility_rule=component("mlb-winner-input-compatibility"),
        observation_eligibility_rule=component("validated-strictly-pregame-eligibility"),
        observation_selection_rule=component("unique-latest-before-as-of"),
        provider_selection_rule=component("required-provider-selection"),
        transformation_rule=component("identity-probability-transformation"),
        weighting_rule=component("fixed-provider-weighting"),
        normalization_rule=component("validate-complete-distribution"),
        missing_provider_rule=component("fail-closed-missing-provider"),
        fallback_rule=component("no-fallback"),
        output_validation_rule=component("complete-two-outcome-validation"),
        implementation_version="forecast-policy-engine:1",
        limitations=("single-provider deterministic contract demonstration; no governance authority",),
    )


@dataclass(frozen=True, slots=True)
class ExecutionScope:
    scope_id: str
    sport: str
    competition: str
    proposition_type: str
    event_ids: tuple[str, ...]
    analysis_as_of: datetime
    slate_label: str | None = None

    def __post_init__(self) -> None:
        for value, label in ((self.scope_id, "scope_id"), (self.sport, "scope sport"), (self.competition, "scope competition"), (self.proposition_type, "scope proposition_type")):
            _require_identifier(value, label)
        _require_aware(self.analysis_as_of, "analysis_as_of")
        if not self.event_ids:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "execution scope requires explicit event IDs")
        for value in self.event_ids:
            _require_identifier(value, "scope event_id")
        object.__setattr__(self, "event_ids", tuple(sorted(set(self.event_ids))))


@dataclass(frozen=True, slots=True)
class ForecastPolicyEventContext:
    context_id: str
    context_version: str
    canonical_event_id: str
    sport: str
    competition: str
    proposition_type: str
    model_id: str
    scheduled_start: datetime | None
    away_participant_id: str
    home_participant_id: str
    away_outcome_id: str
    home_outcome_id: str
    source_object_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    context_digest: str = ""

    @classmethod
    def create(
        cls,
        *,
        context_version: str,
        canonical_event_id: str,
        sport: str,
        competition: str,
        proposition_type: str,
        model_id: str,
        scheduled_start: datetime | None,
        away_participant_id: str,
        home_participant_id: str,
        away_outcome_id: str,
        home_outcome_id: str,
        source_object_ids: tuple[str, ...],
        limitations: tuple[str, ...] = (),
    ) -> "ForecastPolicyEventContext":
        material = _event_context_material(
            context_version, canonical_event_id, sport, competition,
            proposition_type, model_id, scheduled_start, away_participant_id,
            home_participant_id, away_outcome_id, home_outcome_id,
            tuple(sorted(set(source_object_ids))), tuple(sorted(set(limitations))),
        )
        digest = _digest(material)
        return cls(
            f"forecast-policy-event-context:{digest}", context_version,
            canonical_event_id, sport, competition, proposition_type, model_id,
            scheduled_start, away_participant_id, home_participant_id,
            away_outcome_id, home_outcome_id, tuple(sorted(set(source_object_ids))),
            tuple(sorted(set(limitations))), digest,
        )

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "context_id"),
            (self.context_version, "context_version"),
            (self.canonical_event_id, "context canonical_event_id"),
            (self.sport, "context sport"), (self.competition, "context competition"),
            (self.proposition_type, "context proposition_type"), (self.model_id, "context model_id"),
            (self.away_participant_id, "away_participant_id"),
            (self.home_participant_id, "home_participant_id"),
            (self.away_outcome_id, "away_outcome_id"), (self.home_outcome_id, "home_outcome_id"),
            (self.context_digest, "context_digest"),
        ):
            _require_identifier(value, label)
        if self.away_participant_id == self.home_participant_id:
            raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS, "away and home participants must differ")
        if self.away_outcome_id == self.home_outcome_id:
            raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS, "away and home outcomes must differ")
        if self.scheduled_start is not None:
            _require_aware(self.scheduled_start, "scheduled_start")
        for value in self.source_object_ids:
            _require_identifier(value, "context source object identity")
        object.__setattr__(self, "source_object_ids", tuple(sorted(set(self.source_object_ids))))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))
        expected = _digest(_event_context_material(
            self.context_version, self.canonical_event_id, self.sport,
            self.competition, self.proposition_type, self.model_id,
            self.scheduled_start, self.away_participant_id,
            self.home_participant_id, self.away_outcome_id,
            self.home_outcome_id, self.source_object_ids, self.limitations,
        ))
        if self.context_digest != expected or self.context_id != f"forecast-policy-event-context:{expected}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "event-context identity conflicts with digest")


def _event_context_material(
    context_version: str,
    canonical_event_id: str,
    sport: str,
    competition: str,
    proposition_type: str,
    model_id: str,
    scheduled_start: datetime | None,
    away_participant_id: str,
    home_participant_id: str,
    away_outcome_id: str,
    home_outcome_id: str,
    source_object_ids: tuple[str, ...],
    limitations: tuple[str, ...],
) -> dict[str, object]:
    return {
        "context_version": context_version,
        "event": canonical_event_id,
        "domain": [sport, competition, proposition_type],
        "model": model_id,
        "scheduled_start": scheduled_start.isoformat() if scheduled_start else None,
        "participants": [away_participant_id, home_participant_id],
        "outcomes": [[away_outcome_id, "away-win"], [home_outcome_id, "home-win"]],
        "source_object_ids": list(source_object_ids),
        "limitations": list(limitations),
    }


@dataclass(frozen=True, slots=True, order=True)
class ProductionEligibilityDecision:
    decision_id: str
    observation_id: str
    canonical_event_id: str
    outcome: EligibilityOutcome
    rule_id: str
    rule_version: str
    reason_codes: tuple[ExecutionReasonCode, ...]
    observation_collected_at: datetime
    scheduled_start: datetime | None
    analysis_as_of: datetime
    limitations: tuple[str, ...]
    input_digest: str

    def __post_init__(self) -> None:
        for value, label in ((self.decision_id, "decision_id"), (self.observation_id, "decision observation_id"), (self.canonical_event_id, "decision event_id"), (self.rule_id, "eligibility rule_id"), (self.rule_version, "eligibility rule version"), (self.input_digest, "eligibility input_digest")):
            _require_identifier(value, label)
        _require_aware(self.observation_collected_at, "decision observation_collected_at")
        _require_aware(self.analysis_as_of, "decision analysis_as_of")
        if self.scheduled_start is not None:
            _require_aware(self.scheduled_start, "decision scheduled_start")
        if self.outcome is EligibilityOutcome.ELIGIBLE and self.reason_codes:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "eligible observation cannot carry rejection reasons")
        if self.outcome is not EligibilityOutcome.ELIGIBLE and not self.reason_codes:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "non-eligible observation requires structured reasons")
        material = _eligibility_material(
            self.observation_id, self.canonical_event_id, self.outcome,
            self.rule_id, self.rule_version, self.reason_codes,
            self.observation_collected_at, self.scheduled_start, self.analysis_as_of,
        )
        expected_digest = _digest(material)
        if self.input_digest != expected_digest or self.decision_id != f"production-eligibility:{expected_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "eligibility decision identity conflicts with digest")


@dataclass(frozen=True, slots=True, order=True)
class ExcludedObservation:
    observation_id: str
    canonical_event_id: str
    reason_codes: tuple[ExecutionReasonCode, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.observation_id, "excluded observation_id")
        _require_identifier(self.canonical_event_id, "excluded event_id")
        if not self.reason_codes:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "excluded observation requires structured reasons")


@dataclass(frozen=True, slots=True)
class StageDecision:
    stage_id: str
    component_id: str
    component_version: str
    status: StageStatus
    observation_ids: tuple[str, ...]
    input_probabilities: tuple[tuple[str, Decimal], ...] = ()
    output_probabilities: tuple[tuple[str, Decimal], ...] = ()
    applied_weights: tuple[tuple[str, Decimal], ...] = ()
    reason_codes: tuple[ExecutionReasonCode, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.stage_id, "stage_id"), (self.component_id, "stage component_id"), (self.component_version, "stage component version")):
            _require_identifier(value, label)
        if self.status is StageStatus.FAILED and not self.reason_codes:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "failed stage requires structured reasons")
        object.__setattr__(self, "observation_ids", tuple(sorted(set(self.observation_ids))))


@dataclass(frozen=True, slots=True)
class PolicyForecast:
    policy_forecast_id: str
    algorithm_id: str
    algorithm_version: str
    execution_id: str
    policy_id: str
    policy_version: str
    canonical_event_id: str
    sport: str
    competition: str
    proposition_type: str
    event_context_id: str
    candidate_observation_ids: tuple[str, ...]
    eligible_observation_ids: tuple[str, ...]
    included_observation_ids: tuple[str, ...]
    excluded_observations: tuple[ExcludedObservation, ...]
    provider_model_versions: tuple[tuple[str, str, str], ...]
    source_distributions: tuple[tuple[str, tuple[tuple[str, Decimal], ...]], ...]
    stage_decisions: tuple[StageDecision, ...]
    output_distribution: tuple[tuple[str, str, Decimal], ...]
    arithmetic_precision: str
    total_probability: Decimal
    validation_status: ForecastValidationStatus
    issues: tuple[ExecutionReasonCode, ...]
    limitations: tuple[str, ...]
    analysis_as_of: datetime
    derivation_digest: str

    def __post_init__(self) -> None:
        expected_digest = _digest(_policy_forecast_material(
            self.algorithm_id, self.algorithm_version, self.execution_id,
            self.policy_id, self.policy_version, self.canonical_event_id,
            self.sport, self.competition, self.proposition_type,
            self.event_context_id, self.candidate_observation_ids,
            self.eligible_observation_ids, self.included_observation_ids,
            self.excluded_observations, self.source_distributions,
            self.stage_decisions, self.output_distribution, self.analysis_as_of,
            self.issues, self.limitations,
        ))
        if self.derivation_digest != expected_digest or self.policy_forecast_id != f"policy-forecast:{expected_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "Policy Forecast identity conflicts with derivation digest")
        _require_aware(self.analysis_as_of, "Policy Forecast analysis_as_of")
        _require_identifier(self.event_context_id, "Policy Forecast event_context_id")
        if self.validation_status is not ForecastValidationStatus.VALID or self.issues:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Forecast output must be valid")
        if len(self.output_distribution) != 2 or self.total_probability != Decimal(1):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Forecast requires a complete exact two-outcome distribution")
        if {semantic for _, semantic, _ in self.output_distribution} != {"away-win", "home-win"}:
            raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "Policy Forecast output semantics must be away-win and home-win")
        if sum((value for _, _, value in self.output_distribution), Decimal(0)) != self.total_probability:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Forecast output total conflicts with probabilities")
        if any(value < 0 or value > 1 for _, _, value in self.output_distribution):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Forecast probabilities must be between zero and one")
        if not set(self.included_observation_ids) <= set(self.eligible_observation_ids) <= set(self.candidate_observation_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "Policy Forecast observation provenance does not reconcile")
        _validate_components(tuple(RuleComponentSpec(item.component_id, item.component_version) for item in self.stage_decisions))


@dataclass(frozen=True, slots=True)
class ExecutionStatistics:
    candidate_observation_count: int
    eligible_observation_count: int
    ineligible_observation_count: int
    indeterminate_observation_count: int
    included_observation_count: int
    excluded_observation_count: int
    event_count: int
    policy_forecast_count: int
    unresolved_event_count: int
    fallback_invocation_count: int

    def __post_init__(self) -> None:
        if any(value < 0 for value in (
            self.candidate_observation_count, self.eligible_observation_count,
            self.ineligible_observation_count, self.indeterminate_observation_count,
            self.included_observation_count, self.excluded_observation_count,
            self.event_count, self.policy_forecast_count,
            self.unresolved_event_count, self.fallback_invocation_count,
        )):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "execution statistics cannot be negative")


@dataclass(frozen=True, slots=True)
class ForecastPolicyExecution:
    execution_id: str
    algorithm_id: str
    algorithm_version: str
    policy_id: str
    policy_version: str
    scope: ExecutionScope
    candidate_observation_ids: tuple[str, ...]
    eligible_observation_ids: tuple[str, ...]
    ineligible_observation_ids: tuple[str, ...]
    indeterminate_observation_ids: tuple[str, ...]
    included_observation_ids: tuple[str, ...]
    excluded_observations: tuple[ExcludedObservation, ...]
    event_ids: tuple[str, ...]
    candidate_event_context_ids: tuple[str, ...]
    used_event_context_ids: tuple[str, ...]
    unresolved_event_context_ids: tuple[str, ...]
    event_context_conflicts: tuple[tuple[str, tuple[str, ...]], ...]
    policy_forecast_ids: tuple[str, ...]
    unresolved_event_ids: tuple[str, ...]
    unresolved_event_reasons: tuple[tuple[str, tuple[ExecutionReasonCode, ...]], ...]
    eligibility_decisions: tuple[ProductionEligibilityDecision, ...]
    component_versions: tuple[tuple[str, str], ...]
    exclusion_reason_counts: tuple[tuple[ExecutionReasonCode, int], ...]
    input_digest: str
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    statistics: ExecutionStatistics

    def __post_init__(self) -> None:
        if self.execution_id != f"forecast-policy-execution:{self.input_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "execution identity conflicts with input digest")
        if len(self.policy_forecast_ids) != len(set(self.policy_forecast_ids)):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "completed execution contains duplicate Policy Forecast IDs")
        if not set(self.used_event_context_ids) <= set(self.candidate_event_context_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "used event contexts must be supplied execution inputs")
        if not set(self.unresolved_event_context_ids) <= set(self.candidate_event_context_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "unresolved event contexts must be supplied execution inputs")
        if set(self.included_observation_ids) & {item.observation_id for item in self.excluded_observations}:
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "included and excluded observations overlap")
        if set(self.eligible_observation_ids) | set(self.ineligible_observation_ids) | set(self.indeterminate_observation_ids) != set(self.candidate_observation_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "eligibility classifications must account for every candidate observation")
        if set(self.eligible_observation_ids) & set(self.ineligible_observation_ids) or set(self.eligible_observation_ids) & set(self.indeterminate_observation_ids) or set(self.ineligible_observation_ids) & set(self.indeterminate_observation_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "eligibility classifications overlap")
        expected = (
            len(self.candidate_observation_ids), len(self.eligible_observation_ids),
            len(self.ineligible_observation_ids), len(self.indeterminate_observation_ids),
            len(self.included_observation_ids), len(self.excluded_observations),
            len(self.event_ids), len(self.policy_forecast_ids), len(self.unresolved_event_ids),
        )
        actual = (
            self.statistics.candidate_observation_count, self.statistics.eligible_observation_count,
            self.statistics.ineligible_observation_count, self.statistics.indeterminate_observation_count,
            self.statistics.included_observation_count, self.statistics.excluded_observation_count,
            self.statistics.event_count, self.statistics.policy_forecast_count,
            self.statistics.unresolved_event_count,
        )
        if expected != actual:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "execution statistics conflict with preserved identities")


@dataclass(frozen=True, slots=True)
class ForecastPolicyBatchResult:
    execution: ForecastPolicyExecution
    policy_forecasts: tuple[PolicyForecast, ...]

    def __post_init__(self) -> None:
        produced_ids = tuple(item.policy_forecast_id for item in self.policy_forecasts)
        if len(produced_ids) != len(set(produced_ids)) or set(produced_ids) != set(self.execution.policy_forecast_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "execution and Policy Forecast IDs do not reconcile")
        if any(item.execution_id != self.execution.execution_id for item in self.policy_forecasts):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "Policy Forecast references a foreign execution")
        if any(item.policy_id != self.execution.policy_id for item in self.policy_forecasts):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "Policy Forecast references a foreign policy")


def execute_forecast_policy(
    policy: ForecastPolicy,
    scope: ExecutionScope,
    observations: tuple[ForecastObservation, ...],
    contexts: tuple[ForecastPolicyEventContext, ...],
) -> ForecastPolicyBatchResult:
    """Execute a supplied policy against a supplied immutable batch only."""
    if (scope.sport, scope.competition, scope.proposition_type) != (policy.sport, policy.competition, policy.proposition_type):
        raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "execution scope conflicts with policy domain")
    unique_contexts = tuple(sorted(set(contexts), key=lambda item: item.context_id))
    contexts_by_event: dict[str, tuple[ForecastPolicyEventContext, ...]] = {}
    for event_id in scope.event_ids:
        contexts_by_event[event_id] = tuple(item for item in unique_contexts if item.canonical_event_id == event_id)
    resolved_context = {
        event_id: items[0] for event_id, items in contexts_by_event.items() if len(items) == 1
    }
    observation_ids = [item.observation_id for item in observations]
    if len(observation_ids) != len(set(observation_ids)):
        raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate Forecast Observation identity")
    ordered = tuple(sorted(observations, key=lambda item: item.observation_id))
    decisions = tuple(
        _decide_eligibility(
            policy, scope, item,
            resolved_context.get(_observation_event_id(item)),
            contexts_by_event.get(_observation_event_id(item), ()),
        )
        for item in ordered
    )
    decision_by_id = {item.observation_id: item for item in decisions}
    observations_by_event: dict[str, list[ForecastObservation]] = {event_id: [] for event_id in scope.event_ids}
    for observation in ordered:
        event_id = _observation_event_id(observation)
        if event_id in observations_by_event:
            observations_by_event[event_id].append(observation)

    execution_id, execution_digest = derive_forecast_policy_execution_identity(
        policy, scope, ordered, unique_contexts,
    )
    forecasts: list[PolicyForecast] = []
    excluded: list[ExcludedObservation] = []
    unresolved: list[str] = []
    unresolved_reason_items: list[tuple[str, tuple[ExecutionReasonCode, ...]]] = []
    included_ids: set[str] = set()
    used_context_ids: set[str] = set()

    for event_id in scope.event_ids:
        event_observations = tuple(observations_by_event[event_id])
        eligible = tuple(item for item in event_observations if decision_by_id[item.observation_id].outcome is EligibilityOutcome.ELIGIBLE)
        eligibility_exclusions = tuple(
            ExcludedObservation(item.observation_id, event_id, decision_by_id[item.observation_id].reason_codes)
            for item in event_observations
            if decision_by_id[item.observation_id].outcome is not EligibilityOutcome.ELIGIBLE
        )
        event_contexts = contexts_by_event[event_id]
        if len(event_contexts) != 1:
            selected = None
            selection_exclusions = ()
            unresolved_reasons = (
                ExecutionReasonCode.MISSING_EVENT_CONTEXT if not event_contexts
                else ExecutionReasonCode.EVENT_CONTEXT_CONFLICT,
            )
        else:
            selected, selection_exclusions, unresolved_reasons = _select_event(policy, event_id, event_observations, eligible)
        event_exclusions = eligibility_exclusions + selection_exclusions
        excluded.extend(event_exclusions)
        if selected is None:
            unresolved.append(event_id)
            unresolved_reason_items.append((event_id, unresolved_reasons))
            continue
        context = event_contexts[0]
        forecast = _create_policy_forecast(
            policy, scope, execution_id, event_id, event_observations, eligible,
            selected, context, tuple(event_exclusions),
        )
        forecasts.append(forecast)
        included_ids.add(selected.observation_id)
        used_context_ids.add(context.context_id)

    for observation in ordered:
        decision = decision_by_id[observation.observation_id]
        if observation.observation_id in included_ids or any(item.observation_id == observation.observation_id for item in excluded):
            continue
        reasons = decision.reason_codes or (ExecutionReasonCode.EVENT_NOT_IN_SCOPE,)
        excluded.append(ExcludedObservation(observation.observation_id, decision.canonical_event_id, reasons))
    excluded_tuple = tuple(sorted(set(excluded)))
    forecasts_tuple = tuple(sorted(forecasts, key=lambda item: item.canonical_event_id))
    eligible_ids = tuple(sorted(item.observation_id for item in decisions if item.outcome is EligibilityOutcome.ELIGIBLE))
    ineligible_ids = tuple(sorted(item.observation_id for item in decisions if item.outcome is EligibilityOutcome.INELIGIBLE))
    indeterminate_ids = tuple(sorted(item.observation_id for item in decisions if item.outcome is EligibilityOutcome.INDETERMINATE))
    all_reasons = (
        {reason for item in excluded_tuple for reason in item.reason_codes}
        | {reason for _, reasons in unresolved_reason_items for reason in reasons}
    )
    reason_counts = tuple(sorted(
        (
            (
                reason,
                sum(reason in item.reason_codes for item in excluded_tuple)
                + sum(reason in reasons for _, reasons in unresolved_reason_items),
            )
            for reason in all_reasons
        ),
        key=lambda item: item[0].value,
    ))
    warnings = tuple(f"unresolved event {event_id}" for event_id in sorted(unresolved))
    stats = ExecutionStatistics(
        len(ordered), len(eligible_ids), len(ineligible_ids), len(indeterminate_ids),
        len(included_ids), len(excluded_tuple), len(scope.event_ids), len(forecasts_tuple),
        len(unresolved), 0,
    )
    execution = ForecastPolicyExecution(
        execution_id, EXECUTION_ALGORITHM_ID, EXECUTION_ALGORITHM_VERSION,
        policy.policy_id, policy.policy_version, scope,
        tuple(item.observation_id for item in ordered), eligible_ids, ineligible_ids,
        indeterminate_ids, tuple(sorted(included_ids)), excluded_tuple,
        scope.event_ids, tuple(item.context_id for item in unique_contexts),
        tuple(sorted(used_context_ids)),
        tuple(sorted(item.context_id for event_id in unresolved for item in contexts_by_event[event_id])),
        tuple(sorted(
            (event_id, tuple(item.context_id for item in items))
            for event_id, items in contexts_by_event.items() if len(items) > 1
        )),
        tuple(item.policy_forecast_id for item in forecasts_tuple),
        tuple(sorted(unresolved)), tuple(sorted(unresolved_reason_items)), tuple(sorted(decisions)),
        tuple((item.component_id, item.version) for item in policy.components),
        reason_counts, execution_digest, warnings,
        tuple(sorted(set(policy.limitations + (("one or more events unresolved",) if unresolved else ())))),
        stats,
    )
    return ForecastPolicyBatchResult(execution, forecasts_tuple)


def derive_forecast_policy_execution_identity(
    policy: ForecastPolicy,
    scope: ExecutionScope,
    observations: tuple[ForecastObservation, ...],
    contexts: tuple[ForecastPolicyEventContext, ...],
) -> tuple[str, str]:
    """Derive execution identity solely from immutable material inputs."""
    ordered = tuple(sorted(observations, key=lambda item: item.observation_id))
    unique_contexts = tuple(sorted(set(contexts), key=lambda item: item.context_id))
    material = {
        "algorithm": [EXECUTION_ALGORITHM_ID, EXECUTION_ALGORITHM_VERSION],
        "policy": policy.policy_id,
        "scope": scope.to_dict(),
        "candidate_observations": [item.to_dict() for item in ordered],
        "event_contexts": [item.to_dict() for item in unique_contexts],
        "components": [item.to_dict() for item in policy.components],
    }
    digest = _digest(material)
    return f"forecast-policy-execution:{digest}", digest


def _observation_event_id(observation: ForecastObservation) -> str:
    return observation.distribution.canonical_event_id or (
        observation.reconciliation.matched_event.canonical_event_id
        if observation.reconciliation.outcome is ReconciliationOutcome.MATCHED
        else "event:unresolved"
    )


def _decide_eligibility(
    policy: ForecastPolicy,
    scope: ExecutionScope,
    observation: ForecastObservation,
    context: ForecastPolicyEventContext | None,
    supplied_contexts: tuple[ForecastPolicyEventContext, ...],
) -> ProductionEligibilityDecision:
    reasons: list[ExecutionReasonCode] = []
    indeterminate = False
    event_id = _observation_event_id(observation)
    if not supplied_contexts:
        reasons.append(ExecutionReasonCode.MISSING_EVENT_CONTEXT)
        indeterminate = True
    elif len(supplied_contexts) > 1:
        reasons.append(ExecutionReasonCode.EVENT_CONTEXT_CONFLICT)
        indeterminate = True
    if context is None or context.scheduled_start is None:
        reasons.append(ExecutionReasonCode.MISSING_CHRONOLOGY)
        indeterminate = True
    else:
        if context.canonical_event_id not in scope.event_ids:
            reasons.append(ExecutionReasonCode.EVENT_NOT_IN_SCOPE)
        if (context.sport, context.competition) != (policy.sport, policy.competition):
            reasons.append(ExecutionReasonCode.EVENT_IDENTITY_MISMATCH)
        if context.proposition_type != policy.proposition_type:
            reasons.append(ExecutionReasonCode.PROPOSITION_MISMATCH)
        if observation.collected_at >= context.scheduled_start:
            reasons.append(ExecutionReasonCode.AT_OR_AFTER_EVENT_START)
    if observation.collected_at > scope.analysis_as_of:
        reasons.append(ExecutionReasonCode.ANALYSIS_AS_OF_EXCEEDED)
    if observation.reconciliation.outcome is not ReconciliationOutcome.MATCHED:
        reasons.append(ExecutionReasonCode.RECONCILIATION_UNRESOLVED)
    elif context and observation.reconciliation.matched_event.canonical_event_id != context.canonical_event_id:
        reasons.append(ExecutionReasonCode.EVENT_IDENTITY_MISMATCH)
    elif context:
        participant_ids = tuple(item.canonical_id for item in observation.reconciliation.matched_event.participants)
        if participant_ids != (context.away_participant_id, context.home_participant_id):
            reasons.append(ExecutionReasonCode.PARTICIPANT_ORIENTATION_MISMATCH)
    provider = observation.provenance.provider
    constraint = next((item for item in policy.provider_constraints if item.provider_id == provider), None)
    if constraint is None:
        reasons.append(ExecutionReasonCode.PROVIDER_MISMATCH)
    elif context:
        if context.model_id not in constraint.model_ids:
            reasons.append(ExecutionReasonCode.MODEL_MISMATCH)
        if observation.version_id not in constraint.version_ids:
            reasons.append(ExecutionReasonCode.VERSION_MISMATCH)
    if observation.validation_status is not ForecastValidationStatus.VALID:
        reasons.append(ExecutionReasonCode.OBSERVATION_INVALID)
    if observation.provider_disposition is not ProviderDisposition.ACTIVE:
        reasons.append(ExecutionReasonCode.PROVIDER_DISPOSITION_UNSUPPORTED)
    if context:
        outcomes = {item.outcome.outcome_id for item in observation.distribution.probabilities}
        if outcomes != {context.away_outcome_id, context.home_outcome_id}:
            reasons.append(ExecutionReasonCode.DISTRIBUTION_INCOMPLETE)
    if observation.distribution.validation_status is not ForecastValidationStatus.VALID or observation.distribution.observed_total != Decimal(1):
        reasons.append(ExecutionReasonCode.DISTRIBUTION_TOTAL_INVALID)
    outcome = EligibilityOutcome.INDETERMINATE if indeterminate else (EligibilityOutcome.INELIGIBLE if reasons else EligibilityOutcome.ELIGIBLE)
    material = _eligibility_material(
        observation.observation_id, event_id, outcome,
        policy.observation_eligibility_rule.component_id,
        policy.observation_eligibility_rule.version,
        tuple(sorted(set(reasons), key=lambda item: item.value)), observation.collected_at,
        context.scheduled_start if context else None, scope.analysis_as_of,
    )
    digest = _digest(material)
    return ProductionEligibilityDecision(
        f"production-eligibility:{digest}", observation.observation_id, event_id,
        outcome, policy.observation_eligibility_rule.component_id,
        policy.observation_eligibility_rule.version,
        tuple(sorted(set(reasons), key=lambda item: item.value)), observation.collected_at,
        context.scheduled_start if context else None, scope.analysis_as_of,
        context.limitations if context else ("observation execution context missing",), digest,
    )


def _eligibility_material(
    observation_id: str,
    event_id: str,
    outcome: EligibilityOutcome,
    rule_id: str,
    rule_version: str,
    reasons: tuple[ExecutionReasonCode, ...],
    collected_at: datetime,
    scheduled_start: datetime | None,
    analysis_as_of: datetime,
) -> list[object]:
    return [
        observation_id, event_id, outcome.value, rule_id, rule_version,
        sorted(item.value for item in reasons), collected_at.isoformat(),
        scheduled_start.isoformat() if scheduled_start else None,
        analysis_as_of.isoformat(),
    ]


def _select_event(
    policy: ForecastPolicy,
    event_id: str,
    candidates: tuple[ForecastObservation, ...],
    eligible: tuple[ForecastObservation, ...],
) -> tuple[ForecastObservation | None, tuple[ExcludedObservation, ...], tuple[ExecutionReasonCode, ...]]:
    exclusions: list[ExcludedObservation] = []
    required_provider = policy.provider_constraints[0].provider_id
    provider_eligible = tuple(item for item in eligible if item.provenance.provider == required_provider)
    if not provider_eligible:
        has_required_candidate = any(item.provenance.provider == required_provider for item in candidates)
        reasons = (ExecutionReasonCode.FALLBACK_UNAVAILABLE,)
        if not has_required_candidate:
            reasons = (ExecutionReasonCode.MISSING_REQUIRED_PROVIDER,) + reasons
        return None, tuple(exclusions), reasons
    latest_at = max(item.collected_at for item in provider_eligible)
    latest = tuple(item for item in provider_eligible if item.collected_at == latest_at)
    if len(latest) != 1:
        for item in eligible:
            reason = ExecutionReasonCode.LATEST_OBSERVATION_AMBIGUOUS if item in latest else ExecutionReasonCode.NOT_SELECTED_LATEST
            exclusions.append(ExcludedObservation(item.observation_id, event_id, (reason,)))
        return None, tuple(exclusions), (ExecutionReasonCode.LATEST_OBSERVATION_AMBIGUOUS,)
    selected = latest[0]
    for item in eligible:
        if item.observation_id != selected.observation_id:
            exclusions.append(ExcludedObservation(item.observation_id, event_id, (ExecutionReasonCode.NOT_SELECTED_LATEST,)))
    return selected, tuple(exclusions), ()


def _create_policy_forecast(
    policy: ForecastPolicy,
    scope: ExecutionScope,
    execution_id: str,
    event_id: str,
    candidates: tuple[ForecastObservation, ...],
    eligible: tuple[ForecastObservation, ...],
    selected: ForecastObservation,
    context: ForecastPolicyEventContext,
    exclusions: tuple[ExcludedObservation, ...],
) -> PolicyForecast:
    source = tuple((item.outcome.outcome_id, item.probability) for item in selected.distribution.probabilities)
    transformed = source
    weight = next(item.weight for item in policy.provider_weights if item.provider_id == selected.provenance.provider)
    weighted = tuple((outcome, probability * weight) for outcome, probability in transformed)
    total = sum((probability for _, probability in weighted), Decimal(0))
    if total != Decimal(1) or len(weighted) != 2 or any(value < 0 or value > 1 for _, value in weighted):
        raise ContractError(ReasonCode.VALIDATION_FAILURE, "selected observation failed complete-distribution output validation")
    stages = (
        StageDecision("input-compatibility", policy.input_compatibility_rule.component_id, policy.input_compatibility_rule.version, StageStatus.APPLIED, (selected.observation_id,), source, source),
        StageDecision("observation-eligibility", policy.observation_eligibility_rule.component_id, policy.observation_eligibility_rule.version, StageStatus.APPLIED, (selected.observation_id,)),
        StageDecision("observation-selection", policy.observation_selection_rule.component_id, policy.observation_selection_rule.version, StageStatus.APPLIED, (selected.observation_id,)),
        StageDecision("provider-selection", policy.provider_selection_rule.component_id, policy.provider_selection_rule.version, StageStatus.APPLIED, (selected.observation_id,)),
        StageDecision("transformation", policy.transformation_rule.component_id, policy.transformation_rule.version, StageStatus.APPLIED, (selected.observation_id,), source, transformed),
        StageDecision("weighting", policy.weighting_rule.component_id, policy.weighting_rule.version, StageStatus.APPLIED, (selected.observation_id,), transformed, weighted, ((selected.provenance.provider, weight),)),
        StageDecision("normalization", policy.normalization_rule.component_id, policy.normalization_rule.version, StageStatus.APPLIED, (selected.observation_id,), weighted, weighted),
        StageDecision("fallback", policy.fallback_rule.component_id, policy.fallback_rule.version, StageStatus.NOT_INVOKED, (selected.observation_id,)),
        StageDecision("output-validation", policy.output_validation_rule.component_id, policy.output_validation_rule.version, StageStatus.APPLIED, (selected.observation_id,), weighted, weighted),
    )
    output = (
        (context.away_outcome_id, "away-win", dict(weighted)[context.away_outcome_id]),
        (context.home_outcome_id, "home-win", dict(weighted)[context.home_outcome_id]),
    )
    limitations = tuple(sorted(set(
        policy.limitations + context.limitations
        + ("no production authority before PR12 governance",)
    )))
    material = _policy_forecast_material(
        POLICY_FORECAST_ALGORITHM_ID, POLICY_FORECAST_ALGORITHM_VERSION,
        execution_id, policy.policy_id, policy.policy_version, event_id,
        scope.sport, scope.competition, scope.proposition_type,
        context.context_id, tuple(sorted(item.observation_id for item in candidates)),
        tuple(sorted(item.observation_id for item in eligible)),
        (selected.observation_id,), tuple(sorted(exclusions)),
        ((selected.observation_id, source),), stages, output,
        scope.analysis_as_of, (), limitations,
    )
    digest = _digest(material)
    return PolicyForecast(
        f"policy-forecast:{digest}", POLICY_FORECAST_ALGORITHM_ID,
        POLICY_FORECAST_ALGORITHM_VERSION, execution_id, policy.policy_id,
        policy.policy_version, event_id, scope.sport, scope.competition,
        scope.proposition_type, context.context_id,
        tuple(sorted(item.observation_id for item in candidates)),
        tuple(sorted(item.observation_id for item in eligible)), (selected.observation_id,),
        tuple(sorted(exclusions)), ((selected.provenance.provider, context.model_id, selected.version_id),),
        ((selected.observation_id, source),), stages, output, "exact-decimal",
        total, ForecastValidationStatus.VALID, (),
        limitations,
        scope.analysis_as_of, digest,
    )


def _policy_forecast_material(
    algorithm_id: str,
    algorithm_version: str,
    execution_id: str,
    policy_id: str,
    policy_version: str,
    event_id: str,
    sport: str,
    competition: str,
    proposition_type: str,
    event_context_id: str,
    candidate_observation_ids: tuple[str, ...],
    eligible_observation_ids: tuple[str, ...],
    included_observation_ids: tuple[str, ...],
    excluded_observations: tuple[ExcludedObservation, ...],
    source_distributions: tuple[tuple[str, tuple[tuple[str, Decimal], ...]], ...],
    stage_decisions: tuple[StageDecision, ...],
    output_distribution: tuple[tuple[str, str, Decimal], ...],
    analysis_as_of: datetime,
    issues: tuple[ExecutionReasonCode, ...],
    limitations: tuple[str, ...],
) -> dict[str, object]:
    return {
        "algorithm": [algorithm_id, algorithm_version],
        "execution": execution_id,
        "policy": [policy_id, policy_version],
        "event": event_id,
        "domain": [sport, competition, proposition_type],
        "event_context": event_context_id,
        "candidates": sorted(candidate_observation_ids),
        "eligible": sorted(eligible_observation_ids),
        "included": sorted(included_observation_ids),
        "excluded": [item.to_dict() for item in sorted(excluded_observations)],
        "source_distributions": [
            [observation_id, [[outcome, str(value)] for outcome, value in distribution]]
            for observation_id, distribution in source_distributions
        ],
        "stages": [item.to_dict() for item in stage_decisions],
        "output": [[outcome, semantic, str(value)] for outcome, semantic, value in output_distribution],
        "analysis_as_of": analysis_as_of.isoformat(),
        "issues": sorted(item.value for item in issues),
        "limitations": sorted(limitations),
    }


_CONTRACTS = (
    RuleComponentSpec, ProviderModelConstraint, PolicyProviderWeight, ForecastPolicy,
    ExecutionScope, ForecastPolicyEventContext, ProductionEligibilityDecision,
    ExcludedObservation, StageDecision, PolicyForecast, ExecutionStatistics,
    ForecastPolicyExecution, ForecastPolicyBatchResult,
)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(EligibilityOutcome, ExecutionReasonCode, StageStatus, ConstraintMode))
