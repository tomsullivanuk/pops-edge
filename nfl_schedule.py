"""Bounded official NFL weekly schedule capture and offline parsing."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import uuid
import requests
from nfl_forecast_import import digest, encode, write_once
from retrieve_kalshi_nfl import aware, utc

VERSION = 'nfl-official-schedule-v1'
NAMES = dict(zip(
    'ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WAS'.split(),
    ['Arizona Cardinals','Atlanta Falcons','Baltimore Ravens','Buffalo Bills','Carolina Panthers','Chicago Bears','Cincinnati Bengals','Cleveland Browns','Dallas Cowboys','Denver Broncos','Detroit Lions','Green Bay Packers','Houston Texans','Indianapolis Colts','Jacksonville Jaguars','Kansas City Chiefs','Las Vegas Raiders','Los Angeles Chargers','Los Angeles Rams','Miami Dolphins','Minnesota Vikings','New England Patriots','New Orleans Saints','New York Giants','New York Jets','Philadelphia Eagles','Pittsburgh Steelers','San Francisco 49ers','Seattle Seahawks','Tampa Bay Buccaneers','Tennessee Titans','Washington Commanders']))
FULL_NAMES = {v:k for k,v in NAMES.items()}


def scope(season, week):
    if type(season) is not int or not 2000 <= season <= 2100 or type(week) is not int or not 1 <= week <= 18:
        raise ValueError('Use a regular-season year and week 1–18')


def url(season, week):
    scope(season, week)
    return f'https://www.nfl.com/schedules/{season}/by-week/week-{week}'


def parse(raw, season, week):
    scope(season, week)
    chunks=[]
    for m in re.finditer(r'self\.__next_f\.push\((\[.*?\])\)</script>', raw.decode('utf-8')):
        value=json.loads(m[1])
        if len(value)==2 and value[0]==1 and isinstance(value[1],str):chunks.append(value[1])
    found=[]
    def walk(value):
        if isinstance(value,dict):
            key=value.get('queryKey')
            if isinstance(key,list) and key and key[0]=='useFetchFootballWeeklyGameDetails':
                if len(key)!=2 or not isinstance(key[1],dict):raise ValueError('Unknown schedule query')
                arg=key[1]
                if str(arg.get('season'))==str(season) and arg.get('seasonType')=='REG' and str(arg.get('week'))==str(week):
                    state=value['state']
                    if state.get('status')!='success':raise ValueError('Schedule query failed')
                    found.append(state['data'])
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for line in ''.join(chunks).splitlines():
        try:value=json.loads(line.split(':',1)[1])
        except (ValueError,IndexError):continue
        walk(value)
    if len(found)!=1 or not isinstance(found[0],list) or not 1<=len(found[0])<=16:
        raise ValueError('Expected exactly one complete weekly schedule query')
    rows=[];ids=set();teams=set()
    for game in found[0]:
        if game['season']!=season or game['week']!=week or game['seasonType']!='REG' or game['weekType']!='REG':
            raise ValueError('Schedule game outside requested scope')
        identity=str(uuid.UUID(game['id']))
        home=FULL_NAMES[game['homeTeam']['fullName']];away=FULL_NAMES[game['awayTeam']['fullName']]
        if identity in ids or home==away or home in teams or away in teams:raise ValueError('Duplicate schedule identity/team')
        ids.add(identity);teams.update((home,away))
        if type(game['neutralSite']) is not bool:raise ValueError('Missing explicit neutral flag')
        kickoff=game.get('time')
        if kickoff is not None:aware(kickoff)
        if not isinstance(game.get('status'),str):raise ValueError('Missing schedule status')
        rows.append(dict(game_id=identity,season=season,week=week,home=home,away=away,
                         neutral=game['neutralSite'],kickoff=kickoff,status=game['status'],
                         venue=game.get('venue',{}).get('name')))
    return sorted(rows,key=lambda r:r['game_id'])


def fetch(address):
    with requests.Session() as session:
        session.trust_env=False
        with session.get(address,timeout=20,allow_redirects=False,stream=True) as response:
            raw=bytearray()
            for part in response.iter_content(65536):
                raw.extend(part)
                if len(raw)>8*1024*1024:raise ValueError('Schedule response exceeds bound')
            return response.status_code,bytes(raw)


def capture(store,season,week,transport=fetch,clock=utc):
    address=url(season,week);folder=Path(store)/('schedule-'+uuid.uuid4().hex)
    folder.mkdir(parents=True,exist_ok=False)
    started=clock();write_once(folder/'started.json',encode(dict(url=address,started_at=started)))
    raw=b'';status=None;error=None
    try:status,raw=transport(address)
    except (requests.RequestException,OSError,ValueError) as exc:error=type(exc).__name__
    ended=clock();rows=[]
    try:
        if error or status!=200:raise ValueError('Schedule request failed')
        if aware(ended)<aware(started):raise ValueError('Schedule clock moved backwards')
        rows=parse(raw,season,week)
    except (ValueError,KeyError,TypeError) as exc:error=str(exc)
    receipt=dict(schema=VERSION,url=address,season=season,week=week,started_at=started,completed_at=ended,
                 status=status,error=error,raw_sha256=digest(raw),rows=rows)
    write_once(folder/'source.html',raw);write_once(folder/'receipt.json',encode(receipt))
    return folder,receipt


def replay(folder, *, parse_rows=None):
    parse_rows = parse_rows or parse
    folder=Path(folder);r=json.loads((folder/'receipt.json').read_text());raw=(folder/'source.html').read_bytes()
    if r['schema']!=VERSION or r['url']!=url(r['season'],r['week']) or r['error'] or r['status']!=200:raise ValueError('Invalid schedule receipt')
    if digest(raw)!=r['raw_sha256'] or aware(r['completed_at'])<aware(r['started_at']):raise ValueError('Schedule integrity/chronology failure')
    started=json.loads((folder/'started.json').read_text())
    if started!=dict(url=r['url'],started_at=r['started_at']):raise ValueError('Schedule start receipt mismatch')
    if parse_rows(raw,r['season'],r['week'])!=r['rows']:raise ValueError('Schedule differs from raw source')
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--season',type=int,required=True);p.add_argument('--week',type=int,required=True)
    p.add_argument('--store',type=Path,default=Path.home()/'PopsEdgeData/NFL/schedules');a=p.parse_args()
    try:
        folder,r=capture(a.store,a.season,a.week)
        print(('FAILED: '+r['error'] if r['error'] else f"Captured {len(r['rows'])} scheduled games")+f'\nSaved: {folder.resolve()}')
        return 2 if r['error'] else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:print(f'Schedule needs attention: {exc}',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
