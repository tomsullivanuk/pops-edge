"""Offline overlap and bounded-failure regressions for daily maintenance."""
import json
import unittest
from datetime import timedelta
from unittest.mock import patch

import forecast_prospective_projection as projection
from forecast_standalone_operations import OperationsError, archive_pr17_authority
from tests import test_forecast_standalone_operations as fixtures


class RebuildRetryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OperationsTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.graph, self.at = self.fixture.seed_prospective()
        self.archive = self.fixture.archive

    def test_append_and_newer_checkpoint_retry_without_rejecting_lineage(self):
        original = projection.replay_boundary
        times = []
        now = [self.at]
        appended = []
        def replay(boundary, at):
            state = original(boundary, at)
            if not appended:
                appended.append(True)
                archive_pr17_authority(self.archive, (self.graph['observation'],), recorded_at=at)
                # Reproduce a collector refreshing its cache after publication.
                projection.load_projection(self.archive, at)
                now[0] += timedelta(seconds=1)
            return state
        def clock():
            times.append(now[0])
            return now[0]
        with patch.object(projection, 'replay_boundary', side_effect=replay):
            count = projection.rebuild_projection_with_retry(self.archive, clock=clock)
        self.assertEqual(count, 2)
        self.assertEqual(times, [self.at, self.at + timedelta(seconds=1)])
        self.assertFalse(list(self.archive.root.glob('prospective-projection-rejected-*')))
        _, state = projection.load_projection(self.archive, now[0])
        self.assertEqual(len(state.bucket('market_observations')), 1)
        self.assertEqual(json.loads(projection.projection_path(self.archive).read_text())['projection']['built_at'], now[0].isoformat())

    def test_publication_race_retries_and_exhaustion_preserves_checkpoint(self):
        before = projection.projection_path(self.archive).read_bytes()
        original = projection._publish
        for failures in (1, 3):
            calls = []
            def publish(*args):
                calls.append(1)
                if len(calls) <= failures:
                    raise OperationsError('projection-stale', 'concurrent publication')
                return original(*args)
            with patch.object(projection, '_publish', side_effect=publish):
                if failures == 1:
                    self.assertEqual(projection.rebuild_projection_with_retry(self.archive, clock=lambda:self.at), 2)
                    before = projection.projection_path(self.archive).read_bytes()
                else:
                    with self.assertRaisesRegex(OperationsError, 'projection-stale'):
                        projection.rebuild_projection_with_retry(self.archive, clock=lambda:self.at)
                    self.assertEqual(projection.projection_path(self.archive).read_bytes(), before)
            self.assertEqual(len(calls), 2 if failures == 1 else 3)
        self.assertFalse(list(self.archive.root.glob('.prospective-*.partial')))

    def test_other_failures_are_not_retried(self):
        for code in ('projection-replay-conflict', 'projection-rejected', 'capture-persistence-unsafe', 'projection-budget-exceeded'):
            with self.subTest(code=code), patch.object(projection, 'rebuild_projection', side_effect=OperationsError(code, 'fixture')) as rebuild:
                with self.assertRaisesRegex(OperationsError, code):
                    projection.rebuild_projection_with_retry(self.archive, clock=lambda:self.at)
                self.assertEqual(rebuild.call_count, 1)

    def test_later_publication_is_replayed_at_fresh_retry_time(self):
        original = projection._publish
        now = [self.at]
        calls = []
        def publish(archive, boundary, at):
            calls.append(at)
            if len(calls) == 1:
                now[0] += timedelta(seconds=1)
                archive_pr17_authority(archive, (self.graph['observation'],), recorded_at=now[0])
            return original(archive, boundary, at)
        with patch.object(projection, '_publish', side_effect=publish):
            self.assertEqual(projection.rebuild_projection_with_retry(self.archive, clock=lambda:now[0]), 2)
        self.assertEqual(calls, [self.at, now[0]])
        _, state = projection.load_projection(self.archive, now[0])
        self.assertEqual(len(state.bucket('market_observations')), 1)
        self.assertFalse(list(self.archive.root.glob('.prospective-*.partial')))

    def test_reversed_clock_stops_retry(self):
        with patch.object(projection, 'rebuild_projection', side_effect=OperationsError('projection-stale', 'fixture')) as rebuild:
            times = iter((self.at, self.at-timedelta(seconds=1)))
            with self.assertRaisesRegex(OperationsError, 'trusted-clock-invalid'):
                projection.rebuild_projection_with_retry(self.archive, clock=lambda:next(times))
            self.assertEqual(rebuild.call_count, 1)


if __name__ == '__main__':
    unittest.main()
