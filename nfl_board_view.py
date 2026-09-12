"""Compact NFL bet sheet. Presentation only; observed quotes are never refreshed."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from zoneinfo import ZoneInfo
from nfl_brand import BRAND_CSS


def esc(value):
    return escape(str(value))


def dollars(value,signed=False):
    n=Decimal(value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    prefix='-' if n<0 else '+' if signed else ''
    return prefix+'$'+f'{abs(n):.2f}'


def minute_time(value):
    if not value:return None
    dt=datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
    dt=(dt+timedelta(seconds=30)).replace(second=0,microsecond=0)
    return dt.astimezone(ZoneInfo('America/Chicago'))


def display_time(value):
    dt=minute_time(value)
    return dt.strftime('%m/%d/%Y %I:%M %p %Z') if dt else 'TBD'


def contracts(value):
    return f"{Decimal(value).quantize(Decimal('1'),rounding=ROUND_HALF_UP):,}" if value is not None else '—'


def wager_summary(trades, value):
    """Purchase illustration only; this export cannot establish open holdings."""
    if not trades or value is None or any(t['needs_review'] or t['settlement_seen'] for t in trades):
        return None
    quantity=sum((Decimal(t['quantity']) for t in trades),Decimal(0))
    spent=sum((Decimal(t['quantity'])*Decimal(t['price'])+Decimal(t['fee']) for t in trades),Decimal(0))
    return dict(spent=spent,expected=quantity*Decimal(value['central']),win=quantity,tie=quantity/2)


def sheet_rows(data):
    """Largest model-minus-total-cost discrepancy first; missing last."""
    rows=[]
    settled_games={s['game_id'] for s in data.get('activity',{}).get('settlements',[])}
    settled_games.update(e['game_id'] for e in data.get('activity',{}).get('settlement_events',[]))
    for game in data['games']:
        for outcome in game['outcomes']:
            usable=[r for r in outcome['routes'] if r['usable'] and game['game_id'] not in settled_games]
            route=min(usable,key=lambda r:(Decimal(r['cost']['price']),Decimal(r['cost']['total']),r['ticker'],r['side'])) if usable else None
            gap=Decimal(outcome['payout']['central'])-Decimal(route['cost']['total']) if route else None
            rows.append(dict(game=game,outcome=outcome,route=route,gap=gap))
    return sorted(rows,key=lambda r:(r['gap'] is None,-r['gap'] if r['gap'] is not None else Decimal(0),r['game']['game_id'],r['outcome']['team']))


def render(data):
    rows=sheet_rows(data);body=[]
    activity=data.get('activity')
    recorded=activity['trades'] if activity else []
    for item in rows:
        g,o,r,gap=(item[k] for k in ('game','outcome','route','gap'))
        value=o['payout'];kick=g['kickoff'];details=[]
        wagers=[t for t in recorded if t['game_id']==g['game_id'] and t['team']==o['team']]
        settlements=[t for t in (activity or {}).get('settlements',[]) if t['game_id']==g['game_id'] and t['team']==o['team']]
        closed=any(e['game_id']==g['game_id'] for e in (activity or {}).get('settlement_events',[]))
        unresolved_close=closed and not settlements
        paid=sum((Decimal(t['payout']) for t in settlements),Decimal(0)) if settlements and not any(t['needs_review'] for t in settlements) else None
        settled_label='Settled · '+('/'.join(sorted({t['result'] for t in settlements}))) if settlements else 'Recorded'
        summary=None if closed else wager_summary(wagers,value)
        settlement_details=''.join('<li>'+esc(t['side'].upper()+' '+t['yes_team'])+' · '+esc(t['result'])+' · payout '+dollars(t['payout'])+' · '+esc(display_time(t['at']))+(' · cost basis differs or trade history incomplete; realized profit unavailable' if not t['cost_reconciled'] else '')+(' · payout needs review' if t['needs_review'] else '')+'</li>' for t in settlements)
        wager_label=', '.join(sorted({t['side'].upper()+' '+t['yes_team'] for t in wagers+settlements})) if wagers or settlements else 'None in export' if activity else 'Not loaded'
        wager_lines=[]
        for t in wagers:
            amount=Decimal(t['quantity'])*Decimal(t['price'])+Decimal(t['fee'])
            wager_lines.append('<div><b>'+esc(t['side'].upper()+' '+t['yes_team'])+'</b> · '+('Cash-flow review needed' if unresolved_close else 'Review needed' if t['needs_review'] else dollars(amount))+'</div>')
        for t in settlements:
            if not any(w['ticker']==t['ticker'] and w['side']==t['side'] for w in wagers):
                wager_lines.append('<div><b>'+esc(t['side'].upper()+' '+t['yes_team'])+'</b> · Amount unavailable</div>')
        wager_cell=''.join(wager_lines)
        if closed and wagers:wager_cell+='<small>Closed · market settled</small>'
        elif settlements:wager_cell+='<small>'+esc(settled_label)+'</small>'
        wager_details=''.join('<li><b>'+esc(t['side'].upper()+' '+t['yes_team'])+'</b> · '+esc(t['ticker'])+' · reported quantity '+esc(t['quantity'])+' · recorded price '+dollars(t['price'])+' · recorded fee '+dollars(t['fee'])+' · '+esc(display_time(t['at']))+(' · settlement appears later in export' if t['settlement_seen'] else '')+(' · duplicate rows: needs review' if t['needs_review'] else '')+'</li>' for t in wagers)
        for q in o['routes']:
            cost=q['cost']
            details.append('<li><b>'+esc(q['side'].upper()+' '+q['yes_team'])+'</b> · '+esc(q['ticker'])+
                (' · offer '+dollars(cost['price'])+' + fee '+dollars(cost['estimated_fee']) if cost else '')+
                ' · Contracts available: '+contracts(q['quantity'])+' · '+esc(display_time(q['book_received_at']) if q['book_received_at'] else 'no quote')+
                ('<br>'+esc('; '.join(q['reasons'])) if q['reasons'] else '')+'</li>')
        reasons='; '.join(g['issues'])
        if not r and not reasons:reasons='No usable quote; see route details.'
        when=minute_time(kick)
        date_label=when.strftime('%m/%d') if when else 'TBD';time_label=when.strftime('%I:%M %p %Z').lstrip('0') if when else ''
        after=Decimal(value['central'])-Decimal(r['cost']['total']) if r else None
        cells=[f'<td data-sort="{esc(kick or "")}">{date_label if when else "TBD"}<small>{time_label}</small></td>',
               '<td class="match">'+esc(g['away']+' at '+g['home'])+('<small>Neutral site</small>' if g['neutral'] else '')+'</td>',
               '<td><b>'+esc(o['team'])+'</b></td>',
               '<td>'+('<span class="contract">'+esc(r['side'].upper()+' '+r['yes_team'])+'</span>' if r else '—')+'</td>',
               '<td class="num" data-sort="'+esc(value['central'] if value else '')+'">'+(dollars(value['central']) if value else '—')+'</td>',
               '<td class="num" data-sort="'+esc(r['cost']['price'] if r else '')+'">'+(dollars(r['cost']['price']) if r else '—')+'</td>',
               '<td class="num gap '+('positive' if gap is not None and gap>0 else 'negative' if gap is not None and gap<0 else '')+'" data-sort="'+esc(gap if gap is not None else '')+'">'+(dollars(gap,True) if gap is not None else '—')+'</td>',
               '<td class="wager" data-sort="'+esc(wager_label if wagers or settlements else '')+'">'+wager_cell+'</td>',
               '<td class="num" data-sort="'+esc(paid if paid is not None else summary['expected'] if summary else '')+'">'+(dollars(paid)+'<small>Actual payout</small>' if paid is not None else dollars(summary['expected'])+'<small>'+dollars(summary['win'])+' if win · expected above</small>' if summary else '—')+'</td>',
               '<td><button class="expand" aria-expanded="false" aria-label="Details for '+esc(o['team'])+'">Details</button></td>']
        ident=g['game_id']+'-'+o['team']
        body.append('<tbody data-id="'+esc(ident)+'" data-search="'+esc(g['away']+' '+g['home']+' '+o['team'])+'" data-gap="'+esc(gap if gap is not None else '')+'"><tr class="quote">'+''.join(cells)+'</tr><tr class="detail" hidden><td colspan="10">'+
                    ('<p class="reason">'+esc(reasons)+'</p>' if reasons else '')+
                    ('<p>Market settled. Cash-out proceeds and realized profit are not established by this export; original trade records remain below.</p>' if unresolved_close and wagers else '')+
                    '<p>ELWAY win: '+esc(o['displayed_win'] or '—')+'. '+('Difference before fee: '+dollars(Decimal(value['central'])-Decimal(r['cost']['price']),True)+'.' if r else '')+'</p>'+
                    '<p>'+esc(g['venue'] or '')+' · kickoff '+esc(display_time(kick))+'</p>'+
                    ('<p>ELWAY payout range: <b>'+dollars(value['low'])+'–'+dollars(value['high'])+'</b>. '+
                     ('After-fee difference range: <b>'+dollars(Decimal(value['low'])-Decimal(r['cost']['total']),True)+' to '+dollars(Decimal(value['high'])-Decimal(r['cost']['total']),True)+'</b>.' if r else '')+'</p>' if value else '')+
                    ('<p><b>Your recorded activity</b> · current open balance is not established by this export.</p><ul>'+wager_details+'</ul>' if wagers else '')+
                    ('<p>Assuming these recorded trades are purchases still held: total paid including recorded fees '+dollars(summary['spent'])+'; gross payout if '+esc(o['team'])+' wins '+dollars(summary['win'])+', tie '+dollars(summary['tie'])+', loss $0.00. ELWAY expected gross payout '+dollars(summary['expected'])+'; expected net '+dollars(summary['expected']-summary['spent'],True)+'. Payout includes returned stake; it is not profit.</p>' if summary else '')+
                    ('<p><b>Settlement reported by Kalshi</b>. Actual payout is gross return, not profit.</p><ul>'+settlement_details+'</ul>' if settlements else '')+
                    '<ul>'+(''.join(details) or '<li>No supported market matched.</li>')+'</ul></td></tr></tbody>')
    headers=[('Date / time','Kickoff in Central time'),('Match','Designated away and home teams'),('Outcome','Team whose normal full-game payout is represented'),('Contract','Observed purchase route; YES team or NO opponent'),('ELWAY Contract','ELWAY expected payout per contract, including $0.50 on a tie'),('Kalshi price','Observed offer for the same payout'),('Difference after fee ↓','ELWAY value minus offer and estimated one-contract fee'),('Recorded wager (incl. fees)','Each recorded trade: contract and quantity × paid price + recorded fees; current holdings unconfirmed'),('Payout','Actual gross payout when settled; otherwise ELWAY expected gross payout'),('','Expand all source and quote details')]
    th=''.join('<th scope="col"'+(' aria-sort="descending"' if i==6 else '')+'>'+('<button data-column="'+str(i)+'" title="'+esc(tip)+'">'+esc(label)+'</button>' if label else '')+'</th>' for i,(label,tip) in enumerate(headers))
    count=sum(r['route'] is not None for r in rows);top=next((r['gap'] for r in rows if r['gap'] is not None),None)
    diagnostics=''.join('<li>'+esc(json.dumps(d,sort_keys=True))+'</li>' for d in data['diagnostics']) or '<li>No unmatched inputs.</li>'
    activity_note=('<p class="activity-note"><b>Wager activity:</b> '+str(len(recorded))+' matched NFL trades · imported '+esc(display_time(activity['imported_at']))+'. Wagered and payout figures assume recorded purchases are still held. Current holdings are unconfirmed; activity can be newer than these saved prices.</p>' if activity else '<p class="activity-note">Wager activity not loaded. Attach a Kalshi activity export to identify recorded trades.</p>')
    activity_issues=(''.join('<li>'+esc(json.dumps(d,sort_keys=True))+'</li>' for d in activity['diagnostics']) if activity else '')
    clocks=json.dumps(dict(generated=display_time(data['generated_at']),capture=data['capture_started_at'],kickoffs=[g['kickoff'] for g in data['games'] if g['rank'] is not None and g['kickoff']],maxAge=data['guards']['quote_seconds'])).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pops&#39; Edge - NFL</title><style>
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:32px;background:#f6f7f9;color:#222}h1{margin:0 0 5px;font-size:30px;letter-spacing:-.5px}.subtitle{color:#666;margin:0 0 16px}.summary{display:flex;gap:24px;flex-wrap:wrap;font-size:14px;margin:18px 0}.summary b{font-size:18px}.toolbar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin:18px 0}input[type=search]{padding:9px 12px;border:1px solid #cbd0d8;border-radius:6px;font:inherit;min-width:250px}.toolbar label{font-size:14px}.scroll{overflow:auto;box-shadow:0 2px 12px #00000014;border-radius:10px}table.betsheet{border-collapse:collapse;width:100%;min-width:1060px;background:white;font-size:14px}.betsheet th{background:#1f2937;color:white;padding:0;text-align:left;white-space:nowrap;position:sticky;top:0}.betsheet th button{color:inherit;background:none;border:0;padding:12px 10px;font:inherit;font-weight:600;cursor:pointer;white-space:nowrap;width:100%;text-align:left}.betsheet th:hover{background:#374151}.betsheet td{padding:10px;border-bottom:1px solid #e5e7eb;vertical-align:middle}.betsheet tr.quote:hover{background:#f3f4f6}.num{font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}.match{white-space:nowrap;font-weight:600}small{display:block;font-size:11px;color:#697382;margin-top:3px;white-space:nowrap}.gap{background:#f0f5f9;font-weight:750;font-size:16px}.positive{color:#08764d}.negative{color:#a13c38}.wager{font-size:12px;white-space:nowrap}.wager b{color:#17694c}.activity-note{font-size:13px;color:#475569}.contract{font-size:12px;font-weight:600;background:#edf0f5;border-radius:4px;padding:4px 6px;white-space:nowrap}.expand{font:inherit;font-size:12px;border:1px solid #d4d9e0;border-radius:4px;background:white;padding:5px 8px;cursor:pointer}.detail td{background:#f0f3f7;padding:14px 24px;color:#465365;font-size:13px}.detail p{margin:5px 0}.detail li{margin:7px 0;overflow-wrap:anywhere}.reason{color:#93551f;font-weight:600}#age{font-size:13px;color:#705317;background:#fff5df;padding:9px 12px;border-radius:5px}.guide{font-size:13px;line-height:1.65;color:#647080;max-width:1100px;margin-top:20px}.guide summary{cursor:pointer;font-weight:600;color:#39485c}.guide a{color:#225c91}[hidden]{display:none!important}#count{color:#687281;font-size:13px}button:focus-visible,input:focus-visible{outline:3px solid #609ee2;outline-offset:2px}@media(max-width:650px){body{margin:16px}.toolbar{gap:12px}h1{font-size:25px}.summary{gap:14px}}
/* Quiet contrast and consistent controls keep attention on the comparisons. */
body{background:#fff;color:#242925;margin:24px}.toolbar{margin:0 0 14px;padding:16px 18px;background:#f5f7f4;border:1px solid #e0e5df;border-radius:10px;gap:20px}.toolbar label{display:inline-flex;align-items:center;gap:8px;color:#414b43;font-weight:550}.toolbar select{font:inherit;color:#252e27;background:white;border:1px solid #ccd5cd;border-radius:7px;padding:8px 10px;min-height:36px}.toolbar input[type=checkbox]{accent-color:#36705b;width:16px;height:16px;margin:0}.toolbar select:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid #36705b;outline-offset:3px}#count{margin:0 0 16px;color:#667169;font-size:12px;letter-spacing:.1px}.scroll{border:1px solid #dce2db;box-shadow:0 3px 14px #1c30200a;border-radius:10px}.betsheet th{background:#272e29}.betsheet th:hover{background:#39483d}.betsheet th button{padding:13px 11px;font-size:12px;letter-spacing:.1px}.betsheet td{padding:12px 11px;border-color:#e8ece6}.betsheet tbody:nth-of-type(even) .quote{background:#fafbf9}.betsheet tr.quote:hover{background:#f0f5ef}.gap{background:#f0f5ef;font-size:15px}.positive{color:#246347}.negative{color:#94504b}.contract{background:#eef1eb;color:#344239;border:1px solid #e1e6dc}.expand{border-color:#ced8cb;color:#43563f;border-radius:6px}.expand:hover{background:#f0f5ed}.detail td{background:#f4f6f2}.guide{color:#687265}.guide summary{color:#374735}@media(max-width:650px){body{margin:14px}.toolbar{padding:12px;gap:12px}}
'''+BRAND_CSS+'''</style></head><body>'''+f'''<h1>NFL Bet Sheet</h1><p class="subtitle">Pops’ Edge · {data['season']} / Week {data['week']} · Largest ELWAY–Kalshi differences after fee first</p>
<p id="age">Saved snapshot · {esc(display_time(data['generated_at']))}. Prices do not update in this page.</p>
<div class="summary"><span><b>{data['scheduled_games']}</b> games</span><span><b>{count}</b> comparable outcomes shown</span><span>Largest difference after fee <b>{dollars(top,True) if top is not None else '—'}</b></span></div>
<div class="toolbar"><input id="search" type="search" aria-label="Filter team abbreviation" placeholder="Find a team or match"><label><input id="positive" type="checkbox"> Positive differences only</label><span id="count"></span></div>
<div class="scroll"><table class="betsheet"><thead><tr>{th}</tr></thead>{''.join(body)}</table></div><p id="empty" hidden>No outcomes match these filters.</p>
<div class="guide"><p><b>Difference after fee = ELWAY Contract − Kalshi price − estimated one-contract fee.</b> ELWAY Contract is expected payout per contract: $1.00 on a win, $0.00 on a loss and $0.50 on a tie. Wagered includes recorded purchase fees. Expected payout is the model-weighted gross return on the recorded quantity, including tie outcomes; the smaller “if win” figure is the gross return if that row’s team wins. These are outcome-level totals for each game, assuming purchases still held. They are not confirmed open balances. Payout includes returned stake; it is not profit. Dollars display to two decimals; calculations retain full precision. Original win probabilities and before-fee differences remain in Details.</p>
<details><summary>Calculation notes, source times and unmatched inputs</summary>{activity_note}<p>The default order uses the largest signed difference after the estimated one-contract fee, matching the bet-sheet workflow. Both team outcomes are shown. Each outcome has two equivalent routes for a normal win, loss or tie: team YES and opponent NO. We show the lower usable offer; if prices tie, lower estimated total cost wins, then contract ID provides a stable display order. Details show contracts available at each captured offer, rounded to the nearest whole contract. Displayed timestamps are rounded to the nearest minute in Central time; eligibility checks use the exact timestamps. All four routes for a game remain available across its two Details panels. Click column headings to sort. Missing or excluded quotes stay at the bottom and have no numeric difference.</p><p>Payout ranges assume rounding to the nearest displayed ELWAY percentage unit; they are not confidence intervals. Positive differences are not proof of forecast accuracy or a wagering recommendation. No stake sizing, positions or order execution is included. Fees illustrate one standard taker contract, including cent alignment. Fair-price cancellation outcomes are not modeled.</p>
<p>ELWAY updated: {esc(display_time(data['forecast_updated_at']))}<br>Verified: {esc(display_time(data['forecast_verified_at']))}<br>Schedule received: {esc(display_time(data['schedule_received_at']))}<br>Kalshi capture: {esc(display_time(data['capture_started_at']))} to {esc(display_time(data['capture_completed_at']))}<br>Snapshot built: {esc(display_time(data['generated_at']))}</p>
<p>Build-time guards: quotes/catalog ≤5 minutes; schedule ≤24 hours; ELWAY ≤8 days; kickoff still ahead. The table is a saved snapshot. Refresh inputs and rebuild for newer comparisons.</p><ul>{diagnostics}</ul><p>Activity diagnostics:</p><ul>{activity_issues or '<li>None.</li>'}</ul><p><a href="comparison.json">Saved comparison data</a> · <a href="complete.json">Manifest</a></p></details></div>
<script>const clocks={clocks};
'''+'''const table=document.querySelector('table');const groups=[...table.querySelectorAll('tbody')];function filter(){const term=document.getElementById('search').value.trim().toUpperCase();let n=0;groups.forEach(g=>{g.hidden=!g.dataset.search.includes(term)||(document.getElementById('positive').checked&&!(g.dataset.gap!==''&&Number(g.dataset.gap)>0));if(!g.hidden)n++});document.getElementById('count').textContent=n+' outcomes shown';document.getElementById('empty').hidden=n>0}document.getElementById('search').addEventListener('input',filter);document.getElementById('positive').addEventListener('change',filter);filter();document.querySelectorAll('.expand').forEach(b=>b.addEventListener('click',()=>{const row=b.closest('tbody').querySelector('.detail');row.hidden=!row.hidden;b.setAttribute('aria-expanded',String(!row.hidden));b.textContent=row.hidden?'Details':'Close'}));let col=6,desc=true;const labels=[...document.querySelectorAll('th button')].map(b=>b.textContent.replace(' ↓',''));document.querySelectorAll('th button').forEach(button=>button.addEventListener('click',()=>{const next=Number(button.dataset.column);desc=next===col?!desc:next>=4;col=next;const sorted=[...groups].sort((a,b)=>{let x=a.rows[0].cells[col],y=b.rows[0].cells[col];x=x.dataset.sort??x.textContent;y=y.dataset.sort??y.textContent;if(x===''||y==='')return x===''?(y===''?0:1):-1;const cmp=[4,5,6,8].includes(col)?Number(x)-Number(y):x.localeCompare(y);return (desc?-cmp:cmp)||a.dataset.id.localeCompare(b.dataset.id)});sorted.forEach(g=>table.appendChild(g));document.querySelectorAll('th').forEach(h=>h.removeAttribute('aria-sort'));document.querySelectorAll('th button').forEach((b,i)=>{b.textContent=labels[i]+(Number(b.dataset.column)===col?(desc?' ↓':' ↑'):'')});button.closest('th').setAttribute('aria-sort',desc?'descending':'ascending')}));function age(){const now=Date.now(),stale=now-Date.parse(clocks.capture)>clocks.maxAge*1000,started=clocks.kickoffs.some(k=>Date.parse(k)<=now);document.getElementById('age').textContent=(stale?'Archived prices — refresh before using. ':'Saved snapshot — prices do not update. ')+(started?'A previously comparable game has reached kickoff. ':'')+'Data snapshot: '+clocks.generated}age();setInterval(age,30000);</script></body></html>'''
