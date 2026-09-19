from copy import deepcopy
from tempfile import TemporaryDirectory
import unittest
import nfl_season_board as season
import nfl_accounting as accounting
from nfl_activity import parse_current
from tests.test_nfl_accounting import fixtures, encoded, AT, TICKER, GAME


class RecordedTradeTests(unittest.TestCase):
    def data(self, closed=False):
        a,p=fixtures()
        for row in a:
            if row.get('Fee_In_Dollars','').startswith('.'):
                row['Fee_In_Dollars']='0'+row['Fee_In_Dollars']
        if not closed: a,p=a[:1],[]
        candidate=dict(season=2026,updated_at=AT,rows=[dict(week=1,home='LAR',away='SF',neutral=False,home_win='58%',away_win='42%')])
        with TemporaryDirectory() as tmp:
            data=season.assemble(tmp,[],candidate,now=AT)
            data['games'][0].update(GAME)
            accounting.save(tmp,*encoded(a,p),AT)
            data['accounting'],issues=accounting.load(tmp,[data['games'][0]],AT)
        data['accounting_enabled']=True
        data['activity']=parse_current(encoded(a,p)[0],AT,{TICKER:dict(game_id='g',yes_team='LAR',opponent='SF')})
        data['diagnostics']=issues
        season.separate_accounting_notes(data,issues)
        return data

    def test_open_trade_visible_without_amount_or_profit_inference(self):
        data=self.data();before=deepcopy(data);html=season.render(data)
        self.assertIn('NO LAR</b> · 26.58 contracts',html)
        self.assertIn('Export YES price $0.64 · recorded fee $0.42',html)
        self.assertIn('09/09/2026 04:54 PM CDT · export row 2',html)
        self.assertIn('Recorded trade · current holding unverified',html)
        self.assertNotIn('Accounting review needed',html)
        self.assertNotIn('Some saved history',html)
        self.assertNotIn('Profit +',html)
        self.assertNotIn('expected net',html)
        self.assertEqual(data,before)
        self.assertEqual(len(data['accounting_notes']),1)

    def test_closed_cost_and_profit_stay_separate_from_execution_rows(self):
        html=season.render(self.data(True))
        self.assertIn('NO LAR</b> · $10.00',html)
        self.assertIn('Sale proceeds</small><small>Profit +$15.45',html)
        self.assertIn('NO LAR</b> · 26.58 contracts',html)
        self.assertIn('YES LAR</b> · 26.58 contracts',html)
        self.assertNotIn('Recorded trade · current holding unverified',html)

    def test_mixed_preserves_closed_results_without_summing_trades(self):
        data=self.data(True)
        t=deepcopy(data['activity']['trades'][0]);t.update(quantity='2.25',at=AT,source_row=99,settlement_seen=False)
        data['activity']['trades'].append(t)
        html=season.render(data)
        self.assertIn('2.25 contracts',html)
        self.assertIn('Profit +$15.45',html)
        self.assertIn('current holding unverified',html)

    def test_discrepancies_and_settlement_without_closure_stay_warnings(self):
        for kind in ('duplicate','settlement','conflict','unmatched'):
            data=self.data();issue=data['accounting_notes'][0]
            data['diagnostics']=[issue]
            if kind=='duplicate': data['activity']['trades'][0]['needs_review']=True
            if kind=='settlement': data['activity']['trades'][0]['settlement_seen']=True
            if kind=='conflict': data['diagnostics'].append(dict(ticker=TICKER,reason='Conflicting overlapping P&L lots; accounting needs review'))
            if kind=='unmatched': data['activity']['trades']=[]
            season.separate_accounting_notes(data,[issue])
            self.assertEqual(data['accounting_notes'],[])
            self.assertIn(issue,data['diagnostics'])
            self.assertIn('Some saved history',season.render(data))

    def test_legacy_weekly_renderer_is_not_changed_without_accounting(self):
        data=self.data();data['accounting_enabled']=False
        html=season.render(data)
        self.assertNotIn('Recorded trades / closed cost',html)
        self.assertNotIn('Export YES price',html)
