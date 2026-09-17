"""Manual update boundary tests, isolated archives and outputs only."""
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import forecast_reporting_delivery as delivery
import mlb_performance_update as update
import tests.test_forecast_reporting_delivery as fixtures
from tests.reporting_fixtures import event_sources,archive_events
from mlb_performance_matches import prepare
from performance_reader import MLBReader


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.DeliveryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.output
        self.old=self.fixture.generate();prepare(self.root,self.fixture.archive.root,self.root/'matches')
        self.controller=update.UpdateController(self.root)
        self.attempt='a'*32;target=self.controller.path(self.attempt);target.mkdir(parents=True)
        update.write(target/'attempt.json',dict(status='running',attempt_id=self.attempt,started_at=update.now()))
        self.config=dict(reports=str(self.root),revision=fixtures.REVISION,archive_config='fixture',operational_state=str(self.fixture.root/'logs/operational-state'))

    def run_worker(self):
        generate=delivery.generate_report
        def synthetic(**kw):
            kw.update(clock=self.fixture.clock,synthetic_validation=True)
            return generate(**kw)
        with patch.object(update,'now',side_effect=lambda:self.fixture.clock().isoformat()),patch.object(delivery,'_revision',return_value=fixtures.REVISION),patch('forecast_standalone_operations.DeploymentConfig.from_json',return_value=self.fixture.archive.config),patch.object(delivery,'generate_report',side_effect=synthetic),patch('socket.socket',side_effect=AssertionError('no acquisition')):
            return update.run(self.config,self.attempt)

    def test_success_selects_complete_rows_and_keeps_archive_and_old_package(self):
        before=self.fixture.inventory(self.fixture.archive.root);old=self.fixture.inventory(self.root/'packages'/self.old['package_id'])
        self.assertEqual(self.run_worker(),0)
        state=self.controller.status();self.assertEqual(state['status'],'succeeded')
        self.assertEqual(state['collection_availability'],'unavailable')
        ref=delivery.read_entry(self.root)['live'];self.assertNotEqual(ref,self.old)
        self.assertTrue((self.root/'matches'/(ref['package_id']+'.json')).exists())
        self.assertIn('No additional scored results',state['message'])
        self.assertIn(b'1 of 1 opportunities shown',MLBReader(self.root).render(updates=self.controller))
        self.assertEqual(before,self.fixture.inventory(self.fixture.archive.root));self.assertEqual(old,self.fixture.inventory(self.root/'packages'/self.old['package_id']))
        self.fixture.verify(self.old)

    def test_additional_evidence_adds_rows_without_filter_input(self):
        event=event_sources(design='prospective',name='new',start='2026-09-11T20:00:00-04:00',acquired='2026-09-10T12:00:00Z')[0]
        archive_events(self.fixture.archive,(event,),self.fixture.now)
        self.assertEqual(self.run_worker(),0)
        self.assertNotIn('No additional',self.controller.status()['message'])
        self.assertIn(b'2 of 2 opportunities shown',MLBReader(self.root).render())

    def test_match_failure_keeps_previous_selection_and_rows(self):
        with patch('mlb_performance_matches.prepare',side_effect=ValueError('match invalid')):
            self.assertEqual(self.run_worker(),1)
        self.assertEqual(delivery.read_entry(self.root)['live'],self.old)
        self.assertEqual(delivery.read_entry(self.root)['last_attempt']['status'],'failed')
        self.assertEqual(self.controller.status()['status'],'failed')
        self.assertIn(b'1 of 1 opportunities shown',MLBReader(self.root).render())

    def test_source_failure_keeps_previous_selection(self):
        with patch.object(delivery,'freeze_reporting_source',side_effect=ValueError('source invalid')):
            self.assertEqual(self.run_worker(),1)
        self.assertEqual(delivery.read_entry(self.root)['live'],self.old)
        self.assertEqual(self.controller.status()['status'],'failed')

    def test_status_exception_does_not_invalidate_new_science(self):
        with patch('forecast_reporting_collection.snapshot',side_effect=OSError('unavailable')):
            self.assertEqual(self.run_worker(),0)
        self.assertNotEqual(delivery.read_entry(self.root)['live'],self.old)
        state=self.controller.status();self.assertEqual(state['status'],'succeeded');self.assertIn('unavailable',state['collection_error'])

    def test_interrupted_and_busy_are_read_only(self):
        state=dict(status='running',attempt_id=self.attempt,started_at=update.now())
        update.write(self.controller.path('current.json'),state)
        lock=self.controller.path('writer.lock').open('a+b');self.addCleanup(lock.close)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=self.fixture.inventory(self.root)
        self.assertEqual(self.controller.status()['status'],'running')
        self.assertEqual(before,self.fixture.inventory(self.root))
        fcntl.flock(lock,fcntl.LOCK_UN)
        self.assertEqual(self.controller.status()['status'],'interrupted')
        self.assertEqual(before,self.fixture.inventory(self.root))

    def test_optional_collection_digest_damage_does_not_hide_report(self):
        self.assertEqual(self.run_worker(),0);state=self.controller.status()
        self.controller.path(self.attempt+'/collection.json').write_text('{}')
        with self.assertRaises(ValueError):self.controller.download(self.attempt)
        self.assertIn(b'Average Brier score',MLBReader(self.root).render(updates=self.controller))

    def test_new_report_can_start_without_historical_selection(self):
        self.assertIsNone(delivery.read_entry(self.root)['historical']);self.assertEqual(self.run_worker(),0)
        self.assertIsNone(delivery.read_entry(self.root)['historical'])

    def test_no_configuration_or_browser_body_can_choose_source(self):
        with self.assertRaisesRegex(ValueError,'not been configured'):self.controller.start()
        self.assertFalse(self.controller.status()['configured'])
        with self.assertRaises(ValueError):self.controller.download('../collection')

    def test_read_only_page_does_not_generate_or_prepare(self):
        before=self.fixture.inventory(self.root)
        with patch.object(delivery,'generate_report',side_effect=AssertionError('GET generates')),patch('mlb_performance_matches.prepare',side_effect=AssertionError('GET prepares')):
            raw=MLBReader(self.root).render({'period':['7']},updates=self.controller,token='test-token')
            self.assertIn(b'Update report',raw)
        self.assertEqual(before,self.fixture.inventory(self.root))

    def test_historical_selection_and_bytes_survive_complete_workflow(self):
        historical=self.fixture.generate('historical')
        delivery.select_historical(output=self.root,package_id=historical['package_id'],anchor_key=historical['anchor_key'],archive=self.fixture.archive,clock=self.fixture.clock)
        before=self.fixture.inventory(self.root/'packages'/historical['package_id'])
        self.assertEqual(self.run_worker(),0)
        self.assertEqual(delivery.read_entry(self.root)['historical'],historical)
        self.assertEqual(before,self.fixture.inventory(self.root/'packages'/historical['package_id']))

    def test_match_preparation_runs_before_selected_reference_changes(self):
        selected=[]
        def checked(*args,**kw):
            selected.append(delivery.read_entry(self.root)['live'])
            self.assertNotEqual(kw['reference'],self.old)
            return prepare(*args,**kw)
        with patch('mlb_performance_matches.prepare',side_effect=checked):
            self.assertEqual(self.run_worker(),0)
        self.assertEqual(selected,[self.old])

    def test_valid_unscored_report_remains_distinct_from_failure(self):
        from dataclasses import replace
        from forecast_standalone_operations import NamespaceArchive
        self.fixture.archive=NamespaceArchive(replace(self.fixture.archive.config,primary_root=self.fixture.root/'empty/dry-run/delivery/primary',secondary_root=self.fixture.root/'empty/dry-run/delivery/secondary'))
        event=event_sources(design='prospective',name='awaiting',start='2026-09-12T20:00:00-04:00',acquired='2026-09-11T12:00:00Z',final=False)[0]
        archive_events(self.fixture.archive,(event,),self.fixture.now)
        self.assertEqual(self.run_worker(),0)
        self.assertEqual(self.controller.status()['status'],'succeeded')
        self.assertIn(b'No scored results are available',MLBReader(self.root).render())

    def test_malformed_attempt_is_visible_without_page_failure(self):
        for value in ([], {'status':'unknown'}, {'status':'running','attempt_id':'invalid'}):
            update.write(self.controller.path('current.json'),value)
            self.assertEqual(self.controller.status()['status'],'unavailable')
            self.assertIn(b'Saved update status unavailable',MLBReader(self.root).render(updates=self.controller))


class UpdateHTTPTests(unittest.TestCase):
    def test_request_authority_empty_body_and_read_only_status(self):
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import nfl_refresh
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            server=ThreadingHTTPServer(('127.0.0.1',0),nfl_refresh.handler(nfl_refresh.Workflow(root),'secret',root/'reports'))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url='http://127.0.0.1:'+str(server.server_port)
                headers={'Origin':url,'X-Pops-Token':'secret','Content-Type':'application/json'}
                with patch.object(update.UpdateController,'start',return_value={'status':'running','message':'Updating'}) as start:
                    self.assertEqual(requests.get(url+'/api/mlb/performance/update').status_code,200)
                    self.assertIn('Update report',requests.get(url+'/performance/mlb').text)
                    self.assertEqual(requests.post(url+'/api/mlb/performance/update',json={}).status_code,403)
                    self.assertEqual(requests.post(url+'/api/mlb/performance/update',json={},headers={**headers,'Origin':'http://evil.test'}).status_code,403)
                    self.assertEqual(requests.post(url+'/api/mlb/performance/update',json={'from':'2026-09-01'},headers=headers).status_code,400)
                    start.assert_not_called()
                    self.assertEqual(requests.post(url+'/api/mlb/performance/update',json={},headers=headers).status_code,202)
                    start.assert_called_once_with()
                self.assertFalse((root/'reports').exists())
            finally:server.shutdown();server.server_close();thread.join()


class ControllerTests(unittest.TestCase):
    def test_pinned_configuration_rejects_revision_dirty_paths_and_wrong_logs(self):
        fixture=fixtures.DeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        path=fixture.root/'worker-config.json';checkout=Path(update.__file__).parent.resolve()
        config=dict(checkout=str(checkout),revision='a'*40,python='/usr/bin/python3',archive_config='/tmp/archive-config',reports=str(fixture.output),operational_state=str(fixture.archive.config.log_root/'operational-state'))
        update.write(path,config)
        with patch('forecast_standalone_operations.DeploymentConfig.from_json',return_value=fixture.archive.config):
            with patch.object(update.subprocess,'check_output',side_effect=['b'*40,'']):
                with self.assertRaisesRegex(ValueError,'pinned revision'):update.configured(path,fixture.output)
            with patch.object(update.subprocess,'check_output',side_effect=['a'*40,' M dirty']):
                with self.assertRaisesRegex(ValueError,'pinned revision'):update.configured(path,fixture.output)
            with patch.object(update.subprocess,'check_output',side_effect=['a'*40,'']):
                self.assertEqual(update.configured(path,fixture.output),config)
            update.write(path,{**config,'operational_state':'/tmp/wrong-log'})
            with patch.object(update.subprocess,'check_output',side_effect=['a'*40,'']):
                with self.assertRaisesRegex(ValueError,'this archive'):update.configured(path,fixture.output)
            update.write(path,{**config,'reports':str(fixture.archive.root)})
            with patch.object(update.subprocess,'check_output',side_effect=['a'*40,'']):
                with self.assertRaises(Exception):update.configured(path,fixture.archive.root)

    def test_spawn_failure_is_persisted_and_can_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);controller=update.UpdateController(root/'reports',root/'config.json')
            config=dict(checkout=str(root),revision='a'*40,python='/missing/python')
            with patch.object(update,'configured',return_value=config),patch.object(update.subprocess,'Popen',side_effect=OSError('could not start')):
                for _ in range(2):
                    with self.assertRaises(OSError):controller.start()
                    self.assertEqual(controller.status()['status'],'failed')
            self.assertEqual(len(list((root/'reports/updates').glob('*/attempt.json'))),2)

    def test_real_subprocess_holds_lock_across_controller_reload(self):
        import sys,time
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);reports=root/'reports'
            script=root/'mlb_performance_update.py'
            script.write_text('''import sys,json,time,os\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index('--run')+1]).parent\ns=json.loads((p/'attempt.json').read_text())\nfor _ in range(100):\n if (p/'release').exists():break\n time.sleep(.05)\ns['status']='succeeded'\nfor q in [p/'attempt.json',p.parent/'current.json']:\n t=q.with_suffix('.tmp');t.write_text(json.dumps(s));os.replace(t,q)\n''')
            config=dict(checkout=str(root),revision='a'*40,python=sys.executable)
            controller=update.UpdateController(reports,root/'config')
            with patch.object(update,'configured',return_value=config):
                state=controller.start();reloaded=update.UpdateController(reports,root/'config')
                self.assertEqual(reloaded.status()['status'],'running')
                with self.assertRaisesRegex(ValueError,'already running'):reloaded.start()
                (reports/'updates'/state['attempt_id']/'release').touch()
                for _ in range(100):
                    if reloaded.status()['status']=='succeeded':break
                    time.sleep(.05)
                self.assertEqual(reloaded.status()['status'],'succeeded')
