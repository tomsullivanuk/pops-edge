"""Read-only presentation adapters; never capture, publish, initialize or select reports."""
from decimal import Decimal, localcontext
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zoneinfo import ZoneInfo
import hashlib
import json
import posixpath
import re

import nfl_forecast_import as base
from nfl_performance import Performance, instant
from nfl_brand import BRAND_CSS, BRAND_MARK
from forecast_standalone_operations import OperationsError

READER_ERRORS = (ValueError, OSError, KeyError, TypeError, OperationsError)

CENTRAL = ZoneInfo('America/Chicago')
HEX = r'[0-9a-f]{64}'
DEFAULT_MLB = Path.home()/'PopsEdgeReports/mlb/real/2026-09-13-accepted/reports'


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
    return ('<nav class="product-nav" aria-label="Area">'+link(bet,'Bet Sheet',area=='bet')+
        link('/performance/'+sport,'Performance',area=='performance')+'</nav>'+
        '<nav class="product-nav sports" aria-label="Sport">'+
        link('/performance/nfl' if area=='performance' else '/', 'NFL',sport=='nfl')+
        link('/performance/mlb' if area=='performance' else '/mlb','MLB',sport=='mlb')+'</nav>')


NAV_CSS = '.product-nav{display:flex;gap:8px;margin:12px 0}.product-nav a{display:inline-block;padding:10px 18px;border:1px solid #d7dfe7;border-radius:7px;background:white;color:#17314c;text-decoration:none;font-weight:600}.product-nav a[aria-current=page]{background:#102b49;color:white}.product-nav.sports{margin-bottom:24px}.product-nav a:focus-visible{outline:3px solid #16834c;outline-offset:2px}'
CSS = '''*{box-sizing:border-box}body{margin:28px;background:#f5f7fa;color:#18304a;font:15px/1.5 system-ui}main{max-width:1250px;margin:auto}h1{margin:0}h2{margin:0 0 10px}p{margin:8px 0}.panel{background:white;border:1px solid #dbe2e9;border-radius:12px;padding:24px;margin:18px 0}.filters{display:flex;align-items:center;gap:18px;flex-wrap:wrap;background:#f3f6fa;border:1px solid #dce4ed;border-radius:10px;padding:16px}select,button{font:inherit;background:white;border:1px solid #c9d5e2;border-radius:6px;padding:6px 12px;color:#18304a}.metrics{display:flex;gap:18px;flex-wrap:wrap;margin:18px 0}.metric{flex:1;min-width:170px;padding:18px;background:#f2f6fa;border-radius:8px}.metric b{font-size:28px;display:block}.muted{color:#60738a}.notice{padding:14px;background:#fff6e5;border-left:4px solid #b88322}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:white}th{background:#102b49;color:white;text-align:left}td,th{padding:14px;border-bottom:1px solid #e1e7ed;vertical-align:top}td small{display:block;color:#60738a}table[aria-label="Comparison with 50% reference"] tbody th{background:#eaf0f6;color:#20334a;font-weight:600}summary{cursor:pointer;font-weight:600}details p{max-width:650px}a{color:#195c89}iframe{width:100%;height:80vh;border:1px solid #dbe2e9;border-radius:10px;background:white}dl{display:grid;grid-template-columns:minmax(100px,200px) 1fr;gap:8px}dd{margin:0;overflow-wrap:anywhere}.error{color:#8d3c21}@media(max-width:650px){body{margin:12px}.panel{padding:16px}.metric{min-width:120px}td,th{padding:10px}}'''


def page(sport, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Pops’ Edge · '+sport.upper()+' Performance</title><style>'+BRAND_CSS+CSS+NAV_CSS+'</style></head><body><main>'
        '<header class="brand-header">'+BRAND_MARK+'<h1>Pops’ Edge</h1></header>'+navigation(sport,'performance')+body+'</main></body></html>').encode()


class NFLReader:
    def __init__(self, root):
        self.root = Path(root).absolute()

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
        engine = Performance(safe_path(self.root))
        r = engine.replay_report(self.root/'reports'/(latest[0]['report_id']+'.json'))
        return r

    def render(self, query):
        try:
            if set(query)-{'season','week'} or any(len(v)!=1 for v in query.values()):
                raise ValueError('Select one season and one week')
            reports = self.catalog()
            if not reports:
                return page('nfl','<section class="panel"><h2>NFL weekly performance</h2><p>No saved weekly reports available.</p><p>Use the existing NFL Import &amp; Refresh workflow to update enrolled weeks. Opening this page does not create or update reports.</p></section>')
            seasons = sorted({r['season'] for r in reports})
            season = int(query.get('season',[str(max(seasons))])[0])
            weeks = sorted({r['week'] for r in reports if r['season']==season})
            if not weeks:
                raise ValueError('No saved reports for this season')
            week = int(query.get('week',[str(max(weeks))])[0])
            r = self.selected(season,week)
            if r is None:
                raise ValueError('No saved report for this week')
            options = lambda values, selected: ''.join(f'<option value="{v}"'+(' selected' if v==selected else '')+f'>{v}</option>' for v in values)
            # Changing season clears the old week; week selection is an explicit GET.
            filters = ('<form class="filters" method="get"><label>Season <select name="season" aria-label="Season" onchange="location.href=\'/performance/nfl?season=\'+this.value">'+options(seasons,season)+
                '</select></label><label>Week <select name="week" aria-label="Week">'+options(weeks,week)+'</select></label><button>View week</button></form>')
            cohort=r.get('starting_cohort')
            coverage = ' · '.join(f'{count} {LABELS.get(state,state.replace("-"," "))}' for state,count in r['coverage'].items())
            body='<section class="panel"><h2>NFL weekly performance</h2>'+filters
            report_details='<p class="muted">Saved analysis: '+text(date(r['boundary']))+'. Opening this page does not update results.</p>'
            report_details+='<p>'+('Baseline frozen' if r['frozen'] else 'Baseline not yet frozen')+' · Cutoff: '+text(date(r['cutoff']))+'</p>'
            if cohort:
                report_details+='<p class="notice">Partial Week 1 — '+str(cohort['eligible_population'])+' enrolled of '+str(cohort['official_population'])+' official games. The two starting-cohort exclusions remain outside scoring.</p>'
            report_details+='<p>'+str(r['population'])+' official games · '+str(r['paired_games'])+' scored pairs</p><p>'+text(coverage)+'</p>'
            enrolled=cohort['eligible_population'] if cohort else r['population']
            body+='<p class="muted">Results as of: '+text(date(r['boundary']))+'</p>'
            body+='<p>'+str(r['paired_games'])+' of '+str(enrolled)+' enrolled games scored</p>'
            if r['selection_issue']:
                body+='<p class="notice">'+text(r['selection_issue'])+'</p>'
            if not r['paired_games']:
                body+='<p class="notice">No scored comparison available for this week. Missing inputs and unresolved outcomes are shown below.</p>'
            report_details+='<h3>Payout-adjusted Brier score</h3><p>Lower is better. Both sources use the same scored games, without fees. Values in the table refer to the home-team contract.</p>'
            reference, elway_gain, kalshi_gain = reference_comparison(r)
            body+='<div class="table-wrap"><table aria-label="Comparison with 50% reference"><thead><tr><th>Metric</th><th>ELWAY</th><th>Kalshi</th><th>50% reference</th></tr></thead><tbody>'
            body+='<tr><th scope="row">Payout-adjusted Brier score</th><td>'+number(r['means']['elway_error'])+'</td><td>'+number(r['means']['kalshi_error'])+'</td><td>'+number(reference)+'</td></tr>'
            body+='<tr><th scope="row">Improvement over reference</th><td>'+number(elway_gain)+'</td><td>'+number(kalshi_gain)+'</td><td>—</td></tr></tbody></table></div></section>'
            report_details+='<p>The 50% reference assigns a fixed home-team contract value of 0.50 to the same scored games. Its error is 0.25 for a home or away win and 0.00 for a tie. The average is calculated from the actual scored outcomes. This descriptive reference was adopted September 15, 2026, after the weekly study began; it does not change the saved measurement or population.</p>'
            report_details+='<p>Improvement over reference is reference error minus source error. Positive means lower error than the reference; negative means higher error.</p>'
            report_details+='<p>Direct ELWAY improvement versus Kalshi: '+number(r['means']['difference'])+'. This is Kalshi error minus ELWAY error. Positive means lower observed ELWAY error; negative means lower Kalshi error. Rounded values may appear equal. These are descriptive comparisons, not profit or proof of an edge.</p>'
            body+='<div class="table-wrap"><table><thead><tr><th>Match / result</th><th>ELWAY value</th><th>Kalshi value</th><th>ELWAY score</th><th>Kalshi score</th><th>Details</th></tr></thead><tbody>'
            for g in r['games']:
                e,k,o,sc=g['elway'],g['kalshi'],g['outcome'],g['scores']
                result=(f"Final: {g['away']} {o['away_score']} – {g['home']} {o['home_score']}" if o and o['state']=='final' else '')
                body+='<tr><td><strong>'+text(g['away']+' at '+g['home'])+'</strong>'+('<small>'+text(result)+'</small>' if result else '')+'</td>'
                body+=''.join('<td>'+number(v,pct)+'</td>' for v,pct in [(e['central'] if e else None,True),(k['value'] if k else None,True),(sc['elway_error'] if sc else None,False),(sc['kalshi_error'] if sc else None,False)])
                details=[('Evaluation status',LABELS.get(g['state'],g['state'].replace('-',' '))),('Result',result or 'Unresolved result'),('Forecast published',date((r['selected_forecast'] or {}).get('updated_at'))),('Forecast imported',date(r['selected_imported_at'])),('Outcome observed',date(o.get('observed_at')) if o else 'Unavailable')]
                if k:
                    details.extend((key.replace('_',' ').capitalize(),date(value) if key in ('started_at','received_at') else str(value)) for key,value in k.items() if key in ('started_at','received_at','retry'))
                body+='<td><details><summary>Details</summary><p>'+text('; '.join(g['issues']+(o.get('issues',[]) if o else [])) or 'No additional exclusions recorded.')+'</p><dl>'+''.join('<dt>'+text(a)+'</dt><dd>'+text(b)+'</dd>' for a,b in details)+'</dl></details></td></tr>'
            body+='</tbody></table></div>'
            if r['diagnostics']:
                body+='<section class="panel"><h3>Recorded attempt issues</h3>'+''.join('<p>'+text(d['error'])+'</p>' for d in r['diagnostics'])+'</section>'
            body+='<section class="panel"><details><summary>Report details and evidence</summary>'+report_details+'<p>Payout-adjusted Brier score is the product label for squared contract-value error: squared error against the final contract payout, 1 for a home win, 0 for an away win, and 0.5 for a tie. Each game contributes once through its home-team equivalent value. The summary shows the mean across scored games. This descriptive label is not standard binary or multiclass Brier scoring.</p><p>Original source values, times, retries, diagnostics and identities are retained in the exact report download.</p><p>Selected forecast publication: '+text(date((r['selected_forecast'] or {}).get('updated_at')))+'.</p><a download href="/performance/nfl/report/'+r['report_id']+'.json">Download exact weekly report</a></details></section>'
            return page('nfl',body)
        except READER_ERRORS as exc:
            return page('nfl','<section class="panel"><h2>NFL weekly performance unavailable</h2><p class="notice">'+text(exc)+'</p><p>No substitute report was selected. Inspect the saved report or use the existing manual workflow; this page does not repair or update evidence.</p></section>')

    def download(self, identity):
        reports=self.catalog()
        r=next((r for r in reports if r['report_id']==identity),None)
        if not r:raise ValueError('Saved report unavailable')
        for p in self.root.rglob('*'):
            if p.is_symlink():raise ValueError('Aliased performance evidence is not allowed')
        path=safe_path(self.root,'reports/'+identity+'.json')
        Performance(safe_path(self.root)).replay_report(path)
        return path.read_bytes()


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

    def render(self, query=None):
        try:
            assets,state=self.assets()
            from mlb_performance_view import render
            return render(self,assets,state,query or {})
        except READER_ERRORS as exc:
            return page('mlb','<section class="panel"><h2>MLB Performance Report unavailable</h2><p class="notice">'+text(exc)+'</p><p>No report was generated or selected. Use the existing manual reporting workflow to inspect the saved output.</p></section>')

    def asset(self, name):
        assets,state=self.assets()
        if name not in assets:raise ValueError('Saved report asset unavailable')
        if name.endswith('/historical.html') or (state['historical'] and name.startswith('packages/'+state['historical']['package_id']+'/')):
            from forecast_reporting_activation import _retained
            _retained(self.root,'historical',state['historical'])
        return assets[name], 'text/html; charset=utf-8' if name.endswith('.html') else 'application/octet-stream'
