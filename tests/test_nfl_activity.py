import csv,io
from copy import deepcopy
import unittest
from nfl_activity import parse

AT='2026-09-09T22:00:00Z'
TICKER='KXNFLGAME-26SEP09NESEA-NE'
MAP={TICKER:dict(game_id='official-game',yes_team='NE',opponent='SEA')}
FIELDS=['type','Market_Ticker','Direction','Price_In_Cents','Amount_In_Dollars','Fee_In_Dollars','Original_Date']


def trade(**kw):
    row=dict(zip(FIELDS,['Trade',TICKER,'No','38','15.7','0.25','2026-09-09T21:52:59Z']))
    row.update(kw);return row


def raw(rows):
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    return out.getvalue().encode('utf-8-sig')


class ActivityTests(unittest.TestCase):
    def test_bom_order_not_double_counted_and_no_maps_opponent(self):
        r=parse(raw([trade(),trade(type='Order')]),AT,MAP)
        self.assertEqual(len(r['trades']),1);self.assertEqual(r['trades'][0]['team'],'SEA')
        self.assertEqual(r['trades'][0]['price'],'0.38')
        self.assertNotIn('open_quantity',r['trades'][0])

    def test_thousands_and_yes(self):
        r=parse(raw([trade(Direction='Yes',Amount_In_Dollars='1,870.38',Fee_In_Dollars='1.29')]),AT,MAP)
        self.assertEqual(r['trades'][0]['quantity'],'1870.38');self.assertEqual(r['trades'][0]['team'],'NE')

    def test_opposite_sides_not_netted(self):
        r=parse(raw([trade(),trade(Direction='Yes')]),AT,MAP)
        self.assertEqual(len(r['trades']),2)
        self.assertEqual({t['team'] for t in r['trades']},{'SEA','NE'})

    def test_duplicates_visible_not_silently_added(self):
        r=parse(raw([trade(),trade()]),AT,MAP)
        self.assertEqual(len(r['diagnostics']),1);self.assertTrue(r['trades'][0]['needs_review'])

    def test_settlement_retains_activity_without_open_claim(self):
        r=parse(raw([trade(),trade(type='Settlement',Original_Date='2026-09-09T21:59:00Z')]),AT,MAP)
        self.assertTrue(r['trades'][0]['settlement_seen'])

    def test_unknown_future_and_invalid_values_visible(self):
        for kw in [dict(Original_Date='2026-09-10T22:00:00Z'),dict(Amount_In_Dollars='12,34'),dict(Price_In_Cents='101'),dict(Direction='Unknown'),dict(Market_Ticker='KXNFLGAME-UNKNOWN')]:
            with self.subTest(kw=kw):
                r=parse(raw([trade(**kw)]),AT,MAP);self.assertEqual(r['trades'],[]);self.assertEqual(len(r['diagnostics']),1)

    def test_other_sports_not_matched_and_headers_required(self):
        r=parse(raw([trade(Market_Ticker='KXWTA-26-POT')]),AT,MAP)
        self.assertEqual(r['outside_nfl_rows'],1);self.assertEqual(r['trades'],[])
        with self.assertRaises(ValueError):parse(b'ticker,quantity\nx,1\n',AT,MAP)

if __name__=='__main__':unittest.main()
