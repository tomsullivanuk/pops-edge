from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import nfl_comparison_board as board
from nfl_board_view import sheet_rows
from nfl_season_board import assemble, render
from tests.test_nfl_comparison_board import inputs, AT


class HistoricalComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old = board.derive(*inputs(), AT)
        self.candidate = dict(season=2026, updated_at=AT, rows=[dict(
            week=1, home='SEA', away='NE', neutral=False,
            home_win='68.4%', away_win='31.1%')])
        self.new = deepcopy(self.old)
        self.new['generated_at'] = '2026-09-11T15:00:00Z'
        self.new['capture_started_at'] = self.new['generated_at']
        self.new['capture_completed_at'] = self.new['generated_at']
        for o in self.new['games'][0]['outcomes']:
            o['routes'] = []
            o['best'] = None
            o['payout'] = dict(low='.1', central='.2', high='.3')
        self.sources = {}
        self.add('old', self.old)
        self.add('new', self.new)

    def add(self, name, data):
        p = self.root/'boards'/name
        p.mkdir(parents=True)
        (p/'comparison.json').write_text(json.dumps(data))
        (p/'complete.json').write_text('{}')
        self.sources[p] = data
        return p

    def assemble(self, name='new', now='2026-09-11T15:01:00Z'):
        def replay(path, **kwargs):
            value = self.sources[Path(path)]
            if isinstance(value, Exception):
                raise value
            return value
        with patch('nfl_season_board.board.replay', side_effect=replay):
            return assemble(self.root, [self.root/'boards'/name], self.candidate, now=now)

    def test_refresh_retains_dated_values_and_original_forecast_without_mutation(self):
        before = deepcopy(self.sources)
        data = self.assemble()
        o = data['games'][0]['outcomes'][0]
        h = o['historical']
        self.assertEqual(h['outcome'], self.old['games'][0]['outcomes'][0])
        self.assertEqual(o['payout']['central'], '.2')
        self.assertEqual(self.sources, before)
        self.assertTrue(all(row['route'] is None for row in sheet_rows(data)))
        self.assertEqual(data['ranked_games'], 0)
        html = render(data)
        self.assertIn('Historical comparison', html)
        self.assertIn('09/09/2026 10:00 AM CDT', html)
        self.assertIn('current comparable outcomes', html)
        self.assertIn('data-gap=""', html)
        from decimal import Decimal
        from html.parser import HTMLParser
        class Table(HTMLParser):
            def __init__(self): super().__init__(); self.groups=[]; self.cells=[]
            def handle_starttag(self, tag, attrs):
                if tag == 'tbody': self.groups.append(dict(attrs))
                if tag == 'td': self.cells.append(dict(attrs))
        table=Table();table.feed(html)
        expected_gap=str(Decimal(h['outcome']['payout']['central'])-Decimal(h['route']['cost']['total']))
        self.assertTrue(all(g['data-gap']=='' for g in table.groups))
        for value in (h['outcome']['payout']['central'], h['route']['cost']['price'], expected_gap):
            self.assertIn(value, [c.get('data-sort') for c in table.cells])
        self.assertIn('Latest snapshot ELWAY win:', html)

    def test_aging_without_refresh_and_fresh_current_precedence(self):
        fresh = self.assemble('old', AT)
        self.assertTrue(all('historical' not in o for o in fresh['games'][0]['outcomes']))
        self.assertTrue(all(row['route'] for row in sheet_rows(fresh)))
        stale = self.assemble('old', '2026-09-09T15:06:00Z')
        self.assertTrue(all('historical' in o for o in stale['games'][0]['outcomes']))
        self.assertFalse(any(row['route'] for row in sheet_rows(stale)))

    def test_no_valid_history_stays_missing_and_invalid_history_is_visible(self):
        self.sources[self.root/'boards/old'] = ValueError('digest mismatch')
        data = self.assemble()
        self.assertTrue(data['diagnostics'])
        self.assertTrue(all('historical' not in o for o in data['games'][0]['outcomes']))
        html = render(data)
        self.assertIn('Some saved history or official results could not be verified', html)
        self.assertIn('No saved pregame comparison', html)

    def test_changed_identity_or_kickoff_never_borrows_history(self):
        for field, value in [('game_id', 'different'), ('kickoff', '2026-09-12T00:20:00Z'), ('neutral', True)]:
            with self.subTest(field=field):
                original = self.new['games'][0][field]
                self.new['games'][0][field] = value
                data = self.assemble()
                self.assertTrue(all('historical' not in o for o in data['games'][0]['outcomes']))
                self.new['games'][0][field] = original

    def test_latest_valid_per_outcome_and_tied_conflict(self):
        later = deepcopy(self.old)
        later['generated_at'] = '2026-09-09T15:01:00Z'
        later['games'][0]['outcomes'][0]['routes'] = []
        later['games'][0]['outcomes'][0]['best'] = None
        self.add('later', later)
        data = self.assemble()
        self.assertEqual(data['games'][0]['outcomes'][0]['historical']['generated_at'], AT)
        self.assertEqual(data['games'][0]['outcomes'][1]['historical']['generated_at'], later['generated_at'])
        conflict = deepcopy(later)
        conflict['games'][0]['outcomes'][1]['payout']['central'] = '.123'
        self.add('conflict', conflict)
        data = self.assemble()
        self.assertNotIn('historical', data['games'][0]['outcomes'][1])
        self.assertIn('Conflicting', data['diagnostics'][0]['history'])

    def test_outer_final_alone_preserves_history_without_claiming_completion(self):
        self.new['games'][0]['status'] = 'FINAL'
        data = self.assemble()
        self.assertFalse(data['games'][0]['completed'])
        self.assertEqual(data['games'][0]['display_status'], 'Started')
        self.assertTrue(all('historical' in o for o in data['games'][0]['outcomes']))
        self.assertFalse(any(row['route'] for row in sheet_rows(data)))
        self.assertIn('data-completed="false"', render(data))

    def test_later_settlement_overlay_does_not_erase_pregame_history(self):
        self.old['activity'] = dict(settlement_events=[dict(game_id=self.old['games'][0]['game_id'])])
        data = self.assemble()
        self.assertTrue(all('historical' in o for o in data['games'][0]['outcomes']))

    def test_future_snapshot_cannot_supply_history(self):
        self.old['generated_at'] = '2027-01-01T00:00:00Z'
        (self.root/'boards/old/comparison.json').write_text(json.dumps(self.old))
        data = self.assemble()
        self.assertTrue(all('historical' not in o for o in data['games'][0]['outcomes']))


if __name__ == '__main__':
    unittest.main()
