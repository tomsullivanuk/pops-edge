import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import openpyxl
import nfl_excel_import as excel
import nfl_refresh as app
import nfl_forecast_import as f
from nfl_activity import parse_current


def workbook(change=None):
    w=openpyxl.Workbook();s=w.active
    for row in [('ELWAY future game projections',),('Projected scores for every 2026 regular-season game',),('All weeksWeek 1Week 181 games',),('Wk','Home','Avg.','Win','Away','Avg.','Win','Home','Total'),(None,None,'pts.','prob.',None,'pts.','prob.','spread','(O/U)'),('1N','LAR',25.5,.576,'SF',22.8,.418,-3,48),('Note: N indicates a neutral site. * and gray rows indicate conditional projections.',),('Updated September 9, 2026 at 10:51 AM EDT',)]:s.append(row)
    if change:change(s)
    out=BytesIO();w.save(out);return out.getvalue()


def upload(raw,name):return dict(name=name,data=base64.b64encode(raw).decode())


class ExcelTests(unittest.TestCase):
    def test_import_and_confirm_selected_week_replay(self):
        raw=workbook()
        with tempfile.TemporaryDirectory() as d:
            c=excel.prepare(raw,'elway.xlsx',Path(d));self.assertEqual(c['rows'][0]['home_win'],'57.6%');self.assertTrue(c['rows'][0]['neutral'])
            with self.assertRaises(ValueError):excel.verify(c,1,'Tom',d)
            path=excel.verify(c,1,'Tom',d,True);r=json.loads(path.read_text());excel.validate(r,raw,c['source'])
            self.assertEqual(excel.verify(c,1,'Tom',d,True),path)
            r['rows'][0]['home_win']='60.0%'
            with self.assertRaises(ValueError):excel.validate(r,raw,c['source'])
    def test_bad_counts_formula_and_conditional(self):
        for change in (lambda s:setattr(s['A3'],'value','2 games'),lambda s:setattr(s['D6'],'value','=1/2'),lambda s:setattr(s['A8'],'value','No update time'),lambda s:setattr(s['G6'],'value',.9)):
            with self.subTest(change=change),self.assertRaises(ValueError):excel.parse(workbook(change))
        with tempfile.TemporaryDirectory() as d:
            c=excel.prepare(workbook(lambda s:setattr(s['A6'],'value','1N*')),'x.xlsx',d)
            with self.assertRaises(ValueError):excel.verify(c,1,'Tom',d,True)


class WorkflowTests(unittest.TestCase):
    def inputs(self,w):
        from tests.test_nfl_activity import raw,trade
        (w.inbox/'elway.xlsx').write_bytes(workbook())
        (w.inbox/'activity.csv').write_bytes(raw([trade()]))
        files=w.catalog()['files']
        return {key:{'id':next(f['id'] for f in files if f['kind']==kind)} for key,kind in [('forecast','.xlsx'),('activity','.csv')]}

    def test_inbox_only_no_review_and_partial_failure_preserves_old(self):
        with tempfile.TemporaryDirectory() as d:
            w=app.Workflow(d);payload=self.inputs(w)
            with self.assertRaises(ValueError):w.file_bytes(upload(workbook(),'x.xlsx'),'.xlsx')
            archive=w.data/'forecasts/sources/x';archive.mkdir(parents=True);(archive/'source.xlsx').write_bytes(workbook())
            self.assertEqual(len(w.catalog()['files']),2)
            w.boards['2026-1']=Path(d)/'old'
            with patch.object(app.threading,'Thread') as t:
                w.generate(payload);args=t.call_args.kwargs['args']
            with self.assertRaises(ValueError):w.generate(payload)
            with patch.object(app.schedule,'capture',side_effect=ValueError('Schedule unavailable')):w.run(*args)
            self.assertEqual(w.status['state'],'attention');self.assertEqual(w.boards['2026-1'],Path(d)/'old');self.assertFalse(w.lock.locked())
            self.assertEqual(len(list((w.data/'refreshes').glob('*/partial.json'))),1)
            record=json.loads(next((w.data/'forecasts/verified').glob('*.json')).read_text())
            self.assertEqual(record['schema'],excel.AUTO_VERSION);self.assertNotIn('reviewer',record)
            self.assertNotIn('metadata_reviewed',record['review'])

    def test_success_captures_every_workbook_week(self):
        with tempfile.TemporaryDirectory() as d:
            w=app.Workflow(d);payload=self.inputs(w)
            with patch.object(app.threading,'Thread') as t:
                w.generate(payload);args=t.call_args.kwargs['args']
            schedule=dict(error=None,rows=[dict(kickoff='2026-09-10T20:00:00Z'),dict(kickoff='2026-09-14T23:00:00Z')])
            original=excel.prepare
            def prepare(*a):
                c=original(*a);c['weeks']=[1,2];return c
            result=w.data/'boards/board-test'
            with patch.object(app.excel,'prepare',side_effect=prepare),patch.object(app.excel,'validate_automatically',return_value=Path(d)/'validated'),patch.object(app.schedule,'capture',return_value=(Path(d),schedule)) as schedules,patch.object(app.kalshi,'capture',return_value=(Path(d),{'state':'complete'})) as capture,patch.object(app.board,'build',return_value=(result,dict(ranked_games=1,scheduled_games=2))),patch.object(app.board,'replay'):
                w.run(*args)
                self.assertEqual([c.args[2] for c in schedules.call_args_list],[1,2]);self.assertEqual(capture.call_count,2)
                self.assertEqual(capture.call_args.args[1:],('2026-09-10','2026-09-14'))
            self.assertEqual(w.status['state'],'complete');self.assertEqual(set(w.boards),{'2026-1','2026-2'})

    def test_automatic_validation_replay_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            raw=workbook();c=excel.prepare(raw,'x.xlsx',d)
            path=excel.validate_automatically(c,1,d);r=json.loads(path.read_text());excel.validate_auto(r,raw,c['source'])
            r['rows'][0]['home_win']='60.0%'
            with self.assertRaises(ValueError):excel.validate_auto(r,raw,c['source'])


class SettlementTests(unittest.TestCase):
    def raw(self,duplicate=False):
        import csv
        from io import StringIO
        rows=[dict(type='Trade',Market_Ticker='KXNFLGAME-26SEP09NESEA-NE',Direction='No',Price_In_Cents='38',Amount_In_Dollars='15.7',Fee_In_Dollars='.25',Original_Date='2026-09-09T21:52:59Z'),dict(type='Settlement',Market_Ticker='KXNFLGAME-26SEP09NESEA-NE',Original_Date='2026-09-10T03:29:46Z',No_Contracts_Owned='15.7',Yes_Contracts_Owned='0',No_Contracts_Average_Price_In_Cents='61.97',Yes_Contracts_Average_Price_In_Cents='0',Result='no',Profit_In_Dollars='15.70')]
        rows[0]['Fee_In_Dollars']='0.25'
        if duplicate:rows.append(rows[-1].copy())
        out=StringIO();writer=csv.DictWriter(out,fieldnames=sorted(set().union(*(r.keys() for r in rows))));writer.writeheader();writer.writerows(rows);return out.getvalue().encode()
    def test_gross_payout_not_profit_and_cost_mismatch(self):
        mapping={'KXNFLGAME-26SEP09NESEA-NE':dict(game_id='g',yes_team='NE',opponent='SEA')}
        r=parse_current(self.raw(),'2026-09-10T12:00:00Z',mapping)
        self.assertEqual(r['settlements'][0]['payout'],'15.7');self.assertEqual(r['settlements'][0]['team'],'SEA');self.assertFalse(r['settlements'][0]['cost_reconciled']);self.assertTrue(r['trades'][0]['settlement_seen'])
        self.assertNotIn('profit',r['settlements'][0])
        r=parse_current(self.raw(True),'2026-09-10T12:00:00Z',mapping);self.assertTrue(r['settlements'][0]['needs_review'])

if __name__=='__main__':unittest.main()

class LocalRequestTests(unittest.TestCase):
    def test_origin_host_token_and_content_type_required(self):
        from types import SimpleNamespace
        from email.message import Message
        cls=app.handler(None,'secret');obj=object.__new__(cls);obj.server=SimpleNamespace(server_port=8766)
        good={'Host':'127.0.0.1:8766','Origin':'http://127.0.0.1:8766','X-Pops-Token':'secret','Content-Type':'application/json'}
        for replacement in ({},{'Origin':'https://other.example'},{'Host':'other.example'},{'X-Pops-Token':'bad'},{'Content-Type':'text/plain'},{'Sec-Fetch-Site':'cross-site'}):
            obj.headers=Message()
            for k,v in (good|replacement).items():obj.headers[k]=v
            self.assertEqual(obj.trusted(True),not bool(replacement))

class TBDWorkflowTests(unittest.TestCase):
    def test_undated_week_completes_without_price_request(self):
        with tempfile.TemporaryDirectory() as d:
            w=app.Workflow(d);payload=WorkflowTests().inputs(w)
            with patch.object(app.threading,'Thread') as thread:
                w.generate(payload);args=thread.call_args.kwargs['args']
            with patch.object(app.schedule,'capture',return_value=(Path(d),dict(error=None,rows=[dict(kickoff=None)]))),patch.object(app.kalshi,'capture') as capture:
                w.run(*args)
            capture.assert_not_called()
            self.assertEqual(w.status['state'],'complete');self.assertIn('date/time TBD',w.status['message']);self.assertNotIn('Needs attention',w.status['message'])
            result=json.loads(next((w.data/'refreshes').glob('*/complete.json')).read_text())
            self.assertEqual(result['failures'],[]);self.assertEqual(result['pending_dates'][0]['week'],1)
