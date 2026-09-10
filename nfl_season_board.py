"""Full-season presentation over immutable weekly snapshots and workbook rows."""
from copy import deepcopy
import json
from decimal import Decimal
from pathlib import Path
import nfl_comparison_board as board
import nfl_excel_import as excel
import nfl_forecast_import as source
from nfl_board_view import render as weekly_render,esc,display_time


def assemble(data_root,folders,candidate=None,now=None):
    now=now or source.now();root=Path(data_root)
    snapshots=[board.replay(p,check_html=False) for p in folders]
    if candidate is None:
        records=[]
        for p in root.glob('forecasts/sources/*/receipt.json'):
            receipt=json.loads(p.read_text());raw=(p.parent/'source.xlsx').read_bytes()
            if source.digest(raw)!=receipt['source_sha256']:raise ValueError('Workbook identity mismatch')
            parsed=excel.parse(raw);records.append(dict(source=receipt,**parsed))
        if not records:raise ValueError('Select an ELWAY workbook to display the full season')
        candidate=max(records,key=lambda r:(r['source']['imported_at'],r['source']['source_sha256']))
    season=candidate['season'];saved={};activities=[]
    for snap in snapshots:
        if snap['season']!=season:continue
        activities.append(snap.get('activity',{}))
        for g in snap['games']:
            key=(g['week'],g['home'],g['away'])
            if key not in saved or snap['generated_at']>saved[key][0]['generated_at']:saved[key]=(snap,g)
    # Successful schedule-only captures can establish TBD without a quote bundle.
    latest_schedules={};undated={}
    for path in root.glob('schedules/*/receipt.json'):
        receipt=json.loads(path.read_text())
        if receipt.get('season')!=season or receipt.get('error'):continue
        week=receipt['week']
        if week not in latest_schedules or receipt['completed_at']>latest_schedules[week][0]:latest_schedules[week]=(receipt['completed_at'],path.parent)
    for at,path in latest_schedules.values():
        receipt=board.schedule.replay(path)
        for g in receipt['rows']:
            if g['kickoff'] is None:undated[(g['week'],g['home'],g['away'])]=(g,at)
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
    trades=activity['trades'] if activity else []
    settlements=activity.get('settlements',[]) if activity else []
    completed={t['game_id'] for t in settlements if not t['needs_review']}
    games=[]
    for row in candidate['rows']:
        key=(row['week'],row['home'],row['away']);pair=saved.get(key)
        if pair:
            snap,original=pair;g=deepcopy(original)
            g['source_note']='ELWAY updated '+display_time(snap['forecast_updated_at'])+' · Prices captured '+display_time(snap['capture_completed_at'])
            if key in undated and undated[key][1]>=snap.get('schedule_received_at',''):
                g['kickoff']=None
                g['source_note']+=' · Schedule received '+display_time(undated[key][1])+' · Date/time TBD'
            done=g['game_id'] in completed or g['status'].upper() in ('FINAL','FINAL_OVERTIME','COMPLETED','COMPLETE','CLOSED')
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
        games.append(g)
    result=dict(schema='nfl-season-view-v1',season=season,week='All',generated_at=now,games=games,guards=board.GUARDS,scheduled_games=len(games),ranked_games=sum(any(r['usable'] for o in g['outcomes'] for r in o['routes']) for g in games),diagnostics=[],forecast_updated_at=candidate['updated_at'],forecast_verified_at=None,schedule_received_at=None,capture_started_at=now,capture_completed_at=now)
    if activity:result['activity']=activity
    return result


def render(data):
    html=weekly_render(data)
    for g in data['games']:
        for o in g['outcomes']:
            ident=esc(g['game_id']+'-'+o['team'])
            html=html.replace('<tbody data-id="'+ident+'"','<tbody data-week="'+str(g['week'])+'" data-game="'+esc(g['game_id'])+'" data-completed="'+str(g['completed']).lower()+'" data-id="'+ident+'"')
        match=esc(g['away']+' at '+g['home'])
        # Match can repeat in later weeks: target each tbody rather than global text.
        for o in g['outcomes']:
            ident=esc(g['game_id']+'-'+o['team']);start=html.index('data-id="'+ident+'"');end=html.index('</tbody>',start)
            section=html[start:end];section=section.replace(match+'</td>',match+'<small>Week '+str(g['week'])+(' · '+esc(g['display_status']) if g['display_status']!='Captured prices' else '')+'</small></td>')
            if g['neutral']:section=section.replace('<small>Neutral site</small>','<small>Week '+str(g['week'])+' · Neutral'+(' · '+esc(g['display_status']) if g['display_status']!='Captured prices' else '')+'</small>')
            section=section.replace('<p>ELWAY win:', '<p>'+esc(g['source_note'])+'</p><p>ELWAY win:')
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
    html=html.replace("document.getElementById('count').textContent=n+' outcomes shown';", "const visible=groups.filter(g=>!g.hidden),gaps=visible.filter(g=>g.dataset.gap!=='').map(g=>Number(g.dataset.gap));document.getElementById('count').textContent=new Set(visible.map(g=>g.dataset.game)).size+' games · '+n+' outcomes shown · '+gaps.length+' comparable outcomes';")
    extra="document.querySelectorAll('#seasonWeek,#seasonTeam,#omitCompleted').forEach(e=>e.addEventListener('change',filter));"
    html=html.replace('</script>',extra+'</script>')
    # A composite view has no single source capture or verification time.
    a=html.index('<p>ELWAY updated:');b=html.index('</p>',a)+4
    html=html[:a]+'<p>Full-season view assembled: '+esc(display_time(data['generated_at']))+'. Individual game source times appear in Details. Price captures vary by week; archived prices are excluded from positive differences. Filtering does not refresh prices. Workbook-only games show probabilities as an unverified preview; no contract value or difference is inferred.</p>'+html[b:]
    html=html.replace('<p><a href="comparison.json">Saved comparison data</a> · <a href="complete.json">Manifest</a></p>','')
    return html
