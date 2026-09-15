"""Recorded NFL trades from a supplied export; never infers open positions."""
import csv
from decimal import Decimal,InvalidOperation
import io
import re
from nfl_forecast_import import digest
from retrieve_kalshi_nfl import aware

VERSION='nfl-activity-markers-v1'
REQUIRED={'type','Market_Ticker','Direction','Price_In_Cents','Amount_In_Dollars','Fee_In_Dollars','Original_Date'}


def number(text,limit=None):
    text=str(text).strip()
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',text):raise ValueError('Invalid numeric field')
    try:value=Decimal(text.replace(',',''))
    except InvalidOperation as exc:raise ValueError('Invalid decimal') from exc
    if not value.is_finite() or value<0 or limit is not None and value>limit:raise ValueError('Numeric value out of range')
    return value


def parse(raw,imported_at,market_map):
    now=aware(imported_at)
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''))
    if not REQUIRED.issubset(reader.fieldnames or []):raise ValueError('Activity export missing required columns')
    rows=list(reader);trades=[];issues=[];outside=0;seen=set();settlements={}
    for i,row in enumerate(rows,2):
        ticker=(row.get('Market_Ticker') or '').strip();kind=(row.get('type') or '').strip()
        if not ticker.startswith('KXNFLGAME-'):
            outside+=1;continue
        if kind=='Order':continue
        try:
            if kind not in ('Trade','Settlement'):raise ValueError('Unsupported NFL activity type')
            at=(row.get('Original_Date') or '').strip()
            if aware(at)>now:raise ValueError('Activity timestamp is in the future')
            if kind=='Settlement':settlements.setdefault(ticker,[]).append(at);continue
            sig=tuple(sorted((str(k),str(v)) for k,v in row.items()))
            if sig in seen:raise ValueError('Duplicate trade row; activity needs review')
            seen.add(sig)
            side=(row.get('Direction') or '').strip().lower()
            if side not in ('yes','no'):raise ValueError('Unknown contract side')
            qty=number(row.get('Amount_In_Dollars'));price=number(row.get('Price_In_Cents'),Decimal(100))/100
            fee=number(row.get('Fee_In_Dollars'))
            if qty<=0:raise ValueError('Nonpositive trade quantity')
            if ticker not in market_map:raise ValueError('No unique supported market match')
            match=market_map[ticker];team=match['yes_team'] if side=='yes' else match['opponent']
            trades.append(dict(source_row=i,ticker=ticker,side=side,yes_team=match['yes_team'],team=team,game_id=match['game_id'],quantity=str(qty),price=str(price),fee=str(fee),at=at,settlement_seen=False))
        except (ValueError,TypeError,KeyError) as exc:issues.append(dict(row=i,ticker=ticker,reason=str(exc)))
    for trade in trades:
        trade['settlement_seen']=any(aware(t)>=aware(trade['at']) for t in settlements.get(trade['ticker'],[]))
    # Duplicate rows make the affected ticker ambiguous; retain original rows but flag them.
    ambiguous={i['ticker'] for i in issues if 'Duplicate trade' in i['reason']}
    for trade in trades:trade['needs_review']=trade['ticker'] in ambiguous
    return dict(schema=VERSION,source_sha256=digest(raw),imported_at=imported_at,total_rows=len(rows),outside_nfl_rows=outside,
                trades=sorted(trades,key=lambda t:(t['at'],t['ticker'],t['source_row'])),diagnostics=issues,
                meaning='Recorded trades in this export; buy/sell action and current open balance not established')


def market_map(inputs,data):
    import json
    from pathlib import Path
    from nfl_comparison_board import strict_market,NY
    root=Path(inputs)/'kalshi';manifest=json.loads((root/'complete.json').read_text());result={};duplicates=set()
    for request in manifest['requests']:
        if request['purpose']!='catalog':continue
        markets=json.loads((root/f"response-{request['sequence']:03d}.body").read_text())['markets']
        for m in markets:
            try:teams,yes,day=strict_market(m,data.get("matching_version"))
            except (ValueError,KeyError,TypeError):continue
            matches=[g for g in data['games'] if frozenset((g['home'],g['away']))==teams and g['kickoff'] and aware(g['kickoff']).astimezone(NY).date().isoformat()==day]
            if len(matches)!=1:continue
            ticker=m['ticker']
            if ticker in result:duplicates.add(ticker)
            g=matches[0];result[ticker]=dict(game_id=g['game_id'],yes_team=yes,opponent=next(t for t in teams if t!=yes))
    return {t:v for t,v in result.items() if t not in duplicates}


def activity_map(raw,inputs,data):
    """Closed activity identity from exact ticker/date/team tuple, never quote eligibility."""
    from nfl_comparison_board import NY
    result=market_map(inputs,data)
    tickers={r.get('Market_Ticker','') for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))}
    for ticker in tickers-result.keys():
        candidates=[]
        for g in data['games']:
            if not g['kickoff']:continue
            date=aware(g['kickoff']).astimezone(NY)
            stamp=f'{date.year%100:02d}'+('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()[date.month-1])+f'{date.day:02d}'
            for yes in (g['home'],g['away']):
                if ticker==f"KXNFLGAME-{stamp}{g['away']}{g['home']}-{yes}":
                    candidates.append(dict(game_id=g['game_id'],yes_team=yes,opponent=g['away'] if yes==g['home'] else g['home']))
        if len(candidates)==1:result[ticker]=candidates[0]
    return result


def parse_v2(raw,imported_at,mapping):
    result=parse(raw,imported_at,mapping);result['schema']='nfl-activity-settlements-v2';settled=[];seen=set();bad=set()
    for i,row in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))),2):
        ticker=(row.get('Market_Ticker') or '').strip()
        if row.get('type')!='Settlement' or not ticker.startswith('KXNFLGAME-'):continue
        try:
            if ticker not in mapping:raise ValueError('Settlement has no unique game match')
            if ticker in seen:raise ValueError('Duplicate settlement; payout needs review')
            seen.add(ticker);match=mapping[ticker];at=row['Original_Date']
            if aware(at)>aware(imported_at):raise ValueError('Settlement timestamp is in the future')
            outcome=(row.get('Result') or '').lower()
            if outcome not in ('yes','no'):raise ValueError('Unsupported settlement result; review payout manually')
            yes=number(row.get('Yes_Contracts_Owned'));no=number(row.get('No_Contracts_Owned'))
            paid=number(row.get('Profit_In_Dollars'))
            expected=yes if outcome=='yes' else no
            if abs(paid-expected)>Decimal('.005'):raise ValueError('Export settlement amount does not reconcile to winning quantity')
            for side,quantity in [('yes',yes),('no',no)]:
                if not quantity:continue
                avg=number(row.get(('Yes' if side=='yes' else 'No')+'_Contracts_Average_Price_In_Cents'),Decimal(100))/100
                trades=[t for t in result['trades'] if t['ticker']==ticker and t['side']==side and aware(t['at'])<=aware(at)]
                qty=sum((Decimal(t['quantity']) for t in trades),Decimal(0))
                basis=sum((Decimal(t['quantity'])*Decimal(t['price']) for t in trades),Decimal(0))
                reconciled=qty==quantity and abs(basis-quantity*avg)<=Decimal('.005')+quantity*Decimal('.00005') and not any(t['needs_review'] for t in trades)
                settled.append(dict(source_row=i,ticker=ticker,side=side,yes_team=match['yes_team'],team=match['yes_team'] if side=='yes' else match['opponent'],game_id=match['game_id'],at=at,result='won' if outcome==side else 'lost',quantity=str(quantity),payout=str(quantity if outcome==side else Decimal(0)),average_price=str(avg),cost_reconciled=reconciled,needs_review=False))
        except (ValueError,KeyError,TypeError) as exc:
            result['diagnostics'].append(dict(row=i,ticker=ticker,reason=str(exc)));bad.add(ticker)
    for item in settled:item['needs_review']=item['ticker'] in bad
    result['settlements']=settled
    return result


def parse_current(raw,imported_at,mapping):
    """Separate a matched market's settlement status from payout reconciliation."""
    result=parse_v2(raw,imported_at,mapping)
    result['schema']='nfl-activity-settlements-v3'
    events={};counts={}
    for i,row in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))),2):
        ticker=(row.get('Market_Ticker') or '').strip()
        if row.get('type')!='Settlement' or ticker not in mapping:continue
        counts[ticker]=counts.get(ticker,0)+1
        try:
            at=row['Original_Date'];outcome=(row.get('Result') or '').strip().lower()
            if aware(at)>aware(imported_at) or outcome not in ('yes','no'):continue
            match=mapping[ticker]
            events.setdefault(ticker,[]).append(dict(source_row=i,ticker=ticker,
                game_id=match['game_id'],at=at,result=outcome))
        except (ValueError,KeyError,TypeError):continue
    # Duplicate/contradictory settlement records do not establish completion.
    result['settlement_events']=[items[0] for ticker,items in events.items() if len(items)==1 and counts[ticker]==1]
    result['settlement_events'].sort(key=lambda e:(e['at'],e['ticker']))
    return result
