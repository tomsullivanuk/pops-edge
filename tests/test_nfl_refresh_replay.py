from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from nfl_performance import Performance
from nfl_refresh_replay import RefreshPerformance
from tests import test_nfl_performance as fixtures
from tests.test_nfl_performance import Clock


class RefreshReplayTests(fixtures.PerformanceTests):
    """Run the complete scientific service regression suite through parse reuse."""
    def setUp(self):
        super().setUp()
        self.engine = RefreshPerformance(self.tmp.name, self.clock)

    def test_warm_blob_tamper_still_fails(self):
        self.refresh()
        self.report()
        event = next(e for e in self.engine.events() if e['kind'] == 'schedule')
        key = event['payload']['files']['source.html']
        # Locate the source through the same content-addressed blob layout.
        path = self.engine.root/'blobs'/key
        self.assertTrue(path.exists())
        path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            self.report()


class MemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        clock = Clock()
        Performance.initialize(self.tmp.name, 'offline only', clock)
        self.engine = RefreshPerformance(self.tmp.name, clock)

    def test_keys_copies_new_content_and_rule_arguments(self):
        parse = Mock(return_value={'items': [1]})
        first = self.engine.parsed(parse, b'old', outcome_rule='a')
        first['items'].append(2)
        self.assertEqual(self.engine.parsed(parse, b'old', outcome_rule='a'), {'items': [1]})
        self.assertEqual(parse.call_count, 1)
        self.engine.parsed(parse, b'new', outcome_rule='a')
        self.engine.parsed(parse, b'old', outcome_rule='b')
        self.assertEqual(parse.call_count, 3)
        other = RefreshPerformance(self.tmp.name, Clock())
        other.parsed(parse, b'old', outcome_rule='a')
        self.assertEqual(parse.call_count, 4)

    def test_capacity_eviction_and_oversized_bypass(self):
        e = self.engine
        e.MAX_ENTRIES = 1
        parse = Mock(return_value={'items': [1]})
        for raw in (b'a', b'b', b'a'):
            e.parsed(parse, raw)
        self.assertEqual(parse.call_count, 3)
        self.assertEqual(len(e._parses), 1)
        self.assertLessEqual(e.retained_bytes, e.MAX_BYTES)
        e.MAX_BYTES = e.retained_bytes
        e.parsed(parse, b'a')
        self.assertEqual(parse.call_count, 3)
        fresh = RefreshPerformance(self.tmp.name, Clock())
        fresh.MAX_BYTES = 1
        for _ in range(2):
            fresh.parsed(parse, b'a')
        self.assertEqual(fresh.retained_bytes, 0)
        self.assertEqual(len(fresh._parses), 0)
        self.assertEqual(parse.call_count, 5)

    def test_failures_are_not_memoized(self):
        parse = Mock(side_effect=[ValueError('invalid'), {'ok': True}])
        with self.assertRaises(ValueError):
            self.engine.parsed(parse, b'a')
        self.assertEqual(self.engine.parsed(parse, b'a'), {'ok': True})
        self.assertEqual(parse.call_count, 2)

    def test_byte_limit_evicts_and_function_identity_is_separate(self):
        e = self.engine
        parse = Mock(return_value={'items': [1]})
        e.parsed(parse, b'a')
        e.MAX_BYTES = e.retained_bytes
        e.parsed(parse, b'b')
        self.assertEqual(len(e._parses), 1)
        self.assertEqual(e.retained_bytes, e.MAX_BYTES)
        e.parsed(parse, b'a')
        self.assertEqual(parse.call_count, 3)
        other = Mock(return_value={'items': [2]})
        self.assertEqual(e.parsed(other, b'a'), {'items': [2]})
        self.assertEqual(other.call_count, 1)
