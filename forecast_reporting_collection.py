"""Frozen, non-authoritative display of existing sanitized invocation records."""
from pathlib import Path

from forecast_standalone_activation import OperationalState, operational_observations
from forecast_standalone_operations import OperationsError, canonical_bytes, sha256_bytes
import forecast_reporting_presentation as presentation

VERSION = 'mlb-collection-display-1'
LABELS = {
    'capture-prospective': 'Live quote collection',
    'refresh-supporting': 'Supporting data refresh',
    'reconcile-outcomes': 'Outcome reconciliation',
    'rebuild-prospective-projection': 'Full archive inspection',
    'refresh-prospective-projection': 'Incremental archive inspection',
    'rebuild-index': 'Index rebuild', 'sync-secondary': 'Secondary copy',
    'archive-audit': 'Archive inspection', 'index': 'Index',
    'health-report': 'Recorded health check', 'lifecycle-cycle': 'Collection cycle',
    'lifecycle-hour': 'Scheduled collection hour', 'maintain': 'Maintenance',
}


def snapshot(root, observed_at):
    """Read once. Never run health-report: that command writes a heartbeat.

    No archive integrity, checkpoint, free-space or secondary audit is attempted.
    Bad operational material degrades this display alone, never scientific results.
    """
    result = dict(version=VERSION, observed_at=observed_at.isoformat(),
        authority='non-authoritative saved invocation observations; not a fresh health audit',
        availability='unavailable', reason='No operational records selected',
        latest_record_at=None, last_valid_completions=[], current_blockers=[],
        superseded_failures=[], recent_skips=[], last_health_check=None,
        observations_sha256=None)
    if root is None:
        return result
    try:
        root = Path(root)
        # iterdir raises permission errors; glob alone can hide them as absence.
        files = list(root.iterdir())
        if root.is_symlink() or any(p.is_symlink() for p in files if p.suffix == '.json'):
            raise ValueError('aliased records')
        entries = OperationalState(root).entries()
        if not entries:
            result['reason'] = 'No operational records available'
            return result
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError('unaware observation time')
        identities = {}
        for item in entries:
            if (not isinstance(item.command, str) or not isinstance(item.disposition, str) or
                    (item.failure_code is not None and not isinstance(item.failure_code, str))):
                raise ValueError('invalid operational labels')
            if any(t.tzinfo is None or t.utcoffset() is None for t in (item.started_at, item.completed_at)):
                raise ValueError('unaware record time')
            # Several elapsed hourly skips can truthfully share one detection time.
            # Conflicting dispositions at an equal time must not choose by filename.
            identity = (item.command, item.completed_at)
            meaning = (item.disposition, item.failure_code)
            if identity in identities and identities[identity] != meaning:
                raise ValueError('ambiguous completion')
            identities[identity] = meaning
        observed = operational_observations(entries, observed_at)
        health = observed['latest'].get('health-report')
        result.update(availability='available', reason=None,
            latest_record_at=max(x.completed_at for x in entries).isoformat(),
            last_valid_completions=[(name, item.completed_at.isoformat()) for name, item in sorted(observed['valid'].items())],
            current_blockers=sorted(set(observed['blockers'])),
            superseded_failures=list(observed['superseded']), recent_skips=list(observed['skips']),
            last_health_check=None if health is None else dict(completed_at=health.completed_at.isoformat(),
                disposition=health.disposition, failure_code=health.failure_code),
            observations_sha256=sha256_bytes(canonical_bytes(entries)))
    except FileNotFoundError:
        result['reason'] = 'Operational records are absent'
    except OSError:
        result['reason'] = 'Operational records could not be read'
    except (OperationsError, ValueError, TypeError, KeyError, AttributeError):
        result['reason'] = 'Operational records are malformed, ambiguous or have invalid chronology'
    return result


def label(value):
    command, _, reason = value.partition(':')
    name = LABELS.get(command, command.replace('-', ' ').capitalize())
    return name + (': ' + reason.replace('-', ' ') if reason else '')


def render(value, recovery_href, download_href):
    p = presentation
    body = '<section class="section"><h2>Collection status</h2>'
    body += '<p>Operational records read '+p.friendly(value['observed_at'])+'. This is a frozen observation, separate from the report dates.</p>'
    if value['availability'] != 'available':
        body += '<p><strong>Collection status unavailable.</strong> '+p.text(value['reason'])+'. The saved scientific report remains available.</p>'
    else:
        blockers = value['current_blockers']
        stale = any(x.endswith(':stale-or-absent') for x in blockers)
        headline = ('Stale or incomplete collection observations' if stale else
                    'Collection invocation issues observed' if blockers else 'No invocation blockers observed')
        body += '<p><strong>'+headline+'.</strong> Latest recorded completion: '+p.friendly(value['latest_record_at'])+'.</p>'
        if blockers:
            body += '<ul>'+''.join('<li>'+p.text(label(x))+'</li>' for x in blockers)+'</ul>'
        if value['recent_skips']:
            body += '<p>'+str(len(value['recent_skips']))+' skipped cycle observations in the existing 25-hour health window. Skips do not count as valid completions.</p>'
        health = value['last_health_check']
        if health:
            body += '<p>Last recorded health-check outcome: '+p.text(label(health['disposition']))+' at '+p.friendly(health['completed_at'])+'. It has not been rechecked for this display.</p>'
        else:
            body += '<p>No recorded health-check outcome is available.</p>'
        body += '<details><summary>Collection details</summary>'
        body += p.table('Last valid command completions', ('Work', 'Completed (Eastern)'),
            [(LABELS.get(name, name.replace('-', ' ').capitalize()), p.friendly(at)) for name, at in value['last_valid_completions']])
        if value['superseded_failures']:
            body += '<p>Earlier failures superseded by later valid completion under existing health rules:</p><ul>'
            body += ''.join('<li>'+p.text(label(x))+'</li>' for x in value['superseded_failures'])+'</ul>'
        if value['recent_skips']:
            body += p.table('Recent skipped cycles', ('Work', 'Observed (Eastern)'),
                [(LABELS.get(x.split(':', 1)[0], x.split(':', 1)[0]),
                  p.friendly(x.split(':', 1)[1].rsplit(':skipped-cycle', 1)[0])) for x in value['recent_skips']])
        body += '</details>'
    body += '<p class="muted">Opening this page does not refresh status or run collection. Invocation success does not establish complete capture coverage. Archive integrity, checkpoints, disk space and the secondary copy were not audited for this display.</p>'
    body += '<p><a href="'+p.text(recovery_href)+'">Collection and report recovery guide</a> · <a download href="'+p.text(download_href)+'">Download saved collection observation</a></p></section>'
    return body


def recovery_page():
    return presentation.page('Collection and report recovery guide', '''
<h1>Collection and report recovery</h1>
<p>This saved guide accompanies a frozen operational observation. Opening a report runs no jobs and grants no recovery or collection authority.</p>
<h2>Unavailable or stale status</h2>
<p>Check the configured operational-state directory and readable invocation records. Preserve malformed or ambiguous records for inspection. A missing or stale observation does not invalidate a saved scientific report. Use the documented activate-display command with --operational-state to read existing records again; this changes only the display and its separate observation date.</p>
<h2>Collection failures and skips</h2>
<p>Inspect the recorded failure and the existing operator guides before intervening. A skipped cycle is not a valid completion; later independent valid work can resolve a current invocation failure. Do not erase earlier failures or reconstruct missed prospective quotes. An older health-check outcome is not a new readiness assessment.</p>
<p>Checkpoint loss or corruption requires the existing full offline rebuild after inspection. Preserve unresolved request/publication markers; do not retry unknown calls or relabel them as misses. Collector recovery, archive repairs and job changes require their own operating authority.</p>
<h2>Report recovery</h2>
<p>A failed or unfinished scientific report attempt leaves the previous saved reports selected. Confirm no delivery command is running, inspect the failure, retain diagnostics, and correct the identified storage or configuration issue before a new independent attempt. Never change anchors, immutable packages or Evidence to make validation pass.</p>
<p>The activation record retains a previous-entry backup. The documented rollback-display command restores it only while the current entry and backup match their saved digests. A status refresh does not rescore results, select a new report or change the last scientific attempt.</p>
<p><a href="operator-guide.md">Reporting commands and manual recovery</a> · <a href="collection-guide.md">Existing collection health and recovery rules</a> · <a href="deployment-guide.md">Pinned deployment procedure</a></p>
''')
