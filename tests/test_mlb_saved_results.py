"""Saved quote/result lifecycle and display boundaries, using offline providers only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

import mlb_odds as odds
from tests import test_mlb_odds as fixtures
from tests.test_mlb_odds import game, schedule, DAY, AT


def final_game(away=3, home=5):
    g=game()
    g['status']=dict(detailedState='Final', abstractGameState='Final', codedGameState='F', statusCode='F')
    for side,score in [('away',away),('home',home)]:
        g['teams'][side]['score']=score
    return g


class ResultsInterpretation(unittest.TestCase):
    def test_result_requires_final_valid_scores_and_consistent_flags(self):
        g=final_game()
        r=odds.schedule_games(schedule([g]), DAY, (AT+timedelta(hours=12)).isoformat())[0]['official_result']
        self.assertEqual(r['winning_side'],'home');self.assertEqual(r['away_score'],3)
        for side in ('away','home'):
            for score in (None, True, -1, '5', 1.5):
                changed=deepcopy(g);changed['teams'][side]['score']=score
                self.assertEqual(odds.official_result(changed,(AT+timedelta(hours=12)).isoformat())['state'],'unavailable')
        for key,value in [('detailedState','In Progress'),('detailedState','Suspended'),('detailedState','Game Over'),
                          ('detailedState','Cancelled'),('detailedState','Unknown'),('abstractGameState','Live'),('codedGameState','I')]:
            changed=deepcopy(g);changed['status'][key]=value
            self.assertIsNone(odds.official_result(changed,(AT+timedelta(hours=12)).isoformat())['winning_side'])
        for flag in (True,'false',0):
            changed=deepcopy(g);changed['teams']['away']['isWinner']=flag
            self.assertEqual(odds.official_result(changed,(AT+timedelta(hours=12)).isoformat())['state'],'unavailable')
        self.assertIsNone(odds.official_result(final_game(),AT.isoformat())['winning_side'])
        self.assertIsNone(odds.official_result(final_game(3,3),(AT+timedelta(hours=12)).isoformat())['winning_side'])
        changed=final_game();changed['rescheduledFromDate']='2026-09-14'
        self.assertIsNone(odds.schedule_games(schedule([changed]),DAY,(AT+timedelta(hours=12)).isoformat())[0]['official_result']['winning_side'])

    def test_central_dst_and_calendar_are_distinct_from_rule_timezone(self):
        for instant,expected in [('2026-09-16T05:30:00+00:00','2026-09-16'),
                                 ('2026-09-16T04:30:00+00:00','2026-09-15')]:
            self.assertEqual(odds.aware(instant).astimezone(odds.CENTRAL).date().isoformat(),expected)
        self.assertEqual(odds.aware('2026-01-15T12:00:00+00:00').astimezone(odds.CENTRAL).tzname(),'CST')
        self.assertEqual(odds.aware('2026-09-15T12:00:00+00:00').astimezone(odds.CENTRAL).tzname(),'CDT')


class SavedResults(unittest.TestCase):
    setUp = fixtures.Lifecycle.setUp
    tearDown = fixtures.Lifecycle.tearDown
    def test_past_result_update_preserves_exact_quote_and_original_evidence(self):
        self.store.refresh(DAY);old=self.store.read(DAY);capture=old['result']['games'][0]['away_quote']
        original={p:p.read_bytes() for p in (self.root/'attempts'/old['selected']['id']).rglob('*') if p.is_file()}
        self.clock.seconds=86400;self.clock.seconds=max(self.clock.seconds,43200);self.feed.games=[final_game()];self.feed.calls.clear()
        self.store.refresh(DAY);value=self.store.read(DAY);g=value['result']['games'][0]
        self.assertEqual([call[0] for call in self.feed.calls],['mlb'])
        self.assertEqual(g['official_result']['state'],'final');self.assertEqual(g['official_result']['winning_side'],'home')
        self.assertEqual(g['away_quote']['cents'],capture['cents'])
        self.assertEqual(g['away_quote']['completed_at'],capture['completed_at'])
        self.assertTrue(g['away_quote']['retained'])
        self.assertEqual(g['away_quote']['source_selection'],old['selected'])
        self.assertNotEqual(g['official_result']['observed_at'],capture['completed_at'])
        self.assertIn('Prices were not retrieved',value['attempt']['message'])
        self.assertEqual(original,{p:p.read_bytes() for p in original})
        self.assertEqual(self.store.download(DAY,old['selected']['id'],capture['raw_file']),original[self.root/'attempts'/old['selected']['id']/capture['raw_file']])
        # A second result observation references the original capture directly, not a chain.
        self.clock.seconds+=10;self.store.refresh(DAY,mode='results')
        newer=self.store.read(DAY);self.assertEqual(newer['result']['retained_quotes'][0]['source'],old['selected'])
        self.assertEqual(newer['result']['games'][0]['home_quote']['completed_at'],capture['completed_at'])
        with self.assertRaises(ValueError):self.store.refresh(DAY,mode="odds")

    def test_no_saved_day_future_or_other_season_result_acquisition(self):
        for day in (DAY,'2026-09-16','2025-09-15'):
            with self.assertRaises(ValueError):self.store.refresh(day,mode='results')
        self.assertFalse(self.feed.calls);self.assertFalse(self.root.exists())

    def test_failed_results_keep_selection_and_failure_after_reload(self):
        self.store.refresh(DAY);old=self.store.read(DAY)
        self.feed.fail=lambda route:True
        with self.assertRaises(ValueError):self.store.refresh(DAY,mode='results')
        value=self.store.read(DAY)
        self.assertEqual(value['selected'],old['selected']);self.assertEqual(value['result'],old['result'])
        self.assertEqual(value['attempt']['mode'],'results');self.assertEqual(value['attempt']['state'],'failed')

    def test_result_publication_failure_does_not_select_new_scores(self):
        self.store.refresh(DAY);old=self.store.read(DAY);self.clock.seconds=max(self.clock.seconds,43200);self.feed.games=[final_game()]
        original=self.store._save_state
        def fail_complete(state):
            if state['attempt']['state']=='complete':raise OSError('publication failed')
            return original(state)
        with patch.object(self.store,'_save_state',side_effect=fail_complete),self.assertRaises(OSError):
            self.store.refresh(DAY,mode='results')
        self.assertEqual(self.store.read(DAY)['result'],old['result'])

    def test_missing_final_scores_are_visible_with_prices_retained(self):
        self.store.refresh(DAY);self.clock.seconds=43200;self.feed.games=[final_game(None)]
        self.store.refresh(DAY,mode='results');value=self.store.read(DAY)
        self.assertEqual(value['attempt']['state'],'partial')
        g=value['result']['games'][0];self.assertEqual(g['official_result']['state'],'unavailable')
        self.assertIsNotNone(g['away_quote']);self.assertIsNone(g['official_result']['winning_side'])

    def test_changed_start_team_or_doubleheader_cannot_inherit_quote(self):
        for change in ('start','team','number','reschedule'):
            with self.subTest(change=change):
                self.feed.games=None;self.store.refresh(DAY)
                g=final_game()
                if change=='start':g['gameDate']='2026-09-15T22:15:00Z'
                if change=='team':g['teams']['away']['team']['id']=999
                if change=='number':g['doubleHeader']='S';g['gameNumber']=2
                if change=='reschedule':g['rescheduledFromDate']='2026-09-14'
                self.feed.games=[g];self.store.refresh(DAY,mode='results')
                self.assertIsNone(self.store.read(DAY)['result']['games'][0]['away_quote'])

    def test_failed_book_retains_previous_capture_but_not_new_price_coverage(self):
        self.store.refresh(DAY);old=self.store.read(DAY);self.clock.seconds=30
        self.feed.fail=lambda route:route.endswith('-SF/orderbook')
        self.store.refresh(DAY);value=self.store.read(DAY);g=value['result']['games'][0]
        self.assertEqual(value['attempt']['state'],'partial')
        self.assertTrue(g['home_quote']['retained']);self.assertIn('1 of 2',value['attempt']['message'])
        self.assertEqual(g['home_quote']['completed_at'],old['result']['games'][0]['home_quote']['completed_at'])
        self.assertNotIn('retained',g['away_quote'])

    def test_changed_contract_does_not_reuse_old_quote(self):
        self.store.refresh(DAY);self.feed.markets[1]['ticker']='KXMLBGAME-NEW-SF'
        self.feed.fail=lambda route:route.endswith('-SF/orderbook')
        self.store.refresh(DAY);self.assertIsNone(self.store.read(DAY)['result']['games'][0]['home_quote'])

    def test_original_v1_bundle_remains_readable_and_can_supply_retained_quotes(self):
        self.store.refresh(DAY);state=self.store._state(DAY)
        folder=self.root/'attempts'/state['selected']['id']
        result=odds.decode((folder/'result.json').read_bytes())
        for field in ('view_version','retained_quotes','mode'):result.pop(field,None)
        for g in result['games']:
            for field in ('official_result','away_market','home_market'):g.pop(field,None)
        (folder/'result.json').write_bytes(odds.encode(result))
        manifest=odds.decode((folder/'complete.json').read_bytes())
        manifest['files']['result.json']=odds.digest((folder/'result.json').read_bytes())
        (folder/'complete.json').write_bytes(odds.encode(manifest))
        state['selected']['digest']=odds.digest((folder/'complete.json').read_bytes())
        self.store._save_state(state)
        before={p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        calls=len(self.feed.calls);view=self.store.read(DAY)
        self.assertNotIn('official_result',view['result']['games'][0])
        self.assertIsNone(view['error']);self.assertEqual(len(self.feed.calls),calls)
        self.clock.seconds=43200;self.feed.games=[final_game()]
        self.store.refresh(DAY,mode='results')
        self.assertEqual(self.store.read(DAY)['result']['games'][0]['home_quote']['source_selection'],state['selected'])
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_corrupt_retained_evidence_withholds_view(self):
        self.store.refresh(DAY);old=self.store.read(DAY);self.clock.seconds=max(self.clock.seconds,43200);self.feed.games=[final_game()]
        self.store.refresh(DAY,mode='results')
        (self.root/'attempts'/old['selected']['id']/'raw/002.body').write_bytes(b'corrupt')
        value=self.store.read(DAY);self.assertIsNone(value['result']);self.assertIn('changed',value['error'])


if __name__=='__main__':unittest.main()
