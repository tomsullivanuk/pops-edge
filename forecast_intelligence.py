"""Provider-neutral immutable PR10 Forecast Intelligence Analysis."""

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
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)
from forecast_evaluation import ForecastEvaluation, ForecastEvaluationHistory
from outcome_contracts import OutcomeHistory


INTELLIGENCE_ALGORITHM_ID = "forecast-quality-intelligence"
INTELLIGENCE_ALGORITHM_VERSION = "1"
SEGMENTATION_VERSION = "mlb-home-win-segments-v2"
CALIBRATION_VERSION = "mlb-home-win-decile-calibration-v2"
PROPOSAL_ALGORITHM_ID = "forecast-policy-proposal"
PROPOSAL_ALGORITHM_VERSION = "2"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _mean(values: tuple[Decimal, ...]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


@dataclass(frozen=True, slots=True)
class EvaluationWindow:
    window_id: str
    version: str
    start_at: datetime
    end_at: datetime
    analysis_as_of: datetime | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.window_id, "window_id")
        _require_identifier(self.version, "window version")
        _require_aware(self.start_at, "window start_at")
        _require_aware(self.end_at, "window end_at")
        if self.start_at >= self.end_at:
            raise ContractError(ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY, "evaluation window must be non-empty")
        if self.analysis_as_of is not None:
            _require_aware(self.analysis_as_of, "analysis_as_of")

    def includes(self, value: datetime) -> bool:
        return self.start_at <= value < self.end_at and (self.analysis_as_of is None or value <= self.analysis_as_of)

    @property
    def identity_material(self) -> tuple[str, ...]:
        return (
            self.window_id,
            self.version,
            self.start_at.isoformat(),
            self.end_at.isoformat(),
            self.analysis_as_of.isoformat() if self.analysis_as_of else "none",
        )


@dataclass(frozen=True, slots=True)
class EvaluationParticipantContext:
    evaluation_id: str
    away_participant_id: str
    home_participant_id: str

    def __post_init__(self) -> None:
        for value, label in ((self.evaluation_id, "evaluation_id"), (self.away_participant_id, "away_participant_id"), (self.home_participant_id, "home_participant_id")):
            _require_identifier(value, label)
        if self.away_participant_id == self.home_participant_id:
            raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS, "evaluation roles must differ")


@dataclass(frozen=True, slots=True)
class CurrentEvaluationSelection:
    selection_id: str
    candidate_evaluation_ids: tuple[str, ...]
    current_evaluations: tuple[ForecastEvaluation, ...]
    superseded_evaluation_ids: tuple[str, ...]
    selected_outcome_observation_ids: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, candidate_evaluation_ids: tuple[str, ...], current_evaluations: tuple[ForecastEvaluation, ...], superseded_evaluation_ids: tuple[str, ...], selected_outcome_observation_ids: tuple[str, ...]) -> "CurrentEvaluationSelection":
        material = {
            "candidate_ids": sorted(candidate_evaluation_ids),
            "current_ids": sorted(item.evaluation_id for item in current_evaluations),
            "superseded_ids": sorted(superseded_evaluation_ids),
            "outcome_ids": sorted(selected_outcome_observation_ids),
        }
        digest = _digest(material)
        return cls(f"current-evaluation-selection:{digest}", tuple(material["candidate_ids"]), current_evaluations, tuple(material["superseded_ids"]), tuple(material["outcome_ids"]), digest)

    def __post_init__(self) -> None:
        _require_identifier(self.selection_id, "selection_id")
        _require_identifier(self.input_digest, "input_digest")
        for collection, label in ((self.candidate_evaluation_ids, "candidate"), (self.superseded_evaluation_ids, "superseded"), (self.selected_outcome_observation_ids, "outcome")):
            for value in collection:
                _require_identifier(value, f"{label} identity")
            if len(collection) != len(set(collection)):
                raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, f"duplicate {label} identity")
        current_ids = {item.evaluation_id for item in self.current_evaluations}
        if current_ids & set(self.superseded_evaluation_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "current and superseded evaluations overlap")
        if current_ids | set(self.superseded_evaluation_ids) != set(self.candidate_evaluation_ids):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "selection must account for every candidate evaluation")
        expected_material = {
            "candidate_ids": sorted(self.candidate_evaluation_ids),
            "current_ids": sorted(current_ids),
            "superseded_ids": sorted(self.superseded_evaluation_ids),
            "outcome_ids": sorted(self.selected_outcome_observation_ids),
        }
        expected_digest = _digest(expected_material)
        if self.input_digest != expected_digest or self.selection_id != f"current-evaluation-selection:{expected_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "current selection identity does not match material inputs")
        object.__setattr__(self, "candidate_evaluation_ids", tuple(sorted(self.candidate_evaluation_ids)))
        object.__setattr__(self, "current_evaluations", tuple(sorted(self.current_evaluations, key=lambda item: item.evaluation_id)))
        object.__setattr__(self, "superseded_evaluation_ids", tuple(sorted(self.superseded_evaluation_ids)))
        object.__setattr__(self, "selected_outcome_observation_ids", tuple(sorted(self.selected_outcome_observation_ids)))


def select_current_evaluations(history: ForecastEvaluationHistory, outcome_histories: tuple[OutcomeHistory, ...]) -> CurrentEvaluationSelection:
    current = history.current_evaluations(outcome_histories)
    superseded = history.superseded_evaluations(outcome_histories)
    outcomes = tuple(history_item.latest_authoritative_final for history_item in outcome_histories)
    if any(item is None for item in outcomes):
        raise ContractError(ReasonCode.VALIDATION_FAILURE, "current selection requires authoritative finals")
    return CurrentEvaluationSelection.create(
        candidate_evaluation_ids=tuple(item.evaluation_id for item in history.evaluations),
        current_evaluations=current,
        superseded_evaluation_ids=tuple(item.evaluation_id for item in superseded),
        selected_outcome_observation_ids=tuple(item.observation_id for item in outcomes if item is not None),
    )


@dataclass(frozen=True, slots=True, order=True)
class ExcludedEvaluation:
    evaluation_id: str
    reason: str

    def __post_init__(self) -> None:
        _require_identifier(self.evaluation_id, "excluded evaluation_id")
        _require_identifier(self.reason, "exclusion reason")


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    candidate_evaluation_ids: tuple[str, ...]
    current_evaluation_ids: tuple[str, ...]
    superseded_evaluation_ids: tuple[str, ...]
    included_evaluation_ids: tuple[str, ...]
    excluded_evaluation_ids: tuple[str, ...]
    candidate_count: int
    current_count: int
    superseded_count: int
    included_count: int
    excluded_count: int
    exclusion_reason_counts: tuple[tuple[str, int], ...]
    first_evaluation_at: datetime | None
    last_evaluation_at: datetime | None
    provider_continuity: tuple[str, ...]
    missing_coverage: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ForecastQualitySummary:
    included_evaluation_ids: tuple[str, ...]
    finite_log_loss_evaluation_ids: tuple[str, ...]
    infinite_log_loss_evaluation_ids: tuple[str, ...]
    unique_favorite_evaluation_ids: tuple[str, ...]
    no_unique_favorite_evaluation_ids: tuple[str, ...]
    sample_size: int
    mean_brier_score: Decimal | None
    mean_finite_log_loss: Decimal | None
    finite_log_loss_count: int
    infinite_log_loss_count: int
    unique_favorite_count: int
    directional_correct_count: int
    directional_incorrect_count: int
    no_unique_favorite_count: int
    directional_accuracy_denominator: int
    directional_accuracy: Decimal | None
    probability_distribution: tuple[tuple[Decimal, int], ...]


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    bucket_id: str
    version: str
    target: str
    observation_unit: str
    lower_bound: Decimal
    upper_bound: Decimal
    inclusion_rule: str
    upper_inclusive: bool
    included_evaluation_ids: tuple[str, ...]
    forecast_count: int
    sample_size: int
    sum_predicted_probability: Decimal
    mean_predicted_probability: Decimal | None
    home_win_count: int
    observed_win_frequency: Decimal | None
    calibration_difference: Decimal | None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SegmentSummary:
    segment_id: str
    version: str
    dimension: str
    value: str
    observation_unit: str
    grouping_rule: str
    numerator_name: str
    numerator_value: Decimal
    denominator_name: str
    denominator_value: int
    included_evaluation_ids: tuple[str, ...]
    sample_size: int
    mean_predicted_probability: Decimal | None
    observed_win_frequency: Decimal | None
    mean_squared_error: Decimal | None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AdequacyRule:
    rule_id: str
    version: str
    minimum_report_sample: int
    minimum_segment_sample: int

    def __post_init__(self) -> None:
        _require_identifier(self.rule_id, "adequacy rule_id")
        _require_identifier(self.version, "adequacy version")
        if self.minimum_report_sample < 1 or self.minimum_segment_sample < 1:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "adequacy thresholds must be explicit positive integers")


@dataclass(frozen=True, slots=True)
class SampleAdequacy:
    rule_id: str
    rule_version: str
    label: str
    report_sample_size: int
    included_evaluation_ids: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ForecastIntelligenceReport:
    report_id: str
    algorithm_id: str
    algorithm_version: str
    provider_id: str
    model_ids: tuple[str, ...]
    model_version_ids: tuple[str, ...]
    sport: str
    competition: str
    proposition_type: str
    evaluation_window: EvaluationWindow
    eligibility_policy_id: str
    eligibility_policy_version: str
    forecast_evaluation_algorithm_versions: tuple[str, ...]
    segmentation_version: str
    calibration_version: str
    adequacy_rule_id: str
    adequacy_rule_version: str
    selection_id: str
    included_evaluation_ids: tuple[str, ...]
    excluded_evaluations: tuple[ExcludedEvaluation, ...]
    superseded_evaluation_ids: tuple[str, ...]
    selected_outcome_observation_ids: tuple[str, ...]
    generated_at: datetime
    input_digest: str
    coverage: CoverageSummary
    forecast_quality: ForecastQualitySummary
    calibration: tuple[CalibrationBucket, ...]
    segments: tuple[SegmentSummary, ...]
    historical_trend: tuple[tuple[str, str, Decimal | None, int], ...]
    sample_adequacy: SampleAdequacy
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.report_id, "report_id"), (self.algorithm_id, "algorithm_id"), (self.algorithm_version, "algorithm_version"), (self.provider_id, "provider_id"), (self.sport, "sport"), (self.competition, "competition"), (self.proposition_type, "proposition_type"), (self.eligibility_policy_id, "eligibility_policy_id"), (self.eligibility_policy_version, "eligibility_policy_version"), (self.selection_id, "selection_id"), (self.input_digest, "input_digest")):
            _require_identifier(value, label)
        _require_aware(self.generated_at, "generated_at")
        if self.report_id != f"forecast-intelligence-report:{self.input_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "report identity does not match deterministic input digest")
        included = set(self.included_evaluation_ids)
        excluded = {item.evaluation_id for item in self.excluded_evaluations}
        superseded = set(self.superseded_evaluation_ids)
        if included & excluded or included & superseded or excluded & superseded:
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "report evaluation classifications overlap")
        if (self.coverage.included_count, self.coverage.excluded_count, self.coverage.superseded_count) != (len(included), len(excluded), len(superseded)):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "report coverage counts conflict with evaluation identities")
        object.__setattr__(self, "model_ids", tuple(sorted(set(self.model_ids))))
        object.__setattr__(self, "model_version_ids", tuple(sorted(set(self.model_version_ids))))
        object.__setattr__(self, "included_evaluation_ids", tuple(sorted(self.included_evaluation_ids)))
        object.__setattr__(self, "excluded_evaluations", tuple(sorted(self.excluded_evaluations)))
        object.__setattr__(self, "superseded_evaluation_ids", tuple(sorted(self.superseded_evaluation_ids)))
        object.__setattr__(self, "selected_outcome_observation_ids", tuple(sorted(self.selected_outcome_observation_ids)))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))


def create_forecast_intelligence_report(
    selection: CurrentEvaluationSelection,
    contexts: tuple[EvaluationParticipantContext, ...],
    *,
    provider_id: str,
    model_ids: tuple[str, ...],
    model_version_ids: tuple[str, ...],
    sport: str,
    competition: str,
    proposition_type: str,
    eligibility_policy_id: str,
    eligibility_policy_version: str,
    evaluation_window: EvaluationWindow,
    adequacy_rule: AdequacyRule,
    generated_at: datetime,
    algorithm_id: str = INTELLIGENCE_ALGORITHM_ID,
    algorithm_version: str = INTELLIGENCE_ALGORITHM_VERSION,
) -> ForecastIntelligenceReport:
    _require_aware(generated_at, "generated_at")
    for value in model_ids:
        _require_identifier(value, "report model_id")
    for value in model_version_ids:
        _require_identifier(value, "report model_version_id")
    if not model_ids or not model_version_ids:
        raise ContractError(ReasonCode.VALIDATION_FAILURE, "report requires explicit non-empty model and version scope")
    model_scope = set(model_ids)
    version_scope = set(model_version_ids)
    context_by_id = {item.evaluation_id: item for item in contexts}
    if len(context_by_id) != len(contexts):
        raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate evaluation participant context")
    included: list[ForecastEvaluation] = []
    excluded: list[ExcludedEvaluation] = []
    for item in selection.current_evaluations:
        reason = None
        if item.provider_id != provider_id:
            reason = "provider-scope-mismatch"
        elif item.model_id not in model_scope or item.model_version_id not in version_scope:
            reason = "model-scope-mismatch"
        elif not evaluation_window.includes(item.forecast_collected_at):
            reason = "outside-evaluation-window"
        elif item.evaluation_id not in context_by_id:
            reason = "participant-context-missing"
        if reason:
            excluded.append(ExcludedEvaluation(item.evaluation_id, reason))
        else:
            context = context_by_id[item.evaluation_id]
            if {context.away_participant_id, context.home_participant_id} != {key for key, _ in item.probability_distribution}:
                excluded.append(ExcludedEvaluation(item.evaluation_id, "participant-context-mismatch"))
            else:
                included.append(item)
    included_tuple = tuple(sorted(included, key=lambda item: item.evaluation_id))
    excluded_tuple = tuple(sorted(excluded))
    quality = _quality(included_tuple)
    calibration = _calibration(included_tuple, context_by_id, adequacy_rule)
    segments = _segments(included_tuple, context_by_id, adequacy_rule)
    times = tuple(sorted(item.forecast_collected_at for item in included_tuple))
    reason_counts = tuple(sorted((reason, sum(item.reason == reason for item in excluded_tuple)) for reason in {item.reason for item in excluded_tuple}))
    continuity = tuple(sorted({f"{item.model_id}:{item.model_version_id}" for item in included_tuple}))
    missing = ("evaluation window contains excluded or missing coverage",) if excluded_tuple else ()
    coverage_limitations = (("no evaluations included",) if not included_tuple else ()) + missing
    coverage = CoverageSummary(
        selection.candidate_evaluation_ids,
        tuple(item.evaluation_id for item in selection.current_evaluations),
        selection.superseded_evaluation_ids,
        tuple(item.evaluation_id for item in included_tuple),
        tuple(item.evaluation_id for item in excluded_tuple),
        len(selection.candidate_evaluation_ids),
        len(selection.current_evaluations),
        len(selection.superseded_evaluation_ids),
        len(included_tuple),
        len(excluded_tuple),
        reason_counts,
        times[0] if times else None,
        times[-1] if times else None,
        continuity,
        missing,
        coverage_limitations,
    )
    adequacy_limitations = []
    if len(included_tuple) < adequacy_rule.minimum_report_sample:
        adequacy_limitations.append(f"report sample {len(included_tuple)} is below configured consideration threshold {adequacy_rule.minimum_report_sample}")
    limited_segments = sum(item.sample_size < adequacy_rule.minimum_segment_sample for item in segments)
    if limited_segments:
        adequacy_limitations.append(f"{limited_segments} segments are below configured segment threshold {adequacy_rule.minimum_segment_sample}")
    adequacy = SampleAdequacy(
        adequacy_rule.rule_id, adequacy_rule.version,
        "descriptive-only" if adequacy_limitations else "policy-consideration-supported",
        len(included_tuple), tuple(item.evaluation_id for item in included_tuple),
        tuple(adequacy_limitations),
    )
    trend = tuple((item.evaluation_id, item.forecast_collected_at.date().isoformat(), item.brier_score, 1) for item in sorted(included_tuple, key=lambda value: (value.forecast_collected_at, value.evaluation_id)))
    material = {
        "algorithm": [algorithm_id, algorithm_version],
        "provider": provider_id,
        "models": sorted(model_scope),
        "versions": sorted(version_scope),
        "domain": [sport, competition, proposition_type],
        "window": evaluation_window.identity_material,
        "eligibility_policy": [eligibility_policy_id, eligibility_policy_version],
        "evaluation_algorithms": sorted({f"{item.algorithm_id}:{item.algorithm_version}" for item in included_tuple}),
        "included": [item.evaluation_id for item in included_tuple],
        "excluded": [(item.evaluation_id, item.reason) for item in excluded_tuple],
        "superseded": list(selection.superseded_evaluation_ids),
        "selection": selection.selection_id,
        "participant_contexts": [
            (item.evaluation_id, item.away_participant_id, item.home_participant_id)
            for item in sorted((context_by_id[evaluation.evaluation_id] for evaluation in included_tuple), key=lambda value: value.evaluation_id)
        ],
        "segmentation": SEGMENTATION_VERSION,
        "calibration": CALIBRATION_VERSION,
        "adequacy": [adequacy_rule.rule_id, adequacy_rule.version, adequacy_rule.minimum_report_sample, adequacy_rule.minimum_segment_sample],
    }
    digest = _digest(material)
    limitations = tuple(sorted(set(coverage.limitations + adequacy.limitations + tuple(value for item in included_tuple for value in item.limitations))))
    return ForecastIntelligenceReport(
        f"forecast-intelligence-report:{digest}", algorithm_id, algorithm_version, provider_id,
        tuple(sorted(model_scope)), tuple(sorted(version_scope)),
        sport, competition, proposition_type, evaluation_window,
        eligibility_policy_id, eligibility_policy_version,
        tuple(sorted({f"{item.algorithm_id}:{item.algorithm_version}" for item in included_tuple})),
        SEGMENTATION_VERSION, CALIBRATION_VERSION, adequacy_rule.rule_id, adequacy_rule.version,
        selection.selection_id, tuple(item.evaluation_id for item in included_tuple), excluded_tuple,
        selection.superseded_evaluation_ids, selection.selected_outcome_observation_ids, generated_at, digest,
        coverage, quality, calibration, segments, trend, adequacy, limitations,
    )


def _quality(evaluations: tuple[ForecastEvaluation, ...]) -> ForecastQualitySummary:
    finite_evaluations = tuple(item for item in evaluations if item.log_loss.is_finite())
    infinite_evaluations = tuple(item for item in evaluations if not item.log_loss.is_finite())
    directional_evaluations = tuple(item for item in evaluations if item.directional_correct is not None)
    tied_evaluations = tuple(item for item in evaluations if item.directional_correct is None)
    finite = tuple(item.log_loss for item in finite_evaluations)
    directional = tuple(item.directional_correct for item in directional_evaluations)
    probability_counts: dict[Decimal, int] = {}
    for item in evaluations:
        for _, probability in item.probability_distribution:
            probability_counts[probability] = probability_counts.get(probability, 0) + 1
    return ForecastQualitySummary(
        tuple(item.evaluation_id for item in evaluations),
        tuple(item.evaluation_id for item in finite_evaluations),
        tuple(item.evaluation_id for item in infinite_evaluations),
        tuple(item.evaluation_id for item in directional_evaluations),
        tuple(item.evaluation_id for item in tied_evaluations), len(evaluations),
        _mean(tuple(item.brier_score for item in evaluations)), _mean(finite), len(finite),
        len(evaluations) - len(finite), len(directional), sum(value is True for value in directional),
        sum(value is False for value in directional), len(evaluations) - len(directional), len(directional),
        Decimal(sum(value is True for value in directional)) / len(directional) if directional else None,
        tuple(sorted(probability_counts.items())),
    )


def _home_win_points(
    evaluations: tuple[ForecastEvaluation, ...],
    contexts: dict[str, EvaluationParticipantContext],
) -> tuple[tuple[str, Decimal, int], ...]:
    points = []
    for evaluation in evaluations:
        context = contexts[evaluation.evaluation_id]
        probabilities = dict(evaluation.probability_distribution)
        realized = dict(evaluation.realized_outcome_vector)
        points.append((evaluation.evaluation_id, probabilities[context.home_participant_id], realized[context.home_participant_id]))
    return tuple(points)


def _calibration(
    evaluations: tuple[ForecastEvaluation, ...],
    contexts: dict[str, EvaluationParticipantContext],
    rule: AdequacyRule,
) -> tuple[CalibrationBucket, ...]:
    points = _home_win_points(evaluations, contexts)
    buckets = []
    for index in range(10):
        lower, upper = Decimal(index) / 10, Decimal(index + 1) / 10
        values = tuple(point for point in points if lower <= point[1] and (point[1] <= upper if index == 9 else point[1] < upper))
        predicted_sum = sum((value[1] for value in values), Decimal(0))
        predicted = predicted_sum / len(values) if values else None
        home_wins = sum(value[2] for value in values)
        observed = Decimal(home_wins) / len(values) if values else None
        limitations = (f"bucket sample {len(values)} is below configured segment threshold {rule.minimum_segment_sample}",) if len(values) < rule.minimum_segment_sample else ()
        inclusion = "lower-inclusive-upper-inclusive" if index == 9 else "lower-inclusive-upper-exclusive"
        buckets.append(CalibrationBucket(
            f"home-win:{lower:.1f}-{upper:.1f}", CALIBRATION_VERSION,
            "home-participant-wins", "one-current-included-forecast-evaluation",
            lower, upper, inclusion, index == 9, tuple(value[0] for value in values),
            len(values), len(values), predicted_sum, predicted, home_wins, observed,
            observed - predicted if observed is not None and predicted is not None else None,
            limitations,
        ))
    return tuple(buckets)


def _segments(evaluations: tuple[ForecastEvaluation, ...], contexts: dict[str, EvaluationParticipantContext], rule: AdequacyRule) -> tuple[SegmentSummary, ...]:
    values: dict[tuple[str, str], list[tuple[str, Decimal | None, int | None, Decimal]]] = {}
    for evaluation in evaluations:
        context = contexts[evaluation.evaluation_id]
        probabilities = dict(evaluation.probability_distribution)
        realized = dict(evaluation.realized_outcome_vector)
        home_probability = probabilities[context.home_participant_id]
        home_won = realized[context.home_participant_id]
        actual_value = "actual-home-win" if home_won else "actual-away-win"
        values.setdefault(("actual-result", actual_value), []).append((evaluation.evaluation_id, home_probability, home_won, evaluation.brier_score))
        maximum = max(probabilities.values())
        favorites = tuple(participant for participant, probability in probabilities.items() if probability == maximum)
        if len(favorites) != 1:
            favorite_value, favorite_probability, favorite_won = "no-unique-favorite", None, None
        else:
            favorite = favorites[0]
            favorite_won = realized[favorite]
            favorite_value = "favorite-win" if favorite_won else "favorite-loss"
            favorite_probability = probabilities[favorite]
        values.setdefault(("favorite-result", favorite_value), []).append((evaluation.evaluation_id, favorite_probability, favorite_won, evaluation.brier_score))
    for bucket in _calibration(evaluations, contexts, rule):
        points = []
        for evaluation_id in bucket.included_evaluation_ids:
            evaluation = next(item for item in evaluations if item.evaluation_id == evaluation_id)
            context = contexts[evaluation_id]
            probabilities = dict(evaluation.probability_distribution)
            realized = dict(evaluation.realized_outcome_vector)
            points.append((evaluation_id, probabilities[context.home_participant_id], realized[context.home_participant_id], evaluation.brier_score))
        values[("home-win-probability-bucket", bucket.bucket_id)] = points
    required = (
        [("actual-result", value) for value in ("actual-home-win", "actual-away-win")]
        + [("favorite-result", value) for value in ("favorite-win", "favorite-loss", "no-unique-favorite")]
    )
    for key in required:
        values.setdefault(key, [])
    summaries = []
    for (dimension, value), points in sorted(values.items()):
        predicted_values = tuple(item[1] for item in points if item[1] is not None)
        observed_values = tuple(item[2] for item in points if item[2] is not None)
        predicted = _mean(predicted_values)
        observed = Decimal(sum(observed_values)) / len(observed_values) if observed_values else None
        score_sum = sum((item[3] for item in points), Decimal(0))
        mse = score_sum / len(points) if points else None
        limitations = (f"segment sample {len(points)} is below configured threshold {rule.minimum_segment_sample}",) if len(points) < rule.minimum_segment_sample else ()
        grouping = {
            "actual-result": "group by realized home-participant win indicator",
            "favorite-result": "group by strict forecast favorite result; probability ties are no-unique-favorite",
            "home-win-probability-bucket": "group by published home-win probability using calibration bucket boundaries",
        }[dimension]
        summaries.append(SegmentSummary(
            f"{dimension}:{value}", SEGMENTATION_VERSION, dimension, value,
            "one-current-included-forecast-evaluation", grouping,
            "sum-brier-score", score_sum, "segment-evaluation-count", len(points),
            tuple(item[0] for item in points), len(points), predicted, observed, mse, limitations,
        ))
    return tuple(summaries)


@dataclass(frozen=True, slots=True, order=True)
class ProviderConstraint:
    provider_id: str
    model_ids: tuple[str, ...]
    model_version_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "constraint provider_id")
        for value in self.model_ids:
            _require_identifier(value, "constraint model_id")
        for value in self.model_version_ids:
            _require_identifier(value, "constraint model_version_id")
        if not self.model_ids or not self.model_version_ids:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "provider constraint requires model and version scope")
        object.__setattr__(self, "model_ids", tuple(sorted(set(self.model_ids))))
        object.__setattr__(self, "model_version_ids", tuple(sorted(set(self.model_version_ids))))


@dataclass(frozen=True, slots=True, order=True)
class ProviderWeight:
    provider_id: str
    weight: Decimal

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "weight provider_id")
        if not self.weight.is_finite() or self.weight < 0:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "hypothesis weights must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class PolicyHypothesis:
    hypothesis_id: str
    version: str
    provider_constraints: tuple[ProviderConstraint, ...]
    eligibility_rules: tuple[str, ...]
    provider_selection_rules: tuple[str, ...]
    weights: tuple[ProviderWeight, ...]
    transformations: tuple[str, ...]
    normalization_rule: str
    missing_provider_behavior: str
    fallback_behavior: str
    sport: str
    competition: str
    proposition_type: str
    assumptions: tuple[str, ...]
    algorithm_assumptions: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, version: str, provider_constraints: tuple[ProviderConstraint, ...], eligibility_rules: tuple[str, ...], provider_selection_rules: tuple[str, ...], weights: tuple[ProviderWeight, ...], transformations: tuple[str, ...], normalization_rule: str, missing_provider_behavior: str, fallback_behavior: str, sport: str, competition: str, proposition_type: str, assumptions: tuple[str, ...] = (), algorithm_assumptions: tuple[str, ...] = ()) -> "PolicyHypothesis":
        material = {
            "version": version,
            "constraints": [(item.provider_id, sorted(item.model_ids), sorted(item.model_version_ids)) for item in sorted(provider_constraints)],
            "eligibility": sorted(set(eligibility_rules)), "selection": sorted(set(provider_selection_rules)),
            "weights": [(item.provider_id, str(item.weight)) for item in sorted(weights)], "transformations": sorted(set(transformations)),
            "normalization": normalization_rule, "missing": missing_provider_behavior, "fallback": fallback_behavior,
            "domain": [sport, competition, proposition_type], "assumptions": sorted(set(assumptions)), "algorithm_assumptions": sorted(set(algorithm_assumptions)),
        }
        digest = _digest(material)
        return cls(f"policy-hypothesis:{digest}", version, tuple(sorted(provider_constraints)), tuple(sorted(set(eligibility_rules))), tuple(sorted(set(provider_selection_rules))), tuple(sorted(weights)), tuple(sorted(set(transformations))), normalization_rule, missing_provider_behavior, fallback_behavior, sport, competition, proposition_type, tuple(sorted(set(assumptions))), tuple(sorted(set(algorithm_assumptions))), digest)

    def __post_init__(self) -> None:
        for value, label in ((self.hypothesis_id, "hypothesis_id"), (self.version, "hypothesis version"), (self.normalization_rule, "normalization_rule"), (self.missing_provider_behavior, "missing_provider_behavior"), (self.fallback_behavior, "fallback_behavior"), (self.sport, "sport"), (self.competition, "competition"), (self.proposition_type, "proposition_type"), (self.input_digest, "input_digest")):
            _require_identifier(value, label)
        providers = {item.provider_id for item in self.provider_constraints}
        if not providers:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Hypothesis requires at least one provider constraint")
        if {item.provider_id for item in self.weights} - providers:
            raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "weight references provider absent from hypothesis constraints")
        if self.hypothesis_id != f"policy-hypothesis:{self.input_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "hypothesis identity does not match deterministic input digest")
        object.__setattr__(self, "provider_constraints", tuple(sorted(self.provider_constraints)))
        object.__setattr__(self, "eligibility_rules", tuple(sorted(set(self.eligibility_rules))))
        object.__setattr__(self, "provider_selection_rules", tuple(sorted(set(self.provider_selection_rules))))
        object.__setattr__(self, "weights", tuple(sorted(self.weights)))
        object.__setattr__(self, "transformations", tuple(sorted(set(self.transformations))))
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))
        object.__setattr__(self, "algorithm_assumptions", tuple(sorted(set(self.algorithm_assumptions))))


class SuggestedGovernanceAction(str, Enum):
    CONTINUE_RESEARCH = "continue-research"
    FUTURE_SHADOW = "future-shadow"
    RETAIN_INCUMBENT = "retain-incumbent"
    CONSIDER_PRODUCTION_ADOPTION = "consider-production-adoption"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ProposalSuggestionRule:
    rule_id: str
    version: str

    def __post_init__(self) -> None:
        _require_identifier(self.rule_id, "proposal rule_id")
        _require_identifier(self.version, "proposal rule version")


def _suggest_governance_action(
    report: ForecastIntelligenceReport,
    benchmark_ids: tuple[str, ...],
    benchmark_comparisons: tuple[tuple[str, str], ...],
) -> tuple[SuggestedGovernanceAction, tuple[str, ...]]:
    reasons = []
    if report.sample_adequacy.label != "policy-consideration-supported":
        reasons.append("sample-adequacy-not-supported")
    if not benchmark_ids:
        reasons.append("benchmark-absent")
    if not benchmark_comparisons:
        reasons.append("benchmark-comparison-absent")
    elif any(value == "unavailable" for _, value in benchmark_comparisons):
        reasons.append("benchmark-comparison-unavailable")
    if reasons:
        return SuggestedGovernanceAction.CONTINUE_RESEARCH, tuple(sorted(reasons))
    return SuggestedGovernanceAction.FUTURE_SHADOW, ("adequacy-and-benchmark-comparison-available",)


@dataclass(frozen=True, slots=True)
class PolicyProposal:
    proposal_id: str
    version: str
    algorithm_id: str
    algorithm_version: str
    report_id: str
    hypothesis_id: str
    hypothesis_version: str
    proposal_rule_id: str
    proposal_rule_version: str
    benchmark_ids: tuple[str, ...]
    benchmark_comparisons: tuple[tuple[str, str], ...]
    benchmark_available: bool
    adequacy_rule_result: str
    triggered_reason_codes: tuple[str, ...]
    suggested_action: SuggestedGovernanceAction
    quantitative_metrics: tuple[tuple[str, str], ...]
    analytical_limitations: tuple[str, ...]
    uncertainty: tuple[str, ...]
    sample_adequacy_label: str
    included_evaluation_ids: tuple[str, ...]
    suggestion_evaluation_ids: tuple[str, ...]
    generated_at: datetime
    input_digest: str
    advisory_only: bool = True
    executable: bool = False

    @classmethod
    def create(cls, report: ForecastIntelligenceReport, hypothesis: PolicyHypothesis, *, version: str, proposal_rule: ProposalSuggestionRule, benchmark_ids: tuple[str, ...] = (), benchmark_comparisons: tuple[tuple[str, str], ...] = (), uncertainty: tuple[str, ...] = (), generated_at: datetime) -> "PolicyProposal":
        _require_aware(generated_at, "generated_at")
        benchmark_ids = tuple(sorted(set(benchmark_ids)))
        benchmark_comparisons = tuple(sorted(set(benchmark_comparisons)))
        suggested_action, reason_codes = _suggest_governance_action(report, benchmark_ids, benchmark_comparisons)
        metrics = (
            ("sample-size", str(report.forecast_quality.sample_size)),
            ("mean-brier", str(report.forecast_quality.mean_brier_score)),
            ("mean-finite-log-loss", str(report.forecast_quality.mean_finite_log_loss)),
            ("infinite-log-loss-count", str(report.forecast_quality.infinite_log_loss_count)),
            ("directional-accuracy", str(report.forecast_quality.directional_accuracy)),
        )
        material = {
            "version": version, "algorithm": [PROPOSAL_ALGORITHM_ID, PROPOSAL_ALGORITHM_VERSION],
            "report": report.report_id, "hypothesis": [hypothesis.hypothesis_id, hypothesis.version],
            "proposal_rule": [proposal_rule.rule_id, proposal_rule.version],
            "benchmarks": benchmark_ids, "benchmark_comparisons": benchmark_comparisons,
            "benchmark_available": bool(benchmark_ids), "adequacy_result": report.sample_adequacy.label,
            "reason_codes": reason_codes, "action": suggested_action.value,
            "metrics": metrics, "limitations": sorted(set(report.limitations)), "uncertainty": sorted(set(uncertainty)),
            "adequacy": report.sample_adequacy.label, "evaluations": list(report.included_evaluation_ids),
        }
        digest = _digest(material)
        return cls(
            f"policy-proposal:{digest}", version, PROPOSAL_ALGORITHM_ID,
            PROPOSAL_ALGORITHM_VERSION, report.report_id, hypothesis.hypothesis_id,
            hypothesis.version, proposal_rule.rule_id, proposal_rule.version,
            benchmark_ids, benchmark_comparisons, bool(benchmark_ids),
            report.sample_adequacy.label, reason_codes, suggested_action, metrics,
            report.limitations, tuple(sorted(set(uncertainty))),
            report.sample_adequacy.label, report.included_evaluation_ids,
            report.included_evaluation_ids, generated_at, digest,
        )

    def __post_init__(self) -> None:
        for value, label in ((self.proposal_id, "proposal_id"), (self.version, "proposal version"), (self.algorithm_id, "algorithm_id"), (self.algorithm_version, "algorithm_version"), (self.report_id, "report_id"), (self.hypothesis_id, "hypothesis_id"), (self.hypothesis_version, "hypothesis_version"), (self.proposal_rule_id, "proposal_rule_id"), (self.proposal_rule_version, "proposal_rule_version"), (self.adequacy_rule_result, "adequacy_rule_result"), (self.sample_adequacy_label, "sample_adequacy_label"), (self.input_digest, "input_digest")):
            _require_identifier(value, label)
        _require_aware(self.generated_at, "generated_at")
        if self.proposal_id != f"policy-proposal:{self.input_digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "proposal identity does not match deterministic input digest")
        if not self.advisory_only or self.executable:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "Policy Proposal must remain advisory and non-executable")
        object.__setattr__(self, "benchmark_ids", tuple(sorted(set(self.benchmark_ids))))
        object.__setattr__(self, "benchmark_comparisons", tuple(sorted(set(self.benchmark_comparisons))))
        object.__setattr__(self, "triggered_reason_codes", tuple(sorted(set(self.triggered_reason_codes))))
        object.__setattr__(self, "quantitative_metrics", tuple(sorted(set(self.quantitative_metrics))))
        object.__setattr__(self, "analytical_limitations", tuple(sorted(set(self.analytical_limitations))))
        object.__setattr__(self, "uncertainty", tuple(sorted(set(self.uncertainty))))
        object.__setattr__(self, "included_evaluation_ids", tuple(sorted(set(self.included_evaluation_ids))))
        object.__setattr__(self, "suggestion_evaluation_ids", tuple(sorted(set(self.suggestion_evaluation_ids))))


_CONTRACTS = (
    EvaluationWindow, EvaluationParticipantContext, CurrentEvaluationSelection, ExcludedEvaluation,
    CoverageSummary, ForecastQualitySummary, CalibrationBucket, SegmentSummary, AdequacyRule,
    SampleAdequacy, ForecastIntelligenceReport, ProviderConstraint, ProviderWeight,
    PolicyHypothesis, ProposalSuggestionRule, PolicyProposal,
)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(SuggestedGovernanceAction,))
