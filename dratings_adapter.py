"""Offline parser for manually captured DRatings MLB prediction snapshots.

This module contains no HTTP client and performs no I/O on import.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from event_contracts import (
    CandidateEvaluation,
    ContractError,
    Evidence,
    NativeIdentifier,
    Provenance,
    ReasonCode,
    ReconciliationResult,
    ValidationReason,
    ValidationStatus,
)
from forecast_adapter import (
    ForecastAdapter,
    ForecastAdapterIssue,
    ForecastAdapterOutcome,
    ForecastAdapterResult,
    ForecastSeries,
    RawForecastSnapshot,
)
from forecast_contracts import (
    AssumptionDisclosure,
    ForecastDistribution,
    ForecastIssueCode,
    ForecastMethodology,
    ForecastModel,
    ForecastObservation,
    ForecastOutcome,
    ForecastProvider,
    ForecastValidationIssue,
    ForecastValidationStatus,
    ForecastVersion,
    MarketIndependence,
    ProbabilityScale,
    ProviderAssumption,
    ProviderReportedAssumptions,
)
from forecast_contracts import PublishedProbability
from mlb_contracts import MLBGame, ScheduleObservation
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIClient, MLBStatsAPIResponse


PROVIDER_ID = "dratings"
MODEL_ID = "dratings:inference-index:mlb"
VERSION_ID = "dratings:inference-index:mlb:unknown"
PARSER_VERSION = "dratings-html-snapshot-v1"
CANONICAL_URL = "https://app.dratings.com/predictor/mlb-baseball-predictions/"
DEFAULT_ACCESS_URL = "https://www.dratings.com/predictor/mlb-baseball-predictions/"

DRATINGS_PROVIDER = ForecastProvider(
    provider_id=PROVIDER_ID,
    name="DRatings",
    website=CANONICAL_URL,
    collection_method="manually captured local HTML snapshot",
    supported_competitions=("MLB",),
)
DRATINGS_MODEL = ForecastModel(
    model_id=MODEL_ID,
    provider_id=PROVIDER_ID,
    name="Inference Index",
    methodology=ForecastMethodology.STATISTICAL,
    market_independence=MarketIndependence.UNKNOWN,
    supported_competitions=("MLB",),
    description="Pops' Edge identity grounded in the methodology name published by DRatings.",
)
DRATINGS_VERSION = ForecastVersion.unknown(version_id=VERSION_ID, model_id=MODEL_ID)

TEAM_ALIASES = {"Oakland Athletics": "Athletics"}
_DETAIL_RE = re.compile(r"/predictor/mlb-baseball-predictions/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})")


class DRatingsSnapshotError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DRatingsForecastRow:
    row_number: int
    source_locator: str
    scheduled_at: datetime | None
    team_names: tuple[str, ...]
    team_links: tuple[str, ...]
    team_records: tuple[str, ...]
    pitcher_names: tuple[str, ...]
    probability_texts: tuple[str, ...]
    detail_path: str | None
    raw_row_html: str


@dataclass(frozen=True, slots=True)
class DRatingsSnapshot:
    raw: RawForecastSnapshot
    upcoming_date_label: str
    rows: tuple[DRatingsForecastRow, ...]


@dataclass(frozen=True, slots=True)
class MLBReconciliationCandidate:
    game: MLBGame
    schedule: ScheduleObservation


def _plain(fragment: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def _attributes(fragment: str, name: str) -> tuple[str, ...]:
    return tuple(html.unescape(value) for value in re.findall(fr'{name}=["\']([^"\']+)["\']', fragment, re.I))


class DRatingsAdapter(ForecastAdapter):
    def parse_snapshot(self, path: str, *, captured_at: datetime, access_url: str | None = DEFAULT_ACCESS_URL) -> DRatingsSnapshot:
        source = Path(path)
        raw_bytes = source.read_bytes()
        try:
            document = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DRatingsSnapshotError("snapshot must be UTF-8 HTML") from error

        canonical_match = re.search(r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:url["\'][^>]*>', document, re.I)
        if canonical_match is None:
            canonical_match = re.search(r'<meta\s+[^>]*property=["\']og:url["\'][^>]*content=["\']([^"\']+)["\'][^>]*>', document, re.I)
        canonical_url = html.unescape(canonical_match.group(1)) if canonical_match else None
        update_match = re.search(r'<div class="subheader-heading">.*?<time\s+datetime="([^"]+)"', document, re.I | re.S)
        page_updated = self._timestamp(update_match.group(1)) if update_match else None

        section_match = re.search(
            r'<div[^>]+id=["\']scroll-upcoming["\'][^>]*>\s*<h2[^>]*>(.*?)</h2>\s*<table[^>]*>(.*?)</table>',
            document,
            re.I | re.S,
        )
        if section_match is None:
            raise DRatingsSnapshotError("unsupported layout: Upcoming table not found")
        heading = _plain(section_match.group(1))
        if re.fullmatch(r"Upcoming Games for [A-Za-z]+ \d{1,2}, \d{4}", heading) is None:
            raise DRatingsSnapshotError(f"unsupported Upcoming heading: {heading!r}")
        table = section_match.group(2)
        header_match = re.search(r"<thead[^>]*>(.*?)</thead>", table, re.I | re.S)
        headers = tuple(_plain(item).replace("\n", " ") for item in re.findall(r"<th[^>]*>(.*?)</th>", header_match.group(1), re.I | re.S)) if header_match else ()
        if headers[:4] != ("Time", "Teams", "Pitchers", "Win"):
            raise DRatingsSnapshotError(f"unsupported Upcoming columns: {headers!r}")
        body_match = re.search(r"<tbody[^>]*>(.*?)</tbody>", table, re.I | re.S)
        if body_match is None:
            raise DRatingsSnapshotError("unsupported layout: Upcoming table body not found")

        rows = tuple(self._parse_row(index, row_html) for index, row_html in enumerate(re.findall(r"<tr[^>]*>(.*?)</tr>", body_match.group(1), re.I | re.S), 1))
        if not rows:
            raise DRatingsSnapshotError("unsupported layout: Upcoming table has no rows")
        canonical_payload = {
            "canonical_url": canonical_url,
            "page_updated_at": page_updated.isoformat() if page_updated else None,
            "upcoming_heading": heading,
            "rows": [self._canonical_row(row) for row in rows],
        }
        raw_digest = hashlib.sha256(raw_bytes).hexdigest()
        canonical_digest = hashlib.sha256(json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        evidence = RawForecastSnapshot(
            provider_id=PROVIDER_ID,
            local_source_ref=str(source),
            captured_at=captured_at,
            raw_sha256=raw_digest,
            canonical_evidence_sha256=canonical_digest,
            parser_version=PARSER_VERSION,
            canonical_source_url=canonical_url,
            access_url=access_url,
            provider_page_updated_at=page_updated,
            transformations=("decoded UTF-8 HTML", "selected Upcoming table only", "canonicalized parsed evidence for SHA-256"),
        )
        return DRatingsSnapshot(evidence, heading, rows)

    def transform(self, evidence: DRatingsSnapshot, *, canonical_events: tuple[MLBReconciliationCandidate, ...]) -> tuple[ForecastAdapterResult, ...]:
        return tuple(self._transform_row(row, evidence.raw, canonical_events) for row in evidence.rows)

    def _parse_row(self, row_number: int, row_html: str) -> DRatingsForecastRow:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.I | re.S)
        time_match = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', cells[0], re.I) if cells else None
        scheduled = None
        if time_match:
            try:
                scheduled = self._timestamp(time_match.group(1))
            except ValueError:
                scheduled = None
        team_links = tuple(re.findall(r'<a\s+href=["\'](/teams/mlb-baseball-ratings/[^"\']+)["\'][^>]*>.*?</a>', cells[1], re.I | re.S)) if len(cells) > 1 else ()
        teams = tuple(_plain(value) for value in re.findall(r'<a\s+href=["\']/teams/mlb-baseball-ratings/[^"\']+["\'][^>]*>(.*?)</a>', cells[1], re.I | re.S)) if len(cells) > 1 else ()
        records = tuple(_plain(value).strip("()") for value in re.findall(r'<span class="[^"]*tf--mono[^"]*">(.*?)</span>', cells[1], re.I | re.S)) if len(cells) > 1 else ()
        pitchers = tuple(value for value in (_plain(item) for item in re.findall(r'<span class="[^"]*table-cell--mw[^"]*">(.*?)</span>', cells[2], re.I | re.S)) if value) if len(cells) > 2 else ()
        probabilities = tuple(_plain(item) for item in re.findall(r'<span[^>]*>(.*?)</span>', cells[3], re.I | re.S) if "%" in _plain(item)) if len(cells) > 3 else ()
        detail_match = _DETAIL_RE.search(row_html)
        detail_path = detail_match.group(0) if detail_match else None
        locator = f"upcoming/table[1]/detail-path:{detail_match.group(1)}" if detail_match else f"upcoming/table[1]/row:{row_number}"
        return DRatingsForecastRow(row_number, locator, scheduled, teams, team_links, records, pitchers, probabilities, detail_path, row_html)

    def _transform_row(self, row: DRatingsForecastRow, raw: RawForecastSnapshot, candidates: tuple[MLBReconciliationCandidate, ...]) -> ForecastAdapterResult:
        source = NativeIdentifier("dratings-row-locator", row.source_locator)
        base_evidence = self._row_evidence(row)
        malformed = []
        if row.scheduled_at is None:
            malformed.append("scheduled UTC datetime is missing or malformed")
        if len(row.team_names) != 2:
            malformed.append("row must publish exactly two ordered teams")
        if len(row.probability_texts) != 2:
            malformed.append("row must publish exactly two win probabilities")
        parsed_probabilities: tuple[tuple[Decimal, str, int], ...] = ()
        if not malformed:
            try:
                parsed_probabilities = tuple(self._probability(value) for value in row.probability_texts)
            except (InvalidOperation, ValueError) as error:
                malformed.append(str(error))
        if malformed:
            reason = ValidationReason(ReasonCode.VALIDATION_FAILURE, "; ".join(malformed))
            reconciliation = ReconciliationResult.rejected(source, evidence=base_evidence, reasons=(reason,))
            return self._unresolved(row, raw, ForecastAdapterOutcome.REJECTED, reconciliation, "malformed-source-row", reason.detail)

        mapped_names = tuple(TEAM_ALIASES.get(value, value) for value in row.team_names)
        participant_candidates = tuple(
            item
            for item in candidates
            if len(set(mapped_names)) == 2
            and set((item.game.away_team.display_name, item.game.home_team.display_name)) == set(mapped_names)
        )
        evaluations = tuple(self._candidate_evaluation(item, row) for item in participant_candidates)
        matches = tuple(item for item in participant_candidates if item.schedule.scheduled_start == row.scheduled_at)
        if len(matches) > 1:
            reason = ValidationReason(ReasonCode.AMBIGUOUS_CANDIDATES, "multiple MLB events match the ordered teams and exact scheduled UTC time")
            reconciliation = ReconciliationResult.ambiguous(source, tuple(item.game.event for item in matches), evidence=base_evidence, reasons=(reason,), candidate_evaluations=tuple(self._candidate_evaluation(item, row) for item in matches))
            return self._unresolved(row, raw, ForecastAdapterOutcome.AMBIGUOUS, reconciliation, "ambiguous-event", reason.detail)
        if len(matches) != 1:
            detail = "no MLB event matches the ordered teams and exact scheduled UTC time"
            reason = ValidationReason(ReasonCode.NO_MATCHING_EVENT, detail)
            reconciliation = ReconciliationResult.rejected(source, evidence=base_evidence, reasons=(reason,), candidate_evaluations=evaluations)
            return self._unresolved(row, raw, ForecastAdapterOutcome.REJECTED, reconciliation, "unmatched-event", detail)

        match = matches[0]
        roles = self._source_roles(mapped_names, match.game)
        if roles is None:
            detail = "source positions cannot be aligned uniquely to MLB away/home participants"
            rejected = ReconciliationResult.rejected(
                source,
                evidence=base_evidence,
                reasons=(ValidationReason(ReasonCode.CONFLICTING_NATIVE_IDENTITY, detail),),
                candidate_evaluations=(self._candidate_evaluation(match, row),),
            )
            return self._unresolved(row, raw, ForecastAdapterOutcome.REJECTED, rejected, "orientation-conflict", detail)
        reconciliation = ReconciliationResult.matched(
            source,
            match.game.event,
            evidence=base_evidence + (Evidence("mlb-schedule-observation", match.schedule.observation_id),),
            source_mapping=NativeIdentifier("mlb-game", str(match.game.game_pk)),
            candidate_evaluations=(self._candidate_evaluation(match, row),),
        )
        distribution = self._distribution(row, parsed_probabilities, match.game, roles)
        if distribution.validation_status is ForecastValidationStatus.INVALID:
            detail = distribution.validation_issues[0].detail
            rejected = ReconciliationResult.rejected(source, evidence=base_evidence, reasons=(ValidationReason(ReasonCode.VALIDATION_FAILURE, detail),), candidate_evaluations=(self._candidate_evaluation(match, row),))
            return self._unresolved(row, raw, ForecastAdapterOutcome.REJECTED, rejected, "invalid-distribution", detail)

        assumptions, assumption_issues = self._assumptions(row, roles)
        metadata_issues = []
        if raw.canonical_source_url is None:
            metadata_issues.append(ForecastAdapterIssue("missing-canonical-source-url", "provider canonical URL is absent from the snapshot"))
        if raw.provider_page_updated_at is None:
            metadata_issues.append(ForecastAdapterIssue("missing-page-update-timestamp", "provider page-level update timestamp is absent"))
        issues = assumption_issues + tuple(metadata_issues)
        validation_issues = tuple(ForecastValidationIssue(ForecastIssueCode.MATERIAL_INFORMATION_MISSING, issue.detail) for issue in issues)
        validation_status = ForecastValidationStatus.INCOMPLETE if issues else ForecastValidationStatus.VALID
        provenance = Provenance(
            provider=PROVIDER_ID,
            source_record_id=row.source_locator,
            canonical_event_id=match.game.event.canonical_event_id,
            collected_at=raw.captured_at,
            source_timestamp=None,
            transformations=(f"parsed by {PARSER_VERSION}", "selected Upcoming table", "resolved ordered source teams to MLB away/home roles", "matched exact scheduled UTC time"),
            validation_status=ValidationStatus.INCOMPLETE if issues else ValidationStatus.VALID,
            validation_reasons=tuple(ValidationReason(ReasonCode.VALIDATION_FAILURE, issue.detail) for issue in issues),
            raw_evidence_ref=f"sha256:{raw.raw_sha256}",
            source_url=raw.canonical_source_url,
            collector_version=PARSER_VERSION,
        )
        observation_hash = hashlib.sha256(f"{row.source_locator}|{raw.captured_at.isoformat()}|{raw.canonical_evidence_sha256}".encode()).hexdigest()[:24]
        observation = ForecastObservation(
            observation_id=f"dratings-observation:{observation_hash}",
            version_id=VERSION_ID,
            reconciliation=reconciliation,
            distribution=distribution,
            assumptions=assumptions,
            collected_at=raw.captured_at,
            provenance=provenance,
            provider_published_at=None,
            provider_effective_at=None,
            provider_updated_at=None,
            schedule_observation_id=match.schedule.observation_id,
            validation_status=validation_status,
            validation_issues=validation_issues,
        )
        series = ForecastSeries.create(DRATINGS_PROVIDER, DRATINGS_MODEL, DRATINGS_VERSION, match.game.event)
        outcome = ForecastAdapterOutcome.PARTIAL if issues else ForecastAdapterOutcome.COMPLETE
        return ForecastAdapterResult(row.source_locator, raw, outcome, reconciliation, series, observation, issues)

    @staticmethod
    def _probability(value: str) -> tuple[Decimal, str, int]:
        match = re.fullmatch(r"\s*(\d+(?:\.(\d+))?)%\s*", value)
        if not match:
            raise ValueError(f"malformed percent probability: {value!r}")
        precision = len(match.group(2) or "")
        return Decimal(match.group(1)) / Decimal(100), value, precision

    @staticmethod
    def _distribution(
        row: DRatingsForecastRow,
        probabilities: tuple[tuple[Decimal, str, int], ...],
        game: MLBGame,
        roles: tuple[str, str],
    ) -> ForecastDistribution:
        values = []
        for source_position, (role, (probability, source, precision)) in enumerate(zip(roles, probabilities)):
            semantic = f"{role}-win"
            participant = game.away_team if role == "away" else game.home_team
            outcome = ForecastOutcome(participant.canonical_team_id, semantic, game.event.canonical_event_id, row.team_names[source_position])
            values.append(PublishedProbability(outcome, probability, source, precision, ProbabilityScale.PERCENT))
        return ForecastDistribution(tuple(values))

    @staticmethod
    def _assumptions(row: DRatingsForecastRow, roles: tuple[str, str]) -> tuple[ProviderReportedAssumptions, tuple[ForecastAdapterIssue, ...]]:
        assumptions = tuple(ProviderAssumption(f"{role}-pitcher", f"{role.title()} pitcher", value, "starting-pitcher", value) for role, value in zip(roles, row.pitcher_names) if value)
        if len(assumptions) == 2:
            return ProviderReportedAssumptions(AssumptionDisclosure.REPORTED, assumptions, "ordered Pitchers table cell"), ()
        issue = ForecastAdapterIssue("missing-provider-assumption", "one or both displayed starting-pitcher assumptions are absent")
        if assumptions:
            return ProviderReportedAssumptions(AssumptionDisclosure.REPORTED, assumptions, "ordered Pitchers table cell"), (issue,)
        return ProviderReportedAssumptions(AssumptionDisclosure.UNDISCLOSED), (issue,)

    @staticmethod
    def _source_roles(mapped_names: tuple[str, ...], game: MLBGame) -> tuple[str, str] | None:
        role_by_name = {
            game.away_team.display_name: "away",
            game.home_team.display_name: "home",
        }
        roles = tuple(role_by_name.get(name) for name in mapped_names)
        if len(roles) != 2 or set(roles) != {"away", "home"}:
            return None
        return cast(tuple[str, str], roles)

    @staticmethod
    def _row_evidence(row: DRatingsForecastRow) -> tuple[Evidence, ...]:
        items = [Evidence("source-row-locator", row.source_locator)]
        if row.scheduled_at:
            items.append(Evidence("scheduled-utc", row.scheduled_at.isoformat()))
        if row.team_names:
            items.append(Evidence("ordered-team-names", " | ".join(row.team_names)))
        if row.detail_path:
            items.append(Evidence("detail-path", row.detail_path))
        return tuple(items)

    @staticmethod
    def _candidate_evaluation(item: MLBReconciliationCandidate, row: DRatingsForecastRow) -> CandidateEvaluation:
        exact_time = item.schedule.scheduled_start == row.scheduled_at
        return CandidateEvaluation(
            item.game.event.canonical_event_id,
            mappings_evaluated=(NativeIdentifier("mlb-game", str(item.game.game_pk)),),
            evidence=(Evidence("ordered-mlb-teams", f"{item.game.away_team.display_name} | {item.game.home_team.display_name}"), Evidence("mlb-scheduled-utc", item.schedule.scheduled_start.isoformat())),
            reasons=() if exact_time else (ValidationReason(ReasonCode.CONFLICTING_SCHEDULE, "candidate scheduled UTC time differs"),),
        )

    @staticmethod
    def _unresolved(row: DRatingsForecastRow, raw: RawForecastSnapshot, outcome: ForecastAdapterOutcome, reconciliation: ReconciliationResult, code: str, detail: str) -> ForecastAdapterResult:
        return ForecastAdapterResult(row.source_locator, raw, outcome, reconciliation, issues=(ForecastAdapterIssue(code, detail),))

    @staticmethod
    def _timestamp(value: str) -> datetime:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return result

    @staticmethod
    def _canonical_row(row: DRatingsForecastRow) -> dict[str, object]:
        return {
            "row_number": row.row_number,
            "source_locator": row.source_locator,
            "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at else None,
            "team_names": row.team_names,
            "team_links": row.team_links,
            "team_records": row.team_records,
            "pitcher_names": row.pitcher_names,
            "probability_texts": row.probability_texts,
            "detail_path": row.detail_path,
        }


def load_mlb_reconciliation_candidates(path: str, *, collected_at: datetime) -> tuple[MLBReconciliationCandidate, ...]:
    """Parse a separately captured MLB schedule fixture through the PR5 adapter."""
    source = Path(path)
    raw = source.read_bytes()
    payload = json.loads(raw)
    dates = payload.get("dates")
    if not isinstance(dates, list) or not dates or not isinstance(dates[0], dict) or not isinstance(dates[0].get("date"), str):
        raise ValueError("MLB schedule fixture must contain a dated schedule response")
    endpoint, parameters = MLBStatsAPIClient.schedule_request(datetime.fromisoformat(dates[0]["date"]).date())
    response = MLBStatsAPIResponse(endpoint, parameters, collected_at, 200, endpoint, payload, raw)
    result = MLBStatsAPIAdapter().parse_response(response)
    return tuple(MLBReconciliationCandidate(item.game, item.schedule_observation) for item in result.games if item.game is not None and item.schedule_observation is not None)
