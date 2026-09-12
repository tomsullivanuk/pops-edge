from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import uuid
from unittest.mock import patch
import nfl_schedule as schedule
from nfl_performance import Performance
from tests.test_nfl_performance import Clock, Transport, book
from tests.test_nfl_comparison_board import source

AT='2026-09-12T16:00:00+00:00'
CUT='2026-09-13T17:00:00+00:00'

def games():
    names={v:k for k,v in schedule.FULL_NAMES.items()}
    pairs=[('SEA','NE'),('LAR','SF')]
    rest=sorted(set(names)-{'SEA','NE','LAR','SF'})
    pairs += list(zip(rest[::2],rest[1::2]))
    return [dict(id=str(uuid.UUID(int=i+1)),season=2026,week=1,seasonType='REG',weekType='REG',
                 time='2026-09-10T00:20:00Z' if i<2 else CUT,status='SCHEDULED',neutralSite=False,
                 homeTeam={'fullName':names[h],'id':h},awayTeam={'fullName':names[a],'id':a}) for i,(h,a) in enumerate(pairs)]

class StartingCohortTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.clock=Clock();self.clock.value=AT;self.games=games()
    def initialize(self):
        folder,_=schedule.capture(self.root/'schedule',2026,1,lambda _: (200,source(self.games)),self.clock)
        self.engine=Performance.initialize(self.root/'store','owner-approved fixture',self.clock,partial_week1_schedule=folder)
        return self.engine
    def test_fixed_members_exclusions_and_replay(self):
        e=self.initialize();r=e.save_report(2026,1,AT)
        self.assertEqual(r['population'],16);self.assertEqual(r['starting_cohort']['eligible_population'],14)
        self.assertEqual(r['coverage']['excluded-starting-cohort'],2)
        self.assertEqual(r['cutoff'],CUT)
        self.assertEqual(e.replay_report(e.root/'reports'/(r['report_id']+'.json')),r)
        self.assertNotIn('starting_cohort',e.report(2026,2,AT))
    def test_reject_third_started_game_or_unknown_time(self):
        for time in (None,AT):
            with self.subTest(time=time):
                self.games[2]['time']=time
                with self.assertRaises(ValueError):self.initialize()
                self.assertFalse((self.root/'store/activation.json').exists())
    def test_observed_start_before_activation_rejected_without_activation(self):
        g=self.games[2];h=g['homeTeam']['id'];a=g['awayTeam']['id']
        g['summary']=dict(gameId=g['id'],phase='IN_PROGRESS',quarter='Q1',startTime=AT,
                         homeTeam=dict(teamId=h),awayTeam=dict(teamId=a))
        with self.assertRaises(ValueError):self.initialize()
        self.assertFalse((self.root/'store/activation.json').exists())
    def test_live_summary_without_start_time_rejected(self):
        g=self.games[2];h=g['homeTeam']['id'];a=g['awayTeam']['id']
        for phase,quarter in [('IN_PROGRESS','Q1'), ('IN_PROGRESS',None), (None,'Q1'), ('UNKNOWN',None)]:
            with self.subTest(phase=phase,quarter=quarter):
                g['summary']=dict(gameId=g['id'],phase=phase,quarter=quarter,
                                 homeTeam=dict(teamId=h),awayTeam=dict(teamId=a))
                with self.assertRaises(ValueError):self.initialize()
                self.assertFalse((self.root/'store/activation.json').exists())

    def test_tampered_schedule_fails_open(self):
        e=self.initialize();key=e.activation['starting_cohort']['files']['source.html']
        (e.root/'blobs'/key).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):Performance(e.root,self.clock)
        with self.assertRaises(ValueError):e.report(2026,1,AT)
    def test_excluded_actual_start_does_not_close_remaining_cutoff(self):
        e=self.initialize();g=self.games[0]
        g['summary']=dict(gameId=g['id'],phase='FINAL',quarter='END_OF_GAME',startTime='2026-09-10T00:23:21Z',
                         homeTeam=dict(teamId='SEA',score={'total':13}),awayTeam=dict(teamId='NE',score={'total':10}))
        e.observe_results(2026,1,lambda _: (200,source(self.games)))
        r=e.report(2026,1,AT);self.assertEqual(r['cutoff'],CUT);self.assertFalse(r['frozen'])
        self.assertEqual(r['coverage']['excluded-starting-cohort'],2)
    def test_missing_fixed_member_blocks_cutoff(self):
        e=self.initialize();e.observe_results(2026,1,lambda _: (200,source(self.games[:-1])))
        r=e.report(2026,1,AT);self.assertIsNone(r['cutoff']);self.assertEqual(r['population'],16)
    def test_closed_cutoff_cannot_reopen(self):
        e=self.initialize();self.clock.value='2026-09-13T18:00:00+00:00'
        for g in self.games[2:]:g['time']='2026-09-14T17:00:00+00:00'
        e.observe_results(2026,1,lambda _: (200,source(self.games)))
        self.assertEqual(e.report(2026,1,self.clock())['cutoff'],CUT)
    def test_full_week_mode_keeps_original_cutoff(self):
        e=Performance.initialize(self.root/'normal','fixture',self.clock)
        e.observe_results(2026,1,lambda _: (200,source(self.games)))
        self.assertTrue(e.report(2026,1,AT)['frozen'])
    def test_partial_capture_selection_and_common_cutoff(self):
        e=self.initialize()
        # Workbook and quote only for one included game; other missing games remain visible.
        g=self.games[2];h=g['homeTeam']['id'];a=g['awayTeam']['id']
        from tests.test_nfl_refresh import workbook
        def change(s):
            s['A6']='1';s['B6']=h;s['E6']=a;s['D6']=.60;s['G6']=.39
            s['A8']='Updated September 12, 2026 at 10:00 AM EDT'
        quote=dict(ticker='fixture',value='0.56',bid='0.54',ask='0.58',started_at=AT,received_at=AT,metadata_received_at=AT)
        def midpoint(game,*args):
            if game['game_id']!=g['id']:raise ValueError('No book')
            return quote
        with patch('nfl_performance.sources.midpoint',side_effect=midpoint):
            e.refresh(workbook(change),'week.xlsx',2026,1,schedule_transport=lambda _: (200,source(self.games)),market_transport=Transport())
            r=e.report(2026,1,AT)
            self.assertIsNotNone(r['selected_import']);self.assertEqual(r['coverage']['candidate'],1)
            self.assertEqual(r['coverage']['missing-capture'],13)
            self.clock.value=CUT
            g['summary']=dict(gameId=g['id'],phase='FINAL',quarter='END_OF_GAME',homeTeam=dict(teamId=h,score={'total':14}),awayTeam=dict(teamId=a,score={'total':7}))
            self.clock.value='2026-09-13T21:00:00+00:00'
            e.observe_results(2026,1,lambda _: (200,source(self.games)))
            r=e.report(2026,1,self.clock());self.assertEqual(r['paired_games'],1)
            self.assertEqual(r['coverage']['excluded-starting-cohort'],2)

    def test_automatic_selection_uses_partial_cutoff(self):
        from nfl_refresh import Workflow
        e=self.initialize();w=Workflow(self.root/'app')
        observe=e.observe_results
        with patch.object(e,'observe_results',side_effect=lambda season,week:observe(season,week,lambda _: (200,source(self.games)))),patch('nfl_refresh.kalshi.utc',self.clock):
            self.assertEqual(w.automatic_comparison_week(e,2026,[1]),1)
            self.assertEqual(e.report(2026,1,AT)['coverage']['excluded-starting-cohort'],2)
