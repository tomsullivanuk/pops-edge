import csv
import io
import unittest
from nfl_activity import parse_current,parse_v2
from nfl_season_board import assemble,render

T='KXNFLGAME-26SEP10SFLAR-LAR'
M={T:dict(game_id='g',yes_team='LAR',opponent='SF')}
FIELDS=['type','Market_Ticker','Direction','Price_In_Cents','Amount_In_Dollars','Fee_In_Dollars','Original_Date','Result','Yes_Contracts_Owned','No_Contracts_Owned','Profit_In_Dollars','Yes_Contracts_Average_Price_In_Cents','No_Contracts_Average_Price_In_Cents']
def export(result='no',at='2026-09-11T03:30:00Z',duplicate=False):
    rows=[dict(type='Trade',Market_Ticker=T,Direction=side,Price_In_Cents=price,Amount_In_Dollars='26.58',Fee_In_Dollars=fee,Original_Date=time) for side,price,fee,time in [('No','64','0.42','2026-09-09T21:54:00Z'),('Yes','4','0.07','2026-09-11T02:50:00Z')]]
    row=dict(type='Settlement',Market_Ticker=T,Original_Date=at,Result=result,Yes_Contracts_Owned='26.58',No_Contracts_Owned='26.58',Profit_In_Dollars='0',Yes_Contracts_Average_Price_In_Cents='3.99',No_Contracts_Average_Price_In_Cents='35.97')
    rows.append(row)
    if duplicate:rows.append(row)
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader();w.writerows(rows);return out.getvalue().encode()

class SettlementStatusTests(unittest.TestCase):
    def test_unreconciled_payout_keeps_settlement_status_and_closes_display(self):
        raw=export();at='2026-09-11T12:00:00Z';old=parse_v2(raw,at,M);new=parse_current(raw,at,M)
        self.assertEqual(old['settlements'],[])
        self.assertEqual(new['settlements'],[])
        self.assertEqual(len(new['settlement_events']),1)
        self.assertTrue(any('does not reconcile' in d['reason'] for d in new['diagnostics']))
        self.assertEqual(old['trades'],new['trades'])
        c=dict(season=2026,updated_at=at,rows=[dict(week=1,home='LAR',away='SF',neutral=False,home_win='57.2%',away_win='42.2%')])
        d=assemble('/unused',[],c);d['games'][0]['game_id']='g';d['activity']=new
        h=render(d)
        self.assertEqual(h.count('Closed · market settled'),2)
        self.assertNotIn('if win · expected above',h)
        self.assertIn('Cash-flow review needed',h)

    def test_invalid_future_duplicate_or_unmatched_not_completion(self):
        for raw,mapping in [(export(result='unknown'),M),(export(at='2027-01-01T00:00:00Z'),M),(export(duplicate=True),M),(export(),{})]:
            with self.subTest(raw=raw):self.assertEqual(parse_current(raw,'2026-09-11T12:00:00Z',mapping)['settlement_events'],[])

    def test_opposite_trades_without_settlement_not_closed(self):
        raw=export().decode().splitlines();raw='\n'.join(raw[:-1]).encode()
        r=parse_current(raw,'2026-09-11T12:00:00Z',M)
        self.assertEqual(r['settlement_events'],[]);self.assertEqual(len(r['trades']),2)
