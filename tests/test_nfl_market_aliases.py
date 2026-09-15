"""Observed abbreviated team names remain explicit and replay-versioned."""
from copy import deepcopy
import unittest
import nfl_comparison_board as board
from tests.test_nfl_comparison_board import inputs, AT, market


class AliasTests(unittest.TestCase):
    def test_observed_names_are_opt_in_and_exact(self):
        for label, code in board.ABBREVIATED_ALIASES.items():
            with self.subTest(label=label):
                opponent='Seattle' if code!='SEA' else 'New England'
                other='SEA' if code!='SEA' else 'NE'
                m=market(team=label,code=code)
                for field in ('rules_primary','rules_secondary'):
                    m[field]=m[field].replace('New England vs Seattle',label+' vs '+opponent)
                self.assertEqual(board.strict_market(m,board.MATCHING_VERSION), (frozenset((code,other)),code,'2026-09-09'))
                with self.assertRaises(ValueError):board.strict_market(m)
                bad=deepcopy(m)
                for field in ('rules_primary','rules_secondary'):
                    bad[field]=bad[field].replace(label,label+' unknown')
                bad['yes_sub_title']=label+' unknown'
                with self.assertRaises(ValueError):board.strict_market(bad,board.MATCHING_VERSION)

    def abbreviated(self):
        i=inputs()
        for m in i[3]:
            for field in ('rules_primary','rules_secondary'):
                m[field]=m[field].replace('New England vs Seattle','NE Patriots vs SEA Seahawks')
        return i

    def test_new_derivation_matches_and_legacy_is_unchanged(self):
        i=self.abbreviated()
        old=board.derive(*i,AT)
        new=board.derive(*i,AT,matching_version=board.MATCHING_VERSION)
        self.assertEqual(old['ranked_games'],0)
        self.assertNotIn('matching_version',old)
        self.assertEqual(new['ranked_games'],1)
        self.assertEqual(new['matching_version'],board.MATCHING_VERSION)
        self.assertEqual(board.derive(*i,AT),old)
        with self.assertRaises(ValueError):board.derive(*i,AT,matching_version='unknown')

    def test_rules_dates_conflicts_and_freshness_still_fail(self):
        for change in ('rules','date','label','teams','stale'):
            i=self.abbreviated();at=AT
            if change=='rules':
                for m in i[3]:m['rules_secondary']+=' Ties resolve to No.'
            if change=='date':i[1]['rows'][0]['kickoff']='2026-09-12T00:20:00Z'
            if change=='label':
                for m in i[3]:m['yes_sub_title']='Kansas City'
            if change=='teams':
                for m in i[3]:
                    for field in ('rules_primary','rules_secondary'):m[field]=m[field].replace('NE Patriots','SEA Seahawks')
            if change=='stale':at='2026-09-09T15:05:01+00:00'
            with self.subTest(change=change):
                self.assertEqual(board.derive(*i,at,matching_version=board.MATCHING_VERSION)['ranked_games'],0)
