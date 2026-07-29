import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

from event_contracts import (
    CandidateEvaluation,
    CanonicalEvent,
    ContractError,
    Evidence,
    NativeIdentifier,
    ParticipantRef,
    Provenance,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
    SourceMapping,
    SportNativeIdentifier,
    ValidationReason,
    ValidationStatus,
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


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mlb_contract_cases.json"


def aware(value):
    return datetime.fromisoformat(value)


class EventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def team(self, key):
        item = self.fixture["teams"][key]
        return MLBTeamRef(
            canonical_team_id=item["canonical_team_id"],
            mlb_team_id=item["mlb_team_id"],
            display_name=item["display_name"],
            abbreviation=item["abbreviation"],
        )

    def game(self, key, away="cleveland", home="cincinnati"):
        item = self.fixture["games"][key]
        return make_mlb_game(
            game_pk=item["game_pk"],
            away_team=self.team(away),
            home_team=self.team(home),
            season=item["season"],
            game_type=item["game_type"],
            game_number=item.get("game_number"),
            doubleheader_designation=item.get("doubleheader_designation"),
        )

    def provenance(
        self,
        event,
        *,
        record_id="schedule:1",
        status=ValidationStatus.VALID,
        reasons=(),
    ):
        timestamps = self.fixture["timestamps"]
        return Provenance(
            provider="fixture-provider",
            source_record_id=record_id,
            canonical_event_id=event.event.canonical_event_id,
            source_timestamp=aware(timestamps["published"]),
            collected_at=aware(timestamps["collected"]),
            transformations=("source time converted to UTC",),
            validation_status=status,
            validation_reasons=reasons,
            raw_evidence_ref="sha256:fixture",
        )

    def test_canonical_event_excludes_mutable_mlb_facts(self):
        game = self.game("ordinary")
        self.assertEqual(game.game_pk, 823350)
        self.assertEqual(
            game.event.native_identifiers,
            (SportNativeIdentifier("mlb_game", "823350"),),
        )
        self.assertEqual(
            {item.canonical_id for item in game.event.participants},
            {"mlb-team:113", "mlb-team:114"},
        )
        event_fields = set(game.event.__dataclass_fields__)
        self.assertFalse(
            event_fields
            & {
                "game_pk",
                "scheduled_start",
                "status",
                "pitchers",
                "probability",
                "price",
                "outcome",
            }
        )

    def test_team_mapping_does_not_depend_on_display_text(self):
        team = self.team("new_york_mets")
        participant = team.as_participant()
        event_before_mapping = self.game(
            "ordinary", away="atlanta", home="new_york_mets"
        ).event
        mapping = SourceMapping(
            mapping_id="mapping:kalshi:new-york-m",
            canonical_entity_id=team.canonical_team_id,
            source_identifier=NativeIdentifier(
                "kalshi_team_name", self.fixture["teams"]["new_york_mets"]["provider_name"]
            ),
            collected_at=aware(self.fixture["timestamps"]["collected"]),
            evidence=(Evidence("provider_display_name", "New York M"),),
        )
        self.assertEqual(participant.canonical_id, "mlb-team:121")
        self.assertEqual(mapping.canonical_entity_id, participant.canonical_id)
        self.assertNotIn(mapping.source_identifier, participant.native_identifiers)
        self.assertEqual(SourceMapping.from_json(mapping.to_json()), mapping)
        self.assertEqual(
            event_before_mapping,
            self.game("ordinary", away="atlanta", home="new_york_mets").event,
        )
        self.assertNotEqual(team.display_name, "New York M")

    def test_canonical_identity_rejects_provider_identifiers(self):
        first = self.team("cleveland").as_participant()
        second = self.team("cincinnati").as_participant()
        with self.assertRaises(ContractError) as context:
            CanonicalEvent(
                sport="baseball",
                competition="MLB",
                season="2026",
                canonical_event_id="mlb:823350",
                participants=(first, second),
                native_identifiers=(NativeIdentifier("forecast_game", "abc"),),
            )
        self.assertEqual(
            context.exception.code, ReasonCode.CONFLICTING_SOURCE_MAPPING
        )

    def test_conflicting_game_pk_is_invalid(self):
        ordinary = self.game("ordinary")
        with self.assertRaises(ContractError) as context:
            MLBGame(
                event=ordinary.event,
                game_pk=999999,
                home_team=ordinary.home_team,
                away_team=ordinary.away_team,
                season=ordinary.season,
                game_type=ordinary.game_type,
            )
        self.assertEqual(context.exception.code, ReasonCode.CONFLICTING_GAME_PK)

    def test_mlb_identity_layers_must_agree(self):
        ordinary = self.game("ordinary")
        with self.assertRaises(ContractError) as season:
            MLBGame(
                event=ordinary.event,
                game_pk=ordinary.game_pk,
                home_team=ordinary.home_team,
                away_team=ordinary.away_team,
                season="2025",
                game_type=ordinary.game_type,
            )
        self.assertEqual(
            season.exception.code, ReasonCode.CONFLICTING_NATIVE_IDENTITY
        )

        with self.assertRaises(ContractError) as participants:
            MLBGame(
                event=ordinary.event,
                game_pk=ordinary.game_pk,
                home_team=self.team("new_york_mets"),
                away_team=ordinary.away_team,
                season=ordinary.season,
                game_type=ordinary.game_type,
            )
        self.assertEqual(
            participants.exception.code, ReasonCode.CONFLICTING_NATIVE_IDENTITY
        )

    def test_identity_rejects_identical_teams_and_missing_participants(self):
        team = self.team("cleveland")
        with self.assertRaises(ContractError) as identical:
            make_mlb_game(
                game_pk=1,
                home_team=team,
                away_team=team,
                season="2026",
            )
        self.assertEqual(
            identical.exception.code, ReasonCode.IDENTICAL_PARTICIPANTS
        )
        with self.assertRaises(ContractError) as missing:
            CanonicalEvent(
                sport="baseball",
                competition="MLB",
                season="2026",
                canonical_event_id="mlb:1",
                participants=(team.as_participant(),),
            )
        self.assertEqual(missing.exception.code, ReasonCode.MISSING_PARTICIPANT)

    def test_split_doubleheader_games_have_distinct_identity(self):
        first = self.game("doubleheader_game_1")
        second = self.game("doubleheader_game_2")
        self.assertNotEqual(first.game_pk, second.game_pk)
        self.assertNotEqual(
            first.event.canonical_event_id, second.event.canonical_event_id
        )
        self.assertEqual((first.game_number, second.game_number), (1, 2))
        with self.assertRaises(ContractError) as ambiguity:
            make_mlb_game(
                game_pk=123,
                away_team=self.team("cleveland"),
                home_team=self.team("cincinnati"),
                season="2026",
                doubleheader_designation="split",
            )
        self.assertEqual(
            ambiguity.exception.code, ReasonCode.DOUBLEHEADER_AMBIGUITY
        )

    def test_postponed_same_game_pk_remains_same_event(self):
        game = self.game(
            "postponed_same_identity", away="atlanta", home="new_york_mets"
        )
        before = ScheduleObservation(
            observation_id="schedule:before",
            canonical_event_id=game.event.canonical_event_id,
            scheduled_start=aware("2026-07-28T23:10:00+00:00"),
            provenance=self.provenance(game, record_id="schedule:before"),
        )
        after = ScheduleObservation(
            observation_id="schedule:after",
            canonical_event_id=game.event.canonical_event_id,
            scheduled_start=aware("2026-07-29T23:10:00+00:00"),
            provenance=self.provenance(game, record_id="schedule:after"),
            status_evidence=("postponed for weather",),
        )
        self.assertEqual(before.canonical_event_id, after.canonical_event_id)
        self.assertNotEqual(before, after)
        self.assertEqual(game.game_pk, 823598)

    def test_replacement_game_has_new_identity_and_explicit_lineage(self):
        original = self.game(
            "postponed_same_identity", away="atlanta", home="new_york_mets"
        )
        replacement = self.game(
            "replacement_identity", away="atlanta", home="new_york_mets"
        )
        lineage = ScheduleLineage(
            relationship_id="lineage:replacement",
            from_event_id=original.event.canonical_event_id,
            to_event_id=replacement.event.canonical_event_id,
            relationship=LineageType.REPLACEMENT_GAME,
            provenance=self.provenance(
                replacement, record_id="lineage:replacement"
            ),
            evidence=("provider explicitly linked replacement game",),
        )
        self.assertNotEqual(original.game_pk, replacement.game_pk)
        self.assertEqual(lineage.to_event_id, replacement.event.canonical_event_id)

    def test_contradictory_lineage_is_rejected(self):
        game = self.game("ordinary")
        with self.assertRaises(ContractError) as context:
            ScheduleLineage(
                relationship_id="lineage:self",
                from_event_id=game.event.canonical_event_id,
                to_event_id=game.event.canonical_event_id,
                relationship=LineageType.POSTPONED_FROM,
                provenance=self.provenance(game),
                evidence=("same event",),
            )
        self.assertEqual(
            context.exception.code, ReasonCode.CONTRADICTORY_LINEAGE
        )

    def test_suspended_and_resumed_are_separate_status_observations(self):
        game = self.game("ordinary")
        suspended = GameStatusObservation(
            observation_id="status:suspended",
            canonical_event_id=game.event.canonical_event_id,
            status=GameStatus.SUSPENDED,
            source_reported_status="Suspended",
            provenance=self.provenance(game, record_id="status:suspended"),
        )
        resumed = GameStatusObservation(
            observation_id="status:resumed",
            canonical_event_id=game.event.canonical_event_id,
            status=GameStatus.RESUMED,
            source_reported_status="Resumed",
            provenance=self.provenance(game, record_id="status:resumed"),
        )
        self.assertEqual(suspended.canonical_event_id, resumed.canonical_event_id)
        self.assertNotEqual(suspended.status, resumed.status)
        with self.assertRaises(ContractError) as self_lineage:
            ScheduleLineage(
                relationship_id="lineage:suspension:self",
                from_event_id=game.event.canonical_event_id,
                to_event_id=game.event.canonical_event_id,
                relationship=LineageType.RESUMED_FROM_SUSPENSION,
                provenance=self.provenance(game),
                evidence=("source retained the same gamePk",),
            )
        self.assertEqual(
            self_lineage.exception.code, ReasonCode.CONTRADICTORY_LINEAGE
        )

    def test_explicit_suspension_lineage_can_link_distinct_game_pk_values(self):
        original = self.game(
            "postponed_same_identity", away="atlanta", home="new_york_mets"
        )
        resumed_as_new_event = self.game(
            "replacement_identity", away="atlanta", home="new_york_mets"
        )
        lineage = ScheduleLineage(
            relationship_id="lineage:suspension:new-identity",
            from_event_id=original.event.canonical_event_id,
            to_event_id=resumed_as_new_event.event.canonical_event_id,
            relationship=LineageType.RESUMED_FROM_SUSPENSION,
            provenance=self.provenance(
                resumed_as_new_event, record_id="lineage:suspension:new-identity"
            ),
            evidence=("source explicitly linked the distinct MLB game records",),
        )
        self.assertNotEqual(original.game_pk, resumed_as_new_event.game_pk)
        self.assertEqual(
            lineage.to_event_id, resumed_as_new_event.event.canonical_event_id
        )

    def test_missing_pitcher_is_valid_incomplete_observation(self):
        game = self.game("ordinary")
        missing_reason = ValidationReason(
            ReasonCode.MISSING_PITCHER, "home probable pitcher unavailable"
        )
        observation = PitcherObservation(
            observation_id="pitchers:missing",
            canonical_event_id=game.event.canonical_event_id,
            home_pitcher=None,
            away_pitcher=PitcherRef(
                provider="mlb",
                source_pitcher_id="677944",
                display_name="Slade Cecconi",
            ),
            home_state=PitcherState.MISSING,
            away_state=PitcherState.PROBABLE,
            provenance=self.provenance(
                game,
                record_id="pitchers:missing",
                status=ValidationStatus.INCOMPLETE,
                reasons=(missing_reason,),
            ),
        )
        self.assertEqual(
            observation.provenance.validation_status, ValidationStatus.INCOMPLETE
        )
        self.assertEqual(game.game_pk, 823350)

    def test_pitcher_change_preserves_prior_observation(self):
        game = self.game("ordinary")
        initial = PitcherObservation(
            observation_id="pitchers:initial",
            canonical_event_id=game.event.canonical_event_id,
            home_pitcher=PitcherRef("mlb", "1", "Initial Home"),
            away_pitcher=PitcherRef("mlb", "2", "Away"),
            home_state=PitcherState.PROBABLE,
            away_state=PitcherState.PROBABLE,
            provenance=self.provenance(game, record_id="pitchers:initial"),
        )
        changed = PitcherObservation(
            observation_id="pitchers:changed",
            canonical_event_id=game.event.canonical_event_id,
            home_pitcher=PitcherRef("mlb", "3", "Replacement Home"),
            away_pitcher=initial.away_pitcher,
            home_state=PitcherState.CHANGED,
            away_state=PitcherState.PROBABLE,
            provenance=self.provenance(game, record_id="pitchers:changed"),
            replaces_observation_id=initial.observation_id,
        )
        self.assertEqual(initial.home_pitcher.source_pitcher_id, "1")
        self.assertEqual(changed.replaces_observation_id, initial.observation_id)
        with self.assertRaises(FrozenInstanceError):
            initial.home_pitcher = changed.home_pitcher

    def test_conflicting_schedule_observations_remain_distinct(self):
        game = self.game("doubleheader_game_1")
        first = ScheduleObservation(
            observation_id="schedule:mlb",
            canonical_event_id=game.event.canonical_event_id,
            scheduled_start=aware(
                self.fixture["timestamps"]["doubleheader_game_1"]
            ),
            provenance=self.provenance(game, record_id="schedule:mlb"),
        )
        conflict = ScheduleObservation(
            observation_id="schedule:provider",
            canonical_event_id=game.event.canonical_event_id,
            scheduled_start=aware(
                self.fixture["timestamps"]["conflicting_game_1"]
            ),
            provenance=Provenance(
                provider="other-provider",
                source_record_id="schedule:provider",
                canonical_event_id=game.event.canonical_event_id,
                source_timestamp=aware(
                    self.fixture["timestamps"]["published"]
                ),
                collected_at=aware(self.fixture["timestamps"]["collected"]),
            ),
        )
        self.assertNotEqual(first.scheduled_start, conflict.scheduled_start)
        reason = ValidationReason(
            ReasonCode.CONFLICTING_SCHEDULE, "sources differ by one hour"
        )
        rejected = ReconciliationResult.rejected(
            NativeIdentifier("other-provider", "schedule:provider"),
            evidence=(
                Evidence("mlb_time", first.scheduled_start.isoformat()),
                Evidence("provider_time", conflict.scheduled_start.isoformat()),
            ),
            reasons=(reason,),
        )
        self.assertEqual(rejected.outcome, ReconciliationOutcome.REJECTED)

    def test_naive_and_impossible_timestamps_are_invalid(self):
        game = self.game("ordinary")
        with self.assertRaises(ContractError) as naive:
            ScheduleObservation(
                observation_id="schedule:naive",
                canonical_event_id=game.event.canonical_event_id,
                scheduled_start=datetime(2026, 7, 28, 12, 0),
                provenance=self.provenance(game),
            )
        self.assertEqual(naive.exception.code, ReasonCode.NAIVE_TIMESTAMP)
        with self.assertRaises(ContractError) as chronology:
            Provenance(
                provider="fixture",
                source_record_id="future-publication",
                canonical_event_id=game.event.canonical_event_id,
                source_timestamp=aware("2026-07-28T13:00:00+00:00"),
                collected_at=aware("2026-07-28T12:00:00+00:00"),
            )
        self.assertEqual(
            chronology.exception.code, ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY
        )

    def test_conflicting_provider_mappings_are_invalid(self):
        with self.assertRaises(ContractError) as context:
            ParticipantRef(
                canonical_id="team:1",
                display_name="Team",
                native_identifiers=(
                    NativeIdentifier("provider", "one"),
                    NativeIdentifier("provider", "two"),
                ),
            )
        self.assertEqual(
            context.exception.code, ReasonCode.CONFLICTING_SOURCE_MAPPING
        )

    def test_malformed_source_identifier_is_invalid(self):
        with self.assertRaises(ContractError) as context:
            NativeIdentifier("provider_game", " record-1 ")
        self.assertEqual(context.exception.code, ReasonCode.MALFORMED_IDENTIFIER)

    def test_matched_ambiguous_and_rejected_reconciliation(self):
        first = self.game("doubleheader_game_1").event
        second = self.game("doubleheader_game_2").event
        source = NativeIdentifier("provider_game", "record-1")
        evidence = (Evidence("game_pk", "824490"),)

        matched = ReconciliationResult.matched(
            source,
            first,
            evidence=evidence,
            source_mapping=NativeIdentifier("mlb_game", "824490"),
        )
        ambiguous = ReconciliationResult.ambiguous(
            source,
            (first, second),
            evidence=(Evidence("participants", "CLE at CIN"),),
            reasons=(
                ValidationReason(
                    ReasonCode.DOUBLEHEADER_AMBIGUITY,
                    "source omitted game number and gamePk",
                ),
            ),
        )
        rejected = ReconciliationResult.rejected(
            source,
            evidence=(Evidence("game_pk", "conflicting values"),),
            reasons=(
                ValidationReason(
                    ReasonCode.CONFLICTING_GAME_PK,
                    "source supplied two gamePk values",
                ),
            ),
            candidate_evaluations=(
                CandidateEvaluation(
                    canonical_event_id=first.canonical_event_id,
                    mappings_evaluated=(NativeIdentifier("mlb_game", "824490"),),
                    evidence=(Evidence("participants", "CLE at CIN"),),
                    reasons=(
                        ValidationReason(
                            ReasonCode.CONFLICTING_GAME_PK,
                            "candidate gamePk conflicts with the source record",
                        ),
                    ),
                ),
                CandidateEvaluation(
                    canonical_event_id=second.canonical_event_id,
                    mappings_evaluated=(NativeIdentifier("mlb_game", "824489"),),
                    evidence=(Evidence("participants", "CLE at CIN"),),
                    reasons=(
                        ValidationReason(
                            ReasonCode.DOUBLEHEADER_AMBIGUITY,
                            "source record omitted doubleheader position",
                        ),
                    ),
                ),
            ),
        )

        self.assertEqual(matched.outcome, ReconciliationOutcome.MATCHED)
        self.assertIsNone(ambiguous.matched_event)
        self.assertEqual(len(ambiguous.candidate_events), 2)
        self.assertEqual(rejected.outcome, ReconciliationOutcome.REJECTED)
        self.assertIsNone(rejected.matched_event)
        self.assertFalse(rejected.candidate_events)
        self.assertEqual(len(rejected.candidate_evaluations), 2)
        self.assertEqual(
            ReconciliationResult.from_json(rejected.to_json()), rejected
        )
        with self.assertRaises(ContractError):
            ReconciliationResult(
                outcome=ReconciliationOutcome.AMBIGUOUS,
                source_record=source,
                candidate_events=(first,),
                reasons=ambiguous.reasons,
            )

    def test_deterministic_serialization_round_trips(self):
        game = self.game("doubleheader_game_1")
        payload = game.to_json()
        self.assertEqual(payload, game.to_json())
        self.assertEqual(MLBGame.from_json(payload), game)

        observation = ScheduleObservation(
            observation_id="schedule:roundtrip",
            canonical_event_id=game.event.canonical_event_id,
            scheduled_start=aware(
                self.fixture["timestamps"]["doubleheader_game_1"]
            ),
            provenance=self.provenance(game, record_id="schedule:roundtrip"),
            game_number=1,
            doubleheader_designation="split",
        )
        observation_payload = observation.to_json()
        self.assertEqual(
            ScheduleObservation.from_json(observation_payload), observation
        )
        self.assertIn("+00:00", observation_payload)

        replacement = self.game(
            "replacement_identity", away="atlanta", home="new_york_mets"
        )
        lineage = ScheduleLineage(
            relationship_id="lineage:roundtrip",
            from_event_id=game.event.canonical_event_id,
            to_event_id=replacement.event.canonical_event_id,
            relationship=LineageType.REPLACEMENT_GAME,
            provenance=self.provenance(
                replacement, record_id="lineage:roundtrip"
            ),
            evidence=("explicit replacement record",),
        )
        self.assertEqual(ScheduleLineage.from_json(lineage.to_json()), lineage)

        source = NativeIdentifier("provider_game", "record-1")
        rejected = ReconciliationResult.rejected(
            source,
            evidence=(Evidence("game_pk", "conflicting values"),),
            reasons=(
                ValidationReason(
                    ReasonCode.CONFLICTING_GAME_PK,
                    "source supplied contradictory gamePk values",
                ),
            ),
        )
        self.assertEqual(
            ReconciliationResult.from_json(rejected.to_json()), rejected
        )

    def test_new_game_pk_wins_over_similar_schedule_evidence(self):
        original = self.game(
            "postponed_same_identity", away="atlanta", home="new_york_mets"
        )
        replacement = self.game(
            "replacement_identity", away="atlanta", home="new_york_mets"
        )
        self.assertEqual(
            {p.canonical_id for p in original.event.participants},
            {p.canonical_id for p in replacement.event.participants},
        )
        self.assertNotEqual(
            original.event.canonical_event_id,
            replacement.event.canonical_event_id,
        )


if __name__ == "__main__":
    unittest.main()
