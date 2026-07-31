import copy
import json
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from event_contracts import ContractError, ValidationStatus
from mlb_contracts import GameStatus, LineageType, PitcherState
from mlb_stats_api import (
    AdapterComponent,
    AdapterIssueCode,
    AdapterIssueSeverity,
    AdapterOutcome,
    BASE_URL,
    MLBStatsAPIAdapter,
    MLBStatsAPIClient,
    MLBStatsAPIError,
    MLBStatsAPIResponse,
    MLBStatsAdapterResult,
    PROVIDER_ID,
)
from smoke_mlb_stats_api import run as run_smoke


FIXTURE = Path(__file__).parent / "fixtures" / "mlb_stats_api_schedule.json"
COLLECTED = datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)


class MockResponse:
    def __init__(self, status_code=200, payload=None, *, json_error=None, content=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"dates": []}
        self._json_error = json_error
        self.url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        self.content = content if content is not None else json.dumps(self._payload).encode()

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class SequenceTransport:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class MLBStatsAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def record(self, name):
        return copy.deepcopy(self.fixture["cases"][name])

    def payload(self, *names, reverse=False):
        games = [self.record(name) for name in names]
        if reverse:
            games.reverse()
        return {"dates": [{"date": "2026-07-31", "games": games}]}

    def response(self, *names, reverse=False, collected_at=COLLECTED):
        endpoint, params = MLBStatsAPIClient.schedule_request(date(2026, 7, 31))
        payload = self.payload(*names, reverse=reverse)
        return MLBStatsAPIResponse(
            endpoint,
            params,
            collected_at,
            200,
            "https://statsapi.mlb.com/api/v1/schedule?sportId=1",
            payload,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        )

    def result(self, name, *, collected_at=COLLECTED):
        return MLBStatsAPIAdapter().parse_response(
            self.response(name, collected_at=collected_at)
        ).games[0]


class MLBStatsAPIClientTests(MLBStatsAPITestCase):
    def test_deterministic_schedule_request(self):
        endpoint, params = MLBStatsAPIClient.schedule_request(
            date(2026, 7, 31), game_pk=900001
        )
        self.assertEqual(endpoint, f"{BASE_URL}/schedule")
        self.assertEqual(params, tuple(sorted(params)))
        self.assertEqual(dict(params)["sportId"], "1")
        self.assertEqual(dict(params)["gamePk"], "900001")

    def test_mocked_transport_and_timeout(self):
        transport = SequenceTransport(MockResponse(payload={"dates": []}))
        client = MLBStatsAPIClient(
            transport=transport, timeout=7, retry_delays=(), clock=lambda: COLLECTED
        )
        response = client.fetch_schedule(date(2026, 7, 31))
        self.assertEqual(response.collected_at, COLLECTED)
        self.assertEqual(transport.calls[0][2], 7)

    def test_client_captures_raw_bytes_before_json_parsing(self):
        class MutatingResponse(MockResponse):
            def json(self):
                payload = super().json()
                self.content = b"changed-after-json-parse"
                return payload

        original = b'{ "dates": [] }'
        client = MLBStatsAPIClient(
            transport=SequenceTransport(MutatingResponse(content=original)),
            retry_delays=(),
        )
        response = client.fetch_schedule(date(2026, 7, 31), collected_at=COLLECTED)
        self.assertEqual(response.raw_body, original)

    def test_transient_timeout_and_http_failure_retry(self):
        transport = SequenceTransport(
            requests.Timeout(),
            MockResponse(503),
            MockResponse(payload={"dates": []}),
        )
        sleeper = Mock()
        client = MLBStatsAPIClient(
            transport=transport,
            retry_delays=(0, 0),
            sleeper=sleeper,
            clock=lambda: COLLECTED,
        )
        client.fetch_schedule(date(2026, 7, 31))
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_permanent_error_does_not_retry(self):
        transport = SequenceTransport(MockResponse(404))
        client = MLBStatsAPIClient(transport=transport, retry_delays=(0, 0))
        with self.assertRaises(MLBStatsAPIError) as context:
            client.fetch_schedule(date(2026, 7, 31), collected_at=COLLECTED)
        self.assertEqual(context.exception.code, "permanent_http_failure")
        self.assertEqual(len(transport.calls), 1)

    def test_malformed_json_and_shape_are_deterministic_errors(self):
        for response, code in (
            (MockResponse(json_error=ValueError("bad")), "malformed_json"),
            (MockResponse(payload=[]), "unsupported_response_shape"),
        ):
            with self.subTest(code=code):
                client = MLBStatsAPIClient(
                    transport=SequenceTransport(response), retry_delays=()
                )
                with self.assertRaises(MLBStatsAPIError) as context:
                    client.fetch_schedule(date(2026, 7, 31), collected_at=COLLECTED)
                self.assertEqual(context.exception.code, code)

    def test_adapter_construction_has_no_network_behavior(self):
        with patch("mlb_stats_api.requests.Session") as session:
            MLBStatsAPIAdapter()
        session.assert_not_called()


class MLBStatsAPIIdentityAndScheduleTests(MLBStatsAPITestCase):
    def test_valid_game_pk_and_team_identity_construct_event(self):
        item = self.result("ordinary")
        self.assertTrue(item.accepted)
        self.assertEqual(item.game.game_pk, 900001)
        self.assertEqual(item.game.event.canonical_event_id, "mlb:900001")
        self.assertEqual(
            {team.mlb_team_id for team in (item.game.away_team, item.game.home_team)},
            {113, 114},
        )
        self.assertEqual(item.raw_evidence.provider, PROVIDER_ID)

    def test_missing_malformed_and_conflicting_game_pk_fail_closed(self):
        malformed = self.record("ordinary")
        malformed["gamePk"] = "900001"
        cases = (
            self.record("missing_game_pk"),
            malformed,
            self.record("conflicting_game_pk"),
        )
        expected = (
            AdapterIssueCode.MISSING_GAME_PK,
            AdapterIssueCode.MALFORMED_GAME_PK,
            AdapterIssueCode.CONFLICTING_GAME_PK,
        )
        adapter = MLBStatsAPIAdapter()
        raw = adapter._raw_evidence(self.response("ordinary"))
        for record, code in zip(cases, expected):
            with self.subTest(code=code):
                result = adapter.parse_game(record, raw)
                self.assertFalse(result.accepted)
                self.assertEqual(result.issues[0].code, code)
                self.assertIsNotNone(result.raw_evidence)

    def test_missing_and_identical_team_identity_fail_closed(self):
        identical = self.record("ordinary")
        identical["teams"]["away"]["team"]["id"] = 114
        adapter = MLBStatsAPIAdapter()
        raw = adapter._raw_evidence(self.response("ordinary"))
        for record, code in (
            (self.record("missing_team_identity"), AdapterIssueCode.MISSING_TEAM_ID),
            (identical, AdapterIssueCode.IDENTICAL_TEAMS),
        ):
            with self.subTest(code=code):
                result = adapter.parse_game(record, raw)
                self.assertFalse(result.accepted)
                self.assertEqual(result.issues[0].code, code)

    def test_timezone_aware_schedule_and_malformed_timestamp(self):
        valid = self.result("timezone_edge")
        self.assertEqual(
            valid.schedule_observation.scheduled_start.utcoffset().total_seconds(),
            -5 * 3600,
        )
        invalid = self.result("malformed_timestamp")
        self.assertFalse(invalid.accepted)
        self.assertEqual(invalid.issues[0].code, AdapterIssueCode.MALFORMED_TIMESTAMP)

    def test_split_doubleheader_and_deterministic_identity(self):
        first = self.result("doubleheader_1")
        second = self.result("doubleheader_2")
        self.assertEqual((first.game.game_number, second.game.game_number), (1, 2))
        self.assertEqual(
            (first.game.doubleheader_designation, second.game.doubleheader_designation),
            ("S", "S"),
        )
        self.assertNotEqual(first.game.event, second.game.event)

    def test_missing_venue_is_partial_success(self):
        item = self.result("missing_both_pitchers")
        self.assertTrue(item.accepted)
        self.assertIsNone(item.schedule_observation.venue)
        self.assertIs(
            item.schedule_observation.provenance.validation_status,
            ValidationStatus.INCOMPLETE,
        )
        self.assertIn(AdapterIssueCode.MISSING_VENUE, {x.code for x in item.issues})

    def test_same_game_pk_schedule_revision_preserves_identity(self):
        before = self.result("postponed_before")
        after = self.result(
            "postponed_after",
            collected_at=datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(before.game.event, after.game.event)
        self.assertNotEqual(
            before.schedule_observation.scheduled_start,
            after.schedule_observation.scheduled_start,
        )
        self.assertIn("rescheduledFromDate=2026-08-02", after.schedule_observation.status_evidence)

    def test_explicit_distinct_game_lineage_and_self_lineage_rejection(self):
        first = self.result("doubleheader_1")
        second = self.result("doubleheader_2")
        adapter = MLBStatsAPIAdapter()
        lineage = adapter.explicit_lineage(
            from_game=first.game,
            to_game=second.game,
            relationship=LineageType.DOUBLEHEADER_COMPANION,
            raw=second.raw_evidence,
            source_record_id=second.source_record_id,
            source_relation_field="relatedGamePk",
            source_related_game_pk=first.game.game_pk,
            source_evidence=("source explicitly identified companion gamePk",),
        )
        self.assertNotEqual(lineage.from_event_id, lineage.to_event_id)
        with self.assertRaises(ContractError):
            adapter.explicit_lineage(
                from_game=first.game,
                to_game=first.game,
                relationship=LineageType.REPLACEMENT_GAME,
                raw=first.raw_evidence,
                source_record_id=first.source_record_id,
                source_relation_field="relatedGamePk",
                source_related_game_pk=first.game.game_pk,
                source_evidence=("invalid self relation",),
            )

    def test_similarity_without_explicit_linkage_creates_no_lineage(self):
        result = MLBStatsAPIAdapter().parse_response(
            self.response("doubleheader_1", "doubleheader_2")
        )
        self.assertTrue(all(not item.lineages for item in result.games))

    def test_contradictory_explicit_linkage_is_rejected(self):
        first = self.result("doubleheader_1")
        second = self.result("doubleheader_2")
        with self.assertRaises(ContractError):
            MLBStatsAPIAdapter().explicit_lineage(
                from_game=first.game,
                to_game=second.game,
                relationship=LineageType.DOUBLEHEADER_COMPANION,
                raw=second.raw_evidence,
                source_record_id=second.source_record_id,
                source_relation_field="relatedGamePk",
                source_related_game_pk=999999,
            )


class MLBStatsAPIStatusAndPitcherTests(MLBStatsAPITestCase):
    def test_supported_status_mapping(self):
        cases = {
            "Scheduled": GameStatus.SCHEDULED,
            "Delayed": GameStatus.DELAYED,
            "Postponed": GameStatus.POSTPONED,
            "Suspended": GameStatus.SUSPENDED,
            "Resumed": GameStatus.RESUMED,
            "In Progress": GameStatus.IN_PROGRESS,
            "Final": GameStatus.FINAL,
            "Cancelled": GameStatus.CANCELLED,
        }
        adapter = MLBStatsAPIAdapter()
        raw = adapter._raw_evidence(self.response("ordinary"))
        for label, expected in cases.items():
            with self.subTest(label=label):
                record = self.record("ordinary")
                record["status"]["detailedState"] = label
                result = adapter.parse_game(record, raw)
                self.assertIs(result.status_observation.status, expected)
                self.assertEqual(result.status_observation.source_reported_status, label)

    def test_unknown_status_is_preserved_and_incomplete(self):
        item = self.result("unknown_status")
        self.assertIs(item.outcome, AdapterOutcome.PARTIAL)
        self.assertIsNotNone(item.game)
        self.assertIs(
            item.schedule_observation.provenance.validation_status,
            ValidationStatus.VALID,
        )
        self.assertIs(item.status_observation.status, GameStatus.UNSUPPORTED)
        self.assertEqual(
            item.status_observation.source_reported_status, "Provider Mystery"
        )
        self.assertIs(
            item.status_observation.provenance.validation_status,
            ValidationStatus.INCOMPLETE,
        )

    def test_probable_pitchers_complete_partial_and_missing(self):
        complete = self.result("ordinary").pitcher_observation
        partial = self.result("missing_one_pitcher").pitcher_observation
        missing = self.result("missing_both_pitchers").pitcher_observation
        self.assertEqual(
            (complete.away_state, complete.home_state),
            (PitcherState.PROBABLE, PitcherState.PROBABLE),
        )
        self.assertEqual(
            (partial.away_state, partial.home_state),
            (PitcherState.MISSING, PitcherState.PROBABLE),
        )
        self.assertEqual(
            (missing.away_state, missing.home_state),
            (PitcherState.MISSING, PitcherState.MISSING),
        )
        self.assertIs(partial.provenance.validation_status, ValidationStatus.INCOMPLETE)
        self.assertIsNotNone(self.result("missing_one_pitcher").game)

    def test_pitcher_change_creates_new_observation(self):
        adapter = MLBStatsAPIAdapter()
        first_batch = adapter.parse_response(self.response("ordinary"))
        prior = first_batch.games[0].pitcher_observation
        changed_record = self.record("ordinary")
        changed_record["teams"]["home"]["probablePitcher"] = {
            "id": 5999,
            "fullName": "Changed Pitcher",
        }
        later = datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc)
        response = MLBStatsAPIResponse(
            first_batch.raw_evidence.endpoint,
            first_batch.raw_evidence.request_parameters,
            later,
            200,
            first_batch.raw_evidence.source_url,
            {"dates": [{"games": [changed_record]}]},
            json.dumps({"dates": [{"games": [changed_record]}]}).encode(),
        )
        current = adapter.parse_response(response, prior_pitchers={900001: prior}).games[0]
        self.assertIs(current.pitcher_observation.home_state, PitcherState.CHANGED)
        self.assertEqual(
            current.pitcher_observation.replaces_observation_id, prior.observation_id
        )
        self.assertNotEqual(current.pitcher_observation, prior)


class MLBStatsAPIResultTests(MLBStatsAPITestCase):
    def test_partial_success_and_stable_issue_order(self):
        item = self.result("missing_both_pitchers")
        self.assertIs(item.outcome, AdapterOutcome.PARTIAL)
        self.assertTrue(item.accepted)
        self.assertIsNotNone(item.schedule_observation)
        self.assertIsNotNone(item.status_observation)
        self.assertEqual(item.issues, tuple(sorted(item.issues)))
        self.assertEqual(
            {issue.severity for issue in item.issues},
            {AdapterIssueSeverity.WARNING, AdapterIssueSeverity.INCOMPLETE},
        )

    def test_failed_identity_preserves_raw_evidence(self):
        item = self.result("missing_game_pk")
        self.assertIs(item.outcome, AdapterOutcome.REJECTED)
        self.assertFalse(item.accepted)
        self.assertIsNone(item.schedule_observation)
        self.assertEqual(len(item.raw_evidence.raw_response_sha256), 64)

    def test_complete_event_outcome_is_explicit(self):
        item = self.result("ordinary")
        self.assertIs(item.outcome, AdapterOutcome.COMPLETE)

    def test_source_timestamp_is_explicit_or_unknown_never_collection_time(self):
        explicit = self.result("ordinary")
        self.assertEqual(
            explicit.status_observation.provenance.source_timestamp,
            datetime(2026, 7, 31, 14, 0, tzinfo=timezone.utc),
        )
        missing_record = self.record("ordinary")
        missing_record.pop("lastUpdated")
        adapter = MLBStatsAPIAdapter()
        missing = adapter.parse_game(missing_record, adapter._raw_evidence(self.response("ordinary")))
        self.assertIsNone(missing.schedule_observation.provenance.source_timestamp)
        self.assertNotEqual(
            missing.schedule_observation.provenance.source_timestamp,
            missing.raw_evidence.collected_at,
        )

    def test_raw_hash_round_trip_and_repeated_parse_are_stable(self):
        response = self.response("ordinary", "missing_one_pitcher")
        adapter = MLBStatsAPIAdapter()
        first = adapter.parse_response(response)
        second = adapter.parse_response(response)
        self.assertEqual(
            first.raw_evidence.raw_response_sha256,
            second.raw_evidence.raw_response_sha256,
        )
        self.assertEqual(
            first.raw_evidence.canonical_json_sha256,
            second.raw_evidence.canonical_json_sha256,
        )
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(MLBStatsAdapterResult.from_json(first.to_json()), first)

    def test_multiple_games_have_deterministic_order(self):
        adapter = MLBStatsAPIAdapter()
        forward = adapter.parse_response(
            self.response("ordinary", "missing_one_pitcher")
        )
        reversed_result = adapter.parse_response(
            self.response("ordinary", "missing_one_pitcher", reverse=True)
        )
        self.assertEqual(
            tuple(item.source_record_id for item in forward.games),
            tuple(item.source_record_id for item in reversed_result.games),
        )
        self.assertEqual(
            tuple(item.game for item in forward.games),
            tuple(item.game for item in reversed_result.games),
        )
        self.assertNotEqual(
            forward.raw_evidence.canonical_json_sha256,
            reversed_result.raw_evidence.canonical_json_sha256,
        )

    def test_unsupported_response_shape_is_structured(self):
        response = self.response("ordinary")
        response = MLBStatsAPIResponse(
            response.endpoint,
            response.parameters,
            response.collected_at,
            response.status_code,
            response.source_url,
            {"unexpected": []},
            b'{"unexpected":[]}',
        )
        result = MLBStatsAPIAdapter().parse_response(response)
        self.assertEqual(result.games, ())
        self.assertEqual(result.issues[0].component, AdapterComponent.SOURCE)
        self.assertEqual(result.issues[0].code, AdapterIssueCode.UNSUPPORTED_SOURCE_SHAPE)

    def test_raw_and_canonical_digests_have_distinct_semantics(self):
        payload = {"dates": [], "copyright": "synthetic"}
        endpoint, params = MLBStatsAPIClient.schedule_request(date(2026, 7, 31))
        compact = b'{"dates":[],"copyright":"synthetic"}'
        formatted = b'{\n  "copyright": "synthetic",\n  "dates": []\n}'
        responses = tuple(
            MLBStatsAPIResponse(endpoint, params, COLLECTED, 200, endpoint, payload, body)
            for body in (compact, formatted)
        )
        evidence = tuple(MLBStatsAPIAdapter()._raw_evidence(item) for item in responses)
        self.assertNotEqual(evidence[0].raw_response_sha256, evidence[1].raw_response_sha256)
        self.assertEqual(evidence[0].canonical_json_sha256, evidence[1].canonical_json_sha256)


class MLBStatsAPISmokeTests(MLBStatsAPITestCase):
    def test_smoke_is_concise_and_successful_for_safe_result(self):
        client = Mock()
        client.fetch_schedule.return_value = self.response("ordinary")
        with patch("builtins.print") as printer:
            self.assertEqual(run_smoke(["2026-07-31", "--game-pk", "900001"], client=client), 0)
        rendered = " ".join(str(call) for call in printer.call_args_list)
        self.assertIn("gamePk=900001", rendered)
        self.assertNotIn("raw_body", rendered)

    def test_smoke_returns_nonzero_for_rejection_or_transport_failure(self):
        rejected_client = Mock()
        rejected_client.fetch_schedule.return_value = self.response("missing_game_pk")
        with patch("builtins.print"):
            self.assertEqual(run_smoke(["2026-07-31"], client=rejected_client), 1)
        failed_client = Mock()
        failed_client.fetch_schedule.side_effect = MLBStatsAPIError("transport_failure", "Timeout")
        with patch("builtins.print"):
            self.assertEqual(run_smoke(["2026-07-31"], client=failed_client), 1)


if __name__ == "__main__":
    unittest.main()
