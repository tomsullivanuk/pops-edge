import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import nfl_refresh as app
from nfl_performance import Performance
from nfl_refresh_replay import RefreshPerformance
from tests.test_nfl_performance import Clock, Transport, book, game, source, AFTER
from tests.test_nfl_activity import raw, trade


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.w=app.Workflow(self.tmp.name);self.clock=Clock();self.transport=Transport()
        self.engine=Performance.initialize(self.w.data/'performance','offline test only',self.clock)
        self.engine=RefreshPerformance(self.w.data/'performance',self.clock)
        (self.w.inbox/'forecast.xlsx').write_bytes(book())
        (self.w.inbox/'activity.csv').write_bytes(raw([dict(trade(),Original_Date='2026-09-09T15:00:00Z')]))
        self.g=game()
    def payload(self):
        files=self.w.catalog()['files']
        return dict(forecast={'id':next(f['id'] for f in files if f['kind']=='.xlsx')},
                    activity={'id':next(f['id'] for f in files if f['kind']=='.csv')},performance_week=1)
    def run_refresh(self,retry=False,automatic=False):
        payload=self.payload();payload['retry_missing']=retry
        if automatic:payload.pop('performance_week')
        original_schedule=app.schedule.capture;original_market=app.kalshi.capture
        def schedule(store,season,week,**kw):
            return original_schedule(store,season,week,transport=lambda _: (200,source([self.g])),clock=self.clock)
        def market(store,start,end,**kw):
            return original_market(store,start,end,transport=self.transport,clock=self.clock)
        folder=self.w.data/'boards/board-fixture'
        with patch.object(app,'Performance',return_value=self.engine),patch.object(app,'RefreshPerformance',side_effect=lambda *a:RefreshPerformance(self.w.data/'performance',self.clock)),patch.object(app.kalshi,'utc',self.clock),patch.object(app.schedule,'capture',side_effect=schedule),patch.object(app.kalshi,'capture',side_effect=market),patch.object(app.board,'build',return_value=(folder,{})),patch.object(app.board,'replay'),patch.object(app.threading,'Thread') as thread:
            self.w.generate(payload);args=thread.call_args.kwargs['args'];self.w.run(*args)
        return self.engine.report(2026,1,self.clock())
    def test_default_request_automatically_resolves_target(self):
        with patch.object(self.w,'automatic_comparison_week',return_value=1) as choose:
            report=self.run_refresh(automatic=True)
        choose.assert_called_once()
        self.assertIsNotNone(report['selected_import'])
        self.assertEqual(self.w.status['state'],'complete')

    def test_actual_service_first_capture_and_repeat_odds_preserve_prices(self):
        first=self.run_refresh();self.assertEqual(first['games'][0]['kalshi']['value'],'0.56')
        self.transport.yes='0.10';self.clock.value='2026-09-09T18:00:00+00:00'
        second=self.run_refresh();self.assertEqual(second['games'][0]['kalshi']['value'],'0.56')
        markets=[e for e in self.engine.events() if e['kind']=='market'];self.assertEqual(len(markets),1)
        self.assertEqual(self.w.status['state'],'complete');self.assertEqual(self.w.performance_status['week'],1)
    def test_refresh_scores_official_result_without_resetting_baseline(self):
        self.run_refresh();self.clock.value=AFTER;self.g=game(True)
        report=self.run_refresh();self.assertEqual(report['paired_games'],1)
        self.assertTrue(report['frozen']);self.assertIn('1 results scored',self.w.performance_status['message'])
    def test_explicit_week_and_retry_validation(self):
        for changes in ({'performance_week':None},{'performance_week':True},{'performance_week':19},{'retry_missing':'yes'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.w.generate(self.payload()|changes)
        self.assertFalse(self.w.lock.locked())
    def test_failure_does_not_abort_bet_sheet(self):
        with patch.object(self.w,'capture_performance',side_effect=ValueError('corrupt comparison store')):
            self.run_refresh()
        self.assertEqual(self.w.status['state'],'complete')
        self.assertEqual(self.w.performance_status['state'],'attention')
        self.assertIn('corrupt comparison store',self.w.catalog()['performance']['message'])
    def test_missing_price_retry_is_explicit(self):
        self.transport.fail=True;self.run_refresh()
        self.transport.fail=False;self.clock.value='2026-09-09T18:00:00+00:00'
        self.assertIsNone(self.run_refresh()['games'][0]['kalshi'])
        self.assertTrue(self.run_refresh(retry=True)['games'][0]['kalshi']['retry'])
    def test_workflow_never_auto_initializes(self):
        with TemporaryDirectory() as tmp:
            w=app.Workflow(tmp)
            self.assertFalse(w.catalog()['performance']['enabled'])
            self.assertFalse((w.data/'performance').exists())
    def test_controls_and_request_fields_present(self):
        html=Path(app.__file__).with_suffix('.html').read_text()
        self.assertIn('Model comparison week',html);self.assertIn('Retry missing comparison prices',html)
        self.assertIn('Automatic — next eligible week',html)
        self.assertIn('<summary>Advanced options</summary>',html)

if __name__=='__main__':unittest.main()


class AutomaticWeekTests(unittest.TestCase):
    def test_ordered_selection_and_unknown_does_not_skip(self):
        from unittest.mock import Mock
        with TemporaryDirectory() as tmp:
            w=app.Workflow(tmp);e=Mock()
            e.report.side_effect=[dict(cutoff='known',frozen=True),dict(cutoff='known',frozen=False)]
            self.assertEqual(w.automatic_comparison_week(e,2026,[1,2]),2)
            self.assertEqual(e.observe_results.call_args_list[0].args,(2026,1))
            self.assertEqual(e.observe_results.call_args_list[1].args,(2026,2))
            e.reset_mock();e.report.side_effect=[dict(cutoff=None,frozen=False)]
            with self.assertRaisesRegex(ValueError,'dates are unresolved'):w.automatic_comparison_week(e,2026,[1,2])
            self.assertEqual(e.observe_results.call_count,1)
    def test_missing_workbook_target_does_not_skip(self):
        from unittest.mock import Mock
        with TemporaryDirectory() as tmp:
            w=app.Workflow(tmp);e=Mock();e.report.return_value=dict(cutoff='known',frozen=False)
            with self.assertRaisesRegex(ValueError,'absent'):w.automatic_comparison_week(e,2026,[2])
            self.assertEqual(e.observe_results.call_count,1)
    def test_end_of_season_has_no_new_baseline(self):
        from unittest.mock import Mock
        with TemporaryDirectory() as tmp:
            w=app.Workflow(tmp);e=Mock();e.report.return_value=dict(cutoff='known',frozen=True)
            self.assertIsNone(w.automatic_comparison_week(e,2026,list(range(1,19))))
            self.assertEqual(e.observe_results.call_count,18)
