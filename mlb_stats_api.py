"""Read-only MLB Stats API client and replaceable MLB facts adapter.

No network activity occurs on import. The adapter translates provider-native
schedule records into the existing immutable MLB contracts and contains no
forecast, market, persistence, valuation, or wagering behavior.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Callable, Protocol

import requests

from event_contracts import (
    ContractError,
    Provenance,
    ReasonCode,
    SerializableContract,
    ValidationReason,
    ValidationStatus,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)
from mlb_contracts import (
    GameStatus,
    GameStatusObservation,
    LineageType,
    MLBGame,
    MLBTeamRef,
    PitcherObservation,
    PitcherRef,
    PitcherState,
    ScheduleLineage,
    ScheduleObservation,
    make_mlb_game,
)


PROVIDER_ID = "mlb-stats-api"
ADAPTER_VERSION = "1"
BASE_URL = "https://statsapi.mlb.com/api/v1"
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class MLBStatsAPIError(RuntimeError):
    """Deterministic read-only client failure."""

    def __init__(self, code: str, detail: str, *, status_code: int | None = None):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(f"{code}: {detail}")


class ResponseLike(Protocol):
    status_code: int
    url: str
    content: bytes

    def json(self) -> Any: ...


class TransportLike(Protocol):
    def get(
        self, url: str, *, params: dict[str, str], timeout: float
    ) -> ResponseLike: ...


@dataclass(frozen=True, slots=True)
class MLBStatsAPIResponse:
    endpoint: str
    parameters: tuple[tuple[str, str], ...]
    collected_at: datetime
    status_code: int
    source_url: str
    payload: dict[str, Any]
    raw_body: bytes


class MLBStatsAPIClient:
    """Small injectable client for supported MLB schedule requests."""

    def __init__(
        self,
        *,
        transport: TransportLike | None = None,
        timeout: float = 15.0,
        retry_delays: tuple[float, ...] = (0.25, 1.0),
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if any(delay < 0 for delay in retry_delays):
            raise ValueError("retry delays cannot be negative")
        self._transport = transport or requests.Session()
        self.timeout = timeout
        self.retry_delays = retry_delays
        self._sleeper = sleeper
        self._clock = clock

    @staticmethod
    def schedule_request(
        query_date: date, *, game_pk: int | None = None
    ) -> tuple[str, tuple[tuple[str, str], ...]]:
        parameters = {
            "date": query_date.isoformat(),
            "hydrate": "probablePitcher,team,venue",
            "sportId": "1",
        }
        if game_pk is not None:
            if not isinstance(game_pk, int) or game_pk <= 0:
                raise ValueError("game_pk must be a positive integer")
            parameters["gamePk"] = str(game_pk)
        return f"{BASE_URL}/schedule", tuple(sorted(parameters.items()))

    def fetch_schedule(
        self,
        query_date: date,
        *,
        game_pk: int | None = None,
        collected_at: datetime | None = None,
    ) -> MLBStatsAPIResponse:
        endpoint, parameter_items = self.schedule_request(query_date, game_pk=game_pk)
        parameters = dict(parameter_items)
        collected = collected_at or self._clock()
        _require_aware(collected, "collection timestamp")
        response: ResponseLike | None = None
        attempts = len(self.retry_delays) + 1
        for attempt in range(attempts):
            try:
                response = self._transport.get(
                    endpoint, params=parameters, timeout=self.timeout
                )
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt == attempts - 1:
                    raise MLBStatsAPIError(
                        "transport_failure", type(error).__name__
                    ) from error
                self._sleeper(self.retry_delays[attempt])
                continue
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == attempts - 1:
                    raise MLBStatsAPIError(
                        "retryable_http_failure",
                        f"HTTP {response.status_code} after {attempts} attempts",
                        status_code=response.status_code,
                    )
                self._sleeper(self.retry_delays[attempt])
                continue
            if response.status_code < 200 or response.status_code >= 300:
                raise MLBStatsAPIError(
                    "permanent_http_failure",
                    f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )
            raw_body = bytes(response.content)
            try:
                payload = response.json()
            except (ValueError, json.JSONDecodeError) as error:
                raise MLBStatsAPIError("malformed_json", "response is not JSON") from error
            if not isinstance(payload, dict):
                raise MLBStatsAPIError(
                    "unsupported_response_shape", "response root must be an object"
                )
            return MLBStatsAPIResponse(
                endpoint=endpoint,
                parameters=parameter_items,
                collected_at=collected,
                status_code=response.status_code,
                source_url=response.url,
                payload=payload,
                raw_body=raw_body,
            )
        raise AssertionError("unreachable request state")


class AdapterComponent(str, Enum):
    SOURCE = "source"
    EVENT = "event"
    SCHEDULE = "schedule"
    STATUS = "status"
    PITCHER = "pitcher"
    LINEAGE = "lineage"


class AdapterIssueSeverity(str, Enum):
    WARNING = "warning"
    INCOMPLETE = "incomplete"
    REJECTED = "rejected"


class AdapterOutcome(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    REJECTED = "rejected"


class AdapterIssueCode(str, Enum):
    MISSING_GAME_PK = "missing-game-pk"
    MALFORMED_GAME_PK = "malformed-game-pk"
    CONFLICTING_GAME_PK = "conflicting-game-pk"
    MISSING_SEASON = "missing-season"
    MISSING_TEAM_ID = "missing-team-id"
    MALFORMED_TEAM = "malformed-team"
    IDENTICAL_TEAMS = "identical-teams"
    MISSING_SCHEDULED_START = "missing-scheduled-start"
    MALFORMED_TIMESTAMP = "malformed-timestamp"
    MISSING_SOURCE_TIMESTAMP = "missing-source-timestamp"
    MISSING_VENUE = "missing-venue"
    INCOMPLETE_DOUBLEHEADER = "incomplete-doubleheader"
    MISSING_HOME_PITCHER = "missing-home-pitcher"
    MISSING_AWAY_PITCHER = "missing-away-pitcher"
    MALFORMED_PITCHER = "malformed-pitcher"
    PITCHER_CHANGED = "pitcher-changed"
    UNSUPPORTED_STATUS = "unsupported-status"
    UNPROVEN_LINEAGE = "unproven-lineage"
    UNSUPPORTED_SOURCE_SHAPE = "unsupported-source-shape"


@dataclass(frozen=True, slots=True, order=True)
class AdapterIssue:
    component: AdapterComponent
    code: AdapterIssueCode
    severity: AdapterIssueSeverity
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "adapter issue")


@dataclass(frozen=True, slots=True)
class RawSourceEvidence:
    provider: str
    endpoint: str
    request_parameters: tuple[tuple[str, str], ...]
    collected_at: datetime
    http_status: int
    source_record_ids: tuple[str, ...]
    raw_response_sha256: str
    canonical_json_sha256: str
    raw_payload_ref: str
    adapter_version: str
    source_url: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.provider, "raw evidence provider")
        _require_text(self.endpoint, ReasonCode.VALIDATION_FAILURE, "endpoint")
        _require_aware(self.collected_at, "raw evidence collected_at")
        if not isinstance(self.http_status, int) or self.http_status < 100:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE, "http_status must be valid"
            )
        for field_name, digest in (
            ("raw_response_sha256", self.raw_response_sha256),
            ("canonical_json_sha256", self.canonical_json_sha256),
        ):
            if len(digest) != 64 or any(
                char not in "0123456789abcdef" for char in digest
            ):
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    f"{field_name} must be lowercase SHA-256",
                )
        _require_identifier(self.raw_payload_ref, "raw_payload_ref")
        _require_identifier(self.adapter_version, "adapter_version")
        for key, value in self.request_parameters:
            _require_identifier(key, "request parameter name")
            _require_text(value, ReasonCode.VALIDATION_FAILURE, "request parameter")
        object.__setattr__(
            self, "request_parameters", tuple(sorted(self.request_parameters))
        )
        object.__setattr__(
            self, "source_record_ids", tuple(sorted(set(self.source_record_ids)))
        )
        for source_record_id in self.source_record_ids:
            _require_identifier(source_record_id, "source_record_id")


@dataclass(frozen=True, slots=True)
class MLBStatsGameResult:
    source_record_id: str
    raw_evidence: RawSourceEvidence
    outcome: AdapterOutcome
    game: MLBGame | None = None
    schedule_observation: ScheduleObservation | None = None
    status_observation: GameStatusObservation | None = None
    pitcher_observation: PitcherObservation | None = None
    lineages: tuple[ScheduleLineage, ...] = ()
    issues: tuple[AdapterIssue, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.source_record_id, "source_record_id")
        object.__setattr__(self, "lineages", tuple(sorted(self.lineages, key=lambda x: x.relationship_id)))
        object.__setattr__(self, "issues", tuple(sorted(set(self.issues))))
        if self.game is None and any(
            item is not None
            for item in (
                self.schedule_observation,
                self.status_observation,
                self.pitcher_observation,
            )
        ):
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "normalized observations require a canonical MLB game",
            )
        if self.outcome is AdapterOutcome.REJECTED:
            if self.game is not None:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "rejected adapter outcome cannot expose a canonical game",
                )
            if not any(
                issue.severity is AdapterIssueSeverity.REJECTED
                for issue in self.issues
            ):
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "rejected adapter outcome requires a rejected issue",
                )
        elif self.game is None:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "complete or partial adapter outcome requires a canonical game",
            )
        if self.outcome is AdapterOutcome.COMPLETE and self.issues:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "complete adapter outcome cannot carry issues",
            )
        if self.outcome is AdapterOutcome.COMPLETE and any(
            item is None
            for item in (
                self.schedule_observation,
                self.status_observation,
                self.pitcher_observation,
            )
        ):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "complete adapter outcome requires every supported observation",
            )
        if self.outcome is AdapterOutcome.PARTIAL and not self.issues:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "partial adapter outcome requires structured issues",
            )

    @property
    def accepted(self) -> bool:
        return self.outcome is not AdapterOutcome.REJECTED


@dataclass(frozen=True, slots=True)
class MLBStatsAdapterResult:
    raw_evidence: RawSourceEvidence
    games: tuple[MLBStatsGameResult, ...]
    issues: tuple[AdapterIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "games",
            tuple(sorted(self.games, key=lambda item: item.source_record_id)),
        )
        object.__setattr__(self, "issues", tuple(sorted(set(self.issues))))


class MLBStatsAPIAdapter:
    def parse_response(
        self,
        response: MLBStatsAPIResponse,
        *,
        prior_pitchers: dict[int, PitcherObservation] | None = None,
    ) -> MLBStatsAdapterResult:
        raw = self._raw_evidence(response)
        records, response_issues = self._game_records(response.payload)
        prior = prior_pitchers or {}
        results = tuple(
            self.parse_game(
                record,
                raw,
                prior_pitcher=(
                    prior.get(record.get("gamePk"))
                    if isinstance(record.get("gamePk"), int)
                    else None
                ),
            )
            for record in records
        )
        return MLBStatsAdapterResult(raw, results, response_issues)

    def parse_game(
        self,
        record: dict[str, Any],
        raw: RawSourceEvidence,
        *,
        prior_pitcher: PitcherObservation | None = None,
    ) -> MLBStatsGameResult:
        issues: list[AdapterIssue] = []
        source_record_id = self._source_record_id(record)
        try:
            game_pk = self._game_pk(record)
            season = self._required_identifier(record.get("season"), "season")
            scheduled_start = self._scheduled_start(record)
            away = self._team(record, "away")
            home = self._team(record, "home")
            game_number, doubleheader = self._doubleheader(record, issues)
            game = make_mlb_game(
                game_pk=game_pk,
                away_team=away,
                home_team=home,
                season=season,
                game_type=self._game_type(record),
                game_number=game_number,
                doubleheader_designation=doubleheader,
            )
        except (ContractError, KeyError, TypeError, ValueError) as error:
            issues.append(self._identity_issue(error))
            return MLBStatsGameResult(
                source_record_id,
                raw,
                AdapterOutcome.REJECTED,
                issues=tuple(issues),
            )

        canonical_id = game.event.canonical_event_id
        source_timestamp, timestamp_issue = self._optional_source_timestamp(record)
        if timestamp_issue is not None:
            issues.append(timestamp_issue)
        venue = self._venue(record)
        schedule_reasons: list[ValidationReason] = []
        schedule_component_issues = tuple(
            issue
            for issue in issues
            if issue.component is AdapterComponent.SCHEDULE
            and issue.severity is AdapterIssueSeverity.INCOMPLETE
        )
        if venue is None:
            issues.append(
                AdapterIssue(
                    AdapterComponent.SCHEDULE,
                    AdapterIssueCode.MISSING_VENUE,
                    AdapterIssueSeverity.INCOMPLETE,
                    "source venue is absent",
                )
            )
            schedule_reasons.append(
                ValidationReason(ReasonCode.VALIDATION_FAILURE, "source venue is absent")
            )
        schedule_reasons.extend(
            ValidationReason(ReasonCode.VALIDATION_FAILURE, issue.detail)
            for issue in schedule_component_issues
        )
        schedule_provenance = self._provenance(
            raw,
            source_record_id,
            canonical_id,
            source_timestamp,
            ValidationStatus.INCOMPLETE if schedule_reasons else ValidationStatus.VALID,
            tuple(schedule_reasons),
        )
        schedule = ScheduleObservation(
            observation_id=self._observation_id("schedule", game_pk, raw.collected_at),
            canonical_event_id=canonical_id,
            scheduled_start=scheduled_start,
            provenance=schedule_provenance,
            source_reported_datetime=self._optional_text(record.get("gameDate")),
            venue=venue,
            game_number=game_number,
            doubleheader_designation=doubleheader,
            status_evidence=self._schedule_status_evidence(record),
        )

        status_value, status_reasons, status_issue = self._status(record)
        if status_issue is not None:
            issues.append(status_issue)
        status_provenance = self._provenance(
            raw,
            source_record_id,
            canonical_id,
            source_timestamp,
            ValidationStatus.INCOMPLETE if status_reasons else ValidationStatus.VALID,
            status_reasons,
        )
        status = GameStatusObservation(
            observation_id=self._observation_id("status", game_pk, raw.collected_at),
            canonical_event_id=canonical_id,
            status=status_value,
            source_reported_status=self._source_status(record),
            provenance=status_provenance,
        )

        pitcher, pitcher_issues = self._pitchers(
            record, game_pk, canonical_id, raw, source_timestamp, prior_pitcher
        )
        issues.extend(pitcher_issues)
        return MLBStatsGameResult(
            source_record_id=source_record_id,
            raw_evidence=raw,
            outcome=(AdapterOutcome.PARTIAL if issues else AdapterOutcome.COMPLETE),
            game=game,
            schedule_observation=schedule,
            status_observation=status,
            pitcher_observation=pitcher,
            issues=tuple(issues),
        )

    def explicit_lineage(
        self,
        *,
        from_game: MLBGame,
        to_game: MLBGame,
        relationship: LineageType,
        raw: RawSourceEvidence,
        source_record_id: str,
        source_relation_field: str,
        source_related_game_pk: int,
        source_evidence: tuple[str, ...] = (),
    ) -> ScheduleLineage:
        """Translate a direct source relation field; never infer similarity."""

        _require_identifier(source_relation_field, "source_relation_field")
        if source_related_game_pk != from_game.game_pk:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "explicit source relation must identify the related from-game gamePk",
            )
        evidence = (
            f"{source_relation_field}={source_related_game_pk}",
        ) + source_evidence

        provenance = self._provenance(
            raw,
            source_record_id,
            to_game.event.canonical_event_id,
            None,
            ValidationStatus.VALID,
            (),
        )
        return ScheduleLineage(
            relationship_id=(
                f"mlb-stats-api:lineage:{from_game.game_pk}:{to_game.game_pk}:"
                f"{relationship.value}"
            ),
            from_event_id=from_game.event.canonical_event_id,
            to_event_id=to_game.event.canonical_event_id,
            relationship=relationship,
            provenance=provenance,
            evidence=evidence,
        )

    def _raw_evidence(self, response: MLBStatsAPIResponse) -> RawSourceEvidence:
        canonical = json.dumps(
            response.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        raw_digest = hashlib.sha256(response.raw_body).hexdigest()
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        record_ids = tuple(
            self._source_record_id(record)
            for record in self._game_records(response.payload)[0]
        )
        return RawSourceEvidence(
            provider=PROVIDER_ID,
            endpoint=response.endpoint,
            request_parameters=response.parameters,
            collected_at=response.collected_at,
            http_status=response.status_code,
            source_record_ids=record_ids,
            raw_response_sha256=raw_digest,
            canonical_json_sha256=canonical_digest,
            raw_payload_ref=f"sha256:{raw_digest}",
            adapter_version=ADAPTER_VERSION,
            source_url=response.source_url,
        )

    def _game_records(
        self, payload: dict[str, Any]
    ) -> tuple[tuple[dict[str, Any], ...], tuple[AdapterIssue, ...]]:
        dates = payload.get("dates")
        if not isinstance(dates, list):
            issue = AdapterIssue(
                AdapterComponent.SOURCE,
                AdapterIssueCode.UNSUPPORTED_SOURCE_SHAPE,
                AdapterIssueSeverity.REJECTED,
                "schedule response requires a dates array",
            )
            return (), (issue,)
        records: list[dict[str, Any]] = []
        issues: list[AdapterIssue] = []
        for date_record in dates:
            games = date_record.get("games") if isinstance(date_record, dict) else None
            if not isinstance(games, list):
                issues.append(
                    AdapterIssue(
                        AdapterComponent.SOURCE,
                        AdapterIssueCode.UNSUPPORTED_SOURCE_SHAPE,
                        AdapterIssueSeverity.REJECTED,
                        "schedule date requires a games array",
                    )
                )
                continue
            for game in games:
                if isinstance(game, dict):
                    records.append(game)
                else:
                    issues.append(
                        AdapterIssue(
                            AdapterComponent.SOURCE,
                            AdapterIssueCode.UNSUPPORTED_SOURCE_SHAPE,
                            AdapterIssueSeverity.REJECTED,
                            "game record must be an object",
                        )
                    )
        return tuple(records), tuple(sorted(set(issues)))

    def _game_pk(self, record: dict[str, Any]) -> int:
        value = record.get("gamePk")
        if value is None:
            raise ContractError(ReasonCode.MISSING_GAME_PK, "gamePk is absent")
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ContractError(ReasonCode.MALFORMED_IDENTIFIER, "gamePk is malformed")
        conflicting = record.get("officialGamePk")
        if conflicting is not None and conflicting != value:
            raise ContractError(ReasonCode.CONFLICTING_GAME_PK, "gamePk values conflict")
        return value

    def _team(self, record: dict[str, Any], side: str) -> MLBTeamRef:
        team = record["teams"][side]["team"]
        team_id = team.get("id")
        if not isinstance(team_id, int) or isinstance(team_id, bool) or team_id <= 0:
            raise ContractError(
                ReasonCode.MISSING_PARTICIPANT, f"{side} MLB team id is absent"
            )
        name = self._required_text(team.get("name"), f"{side} team name")
        abbreviation = team.get("abbreviation") or team.get("teamCode")
        abbreviation = self._required_identifier(
            abbreviation, f"{side} team abbreviation"
        )
        return MLBTeamRef(
            canonical_team_id=f"mlb-team:{team_id}",
            mlb_team_id=team_id,
            display_name=name,
            abbreviation=abbreviation,
        )

    def _scheduled_start(self, record: dict[str, Any]) -> datetime:
        value = record.get("gameDate")
        if not isinstance(value, str) or not value.strip():
            raise ContractError(
                ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY, "gameDate is absent"
            )
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ContractError(
                ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY, "gameDate is malformed"
            ) from error
        _require_aware(timestamp, "gameDate")
        return timestamp

    def _optional_source_timestamp(
        self, record: dict[str, Any]
    ) -> tuple[datetime | None, AdapterIssue | None]:
        value = record.get("lastUpdated")
        if value is None:
            return None, AdapterIssue(
                AdapterComponent.SOURCE,
                AdapterIssueCode.MISSING_SOURCE_TIMESTAMP,
                AdapterIssueSeverity.WARNING,
                "source publication or update timestamp is unavailable",
            )
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            _require_aware(timestamp, "lastUpdated")
            return timestamp, None
        except (ContractError, ValueError):
            return None, AdapterIssue(
                AdapterComponent.SOURCE,
                AdapterIssueCode.MALFORMED_TIMESTAMP,
                AdapterIssueSeverity.WARNING,
                "source lastUpdated timestamp is malformed and remains unknown",
            )

    def _doubleheader(
        self, record: dict[str, Any], issues: list[AdapterIssue]
    ) -> tuple[int | None, str | None]:
        designation = record.get("doubleHeader")
        number = record.get("gameNumber")
        if designation in (None, "N", "n", ""):
            return None, None
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            issues.append(
                AdapterIssue(
                    AdapterComponent.SCHEDULE,
                    AdapterIssueCode.INCOMPLETE_DOUBLEHEADER,
                    AdapterIssueSeverity.INCOMPLETE,
                    "doubleheader designation lacks a valid game number",
                )
            )
            return None, None
        return number, str(designation)

    def _status(
        self, record: dict[str, Any]
    ) -> tuple[GameStatus, tuple[ValidationReason, ...], AdapterIssue | None]:
        source = self._source_status(record)
        normalized = source.casefold()
        mappings = (
            (("scheduled", "pre-game", "warmup"), GameStatus.SCHEDULED),
            (("delayed", "delayed start"), GameStatus.DELAYED),
            (("postponed",), GameStatus.POSTPONED),
            (("suspended",), GameStatus.SUSPENDED),
            (("resumed",), GameStatus.RESUMED),
            (("in progress", "manager challenge", "review"), GameStatus.IN_PROGRESS),
            (("final", "game over", "completed early"), GameStatus.FINAL),
            (("cancelled", "canceled"), GameStatus.CANCELLED),
        )
        for labels, status in mappings:
            if normalized in labels:
                return status, (), None
        reason = ValidationReason(
            ReasonCode.UNSUPPORTED_STATUS, f"unsupported MLB status: {source}"
        )
        issue = AdapterIssue(
            AdapterComponent.STATUS,
            AdapterIssueCode.UNSUPPORTED_STATUS,
            AdapterIssueSeverity.INCOMPLETE,
            f"unsupported MLB status preserved: {source}",
        )
        return GameStatus.UNSUPPORTED, (reason,), issue

    def _source_status(self, record: dict[str, Any]) -> str:
        status = record.get("status")
        if isinstance(status, dict):
            for key in ("detailedState", "abstractGameState", "codedGameState"):
                value = status.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return "Unknown"

    def _pitchers(
        self,
        record: dict[str, Any],
        game_pk: int,
        canonical_id: str,
        raw: RawSourceEvidence,
        source_timestamp: datetime | None,
        prior: PitcherObservation | None,
    ) -> tuple[PitcherObservation, tuple[AdapterIssue, ...]]:
        home, home_issue = self._pitcher(record, "home")
        away, away_issue = self._pitcher(record, "away")
        issues = tuple(item for item in (home_issue, away_issue) if item is not None)
        home_state = PitcherState.PROBABLE if home else PitcherState.MISSING
        away_state = PitcherState.PROBABLE if away else PitcherState.MISSING
        changed = False
        if prior is not None:
            if home is not None and prior.home_pitcher is not None and home != prior.home_pitcher:
                home_state = PitcherState.CHANGED
                changed = True
            if away is not None and prior.away_pitcher is not None and away != prior.away_pitcher:
                away_state = PitcherState.CHANGED
                changed = True
        reasons = tuple(
            ValidationReason(ReasonCode.MISSING_PITCHER, issue.detail)
            for issue in issues
        )
        provenance = self._provenance(
            raw,
            self._source_record_id(record),
            canonical_id,
            source_timestamp,
            ValidationStatus.INCOMPLETE if issues else ValidationStatus.VALID,
            reasons,
        )
        observation = PitcherObservation(
            observation_id=self._observation_id("pitcher", game_pk, raw.collected_at),
            canonical_event_id=canonical_id,
            home_pitcher=home,
            away_pitcher=away,
            home_state=home_state,
            away_state=away_state,
            provenance=provenance,
            replaces_observation_id=(prior.observation_id if changed else None),
        )
        if changed:
            issues = issues + (
                AdapterIssue(
                    AdapterComponent.PITCHER,
                    AdapterIssueCode.PITCHER_CHANGED,
                    AdapterIssueSeverity.WARNING,
                    "probable pitcher differs from the supplied prior observation",
                ),
            )
        return observation, tuple(sorted(issues))

    def _pitcher(
        self, record: dict[str, Any], side: str
    ) -> tuple[PitcherRef | None, AdapterIssue | None]:
        side_record = record.get("teams", {}).get(side, {})
        value = side_record.get("probablePitcher")
        if value is None:
            code = (
                AdapterIssueCode.MISSING_HOME_PITCHER
                if side == "home"
                else AdapterIssueCode.MISSING_AWAY_PITCHER
            )
            return None, AdapterIssue(
                AdapterComponent.PITCHER,
                code,
                AdapterIssueSeverity.INCOMPLETE,
                f"{side} probable pitcher is absent",
            )
        pitcher_id = value.get("id") if isinstance(value, dict) else None
        name = value.get("fullName") if isinstance(value, dict) else None
        if not isinstance(pitcher_id, int) or pitcher_id <= 0 or not isinstance(name, str) or not name.strip():
            return None, AdapterIssue(
                AdapterComponent.PITCHER,
                AdapterIssueCode.MALFORMED_PITCHER,
                AdapterIssueSeverity.INCOMPLETE,
                f"{side} probable pitcher is malformed",
            )
        return (
            PitcherRef(PROVIDER_ID, str(pitcher_id), name),
            None,
        )

    def _provenance(
        self,
        raw: RawSourceEvidence,
        source_record_id: str,
        canonical_event_id: str,
        source_timestamp: datetime | None,
        validation_status: ValidationStatus,
        reasons: tuple[ValidationReason, ...],
    ) -> Provenance:
        return Provenance(
            provider=PROVIDER_ID,
            source_record_id=source_record_id,
            canonical_event_id=canonical_event_id,
            collected_at=raw.collected_at,
            source_timestamp=source_timestamp,
            transformations=(f"parsed by MLB Stats API adapter {ADAPTER_VERSION}",),
            validation_status=validation_status,
            validation_reasons=reasons,
            raw_evidence_ref=raw.raw_payload_ref,
            source_url=raw.source_url,
            collector_version=ADAPTER_VERSION,
        )

    def _identity_issue(self, error: Exception) -> AdapterIssue:
        if isinstance(error, ContractError):
            mappings = {
                ReasonCode.MISSING_GAME_PK: AdapterIssueCode.MISSING_GAME_PK,
                ReasonCode.CONFLICTING_GAME_PK: AdapterIssueCode.CONFLICTING_GAME_PK,
                ReasonCode.IDENTICAL_PARTICIPANTS: AdapterIssueCode.IDENTICAL_TEAMS,
                ReasonCode.MISSING_PARTICIPANT: AdapterIssueCode.MISSING_TEAM_ID,
                ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY: AdapterIssueCode.MALFORMED_TIMESTAMP,
            }
            code = mappings.get(error.code, AdapterIssueCode.MALFORMED_TEAM)
            if error.code is ReasonCode.MALFORMED_IDENTIFIER and "gamePk" in error.detail:
                code = AdapterIssueCode.MALFORMED_GAME_PK
            elif error.code is ReasonCode.MISSING_IDENTIFIER and "season" in error.detail:
                code = AdapterIssueCode.MISSING_SEASON
            detail = error.detail
        elif isinstance(error, KeyError):
            code = AdapterIssueCode.MISSING_TEAM_ID
            detail = f"required source field absent: {error.args[0]}"
        else:
            code = AdapterIssueCode.UNSUPPORTED_SOURCE_SHAPE
            detail = str(error) or type(error).__name__
        return AdapterIssue(
            AdapterComponent.EVENT, code, AdapterIssueSeverity.REJECTED, detail
        )

    @staticmethod
    def _source_record_id(record: dict[str, Any]) -> str:
        value = record.get("gamePk")
        return f"mlb-game:{value}" if isinstance(value, int) and value > 0 else "mlb-game:unknown"

    @staticmethod
    def _observation_id(kind: str, game_pk: int, collected_at: datetime) -> str:
        stamp = collected_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return f"mlb-stats-api:{kind}:{game_pk}:{stamp}"

    @staticmethod
    def _required_identifier(value: Any, label: str) -> str:
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ContractError(ReasonCode.MISSING_IDENTIFIER, f"{label} is absent")
        result = str(value)
        _require_identifier(result, label)
        return result

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        if not isinstance(value, str):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, f"{label} is absent")
        _require_text(value, ReasonCode.VALIDATION_FAILURE, label)
        return value

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _game_type(record: dict[str, Any]) -> str:
        value = record.get("gameType")
        return str(value) if value is not None and str(value).strip() else "unknown"

    @staticmethod
    def _venue(record: dict[str, Any]) -> str | None:
        venue = record.get("venue")
        name = venue.get("name") if isinstance(venue, dict) else None
        return name if isinstance(name, str) and name.strip() else None

    def _schedule_status_evidence(self, record: dict[str, Any]) -> tuple[str, ...]:
        values = []
        for key in ("rescheduledFromDate", "rescheduledGameDate"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                values.append(f"{key}={value}")
        source_status = self._source_status(record)
        if source_status.casefold() in {"postponed", "suspended", "resumed"}:
            values.append(f"status={source_status}")
        return tuple(sorted(values))


_CONTRACTS = (
    AdapterIssue,
    RawSourceEvidence,
    MLBStatsGameResult,
    MLBStatsAdapterResult,
)

for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(
    *_CONTRACTS,
    enums=(AdapterComponent, AdapterIssueSeverity, AdapterOutcome, AdapterIssueCode),
)
