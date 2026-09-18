"""Original-rule reconstruction equivalence and reconstruction-local read bounds."""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_source as source
from forecast_standalone_operations import OperationsError, canonical_bytes
from tests.test_forecast_supporting_replay import supporting_fixture


class UncachedReportingView(source._ReportingArchiveView):
    """Pre-amendment read/check behavior, used only as an offline reference."""
    memoized_supporting_verification = None

    def entries(self):
        return tuple(json.loads(canonical_bytes(item)) for item in self._entries)

    def read_verified(self, family, identity):
        return self._archive.read_verified(family, identity)

    def read_json_verified(self, family, identity):
        return json.loads(self.read_verified(family, identity))

    def verify_unchanged(self):
        pass


class ReconstructionReadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive, self.at = supporting_fixture(Path(self.temp.name), sessions=2, markets=120)
        self.inventory = source._inventory(self.archive)

    def view(self):
        return source._ReportingArchiveView(self.archive, self.inventory)

    def test_exact_replay_and_each_consumed_object_read_twice(self):
        with patch.object(source, '_ReportingArchiveView', UncachedReportingView):
            expected = source._reconstruct_uncached(self.archive, self.inventory, self.at)
        reads = Counter()
        original = self.archive.read_verified
        def counted(family, identity):
            reads[(family, identity)] += 1
            return original(family, identity)
        with patch.object(self.archive, 'read_verified', side_effect=counted):
            actual = source._reconstruct_uncached(self.archive, self.inventory, self.at)
        self.assertEqual(expected, actual)
        self.assertTrue(reads)
        # The namespace-wide audit uses its own direct filesystem reads.
        self.assertEqual(set(reads.values()), {2})

    def test_manifest_is_deeply_read_only(self):
        view = self.view()
        entry = view.entries()[0]
        with self.assertRaises(TypeError):
            entry['command'] = 'invented'
        with self.assertRaises(TypeError):
            entry['acquired_at']['datetime_utc'] = 'invented'
        self.assertIs(view.entries(), view.entries())

    def test_decoded_mutation_is_rejected_before_acceptance(self):
        view = self.view()
        identity = next(x['normalized_object_id'] for x in view.entries()
                        if x.get('normalized_object_id'))
        value = view.read_json_verified('normalized', identity)
        value['invented'] = True
        with self.assertRaisesRegex(OperationsError, 'decoded source changed'):
            view.verify_unchanged()

    def test_missing_or_corrupt_cached_bytes_rejected(self):
        identity = next(x['raw_object_sha256'] for x in self.archive.entries()
                        if x.get('raw_object_sha256'))
        path = self.archive._path('raw', identity)
        original = path.read_bytes()
        for mutation in ('corrupt', 'missing'):
            with self.subTest(mutation=mutation):
                view = self.view()
                self.assertEqual(view.read_verified('raw', identity), original)
                if mutation == 'corrupt':
                    path.chmod(0o644)
                    path.write_bytes(b'corrupt synthetic source')
                else:
                    path.unlink()
                with self.assertRaises((OperationsError, FileNotFoundError)):
                    view.verify_unchanged()
                path.write_bytes(original)

    def test_public_verification_rejects_corruption_during_reconstruction(self):
        boundary = source.freeze_reporting_source(archive=self.archive, clock=lambda: self.at)
        original = source.replay_pr17_archive
        def corrupt_after_replay(view, **kwargs):
            state = original(view, **kwargs)
            identity = next(x['raw_object_sha256'] for x in view.entries()
                            if x.get('raw_object_sha256'))
            path = self.archive._path('raw', identity)
            path.chmod(0o644)
            path.write_bytes(b'corrupt after replay')
            return state
        with patch.object(source, 'replay_pr17_archive', side_effect=corrupt_after_replay):
            with self.assertRaises(OperationsError):
                source.verify_reporting_source(archive=self.archive, boundary=boundary,
                    expected_boundary_id=boundary.boundary_id, clock=lambda: self.at)

    def test_success_only_memoization_and_fresh_view(self):
        view = self.view()
        calls = []
        def success():
            calls.append(1)
            return 'verified'
        for _ in range(2):
            self.assertEqual(view.memoized_supporting_verification(('fixture',), success), 'verified')
        self.assertEqual(len(calls), 1)
        self.view().memoized_supporting_verification(('fixture',), success)
        self.assertEqual(len(calls), 2)
        def fail():
            calls.append(1)
            raise ValueError('not verified')
        for _ in range(2):
            with self.assertRaises(ValueError):
                view.memoized_supporting_verification(('failure',), fail)
        self.assertEqual(len(calls), 4)
