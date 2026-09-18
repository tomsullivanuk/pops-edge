"""Saved reader semantics, integrity, safe serving and inert HTTP behavior."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from http.server import ThreadingHTTPServer
import threading
import requests
import nfl_forecast_import as base
import nfl_refresh
from performance_reader import NFLReader, MLBReader, safe_path, READER_ERRORS, reference_comparison
from tests import test_nfl_performance as nfl_fixture
from tests import test_forecast_reporting_delivery as mlb_fixture


def inventory(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


class NFLReaderTests(unittest.TestCase):
    def setUp(self):
        self.fixture=nfl_fixture.PerformanceTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=Path(self.fixture.tmp.name);self.reader=NFLReader(self.root)
    def save(self):
        return self.fixture.engine.save_report(2026,1,self.fixture.clock())
    def test_frozen_scores_replay_and_read_only_render(self):
        self.fixture.refresh();self.fixture.finish();r=self.save();before=inventory(self.root)
        with patch('requests.get',side_effect=AssertionError('provider request')):
            html=self.reader.render({'season':['2026'],'week':['1']}).decode()
            self.assertIn('Payout-adjusted Brier score',html);self.assertIn('ELWAY score',html);self.assertIn('1 scored pairs',html);self.assertIn('0.37',html);self.assertIn('0.31',html)
            self.assertNotIn('Unavailable.</p><a download',html)
            self.assertEqual(json.loads(self.reader.download(r['report_id'])),r)
            self.assertIn('Market matching correction: nfl-market-aliases-v2',html)
            self.assertIn(r['legacy_interpretation_id'],html)
        self.assertEqual(before,inventory(self.root))
    def test_match_cells_omit_evaluation_labels_but_details_preserve_them(self):
        import re
        self.fixture.refresh();self.save()
        body=self.reader.render({}).decode()
        match=re.search(r'<tr><td>(.*?)</td>',body).group(1)
        self.assertNotIn('unresolved',match.lower())
        self.assertNotIn('awaiting',match.lower())
        self.assertIn('<dt>Evaluation status</dt><dd>awaiting baseline freeze</dd>',body)
        self.assertIn('<dt>Result</dt><dd>Unresolved result</dd>',body)
        self.fixture.finish();self.save()
        body=self.reader.render({}).decode()
        match=re.search(r'<tr><td>(.*?)</td>',body).group(1)
        self.assertIn('Final:',match);self.assertNotIn('scored',match)
        self.assertIn('<dt>Evaluation status</dt><dd>scored</dd>',body)

    def test_empty_and_no_scored_pair(self):
        self.assertIn(b'No saved weekly reports',self.reader.render({}))
        self.fixture.refresh();self.save();body=self.reader.render({})
        self.assertIn(b'No scored comparison',body);self.assertIn(b'Unavailable',body)
    def test_boundary_not_mtime_and_preserved_correction(self):
        self.fixture.refresh();self.fixture.finish();old=self.save()
        self.fixture.clock.value='2026-09-11T04:00:00+00:00';self.fixture.finish(score=30)
        # finish resets fixture clock; advance it for a later saved boundary.
        self.fixture.clock.value='2026-09-11T04:00:00+00:00';new=self.save()
        os.utime(self.root/'reports'/(old['report_id']+'.json'),(2000000000,2000000000))
        self.assertEqual(self.reader.selected(2026,1)['report_id'],new['report_id'])
        self.assertEqual(json.loads(self.reader.download(old['report_id'])),old)
    def test_tampering_does_not_fall_back(self):
        self.fixture.refresh();self.fixture.finish();r=self.save()
        p=self.root/'reports'/(r['report_id']+'.json');r['means']['elway_error']='0';p.write_text(json.dumps(r))
        self.assertIn(b'digest is invalid',self.reader.render({}))
    def test_same_boundary_conflict_visible(self):
        self.fixture.refresh();self.fixture.finish();r=self.save()
        r['selection_issue']='conflicting fixture'
        r['report_id']=base.digest(base.encode({k:v for k,v in r.items() if k!='report_id'}))
        (self.root/'reports'/(r['report_id']+'.json')).write_bytes(base.encode(r))
        self.assertIn(b'Conflicting saved reports',self.reader.render({}))
    def test_symlink_and_traversal_rejected(self):
        self.fixture.refresh();self.fixture.finish();r=self.save()
        path=self.root/'reports'/(r['report_id']+'.json');copy=self.root/'copy';copy.write_bytes(path.read_bytes());path.unlink();path.symlink_to(copy)
        self.assertIn(b'Aliased',self.reader.render({}))
        with self.assertRaises(ValueError):safe_path(self.root,'../secret')
    def test_fixed_starting_cohort_is_visible_without_scores(self):
        from tests import test_nfl_starting_cohort as cohort
        fixture=cohort.StartingCohortTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        engine=fixture.initialize();engine.save_report(2026,1,cohort.AT)
        body=NFLReader(engine.root).render({})
        self.assertIn(b'14 enrolled of 16 official games',body)
        self.assertIn(b'2 outside starting cohort',body)
        self.assertIn(b'0 scored pairs',body)

    def test_query_does_not_accept_paths_or_multiple_values(self):
        for query in ({'path':['/etc/passwd']},{'week':['1','2']}):
            self.assertIn(b'Select one season',self.reader.render(query))


class MLBReaderTests(unittest.TestCase):
    def setUp(self):
        self.fixture=mlb_fixture.DeliveryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.ref=self.fixture.generate();self.root=self.fixture.output;self.reader=MLBReader(self.root)
    def test_existing_reader_and_links_are_read_only(self):
        before=inventory(self.root)
        with patch('requests.get',side_effect=AssertionError('network')):
            assets,state=self.reader.assets();self.assertIn('entry.html',assets)
            self.assertIn(self.ref['package_id'],assets['entry.html'].decode())
            for name in assets:
                raw,kind=self.reader.asset(name);self.assertEqual(raw,assets[name])
        self.assertEqual(before,inventory(self.root))
    def test_unreferenced_and_escaped_assets_not_served(self):
        (self.root/'secret.json').write_text('private')
        for name in ('secret.json','../secret.json','%2e%2e/secret.json','anchors/unknown.json'):
            with self.assertRaises(ValueError):self.reader.asset(name)
    def test_damaged_selected_package_visible(self):
        path=self.root/'packages'/self.ref['package_id']/'analysis.json';path.chmod(0o644);path.write_text('{}')
        self.assertIn(b'unavailable',self.reader.render())
        with self.assertRaises(READER_ERRORS):self.reader.asset('entry.html')
    def test_symlink_selected_package_rejected(self):
        folder=self.root/'packages'/self.ref['package_id'];new=self.root/'relocated';folder.chmod(0o755);folder.rename(new);folder.symlink_to(new,target_is_directory=True)
        self.assertIn(b'Aliased',self.reader.render())


class ReaderHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),nfl_refresh.handler(nfl_refresh.Workflow(self.root),'test',self.root/'mlb-reports'))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def test_navigation_missing_roots_and_no_writes(self):
        before=inventory(self.root)
        for sport,bet in [('nfl','/'),('mlb','/mlb')]:
            html=requests.get(self.url+bet).text
            self.assertIn('href="/performance/'+sport+'"',html);self.assertNotIn('__PRODUCT_NAV__',html)
            page=requests.get(self.url+'/performance/'+sport)
            self.assertEqual(page.status_code,200);self.assertIn('unavailable' if sport=='mlb' else 'No saved',page.text)
        self.assertEqual(inventory(self.root),before)
        self.assertFalse((self.root/'Data/NFL/performance').exists())
        self.assertEqual(requests.get(self.url+'/performance/nfl',headers={'Host':'evil.test'}).status_code,403)
        self.assertEqual(requests.get(self.url+'/performance/mlb/saved/secret.json').status_code,404)


class ReferenceComparisonTests(unittest.TestCase):
    def test_same_population_wins_ties_and_empty(self):
        from decimal import Decimal
        report={'games':[{'state':'scored','outcome':{'payout':'1'}},
                         {'state':'scored','outcome':{'payout':'0'}},
                         {'state':'unresolved-outcome','outcome':None}],
                'paired_games':2,'means':{'elway_error':'0.20','kalshi_error':'0.30'}}
        self.assertEqual(reference_comparison(report),(Decimal('.25'),Decimal('.05'),Decimal('-.05')))
        report['games'][1]['outcome']['payout']='0.5'
        self.assertEqual(reference_comparison(report)[0],Decimal('.125'))
        report['games']=[];report['paired_games']=0
        self.assertEqual(reference_comparison(report),(None,None,None))
    def test_mismatched_count_is_rejected(self):
        with self.assertRaises(ValueError):
            reference_comparison({'games':[],'paired_games':1})
