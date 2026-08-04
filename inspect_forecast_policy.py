"""Bounded fixture-only PR11 Forecast Policy inspection."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from event_contracts import CanonicalEvent, Evidence, NativeIdentifier, ParticipantRef, Provenance, ReconciliationResult
from forecast_contracts import (
    AssumptionDisclosure,
    ForecastDistribution,
    ForecastIssueCode,
    ForecastObservation,
    ForecastOutcome,
    ForecastValidationIssue,
    ForecastValidationStatus,
    ProbabilityScale,
    ProviderReportedAssumptions,
    PublishedProbability,
)
from forecast_policy import (
    ExecutionScope,
    ForecastPolicyEventContext,
    create_dratings_mlb_winner_policy,
    execute_forecast_policy,
)


def load_fixture(path: Path):
    specification = json.loads(path.read_text(encoding="utf-8"))
    policy = create_dratings_mlb_winner_policy()
    scope_spec = specification["scope"]
    scope = ExecutionScope(
        scope_spec["scope_id"], scope_spec["sport"], scope_spec["competition"],
        scope_spec["proposition_type"], tuple(scope_spec["event_ids"]),
        datetime.fromisoformat(scope_spec["analysis_as_of"]), scope_spec.get("slate_label"),
    )
    observations = tuple(_observation(item) for item in specification["observations"])
    contexts = tuple(_context(item) for item in specification["observations"])
    result = execute_forecast_policy(policy, scope, observations, contexts)
    return policy, scope, observations, contexts, result


def run(path: Path) -> tuple[str, ...]:
    policy, _, _, _, result = load_fixture(path)
    execution = result.execution
    lines = [
        f"Candidate Forecast Observations: {execution.statistics.candidate_observation_count}",
        f"Eligible Forecast Observations: {execution.statistics.eligible_observation_count}",
        f"Ineligible Forecast Observations: {execution.statistics.ineligible_observation_count}",
        f"Indeterminate Forecast Observations: {execution.statistics.indeterminate_observation_count}",
        f"Events considered: {execution.statistics.event_count}",
        f"Policy Forecasts produced: {execution.statistics.policy_forecast_count}",
        f"Unresolved events: {execution.statistics.unresolved_event_count}",
        "Reason-code occurrences (observation and event level; overlapping): "
        + ", ".join(f"{reason.value}={count}" for reason, count in execution.exclusion_reason_counts),
        f"Forecast Policy: {policy.policy_id}",
        f"Forecast Policy Execution: {execution.execution_id}",
    ]
    for forecast in result.policy_forecasts:
        distribution = ", ".join(f"{semantic}={probability}" for _, semantic, probability in forecast.output_distribution)
        lines.append(f"{forecast.canonical_event_id}: {distribution}")
    lines.extend((
        f"Fallback invocations: {execution.statistics.fallback_invocation_count}",
        "Governance authority: none",
    ))
    return tuple(lines)


def _observation(specification: dict) -> ForecastObservation:
    event_id = specification["event_id"]
    away_id = specification.get("away_outcome_id", f"{event_id}:away-win")
    home_id = specification.get("home_outcome_id", f"{event_id}:home-win")
    collected_at = datetime.fromisoformat(specification["collected_at"])
    event = CanonicalEvent(
        "baseball", "MLB", "2026", event_id,
        (ParticipantRef(f"{event_id}:away", "Away"), ParticipantRef(f"{event_id}:home", "Home")),
    )
    distribution = ForecastDistribution((
        PublishedProbability(ForecastOutcome(away_id, "away-win", event_id), Decimal(specification["away"]), specification["away"], 2, ProbabilityScale.PROPORTION),
        PublishedProbability(ForecastOutcome(home_id, "home-win", event_id), Decimal(specification["home"]), specification["home"], 2, ProbabilityScale.PROPORTION),
    ))
    validation = ForecastValidationStatus(specification.get("validation", distribution.validation_status.value))
    issues = () if validation is ForecastValidationStatus.VALID else (
        ForecastValidationIssue(ForecastIssueCode.DISTRIBUTION_TOTAL_OUTSIDE_TOLERANCE, "synthetic invalid distribution"),
    )
    return ForecastObservation(
        specification["id"], specification.get("version_id", "dratings-mlb-undisclosed"),
        ReconciliationResult.matched(NativeIdentifier("fixture-forecast", specification["id"]), event, evidence=(Evidence("fixture", specification["id"]),)),
        distribution, ProviderReportedAssumptions(AssumptionDisclosure.UNKNOWN), collected_at,
        Provenance(
            specification.get("provider_id", "dratings"), specification["id"], event_id, collected_at,
            raw_evidence_ref=f"fixture:{specification['id']}",
            source_url="fixture://forecast-policy", collector_version="fixture-v1",
        ),
        schedule_observation_id=f"schedule:{event_id}", validation_status=validation, validation_issues=issues,
    )


def _context(specification: dict) -> ForecastPolicyEventContext:
    event_id = specification["event_id"]
    start = specification.get("start_at")
    return ForecastPolicyEventContext.create(
        context_version="1", canonical_event_id=event_id,
        sport="baseball", competition="MLB",
        proposition_type=specification.get("proposition_type", "winner"),
        model_id=specification.get("model_id", "dratings-mlb"),
        scheduled_start=datetime.fromisoformat(start) if start else None,
        away_participant_id=f"{event_id}:away",
        home_participant_id=f"{event_id}:home",
        away_outcome_id=f"{event_id}:away-win",
        home_outcome_id=f"{event_id}:home-win",
        source_object_ids=(event_id, f"schedule:{event_id}"),
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    arguments = parser.parse_args()
    for line in run(arguments.fixture):
        print(line)
