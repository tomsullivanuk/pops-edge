import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import nfl_completion as completion
import nfl_schedule as schedule
import nfl_performance_sources as legacy
import nfl_season_board as season
import nfl_comparison_board as board
from tests.test_nfl_performance import game
from tests.test_nfl_comparison_board import source, inputs, AT, ID

AFTER = '2026-09-11T15:00:00Z'
LATER = '2026-09-11T16:00:00Z'


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def capture(self, g=None, at=AFTER):
        return schedule.capture(self.root/'schedules',2026,1,
            transport=lambda _: (200,source([g or game(True)])),clock=lambda:at)[0]

    def decode(self,g):
        return completion.summaries(source([g]),2026,1)[ID]

    def view(self, folders=True):
        snapshot=board.derive(*inputs(),AT)
        candidate=dict(season=2026,updated_at=AT,rows=[dict(week=1,home='SEA',away='NE',neutral=False,home_win='68.4%',away_win='31.1%')])
        with patch('nfl_season_board.board.replay',return_value=snapshot):
            return season.assemble(self.root,[self.root/'board'] if folders else [],candidate,AFTER)

    def test_final_overtime_tie_and_legacy_replay_unchanged(self):
        for phase in ['FINAL','FINAL_OVERTIME']:
            for score in [7,27]:
                g=game(True,score);g['summary']['phase']=phase
                result=self.decode(g)
                self.assertEqual(result['state'],'final')
                self.assertEqual(result['home_score'],score)
                self.assertEqual(result['away_score'],27)
                self.assertEqual(result['overtime'],phase=='FINAL_OVERTIME')
        self.assertEqual(legacy.outcomes(source([g]),2026,1)[ID]['state'],'unresolved-outcome')

    def test_invalid_summary_never_displays_scores(self):
        for change in [lambda g:g['summary'].update(gameId='wrong'),
                       lambda g:g['summary']['homeTeam'].update(teamId='wrong'),
                       lambda g:g['summary'].update(quarter='Q4'),
                       lambda g:g.update(status='CANCELLED'),
                       lambda g:g['summary']['homeTeam']['score'].update(total=-1),
                       lambda g:g['summary']['homeTeam']['score'].update(total=True),
                       lambda g:g['summary']['homeTeam']['score'].update(q1=99),
                       lambda g:g['summary']['homeTeam']['score'].update(q1=1,q2=1,q3=1,q4=1,ot=1)]:
            g=game(True);change(g)
            result=self.decode(g)
            self.assertEqual(result['state'],'unresolved')
            self.assertNotIn('home_score',result)

    def test_missing_pregame_in_progress_and_unsupported(self):
        self.assertEqual(self.decode(game())['state'],'awaiting')
        for phase in ['PREGAME','IN_PROGRESS']:
            g=game(True);g['summary'].update(phase=phase,quarter='Q1')
            self.assertEqual(self.decode(g)['state'],'awaiting')
        g=game(True);g['summary'].update(phase='SUSPENDED',quarter='Q1')
        self.assertEqual(self.decode(g)['state'],'unresolved')
        g=game();g['status']='FINAL'
        self.assertEqual(self.decode(g)['state'],'unresolved')

    def test_latest_correction_future_and_unresolved_no_fallback(self):
        self.capture();self.capture(game(True,30),LATER)
        selected,_=completion.latest(self.root,2026,AFTER)
        self.assertEqual(selected[1]['outcomes'][ID]['home_score'],7)
        selected,_=completion.latest(self.root,2026,LATER)
        self.assertEqual(selected[1]['outcomes'][ID]['home_score'],30)
        g=game(True);g['summary']['homeTeam']['teamId']='wrong'
        self.capture(g,'2026-09-11T17:00:00Z')
        selected,_=completion.latest(self.root,2026,'2026-09-11T18:00:00Z')
        self.assertEqual(selected[1]['outcomes'][ID]['state'],'unresolved')

    def test_same_time_conflict_and_identical_duplicates(self):
        self.capture();self.capture()
        selected,_=completion.latest(self.root,2026,AFTER)
        self.assertNotIn('error',selected[1])
        self.capture(game(True,30))
        selected,_=completion.latest(self.root,2026,AFTER)
        self.assertIn('Conflicting',selected[1]['error'])

    def test_tamper_or_newer_failure_not_hidden_by_old_valid(self):
        self.capture();path=self.capture(at=LATER)
        (path/'source.html').write_bytes(b'bad')
        selected,_=completion.latest(self.root,2026,LATER)
        self.assertIn('error',selected[1])
        data=self.view();self.assertTrue(data['games'][0]['completed']) # future tamper excluded
        schedule.capture(self.root/'schedules',2026,1,transport=lambda _: (503,b''),clock=lambda:'2026-09-11T17:00:00Z')
        selected,_=completion.latest(self.root,2026,'2026-09-11T18:00:00Z')
        self.assertIn('error',selected[1])

    def test_completion_without_activity_prices_or_research_and_layout(self):
        g=game(True);g['summary']['phase']='FINAL_OVERTIME';self.capture(g)
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        for folders in [False,True]:
            data=self.view(folders);row=data['games'][0]
            self.assertTrue(row['completed'])
            self.assertEqual(row['official_result']['home_score'],7)
            self.assertFalse(any(r['usable'] for o in row['outcomes'] for r in o['routes']))
            html=season.render(data)
            self.assertEqual(html.count('Final (OT): NE 27–SEA 7</small>'),2)
            self.assertIn('09/09 · Week 1<small>',html)
            self.assertNotIn('Week 1 · Final',html)
            self.assertEqual(html.count(' data-completed="true"'),2)
            self.assertIn('Official NFL result',html)
            self.assertIn('Observed 09/11/2026',html)
            self.assertIn('data-sort="NE at SEA"',html)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_neutral_and_identity_mismatch(self):
        self.capture()
        data=self.view();g=data['games'][0];g['neutral']=True
        observations,_=completion.latest(self.root,2026,AFTER)
        completion.apply([g],observations,AFTER)
        self.assertFalse(g['completed'])
        self.assertEqual(g['display_status'],'Result needs review')
        self.assertIn('Neutral · Result needs review',season.render(data))
        g['neutral']=False;g['game_id']='wrong'
        completion.apply([g],observations,AFTER)
        self.assertFalse(g['completed'])

    def test_no_official_result_never_uses_account_settlement(self):
        data=self.view();g=data['games'][0]
        self.assertFalse(g['completed'])
        self.assertEqual(g['display_status'],'Started')
        data['activity']={'settlement_events':[dict(game_id=ID)]}
        completion.apply([g],{},AFTER)
        self.assertFalse(g['completed'])

    def test_unreadable_metadata_is_visible_and_cannot_authorize_completion(self):
        self.capture()
        folder=self.root/'schedules/bad';folder.mkdir()
        (folder/'receipt.json').write_text('{')
        observations,issues=completion.latest(self.root,2026,AFTER)
        self.assertTrue(issues)
        self.assertIn('error',observations[1])
        data=self.view()
        self.assertFalse(data['games'][0]['completed'])
        self.assertEqual(data['games'][0]['display_status'],'Result needs review')
        self.assertIn('Some saved history or official results could not be verified',season.render(data))

    def test_displayed_yes_no_alignment_is_independent_of_cash_flow(self):
        g=dict(home='SEA',away='NE',completed=True,
               official_result=dict(state='final',home_score=13,away_score=10),
               activity=dict(realized_profit='999'))
        for side,team,kind in [('YES','SEA','aligned'),('NO','NE','aligned'),('YES','NE','opposed'),('NO','SEA','opposed')]:
            self.assertIn('result-mark '+kind,season.contract_result(g,side,team))
        g['official_result']['away_score']=13
        self.assertIn('result-mark tie',season.contract_result(g,'NO','SEA'))
        g['completed']=False
        self.assertEqual(season.contract_result(g,'YES','SEA'),'')
        g['completed']=True;g['official_result']['state']='unresolved'
        self.assertEqual(season.contract_result(g,'YES','SEA'),'')

    def test_integrated_icon_precedes_badge_and_labels_are_clean(self):
        self.capture()
        data=self.view();row=data['games'][0]
        row['outcomes'][0]['historical']=dict(route=dict(side='yes',yes_team='SEA',cost=dict(price='.6',total='.62',estimated_fee='.02'),book_received_at=AT,ticker='fixture'),outcome=dict(payout=dict(central='.7'),displayed_win='70%'),forecast_updated_at=AT,forecast_verified_at=AT,fee_model='fixture',source_bundle='fixture')
        html=season.render(data)
        contract=html.split('<td data-sort="YES SEA">',1)[1].split('</td>',1)[0]
        self.assertLess(contract.index('result-mark opposed'),contract.index('class="contract"'))
        self.assertIn('data-sort="YES SEA"',html)
        self.assertNotIn('<small>Historical</small>',html)
        self.assertNotIn('<small>Captured ',html)
        self.assertIn('separate from your payout or profit',html)
