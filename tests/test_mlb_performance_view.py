"""Reader-only presentation, frozen match mapping, filters and integrity boundaries."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from performance_reader import MLBReader
from mlb_performance_matches import prepare, validate, VERSION, index_contracts
from mlb_performance_view import filtered
from forecast_standalone_operations import canonical_bytes, sha256_bytes
from tests import test_forecast_reporting_delivery as delivery_fixture
from tests.reporting_fixtures import event_sources, archive_events


class Filters(unittest.TestCase):
    def setUp(self):
        self.cutoff=datetime.fromisoformat('2026-09-14T01:10:00+00:00')
        self.rows=[dict(start=s,home='a',away='b') for s in ['2026-09-07T04:59:00+00:00','2026-09-07T05:00:00+00:00','2026-09-14T04:59:00+00:00','2026-09-14T05:00:00+00:00']]
    def test_calendar_bounds_and_future_known_opportunities(self):
        self.assertEqual(filtered(self.rows,{'period':['7']},self.cutoff),self.rows[1:3])
        self.assertEqual(filtered(self.rows,{'period':['season']},self.cutoff),self.rows)
        self.assertEqual(filtered(self.rows,{'period':['custom'],'from':['2026-09-07'],'to':['2026-09-07']},self.cutoff),self.rows[1:2])
        for n in ('14','60','90'):
            self.assertEqual(filtered(self.rows,{'period':[n]},self.cutoff),self.rows[:3])
    def test_invalid_dates_filters_and_empty_result(self):
        bad=[{'period':['custom'],'from':['2026-09-13'],'to':['2026-09-12']},
             {'period':['custom'],'from':[''],'to':['2026-09-12']},
             {'period':['custom'],'from':['2026-09-13'],'to':['2026-09-14']},
             {'period':['1']},{'period':['7','14']},{'team':['unknown']},{'path':['secret']}]
        for q in bad:
            with self.subTest(q=q),self.assertRaises(ValueError):filtered(self.rows,q,self.cutoff)
        self.assertEqual(filtered(self.rows,{'period':['custom'],'from':['2026-09-08'],'to':['2026-09-08']},self.cutoff),[])


class MatchReader(unittest.TestCase):
    def setUp(self):
        self.fixture=delivery_fixture.DeliveryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.ref=self.fixture.generate();self.root=self.fixture.output
    def payloads(self):
        a=json.loads(self.fixture.payload(self.ref,'analysis.json'))
        p=json.loads(self.fixture.payload(self.ref,'projections.json'))['scopes'][0]
        return a,p
    def test_preparation_render_and_download_are_inert(self):
        before=self.fixture.inventory(self.fixture.archive.root)
        selected=(self.root/'entry.html').read_bytes()
        with patch('socket.socket',side_effect=AssertionError('no network')):
            path=prepare(self.root,self.fixture.archive.root,self.root/'matches')
            self.assertEqual(prepare(self.root,self.fixture.archive.root,self.root/'matches'),path)
            snap=self.fixture.inventory(self.root)
            page=MLBReader(self.root).render().decode()
            self.assertIn('Average Brier score',page);self.assertIn('1 of 1 opportunities shown',page)
            self.assertNotIn('<iframe',page);self.assertIn('Illustrative example',page)
            self.assertIn('From',MLBReader(self.root).render({'period':['custom']}).decode())
            self.assertEqual(self.fixture.inventory(self.root),snap)
        self.assertEqual(before,self.fixture.inventory(self.fixture.archive.root))
        self.assertEqual(selected,(self.root/'entry.html').read_bytes())
    def test_missing_and_corrupt_match_display_preserve_summary(self):
        reader=MLBReader(self.root)
        self.assertIn(b'Match details have not been prepared',reader.render())
        path=prepare(self.root,self.fixture.archive.root,self.root/'matches')
        value=json.loads(path.read_text());value['rows'][0]['score']='0'
        path.write_text(json.dumps(value))
        page=reader.render();self.assertIn(b'Saved match details unavailable',page);self.assertIn(b'Average Brier score',page)
        value['digest']=sha256_bytes(canonical_bytes({k:v for k,v in value.items() if k!='digest'}))
        a,p=self.payloads()
        with self.assertRaises(ValueError):validate(value,self.ref['package_id'],a,p)
    def test_population_missing_duplicate_wrong_package_and_symlink(self):
        path=prepare(self.root,self.fixture.archive.root,self.root/'matches');original=json.loads(path.read_text());a,p=self.payloads()
        for mutate in (lambda v:v['rows'].clear(),lambda v:v['rows'].append(v['rows'][0]),lambda v:v.update(package_id='f'*64)):
            v=copy.deepcopy(original);mutate(v);v['digest']=sha256_bytes(canonical_bytes({k:x for k,x in v.items() if k!='digest'}))
            with self.assertRaises(ValueError):validate(v,self.ref['package_id'],a,p)
        path.unlink();path.symlink_to(self.root/'entry.html')
        self.assertIn(b'Saved match details unavailable',MLBReader(self.root).render())
    def test_complete_population_includes_missing_unresolved_and_future(self):
        events=[]
        for name,kw in [('future',dict(final=False,capture=False,start='2026-09-13T20:00:00-04:00')),('awaiting',dict(final=False,start='2026-09-12T20:00:00-04:00')),('missed',dict(missed=True,start='2026-09-10T20:00:00-04:00'))]:
            events.append(event_sources(design='prospective',name=name,acquired='2026-09-09T12:00:00Z',**kw)[0])
        archive_events(self.fixture.archive,events,self.fixture.now)
        self.ref=self.fixture.generate()
        path=prepare(self.root,self.fixture.archive.root,self.root/'matches');payload=json.loads(path.read_text())
        self.assertEqual(len(payload['rows']),4)
        self.assertEqual(sum(r['score'] is not None for r in payload['rows']),1)
        page=MLBReader(self.root).render().decode();self.assertIn('4 of 4 opportunities shown',page)
        self.assertIn('Unavailable',page)
        value=copy.deepcopy(payload);r=next(r for r in value['rows'] if r['score'] is None);r['home_score']=9
        value['digest']=sha256_bytes(canonical_bytes({k:v for k,v in value.items() if k!='digest'}))
        a,p=self.payloads()
        with self.assertRaises(ValueError):validate(value,self.ref['package_id'],a,p)
    def test_conflicting_dependency_rejected(self):
        c={'__type__':'ResearchCaptureOpportunity','research_capture_opportunity_id':'a','schedule_observation_id':'b'}
        with self.assertRaises(ValueError):index_contracts([c,{**c,'schedule_observation_id':'c'}])
    def test_preparation_cannot_write_archive(self):
        with self.assertRaises(ValueError):prepare(self.root,self.fixture.archive.root,self.fixture.archive.root/'matches')
