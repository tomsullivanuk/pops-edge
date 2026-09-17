"""Manual, archive-read-only report packages and a small local delivery entry.

The only mutable publication is entry.html. Source anchors and verification
receipts are separate from immutable candidate/package payloads.
"""
from __future__ import annotations

import fcntl
import html
import json
import os
import re
import shutil
import subprocess
import uuid
import webbrowser
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import forecast_reporting_analysis as analysis
from forecast_reporting_projections import VERSION as PROJECTION_VERSION, create_reporting_projections
from forecast_reporting_source import FrozenReportingSource, freeze_reporting_source, verify_reporting_source
from forecast_standalone_operations import OperationsError, canonical_bytes, sha256_bytes

VERSION = 'mlb-reporting-delivery-1'
RENDERER = 'mlb-reporting-html-3'
REPOSITORY = Path(__file__).resolve().parent
PAYLOAD_NAMES = {'source.json', 'analysis.json', 'projections.json', 'envelope.json',
                 'protocol.json', 'report.html', 'REPRODUCE.txt'}
TRUST = ('Local retained anchors and truthful clocks are trusted. Hashes do not authenticate '
         'an adversary replacing both package and anchor. Retained archive Evidence is required '
         'for scientific replay. A copied package without its independent anchor is inspectable only.')


def _fail(message):
    raise OperationsError('reporting-delivery-failure', message)


def utc_now():
    return datetime.now(timezone.utc)


def _time(clock):
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail('aware actual wall time required')
    return value.astimezone(timezone.utc)


def _json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(body, object_pairs_hook=pairs)


def _overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def validate_output_root(output, archive=None):
    output = Path(output).resolve()
    forbidden = [REPOSITORY]
    if archive is not None:
        forbidden += [archive.root.resolve(), archive.config.secondary_root.resolve()]
    if any(_overlap(output, root) for root in forbidden) or any((parent/'.git').exists() for parent in (output, *output.parents)):
        _fail('delivery output must not overlap source checkout or either archive root')
    # Resolve root aliases, then forbid redirection within its managed layout.
    for name in ('anchors', 'receipts', 'packages', 'candidates', 'entry.html', '.delivery.lock'):
        if (output/name).is_symlink():
            _fail('symlink in managed delivery layout')
    return output


def _identity(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        _fail('exact package digest required')
    return value


def _anchor_key(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        _fail('explicit independently retained anchor key required')
    return value


def _create(path, body):
    with path.open('xb') as handle:
        handle.write(body); handle.flush(); os.fsync(handle.fileno())


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _local_writer(output):
    output.mkdir(parents=True, exist_ok=True)
    with (output/'.delivery.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            _fail('another local delivery command is running; retry manually')
        for name in ('anchors', 'receipts', 'packages', 'candidates'):
            (output/name).mkdir(exist_ok=True)
        yield


def _text(value):
    if value is None:
        return 'Unavailable'
    return html.escape(str(value))


def _table(caption, headers, rows):
    return ('<table><caption>' + _text(caption) + '</caption><thead><tr>' +
            ''.join('<th scope="col">'+_text(x)+'</th>' for x in headers) +
            '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+_text(x)+'</td>' for x in row)+'</tr>' for row in rows) + '</tbody></table>')


def _page(title, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>'+_text(title)+'</title><style>body{font:17px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17212b;background:#fff}table{border-collapse:collapse;width:100%;margin:1rem 0}caption{text-align:left;font-weight:700}th,td{border:1px solid #aab4bf;padding:.45rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf2f7}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#0645ad}details{margin:1rem 0}h1,h2{line-height:1.2}</style></head><body><main><h1>'+_text(title)+'</h1>'+body+'</main></body></html>').encode()


@dataclass(frozen=True)
class DeliveryEnvelope:
    version: str
    renderer_version: str
    projection_version: str
    report_id: str
    source_boundary_id: str
    projection_id: str
    protocol_id: str
    software_revision: str
    projection_started_at: str
    projection_completed_at: str
    rendering_started_at: str
    anchor_key: str
    synthetic_validation: bool
    trust_assumption: str = TRUST


def _render_report_v1(report, projections, envelope):
    context = report.context; spec = context.computation
    title = 'Historical candle report' if spec.design_tag.value == 'retrospective' else 'Performance Report'
    body = '<p>'+_text(context.report_status)+' · '+_text(spec.design_tag.value)+' · Derived Analysis</p>'
    if envelope['synthetic_validation']:
        body += '<p><strong>SYNTHETIC VALIDATION ONLY — not a production report.</strong></p>'
    body += _table('Identity and chronology', ('Field', 'Value'), (
        ('Report identity', report.object_id), ('Protocol', spec.protocol_id),
        ('Evidence cutoff K', spec.evidence_cutoff_at.isoformat()),
        ('Computation started', spec.computation_started_at.isoformat()),
        ('Computation completed', context.computation_completed_at.isoformat()),
        ('Original report generated', context.report_generated_at.isoformat()),
        ('Projection started', envelope['projection_started_at']),
        ('Projection completed', envelope['projection_completed_at']),
        ('Rendering started', envelope['rendering_started_at']),
        ('Validation base revision' if envelope['synthetic_validation'] else 'Executing revision', envelope['software_revision'])))
    body += '<p>Collection status: unavailable. This saved report does not certify current collection health.</p>'
    body += '<p>The 50% reference is a descriptive addition adopted September 12, 2026, after study commencement. It uses exactly the same scored Measurements as Kalshi. No significance, Market Edge, Policy or wagering authority is created.</p>'
    for coverage, performance, projection in zip(report.coverages, report.performances, projections['scopes'], strict=True):
        scope = coverage.scope
        body += '<section><h2>'+_text(scope.name)+'</h2><p>Study interval: '+_text(scope.start)+' to '+_text(scope.end if scope.end else 'ongoing; all known obligations through K')+'. '+_text(scope.endpoint_semantics)+'.</p>'
        body += _table('Observed performance and exact-population reference', ('Metric', 'Kalshi', '50% reference'), (
            ('Scored sample size', performance.sample_size, projection['reference']['sample_size']),
            ('Mean Brier score', performance.mean_brier_score, projection['reference']['mean_brier_score']),
            ('Mean log loss', performance.mean_log_loss, projection['reference']['mean_log_loss']),
            ('Weighted absolute calibration error', performance.calibration.wace, 'Not evaluated')))
        body += _table('Coverage — counts of distinct opportunities', ('Population', 'Count'), (
            ('Known schedule opportunities', len(coverage.coverage_universe_ids)),
            ('Eligible due', len(projection['eligible_ids'])), ('Captured', len(projection['captured_ids'])),
            ('Valid probability observations', len(projection['valid_probability_ids'])),
            ('Scored', len(projection['scored_ids'])), ('Unscored (all reasons)', len(projection['unscored_ids'])),
            *[(name, len(ids)) for name, ids in projection['reconciliation'].items()]))
        body += '<p>Overall scored / eligible due: '+_text(projection['scored_over_eligible'])+'</p>'
        markets = projection['historical_markets']
        if markets is not None:
            body += _table('Historical offered-market coverage', ('Metric', 'Value'), (
                ('Verified offered opportunities', len(markets['offered_ids'])),
                ('Unknown offered membership', len(markets['unknown_membership_ids'])),
                ('Offered / eligible due', markets['offered_over_eligible']),
                ('Scored offered / offered', markets['scored_over_offered'])))
            body += '<p>'+_text(markets['limitation'])+'</p>'
        uncertainty = performance.uncertainty
        body += '<p>95% one-sample Brier interval: '+_text(uncertainty.lower)+' to '+_text(uncertainty.upper)+'. 200 resamples. Sampling uncertainty does not include every acquisition or selection bias.</p>'
        body += '<p>'+_text('; '.join(uncertainty.limitations))+'</p>'
        body += _table('Fixed-bin calibration on exact scored Measurements', ('Bin (final upper endpoint closed)', 'Count', 'Mean home probability', 'Home-win frequency'),
            [(f"[{x['lower']}, {x['upper']}{']' if x['upper_inclusive'] else ')'}", x['count'], x['mean_home_probability'], x['home_win_frequency']) for x in projection['calibration']['bins']])
        body += '<details><summary>Calendar coverage, identities and limitations</summary><p>Unknown dates do not imply a known count of missing games.</p><pre>'+_text(json.dumps(dict(
            verified_calendar_dates=[str(x) for x in coverage.verified_calendar_dates],
            unknown_calendar_dates=[str(x) for x in coverage.unknown_calendar_dates],
            limitations=list(coverage.limitations), projection=projection), indent=2, sort_keys=True))+'</pre></details></section>'
    body += '<details><summary>Scientific provenance and original root limitations</summary><p>The original analytical root is preserved unchanged. Its downstream-reference limitation describes the earlier library slice; this delivery envelope adds the independently validated reference and display projections.</p><pre>'+_text(json.dumps(dict(
        original_limitations=report.limitations, rules=spec.rule_references,
        source_boundary_id=spec.source_boundary_id, envelope=envelope), indent=2, sort_keys=True))+'</pre></details>'
    body += '<p>'+_text(TRUST)+'</p><p><a href="analysis.json">Original Analysis</a> · <a href="projections.json">Projections</a> · <a href="source.json">Source boundary</a> · <a href="REPRODUCE.txt">Reproduction instructions</a></p>'
    return _page(title, body)


def render_report(report, projections, envelope):
    if envelope['renderer_version'] == 'mlb-reporting-html-1':
        return _render_report_v1(report, projections, envelope)
    if envelope['renderer_version'] == 'mlb-reporting-html-2':
        from forecast_reporting_presentation_v2 import render
        return render(report, projections, envelope, _render_report_v1(report, projections, envelope))
    if envelope['renderer_version'] != RENDERER:
        _fail('unknown report renderer version')
    from forecast_reporting_presentation import render
    return render(report, projections, envelope)


def _empty_state():
    return dict(version=VERSION, live=None, historical=None, last_attempt=None)


def read_entry(output):
    path = Path(output)/'entry.html'
    if not path.exists():
        return _empty_state()
    raw = path.read_text()
    match = re.search(r'<script type="application/json" id="delivery-state">(.*?)</script>', raw, re.S)
    if not match:
        _fail('local entry record is invalid; inspect manually')
    state = _json(match.group(1))
    if set(state) != set(_empty_state()) or state['version'] != VERSION:
        _fail('local entry version or fields conflict')
    for key in ('live', 'historical'):
        if state[key] is not None:
            _identity(state[key]['package_id']); _anchor_key(state[key]['anchor_key'])
    return state


def _replace_entry(output, state):
    from forecast_reporting_presentation import page, summary, technical_contents, friendly, saved_reports, update_notice
    body = ''; metadata = ''; live = state['live']
    historical = state['historical']
    if historical is None:
        body += '<nav>Historical candle report: no validated report available.</nav>'
    else:
        relative = 'packages/'+_identity(historical['package_id'])+'/report.html'
        body += '<nav><a href="'+relative+'">Historical candle report</a></nav>'
        if not (output/relative).is_file():
            body += '<p class="notice">Selected package unavailable. Historical selection retained; no substitute chosen.</p>'
    attempt = state['last_attempt']
    body += update_notice(state)
    if live is None:
        body += '<p>No validated report available.</p><p>A live report has not yet been generated and selected successfully.</p>'
    else:
        package = output/'packages'/_identity(live['package_id'])
        try:
            _, payloads = _inspect(package, live['package_id'])
            report = analysis.deserialize_reporting_analysis(payloads['analysis.json'].decode())
            projections = _json(payloads['projections.json']); envelope = _json(payloads['envelope.json'])
            if report.object_id != live['report_id'] or report.context.computation.design_tag.value != 'prospective':
                _fail('saved live reference conflicts with package')
            body += summary(report, projections, envelope['synthetic_validation'])
            prefix = 'packages/'+live['package_id']+'/'
            metadata += '<p><a href="'+prefix+'report.html">Immutable saved report</a></p>'
            metadata += technical_contents(report, projections, envelope, prefix)
        except Exception as exc:
            # A newly selected update must still be readable when the entry is built.
            # Fail through generation's existing rollback, preserving the old reference.
            if attempt and attempt['status'] == 'succeeded' and attempt.get('operation') == 'update-live':
                raise
            body += '<p class="notice">Selected package unavailable or damaged. Its identity and original date are retained; no replacement was chosen.</p>'
            metadata += '<p>The selected report could not be read. Exact references and diagnostics remain in the metadata download.</p>'
    body += '<details id="report-details"><summary>Details</summary>'+metadata+saved_reports(state, {name:'packages/'+ref['package_id']+'/report.html' for name,ref in [('live',live),('historical',historical)] if ref}, 'entry.html')+'</details>'
    state_json = canonical_bytes(state).decode().replace('<', '\\u003c')
    body += '<script type="application/json" id="delivery-state">'+state_json+'</script>'
    temporary = output/('entry-'+uuid.uuid4().hex+'.partial')
    _create(temporary, page('Performance Report', body))
    try:
        os.replace(temporary, output/'entry.html')
    finally:
        temporary.unlink(missing_ok=True)


def _revision(expected):
    def git(*args):
        return subprocess.run(['git', '-C', str(REPOSITORY), *args], check=True, capture_output=True, text=True).stdout.strip()
    head = git('rev-parse', 'HEAD')
    if not re.fullmatch('[0-9a-f]{40}', expected or '') or head != expected or git('status', '--porcelain', '--untracked-files=all'):
        _fail('generation requires a clean reproducible checkout at the explicit executing revision')
    return head


def _read_anchor(output, key):
    path = output/'anchors'/(_anchor_key(key)+'.json')
    if path.is_symlink():
        _fail('anchor must be independently retained, not a package alias')
    if not path.is_file():
        _fail('independently retained source anchor is missing')
    value = _json(path.read_bytes())
    if set(value) != {'version', 'anchor_key', 'boundary_id', 'retained_at'} or value['version'] != VERSION or value['anchor_key'] != key:
        _fail('invalid independent source anchor')
    return value


def _reproduction():
    return (f'Immutable derived report package, {VERSION}.\n{TRUST}\n'
        'Open report.html directly offline: this does not run scientific verification or refresh dates.\n'
        'For replay use the exact software_revision in envelope.json and retained archive configuration.\n'
        'Run operate_forecast_reporting.py --output OUTPUT verify --config CONFIG --package PACKAGE_DIGEST --anchor INDEPENDENT_ANCHOR_KEY\n'
        'Obtain the anchor key from the retained local entry/receipt, never by trusting the candidate.\n'
        'All seven payload files determine the sorted inventory. package.json contains that inventory,\n'
        'a separately dated package completion, and its SHA-256 identity (excluding the identity field).\n'
        'HTML displays the report identity to avoid a circular package digest. Later receipts reference\n'
        'the package identity and remain outside it. Retain source, anchors, receipts and packages together\n'
        'with their distinct trust roles. New Evidence requires a new package; old bytes are never updated.\n').encode()


def _inspect(path, expected_id=None):
    if path.is_symlink() or not path.is_dir():
        _fail('package directory is absent or aliased')
    if set(x.name for x in path.iterdir()) != PAYLOAD_NAMES | {'package.json'}:
        _fail('package payload inventory has missing or extra files')
    if any(not x.is_file() or x.is_symlink() for x in path.iterdir()):
        _fail('package payload must be regular retained files')
    manifest = _json((path/'package.json').read_bytes())
    if set(manifest) != {'version', 'package_id', 'inventory', 'package_completed_at'} or manifest['version'] != VERSION:
        _fail('unknown package manifest')
    if (path/'package.json').read_bytes() != canonical_bytes(manifest):
        _fail('package manifest is not canonical')
    material = {k:v for k,v in manifest.items() if k != 'package_id'}
    identity = sha256_bytes(canonical_bytes(material))
    if manifest['package_id'] != identity or (expected_id is not None and expected_id != identity):
        _fail('package identity conflict')
    payloads = {name:(path/name).read_bytes() for name in sorted(PAYLOAD_NAMES)}
    if manifest['inventory'] != {name:sha256_bytes(body) for name,body in payloads.items()}:
        _fail('package payload digest conflict')
    return manifest, payloads


def _verify(path, output, anchor_key, archive, clock, expected_id=None):
    anchor = _read_anchor(output, anchor_key)  # independent of all candidate bytes
    manifest, payloads = _inspect(path, expected_id)
    source = FrozenReportingSource.from_json(payloads['source.json'].decode())
    report = analysis.deserialize_reporting_analysis(payloads['analysis.json'].decode())
    expected = anchor['boundary_id']
    projected = create_reporting_projections(archive=archive, source=source,
        expected_source_boundary_id=expected, report=report, clock=clock)
    state, source_receipt = verify_reporting_source(archive=archive, boundary=source,
        expected_boundary_id=expected, clock=clock)
    _, protocol = analysis._authority(state, report.context.computation.protocol_id)
    envelope = _json(payloads['envelope.json'])
    try:
        typed = DeliveryEnvelope(**envelope)
        times = [datetime.fromisoformat(envelope[x]) for x in ('projection_started_at', 'projection_completed_at', 'rendering_started_at')]
        completed = datetime.fromisoformat(manifest['package_completed_at'])
        retained = datetime.fromisoformat(anchor['retained_at'])
        for value in (*times, completed, retained):
            if value.tzinfo is None or value.utcoffset() is None:
                _fail('package chronology must be aware')
    except (TypeError, KeyError, ValueError) as exc:
        _fail('invalid delivery envelope: '+str(exc))
    if not source.frozen_at <= retained <= report.context.computation.computation_started_at:
        _fail('anchor was not retained before computing the candidate')
    if not report.context.report_generated_at <= times[0] <= times[1] <= times[2] <= completed <= source_receipt.verified_at:
        _fail('package chronology does not follow actual analytical work')
    if typed.renderer_version not in {'mlb-reporting-html-1', 'mlb-reporting-html-2', RENDERER}:
        _fail('unknown report renderer version')
    wanted = DeliveryEnvelope(VERSION, typed.renderer_version, PROJECTION_VERSION, report.object_id,
        source.boundary_id, projected['object_id'], protocol.standalone_probability_source_protocol_id,
        report.context.computation.software_revision, *[x.isoformat() for x in times],
        anchor_key, typed.synthetic_validation)
    if type(typed.synthetic_validation) is not bool or typed != wanted:
        _fail('incompatible package envelope references')
    exact = {'source.json': source.to_json().encode(), 'analysis.json': report.to_json().encode(),
        'projections.json': canonical_bytes(projected), 'envelope.json': canonical_bytes(asdict(wanted)),
        'protocol.json': protocol.to_json().encode(), 'report.html': render_report(report, projected, envelope),
        'REPRODUCE.txt': _reproduction()}
    if payloads != exact:
        _fail('package payloads do not reconstruct: '+', '.join(name for name in exact if payloads[name] != exact[name]))
    return manifest, report, source_receipt


def _receipt(output, manifest, report, source_receipt, anchor_key, clock):
    at = _time(clock)
    if at < source_receipt.verified_at:
        _fail('receipt clock reversed')
    value = dict(version=VERSION, package_id=manifest['package_id'], report_id=report.object_id,
        source_boundary_id=source_receipt.boundary_id, anchor_key=anchor_key, verified_at=at.isoformat())
    path = output/'receipts'/(uuid.uuid4().hex+'.json')
    _create(path, canonical_bytes(value))
    return value


def verify_package(*, output, package_id, anchor_key, archive, clock=utc_now):
    output = validate_output_root(output, archive)
    with _local_writer(output):
        manifest, report, receipt = _verify(output/'packages'/_identity(package_id), output,
            anchor_key, archive, clock, package_id)
        return _receipt(output, manifest, report, receipt, anchor_key, clock)


def _reference(manifest, report, anchor_key):
    return dict(package_id=manifest['package_id'], anchor_key=anchor_key, report_id=report.object_id,
                report_status=report.context.report_status, report_generated_at=report.context.report_generated_at.isoformat())


def generate_report(*, archive, output, study, expected_revision, report_status='in-progress',
                    update_live=False, clock=utc_now, synthetic_validation=False, prepare_matches=False):
    output = validate_output_root(output, archive)
    with _local_writer(output):
        state = read_entry(output)
        attempt = dict(attempt_id=uuid.uuid4().hex, operation='update-live' if update_live else 'generate-'+study,
                       status='running', started_at=_time(clock).isoformat())
        try:
            _replace_entry(output, {**state, 'last_attempt':attempt})
            if prepare_matches and not (study == 'live' and update_live):
                _fail('match preparation requires a live update')
            if study not in {'historical', 'live'} or (update_live and study != 'live'):
                _fail('exactly one study required; only live update may move current live reference')
            if report_status not in {'in-progress', 'interim'}:
                _fail('final, closure and correction publication are outside this workflow')
            if synthetic_validation:
                if archive.config.mode.value != 'dry-run':
                    _fail('synthetic clock/revision injection requires a dry-run archive')
                revision = expected_revision
            else:
                if clock is not utc_now:
                    _fail('operational generation requires actual wall time')
                revision = _revision(expected_revision)
            source = freeze_reporting_source(archive=archive, clock=clock)
            key = uuid.uuid4().hex
            retained = _time(clock)
            if retained < source.frozen_at:
                _fail('anchor retention clock reversed')
            _create(output/'anchors'/(key+'.json'), canonical_bytes(dict(version=VERSION,
                anchor_key=key, boundary_id=source.boundary_id, retained_at=retained.isoformat())))
            _sync_directory(output/'anchors')
            from forecast_standalone_activation import canonical_retrospective_authority, canonical_prospective_authority
            _, protocol = canonical_retrospective_authority() if study == 'historical' else canonical_prospective_authority()
            report = analysis.create_standalone_report_analysis(archive=archive, source=source,
                expected_source_boundary_id=_read_anchor(output,key)['boundary_id'],
                protocol_id=protocol.standalone_probability_source_protocol_id,
                software_revision=revision, clock=clock, report_status=report_status)
            started = _time(clock)
            projections = create_reporting_projections(archive=archive, source=source,
                expected_source_boundary_id=_read_anchor(output,key)['boundary_id'], report=report, clock=clock)
            completed = _time(clock); rendering = _time(clock)
            envelope = asdict(DeliveryEnvelope(VERSION, RENDERER, PROJECTION_VERSION, report.object_id,
                source.boundary_id, projections['object_id'], protocol.standalone_probability_source_protocol_id,
                revision, started.isoformat(), completed.isoformat(), rendering.isoformat(), key, synthetic_validation))
            payloads = {'source.json':source.to_json().encode(), 'analysis.json':report.to_json().encode(),
                'projections.json':canonical_bytes(projections), 'envelope.json':canonical_bytes(envelope),
                'protocol.json':protocol.to_json().encode(), 'report.html':render_report(report, projections, envelope),
                'REPRODUCE.txt':_reproduction()}
            candidate = output/'candidates'/attempt['attempt_id']; candidate.mkdir()
            for name, body in sorted(payloads.items()):
                _create(candidate/name, body)
            material = dict(version=VERSION, inventory={name:sha256_bytes(body) for name,body in sorted(payloads.items())},
                            package_completed_at=_time(clock).isoformat())
            manifest = {**material, 'package_id':sha256_bytes(canonical_bytes(material))}
            _create(candidate/'package.json', canonical_bytes(manifest))
            manifest, report, source_receipt = _verify(candidate, output, key, archive, clock)
            if not synthetic_validation:
                _revision(revision)  # detect checkout drift across the calculation
            target = output/'packages'/manifest['package_id']
            if target.exists() or target.is_symlink():
                old, old_payloads = _inspect(target, manifest['package_id'])
                if old != manifest or old_payloads != payloads:
                    _fail('immutable package collision')
                shutil.rmtree(candidate)
            else:
                for path in candidate.iterdir():
                    path.chmod(0o444)
                _sync_directory(candidate)
                os.rename(candidate, target)
                target.chmod(0o555)
                _sync_directory(output/'packages')
            _receipt(output, manifest, report, source_receipt, key, clock)
            ref = _reference(manifest, report, key)
            if prepare_matches:
                from mlb_performance_matches import prepare
                prepare(output, archive.root, output/'matches', reference=ref)
                if not synthetic_validation:
                    _revision(revision)
            new_state = {**state, 'last_attempt':{**attempt, 'status':'succeeded',
                'completed_at':_time(clock).isoformat(), 'package':ref}}
            if update_live:
                new_state['live'] = ref
            _replace_entry(output, new_state)
            return ref
        except BaseException as exc:
            try:
                _replace_entry(output, {**state, 'last_attempt':{**attempt, 'status':'failed',
                    'completed_at':_time(clock).isoformat(), 'error':str(exc)}})
            except BaseException as persistence:
                _fail(f'{exc}; ATTEMPT STATUS COULD NOT BE SAVED: {persistence}')
            raise


def select_historical(*, output, package_id, anchor_key, archive, clock=utc_now):
    output = validate_output_root(output, archive)
    with _local_writer(output):
        state = read_entry(output)
        try:
            manifest, report, receipt = _verify(output/'packages'/_identity(package_id), output, anchor_key, archive, clock, package_id)
            if report.context.computation.design_tag.value != 'retrospective':
                _fail('historical selection requires a historical package')
            _receipt(output, manifest, report, receipt, anchor_key, clock)
            _replace_entry(output, {**state, 'historical':_reference(manifest,report,anchor_key),
                'last_attempt':dict(operation='select-historical',status='succeeded',completed_at=_time(clock).isoformat())})
        except BaseException as exc:
            try:
                _replace_entry(output, {**state,'last_attempt':dict(operation='select-historical',status='failed',error=str(exc),completed_at=_time(clock).isoformat())})
            except BaseException as persistence:
                _fail(f'{exc}; ATTEMPT STATUS COULD NOT BE SAVED: {persistence}')
            raise


def open_saved(*, output, package_id=None, opener=webbrowser.open):
    """Viewing only: no source, network request, verification, scoring or writes."""
    output = validate_output_root(output)
    path = output/'entry.html' if package_id is None else output/'packages'/_identity(package_id)/'report.html'
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(output):
        _fail('saved report unavailable; no generation was attempted')
    if opener(path.as_uri()) is False:
        _fail('browser could not open saved output')
    return path
