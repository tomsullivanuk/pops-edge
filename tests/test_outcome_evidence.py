import copy
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from event_contracts import ContractError, ValidationStatus
from mlb_outcome_adapter import MLBOutcomeAdapter
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


FIXTURE = Path(__file__).parent / "fixtures" / "mlb_outcome_cases.json"
COLLECTED = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)


class OutcomeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

    def response(self, name, *, collected_at=COLLECTED, mutation=None):
        record = copy.deepcopy(self.cases[name])
        if mutation:
            mutation(record)
        payload = {"dates": [{"date": "2026-08-03", "games": [record]}]}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return MLBStatsAPIResponse("https://statsapi.mlb.com/api/v1/schedule", (("sportId", "1"),), collected_at, 200, "https://statsapi.mlb.com/api/v1/schedule?sportId=1", payload, raw)

    def observation(self, name, **kwargs):
        result = MLBOutcomeAdapter().parse_response(self.response(name, **kwargs))[0]
        self.assertIsNotNone(result.observation, result.issues)
        return result.observation

    def test_immutable_deterministic_identity_and_serialization(self):
        one = self.observation("normal_final")
        two = self.observation("normal_final")
        self.assertEqual(one, two)
        self.assertEqual(OutcomeObservation.from_json(one.to_json()), one)
        self.assertEqual(len(one.raw_evidence_sha256), 64)
        self.assertEqual(len(one.canonical_evidence_sha256), 64)
        self.assertNotEqual(one.raw_evidence_sha256, one.canonical_evidence_sha256)
        with self.assertRaises(FrozenInstanceError):
            one.away_score = 99

    def test_lifecycle_states_and_authoritative_finals(self):
        expected = {
            "scheduled": OutcomeStatus.SCHEDULED,
            "in_progress": OutcomeStatus.IN_PROGRESS,
            "postponed": OutcomeStatus.POSTPONED,
            "suspended": OutcomeStatus.SUSPENDED,
            "cancelled": OutcomeStatus.CANCELLED,
        }
        for name, status in expected.items():
            with self.subTest(name=name):
                item = self.observation(name)
                self.assertIs(item.provider_status, status)
                self.assertFalse(item.authoritative_final)
                self.assertIsNone(item.winning_participant_id)
        for name, innings in (("normal_final", 9), ("extra_inning_final", 11), ("shortened_final", 7), ("suspended_final", 9)):
            with self.subTest(name=name):
                item = self.observation(name)
                self.assertTrue(item.authoritative_final)
                self.assertEqual(item.completed_periods, innings)
                self.assertIsNotNone(item.winning_participant_id)

    def test_delayed_and_no_contest_provider_states_are_preserved(self):
        delayed = self.observation("scheduled", mutation=lambda row: row["status"].update(detailedState="Delayed"))
        no_contest = self.observation("cancelled", mutation=lambda row: row["status"].update(detailedState="No Contest"))
        self.assertIs(delayed.provider_status, OutcomeStatus.DELAYED)
        self.assertIs(no_contest.provider_status, OutcomeStatus.NO_CONTEST)
        self.assertFalse(delayed.authoritative_final)
        self.assertFalse(no_contest.authoritative_final)

    def test_corrected_final_is_later_immutable_observation(self):
        original = self.observation("normal_final", collected_at=datetime(2026, 8, 2, tzinfo=timezone.utc))
        corrected = self.observation("corrected_final", collected_at=COLLECTED)
        history = OutcomeHistory(original.canonical_event_id, original.authoritative_provider_id, (corrected, original))
        self.assertEqual(history.latest, corrected)
        self.assertEqual(history.latest_authoritative_final, corrected)
        self.assertEqual(original.away_score, 3)
        self.assertEqual(corrected.away_score, 4)

    def test_history_append_only_order_duplicate_and_compatibility(self):
        suspended = self.observation("suspended", collected_at=datetime(2026, 8, 3, 12, tzinfo=timezone.utc))
        final = self.observation("suspended_final")
        history = OutcomeHistory(suspended.canonical_event_id, suspended.authoritative_provider_id, (final, suspended))
        self.assertEqual(history.observations, (suspended, final))
        self.assertEqual(history.latest_authoritative_final, final)
        with self.assertRaises(ContractError):
            history.append(final)
        with self.assertRaises(ContractError):
            OutcomeHistory(suspended.canonical_event_id, suspended.authoritative_provider_id, (suspended, suspended))
        other = self.observation("normal_final")
        with self.assertRaises(ContractError):
            OutcomeHistory(suspended.canonical_event_id, suspended.authoritative_provider_id, (suspended, other))

    def test_doubleheaders_remain_distinct_by_game_pk(self):
        first = self.observation("doubleheader_one")
        second = self.observation("doubleheader_two")
        self.assertNotEqual(first.provider_event_id, second.provider_event_id)
        self.assertNotEqual(first.canonical_event_id, second.canonical_event_id)

    def test_malformed_score_and_winner_contradiction_fail_closed(self):
        malformed = self.observation("malformed_score")
        contradiction = self.observation("winner_contradiction")
        tied = self.observation("normal_final", mutation=lambda row: row["teams"]["away"].update(score=5))
        self.assertIs(malformed.validation_status, ValidationStatus.REJECTED)
        self.assertIn("away-score-malformed", {issue.code for issue in malformed.issues})
        self.assertIs(contradiction.validation_status, ValidationStatus.REJECTED)
        self.assertIsNone(contradiction.winning_participant_id)
        self.assertIs(tied.validation_status, ValidationStatus.REJECTED)
        self.assertTrue(tied.tie)

    def test_game_pk_and_participant_mismatch_fail_closed(self):
        response = self.response("normal_final")
        game = MLBStatsAPIAdapter().parse_response(response).games[0].game
        mismatched = self.response("normal_final", mutation=lambda row: row["teams"]["away"]["team"].update(id=999))
        result = MLBOutcomeAdapter().parse_response(mismatched, canonical_games=(game,))[0]
        self.assertIsNone(result.observation)
        self.assertIn(result.issues[0].code, {"participant-mismatch", "canonical-event-rejected"})
        direct = MLBOutcomeAdapter().parse_game({**self.cases["normal_final"], "gamePk": 999999}, response, game, datetime.fromisoformat("2026-08-01T18:00:00+00:00"))
        self.assertIsNone(direct.observation)
        self.assertEqual(direct.issues[0].code, "game-pk-mismatch")

    def test_unknown_provider_timestamp_stays_unknown(self):
        self.assertIsNone(self.observation("scheduled").provider_result_at)
        self.assertIsNone(self.observation("normal_final").provider_result_at)

    def test_import_and_adapter_construction_have_no_network_io(self):
        with patch("mlb_stats_api.requests.Session") as session:
            MLBOutcomeAdapter()
        session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
