import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decimal import Decimal
import nfl_accounting as accounting
from nfl_activity import REQUIRED
from nfl_refresh import Workflow

AT='2026-09-15T00:00:00Z'
TICKER='KXNFLGAME-26SEP10SFLAR-LAR'
GAME=dict(game_id='g',home='LAR',away='SF',kickoff='2026-09-11T00:35:00Z')


def csv_bytes(records, fields):
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=sorted(set(fields)|{k for r in records for k in r}))
    writer.writeheader();writer.writerows(records);return out.getvalue().encode()


def fixtures():
    trades=[dict(type='Trade',Market_Ticker=TICKER,Direction='No',Amount_In_Dollars='26.58',Price_In_Cents='64',Fee_In_Dollars='.42',Original_Date='2026-09-09T21:54:18.408Z'),
            dict(type='Trade',Market_Ticker=TICKER,Direction='Yes',Amount_In_Dollars='26.58',Price_In_Cents='4',Fee_In_Dollars='.07',Original_Date='2026-09-11T02:50:08.229Z'),
            dict(type='Settlement',Market_Ticker=TICKER,Original_Date='2026-09-11T03:30:54.399Z',Result='no',Profit_In_Dollars='0')]
    pnl=[dict(subtrader_id='test-account',type='trade',quantity_fp='26.58',market_ticker=TICKER,side='no',entry_price_dollars='.36',exit_price_dollars='.96',open_fees_dollars='.4287',close_fees_dollars='.0715',realized_pnl_without_fees_dollars='15.948',realized_pnl_with_fees_dollars='15.4478',open_timestamp='2026-09-09T17:54:18-04:00',close_timestamp='2026-09-10T22:50:08-04:00')]
    return trades,pnl


def encoded(a,p):return csv_bytes(a,REQUIRED),csv_bytes(p,accounting.PNL_FIELDS)


class AccountingTests(unittest.TestCase):
    def test_sale_and_precise_fees(self):
        a,p=fixtures();records,issues=accounting.reconcile(*encoded(a,p),AT)
        self.assertEqual(issues,[]);lot=records[0]['lots'][0]
        self.assertEqual(lot['kind'],'sale')
        self.assertEqual(Decimal(lot['profit']),Decimal('15.4478'))
        self.assertEqual(Decimal(lot['cost'])+Decimal(lot['opening_fee']),Decimal('9.9975'))

    def test_settlement_is_not_a_sale(self):
        a,p=fixtures();a.pop(1);a[-1]['Profit_In_Dollars']='26.58'
        p[0].update(exit_price_dollars='1',close_fees_dollars='0',close_timestamp='2026-09-10T23:30:54-04:00',realized_pnl_without_fees_dollars='17.0112',realized_pnl_with_fees_dollars='16.5825')
        records,issues=accounting.reconcile(*encoded(a,p),AT)
        self.assertEqual(issues,[]);self.assertEqual(records[0]['lots'][0]['kind'],'settlement')

    def test_bad_math_missing_execution_duplicates_and_future_fail_closed(self):
        for mutation in ('math','missing','duplicate','future','price','fee','quantity'):
            with self.subTest(mutation=mutation):
                a,p=fixtures()
                if mutation=='math':p[0]['realized_pnl_with_fees_dollars']='99'
                if mutation=='missing':a.pop(1)
                if mutation=='duplicate':p.append(p[0].copy())
                if mutation=='future':a[0]['Original_Date']='2027-09-09T21:54:18Z'
                if mutation=='price':a[0]['Price_In_Cents']='36'
                if mutation=='fee':a[0]['Fee_In_Dollars']='.40'
                if mutation=='quantity':a[0]['Amount_In_Dollars']='30'
                records,issues=accounting.reconcile(*encoded(a,p),AT)
                self.assertEqual(records,[]);self.assertTrue(issues)

    def test_repeated_windows_restart_and_aging_out(self):
        a,p=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            accounting.save(tmp,*encoded(a,p),AT)
            accounting.save(tmp,*encoded(a,p),'2026-09-16T00:00:00Z')
            self.assertEqual(len(list(Path(tmp).glob('accounting/*/complete.json'))),1)
            accounting.save(tmp,*encoded([],[]),'2026-10-16T00:00:00Z')
            records,issues=accounting.load(tmp,[GAME],'2026-10-17T00:00:00Z')
            self.assertEqual(len(records),1);self.assertFalse(issues)
            self.assertEqual(accounting.load(tmp,[GAME],'2026-09-14T00:00:00Z')[0],[])
            raw=next(Path(tmp).glob('accounting/*/pnl.csv'));raw.write_bytes(b'changed')
            records,issues=accounting.load(tmp,[GAME],'2026-10-17T00:00:00Z')
            self.assertEqual(records,[]);self.assertTrue(issues)

    def test_conflicting_overlap_does_not_select_latest_or_double_count(self):
        a,p=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            accounting.save(tmp,*encoded(a,p),AT)
            p[0]['open_fees_dollars']='.4290';p[0]['realized_pnl_with_fees_dollars']='15.4475'
            accounting.save(tmp,*encoded(a,p),'2026-09-16T00:00:00Z')
            records,issues=accounting.load(tmp,[GAME],'2026-09-17T00:00:00Z')
            self.assertFalse(records);self.assertIn('Conflicting',issues[0]['reason'])

    def test_conflicting_close_times_cannot_reuse_the_opening_quantity(self):
        a,p=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            accounting.save(tmp,*encoded(a,p),AT)
            a[1]['Original_Date']='2026-09-11T02:51:08.229Z'
            p[0]['close_timestamp']='2026-09-10T22:51:08-04:00'
            accounting.save(tmp,*encoded(a,p),'2026-09-16T00:00:00Z')
            records,issues=accounting.load(tmp,[GAME],'2026-09-17T00:00:00Z')
            self.assertFalse(records);self.assertTrue(issues)

    def test_two_files_required_and_no_provider_calls(self):
        a,p=fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            workflow=Workflow(tmp)
            ar,pr=encoded(a,p)
            (workflow.inbox/'activity.csv').write_bytes(ar);(workflow.inbox/'pnl.csv').write_bytes(pr)
            files={f['name']:dict(id=f['id']) for f in workflow.catalog()['files']}
            with self.assertRaises(ValueError):workflow.update_accounting(dict(activity=files['activity.csv']))
            with patch('nfl_refresh.kalshi.capture',side_effect=AssertionError('network')),patch('nfl_refresh.schedule.capture',side_effect=AssertionError('network')),patch('nfl_refresh.kalshi.utc',return_value=AT):
                result=workflow.update_accounting(dict(activity=files['activity.csv'],pnl=files['pnl.csv']))
            self.assertEqual(result['state'],'complete');self.assertFalse(workflow.lock.locked())
            self.assertFalse((workflow.data/'boards').exists())

    def test_render_preserves_contract_side_and_separates_proceeds_from_profit(self):
        from nfl_season_board import assemble,render
        from nfl_activity import parse_current
        a,p=fixtures()
        candidate=dict(season=2026,updated_at=AT,rows=[dict(week=1,home='LAR',away='SF',neutral=False,home_win='58%',away_win='42%')])
        with tempfile.TemporaryDirectory() as tmp:
            data=assemble(tmp,[],candidate,now=AT)
            g=data['games'][0];g.update(GAME)
            accounting.save(tmp,*encoded(a,p),AT)
            data['accounting'],issues=accounting.load(tmp,[g],AT)
            data['accounting_enabled']=True
            data['activity']=parse_current(encoded(a,p)[0],AT,{TICKER:dict(game_id='g',yes_team='LAR',opponent='SF')})
            html=render(data)
            self.assertFalse(issues)
            self.assertIn('NO LAR</b> · $10.00',html)
            self.assertIn('Sale proceeds</small><small>Profit +$15.45',html)
            self.assertIn('data-sort="25.5168"',html)
            self.assertNotIn('YES LAR</b> · $',html)
            self.assertNotIn('Cash-flow review needed',html)
            self.assertIn('opening fee $0.4287',html)
            self.assertIn('Calculation notes',html)

    def test_split_lots_partition_one_execution(self):
        a,p=fixtures();base=p[0];p=[]
        for quantity in ('10','16.58'):
            q=Decimal(quantity);ratio=q/Decimal('26.58');open_fee=Decimal('.4287')*ratio;close_fee=Decimal('.0715')*ratio
            # Exact allocations with finite precision; retain a total of the source fee.
            if p:
                open_fee=Decimal('.4287')-Decimal(p[0]['open_fees_dollars']);close_fee=Decimal('.0715')-Decimal(p[0]['close_fees_dollars'])
            else:
                open_fee=open_fee.quantize(Decimal('.00000001'));close_fee=close_fee.quantize(Decimal('.00000001'))
            p.append(dict(base,quantity_fp=quantity,open_fees_dollars=str(open_fee),close_fees_dollars=str(close_fee),realized_pnl_without_fees_dollars=str(q*Decimal('.60')),realized_pnl_with_fees_dollars=str(q*Decimal('.60')-open_fee-close_fee)))
        records,issues=accounting.reconcile(*encoded(a,p),AT)
        self.assertFalse(issues);self.assertEqual(len(records[0]['lots']),2)


if __name__=='__main__':unittest.main()
