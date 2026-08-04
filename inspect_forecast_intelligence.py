"""Bounded fixture-only PR10 Forecast Intelligence inspection."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

from forecast_evaluation import EvaluationArithmeticInput, ForecastEvaluation
from forecast_intelligence import (
    AdequacyRule,
    CurrentEvaluationSelection,
    EvaluationParticipantContext,
    EvaluationWindow,
    PolicyHypothesis,
    PolicyProposal,
    ProposalSuggestionRule,
    ProviderConstraint,
    ProviderWeight,
    create_forecast_intelligence_report,
)


def load_fixture(path: Path):
    specification = json.loads(path.read_text(encoding="utf-8"))
    evaluations = tuple(_evaluation(item) for item in specification["evaluations"])
    by_id = {item.evaluation_id: item for item in evaluations}
    selection_spec = specification["selection"]
    material_ids = tuple(sorted(item.evaluation_id for item in evaluations))
    current = tuple(by_id[item] for item in selection_spec["current_evaluation_ids"])
    superseded = tuple(sorted(selection_spec["superseded_evaluation_ids"]))
    selection = CurrentEvaluationSelection.create(
        candidate_evaluation_ids=material_ids, current_evaluations=current, superseded_evaluation_ids=superseded,
        selected_outcome_observation_ids=tuple(selection_spec["selected_outcome_observation_ids"]),
    )
    contexts = tuple(EvaluationParticipantContext(item["evaluation_id"], item["away_participant_id"], item["home_participant_id"]) for item in specification["contexts"])
    window_spec = specification["window"]
    window = EvaluationWindow(window_spec["window_id"], window_spec["version"], datetime.fromisoformat(window_spec["start_at"]), datetime.fromisoformat(window_spec["end_at"]), datetime.fromisoformat(window_spec["analysis_as_of"]) if window_spec.get("analysis_as_of") else None)
    adequacy_spec = specification["adequacy_rule"]
    adequacy = AdequacyRule(adequacy_spec["rule_id"], adequacy_spec["version"], adequacy_spec["minimum_report_sample"], adequacy_spec["minimum_segment_sample"])
    generated_at = datetime.fromisoformat(specification["generated_at"])
    report = create_forecast_intelligence_report(
        selection, contexts, provider_id=specification["scope"]["provider_id"], model_ids=tuple(specification["scope"]["model_ids"]),
        model_version_ids=tuple(specification["scope"]["model_version_ids"]), sport=specification["scope"]["sport"],
        competition=specification["scope"]["competition"], proposition_type=specification["scope"]["proposition_type"],
        eligibility_policy_id=specification["scope"]["eligibility_policy_id"], eligibility_policy_version=specification["scope"]["eligibility_policy_version"],
        evaluation_window=window, adequacy_rule=adequacy, generated_at=generated_at,
    )
    hypothesis_spec = specification["hypothesis"]
    hypothesis = PolicyHypothesis.create(
        version=hypothesis_spec["version"],
        provider_constraints=tuple(ProviderConstraint(item["provider_id"], tuple(item["model_ids"]), tuple(item["model_version_ids"])) for item in hypothesis_spec["provider_constraints"]),
        eligibility_rules=tuple(hypothesis_spec["eligibility_rules"]), provider_selection_rules=tuple(hypothesis_spec["provider_selection_rules"]),
        weights=tuple(ProviderWeight(item["provider_id"], Decimal(item["weight"])) for item in hypothesis_spec["weights"]),
        transformations=tuple(hypothesis_spec["transformations"]), normalization_rule=hypothesis_spec["normalization_rule"],
        missing_provider_behavior=hypothesis_spec["missing_provider_behavior"], fallback_behavior=hypothesis_spec["fallback_behavior"],
        sport=specification["scope"]["sport"], competition=specification["scope"]["competition"], proposition_type=specification["scope"]["proposition_type"],
        assumptions=tuple(hypothesis_spec["assumptions"]), algorithm_assumptions=tuple(hypothesis_spec["algorithm_assumptions"]),
    )
    proposal_spec = specification["proposal"]
    proposal = PolicyProposal.create(
        report, hypothesis, version=proposal_spec["version"],
        proposal_rule=ProposalSuggestionRule(proposal_spec["rule_id"], proposal_spec["rule_version"]),
        benchmark_ids=tuple(proposal_spec["benchmark_ids"]), benchmark_comparisons=tuple(tuple(item) for item in proposal_spec["benchmark_comparisons"]),
        uncertainty=tuple(proposal_spec["uncertainty"]), generated_at=generated_at,
    )
    return selection, report, hypothesis, proposal


def run(path: Path) -> tuple[str, ...]:
    selection, report, hypothesis, proposal = load_fixture(path)
    return (
        f"Candidate Forecast Evaluations: {len(selection.candidate_evaluation_ids)}",
        f"Current Forecast Evaluations: {report.coverage.current_count}",
        f"Superseded Forecast Evaluations: {report.coverage.superseded_count}",
        f"Included Forecast Evaluations: {report.coverage.included_count}",
        f"Excluded Forecast Evaluations: {report.coverage.excluded_count}",
        f"Mean Brier score: {report.forecast_quality.mean_brier_score}",
        f"Finite log losses: {report.forecast_quality.finite_log_loss_count}",
        f"Infinite log losses: {report.forecast_quality.infinite_log_loss_count}",
        f"Calibration buckets: {len(report.calibration)}",
        f"Segments: {len(report.segments)}",
        f"Sample adequacy: {report.sample_adequacy.label}",
        f"Policy Hypothesis: {hypothesis.hypothesis_id}",
        f"Suggested governance action: {proposal.suggested_action.value}",
        f"Proposal reasons: {', '.join(proposal.triggered_reason_codes)}",
        f"Benchmark available: {'yes' if proposal.benchmark_available else 'no'}",
        "Advisory only: yes" if proposal.advisory_only and not proposal.executable else "Advisory only: no",
    )


def _evaluation(specification: dict) -> ForecastEvaluation:
    away, home = specification["away_participant_id"], specification["home_participant_id"]
    probabilities = {away: Decimal(specification["away_probability"]), home: Decimal(specification["home_probability"])}
    winner = specification["winner_participant_id"]
    realized_probability = probabilities[winner]
    brier = (realized_probability - 1) ** 2
    if realized_probability == 0:
        log_loss = Decimal("Infinity")
        limitations = ("zero probability assigned to realized winner; log loss is positive infinity",)
    else:
        with localcontext() as context:
            context.prec = 50
            log_loss = -realized_probability.ln()
        limitations = ()
    maximum = max(probabilities.values())
    favorites = tuple(key for key, value in probabilities.items() if value == maximum)
    favorite = favorites[0] if len(favorites) == 1 else None
    inputs = tuple(EvaluationArithmeticInput(key, value, int(key == winner)) for key, value in probabilities.items())
    return ForecastEvaluation(
        specification["evaluation_id"], "mlb-winner-forecast-quality", "1", specification["eligibility_decision_id"],
        specification["forecast_observation_id"], specification["outcome_observation_id"], specification["canonical_event_id"],
        specification["provider_id"], specification["model_id"], specification["model_version_id"], datetime.fromisoformat(specification["forecast_collected_at"]),
        tuple(probabilities.items()), winner, tuple((item.participant_id, item.realized_value) for item in inputs), brier, log_loss,
        None if favorite is None else favorite == winner, favorite, "fixture-bucket", inputs, f"derivation:{specification['evaluation_id']}", limitations=limitations,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    arguments = parser.parse_args()
    for line in run(arguments.fixture):
        print(line)
