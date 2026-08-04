import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from dratings_adapter import DRATINGS_MODEL, DRATINGS_PROVIDER, DRATINGS_VERSION
from event_contracts import ContractError, Evidence, NativeIdentifier, Provenance, ReasonCode, ReconciliationResult, ValidationReason, ValidationStatus
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
from forecast_evaluation import (
    ELIGIBILITY_POLICY_ID,
    ELIGIBILITY_POLICY_VERSION,
    EvaluationEligibilityDecision,
    EligibilityDecisionValue,
    EligibilityReasonCode,
    ForecastEvaluation,
    ForecastEvaluationHistory,
    create_forecast_evaluation,
    decide_evaluation_eligibility,
)
from mlb_outcome_adapter import MLBOutcomeAdapter
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse
from outcome_contracts import OutcomeHistory
from inspect_forecast_evaluation import run as run_inspection


FIXTURE = Path(__file__).parent / "fixtures" / "mlb_outcome_cases.json"
INSPECTION_FIXTURE = Path(__file__).parent / "fixtures" / "forecast_evaluation_inspection.json"
AT = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)


class ForecastEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

    def evidence(self, name="normal_final", *, collected_at=AT):
        return self.evidence_record(self.cases[name], collected_at=collected_at)

    def evidence_record(self, record, *, collected_at):
        payload = {"dates": [{"date": "2026-08-01", "games": [record]}]}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        response = MLBStatsAPIResponse("https://statsapi.mlb.com/api/v1/schedule", (("sportId", "1"),), collected_at, 200, "https://statsapi.mlb.com/api/v1/schedule?sportId=1", payload, raw)
        game = MLBStatsAPIAdapter().parse_response(response).games[0].game
        outcome = MLBOutcomeAdapter().parse_response(response)[0].observation
        return game, outcome

    def forecast(self, game, *, away=Decimal("0.40"), home=Decimal("0.60"), collected_at=None, validation=ForecastValidationStatus.VALID):
        collected_at = collected_at or (datetime.fromisoformat(self.cases["normal_final"]["gameDate"].replace("Z", "+00:00")) - timedelta(hours=2))
        event_id = game.event.canonical_event_id
        probabilities = (
            PublishedProbability(ForecastOutcome(game.away_team.canonical_team_id, f"participant-wins:{game.away_team.canonical_team_id}", event_id), away, str(away), 2, ProbabilityScale.PROPORTION),
            PublishedProbability(ForecastOutcome(game.home_team.canonical_team_id, f"participant-wins:{game.home_team.canonical_team_id}", event_id), home, str(home), 2, ProbabilityScale.PROPORTION),
        )
        distribution = ForecastDistribution(probabilities)
        issues = () if validation is ForecastValidationStatus.VALID else (ForecastValidationIssue(code=ForecastIssueCode.MATERIAL_INFORMATION_MISSING, detail="intentional test mutation"),)
        reconciliation = ReconciliationResult.matched(NativeIdentifier("fixture-forecast", f"forecast:{event_id}"), game.event, evidence=(Evidence("fixture", "intentional forecast fixture"),))
        provenance = Provenance(DRATINGS_PROVIDER.provider_id, f"forecast:{event_id}", event_id, collected_at, validation_status=ValidationStatus.VALID)
        return ForecastObservation(f"forecast-observation:{event_id}:{collected_at.isoformat()}", DRATINGS_VERSION.version_id, reconciliation, distribution, ProviderReportedAssumptions(AssumptionDisclosure.UNDISCLOSED), collected_at, provenance, validation_status=validation, validation_issues=issues)

    def decision(self, forecast, outcome, **kwargs):
        return decide_evaluation_eligibility(forecast, outcome, **kwargs)

    def evaluation(self, forecast, outcome, decision=None):
        return create_forecast_evaluation(forecast, outcome, decision or self.decision(forecast, outcome), provider_id=DRATINGS_PROVIDER.provider_id, model_id=DRATINGS_MODEL.model_id, model_version_id=DRATINGS_VERSION.version_id)

    def test_policy_identity_and_ordinary_extra_shortened_completed_suspended_are_eligible(self):
        for name in ("normal_final", "extra_inning_final", "shortened_final", "suspended_final"):
            with self.subTest(name=name):
                game, outcome = self.evidence(name)
                decision = self.decision(self.forecast(game), outcome)
                self.assertIs(decision.decision, EligibilityDecisionValue.ELIGIBLE)
                self.assertEqual((decision.policy_id, decision.policy_version), (ELIGIBILITY_POLICY_ID, ELIGIBILITY_POLICY_VERSION))

    def test_strict_collection_chronology(self):
        game, outcome = self.evidence()
        start = outcome.scheduled_start
        before = self.decision(self.forecast(game, collected_at=start - timedelta(microseconds=1)), outcome)
        at_start = self.decision(self.forecast(game, collected_at=start), outcome)
        after = self.decision(self.forecast(game, collected_at=start + timedelta(microseconds=1)), outcome)
        self.assertIs(before.decision, EligibilityDecisionValue.ELIGIBLE)
        self.assertEqual(at_start.reasons[0].code, EligibilityReasonCode.FORECAST_AT_START)
        self.assertEqual(after.reasons[0].code, EligibilityReasonCode.FORECAST_AFTER_START)
        self.assertEqual(at_start.forecast_collected_at, start)

    def test_nonfinal_cancelled_suspended_and_forfeit_reason_codes(self):
        expected = {
            "scheduled": EligibilityReasonCode.OUTCOME_NOT_FINAL,
            "postponed": EligibilityReasonCode.OUTCOME_NOT_FINAL,
            "suspended": EligibilityReasonCode.OUTCOME_SUSPENDED,
            "cancelled": EligibilityReasonCode.OUTCOME_CANCELLED,
            "forfeit": EligibilityReasonCode.OUTCOME_FORFEIT_POLICY_DEFERRED,
        }
        for name, reason in expected.items():
            game, outcome = self.evidence(name)
            decision = self.decision(self.forecast(game), outcome)
            self.assertIs(decision.decision, EligibilityDecisionValue.INELIGIBLE)
            self.assertIn(reason, {item.code for item in decision.reasons})

    def test_invalid_forecast_and_incomplete_distribution_are_ineligible(self):
        game, outcome = self.evidence()
        invalid = self.forecast(game, validation=ForecastValidationStatus.INCOMPLETE)
        decision = self.decision(invalid, outcome)
        self.assertIn(EligibilityReasonCode.FORECAST_INVALID, {item.code for item in decision.reasons})
        other = replace(invalid.distribution.probabilities[0].outcome, outcome_id="team:other")
        bad_distribution = ForecastDistribution((replace(invalid.distribution.probabilities[0], outcome=other), invalid.distribution.probabilities[1]))
        bad = replace(invalid, distribution=bad_distribution)
        decision = self.decision(bad, outcome)
        self.assertIn(EligibilityReasonCode.FORECAST_DISTRIBUTION_INCOMPLETE, {item.code for item in decision.reasons})

    def test_ambiguous_forecast_and_event_mismatch_are_explicit(self):
        game, outcome = self.evidence()
        other_game, other_outcome = self.evidence("extra_inning_final")
        base = self.forecast(game)
        probabilities = tuple(replace(item, outcome=replace(item.outcome, canonical_event_id=None)) for item in base.distribution.probabilities)
        ambiguous = ForecastObservation(
            "forecast-observation:ambiguous",
            base.version_id,
            ReconciliationResult.ambiguous(NativeIdentifier("fixture-forecast", "ambiguous"), (game.event, other_game.event), evidence=(Evidence("fixture", "intentional ambiguity"),), reasons=(ValidationReason(ReasonCode.AMBIGUOUS_CANDIDATES, "two candidates"),)),
            ForecastDistribution(probabilities),
            base.assumptions,
            base.collected_at,
            replace(base.provenance, canonical_event_id=None),
        )
        ambiguous_decision = self.decision(ambiguous, outcome)
        self.assertIn(EligibilityReasonCode.FORECAST_EVENT_AMBIGUOUS, {item.code for item in ambiguous_decision.reasons})
        mismatch = self.decision(base, other_outcome)
        self.assertIn(EligibilityReasonCode.OUTCOME_EVENT_MISMATCH, {item.code for item in mismatch.reasons})

    def test_chronology_incomplete_is_indeterminate_and_eligibility_is_state_independent(self):
        game, outcome = self.evidence()
        forecast = self.forecast(game)
        unknown = self.decision(forecast, outcome, scheduled_start_known=False)
        self.assertIs(unknown.decision, EligibilityDecisionValue.INDETERMINATE)
        first = self.decision(forecast, outcome)
        repeated = self.decision(forecast, outcome)
        self.assertEqual(first, repeated)
        self.assertIs(first.decision, EligibilityDecisionValue.ELIGIBLE)
        first_evaluation = self.evaluation(forecast, outcome, first)
        repeated_evaluation = self.evaluation(forecast, outcome, repeated)
        self.assertEqual(first_evaluation.evaluation_id, repeated_evaluation.evaluation_id)
        with self.assertRaises(ContractError):
            ForecastEvaluationHistory((first_evaluation,)).append(repeated_evaluation)

    def test_postponement_and_material_reschedule_policy(self):
        original_start = datetime(2026, 8, 1, 18, tzinfo=timezone.utc)
        revised_start = datetime(2026, 8, 2, 18, tzinfo=timezone.utc)
        base = json.loads(json.dumps(self.cases["normal_final"]))
        base.pop("lastUpdated", None)
        scheduled_record = json.loads(json.dumps(base))
        scheduled_record["status"]["detailedState"] = "Scheduled"
        scheduled_record["gameDate"] = original_start.isoformat().replace("+00:00", "Z")
        for side in ("away", "home"):
            scheduled_record["teams"][side].pop("score", None)
            scheduled_record["teams"][side].pop("isWinner", None)
        postponed_record = json.loads(json.dumps(scheduled_record))
        postponed_record["status"]["detailedState"] = "Postponed"
        postponed_record["gameDate"] = revised_start.isoformat().replace("+00:00", "Z")
        final_record = json.loads(json.dumps(base))
        final_record["gameDate"] = revised_start.isoformat().replace("+00:00", "Z")
        game, scheduled = self.evidence_record(scheduled_record, collected_at=original_start - timedelta(hours=5))
        _, postponed = self.evidence_record(postponed_record, collected_at=original_start - timedelta(hours=2))
        _, final = self.evidence_record(final_record, collected_at=revised_start + timedelta(hours=4))
        history = OutcomeHistory(final.canonical_event_id, final.authoritative_provider_id, (final, postponed, scheduled))
        old_forecast = self.forecast(game, collected_at=original_start - timedelta(hours=4))
        without_history = self.decision(old_forecast, final)
        old_decision = self.decision(old_forecast, final, outcome_history=history)
        self.assertIs(old_decision.decision, EligibilityDecisionValue.INELIGIBLE)
        self.assertIn(EligibilityReasonCode.FORECAST_PREDATES_POSTPONEMENT, {item.code for item in old_decision.reasons})
        self.assertNotEqual(without_history.decision_id, old_decision.decision_id)
        self.assertEqual(
            set(old_decision.outcome_history_observation_ids),
            {scheduled.observation_id, postponed.observation_id, final.observation_id},
        )
        self.assertEqual(EvaluationEligibilityDecision.from_json(old_decision.to_json()), old_decision)
        reordered = OutcomeHistory(final.canonical_event_id, final.authoritative_provider_id, (scheduled, final, postponed))
        self.assertEqual(self.decision(old_forecast, final, outcome_history=reordered).decision_id, old_decision.decision_id)
        irrelevant_record = json.loads(json.dumps(scheduled_record))
        irrelevant_record["status"]["detailedState"] = "Delayed"
        _, irrelevant = self.evidence_record(irrelevant_record, collected_at=original_start - timedelta(hours=4, minutes=30))
        with_irrelevant = OutcomeHistory(final.canonical_event_id, final.authoritative_provider_id, (irrelevant, final, scheduled, postponed))
        self.assertEqual(self.decision(old_forecast, final, outcome_history=with_irrelevant).decision_id, old_decision.decision_id)
        new_forecast = self.forecast(game, collected_at=original_start - timedelta(hours=1))
        new_decision = self.decision(new_forecast, final, outcome_history=history)
        self.assertIs(new_decision.decision, EligibilityDecisionValue.ELIGIBLE)
        self.assertEqual(self.decision(new_forecast, final, outcome_history=history).decision_id, new_decision.decision_id)
        at_revised = self.forecast(game, collected_at=revised_start)
        self.assertIn(EligibilityReasonCode.FORECAST_AT_START, {item.code for item in self.decision(at_revised, final, outcome_history=history).reasons})
        after_revised = self.forecast(game, collected_at=revised_start + timedelta(seconds=1))
        self.assertIn(EligibilityReasonCode.FORECAST_AFTER_START, {item.code for item in self.decision(after_revised, final, outcome_history=history).reasons})
        incomplete = OutcomeHistory(final.canonical_event_id, final.authoritative_provider_id, (postponed, final))
        incomplete_decision = self.decision(new_forecast, final, outcome_history=incomplete)
        self.assertIs(incomplete_decision.decision, EligibilityDecisionValue.INDETERMINATE)

    def test_suspension_history_does_not_trigger_postponement_rule(self):
        game, suspended = self.evidence("suspended", collected_at=datetime(2026, 8, 2, 23, tzinfo=timezone.utc))
        _, final = self.evidence("suspended_final", collected_at=datetime(2026, 8, 4, 12, tzinfo=timezone.utc))
        history = OutcomeHistory(final.canonical_event_id, final.authoritative_provider_id, (suspended, final))
        forecast = self.forecast(game, collected_at=suspended.scheduled_start - timedelta(hours=1))
        self.assertIs(self.decision(forecast, final, outcome_history=history).decision, EligibilityDecisionValue.ELIGIBLE)
        self.assertIn(EligibilityReasonCode.OUTCOME_SUSPENDED, {item.code for item in self.decision(forecast, suspended, outcome_history=OutcomeHistory(suspended.canonical_event_id, suspended.authoritative_provider_id, (suspended,))).reasons})

    def test_exact_binary_brier_full_distribution_log_loss_and_mapping(self):
        game, outcome = self.evidence()
        forecast = self.forecast(game)
        item = self.evaluation(forecast, outcome)
        self.assertEqual(item.brier_score, Decimal("0.16"))
        self.assertEqual(dict(item.probability_distribution), {game.away_team.canonical_team_id: Decimal("0.40"), game.home_team.canonical_team_id: Decimal("0.60")})
        self.assertEqual(dict(item.realized_outcome_vector), {game.away_team.canonical_team_id: 0, game.home_team.canonical_team_id: 1})
        self.assertEqual(item.log_loss.quantize(Decimal("0.000001")), Decimal("0.510826"))
        self.assertTrue(item.directional_correct)
        self.assertEqual(item.calibration_bucket, "0.6-0.7")
        self.assertEqual(ForecastEvaluation.from_json(item.to_json()), item)

    def test_zero_realized_probability_is_explicit_positive_infinity(self):
        game, outcome = self.evidence()
        item = self.evaluation(self.forecast(game, away=Decimal("1"), home=Decimal("0")), outcome)
        self.assertTrue(item.log_loss.is_infinite())
        self.assertTrue(item.limitations)
        payload = item.to_json()
        self.assertIn('"__non_finite_decimal__":"positive-infinity"', payload)
        json.loads(payload)
        self.assertEqual(ForecastEvaluation.from_json(payload), item)
        finite = self.evaluation(self.forecast(game, collected_at=outcome.scheduled_start - timedelta(hours=1)), outcome)
        summary = ForecastEvaluationHistory((item, finite)).summary
        self.assertEqual(summary.count, 2)
        self.assertEqual(summary.finite_log_loss_count, 1)
        self.assertEqual(summary.infinite_log_loss_count, 1)

    def test_directional_tie_and_calibration_boundaries(self):
        game, outcome = self.evidence()
        tied = self.evaluation(self.forecast(game, away=Decimal("0.5"), home=Decimal("0.5")), outcome)
        self.assertIsNone(tied.predicted_favorite_id)
        self.assertIsNone(tied.directional_correct)
        self.assertEqual(tied.calibration_bucket, "0.5-0.6")
        perfect = self.evaluation(self.forecast(game, away=Decimal("0"), home=Decimal("1")), outcome)
        self.assertEqual(perfect.calibration_bucket, "0.9-1.0")

    def test_identity_preservation_immutability_and_no_market_or_wager_fields(self):
        game, outcome = self.evidence()
        forecast = self.forecast(game)
        item = self.evaluation(forecast, outcome)
        self.assertEqual((item.provider_id, item.model_id, item.model_version_id), (DRATINGS_PROVIDER.provider_id, DRATINGS_MODEL.model_id, DRATINGS_VERSION.version_id))
        self.assertNotIn("market", item.to_json().lower())
        self.assertNotIn("wager", item.to_json().lower())
        with self.assertRaises(FrozenInstanceError):
            item.brier_score = Decimal("0")

    def test_ineligible_or_incompatible_inputs_cannot_create_evaluation(self):
        game, outcome = self.evidence()
        forecast = self.forecast(game, collected_at=outcome.scheduled_start)
        with self.assertRaises(ContractError):
            self.evaluation(forecast, outcome)
        other_game, other_outcome = self.evidence("extra_inning_final")
        with self.assertRaises(ContractError):
            create_forecast_evaluation(self.forecast(game), other_outcome, self.decision(self.forecast(game), outcome), provider_id=DRATINGS_PROVIDER.provider_id, model_id=DRATINGS_MODEL.model_id, model_version_id=DRATINGS_VERSION.version_id)

    def test_history_duplicate_rejection_append_order_and_reproducible_summary(self):
        game, outcome = self.evidence()
        first = self.evaluation(self.forecast(game), outcome)
        other_game, other_outcome = self.evidence("extra_inning_final")
        second = self.evaluation(self.forecast(other_game, away=Decimal("0.7"), home=Decimal("0.3")), other_outcome)
        history = ForecastEvaluationHistory((second, first))
        self.assertEqual(history.summary.count, 2)
        self.assertEqual(history.summary.mean_brier_score, (first.brier_score + second.brier_score) / 2)
        self.assertEqual(ForecastEvaluationHistory.from_json(history.to_json()), history)
        with self.assertRaises(ContractError):
            ForecastEvaluationHistory((first, first))

    def test_corrected_final_is_immutable_and_current_view_excludes_superseded_evaluation(self):
        initial_record = json.loads(json.dumps(self.cases["normal_final"]))
        game, initial = self.evidence_record(initial_record, collected_at=AT)
        corrected_record = json.loads(json.dumps(initial_record))
        corrected_record["teams"]["away"]["score"] = 5
        corrected_record["teams"]["away"]["isWinner"] = True
        corrected_record["teams"]["home"]["score"] = 4
        corrected_record["teams"]["home"]["isWinner"] = False
        _, corrected = self.evidence_record(corrected_record, collected_at=AT + timedelta(hours=1))
        forecast = self.forecast(game)
        first = self.evaluation(forecast, initial)
        second = self.evaluation(forecast, corrected)
        self.assertNotEqual(first.evaluation_id, second.evaluation_id)
        history = ForecastEvaluationHistory((second, first))
        outcomes = OutcomeHistory(initial.canonical_event_id, initial.authoritative_provider_id, (corrected, initial))
        self.assertEqual(history.evaluation_by_id(first.evaluation_id), first)
        self.assertEqual(history.current_evaluations((outcomes,)), (second,))
        self.assertEqual(history.superseded_evaluations((outcomes,)), (first,))
        self.assertEqual(history.summary.count, 2)
        self.assertEqual(history.current_summary((outcomes,)).count, 1)
        self.assertEqual(ForecastEvaluationHistory.from_json(history.to_json()), history)

    def test_conflicting_corrected_final_chronology_fails_closed(self):
        initial_record = json.loads(json.dumps(self.cases["normal_final"]))
        _, initial = self.evidence_record(initial_record, collected_at=AT)
        corrected_record = json.loads(json.dumps(initial_record))
        corrected_record["teams"]["away"]["score"] = 5
        corrected_record["teams"]["away"]["isWinner"] = True
        corrected_record["teams"]["home"]["score"] = 4
        corrected_record["teams"]["home"]["isWinner"] = False
        _, corrected = self.evidence_record(corrected_record, collected_at=AT)
        outcomes = OutcomeHistory(initial.canonical_event_id, initial.authoritative_provider_id, (initial, corrected))
        with self.assertRaises(ContractError):
            _ = outcomes.latest_authoritative_final

    def test_offline_inspection_reports_factual_counts(self):
        lines = run_inspection(FIXTURE, INSPECTION_FIXTURE)
        self.assertIn("Outcome Observations parsed: 5", lines)
        self.assertIn("Final outcomes: 3", lines)
        self.assertIn("Candidate pairs: 5", lines)
        self.assertIn("Eligible pairs: 2", lines)
        self.assertIn("Ineligible pairs: 3", lines)
        self.assertIn("Stored Forecast Evaluations: 2", lines)
        self.assertIn("Current Forecast Evaluations: 2", lines)
        self.assertIn("Superseded Forecast Evaluations: 0", lines)
        self.assertIn("Current finite log losses: 2", lines)
        self.assertIn("Current infinite log losses: 0", lines)


if __name__ == "__main__":
    unittest.main()
