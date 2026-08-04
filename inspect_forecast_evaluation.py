"""Bounded offline PR9 Outcome Evidence → Forecast Evaluation inspection."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from dratings_adapter import DRATINGS_MODEL, DRATINGS_PROVIDER, DRATINGS_VERSION
from event_contracts import Evidence, NativeIdentifier, Provenance, ReconciliationResult, ValidationStatus
from forecast_contracts import AssumptionDisclosure, ForecastDistribution, ForecastObservation, ForecastOutcome, ProbabilityScale, ProviderReportedAssumptions, PublishedProbability
from forecast_evaluation import EligibilityDecisionValue, ForecastEvaluationHistory, create_forecast_evaluation, decide_evaluation_eligibility
from mlb_outcome_adapter import MLBOutcomeAdapter
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse
from outcome_contracts import OutcomeHistory


def run(outcome_fixture: Path, inspection_fixture: Path) -> tuple[str, ...]:
    outcomes = json.loads(outcome_fixture.read_text(encoding="utf-8"))["cases"]
    specification = json.loads(inspection_fixture.read_text(encoding="utf-8"))
    evaluated_at = datetime.fromisoformat(specification["evaluated_at"])
    decisions = []
    evaluations = []
    observations = []
    for candidate in specification["candidates"]:
        record = outcomes[candidate["outcome_case"]]
        payload = {"dates": [{"date": record.get("officialDate", "fixture"), "games": [record]}]}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        response = MLBStatsAPIResponse("https://statsapi.mlb.com/api/v1/schedule", (("sportId", "1"),), evaluated_at, 200, "fixture://mlb-outcome-cases", payload, raw)
        game = MLBStatsAPIAdapter().parse_response(response).games[0].game
        outcome = MLBOutcomeAdapter().parse_response(response)[0].observation
        if game is None or outcome is None:
            continue
        observations.append(outcome)
        forecast = _fixture_forecast(game, outcome.scheduled_start + timedelta(seconds=int(candidate["collection_offset_seconds"])), Decimal(candidate["away_probability"]), Decimal(candidate["home_probability"]))
        decision = decide_evaluation_eligibility(forecast, outcome)
        decisions.append(decision)
        if decision.decision is EligibilityDecisionValue.ELIGIBLE:
            evaluations.append(create_forecast_evaluation(forecast, outcome, decision, provider_id=DRATINGS_PROVIDER.provider_id, model_id=DRATINGS_MODEL.model_id, model_version_id=DRATINGS_VERSION.version_id))
    history = ForecastEvaluationHistory(tuple(evaluations))
    outcome_histories = tuple(
        OutcomeHistory(event_id, event_observations[0].authoritative_provider_id, tuple(event_observations))
        for event_id in sorted({item.canonical_event_id for item in evaluations})
        if (event_observations := [item for item in observations if item.canonical_event_id == event_id and item.authoritative_final])
    )
    current_summary = history.current_summary(outcome_histories)
    counts = Counter(decision.decision.value for decision in decisions)
    reasons = Counter(reason.code.value for decision in decisions for reason in decision.reasons)
    finals = sum(item.authoritative_final for item in observations)
    return (
        f"Outcome Observations parsed: {len(observations)}",
        f"Final outcomes: {finals}",
        f"Candidate pairs: {len(decisions)}",
        f"Eligible pairs: {counts['eligible']}",
        f"Ineligible pairs: {counts['ineligible']}",
        f"Indeterminate pairs: {counts['indeterminate']}",
        f"Stored Forecast Evaluations: {len(evaluations)}",
        f"Current Forecast Evaluations: {current_summary.count}",
        f"Superseded Forecast Evaluations: {len(history.superseded_evaluations(outcome_histories))}",
        "Reason codes: " + (", ".join(f"{key}={reasons[key]}" for key in sorted(reasons)) or "none"),
        f"Current mean Brier score: {current_summary.mean_brier_score}",
        f"Current finite log losses: {current_summary.finite_log_loss_count}",
        f"Current infinite log losses: {current_summary.infinite_log_loss_count}",
    )


def _fixture_forecast(game, collected_at, away_probability, home_probability):
    event_id = game.event.canonical_event_id
    probabilities = (
        PublishedProbability(ForecastOutcome(game.away_team.canonical_team_id, f"participant-wins:{game.away_team.canonical_team_id}", event_id), away_probability, str(away_probability), 2, ProbabilityScale.PROPORTION),
        PublishedProbability(ForecastOutcome(game.home_team.canonical_team_id, f"participant-wins:{game.home_team.canonical_team_id}", event_id), home_probability, str(home_probability), 2, ProbabilityScale.PROPORTION),
    )
    reconciliation = ReconciliationResult.matched(NativeIdentifier("inspection-forecast", f"inspection:{event_id}"), game.event, evidence=(Evidence("fixture", "explicit offline inspection input"),))
    provenance = Provenance(DRATINGS_PROVIDER.provider_id, f"inspection:{event_id}", event_id, collected_at, validation_status=ValidationStatus.VALID)
    return ForecastObservation(f"inspection-forecast:{event_id}:{collected_at.isoformat()}", DRATINGS_VERSION.version_id, reconciliation, ForecastDistribution(probabilities), ProviderReportedAssumptions(AssumptionDisclosure.UNDISCLOSED), collected_at, provenance)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outcome_fixture", type=Path)
    parser.add_argument("inspection_fixture", type=Path)
    arguments = parser.parse_args()
    for line in run(arguments.outcome_fixture, arguments.inspection_fixture):
        print(line)
