"""Presentation must not repair evidence or confuse requested/selected forecasts."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest

from performance_reader import WEEK2_2026_FORECAST, week2_2026_limitation
from tests import test_performance_reader as reader_fixture
from tests import test_nfl_performance_workflow as workflow_fixture
from tests.test_nfl_performance import book, AFTER


class IncidentPresentationTests(unittest.TestCase):
    setUp= reader_fixture.NFLReaderTests.setUp
    save= reader_fixture.NFLReaderTests.save
    def test_incident_identity_and_sensitivity_leave_original_untouched(self):
        self.fixture.refresh(); self.fixture.finish(); original=self.save()
        affected=deepcopy(original)
        affected.update(week=2)
        affected['selected_forecast']['semantic']=WEEK2_2026_FORECAST
        for g in affected['games']:g['game_id']+='week2'
        unaffected=deepcopy(original)
        before=deepcopy([affected,unaffected])
        body=self.reader._cumulative([affected,unaffected],affected['games']+unaffected['games'])
        self.assertIn('September 17 workbook failed',body)
        self.assertIn('1 scored games omitted; 1 scored games remain',body)
        self.assertIn('does not replace the cumulative result',body)
        self.assertEqual([affected,unaffected],before)
        self.assertIn('No scored games remain',self.reader._cumulative([affected],affected['games']))
        self.assertIn('September 17 workbook failed',self.reader._weekly_evidence(affected))
        for field,value in [('week',3),('season',2027)]:
            other=deepcopy(affected);other[field]=value
            self.assertFalse(week2_2026_limitation(other))
        other=deepcopy(affected);other['selected_forecast']['semantic']='other'
        self.assertFalse(week2_2026_limitation(other))
        self.assertNotIn('Sensitivity:',self.reader._cumulative([other],other['games']))

    def test_incident_render_does_not_mutate_download_or_evidence(self):
        self.fixture.refresh();self.fixture.finish();r=self.save()
        before=reader_fixture.inventory(self.root)
        # Exercise rendering under the incident predicate without changing saved bytes.
        with patch('performance_reader.week2_2026_limitation',return_value=True),patch('requests.get',side_effect=AssertionError('network')):
            body=self.reader.render({})
            self.assertIn(b'September 17 workbook failed',body)
            raw=self.reader.download(r['report_id'])
        self.assertEqual(raw,(self.root/'reports'/(r['report_id']+'.json')).read_bytes())
        self.assertEqual(before,reader_fixture.inventory(self.root))


class BaselineCheckTests(unittest.TestCase):
    setUp= workflow_fixture.IntegrationTests.setUp
    payload= workflow_fixture.IntegrationTests.payload
    run_refresh= workflow_fixture.IntegrationTests.run_refresh
    def test_complete_check_identifies_requested_forecast_and_time(self):
        self.run_refresh()
        status=self.w.performance_status
        self.assertEqual(status['state'],'complete')
        for label in ('Weekly baseline check','Selected workbook: forecast.xlsx','Requested workbook matches',
                      'Forecast published:', 'Imported:', 'Weekly cutoff:', 'Checked:'):
            self.assertIn(label,status['message'])

    def test_rejected_workbook_clears_previous_success_without_changing_baseline(self):
        r=self.run_refresh();selected=r['selected_import']
        (self.w.inbox/'forecast.xlsx').write_bytes(book(pub='Vendor omitted publication time'))
        self.run_refresh()
        self.assertEqual(self.w.performance_status['state'],'attention')
        self.assertIn('Weekly baseline check failed',self.w.performance_status['message'])
        self.assertNotIn('Requested workbook matches',self.w.performance_status['message'])
        self.assertEqual(self.engine.report(2026,1,self.clock())['selected_import'],selected)

    def test_preflight_rejection_clears_success_preserves_evidence_and_recovers(self):
        for rejection in ('changed', 'missing'):
            with self.subTest(rejection=rejection):
                self.run_refresh()
                payload=self.payload()
                workbook=self.w.inbox/'forecast.xlsx'
                original=workbook.read_bytes()
                payload['forecast']['fingerprint']=workflow_fixture.app.source.digest(original)
                before=reader_fixture.inventory(self.w.data)
                if rejection=='changed':workbook.write_bytes(original+b'changed')
                else:workbook.unlink()
                with self.assertRaises((ValueError, OSError)):
                    self.w.generate(payload)
                self.assertFalse(self.w.lock.locked())
                self.assertEqual(before,reader_fixture.inventory(self.w.data))
                status=self.w.catalog()['performance']
                self.assertEqual(status['state'],'attention')
                self.assertIn('This request did not confirm',status['message'])
                self.assertNotIn('Requested workbook matches',status['message'])
                workbook.write_bytes(original)
                self.run_refresh()
                self.assertEqual(self.w.performance_status['state'],'complete')

    def test_busy_rejection_preserves_running_check_and_lock(self):
        self.run_refresh()
        self.w.performance_status=dict(state='running',message='Checking the active request')
        before=deepcopy(self.w.performance_status)
        self.w.lock.acquire()
        try:
            with self.assertRaisesRegex(ValueError,'already running'):
                self.w.generate(self.payload())
            self.assertEqual(self.w.performance_status,before)
            self.assertTrue(self.w.lock.locked())
        finally:self.w.lock.release()

    def test_inactive_preflight_does_not_create_baseline_check(self):
        before=deepcopy(self.w.performance_status)
        with patch.object(self.w,'performance_config',return_value={'enabled':False}):
            with self.assertRaises(ValueError):self.w.generate({'forecast':None})
        self.assertEqual(self.w.performance_status,before)
        self.assertFalse(self.w.lock.locked())

    def test_late_new_forecast_cannot_receive_success_for_older_frozen_baseline(self):
        r=self.run_refresh();selected=r['selected_import'];self.clock.value=AFTER
        (self.w.inbox/'forecast.xlsx').write_bytes(book(.59,'Updated September 9, 2026 at 12:00 PM EDT'))
        report=self.run_refresh()
        self.assertEqual(report['selected_import'],selected)
        self.assertEqual(self.w.performance_status['state'],'attention')
        self.assertIn('NOT the selected weekly forecast',self.w.performance_status['message'])

    def test_excluded_quote_is_not_a_complete_usable_capture(self):
        self.run_refresh();report=self.engine.report(2026,1,self.clock())
        report['games'][0]['state']='excluded'
        with patch.object(self.engine,'save_report',return_value=report),patch('nfl_refresh.kalshi.utc',self.clock):
            self.w.performance_summary(self.engine,2026,1)
        self.assertEqual(self.w.performance_status['state'],'attention')
        self.assertIn('0 of 1 games',self.w.performance_status['message'])


if __name__=='__main__':unittest.main()
