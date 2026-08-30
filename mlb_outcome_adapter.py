"""Authoritative MLB Stats API outcome Evidence adapter; no network on import."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from event_contracts import ValidationStatus
from mlb_contracts import MLBGame
from mlb_stats_api import ADAPTER_VERSION, MLBStatsAPIAdapter, MLBStatsAPIResponse, PROVIDER_ID
from outcome_contracts import OutcomeIssue, OutcomeObservation, OutcomeStatus


OUTCOME_ADAPTER_VERSION = f"mlb-outcome-{ADAPTER_VERSION}"


@dataclass(frozen=True, slots=True)
class MLBOutcomeAdapterResult:
    provider_event_id: str | None
    observation: OutcomeObservation | None
    issues: tuple[OutcomeIssue, ...]


_STATUS_MAP = {
    "scheduled": OutcomeStatus.SCHEDULED,
    "pre-game": OutcomeStatus.SCHEDULED,
    "warmup": OutcomeStatus.SCHEDULED,
    "in progress": OutcomeStatus.IN_PROGRESS,
    "manager challenge": OutcomeStatus.IN_PROGRESS,
    "delayed": OutcomeStatus.DELAYED,
    "rain delay": OutcomeStatus.DELAYED,
    "postponed": OutcomeStatus.POSTPONED,
    "suspended": OutcomeStatus.SUSPENDED,
    "resumed": OutcomeStatus.IN_PROGRESS,
    "final": OutcomeStatus.FINAL,
    "game over": OutcomeStatus.FINAL,
    "completed early": OutcomeStatus.FINAL,
    "cancelled": OutcomeStatus.CANCELLED,
    "canceled": OutcomeStatus.CANCELLED,
    "no game": OutcomeStatus.CANCELLED,
    "no contest": OutcomeStatus.NO_CONTEST,
    "forfeit": OutcomeStatus.FORFEIT,
}


class MLBOutcomeAdapter:
    """Translate an existing bounded schedule response into Outcome Evidence."""

    def parse_response(
        self,
        response: MLBStatsAPIResponse,
        *,
        canonical_games: tuple[MLBGame, ...] = (),
    ) -> tuple[MLBOutcomeAdapterResult, ...]:
        adapter = MLBStatsAPIAdapter()
        raw = adapter._raw_evidence(response)
        supplied = {game.game_pk: game for game in canonical_games}
        results = []
        for record in _game_records(response.payload):
            game_pk = record.get("gamePk")
            if not isinstance(game_pk, int) or game_pk <= 0:
                results.append(MLBOutcomeAdapterResult(None, None, (OutcomeIssue("missing-game-pk", "positive integer gamePk is required"),)))
                continue
            fact = adapter.parse_game(record, raw)
            if fact is None or fact.game is None or fact.schedule_observation is None:
                results.append(MLBOutcomeAdapterResult(str(game_pk), None, (OutcomeIssue("canonical-event-rejected", "existing MLB facts adapter could not establish Canonical Event identity"),)))
                continue
            game = supplied.get(game_pk, fact.game)
            if canonical_games and game_pk not in supplied:
                results.append(MLBOutcomeAdapterResult(str(game_pk), None, (OutcomeIssue("canonical-event-missing", "no supplied Canonical Event matches gamePk"),)))
                continue
            identity_issue = _compatible_game(game, fact.game)
            if identity_issue is not None:
                results.append(MLBOutcomeAdapterResult(str(game_pk), None, (identity_issue,)))
                continue
            results.append(self.parse_game(record, response, game, fact.schedule_observation.scheduled_start))
        return tuple(sorted(results, key=lambda item: item.provider_event_id or ""))

    def parse_game(
        self,
        record: dict[str, Any],
        response: MLBStatsAPIResponse,
        game: MLBGame,
        scheduled_start: datetime,
    ) -> MLBOutcomeAdapterResult:
        game_pk = record.get("gamePk")
        if game_pk != game.game_pk:
            return MLBOutcomeAdapterResult(str(game_pk) if game_pk is not None else None, None, (OutcomeIssue("game-pk-mismatch", "provider gamePk conflicts with Canonical Event"),))
        teams = record.get("teams")
        if not isinstance(teams, dict):
            return MLBOutcomeAdapterResult(str(game_pk), None, (OutcomeIssue("teams-malformed", "teams object is required"),))
        away = teams.get("away") if isinstance(teams.get("away"), dict) else {}
        home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
        if _team_id(away) != game.away_team.mlb_team_id or _team_id(home) != game.home_team.mlb_team_id:
            return MLBOutcomeAdapterResult(str(game_pk), None, (OutcomeIssue("participant-mismatch", "provider team identities conflict with Canonical Event orientation"),))
        detail = _status_detail(record)
        status = _STATUS_MAP.get(detail.lower(), OutcomeStatus.UNKNOWN)
        issues: list[OutcomeIssue] = []
        validation = ValidationStatus.VALID
        if status is OutcomeStatus.UNKNOWN:
            issues.append(OutcomeIssue("unsupported-status", f"unsupported provider status {detail!r}"))
            validation = ValidationStatus.INCOMPLETE
        away_score, away_issue = _score(away, "away")
        home_score, home_issue = _score(home, "home")
        issues.extend(item for item in (away_issue, home_issue) if item is not None)
        if issues and validation is ValidationStatus.VALID:
            validation = ValidationStatus.REJECTED
        winner = loser = None
        tie = False
        unresolved = status is not OutcomeStatus.FINAL
        if status is OutcomeStatus.FINAL:
            if away_score is None or home_score is None:
                issues.append(OutcomeIssue("final-score-incomplete", "final outcome requires both scores"))
                if validation is ValidationStatus.VALID:
                    validation = ValidationStatus.INCOMPLETE
                unresolved = True
            elif away_score == home_score:
                issues.append(OutcomeIssue("final-tied", "final MLB winner outcome has no determinable winner"))
                validation = ValidationStatus.REJECTED
                tie = True
                unresolved = True
            else:
                winner, loser = (
                    (game.away_team.canonical_team_id, game.home_team.canonical_team_id)
                    if away_score > home_score
                    else (game.home_team.canonical_team_id, game.away_team.canonical_team_id)
                )
                unresolved = False
                claimed = _claimed_winner(away, home, game)
                if claimed is not None and claimed != winner:
                    issues.append(OutcomeIssue("winner-score-contradiction", "provider winner flag conflicts with final score"))
                    validation = ValidationStatus.REJECTED
                    winner = loser = None
                    unresolved = True
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        raw_digest = hashlib.sha256(response.raw_body).hexdigest()
        identity_material = f"{game.event.canonical_event_id}|{response.collected_at.isoformat()}|{canonical_digest}|{raw_digest}|{OUTCOME_ADAPTER_VERSION}|{response.source_url}"
        observation_id = f"outcome:{hashlib.sha256(identity_material.encode()).hexdigest()}"
        observation = OutcomeObservation(
            observation_id=observation_id,
            canonical_event_id=game.event.canonical_event_id,
            authoritative_provider_id=PROVIDER_ID,
            provider_event_id=str(game_pk),
            provider_status=status,
            provider_status_detail=detail,
            away_participant_id=game.away_team.canonical_team_id,
            home_participant_id=game.home_team.canonical_team_id,
            away_score=away_score,
            home_score=home_score,
            winning_participant_id=winner,
            losing_participant_id=loser,
            tie=tie,
            unresolved=unresolved,
            scheduled_start=scheduled_start,
            completed_periods=_completed_periods(record),
            provider_result_at=None,
            collected_at=response.collected_at,
            raw_evidence_sha256=raw_digest,
            canonical_evidence_sha256=canonical_digest,
            source_url=response.source_url,
            collector_version=OUTCOME_ADAPTER_VERSION,
            validation_status=validation,
            issues=tuple(issues),
        )
        return MLBOutcomeAdapterResult(str(game_pk), observation, tuple(sorted(issues)))


def _game_records(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records = []
    for date_group in payload.get("dates", ()):
        if isinstance(date_group, dict):
            records.extend(item for item in date_group.get("games", ()) if isinstance(item, dict))
    return tuple(records)


def _compatible_game(expected: MLBGame, actual: MLBGame) -> OutcomeIssue | None:
    if expected.event.canonical_event_id != actual.event.canonical_event_id or expected.game_pk != actual.game_pk:
        return OutcomeIssue("canonical-event-mismatch", "Canonical Event identity conflicts with gamePk")
    if (expected.away_team.mlb_team_id, expected.home_team.mlb_team_id) != (actual.away_team.mlb_team_id, actual.home_team.mlb_team_id):
        return OutcomeIssue("participant-mismatch", "Canonical Event participants conflict with provider teams")
    return None


def _team_id(side: dict[str, Any]) -> int | None:
    team = side.get("team")
    return team.get("id") if isinstance(team, dict) and isinstance(team.get("id"), int) else None


def _status_detail(record: dict[str, Any]) -> str:
    status = record.get("status")
    if not isinstance(status, dict):
        return "Unknown"
    value = status.get("detailedState") or status.get("abstractGameState") or "Unknown"
    return value if isinstance(value, str) and value.strip() else "Unknown"


def _score(side: dict[str, Any], label: str) -> tuple[int | None, OutcomeIssue | None]:
    value = side.get("score")
    if value is None:
        return None, None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None, OutcomeIssue(f"{label}-score-malformed", f"{label} score must be a non-negative integer")
    return value, None


def _claimed_winner(away: dict[str, Any], home: dict[str, Any], game: MLBGame) -> str | None:
    flags = []
    if away.get("isWinner") is True:
        flags.append(game.away_team.canonical_team_id)
    if home.get("isWinner") is True:
        flags.append(game.home_team.canonical_team_id)
    return flags[0] if len(flags) == 1 else None


def _completed_periods(record: dict[str, Any]) -> int | None:
    linescore = record.get("linescore")
    if not isinstance(linescore, dict):
        return None
    innings = linescore.get("innings")
    if isinstance(innings, list):
        return len(innings)
    value = linescore.get("currentInning")
    return value if isinstance(value, int) and value >= 0 else None
