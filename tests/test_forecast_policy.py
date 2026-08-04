import json
import inspect
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from event_contracts import ContractError
from forecast_contracts import ForecastDistribution, ForecastValidationStatus, ProviderDisposition
from forecast_intelligence import PolicyHypothesis, ProviderConstraint, ProviderWeight
from forecast_policy import (
    ConstraintMode,
    EligibilityOutcome,
    ExecutionReasonCode,
    ForecastPolicyEventContext,
    ForecastPolicyExecution,
    ForecastPolicy,
    ForecastPolicyBatchResult,
    PolicyForecast,
    PolicyProviderWeight,
    ProviderModelConstraint,
    RuleComponentSpec,
    StageStatus,
    create_dratings_mlb_winner_policy,
    derive_forecast_policy_execution_identity,
    execute_forecast_policy,
)
from inspect_forecast_policy import load_fixture, run


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_policy_cases.json"


class ForecastPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.scope, self.observations, self.contexts, self.result = load_fixture(FIXTURE)

    def _execute(self, observations=None, contexts=None):
        return execute_forecast_policy(
            self.policy, self.scope,
            self.observations if observations is None else observations,
            self.contexts if contexts is None else contexts,
        )

    def _recreate_policy(self, **changes):
        values = dict(
            policy_version=self.policy.policy_version, sport=self.policy.sport,
            competition=self.policy.competition, proposition_type=self.policy.proposition_type,
            provider_constraints=self.policy.provider_constraints,
            provider_weights=self.policy.provider_weights,
            input_compatibility_rule=self.policy.input_compatibility_rule,
            observation_eligibility_rule=self.policy.observation_eligibility_rule,
            observation_selection_rule=self.policy.observation_selection_rule,
            provider_selection_rule=self.policy.provider_selection_rule,
            transformation_rule=self.policy.transformation_rule,
            weighting_rule=self.policy.weighting_rule,
            normalization_rule=self.policy.normalization_rule,
            missing_provider_rule=self.policy.missing_provider_rule,
            fallback_rule=self.policy.fallback_rule,
            output_validation_rule=self.policy.output_validation_rule,
            implementation_version=self.policy.implementation_version,
            limitations=self.policy.limitations,
        )
        values.update(changes)
        return ForecastPolicy.create(**values)

    def _recreate_context(self, context, **changes):
        values = dict(
            context_version=context.context_version,
            canonical_event_id=context.canonical_event_id,
            sport=context.sport,
            competition=context.competition,
            proposition_type=context.proposition_type,
            model_id=context.model_id,
            scheduled_start=context.scheduled_start,
            away_participant_id=context.away_participant_id,
            home_participant_id=context.home_participant_id,
            away_outcome_id=context.away_outcome_id,
            home_outcome_id=context.home_outcome_id,
            source_object_ids=context.source_object_ids,
            limitations=context.limitations,
        )
        values.update(changes)
        return ForecastPolicyEventContext.create(**values)

    def test_policy_is_immutable_deterministic_serializable_and_governance_free(self):
        repeated = create_dratings_mlb_winner_policy()
        self.assertEqual(repeated.policy_id, self.policy.policy_id)
        self.assertEqual(ForecastPolicy.from_json(self.policy.to_json()), self.policy)
        forbidden = {"approved", "active", "shadow", "retired", "rejected", "product_owner", "effective_at"}
        self.assertTrue(forbidden.isdisjoint(self.policy.__dataclass_fields__))
        with self.assertRaises(FrozenInstanceError):
            self.policy.policy_version = "2"
        payload = self.policy.to_dict()
        payload["sport"] = "soccer"
        with self.assertRaises(ContractError):
            ForecastPolicy.from_dict(payload)

    def test_material_component_change_changes_policy_identity(self):
        changed = self._recreate_policy(
            transformation_rule=RuleComponentSpec(
                "identity-probability-transformation", "1", (("mode", "identity"),)
            )
        )
        self.assertNotEqual(changed.policy_id, self.policy.policy_id)

    def test_unknown_component_and_invalid_weights_fail_closed(self):
        with self.assertRaises(ContractError):
            self._recreate_policy(transformation_rule=RuleComponentSpec("unknown-transform", "1"))
        with self.assertRaises(ContractError):
            self._recreate_policy(provider_weights=(PolicyProviderWeight("dratings", Decimal("0.9")),))
        with self.assertRaises(ContractError):
            PolicyProviderWeight("dratings", Decimal("-0.1"))

    def test_policy_hypothesis_remains_a_distinct_non_executable_contract(self):
        hypothesis = PolicyHypothesis.create(
            version="1", provider_constraints=(ProviderConstraint("dratings", ("dratings-mlb",), ("dratings-mlb-undisclosed",)),),
            eligibility_rules=("pregame",), provider_selection_rules=("latest",),
            weights=(ProviderWeight("dratings", Decimal("1")),), transformations=("identity",),
            normalization_rule="identity", missing_provider_behavior="unavailable",
            fallback_behavior="none", sport="baseball", competition="MLB", proposition_type="winner",
        )
        self.assertNotIsInstance(hypothesis, ForecastPolicy)
        self.assertNotEqual(hypothesis.hypothesis_id, self.policy.policy_id)

    def test_exact_model_and_version_constraints_are_explicit(self):
        constraint = self.policy.provider_constraints[0]
        self.assertEqual(constraint.mode, ConstraintMode.EXACT)
        self.assertEqual(constraint.model_ids, ("dratings-mlb",))
        self.assertEqual(constraint.version_ids, ("dratings-mlb-undisclosed",))

    def test_eligibility_outcomes_and_structured_reasons(self):
        decisions = {item.observation_id: item for item in self.result.execution.eligibility_decisions}
        self.assertEqual(decisions["forecast:policy-1-latest"].outcome, EligibilityOutcome.ELIGIBLE)
        self.assertIn(ExecutionReasonCode.AT_OR_AFTER_EVENT_START, decisions["forecast:at-start"].reason_codes)
        self.assertIn(ExecutionReasonCode.AT_OR_AFTER_EVENT_START, decisions["forecast:after-start"].reason_codes)
        self.assertIn(ExecutionReasonCode.ANALYSIS_AS_OF_EXCEEDED, decisions["forecast:after-as-of"].reason_codes)
        self.assertIn(ExecutionReasonCode.OBSERVATION_INVALID, decisions["forecast:invalid"].reason_codes)
        self.assertIn(ExecutionReasonCode.PROPOSITION_MISMATCH, decisions["forecast:proposition"].reason_codes)
        self.assertIn(ExecutionReasonCode.MODEL_MISMATCH, decisions["forecast:model"].reason_codes)
        self.assertIn(ExecutionReasonCode.PROVIDER_MISMATCH, decisions["forecast:provider"].reason_codes)
        self.assertIn(ExecutionReasonCode.DISTRIBUTION_INCOMPLETE, decisions["forecast:incomplete"].reason_codes)
        self.assertTrue(all(item.rule_id == "validated-strictly-pregame-eligibility" for item in decisions.values()))

    def test_missing_chronology_is_indeterminate(self):
        target = next(item for item in self.contexts if item.canonical_event_id == "mlb:policy-2")
        changed = self._recreate_context(target, scheduled_start=None)
        contexts = tuple(changed if item == target else item for item in self.contexts)
        result = self._execute(contexts=contexts)
        decision = next(item for item in result.execution.eligibility_decisions if item.observation_id == "forecast:policy-2")
        self.assertEqual(decision.outcome, EligibilityOutcome.INDETERMINATE)
        self.assertIn(ExecutionReasonCode.MISSING_CHRONOLOGY, decision.reason_codes)

    def test_version_and_event_mismatch_are_structured(self):
        observation = next(item for item in self.observations if item.observation_id == "forecast:policy-2")
        observations = tuple(replace(item, version_id="unexpected-version") if item == observation else item for item in self.observations)
        result = self._execute(observations=observations)
        decision = next(item for item in result.execution.eligibility_decisions if item.observation_id == observation.observation_id)
        self.assertIn(ExecutionReasonCode.VERSION_MISMATCH, decision.reason_codes)
        context = next(item for item in self.contexts if item.canonical_event_id == "mlb:policy-2")
        changed_context = self._recreate_context(context, canonical_event_id="mlb:other")
        contexts = tuple(changed_context if item == context else item for item in self.contexts)
        result = self._execute(contexts=contexts)
        decision = next(item for item in result.execution.eligibility_decisions if item.observation_id == observation.observation_id)
        self.assertIn(ExecutionReasonCode.MISSING_EVENT_CONTEXT, decision.reason_codes)

    def test_withdrawn_provider_observation_is_ineligible(self):
        observation = next(item for item in self.observations if item.observation_id == "forecast:policy-2")
        observations = tuple(replace(item, provider_disposition=ProviderDisposition.WITHDRAWN) if item == observation else item for item in self.observations)
        result = self._execute(observations=observations)
        decision = next(item for item in result.execution.eligibility_decisions if item.observation_id == observation.observation_id)
        self.assertIn(ExecutionReasonCode.PROVIDER_DISPOSITION_UNSUPPORTED, decision.reason_codes)
        self.assertIn("mlb:policy-2", result.execution.unresolved_event_ids)

    def test_latest_selection_and_earlier_exclusion(self):
        forecast = next(item for item in self.result.policy_forecasts if item.canonical_event_id == "mlb:policy-1")
        self.assertEqual(forecast.included_observation_ids, ("forecast:policy-1-latest",))
        excluded = {item.observation_id: item.reason_codes for item in forecast.excluded_observations}
        self.assertEqual(excluded["forecast:policy-1-early"], (ExecutionReasonCode.NOT_SELECTED_LATEST,))

    def test_tied_latest_observations_fail_closed(self):
        self.assertIn("mlb:tied", self.result.execution.unresolved_event_ids)
        reasons = dict(self.result.execution.unresolved_event_reasons)["mlb:tied"]
        self.assertIn(ExecutionReasonCode.LATEST_OBSERVATION_AMBIGUOUS, reasons)
        self.assertNotIn("mlb:tied", {item.canonical_event_id for item in self.result.policy_forecasts})

    def test_input_order_is_semantically_irrelevant(self):
        repeated = self._execute(
            tuple(reversed(self.observations)), tuple(reversed(self.contexts)),
        )
        self.assertEqual(repeated.execution.execution_id, self.result.execution.execution_id)
        self.assertEqual(repeated.execution, self.result.execution)
        self.assertEqual(repeated.policy_forecasts, self.result.policy_forecasts)

    def test_wall_clock_time_is_absent_from_canonical_contracts(self):
        self.assertNotIn("generated_at", ForecastPolicyExecution.__dataclass_fields__)
        self.assertNotIn("generated_at", PolicyForecast.__dataclass_fields__)
        repeated = self._execute()
        self.assertEqual(repeated.to_json(), self.result.to_json())
        self.assertNotIn("generated_at", inspect.signature(execute_forecast_policy).parameters)

    def test_material_analysis_as_of_changes_execution_identity(self):
        earlier_scope = replace(self.scope, analysis_as_of=self.scope.analysis_as_of - timedelta(hours=1))
        changed = execute_forecast_policy(self.policy, earlier_scope, self.observations, self.contexts)
        self.assertNotEqual(changed.execution.execution_id, self.result.execution.execution_id)

    def test_batch_accounting_multiple_events_and_mixed_results(self):
        stats = self.result.execution.statistics
        self.assertEqual((stats.event_count, stats.policy_forecast_count, stats.unresolved_event_count), (12, 2, 10))
        self.assertEqual(stats.candidate_observation_count, 13)
        self.assertEqual(stats.included_observation_count, 2)
        self.assertEqual(stats.included_observation_count + stats.excluded_observation_count, stats.candidate_observation_count)
        self.assertEqual(set(self.result.execution.event_ids), set(self.scope.event_ids))
        self.assertEqual(len(self.result.execution.policy_forecast_ids), len(self.result.policy_forecasts))

    def test_policy_forecast_exact_distribution_and_provenance(self):
        forecast = next(item for item in self.result.policy_forecasts if item.canonical_event_id == "mlb:policy-1")
        output = {semantic: value for _, semantic, value in forecast.output_distribution}
        self.assertEqual(output, {"away-win": Decimal("0.400"), "home-win": Decimal("0.600")})
        self.assertEqual(forecast.total_probability, Decimal(1))
        self.assertEqual(forecast.execution_id, self.result.execution.execution_id)
        self.assertEqual(forecast.policy_id, self.policy.policy_id)
        self.assertEqual(forecast.validation_status, ForecastValidationStatus.VALID)
        self.assertEqual(forecast.arithmetic_precision, "exact-decimal")
        self.assertEqual(PolicyForecast.from_json(forecast.to_json()), forecast)

    def test_stage_decisions_preserve_identity_weight_and_no_fallback(self):
        forecast = self.result.policy_forecasts[0]
        stages = {item.stage_id: item for item in forecast.stage_decisions}
        self.assertEqual(stages["transformation"].input_probabilities, stages["transformation"].output_probabilities)
        self.assertEqual(stages["weighting"].applied_weights, (("dratings", Decimal("1.0")),))
        self.assertEqual(stages["fallback"].status, StageStatus.NOT_INVOKED)
        self.assertEqual(stages["normalization"].input_probabilities, stages["normalization"].output_probabilities)

    def test_policy_forecast_has_no_market_wager_or_governance_fields(self):
        forbidden = {"market", "price", "expected_value", "kelly", "bankroll", "position", "wager", "order", "active", "approved", "shadow"}
        self.assertTrue(forbidden.isdisjoint(PolicyForecast.__dataclass_fields__))

    def test_distinct_policies_produce_coexisting_non_authoritative_forecasts(self):
        other_policy = self._recreate_policy(limitations=self.policy.limitations + ("comparison policy",))
        other = execute_forecast_policy(other_policy, self.scope, self.observations, self.contexts)
        first = next(item for item in self.result.policy_forecasts if item.canonical_event_id == "mlb:policy-1")
        second = next(item for item in other.policy_forecasts if item.canonical_event_id == "mlb:policy-1")
        self.assertNotEqual(first.policy_id, second.policy_id)
        self.assertNotEqual(first.execution_id, second.execution_id)
        self.assertNotEqual(first.policy_forecast_id, second.policy_forecast_id)
        self.assertEqual(first.canonical_event_id, second.canonical_event_id)
        forbidden = {"active", "approved", "shadow", "retired", "rejected", "production_authority"}
        self.assertTrue(forbidden.isdisjoint(first.to_dict()))
        self.assertTrue(forbidden.isdisjoint(second.to_dict()))

    def test_execution_identity_is_derived_before_outputs_and_is_output_order_independent(self):
        execution_id, digest = derive_forecast_policy_execution_identity(
            self.policy, self.scope, self.observations, self.contexts,
        )
        self.assertEqual(execution_id, self.result.execution.execution_id)
        self.assertEqual(digest, self.result.execution.input_digest)
        self.assertTrue(all(item.execution_id == execution_id for item in self.result.policy_forecasts))
        completed_reordered = replace(
            self.result.execution,
            policy_forecast_ids=tuple(reversed(self.result.execution.policy_forecast_ids)),
        )
        reordered = ForecastPolicyBatchResult(
            completed_reordered, tuple(reversed(self.result.policy_forecasts)),
        )
        self.assertEqual(reordered.execution.execution_id, execution_id)

    def test_material_candidate_change_changes_execution_identity(self):
        target = self.observations[0]
        changed_observations = tuple(
            replace(item, provider_updated_at=item.collected_at) if item == target else item
            for item in self.observations
        )
        changed = self._execute(observations=changed_observations)
        self.assertNotEqual(changed.execution.execution_id, self.result.execution.execution_id)

    def test_execution_forecast_reconciliation_rejects_missing_duplicate_and_foreign_ids(self):
        with self.assertRaises(ContractError):
            ForecastPolicyBatchResult(
                replace(self.result.execution, policy_forecast_ids=self.result.execution.policy_forecast_ids[:-1]),
                self.result.policy_forecasts,
            )
        with self.assertRaises(ContractError):
            replace(
                self.result.execution,
                policy_forecast_ids=(self.result.execution.policy_forecast_ids[0],) * 2,
            )
        with self.assertRaises(ContractError):
            replace(self.result.policy_forecasts[0], execution_id="forecast-policy-execution:foreign")

    def test_event_context_identity_round_trip_and_duplicate_identical_input(self):
        context = self.contexts[0]
        self.assertEqual(ForecastPolicyEventContext.from_json(context.to_json()), context)
        duplicate = self._execute(contexts=self.contexts + (context,))
        self.assertEqual(duplicate, self.result)

    def test_missing_and_conflicting_event_contexts_fail_closed(self):
        target = next(item for item in self.contexts if item.canonical_event_id == "mlb:policy-2")
        missing = self._execute(contexts=tuple(item for item in self.contexts if item != target))
        self.assertIn("mlb:policy-2", missing.execution.unresolved_event_ids)
        decision = next(item for item in missing.execution.eligibility_decisions if item.observation_id == "forecast:policy-2")
        self.assertIn(ExecutionReasonCode.MISSING_EVENT_CONTEXT, decision.reason_codes)

        conflicting = self._recreate_context(target, scheduled_start=target.scheduled_start + timedelta(minutes=1))
        conflict_result = self._execute(contexts=self.contexts + (conflicting,))
        self.assertIn("mlb:policy-2", conflict_result.execution.unresolved_event_ids)
        self.assertIn("mlb:policy-2", dict(conflict_result.execution.event_context_conflicts))
        decision = next(item for item in conflict_result.execution.eligibility_decisions if item.observation_id == "forecast:policy-2")
        self.assertIn(ExecutionReasonCode.EVENT_CONTEXT_CONFLICT, decision.reason_codes)

    def test_context_orientation_and_material_changes_are_identifying(self):
        target = next(item for item in self.contexts if item.canonical_event_id == "mlb:policy-2")
        later = self._recreate_context(target, scheduled_start=target.scheduled_start + timedelta(minutes=1))
        later_result = self._execute(contexts=tuple(later if item == target else item for item in self.contexts))
        self.assertNotEqual(later_result.execution.execution_id, self.result.execution.execution_id)

        swapped = self._recreate_context(
            target,
            away_outcome_id=target.home_outcome_id,
            home_outcome_id=target.away_outcome_id,
        )
        swapped_result = self._execute(contexts=tuple(swapped if item == target else item for item in self.contexts))
        original_forecast = next(item for item in self.result.policy_forecasts if item.canonical_event_id == "mlb:policy-2")
        swapped_forecast = next(item for item in swapped_result.policy_forecasts if item.canonical_event_id == "mlb:policy-2")
        self.assertNotEqual(swapped_forecast.event_context_id, original_forecast.event_context_id)
        self.assertNotEqual(swapped_forecast.policy_forecast_id, original_forecast.policy_forecast_id)

        reversed_participants = self._recreate_context(
            target,
            away_participant_id=target.home_participant_id,
            home_participant_id=target.away_participant_id,
        )
        orientation_result = self._execute(
            contexts=tuple(reversed_participants if item == target else item for item in self.contexts)
        )
        decision = next(item for item in orientation_result.execution.eligibility_decisions if item.observation_id == "forecast:policy-2")
        self.assertIn(ExecutionReasonCode.PARTICIPANT_ORIENTATION_MISMATCH, decision.reason_codes)

    def test_reason_counts_are_overlapping_occurrences_not_a_partition(self):
        occurrence_total = sum(count for _, count in self.result.execution.exclusion_reason_counts)
        self.assertGreater(occurrence_total, self.result.execution.statistics.excluded_observation_count)
        lines = run(FIXTURE)
        self.assertTrue(any(line.startswith("Reason-code occurrences (observation and event level; overlapping):") for line in lines))

    def test_batch_result_is_immutable_and_serializable(self):
        self.assertEqual(ForecastPolicyBatchResult.from_json(self.result.to_json()), self.result)
        with self.assertRaises(FrozenInstanceError):
            self.result.execution.execution_id = "changed"

    def test_malformed_probability_and_incomplete_distribution_are_rejected(self):
        from inspect_forecast_policy import _observation
        specification = {
            "id": "forecast:bad-probability", "event_id": "mlb:bad",
            "collected_at": "2026-08-04T12:00:00+00:00", "start_at": "2026-08-04T20:00:00+00:00",
            "away": "1.2", "home": "-0.2",
        }
        with self.assertRaises(ContractError):
            _observation(specification)
        with self.assertRaises(ContractError):
            ForecastDistribution(())

    def test_execution_serialization_round_trip(self):
        from forecast_policy import ForecastPolicyExecution
        self.assertEqual(ForecastPolicyExecution.from_json(self.result.execution.to_json()), self.result.execution)

    def test_inspection_reports_factual_execution(self):
        lines = run(FIXTURE)
        expected = {
            "Candidate Forecast Observations: 13",
            "Eligible Forecast Observations: 5",
            "Ineligible Forecast Observations: 8",
            "Indeterminate Forecast Observations: 0",
            "Events considered: 12",
            "Policy Forecasts produced: 2",
            "Unresolved events: 10",
            "Fallback invocations: 0",
            "Governance authority: none",
        }
        self.assertTrue(expected.issubset(lines))

    def test_serialized_unknown_contract_and_enum_are_rejected(self):
        payload = json.loads(self.policy.to_json())
        payload["__type__"] = "UnknownForecastPolicy"
        with self.assertRaises(ContractError):
            ForecastPolicy.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
