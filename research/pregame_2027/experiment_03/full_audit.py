"""Read-only 2023 Retrosheet readiness audit; no estimation or source mutation."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path


def main(root, year):
    raw = root / 'raw'
    def rows(name):
        with (raw / (str(year) + name + '.csv')).open(newline='') as f:
            yield from csv.DictReader(f)
    def num(row, key):
        return int(row[key] or 0)
    info = {r['gid']: r for r in rows('gameinfo')}
    selected = sorted(g for g,r in info.items() if r['gametype']=='regular')
    sample = set(selected)
    players = {r['id'] for r in rows('allplayers')}
    pitching = {(r['gid'], r['id']): r for r in rows('pitching') if r['gid'] in sample}
    teams = {(r['gid'], r['team']): r for r in rows('teamstats') if r['gid'] in sample}
    starters = {(r['gid'], r['team']): r['id'] for r in pitching.values() if num(r, 'p_gs') == 1}
    assert len(teams) == 2*len(selected) and len(starters) == 2*len(selected)
    # Outcome-independent sample stays intact, including any postseason records.
    counts = collections.Counter()
    issues = collections.defaultdict(list)
    by_pitcher = collections.defaultdict(collections.Counter)
    by_team = collections.defaultdict(collections.Counter)
    seen = collections.defaultdict(set)
    dates = collections.defaultdict(set)
    first = {}
    ordinals = collections.Counter()
    suspended = {g for g, r in info.items() if r['suspend']}
    suspended_dates = collections.defaultdict(set)
    fields = ['single', 'double', 'triple', 'hr', 'sh', 'sf', 'hbp', 'walk', 'k', 'xi', 'roe', 'fc', 'othout', 'noout']
    for r in rows('plays'):
        gid = r['gid']
        if gid in suspended:
            suspended_dates[gid].add(r['date'])
        if gid not in sample:
            continue
        counts['play_rows'] += 1
        ordinals[gid] += 1
        signature = tuple(r.values())
        if signature in seen[gid]:
            issues['identical_play_rows'].append([gid, ordinals[gid]])
        seen[gid].add(signature)
        dates[gid].add(r['date'])
        if not num(r, 'pa'):
            counts['non_pa_rows'] += 1
            continue
        counts['pa'] += 1
        key = (gid, r['pitteam'])
        first.setdefault(key, r)
        if sum(num(r, f) for f in fields) != 1:
            issues['non_exclusive_outcome'].append([gid, ordinals[gid]])
        if num(r, 'iw') > num(r, 'walk') or num(r, 'k_safe') > num(r, 'k'):
            issues['invalid_subset'].append([gid, ordinals[gid]])
        for identity in ['batter', 'pitcher']:
            if r[identity] not in players:
                issues['unknown_' + identity].append([gid, r[identity]])
        counts['unknown_batter_hand'] += r['bathand'] not in ['L', 'R', 'B']
        counts['unknown_pitcher_hand'] += r['pithand'] not in ['L', 'R']
        for i in range(1, 10):
            if r['l' + str(i)] not in players:
                issues['unknown_lineup_id'].append([gid, ordinals[gid], i])
        if len({r['l' + str(i)] for i in range(1, 10)}) != 9:
            issues['non_unique_lineup'].append([gid, ordinals[gid]])
        counts['pa_by_initial_batter'] += r['batter'] in {teams[(gid, r['batteam'])]['start_l' + str(i)] for i in range(1, 10)}
        starter = r['pitcher'] == starters.get(key)
        counts['starter_pa'] += starter
        counts['starter_iw'] += starter and num(r, 'iw') == 1
        counts['iw'] += num(r, 'iw')
        counts['k_safe'] += num(r, 'k_safe')
        if not num(r, 'iw'):
            label = 'K' if num(r, 'k') else 'BB' if num(r, 'walk') else 'other'
            counts['label_' + label] += 1
            if starter:
                counts['starter_label_' + label] += 1
        for aggregate, aggregate_key in [(by_pitcher, (gid, r['pitcher'])), (by_team, (gid, r['batteam']))]:
            aggregate[aggregate_key]['pa'] += 1
            for field in ['k', 'walk', 'iw', 'hr', 'hbp']:
                aggregate[aggregate_key][field] += num(r, field)
    for key, r in first.items():
        if r['pitcher'] != starters[key]:
            issues['first_pa_not_recorded_starter'].append(list(key))
        team = teams[(key[0], r['batteam'])]
        if [r['l' + str(i)] for i in range(1, 10)] != [team['start_l' + str(i)] for i in range(1, 10)]:
            issues['initial_lineup_disagreement'].append(list(key))
    for key, r in pitching.items():
        for observed, source in [('pa','p_bfp'), ('k','p_k'), ('walk','p_w'), ('iw','p_iw'), ('hr','p_hr'), ('hbp','p_hbp')]:
            if by_pitcher[key][observed] != num(r, source):
                issues['pitcher_count_mismatch'].append([*key, observed, by_pitcher[key][observed],num(r,source)])
    for key, r in teams.items():
        for observed, source in [('pa','b_pa'), ('k','b_k'), ('walk','b_w'), ('iw','b_iw'), ('hr','b_hr'), ('hbp','b_hbp')]:
            if by_team[key][observed] != num(r, source):
                issues['team_count_mismatch'].append([*key, observed, by_team[key][observed],num(r,source)])
    for gid in sample:
        allowed = {info[gid]['date'], info[gid]['suspend']} - {''}
        if not dates[gid] or not dates[gid] <= allowed:
            issues['unexplained_play_dates'].append([gid, sorted(dates[gid]), sorted(allowed)])
    result = {
        'sample_rule': 'all regular-season games', 'sample_games':len(selected),
        'season_game_types':dict(collections.Counter(r['gametype'] for r in info.values())),
        'sample_game_types':dict(collections.Counter(info[g]['gametype'] for g in sample)),
        'counts':dict(counts), 'sample_pitching_rows':len(pitching),
        'sample_team_rows':len(teams),'initial_starters':len(starters),
        'sample_date_range':[min(info[g]['date'] for g in sample),max(info[g]['date'] for g in sample)],
        'issues':{k:len(v) for k,v in issues.items()},
        'suspended_games':{g:{'original':info[g]['date'],'resume':info[g]['suspend'],'play_dates':sorted(suspended_dates[g]),'in_sample':g in sample} for g in sorted(suspended)},
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.glob(f'{year}*.csv'))},
    }
    (root/f'audit_results_{year}.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/f'audit_discrepancies_{year}_private.json').write_text(json.dumps(issues,indent=2)+'\n')
    print(year, 'games', len(selected), 'PA', counts['pa'], 'issues',result['issues'],flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    args=parser.parse_args()
    for year in [2022,2023,2024,2025]:main(args.root,year)
