"""Read-only operational display; no collection or new readiness engine."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_collection as collection
from forecast_standalone_activation import OperationalHeartbeat, OperationalState


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'state'; self.state = OperationalState(self.root)
        self.at = datetime(2026, 9, 14, 15, tzinfo=timezone.utc)

    def record(self, command='capture-prospective', age=0, disposition='success', failure=None):
        at = self.at-timedelta(seconds=age)
        self.state.append(OperationalHeartbeat('1',command,at,at,disposition,0,None,None,failure))

    def healthy(self):
        for name in ('capture-prospective','refresh-supporting','reconcile-outcomes',
                     'rebuild-prospective-projection','rebuild-index','sync-secondary','health-report'):
            self.record(name)

    def read(self):
        return collection.snapshot(self.root,self.at)

    def test_healthy_frozen_read_without_health_engine_or_writes(self):
        self.healthy(); before={p.name:p.read_bytes() for p in self.root.iterdir()}
        with patch('forecast_standalone_activation.health_from_operational_state',side_effect=AssertionError('no audit')), \
             patch.object(OperationalState,'append',side_effect=AssertionError('no heartbeat')), \
             patch('socket.socket',side_effect=AssertionError('no network')):
            result=self.read(); html=collection.render(result,'recovery.html','status.json')
        self.assertEqual(result['current_blockers'],[])
        self.assertEqual(len(result['last_valid_completions']),7)
        self.assertIn('No invocation blockers observed',html)
        self.assertIn('not been rechecked',html)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
        self.assertEqual(html,collection.render(result,'recovery.html','status.json'))

    def test_current_failure_and_later_success_preserve_history(self):
        self.healthy(); self.record(age=-1,disposition='failed',failure='projection-invalid')
        result=collection.snapshot(self.root,self.at+timedelta(seconds=2))
        self.assertIn('capture-prospective:projection-invalid',result['current_blockers'])
        self.record(age=-3)
        result=collection.snapshot(self.root,self.at+timedelta(seconds=4))
        self.assertNotIn('capture-prospective:projection-invalid',result['current_blockers'])
        self.assertIn('capture-prospective:projection-invalid',result['superseded_failures'])
        self.assertIn('superseded',collection.render(result,'r','s'))

    def test_cross_checkpoint_success_resolves_existing_blocker(self):
        self.healthy(); self.record('rebuild-prospective-projection',age=-1,disposition='failed',failure='projection-invalid')
        self.record('refresh-prospective-projection',age=-2)
        result=collection.snapshot(self.root,self.at+timedelta(seconds=3))
        self.assertNotIn('rebuild-prospective-projection:projection-invalid',result['current_blockers'])

    def test_skipped_hour_reuses_existing_supporting_grace(self):
        for name in ('capture-prospective','reconcile-outcomes','rebuild-prospective-projection','rebuild-index','sync-secondary'):
            self.record(name)
        self.record('refresh-supporting',age=5000)
        self.assertIn('refresh-supporting:stale-or-absent',self.read()['current_blockers'])
        self.record('lifecycle-hour',age=60,disposition='skipped-cycle')
        result=self.read()
        self.assertNotIn('refresh-supporting:stale-or-absent',result['current_blockers'])
        self.assertEqual(len(result['recent_skips']),1)
        self.assertNotIn('lifecycle-hour',dict(result['last_valid_completions']))
        self.assertIn('skipped cycle observations',collection.render(result,'r','s'))

    def test_elapsed_hour_skips_can_share_a_detection_time(self):
        self.healthy()
        for hours in (1,2,3):
            self.state.append(OperationalHeartbeat('1','lifecycle-hour',
                self.at-timedelta(hours=hours),self.at,'skipped-cycle',0,None,None,None))
        result=self.read()
        self.assertEqual(result['availability'],'available')
        self.assertEqual(len(result['recent_skips']),3)
        self.assertEqual(result['current_blockers'],[])

    def test_stale_dates_and_absent_records_are_honest(self):
        self.assertEqual(self.read()['availability'],'unavailable')
        self.healthy()
        result=collection.snapshot(self.root,self.at+timedelta(days=2))
        self.assertIn('capture-prospective:stale-or-absent',result['current_blockers'])
        self.assertIn('Stale or incomplete',collection.render(result,'r','s'))
        self.assertEqual(result['latest_record_at'],self.at.isoformat())

    def test_malformed_inaccessible_future_and_ambiguous_degrade_only_display(self):
        self.healthy(); bad=self.root/'bad.json';bad.write_text('{}')
        self.assertEqual(self.read()['availability'],'unavailable');bad.unlink()
        with patch.object(Path,'iterdir',side_effect=PermissionError('private detail')):
            result=self.read()
        self.assertEqual(result['reason'],'Operational records could not be read')
        self.assertNotIn('private detail',str(result))
        self.assertEqual(collection.snapshot(self.root,self.at-timedelta(seconds=1))['availability'],'unavailable')
        item=OperationalHeartbeat('1','capture-prospective',self.at-timedelta(seconds=1),self.at,'failed',0,None,None,'failure')
        self.state.append(item)
        self.assertEqual(self.read()['availability'],'unavailable')

    def test_malformed_health_disposition_cannot_break_report_rendering(self):
        self.healthy()
        self.record('health-report',age=-1,disposition=123)
        result=collection.snapshot(self.root,self.at+timedelta(seconds=2))
        self.assertEqual(result['availability'],'unavailable')
        self.assertIn('saved scientific report remains available',collection.render(result,'r','s'))

    def test_missing_status_and_html_are_safe_and_readable(self):
        result=collection.snapshot(None,self.at)
        html=collection.render(result,'r','s')
        self.assertIn('Collection status unavailable',html)
        self.assertIn('saved scientific report remains available',html)
        self.assertNotIn('<pre>',html)
        self.assertIn('Recovery'.lower(),collection.recovery_page().decode().lower())
