#!/usr/bin/env python3
"""Inspect deterministic fixture-only Forecast Policy governance replay."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from forecast_governance import (
    GovernanceDecision,
    GovernanceHistory,
    GovernanceRecord,
    GovernanceScope,
    ProductOwnerIdentity,
)
from forecast_policy import ForecastPolicy, create_dratings_mlb_winner_policy


def _variant(base: ForecastPolicy, version: str, *, sport: str | None = None,
             competition: str | None = None) -> ForecastPolicy:
    return ForecastPolicy.create(
        policy_version=version, sport=sport or base.sport,
        competition=competition or base.competition,
        proposition_type=base.proposition_type,
        provider_constraints=base.provider_constraints,
        provider_weights=base.provider_weights,
        input_compatibility_rule=base.input_compatibility_rule,
        observation_eligibility_rule=base.observation_eligibility_rule,
        observation_selection_rule=base.observation_selection_rule,
        provider_selection_rule=base.provider_selection_rule,
        transformation_rule=base.transformation_rule,
        weighting_rule=base.weighting_rule,
        normalization_rule=base.normalization_rule,
        missing_provider_rule=base.missing_provider_rule,
        fallback_rule=base.fallback_rule,
        output_validation_rule=base.output_validation_rule,
        implementation_version=base.implementation_version,
        limitations=base.limitations + (f"synthetic governance policy {version}",),
    )


def load_fixture(path: Path):
    payload = json.loads(path.read_text())
    base = create_dratings_mlb_winner_policy()
    policies = {
        "mlb-a": base,
        "mlb-b": _variant(base, "governance-b"),
        "mlb-c": _variant(base, "governance-c"),
        "mlb-d": _variant(base, "governance-d"),
        "soccer-a": _variant(base, "governance-soccer", sport="soccer", competition="FIFA World Cup"),
    }
    scopes = {
        "mlb": GovernanceScope.from_policy(policies["mlb-a"], limitations=tuple(payload["limitations"])),
        "soccer": GovernanceScope.from_policy(policies["soccer-a"], limitations=tuple(payload["limitations"])),
    }
    owner = ProductOwnerIdentity(**payload["product_owner"])
    records = []
    for key, decision, effective_at in payload["records"]:
        policy = policies[key]
        scope = scopes["soccer" if key.startswith("soccer") else "mlb"]
        records.append(GovernanceRecord.create(
            policy=policy, scope=scope, decision=GovernanceDecision(decision),
            decision_effective_at=datetime.fromisoformat(effective_at), product_owner=owner,
            rationale=f"Synthetic fixture decision for {key}",
            policy_proposal_ids=(f"policy-proposal:{key}",),
            forecast_intelligence_report_ids=("forecast-intelligence-report:fixture",),
            limitations=tuple(payload["limitations"]),
        ))
    return payload, policies, scopes, owner, GovernanceHistory(tuple(reversed(records)))


def run(path: Path) -> str:
    payload, policies, scopes, owner, history = load_fixture(path)
    lines = [
        f"Governance Records loaded: {len(history.records)}",
        f"Policies referenced: {len(policies)}",
        f"Governance Scopes: {len(scopes)}",
        f"Product Owner ID: {owner.product_owner_id}",
    ]
    all_policies = tuple(policies.values())
    for raw_as_of in payload["as_of_boundaries"]:
        as_of = datetime.fromisoformat(raw_as_of)
        lines.append(f"Replay as_of: {as_of.isoformat()}")
        for name, scope in scopes.items():
            resolution = history.production_policy(scope, all_policies, as_of=as_of)
            lines.append(f"  Governance Scope {name}: {scope.scope_id}")
            lines.append(f"  {name} resolution status: {resolution.status.value}")
            lines.append(f"  {name} production-authorized policy: {resolution.policy_id or 'none'}")
            lines.append(f"  {name} supporting Governance Record IDs: {json.dumps(resolution.supporting_record_ids)}")
            lines.append(f"  {name} resolution conflict reason codes: {json.dumps([item.value for item in resolution.reason_codes])}")
            lines.append(f"  {name} governance authority derived: {'yes' if resolution.governance_authority_derived else 'no'}")
            lines.append(f"  {name} Shadow policy count: {len(history.shadow_policies(scope, all_policies, as_of=as_of))}")
            lines.append(f"  {name} Research policy count: {len(history.research_policies(scope, all_policies, as_of=as_of))}")
            lines.append(f"  {name} Retired policy count: {len(history.retired_policies(scope, all_policies, as_of=as_of))}")
            lines.append(f"  {name} Rejected policy count: {len(history.rejected_policies(scope, all_policies, as_of=as_of))}")
            conflicts = tuple(conflict for lifecycle in history.lifecycles(scope, all_policies, as_of=as_of) for conflict in lifecycle.conflicts)
            counts: dict[str, int] = {}
            for conflict in conflicts + resolution.conflicts:
                counts[conflict.reason_code.value] = counts.get(conflict.reason_code.value, 0) + 1
            lines.append(f"  {name} conflict count: {sum(counts.values())}")
            lines.append(f"  {name} conflict reason counts: {json.dumps(counts, sort_keys=True)}")
            for lifecycle in history.lifecycles(scope, all_policies, as_of=as_of):
                lines.append(f"    lifecycle policy: {lifecycle.policy_id}")
                lines.append(f"      status: {lifecycle.status.value}")
                lines.append(f"      derived lifecycle: {lifecycle.lifecycle.value if lifecycle.lifecycle else 'none'}")
                lines.append(f"      supporting effective time: {lifecycle.supporting_decision_effective_at.isoformat() if lifecycle.supporting_decision_effective_at else 'none'}")
                lines.append(f"      supporting record IDs: {json.dumps(lifecycle.supporting_record_ids)}")
                lines.append(f"      conflict record IDs: {json.dumps(lifecycle.conflict_record_ids)}")
                lines.append(f"      reason codes: {json.dumps([item.value for item in lifecycle.reason_codes])}")
    conflict_counts: dict[str, int] = {}
    conflict_at = datetime.fromisoformat("2026-08-02T12:00:00-05:00")
    def make(key: str, decision: GovernanceDecision, minute: int = 0) -> GovernanceRecord:
        policy = policies[key]
        return GovernanceRecord.create(
            policy=policy, scope=scopes["mlb"], decision=decision,
            decision_effective_at=conflict_at.replace(minute=minute),
            product_owner=owner, rationale=f"Synthetic conflict fixture for {key}",
        )
    equivalent_first = GovernanceRecord.create(
        policy=policies["mlb-a"], scope=scopes["mlb"],
        decision=GovernanceDecision.PRODUCTION, decision_effective_at=conflict_at,
        product_owner=owner, rationale="Equivalent decision first provenance",
    )
    equivalent_second = GovernanceRecord.create(
        policy=policies["mlb-a"], scope=scopes["mlb"],
        decision=GovernanceDecision.PRODUCTION, decision_effective_at=conflict_at,
        product_owner=owner, rationale="Equivalent decision second provenance",
        notes=("different non-lifecycle note",),
    )
    material_production = make("mlb-a", GovernanceDecision.PRODUCTION, 0)
    material_retire = make("mlb-a", GovernanceDecision.RETIRE, 1)
    material_shadow = make("mlb-a", GovernanceDecision.SHADOW, 1)
    unrelated_production = make("mlb-a", GovernanceDecision.PRODUCTION, 0)
    unrelated_research = make("mlb-c", GovernanceDecision.RESEARCH, 1)
    unrelated_shadow = make("mlb-c", GovernanceDecision.SHADOW, 1)
    conflict_histories = (
        ("equivalent-same-time-production", GovernanceHistory((equivalent_first, equivalent_second))),
        ("material-policy-conflict", GovernanceHistory((material_production, material_retire, material_shadow))),
        ("unrelated-research-conflict", GovernanceHistory((unrelated_production, unrelated_research, unrelated_shadow))),
        ("decision-after-reject", GovernanceHistory((make("mlb-d", GovernanceDecision.REJECT),
                                                       make("mlb-d", GovernanceDecision.RESEARCH, 1)))),
        ("same-time-policy-decision-conflict", GovernanceHistory((make("mlb-a", GovernanceDecision.RESEARCH),
                                                                    make("mlb-a", GovernanceDecision.SHADOW)))),
        ("simultaneous-production-conflict", GovernanceHistory((make("mlb-a", GovernanceDecision.PRODUCTION),
                                                                  make("mlb-b", GovernanceDecision.PRODUCTION)))),
    )
    for scenario, conflict_history in conflict_histories:
        resolution = conflict_history.production_policy(scopes["mlb"], all_policies,
                                                        as_of=conflict_at.replace(minute=2))
        lines.append(f"Conflict scenario: {scenario}")
        lines.append(f"  status: {resolution.status.value}")
        lines.append(f"  authorized policy: {resolution.policy_id or 'none'}")
        lines.append(f"  supporting record IDs: {json.dumps(resolution.supporting_record_ids)}")
        lines.append(f"  conflict record IDs: {json.dumps(resolution.conflict_record_ids)}")
        lines.append(f"  reason codes: {json.dumps([item.value for item in resolution.reason_codes])}")
        for conflict in resolution.conflicts:
            conflict_counts[conflict.reason_code.value] = conflict_counts.get(conflict.reason_code.value, 0) + 1
    unknown = GovernanceHistory((make("mlb-a", GovernanceDecision.PRODUCTION),)).production_policy(
        scopes["mlb"], tuple(policy for key, policy in policies.items() if key != "mlb-a"),
        as_of=conflict_at,
    )
    for conflict in unknown.conflicts:
        conflict_counts[conflict.reason_code.value] = conflict_counts.get(conflict.reason_code.value, 0) + 1
    lines.append("Conflict scenario: unknown-forecast-policy")
    lines.append(f"  status: {unknown.status.value}")
    lines.append(f"  authorized policy: {unknown.policy_id or 'none'}")
    lines.append(f"  conflict record IDs: {json.dumps(unknown.conflict_record_ids)}")
    lines.append(f"  reason codes: {json.dumps([item.value for item in unknown.reason_codes])}")
    soccer_record = GovernanceRecord.create(
        policy=policies["soccer-a"], scope=scopes["soccer"],
        decision=GovernanceDecision.RESEARCH, decision_effective_at=conflict_at,
        product_owner=owner, rationale="Synthetic scope mismatch provenance",
    )
    mismatch = GovernanceHistory((soccer_record,)).policy_lifecycle(
        policies["soccer-a"], scopes["mlb"], all_policies, as_of=conflict_at
    )
    for conflict in mismatch.conflicts:
        conflict_counts[conflict.reason_code.value] = conflict_counts.get(conflict.reason_code.value, 0) + 1
    lines.append("Conflict scenario: governance-scope-mismatch")
    lines.append(f"  lifecycle status: {mismatch.status.value}")
    lines.append(f"  conflict record IDs: {json.dumps(mismatch.conflict_record_ids)}")
    lines.append(f"  reason codes: {json.dumps([item.value for item in mismatch.reason_codes])}")
    lines.append(f"Conflict fixtures requested: {len(payload['conflict_cases'])}")
    lines.append(f"Conflict fixture reason counts: {json.dumps(conflict_counts, sort_keys=True)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    print(run(args.fixture))


if __name__ == "__main__":
    main()
