"""Explicit overtime interpretation with byte-stable legacy report replay."""
from copy import deepcopy
from pathlib import Path
import unittest
import nfl_forecast_import as base
import nfl_performance_sources as adapter
from tests import test_nfl_performance as fixture
from tests.test_nfl_comparison_board import source, ID

class OvertimeRuleTests(unittest.TestCase):
    def outcome(self,g,rule=adapter.OVERTIME_OUTCOME_RULE):
        return adapter.outcomes(source([g]),2026,1,outcome_rule=rule)[ID]
    def test_completed_overtime_win_loss_tie_and_regulation(self):
        for phase in ('FINAL','FINAL_OVERTIME'):
            for score,payout in ((31,'1'),(20,'0'),(27,'0.5')):
                g=fixture.game(True,score);g['summary']['phase']=phase
                r=self.outcome(g);self.assertEqual(r['state'],'final');self.assertEqual(r['payout'],payout)
        self.assertEqual(self.outcome(g,adapter.LEGACY_OUTCOME_RULE)['state'],'unresolved-outcome')
    def test_incomplete_contradictory_and_invalid_evidence_remains_unscored(self):
        mutations=[lambda g:g['summary'].update(quarter='OT'),
          lambda g:g['summary'].update(gameId='wrong'),
          lambda g:g['summary']['homeTeam'].update(teamId='wrong'),
          lambda g:g['summary']['homeTeam']['score'].update(total=-1),
          lambda g:g['summary']['homeTeam']['score'].update(total=True),
          lambda g:g['summary']['homeTeam']['score'].update(q1=1,q2=1,q3=1,q4=1,ot=1),
          lambda g:g.update(status='CANCELLED'),
          lambda g:g['summary'].update(phase='UNKNOWN_FINAL')]
        for mutate in mutations:
            g=fixture.game(True,31);g['summary']['phase']='FINAL_OVERTIME';mutate(g)
            r=self.outcome(g);self.assertNotEqual(r['state'],'final');self.assertIsNone(r['payout'])
        g=fixture.game(True);g['summary'].update(phase='IN_PROGRESS',quarter='OT')
        self.assertEqual(self.outcome(g)['state'],'awaiting-outcome')
    def test_unknown_rule_is_rejected(self):
        with self.assertRaises(ValueError):self.outcome(fixture.game(True),'unknown')
    def test_old_report_replay_and_new_rule_preserve_evidence(self):
        f=fixture.PerformanceTests();f.setUp();self.addCleanup(f.doCleanups);f.refresh();f.clock.value=fixture.AFTER
        g=fixture.game(True,31);g['summary']['phase']='FINAL_OVERTIME'
        f.engine.observe_results(2026,1,lambda _: (200,source([g])))
        old=f.engine.report(2026,1,f.clock(),outcome_rule=adapter.LEGACY_OUTCOME_RULE)
        path=f.engine.root/'reports'/(old['report_id']+'.json');base.write_once(path,base.encode(old))
        before={str(p):p.read_bytes() for p in f.engine.root.rglob('*') if p.is_file()}
        current=f.engine.report(2026,1,f.clock())
        self.assertEqual(f.engine.replay_report(path),old)
        self.assertNotIn('outcome_rule',old);self.assertEqual(old['paired_games'],0)
        self.assertEqual(current['outcome_rule'],adapter.OVERTIME_OUTCOME_RULE);self.assertEqual(current['paired_games'],1)
        self.assertNotEqual(old['report_id'],current['report_id'])
        for key in ('selected_import','source_boundary','cutoff','activation'):
            self.assertEqual(old[key],current[key])
        self.assertEqual(old['games'][0]['kalshi'],current['games'][0]['kalshi'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in f.engine.root.rglob('*') if p.is_file()})
        newpath=f.engine.root/'reports'/(current['report_id']+'.json');base.write_once(newpath,base.encode(current))
        self.assertEqual(f.engine.replay_report(newpath),current)
        bad=deepcopy(current);bad['outcome_rule']='unknown';badpath=f.engine.root/'bad.json';badpath.write_bytes(base.encode(bad))
        with self.assertRaises(ValueError):f.engine.replay_report(badpath)
