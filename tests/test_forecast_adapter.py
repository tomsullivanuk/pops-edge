import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from dratings_adapter import (
    CANONICAL_URL,
    DEFAULT_ACCESS_URL,
    DRATINGS_MODEL,
    DRATINGS_PROVIDER,
    DRATINGS_VERSION,
    DRatingsAdapter,
    DRatingsSnapshotError,
    MLBReconciliationCandidate,
    load_mlb_reconciliation_candidates,
)
from event_contracts import ContractError, Provenance, ValidationStatus
from forecast_adapter import ForecastAdapterOutcome, ForecastHistory, ForecastSeries
from forecast_contracts import ForecastModel, ForecastValidationStatus
from inspect_dratings_snapshot import run as run_inspection
from mlb_contracts import ScheduleObservation, make_mlb_game


FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT = FIXTURES / "dratings_mlb_snapshot_2026-07-31.html"
MLB_FIXTURE = FIXTURES / "mlb_stats_api_2026-07-31.json"
CAPTURED = datetime.fromisoformat("2026-07-31T17:53:55-05:00")
RAW_DIGEST = "7c36d3399b3cf1e916b2c3492faa2b1db209d7bd29ad408902bdf2b3311a6ff8"


class AdapterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = DRatingsAdapter()
        cls.snapshot = cls.adapter.parse_snapshot(str(SNAPSHOT), captured_at=CAPTURED)
        cls.candidates = load_mlb_reconciliation_candidates(str(MLB_FIXTURE), collected_at=CAPTURED)
        cls.results = cls.adapter.transform(cls.snapshot, canonical_events=cls.candidates)

    def mutated_snapshot(self, old, new):
        return self.mutated_snapshot_many(((old, new),))

    def mutated_snapshot_many(self, replacements):
        value = SNAPSHOT.read_text(encoding="utf-8")
        for old, new in replacements:
            value = value.replace(old, new, 1)
        temporary = tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False)
        temporary.write(value)
        temporary.close()
        self.addCleanup(Path(temporary.name).unlink)
        return self.adapter.parse_snapshot(temporary.name, captured_at=CAPTURED)


class ForecastSeriesTests(AdapterTestCase):
    def test_deterministic_immutable_series_and_serialization(self):
        first = self.results[0]
        duplicate = ForecastSeries.create(DRATINGS_PROVIDER, DRATINGS_MODEL, DRATINGS_VERSION, first.reconciliation.matched_event)
        self.assertEqual(first.series, duplicate)
        self.assertEqual(ForecastSeries.from_json(first.series.to_json()), first.series)
        self.assertNotIn("probab", first.series.to_json())
        with self.assertRaises(FrozenInstanceError):
            first.series.version_id = "changed"

    def test_hierarchy_integrity(self):
        invalid_model = replace(DRATINGS_MODEL, provider_id="some-other-provider")
        with self.assertRaises(ContractError):
            ForecastSeries.create(DRATINGS_PROVIDER, invalid_model, DRATINGS_VERSION, self.results[0].reconciliation.matched_event)
        invalid_version = replace(DRATINGS_VERSION, model_id="some-other-model")
        with self.assertRaises(ContractError):
            ForecastSeries.create(DRATINGS_PROVIDER, DRATINGS_MODEL, invalid_version, self.results[0].reconciliation.matched_event)

    def test_lazy_series_and_no_empty_history(self):
        unmatched = self.adapter.transform(self.snapshot, canonical_events=())[0]
        self.assertIs(unmatched.outcome, ForecastAdapterOutcome.REJECTED)
        self.assertIsNone(unmatched.series)
        self.assertIsNone(unmatched.observation)
        with self.assertRaises(ContractError):
            ForecastHistory(self.results[0].series, ())

    def test_append_only_history_and_derived_current(self):
        first = self.results[0]
        later_snapshot = replace(self.snapshot, raw=replace(self.snapshot.raw, captured_at=CAPTURED + timedelta(hours=1)))
        later = self.adapter.transform(later_snapshot, canonical_events=self.candidates)[0]
        history = ForecastHistory(first.series, (later.observation, first.observation))
        self.assertEqual(history.observations[0], first.observation)
        self.assertEqual(history.current, later.observation)
        self.assertEqual(first.observation.collected_at, CAPTURED)
        with self.assertRaises(ContractError):
            ForecastHistory(first.series, (first.observation, first.observation))

    def test_history_rejects_incompatible_provider_or_version_chain(self):
        first = self.results[0]
        wrong_provider = replace(first.observation, provenance=replace(first.observation.provenance, provider="other-provider"))
        wrong_version = replace(first.observation, version_id="other-version")
        with self.assertRaises(ContractError):
            ForecastHistory(first.series, (wrong_provider,))
        with self.assertRaises(ContractError):
            ForecastHistory(first.series, (wrong_version,))

    def test_same_detail_locator_distinguishes_separate_capture_evidence(self):
        first = self.results[0]
        changed = self.mutated_snapshot_many((("46.1%", "45.1%"), ("53.9%", "54.9%")))
        changed = replace(changed, raw=replace(changed.raw, captured_at=CAPTURED + timedelta(minutes=30)))
        second = self.adapter.transform(changed, canonical_events=self.candidates)[0]
        self.assertEqual(first.source_locator, second.source_locator)
        self.assertEqual(first.series, second.series)
        self.assertNotEqual(first.observation.observation_id, second.observation.observation_id)
        self.assertNotEqual(first.observation.distribution, second.observation.distribution)
        history = ForecastHistory(first.series, (first.observation, second.observation))
        self.assertEqual(history.observations[0], first.observation)


class FaithfulParsingTests(AdapterTestCase):
    def test_upcoming_rows_and_page_metadata(self):
        self.assertEqual(len(self.snapshot.rows), 13)
        self.assertEqual(self.snapshot.upcoming_date_label, "Upcoming Games for July 31, 2026")
        self.assertEqual(self.snapshot.raw.canonical_source_url, CANONICAL_URL)
        self.assertEqual(self.snapshot.raw.access_url, DEFAULT_ACCESS_URL)
        self.assertEqual(self.snapshot.raw.provider_page_updated_at, datetime(2026, 7, 31, 22, 52, 31, tzinfo=timezone.utc))
        self.assertEqual(self.snapshot.raw.captured_at, CAPTURED)

    def test_first_row_exact_source_evidence(self):
        row = self.snapshot.rows[0]
        self.assertEqual(row.scheduled_at, datetime(2026, 7, 31, 23, 5, tzinfo=timezone.utc))
        self.assertEqual(row.team_names, ("Philadelphia Phillies", "Baltimore Orioles"))
        self.assertEqual(row.pitcher_names, ("Andrew Painter", "Brandon Young"))
        self.assertEqual(row.probability_texts, ("46.1%", "53.9%"))
        self.assertTrue(row.source_locator.startswith("upcoming/table[1]/detail-path:"))

    def test_probability_precision_and_no_row_timestamps(self):
        observation = self.results[0].observation
        values = observation.distribution.probabilities
        self.assertEqual({item.source_representation for item in values}, {"46.1%", "53.9%"})
        self.assertEqual({item.published_precision for item in values}, {1})
        self.assertEqual(str(observation.distribution.observed_total), "1.000")
        self.assertIsNone(observation.provider_published_at)
        self.assertIsNone(observation.provider_updated_at)
        self.assertIsNone(observation.provenance.source_timestamp)
        self.assertIs(self.results[0].outcome, ForecastAdapterOutcome.COMPLETE)
        self.assertIs(observation.validation_status, ForecastValidationStatus.VALID)

    def test_raw_and_canonical_digests_are_deterministic_and_distinct(self):
        repeated = self.adapter.parse_snapshot(str(SNAPSHOT), captured_at=CAPTURED)
        self.assertEqual(self.snapshot.raw.raw_sha256, RAW_DIGEST)
        self.assertEqual(self.snapshot.raw, repeated.raw)
        self.assertNotEqual(self.snapshot.raw.raw_sha256, self.snapshot.raw.canonical_evidence_sha256)

    def test_only_upcoming_table_is_parsed(self):
        document = SNAPSHOT.read_text(encoding="utf-8")
        self.assertIn("Games In Progress", document)
        self.assertIn("Completed Games", document)
        self.assertEqual(len(self.snapshot.rows), 13)

    def test_unsupported_layout_fails_top_level(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as temporary:
            temporary.write("<html><body>not a predictions page</body></html>")
            path = temporary.name
        self.addCleanup(Path(path).unlink)
        with self.assertRaises(DRatingsSnapshotError):
            self.adapter.parse_snapshot(path, captured_at=CAPTURED)

    def test_required_heading_and_column_drift_fail_closed(self):
        with self.assertRaises(DRatingsSnapshotError):
            self.mutated_snapshot("Upcoming Games for July 31, 2026", "Future Games for July 31, 2026")
        with self.assertRaises(DRatingsSnapshotError):
            self.mutated_snapshot("<span>Pitchers</span>", "<span>Starters</span>")

    def test_malformed_probability_rejected_without_series(self):
        snapshot = self.mutated_snapshot("46.1%", "not-a-percent")
        result = self.adapter.transform(snapshot, canonical_events=self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.REJECTED)
        self.assertIsNone(result.series)
        self.assertIn("malformed-source-row", {issue.code for issue in result.issues})

    def test_missing_pitcher_is_partial(self):
        snapshot = self.mutated_snapshot(">Andrew Painter<", "><")
        result = self.adapter.transform(snapshot, canonical_events=self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.PARTIAL)
        self.assertIsNotNone(result.series)
        self.assertIs(result.observation.validation_status, ForecastValidationStatus.INCOMPLETE)

    def test_missing_optional_page_metadata_is_partial(self):
        snapshot = self.mutated_snapshot(' property="og:url"', ' property="removed:url"')
        result = self.adapter.transform(snapshot, canonical_events=self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.PARTIAL)
        self.assertIn("missing-canonical-source-url", {issue.code for issue in result.issues})

    def test_mixed_row_outcomes_do_not_discard_valid_rows(self):
        snapshot = self.mutated_snapshot("46.1%", "bad-probability")
        results = self.adapter.transform(snapshot, canonical_events=self.candidates)
        self.assertEqual(len(results), 13)
        self.assertIs(results[0].outcome, ForecastAdapterOutcome.REJECTED)
        self.assertTrue(all(item.outcome is ForecastAdapterOutcome.COMPLETE for item in results[1:]))


class ReconciliationTests(AdapterTestCase):
    def first_row_candidate(self):
        return next(item for item in self.candidates if item.game.game_pk == 824809)

    def reversed_first_row_snapshot(self):
        return self.mutated_snapshot_many((
            ("/19-philadelphia-phillies", "/__SOURCE_TEAM_LINK_ONE__"),
            ("/1-baltimore-orioles", "/19-philadelphia-phillies"),
            ("/__SOURCE_TEAM_LINK_ONE__", "/1-baltimore-orioles"),
            ("Philadelphia Phillies", "__SOURCE_TEAM_ONE__"),
            ("Baltimore Orioles", "Philadelphia Phillies"),
            ("__SOURCE_TEAM_ONE__", "Baltimore Orioles"),
            ("(57-52)", "__SOURCE_RECORD_ONE__"),
            ("(53-56)", "(57-52)"),
            ("__SOURCE_RECORD_ONE__", "(53-56)"),
            ("Andrew Painter", "__SOURCE_PITCHER_ONE__"),
            ("Brandon Young", "Andrew Painter"),
            ("__SOURCE_PITCHER_ONE__", "Brandon Young"),
            ("46.1%", "__SOURCE_PROBABILITY_ONE__"),
            ("53.9%", "46.1%"),
            ("__SOURCE_PROBABILITY_ONE__", "53.9%"),
        ))

    def test_all_faithful_rows_uniquely_reconcile(self):
        self.assertEqual(len(self.results), 13)
        self.assertTrue(all(result.outcome is ForecastAdapterOutcome.COMPLETE for result in self.results))
        self.assertEqual(len({result.series.series_id for result in self.results}), 13)

    def test_controlled_oakland_alias_and_home_away_resolution(self):
        result = next(item for item in self.results if item.observation.distribution.probabilities[0].outcome.provider_label == "Detroit Tigers")
        labels = tuple(item.outcome.provider_label for item in result.observation.distribution.probabilities)
        semantics = tuple(item.outcome.semantic for item in result.observation.distribution.probabilities)
        self.assertEqual(labels, ("Detroit Tigers", "Oakland Athletics"))
        self.assertEqual(semantics, ("away-win", "home-win"))
        self.assertEqual(result.reconciliation.matched_event.canonical_event_id, "mlb:824975")

    def test_reversed_provider_display_order_resolves_roles_from_mlb(self):
        snapshot = self.reversed_first_row_snapshot()
        row = snapshot.rows[0]
        self.assertEqual(row.team_names, ("Baltimore Orioles", "Philadelphia Phillies"))
        self.assertEqual(row.probability_texts, ("53.9%", "46.1%"))
        result = self.adapter.transform(snapshot, canonical_events=self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.COMPLETE)
        probabilities = {item.outcome.semantic: item for item in result.observation.distribution.probabilities}
        self.assertEqual(probabilities["away-win"].outcome.outcome_id, "mlb-team:143")
        self.assertEqual(probabilities["home-win"].outcome.outcome_id, "mlb-team:110")
        self.assertEqual(probabilities["away-win"].outcome.provider_label, "Philadelphia Phillies")
        self.assertEqual(probabilities["away-win"].source_representation, "46.1%")
        self.assertEqual(probabilities["home-win"].outcome.provider_label, "Baltimore Orioles")
        self.assertEqual(probabilities["home-win"].source_representation, "53.9%")
        assumptions = {item.assumption_id: item.provider_value for item in result.observation.assumptions.assumptions}
        self.assertEqual(assumptions, {"away-pitcher": "Andrew Painter", "home-pitcher": "Brandon Young"})

    def test_orientation_conflict_fails_closed(self):
        snapshot = self.mutated_snapshot("Baltimore Orioles", "Philadelphia Phillies")
        result = self.adapter.transform(snapshot, canonical_events=self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.REJECTED)
        self.assertIsNone(result.series)
        self.assertIsNone(result.observation)

    def test_conflicting_time_rejected_with_candidate_evidence(self):
        candidate = self.first_row_candidate()
        changed_schedule = replace(candidate.schedule, scheduled_start=candidate.schedule.scheduled_start + timedelta(minutes=1))
        changed = tuple(MLBReconciliationCandidate(item.game, changed_schedule) if item.game.game_pk == candidate.game.game_pk else item for item in self.candidates)
        result = self.adapter.transform(self.snapshot, canonical_events=changed)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.REJECTED)
        self.assertTrue(result.reconciliation.candidate_evaluations)
        self.assertIsNone(result.series)

    def test_no_fuzzy_forced_match(self):
        result = self.adapter.transform(self.snapshot, canonical_events=tuple(item for item in self.candidates if item.game.game_pk != 824809))[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.REJECTED)
        self.assertIsNone(result.reconciliation.matched_event)

    def test_ambiguous_candidates_fail_closed(self):
        first = self.first_row_candidate()
        duplicate = MLBReconciliationCandidate(first.game, first.schedule)
        result = self.adapter.transform(self.snapshot, canonical_events=(duplicate,) + self.candidates)[0]
        self.assertIs(result.outcome, ForecastAdapterOutcome.AMBIGUOUS)
        self.assertEqual(len(result.reconciliation.candidate_events), 2)
        self.assertIsNone(result.series)
        self.assertIsNone(result.observation)

    def test_no_dratings_gamepk_or_stable_record_claim(self):
        source = SNAPSHOT.read_text(encoding="utf-8")
        self.assertNotIn("gamePk", source)
        result_json = self.results[0].to_json()
        self.assertNotIn("provider_record", result_json)
        self.assertIn("source-row-locator", result_json)


class InspectionCommandTests(AdapterTestCase):
    def test_explicit_snapshot_path_required(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                run_inspection([])

    def test_valid_local_inspection_and_no_network(self):
        stdout = io.StringIO()
        with patch("requests.sessions.Session.request", side_effect=AssertionError("network forbidden")):
            with redirect_stdout(stdout):
                code = run_inspection([str(SNAPSHOT), "--mlb-fixture", str(MLB_FIXTURE)])
        self.assertEqual(code, 0)
        self.assertIn("parsed=13 matched=13", stdout.getvalue())

    def test_unreadable_and_unsupported_sources_return_nonzero(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(run_inspection(["/does/not/exist.html"]), 1)
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as temporary:
            temporary.write("<html></html>")
            path = temporary.name
        self.addCleanup(Path(path).unlink)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(run_inspection([path]), 1)

    def test_gitignore_exception_is_narrowly_scoped(self):
        rules = (Path(__file__).parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("*.html", rules)
        self.assertIn("!tests/fixtures/dratings_mlb_snapshot_2026-07-31.html", rules)
        self.assertEqual([rule for rule in rules if rule.startswith("!tests/fixtures/")], ["!tests/fixtures/dratings_mlb_snapshot_2026-07-31.html"])


if __name__ == "__main__":
    unittest.main()
