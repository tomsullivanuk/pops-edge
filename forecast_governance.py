"""Immutable, event-sourced PR12 Forecast Policy governance contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from event_contracts import (
    ContractError,
    ReasonCode,
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
)
from forecast_policy import ForecastPolicy


GOVERNANCE_SCHEMA_VERSION = "1"
GOVERNANCE_ALGORITHM_ID = "forecast-policy-governance-replay"
GOVERNANCE_ALGORITHM_VERSION = "1"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class GovernanceDecision(str, Enum):
    RESEARCH = "research"
    SHADOW = "shadow"
    PRODUCTION = "production"
    RETIRE = "retire"
    REJECT = "reject"


class PolicyLifecycle(str, Enum):
    RESEARCH = "research"
    SHADOW = "shadow"
    PRODUCTION = "production"
    RETIRED = "retired"
    REJECTED = "rejected"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    NONE = "none"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"


class GovernanceReasonCode(str, Enum):
    DUPLICATE_GOVERNANCE_RECORD = "duplicate-governance-record"
    UNKNOWN_FORECAST_POLICY = "unknown-forecast-policy"
    GOVERNANCE_SCOPE_MISMATCH = "governance-scope-mismatch"
    MISSING_DECISION_EFFECTIVE_AT = "missing-decision-effective-at"
    MISSING_PRODUCT_OWNER = "missing-product-owner"
    DECISION_AFTER_REJECT = "decision-after-reject"
    SAME_TIME_POLICY_DECISION_CONFLICT = "same-time-policy-decision-conflict"
    SIMULTANEOUS_PRODUCTION_CONFLICT = "simultaneous-production-conflict"
    UNSUPPORTED_GOVERNANCE_VERSION = "unsupported-governance-version"
    UNSUPPORTED_DECISION = "unsupported-governance-decision"


@dataclass(frozen=True, slots=True, order=True)
class GovernanceScope:
    scope_id: str
    schema_version: str
    sport: str
    competition: str
    proposition_type: str
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, sport: str, competition: str, proposition_type: str,
               limitations: tuple[str, ...] = ()) -> "GovernanceScope":
        ordered = tuple(sorted(set(limitations)))
        material = {
            "schema_version": GOVERNANCE_SCHEMA_VERSION,
            "sport": sport,
            "competition": competition,
            "proposition_type": proposition_type,
            "limitations": list(ordered),
        }
        digest = _digest(material)
        return cls(f"governance-scope:{digest}", GOVERNANCE_SCHEMA_VERSION,
                   sport, competition, proposition_type, ordered, digest)

    @classmethod
    def from_policy(cls, policy: ForecastPolicy, *, limitations: tuple[str, ...] = ()) -> "GovernanceScope":
        return cls.create(sport=policy.sport, competition=policy.competition,
                          proposition_type=policy.proposition_type, limitations=limitations)

    def __post_init__(self) -> None:
        for value, label in ((self.scope_id, "scope_id"), (self.schema_version, "schema_version"),
                             (self.sport, "sport"), (self.competition, "competition"),
                             (self.proposition_type, "proposition_type"), (self.input_digest, "input_digest")):
            _require_identifier(value, label)
        if self.schema_version != GOVERNANCE_SCHEMA_VERSION:
            raise ContractError(GovernanceReasonCode.UNSUPPORTED_GOVERNANCE_VERSION, "unsupported Governance Scope version")  # type: ignore[arg-type]
        ordered = tuple(sorted(set(self.limitations)))
        material = {"schema_version": self.schema_version, "sport": self.sport,
                    "competition": self.competition, "proposition_type": self.proposition_type,
                    "limitations": list(ordered)}
        digest = _digest(material)
        if self.input_digest != digest or self.scope_id != f"governance-scope:{digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "Governance Scope identity conflicts with material inputs")
        object.__setattr__(self, "limitations", ordered)

    def supports(self, policy: ForecastPolicy) -> bool:
        return (self.sport, self.competition, self.proposition_type) == (
            policy.sport, policy.competition, policy.proposition_type)


@dataclass(frozen=True, slots=True, order=True)
class ProductOwnerIdentity:
    product_owner_id: str
    display_name: str | None = None
    schema_version: str = "1"

    def __post_init__(self) -> None:
        _require_identifier(self.product_owner_id, "product_owner_id")
        if self.display_name is not None:
            _require_identifier(self.display_name, "product_owner display_name")
        if self.schema_version != "1":
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "unsupported Product Owner identity version")


@dataclass(frozen=True, slots=True)
class GovernanceRecord:
    record_id: str
    schema_version: str
    algorithm_id: str
    algorithm_version: str
    policy_id: str
    policy_version: str
    scope: GovernanceScope
    decision: GovernanceDecision
    decision_effective_at: datetime
    product_owner: ProductOwnerIdentity
    policy_proposal_ids: tuple[str, ...]
    forecast_intelligence_report_ids: tuple[str, ...]
    policy_hypothesis_ids: tuple[str, ...]
    rationale: str
    notes: tuple[str, ...]
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, policy: ForecastPolicy, scope: GovernanceScope,
               decision: GovernanceDecision, decision_effective_at: datetime,
               product_owner: ProductOwnerIdentity, rationale: str,
               policy_proposal_ids: tuple[str, ...] = (),
               forecast_intelligence_report_ids: tuple[str, ...] = (),
               policy_hypothesis_ids: tuple[str, ...] = (), notes: tuple[str, ...] = (),
               limitations: tuple[str, ...] = ()) -> "GovernanceRecord":
        if not scope.supports(policy):
            raise ContractError(GovernanceReasonCode.GOVERNANCE_SCOPE_MISMATCH, "Governance Scope does not match Forecast Policy")  # type: ignore[arg-type]
        material = _record_material(
            policy.policy_id, policy.policy_version, scope, decision,
            decision_effective_at, product_owner, policy_proposal_ids,
            forecast_intelligence_report_ids, policy_hypothesis_ids,
            rationale, notes, limitations,
        )
        digest = _digest(material)
        return cls(f"governance-record:{digest}", GOVERNANCE_SCHEMA_VERSION,
                   GOVERNANCE_ALGORITHM_ID, GOVERNANCE_ALGORITHM_VERSION,
                   policy.policy_id, policy.policy_version, scope, decision,
                   decision_effective_at, product_owner,
                   tuple(sorted(set(policy_proposal_ids))),
                   tuple(sorted(set(forecast_intelligence_report_ids))),
                   tuple(sorted(set(policy_hypothesis_ids))), rationale,
                   tuple(sorted(set(notes))), tuple(sorted(set(limitations))), digest)

    def __post_init__(self) -> None:
        for value, label in ((self.record_id, "record_id"), (self.schema_version, "schema_version"),
                             (self.algorithm_id, "algorithm_id"), (self.algorithm_version, "algorithm_version"),
                             (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
                             (self.input_digest, "input_digest")):
            _require_identifier(value, label)
        if self.schema_version != GOVERNANCE_SCHEMA_VERSION or self.algorithm_id != GOVERNANCE_ALGORITHM_ID or self.algorithm_version != GOVERNANCE_ALGORITHM_VERSION:
            raise ContractError(GovernanceReasonCode.UNSUPPORTED_GOVERNANCE_VERSION, "unsupported governance schema or algorithm version")  # type: ignore[arg-type]
        if self.decision_effective_at is None:
            raise ContractError(GovernanceReasonCode.MISSING_DECISION_EFFECTIVE_AT, "decision_effective_at is required")  # type: ignore[arg-type]
        _require_aware(self.decision_effective_at, "decision_effective_at")
        if not isinstance(self.product_owner, ProductOwnerIdentity):
            raise ContractError(GovernanceReasonCode.MISSING_PRODUCT_OWNER, "Product Owner identity is required")  # type: ignore[arg-type]
        if not isinstance(self.decision, GovernanceDecision):
            raise ContractError(GovernanceReasonCode.UNSUPPORTED_DECISION, "unsupported governance decision")  # type: ignore[arg-type]
        _require_identifier(self.rationale, "rationale")
        for values, label in ((self.policy_proposal_ids, "Policy Proposal"),
                              (self.forecast_intelligence_report_ids, "Forecast Intelligence Report"),
                              (self.policy_hypothesis_ids, "Policy Hypothesis")):
            for value in values:
                _require_identifier(value, f"{label} reference")
        material = _record_material(
            self.policy_id, self.policy_version, self.scope, self.decision,
            self.decision_effective_at, self.product_owner, self.policy_proposal_ids,
            self.forecast_intelligence_report_ids, self.policy_hypothesis_ids,
            self.rationale, self.notes, self.limitations,
        )
        digest = _digest(material)
        if self.input_digest != digest or self.record_id != f"governance-record:{digest}":
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "Governance Record identity conflicts with material inputs")
        object.__setattr__(self, "policy_proposal_ids", tuple(sorted(set(self.policy_proposal_ids))))
        object.__setattr__(self, "forecast_intelligence_report_ids", tuple(sorted(set(self.forecast_intelligence_report_ids))))
        object.__setattr__(self, "policy_hypothesis_ids", tuple(sorted(set(self.policy_hypothesis_ids))))
        object.__setattr__(self, "notes", tuple(sorted(set(self.notes))))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))


def _record_material(policy_id: str, policy_version: str, scope: GovernanceScope,
                     decision: GovernanceDecision, effective_at: datetime,
                     owner: ProductOwnerIdentity, proposal_ids: tuple[str, ...],
                     report_ids: tuple[str, ...], hypothesis_ids: tuple[str, ...],
                     rationale: str, notes: tuple[str, ...], limitations: tuple[str, ...]) -> dict[str, object]:
    if effective_at is None:
        raise ContractError(GovernanceReasonCode.MISSING_DECISION_EFFECTIVE_AT, "decision_effective_at is required")  # type: ignore[arg-type]
    _require_aware(effective_at, "decision_effective_at")
    if not isinstance(owner, ProductOwnerIdentity):
        raise ContractError(GovernanceReasonCode.MISSING_PRODUCT_OWNER, "Product Owner identity is required")  # type: ignore[arg-type]
    if not isinstance(decision, GovernanceDecision):
        raise ContractError(GovernanceReasonCode.UNSUPPORTED_DECISION, "unsupported governance decision")  # type: ignore[arg-type]
    _require_identifier(rationale, "rationale")
    return {
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "algorithm": [GOVERNANCE_ALGORITHM_ID, GOVERNANCE_ALGORITHM_VERSION],
        "policy": [policy_id, policy_version], "scope_id": scope.scope_id,
        "decision": decision.value, "decision_effective_at": effective_at.isoformat(),
        "product_owner": [owner.product_owner_id, owner.schema_version],
        "policy_proposal_ids": sorted(set(proposal_ids)),
        "forecast_intelligence_report_ids": sorted(set(report_ids)),
        "policy_hypothesis_ids": sorted(set(hypothesis_ids)),
        "rationale": rationale, "notes": sorted(set(notes)),
        "limitations": sorted(set(limitations)),
    }


@dataclass(frozen=True, slots=True, order=True)
class GovernanceConflict:
    reason_code: GovernanceReasonCode
    record_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]
    scope_id: str
    detail: str


@dataclass(frozen=True, slots=True)
class PolicyLifecycleResult:
    status: ResolutionStatus
    policy_id: str
    policy_version: str
    scope_id: str
    as_of: datetime
    lifecycle: PolicyLifecycle | None
    supporting_record_id: str | None
    supporting_record_ids: tuple[str, ...]
    supporting_decision_effective_at: datetime | None
    considered_record_ids: tuple[str, ...]
    conflicts: tuple[GovernanceConflict, ...]
    limitations: tuple[str, ...]

    @property
    def conflict_record_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record_id for conflict in self.conflicts for record_id in conflict.record_ids}))

    @property
    def reason_codes(self) -> tuple[GovernanceReasonCode, ...]:
        return tuple(sorted({conflict.reason_code for conflict in self.conflicts}, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ProductionPolicyResolution:
    status: ResolutionStatus
    scope_id: str
    as_of: datetime
    policy_id: str | None
    policy_version: str | None
    supporting_record_id: str | None
    supporting_record_ids: tuple[str, ...]
    supporting_decision_effective_at: datetime | None
    considered_record_ids: tuple[str, ...]
    considered_policy_ids: tuple[str, ...]
    conflicts: tuple[GovernanceConflict, ...]
    limitations: tuple[str, ...]

    @property
    def governance_authority_derived(self) -> bool:
        return self.status is ResolutionStatus.RESOLVED and self.policy_id is not None

    @property
    def conflict_record_ids(self) -> tuple[str, ...]:
        return tuple(sorted({record_id for conflict in self.conflicts for record_id in conflict.record_ids}))

    @property
    def reason_codes(self) -> tuple[GovernanceReasonCode, ...]:
        return tuple(sorted({conflict.reason_code for conflict in self.conflicts}, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class GovernanceHistory:
    records: tuple[GovernanceRecord, ...] = ()

    def __post_init__(self) -> None:
        ids = tuple(item.record_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise ContractError(GovernanceReasonCode.DUPLICATE_GOVERNANCE_RECORD, "duplicate Governance Record identity")  # type: ignore[arg-type]
        object.__setattr__(self, "records", tuple(sorted(self.records, key=lambda item: (item.decision_effective_at, item.record_id))))

    def append(self, record: GovernanceRecord) -> "GovernanceHistory":
        return GovernanceHistory(self.records + (record,))

    def policy_lifecycle(self, policy: ForecastPolicy, scope: GovernanceScope,
                         policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> PolicyLifecycleResult:
        _require_aware(as_of, "as_of")
        index, registry_conflicts = _policy_index(policies, scope)
        relevant = tuple(item for item in self.records if item.policy_id == policy.policy_id and item.decision_effective_at <= as_of)
        base = list(registry_conflicts)
        if policy.policy_id not in index:
            base.append(_conflict(GovernanceReasonCode.UNKNOWN_FORECAST_POLICY, relevant, (policy.policy_id,), scope.scope_id, "Forecast Policy is absent from the supplied immutable registry"))
        elif not scope.supports(policy):
            base.append(_conflict(GovernanceReasonCode.GOVERNANCE_SCOPE_MISMATCH, relevant, (policy.policy_id,), scope.scope_id, "Forecast Policy does not match Governance Scope"))
        base.extend(_record_reference_conflicts(relevant, index, scope))
        if base:
            return _lifecycle_result(ResolutionStatus.INVALID, policy, scope, as_of, relevant, None, tuple(_unique_conflicts(base)))
        if not relevant:
            return _lifecycle_result(ResolutionStatus.NONE, policy, scope, as_of, (), None, ())
        conflicts = _policy_chronology_conflicts(relevant, scope)
        if conflicts:
            status = (ResolutionStatus.AMBIGUOUS
                      if any(item.reason_code is GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT for item in conflicts)
                      else ResolutionStatus.INVALID)
            return _lifecycle_result(status, policy, scope, as_of, relevant, None, conflicts)
        latest_group = _effective_groups(relevant)[-1]
        latest = latest_group[0]
        lifecycle = {
            GovernanceDecision.RESEARCH: PolicyLifecycle.RESEARCH,
            GovernanceDecision.SHADOW: PolicyLifecycle.SHADOW,
            GovernanceDecision.PRODUCTION: PolicyLifecycle.PRODUCTION,
            GovernanceDecision.RETIRE: PolicyLifecycle.RETIRED,
            GovernanceDecision.REJECT: PolicyLifecycle.REJECTED,
        }[latest.decision]
        return _lifecycle_result(ResolutionStatus.RESOLVED, policy, scope, as_of, relevant, latest_group, (), lifecycle)

    def lifecycles(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return tuple(sorted((self.policy_lifecycle(policy, scope, policies, as_of=as_of)
                             for policy in policies if scope.supports(policy)), key=lambda item: item.policy_id))

    def lifecycle_view(self, lifecycle: PolicyLifecycle, scope: GovernanceScope,
                       policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return tuple(item for item in self.lifecycles(scope, policies, as_of=as_of)
                     if item.status is ResolutionStatus.RESOLVED and item.lifecycle is lifecycle)

    def shadow_policies(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return self.lifecycle_view(PolicyLifecycle.SHADOW, scope, policies, as_of=as_of)

    def research_policies(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return self.lifecycle_view(PolicyLifecycle.RESEARCH, scope, policies, as_of=as_of)

    def retired_policies(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return self.lifecycle_view(PolicyLifecycle.RETIRED, scope, policies, as_of=as_of)

    def rejected_policies(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> tuple[PolicyLifecycleResult, ...]:
        return self.lifecycle_view(PolicyLifecycle.REJECTED, scope, policies, as_of=as_of)

    def production_policy(self, scope: GovernanceScope, policies: tuple[ForecastPolicy, ...], *, as_of: datetime) -> ProductionPolicyResolution:
        _require_aware(as_of, "as_of")
        index, conflicts = _policy_index(policies, scope)
        relevant = tuple(item for item in self.records if item.scope.scope_id == scope.scope_id and item.decision_effective_at <= as_of)
        conflicts = list(conflicts) + list(_record_reference_conflicts(relevant, index, scope))
        for policy in policies:
            if not scope.supports(policy):
                continue
            result = self.policy_lifecycle(policy, scope, policies, as_of=as_of)
            conflicts.extend(result.conflicts)
        by_time: dict[datetime, list[GovernanceRecord]] = {}
        for record in relevant:
            by_time.setdefault(record.decision_effective_at, []).append(record)
        for effective_at, records in by_time.items():
            productions = [item for item in records if item.decision is GovernanceDecision.PRODUCTION]
            if len({item.policy_id for item in productions}) > 1:
                conflicts.append(_conflict(GovernanceReasonCode.SIMULTANEOUS_PRODUCTION_CONFLICT, productions,
                                           tuple(item.policy_id for item in productions), scope.scope_id,
                                           f"multiple Production decisions share {effective_at.isoformat()}"))
        conflicts = _unique_conflicts(conflicts)
        production_policy_ids = {
            item.policy_id for item in relevant
            if item.decision is GovernanceDecision.PRODUCTION
        }
        material_conflicts = tuple(
            conflict for conflict in conflicts
            if conflict.reason_code is GovernanceReasonCode.SIMULTANEOUS_PRODUCTION_CONFLICT
            or bool(set(conflict.policy_ids) & production_policy_ids)
        )
        if material_conflicts:
            status = ResolutionStatus.AMBIGUOUS if any(item.reason_code in {
                GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT,
                GovernanceReasonCode.SIMULTANEOUS_PRODUCTION_CONFLICT,
            } for item in material_conflicts) else ResolutionStatus.INVALID
            return _production_result(status, scope, as_of, relevant, policies, None,
                                      tuple(conflicts))
        current: tuple[GovernanceRecord, ...] | None = None
        for effective_at in sorted(by_time):
            records = by_time[effective_at]
            policy_groups: dict[str, list[GovernanceRecord]] = {}
            for record in records:
                policy_groups.setdefault(record.policy_id, []).append(record)
            production = next((tuple(sorted(group, key=lambda item: item.record_id))
                               for group in policy_groups.values()
                               if group[0].decision is GovernanceDecision.PRODUCTION), None)
            if production:
                current = production
            for group in policy_groups.values():
                if (current is not None and group[0].policy_id == current[0].policy_id
                        and group[0].decision is not GovernanceDecision.PRODUCTION):
                    current = None
        if current is None:
            return _production_result(ResolutionStatus.NONE, scope, as_of, relevant,
                                      policies, None, tuple(conflicts))
        policy = index[current[0].policy_id]
        return _production_result(ResolutionStatus.RESOLVED, scope, as_of, relevant,
                                  policies, current, tuple(conflicts), policy)


def _policy_index(policies: tuple[ForecastPolicy, ...], scope: GovernanceScope) -> tuple[dict[str, ForecastPolicy], tuple[GovernanceConflict, ...]]:
    index: dict[str, ForecastPolicy] = {}
    conflicts: list[GovernanceConflict] = []
    for policy in policies:
        if policy.policy_id in index:
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate Forecast Policy identity in registry")
        index[policy.policy_id] = policy
    return index, tuple(conflicts)


def _record_reference_conflicts(records: tuple[GovernanceRecord, ...], index: dict[str, ForecastPolicy], scope: GovernanceScope) -> tuple[GovernanceConflict, ...]:
    conflicts: list[GovernanceConflict] = []
    for record in records:
        policy = index.get(record.policy_id)
        if policy is None or (policy is not None and policy.policy_version != record.policy_version):
            conflicts.append(_conflict(GovernanceReasonCode.UNKNOWN_FORECAST_POLICY, (record,), (record.policy_id,), scope.scope_id, "record references an unknown Forecast Policy identity/version"))
        elif record.scope.scope_id != scope.scope_id or not record.scope.supports(policy):
            conflicts.append(_conflict(GovernanceReasonCode.GOVERNANCE_SCOPE_MISMATCH, (record,), (record.policy_id,), scope.scope_id, "record Governance Scope conflicts with supplied policy or requested scope"))
    return tuple(conflicts)


def _policy_chronology_conflicts(records: tuple[GovernanceRecord, ...], scope: GovernanceScope) -> tuple[GovernanceConflict, ...]:
    conflicts: list[GovernanceConflict] = []
    rejected = False
    for group in _effective_groups(records):
        effective_at = group[0].decision_effective_at
        decisions = {record.decision for record in group}
        if len(decisions) > 1:
            conflicts.append(_conflict(GovernanceReasonCode.SAME_TIME_POLICY_DECISION_CONFLICT, group,
                                       tuple(item.policy_id for item in group), scope.scope_id,
                                       f"conflicting policy decisions share {effective_at.isoformat()}"))
            continue
        record = group[0]
        if rejected:
            conflicts.append(_conflict(GovernanceReasonCode.DECISION_AFTER_REJECT, group,
                                       (record.policy_id,), scope.scope_id, "a decision follows terminal Reject"))
        if record.decision is GovernanceDecision.REJECT:
            rejected = True
    return tuple(conflicts)


def _effective_groups(records: tuple[GovernanceRecord, ...]) -> tuple[tuple[GovernanceRecord, ...], ...]:
    by_time: dict[datetime, list[GovernanceRecord]] = {}
    for record in records:
        by_time.setdefault(record.decision_effective_at, []).append(record)
    return tuple(
        tuple(sorted(by_time[effective_at], key=lambda item: item.record_id))
        for effective_at in sorted(by_time)
    )


def _conflict(code: GovernanceReasonCode, records: tuple[GovernanceRecord, ...] | list[GovernanceRecord],
              policy_ids: tuple[str, ...], scope_id: str, detail: str) -> GovernanceConflict:
    return GovernanceConflict(code, tuple(sorted(item.record_id for item in records)),
                              tuple(sorted(set(policy_ids))), scope_id, detail)


def _unique_conflicts(conflicts: list[GovernanceConflict] | tuple[GovernanceConflict, ...]) -> list[GovernanceConflict]:
    return sorted(set(conflicts), key=lambda item: (item.reason_code.value, item.record_ids, item.policy_ids, item.detail))


def _lifecycle_result(status: ResolutionStatus, policy: ForecastPolicy, scope: GovernanceScope,
                      as_of: datetime, records: tuple[GovernanceRecord, ...],
                      supporting: tuple[GovernanceRecord, ...] | None,
                      conflicts: tuple[GovernanceConflict, ...],
                      lifecycle: PolicyLifecycle | None = None) -> PolicyLifecycleResult:
    support = supporting or ()
    return PolicyLifecycleResult(status, policy.policy_id, policy.policy_version, scope.scope_id,
                                 as_of, lifecycle,
                                 support[0].record_id if len(support) == 1 else None,
                                 tuple(item.record_id for item in support),
                                 support[0].decision_effective_at if support else None,
                                 tuple(item.record_id for item in records), conflicts,
                                 tuple(sorted(set(scope.limitations + (
                                     "lifecycle is derived at the explicit as_of boundary",
                                 )))))


def _production_result(status: ResolutionStatus, scope: GovernanceScope, as_of: datetime,
                       records: tuple[GovernanceRecord, ...], policies: tuple[ForecastPolicy, ...],
                       supporting: tuple[GovernanceRecord, ...] | None,
                       conflicts: tuple[GovernanceConflict, ...],
                       policy: ForecastPolicy | None = None) -> ProductionPolicyResolution:
    support = supporting or ()
    return ProductionPolicyResolution(
        status, scope.scope_id, as_of,
        policy.policy_id if policy else None,
        policy.policy_version if policy else None,
        support[0].record_id if len(support) == 1 else None,
        tuple(item.record_id for item in support),
        support[0].decision_effective_at if support else None,
        tuple(item.record_id for item in records),
        tuple(sorted(policy.policy_id for policy in policies if scope.supports(policy))),
        conflicts,
        tuple(sorted(set(scope.limitations + (
            "governance resolution does not select a Policy Forecast execution",
            "unrelated non-production conflicts remain diagnostic and do not erase authority",
        )))),
    )


_CONTRACTS = (GovernanceScope, ProductOwnerIdentity, GovernanceRecord, GovernanceConflict,
              PolicyLifecycleResult, ProductionPolicyResolution, GovernanceHistory)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(GovernanceDecision, PolicyLifecycle, ResolutionStatus, GovernanceReasonCode))
