"""PR19B development-only native MLB Model 0 feasibility study.

This module reads the existing PR17C archive without mutation, constructs only
market-independent derived rows, seals the fixed protocol and test identity
before fitting, and permits one sealed-test evaluation.  It creates Derived
Analysis only; none of its outputs is Evidence or operational authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sqlite3
import sys
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo


PROTOCOL_ID = "pr19b-feasibility-2026-v1"
ALGORITHM_VERSION = "pr19b-feasibility-engine-1"
SOURCE_ADAPTER_VERSION = "pr19b-pr17c-mlb-schedule-adapter-1"
FEATURE_VERSION = "pr19a-model-0-features-with-pr19b-eight-hour-proxy-1"
ESTIMATOR_VERSION = "deterministic-newton-binary64-1"
CALIBRATION_VERSION = "validation-sigmoid-newton-binary64-1"
METRIC_VERSION = "pr19b-brier-logloss-calibration-1"
BOOTSTRAP_VERSION = "sha256-counter-paired-percentile-type7-1"
CLASSIFIER_VERSION = "pr19b-fixed-signal-classifier-1"

NY = ZoneInfo("America/New_York")
SPLITS = (
    ("training", "2026-03-25", "2026-06-30"),
    ("validation", "2026-07-01", "2026-07-31"),
    ("test", "2026-08-01", "2026-08-27"),
)
FEATURE_NAMES = (
    "season_win_rate_difference",
    "season_run_rate_difference",
    "recent_ten_win_rate_difference",
)
NATIVE_ROW_FIELDS = frozenset(
    {
        "game_pk",
        "split",
        "scheduled_start",
        "scheduled_date_ny",
        "home_team_id",
        "away_team_id",
        "feature_snapshot_digest",
        "features",
        "label",
    }
)
PROHIBITED_FIELD_TERMS = frozenset(
    {
        "kalshi",
        "sportsbook",
        "exchange",
        "market",
        "market_id",
        "ticker",
        "odds",
        "price",
        "candle",
        "liquidity",
        "volume",
        "probability",
        "payout",
        "moneyline",
        "spread",
    }
)
FINAL_STATUSES = frozenset({"final", "game over", "completed early"})


PROTOCOL: dict[str, Any] = {
    "authority": {
        "artifact": "PR19B Development-Only Feasibility Study — Product Decision",
        "decision_date": "2026-09-01",
        "historical_protocol": "pr19a-model-0-v1",
        "amendment": "development-only 2026 feasibility; no admission authority",
    },
    "classification": {
        "basic_signal": {
            "brier": "model strictly lower than both baselines",
            "log_loss": "model no greater than both baselines",
        },
        "credible_signal": {
            "requires": "basic_signal",
            "paired_brier_improvement_95pct_lower_bound": "strictly greater than zero against both baselines",
        },
        "otherwise": "NO BASIC SIGNAL",
        "version": CLASSIFIER_VERSION,
    },
    "estimand": "probability that the canonical home team wins an eligible 2026 MLB regular-season game",
    "forecast_boundary": {
        "definition": "authoritative scheduled start minus six hours",
        "prior_outcome_proxy": "prior scheduled start plus eight hours must be no later than the target boundary",
        "limitation": "development proxy; not historical publication-time authority",
        "timezone": "America/New_York",
    },
    "population": {
        "include": "uniquely resolved 2026 MLB regular-season game identity and decisive final outcome",
        "exclude": [
            "spring training",
            "exhibition",
            "All-Star",
            "postseason",
            "unresolved or non-decisive outcome",
            "ambiguous identity",
            "unresolved schedule evolution",
            "postponed, cancelled, suspended, or resumed ambiguity",
        ],
        "market_independence": "population and missingness use MLB schedule/status/score/outcome material only",
    },
    "features": {
        "names": list(FEATURE_NAMES),
        "same_season_only": True,
        "season_win_rate": "(wins + 1) / (games + 2)",
        "season_run_rate": "run_differential / (games + 10)",
        "recent_win_rate": "(wins_in_latest_at_most_10 + 1) / (recent_games + 2)",
        "orientation": "home minus away",
        "recent_tie_rule": "invalidate when an equal scheduled-start tie straddles the ten-game cutoff",
        "version": FEATURE_VERSION,
    },
    "model": {
        "family": "binary logistic regression",
        "regularization": "L2 on feature coefficients only",
        "C": "1",
        "objective": "sum binary log loss + 0.5 * sum(coefficient squared) / C",
        "intercept": True,
        "class_weights": None,
        "hyperparameter_search": False,
        "numeric_representation": "IEEE-754 binary64 through CPython float",
        "solver": {
            "algorithm": "damped Newton with deterministic Gaussian elimination",
            "tolerance": "1e-12 maximum absolute Newton step",
            "iteration_limit": 200,
            "line_search": "fixed halving, at most 60 reductions",
            "primary_initial_parameters": ["0", "0", "0", "0"],
            "version": ESTIMATOR_VERSION,
        },
        "standardization": {
            "fit_split": "training",
            "standard_deviation": "population",
            "zero_scale": "1",
        },
    },
    "calibration": {
        "family": "two-parameter sigmoid on primary raw logits",
        "fit_split": "validation only",
        "penalty": None,
        "initial_parameters": ["0", "1"],
        "solver": ESTIMATOR_VERSION,
        "version": CALIBRATION_VERSION,
    },
    "splits": [
        {"name": name, "start": start, "end": end, "assignment": "scheduled date in America/New_York"}
        for name, start, end in SPLITS
    ],
    "baselines": {
        "even": "constant 0.5",
        "training_home_rate": "(training home wins + 1) / (training games + 2), held fixed",
    },
    "metrics": {
        "brier": "mean squared probability error",
        "log_loss": "mean negative natural log likelihood; exact zero realized probability is positive infinity",
        "calibration_bins": [
            "[0.0,0.1)",
            "[0.1,0.2)",
            "[0.2,0.3)",
            "[0.3,0.4)",
            "[0.4,0.5)",
            "[0.5,0.6)",
            "[0.6,0.7)",
            "[0.7,0.8)",
            "[0.8,0.9)",
            "[0.9,1.0]",
        ],
        "wace": "sum bin_count / N * abs(observed_frequency - mean_probability)",
        "version": METRIC_VERSION,
    },
    "bootstrap": {
        "unit": "test game paired Brier improvement",
        "resamples": 10000,
        "confidence_level": "0.95",
        "interval": "two-sided percentile with deterministic type-7 linear quantiles",
        "seed_material": [
            "protocol digest",
            "dataset digest",
            "sorted test game identities",
            "model bundle digest",
            "baseline identity",
            "confidence level",
            "resample count",
            "algorithm version",
        ],
        "randomness": "SHA-256 counter stream with unbiased rejection sampling",
        "version": BOOTSTRAP_VERSION,
    },
    "authority_boundary": "development-only Derived Analysis; no Evidence, Probability Source admission, Forecast, Policy, Governance, wagering, deployment, or production authority",
    "clean_room": "no use of gmalbert/baseball-predictions or other unlicensed external implementation, data, model, asset, prose, schema, or lock",
    "protocol_id": PROTOCOL_ID,
}


class FeasibilityError(RuntimeError):
    """Fail-closed study error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write_canonical(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = canonical_bytes(value) + b"\n"
    if path.exists():
        raise FeasibilityError(f"refusing to overwrite sealed artifact: {path}")
    path.write_bytes(body)
    return hashlib.sha256(body[:-1]).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _float_text(value: float) -> str:
    if not math.isfinite(value):
        raise FeasibilityError("non-finite numeric value")
    return format(value, ".17g")


def _float_list(values: Iterable[float]) -> list[str]:
    return [_float_text(value) for value in values]


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise FeasibilityError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeasibilityError(f"invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise FeasibilityError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def split_for_start(scheduled_start: datetime) -> str | None:
    day = scheduled_start.astimezone(NY).date().isoformat()
    for name, start, end in SPLITS:
        if start <= day <= end:
            return name
    return None


def _object_path(root: Path, kind: str, digest: str, *, suffix: str = "") -> Path:
    return root / kind / digest[:2] / f"{digest}{suffix}"


def _assert_digest(path: Path, expected: str) -> None:
    if len(expected) != 64 or digest_file(path) != expected:
        raise FeasibilityError(f"content digest mismatch: {path}")


def _scan_prohibited_fields(value: Any, *, location: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            tokens = set(lowered.replace("-", "_").split("_"))
            if lowered in PROHIBITED_FIELD_TERMS or tokens & PROHIBITED_FIELD_TERMS:
                findings.append(f"{location}.{key}")
            findings.extend(_scan_prohibited_fields(child, location=f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_prohibited_fields(child, location=f"{location}[{index}]"))
    return findings


@dataclass(frozen=True)
class SourcePage:
    manifest_id: str
    acquired_at: str
    request_identity: str
    manifest_digest: str
    normalized_digest: str
    raw_digest: str
    raw_path: Path
    payload: dict[str, Any]


def load_mlb_schedule_pages(primary_root: Path) -> tuple[SourcePage, ...]:
    """Load only immutable MLB schedule pages from manifest authority."""
    pages: list[SourcePage] = []
    seen_manifest_ids: set[str] = set()
    for manifest_path in sorted((primary_root / "manifest").glob("*/*.json")):
        manifest = read_json(manifest_path)
        if manifest.get("command") != "refresh-retrospective-supporting-page" or manifest.get("disposition") != "success":
            continue
        if manifest.get("provider_id") != "mlb-stats-api":
            continue
        if manifest.get("design_authority") != "supporting":
            raise FeasibilityError("MLB schedule page has unexpected design authority")
        manifest_id = manifest.get("manifest_entry_id")
        if not isinstance(manifest_id, str) or not manifest_id.startswith("operations-manifest:"):
            raise FeasibilityError("invalid source manifest identity")
        if manifest_id in seen_manifest_ids:
            raise FeasibilityError("duplicate source manifest identity")
        seen_manifest_ids.add(manifest_id)
        raw_digest = manifest.get("raw_object_sha256")
        normalized_id = manifest.get("normalized_object_id")
        if not isinstance(raw_digest, str) or not isinstance(normalized_id, str) or not normalized_id.startswith("normalized:"):
            raise FeasibilityError("successful source page lacks immutable objects")
        normalized_digest = normalized_id.split(":", 1)[1]
        normalized_path = _object_path(primary_root, "normalized", normalized_digest, suffix=".json")
        raw_path = _object_path(primary_root, "raw", raw_digest)
        _assert_digest(normalized_path, normalized_digest)
        _assert_digest(raw_path, raw_digest)
        normalized = read_json(normalized_path)
        if normalized.get("provider") != "mlb-stats-api" or normalized.get("purpose") != "schedule":
            raise FeasibilityError("source page is not allowlisted MLB schedule material")
        if normalized.get("record_kind") != "pr17c2-supporting-session-page" or normalized.get("disposition") != "success":
            raise FeasibilityError("source page normalized contract is incompatible")
        endpoint = normalized.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith("https://statsapi.mlb.com/api/v1/schedule?"):
            raise FeasibilityError("source page endpoint is outside the MLB allowlist")
        payload = read_json(raw_path)
        prohibited = _scan_prohibited_fields(payload)
        if prohibited:
            raise FeasibilityError(f"market-derived field name in MLB source: {prohibited[0]}")
        request_identity = normalized.get("request_identity")
        if not isinstance(request_identity, str):
            raise FeasibilityError("source page lacks request identity")
        acquired = normalized.get("completed_at", {}).get("datetime_utc")
        _parse_datetime(acquired, "completed_at")
        pages.append(
            SourcePage(
                manifest_id=manifest_id,
                acquired_at=acquired,
                request_identity=request_identity,
                manifest_digest=digest_file(manifest_path),
                normalized_digest=normalized_digest,
                raw_digest=raw_digest,
                raw_path=raw_path,
                payload=payload,
            )
        )
    if not pages:
        raise FeasibilityError("archive contains no allowlisted MLB schedule pages")
    return tuple(sorted(pages, key=lambda page: (page.request_identity, page.acquired_at, page.manifest_id)))


def source_snapshot_manifest(pages: Sequence[SourcePage]) -> dict[str, Any]:
    entries = [
        {
            "acquired_at": page.acquired_at,
            "manifest_digest": page.manifest_digest,
            "manifest_id": page.manifest_id,
            "normalized_digest": page.normalized_digest,
            "provider": "mlb-stats-api",
            "purpose": "schedule",
            "raw_digest": page.raw_digest,
            "request_identity": page.request_identity,
        }
        for page in pages
    ]
    return {
        "adapter_version": SOURCE_ADAPTER_VERSION,
        "authority": "content-addressed read-only descriptor; raw provider material is not copied",
        "market_sources_included": False,
        "page_count": len(entries),
        "pages": entries,
        "source_allowlist": [{"provider": "mlb-stats-api", "purpose": "schedule"}],
    }


@dataclass(frozen=True)
class GameObservation:
    game_pk: int
    season: str
    game_type: str
    scheduled_start: datetime
    official_date: str
    home_team_id: int
    away_team_id: int
    game_number: int | None
    doubleheader: str
    status: str
    home_score: int | None
    away_score: int | None
    home_is_winner: bool | None
    away_is_winner: bool | None
    source_raw_digest: str


@dataclass(frozen=True)
class ResolvedGame:
    game_pk: int
    season: str | None
    game_type: str | None
    scheduled_start: datetime | None
    official_date: str | None
    home_team_id: int | None
    away_team_id: int | None
    game_number: int | None
    doubleheader: str | None
    home_score: int | None
    away_score: int | None
    label: int | None
    disposition: str
    status_history: tuple[str, ...]


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _team_id(side: Any) -> int | None:
    if not isinstance(side, dict) or not isinstance(side.get("team"), dict):
        return None
    return _positive_int(side["team"].get("id"))


def extract_observations(pages: Sequence[SourcePage]) -> dict[int, tuple[GameObservation, ...]]:
    by_game: dict[int, list[GameObservation]] = defaultdict(list)
    for page in pages:
        dates = page.payload.get("dates")
        if not isinstance(dates, list):
            raise FeasibilityError("MLB schedule payload dates must be a list")
        for date_group in dates:
            if not isinstance(date_group, dict) or not isinstance(date_group.get("games"), list):
                raise FeasibilityError("MLB schedule date group is malformed")
            for record in date_group["games"]:
                if not isinstance(record, dict):
                    raise FeasibilityError("MLB schedule game record is malformed")
                game_pk = _positive_int(record.get("gamePk"))
                teams = record.get("teams")
                status = record.get("status")
                if game_pk is None or not isinstance(teams, dict) or not isinstance(status, dict):
                    continue
                home = teams.get("home")
                away = teams.get("away")
                home_id = _team_id(home)
                away_id = _team_id(away)
                season = record.get("season")
                game_type = record.get("gameType")
                official_date = record.get("officialDate")
                if home_id is None or away_id is None or not all(isinstance(value, str) for value in (season, game_type, official_date)):
                    continue
                scheduled_start = _parse_datetime(record.get("gameDate"), "gameDate")
                detail = status.get("detailedState") or status.get("abstractGameState") or "Unknown"
                if not isinstance(detail, str):
                    detail = "Unknown"
                game_number = _positive_int(record.get("gameNumber"))
                doubleheader = record.get("doubleHeader")
                if not isinstance(doubleheader, str):
                    doubleheader = "unknown"
                home_score = _nonnegative_int(home.get("score")) if isinstance(home, dict) else None
                away_score = _nonnegative_int(away.get("score")) if isinstance(away, dict) else None
                home_winner = home.get("isWinner") if isinstance(home, dict) and isinstance(home.get("isWinner"), bool) else None
                away_winner = away.get("isWinner") if isinstance(away, dict) and isinstance(away.get("isWinner"), bool) else None
                by_game[game_pk].append(
                    GameObservation(
                        game_pk=game_pk,
                        season=season,
                        game_type=game_type,
                        scheduled_start=scheduled_start,
                        official_date=official_date,
                        home_team_id=home_id,
                        away_team_id=away_id,
                        game_number=game_number,
                        doubleheader=doubleheader,
                        status=detail.strip().lower(),
                        home_score=home_score,
                        away_score=away_score,
                        home_is_winner=home_winner,
                        away_is_winner=away_winner,
                        source_raw_digest=page.raw_digest,
                    )
                )
    if not by_game:
        raise FeasibilityError("MLB source pages contain no resolvable game identities")
    return {
        game_pk: tuple(
            sorted(
                observations,
                key=lambda item: (
                    item.scheduled_start,
                    item.source_raw_digest,
                    item.status,
                    item.home_score if item.home_score is not None else -1,
                    item.away_score if item.away_score is not None else -1,
                ),
            )
        )
        for game_pk, observations in sorted(by_game.items())
    }


def resolve_game(game_pk: int, observations: Sequence[GameObservation]) -> ResolvedGame:
    statuses = tuple(sorted({item.status for item in observations}))
    identity_variants = {
        (
            item.season,
            item.game_type,
            item.home_team_id,
            item.away_team_id,
            item.game_number,
            item.doubleheader,
        )
        for item in observations
    }
    starts = {item.scheduled_start for item in observations}
    official_dates = {item.official_date for item in observations}
    if len(identity_variants) != 1:
        return _unresolved(game_pk, "ambiguous_identity", statuses)
    season, game_type, home_id, away_id, game_number, doubleheader = next(iter(identity_variants))
    if home_id == away_id:
        return _unresolved(game_pk, "ambiguous_identity", statuses)
    if len(starts) != 1 or len(official_dates) != 1:
        return ResolvedGame(game_pk, season, game_type, None, None, home_id, away_id, game_number, doubleheader, None, None, None, "schedule_evolution_ambiguous", statuses)
    scheduled_start = next(iter(starts))
    official_date = next(iter(official_dates))
    status_text = " ".join(statuses)
    for marker, disposition in (
        ("cancel", "cancelled"),
        ("no game", "cancelled"),
        ("no contest", "non_decisive"),
        ("postpon", "postponed"),
        ("suspend", "suspended_or_resumed"),
        ("resum", "suspended_or_resumed"),
        ("forfeit", "non_decisive"),
    ):
        if marker in status_text:
            return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, disposition, statuses)
    if season != "2026":
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "outside_2026_season", statuses)
    if game_type != "R":
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "unsupported_game_type", statuses)
    if doubleheader.lower() not in {"n", "none"} and game_number is None:
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "doubleheader_ambiguous", statuses)
    finals: set[tuple[int, int, int]] = set()
    contradiction = False
    for item in observations:
        if item.status not in FINAL_STATUSES:
            continue
        if item.home_score is None or item.away_score is None or item.home_score == item.away_score:
            continue
        label = int(item.home_score > item.away_score)
        claimed = None
        if item.home_is_winner is True and item.away_is_winner is not True:
            claimed = 1
        elif item.away_is_winner is True and item.home_is_winner is not True:
            claimed = 0
        elif item.home_is_winner is True and item.away_is_winner is True:
            contradiction = True
        if claimed is not None and claimed != label:
            contradiction = True
        finals.add((item.home_score, item.away_score, label))
    if contradiction:
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "outcome_contradiction", statuses)
    if len(finals) == 0:
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "outcome_unresolved", statuses)
    if len(finals) > 1:
        return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, None, None, None, "outcome_ambiguous", statuses)
    home_score, away_score, label = next(iter(finals))
    return ResolvedGame(game_pk, season, game_type, scheduled_start, official_date, home_id, away_id, game_number, doubleheader, home_score, away_score, label, "eligible", statuses)


def _unresolved(game_pk: int, disposition: str, statuses: tuple[str, ...]) -> ResolvedGame:
    return ResolvedGame(game_pk, None, None, None, None, None, None, None, None, None, None, None, disposition, statuses)


def resolve_population(pages: Sequence[SourcePage]) -> tuple[ResolvedGame, ...]:
    observations = extract_observations(pages)
    return tuple(resolve_game(game_pk, records) for game_pk, records in observations.items())


def _team_history(
    team_id: int,
    target: ResolvedGame,
    eligible_games: Sequence[ResolvedGame],
) -> tuple[list[tuple[datetime, int, int, int]], bool]:
    if target.scheduled_start is None:
        raise FeasibilityError("target schedule is unresolved")
    boundary = target.scheduled_start - timedelta(hours=6)
    proxy_cutoff = boundary - timedelta(hours=8)
    history: list[tuple[datetime, int, int, int]] = []
    for game in eligible_games:
        if game.game_pk == target.game_pk or game.season != target.season:
            continue
        if game.scheduled_start is None or game.scheduled_start > proxy_cutoff:
            continue
        if team_id not in (game.home_team_id, game.away_team_id):
            continue
        if game.home_score is None or game.away_score is None or game.label is None:
            continue
        is_home = team_id == game.home_team_id
        runs_for = game.home_score if is_home else game.away_score
        runs_against = game.away_score if is_home else game.home_score
        won = int((game.label == 1) if is_home else (game.label == 0))
        history.append((game.scheduled_start, game.game_pk, won, runs_for - runs_against))
    history.sort(key=lambda item: (item[0], item[1]))
    tie_at_cutoff = len(history) > 10 and history[-10][0] == history[-11][0]
    return history, tie_at_cutoff


def _team_rates(history: Sequence[tuple[datetime, int, int, int]]) -> tuple[float, float, float]:
    games = len(history)
    wins = sum(item[2] for item in history)
    run_diff = sum(item[3] for item in history)
    recent = history[-10:]
    recent_wins = sum(item[2] for item in recent)
    return (
        (wins + 1) / (games + 2),
        run_diff / (games + 10),
        (recent_wins + 1) / (len(recent) + 2),
    )


def feature_snapshot(target: ResolvedGame, eligible_games: Sequence[ResolvedGame]) -> tuple[tuple[float, float, float] | None, str | None]:
    if target.disposition != "eligible" or target.home_team_id is None or target.away_team_id is None:
        return None, "target_ineligible"
    home_history, home_tie = _team_history(target.home_team_id, target, eligible_games)
    away_history, away_tie = _team_history(target.away_team_id, target, eligible_games)
    if home_tie or away_tie:
        return None, "recent_ten_schedule_tie"
    home_rates = _team_rates(home_history)
    away_rates = _team_rates(away_history)
    return tuple(home - away for home, away in zip(home_rates, away_rates)), None


def build_native_dataset(population: Sequence[ResolvedGame]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible_games = tuple(game for game in population if game.disposition == "eligible")
    rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for game in sorted(population, key=lambda item: item.game_pk):
        disposition = game.disposition
        split = split_for_start(game.scheduled_start) if game.scheduled_start is not None else None
        if disposition == "eligible" and split is None:
            disposition = "outside_study_dates"
        features = None
        if disposition == "eligible":
            features, feature_issue = feature_snapshot(game, eligible_games)
            if feature_issue is not None:
                disposition = feature_issue
        coverage.append(
            {
                "disposition": disposition,
                "game_pk": game.game_pk,
                "scheduled_date_ny": game.scheduled_start.astimezone(NY).date().isoformat() if game.scheduled_start else None,
                "split": split,
                "status_history": list(game.status_history),
            }
        )
        if disposition != "eligible" or features is None or game.label is None or game.scheduled_start is None:
            continue
        snapshot_material = {
            "away_team_id": game.away_team_id,
            "feature_names": list(FEATURE_NAMES),
            "features": _float_list(features),
            "game_pk": game.game_pk,
            "home_team_id": game.home_team_id,
            "scheduled_start": game.scheduled_start.isoformat(),
            "version": FEATURE_VERSION,
        }
        row = {
            "away_team_id": game.away_team_id,
            "feature_snapshot_digest": digest_value(snapshot_material),
            "features": _float_list(features),
            "game_pk": game.game_pk,
            "home_team_id": game.home_team_id,
            "label": game.label,
            "scheduled_date_ny": game.scheduled_start.astimezone(NY).date().isoformat(),
            "scheduled_start": game.scheduled_start.isoformat(),
            "split": split,
        }
        if set(row) != NATIVE_ROW_FIELDS:
            raise FeasibilityError("native row violates the exact field allowlist")
        if _scan_prohibited_fields(row):
            raise FeasibilityError("native row contains a prohibited field")
        rows.append(row)
    return sorted(rows, key=lambda item: item["game_pk"]), coverage


def coverage_summary(coverage: Sequence[dict[str, Any]], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    dispositions = Counter(item["disposition"] for item in coverage)
    split_counts = Counter(item["split"] for item in rows)
    franchises: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        franchises[row["split"]].update((row["home_team_id"], row["away_team_id"]))
    return {
        "disposition_counts": dict(sorted(dispositions.items())),
        "franchise_counts_by_split": {name: len(franchises[name]) for name, _, _ in SPLITS},
        "measured_rows": len(rows),
        "population_reconciliation": list(coverage),
        "schedule_universe": len(coverage),
        "split_counts": {name: split_counts[name] for name, _, _ in SPLITS},
    }


def _softplus(value: float) -> float:
    if value > 0:
        return value + math.log1p(math.exp(-value))
    return math.log1p(math.exp(value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _linear_solve(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: (abs(augmented[row][column]), -row))
        if abs(augmented[pivot][column]) <= 1e-18:
            raise FeasibilityError("solver Hessian is singular")
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        for index in range(column, size + 1):
            augmented[column][index] /= pivot_value
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            for index in range(column, size + 1):
                augmented[row][index] -= factor * augmented[column][index]
    solution = [augmented[row][size] for row in range(size)]
    if not all(math.isfinite(value) for value in solution):
        raise FeasibilityError("solver produced non-finite step")
    return solution


def _logistic_objective(
    matrix: Sequence[Sequence[float]],
    labels: Sequence[int],
    parameters: Sequence[float],
    *,
    penalty: float,
    penalized_from: int,
) -> float:
    result = 0.0
    for row, label in zip(matrix, labels):
        linear = sum(value * coefficient for value, coefficient in zip(row, parameters))
        result += _softplus(linear) - label * linear
    result += 0.5 * penalty * sum(value * value for value in parameters[penalized_from:])
    return result


def fit_logistic_newton(
    matrix: Sequence[Sequence[float]],
    labels: Sequence[int],
    *,
    penalty: float,
    initial: Sequence[float],
) -> dict[str, Any]:
    if not matrix or len(matrix) != len(labels):
        raise FeasibilityError("model split must be nonempty and aligned")
    width = len(initial)
    if any(len(row) != width for row in matrix) or any(label not in (0, 1) for label in labels):
        raise FeasibilityError("model matrix or labels are invalid")
    parameters = [float(value) for value in initial]
    previous = _logistic_objective(matrix, labels, parameters, penalty=penalty, penalized_from=1)
    converged = False
    iterations = 0
    for iteration in range(1, 201):
        gradient = [0.0] * width
        hessian = [[0.0] * width for _ in range(width)]
        for row, label in zip(matrix, labels):
            linear = sum(value * coefficient for value, coefficient in zip(row, parameters))
            probability = _sigmoid(linear)
            residual = probability - label
            weight = probability * (1.0 - probability)
            for left in range(width):
                gradient[left] += row[left] * residual
                for right in range(width):
                    hessian[left][right] += row[left] * row[right] * weight
        for index in range(1, width):
            gradient[index] += penalty * parameters[index]
            hessian[index][index] += penalty
        step = _linear_solve(hessian, gradient)
        scale = 1.0
        accepted = False
        candidate: list[float] = []
        candidate_objective = previous
        for _ in range(61):
            candidate = [value - scale * delta for value, delta in zip(parameters, step)]
            candidate_objective = _logistic_objective(matrix, labels, candidate, penalty=penalty, penalized_from=1)
            if math.isfinite(candidate_objective) and candidate_objective <= previous:
                accepted = True
                break
            scale *= 0.5
        if not accepted:
            raise FeasibilityError("deterministic solver line search failed")
        parameters = candidate
        previous = candidate_objective
        iterations = iteration
        if max(abs(scale * delta) for delta in step) < 1e-12:
            converged = True
            break
    if not converged:
        raise FeasibilityError("deterministic solver did not converge")
    return {
        "converged": True,
        "iterations": iterations,
        "objective": _float_text(previous),
        "parameters": _float_list(parameters),
        "solver_version": ESTIMATOR_VERSION,
    }


def fit_scaler(rows: Sequence[dict[str, Any]]) -> tuple[list[float], list[float]]:
    if not rows:
        raise FeasibilityError("training split is empty")
    columns = list(zip(*(tuple(float(value) for value in row["features"]) for row in rows)))
    means = [sum(column) / len(column) for column in columns]
    scales = []
    for column, mean in zip(columns, means):
        variance = sum((value - mean) ** 2 for value in column) / len(column)
        scale = math.sqrt(variance)
        scales.append(scale if scale != 0.0 else 1.0)
    return means, scales


def standardized_matrix(rows: Sequence[dict[str, Any]], means: Sequence[float], scales: Sequence[float]) -> list[list[float]]:
    return [
        [1.0] + [(float(value) - mean) / scale for value, mean, scale in zip(row["features"], means, scales)]
        for row in rows
    ]


def raw_logit(row: dict[str, Any], means: Sequence[float], scales: Sequence[float], coefficients: Sequence[float]) -> float:
    matrix_row = [1.0] + [(float(value) - mean) / scale for value, mean, scale in zip(row["features"], means, scales)]
    return sum(value * coefficient for value, coefficient in zip(matrix_row, coefficients))


def calibrated_probability(raw_value: float, calibrator: Sequence[float]) -> float:
    probability = _sigmoid(calibrator[0] + calibrator[1] * raw_value)
    if not (math.isfinite(probability) and 0.0 < probability < 1.0):
        raise FeasibilityError("calibrated probability is not finite and strictly interior")
    return probability


def fit_model_bundle(train_rows: Sequence[dict[str, Any]], validation_rows: Sequence[dict[str, Any]], *, dependency_identity: dict[str, Any], protocol_digest: str, dataset_digest: str, source_revision: str, source_tree: str, code_digest: str) -> dict[str, Any]:
    train_rows = sorted(train_rows, key=lambda row: row["game_pk"])
    validation_rows = sorted(validation_rows, key=lambda row: row["game_pk"])
    means, scales = fit_scaler(train_rows)
    training_matrix = standardized_matrix(train_rows, means, scales)
    training_labels = [row["label"] for row in train_rows]
    primary = fit_logistic_newton(training_matrix, training_labels, penalty=1.0, initial=(0.0, 0.0, 0.0, 0.0))
    primary_parameters = [float(value) for value in primary["parameters"]]
    validation_logits = [raw_logit(row, means, scales, primary_parameters) for row in validation_rows]
    validation_matrix = [[1.0, value] for value in validation_logits]
    validation_labels = [row["label"] for row in validation_rows]
    calibrator = fit_logistic_newton(validation_matrix, validation_labels, penalty=0.0, initial=(0.0, 1.0))
    training_probability = (sum(training_labels) + 1) / (len(training_labels) + 2)
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "authority": "development-only Derived Analysis; not an admitted Probability Source",
        "baseline_probabilities": {"even": "0.5", "training_home_rate": _float_text(training_probability)},
        "calibrator": calibrator,
        "code_digest": code_digest,
        "dataset_digest": dataset_digest,
        "dependency_identity": dependency_identity,
        "feature_names": list(FEATURE_NAMES),
        "primary_estimator": primary,
        "protocol_digest": protocol_digest,
        "scaler": {"means": _float_list(means), "scales": _float_list(scales), "standard_deviation": "population"},
        "source_revision": source_revision,
        "source_tree": source_tree,
    }


def _decimal(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def metric_report(probabilities: Sequence[str], labels: Sequence[int]) -> tuple[dict[str, Any], list[Decimal]]:
    if not probabilities or len(probabilities) != len(labels):
        raise FeasibilityError("metric population must be nonempty and aligned")
    with localcontext() as context:
        context.prec = 50
        briers: list[Decimal] = []
        losses: list[Decimal] = []
        bins: list[list[tuple[Decimal, int]]] = [[] for _ in range(10)]
        for probability_text, label in zip(probabilities, labels):
            probability = Decimal(probability_text)
            if probability < 0 or probability > 1 or label not in (0, 1):
                raise FeasibilityError("invalid metric input")
            error = probability - Decimal(label)
            briers.append(error * error)
            realized = probability if label == 1 else Decimal(1) - probability
            losses.append(Decimal("Infinity") if realized == 0 else -realized.ln())
            index = min(int(probability * 10), 9)
            bins[index].append((probability, label))
        count = Decimal(len(labels))
        mean_brier = sum(briers, Decimal(0)) / count
        mean_log_loss = Decimal("Infinity") if any(not item.is_finite() for item in losses) else sum(losses, Decimal(0)) / count
        calibration = []
        wace = Decimal(0)
        for index, entries in enumerate(bins):
            if entries:
                bin_count = Decimal(len(entries))
                mean_probability = sum((item[0] for item in entries), Decimal(0)) / bin_count
                observed = sum((Decimal(item[1]) for item in entries), Decimal(0)) / bin_count
                gap = observed - mean_probability
                wace += (bin_count / count) * abs(gap)
                calibration.append({"bin": index, "count": len(entries), "mean_probability": str(mean_probability), "observed_frequency": str(observed), "gap": str(gap)})
            else:
                calibration.append({"bin": index, "count": 0, "mean_probability": None, "observed_frequency": None, "gap": None})
        return ({"brier": str(mean_brier), "calibration": calibration, "log_loss": str(mean_log_loss), "wace": str(wace)}, briers)


class _HashCounterIndices:
    def __init__(self, seed: bytes, upper: int):
        if upper <= 0:
            raise FeasibilityError("bootstrap population must be positive")
        self.seed = seed
        self.upper = upper
        self.counter = 0
        self.words: list[int] = []
        self.limit = (1 << 64) - ((1 << 64) % upper)

    def next(self) -> int:
        while True:
            if not self.words:
                block = hashlib.sha256(self.seed + self.counter.to_bytes(16, "big")).digest()
                self.counter += 1
                self.words = [int.from_bytes(block[offset : offset + 8], "big") for offset in range(0, 32, 8)]
            value = self.words.pop(0)
            if value < self.limit:
                return value % self.upper


def _quantile_type7(values: Sequence[Decimal], probability: Decimal) -> Decimal:
    ordered = sorted(values)
    position = probability * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def paired_bootstrap(improvements: Sequence[Decimal], seed_material: dict[str, Any]) -> dict[str, Any]:
    if not improvements:
        raise FeasibilityError("paired bootstrap population is empty")
    improvements = tuple(sorted(improvements))
    seed_digest = digest_value(seed_material)
    generator = _HashCounterIndices(bytes.fromhex(seed_digest), len(improvements))
    with localcontext() as context:
        context.prec = 50
        estimates = []
        denominator = Decimal(len(improvements))
        for _ in range(10000):
            total = Decimal(0)
            for _ in improvements:
                total += improvements[generator.next()]
            estimates.append(total / denominator)
        return {
            "algorithm_version": BOOTSTRAP_VERSION,
            "confidence_level": "0.95",
            "lower": str(_quantile_type7(estimates, Decimal("0.025"))),
            "resamples": 10000,
            "seed_digest": seed_digest,
            "upper": str(_quantile_type7(estimates, Decimal("0.975"))),
        }


def classify_signal(model: dict[str, Any], baselines: dict[str, dict[str, Any]], intervals: dict[str, dict[str, Any]]) -> str:
    model_brier = Decimal(model["brier"])
    model_log_loss = Decimal(model["log_loss"])
    basic = all(model_brier < Decimal(report["brier"]) and model_log_loss <= Decimal(report["log_loss"]) for report in baselines.values())
    if not basic:
        return "NO BASIC SIGNAL"
    credible = all(Decimal(interval["lower"]) > 0 for interval in intervals.values())
    return "CREDIBLE SIGNAL" if credible else "BASIC SIGNAL"


def dependency_identity() -> dict[str, Any]:
    return {
        "implementation": "Python standard library only",
        "platform": platform.platform(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
    }


def validated_primary_root(config_path: Path) -> Path:
    config = read_json(config_path)
    required = {
        "mode": "activated",
        "namespace": "kalshi-mlb-prospective",
        "timezone_name": "America/New_York",
    }
    for field, expected in required.items():
        if config.get(field) != expected:
            raise FeasibilityError(f"configuration {field} is not the validated PR17C1 value")
    primary = config.get("primary_root")
    if not isinstance(primary, str):
        raise FeasibilityError("configuration has no primary_root")
    root = Path(primary)
    if not root.is_dir() or not (root / "manifest").is_dir() or not (root / "raw").is_dir() or not (root / "normalized").is_dir():
        raise FeasibilityError("configured primary archive is unavailable")
    return root


def _validate_revision(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise FeasibilityError(f"{label} must be a full lowercase Git SHA-1")


def _verify_selected_source_bytes(primary_root: Path, pages: Sequence[SourcePage]) -> str:
    inventory = []
    for page in pages:
        manifest_digest = page.manifest_id.split(":", 1)[1]
        manifest_path = _object_path(primary_root, "manifest", manifest_digest, suffix=".json")
        if digest_file(manifest_path) != page.manifest_digest:
            raise FeasibilityError("source manifest changed during read-only study")
        normalized_path = _object_path(primary_root, "normalized", page.normalized_digest, suffix=".json")
        _assert_digest(normalized_path, page.normalized_digest)
        _assert_digest(page.raw_path, page.raw_digest)
        inventory.append(
            {
                "manifest_file_digest": page.manifest_digest,
                "manifest_id": page.manifest_id,
                "normalized_digest": page.normalized_digest,
                "raw_digest": page.raw_digest,
            }
        )
    return digest_value(inventory)


def freeze_study(*, config_path: Path, output_dir: Path, source_revision: str, source_tree: str) -> dict[str, Any]:
    _validate_revision(source_revision, "source revision")
    _validate_revision(source_tree, "source tree")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FeasibilityError("freeze output directory must not already contain artifacts")
    output_dir.mkdir(parents=True, exist_ok=True)
    code_digest = digest_file(Path(__file__))
    protocol_manifest = {
        "algorithm_version": ALGORITHM_VERSION,
        "code_digest": code_digest,
        "dependency_identity": dependency_identity(),
        "protocol": PROTOCOL,
        "source_revision": source_revision,
        "source_tree": source_tree,
    }
    protocol_digest = digest_value(protocol_manifest)
    write_canonical(output_dir / "protocol_manifest.json", protocol_manifest)

    # Protocol is now frozen.  Only after this write may archive labels be read
    # to form the identity/label seal; no aggregate or model is calculated here.
    primary_root = validated_primary_root(config_path)
    pages = load_mlb_schedule_pages(primary_root)
    selected_bytes_before = _verify_selected_source_bytes(primary_root, pages)
    snapshot = source_snapshot_manifest(pages)
    snapshot_digest = digest_value(snapshot)
    population = resolve_population(pages)
    rows, coverage = build_native_dataset(population)
    by_split = {name: [row for row in rows if row["split"] == name] for name, _, _ in SPLITS}
    for name, split_rows in by_split.items():
        if not split_rows:
            raise FeasibilityError(f"fixed {name} split has no valid native row")

    test_identity_labels = [
        {
            "feature_snapshot_digest": row["feature_snapshot_digest"],
            "game_pk": row["game_pk"],
            "label": row["label"],
            "scheduled_start": row["scheduled_start"],
        }
        for row in by_split["test"]
    ]
    test_row_label_digest = digest_value(test_identity_labels)
    protocol_seal = {
        "freeze_sequence": [
            {"phase": "protocol_manifest_written", "sequence": 1},
            {"phase": "test_row_identity_and_label_digest_frozen_without_aggregate", "sequence": 2},
        ],
        "protocol_digest": protocol_digest,
        "test_row_label_digest": test_row_label_digest,
    }
    write_canonical(output_dir / "protocol_seal.json", protocol_seal)

    train_validation_rows = by_split["training"] + by_split["validation"]
    test_features = [{key: value for key, value in row.items() if key != "label"} for row in by_split["test"]]
    test_labels = [{"game_pk": row["game_pk"], "label": row["label"]} for row in by_split["test"]]
    train_validation_digest = digest_value(train_validation_rows)
    test_features_digest = digest_value(test_features)
    test_labels_digest = digest_value(test_labels)
    dataset_digest = digest_value(
        {
            "feature_version": FEATURE_VERSION,
            "protocol_digest": protocol_digest,
            "source_snapshot_digest": snapshot_digest,
            "test_features_digest": test_features_digest,
            "test_labels_digest": test_labels_digest,
            "test_row_label_digest": test_row_label_digest,
            "train_validation_digest": train_validation_digest,
        }
    )
    coverage_document = coverage_summary(coverage, rows)
    dataset_manifest = {
        "authority": "development-only Derived Analysis; not Evidence",
        "dataset_digest": dataset_digest,
        "field_allowlist": sorted(NATIVE_ROW_FIELDS),
        "market_exclusion": {
            "prohibited_field_terms": sorted(PROHIBITED_FIELD_TERMS),
            "source_allowlist": [{"provider": "mlb-stats-api", "purpose": "schedule"}],
            "transitive_scan": "pass",
        },
        "protocol_digest": protocol_digest,
        "source_snapshot_digest": snapshot_digest,
        "split_membership": {name: [row["game_pk"] for row in by_split[name]] for name, _, _ in SPLITS},
        "test_features_digest": test_features_digest,
        "test_labels_digest": test_labels_digest,
        "test_row_label_digest": test_row_label_digest,
        "train_validation_digest": train_validation_digest,
    }
    write_canonical(output_dir / "source_snapshot_manifest.json", snapshot)
    write_canonical(output_dir / "coverage.json", coverage_document)
    write_canonical(output_dir / "train_validation_rows.json", train_validation_rows)
    write_canonical(output_dir / "test_features.json", test_features)
    write_canonical(output_dir / "test_labels.sealed.json", test_labels)
    write_canonical(output_dir / "dataset_manifest.json", dataset_manifest)
    selected_bytes_after = _verify_selected_source_bytes(primary_root, pages)
    if selected_bytes_before != selected_bytes_after:
        raise FeasibilityError("selected production archive bytes changed")
    freeze_evidence = {
        "archive_access": "read-only; no provider calls, credentials, repair, or archive writes",
        "dataset_digest": dataset_digest,
        "fitting_performed": False,
        "protocol_digest": protocol_digest,
        "selected_source_bytes_after": selected_bytes_after,
        "selected_source_bytes_before": selected_bytes_before,
        "selected_source_bytes_unchanged": True,
        "test_aggregate_calculated": False,
        "test_row_label_digest": test_row_label_digest,
    }
    write_canonical(output_dir / "freeze_evidence.json", freeze_evidence)
    return {"dataset_digest": dataset_digest, "protocol_digest": protocol_digest, "test_row_label_digest": test_row_label_digest, "split_counts": coverage_document["split_counts"]}


def _verify_frozen_inputs(output_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    protocol_manifest = read_json(output_dir / "protocol_manifest.json")
    protocol_seal = read_json(output_dir / "protocol_seal.json")
    dataset_manifest = read_json(output_dir / "dataset_manifest.json")
    if digest_value(protocol_manifest) != protocol_seal.get("protocol_digest"):
        raise FeasibilityError("protocol seal does not match protocol manifest")
    if protocol_manifest.get("code_digest") != digest_file(Path(__file__)):
        raise FeasibilityError("implementation changed after protocol freeze")
    train_validation_rows = read_json(output_dir / "train_validation_rows.json")
    test_features = read_json(output_dir / "test_features.json")
    if digest_value(train_validation_rows) != dataset_manifest.get("train_validation_digest"):
        raise FeasibilityError("training/validation rows do not match dataset seal")
    if digest_value(test_features) != dataset_manifest.get("test_features_digest"):
        raise FeasibilityError("test features do not match dataset seal")
    if dataset_manifest.get("protocol_digest") != protocol_seal.get("protocol_digest"):
        raise FeasibilityError("dataset protocol identity conflicts with protocol seal")
    return protocol_manifest, dataset_manifest, train_validation_rows, test_features


def evaluate_once(*, output_dir: Path) -> dict[str, Any]:
    for forbidden in ("test_opened.marker.json", "result.json", "evaluation_complete.json"):
        if (output_dir / forbidden).exists():
            raise FeasibilityError("sealed test was already opened; a second evaluation is prohibited")
    protocol_manifest, dataset_manifest, train_validation_rows, test_features = _verify_frozen_inputs(output_dir)
    training = [row for row in train_validation_rows if row["split"] == "training"]
    validation = [row for row in train_validation_rows if row["split"] == "validation"]
    if len(training) + len(validation) != len(train_validation_rows):
        raise FeasibilityError("non-training/validation row crossed the pre-test fit boundary")
    model_bundle = fit_model_bundle(
        training,
        validation,
        dependency_identity=protocol_manifest["dependency_identity"],
        protocol_digest=dataset_manifest["protocol_digest"],
        dataset_digest=dataset_manifest["dataset_digest"],
        source_revision=protocol_manifest["source_revision"],
        source_tree=protocol_manifest["source_tree"],
        code_digest=protocol_manifest["code_digest"],
    )
    model_bundle_digest = digest_value(model_bundle)
    write_canonical(output_dir / "model_bundle.json", model_bundle)
    model_seal = {
        "freeze_sequence": [
            {"phase": "protocol_and_test_identity_frozen", "sequence": 2},
            {"phase": "fitted_model_bundle_frozen_before_test_labels_opened", "sequence": 3},
        ],
        "model_bundle_digest": model_bundle_digest,
        "protocol_digest": dataset_manifest["protocol_digest"],
    }
    write_canonical(output_dir / "model_seal.json", model_seal)

    means = [float(value) for value in model_bundle["scaler"]["means"]]
    scales = [float(value) for value in model_bundle["scaler"]["scales"]]
    coefficients = [float(value) for value in model_bundle["primary_estimator"]["parameters"]]
    calibrator = [float(value) for value in model_bundle["calibrator"]["parameters"]]
    predictions = [
        {
            "game_pk": row["game_pk"],
            "probability": _float_text(calibrated_probability(raw_logit(row, means, scales, coefficients), calibrator)),
        }
        for row in test_features
    ]
    predictions.sort(key=lambda item: item["game_pk"])
    prediction_digest = digest_value(predictions)
    write_canonical(output_dir / "predictions.json", predictions)

    # The durable marker is written before labels are read.  A crash after this
    # point is a failed one-look study and cannot be retried under this protocol.
    test_opened_marker = {
        "model_bundle_digest": model_bundle_digest,
        "phase": "sealed_test_open_authorized_once",
        "prediction_digest": prediction_digest,
        "protocol_digest": dataset_manifest["protocol_digest"],
        "sequence": 4,
        "test_row_label_digest": dataset_manifest["test_row_label_digest"],
    }
    write_canonical(output_dir / "test_opened.marker.json", test_opened_marker)
    test_labels = read_json(output_dir / "test_labels.sealed.json")
    if digest_value(test_labels) != dataset_manifest.get("test_labels_digest"):
        raise FeasibilityError("sealed test labels do not match dataset manifest")
    labels_by_game = {item["game_pk"]: item["label"] for item in test_labels}
    if len(labels_by_game) != len(test_labels) or [item["game_pk"] for item in predictions] != sorted(labels_by_game):
        raise FeasibilityError("test prediction/label identity mismatch")
    reconstructed_identity_labels = [
        {
            "feature_snapshot_digest": row["feature_snapshot_digest"],
            "game_pk": row["game_pk"],
            "label": labels_by_game[row["game_pk"]],
            "scheduled_start": row["scheduled_start"],
        }
        for row in sorted(test_features, key=lambda item: item["game_pk"])
    ]
    if digest_value(reconstructed_identity_labels) != dataset_manifest.get("test_row_label_digest"):
        raise FeasibilityError("test row identity/label seal mismatch")
    labels = [labels_by_game[item["game_pk"]] for item in predictions]
    model_probabilities = [item["probability"] for item in predictions]
    even_probabilities = ["0.5"] * len(labels)
    training_home_probability = model_bundle["baseline_probabilities"]["training_home_rate"]
    training_home_probabilities = [training_home_probability] * len(labels)
    model_metrics, model_briers = metric_report(model_probabilities, labels)
    even_metrics, even_briers = metric_report(even_probabilities, labels)
    training_metrics, training_briers = metric_report(training_home_probabilities, labels)
    baseline_metrics = {"even": even_metrics, "training_home_rate": training_metrics}
    baseline_briers = {"even": even_briers, "training_home_rate": training_briers}
    intervals: dict[str, dict[str, Any]] = {}
    mean_improvements: dict[str, str] = {}
    for baseline_name, briers in baseline_briers.items():
        improvements = [baseline - model for baseline, model in zip(briers, model_briers)]
        mean_improvements[baseline_name] = str(sum(improvements, Decimal(0)) / Decimal(len(improvements)))
        seed_material = {
            "algorithm_version": BOOTSTRAP_VERSION,
            "baseline_identity": baseline_name,
            "confidence_level": "0.95",
            "dataset_digest": dataset_manifest["dataset_digest"],
            "model_bundle_digest": model_bundle_digest,
            "protocol_digest": dataset_manifest["protocol_digest"],
            "resamples": 10000,
            "test_game_ids": [item["game_pk"] for item in predictions],
        }
        intervals[baseline_name] = paired_bootstrap(improvements, seed_material)
    classification = classify_signal(model_metrics, baseline_metrics, intervals)
    coverage = read_json(output_dir / "coverage.json")
    result = {
        "classification": classification,
        "authority": "DEVELOPMENT-ONLY DERIVED ANALYSIS; NON-AUTHORITATIVE; NO MODEL OR PROBABILITY SOURCE ADMITTED",
        "baseline_probabilities": model_bundle["baseline_probabilities"],
        "baselines": baseline_metrics,
        "coverage_exclusions": {key: value for key, value in coverage["disposition_counts"].items() if key != "eligible"},
        "dataset_digest": dataset_manifest["dataset_digest"],
        "mean_paired_brier_improvement": mean_improvements,
        "metric_algorithm_version": METRIC_VERSION,
        "model": model_metrics,
        "model_bundle_digest": model_bundle_digest,
        "paired_brier_improvement_95pct_intervals": intervals,
        "prediction_digest": prediction_digest,
        "protocol_digest": dataset_manifest["protocol_digest"],
        "test_population": len(labels),
    }
    result_digest = digest_value(result)
    write_canonical(output_dir / "result.json", result)
    complete = {
        "archive_mutated": False,
        "classification": classification,
        "model_bundle_digest": model_bundle_digest,
        "provider_calls": False,
        "result_digest": result_digest,
        "sealed_test_evaluations": 1,
        "test_open_sequence": 4,
    }
    write_canonical(output_dir / "evaluation_complete.json", complete)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze", help="freeze protocol and test identity/label digest without fitting")
    freeze.add_argument("--config", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    freeze.add_argument("--source-revision", required=True)
    freeze.add_argument("--source-tree", required=True)
    evaluate = subparsers.add_parser("evaluate", help="fit, seal, and evaluate the test exactly once")
    evaluate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "freeze":
            result = freeze_study(config_path=arguments.config, output_dir=arguments.output, source_revision=arguments.source_revision, source_tree=arguments.source_tree)
        else:
            result = evaluate_once(output_dir=arguments.output)
    except FeasibilityError as exc:
        print(json.dumps({"error": str(exc), "status": "failed-closed"}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
