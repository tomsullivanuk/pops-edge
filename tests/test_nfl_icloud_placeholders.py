import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from nfl_refresh import Workflow
from nfl_inbox import is_dataless, newest
from nfl_activity import REQUIRED
from nfl_accounting import PNL_FIELDS

class PlaceholderTests(unittest.TestCase):
    def test_flags(self):
        with patch('nfl_inbox.sys.platform','darwin'):
            self.assertTrue(is_dataless(SimpleNamespace(st_flags=0x40000060)))
            self.assertFalse(is_dataless(SimpleNamespace(st_flags=0x40)))
            self.assertFalse(is_dataless(SimpleNamespace()))
        with patch('nfl_inbox.sys.platform','linux'):
            self.assertFalse(is_dataless(SimpleNamespace(st_flags=0x40000000)))

    def test_cold_scan_no_open_and_download_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d); p=w.inbox/'renamed.csv';p.write_text(','.join(sorted(REQUIRED))+'\n')
            with patch('nfl_refresh.is_dataless',return_value=True), patch.object(Path,'read_bytes',side_effect=AssertionError('placeholder opened')):
                c=w.catalog()
                for k in ('activity','pnl'):
                    self.assertEqual(c['latest_inputs'][k]['state'],'not_downloaded')
                    with self.assertRaisesRegex(ValueError,'Not downloaded'): w.automatic_inputs((k,))
            self.assertEqual(w.catalog()['latest_inputs']['activity']['state'],'ready')
            self.assertFalse((w.data/'refreshes').exists())

    def test_unknown_newer_blocks_both_but_old_does_not(self):
        good=[dict(name=k,input_kind=k,modified_ns=20) for k in ('forecast','activity','pnl')]
        p=dict(name='unknown.csv',possible_kinds=['activity','pnl'],modified_ns=21,not_downloaded=True,input_error='Not downloaded')
        c=newest(good+[p]);self.assertEqual(c['forecast']['state'],'ready')
        for k in ('activity','pnl'):self.assertEqual(c[k]['state'],'not_downloaded')
        p['modified_ns']=19
        for k in ('activity','pnl'):self.assertEqual(newest(good+[p])[k]['state'],'ready')
        p['modified_ns']=20
        for k in ('activity','pnl'):self.assertEqual(newest(good+[p])[k]['state'],'ambiguous')

    def test_action_rechecks_locality_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d);(w.inbox/'test.xlsx').write_bytes(b'fixture')
            item=w.catalog()['files'][0];spec={k:item[k] for k in ('id','fingerprint')}
            with patch('nfl_refresh.is_dataless',return_value=True),patch.object(Path,'read_bytes',side_effect=AssertionError('opened')):
                for with_time in (False,True):
                    with self.assertRaisesRegex(ValueError,'not downloaded'):w.file_bytes(spec,'.xlsx',with_time)

    def test_named_placeholder_only_blocks_its_kind(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow(d)
            for name in ('Elway.xlsx','Kalshi-Activity.csv','kalshi-realized.csv'):
                (w.inbox/name).write_bytes(b'fixture')
            with patch('nfl_refresh.is_dataless',return_value=True),patch.object(Path,'read_bytes',side_effect=AssertionError('opened')):
                c=w.catalog()
            self.assertEqual({f['input_kind'] for f in c['files']},{'forecast','activity','pnl'})
            self.assertTrue(all(f['state']=='not_downloaded' for f in c['latest_inputs'].values()))

if __name__=='__main__':unittest.main()
