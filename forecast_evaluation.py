"""PR9 forecast-quality eligibility and immutable derived evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from enum import Enum

from event_contracts import (
    ContractError,
    ReasonCode,
    ReconciliationOutcome,
    SerializableContract,
    ValidationStatus,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)
from forecast_contracts import ForecastObservation, ForecastValidationStatus
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


ELIGIBILITY_POLICY_ID = "mlb-winner-evaluation-eligibility"
ELIGIBILITY_POLICY_VERSION = "1"
EVALUATION_ALGORITHM_ID = "mlb-winner-forecast-quality"
EVALUATION_ALGORITHM_VERSION = "1"


class EligibilityDecisionValue(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    INDETERMINATE = "indeterminate"


class EligibilityReasonCode(str, Enum):
    FORECAST_AFTER_START = "forecast-after-start"
    FORECAST_AT_START = "forecast-at-start"
    FORECAST_INVALID = "forecast-invalid"
    FORECAST_DISTRIBUTION_INCOMPLETE = "forecast-distribution-incomplete"
    FORECAST_EVENT_AMBIGUOUS = "forecast-event-ambiguous"
    OUTCOME_NOT_FINAL = "outcome-not-final"
    OUTCOME_INVALID = "outcome-invalid"
    OUTCOME_EVENT_MISMATCH = "outcome-event-mismatch"
    OUTCOME_CANCELLED = "outcome-cancelled"
    OUTCOME_SUSPENDED = "outcome-suspended"
    OUTCOME_FORFEIT_POLICY_DEFERRED = "outcome-forfeit-policy-deferred"
    FORECAST_PREDATES_POSTPONEMENT = "forecast-predates-postponement"
    CHRONOLOGY_INCOMPLETE = "chronology-incomplete"


@dataclass(frozen=True, slots=True)
class EvaluationEligibilityPolicy:
    policy_id: str = ELIGIBILITY_POLICY_ID
    version: str = ELIGIBILITY_POLICY_VERSION
    competition: str = "MLB"
    proposition: str = "two-participant-winner"
    authoritative_provider_id: str = "mlb-stats-api"
    strictly_pregame: bool = True
    require_valid_complete_distribution: bool = True
    forfeits_eligible: bool = False

    def __post_init__(self) -> None:
        for value, label in ((self.policy_id, "policy_id"), (self.version, "policy version"), (self.competition, "competition"), (self.proposition, "proposition"), (self.authoritative_provider_id, "authoritative_provider_id")):
            _require_identifier(value, label)

    @property
    def identity(self) -> str:
        return f"{self.policy_id}-v{self.version}"


@dataclass(frozen=True, slots=True, order=True)
class EligibilityReason:
    code: EligibilityReasonCode
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "eligibility reason")


@dataclass(frozen=True, slots=True)
class EvaluationEligibilityDecision:
    decision_id: str
    policy_id: str
    policy_version: str
    forecast_observation_id: str
    outcome_observation_id: str
    canonical_event_id: str | None
    decision: EligibilityDecisionValue
    reasons: tuple[EligibilityReason, ...]
    forecast_collected_at: datetime
    scheduled_start: datetime | None
    outcome_status: OutcomeStatus
    derivation_id: str
    outcome_history_observation_ids: tuple[str, ...] = ()
    validation_issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.decision_id, "decision_id"), (self.policy_id, "policy_id"), (self.policy_version, "policy_version"), (self.forecast_observation_id, "forecast_observation_id"), (self.outcome_observation_id, "outcome_observation_id"), (self.derivation_id, "derivation_id")):
            _require_identifier(value, label)
        if self.canonical_event_id is not None:
            _require_identifier(self.canonical_event_id, "canonical_event_id")
        _require_aware(self.forecast_collected_at, "forecast_collected_at")
        if self.scheduled_start is not None:
            _require_aware(self.scheduled_start, "scheduled_start")
        if self.decision is EligibilityDecisionValue.ELIGIBLE and (self.reasons or self.validation_issues):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "eligible decision cannot carry reasons or issues")
        if self.decision is not EligibilityDecisionValue.ELIGIBLE and not self.reasons:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "non-eligible decision requires reasons")
        object.__setattr__(self, "reasons", tuple(sorted(set(self.reasons))))
        history_ids = tuple(self.outcome_history_observation_ids)
        for observation_id in history_ids:
            _require_identifier(observation_id, "outcome_history_observation_id")
        if len(history_ids) != len(set(history_ids)):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "eligibility history identities must be unique")
        object.__setattr__(self, "outcome_history_observation_ids", history_ids)
        object.__setattr__(self, "validation_issues", tuple(sorted(set(self.validation_issues))))


def decide_evaluation_eligibility(
    forecast: ForecastObservation,
    outcome: OutcomeObservation,
    *,
    policy: EvaluationEligibilityPolicy = EvaluationEligibilityPolicy(),
    scheduled_start: datetime | None = None,
    scheduled_start_known: bool = True,
    outcome_history: OutcomeHistory | None = None,
) -> EvaluationEligibilityDecision:
    start = (outcome.scheduled_start if scheduled_start is None else scheduled_start) if scheduled_start_known else None
    forecast_event_id = forecast.distribution.canonical_event_id
    pair_id = f"{forecast.observation_id}|{outcome.observation_id}"
    reasons: list[EligibilityReason] = []
    indeterminate = False
    if forecast.reconciliation.outcome is not ReconciliationOutcome.MATCHED or forecast_event_id is None:
        reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_EVENT_AMBIGUOUS, "forecast is not uniquely reconciled"))
    if forecast_event_id != outcome.canonical_event_id:
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_EVENT_MISMATCH, "forecast and outcome reference different Canonical Events"))
    if forecast.validation_status is not ForecastValidationStatus.VALID:
        reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_INVALID, "forecast validation did not pass"))
    participant_ids = {outcome.away_participant_id, outcome.home_participant_id}
    distribution_ids = {item.outcome.outcome_id for item in forecast.distribution.probabilities}
    if len(forecast.distribution.probabilities) != 2 or distribution_ids != participant_ids or forecast.distribution.validation_status is not ForecastValidationStatus.VALID:
        reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_DISTRIBUTION_INCOMPLETE, "complete oriented two-participant distribution is required"))
    if outcome.authoritative_provider_id != policy.authoritative_provider_id or outcome.validation_status is not ValidationStatus.VALID:
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_INVALID, "outcome is not valid authoritative MLB Evidence"))
    if outcome.provider_status in (OutcomeStatus.CANCELLED, OutcomeStatus.NO_CONTEST):
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_CANCELLED, "cancelled or no-contest outcome is ineligible"))
    elif outcome.provider_status is OutcomeStatus.SUSPENDED:
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_SUSPENDED, "unresolved suspended outcome is ineligible"))
    elif outcome.provider_status is OutcomeStatus.FORFEIT:
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_FORFEIT_POLICY_DEFERRED, "forfeit treatment is deferred"))
    elif not outcome.authoritative_final:
        reasons.append(EligibilityReason(EligibilityReasonCode.OUTCOME_NOT_FINAL, "official final with a determinable winner is required"))
    material_history: list[OutcomeObservation] = [outcome]
    if outcome_history is not None:
        supplied_ids = {item.observation_id for item in outcome_history.observations}
        if outcome.observation_id not in supplied_ids:
            reasons.append(EligibilityReason(EligibilityReasonCode.CHRONOLOGY_INCOMPLETE, "Outcome History does not contain the evaluated Outcome Observation"))
            indeterminate = True
        postponed = tuple(
            item
            for item in outcome_history.observations
            if item.provider_status is OutcomeStatus.POSTPONED
            and item.collected_at <= outcome.collected_at
        )
        if postponed:
            first_postponement = postponed[0]
            material_history.append(first_postponement)
            prior_schedules = tuple(
                item
                for item in outcome_history.observations
                if item.provider_status is OutcomeStatus.SCHEDULED
                and item.collected_at < first_postponement.collected_at
            )
            if not prior_schedules:
                reasons.append(EligibilityReason(EligibilityReasonCode.CHRONOLOGY_INCOMPLETE, "postponement history lacks an earlier authoritative schedule observation"))
                indeterminate = True
            else:
                material_history.append(prior_schedules[-1])
            if forecast.collected_at < first_postponement.collected_at:
                reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_PREDATES_POSTPONEMENT, "forecast predates authoritative postponement evidence"))
    history_ids = tuple(sorted({item.observation_id for item in material_history}))
    if start is None:
        reasons.append(EligibilityReason(EligibilityReasonCode.CHRONOLOGY_INCOMPLETE, "scheduled event start is unavailable"))
        indeterminate = True
    elif forecast.collected_at == start:
        reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_AT_START, "forecast collection exactly at start is not pregame"))
    elif forecast.collected_at > start:
        reasons.append(EligibilityReason(EligibilityReasonCode.FORECAST_AFTER_START, "forecast collection occurred after start"))
    decision = EligibilityDecisionValue.ELIGIBLE if not reasons else (EligibilityDecisionValue.INDETERMINATE if indeterminate and all(reason.code is EligibilityReasonCode.CHRONOLOGY_INCOMPLETE for reason in reasons) else EligibilityDecisionValue.INELIGIBLE)
    reason_codes = ",".join(sorted(reason.code.value for reason in reasons))
    material = f"{policy.identity}|{pair_id}|{decision.value}|{reason_codes}|{start.isoformat() if start else 'unknown'}|history={','.join(history_ids)}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return EvaluationEligibilityDecision(
        decision_id=f"eligibility:{digest}",
        policy_id=policy.policy_id,
        policy_version=policy.version,
        forecast_observation_id=forecast.observation_id,
        outcome_observation_id=outcome.observation_id,
        canonical_event_id=forecast_event_id if forecast_event_id == outcome.canonical_event_id else None,
        decision=decision,
        reasons=tuple(reasons),
        forecast_collected_at=forecast.collected_at,
        scheduled_start=start,
        outcome_status=outcome.provider_status,
        derivation_id=f"eligibility-derivation:{digest}",
        outcome_history_observation_ids=history_ids,
    )


@dataclass(frozen=True, slots=True, order=True)
class EvaluationArithmeticInput:
    participant_id: str
    probability: Decimal
    realized_value: int

    def __post_init__(self) -> None:
        _require_identifier(self.participant_id, "participant_id")
        if not isinstance(self.probability, Decimal) or not self.probability.is_finite() or self.probability < 0 or self.probability > 1:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "evaluation probability must be a finite Decimal in [0,1]")
        if self.realized_value not in (0, 1):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "realized_value must be binary")


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    evaluation_id: str
    algorithm_id: str
    algorithm_version: str
    eligibility_decision_id: str
    forecast_observation_id: str
    outcome_observation_id: str
    canonical_event_id: str
    provider_id: str
    model_id: str
    model_version_id: str
    forecast_collected_at: datetime
    probability_distribution: tuple[tuple[str, Decimal], ...]
    realized_winning_participant_id: str
    realized_outcome_vector: tuple[tuple[str, int], ...]
    brier_score: Decimal
    log_loss: Decimal
    directional_correct: bool | None
    predicted_favorite_id: str | None
    calibration_bucket: str
    arithmetic_inputs: tuple[EvaluationArithmeticInput, ...]
    derivation_id: str
    issues: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.evaluation_id, "evaluation_id"), (self.algorithm_id, "algorithm_id"), (self.algorithm_version, "algorithm_version"), (self.eligibility_decision_id, "eligibility_decision_id"), (self.forecast_observation_id, "forecast_observation_id"), (self.outcome_observation_id, "outcome_observation_id"), (self.canonical_event_id, "canonical_event_id"), (self.provider_id, "provider_id"), (self.model_id, "model_id"), (self.model_version_id, "model_version_id"), (self.realized_winning_participant_id, "realized_winning_participant_id"), (self.calibration_bucket, "calibration_bucket"), (self.derivation_id, "derivation_id")):
            _require_identifier(value, label)
        _require_aware(self.forecast_collected_at, "forecast_collected_at")
        if not self.brier_score.is_finite() or self.brier_score < 0 or self.brier_score > 1:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "binary Brier score must be finite in [0,1]")
        if not (self.log_loss.is_finite() or self.log_loss == Decimal("Infinity")):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "log loss must be finite or positive infinity")
        object.__setattr__(self, "probability_distribution", tuple(sorted(self.probability_distribution)))
        object.__setattr__(self, "realized_outcome_vector", tuple(sorted(self.realized_outcome_vector)))
        object.__setattr__(self, "arithmetic_inputs", tuple(sorted(self.arithmetic_inputs)))
        object.__setattr__(self, "issues", tuple(sorted(set(self.issues))))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))


def create_forecast_evaluation(
    forecast: ForecastObservation,
    outcome: OutcomeObservation,
    decision: EvaluationEligibilityDecision,
    *,
    provider_id: str,
    model_id: str,
    model_version_id: str,
) -> ForecastEvaluation:
    if decision.decision is not EligibilityDecisionValue.ELIGIBLE:
        raise ContractError(ReasonCode.VALIDATION_FAILURE, "ineligible decision cannot create Forecast Evaluation")
    if (decision.forecast_observation_id, decision.outcome_observation_id) != (forecast.observation_id, outcome.observation_id):
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "eligibility decision does not reference supplied Evidence")
    event_id = forecast.distribution.canonical_event_id
    if event_id is None or event_id != outcome.canonical_event_id or decision.canonical_event_id != event_id:
        raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "evaluation inputs reference incompatible events")
    if forecast.provenance.provider != provider_id or forecast.version_id != model_version_id:
        raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "forecast provider or version identity mismatch")
    probabilities = {item.outcome.outcome_id: item.probability for item in forecast.distribution.probabilities}
    winner = outcome.winning_participant_id
    if winner is None or winner not in probabilities:
        raise ContractError(ReasonCode.VALIDATION_FAILURE, "realized winner is absent from forecast distribution")
    inputs = tuple(EvaluationArithmeticInput(participant_id, probability, int(participant_id == winner)) for participant_id, probability in probabilities.items())
    realized_probability = probabilities[winner]
    brier = (realized_probability - Decimal(1)) ** 2
    limitations = []
    if realized_probability == 0:
        log_loss = Decimal("Infinity")
        limitations.append("zero probability assigned to realized winner; log loss is positive infinity")
    else:
        with localcontext() as context:
            context.prec = 50
            log_loss = -realized_probability.ln()
    maximum = max(probabilities.values())
    favorites = sorted(participant_id for participant_id, value in probabilities.items() if value == maximum)
    favorite = favorites[0] if len(favorites) == 1 else None
    directional = None if favorite is None else favorite == winner
    distribution_text = ",".join(f"{key}={probabilities[key]}" for key in sorted(probabilities))
    material = f"{EVALUATION_ALGORITHM_ID}-v{EVALUATION_ALGORITHM_VERSION}|{decision.decision_id}|{provider_id}|{model_id}|{model_version_id}|{distribution_text}|winner={winner}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return ForecastEvaluation(
        evaluation_id=f"forecast-evaluation:{digest}",
        algorithm_id=EVALUATION_ALGORITHM_ID,
        algorithm_version=EVALUATION_ALGORITHM_VERSION,
        eligibility_decision_id=decision.decision_id,
        forecast_observation_id=forecast.observation_id,
        outcome_observation_id=outcome.observation_id,
        canonical_event_id=event_id,
        provider_id=provider_id,
        model_id=model_id,
        model_version_id=model_version_id,
        forecast_collected_at=forecast.collected_at,
        probability_distribution=tuple(probabilities.items()),
        realized_winning_participant_id=winner,
        realized_outcome_vector=tuple((item.participant_id, item.realized_value) for item in inputs),
        brier_score=brier,
        log_loss=log_loss,
        directional_correct=directional,
        predicted_favorite_id=favorite,
        calibration_bucket=_calibration_bucket(realized_probability),
        arithmetic_inputs=inputs,
        derivation_id=f"forecast-evaluation-derivation:{digest}",
        limitations=tuple(limitations),
    )


def _calibration_bucket(probability: Decimal) -> str:
    if probability == 1:
        return "0.9-1.0"
    lower = int(probability * 10)
    return f"{Decimal(lower) / 10:.1f}-{Decimal(lower + 1) / 10:.1f}"


@dataclass(frozen=True, slots=True)
class ForecastEvaluationHistory:
    evaluations: tuple[ForecastEvaluation, ...]

    def __post_init__(self) -> None:
        ids = [item.evaluation_id for item in self.evaluations]
        if len(ids) != len(set(ids)):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate Forecast Evaluation identity")
        pairs = [(item.forecast_observation_id, item.outcome_observation_id) for item in self.evaluations]
        if len(pairs) != len(set(pairs)):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate forecast/outcome evaluation pair")
        object.__setattr__(self, "evaluations", tuple(sorted(self.evaluations, key=lambda item: (item.forecast_collected_at, item.evaluation_id))))

    def append(self, evaluation: ForecastEvaluation) -> "ForecastEvaluationHistory":
        return ForecastEvaluationHistory(self.evaluations + (evaluation,))

    def evaluation_by_id(self, evaluation_id: str) -> ForecastEvaluation:
        _require_identifier(evaluation_id, "evaluation_id")
        matches = tuple(item for item in self.evaluations if item.evaluation_id == evaluation_id)
        if not matches:
            raise ContractError(ReasonCode.NO_MATCHING_EVENT, "Forecast Evaluation identity is not present")
        return matches[0]

    def current_evaluations(self, outcome_histories: tuple[OutcomeHistory, ...]) -> tuple[ForecastEvaluation, ...]:
        selected_outcomes = _selected_final_outcomes(outcome_histories)
        event_ids = {item.canonical_event_id for item in self.evaluations}
        if event_ids != set(selected_outcomes):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "current evaluation view requires one Outcome History for every evaluated Canonical Event")
        return tuple(
            item
            for item in self.evaluations
            if item.outcome_observation_id == selected_outcomes[item.canonical_event_id].observation_id
        )

    def superseded_evaluations(self, outcome_histories: tuple[OutcomeHistory, ...]) -> tuple[ForecastEvaluation, ...]:
        current_ids = {item.evaluation_id for item in self.current_evaluations(outcome_histories)}
        return tuple(item for item in self.evaluations if item.evaluation_id not in current_ids)

    def current_summary(self, outcome_histories: tuple[OutcomeHistory, ...]) -> "ForecastEvaluationSummary":
        return ForecastEvaluationHistory(self.current_evaluations(outcome_histories)).summary

    @property
    def summary(self) -> "ForecastEvaluationSummary":
        count = len(self.evaluations)
        if not count:
            return ForecastEvaluationSummary(0, None, None, 0, 0, 0, 0)
        brier = sum((item.brier_score for item in self.evaluations), Decimal(0)) / count
        finite_logs = tuple(item.log_loss for item in self.evaluations if item.log_loss.is_finite())
        mean_log = sum(finite_logs, Decimal(0)) / len(finite_logs) if finite_logs else None
        directional = tuple(item.directional_correct for item in self.evaluations if item.directional_correct is not None)
        return ForecastEvaluationSummary(count, brier, mean_log, len(finite_logs), count - len(finite_logs), sum(item is True for item in directional), len(directional))


@dataclass(frozen=True, slots=True)
class ForecastEvaluationSummary:
    count: int
    mean_brier_score: Decimal | None
    mean_finite_log_loss: Decimal | None
    finite_log_loss_count: int
    infinite_log_loss_count: int
    directional_correct_count: int
    directional_decision_count: int


def _selected_final_outcomes(outcome_histories: tuple[OutcomeHistory, ...]) -> dict[str, OutcomeObservation]:
    selected: dict[str, OutcomeObservation] = {}
    for history in outcome_histories:
        if history.canonical_event_id in selected:
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate Outcome History for Canonical Event")
        final = history.latest_authoritative_final
        if final is None:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "current evaluation view requires an authoritative final")
        selected[history.canonical_event_id] = final
    return selected


_CONTRACTS = (EvaluationEligibilityPolicy, EligibilityReason, EvaluationEligibilityDecision, EvaluationArithmeticInput, ForecastEvaluation, ForecastEvaluationHistory, ForecastEvaluationSummary)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(EligibilityDecisionValue, EligibilityReasonCode))
