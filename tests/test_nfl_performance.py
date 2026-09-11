from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from tests.test_nfl_refresh import workbook
from tests.test_nfl_comparison_board import source, market, ID
from nfl_performance import Performance
import nfl_performance_sources as adapter

BEFORE = '2026-09-09T16:00:00+00:00'
AFTER = '2026-09-10T04:00:00+00:00'


class Clock:
    value = BEFORE
    def __call__(self):
        return self.value


def book(home=.60, pub='Updated September 9, 2026 at 10:51 AM EDT'):
    def change(s):
        s['A6']='1';s['B6']='SEA';s['E6']='NE';s['D6']=home;s['G6']=.39;s['A8']=pub
    return workbook(change)


def game(final=False, score=7):
    query=json.loads(json.loads(source().decode().split('push(')[1].split(')</script>')[0])[1].split(':',1)[1])
    g=query['state']['data'][0]
    g['homeTeam']['id']='home';g['awayTeam']['id']='away'
    if final:
        g['summary']=dict(gameId=ID,phase='FINAL',quarter='END_OF_GAME',startTime='2026-09-10T00:21:00Z',
            homeTeam=dict(teamId='home',score=dict(total=score)),awayTeam=dict(teamId='away',score=dict(total=27)))
    return g


class Transport:
    def __init__(self):
        self.fail=False;self.yes='0.54';self.no='0.42';self.calls=0;self.extra=[]
    def __call__(self,route,params):
        self.calls+=1
        if route.startswith('/series/'):
            data={'series':{'ticker':'KXNFLGAME','product_metadata':{'scope':'Game'}}}
        elif route=='/markets':
            data={'markets':[market()]+self.extra,'cursor':''}
        elif self.fail:
            return 503,b'unavailable'
        else:
            data={'orderbook_fp':{'yes_dollars':[[self.yes,'10']], 'no_dollars':[[self.no,'20']]}}
        return 200,json.dumps(data).encode()


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.clock=Clock();self.engine=Performance.initialize(self.tmp.name,'test fixture only',self.clock)
        self.transport=Transport();self.g=game()
    def refresh(self,raw=None,**kw):
        return self.engine.refresh(raw or book(),'elway.xlsx',2026,1,
             schedule_transport=lambda _: (200,source([self.g])),market_transport=self.transport,**kw)
    def report(self):
        return self.engine.report(2026,1,self.clock())
    def finish(self,score=7):
        self.clock.value=AFTER
        self.engine.observe_results(2026,1,lambda _: (200,source([game(True,score)])))
        return self.report()
    def test_complete_capture_and_official_result_without_fees(self):
        self.refresh();r=self.report();self.assertEqual(r['games'][0]['state'],'candidate')
        r=self.finish();self.assertEqual(r['paired_games'],1)
        self.assertEqual(Decimal(r['means']['elway_error']),Decimal('.366025'))
        self.assertEqual(Decimal(r['means']['kalshi_error']),Decimal('.3136'))
        self.assertEqual(r['games'][0]['outcome']['issues'],['Outer SCHEDULED; validated summary FINAL'])
    def test_identical_import_and_metadata_resave_do_not_reset(self):
        raw=book();self.refresh(raw);calls=self.transport.calls
        self.clock.value='2026-09-09T17:00:00+00:00';self.transport.yes='0.10'
        # Workbook zip bytes can differ; identity is validated target-week content.
        self.refresh(book());self.assertEqual(self.transport.calls,calls)
        self.assertEqual(self.report()['games'][0]['kalshi']['value'],'0.56')
    def test_newer_partial_never_falls_back(self):
        self.refresh();self.transport.fail=True;self.clock.value='2026-09-09T18:00:00+00:00'
        newer=book(.59,'Updated September 9, 2026 at 12:00 PM EDT');self.refresh(newer)
        r=self.finish();self.assertEqual(r['paired_games'],0);self.assertEqual(r['population'],1)
        self.assertEqual(r['means']['elway_error'],None)
    def test_retry_missing_only_and_real_times(self):
        raw=book();self.transport.fail=True;self.refresh(raw)
        self.transport.fail=False;self.clock.value='2026-09-09T18:00:00+00:00';self.refresh(raw,retry=True)
        q=self.report()['games'][0]['kalshi'];self.assertTrue(q['retry']);self.assertEqual(q['received_at'],self.clock())
        self.transport.yes='0.01';self.refresh(raw,retry=True)
        self.assertEqual(self.report()['games'][0]['kalshi']['value'],'0.56')
    def test_late_newer_does_not_replace_frozen_selection(self):
        self.refresh();identity=self.report()['selected_import'];self.clock.value=AFTER
        self.refresh(book(.59,'Updated September 9, 2026 at 12:00 PM EDT'))
        self.assertEqual(self.report()['selected_import'],identity)
    def test_missing_weekly_baseline_after_activation_cutoff(self):
        self.clock.value=AFTER;self.refresh();self.assertIsNone(self.report()['selected_import'])
    def test_conflicting_same_publication_no_fallback(self):
        self.refresh();self.clock.value='2026-09-09T17:00:00+00:00';self.refresh(book(.59))
        self.assertIsNone(self.report()['selected_import']);self.assertIn('Conflicting',self.report()['selection_issue'])
    def test_outcome_correction_and_historical_replay(self):
        self.refresh();old=self.finish();self.clock.value='2026-09-10T06:00:00+00:00'
        self.engine.observe_results(2026,1,lambda _: (200,source([game(True,30)])))
        self.assertEqual(self.report()['games'][0]['outcome']['payout'],'1')
        self.assertEqual(self.engine.report(2026,1,AFTER),old)
    def test_tie_and_invalid_outcome_identity(self):
        self.refresh();r=self.finish(27);self.assertEqual(Decimal(r['means']['elway_error']),Decimal('.011025'))
        g=game(True);g['summary']['homeTeam']['teamId']='wrong';self.clock.value='2026-09-10T06:00:00+00:00'
        self.engine.observe_results(2026,1,lambda _: (200,source([g])))
        self.assertEqual(self.report()['games'][0]['state'],'unresolved-outcome')
    def test_unknown_cutoff_and_later_schedule_cannot_reopen(self):
        self.g['time']=None;self.refresh();self.assertIsNone(self.report()['cutoff'])
        self.g=game();self.clock.value='2026-09-09T18:00:00+00:00';self.refresh(retry=True)
        cutoff=self.report()['cutoff'];self.clock.value=AFTER
        self.g['time']='2026-09-12T00:20:00Z'
        self.engine.observe_results(2026,1,lambda _: (200,source([self.g])))
        self.assertEqual(self.report()['cutoff'],cutoff)
    def test_blob_tampering_fails_replay(self):
        self.refresh();p=next((Path(self.tmp.name)/'blobs').iterdir());p.write_bytes(b'bad')
        with self.assertRaises(ValueError):self.report()
    def test_ambiguous_home_market_no_selection(self):
        duplicate=market();duplicate['ticker']+='-OTHER';self.transport.extra=[duplicate]
        self.refresh();self.assertEqual(self.finish()['paired_games'],0)
    def test_crossed_book_unavailable(self):
        self.transport.yes='0.9';self.refresh();self.assertEqual(self.finish()['paired_games'],0)
    def test_sources_no_forecast_are_coverage(self):
        self.engine.observe_results(2026,1,lambda _: (200,source([game(True)])))
        self.assertEqual(self.report()['population'],1);self.assertEqual(self.report()['paired_games'],0)
    def test_rejected_zip_preserved_without_destroying_baseline(self):
        self.refresh();selected=self.report()['selected_import']
        self.refresh(b'not an Excel workbook')
        self.assertEqual(self.report()['selected_import'],selected)
        self.assertTrue(self.report()['diagnostics'])
    def test_exact_cutoff_response_excluded(self):
        original=self.transport
        def transport(route,params):
            response=original(route,params)
            if route.endswith('/orderbook'):
                self.clock.value='2026-09-10T00:20:00+00:00'
            return response
        self.engine.refresh(book(),'x.xlsx',2026,1,schedule_transport=lambda _: (200,source([self.g])),market_transport=transport)
        self.assertEqual(self.finish()['paired_games'],0)
    def test_saved_boundary_replay_with_equal_time_correction(self):
        self.refresh();self.finish()
        r=self.engine.save_report(2026,1,self.clock())
        self.engine.observe_results(2026,1,lambda _: (200,source([game(True,30)])))
        path=Path(self.tmp.name)/'reports'/(r['report_id']+'.json')
        self.assertEqual(self.engine.replay_report(path),r)
        self.assertNotEqual(self.report()['means'],r['means'])
    def test_schedule_identity_replacement_never_double_scores(self):
        self.refresh();self.finish();self.clock.value='2026-09-10T06:00:00+00:00'
        replacement=game(True);replacement['id']='a8fb0d79-4feb-11f1-abca-2c54536568a9'
        replacement['summary']['gameId']=replacement['id']
        self.engine.observe_results(2026,1,lambda _: (200,source([replacement])))
        self.assertEqual(self.report()['paired_games'],0)
    def test_other_official_game_is_not_lost_when_workbook_missing(self):
        second=game();second['id']='a8fb0d79-4feb-11f1-abca-2c54536568a9'
        second['homeTeam']={'id':'h2','fullName':'Buffalo Bills'};second['awayTeam']={'id':'a2','fullName':'New York Jets'}
        self.engine.refresh(book(),'x.xlsx',2026,1,schedule_transport=lambda _: (200,source([self.g,second])),market_transport=self.transport)
        self.assertEqual(self.report()['population'],2)
        missing=next(g for g in self.report()['games'] if g['home']=='BUF')
        self.assertIn('Missing forecast',missing['issues'])
    def test_schedule_failure_visible_and_no_market_calls(self):
        self.engine.refresh(book(),'x.xlsx',2026,1,schedule_transport=lambda _: (503,b'no'),market_transport=self.transport)
        self.assertEqual(self.transport.calls,0);self.assertTrue(self.report()['diagnostics'])
    def test_empty_store_report_replay_and_no_default_activation(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):Performance(tmp)
        r=self.engine.save_report(2026,1,self.clock())
        self.refresh()
        self.assertEqual(self.engine.replay_report(Path(self.tmp.name)/'reports'/(r['report_id']+'.json')),r)
    def test_future_boundary_rejected(self):
        with self.assertRaises(ValueError):self.engine.report(2026,1,AFTER)
    def test_failed_opponent_book_does_not_discard_valid_home_book(self):
        self.transport.extra=[market('New England','NE')]
        original=self.transport
        def partial(route,params):
            if route.endswith('NE/orderbook'):
                return 503,b'failed away book'
            return original(route,params)
        self.engine.refresh(book(),'x.xlsx',2026,1,schedule_transport=lambda _: (200,source([self.g])),market_transport=partial)
        self.assertEqual(self.finish()['paired_games'],1)
    def test_exact_arithmetic(self):
        for y,e,k in [('1','.156025','.1936'),('0','.366025','.3136'),('.5','.011025','.0036')]:
            result=adapter.error_scores('.605','.56',y)
            self.assertEqual(Decimal(result['elway_error']),Decimal(e));self.assertEqual(Decimal(result['kalshi_error']),Decimal(k))

if __name__=='__main__':unittest.main()
