from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

import nfl_excel_import as excel
import nfl_forecast_time as timing
import nfl_forecast_import as base
from nfl_performance import Performance
from tests.test_nfl_performance import Clock, Transport, book, game, BEFORE, AFTER
from tests.test_nfl_comparison_board import source

CREATED='2026-09-09T14:00:00+00:00'


def missing(home=.60):
    return book(home,'Updated time unavailable')


def observation(raw,created=CREATED,observed=BEFORE):
    return timing.evidence(raw,created,observed)


class FileTimeTests(unittest.TestCase):
    def test_explicit_missing_marker_uses_bound_birth_evidence(self):
        raw=missing();value=excel.parse(raw,observation(raw))
        self.assertEqual(value['updated_at'],CREATED)
        self.assertEqual(value['file_time']['rule'],timing.RULE)
        with self.assertRaises(ValueError):excel.parse(raw)

    def test_published_timestamp_has_precedence(self):
        raw=book();value=excel.parse(raw,observation(raw))
        self.assertNotIn('file_time',value)
        self.assertEqual(value['updated_at'],'2026-09-09T10:51:00-04:00')

    def test_bad_or_conflicting_source_time_not_repaired(self):
        for text in ('No update time','Updated September broken','Updated time unavailable\nUpdated September 9, 2026 at 10:51 AM EDT','Updated time unavailable\nUpdated time unavailable'):
            raw=book(pub=text)
            with self.subTest(text=text),self.assertRaises(ValueError):excel.parse(raw,observation(raw))

    def test_evidence_digest_rule_and_chronology(self):
        raw=missing()
        for field,value in [('source_sha256','0'*64),('rule_digest','0'*64),('created_at','2027-01-01T00:00:00+00:00'),('created_at','2026-09-09T14:00:00')]:
            evidence=observation(raw);evidence[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):excel.parse(raw,evidence)

    def test_prepare_preserves_receipt_and_first_birth_for_exact_copy(self):
        raw=missing()
        with TemporaryDirectory() as d,patch.object(base,'now',return_value=BEFORE):
            # Earlier rejected attempt remains intact; append time evidence separately.
            with self.assertRaises(ValueError):excel.prepare(raw,'original.xlsx',d)
            receipt=Path(d)/'sources'/base.digest(raw)/'receipt.json';before=receipt.read_bytes()
            c=excel.prepare(raw,'original.xlsx',d,observation(raw))
            path=excel.validate_automatically(c,1,d)
            record=json.loads(path.read_text());excel.validate_auto(record,raw,c['source'])
            again=excel.prepare(raw,'copy.xlsx',d,observation(raw,'2026-09-09T15:00:00+00:00'))
            self.assertEqual(c,again);self.assertEqual(receipt.read_bytes(),before)
            self.assertEqual(path,excel.validate_automatically(again,1,d))
            record['review']['file_time']['created_at']='2026-09-09T13:00:00+00:00'
            with self.assertRaises(ValueError):excel.validate_auto(record,raw,c['source'])

    def test_restart_season_view_keeps_proxy_label(self):
        from nfl_season_board import assemble,render
        with TemporaryDirectory() as d,patch.object(base,'now',return_value=BEFORE):
            raw=missing();excel.prepare(raw,'x.xlsx',Path(d)/'forecasts',observation(raw))
            result=assemble(d,[],now=BEFORE)
            self.assertEqual(result['forecast_time_basis'],timing.RULE)
            self.assertIn('publication-time proxy',result['games'][0]['source_note'])
            html=render(result)
            self.assertIn('publication-time proxy',html)
            self.assertNotIn('ELWAY updated:',html)

    def test_file_read_uses_birth_not_modification_or_ctime(self):
        from types import SimpleNamespace
        from datetime import datetime
        raw=missing()
        stat=SimpleNamespace(st_ino=1,st_size=len(raw),st_mtime_ns=99,st_ctime_ns=100,
                             st_birthtime=datetime.fromisoformat(CREATED).timestamp())
        with TemporaryDirectory() as d:
            path=Path(d)/'x.xlsx';path.write_bytes(raw)
            with patch.object(timing.os,'fstat',return_value=stat),patch.object(base,'now',return_value=BEFORE):
                actual,e=timing.read_file(path)
            self.assertEqual(actual,raw);self.assertEqual(e['created_at'],CREATED)
            del stat.st_birthtime
            with patch.object(timing.os,'fstat',return_value=stat):
                _,e=timing.read_file(path)
            self.assertIsNone(e)

    def test_refresh_ui_passes_original_file_observation_to_research(self):
        import nfl_refresh as app
        from tests.test_nfl_refresh import WorkflowTests
        with TemporaryDirectory() as d:
            workflow=app.Workflow(d);payload=WorkflowTests().inputs(workflow)
            raw=missing();e=observation(raw)
            (workflow.inbox/'elway.xlsx').write_bytes(raw)
            with patch.object(timing,'read_file',return_value=(raw,e)),patch.object(workflow,'performance_config',return_value={'enabled':True}),patch.object(app.threading,'Thread') as thread:
                workflow.generate(payload);args=thread.call_args.kwargs['args']
            with patch.object(app,'RefreshPerformance'),patch.object(workflow,'automatic_comparison_week',return_value=1),patch.object(workflow,'capture_performance',return_value=None) as capture,patch.object(app.schedule,'capture',side_effect=ValueError('offline test')):
                workflow.run(*args)
            self.assertEqual(capture.call_args.kwargs['file_time'],e)
            self.assertIn('publication-time proxy',workflow.status['message'])


class PerformanceFileTimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.clock=Clock();self.engine=Performance.initialize(self.tmp.name,'offline fixture',self.clock)
        self.market=Transport()

    def refresh(self,raw=None,created=CREATED,**kwargs):
        raw=raw or missing()
        return self.engine.refresh(raw,'x.xlsx',2026,1,file_time=observation(raw,created,self.clock()),
            schedule_transport=lambda _: (200,source([game()])),market_transport=self.market,**kwargs)

    def report(self):return self.engine.report(2026,1,self.clock())

    def test_proxy_capture_eligible_with_honest_times(self):
        self.refresh();r=self.report()
        self.assertEqual(r['games'][0]['state'],'candidate')
        self.assertEqual(r['selected_forecast']['time_basis'],timing.RULE)
        self.assertIsNone(r['selected_forecast']['published_at'])
        self.assertEqual(r['selected_imported_at'],BEFORE)
        self.assertEqual(r['games'][0]['kalshi']['received_at'],BEFORE)

    def test_performance_reader_labels_proxy_not_publication(self):
        from performance_reader import NFLReader
        self.refresh();self.engine.save_report(2026,1,self.clock())
        html=NFLReader(self.engine.root).render({}).decode()
        self.assertIn(timing.LABEL,html)
        self.assertIn('model age are unknown',html)
        self.assertNotIn('<dt>Forecast published</dt>',html)

    def test_pinned_rule_tamper_cannot_enter_baseline(self):
        raw=missing();e=observation(raw);e['rule_digest']='0'*64
        result=self.engine.refresh(raw,'x.xlsx',2026,1,file_time=e,market_transport=self.market)
        self.assertEqual(result['kind'],'rejected');self.assertEqual(self.market.calls,0)

    def test_copied_or_resaved_rows_never_reset_time_or_quotes(self):
        self.refresh();calls=self.market.calls;original=self.report()['selected_import']
        self.clock.value='2026-09-09T18:00:00+00:00'
        self.assertEqual(self.refresh(created='2026-09-09T17:00:00+00:00')['kind'],'duplicate')
        self.assertEqual(self.market.calls,calls)
        r=self.report();self.assertEqual(r['selected_import'],original)
        self.assertEqual(r['selected_forecast']['updated_at'],CREATED)

    def test_new_content_supersedes_but_old_copy_does_not(self):
        self.refresh();self.clock.value='2026-09-09T18:00:00+00:00'
        self.refresh(missing(.59),'2026-09-09T17:00:00+00:00');selected=self.report()['selected_import']
        self.clock.value='2026-09-09T20:00:00+00:00';calls=self.market.calls
        self.refresh(missing(),'2026-09-09T19:00:00+00:00')
        self.assertEqual(self.report()['selected_import'],selected);self.assertEqual(self.market.calls,calls)

    def test_same_time_conflicting_rows_remain_ambiguous(self):
        self.refresh();self.refresh(missing(.59))
        self.assertIsNone(self.report()['selected_import'])

    def test_after_cutoff_old_birth_does_not_enroll_or_capture(self):
        self.clock.value=AFTER;self.refresh()
        self.assertEqual(self.market.calls,0);self.assertIsNone(self.report()['selected_import'])

    def test_retry_fills_missing_with_actual_later_time(self):
        self.market.fail=True;self.refresh();self.market.fail=False
        self.clock.value='2026-09-09T18:00:00+00:00'
        self.refresh(created='2026-09-09T17:00:00+00:00',retry=True)
        r=self.report();self.assertEqual(r['selected_forecast']['updated_at'],CREATED)
        self.assertTrue(r['games'][0]['kalshi']['retry'])
        self.assertEqual(r['games'][0]['kalshi']['received_at'],self.clock())

    def test_old_rejected_import_and_saved_report_not_reinterpreted(self):
        raw=missing()
        event=self.engine.refresh(raw,'old.xlsx',2026,1)
        self.assertEqual(event['kind'],'rejected')
        saved=self.engine.save_report(2026,1,self.clock());before=deepcopy(saved)
        self.clock.value='2026-09-09T18:00:00+00:00';self.refresh()
        path=Path(self.tmp.name)/'reports'/(saved['report_id']+'.json')
        self.assertEqual(self.engine.replay_report(path),before)
        self.assertEqual(len(self.report()['diagnostics']),2)
        self.assertIn('Include heading, game count and published update time',self.report()['diagnostics'][0]['error'])

    def test_published_report_replay_unchanged_after_proxy_import(self):
        self.refresh(book());saved=self.engine.save_report(2026,1,self.clock())
        self.clock.value='2026-09-09T18:00:00+00:00';self.refresh(created='2026-09-09T17:00:00+00:00')
        path=Path(self.tmp.name)/'reports'/(saved['report_id']+'.json')
        self.assertEqual(self.engine.replay_report(path),saved)

    def test_future_observation_rejected_without_provider_calls(self):
        raw=missing();e=observation(raw,CREATED,'2026-09-09T18:00:00+00:00')
        result=self.engine.refresh(raw,'x.xlsx',2026,1,file_time=e,market_transport=self.market)
        self.assertEqual(result['kind'],'rejected');self.assertEqual(self.market.calls,0)
