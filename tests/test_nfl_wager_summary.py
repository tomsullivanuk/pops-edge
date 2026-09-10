import unittest
from decimal import Decimal as D
from nfl_board_view import wager_summary

class WagerSummaryTests(unittest.TestCase):
    def trade(self,quantity='15.7',price='.38',fee='.25',**flags):
        return dict(quantity=quantity,price=price,fee=fee,needs_review=False,settlement_seen=False)|flags

    def test_recorded_cost_and_gross_payout_include_actual_fees_and_ties(self):
        got=wager_summary([self.trade()],{'central':'.6865'})
        self.assertEqual(got,dict(spent=D('6.216'),expected=D('10.77805'),win=D('15.7'),tie=D('7.85')))
        other=wager_summary([self.trade('26.58','.64','.42')],{'central':'.425'})
        self.assertEqual(other['spent'],D('17.4312'))
        self.assertEqual(other['expected'],D('11.29650'))

    def test_multiple_fills_sum_and_ambiguous_or_settled_activity_has_no_total(self):
        self.assertEqual(wager_summary([self.trade(),self.trade()],{'central':'.6865'})['spent'],D('12.432'))
        for rows in ([],[self.trade(needs_review=True)],[self.trade(settlement_seen=True)]):
            self.assertIsNone(wager_summary(rows,{'central':'.6865'}))
        self.assertIsNone(wager_summary([self.trade()],None))
