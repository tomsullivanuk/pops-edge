"""Explicit offline display preparation from a retained report's pinned dependencies.

Never acquires, scores, changes source archives or selects a scientific report.
The browser consumes the resulting package-bound supplement without archive access.
"""
import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from forecast_standalone_operations import canonical_bytes, sha256_bytes
from forecast_reporting_activation import _retained
from forecast_reporting_delivery import read_entry, _json
from performance_reader import safe_path

VERSION = 'mlb-performance-matches-1'


def exact(root, family, identity):
    digest = identity.rsplit(':', 1)[-1]
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid retained dependency identity')
    raw = safe_path(root, f'{family}/{digest[:2]}/{digest}.json').read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError('Retained dependency digest mismatch')
    return _json(raw)


def pinned_contracts(source, archive):
    """Only normalized dependencies already pinned in this verified report package."""
    ids = set(source['source_manifest_ids']) | set(source['dependency_manifest_ids'])
    manifests = {_json(raw)['manifest_entry_id']: _json(raw) for raw in source['manifest_inventory']}
    if not ids <= manifests.keys():
        raise ValueError('Incomplete pinned manifest inventory')
    normalized = {manifests[i]['normalized_object_id'] for i in ids} - {None}
    for identity in sorted(normalized):
        value = exact(archive, 'normalized', identity)
        for raw in value.get('contracts', []):
            yield _json(raw) if isinstance(raw, str) else raw


def index_contracts(contracts):
    opportunities, observations = {}, {}
    def add(target, key, value):
        if key in target and target[key] != value:
            raise ValueError('Conflicting retained match dependency')
        target[key] = value
    for c in contracts:
        if c.get('__type__') == 'ResearchCaptureOpportunity':
            add(opportunities, c['research_capture_opportunity_id'], c)
        if c.get('__type__') == 'OutcomeHistory':
            for o in c['observations']:
                add(observations, o['observation_id'], o)
    return opportunities, observations


def value(v):
    return v.get('__datetime__') if isinstance(v, dict) else v


def rows_from_contracts(analysis, projection, opportunities, observations):
    coverage = analysis['coverages'][0]
    measurements = {m['calculation']['opportunity_id']: m['calculation'] for m in analysis['measurements']
                    if m['object_id'] in coverage['measurement_ids']}
    if len(measurements) != len(coverage['measurement_ids']):
        raise ValueError('Duplicate or missing scored match')
    derivations = {d['opportunity_id']: d['calculation'] for d in analysis['derivations']
                   if d['object_id'] in projection['derivation_ids']}
    cutoff = value(analysis['context']['computation']['evidence_cutoff_at'])
    categories = {i: category for category, ids in projection['reconciliation'].items() for i in ids}
    rows = []
    for identity in coverage['coverage_universe_ids']:
        opportunity = opportunities[identity]
        schedule = observations[opportunity['schedule_observation_id']]
        if datetime.fromisoformat(value(schedule['collected_at'])) > datetime.fromisoformat(cutoff):
            raise ValueError('Match schedule is later than the report cutoff')
        row = dict(opportunity_id=identity, event_id=schedule['canonical_event_id'],
                   home=schedule['home_participant_id'], away=schedule['away_participant_id'],
                   start=value(schedule['scheduled_start']), disposition=categories[identity],
                   probability=None, score=None, home_score=None, away_score=None,
                   outcome_id=None, outcome_observed_at=None)
        m = measurements.get(identity)
        if m:
            o = observations[m['outcome_observation_id']]
            if (o['canonical_event_id'] != row['event_id'] or o['home_participant_id'] != row['home'] or
                o['away_participant_id'] != row['away'] or m['canonical_proposition_outcome_id'] != row['home'] or
                m['realized_outcome_id'] != o['winning_participant_id'] or
                datetime.fromisoformat(value(o['collected_at'])) > datetime.fromisoformat(cutoff)):
                raise ValueError('Scored match outcome does not match saved measurement')
            row.update(probability=m['calibration_probability']['__decimal__'], score=m['brier_score']['__decimal__'],
                       home_score=o['home_score'], away_score=o['away_score'], outcome_id=o['observation_id'],
                       outcome_observed_at=value(o['collected_at']))
        elif identity in derivations:
            # Do not invent a score or final result for an unmeasured opportunity.
            d = derivations[identity]
            distribution = d.get('probability_distribution', [])
            row['probability'] = next((p['__decimal__'] for team, p in distribution if team == row['home']), None)
        rows.append(row)
    return sorted(rows, key=lambda r: (r['start'], r['event_id'], r['opportunity_id']))


def validate(payload, package_id, analysis, projection):
    material = {k:v for k,v in payload.items() if k != 'digest'}
    if (payload.get('version') != VERSION or payload.get('package_id') != package_id or
        payload.get('report_id') != analysis['object_id'] or payload.get('digest') != sha256_bytes(canonical_bytes(material))):
        raise ValueError('Saved match display does not match the selected report')
    rows = payload['rows'];coverage = analysis['coverages'][0]
    if len(rows) != len({r['opportunity_id'] for r in rows}) or {r['opportunity_id'] for r in rows} != set(coverage['coverage_universe_ids']):
        raise ValueError('Saved match population does not reconcile')
    scored = {m['calculation']['opportunity_id']:m['calculation'] for m in analysis['measurements']
              if m['object_id'] in coverage['measurement_ids']}
    categories = {i:k for k,ids in projection['reconciliation'].items() for i in ids}
    derivations = {d['opportunity_id']:d['calculation'] for d in analysis['derivations'] if d['object_id'] in projection['derivation_ids']}
    for r in rows:
        datetime.fromisoformat(r['start'])
        if datetime.fromisoformat(r['start']).utcoffset() is None:
            raise ValueError('Match date must include a timezone')
        if r['disposition'] != categories[r['opportunity_id']]:
            raise ValueError('Saved match disposition differs')
        m = scored.get(r['opportunity_id'])
        if m:
            if (r['event_id'] != m['canonical_event_id'] or r['home'] != m['canonical_proposition_outcome_id'] or
                r['score'] != m['brier_score']['__decimal__'] or r['probability'] != m['calibration_probability']['__decimal__'] or
                r['outcome_id'] != m['outcome_observation_id']):
                raise ValueError('Saved match score differs from measurement')
        elif r['score'] is not None or r['outcome_id'] is not None or r['home_score'] is not None or r['away_score'] is not None:
            raise ValueError('Unmeasured match has invented result')
        if not m:
            d = derivations.get(r['opportunity_id'], {})
            expected = next((p['__decimal__'] for team,p in d.get('probability_distribution',[]) if team==r['home']),None)
            if r['probability'] != expected:
                raise ValueError('Saved unscored probability differs from derivation')
        if m:
            hs,aws = r['home_score'],r['away_score']
            if type(hs) is not int or type(aws) is not int or min(hs,aws)<0 or hs==aws:
                raise ValueError('Invalid scored final result')
            winner = r['home'] if hs>aws else r['away']
            if winner != m['realized_outcome_id']:
                raise ValueError('Displayed result winner differs from measurement')
    return rows


def prepare(reports, archive, destination):
    reports = Path(reports).absolute();archive = Path(archive).resolve();destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError('Aliased match display destination')
    destination = destination.resolve()
    # Only presentation output, never an archive or repository, can be written.
    if destination == archive or archive in destination.parents or any((parent/'.git').exists() for parent in (destination, *destination.parents)):
        raise ValueError('Match display output must be separate from source')
    ref = read_entry(reports)['live']
    if not ref:
        raise ValueError('No selected live report')
    _retained(reports, 'live', ref)
    package = safe_path(reports, 'packages/'+ref['package_id'])
    source = _json((package/'source.json').read_bytes());analysis = _json((package/'analysis.json').read_bytes())
    projection = _json((package/'projections.json').read_bytes())['scopes'][0]
    opportunities, observations = index_contracts(pinned_contracts(source, archive))
    rows = rows_from_contracts(analysis, projection, opportunities, observations)
    payload = dict(version=VERSION, package_id=ref['package_id'], report_id=ref['report_id'], rows=rows)
    payload['digest'] = sha256_bytes(canonical_bytes(payload))
    validate(payload, ref['package_id'], analysis, projection)
    if read_entry(reports)['live'] != ref:
        raise ValueError('Selected report changed during preparation')
    destination.mkdir(parents=True, exist_ok=True)
    target = safe_path(destination, ref['package_id']+'.json')
    raw = canonical_bytes(payload)
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError('Conflicting saved match display; preserve and investigate')
    else:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination, prefix='.match-display-', delete=False) as stream:
                temporary = Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
            # Atomic create-only publication: concurrent preparations cannot overwrite history.
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != raw:
                    raise ValueError('Conflicting concurrent match display') from None
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', required=True);parser.add_argument('--archive', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(prepare(args.reports, args.archive, args.destination))
