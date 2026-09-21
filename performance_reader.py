"""Read-only presentation adapters; never capture, publish, initialize or select reports."""
from decimal import Decimal, localcontext
from datetime import date as calendar_date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zoneinfo import ZoneInfo
import hashlib
import json
import posixpath
import re
from nfl_reader_cache import ReaderCache

import nfl_forecast_import as base
from nfl_performance import Performance, instant
from nfl_brand import BRAND_CSS, BRAND_MARK
from forecast_standalone_operations import OperationsError

READER_ERRORS = (ValueError, OSError, KeyError, TypeError, OperationsError)

CENTRAL = ZoneInfo('America/Chicago')
HEX = r'[0-9a-f]{64}'
DEFAULT_MLB = Path.home()/'PopsEdgeReports/mlb/real/2026-09-13-accepted/reports'
NFL_PERIODS = [('7','Last 7 Days'),('14','Last 14 Days'),('60','Last 60 Days'),
               ('90','Last 90 Days'),('season','This Season'),('custom','Custom Period')]


def nfl_filtered(games, query, cutoff):
    period=query.get('period',['season'])[0];team=query.get('team',[''])[0]
    if period not in dict(NFL_PERIODS):raise ValueError('Choose a supported period')
    if team and team not in {g[k] for g in games for k in ('home','away')}:
        raise ValueError('Choose a team from these saved reports')
    end=cutoff.astimezone(CENTRAL).date();start=None
    if period=='custom':
        try:
            start=calendar_date.fromisoformat(query.get('from',[''])[0])
            end=calendar_date.fromisoformat(query.get('to',[''])[0])
        except ValueError:raise ValueError('Choose both From and To dates') from None
        if start>end:raise ValueError('From must be on or before To')
        if end>cutoff.astimezone(CENTRAL).date():raise ValueError('To cannot be after the saved data date')
    elif period!='season':start=end-timedelta(days=int(period)-1)
    return [g for g in games if (not team or team in (g['home'],g['away'])) and
            (period=='season' or (g.get('kickoff') and start<=instant(g['kickoff']).astimezone(CENTRAL).date()<=end))]


def safe_path(root, relative=''):
    root = Path(root).absolute()
    target = root/relative
    if '..' in Path(relative).parts or Path(relative).is_absolute():
        raise ValueError('Report path is not allowed')
    for part in (target, *target.parents):
        if part.is_symlink():
            raise ValueError('Aliased report paths are not allowed')
        if part == root:
            break
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Report path leaves its configured root')
    return target


def text(value):
    return escape(str(value))


def number(value, percent=False):
    if value is None:
        return 'Unavailable'
    n = Decimal(str(value)) * (100 if percent else 1)
    return f'{n:.2f}' + ('%' if percent else '')


def reference_comparison(report):
    """Display-only reference on the report's exact paired scored population."""
    scored = [g for g in report['games'] if g['state'] == 'scored']
    if len(scored) != report['paired_games']:
        raise ValueError('Scored population does not reconcile')
    if not scored:
        return None, None, None
    with localcontext() as context:
        context.prec = 50
        reference = sum((Decimal('0.5') - Decimal(g['outcome']['payout'])) ** 2 for g in scored) / len(scored)
        return (reference, reference - Decimal(report['means']['elway_error']),
                reference - Decimal(report['means']['kalshi_error']))


def date(value):
    if not value:
        return 'Unavailable'
    return instant(value).astimezone(CENTRAL).strftime('%b %d, %Y, %I:%M %p %Z')


def navigation(sport, area):
    bet = '/mlb' if sport == 'mlb' else '/'
    def link(url, label, active):
        return f'<a href="{url}"'+(' aria-current="page"' if active else '')+f'>{label}</a>'
    return ('<script src="/navigation-state.js"></script><nav class="product-nav" aria-label="Area">'+link(bet,'Bet Sheet',area=='bet')+
        link('/performance/'+sport,'Performance',area=='performance')+'</nav>'+
        '<nav class="product-nav sports" aria-label="Sport">'+
        link('/performance/nfl' if area=='performance' else '/', 'NFL',sport=='nfl')+
        link('/performance/mlb' if area=='performance' else '/mlb','MLB',sport=='mlb')+'</nav>')


NAV_CSS = '.product-nav{display:flex;gap:8px;margin:12px 0}.product-nav a{display:inline-block;padding:10px 18px;border:1px solid #d7dfe7;border-radius:7px;background:white;color:#17314c;text-decoration:none;font-weight:600}.product-nav a[aria-current=page]{background:#102b49;color:white}.product-nav.sports{margin-bottom:24px}.product-nav a:focus-visible{outline:3px solid #16834c;outline-offset:2px}'
CSS = '''*{box-sizing:border-box}body{margin:28px;background:#f5f7fa;color:#18304a;font:15px/1.5 system-ui}main{max-width:1250px;margin:auto}h1{margin:0}h2{margin:0 0 10px}p{margin:8px 0}.panel{background:white;border:1px solid #dbe2e9;border-radius:12px;padding:24px;margin:18px 0}.filters{display:flex;align-items:center;gap:18px;flex-wrap:wrap;background:#f3f6fa;border:1px solid #dce4ed;border-radius:10px;padding:16px}select,button{font:inherit;background:white;border:1px solid #c9d5e2;border-radius:6px;padding:6px 12px;color:#18304a}.metrics{display:flex;gap:18px;flex-wrap:wrap;margin:18px 0}.metric{flex:1;min-width:170px;padding:18px;background:#f2f6fa;border-radius:8px}.metric b{font-size:28px;display:block}.muted{color:#60738a}.notice{padding:14px;background:#fff6e5;border-left:4px solid #b88322}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:white}th{background:#102b49;color:white;text-align:left}td,th{padding:14px;border-bottom:1px solid #e1e7ed;vertical-align:top}td small{display:block;color:#60738a}table[aria-label="Comparison with 50% reference"] tbody th{background:#eaf0f6;color:#20334a;font-weight:600}summary{cursor:pointer;font-weight:600}details p{max-width:650px}a{color:#195c89}iframe{width:100%;height:80vh;border:1px solid #dbe2e9;border-radius:10px;background:white}dl{display:grid;grid-template-columns:minmax(100px,200px) 1fr;gap:8px}dd{margin:0;overflow-wrap:anywhere}.error{color:#8d3c21}@media(max-width:650px){body{margin:12px}.panel{padding:16px}.metric{min-width:120px}td,th{padding:10px}}'''


CSS += """.summary-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.summary-heading h2{margin:0}.report-update{max-width:100%}.summary-dates{margin:12px 0 16px}.coverage-note{font-size:14px;font-weight:400;color:#7c6025}#update-result:empty{display:none}@media(max-width:600px){.summary-heading{align-items:flex-start}.summary-dates span{display:block;margin-top:5px}}"""


def page(sport, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Pops’ Edge · '+sport.upper()+' Performance</title><style>'+BRAND_CSS+CSS+NAV_CSS+'</style></head><body><main>'
        '<header class="brand-header">'+BRAND_MARK+'<h1>Pops’ Edge</h1></header>'+navigation(sport,'performance')+body+'</main></body></html>').encode()


class NFLReader:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.cache = ReaderCache(self.root)
        self._engine = None

    def catalog(self):
        folder = safe_path(self.root,'reports')
        reports = []
        for path in sorted(folder.glob('*.json')):
            safe_path(self.root,str(path.relative_to(self.root)))
            value = json.loads(path.read_bytes())
            identity = value.get('report_id')
            if not re.fullmatch(HEX, str(identity)) or path.stem != identity:
                raise ValueError('Saved report identity is invalid; inspect the report store')
            if base.digest(base.encode({k:v for k,v in value.items() if k!='report_id'})) != identity:
                raise ValueError('Saved report digest is invalid; inspect the report store')
            if type(value.get('season')) is not int or type(value.get('week')) is not int:
                raise ValueError('Saved report season/week is invalid')
            instant(value['boundary'])
            reports.append(value)
        return reports

    def selected(self, season, week):
        reports = [r for r in self.catalog() if (r['season'],r['week']) == (season,week)]
        if not reports:
            return None
        boundary = max(instant(r['boundary']) for r in reports)
        latest = [r for r in reports if instant(r['boundary']) == boundary]
        if len(latest) != 1:
            raise ValueError('Conflicting saved reports at the latest analysis time; no report was selected')
        # Replay may read any archived event/blob. Disallow aliases throughout this bounded store.
        for p in self.root.rglob('*'):
            if p.is_symlink():
                raise ValueError('Aliased performance evidence is not allowed')
        if self._engine is not None:
            return self.cache.report(latest[0])
        engine = Performance(safe_path(self.root))
        r = engine.replay_report(self.root/'reports'/(latest[0]['report_id']+'.json'))
        return r

    def game_dates(self, report):
        """Display-only dates from the exact replay-validated report prefix."""
        engine=self._engine or Performance(safe_path(self.root));events=engine.events()
        tip=report['source_boundary']
        if tip:
            indexes=[i for i,e in enumerate(events) if e['id']==tip]
            if len(indexes)!=1:raise ValueError('Missing report source boundary')
            events=events[:indexes[0]+1]
        else:events=[]
        dates={};identities={};conflicts=set();at=instant(report['boundary'])
        def observe(rows):
            for g in rows:
                key=g['game_id'];identity=(g['home'],g['away'])
                if key in identities and identities[key]!=identity:conflicts.add(key)
                identities[key]=identity;dates[key]=g.get('kickoff')
        if (report['season'],report['week'])==(2026,1):
            cohort=engine.validate_starting_cohort()
            if cohort and instant(engine.activation['effective_at'])<=at:observe(cohort['receipt']['rows'])
        for e in events:
            p=e['payload']
            if e['kind']=='schedule' and instant(e['at'])<=at and (p.get('season'),p.get('week'))==(report['season'],report['week']):
                from nfl_performance_sources import LEGACY_OUTCOME_RULE
                decoded=engine.decode(e,outcome_rule=report.get('outcome_rule',LEGACY_OUTCOME_RULE))
                if not decoded.get('error'):observe(decoded['rows'])
        return {g['game_id']:dates.get(g['game_id']) if g['game_id'] not in conflicts and identities.get(g['game_id'])==(g['home'],g['away']) else None for g in report['games']}

    def render(self, query):
        with self.cache.lock:
            try:
                self._engine = self.cache.prepare()
                result = self._render(query)
                self.cache.verify()
                return result
            except READER_ERRORS as exc:
                self.cache.clear()
                return page('nfl','<section class="panel"><h2>NFL weekly performance unavailable</h2><p class="notice">'+text(exc)+'</p></section>')
            finally:
                self._engine = None

    def _render(self, query):
        try:
            if set(query)-{'season','week','period','from','to','team'} or any(len(v)!=1 for v in query.values()):
                raise ValueError('Select one season and one week')
            reports = self.catalog()
            if not reports:
                return page('nfl','<section class="panel"><h2>NFL weekly performance</h2><p>No saved weekly reports available.</p><p>Use the existing NFL Import &amp; Refresh workflow to update enrolled weeks. Opening this page does not create or update reports.</p></section>')
            seasons = sorted({r['season'] for r in reports})
            season = int(query.get('season',[str(max(seasons))])[0])
            weeks = sorted({r['week'] for r in reports if r['season']==season})
            if not weeks:
                raise ValueError('No saved reports for this season')
            week = query.get('week',['all'])[0]
            if week!='all' and int(week) not in weeks:raise ValueError('No saved report for this week')
            selected=[self.selected(season,w) for w in weeks if week=='all' or w==int(week)]
            # Kickoff is a display projection, not a change to saved report bytes.
            projected=[]
            for r in selected:
                dates=self.game_dates(r)
                projected.append(dict(r,games=[dict(g,kickoff=dates.get(g['game_id'])) for g in r['games']]))
            selected=projected
            games=[g for report in selected for g in report['games']]
            cutoff=max(instant(report['boundary']) for report in selected)
            q=dict(query)
            if q.get('period')==['custom']:
                days=[instant(g['kickoff']).astimezone(CENTRAL).date() for g in games if g.get('kickoff')]
                q.setdefault('from',[min(days+[cutoff.astimezone(CENTRAL).date()]).isoformat()])
                q.setdefault('to',[cutoff.astimezone(CENTRAL).date().isoformat()])
            filters = '<form class="filters" method="get" action="/performance/nfl">'
            # Older explicit week/season links remain scoped, without extra main controls.
            for key in ('season','week'):
                if key in q:filters+='<input type="hidden" name="'+key+'" value="'+text(q[key][0])+'">'
            period=q.get('period',['season'])[0]
            filters+='<label>Period <select name="period" onchange="this.form.submit()">'+''.join('<option value="'+v+'"'+(' selected' if period==v else '')+'>'+label+'</option>' for v,label in NFL_PERIODS)+'</select></label>'
            for key,label in [('from','From'),('to','To')]:
                if period=='custom':
                    filters+='<label>'+label+' <input type="date" name="'+key+'" value="'+text(q.get(key,[''])[0])+'" max="'+cutoff.astimezone(CENTRAL).date().isoformat()+'" required></label>'
                elif key in q:filters+='<input type="hidden" name="'+key+'" value="'+text(q[key][0])+'">'
            team=q.get('team',[''])[0]
            filters+='<label>Team <select name="team"><option value="">All teams</option>'+''.join('<option value="'+text(t)+'"'+(' selected' if team==t else '')+'>'+text(t)+'</option>' for t in sorted({g[k] for g in games for k in ('home','away')}))+'</select></label><button>View matches</button></form>'
            body=self._cumulative(selected, games)+'<section class="panel"><h2>Match results</h2>'+filters
            body+='<p class="muted">Preset periods end '+text(cutoff.astimezone(CENTRAL).date().isoformat())+'. Filters apply to match rows; the summary remains cumulative.</p>'
            try:shown=nfl_filtered(games,q,cutoff)
            except ValueError as exc:return page('nfl',body+'<p class="notice" role="alert">'+text(exc)+'</p></section>')
            body+='<p>'+str(len(shown))+' of '+str(len(games))+' saved games shown.</p>'
            owners={g['game_id']:r for r in selected for g in r['games']}
            shown=sorted(shown,key=lambda g:(g.get('kickoff') is None,instant(g['kickoff']).timestamp() if g.get('kickoff') else 0,g['game_id']))
            body+='<div class="table-wrap"><table aria-label="Match results"><thead><tr><th>Match / result</th><th>ELWAY value</th><th>Kalshi value</th><th>ELWAY score</th><th>Kalshi score</th><th>Details</th></tr></thead><tbody>'
            for g in shown:body+=self._match_row(owners[g['game_id']],g)
            if not shown:body+='<tr><td colspan="6">No matches in this saved report match your filters.</td></tr>'
            body+='</tbody></table></div></section><section class="panel"><details><summary>Report details and evidence</summary><p>Each game contributes once. Payout-adjusted Brier score means squared contract-value error against payout 1, 0 or 0.5 for a tie; it is not standard binary/multiclass Brier scoring, profit or proof of an edge. Both sources and the reference use the same paired scored games. Missing and excluded games are not scored. Unknown kickoff games appear only in This Season. This Season includes saved games not yet due; it does not imply complete season coverage.</p>'
            for r in selected:body+=self._weekly_evidence(r)
            body+='</details></section>'
            return page('nfl',body)
        except READER_ERRORS as exc:
            return page('nfl','<section class="panel"><h2>NFL weekly performance unavailable</h2><p class="notice">'+text(exc)+'</p><p>No substitute report was selected. Inspect the saved report or use the existing manual workflow; this page does not repair or update evidence.</p></section>')

    def _cumulative(self, reports, games):
        if len({g['game_id'] for g in games})!=len(games):
            raise ValueError('Duplicate game identity across saved weeks; cumulative results unavailable')
        scored=[g for g in games if g['state']=='scored']
        if len(scored)!=sum(r['paired_games'] for r in reports):raise ValueError('Scored population does not reconcile')
        with localcontext() as context:
            context.prec=50
            means={k:sum(Decimal(g['scores'][k]) for g in scored)/len(scored) if scored else None for k in ('elway_error','kalshi_error')}
            reference=sum((Decimal('0.5')-Decimal(g['outcome']['payout']))**2 for g in scored)/len(scored) if scored else None
            gains={k:reference-v if v is not None else None for k,v in means.items()}
        boundaries=sorted({r['boundary'] for r in reports},key=instant)
        enrolled=sum(r['starting_cohort']['eligible_population'] if r.get('starting_cohort') else r['population'] for r in reports)
        body='<section class="panel"><h2>NFL Performance</h2><p class="muted">Cumulative · Season '+str(reports[0]['season'])+' · Saved weeks '+', '.join(str(r['week']) for r in reports)+' · Saved analyses '+text(date(boundaries[0]))+(' through '+text(date(boundaries[-1])) if len(boundaries)>1 else '')+'</p>'
        body+='<p>'+str(len(scored))+' of '+str(enrolled)+' enrolled games scored'+(' — Limited coverage' if len(scored)<enrolled else '')+'</p>'
        for r in reports:
            if r.get('selection_issue'):body+='<p class="notice">Week '+str(r['week'])+': '+text(r['selection_issue'])+'</p>'
            if r.get('diagnostics'):body+='<p class="notice">Week '+str(r['week'])+' has recorded attempt issues; see report details.</p>'
        if not scored:body+='<p class="notice">No scored comparison available. Missing inputs and unresolved outcomes remain visible.</p>'
        body+='<div class="table-wrap"><table aria-label="Comparison with 50% reference"><thead><tr><th>Metric</th><th>ELWAY</th><th>Kalshi</th><th>50% reference</th></tr></thead><tbody><tr><th scope="row">Payout-adjusted Brier score</th>'
        body+=''.join('<td>'+number(v)+'</td>' for v in (means['elway_error'],means['kalshi_error'],reference))+'</tr><tr><th scope="row">Improvement over reference</th>'
        return body+''.join('<td>'+number(gains[k])+'</td>' for k in ('elway_error','kalshi_error'))+'<td>—</td></tr></tbody></table></div></section>'

    def _match_row(self,r,g):
        e,k,o,sc=g['elway'],g['kalshi'],g['outcome'],g['scores']
        result=(f"Final: {g['away']} {o['away_score']} – {g['home']} {o['home_score']}" if o and o['state']=='final' else '')
        body='<tr><td><strong>'+text(g['away']+' at '+g['home'])+'</strong><small>'+text(date(g.get('kickoff')))+'</small>'+('<small>'+text(result)+'</small>' if result else '')+'</td>'
        body+=''.join('<td>'+number(v,pct)+'</td>' for v,pct in [(e['central'] if e else None,True),(k['value'] if k else None,True),(sc['elway_error'] if sc else None,False),(sc['kalshi_error'] if sc else None,False)])
        label='File creation time — publication-time proxy' if (r['selected_forecast'] or {}).get('time_basis') else 'Forecast published'
        details=[('Week',str(r['week'])),('Saved analysis',date(r['boundary'])),('Evaluation status',LABELS.get(g['state'],g['state'].replace('-',' '))),('Result',result or 'Unresolved result'),(label,date((r['selected_forecast'] or {}).get('updated_at'))),('Forecast imported',date(r['selected_imported_at'])),('Outcome observed',date(o.get('observed_at')) if o else 'Unavailable')]
        if k:details.extend((key.replace('_',' ').capitalize(),date(value) if key in ('started_at','received_at') else str(value)) for key,value in k.items() if key in ('started_at','received_at','retry'))
        return body+'<td><details><summary>Details</summary><p>'+text('; '.join(g['issues']+(o.get('issues',[]) if o else [])) or 'No additional exclusions recorded.')+'</p><dl>'+''.join('<dt>'+text(a)+'</dt><dd>'+text(b)+'</dd>' for a,b in details)+'</dl></details></td></tr>'

    def _weekly_evidence(self,r):
        body='<h3>Week '+str(r['week'])+'</h3><p>Saved analysis: '+text(date(r['boundary']))+' · '+str(r['population'])+' official games · '+str(r['paired_games'])+' scored pairs</p>'
        body+='<p>'+('Baseline frozen' if r['frozen'] else 'Baseline not yet frozen')+' · Cutoff: '+text(date(r['cutoff']))+'</p>'
        if r.get('starting_cohort'):body+='<p>Partial Week 1 — 14 enrolled of 16 official games; the two starting-cohort exclusions remain outside scoring.</p>'
        body+='<p>'+text(' · '.join(str(v)+' '+LABELS.get(k,k) for k,v in r['coverage'].items()))+'</p>'
        if (r['selected_forecast'] or {}).get('time_basis'):body+='<p>File creation time — publication-time proxy. Publisher update time and model age are unknown.</p>'
        if r.get('matching_version'):body+='<p>Market matching correction: '+text(r['matching_version'])+' · Legacy interpretation ID: '+text(r['legacy_interpretation_id'])+'. No replacement observations acquired.</p>'
        body+='<p>Direct ELWAY improvement versus Kalshi: '+number(r['means']['difference'])+'. Positive means lower observed error, not proof of an edge.</p>'
        body+=''.join('<p>'+text(d['error'])+'</p>' for d in r['diagnostics'])
        return body+'<a download href="/performance/nfl/report/'+r['report_id']+'.json">Download exact weekly report</a>'

    def download(self, identity):
        with self.cache.lock:
            try:
                self.cache.prepare()
                r=next((r for r in self.catalog() if r['report_id']==identity),None)
                if not r:raise ValueError('Saved report unavailable')
                self.cache.report(r)
                raw=(self.cache.engine.root/'reports'/(identity+'.json')).read_bytes()
                self.cache.verify()
                return raw
            except Exception:
                self.cache.clear()
                raise


LABELS={'scored':'scored','excluded-starting-cohort':'outside starting cohort','unresolved-outcome':'unresolved result','missing-capture':'missing capture','candidate':'awaiting baseline freeze','awaiting-outcome':'awaiting result'}


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key=='href' and value:self.links.append(value)


class MLBReader:
    def __init__(self, root):
        self.root=Path(root).absolute()

    def assets(self):
        """Snapshot only the saved entry's reachable, explicitly permitted delivery assets."""
        from forecast_reporting_delivery import read_entry
        from forecast_reporting_activation import _retained
        entry=safe_path(self.root,'entry.html').read_bytes()
        state=read_entry(self.root)
        if state['live']:
            # Validate retained packages/receipts, not source acquisition or scientific scoring.
            for directory in ('packages','anchors','receipts','displays'):
                parent=safe_path(self.root,directory)
                for p in parent.rglob('*'):
                    if p.is_symlink():raise ValueError('Aliased MLB report evidence is not allowed')
            _retained(self.root,'live',state['live'])
        allowed=re.compile(r'(entry\.html|packages/'+HEX+r'/(analysis|projections|source|protocol|envelope|package)\.json|packages/'+HEX+r'/(report\.html|REPRODUCE\.txt)|(?:anchors|receipts)/[0-9a-f]{32}\.json|displays/[0-9a-f]{32}/(?:live\.html|historical\.html|recovery\.html|saved-state\.json|collection-status\.json|activation\.json|operator-guide\.md|collection-guide\.md|deployment-guide\.md))')
        assets={'entry.html':entry};pending=['entry.html']
        while pending:
            name=pending.pop()
            if not name.endswith('.html'):continue
            links=Links();links.feed(assets[name].decode())
            for href in links.links:
                url=urlsplit(href)
                if url.scheme or url.netloc or url.query:continue
                target=posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(url.path)))
                if not allowed.fullmatch(target) or target in assets:continue
                path=safe_path(self.root,target)
                if not path.is_file():continue  # Existing missing-link outcome remains visible on request.
                assets[target]=path.read_bytes();pending.append(target)
                if len(assets)>150:raise ValueError('Saved report link inventory exceeds expected bounds')
        for name,raw in assets.items():
            if name.endswith('/activation.json'):
                record=json.loads(raw)
                if record.get('active_entry_sha256')!=hashlib.sha256(entry).hexdigest():
                    raise ValueError('Saved display activation does not match the current entry')
        if safe_path(self.root,'entry.html').read_bytes()!=entry:
            raise ValueError('Saved MLB report changed while reading; reopen the page')
        return assets,state

    def render(self, query=None, *, updates=None, token=""):
        status=updates.status() if updates else None
        from mlb_performance_update_view import panel
        controls=panel(status,token) if status else ""
        try:
            assets,state=self.assets()
            from mlb_performance_view import render
            return render(self,assets,state,query or {},updates=updates,update_status=status,controls=controls)
        except READER_ERRORS as exc:
            return page('mlb','<section class="panel"><div class="summary-heading"><h2>MLB Performance Report unavailable</h2>'+controls+'</div><p class="notice">'+text(exc)+'</p><p>No report was generated or selected. Use Update Performance Report when configured, or inspect the saved output with the manual reporting workflow.</p></section>')

    def asset(self, name):
        assets,state=self.assets()
        if name not in assets:raise ValueError('Saved report asset unavailable')
        if name.endswith('/historical.html') or (state['historical'] and name.startswith('packages/'+state['historical']['package_id']+'/')):
            from forecast_reporting_activation import _retained
            _retained(self.root,'historical',state['historical'])
        return assets[name], 'text/html; charset=utf-8' if name.endswith('.html') else 'application/octet-stream'
