import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nfl_refresh import Workflow
from nfl_inbox import classify
from nfl_activity import REQUIRED
from nfl_accounting import PNL_FIELDS
from tests.test_nfl_refresh import workbook


def header(fields):
    return (','.join(sorted(fields))+'\n').encode()


class AutomaticInputsTests(unittest.TestCase):
    def put(self, workflow, name, raw, seconds):
        p=workflow.inbox/name
        p.write_bytes(raw)
        os.utime(p, ns=(seconds*10**9, seconds*10**9))
        return p

    def inputs(self,w):
        self.put(w,'Elway_old.xlsx',workbook(),100)
        self.put(w,'Elway_new.xlsx',workbook(),200)
        self.put(w,'renamed-activity.csv',header(REQUIRED),100)
        self.put(w,'renamed-pnl.csv',header(PNL_FIELDS),100)

    def test_csv_contents_distinguish_renamed_exports_and_unrelated_csv(self):
        self.assertEqual(classify('renamed.csv',header(REQUIRED)),('activity',None))
        self.assertEqual(classify('renamed.csv',header(PNL_FIELDS)),('pnl',None))
        self.assertIsNone(classify('fangraphs.csv',b'name,score\n')[0])
        self.assertIsNotNone(classify('Kalshi-Recent-Activity-All.csv',header(PNL_FIELDS))[1])

    def test_latest_is_saved_time_not_filename_and_scan_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w)
            self.put(w,'Elway_Week99.xlsx',workbook(),50)
            with patch('nfl_refresh.schedule.capture') as acquisition:
                s=w.catalog()
                acquisition.assert_not_called()
            self.assertEqual(s['latest_inputs']['forecast']['name'],'Elway_new.xlsx')
            self.assertTrue(all(item['state']=='ready' for item in s['latest_inputs'].values()))
            self.assertFalse((w.data/'refreshes').exists())

    def test_click_rescans_and_archives_exact_automatic_choice(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w);w.catalog()
            self.put(w,'just-downloaded.xlsx',workbook(),300)
            with patch('nfl_refresh.threading.Thread') as thread:
                w.generate_latest({})
            self.assertEqual(thread.call_args.kwargs['args'][1],'just-downloaded.xlsx')
            receipt=json.loads(next((w.data/'refreshes').glob('*/started.json')).read_text())
            self.assertEqual(receipt['selection_rule'],'latest-local-modification-time-v1')
            self.assertEqual(receipt['automatic_inputs']['activity']['name'],'renamed-activity.csv')
            w.lock.release()

    def test_latest_bad_named_export_blocks_instead_of_falling_back(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w)
            self.put(w,'Kalshi-Recent-Activity-All-bad.csv',b'bad,columns\n',300)
            self.assertEqual(w.catalog()['latest_inputs']['activity']['state'],'invalid')
            with patch.object(w,'generate') as generate:
                with self.assertRaisesRegex(ValueError,'CSV columns'):
                    w.generate_latest({})
                generate.assert_not_called()

    def test_equal_newest_times_are_visible_ambiguity(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w)
            self.put(w,'another.xlsx',workbook(),200)
            self.assertEqual(w.catalog()['latest_inputs']['forecast']['state'],'ambiguous')
            with self.assertRaisesRegex(ValueError,'same newest saved time'):
                w.generate_latest({})

    def test_missing_pnl_blocks_only_accounting_and_buttons_reuse_activity(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w)
            (w.inbox/'renamed-pnl.csv').unlink()
            with patch.object(w,'generate',return_value={}) as generate:
                w.generate_latest({})
            activity=generate.call_args.args[0]['activity']
            with self.assertRaisesRegex(ValueError,'No Kalshi realized P&L'):
                w.accounting_latest({})
            self.put(w,'renamed-pnl.csv',header(PNL_FIELDS),100)
            with patch.object(w,'update_accounting',return_value={'state':'complete'}) as accounting:
                w.accounting_latest({})
            self.assertEqual(accounting.call_args.args[0]['activity'],activity)

    def test_automatic_actions_reject_browser_file_and_path_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d)
            for payload in [{'forecast':{}},{'inbox':'/tmp'},{'activity':{}}]:
                with self.assertRaises(ValueError):w.generate_latest(payload)
                with self.assertRaises(ValueError):w.accounting_latest(payload)

    def test_changed_file_rejected_after_automatic_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);self.inputs(w)
            specs,_=w.automatic_inputs(('activity',))
            (w.inbox/'renamed-activity.csv').write_bytes(header(REQUIRED)+b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):
                w.file_bytes(specs['activity'],'.csv')

    def test_failed_automatic_discovery_does_not_leave_prior_baseline_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d)
            w.performance_status={'state':'complete','message':'Previous baseline checked'}
            with patch.object(w,'performance_config',return_value={'enabled':True}):
                with self.assertRaises(ValueError):w.generate_latest({})
            self.assertEqual(w.performance_status['state'],'attention')
            self.assertIn('unconfirmed',w.performance_status['message'])
            self.assertEqual(w.status['state'],'attention')
            self.assertFalse((w.data/'performance').exists())
            self.assertFalse((w.data/'refreshes').exists())


class AutomaticInputHTTPTests(unittest.TestCase):
    def test_fixed_actions_use_latest_inputs_and_preserve_request_guards(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.error import HTTPError
        from urllib.request import build_opener, ProxyHandler, Request
        from nfl_refresh import handler

        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d)
            setup=AutomaticInputsTests()
            setup.inputs(w)
            server=ThreadingHTTPServer(('127.0.0.1',0),handler(w,'test-token',Path(d)/'reports'))
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            origin='http://127.0.0.1:'+str(server.server_port)
            opener=build_opener(ProxyHandler({}))

            def post(route,payload,token='test-token'):
                request=Request(origin+route,data=json.dumps(payload).encode(),headers={
                    'Origin':origin,'Content-Type':'application/json','X-Pops-Token':token})
                try:
                    with opener.open(request) as response:return response.status,json.load(response)
                except HTTPError as error:
                    with error:return error.code,json.load(error)

            try:
                with patch('nfl_refresh.schedule.capture') as acquisition:
                    with opener.open(origin+'/api/state') as response:state=json.load(response)
                    acquisition.assert_not_called()
                self.assertEqual(state['latest_inputs']['forecast']['name'],'Elway_new.xlsx')
                self.assertFalse((w.data/'refreshes').exists())
                setup.put(w,'new-since-page-load.xlsx',workbook(),300)
                with patch.object(w,'generate',return_value={'state':'running','message':'Test fixture'}) as generate:
                    code,_=post('/api/generate-latest',{})
                    self.assertEqual(code,200)
                    self.assertEqual(generate.call_args.kwargs['automatic_inputs']['forecast']['name'],'new-since-page-load.xlsx')
                    activity=generate.call_args.args[0]['activity']
                    generate.reset_mock()
                    self.assertEqual(post('/api/generate-latest',{'inbox':'/tmp'})[0],400)
                    self.assertEqual(post('/api/generate-latest',{},token='wrong')[0],403)
                    generate.assert_not_called()
                with patch.object(w,'update_accounting',return_value={'state':'complete','message':'Test fixture'}) as accounting:
                    code,result=post('/api/accounting-latest',{})
                    self.assertEqual(code,200)
                    self.assertEqual(accounting.call_args.args[0]['activity'],activity)
                    self.assertEqual(result['used_inputs']['pnl']['name'],'renamed-pnl.csv')
                    accounting.reset_mock()
                    self.assertEqual(post('/api/accounting-latest',{'activity':{}})[0],400)
                    accounting.assert_not_called()
            finally:
                server.shutdown();server.server_close();thread.join()
