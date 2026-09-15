"""Build a saved, read-only NFL comparison board from explicit local inputs."""
from __future__ import annotations
import argparse
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import re
import sys
import uuid
from zoneinfo import ZoneInfo
import nfl_forecast_import as forecast
import nfl_schedule as schedule
import retrieve_kalshi_nfl as kalshi

VERSION='nfl-comparison-board-v1'
D=Decimal
NY=ZoneInfo('America/New_York')
GUARDS=dict(quote_seconds=300,schedule_seconds=86400,forecast_seconds=8*86400)
CITIES=['Arizona','Atlanta','Baltimore','Buffalo','Carolina','Chicago','Cincinnati','Cleveland','Dallas','Denver','Detroit','Green Bay','Houston','Indianapolis','Jacksonville','Kansas City','Las Vegas','Los Angeles C','Los Angeles R','Miami','Minnesota','New England','New Orleans','New York G','New York J','Philadelphia','Pittsburgh','San Francisco','Seattle','Tampa Bay','Tennessee','Washington']
ALIASES={name:code for name,code in zip(CITIES,schedule.NAMES)}
ALIASES.update(schedule.FULL_NAMES)
ALIASES.update({'LA Rams':'LAR','LA Chargers':'LAC','NY Giants':'NYG','NY Jets':'NYJ'})
MATCHING_VERSION='nfl-market-aliases-v2'
ABBREVIATED_ALIASES={
    'ARI Cardinals':'ARI','ATL Falcons':'ATL','BAL Ravens':'BAL','BUF Bills':'BUF',
    'CAR Panthers':'CAR','CHI Bears':'CHI','CIN Bengals':'CIN','CLE Browns':'CLE',
    'DAL Cowboys':'DAL','DEN Broncos':'DEN','DET Lions':'DET','GB Packers':'GB',
    'HOU Texans':'HOU','IND Colts':'IND','JAC Jaguars':'JAX','KC Chiefs':'KC',
    'LV Raiders':'LV','MIA Dolphins':'MIA','MIN Vikings':'MIN','NE Patriots':'NE',
    'NO Saints':'NO','PHI Eagles':'PHI','PIT Steelers':'PIT','SF 49ers':'SF',
    'SEA Seahawks':'SEA','TB Buccaneers':'TB','TEN Titans':'TEN','WAS Commanders':'WAS',
}


SECONDARY=('The following market refers to the team who wins the {game} {sport} game originally scheduled for {day}. '
           'If the game ends in a tie, the market will resolve to $0.50 for each team. '
           'If the game is postponed but begins within 48 hours from its originally scheduled start time, the market will remain open and resolve based on the official final result. '
           'If the game is not started within 48 hours, the market will resolve to a {fair}.\n\n'
           'Kalshi is not affiliated, associated, authorized, endorsed by, or in any way officially connected with the Governing League. '
           'All trademarks, logos, and brand names are the property of their respective owners.')


def strict_market(m,matching_version=None):
    if matching_version not in (None,MATCHING_VERSION):raise ValueError('Unsupported market matching version')
    aliases=ALIASES if matching_version is None else {**ALIASES,**ABBREVIATED_ALIASES}
    rule=kalshi.market_rule(m)
    match=kalshi.RULE.fullmatch(m['rules_primary'])
    sport='Pro Football' if ' Pro Football game ' in m['rules_primary'] else 'professional football'
    allowed=[SECONDARY.format(game=match['game'],sport=sport,day=match['day'],fair=f) for f in ('fair price','fair market price')]
    if m['rules_secondary'] not in allowed:raise ValueError('Unsupported full settlement wording')
    parts=rule['game'].split(' vs ')
    if len(parts)!=2 or any(p not in aliases for p in parts) or rule['yes_label'] not in aliases:raise ValueError('Unknown team alias')
    teams=frozenset(aliases[p] for p in parts);team=aliases[rule['yes_label']]
    if len(teams)!=2 or team not in teams:raise ValueError('Conflicting market teams')
    return teams,team,rule['provider_game_date']


def payout_range(own,opponent):
    def interval(text):
        p=D(text[:-1])/100
        unit=D(10)**D(-len(text[:-1].split('.')[1])) if '.' in text else D(1)
        half=unit/200
        return max(D(0),p-half),min(D(1),p+half),p
    lo,hi,p=interval(own);olo,ohi,op=interval(opponent)
    if lo+olo>1:raise ValueError('Infeasible forecast rounding intervals')
    low=(1+lo-min(ohi,1-lo))/2
    high=(1+min(hi,1-olo)-olo)/2
    return dict(low=str(low),central=str((1+p-op)/2),high=str(high))


def one_contract_cost(price):
    p=kalshi.number(price,True)
    trade=(D('.07')*p*(1-p)).quantize(D('.0001'),rounding=ROUND_CEILING)
    total=(p+trade).quantize(D('.01'),rounding=ROUND_CEILING)
    return dict(price=str(p),trade_fee=str(trade),estimated_fee=str(total-p),total=str(total),contracts=1)


def validated_forecast(record,image,receipt):
    if record['schema']=='elway-excel-validation-v2':
        from nfl_excel_import import validate_auto
        return validate_auto(record,image,receipt)
    if record['schema']=='elway-excel-import-v1':
        from nfl_excel_import import validate
        return validate(record,image,receipt)
    if record['schema']!=forecast.VERSION or record['source']!=receipt:raise ValueError('Forecast receipt mismatch')
    if forecast.digest(image)!=receipt['source_sha256']:raise ValueError('Forecast image digest mismatch')
    if not isinstance(record['reviewer'],str) or not record['reviewer'].strip():raise ValueError('Missing forecast reviewer')
    expected=forecast.digest(forecast.encode(dict(review=record['review'],reviewer=record['reviewer'],supersedes=record['supersedes'])))
    if record['verification_id']!=expected or record['rows']!=forecast.validate(record['review'],receipt):raise ValueError('Forecast verification mismatch')
    if kalshi.aware(record['verified_at'])<kalshi.aware(receipt['imported_at']):raise ValueError('Forecast chronology mismatch')
    return record


def age_guard(at,boundary,limit,label):
    elapsed=(kalshi.aware(boundary)-kalshi.aware(at)).total_seconds()
    if elapsed<0:raise ValueError(f'{label} timestamp is in the future')
    return f'{label} is stale' if elapsed>limit else None


def derive(f,s,k,raw_markets,asof,matching_version=None):
    if matching_version not in (None,MATCHING_VERSION):raise ValueError('Unsupported market matching version')
    at=kalshi.aware(asof);review=f['review']
    if (review['season'],review['week'])!=(s['season'],s['week']):raise ValueError('Forecast and schedule scope differ')
    general=[]
    for time,limit,label in [(s['started_at'],GUARDS['schedule_seconds'],'Schedule'),(review['updated_at'],GUARDS['forecast_seconds'],'Forecast')]:
        issue=age_guard(time,asof,limit,label)
        if issue:general.append(issue)
    for time in (s['completed_at'],f['verified_at'],f['source']['imported_at'],k['run_started_at'],k['run_completed_at']):
        age_guard(time,asof,float('inf'),'Input')
    if k['state']!='complete':general.append('Market capture is incomplete')
    series=k.get('series_metadata',{})
    if series.get('ticker')!='KXNFLGAME' or series.get('fee_type') not in ('quadratic','quadratic_with_maker_fees') or str(series.get('fee_multiplier')) not in ('1','1.0'):
        general.append('Unsupported fee metadata')
    forecasts={(r['home'],r['away']):r for r in f['rows']}
    mapped={};diagnostics=[];consumed=set()
    quotes={r['ticker']:r for r in k.get('rows',[])}
    for m in raw_markets:
        if m.get('ticker') not in quotes:continue
        try:teams,team,day=strict_market(m,matching_version)
        except (ValueError,KeyError,TypeError) as exc:
            diagnostics.append(dict(ticker=m.get('ticker'),reason=str(exc)));continue
        mapped[m['ticker']]=(teams,team,day)
    games=[];used_forecasts=set()
    for g in s['rows']:
        issues=list(general);fr=forecasts.get((g['home'],g['away']))
        if fr is None:issues.append('Missing forecast or home/away mismatch')
        else:
            used_forecasts.add(fr['forecast_match_key'])
            if fr['neutral']!=g['neutral']:issues.append('Neutral-site mismatch')
        kick=kalshi.aware(g['kickoff']) if g['kickoff'] else None
        day=kick.astimezone(NY).date().isoformat() if kick else None
        if kick is None:issues.append('Kickoff is unconfirmed')
        elif kick<=at:issues.append('Game has started')
        if g['status']!='SCHEDULED':issues.append('Game is not scheduled/pregame')
        teamset=frozenset((g['home'],g['away']))
        candidates=[(ticker,value) for ticker,value in mapped.items() if value[0]==teamset and value[2]==day and ticker in quotes]
        consumed.update(t for t,_ in candidates)
        events={quotes[t]['event_ticker'] for t,_ in candidates}
        if len(events)>1:issues.append('Ambiguous Kalshi event mapping')
        if not candidates:issues.append('No matching market with supported rules and date')
        outcomes=[]
        for role,other in [('home','away'),('away','home')]:
            team=g[role];ranges=payout_range(fr[role+'_win'],fr[other+'_win']) if fr else None
            routes=[]
            for ticker,(_,yes_team,_) in candidates:
                side='yes' if yes_team==team else 'no';q=quotes[ticker]
                reasons=list(issues)
                if sum(1 for _,v in candidates if v[1]==yes_team)>1:reasons.append('Duplicate team market')
                if q['state'] not in ('captured','missing-depth'):reasons.append('Market is unavailable')
                for key in ('book_started_at','metadata_received_at'):
                    if not q.get(key):reasons.append('Missing quote chronology');continue
                    issue=age_guard(q[key],asof,GUARDS['quote_seconds'],'Quote' if key.startswith('book') else 'Catalog')
                    if issue:reasons.append(issue)
                if q.get('book_received_at'):
                    age_guard(q['book_received_at'],asof,float('inf'),'Quote')
                    if kick and kalshi.aware(q['book_received_at'])>=kick:reasons.append('Quote was captured after kickoff')
                offer=(q.get('offers') or {}).get(side) or {};price=offer.get('offer_price');quantity=offer.get('offer_quantity')
                cost=None
                if price is None or quantity is None or D(quantity)<1:reasons.append('Less than one contract at the best offer')
                else:cost=one_contract_cost(price)
                usable=not reasons and cost is not None and ranges is not None
                routes.append(dict(ticker=ticker,side=side,yes_team=yes_team,quantity=quantity,cost=cost,
                                   book_received_at=q.get('book_received_at'),reasons=sorted(set(reasons)),usable=usable,
                                   delta_low=str(D(ranges['low'])-D(cost['total'])) if usable else None,
                                   delta_high=str(D(ranges['high'])-D(cost['total'])) if usable else None))
            valid=[r for r in routes if r['usable']]
            best=min(valid,key=lambda r:(D(r['cost']['total']),r['ticker'],r['side'])) if valid else None
            outcomes.append(dict(team=team,displayed_win=fr[role+'_win'] if fr else None,payout=ranges,routes=routes,best=best))
        lows=[D(o['best']['delta_low']) for o in outcomes if o['best']]
        games.append(dict(**g,issues=sorted(set(issues)),outcomes=outcomes,score=str(max(lows)) if lows else None,rank=None))
    scores=sorted({D(g['score']) for g in games if g['score'] is not None},reverse=True)
    for g in games:
        if g['score'] is not None:g['rank']=scores.index(D(g['score']))+1
    games.sort(key=lambda g:(g['rank'] is None,g['rank'] or 0,g['kickoff'] or '',g['game_id']))
    for ticker in sorted(set(quotes)-consumed):diagnostics.append(dict(ticker=ticker,reason='Market not matched to this weekly schedule'))
    for fr in f['rows']:
        if fr['forecast_match_key'] not in used_forecasts:diagnostics.append(dict(forecast=fr['forecast_match_key'],reason='Forecast not matched to schedule'))
    return dict(**({"matching_version":matching_version} if matching_version else {}),schema=VERSION,generated_at=asof,season=s['season'],week=s['week'],guards=GUARDS,games=games,
                scheduled_games=len(games),ranked_games=sum(g['rank'] is not None for g in games),diagnostics=diagnostics,
                forecast_updated_at=review['updated_at'],forecast_verified_at=f['verified_at'],schedule_received_at=s['completed_at'],
                capture_started_at=k['run_started_at'],capture_completed_at=k['run_completed_at'],
                fee_model='Standard taker, multiplier 1; one-contract single-fill illustration; cent-aligned total cost',
                authority='Personal comparison only; no demonstrated edge, stake sizing or wagering signal')


def read_inputs(folder):
    folder=Path(folder)
    f=json.loads((folder/'forecast.json').read_text());receipt=json.loads((folder/'forecast-receipt.json').read_text())
    validated_forecast(f,(folder/'forecast-image').read_bytes(),receipt)
    s=schedule.replay(folder/'schedule');k=kalshi.replay(folder/'kalshi')
    start=json.loads((folder/'kalshi/started.json').read_text())
    if start!=dict(schema=kalshi.VERSION,started_at=k['run_started_at'],start_date=k['start_date'],end_date=k['end_date']):raise ValueError('Kalshi start receipt mismatch')
    markets=[]
    manifest=json.loads((folder/'kalshi/complete.json').read_text())
    for r in manifest['requests']:
        if kalshi.aware(r['started_at'])<kalshi.aware(k['run_started_at']) or kalshi.aware(r['completed_at'])>kalshi.aware(k['run_completed_at']):raise ValueError('Request outside run chronology')
        if r['purpose']=='catalog':markets.extend(json.loads((folder/'kalshi'/f"response-{r['sequence']:03d}.body").read_text())['markets'])
    return f,s,k,markets


def copy_file(source,target):
    source=Path(source)
    if source.is_symlink() or not source.is_file():raise ValueError('Input must be a regular local file')
    forecast.write_once(target,source.read_bytes())


def build(store,verified,forecast_store,schedule_run,kalshi_run,activity=None):
    from nfl_board_view import render
    folder=Path(store)/('board-'+uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=False)
    forecast.write_once(folder/'started.json',forecast.encode(dict(started_at=kalshi.utc())))
    record=json.loads(Path(verified).read_text())
    source_id=record['source']['source_sha256']
    if not isinstance(source_id,str) or not re.fullmatch('[a-f0-9]{64}',source_id):raise ValueError('Invalid forecast source ID')
    source=Path(forecast_store)/'sources'/source_id
    copy_file(verified,folder/'inputs/forecast.json');copy_file(source/('source.xlsx' if record['schema'] in ('elway-excel-import-v1','elway-excel-validation-v2') else 'image'),folder/'inputs/forecast-image');copy_file(source/'receipt.json',folder/'inputs/forecast-receipt.json')
    for root,name,files in [(Path(schedule_run),'schedule',['started.json','receipt.json','source.html']),
                            (Path(kalshi_run),'kalshi',['started.json','summary.json','complete.json'])]:
        if name=='kalshi':
            manifest=json.loads((root/'complete.json').read_text())
            for i,r in enumerate(manifest['requests'],1):
                if r['sequence']!=i:raise ValueError('Invalid capture sequence')
                files.extend([f'response-{i:03d}.body',f'response-{i:03d}.json'])
        for file in files:copy_file(root/file,folder/'inputs'/name/file)
    data=derive(*read_inputs(folder/'inputs'),kalshi.utc(),matching_version=MATCHING_VERSION)
    if activity is not None:data=add_activity(folder,data,activity)
    forecast.write_once(folder/'comparison.json',forecast.encode(data));forecast.write_once(folder/'board.html',render(data).encode())
    files={str(p.relative_to(folder)):forecast.digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}
    forecast.write_once(folder/'complete.json',forecast.encode(dict(schema=VERSION,files=files)))
    return folder,data


def replay(folder,check_html=True):
    from nfl_board_view import render
    folder=Path(folder);manifest=json.loads((folder/'complete.json').read_text())
    if manifest['schema']!=VERSION:raise ValueError('Unsupported board version')
    actual={str(p.relative_to(folder)):forecast.digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file() and p!=folder/'complete.json'}
    if actual!=manifest['files']:raise ValueError('Board file digest mismatch')
    data=json.loads((folder/'comparison.json').read_text());rebuilt=derive(*read_inputs(folder/'inputs'),data['generated_at'],matching_version=data.get('matching_version'))
    if 'activity' in data:
        from nfl_activity import parse,market_map,parse_current,parse_v2,activity_map
        receipt=json.loads((folder/'inputs/activity-receipt.json').read_text())
        raw=(folder/'inputs/activity.csv').read_bytes()
        rebuilt['activity']=(parse(raw,receipt['imported_at'],market_map(folder/'inputs',rebuilt)) if data['activity']['schema']=='nfl-activity-markers-v1' else (parse_v2 if data['activity']['schema']=='nfl-activity-settlements-v2' else parse_current)(raw,receipt['imported_at'],activity_map(raw,folder/'inputs',rebuilt)))
        if receipt['source_sha256']!=rebuilt['activity']['source_sha256']:raise ValueError('Activity receipt mismatch')
    if data!=rebuilt or check_html and (folder/'board.html').read_text()!=render(rebuilt):raise ValueError('Board differs from source inputs')
    return data


def add_activity(folder,data,activity):
    from nfl_activity import parse,market_map,parse_current,parse_v2,activity_map
    raw=Path(activity).read_bytes();at=kalshi.utc()
    overlay=parse_current(raw,at,activity_map(raw,folder/'inputs',data))
    forecast.write_once(folder/'inputs/activity.csv',raw)
    forecast.write_once(folder/'inputs/activity-receipt.json',forecast.encode(dict(imported_at=at,source_sha256=forecast.digest(raw))))
    return {**data,'activity':overlay}


def attach_activity(source,activity,store):
    from nfl_board_view import render
    source=Path(source);data=replay(source,check_html=False)
    folder=Path(store)/('activity-'+uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'complete.json').read_text())
    for name in manifest['files']:
        if name in ('board.html','comparison.json','inputs/activity.csv','inputs/activity-receipt.json'):continue
        copy_file(source/name,folder/name)
    data=add_activity(folder,{k:v for k,v in data.items() if k!='activity'},activity)
    forecast.write_once(folder/'comparison.json',forecast.encode(data))
    forecast.write_once(folder/'board.html',render(data).encode())
    files={str(p.relative_to(folder)):forecast.digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}
    forecast.write_once(folder/'complete.json',forecast.encode(dict(schema=VERSION,files=files,presentation_rendered_at=kalshi.utc(),source_board=str(source.resolve()),scope='Activity overlay; comparison times and quote data preserved')))
    return folder,data


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('--verified',type=Path,required=True);b.add_argument('--forecast-store',type=Path,required=True)
    b.add_argument('--schedule',type=Path,required=True);b.add_argument('--kalshi',type=Path,required=True)
    b.add_argument('--activity',type=Path,help='Optional Kalshi activity CSV; recorded trades, not open balances')
    b.add_argument('--store',type=Path,default=Path.home()/'PopsEdgeData/NFL/boards')
    aview=sub.add_parser('activity');aview.add_argument('--board',type=Path,required=True);aview.add_argument('--activity',type=Path,required=True);aview.add_argument('--store',type=Path,default=Path.home()/'PopsEdgeData/NFL/boards')
    r=sub.add_parser('replay');r.add_argument('folder',type=Path);a=p.parse_args()
    try:
        if a.command=='build':
            folder,data=build(a.store,a.verified,a.forecast_store,a.schedule,a.kalshi,a.activity)
            print(f"{data['ranked_games']} of {data['scheduled_games']} games have usable comparisons.\nBoard: {(folder/'board.html').resolve()}")
        elif a.command=='activity':
            folder,data=attach_activity(a.board,a.activity,a.store)
            print(f"Matched {len(data['activity']['trades'])} recorded NFL trades.\nBoard: {(folder/'board.html').resolve()}")
        else:data=replay(a.folder);print(f"Replay verified: {data['scheduled_games']} scheduled games")
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:print(f'Board needs attention: {exc}',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
