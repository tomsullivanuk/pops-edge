"""One manual sheet refresh: valid result authority and failed odds stay separate."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_mlb_odds as fixtures
from tests.test_mlb_odds import DAY, game, market
from tests.test_mlb_saved_results import final_game
from mlb_odds_store import OddsStore


class UnifiedRefresh(unittest.TestCase):
    setUp=fixtures.Lifecycle.setUp
    tearDown=fixtures.Lifecycle.tearDown

    def test_final_result_publishes_when_other_game_catalog_fails(self):
        self.store.refresh(DAY);old=self.store.read(DAY)
        before={p:p.read_bytes() for p in (self.root/'attempts'/old['selected']['id']).rglob('*') if p.is_file()}
        self.clock.seconds=43200
        upcoming=game(888);upcoming['gameDate']='2026-09-16T04:15:00Z'
        self.feed.games=[final_game(),upcoming];self.feed.fail=lambda route:route=='/markets';self.feed.calls.clear()
        self.store.refresh(DAY);value=self.store.read(DAY)
        self.assertEqual([call[0] for call in self.feed.calls],['mlb','kalshi'])
        self.assertEqual(value['attempt']['state'],'partial')
        self.assertIn('Odds unavailable',value['attempt']['message'])
        final=value['result']['games'][0]
        self.assertEqual(final['official_result']['state'],'final')
        self.assertEqual(final['official_result']['winning_side'],'home')
        self.assertEqual(final['home_quote']['source_selection'],old['selected'])
        self.assertEqual(final['home_quote']['completed_at'],old['result']['games'][0]['home_quote']['completed_at'])
        self.assertIsNone(value['result']['games'][1]['away_quote'])
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertNotEqual(value['selected'],old['selected'])

    def test_incomplete_catalog_never_matches_or_requests_books(self):
        self.store.refresh(DAY);self.feed.calls.clear()
        self.feed.pages=lambda params:dict(markets=[market('away')],cursor='next') if not params.get('cursor') else dict(markets=[],cursor=42)
        self.store.refresh(DAY);value=self.store.read(DAY)
        self.assertEqual(value['attempt']['state'],'partial')
        self.assertEqual(value['result']['diagnostics'],[])
        self.assertFalse(any(route.endswith('/orderbook') for _,route,_ in self.feed.calls))
        self.assertTrue(value['result']['games'][0]['away_quote']['retained'])

    def test_failed_schedule_preserves_all_previous_data_and_stops_odds(self):
        self.store.refresh(DAY);old=self.store.read(DAY);self.feed.calls.clear()
        self.feed.fail=lambda route:route=='/schedule'
        with self.assertRaises(ValueError):self.store.refresh(DAY)
        value=self.store.read(DAY)
        self.assertEqual(value['selected'],old['selected']);self.assertEqual(value['result'],old['result'])
        self.assertEqual(value['attempt']['state'],'failed')
        self.assertEqual([call[0] for call in self.feed.calls],['mlb'])

    def test_partial_publication_failure_and_clock_failure_preserve_selection(self):
        self.store.refresh(DAY);old=self.store.read(DAY)
        self.feed.fail=lambda route:route=='/markets'
        original=self.store._save_state
        def fail_publish(state):
            if state['attempt']['state']=='partial':raise OSError('cannot publish')
            original(state)
        with patch.object(self.store,'_save_state',side_effect=fail_publish),self.assertRaises(OSError):
            self.store.refresh(DAY)
        self.assertEqual(self.store.read(DAY)['selected'],old['selected'])
        original_collect=self.store._collect
        def uncertain(*args,**kwargs):
            result=original_collect(*args,**kwargs);self.store.clock_bad=True;return result
        with patch.object(self.store,'_collect',side_effect=uncertain),self.assertRaisesRegex(ValueError,'Clock changed'):
            self.store.refresh(DAY)
        self.assertEqual(self.store.read(DAY)['selected'],old['selected'])

    def test_single_action_dispatches_past_saved_date_without_kalshi(self):
        self.store.refresh(DAY);self.clock.seconds=86400;self.feed.calls.clear();self.feed.games=[final_game()]
        self.store.start(DAY);self.store.thread.join(3)
        value=self.store.read(DAY)
        self.assertEqual(value['attempt']['state'],'complete')
        self.assertEqual(value['attempt']['mode'],'results')
        self.assertEqual([call[0] for call in self.feed.calls],['mlb'])
        self.assertTrue(value['result']['games'][0]['home_quote']['retained'])
        calls=len(self.feed.calls)
        with self.assertRaises(ValueError):self.store.start('2026-09-14')
        self.assertEqual(len(self.feed.calls),calls)

    def test_central_today_keeps_date_selectable_after_eastern_midnight(self):
        # Sept 16 04:30 UTC is Sept 15 23:30 Central and Sept 16 in Eastern.
        self.clock.seconds=52200
        self.assertEqual(self.store.read(DAY)['today'],DAY)
        self.assertEqual(self.store._refresh_mode(DAY),'odds')
        # At Central midnight, a saved Sept 15 becomes results-only.
        self.clock.seconds=55800
        self.assertEqual(self.store._refresh_mode(DAY),'results')

    def test_future_date_still_collects_schedule_and_eligible_books(self):
        other='2026-09-16'
        def feed(provider,route,params):
            self.feed.calls.append((provider,route,params))
            if provider=='mlb':
                from mlb_odds import decode,encode
                raw=decode(fixtures.schedule());raw['dates'][0]['date']=other
                raw['dates'][0]['games'][0]['gameDate']='2026-09-16T23:15:00Z'
                return 200,encode(raw)
            return 200,b'{"markets":[],"cursor":""}'
        self.store.fetch=feed;self.store.refresh(other)
        self.assertEqual([call[0] for call in self.feed.calls],['mlb','kalshi'])
        self.assertEqual(self.store.read(other)['attempt']['state'],'partial')
        self.assertEqual(self.store.read(other)['result']['expected_outcomes'],2)

if __name__=='__main__':unittest.main()
