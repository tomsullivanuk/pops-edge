"""Research aliases are explicit; archived interpretations remain replayable."""
import unittest
from unittest.mock import patch
import nfl_forecast_import as base
import nfl_performance_sources as adapter
from tests import test_nfl_performance as fixture
from tests.test_nfl_comparison_board import market, inputs


def abbreviated():
    m = market()
    for field in ('rules_primary', 'rules_secondary'):
        m[field] = m[field].replace('New England vs Seattle', 'NE Patriots vs SEA Seahawks')
    return m


class ResearchMatchingTests(unittest.TestCase):
    def test_alias_retry_fills_only_missing_and_reimports_do_not_reset(self):
        f = fixture.PerformanceTests(); f.setUp(); self.addCleanup(f.doCleanups)
        with patch.object(fixture, 'market', abbreviated):
            f.transport.fail = True
            f.refresh()
            f.transport.fail = False
            f.clock.value = '2026-09-09T18:00:00+00:00'
            f.refresh(retry=True)
            quote = f.report()['games'][0]['kalshi']
            self.assertTrue(quote['retry'])
            calls = f.transport.calls
            f.transport.yes = '0.01'
            f.refresh()
            self.assertEqual(f.transport.calls, calls)
            f.refresh(retry=True)
            self.assertEqual(f.report()['games'][0]['kalshi'], quote)

    def test_legacy_and_corrected_reports_replay_without_changing_evidence(self):
        f = fixture.PerformanceTests(); f.setUp(); self.addCleanup(f.doCleanups)
        with patch.object(fixture, 'market', abbreviated):
            f.refresh()
        f.finish()
        before = {str(p): p.read_bytes() for p in f.engine.root.rglob('*') if p.is_file()}
        old = f.engine.report(2026, 1, f.clock(), matching_version=None)
        new = f.report()
        self.assertEqual(old['coverage'], {'missing-capture': 1})
        self.assertEqual(new['paired_games'], 1)
        self.assertNotIn('matching_version', old)
        self.assertEqual(new['matching_version'], adapter.board.MATCHING_VERSION)
        self.assertEqual(new['legacy_interpretation_id'], old['report_id'])
        for key in ('cutoff', 'source_boundary', 'selected_import', 'selected_forecast', 'attempts', 'activation'):
            self.assertEqual(old[key], new[key])
        self.assertEqual(before, {str(p): p.read_bytes() for p in f.engine.root.rglob('*') if p.is_file()})
        for report in (old, new):
            path = f.engine.root/'reports'/(report['report_id']+'.json')
            base.write_once(path, base.encode(report))
            self.assertEqual(f.engine.replay_report(path), report)
        calls = f.transport.calls
        f.refresh(retry=True)
        self.assertEqual(calls, f.transport.calls)
        with self.assertRaises(ValueError):
            f.engine.report(2026, 1, f.clock(), matching_version='unknown')

    def test_adapter_preserves_legacy_and_fail_closed_guards(self):
        for fault in (None, 'ambiguous', 'rules', 'unknown', 'book', 'date'):
            _, schedule, summary, _ = inputs()
            summary['catalog_complete'] = True
            markets = [abbreviated()]
            if fault == 'ambiguous': markets.append(abbreviated())
            if fault == 'rules': markets[0]['rules_secondary'] += ' Ties resolve to No.'
            if fault == 'unknown': markets[0]['rules_primary'] = markets[0]['rules_primary'].replace('NE Patriots', 'Unknown Team')
            if fault == 'book': summary['rows'] = []
            if fault == 'date': schedule['rows'][0]['kickoff'] = '2026-09-12T00:20:00Z'
            with self.assertRaises(ValueError): adapter.midpoint(schedule['rows'][0], summary, markets)
            if fault:
                with self.assertRaises(ValueError):
                    adapter.midpoint(schedule['rows'][0], summary, markets, matching_version=adapter.board.MATCHING_VERSION)
            else:
                self.assertEqual(adapter.midpoint(schedule['rows'][0], summary, markets,
                    matching_version=adapter.board.MATCHING_VERSION)['value'], '0.59')
        with self.assertRaises(ValueError): adapter.midpoint({}, {}, [], matching_version='unknown')
