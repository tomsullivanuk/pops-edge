"""Manual public NFL market capture. No forecasts, credentials, orders, or policy."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote
import uuid
import requests
from nfl_forecast_import import digest, encode, write_once

BASE = 'https://external-api.kalshi.com/trade-api/v2'
SERIES = 'KXNFLGAME'
VERSION = 'kalshi-nfl-capture-v1'
MAX_PAGES = 10
MAX_MARKETS = 128
MAX_BYTES = 8 * 1024 * 1024
RULE = re.compile(r'^If (?P<team>.+?) wins the (?P<game>.+?) (?:professional football|Pro Football) game originally scheduled for (?P<day>[A-Z][a-z]{2} \d{1,2}, \d{4}), then the market resolves to Yes\.$')


def utc():
    return datetime.now(timezone.utc).isoformat()


def aware(value):
    t = datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('Request clock must be timezone-aware')
    return t


def window(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if a.isoformat()!=start or b.isoformat()!=end or not 0 <= (b-a).days <= 7:
        raise ValueError('Use an inclusive date window of one to eight days')
    return a, b


def public_get(route, params):
    """No netrc, credential lookup, cookies across calls, or redirects."""
    if not (route == '/series/'+SERIES or route == '/markets' or re.fullmatch(r'/markets/KXNFLGAME-[A-Z0-9-]+/orderbook',route)):
        raise ValueError('route is outside public NFL retrieval scope')
    with requests.Session() as session:
        session.trust_env = False
        with session.get(BASE+route, params=params, timeout=15, allow_redirects=False, stream=True) as response:
            raw = bytearray()
            for part in response.iter_content(65536):
                raw.extend(part)
                if len(raw)>MAX_BYTES:
                    raise ValueError('Response exceeds eight-megabyte bound')
            return response.status_code, bytes(raw)


def payload(record):
    if record.get('error') or record['status'] != 200:
        raise ValueError('request failed')
    obj = json.loads(record['raw'])
    if not isinstance(obj,dict):
        raise ValueError('response must be a JSON object')
    return obj


def market_rule(market):
    primary = market.get('rules_primary','')
    match = RULE.fullmatch(primary)
    if not match:
        raise ValueError('unsupported full-game winner rule')
    if match['team'] != market.get('yes_sub_title'):
        raise ValueError('YES label conflicts with winner rule')
    secondary = market.get('rules_secondary','')
    if f"{match['game']} " not in secondary or f"originally scheduled for {match['day']}" not in secondary:
        raise ValueError('secondary rule does not confirm game/date')
    if 'If the game ends in a tie, the market will resolve to $0.50 for each team.' not in secondary:
        raise ValueError('unrecognized tie rule')
    if market.get('market_type') != 'binary' or market.get('mve_selected_legs') or market.get('mve_collection_ticker'):
        raise ValueError('unsupported market type')
    return dict(game=match['game'], provider_game_date=datetime.strptime(match['day'],'%b %d, %Y').date().isoformat(),
                yes_label=match['team'], no_label=market.get('no_sub_title'))


def catalog(records):
    if not records or records[0]['purpose']!='series' or records[0]['route']!='/series/'+SERIES or records[0]['params']!={}:
        raise ValueError('missing/invalid series request')
    series = payload(records[0]).get('series',{})
    if series.get('ticker')!=SERIES or series.get('product_metadata',{}).get('scope')!='Game':
        raise ValueError('series metadata does not identify NFL game scope')
    markets = []
    tickers = set()
    cursor = ''
    seen = set()
    pages = [r for r in records if r['purpose']=='catalog']
    if not pages or len(pages)>MAX_PAGES:
        raise ValueError('missing or excessive catalog pages')
    for i, record in enumerate(pages):
        expected = dict(series_ticker=SERIES,status='open',limit=1000)
        if cursor:expected['cursor']=cursor
        if record['params']!=expected or record['route']!='/markets':
            raise ValueError('catalog cursor/request mismatch')
        data = payload(record)
        batch = data.get('markets')
        if not isinstance(batch,list) or len(batch)>1000:
            raise ValueError('invalid catalog page')
        for market in batch:
            if not isinstance(market,dict):raise ValueError('invalid market object')
            ticker,event=market.get('ticker'),market.get('event_ticker')
            if not isinstance(event,str) or not event.startswith(SERIES+'-') or not isinstance(ticker,str) or not ticker.startswith(event+'-') or not re.fullmatch(r'[A-Z0-9-]+',ticker):
                raise ValueError('foreign or malformed market identity')
            if ticker in tickers:raise ValueError('duplicate market across catalog')
            tickers.add(ticker);markets.append((market,record['sequence']))
        cursor=data.get('cursor','')
        if not isinstance(cursor,str) or cursor in seen and cursor:
            raise ValueError('invalid or repeated catalog cursor')
        if cursor:seen.add(cursor)
        if not cursor and i!=len(pages)-1:raise ValueError('pages after terminal cursor')
    if cursor:raise ValueError('incomplete catalog')
    return series, markets


def number(value, price=False):
    if not isinstance(value,str):raise ValueError('fixed-point values must be strings')
    try:d=Decimal(value)
    except InvalidOperation as exc:raise ValueError('invalid fixed-point number') from exc
    if not d.is_finite() or d<0 or (price and d>1):raise ValueError('invalid price/quantity range')
    return d


def book_view(data, ticker):
    for key in ('ticker','market_ticker'):
        if key in data and data[key]!=ticker:raise ValueError('book market identity mismatch')
    book=data.get('orderbook_fp')
    if not isinstance(book,dict):raise ValueError('missing fixed-point order book')
    bids={}
    for side in ('yes','no'):
        levels=book.get(side+'_dollars')
        if not isinstance(levels,list) or len(levels)>100:raise ValueError('missing/excessive book levels')
        result=[];seen=set()
        for pair in levels:
            if not isinstance(pair,list) or len(pair)!=2:raise ValueError('invalid book level')
            price,quantity=number(pair[0],True),number(pair[1])
            if quantity<=0 or price in seen:raise ValueError('nonpositive depth or duplicate price')
            seen.add(price)
            result.append(dict(provider_bid_price=pair[0],quantity=pair[1],acquisition_price=str(Decimal(1)-price)))
        bids[side]=sorted(result,key=lambda x:Decimal(x['provider_bid_price']),reverse=True)
    if bids['yes'] and bids['no'] and Decimal(bids['yes'][0]['provider_bid_price'])+Decimal(bids['no'][0]['provider_bid_price'])>1:
        raise ValueError('crossed book')
    return {side:dict(offer_price=bids[opposite][0]['acquisition_price'] if bids[opposite] else None,
                      offer_quantity=bids[opposite][0]['quantity'] if bids[opposite] else None,
                      provider_bid_side=opposite,transformation='1 - opposite bid',levels=bids[opposite])
            for side,opposite in (('yes','no'),('no','yes'))}


def selected(markets,start,end):
    chosen=[];issues=[]
    for market,sequence in markets:
        try:rule=market_rule(market)
        except (ValueError,TypeError) as exc:
            issues.append(dict(ticker=market['ticker'],issue=str(exc)));continue
        day=date.fromisoformat(rule['provider_game_date'])
        if start<=day<=end:chosen.append((market,sequence,rule))
    if len(chosen)>MAX_MARKETS:raise ValueError('selected market count exceeds bound')
    return sorted(chosen,key=lambda x:x[0]['ticker']),issues


def derive(records,start,end):
    a,b=window(start,end)
    try:
        for i,r in enumerate(records):
            if r['sequence']!=i+1 or aware(r['completed_at'])<aware(r['started_at']):
                raise ValueError('invalid request chronology/sequence')
            if i and aware(r['started_at'])<aware(records[i-1]['completed_at']):
                raise ValueError('overlapping requests')
        series,markets=catalog(records)
        chosen,issues=selected(markets,a,b)
    except (ValueError,KeyError,TypeError) as exc:
        return dict(state='failed',issue=str(exc),rows=[],catalog_complete=False)
    rows=[]
    books={}
    for record in records:
        if record['purpose']=='book':
            ticker=record['ticker']
            if ticker in books:return dict(state='failed',issue='duplicate book request',rows=[],catalog_complete=False)
            books[ticker]=record
    if set(books)-{m['ticker'] for m,_,_ in chosen}:
        return dict(state='failed',issue='book outside selected population',rows=[],catalog_complete=False)
    for market,sequence,rule in chosen:
        record=books.get(market['ticker'])
        row=dict(**rule,ticker=market['ticker'],event_ticker=market['event_ticker'],
                 metadata_sequence=sequence,market_status=market.get('status'),
                 metadata_updated_at=market.get('updated_time'),
                 metadata_received_at=records[sequence-1]['completed_at'],
                 state='unavailable',offers=None,issue=None)
        try:
            if record is None:raise ValueError('book not retrieved')
            if record['route']!=f"/markets/{quote(market['ticker'],safe='')}/orderbook" or record['params']!={'depth':100}:
                raise ValueError('book request does not match market')
            row.update(book_sequence=record['sequence'],book_started_at=record['started_at'],book_received_at=record['completed_at'])
            view=book_view(payload(record),market['ticker'])
            row['offers']=view
            row['state']='captured' if all(view[s]['offer_price'] is not None for s in ('yes','no')) else 'missing-depth'
            if market.get('status') not in ('open','active'):
                row['state']='non-open';row['offers']=None
        except (ValueError,KeyError,TypeError) as exc:row['issue']=str(exc)
        rows.append(row)
    return dict(state='partial' if issues or any(r['state'] not in ('captured','missing-depth','non-open') for r in rows) else 'complete',
                catalog_complete=True,catalog_market_count=len(markets),selected_market_count=len(rows),
                series_metadata=series,diagnostics=issues,rows=rows,
                eligibility='not assessed; provider dates are not kickoff authority',
                fee_calculation='not implemented; metadata preserved only')


def capture(store,start,end,transport=public_get,clock=utc):
    window(start,end)
    run=Path(store)/('run-'+uuid.uuid4().hex)
    run.mkdir(parents=True,exist_ok=False)
    started=clock()
    write_once(run/'started.json',encode(dict(schema=VERSION,started_at=started,start_date=start,end_date=end)))
    records=[]
    def get(purpose,route,params,ticker=None):
        at=clock()
        if aware(at)<aware(records[-1]['completed_at'] if records else started):raise ValueError('clock moved backwards')
        record=dict(sequence=len(records)+1,purpose=purpose,route=route,params=params,started_at=at,ticker=ticker,status=None,error=None)
        raw=b''
        try:
            status,raw=transport(route,params)
            if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise ValueError('invalid/oversized response')
            record['status']=status
        except (requests.RequestException,OSError,ValueError) as exc:
            record['error']=type(exc).__name__
        record['completed_at']=clock()
        record['raw_sha256']=digest(raw)
        name=f"response-{record['sequence']:03d}"
        write_once(run/(name+'.body'),raw)
        write_once(run/(name+'.json'),encode(record))
        record['raw']=raw;records.append(record)
        if aware(record['completed_at'])<aware(at):raise ValueError('clock moved backwards')
        return payload(record)
    failure=None
    try:
        get('series','/series/'+SERIES,{})
        cursor='';seen=set()
        for _ in range(MAX_PAGES):
            params=dict(series_ticker=SERIES,status='open',limit=1000)
            if cursor:params['cursor']=cursor
            data=get('catalog','/markets',params)
            cursor=data.get('cursor','')
            if not isinstance(cursor,str) or cursor and cursor in seen:raise ValueError('invalid/repeated cursor')
            if not cursor:break
            seen.add(cursor)
        _,markets=catalog(records)
        chosen,_=selected(markets,*window(start,end))
        for market,_,_ in chosen:
            try:get('book',f"/markets/{quote(market['ticker'],safe='')}/orderbook",{'depth':100},market['ticker'])
            except (ValueError,KeyError,TypeError):continue
    except (ValueError,KeyError,TypeError) as exc:failure=str(exc)
    summary=derive(records,start,end)
    if failure:summary.update(state='failed',issue=failure)
    summary.update(schema=VERSION,start_date=start,end_date=end,run_started_at=started,run_completed_at=clock(),request_count=len(records))
    write_once(run/'summary.json',encode(summary))
    manifest=dict(summary_sha256=digest(encode(summary)),requests=[{k:v for k,v in r.items() if k!='raw'} for r in records])
    write_once(run/'complete.json',encode(manifest))
    return run,summary


def replay(run):
    run=Path(run)
    manifest=json.loads((run/'complete.json').read_text())
    saved=json.loads((run/'summary.json').read_text())
    if digest((run/'summary.json').read_bytes())!=manifest['summary_sha256']:raise ValueError('summary digest mismatch')
    records=[]
    for i,r in enumerate(manifest['requests'],1):
        if r['sequence']!=i:raise ValueError('request sequence mismatch')
        name=f'response-{i:03d}'
        if json.loads((run/(name+'.json')).read_text())!=r:raise ValueError('receipt mismatch')
        raw=(run/(name+'.body')).read_bytes()
        if digest(raw)!=r['raw_sha256']:raise ValueError('raw response digest mismatch')
        if aware(r['completed_at'])<aware(r['started_at']):raise ValueError('invalid request chronology')
        if records and aware(r['started_at'])<aware(records[-1]['completed_at']):raise ValueError('overlapping requests')
        records.append({**r,'raw':raw})
    derived=derive(records,saved['start_date'],saved['end_date'])
    # Failed acquisition status is operational; never promotes partial material.
    for key,value in derived.items():
        if saved['state']=='failed' and key in ('state','issue'):continue
        if saved.get(key)!=value:raise ValueError('derived output differs from source responses')
    return saved


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('capture');p.add_argument('--start-date',required=True);p.add_argument('--end-date',required=True)
    p.add_argument('--store',type=Path,default=Path.home()/'PopsEdgeData/NFL/kalshi')
    r=sub.add_parser('replay');r.add_argument('run',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='capture':
            run,summary=capture(args.store,args.start_date,args.end_date)
            print(f"{summary['state'].upper()}: {summary.get('selected_market_count',0)} selected markets; {summary['request_count']} requests.\nSaved: {run.resolve()}")
        else:
            summary=replay(args.run);print(f"Replay verified: {summary['state']}")
        return 0 if summary['state']=='complete' else 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'Retrieval needs attention: {exc}',file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
