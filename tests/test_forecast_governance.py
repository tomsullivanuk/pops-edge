import inspect
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from event_contracts import ContractError
from forecast_governance import (
    GOVERNANCE_ALGORITHM_VERSION,
    GovernanceDecision,
    GovernanceHistory,
    GovernanceReasonCode,
    GovernanceRecord,
    GovernanceScope,
    PolicyLifecycle,
    ProductOwnerIdentity,
    ResolutionStatus,
)
from forecast_policy import ForecastPolicy, create_dratings_mlb_winner_policy
from inspect_forecast_governance import load_fixture, run


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_governance_cases.json"


class ForecastGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.payload, self.policy_map, self.scopes, self.owner, self.history = load_fixture(FIXTURE)
        self.policies = tuple(self.policy_map.values())
        self.scope = self.scopes["mlb"]
        self.policy = self.policy_map["mlb-a"]
        self.start = datetime(2026, 8, 1, 8, tzinfo=timezone(timedelta(hours=-5)))

    def record(self, policy=None, decision=GovernanceDecision.RESEARCH, hours=0,
               scope=None, owner=None, rationale="Fixture governance decision",
               notes=(), proposal_ids=("policy-proposal:z", "policy-proposal:a")):
        policy = policy or self.policy
        return GovernanceRecord.create(
            policy=policy, scope=scope or self.scope, decision=decision,
            decision_effective_at=self.start + timedelta(hours=hours),
            product_owner=owner or self.owner, rationale=rationale,
            policy_proposal_ids=proposal_ids, notes=notes,
            policy_hypothesis_ids=("policy-hypothesis:b",),
        )

    def test_scope_is_deterministic_immutable_and_serializable(self):
        repeated = GovernanceScope.create(sport="baseball", competition="MLB", proposition_type="winner",
                                          limitations=tuple(reversed(self.scope.limitations)))
        self.assertEqual(repeated, self.scope)
        self.assertEqual(GovernanceScope.from_json(self.scope.to_json()), self.scope)
        with self.assertRaises(FrozenInstanceError):
            self.scope.sport = "soccer"

    def test_scope_material_change_changes_identity_and_scopes_are_independent(self):
        changed = GovernanceScope.create(sport="baseball", competition="MLB", proposition_type="total")
        self.assertNotEqual(changed.scope_id, self.scope.scope_id)
        at = datetime.fromisoformat("2026-08-01T12:30:00-05:00")
        self.assertEqual(self.history.production_policy(self.scopes["soccer"], self.policies, as_of=at).status, ResolutionStatus.RESOLVED)

    def test_record_is_deterministic_immutable_and_serializable(self):
        first = self.record()
        second = self.record()
        self.assertEqual(first, second)
        self.assertEqual(GovernanceRecord.from_json(first.to_json()), first)
        self.assertFalse({"lifecycle", "current_state", "previous_state", "generated_at"} & set(first.__dataclass_fields__))
        with self.assertRaises(FrozenInstanceError):
            first.decision = GovernanceDecision.SHADOW

    def test_record_material_changes_change_identity(self):
        first = self.record()
        self.assertNotEqual(first.record_id, self.record(hours=1).record_id)
        self.assertNotEqual(first.record_id, self.record(decision=GovernanceDecision.SHADOW).record_id)
        self.assertNotEqual(first.record_id, self.record(policy=self.policy_map["mlb-b"]).record_id)
        changed_scope = GovernanceScope.from_policy(self.policy, limitations=("changed",))
        self.assertNotEqual(first.record_id, self.record(scope=changed_scope).record_id)
        changed_owner = ProductOwnerIdentity("product-owner:other")
        self.assertNotEqual(first.record_id, self.record(owner=changed_owner).record_id)

    def test_product_owner_display_name_is_optional_nonmaterial_metadata(self):
        named = self.record(owner=ProductOwnerIdentity(self.owner.product_owner_id, "First Name"))
        renamed = self.record(owner=ProductOwnerIdentity(self.owner.product_owner_id, "Renamed Owner"))
        unnamed = self.record(owner=ProductOwnerIdentity(self.owner.product_owner_id))
        self.assertEqual(named.record_id, renamed.record_id)
        self.assertEqual(named.record_id, unnamed.record_id)
        self.assertEqual(named.input_digest, unnamed.input_digest)
        with self.assertRaises(ContractError):
            ProductOwnerIdentity("", None)

    def test_references_are_canonical_and_no_clock_default_exists(self):
        record = self.record()
        self.assertEqual(record.policy_proposal_ids, ("policy-proposal:a", "policy-proposal:z"))
        self.assertNotIn("generated_at", inspect.signature(GovernanceRecord.create).parameters)
        self.assertIs(inspect.signature(GovernanceRecord.create).parameters["decision_effective_at"].default, inspect.Parameter.empty)

    def test_malformed_reference_and_unsupported_decision_fail_closed(self):
        with self.assertRaises(ContractError):
            GovernanceRecord.create(
                policy=self.policy, scope=self.scope, decision=GovernanceDecision.RESEARCH,
                decision_effective_at=self.start, product_owner=self.owner, rationale="x",
                policy_proposal_ids=(" bad-reference",),
            )
        with self.assertRaises(ContractError) as caught:
            GovernanceRecord.create(
                policy=self.policy, scope=self.scope, decision="research",
                decision_effective_at=self.start, product_owner=self.owner, rationale="x",
            )
        self.assertEqual(caught.exception.code, GovernanceReasonCode.UNSUPPORTED_DECISION)

    def test_missing_owner_naive_time_and_scope_mismatch_fail_closed(self):
        with self.assertRaises(ContractError) as missing_owner:
            GovernanceRecord.create(policy=self.policy, scope=self.scope, decision=GovernanceDecision.RESEARCH,
                                    decision_effective_at=self.start, product_owner=None, rationale="x")
        self.assertEqual(missing_owner.exception.code, GovernanceReasonCode.MISSING_PRODUCT_OWNER)
        with self.assertRaises(ContractError) as missing_time:
            GovernanceRecord.create(policy=self.policy, scope=self.scope, decision=GovernanceDecision.RESEARCH,
                                    decision_effective_at=None, product_owner=self.owner, rationale="x")
        self.assertEqual(missing_time.exception.code, GovernanceReasonCode.MISSING_DECISION_EFFECTIVE_AT)
        with self.assertRaises(ContractError):
            GovernanceRecord.create(policy=self.policy, scope=self.scope, decision=GovernanceDecision.RESEARCH,
                                    decision_effective_at=datetime(2026, 8, 1), product_owner=self.owner, rationale="x")
        with self.assertRaises(ContractError):
            GovernanceRecord.create(policy=self.policy_map["soccer-a"], scope=self.scope, decision=GovernanceDecision.RESEARCH,
                                    decision_effective_at=self.start, product_owner=self.owner, rationale="x")

    def test_history_is_append_only_order_invariant_and_serializable(self):
        records = [self.record(hours=2), self.record(hours=1)]
        original = tuple(records)
        history = GovernanceHistory(records)
        appended = history.append(self.record(hours=3))
        self.assertEqual(tuple(records), original)
        self.assertEqual(len(history.records), 2)
        self.assertEqual(len(appended.records), 3)
        self.assertEqual(history, GovernanceHistory(tuple(reversed(records))))
        self.assertEqual(GovernanceHistory.from_json(history.to_json()), history)
        with self.assertRaises(FrozenInstanceError):
            history.records = ()

    def test_duplicate_record_rejected(self):
        record = self.record()
        with self.assertRaises(ContractError) as caught:
            GovernanceHistory((record, record))
        self.assertEqual(caught.exception.code, GovernanceReasonCode.DUPLICATE_GOVERNANCE_RECORD)

    def test_same_record_id_with_different_contents_is_rejected(self):
        record = self.record()
        hostile = object.__new__(GovernanceRecord)
        for field_name in record.__dataclass_fields__:
            object.__setattr__(hostile, field_name, getattr(record, field_name))
        object.__setattr__(hostile, "rationale", "Different hostile contents")
        with self.assertRaises(ContractError) as caught:
            GovernanceHistory((record, hostile))
        self.assertEqual(caught.exception.code, GovernanceReasonCode.DUPLICATE_GOVERNANCE_RECORD)

    def test_lifecycle_replay_and_historical_boundary(self):
        expected = {
            "2026-08-01T09:30:00-05:00": PolicyLifecycle.RESEARCH,
            "2026-08-01T10:30:00-05:00": PolicyLifecycle.SHADOW,
            "2026-08-01T12:30:00-05:00": PolicyLifecycle.PRODUCTION,
        }
        for raw, lifecycle in expected.items():
            result = self.history.policy_lifecycle(self.policy, self.scope, self.policies, as_of=datetime.fromisoformat(raw))
            self.assertEqual((result.status, result.lifecycle), (ResolutionStatus.RESOLVED, lifecycle))

    def test_no_decision_returns_none_and_future_is_excluded(self):
        result = self.history.policy_lifecycle(self.policy, self.scope, self.policies,
                                               as_of=datetime.fromisoformat("2026-08-01T08:00:00-05:00"))
        self.assertEqual(result.status, ResolutionStatus.NONE)

    def test_research_shadow_retired_and_rejected_views(self):
        at = datetime.fromisoformat("2026-08-01T14:30:00-05:00")
        self.assertEqual(len(self.history.shadow_policies(self.scope, self.policies, as_of=at)), 1)
        self.assertEqual(len(self.history.research_policies(self.scope, self.policies, as_of=at)), 0)
        self.assertEqual(len(self.history.retired_policies(self.scope, self.policies, as_of=at)), 1)
        self.assertEqual(len(self.history.rejected_policies(self.scope, self.policies, as_of=at)), 1)

    def test_production_displacement_retirement_and_no_restoration(self):
        before = self.history.production_policy(self.scope, self.policies, as_of=datetime.fromisoformat("2026-08-01T11:45:00-05:00"))
        displaced = self.history.production_policy(self.scope, self.policies, as_of=datetime.fromisoformat("2026-08-01T12:30:00-05:00"))
        retired = self.history.production_policy(self.scope, self.policies, as_of=datetime.fromisoformat("2026-08-01T14:30:00-05:00"))
        self.assertEqual(before.policy_id, self.policy_map["mlb-a"].policy_id)
        self.assertEqual(displaced.policy_id, self.policy_map["mlb-b"].policy_id)
        self.assertEqual(retired.status, ResolutionStatus.NONE)
        self.assertEqual(displaced.supporting_record_id, next(item.record_id for item in self.history.records if item.policy_id == displaced.policy_id and item.decision is GovernanceDecision.PRODUCTION))

    def test_unrelated_shadow_does_not_disturb_authority(self):
        at = datetime.fromisoformat("2026-08-01T11:45:00-05:00")
        self.assertEqual(self.history.production_policy(self.scope, self.policies, as_of=at).policy_id, self.policy.policy_id)

    def test_current_demotions_remove_authority(self):
        for decision in (GovernanceDecision.RESEARCH, GovernanceDecision.SHADOW):
            history = GovernanceHistory((self.record(decision=GovernanceDecision.PRODUCTION), self.record(decision=decision, hours=1)))
            self.assertEqual(history.production_policy(self.scope, self.policies, as_of=self.start + timedelta(hours=2)).status, ResolutionStatus.NONE)

    def test_unknown_policy_is_structured_invalid(self):
        record = self.record(decision=GovernanceDecision.PRODUCTION)
        result = GovernanceHistory((record,)).production_policy(self.scope, tuple(item for item in self.policies if item.policy_id != self.policy.policy_id), as_of=self.start)
        self.assertEqual(result.status, ResolutionStatus.INVALID)
        self.assertIn(GovernanceReasonCode.UNKNOWN_FORECAST_POLICY, {item.reason_code for item in result.conflicts})

    def test_material_policy_conflict_fails_scope_closed_with_provenance(self):
        production = self.record(decision=GovernanceDecision.PRODUCTION)
        retire = self.record(decision=GovernanceDecision.RETIRE, hours=1)
        shadow = self.record(decision=GovernanceDecision.SHADOW, hours=1)
        result = GovernanceHistory((production, retire, shadow)).production_policy(
            self.scope, self.policies, as_of=self.start + timedelta(hours=2)
        )
        self.assertEqual(result.status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(result.policy_id)
        self.assertEqual(set(result.conflict_record_ids), {retire.record_id, shadow.record_id})
        self.assertIn(GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT, result.reason_codes)

    def test_unrelated_research_conflict_is_visible_without_erasing_authority(self):
        other = self.policy_map["mlb-c"]
        production = self.record(decision=GovernanceDecision.PRODUCTION)
        research = self.record(policy=other, decision=GovernanceDecision.RESEARCH, hours=1)
        shadow = self.record(policy=other, decision=GovernanceDecision.SHADOW, hours=1)
        result = GovernanceHistory((production, research, shadow)).production_policy(
            self.scope, self.policies, as_of=self.start + timedelta(hours=2)
        )
        self.assertEqual(result.status, ResolutionStatus.RESOLVED)
        self.assertEqual(result.policy_id, self.policy.policy_id)
        self.assertEqual(set(result.conflict_record_ids), {research.record_id, shadow.record_id})
        self.assertIn(GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT, result.reason_codes)

    def test_equivalent_same_time_decisions_preserve_all_support(self):
        first = self.record(decision=GovernanceDecision.PRODUCTION, rationale="First rationale")
        second = self.record(decision=GovernanceDecision.PRODUCTION, rationale="Second rationale",
                             notes=("additional note",), proposal_ids=("policy-proposal:other",))
        history = GovernanceHistory((second, first))
        lifecycle = history.policy_lifecycle(self.policy, self.scope, self.policies, as_of=self.start)
        resolution = history.production_policy(self.scope, self.policies, as_of=self.start)
        self.assertEqual(lifecycle.status, ResolutionStatus.RESOLVED)
        self.assertEqual(lifecycle.lifecycle, PolicyLifecycle.PRODUCTION)
        self.assertEqual(set(lifecycle.supporting_record_ids), {first.record_id, second.record_id})
        self.assertIsNone(lifecycle.supporting_record_id)
        self.assertEqual(resolution.status, ResolutionStatus.RESOLVED)
        self.assertEqual(set(resolution.supporting_record_ids), {first.record_id, second.record_id})
        self.assertFalse(resolution.conflicts)

    def test_resolution_provenance_is_complete(self):
        at = datetime.fromisoformat("2026-08-01T12:30:00-05:00")
        resolution = self.history.production_policy(self.scope, self.policies, as_of=at)
        self.assertEqual(resolution.scope_id, self.scope.scope_id)
        self.assertEqual(resolution.as_of, at)
        self.assertTrue(resolution.supporting_record_ids)
        self.assertEqual(set(resolution.considered_policy_ids), {
            policy.policy_id for policy in self.policies if self.scope.supports(policy)
        })
        self.assertTrue(resolution.considered_record_ids)
        self.assertTrue(resolution.limitations)

    def test_scope_mismatch_is_structured_invalid(self):
        policy = self.policy_map["soccer-a"]
        record = self.record(policy=policy, scope=self.scopes["soccer"])
        result = GovernanceHistory((record,)).policy_lifecycle(
            policy, self.scope, self.policies, as_of=self.start
        )
        self.assertEqual(result.status, ResolutionStatus.INVALID)
        self.assertIn(GovernanceReasonCode.GOVERNANCE_SCOPE_MISMATCH,
                      {item.reason_code for item in result.conflicts})

    def test_reject_is_terminal_with_diagnostic(self):
        records = (self.record(decision=GovernanceDecision.REJECT), self.record(decision=GovernanceDecision.RESEARCH, hours=1))
        result = GovernanceHistory(records).policy_lifecycle(self.policy, self.scope, self.policies, as_of=self.start + timedelta(hours=2))
        self.assertEqual(result.status, ResolutionStatus.INVALID)
        self.assertIn(GovernanceReasonCode.DECISION_AFTER_REJECT, {item.reason_code for item in result.conflicts})

    def test_same_time_policy_conflict_is_ambiguous(self):
        history = GovernanceHistory((self.record(decision=GovernanceDecision.RESEARCH), self.record(decision=GovernanceDecision.SHADOW)))
        result = history.policy_lifecycle(self.policy, self.scope, self.policies, as_of=self.start)
        self.assertEqual(result.status, ResolutionStatus.AMBIGUOUS)
        self.assertIn(GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT, {item.reason_code for item in result.conflicts})

    def test_simultaneous_production_conflict_is_ambiguous(self):
        history = GovernanceHistory((self.record(decision=GovernanceDecision.PRODUCTION),
                                     self.record(policy=self.policy_map["mlb-b"], decision=GovernanceDecision.PRODUCTION)))
        result = history.production_policy(self.scope, self.policies, as_of=self.start)
        self.assertEqual(result.status, ResolutionStatus.AMBIGUOUS)
        self.assertIn(GovernanceReasonCode.SIMULTANEOUS_PRODUCTION_CONFLICT, {item.reason_code for item in result.conflicts})

    def test_input_order_does_not_change_resolution(self):
        reversed_history = GovernanceHistory(tuple(reversed(self.history.records)))
        at = datetime.fromisoformat("2026-08-01T12:30:00-05:00")
        self.assertEqual(self.history.production_policy(self.scope, self.policies, as_of=at),
                         reversed_history.production_policy(self.scope, self.policies, as_of=at))

    def test_unsupported_versions_fail_closed(self):
        record = self.record()
        with self.assertRaises(ContractError) as caught:
            GovernanceRecord.from_dict({**record.to_dict(), "algorithm_version": "999"})
        self.assertEqual(caught.exception.code, GovernanceReasonCode.UNSUPPORTED_GOVERNANCE_VERSION)
        self.assertEqual(GOVERNANCE_ALGORITHM_VERSION, "1")

    def test_inspection_is_offline_factual_and_deterministic(self):
        first = run(FIXTURE)
        self.assertEqual(first, run(FIXTURE))
        for text in ("Governance Records loaded: 8", "Policies referenced: 5",
                     "Governance Scopes: 2", "Product Owner ID: product-owner:pops-edge-owner",
                     "governance authority derived:", "Shadow policy count:", "conflict reason counts:",
                     "Conflict fixtures requested: 8", "decision-after-reject",
                     "same-time-policy-decision-conflict", "simultaneous-production-conflict",
                     "Conflict scenario: equivalent-same-time-production",
                     "Conflict scenario: material-policy-conflict",
                     "Conflict scenario: unrelated-research-conflict",
                     "supporting Governance Record IDs:"):
            self.assertIn(text, first)

    def test_governance_does_not_modify_forecast_policy_contract(self):
        policy = create_dratings_mlb_winner_policy()
        self.assertFalse({"governance", "lifecycle", "active", "approved"} & set(policy.__dataclass_fields__))
        self.assertNotIn("governance", inspect.signature(ForecastPolicy.create).parameters)


if __name__ == "__main__":
    unittest.main()
