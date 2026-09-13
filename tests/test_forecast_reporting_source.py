"""Reporting freezes use disposable synthetic namespaces only."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import localcontext
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_source as source
import tests.test_forecast_standalone_publication as publication_tests
from forecast_standalone_operations import OperationsError, archive_pr17_authority
from forecast_standalone_research import deserialize_v3


def rehash(boundary, **updates):
    material = boundary.material()
    material.update(updates)
    return source.FrozenReportingSource(**material,
        boundary_id='reporting-source:' + source._hash(material))


class ReportingSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = publication_tests.PinnedSupportingAuthorityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.archive = self.fixture.archive
        self.at = self.fixture.boundary

    def freeze(self, **overrides):
        args = dict(archive=self.archive, clock=lambda: self.at)
        args.update(overrides)
        return source.freeze_reporting_source(**args)

    def verify(self, boundary, **overrides):
        args = dict(archive=self.archive, boundary=boundary,
                    expected_boundary_id=getattr(boundary, 'boundary_id', ''),
                    clock=lambda: self.at + timedelta(days=1))
        args.update(overrides)
        return source.verify_reporting_source(**args)

    def inventory(self):
        return {str(p.relative_to(self.archive.root)): p.read_bytes()
                for p in self.archive.root.rglob('*') if p.is_file()}

    def test_late_completion_preserves_exact_saved_source_and_receipt(self):
        original = self.freeze()
        state, receipt = self.verify(original)
        self.assertTrue(original.session_dispositions[0][1].startswith('excluded:'))
        self.fixture.complete()
        replay, later_receipt = self.verify(original, clock=lambda: self.at + timedelta(days=2))
        self.assertEqual(replay, state)
        self.assertNotEqual(receipt.verified_at, later_receipt.verified_at)
        fresh = self.freeze(clock=lambda: self.at + timedelta(days=2))
        self.assertNotEqual(fresh.boundary_id, original.boundary_id)
        self.assertNotEqual(fresh.graph_digest, original.graph_digest)
        self.assertEqual(fresh.session_dispositions[0][1], 'verified-complete')
        self.assertEqual(source.FrozenReportingSource.from_json(original.to_json()), original)

    def test_failed_session_and_source_root_omissions_cannot_be_rehashed(self):
        original = self.freeze()
        # Complete inventory, including pages with no scientific authority, is pinned.
        entries = [json.loads(value) for value in original.manifest_inventory]
        for victim in (original.source_manifest_ids[0],
                       next(x['manifest_entry_id'] for x in entries
                            if x['command'] == 'refresh-retrospective-supporting-page')):
            reduced = tuple(value for value in original.manifest_inventory
                            if json.loads(value)['manifest_entry_id'] != victim)
            forged = rehash(original, manifest_inventory=reduced)
            with self.assertRaisesRegex(OperationsError, 'retained source boundary'):
                self.verify(forged, expected_boundary_id=original.boundary_id)

    def test_legacy_completion_and_later_correction_keep_original_admission(self):
        import forecast_standalone_activation as activation
        from tests.test_forecast_supporting_replay import supporting_fixture
        complete = activation.complete_supporting_session_from_archive
        def defer_correction(**kwargs):
            return {} if kwargs.get('correction_reason') else complete(**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(activation, 'complete_supporting_session_from_archive',
                              side_effect=defer_correction):
                archive, at = supporting_fixture(Path(directory), sessions=1, markets=0)
            old = self.freeze(archive=archive, clock=lambda: at)
            self.assertIn('correction-required', old.session_dispositions[0][1])
            before, _ = self.verify(old, archive=archive)
            complete(archive=archive, session_id='supporting-session:shape-0',
                     correction_reason=activation.APPROVED_SUPPORTING_CORRECTION_REASON)
            after, _ = self.verify(old, archive=archive)
            self.assertEqual(before, after)
            fresh = self.freeze(archive=archive, clock=lambda: at+timedelta(minutes=1))
            self.assertEqual(fresh.session_dispositions[0][1], 'verified-complete')
            self.assertNotEqual(old.graph_digest, fresh.graph_digest)

    def test_selection_and_dependency_tampering_fails_semantic_reconstruction(self):
        self.fixture.complete()
        original = self.freeze()
        for field in ('source_manifest_ids', 'dependency_manifest_ids', 'manifest_roles',
                      'session_dispositions'):
            forged = rehash(original, **{field: getattr(original, field)[1:]})
            # Even if an application incorrectly trusts the new ID, reconstruction
            # detects internal selection/closure inconsistency against inventory.
            with self.assertRaisesRegex(OperationsError, 'fails reconstruction'):
                self.verify(forged)
        forged = rehash(original, source_manifest_ids=('operations-manifest:invented',))
        with self.assertRaises(OperationsError):
            self.verify(forged)

    def test_foreign_namespace_mode_version_and_type_rejected(self):
        original = self.freeze()
        for field, value in [('namespace', 'foreign'), ('mode', 'activated')]:
            with self.assertRaisesRegex(OperationsError, 'foreign'):
                self.verify(rehash(original, **{field: value}))
        with self.assertRaisesRegex(OperationsError, 'version'):
            rehash(original, version='unknown')
        with self.assertRaisesRegex(OperationsError, 'type'):
            self.verify({}, expected_boundary_id=original.boundary_id)
        with self.assertRaises(OperationsError):
            source.FrozenReportingSource.from_json(original.to_json().replace(
                '"version":"mlb-reporting-source-1"', '"version":"unknown"'))

    def test_post_cutoff_manifest_and_fabricated_earlier_freeze_rejected(self):
        original = self.freeze()
        forged = rehash(original, evidence_cutoff_at=self.at-timedelta(days=2))
        with self.assertRaisesRegex(OperationsError, 'post-cutoff'):
            self.verify(forged)
        with self.assertRaisesRegex(OperationsError, 'predates'):
            self.verify(original, clock=lambda: self.at-timedelta(seconds=1))
        with self.assertRaises(OperationsError):
            self.freeze(clock=lambda: self.at.replace(tzinfo=None))

    def test_namespace_corruption_outside_roots_blocks_saved_replay(self):
        original = self.freeze()
        page = next(json.loads(value) for value in original.manifest_inventory
                    if json.loads(value)['command'] == 'refresh-retrospective-supporting-page')
        self.assertNotIn(page['manifest_entry_id'], original.source_manifest_ids)
        path = self.archive._path('raw', page['raw_object_sha256'])
        body = path.read_bytes()
        for mutation in ('missing', 'corrupt'):
            with self.subTest(mutation=mutation):
                path.unlink()
                if mutation == 'corrupt':
                    path.write_bytes(b'corrupted synthetic data')
                with self.assertRaisesRegex(OperationsError, 'archive-integrity-failure'):
                    self.verify(original)
                path.write_bytes(body)
        self.verify(original)

    def test_concurrent_append_fails_then_independent_freeze_succeeds(self):
        original_clock_called = False
        def clock():
            nonlocal original_clock_called
            if not original_clock_called:
                original_clock_called = True
                self.fixture.complete()
            return self.at
        with self.assertRaisesRegex(OperationsError, 'changed during freeze'):
            self.freeze(clock=clock)
        self.assertTrue(self.freeze().source_manifest_ids)

    def test_source_is_read_only_and_order_decimal_independent(self):
        before = self.inventory()
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch.object(self.archive, 'commit', side_effect=AssertionError('writes forbidden')), \
             patch.object(self.archive, 'mutation_lock', side_effect=AssertionError('locks forbidden')):
            original = self.freeze()
            entries = self.archive.entries()
            with localcontext() as context:
                context.prec = 6
                with patch.object(self.archive, 'entries', return_value=tuple(reversed(entries))):
                    reordered = self.freeze()
                    state, _ = self.verify(original)
            self.assertEqual(original.to_json(), reordered.to_json())
            for item in state.objects:
                self.assertEqual(deserialize_v3(item.to_json()).to_json(), item.to_json())
        self.assertEqual(before, self.inventory())

    def test_saved_manifest_loss_and_duplicate_json_rejected(self):
        original = self.freeze()
        victim = json.loads(original.manifest_inventory[0])
        self.archive._path('manifest', victim['manifest_entry_id']).unlink()
        with self.assertRaises(OperationsError):
            self.verify(original)
        with self.assertRaisesRegex(OperationsError, 'duplicate'):
            source.FrozenReportingSource.from_json('{"version":"1","version":"2"}')
