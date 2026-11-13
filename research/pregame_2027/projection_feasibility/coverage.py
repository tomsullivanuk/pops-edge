"""Read-only identity feasibility; no projection acquisition or model fitting."""
import argparse
import collections
import csv
import json
from pathlib import Path

ALIASES={108:'ANA',109:'ARI',110:'BAL',111:'BOS',112:'CHN',113:'CIN',114:'CLE',115:'COL',116:'DET',117:'HOU',118:'KCA',119:'LAN',120:'WAS',121:'NYN',133:'OAK',134:'PIT',135:'SDN',136:'SEA',137:'SFN',138:'SLN',139:'TBA',140:'TEX',141:'TOR',142:'MIN',143:'PHI',144:'ATL',145:'CHA',146:'MIA',147:'NYA',158:'MIL'}

def main(source,raw,out):
    rows=json.loads((source/'native_starter_2026-09-28/features.json').read_text())
    rows += [r for r in json.loads((source/'native_2025_comparison_2026-09-29/starter_features.json').read_text()) if r['year']==2025]
    report={};private={}
    for year in [2022,2023,2024,2025]:
        aliases=dict(ALIASES);aliases[133]='ATH' if year==2025 else 'OAK'
        with (raw/f'{year}gameinfo.csv').open() as f:
            info={r['gid']:r for r in csv.DictReader(f) if r['gametype']=='regular'}
        official=collections.defaultdict(list)
        for d in json.loads((source/f'historical_data_readiness/season_{year}/official_schedule.json').read_text())['dates']:
            for r in d['games']:official[r['gamePk']].append(r)
        by=collections.defaultdict(list)
        for gid,r in info.items():
            # MLB designated home differs from site-home in home-bats-first case.
            h,v=(r['visteam'],r['hometeam']) if r['htbf']=='true' else (r['hometeam'],r['visteam'])
            by[(r['date'],h,v)].append(gid)
        joins={};issues=[];counts=collections.Counter()
        for r in [r for r in rows if r['year']==year]:
            candidates=by[(r['date'].replace('-',''),aliases[r['home']],aliases[r['away']])]
            if len(candidates)>1:
                numbers={g.get('gameNumber') for g in official[r['game_id']] if g.get('officialDate')==r['date'] and g['status']['detailedState'] in ['Final','Completed Early','Game Over']}
                if len(numbers)==1:
                    number=next(iter(numbers));candidates=[g for g in candidates if int(info[g]['number'])==number]
                    counts['joined_with_retained_final_schedule_number']+=len(candidates)==1
                else:candidates=[]
            if len(candidates)==1:joins[str(r['game_id'])]=candidates[0]
            else:issues.append({'game_id':r['game_id'],'candidates':candidates})
        assert len(set(joins.values()))==len(joins)
        with (raw/f'{year}teamstats.csv').open() as f:
            teams=[r for r in csv.DictReader(f) if r['gid'] in set(joins.values())]
        players={r[f'start_l{i}'] for r in teams for i in range(1,10)}
        report[year]={'native_targets':sum(r['year']==year for r in rows),'retrosheet_regular_games':len(info),'joined_games':len(joins),'unresolved_games':len(issues),'required_initial_lineup_slots':len(teams)*9,'distinct_initial_batter_retrosheet_ids':len(players),**dict(counts)}
        private[year]={'joins':joins,'required_retrosheet_ids':sorted(players),'unresolved':issues}
    (out/'repository_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'private_candidates.json').write_text(json.dumps(private,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('raw',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.source,a.raw,a.out)
