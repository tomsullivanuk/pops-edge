"""Frozen reporting reads old and sequential outcome envelopes without migration."""
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_source as reporting
from tests import test_forecast_standalone_activation as activation_tests
from forecast_standalone_activation import (
    canonical_prospective_authority, initialize_activation, refresh_supporting_from_raw,
    reconcile_outcomes_from_raw, merge_mlb_schedule_responses,
    OUTCOME_RECONCILIATION_RULE_VERSION,
)
from forecast_standalone_operations import (
    DeploymentConfig, NamespaceArchive, OperatingMode, RetryPolicy,
    APPROVED_ACTIVATION_AT, OperationsError, replay_pr17_archive,
)


class ReportingOutcomeCompatibilityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        _, protocol = canonical_prospective_authority()
        self.archive = NamespaceArchive(DeploymentConfig('compatibility', 'compatibility',
            OperatingMode.ACTIVATED, root/'activated/compatibility/primary',
            root/'activated/compatibility/secondary', 'https://fixture.invalid',
            RetryPolicy(1, 1, 1, (), 0), 1, root/'logs',
            research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),
            activation_at=APPROVED_ACTIVATION_AT))
        fixture = activation_tests.ActivationTests()
        self.first = datetime(2026, 9, 24, tzinfo=timezone.utc)
        self.second = self.first + timedelta(days=1)
        self.third = self.second + timedelta(days=1)
        old, new = '2026-09-22', '2026-09-23'
        postponed = fixture._reschedule_game(824785, old, old+'T23:05:00Z', 'Postponed',
            rescheduleDate=new, rescheduleGameDate=new+'T23:05:00Z')
        final = fixture._reschedule_game(824785, new, new+'T23:05:00Z', 'Final',
            rescheduledFromDate=old, rescheduledFrom=old+'T23:05:00Z')
        corrected = copy.deepcopy(final)
        corrected['teams']['away'].update(score=4, isWinner=True)
        corrected['teams']['home'].update(score=3, isWinner=False)
        self.pages = (fixture._schedule_page(old, postponed), fixture._schedule_page(new, final))
        self.union = merge_mlb_schedule_responses(self.pages)
        self.corrected = fixture._schedule_page(new, corrected)
        initialize_activation(self.archive, datetime(2026, 8, 28, tzinfo=timezone.utc))
        refresh_supporting_from_raw(archive=self.archive, mlb_raw=self.union,
            kalshi_raw=b'{"cursor":"","markets":[]}', mlb_pages=self.pages, collected_at=self.first)

    def inventory(self):
        return {str(p.relative_to(self.archive.root)): p.read_bytes()
                for p in self.archive.root.rglob('*') if p.is_file()}

    def freeze_and_verify(self, at):
        before = self.inventory()
        boundary = reporting.freeze_reporting_source(archive=self.archive, clock=lambda: at)
        state, receipt = reporting.verify_reporting_source(archive=self.archive, boundary=boundary,
            expected_boundary_id=boundary.boundary_id, clock=lambda: at)
        self.assertEqual(state.graph, replay_pr17_archive(self.archive, analysis_boundary=at).graph)
        self.assertEqual(receipt.graph_digest, boundary.graph_digest)
        self.assertEqual(before, self.inventory())
        return boundary, state

    def test_legacy_then_sequential_correction_and_saved_boundary(self):
        # Create an authentic unversioned envelope shape before immutable commit.
        # No retained evidence is edited, and all scientific validators run.
        commit = self.archive._commit_locked
        def legacy_commit(**kwargs):
            value = kwargs.get('normalized', {})
            if value.get('family') == 'reconcile-outcomes':
                kwargs['normalized'] = {k: v for k, v in value.items() if k != 'derivation_rule'}
            return commit(**kwargs)
        with patch.object(self.archive, '_commit_locked', side_effect=legacy_commit):
            reconcile_outcomes_from_raw(archive=self.archive, mlb_raw=self.corrected,
                mlb_pages=(self.corrected,), collected_at=self.second, derivation_rule=None)
        old, old_state = self.freeze_and_verify(self.second)
        self.assertEqual(len(old_state.bucket('outcome_histories')[0].observations), 3)
        reconcile_outcomes_from_raw(archive=self.archive, mlb_raw=self.union,
            mlb_pages=self.pages, collected_at=self.third)
        fresh, fresh_state = self.freeze_and_verify(self.third)
        self.assertNotEqual(fresh.graph_digest, old.graph_digest)
        self.assertEqual(len(fresh_state.bucket('outcome_histories')[0].observations), 4)
        self.assertEqual(fresh_state.bucket('outcome_histories')[0].latest.home_score, 3)
        restored, _ = reporting.verify_reporting_source(archive=self.archive, boundary=old,
            expected_boundary_id=old.boundary_id, clock=lambda: self.third)
        self.assertEqual(restored.graph, old_state.graph)
        envelopes = [self.archive.read_json_verified('normalized', e['normalized_object_id'])
                     for e in self.archive.entries() if e['command'] == 'reconcile-outcomes']
        self.assertNotIn('derivation_rule', envelopes[0])
        self.assertEqual(envelopes[1]['derivation_rule'], OUTCOME_RECONCILIATION_RULE_VERSION)

    def test_unknown_outcome_rule_fails_closed_in_reporting(self):
        commit = self.archive._commit_locked
        def incompatible_commit(**kwargs):
            value = kwargs.get('normalized', {})
            if value.get('family') == 'reconcile-outcomes':
                kwargs['normalized'] = {**value, 'derivation_rule': 'unknown-future-rule'}
            return commit(**kwargs)
        with patch.object(self.archive, '_commit_locked', side_effect=incompatible_commit):
            reconcile_outcomes_from_raw(archive=self.archive, mlb_raw=self.corrected,
                mlb_pages=(self.corrected,), collected_at=self.second)
        with self.assertRaisesRegex(OperationsError, 'acquisition-incompatible'):
            reporting.freeze_reporting_source(archive=self.archive, clock=lambda: self.second)

    def test_metadata_reads_share_verified_cache_and_detect_changes(self):
        inventory = reporting._inventory(self.archive)
        view = reporting._ReportingArchiveView(self.archive, inventory)
        identity = next(e['normalized_object_id'] for e in view.entries() if e['normalized_object_id'])
        value = view.read_normalized_metadata(identity)
        self.assertIs(value, view.read_json_verified('normalized', identity))
        view.verify_unchanged()
        value['unexpected-review-mutation'] = True
        with self.assertRaisesRegex(OperationsError, 'decoded source changed'):
            view.verify_unchanged()
        view = reporting._ReportingArchiveView(self.archive, inventory)
        view.read_normalized_metadata(identity)
        # Corrupt only this disposable fixture's consumed bytes.
        path = self.archive._path('normalized', identity)
        path.chmod(0o600)
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(OperationsError, 'archive-corrupt'):
            view.verify_unchanged()
