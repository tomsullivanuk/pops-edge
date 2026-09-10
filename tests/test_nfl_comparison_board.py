from copy import deepcopy
from datetime import datetime,timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import nfl_schedule as s
import nfl_comparison_board as b
import nfl_forecast_import as f
import retrieve_kalshi_nfl as k
from nfl_board_view import render, sheet_rows

AT='2026-09-09T15:00:00+00:00'
ID='a8fb0d78-4feb-11f1-abca-2c54536568a9'


def source(games=None):
    game=dict(id=ID,season=2026,week=1,seasonType='REG',weekType='REG',time='2026-09-10T00:20:00Z',status='SCHEDULED',neutralSite=False,
              homeTeam=dict(fullName='Seattle Seahawks'),awayTeam=dict(fullName='New England Patriots'),venue=dict(name='Lumen Field'))
    query=dict(queryKey=['useFetchFootballWeeklyGameDetails',dict(season='2026',seasonType='REG',week=1)],state=dict(status='success',data=games if games is not None else [game]))
    return ('<script>self.__next_f.push('+json.dumps([1,'0:'+json.dumps(query)+'\n'])+')</script>').encode()


def forecast():
    image=b'synthetic image'
    receipt=dict(schema=f.VERSION,source_sha256=f.digest(image),imported_at=AT,mime='image/png')
    review=dict(source_sha256=f.digest(image),season=2026,week=1,expected_games=1,updated_at=AT,metadata_reviewed=True,
                rows=[dict(home='SEA',away='NE',home_win='68.4%',away_win='31.1%',neutral=False,reviewed=True)])
    record=dict(schema=f.VERSION,source=receipt,review=review,reviewer='test',supersedes=None,verified_at=AT,rows=f.validate(review,receipt))
    record['verification_id']=f.digest(f.encode(dict(review=review,reviewer='test',supersedes=None)))
    return record,image,receipt


def market(team='Seattle',code='SEA'):
    game='New England vs Seattle';day='Sep 9, 2026';sport='professional football'
    return dict(ticker='KXNFLGAME-26SEP09NESEA-'+code,event_ticker='KXNFLGAME-26SEP09NESEA',market_type='binary',status='active',yes_sub_title=team,no_sub_title=team,
                rules_primary=f'If {team} wins the {game} {sport} game originally scheduled for {day}, then the market resolves to Yes.',
                rules_secondary=b.SECONDARY.format(game=game,sport=sport,day=day,fair='fair market price'))


def inputs():
    fr,_,_=forecast();sr=dict(season=2026,week=1,started_at=AT,completed_at=AT,rows=s.parse(source(),2026,1))
    markets=[market(),market('New England','NE')];rows=[]
    for m in markets:
        rows.append(dict(ticker=m['ticker'],event_ticker=m['event_ticker'],state='captured',book_started_at=AT,book_received_at=AT,metadata_received_at=AT,
                         offers=dict(yes=dict(offer_price='.60',offer_quantity='10'),no=dict(offer_price='.42',offer_quantity='20'))))
    kr=dict(state='complete',run_started_at=AT,run_completed_at=AT,series_metadata=dict(ticker='KXNFLGAME',fee_type='quadratic_with_maker_fees',fee_multiplier=1),rows=rows)
    return fr,sr,kr,markets


class NFLBoardTests(unittest.TestCase):
    def test_official_schedule_scope_and_neutral(self):
        self.assertEqual(s.parse(source(),2026,1)[0]['home'],'SEA')
        with self.assertRaises(ValueError):s.parse(source(),2026,2)
        raw=source().replace(b'false',b'true')
        self.assertTrue(s.parse(raw,2026,1)[0]['neutral'])

    def test_duplicate_schedule_and_missing_query_rejected(self):
        query=json.loads(json.loads(source().decode().split('push(')[1].split(')</script>')[0])[1].split(':',1)[1])
        game=query['state']['data'][0]
        with self.assertRaises(ValueError):s.parse(source([game,game]),2026,1)
        with self.assertRaises(ValueError):s.parse(b'<html>changed website</html>',2026,1)
        game['time']='2026-09-10T00:20:00'
        with self.assertRaises(ValueError):s.parse(source([game]),2026,1)

    def test_schedule_capture_failure_and_replay(self):
        with TemporaryDirectory() as tmp:
            run,r=s.capture(tmp,2026,1,lambda _: (200,source()),lambda:AT)
            self.assertEqual(r,s.replay(run))
            (run/'source.html').write_bytes(b'changed')
            with self.assertRaises(ValueError):s.replay(run)
        with TemporaryDirectory() as tmp:
            run,r=s.capture(tmp,2026,1,lambda _: (503,b'unavailable'),lambda:AT)
            self.assertIsNotNone(r['error'])
            with self.assertRaises(ValueError):s.replay(run)

    def test_full_rule_matching_rejects_conflicting_addition(self):
        self.assertEqual(b.strict_market(market())[1],'SEA')
        m=market();m['rules_secondary']+=' Ties resolve to No.'
        with self.assertRaises(ValueError):b.strict_market(m)
        m=market();m['yes_sub_title']='Boston'
        with self.assertRaises(ValueError):b.strict_market(m)

    def test_payout_range_and_no_tie_normalization(self):
        p=b.payout_range('68.4%','31.1%')
        self.assertEqual(p,dict(low='0.6860',central='0.6865',high='0.6870'))
        p=b.payout_range('50.0%','50.0%');self.assertEqual(p['low'],'0.4995');self.assertEqual(p['high'],'0.5005')
        self.assertEqual(b.D(b.payout_range('100.0%','0.0%')['high']),b.D(1))

    def test_fee_single_fill_rounding_including_subcent_price(self):
        self.assertEqual(b.one_contract_cost('.50')['total'],'0.52')
        self.assertEqual(b.one_contract_cost('.055')['total'],'0.06')
        self.assertEqual(b.one_contract_cost('.99')['total'],'1.00')

    def test_cheaper_equivalent_route_and_all_games_visible(self):
        result=b.derive(*inputs(),AT);g=result['games'][0]
        self.assertEqual(result['ranked_games'],1)
        sea=g['outcomes'][0]
        self.assertEqual(sea['best']['side'],'no');self.assertEqual(sea['best']['yes_team'],'NE')
        self.assertEqual(sea['best']['cost']['total'],'0.44')
        self.assertEqual(len(sea['routes']),2)
        self.assertEqual(g['rank'],1)

    def test_stale_quotes_visible_unranked(self):
        i=inputs();later='2026-09-09T15:05:01+00:00'
        result=b.derive(*i,later);self.assertEqual(result['ranked_games'],0);self.assertEqual(result['scheduled_games'],1)
        self.assertIn('Quote is stale',result['games'][0]['outcomes'][0]['routes'][0]['reasons'])
        self.assertEqual(b.derive(*i,'2026-09-09T15:05:00+00:00')['ranked_games'],1)

    def test_kickoff_exclusion_and_future_input(self):
        i=inputs();i[1]['rows'][0]['kickoff']=AT
        self.assertIn('Game has started',b.derive(*i,AT)['games'][0]['issues'])
        with self.assertRaises(ValueError):b.derive(*inputs(),'2026-09-09T14:59:59+00:00')

    def test_neutral_role_and_missing_forecast(self):
        i=inputs();i[1]['rows'][0]['neutral']=True;i[0]['rows'][0]['neutral']=True
        self.assertEqual(b.derive(*i,AT)['ranked_games'],1)
        i[0]['rows'][0]['neutral']=False
        self.assertIn('Neutral-site mismatch',b.derive(*i,AT)['games'][0]['issues'])
        i=inputs();i[0]['rows'][0]['home']='NE';i[0]['rows'][0]['away']='SEA'
        result=b.derive(*i,AT);self.assertEqual(result['ranked_games'],0)
        self.assertTrue(any('Forecast not matched' in x['reason'] for x in result['diagnostics']))

    def test_ambiguous_events_and_duplicate_markets(self):
        for suffix in ['KXNFLGAME-OTHER-SEA','KXNFLGAME-26SEP09NESEA-OTHER']:
            i=inputs();m=deepcopy(i[3][0]);q=deepcopy(i[2]['rows'][0]);m['ticker']=q['ticker']=suffix
            m['event_ticker']=q['event_ticker']=suffix.rsplit('-',1)[0];i[3].append(m);i[2]['rows'].append(q)
            result=b.derive(*i,AT)
            # A duplicate Seattle contract must not be selected; unrelated NE market can remain usable.
            self.assertTrue(any(r['reasons'] for r in result['games'][0]['outcomes'][0]['routes']))

    def test_partial_fee_depth_and_bad_rule_fail_visible(self):
        for change in ['partial','fee','depth','rule','date','status']:
            i=inputs()
            if change=='partial':i[2]['state']='partial'
            if change=='fee':i[2]['series_metadata']['fee_multiplier']=2
            if change=='depth':
                for q in i[2]['rows']:
                    for offer in q['offers'].values():offer['offer_quantity']='0.5'
            if change=='rule':
                for m in i[3]:m['rules_secondary']+=' contradictory clause'
            if change=='date':i[1]['rows'][0]['kickoff']='2026-09-12T00:20:00Z'
            if change=='status':i[1]['rows'][0]['status']='POSTPONED'
            with self.subTest(change=change):self.assertEqual(b.derive(*i,AT)['ranked_games'],0)

    def test_off_window_catalog_is_not_board_diagnostic(self):
        i=inputs();outside=market();outside['ticker']='KXNFLGAME-OTHER-SEA';outside['rules_secondary']='unsupported'
        i[3].append(outside)
        self.assertEqual(b.derive(*i,AT)['diagnostics'],[])

    def test_verified_source_chain(self):
        record,image,receipt=forecast();b.validated_forecast(record,image,receipt)
        record['rows'][0]['home_probability']='.99'
        with self.assertRaises(ValueError):b.validated_forecast(record,image,receipt)

    def test_board_bundle_replay_and_tamper(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);record,image,receipt=forecast();source_dir=root/'forecasts/sources'/receipt['source_sha256'];source_dir.mkdir(parents=True)
            (source_dir/'image').write_bytes(image);(source_dir/'receipt.json').write_bytes(f.encode(receipt))
            verified=root/'verified.json';verified.write_bytes(f.encode(record))
            sched,_=s.capture(root/'schedules',2026,1,lambda _: (200,source()),lambda:AT)
            def transport(route,params):
                if route.startswith('/series'):obj=dict(series=dict(ticker='KXNFLGAME',product_metadata=dict(scope='Game'),fee_type='quadratic_with_maker_fees',fee_multiplier=1))
                elif route=='/markets':obj=dict(markets=[market(),market('New England','NE')],cursor='')
                else:obj=dict(orderbook_fp=dict(yes_dollars=[['.60','10']],no_dollars=[['.35','20']]))
                return 200,json.dumps(obj).encode()
            capture,_=k.capture(root/'kalshi','2026-09-09','2026-09-14',transport,lambda:AT)
            with patch.object(k,'utc',return_value=AT):folder,data=b.build(root/'boards',verified,root/'forecasts',sched,capture)
            self.assertEqual(data,b.replay(folder));self.assertEqual(data['ranked_games'],1)
            activity=root/'activity.csv'
            activity.write_text('type,Market_Ticker,Direction,Price_In_Cents,Amount_In_Dollars,Fee_In_Dollars,Original_Date\nTrade,KXNFLGAME-26SEP09NESEA-NE,No,38,15.7,0.25,2026-09-09T15:30:00Z\n')
            with patch.object(k,'utc',return_value='2026-09-09T16:00:00Z'):
                overlay,annotated=b.attach_activity(folder,activity,root/'boards')
                repeat,again=b.attach_activity(overlay,activity,root/'boards')
            self.assertEqual(annotated,b.replay(overlay))
            self.assertEqual(again,b.replay(repeat))
            self.assertEqual(len(again['activity']['trades']),1)
            self.assertEqual(annotated['generated_at'],data['generated_at'])
            self.assertEqual(annotated['games'],data['games'])
            self.assertEqual(annotated['activity']['trades'][0]['team'],'SEA')
            self.assertIn('Recorded wager',(overlay/'board.html').read_text())
            (overlay/'inputs/activity.csv').write_text('tampered')
            with self.assertRaises(ValueError):b.replay(overlay)
            (folder/'inputs/kalshi/started.json').write_text('{}')
            with self.assertRaises(ValueError):b.replay(folder)

    def test_betsheet_sorts_gross_discrepancy_and_keeps_unavailable(self):
        data=b.derive(*inputs(),AT)
        rows=sheet_rows(data)
        self.assertEqual(rows[0]['outcome']['team'],'SEA')
        self.assertEqual(rows[0]['gap'],b.D('.2465'))
        self.assertEqual(rows[0]['route']['side'],'no')
        html=render(data)
        self.assertIn('class="betsheet"',html)
        self.assertIn('ELWAY win',html)
        self.assertIn('Difference after fee',html)
        self.assertNotIn('<article',html)
        for route in data['games'][0]['outcomes'][0]['routes']:route['usable']=False
        rows=sheet_rows(data)
        self.assertIsNone(rows[-1]['gap'])
        data['games'][0]['kickoff']=None
        self.assertIn('TBD',render(data))

    def test_html_escapes_and_keeps_snapshot_caveats(self):
        data=b.derive(*inputs(),AT);data['games'][0]['venue']='<script>alert(1)</script>'
        html=render(data);self.assertNotIn('<script>alert(1)</script>',html);self.assertIn('&lt;script&gt;',html)
        self.assertIn('not confidence intervals',html);self.assertIn('Archived prices',html)

if __name__=='__main__':unittest.main()
