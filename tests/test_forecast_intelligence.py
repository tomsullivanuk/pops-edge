import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from event_contracts import ContractError, ValidationStatus
from forecast_evaluation import ForecastEvaluationHistory
from forecast_intelligence import (
    AdequacyRule,
    CurrentEvaluationSelection,
    ForecastIntelligenceReport,
    PolicyHypothesis,
    PolicyProposal,
    ProposalSuggestionRule,
    ProviderConstraint,
    ProviderWeight,
    SuggestedGovernanceAction,
    create_forecast_intelligence_report,
    select_current_evaluations,
)
from inspect_forecast_intelligence import load_fixture, run
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_intelligence_cases.json"
GENERATED = datetime(2026, 8, 4, 15, tzinfo=timezone.utc)


class ForecastIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.selection, self.report, self.hypothesis, self.proposal = load_fixture(FIXTURE)

    def rerun_report(self, generated_at=GENERATED):
        selection, report, _, _ = load_fixture(FIXTURE)
        contexts = self._contexts_from_report_fixture()
        return create_forecast_intelligence_report(
            selection,
            contexts,
            provider_id=report.provider_id,
            model_ids=report.model_ids,
            model_version_ids=report.model_version_ids,
            sport=report.sport,
            competition=report.competition,
            proposition_type=report.proposition_type,
            eligibility_policy_id=report.eligibility_policy_id,
            eligibility_policy_version=report.eligibility_policy_version,
            evaluation_window=report.evaluation_window,
            adequacy_rule=AdequacyRule(report.adequacy_rule_id, report.adequacy_rule_version, 4, 2),
            generated_at=generated_at,
        )

    def _contexts_from_report_fixture(self):
        import json
        from forecast_intelligence import EvaluationParticipantContext
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return tuple(EvaluationParticipantContext(item["evaluation_id"], item["away_participant_id"], item["home_participant_id"]) for item in payload["contexts"])

    def test_report_identity_serialization_and_wall_clock_independence(self):
        later = self.rerun_report(GENERATED + timedelta(days=1))
        self.assertEqual(self.report.report_id, later.report_id)
        self.assertEqual(self.report.input_digest, later.input_digest)
        self.assertNotEqual(self.report.generated_at, later.generated_at)
        self.assertEqual(ForecastIntelligenceReport.from_json(self.report.to_json()), self.report)
        with self.assertRaises(FrozenInstanceError):
            self.report.report_id = "changed"

    def test_report_provenance_current_selection_and_complete_accounting(self):
        self.assertEqual(self.report.coverage.candidate_count, 5)
        self.assertEqual(self.report.coverage.current_count, 4)
        self.assertEqual(self.report.coverage.superseded_count, 1)
        self.assertEqual(self.report.coverage.included_count, 3)
        self.assertEqual(self.report.coverage.excluded_count, 1)
        self.assertEqual(self.report.coverage.included_evaluation_ids, self.report.included_evaluation_ids)
        self.assertEqual(self.report.coverage.superseded_evaluation_ids, self.report.superseded_evaluation_ids)
        self.assertEqual(len(self.report.included_evaluation_ids) + len(self.report.excluded_evaluations) + len(self.report.superseded_evaluation_ids), 5)
        self.assertEqual(self.report.excluded_evaluations[0].reason, "outside-evaluation-window")
        self.assertEqual(self.report.eligibility_policy_id, "mlb-winner-evaluation-eligibility")
        self.assertEqual(self.report.eligibility_policy_version, "1")
        self.assertTrue(self.report.selected_outcome_observation_ids)

    def test_authoritative_outcome_history_selects_corrected_final(self):
        evaluations = tuple(self.selection.current_evaluations) + tuple(
            item for item in self._all_fixture_evaluations() if item.evaluation_id in self.selection.superseded_evaluation_ids
        )
        history = ForecastEvaluationHistory(evaluations)
        histories = tuple(self._outcome_history_for_event(event_id, tuple(item for item in evaluations if item.canonical_event_id == event_id)) for event_id in sorted({item.canonical_event_id for item in evaluations}))
        selected = select_current_evaluations(history, histories)
        self.assertIn("evaluation:corrected", {item.evaluation_id for item in selected.current_evaluations})
        self.assertEqual(selected.superseded_evaluation_ids, ("evaluation:original",))
        self.assertEqual(set(selected.candidate_evaluation_ids), {item.evaluation_id for item in evaluations})
        self.assertEqual(CurrentEvaluationSelection.from_json(selected.to_json()), selected)
        repeated = select_current_evaluations(ForecastEvaluationHistory(tuple(reversed(evaluations))), tuple(reversed(histories)))
        self.assertEqual(repeated.selection_id, selected.selection_id)

    def test_material_participant_role_context_changes_report_identity(self):
        contexts = list(self._contexts_from_report_fixture())
        first = contexts[0]
        contexts[0] = replace(first, away_participant_id=first.home_participant_id, home_participant_id=first.away_participant_id)
        changed = create_forecast_intelligence_report(
            self.selection, tuple(contexts), provider_id=self.report.provider_id, model_ids=self.report.model_ids,
            model_version_ids=self.report.model_version_ids, sport=self.report.sport, competition=self.report.competition,
            proposition_type=self.report.proposition_type, eligibility_policy_id=self.report.eligibility_policy_id,
            eligibility_policy_version=self.report.eligibility_policy_version, evaluation_window=self.report.evaluation_window,
            adequacy_rule=AdequacyRule("fixture-descriptive-adequacy", "1", 4, 2), generated_at=GENERATED,
        )
        self.assertNotEqual(changed.report_id, self.report.report_id)

    def _all_fixture_evaluations(self):
        import json
        from inspect_forecast_intelligence import _evaluation
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return tuple(_evaluation(item) for item in payload["evaluations"])

    def _report_for_probabilities(self, cases):
        from forecast_intelligence import EvaluationParticipantContext
        from inspect_forecast_intelligence import _evaluation
        evaluations = []
        contexts = []
        for index, (home_probability, home_won) in enumerate(cases):
            away, home = f"team:boundary-away-{index}", f"team:boundary-home-{index}"
            evaluation_id = f"evaluation:boundary-{index}"
            evaluations.append(_evaluation({
                "evaluation_id": evaluation_id,
                "eligibility_decision_id": f"eligibility:boundary-{index}",
                "forecast_observation_id": f"forecast:boundary-{index}",
                "outcome_observation_id": f"outcome:boundary-{index}",
                "canonical_event_id": f"mlb:boundary-{index}",
                "provider_id": "dratings", "model_id": "dratings-mlb",
                "model_version_id": "dratings-mlb-undisclosed",
                "forecast_collected_at": "2026-08-02T12:00:00+00:00",
                "away_participant_id": away, "home_participant_id": home,
                "away_probability": str(Decimal(1) - home_probability),
                "home_probability": str(home_probability),
                "winner_participant_id": home if home_won else away,
            }))
            contexts.append(EvaluationParticipantContext(evaluation_id, away, home))
        selection = CurrentEvaluationSelection.create(
            candidate_evaluation_ids=tuple(item.evaluation_id for item in evaluations),
            current_evaluations=tuple(evaluations), superseded_evaluation_ids=(),
            selected_outcome_observation_ids=tuple(item.outcome_observation_id for item in evaluations),
        )
        return create_forecast_intelligence_report(
            selection, tuple(contexts), provider_id="dratings", model_ids=("dratings-mlb",),
            model_version_ids=("dratings-mlb-undisclosed",), sport="baseball", competition="MLB",
            proposition_type="winner", eligibility_policy_id="mlb-winner-evaluation-eligibility",
            eligibility_policy_version="1", evaluation_window=self.report.evaluation_window,
            adequacy_rule=AdequacyRule("boundary-adequacy", "1", 1, 1), generated_at=GENERATED,
        )

    def _outcome_history_for_event(self, event_id, evaluations):
        observations = []
        ordered = sorted(evaluations, key=lambda item: (item.evaluation_id == "evaluation:corrected", item.outcome_observation_id))
        for index, evaluation in enumerate(ordered):
            participants = tuple(key for key, _ in evaluation.probability_distribution)
            winner = evaluation.realized_winning_participant_id
            loser = next(item for item in participants if item != winner)
            observations.append(OutcomeObservation(
                evaluation.outcome_observation_id, event_id, "mlb-stats-api", event_id,
                OutcomeStatus.FINAL, "Final", participants[0], participants[1],
                evaluation.forecast_collected_at + timedelta(hours=4), GENERATED + timedelta(hours=index),
                "a" * 64, f"{index + 1:064x}", "fixture://outcome", "fixture-v1", ValidationStatus.VALID,
                1, 0, winner, loser, False, False, 9,
            ))
        return OutcomeHistory(event_id, "mlb-stats-api", tuple(observations))

    def test_forecast_quality_finite_infinite_directional_and_distribution(self):
        quality = self.report.forecast_quality
        self.assertEqual(quality.sample_size, 3)
        self.assertEqual(quality.mean_brier_score, Decimal("0.4166666666666666666666666667"))
        self.assertEqual((quality.finite_log_loss_count, quality.infinite_log_loss_count), (2, 1))
        self.assertEqual((quality.unique_favorite_count, quality.directional_correct_count, quality.directional_incorrect_count), (3, 2, 1))
        self.assertEqual(quality.no_unique_favorite_count, 0)
        self.assertEqual(quality.directional_accuracy_denominator, 3)
        self.assertEqual(quality.directional_accuracy, Decimal(2) / 3)
        self.assertEqual(quality.included_evaluation_ids, self.report.included_evaluation_ids)
        self.assertEqual(len(quality.finite_log_loss_evaluation_ids), quality.finite_log_loss_count)
        self.assertEqual(len(quality.infinite_log_loss_evaluation_ids), quality.infinite_log_loss_count)
        self.assertEqual(len(quality.unique_favorite_evaluation_ids), quality.unique_favorite_count)
        self.assertEqual(sum(count for _, count in quality.probability_distribution), 6)

    def test_calibration_buckets_are_complete_deterministic_and_sample_labeled(self):
        self.assertEqual(len(self.report.calibration), 10)
        self.assertEqual(sum(item.forecast_count for item in self.report.calibration), 3)
        self.assertEqual(sum(item.home_win_count for item in self.report.calibration), 2)
        self.assertEqual(self.report.calibration[0].lower_bound, Decimal("0"))
        self.assertTrue(self.report.calibration[-1].upper_inclusive)
        self.assertTrue(all(item.target == "home-participant-wins" for item in self.report.calibration))
        self.assertEqual(
            set().union(*(set(item.included_evaluation_ids) for item in self.report.calibration)),
            set(self.report.included_evaluation_ids),
        )
        populated = tuple(item for item in self.report.calibration if item.sample_size)
        self.assertIn(Decimal(0), {item.observed_win_frequency for item in populated})
        self.assertIn(Decimal(1), {item.observed_win_frequency for item in populated})
        self.assertTrue(any(item.sample_size == 0 and item.limitations for item in self.report.calibration))
        self.assertEqual(self.report.calibration, self.rerun_report().calibration)

    def test_fixed_home_win_calibration_boundary_and_outcome_semantics(self):
        report = self._report_for_probabilities(((Decimal("0"), 0), (Decimal("0.1"), 1), (Decimal("0.5"), 0), (Decimal("0.9"), 1), (Decimal("1"), 1)))
        populated = {item.lower_bound: item for item in report.calibration if item.sample_size}
        self.assertEqual(set(populated), {Decimal("0"), Decimal("0.1"), Decimal("0.5"), Decimal("0.9")})
        self.assertEqual(populated[Decimal("0.9")].sample_size, 2)
        self.assertEqual(sum(item.sample_size for item in report.calibration), 5)
        self.assertEqual(populated[Decimal("0.5")].observed_win_frequency, Decimal(0))
        self.assertEqual(populated[Decimal("0.1")].observed_win_frequency, Decimal(1))
        self.assertEqual(populated[Decimal("0.9")].inclusion_rule, "lower-inclusive-upper-inclusive")

    def test_directional_accuracy_excludes_probability_ties(self):
        report = self._report_for_probabilities(((Decimal("0.5"), 1), (Decimal("0.7"), 1), (Decimal("0.8"), 0)))
        quality = report.forecast_quality
        self.assertEqual(quality.sample_size, 3)
        self.assertEqual(quality.unique_favorite_count, 2)
        self.assertEqual((quality.directional_correct_count, quality.directional_incorrect_count), (1, 1))
        self.assertEqual(quality.no_unique_favorite_count, 1)
        self.assertEqual(quality.directional_accuracy_denominator, 2)
        self.assertEqual(quality.directional_accuracy, Decimal("0.5"))
        tie_segment = next(item for item in report.segments if item.dimension == "favorite-result" and item.value == "no-unique-favorite")
        self.assertEqual(tie_segment.sample_size, 1)
        self.assertIsNone(tie_segment.mean_predicted_probability)
        self.assertIsNone(tie_segment.observed_win_frequency)
        ties_only = self._report_for_probabilities(((Decimal("0.5"), 1),))
        self.assertIsNone(ties_only.forecast_quality.directional_accuracy)
        self.assertEqual(ties_only.forecast_quality.directional_accuracy_denominator, 0)

    def test_segment_contracts_are_unambiguous_and_reconcile(self):
        segments = {(item.dimension, item.value): item for item in self.report.segments}
        self.assertEqual(segments[("actual-result", "actual-home-win")].sample_size, 2)
        self.assertEqual(segments[("actual-result", "actual-away-win")].sample_size, 1)
        self.assertEqual(segments[("favorite-result", "favorite-win")].sample_size, 2)
        self.assertEqual(segments[("favorite-result", "favorite-loss")].sample_size, 1)
        self.assertEqual(segments[("favorite-result", "no-unique-favorite")].sample_size, 0)
        self.assertEqual(len([item for item in self.report.segments if item.dimension == "home-win-probability-bucket"]), 10)
        for family in ("actual-result", "favorite-result", "home-win-probability-bucket"):
            family_segments = tuple(item for item in self.report.segments if item.dimension == family)
            self.assertEqual(sum(item.sample_size for item in family_segments), 3)
            self.assertEqual(set().union(*(set(item.included_evaluation_ids) for item in family_segments)), set(self.report.included_evaluation_ids))
        self.assertTrue(all(item.observation_unit == "one-current-included-forecast-evaluation" for item in self.report.segments))
        self.assertTrue(all(item.limitations for item in self.report.segments if item.sample_size < 2))

    def test_historical_trend_uses_explicit_window_without_running_totals(self):
        self.assertEqual(len(self.report.historical_trend), 3)
        self.assertEqual(self.report.historical_trend[0][1], "2026-08-01")
        self.assertEqual({item[0] for item in self.report.historical_trend}, set(self.report.included_evaluation_ids))
        changed_window = replace(self.report.evaluation_window, end_at=datetime(2026, 8, 3, tzinfo=timezone.utc))
        narrowed = create_forecast_intelligence_report(
            self.selection, self._contexts_from_report_fixture(), provider_id=self.report.provider_id,
            model_ids=self.report.model_ids, model_version_ids=self.report.model_version_ids, sport=self.report.sport,
            competition=self.report.competition, proposition_type=self.report.proposition_type,
            eligibility_policy_id=self.report.eligibility_policy_id, eligibility_policy_version=self.report.eligibility_policy_version,
            evaluation_window=changed_window, adequacy_rule=AdequacyRule("fixture-descriptive-adequacy", "1", 4, 2), generated_at=GENERATED,
        )
        self.assertNotEqual(narrowed.report_id, self.report.report_id)
        self.assertEqual(narrowed.coverage.included_count, 2)

    def test_sample_adequacy_is_explicit_versioned_and_descriptive(self):
        self.assertEqual(self.report.sample_adequacy.rule_id, "fixture-descriptive-adequacy")
        self.assertEqual(self.report.sample_adequacy.rule_version, "1")
        self.assertEqual(self.report.sample_adequacy.label, "descriptive-only")
        self.assertTrue(self.report.sample_adequacy.limitations)
        self.assertEqual(self.report.sample_adequacy.included_evaluation_ids, self.report.included_evaluation_ids)

    def test_policy_hypothesis_is_deterministic_immutable_serializable_and_non_executable(self):
        _, _, repeated, _ = load_fixture(FIXTURE)
        self.assertEqual(repeated.hypothesis_id, self.hypothesis.hypothesis_id)
        self.assertEqual(PolicyHypothesis.from_json(self.hypothesis.to_json()), self.hypothesis)
        self.assertEqual(self.hypothesis.weights, (ProviderWeight("dratings", Decimal("1.0")),))
        self.assertEqual(self.hypothesis.normalization_rule, "identity")
        self.assertTrue(self.hypothesis.assumptions)
        self.assertFalse(hasattr(self.hypothesis, "activate"))
        with self.assertRaises(FrozenInstanceError):
            self.hypothesis.version = "2"

    def test_hypothesis_rejects_weight_for_unconstrained_provider(self):
        with self.assertRaises(ContractError):
            PolicyHypothesis.create(
                version="1", provider_constraints=(ProviderConstraint("dratings", (), ()),), eligibility_rules=("valid",),
                provider_selection_rules=("select",), weights=(ProviderWeight("other", Decimal("1")),), transformations=(),
                normalization_rule="identity", missing_provider_behavior="unavailable", fallback_behavior="none",
                sport="baseball", competition="MLB", proposition_type="winner",
            )

    def test_policy_proposal_links_report_hypothesis_metrics_benchmarks_and_provenance(self):
        self.assertEqual(self.proposal.report_id, self.report.report_id)
        self.assertEqual(self.proposal.hypothesis_id, self.hypothesis.hypothesis_id)
        self.assertEqual(self.proposal.included_evaluation_ids, self.report.included_evaluation_ids)
        self.assertTrue(self.proposal.quantitative_metrics)
        self.assertFalse(self.proposal.benchmark_ids)
        self.assertFalse(self.proposal.benchmark_comparisons)
        self.assertFalse(self.proposal.benchmark_available)
        self.assertIn("benchmark-absent", self.proposal.triggered_reason_codes)
        self.assertEqual(self.proposal.suggestion_evaluation_ids, self.report.included_evaluation_ids)
        self.assertTrue(self.proposal.analytical_limitations)
        self.assertEqual(self.proposal.sample_adequacy_label, "descriptive-only")

    def test_proposal_identity_ignores_generation_time_and_remains_advisory(self):
        later = PolicyProposal.create(
            self.report, self.hypothesis, version="1",
            proposal_rule=ProposalSuggestionRule(self.proposal.proposal_rule_id, self.proposal.proposal_rule_version),
            benchmark_ids=self.proposal.benchmark_ids, benchmark_comparisons=self.proposal.benchmark_comparisons,
            uncertainty=self.proposal.uncertainty, generated_at=GENERATED + timedelta(days=2),
        )
        self.assertEqual(later.proposal_id, self.proposal.proposal_id)
        self.assertNotEqual(later.generated_at, self.proposal.generated_at)
        self.assertTrue(self.proposal.advisory_only)
        self.assertFalse(self.proposal.executable)
        self.assertFalse(hasattr(self.proposal, "activate"))
        self.assertEqual(PolicyProposal.from_json(self.proposal.to_json()), self.proposal)

    def test_proposal_action_is_rule_derived_and_benchmark_absence_is_factual(self):
        self.assertEqual(self.proposal.suggested_action, SuggestedGovernanceAction.CONTINUE_RESEARCH)
        self.assertEqual(self.proposal.proposal_rule_id, "initial-research-governance-suggestion")
        repeated = PolicyProposal.create(
            self.report, self.hypothesis, version="1",
            proposal_rule=ProposalSuggestionRule("initial-research-governance-suggestion", "1"),
            benchmark_ids=(), benchmark_comparisons=(), uncertainty=self.proposal.uncertainty,
            generated_at=GENERATED + timedelta(days=10),
        )
        self.assertEqual(repeated.proposal_id, self.proposal.proposal_id)
        self.assertEqual(repeated.triggered_reason_codes, self.proposal.triggered_reason_codes)

    def test_all_suggested_actions_are_advisory_enum_values(self):
        self.assertEqual({item.value for item in SuggestedGovernanceAction}, {"continue-research", "future-shadow", "retain-incumbent", "consider-production-adoption", "reject"})

    def test_inspection_reports_factual_pipeline_counts(self):
        lines = run(FIXTURE)
        self.assertIn("Candidate Forecast Evaluations: 5", lines)
        self.assertIn("Current Forecast Evaluations: 4", lines)
        self.assertIn("Superseded Forecast Evaluations: 1", lines)
        self.assertIn("Included Forecast Evaluations: 3", lines)
        self.assertIn("Excluded Forecast Evaluations: 1", lines)
        self.assertIn("Calibration buckets: 10", lines)
        self.assertIn("Sample adequacy: descriptive-only", lines)
        self.assertIn("Advisory only: yes", lines)
        self.assertIn("Benchmark available: no", lines)


if __name__ == "__main__":
    unittest.main()
