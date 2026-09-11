from pathlib import Path
import unittest
from unittest.mock import patch
from nfl_season_board import assemble,render

class SeasonTests(unittest.TestCase):
    def test_all_workbook_games_preserved_without_invented_quotes(self):
        c=dict(season=2026,updated_at='2026-09-09T14:51:00Z',rows=[dict(week=w,home='SEA',away='NE',neutral=False,home_win='69.9%',away_win='29.6%') for w in (1,2)])
        d=assemble(Path('/unused'),[],c,now='2026-09-10T20:00:00Z')
        self.assertEqual(len(d['games']),2)
        self.assertTrue(all(not g['completed'] and g['outcomes'][0]['payout'] is None for g in d['games']))
        h=render(d)
        for control in ('seasonWeek','seasonTeam','omitCompleted','positive'):self.assertIn(control,h)
        self.assertEqual(h.count('class="quote"'),4)
        self.assertNotIn('A previously comparable game has reached kickoff',h)
        self.assertIn('Prices not captured',h)

    def test_started_is_not_completed_and_stale_routes_are_excluded(self):
        c=dict(season=2026,updated_at='2026-09-09T14:51:00Z',rows=[dict(week=1,home='SEA',away='NE',neutral=False,home_win='69.9%',away_win='29.6%')])
        game=dict(game_id='g',week=1,home='SEA',away='NE',status='SCHEDULED',kickoff='2026-09-10T19:00:00Z',outcomes=[dict(routes=[dict(usable=True)])])
        snap=dict(season=2026,generated_at='2026-09-10T18:00:00Z',games=[game],forecast_updated_at=c['updated_at'],capture_started_at='2026-09-10T18:00:00Z',capture_completed_at='2026-09-10T18:00:00Z',guards={'quote_seconds':300})
        with patch('nfl_season_board.board.replay',return_value=snap):d=assemble('/unused',['x'],c,now='2026-09-10T20:00:00Z')
        self.assertEqual(d['games'][0]['display_status'],'Started');self.assertFalse(d['games'][0]['completed']);self.assertFalse(d['games'][0]['outcomes'][0]['routes'][0]['usable'])
        self.assertTrue(game['outcomes'][0]['routes'][0]['usable'])

    def test_schedule_only_tbd_games_keep_their_week(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'schedules/schedule-test';folder.mkdir(parents=True)
            r=dict(season=2026,week=18,error=None,completed_at='2026-09-10T20:00:00Z',rows=[dict(game_id='official-id',season=2026,week=18,home='SEA',away='NE',neutral=False,kickoff=None,status='SCHEDULED',venue=None)])
            (folder/'receipt.json').write_text(json.dumps(r))
            c=dict(season=2026,updated_at='2026-09-09T14:51:00Z',rows=[dict(week=18,home='SEA',away='NE',neutral=False,home_win='69.9%',away_win='29.6%')])
            with patch('nfl_season_board.board.schedule.replay',return_value=r):data=assemble(root,[],c)
            game=data['games'][0];self.assertEqual(game['week'],18);self.assertEqual(game['display_status'],'Date/time TBD');self.assertIsNone(game['kickoff']);self.assertFalse(game['completed']);self.assertIn('Week 18 · Date/time TBD',render(data))
