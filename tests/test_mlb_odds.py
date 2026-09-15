"""Operational odds contract and manual lifecycle; entirely offline fixtures."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mlb_odds as odds
from mlb_odds_store import OddsStore

AT = datetime(2026, 9, 15, 14, tzinfo=timezone.utc)
DAY = '2026-09-15'


def game(pk=777, hour=23, number=None):
    return dict(gamePk=pk, season='2026', gameType='R', gameDate=f'2026-09-15T{hour:02}:15:00Z',
                doubleHeader='S' if number else 'N', gameNumber=number or 1,
                status=dict(detailedState='Scheduled'), venue=dict(name='Fixture Park'),
                teams=dict(away=dict(team=dict(id=135, name='San Diego Padres', abbreviation='SD')),
                           home=dict(team=dict(id=137, name='San Francisco Giants', abbreviation='SF'))))


def schedule(games=None):
    records=[game()] if games is None else games
    return odds.encode(dict(totalGames=len(records), dates=[dict(date=DAY,totalGames=len(records),games=records)] if records else []))


def market(side='home', ticker=None, hour=7, number=None):
    # Synthetic operational fixture based on the retained Sept 9 two-day rule family.
    who='San Francisco' if side=='home' else 'San Diego'
    matchup='San Diego vs San Francisco'+(f' (Game {number})' if number else '')
    fields=dict(match=matchup,day='Sep 15, 2026',clock=f'{hour}:15 PM',zone='EDT')
    return dict(ticker=ticker or f'KXMLBGAME-26SEP151915SDSF-{"SF" if side=="home" else "SD"}',
                title='San Diego vs San Francisco Winner?',market_type='binary',status='open',
                yes_sub_title=who,no_sub_title=who,notional_value_dollars='1.0000',
                rules_primary=f'If {who} wins the {matchup} professional baseball game originally scheduled for Sep 15, 2026 at {hour}:15 PM EDT, then the market resolves to Yes.',
                rules_secondary=odds.SETTLEMENT.format(**fields)+'\n\n'+odds.DISCLAIMER)


def book(no=None,yes=None):
    return odds.encode(dict(orderbook_fp=dict(yes_dollars=[['0.5400','5.00']] if yes is None else yes,
                                            no_dollars=[['0.4400','2.00']] if no is None else no)))


class Clock:
    def __init__(self):self.seconds=0
    def now(self):return (AT+timedelta(seconds=self.seconds)).isoformat()
    def mono(self):return self.seconds


class Feed:
    def __init__(self, games=None):
        self.calls=[];self.games=games;self.markets=[market('away'),market('home')];self.fail=None;self.pages=None
    def __call__(self,provider,route,params):
        self.calls.append((provider,route,params))
        if self.fail and self.fail(route):raise ConnectionError('simulated offline failure')
        if provider=='mlb':return 200,schedule(self.games)
        if route=='/markets':
            if self.pages:return 200,odds.encode(self.pages(params))
            return 200,odds.encode(dict(markets=self.markets,cursor=''))
        return 200,book()


class Interpretation(unittest.TestCase):
    def test_schedule_identity_survives_order_and_missing_data(self):
        records=[game(999),game(100)]
        records[0]['teams']['away']['team']['name']='Other Away'
        rows=odds.schedule_games(schedule(records),DAY,AT.isoformat())
        self.assertEqual(rows[0]['game_pk'],999)
        self.assertEqual(rows[0]['away']['name'],'Other Away')
        self.assertEqual(rows[0]['id'],'mlb:999')
        records[0].pop('gameDate')
        rows=odds.schedule_games(schedule(records),DAY,AT.isoformat())
        self.assertEqual(len(rows),2);self.assertTrue(rows[0]['reasons'])

    def test_full_rules_no_fuzzy_or_prefix_admission(self):
        self.assertEqual(odds.market_identity(market())['winner'],'san francisco giants')
        changes=[('rules_primary',' Only the first five innings count.'),
                 ('rules_secondary',' Winning payout is zero.'),
                 ('rules_primary',' If San Francisco wins, settlement is zero dollars.')]
        for field,suffix in changes:
            m=market();m[field]+=suffix
            with self.subTest(field=field,suffix=suffix),self.assertRaises(ValueError):odds.market_identity(m)
        for key,value in [('yes_sub_title','San Diego'),('notional_value_dollars','0.5'),('status','closed')]:
            m=market();m[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):odds.market_identity(m)
        m=market();m['rules_primary']=m['rules_primary'].replace('EDT','EST')
        m['rules_secondary']=m['rules_secondary'].replace('EDT','EST')
        with self.assertRaises(ValueError):odds.market_identity(m)

    def test_doubleheader_exact_time_number_and_ambiguity(self):
        rows=odds.schedule_games(schedule([game(1,17,1),game(2,23,2)]),DAY,AT.isoformat())
        markets=[market(hour=1,number=1),market(ticker='KXMLBGAME-SECOND-SF',number=2)]
        mapped,issues=odds.map_markets(rows,markets)
        self.assertFalse(issues);self.assertEqual(len(mapped['mlb:1','home']),1);self.assertEqual(len(mapped['mlb:2','home']),1)
        markets[0]['rules_primary']=markets[0]['rules_primary'].replace('Game 1','Game 2')
        markets[0]['rules_secondary']=markets[0]['rules_secondary'].replace('Game 1','Game 2')
        mapped,issues=odds.map_markets(rows,markets);self.assertEqual(len(mapped['mlb:1','home']),0)
        rows[1]['start']=rows[0]['start'];rows[1]['number']=1
        mapped,issues=odds.map_markets(rows,[market(hour=1,number=1)])
        self.assertTrue(issues);self.assertTrue(all(not x for x in mapped.values()))

    def test_exact_book_offer_depth_and_invalid_shapes(self):
        result=odds.best_yes_offer(book())
        self.assertEqual(result['cents'],'56.0000');self.assertEqual(result['quantity'],'2.00')
        self.assertEqual(odds.best_yes_offer(book(yes=[]))['cents'],'56.0000')
        for raw in [book(no=[]),book(no=[['0.4400','0.50']]),book(no=[['1.1000','2.00']]),
                    book(no=[['0.4400','0.00']]),book(no=[['0.4400','2.00']]*2),book(yes=[['0.9000','2.00']]),
                    b'{"orderbook_fp":{"yes_dollars":[],"no_dollars":[],"no_dollars":[]}}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):odds.best_yes_offer(raw)

    def test_empty_schedule_mismatch_and_status(self):
        self.assertEqual(odds.schedule_games(schedule([]),DAY,AT.isoformat()),[])
        p=odds.decode(schedule());p['totalGames']=2
        with self.assertRaises(ValueError):odds.schedule_games(odds.encode(p),DAY,AT.isoformat())
        with self.assertRaises(ValueError):odds.schedule_games(schedule([game(),game()]),DAY,AT.isoformat())
        for change in [('gameType','P'),('resumeDate','2026-09-16'),('rescheduledFromDate','2026-09-14'),('startTimeTBD',True)]:
            g=game();g[change[0]]=change[1]
            self.assertTrue(odds.schedule_games(schedule([g]),DAY,AT.isoformat())[0]['reasons'])

    def test_age_start_and_clock_boundaries(self):
        g=odds.schedule_games(schedule(),DAY,AT.isoformat())[0]
        q={k:AT.isoformat() for k in ('started_at','completed_at','schedule_started_at','catalog_started_at')}
        self.assertEqual(odds.quote_state(g,q,(AT+timedelta(seconds=299)).isoformat()),'current')
        self.assertEqual(odds.quote_state(g,q,(AT+timedelta(seconds=300)).isoformat()),'stale')
        self.assertEqual(odds.quote_state(g,q,(AT-timedelta(seconds=1)).isoformat()),'clock-uncertain')
        self.assertEqual(odds.quote_state(g,q,g['start']),'pregame-ended')


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mlb-odds-test-',dir='/private/tmp')
        self.root=Path(self.temp.name)/'odds';self.feed=Feed();self.clock=Clock()
        self.store=OddsStore(self.root,fetch=self.feed,clock=self.clock.now,monotonic=self.clock.mono)
    def tearDown(self):self.temp.cleanup()

    def test_read_is_inert_and_refresh_downloads_retain_exact_sources(self):
        self.assertIsNone(self.store.read(DAY)['result']);self.assertFalse(self.root.exists());self.assertFalse(self.feed.calls)
        result=self.store.refresh(DAY);self.assertEqual(len(self.feed.calls),4)
        state=self.store.read(DAY);self.assertEqual(state['attempt']['state'],'complete')
        self.assertEqual(result['games'][0]['home_quote']['cents'],'56.0000')
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        download=self.store.download(DAY,state['selected']['id'],'raw/000.body')
        self.assertEqual(download,schedule());self.store.read(DAY)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_partial_books_and_relisted_market_no_arbitrary_choice(self):
        self.feed.fail=lambda route:route.endswith('-SF/orderbook')
        self.store.refresh(DAY);state=self.store.read(DAY)
        self.assertEqual(state['attempt']['state'],'partial');g=state['result']['games'][0]
        self.assertIsNone(g['home_quote']);self.assertIsNotNone(g['away_quote'])
        self.feed.fail=None;self.feed.markets.append(market(ticker='KXMLBGAME-RELIST-SF'))
        self.store.refresh(DAY);g=self.store.read(DAY)['result']['games'][0]
        self.assertIsNone(g['home_quote']);self.assertIn('Ambiguous',g['home_reason'])

    def test_failed_discovery_retains_previous_selection_and_dates(self):
        self.store.refresh(DAY);old=self.store.read(DAY);self.clock.seconds=10
        self.feed.pages=lambda params:dict(markets=[],cursor='loop')
        with self.assertRaisesRegex(ValueError,'cursor repeats'):self.store.refresh(DAY)
        new=self.store.read(DAY)
        self.assertEqual(new['selected'],old['selected']);self.assertEqual(new['result'],old['result'])
        self.assertEqual(new['attempt']['state'],'failed');self.assertNotEqual(new['attempt']['id'],new['selected']['id'])
        self.feed.pages=None;self.store.refresh(DAY);self.assertEqual(self.store.read(DAY)['attempt']['state'],'complete')

    def test_request_failure_and_invalid_catalog_do_not_infer_no_games(self):
        self.feed.fail=lambda route:True
        with self.assertRaises(ValueError):self.store.refresh(DAY)
        self.assertIsNone(self.store.read(DAY)['result'])
        self.feed.fail=None;self.feed.pages=lambda params:dict(markets=[])
        with self.assertRaises(ValueError):self.store.refresh(DAY)
        self.assertIsNone(self.store.read(DAY)['result'])

    def test_no_games_has_authority_no_catalog_calls(self):
        self.feed.games=[];self.store.refresh(DAY)
        state=self.store.read(DAY);self.assertEqual(state['result']['games'],[])
        self.assertEqual(len(self.feed.calls),1);self.assertIn('confirmed no games',state['attempt']['message'])

    def test_integrity_and_path_failures_are_visible(self):
        self.store.refresh(DAY);state=self.store.read(DAY)
        p=self.root/'attempts'/state['selected']['id']/'raw/000.body';p.write_bytes(b'changed')
        self.assertIn('changed',self.store.read(DAY)['error']);self.assertIsNone(self.store.read(DAY)['result'])
        with self.assertRaises(ValueError):self.store.download(DAY,state['selected']['id'],'../anything')
        with self.assertRaises(ValueError):self.store.read('../anything')

    def test_symlinks_and_competing_writer_rejected(self):
        self.root.symlink_to(Path(self.temp.name)/'elsewhere')
        with self.assertRaises(ValueError):self.store.refresh(DAY)
        self.root.unlink()
        with self.store.writer():
            other=OddsStore(self.root,fetch=self.feed,clock=self.clock.now,monotonic=self.clock.mono)
            with self.assertRaisesRegex(ValueError,'Another'):other.refresh(DAY)

    def test_interrupted_candidate_never_selected(self):
        self.store.refresh(DAY);old=self.store.read(DAY)
        original=self.store._write
        def kill(path,raw,**kw):
            if path.name=='result.json':raise KeyboardInterrupt()
            original(path,raw,**kw)
        with patch.object(self.store,'_write',side_effect=kill),self.assertRaises(KeyboardInterrupt):self.store.refresh(DAY)
        restarted=OddsStore(self.root,fetch=self.feed,clock=self.clock.now,monotonic=self.clock.mono)
        state=restarted.read(DAY);self.assertEqual(state['selected'],old['selected']);self.assertEqual(state['attempt']['state'],'interrupted')
        restarted.refresh(DAY);self.assertEqual(restarted.read(DAY)['attempt']['state'],'complete')

    def test_failed_selection_publication_preserves_prior_bundle(self):
        self.store.refresh(DAY);old=self.store.read(DAY)
        original=self.store._save_state
        def fail_once(state):
            if state['attempt']['state'] in ('complete','partial'):
                raise OSError('simulated publication failure')
            original(state)
        with patch.object(self.store,'_save_state',side_effect=fail_once),self.assertRaises(OSError):self.store.refresh(DAY)
        value=self.store.read(DAY)
        self.assertEqual(value['selected'],old['selected']);self.assertEqual(value['result'],old['result'])
        self.assertEqual(value['attempt']['state'],'failed')
        self.store.refresh(DAY);self.assertEqual(self.store.read(DAY)['attempt']['state'],'complete')

    def test_corrupt_day_state_degrades_to_visible_error(self):
        self.store.refresh(DAY)
        for value in [[], {'schema':odds.VERSION,'day':DAY},
                      {'schema':odds.VERSION,'day':DAY,'selected':None,'attempt':[]}]:
            (self.root/'days'/f'{DAY}.json').write_bytes(odds.encode(value))
            result=self.store.read(DAY)
            self.assertTrue(result['error']);self.assertIsNone(result['result'])

    def test_clock_change_blocks_refresh_and_future_capture(self):
        self.clock.seconds=-1
        with self.assertRaises(ValueError):self.store.refresh(DAY)
        self.assertFalse(self.feed.calls)


if __name__=='__main__':unittest.main()
