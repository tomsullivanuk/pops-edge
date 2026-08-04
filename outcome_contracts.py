"""Immutable provider-neutral outcome Evidence and append-only history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from event_contracts import (
    ContractError,
    ReasonCode,
    SerializableContract,
    ValidationStatus,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)


class OutcomeStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    DELAYED = "delayed"
    POSTPONED = "postponed"
    SUSPENDED = "suspended"
    FINAL = "final"
    CANCELLED = "cancelled"
    NO_CONTEST = "no-contest"
    FORFEIT = "forfeit"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True, order=True)
class OutcomeIssue:
    code: str
    detail: str

    def __post_init__(self) -> None:
        _require_identifier(self.code, "outcome issue code")
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "outcome issue detail")


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    observation_id: str
    canonical_event_id: str
    authoritative_provider_id: str
    provider_event_id: str
    provider_status: OutcomeStatus
    provider_status_detail: str
    away_participant_id: str
    home_participant_id: str
    scheduled_start: datetime
    collected_at: datetime
    raw_evidence_sha256: str
    canonical_evidence_sha256: str
    source_url: str
    collector_version: str
    validation_status: ValidationStatus
    away_score: int | None = None
    home_score: int | None = None
    winning_participant_id: str | None = None
    losing_participant_id: str | None = None
    tie: bool = False
    unresolved: bool = True
    completed_periods: int | None = None
    provider_result_at: datetime | None = None
    issues: tuple[OutcomeIssue, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.observation_id, "observation_id"),
            (self.canonical_event_id, "canonical_event_id"),
            (self.authoritative_provider_id, "authoritative_provider_id"),
            (self.provider_event_id, "provider_event_id"),
            (self.away_participant_id, "away_participant_id"),
            (self.home_participant_id, "home_participant_id"),
            (self.collector_version, "collector_version"),
        ):
            _require_identifier(value, label)
        _require_text(self.provider_status_detail, ReasonCode.UNSUPPORTED_STATUS, "provider_status_detail")
        _require_text(self.source_url, ReasonCode.VALIDATION_FAILURE, "source_url")
        _require_aware(self.scheduled_start, "scheduled_start")
        _require_aware(self.collected_at, "collected_at")
        if self.provider_result_at is not None:
            _require_aware(self.provider_result_at, "provider_result_at")
        if self.away_participant_id == self.home_participant_id:
            raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS, "outcome participants must differ")
        for value, label in ((self.away_score, "away_score"), (self.home_score, "home_score"), (self.completed_periods, "completed_periods")):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ContractError(ReasonCode.VALIDATION_FAILURE, f"{label} must be a non-negative integer")
        for digest, label in ((self.raw_evidence_sha256, "raw_evidence_sha256"), (self.canonical_evidence_sha256, "canonical_evidence_sha256")):
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ContractError(ReasonCode.VALIDATION_FAILURE, f"{label} must be a lowercase SHA-256 digest")
        participants = {self.away_participant_id, self.home_participant_id}
        if self.winning_participant_id is not None and self.winning_participant_id not in participants:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "winner is not an event participant")
        if self.losing_participant_id is not None and self.losing_participant_id not in participants:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "loser is not an event participant")
        if (self.winning_participant_id is None) != (self.losing_participant_id is None):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "winner and loser must be supplied together")
        if self.winning_participant_id == self.losing_participant_id and self.winning_participant_id is not None:
            raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS, "winner and loser must differ")
        if self.provider_status is not OutcomeStatus.FINAL and self.winning_participant_id is not None:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "non-final outcome cannot claim a winner")
        if self.tie and self.winning_participant_id is not None:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "a tied outcome cannot claim a winner")
        if self.validation_status is ValidationStatus.VALID and self.issues:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "valid outcome cannot carry issues")
        if self.validation_status is not ValidationStatus.VALID and not self.issues:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "non-valid outcome requires structured issues")
        object.__setattr__(self, "issues", tuple(sorted(self.issues)))

    @property
    def authoritative_final(self) -> bool:
        return (
            self.provider_status is OutcomeStatus.FINAL
            and self.validation_status is ValidationStatus.VALID
            and self.winning_participant_id is not None
            and not self.tie
            and not self.unresolved
        )


@dataclass(frozen=True, slots=True)
class OutcomeHistory:
    canonical_event_id: str
    authoritative_provider_id: str
    observations: tuple[OutcomeObservation, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.canonical_event_id, "canonical_event_id")
        _require_identifier(self.authoritative_provider_id, "authoritative_provider_id")
        if not self.observations:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "outcome history cannot be empty")
        ordered = tuple(sorted(self.observations, key=lambda item: (item.collected_at, item.observation_id)))
        ids = [item.observation_id for item in ordered]
        if len(ids) != len(set(ids)):
            raise ContractError(ReasonCode.CONTRADICTORY_LINEAGE, "duplicate outcome observation identity")
        if any(item.canonical_event_id != self.canonical_event_id for item in ordered):
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "outcome history mixes events")
        if any(item.authoritative_provider_id != self.authoritative_provider_id for item in ordered):
            raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING, "outcome history mixes providers")
        provider_ids = {item.provider_event_id for item in ordered}
        if len(provider_ids) != 1:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "outcome history mixes provider events")
        object.__setattr__(self, "observations", ordered)

    @property
    def latest(self) -> OutcomeObservation:
        return self.observations[-1]

    def append(self, observation: OutcomeObservation) -> "OutcomeHistory":
        return OutcomeHistory(
            self.canonical_event_id,
            self.authoritative_provider_id,
            self.observations + (observation,),
        )

    @property
    def latest_authoritative_final(self) -> OutcomeObservation | None:
        finals = tuple(item for item in self.observations if item.authoritative_final)
        if len(finals) > 1 and finals[-2].collected_at == finals[-1].collected_at:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "authoritative corrected finals require unambiguous collection chronology",
            )
        return finals[-1] if finals else None


_CONTRACTS = (OutcomeIssue, OutcomeObservation, OutcomeHistory)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(OutcomeStatus,))
