"""MLB-specific immutable contracts built on the reusable event boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from event_contracts import (
    CanonicalEvent,
    ContractError,
    ParticipantRef,
    Provenance,
    ReasonCode,
    SerializableContract,
    SportNativeIdentifier,
    ValidationReason,
    ValidationStatus,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)


class PitcherState(str, Enum):
    PROBABLE = "probable"
    CONFIRMED = "confirmed"
    ACTUAL = "actual"
    MISSING = "missing"
    CHANGED = "changed"


class GameStatus(str, Enum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    POSTPONED = "postponed"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


class LineageType(str, Enum):
    POSTPONED_FROM = "postponed_from"
    RESCHEDULED_AS = "rescheduled_as"
    RESUMED_FROM_SUSPENSION = "resumed_from_suspension"
    REPLACEMENT_GAME = "replacement_game"
    DOUBLEHEADER_COMPANION = "doubleheader_companion"
    ORIGINALLY_SCHEDULED_EVENT = "originally_scheduled_event"


@dataclass(frozen=True, slots=True)
class MLBTeamRef:
    canonical_team_id: str
    mlb_team_id: int
    display_name: str
    abbreviation: str

    def __post_init__(self) -> None:
        _require_identifier(self.canonical_team_id, "canonical_team_id")
        if not isinstance(self.mlb_team_id, int) or self.mlb_team_id <= 0:
            raise ContractError(
                ReasonCode.MALFORMED_IDENTIFIER, "mlb_team_id must be a positive integer"
            )
        _require_text(
            self.display_name, ReasonCode.MISSING_PARTICIPANT, "team display_name"
        )
        _require_identifier(self.abbreviation, "team abbreviation")

    def as_participant(self) -> ParticipantRef:
        return ParticipantRef(
            canonical_id=self.canonical_team_id,
            display_name=self.display_name,
            native_identifiers=(
                SportNativeIdentifier("mlb_team", str(self.mlb_team_id)),
            ),
        )


@dataclass(frozen=True, slots=True)
class MLBGame:
    event: CanonicalEvent
    game_pk: int
    home_team: MLBTeamRef
    away_team: MLBTeamRef
    season: str
    game_type: str
    game_number: int | None = None
    doubleheader_designation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.game_pk, int) or self.game_pk <= 0:
            raise ContractError(
                ReasonCode.MISSING_GAME_PK, "game_pk must be a positive integer"
            )
        _require_identifier(self.season, "MLB season")
        _require_identifier(self.game_type, "MLB game_type")
        if self.home_team.canonical_team_id == self.away_team.canonical_team_id:
            raise ContractError(
                ReasonCode.IDENTICAL_PARTICIPANTS,
                "home and away teams must be distinct",
            )
        if self.event.sport.lower() != "baseball" or self.event.competition != "MLB":
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "MLBGame requires a baseball/MLB canonical event",
            )
        if self.event.season != self.season:
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "MLB season conflicts with canonical event season",
            )
        expected_participants = {
            self.home_team.canonical_team_id,
            self.away_team.canonical_team_id,
        }
        actual_participants = {
            participant.canonical_id for participant in self.event.participants
        }
        if actual_participants != expected_participants:
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "MLB teams conflict with canonical event participants",
            )
        game_pk_mappings = tuple(
            item.value
            for item in self.event.native_identifiers
            if item.namespace == "mlb_game"
        )
        if not game_pk_mappings:
            raise ContractError(
                ReasonCode.MISSING_GAME_PK,
                "canonical event must preserve an mlb_game mapping",
            )
        if game_pk_mappings != (str(self.game_pk),):
            raise ContractError(
                ReasonCode.CONFLICTING_GAME_PK,
                "canonical event MLB mapping conflicts with game_pk",
            )
        if self.game_number is not None and self.game_number <= 0:
            raise ContractError(
                ReasonCode.DOUBLEHEADER_AMBIGUITY,
                "game_number must be positive when provided",
            )
        if (self.game_number is None) != (self.doubleheader_designation is None):
            raise ContractError(
                ReasonCode.DOUBLEHEADER_AMBIGUITY,
                "game_number and doubleheader_designation must be supplied together",
            )
        if self.doubleheader_designation is not None:
            _require_identifier(
                self.doubleheader_designation, "doubleheader_designation"
            )


def make_mlb_game(
    *,
    game_pk: int,
    home_team: MLBTeamRef,
    away_team: MLBTeamRef,
    season: str,
    game_type: str = "regular",
    game_number: int | None = None,
    doubleheader_designation: str | None = None,
    canonical_event_id: str | None = None,
) -> MLBGame:
    if not isinstance(game_pk, int) or game_pk <= 0:
        raise ContractError(ReasonCode.MISSING_GAME_PK, "game_pk is required")
    event = CanonicalEvent(
        sport="baseball",
        competition="MLB",
        season=season,
        canonical_event_id=canonical_event_id or f"mlb:{game_pk}",
        participants=(away_team.as_participant(), home_team.as_participant()),
        native_identifiers=(SportNativeIdentifier("mlb_game", str(game_pk)),),
    )
    return MLBGame(
        event=event,
        game_pk=game_pk,
        home_team=home_team,
        away_team=away_team,
        season=season,
        game_type=game_type,
        game_number=game_number,
        doubleheader_designation=doubleheader_designation,
    )


@dataclass(frozen=True, slots=True)
class PitcherRef:
    provider: str
    source_pitcher_id: str
    display_name: str
    canonical_pitcher_id: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.provider, "pitcher provider")
        _require_identifier(self.source_pitcher_id, "source_pitcher_id")
        _require_text(
            self.display_name, ReasonCode.MISSING_IDENTIFIER, "pitcher display_name"
        )
        if self.canonical_pitcher_id is not None:
            _require_identifier(self.canonical_pitcher_id, "canonical_pitcher_id")


@dataclass(frozen=True, slots=True)
class ScheduleObservation:
    observation_id: str
    canonical_event_id: str
    scheduled_start: datetime
    provenance: Provenance
    source_reported_datetime: str | None = None
    venue: str | None = None
    game_number: int | None = None
    doubleheader_designation: str | None = None
    status_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_observation_identity(
            self.observation_id, self.canonical_event_id, self.provenance
        )
        _require_aware(self.scheduled_start, "scheduled_start")
        if self.source_reported_datetime is not None:
            _require_text(
                self.source_reported_datetime,
                ReasonCode.VALIDATION_FAILURE,
                "source_reported_datetime",
            )
        if self.venue is not None:
            _require_text(self.venue, ReasonCode.VALIDATION_FAILURE, "venue")
        if self.game_number is not None and self.game_number <= 0:
            raise ContractError(
                ReasonCode.DOUBLEHEADER_AMBIGUITY,
                "game_number must be positive when provided",
            )
        if (self.game_number is None) != (self.doubleheader_designation is None):
            raise ContractError(
                ReasonCode.DOUBLEHEADER_AMBIGUITY,
                "schedule game_number and doubleheader designation must be paired",
            )
        if self.doubleheader_designation is not None:
            _require_identifier(
                self.doubleheader_designation, "doubleheader_designation"
            )


@dataclass(frozen=True, slots=True)
class PitcherObservation:
    observation_id: str
    canonical_event_id: str
    home_pitcher: PitcherRef | None
    away_pitcher: PitcherRef | None
    home_state: PitcherState
    away_state: PitcherState
    provenance: Provenance
    replaces_observation_id: str | None = None

    def __post_init__(self) -> None:
        _validate_observation_identity(
            self.observation_id, self.canonical_event_id, self.provenance
        )
        _validate_pitcher_side(self.home_pitcher, self.home_state, "home")
        _validate_pitcher_side(self.away_pitcher, self.away_state, "away")
        missing = self.home_pitcher is None or self.away_pitcher is None
        if missing and self.provenance.validation_status is not ValidationStatus.INCOMPLETE:
            raise ContractError(
                ReasonCode.MISSING_PITCHER,
                "missing pitchers require an incomplete provenance state",
            )
        if self.replaces_observation_id is not None:
            _require_identifier(
                self.replaces_observation_id, "replaces_observation_id"
            )
        if (
            PitcherState.CHANGED in (self.home_state, self.away_state)
            and self.replaces_observation_id is None
        ):
            raise ContractError(
                ReasonCode.PITCHER_CHANGED,
                "a changed pitcher observation must reference the prior observation",
            )


@dataclass(frozen=True, slots=True)
class GameStatusObservation:
    observation_id: str
    canonical_event_id: str
    status: GameStatus
    source_reported_status: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _validate_observation_identity(
            self.observation_id, self.canonical_event_id, self.provenance
        )
        _require_text(
            self.source_reported_status,
            ReasonCode.UNSUPPORTED_STATUS,
            "source_reported_status",
        )
        if (
            self.status in (GameStatus.UNKNOWN, GameStatus.UNSUPPORTED)
            and self.provenance.validation_status is ValidationStatus.VALID
        ):
            raise ContractError(
                ReasonCode.UNSUPPORTED_STATUS,
                "unknown or unsupported status cannot be marked valid",
            )


@dataclass(frozen=True, slots=True)
class ScheduleLineage:
    relationship_id: str
    from_event_id: str
    to_event_id: str
    relationship: LineageType
    provenance: Provenance
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.relationship_id, "relationship_id")
        _require_identifier(self.from_event_id, "from_event_id")
        _require_identifier(self.to_event_id, "to_event_id")
        if self.from_event_id == self.to_event_id:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "lineage must relate distinct canonical events",
            )
        if self.provenance.canonical_event_id not in (
            self.from_event_id,
            self.to_event_id,
        ):
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "lineage provenance must map to one related event",
            )
        if not self.evidence:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "lineage requires explicit source evidence",
            )
        for item in self.evidence:
            _require_text(item, ReasonCode.CONTRADICTORY_LINEAGE, "lineage evidence")


def _validate_observation_identity(
    observation_id: str, canonical_event_id: str, provenance: Provenance
) -> None:
    _require_identifier(observation_id, "observation_id")
    _require_identifier(canonical_event_id, "canonical_event_id")
    if provenance.canonical_event_id != canonical_event_id:
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "observation and provenance map to different canonical events",
        )


def _validate_pitcher_side(
    pitcher: PitcherRef | None, state: PitcherState, side: str
) -> None:
    if pitcher is None and state is not PitcherState.MISSING:
        raise ContractError(
            ReasonCode.MISSING_PITCHER,
            f"{side} pitcher must use missing state when no reference is available",
        )
    if pitcher is not None and state is PitcherState.MISSING:
        raise ContractError(
            ReasonCode.MISSING_PITCHER,
            f"{side} pitcher reference conflicts with missing state",
        )


for _contract in (
    MLBTeamRef,
    MLBGame,
    PitcherRef,
    ScheduleObservation,
    PitcherObservation,
    GameStatusObservation,
    ScheduleLineage,
):
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(
    MLBTeamRef,
    MLBGame,
    PitcherRef,
    ScheduleObservation,
    PitcherObservation,
    GameStatusObservation,
    ScheduleLineage,
    enums=(PitcherState, GameStatus, LineageType),
)
