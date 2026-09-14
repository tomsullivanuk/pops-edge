"""Display-only simple MLB report. Canonical scientific payloads stay unchanged."""
import html
from datetime import datetime, date, timedelta
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from zoneinfo import ZoneInfo

VERSION = 'mlb-reporting-html-3'


def text(value):
    return html.escape(str(value))


def rounded(value, places=2, percent=False):
    places = min(2, max(0, places))
    if value is None:
        return 'Unavailable'
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        number=Decimal(value)
        if number.is_infinite():
            return 'Infinite'
        if percent:
            number*=100
        return format(number,f'.{places}f')+('%' if percent else '')


def friendly(value):
    if isinstance(value,str):
        value=datetime.fromisoformat(value)
    local=value.astimezone(ZoneInfo('America/New_York'))
    return f'{local.strftime("%b")} {local.day}, {local.year} at {local.strftime("%I:%M %p").lstrip("0")} {local.tzname()}'


def day(value):
    local=value.astimezone(ZoneInfo('America/New_York'))
    return f'{local.strftime("%b")} {local.day}, {local.year}'


def page(title, body):
    return ('''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>'''+text(title)+'''</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;color:#21382f;background:#f6f7f4;font:17px/1.55 system-ui,sans-serif}
main{max-width:940px;margin:0 auto;padding:40px 24px 60px}h1{font-size:2.2rem;letter-spacing:-.04em;margin:8px 0 12px}h2{font-size:1.3rem;margin:0 0 12px}h3{font-size:1.1rem}p{margin:10px 0}.eyebrow{font-size:.8rem;text-transform:uppercase;letter-spacing:.12em;color:#586d61}.muted{color:#52645b;font-size:.93rem}.section{background:white;border:1px solid #dce2dc;border-radius:14px;padding:24px;margin:20px 0}.notice{background:#fff4dc;border-left:4px solid #a77421;padding:14px 18px;margin:18px 0}.counts{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.count{font-size:2rem;font-weight:650;display:block}a{color:#1b654c;text-underline-offset:3px}summary{cursor:pointer;font-weight:650;padding:14px 0}summary:focus-visible,a:focus-visible{outline:3px solid #ba7811;outline-offset:3px}details{margin-top:22px;border-top:1px solid #c5d0c7}details details{margin:12px 0}table{border-collapse:collapse;width:100%;margin:14px 0}caption{text-align:left;font-weight:650;margin:8px 0}td,th{padding:10px;border-bottom:1px solid #dce2dc;text-align:left;overflow-wrap:anywhere}th{font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.82rem}td:first-child{width:45%}.score{font-size:1.6rem;font-weight:650}.technical h1{font-size:1.4rem}.technical{font-size:.94rem}.technical table{table-layout:fixed}.technical td{border:1px solid #dce2dc}nav{margin-bottom:16px}@media(max-width:560px){main{padding:24px 16px}.section{padding:18px}.counts{gap:8px}.count{font-size:1.7rem}h1{font-size:1.9rem}}
</style></head><body><main><p class="eyebrow">Pops’ Edge · MLB</p><h1>'''+text(title)+'</h1>'+body+'</main></body></html>').encode()


def summary(report, projections, synthetic, collection_status=None):
    context=report.context;spec=context.computation
    coverage=report.coverages[0];performance=report.performances[0];projection=projections['scopes'][0]
    historical=spec.design_tag.value=='retrospective'
    period=(day(spec.cumulative_scope.start)+' – '+day(spec.cumulative_scope.end)+' (starts before September 5)'
            if historical else day(spec.cumulative_scope.start)+' onward')
    body='<p>'+text(period)+' · '+(('Interim historical study' if context.report_status == 'interim' else 'Historical study in progress') if historical else 'Study in progress')+'</p>'
    body+='<p class="muted">Generated '+text(friendly(context.report_generated_at))+'. Data available through '+text(friendly(spec.evidence_cutoff_at))+'.</p>'
    if synthetic:
        body+='<p class="notice"><strong>Illustrative example — synthetic data.</strong> These are not results from the acquired MLB archive.</p>'
    else:
        body+='<p class="muted">Source: retained acquired MLB archive. No new data was collected to make this report.</p>'
    body+='<p>This study is incomplete. These results describe the available observations, not final findings.</p>'
    eligible=len(projection['eligible_ids']);captured=len(projection['captured_ids']);scored=len(projection['scored_ids'])
    body+='<section class="section"><h2>Games in this report</h2><div class="counts">'
    for label,value in (('Eligible',eligible),('Captured',captured),('Scored',scored)):
        body+='<div><span class="count">'+str(value)+'</span>'+label+'</div>'
    body+='</div><p class="muted">Counts refer to scheduled game opportunities. Eligible means the capture was due; scored also requires a valid probability and a resolved result.</p>'
    body+='<p>'+str(scored)+' of '+str(eligible)+' eligible opportunities scored ('+rounded(coverage.coverage_rate,1,True)+').</p>'
    categories=projection['reconciliation']
    gaps=[]
    awaiting=len(categories.get('outcome_unresolved',()))
    missed=sum(len(categories.get(k,())) for k in ('missed_window','archive_unavailable','candle_unavailable'))
    failed=sum(len(categories.get(k,())) for k in ('acquisition_failed','captured_invalid','timing_invalid','archive_invalid','candle_invalid','derivation_unavailable'))
    future=len(categories.get('capture_not_yet_due',()))
    excluded=len(categories.get('protocol_ineligible',()))
    for n,label in ((missed,'missing captures'),(failed,'unusable or failed observations'),(awaiting,'awaiting a usable game result'),(future,'not yet due for capture'),(excluded,'outside study eligibility')):
        if n:gaps.append(f'{label.capitalize()}: {n}')
    if gaps:body+='<p><strong>Gaps:</strong> '+text('; '.join(gaps))+'.</p>'
    body+='</section><section class="section"><h2>Prediction error</h2><p>Lower Brier score is better; 0 means no error. This is not a percentage accuracy.</p>'
    body+='<table><caption>Same '+str(scored)+' scored '+('opportunity' if scored == 1 else 'opportunities')+'</caption><thead><tr><th scope="col">Prediction</th><th scope="col">Mean Brier error</th></tr></thead><tbody>'
    for label,value in (('Kalshi',performance.mean_brier_score),('50% home-win reference',projection['reference']['mean_brier_score'])):
        body+='<tr><td>'+label+'</td><td class="score">'+rounded(value)+'</td></tr>'
    body+='</tbody></table>'
    if not scored:
        body+='<p>No scored results are available. A comparison cannot yet be made.</p>'
    else:
        baseline=Decimal(projection['reference']['mean_brier_score']);score=performance.mean_brier_score
        if rounded(score)==rounded(baseline):
            body+='<p>The displayed scores are tied at two decimals. Rounding can hide a smaller difference; this is not evidence of equivalent performance.</p>'
        else:
            comparison='lower than' if score<baseline else 'higher than'
            body+='<p>Observed Kalshi error is '+comparison+' the 50% reference on this sample. This does not establish a reliable advantage.</p>'
    body+='<p class="muted">The reference assumes an equal home/away chance on exactly the same scored games. It was added on September 12, 2026, after the study began. Displayed metrics use at most two decimal places; full precision is retained in the downloadable evidence linked in Details.</p>'
    uncertainty=performance.uncertainty
    body+='<h3>How much confidence can we place in this?</h3>'
    if not scored:
        body+='<p>No uncertainty interval is available without scored observations.</p>'
    else:
        body+='<p>95% sampling interval for mean Brier error: <strong>'+rounded(uncertainty.lower)+' to '+rounded(uncertainty.upper)+'</strong>.</p>'
        if scored==1:
            body+='<p><strong>Only one scored observation.</strong> The interval collapses to that one result; it does not establish stable performance.</p>'
        elif rounded(uncertainty.lower)==rounded(uncertainty.upper) and uncertainty.lower!=uncertainty.upper:
            body+='<p>The interval endpoints look equal after rounding. The saved interval has a smaller nonzero width; full precision is in the downloadable evidence.</p>'
        elif uncertainty.lower==uncertainty.upper:
            body+='<p>The saved interval has zero width. This does not mean the true prediction error is known with certainty.</p>'
        else:
            body+='<p>Based on '+str(scored)+' scored observations. An interval alone does not establish that the evidence is sufficient.</p>'
    body+='<p class="muted">This interval covers sampling uncertainty, not all bias from missing or selected observations. No betting or policy recommendation follows.</p></section>'
    body+='<section class="section"><h2>What to keep in mind</h2>'
    if performance.mean_log_loss is not None and performance.mean_log_loss.is_infinite():
        body+='<p>At least one scored result occurred despite being assigned a zero probability. The downloadable evidence retains the exact error measures.</p>'
    if coverage.unknown_calendar_dates:
        body+='<p>Calendar coverage is unverified for '+str(len(coverage.unknown_calendar_dates))+' dates. We do not know how many games may be missing from those dates.</p>'
    if historical:
        body+='<p>Historical candle prices were retrieved later. They are one-minute aggregates, not simultaneous executable quotes.</p>'
        if projection['historical_markets']['unknown_membership_ids']:
            body+='<p>Which eligible games had a qualifying market is not fully known, so offered-market coverage rates are unavailable.</p>'
    else:
        body+='<p>Missed live captures cannot be reconstructed later. Future known games remain visible even before their capture is due.</p>'
    body+=('<p class="muted">Collection status: unavailable. This saved report does not certify current collection health.</p>' if collection_status is None else collection_status)+'</section>'
    return body


def table(caption, headers, rows):
    return ('<table><caption>'+text(caption)+'</caption><thead><tr>'+''.join('<th scope="col">'+text(x)+'</th>' for x in headers)+
            '</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+text(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>')


def technical_contents(report, projections, envelope, prefix=''):
    """Readable metrics only; exact scientific records remain separate downloads."""
    context=report.context;spec=context.computation
    body='<p>All displayed metrics use at most two decimals. Counts are integers. Rounding does not change the saved calculations or establish a performance conclusion.</p>'
    body+=table('Original chronology',('Event','Time'),[
        ('Evidence cutoff',friendly(spec.evidence_cutoff_at)),
        ('Computation started',friendly(spec.computation_started_at)),
        ('Computation completed',friendly(context.computation_completed_at)),
        ('Original report generated',friendly(context.report_generated_at)),
        ('Projection started',friendly(envelope['projection_started_at'])),
        ('Projection completed',friendly(envelope['projection_completed_at'])),
        ('Original rendering started',friendly(envelope['rendering_started_at']))])
    for coverage,performance,projection in zip(report.coverages,report.performances,projections['scopes'],strict=True):
        scope=coverage.scope;reference=projection['reference'];uncertainty=performance.uncertainty
        body+='<section><h2>'+text(scope.name)+'</h2><p>'+text(friendly(scope.start))+' to '+text(friendly(scope.end) if scope.end else 'ongoing; known obligations through the cutoff')+'.</p>'
        body+=table('Performance on the same scored observations',('Metric','Kalshi','50% reference'),[
            ('Scored sample size',performance.sample_size,reference['sample_size']),
            ('Mean Brier error',rounded(performance.mean_brier_score),rounded(reference['mean_brier_score'])),
            ('Mean log loss',rounded(performance.mean_log_loss),rounded(reference['mean_log_loss'])),
            ('Weighted absolute calibration error',rounded(performance.calibration.wace),'Not evaluated')])
        body+=table('Coverage — distinct opportunities',('Population','Count'),[
            ('Known scheduled',len(coverage.coverage_universe_ids)),('Eligible due',len(projection['eligible_ids'])),
            ('Captured',len(projection['captured_ids'])),('Valid probability',len(projection['valid_probability_ids'])),
            ('Scored',len(projection['scored_ids'])),('Unscored',len(projection['unscored_ids'])),
            *[(name.replace('_',' ').capitalize(),len(ids)) for name,ids in projection['reconciliation'].items()]])
        body+='<p>Scored / eligible due: '+rounded(projection['scored_over_eligible'],2,True)+'.</p>'
        markets=projection['historical_markets']
        if markets is not None:
            body+=table('Historical market coverage',('Metric','Value'),[
                ('Verified offered opportunities',len(markets['offered_ids'])),('Unknown market membership',len(markets['unknown_membership_ids'])),
                ('Offered / eligible due',rounded(markets['offered_over_eligible'],2,True)),
                ('Scored offered / offered',rounded(markets['scored_over_offered'],2,True))])
            body+='<p>'+text(markets['limitation'])+'</p>'
        body+='<p>95% sampling interval for mean Brier error: '+rounded(uncertainty.lower)+' to '+rounded(uncertainty.upper)+'. '+str(uncertainty.resample_count)+' resamples. Sampling uncertainty does not cover all selection or acquisition bias.</p>'
        if uncertainty.lower is not None and rounded(uncertainty.lower)==rounded(uncertainty.upper):
            body+='<p>Displayed interval endpoints coincide; this does not establish certainty. Rounding may hide a smaller width. See the full-precision evidence for the exact interval.</p>'
        body+=table('Fixed-bin calibration',('Bin (last upper endpoint included)','Count','Mean home probability','Home-win frequency'),[
            ('['+rounded(x['lower'])+', '+rounded(x['upper'])+(']' if x['upper_inclusive'] else ')'),x['count'],rounded(x['mean_home_probability']),rounded(x['home_win_frequency'])) for x in projection['calibration']['bins']])
        body+=calendar_details(coverage.verified_calendar_dates,coverage.unknown_calendar_dates)
        for limitation in (*coverage.limitations,*uncertainty.limitations):body+='<p>'+text(limitation)+'</p>'
        body+='</section>'
    body+='<h2>Full-precision evidence files</h2><p>These unchanged machine-readable files retain exact calculations, identifiers and timestamps. They are separate from this rounded presentation.</p><p>'
    body+=' · '.join('<a href="'+text(prefix+name)+'" download>'+label+'</a>' for name,label in [
        ('analysis.json','Download original Analysis'),('projections.json','Download projections'),('source.json','Download source boundary'),
        ('protocol.json','Download Protocol'),('envelope.json','Download original provenance'),('REPRODUCE.txt','Reproduction instructions')])
    return body+'</p>'


def render(report, projections, envelope, legacy_html=None):
    title='Historical candle report' if report.context.computation.design_tag.value=='retrospective' else 'Performance Report'
    body='<nav><a href="../../entry.html">Saved Performance Report</a></nav>'
    body+=summary(report,projections,envelope['synthetic_validation'])
    body+='<details id="report-details"><summary>Details</summary>'+technical_contents(report,projections,envelope)+'</details>'
    return page(title,body)


def date_ranges(values):
    days=sorted(set(date.fromisoformat(str(x)) for x in values))
    def label(d):return f'{d.strftime("%b")} {d.day}, {d.year}'
    ranges=[]
    for d in days:
        if ranges and d==ranges[-1][1]+timedelta(days=1):ranges[-1]=(ranges[-1][0],d)
        else:ranges.append((d,d))
    return '; '.join(label(a) if a==b else label(a)+' through '+label(b) for a,b in ranges) or 'None recorded'


def calendar_details(verified,unknown):
    body='<h3>Calendar coverage</h3><p>Verified dates have supporting calendar evidence. Unverified dates do not establish how many games are missing. Date ranges below include every date between their endpoints.</p>'
    body+=table('Calendar dates',('Status','Number of dates','Dates'),[
        ('Verified',len(verified),date_ranges(verified)),('Not verified',len(unknown),date_ranges(unknown))])
    if not verified and not unknown:body+='<p>No calendar dates are recorded for this scope; this does not establish complete coverage.</p>'
    elif not unknown:body+='<p>No unverified dates are recorded in this scope. This does not mean every game was captured or scored.</p>'
    return body


def saved_reports(state,links,metadata_href):
    body='<h2>Saved reports and last update</h2>'
    for name,label in [('live','Live Performance Report'),('historical','Historical candle report')]:
        ref=state[name]
        if ref is None:body+='<p>'+label+': no saved report selected.</p>'
        else:
            status={'in-progress':'Study in progress','interim':'Interim study'}.get(ref['report_status'],'Saved study')
            body+='<p><a href="'+text(links[name])+'">'+label+'</a> — '+status+'. Generated '+friendly(ref['report_generated_at'])+'.</p>'
    attempt=state['last_attempt']
    if attempt is None:body+='<p>No previous report attempt is recorded.</p>'
    else:
        operation={'update-live':'Update live report','generate-live':'Generate live report','generate-historical':'Generate historical report','select-historical':'Select historical report'}.get(attempt.get('operation'),'Report operation')
        status={'succeeded':'Succeeded','failed':'Failed','running':'Started; completion not recorded'}.get(attempt['status'],'Status unavailable')
        at=attempt.get('completed_at') or attempt.get('started_at')
        body+='<p>'+operation+': '+status+('. '+friendly(at) if at else '. Time not recorded')+'.</p>'
        if attempt['status']=='failed':
            error=attempt.get('error','').lower()
            reason=('Required saved material was unavailable.' if any(x in error for x in ['missing','unavailable','absent']) else
                    'The required source or report validation did not pass.' if any(x in error for x in ['source','valid','reconstruct','digest','conflict']) else
                    'The operation could not complete; its recorded diagnostic is in the metadata download.')
            body+='<p>'+reason+(' The earlier saved live report remains selected.' if state['live'] else ' No saved live report is selected.')+'</p>'
    body+='<p><a href="'+text(metadata_href)+'" download>Download exact saved-report and update metadata</a></p>'
    return body


def update_notice(state):
    attempt=state['last_attempt'];live=state['live']
    if attempt and attempt['status']=='failed':
        retained=('The saved report from '+friendly(live['report_generated_at'])+' is retained.' if live else 'No validated report available.')
        return '<p class="notice"><strong>The last report attempt failed.</strong> '+text(retained)+' See Details for the reason.</p>'
    if attempt and attempt['status']=='running':
        return '<p class="notice">A report attempt was started. Its completion is not recorded; any previously saved report remains selected.</p>'
    return ''
