"""Read an authorized local export and preserved lineup lineage; no fitting."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path


def main(export,lineage,year,out):
    rows=list(csv.DictReader(export.open(encoding='utf-8-sig',newline='')))
    fields=['PA','AB','H','1B','2B','3B','HR','BB','IBB','HBP','SF','wOBA']
    issues={}
    for field in fields:
        bad=0
        for row in rows:
            try:value=float(row[field]);assert math.isfinite(value) and value>=0
            except (ValueError,AssertionError):bad+=1
        issues[field]=bad
    players=[r for r in rows if r['MLBAMID'] and r['PlayerId']]
    ids=[int(float(r['MLBAMID'])) for r in players]
    assert len(set(ids))==len(ids)
    selected=[r for r in json.loads(lineage.read_text()) if r['date'].startswith(str(year)+'-')]
    slots=[t for r in selected for side in r['sides'].values() for t in side['terms']]
    required={r['mlb_player_id'] for r in slots};available=set(ids)
    result={'filename':export.name,'bytes':export.stat().st_size,'sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'lineage_sha256':hashlib.sha256(lineage.read_bytes()).hexdigest(),'rows':len(rows),'identified_player_rows':len(players),'unidentified_rows':len(rows)-len(players),'duplicate_identified_MLBAMIDs':len(ids)-len(set(ids)),'duplicate_identified_PlayerIds':len(players)-len({r['PlayerId'] for r in players}),'exact_duplicate_rows':len(rows)-len({tuple(r.values()) for r in rows}),'required_numeric_issues':issues,'columns':list(rows[0]),'content_has_season_or_system_field':any(k.lower() in ['year','season','system','type','projection'] for k in rows[0]),'year_coverage_checked':year,'native_games':len(selected),'required_player_ids':len(required),'matched_player_ids':len(required&available),'lineup_slots':len(slots),'matched_lineup_slots':sum(r['mlb_player_id'] in available for r in slots),'both_nines_complete_games':sum(all(t['mlb_player_id'] in available for v in r['sides'].values() for t in v['terms']) for r in selected),'vintage_verified':False,'membership_session_inspected':False,'model_fits':0}
    out.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['columns','required_numeric_issues']})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('export',type=Path);p.add_argument('lineage',type=Path);p.add_argument('year',type=int);p.add_argument('out',type=Path);a=p.parse_args();main(a.export,a.lineage,a.year,a.out)
