"""Reusable offline event, provenance, and reconciliation contracts.

The contracts in this module deliberately contain no sport, provider, network,
storage, pricing, forecast, or settlement behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, TypeVar


class ContractError(ValueError):
    """Raised when an immutable contract cannot be constructed safely."""

    def __init__(self, code: "ReasonCode", detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class ReasonCode(str, Enum):
    MISSING_IDENTIFIER = "missing_identifier"
    MALFORMED_IDENTIFIER = "malformed_identifier"
    MISSING_PARTICIPANT = "missing_participant"
    IDENTICAL_PARTICIPANTS = "identical_participants"
    CONFLICTING_SOURCE_MAPPING = "conflicting_source_mapping"
    CONFLICTING_NATIVE_IDENTITY = "conflicting_native_identity"
    MISSING_GAME_PK = "missing_game_pk"
    CONFLICTING_GAME_PK = "conflicting_game_pk"
    DOUBLEHEADER_AMBIGUITY = "doubleheader_ambiguity"
    CONTRADICTORY_LINEAGE = "contradictory_lineage"
    NAIVE_TIMESTAMP = "naive_timestamp"
    INVALID_TIMESTAMP_CHRONOLOGY = "invalid_timestamp_chronology"
    MISSING_PITCHER = "missing_pitcher"
    PITCHER_CHANGED = "pitcher_changed"
    CONFLICTING_SCHEDULE = "conflicting_schedule"
    AMBIGUOUS_CANDIDATES = "ambiguous_candidates"
    NO_MATCHING_EVENT = "no_matching_event"
    UNSUPPORTED_STATUS = "unsupported_status"
    VALIDATION_FAILURE = "validation_failure"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INCOMPLETE = "incomplete"
    REJECTED = "rejected"


class ReconciliationOutcome(str, Enum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True, order=True)
class ValidationReason:
    code: ReasonCode
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "reason detail")


@dataclass(frozen=True, slots=True, order=True)
class NativeIdentifier:
    namespace: str
    value: str

    def __post_init__(self) -> None:
        _require_identifier(self.namespace, "identifier namespace")
        _require_identifier(self.value, "identifier value")


@dataclass(frozen=True, slots=True, order=True)
class SportNativeIdentifier(NativeIdentifier):
    """Identifier assigned by the sport's authoritative competition source."""


@dataclass(frozen=True, slots=True)
class SourceMapping:
    """Immutable, independently discovered mapping to a canonical entity."""

    mapping_id: str
    canonical_entity_id: str
    source_identifier: NativeIdentifier
    collected_at: datetime
    evidence: tuple["Evidence", ...]

    def __post_init__(self) -> None:
        _require_identifier(self.mapping_id, "mapping_id")
        _require_identifier(self.canonical_entity_id, "canonical_entity_id")
        _require_aware(self.collected_at, "collected_at")
        if not self.evidence:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "a source mapping requires supporting evidence",
            )


@dataclass(frozen=True, slots=True, order=True)
class ParticipantRef:
    canonical_id: str
    display_name: str
    native_identifiers: tuple[SportNativeIdentifier, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.canonical_id, "participant canonical_id")
        _require_text(
            self.display_name, ReasonCode.MISSING_PARTICIPANT, "participant display_name"
        )
        _require_sport_native_identifiers(self.native_identifiers)
        _validate_identifier_mappings(self.native_identifiers)


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    """Immutable identity for one sporting contest."""

    sport: str
    competition: str
    season: str
    canonical_event_id: str
    participants: tuple[ParticipantRef, ...]
    native_identifiers: tuple[SportNativeIdentifier, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.sport, "sport")
        _require_identifier(self.competition, "competition")
        _require_identifier(self.season, "season")
        _require_identifier(self.canonical_event_id, "canonical_event_id")
        if len(self.participants) < 2:
            raise ContractError(
                ReasonCode.MISSING_PARTICIPANT,
                "a canonical event requires at least two participants",
            )
        participant_ids = tuple(item.canonical_id for item in self.participants)
        if len(set(participant_ids)) != len(participant_ids):
            raise ContractError(
                ReasonCode.IDENTICAL_PARTICIPANTS,
                "canonical participant identities must be distinct",
            )
        _require_sport_native_identifiers(self.native_identifiers)
        _validate_identifier_mappings(self.native_identifiers)


@dataclass(frozen=True, slots=True, order=True)
class Evidence:
    kind: str
    value: str

    def __post_init__(self) -> None:
        _require_identifier(self.kind, "evidence kind")
        _require_text(self.value, ReasonCode.VALIDATION_FAILURE, "evidence value")


@dataclass(frozen=True, slots=True)
class Provenance:
    provider: str
    source_record_id: str
    canonical_event_id: str | None
    collected_at: datetime
    source_timestamp: datetime | None = None
    transformations: tuple[str, ...] = ()
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_reasons: tuple[ValidationReason, ...] = ()
    raw_evidence_ref: str | None = None
    source_url: str | None = None
    collector_version: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.provider, "provider")
        _require_identifier(self.source_record_id, "source_record_id")
        if self.canonical_event_id is not None:
            _require_identifier(self.canonical_event_id, "canonical_event_id")
        _require_aware(self.collected_at, "collected_at")
        if self.source_timestamp is not None:
            _require_aware(self.source_timestamp, "source_timestamp")
            if self.collected_at < self.source_timestamp:
                raise ContractError(
                    ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY,
                    "collection cannot precede the source timestamp",
                )
        for transformation in self.transformations:
            _require_text(
                transformation, ReasonCode.VALIDATION_FAILURE, "transformation"
            )
        if self.validation_status is ValidationStatus.VALID and self.validation_reasons:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "valid provenance cannot carry validation reasons",
            )
        if self.validation_status is not ValidationStatus.VALID and not self.validation_reasons:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "incomplete or rejected provenance requires structured reasons",
            )
        if self.raw_evidence_ref is not None:
            _require_identifier(self.raw_evidence_ref, "raw_evidence_ref")
        if self.source_url is not None:
            _require_text(
                self.source_url, ReasonCode.VALIDATION_FAILURE, "source_url"
            )
        if self.collector_version is not None:
            _require_identifier(self.collector_version, "collector_version")


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    """Audit record for a candidate considered during reconciliation."""

    canonical_event_id: str
    mappings_evaluated: tuple[NativeIdentifier, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    reasons: tuple[ValidationReason, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.canonical_event_id, "candidate canonical_event_id")
        _validate_identifier_mappings(self.mappings_evaluated)
        if not self.evidence and not self.reasons:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "a candidate evaluation requires evidence or structured reasons",
            )


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    outcome: ReconciliationOutcome
    source_record: NativeIdentifier
    matched_event: CanonicalEvent | None = None
    candidate_events: tuple[CanonicalEvent, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    source_mapping: NativeIdentifier | None = None
    warnings: tuple[ValidationReason, ...] = ()
    reasons: tuple[ValidationReason, ...] = ()
    candidate_evaluations: tuple[CandidateEvaluation, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome is ReconciliationOutcome.MATCHED:
            if self.matched_event is None or self.candidate_events or self.reasons:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "matched reconciliation requires exactly one matched event",
                )
            evaluated_ids = {
                evaluation.canonical_event_id
                for evaluation in self.candidate_evaluations
            }
            if evaluated_ids and evaluated_ids != {
                self.matched_event.canonical_event_id
            }:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "matched reconciliation evaluations must describe the matched event",
                )
        elif self.outcome is ReconciliationOutcome.AMBIGUOUS:
            if self.matched_event is not None or len(self.candidate_events) < 2:
                raise ContractError(
                    ReasonCode.AMBIGUOUS_CANDIDATES,
                    "ambiguous reconciliation requires at least two candidates",
                )
            if not self.reasons:
                raise ContractError(
                    ReasonCode.AMBIGUOUS_CANDIDATES,
                    "ambiguous reconciliation requires structured reasons",
                )
            candidate_ids = {
                candidate.canonical_event_id for candidate in self.candidate_events
            }
            evaluated_ids = {
                evaluation.canonical_event_id
                for evaluation in self.candidate_evaluations
            }
            if evaluated_ids and not evaluated_ids.issubset(candidate_ids):
                raise ContractError(
                    ReasonCode.AMBIGUOUS_CANDIDATES,
                    "ambiguous evaluations must describe retained candidates",
                )
        elif self.outcome is ReconciliationOutcome.REJECTED:
            if self.matched_event is not None or self.candidate_events:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "rejected reconciliation cannot select or retain candidates",
                )
            if not self.reasons:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "rejected reconciliation requires structured reasons",
                )

    @classmethod
    def matched(
        cls,
        source_record: NativeIdentifier,
        event: CanonicalEvent,
        *,
        evidence: tuple[Evidence, ...],
        source_mapping: NativeIdentifier | None = None,
        warnings: tuple[ValidationReason, ...] = (),
        candidate_evaluations: tuple[CandidateEvaluation, ...] = (),
    ) -> "ReconciliationResult":
        return cls(
            outcome=ReconciliationOutcome.MATCHED,
            source_record=source_record,
            matched_event=event,
            evidence=evidence,
            source_mapping=source_mapping,
            warnings=warnings,
            candidate_evaluations=candidate_evaluations,
        )

    @classmethod
    def ambiguous(
        cls,
        source_record: NativeIdentifier,
        candidates: tuple[CanonicalEvent, ...],
        *,
        evidence: tuple[Evidence, ...],
        reasons: tuple[ValidationReason, ...],
        candidate_evaluations: tuple[CandidateEvaluation, ...] = (),
    ) -> "ReconciliationResult":
        return cls(
            outcome=ReconciliationOutcome.AMBIGUOUS,
            source_record=source_record,
            candidate_events=candidates,
            evidence=evidence,
            reasons=reasons,
            candidate_evaluations=candidate_evaluations,
        )

    @classmethod
    def rejected(
        cls,
        source_record: NativeIdentifier,
        *,
        evidence: tuple[Evidence, ...],
        reasons: tuple[ValidationReason, ...],
        candidate_evaluations: tuple[CandidateEvaluation, ...] = (),
    ) -> "ReconciliationResult":
        return cls(
            outcome=ReconciliationOutcome.REJECTED,
            source_record=source_record,
            evidence=evidence,
            reasons=reasons,
            candidate_evaluations=candidate_evaluations,
        )


ContractT = TypeVar("ContractT", bound="SerializableContract")
_SERIALIZABLE_TYPES: dict[str, type[Any]] = {}
_ENUM_TYPES: dict[str, type[Enum]] = {
    enum_type.__name__: enum_type
    for enum_type in (
        ReasonCode,
        ValidationStatus,
        ReconciliationOutcome,
    )
}


class SerializableContract:
    """Mixin providing tagged, deterministic JSON serialization."""

    _serialization_registry: ClassVar[dict[str, type[Any]]] = _SERIALIZABLE_TYPES

    def to_dict(self) -> dict[str, Any]:
        encoded = _encode(self)
        if not isinstance(encoded, dict):
            raise TypeError("contract serialization must produce an object")
        return encoded

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    @classmethod
    def from_dict(cls: type[ContractT], payload: dict[str, Any]) -> ContractT:
        decoded = _decode(payload)
        if not isinstance(decoded, cls):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                f"serialized payload is not a {cls.__name__}",
            )
        return decoded

    @classmethod
    def from_json(cls: type[ContractT], payload: str) -> ContractT:
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE, "serialized contract must be an object"
            )
        return cls.from_dict(decoded)


def _register(*contract_types: type[Any], enums: tuple[type[Enum], ...] = ()) -> None:
    for contract_type in contract_types:
        _SERIALIZABLE_TYPES[contract_type.__name__] = contract_type
        for base in contract_type.__bases__:
            if base is not SerializableContract:
                continue
    for enum_type in enums:
        _ENUM_TYPES[enum_type.__name__] = enum_type


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        _require_aware(value, "serialized timestamp")
        return {"__datetime__": value.isoformat()}
    if isinstance(value, date):
        return {"__date__": value.isoformat()}
    if isinstance(value, Decimal):
        if value.is_nan():
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "NaN is not serializable scientific data")
        if value == Decimal("Infinity"):
            return {"__non_finite_decimal__": "positive-infinity"}
        if value == Decimal("-Infinity"):
            return {"__non_finite_decimal__": "negative-infinity"}
        return {"__decimal__": str(value)}
    if isinstance(value, Enum):
        return {"__enum__": f"{value.__class__.__name__}:{value.value}"}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": value.__class__.__name__,
            **{field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported serialized value: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_decode(item) for item in value)
    if isinstance(value, dict):
        if set(value) == {"__date__"}:
            return date.fromisoformat(value["__date__"])
        if set(value) == {"__decimal__"}:
            return Decimal(value["__decimal__"])
        if set(value) == {"__non_finite_decimal__"}:
            if value["__non_finite_decimal__"] not in ("positive-infinity", "negative-infinity"):
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "unknown non-finite Decimal representation",
                )
            return Decimal("Infinity" if value["__non_finite_decimal__"] == "positive-infinity" else "-Infinity")
        if set(value) == {"__datetime__"}:
            timestamp = datetime.fromisoformat(value["__datetime__"])
            _require_aware(timestamp, "serialized timestamp")
            return timestamp
        if set(value) == {"__enum__"}:
            enum_name, enum_value = value["__enum__"].split(":", 1)
            try:
                return _ENUM_TYPES[enum_name](enum_value)
            except (KeyError, ValueError) as error:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    f"unknown serialized enum {value['__enum__']}",
                ) from error
        if "__type__" in value:
            type_name = value["__type__"]
            try:
                contract_type = _SERIALIZABLE_TYPES[type_name]
            except KeyError as error:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    f"unknown serialized contract {type_name}",
                ) from error
            kwargs = {
                key: _decode(item) for key, item in value.items() if key != "__type__"
            }
            return contract_type(**kwargs)
    return value


def _require_text(value: str, code: ReasonCode, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(code, f"{label} is required")


def _require_identifier(value: str, label: str) -> None:
    _require_text(value, ReasonCode.MISSING_IDENTIFIER, label)
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise ContractError(
            ReasonCode.MALFORMED_IDENTIFIER,
            f"{label} contains whitespace padding or control characters",
        )


def _require_aware(value: datetime, label: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError(ReasonCode.NAIVE_TIMESTAMP, f"{label} must be timezone-aware")


def _validate_identifier_mappings(
    identifiers: tuple[NativeIdentifier, ...],
) -> None:
    namespaces: dict[str, str] = {}
    for identifier in identifiers:
        prior = namespaces.get(identifier.namespace)
        if prior is not None and prior != identifier.value:
            raise ContractError(
                ReasonCode.CONFLICTING_SOURCE_MAPPING,
                f"namespace {identifier.namespace!r} maps to conflicting values",
            )
        namespaces[identifier.namespace] = identifier.value


def _require_sport_native_identifiers(
    identifiers: tuple[SportNativeIdentifier, ...],
) -> None:
    if any(not isinstance(identifier, SportNativeIdentifier) for identifier in identifiers):
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "canonical identity accepts only authoritative sport-native identifiers",
        )


for _contract in (
    ValidationReason,
    NativeIdentifier,
    SportNativeIdentifier,
    SourceMapping,
    ParticipantRef,
    CanonicalEvent,
    Evidence,
    Provenance,
    CandidateEvaluation,
    ReconciliationResult,
):
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(
    ValidationReason,
    NativeIdentifier,
    SportNativeIdentifier,
    SourceMapping,
    ParticipantRef,
    CanonicalEvent,
    Evidence,
    Provenance,
    CandidateEvaluation,
    ReconciliationResult,
)
