"""Full-season presentation over immutable weekly snapshots and workbook rows."""
from copy import deepcopy
import json
import re
from decimal import Decimal
from pathlib import Path
import nfl_comparison_board as board
import nfl_excel_import as excel
import nfl_forecast_import as source
from nfl_board_view import render as weekly_render,esc,display_time,dollars
from nfl_historical_comparisons import attach_history
import nfl_completion as completion


def assemble(data_root,folders,candidate=None,now=None):
    now=now or source.now();root=Path(data_root)
    snapshots=[board.replay(p,check_html=False) for p in folders]
    if candidate is None:
        records=[]
        for p in root.glob('forecasts/sources/*/receipt.json'):
            receipt=json.loads(p.read_text());raw=(p.parent/'source.xlsx').read_bytes()
            if source.digest(raw)!=receipt['source_sha256']:raise ValueError('Workbook identity mismatch')
            time_path=p.parent/'file-time.json'
            file_time=json.loads(time_path.read_text()) if time_path.exists() else None
            if file_time:
                from nfl_forecast_time import validate
                validate(file_time,raw,now)
            parsed=excel.parse(raw,file_time);records.append(dict(source=receipt,**parsed))
        if not records:raise ValueError('Select an ELWAY workbook to display the full season')
        candidate=max(records,key=lambda r:(r['source']['imported_at'],r['source']['source_sha256']))
    season=candidate['season'];saved={};activities=[]
    for snap in snapshots:
        if snap['season']!=season:continue
        activities.append(snap.get('activity',{}))
        for g in snap['games']:
            key=(g['week'],g['home'],g['away'])
            if key not in saved or snap['generated_at']>saved[key][0]['generated_at']:saved[key]=(snap,g)
    # Use verified observations for both unknown dates and sporting results.
    observations,completion_issues=completion.latest(root,season,now)
    undated={}
    for receipt in observations.values():
        if receipt.get('error'):continue
        for g in receipt['games']:
            if g['kickoff'] is None:undated[(g['week'],g['home'],g['away'])]=(g,receipt['observed_at'])
    # Reparse only the newest selected activity export across all known games.
    # Weekly overlays contain only that week's matches; never add older exports.
    choices=[(snap['activity']['imported_at'],Path(folder),snap['activity']) for folder,snap in zip(folders,snapshots) if snap['season']==season and snap.get('activity')]
    activity=None
    if choices:
        at,folder,_=max(choices,key=lambda x:(x[0],str(x[1])))
        from nfl_activity import activity_map,parse_current
        raw=(folder/'inputs/activity.csv').read_bytes()
        all_games={'games':[pair[1] for pair in saved.values()]}
        activity=parse_current(raw,at,activity_map(raw,folder/'inputs',all_games))
    games=[]
    for row in candidate['rows']:
        key=(row['week'],row['home'],row['away']);pair=saved.get(key)
        if pair:
            snap,original=pair;g=deepcopy(original)
            g['source_note']=('File creation time — publication-time proxy ' if snap.get('forecast_time_basis') else 'ELWAY updated ')+display_time(snap['forecast_updated_at'])+' · Prices captured '+display_time(snap['capture_completed_at'])
            if key in undated and undated[key][1]>=snap.get('schedule_received_at',''):
                g['kickoff']=None
                g['source_note']+=' · Schedule received '+display_time(undated[key][1])+' · Date/time TBD'
            done=False  # Sporting finality comes from validated official summaries below.
            started=bool(g['kickoff'] and board.kalshi.aware(g['kickoff'])<=board.kalshi.aware(now))
            stale=(board.kalshi.aware(now)-board.kalshi.aware(snap['capture_started_at'])).total_seconds()>snap['guards']['quote_seconds']
            g['display_status']='Completed' if done else 'Date/time TBD' if not g['kickoff'] else 'Started' if started else 'Archived prices' if stale else 'Captured prices'
            if stale or started or done or not g['kickoff']:
                for o in g['outcomes']:
                    for r in o['routes']:r['usable']=False
            g['completed']=done
        else:
            g=dict(game_id=f"forecast-{season}-{row['week']}-{row['home']}-{row['away']}",season=season,week=row['week'],home=row['home'],away=row['away'],neutral=row['neutral'],kickoff=None,status='UNKNOWN',venue=None,issues=['Prices not captured; generate the Bet Sheet for a comparison.'],score=None,rank=None,completed=False,display_status='Prices not captured',source_note='Workbook updated '+display_time(candidate['updated_at'])+' · Forecast preview; no weekly comparison captured',outcomes=[dict(team=row[role],displayed_win=row[role+'_win'],payout=None,routes=[],best=None) for role in ('home','away')])
        if not pair and key in undated:
            official,at=undated[key]
            g.update(official)
            g['display_status']='Date/time TBD'
            g['issues']=['Date/time TBD. Awaiting the NFL schedule; no action needed.']
            g['source_note']+=' · Official schedule received '+display_time(at)
        if not pair and candidate.get('file_time'):
            g['source_note']=g['source_note'].replace('Workbook updated ', 'File creation time — publication-time proxy ')
        games.append(g)
    completion.apply(games,observations,now)
    history_issues=attach_history(root,games,list(zip(folders,snapshots)),now)
    result=dict(schema='nfl-season-view-v1',season=season,week='All',generated_at=now,games=games,guards=board.GUARDS,scheduled_games=len(games),ranked_games=sum(any(r['usable'] for o in g['outcomes'] for r in o['routes']) for g in games),diagnostics=history_issues+completion_issues,forecast_updated_at=candidate['updated_at'],forecast_verified_at=None,schedule_received_at=None,capture_started_at=now,capture_completed_at=now)
    if candidate.get('file_time'):result['forecast_time_basis']=candidate['file_time']['rule']
    if activity:result['activity']=activity
    from nfl_accounting import load
    result['accounting'], accounting_issues = load(root, games, now)
    result['accounting_enabled'] = (root/'accounting').exists()
    result['diagnostics'].extend(accounting_issues)
    if choices and result['accounting_enabled']:
        from nfl_accounting import latest_activity
        try:
            recent = latest_activity(root, now)
            if recent and (not activity or board.kalshi.aware(recent[0]) >= board.kalshi.aware(activity['imported_at'])):
                at, raw = recent
                result['activity'] = parse_current(raw, at, activity_map(raw,folder/'inputs',{'games':games}))
        except (OSError, ValueError, KeyError) as exc:
            result['diagnostics'].append(dict(reason='Accounting activity unavailable: '+str(exc)))
    return result



def contract_result(game, side, yes_team):
    """Sporting alignment of this displayed contract, never realized cash flow."""
    result=game.get('official_result',{})
    if not game.get('completed') or result.get('state')!='final':return ''
    if side not in ('YES','NO') or yes_team not in (game['home'],game['away']):return ''
    home,away=result['home_score'],result['away_score']
    if home==away:
        icon,kind,label='—','tie','Tied final result'
    else:
        winner=game['home'] if home>away else game['away']
        aligned=(yes_team==winner) if side=='YES' else (yes_team!=winner)
        icon,kind,label=('✓','aligned','Matched final result') if aligned else ('×','opposed','Did not match final result')
    note=label+' — game result only; does not indicate sale proceeds, payout or profit.'
    return '<span class="result-mark '+kind+'" role="img" aria-label="'+esc(note)+'" title="'+esc(note)+'">'+icon+'</span>'


def render(data):
    html=weekly_render(data)
    html=html.replace('</style>', 'tbody[data-completed="true"] .contract{background:#e5e7eb;color:#4b5563;border-color:#d1d5db}</style>',1)
    html=html.replace('</style>', '.result-mark{display:inline-flex;align-items:center;justify-content:center;margin-left:7px;width:20px;height:20px;border-radius:50%;font-size:16px;font-weight:700;vertical-align:middle}.result-mark.aligned{color:#26704c;background:#edf5f0}.result-mark.opposed{color:#a34b48;background:#fbefee}.result-mark.tie{color:#64748b;background:#eef0f3}.result-legend{font-size:12px;color:#64748b;margin:0 0 14px}.result-legend .result-mark{margin:0 3px 0 12px}.result-legend .result-mark:first-child{margin-left:0}.contract-result{display:inline-flex;flex-flow:row nowrap;align-items:center;gap:8px;white-space:nowrap}.contract-result .contract{display:inline-block;flex:none}.contract-result .result-mark{display:inline-flex;flex:none;margin:0}.betsheet th:nth-child(4),.betsheet td:nth-child(4){width:150px;min-width:150px;white-space:nowrap}.betsheet th:nth-child(6),.betsheet td:nth-child(6){width:180px;min-width:180px}.betsheet th:nth-child(5),.betsheet td:nth-child(5){width:112px;min-width:112px}.betsheet th:nth-child(7),.betsheet td:nth-child(7){width:140px;min-width:140px}.betsheet th:nth-child(9),.betsheet td:nth-child(9){width:100px;min-width:100px}.betsheet th:nth-child(10),.betsheet td:nth-child(10){width:72px}'+'</style>',1)
    html=html.replace('<div class="scroll">', '<p class="result-legend"><span class="result-mark aligned">✓</span> Matched final result <span class="result-mark opposed">×</span> Did not match <span class="result-mark tie">—</span> Tie · Game result only; separate from your payout or profit.</p>'+'<div class="scroll">',1)
    for g in data['games']:
        for o in g['outcomes']:
            ident=esc(g['game_id']+'-'+o['team'])
            html=html.replace('<tbody data-id="'+ident+'"','<tbody data-week="'+str(g['week'])+'" data-game="'+esc(g['game_id'])+'" data-completed="'+str(g['completed']).lower()+'" data-id="'+ident+'"')
        match=esc(g['away']+' at '+g['home'])
        # Match can repeat in later weeks: target each tbody rather than global text.
        for o in g['outcomes']:
            ident=esc(g['game_id']+'-'+o['team']);start=html.index('data-id="'+ident+'"');end=html.index('</tbody>',start)
            section=html[start:end]
            status=g['display_status'] if g['display_status']!='Captured prices' else 'Scheduled'
            result=g.get('official_result',{})
            if result.get('state')=='final':
                status=('Final (OT)' if result['overtime'] else 'Final')+': '+g['away']+' '+str(result['away_score'])+'–'+g['home']+' '+str(result['home_score'])
            subtitle=('Neutral · ' if g['neutral'] else '')+status
            main,rest=section.split('</tr>',1)
            cells=list(re.finditer(r'<td\b[^>]*>.*?</td>',main,re.S))
            cell=cells[1]
            main=main[:cell.start()]+'<td class="match" data-sort="'+match+'">'+match+'<small>'+esc(subtitle)+'</small></td>'+main[cell.end():]
            cell=cells[0]
            date_cell=cell.group().replace('<small>',' · Week '+str(g['week'])+'<small>',1)
            main=main[:cell.start()]+date_cell+main[cell.end():]
            section=main+'</tr>'+rest
            note='<p>'+esc(g['source_note'])+'</p>'
            if result:
                note+='<p><b>Official NFL result</b> · '+esc(status)
                if result.get('observed_at'):note+=' · Observed '+esc(display_time(result['observed_at']))
                if result.get('url'):note+=' · '+esc(result['url'])
                note+='</p><p>'+esc('; '.join(result.get('issues',[])))+'</p><p>Saved source: '+esc(result.get('source',''))+'</p>'
            section=section.replace('<p>ELWAY win:', note+'<p>ELWAY win:')
            historical=o.get('historical')
            if historical:
                route=historical['route'];value=historical['outcome']['payout']
                gap=Decimal(value['central'])-Decimal(route['cost']['total'])
                main,rest=section.split('</tr>',1)
                cells=list(re.finditer(r'<td\b[^>]*>.*?</td>',main,re.S))
                # Manual sorts use full-precision values; tbody data-gap stays empty
                # so historical rows remain outside current filters and counts.
                replacements=[
                    '<td><span class="contract">'+esc(route['side'].upper()+' '+route['yes_team'])+'</span></td>',
                    '<td class="num" data-sort="'+esc(value['central'])+'">'+dollars(value['central'])+'</td>',
                    '<td class="num" data-sort="'+esc(route['cost']['price'])+'">'+dollars(route['cost']['price'])+'<small>'+esc(display_time(route['book_received_at']))+'</small></td>',
                    '<td class="num gap" data-sort="'+esc(gap)+'">'+dollars(gap,True)+'</td>']
                for index in range(6,2,-1):
                    cell=cells[index];main=main[:cell.start()]+replacements[index-3]+main[cell.end():]
                detail=('<p><b>Historical comparison</b> · quote captured '+esc(display_time(route['book_received_at']))+
                        (' · File creation time — publication-time proxy ' if historical.get('forecast_time_basis') else ' · ELWAY updated ')+esc(display_time(historical['forecast_updated_at']))+
                        ' · verified '+esc(display_time(historical['forecast_verified_at']))+'.</p><p>'+esc(route['ticker'])+
                        ' · '+esc(route['side'].upper())+' · original ELWAY win '+esc(historical['outcome']['displayed_win'])+
                        ' · original contract value '+dollars(value['central'])+' · estimated fee '+dollars(route['cost']['estimated_fee'])+
                        ' · total one-contract cost '+dollars(route['cost']['total'])+'. '+esc(historical['fee_model'])+
                        '. These saved values are excluded from current comparisons and difference filters.</p><p>Saved source: '+esc(historical['source_bundle'])+'</p>')
                rest=rest.replace('<td colspan="10">','<td colspan="10">'+detail,1)
                rest=rest.replace('<p>ELWAY win:', '<p>Latest snapshot ELWAY win:')
                rest=rest.replace('<p>ELWAY payout range:', '<p>Latest snapshot ELWAY payout range:')
                section=main+'</tr>'+rest
            elif not any(r['usable'] for r in o['routes']):
                section=section.replace('<td>—</td>','<td>—<small>No saved pregame comparison</small></td>',1)
            main,rest=section.split('</tr>',1)
            badge=re.search(r'<span class="contract">(YES|NO) ([A-Z]+)</span>',main)
            if badge:
                marker=contract_result(g,badge[1],badge[2])
                if marker:
                    # Keep manual Contract sorting based on the label, not the icon.
                    main=main.replace('<td>'+badge[0],'<td data-sort="'+esc(badge[1]+' '+badge[2])+'">'+badge[0],1)
                    main=main.replace(badge[0],'<span class="contract-result">'+marker+badge[0]+'</span>',1)
            section=main+'</tr>'+rest
            html=html[:start]+section+html[end:]
    weeks=sorted({g['week'] for g in data['games']});teams=sorted({g[k] for g in data['games'] for k in ('home','away')})
    controls='<label>Week <select id="seasonWeek"><option value="">All weeks</option>'+''.join(f'<option>{w}</option>' for w in weeks)+'</select></label><label>Team <select id="seasonTeam"><option value="">All teams</option>'+''.join('<option>'+t+'</option>' for t in teams)+'</select></label>'
    html=html.replace('<div class="toolbar">','<div class="toolbar">'+controls)
    # The tab already identifies this view; begin with filters, then their summary.
    a=html.index('<h1>');b=html.index('<div class="toolbar">',a)
    html=html[:a]+html[b:]
    html=html.replace('<input id="search" type="search" aria-label="Filter team abbreviation" placeholder="Find a team or match">','')
    html=html.replace('<span id="count"></span></div>','</div><p id="count" role="status" aria-live="polite"></p>')
    html=html.replace("const term=document.getElementById('search').value.trim().toUpperCase();", "const term='';")
    html=html.replace("document.getElementById('search').addEventListener('input',filter);", '')
    html=html.replace('<label><input id="positive" type="checkbox"> Positive differences only</label>', '<label>Difference after fee <select id="positive"><option value="">All</option><option value="0">Greater than $0.00</option><option value="0.05">Greater than $0.05</option><option value="0.075">Greater than $0.075</option><option value="0.10">Greater than $0.10</option></select></label><label><input id="omitCompleted" type="checkbox"> Omit completed games</label>')
    html=html.replace("document.getElementById('positive').checked&&!(g.dataset.gap!==''&&Number(g.dataset.gap)>0)", "document.getElementById('positive').value!==''&&!(g.dataset.gap!==''&&Number(g.dataset.gap)>Number(document.getElementById('positive').value))")
    a=html.index('function age(){');b=html.index('</script>',a)
    html=html[:a]+html[b:]
    html=html.replace("let n=0;groups.forEach", "const week=document.getElementById('seasonWeek').value,team=document.getElementById('seasonTeam').value,omitCompleted=document.getElementById('omitCompleted').checked;let n=0;groups.forEach")
    html=html.replace("g.hidden=!g.dataset.search.includes(term)","g.hidden=(week!==''&&g.dataset.week!==week)||(team!==''&&!g.dataset.search.split(' ').includes(team))||(omitCompleted&&g.dataset.completed==='true')||!g.dataset.search.includes(term)")
    html=html.replace("document.getElementById('count').textContent=n+' outcomes shown';", "const visible=groups.filter(g=>!g.hidden),gaps=visible.filter(g=>g.dataset.gap!=='').map(g=>Number(g.dataset.gap));document.getElementById('count').textContent=new Set(visible.map(g=>g.dataset.game)).size+' games · '+n+' outcomes shown · '+gaps.length+' current comparable outcomes';")
    extra="document.querySelectorAll('#seasonWeek,#seasonTeam,#omitCompleted').forEach(e=>e.addEventListener('change',filter));"
    html=html.replace('</script>',extra+'</script>')
    # A composite view has no single source capture or verification time.
    a=html.index('<p>File creation time — publication-time proxy' if data.get('forecast_time_basis') else '<p>ELWAY updated:');b=html.index('</p>',a)+4
    html=html[:a]+'<p>Full-season view assembled: '+esc(display_time(data['generated_at']))+'. Individual game source times appear in Details. Price captures vary by week; archived prices are excluded from positive differences. Filtering does not refresh prices. Workbook-only games show probabilities as an unverified preview; no contract value or difference is inferred.</p>'+html[b:]
    if data.get('forecast_time_basis'):
        html=html[:a]+'<p>File creation time — publication-time proxy. Publisher update time and model age are unknown.</p>'+html[a:]
    html=html.replace('<p><a href="comparison.json">Saved comparison data</a> · <a href="complete.json">Manifest</a></p>','')
    html=html.replace('Missing or excluded quotes stay at the bottom and have no numeric difference.', 'Historical comparisons retain their original values and dated quote, but stay outside current comparison ranking and difference filters. Missing comparisons stay unavailable.')
    if data['diagnostics']:
        html=html.replace('<div class="scroll">','<p class="reason">Some saved history or official results could not be verified. See calculation notes for details.</p><div class="scroll">',1)
    if data.get('accounting_enabled'):
        html=html.replace('Some saved history or official results could not be verified.', 'Some saved history, accounting or official results could not be verified.')
    return html
