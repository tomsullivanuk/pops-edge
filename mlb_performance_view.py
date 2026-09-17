"""NFL-style presentation of retained MLB scientific results; no scoring or I/O writes."""
from datetime import datetime, timedelta, date as calendar_date
from decimal import Decimal, localcontext
from html import escape
import json
from urllib.parse import urlencode
from performance_reader import page, text, number, date as saved_date, CENTRAL, safe_path, READER_ERRORS
from forecast_reporting_activation import _retained
from forecast_reporting_delivery import _json
from forecast_standalone_operations import canonical_bytes, sha256_bytes
from mlb_performance_matches import validate

# Stable provider team IDs to readable labels; labels never establish game identity.
TEAM_NAMES = {'mlb-team:108': 'Los Angeles Angels', 'mlb-team:109': 'Arizona Diamondbacks', 'mlb-team:110': 'Baltimore Orioles', 'mlb-team:111': 'Boston Red Sox', 'mlb-team:112': 'Chicago Cubs', 'mlb-team:113': 'Cincinnati Reds', 'mlb-team:114': 'Cleveland Guardians', 'mlb-team:115': 'Colorado Rockies', 'mlb-team:116': 'Detroit Tigers', 'mlb-team:117': 'Houston Astros', 'mlb-team:118': 'Kansas City Royals', 'mlb-team:119': 'Los Angeles Dodgers', 'mlb-team:120': 'Washington Nationals', 'mlb-team:121': 'New York Mets', 'mlb-team:133': 'Athletics', 'mlb-team:134': 'Pittsburgh Pirates', 'mlb-team:135': 'San Diego Padres', 'mlb-team:136': 'Seattle Mariners', 'mlb-team:137': 'San Francisco Giants', 'mlb-team:138': 'St. Louis Cardinals', 'mlb-team:139': 'Tampa Bay Rays', 'mlb-team:140': 'Texas Rangers', 'mlb-team:141': 'Toronto Blue Jays', 'mlb-team:142': 'Minnesota Twins', 'mlb-team:143': 'Philadelphia Phillies', 'mlb-team:144': 'Atlanta Braves', 'mlb-team:145': 'Chicago White Sox', 'mlb-team:146': 'Miami Marlins', 'mlb-team:147': 'New York Yankees', 'mlb-team:158': 'Milwaukee Brewers'}
PERIODS = [('7','Last 7 Days'),('14','Last 14 Days'),('60','Last 60 Days'),('90','Last 90 Days'),('season','This Season'),('custom','Custom Period')]


def date(value):
    return saved_date(value.isoformat() if isinstance(value,datetime) else value)


def team_name(identity):
    return TEAM_NAMES.get(identity, 'MLB team '+identity.rsplit(':',1)[-1])


def filtered(rows, query, cutoff):
    if set(query) - {'period','from','to','team'} or any(len(v) != 1 for v in query.values()):
        raise ValueError('Choose one value for each match filter')
    period = query.get('period',['season'])[0];team = query.get('team',[''])[0]
    if period not in dict(PERIODS):
        raise ValueError('Choose a supported period')
    if team and team not in {r[k] for r in rows for k in ('home','away')}:
        raise ValueError('Choose a team from this report')
    end = cutoff.astimezone(CENTRAL).date();start = None
    if period == 'custom':
        try:
            start = calendar_date.fromisoformat(query.get('from',[''])[0])
            end = calendar_date.fromisoformat(query.get('to',[''])[0])
        except ValueError:
            raise ValueError('Choose both From and To dates') from None
        if start > end:
            raise ValueError('From must be on or before To')
        if end > cutoff.astimezone(CENTRAL).date():
            raise ValueError('To cannot be after the saved data date')
    elif period != 'season':
        start = end-timedelta(days=int(period)-1)
    selected=[]
    for row in rows:
        day=datetime.fromisoformat(row['start']).astimezone(CENTRAL).date()
        if (period=='season' or start<=day<=end) and (not team or team in (row['home'],row['away'])):
            selected.append(row)
    return selected


def controls(rows, query, cutoff, origin):
    one=lambda key,default: query.get(key,[default])[0]
    period=one('period','season');custom=period=='custom'
    end=cutoff.astimezone(CENTRAL).date().isoformat()
    body='<form class="filters" method="get" action="/performance/mlb"><label>Period <select name="period" onchange="this.form.submit()">'
    for value,label in PERIODS:
        body+='<option value="'+value+'"'+(' selected' if period==value else '')+'>'+label+'</option>'
    body+='</select></label>'
    if custom:
        for key,label,default in [('from','From',origin.astimezone(CENTRAL).date().isoformat()),('to','To',end)]:
            body+='<label>'+label+' <input type="date" name="'+key+'" value="'+text(one(key,default))+'" max="'+end+'" required></label>'
    else:
        # Preserve the last custom selection without making it affect presets.
        for key in ('from','to'):
            if key in query:body+='<input type="hidden" name="'+key+'" value="'+text(one(key,''))+'">'
    body+='<label>Team <select name="team"><option value="">All teams</option>'
    for identity in sorted({r[k] for r in rows for k in ('home','away')},key=team_name):
        body+='<option value="'+text(identity)+'"'+(' selected' if one('team','')==identity else '')+'>'+text(team_name(identity))+'</option>'
    body+='</select></label><button>View matches</button></form>'
    return body


def match_table(root, ref, analysis, projection, query, spec):
    body='<section class="panel"><h2>Match results</h2>'
    try:
        path=safe_path(root,'matches/'+ref['package_id']+'.json')
        if not path.is_file():
            return body+'<p class="notice">Match details have not been prepared for this saved report. The summary remains available.</p></section>'
        payload=_json(path.read_bytes());rows=validate(payload,ref['package_id'],analysis,projection)
    except READER_ERRORS as exc:
        return body+'<p class="notice">Saved match details unavailable: '+text(exc)+'</p></section>'
    # Initial selection of Custom Period defaults to this report’s period; an explicitly blank date remains invalid.
    q=dict(query)
    if q.get('period')==['custom']:
        q.setdefault('from',[spec.cumulative_scope.start.astimezone(CENTRAL).date().isoformat()])
        q.setdefault('to',[spec.evidence_cutoff_at.astimezone(CENTRAL).date().isoformat()])
    body+=controls(rows,q,spec.evidence_cutoff_at,spec.cumulative_scope.start)
    try:
        shown=filtered(rows,q,spec.evidence_cutoff_at)
    except ValueError as exc:
        return body+'<p class="notice" role="alert">'+text(exc)+'</p></section>'
    body+='<p class="muted">'+str(len(shown))+' of '+str(len(rows))+' opportunities shown · '+str(len({r['event_id'] for r in shown}))+' games</p>'
    body+='<p class="muted">Preset periods end '+text(spec.evidence_cutoff_at.astimezone(CENTRAL).strftime('%b %d, %Y'))+'. Filters apply to match rows; the summary remains cumulative.</p>'
    if not shown:
        return body+'<p>No matches in this saved report match your filters.</p></section>'
    body+='<div class="table-wrap"><table><thead><tr><th>Match</th><th>Kalshi home-win probability</th><th>Kalshi score</th><th></th></tr></thead><tbody>'
    for r in shown:
        away=team_name(r['away']);home=team_name(r['home'])
        body+='<tr><td><strong>'+text(away+' at '+home)+'</strong><small>'+text(date(r['start']))+'</small>'
        if r['score'] is not None:
            body+='<small>'+text(f"Final: {away} {r['away_score']} – {home} {r['home_score']}")+'</small>'
        body+='</td><td>'+number(r['probability'],True)+'</td><td>'+number(r['score'])+'</td><td><details><summary>Details</summary>'
        if sum(x['event_id']==r['event_id'] for x in rows)>1:
            body+='<p>The report retains separate scheduled opportunities for this game; each row preserves its original capture accounting.</p>'
        body+='<p>Evaluated contract: '+text(home)+' YES.</p><p>Saved evaluation: '+text(r['disposition'].replace('_',' '))+'.</p>'
        body+='<p>'+('Final outcome observed '+text(date(r['outcome_observed_at']))+'.' if r['outcome_id'] else 'No scored final outcome is attached to this opportunity in the saved report.')+'</p>'
        body+='</details></td></tr>'
    return body+'</tbody></table></div></section>'


def collection(assets):
    records=[]
    for name,raw in assets.items():
        if name.endswith('/activation.json'):
            record=_json(raw);status_name=name.removesuffix('activation.json')+'collection-status.json'
            if status_name in assets and sha256_bytes(assets[status_name])==record.get('collection_status_sha256'):
                records.append((status_name,_json(assets[status_name])))
    body='<section class="panel"><h2>Collection status</h2>'
    if len(records)!=1:
        return body+'<p class="notice">Saved collection status unavailable.</p></section>'
    name,status=records[0]
    body+='<p class="muted">Observed '+text(date(status['observed_at']))+' · Not rechecked</p>'
    blockers=status.get('current_blockers',[])
    body+='<p>'+('Recorded as incomplete' if blockers else 'No blockers in the saved observation' if status['availability']=='available' else 'Unavailable')+'</p>'
    body+='<details><summary>Collection details</summary>'
    if status.get('reason'):body+='<p>'+text(status['reason'])+'</p>'
    for blocker in blockers:body+='<p>'+text(blocker)+'</p>'
    body+='<p>Latest recorded completion: '+text(date(status.get('latest_record_at')))+'.</p>'
    body+='<p>'+str(len(status.get('recent_skips',[])))+' skipped cycles in the saved health window.</p>'
    body+='<p>These retained observations do not recheck collector health or change scientific completeness.</p>'
    return body+'<a download href="/performance/mlb/saved/'+text(name)+'">Download saved collection observation</a></details></section>'


def render(reader, assets, state, query):
    ref=state['live']
    if not ref:
        return page('mlb','<section class="panel"><h2>MLB Performance</h2><p>No saved live Performance Report is selected.</p></section>')
    report,projections,envelope,receipt_path,receipt=_retained(reader.root,'live',ref)
    spec=report.context.computation;projection=projections['scopes'][0];perf=report.performances[0]
    analysis=_json(assets['packages/'+ref['package_id']+'/analysis.json'])
    body='<section class="panel"><h2>MLB Performance</h2>'
    # Protocol calendar origin remains explicit; display timestamps elsewhere use Central.
    body+='<div class="filters"><strong>'+str(spec.cumulative_scope.start.year)+' regular season</strong><span>Cumulative · Since '+text(spec.cumulative_scope.start.strftime('%b %d, %Y'))+'</span></div>'
    body+='<p class="muted">Data through: '+text(date(spec.evidence_cutoff_at))+'</p>'
    if envelope['synthetic_validation']:body+='<p class="notice">Illustrative example — synthetic data.</p>'
    attempt=state.get('last_attempt')
    if attempt and attempt['status']=='failed':
        body+='<p class="notice">The last report attempt failed. The previously saved report remains selected; see Details.</p>'
    elif attempt and attempt['status']=='running':
        body+='<p class="notice">A report attempt was started; its completion is not recorded. The saved report remains selected.</p>'
    body+='<p class="counts">'+' &nbsp; '.join('<strong>'+str(len(projection[key]))+'</strong> '+label for key,label in [('eligible_ids','Eligible'),('captured_ids','Captured'),('scored_ids','Scored')])+'</p>'
    cats=projection['reconciliation'];count=lambda keys:sum(len(cats.get(k,[])) for k in keys)
    body+='<p class="muted">'+str(count(['missed_window','archive_unavailable','candle_unavailable']))+' missing captures · '+str(count(['acquisition_failed','captured_invalid','timing_invalid','archive_invalid','candle_invalid','derivation_unavailable']))+' unusable or failed · '+str(count(['outcome_unresolved']))+' awaiting result</p>'
    if report.coverages[0].unknown_calendar_dates:body+='<p class="notice">Calendar coverage is unverified for '+str(len(report.coverages[0].unknown_calendar_dates))+' dates; missing-game counts are unknown.</p>'
    reference=projection['reference']['mean_brier_score'];gain=None
    if reference is not None and perf.mean_brier_score is not None:
        with localcontext() as ctx:
            ctx.prec=50;gain=Decimal(reference)-perf.mean_brier_score
    body+='<div class="table-wrap"><table aria-label="Comparison with 50% reference"><thead><tr><th>Metric</th><th>Kalshi</th><th>50% reference</th></tr></thead><tbody>'
    for label,left,right in [('Average Brier score',number(perf.mean_brier_score),number(reference)),('Improvement over reference',number(gain),'—')]:
        body+='<tr><th scope="row">'+label+'</th><td>'+left+'</td><td>'+right+'</td></tr>'
    body+='</tbody></table></div><p>95% sampling interval: <strong>'+number(perf.uncertainty.lower)+'–'+number(perf.uncertainty.upper)+'</strong> · '+str(perf.sample_size)+' scored games</p>'
    if perf.sample_size==0:body+='<p>No scored results are available.</p>'
    elif perf.sample_size==1:body+='<p class="notice">Only one scored observation; the interval does not establish stable performance.</p>'
    elif number(perf.uncertainty.lower)==number(perf.uncertainty.upper):body+='<p>The displayed interval endpoints coincide; this does not establish certainty.</p>'
    body+='</section>'+match_table(reader.root,ref,analysis,projection,query,spec)+collection(assets)
    body+='<section class="panel"><details><summary>Report details and evidence</summary><p>Study status: '+text(report.context.report_status)+'.</p><p>Limited capture coverage; the sampling interval does not account for missing-capture bias.</p>'
    body+='<p>Brier score evaluates the saved home-win probability against the game outcome. Lower scores are better. Improvement over reference is reference score minus Kalshi score, using full precision before display rounding. The same scored opportunities govern both columns. Rounded ties do not imply exact equivalence.</p><p>The 50% reference was adopted '+text(projection['reference']['adopted_on'])+' after study commencement. These descriptive results grant no wagering or policy authority.</p>'
    body+='<p>Preset periods include the saved Central data date and the preceding calendar days. Custom Period includes both From and To dates. This Season includes all known opportunities in the report, including those not yet due. Filters affect rows only, not scientific populations or summary metrics.</p>'
    body+='<p>Report generated: '+text(date(report.context.report_generated_at))+'. Original verification: '+text(date(receipt['verified_at']))+'.</p>'
    body+='<p>Unmeasured rows do not infer current game results. Missing match-display material is independent of scientific report completeness. Opening this page performs no updates.</p>'
    if attempt:
        body+='<p>Last report attempt: '+text(attempt['status'])+'. '+text(date(attempt.get('completed_at') or attempt.get('started_at')))+'.</p>'
        if attempt.get('error'):body+='<p>'+text(attempt['error'])+'</p>'
    body+='<h3>Coverage</h3><table><thead><tr><th>Category</th><th>Opportunities</th></tr></thead><tbody>'
    for k,v in cats.items():body+='<tr><td>'+text(k.replace('_',' ').capitalize())+'</td><td>'+str(len(v))+'</td></tr>'
    body+='</tbody></table><p><a href="/performance/mlb/saved/entry.html">Open original saved report: calibration, log loss, bounded results and full evidence</a></p>'
    prefix='/performance/mlb/saved/packages/'+ref['package_id']+'/'
    body+='<p>'+' · '.join('<a download href="'+prefix+name+'">'+label+'</a>' for name,label in [('analysis.json','Download exact analysis'),('projections.json','Download projections'),('source.json','Download source boundary'),('protocol.json','Download Protocol'),('envelope.json','Download provenance')])+'</p></details></section>'
    # Preserve the exact historical saved destination, including its interim status on that page.
    from performance_reader import Links
    links=Links();links.feed(assets['entry.html'].decode())
    historical=next((x for x in links.links if x.endswith('/historical.html')),None)
    if historical:body+='<p><a href="/performance/mlb/saved/'+text(historical)+'">Historical candle report</a></p>'
    elif state.get('historical'):body+='<p><a href="/performance/mlb/saved/packages/'+text(state['historical']['package_id'])+'/report.html">Historical candle report</a></p>'
    else:body+='<p>Historical candle report unavailable.</p>'
    body+='<style>input[type=date]{font:inherit;padding:6px 10px;border:1px solid #c9d5e2;border-radius:6px;color:#18304a}.counts{font-size:18px}td details p{min-width:170px;font-size:13px}</style>'
    return page('mlb',body)
