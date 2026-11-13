"""Read-only retained-input WAR audit; writes aggregate receipt only, never fits."""
import argparse,collections,csv,hashlib,json,math
from pathlib import Path
FILES={2022:'fangraphs-leaderboard-projections-2022.csv',2023:'fangraphs-leaderboard-projections-2023.csv',2024:'fangraphs-leaderboard-projections- 2024.csv',2025:'fangraphs-leaderboard-projections-2025.csv'}
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def csvrows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--repository-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();assert not a.output.exists()
 reconciled=read(a.repository_root/'research/pregame_2027/projection_feasibility/replacement_reconciliation.json');rows=read(a.source_root/'native_starter_2026-09-28/features.json');rows += [r for r in read(a.source_root/'native_2025_comparison_2026-09-29/starter_features.json') if r['year']==2025];assert len(rows)==9704 and len({r['game_id'] for r in rows})==9704
 joins=read(a.private_root/'projection-feasibility/private_candidates.json');bridge=read(a.private_root/'projection-feasibility/slot_bridge_private.json');assert all(len(v)==1 for v in bridge.values());retro_to_mlb={v[0]:int(k) for k,v in bridge.items()};assert len(retro_to_mlb)==len(bridge)
 pins={};exports={};raw_inventory=[]
 for y,name in FILES.items():
  p=a.private_root/'projection-feasibility/replacement-import'/name;digest=sha(p);assert digest==reconciled[str(y)]['sha256'];rr=csvrows(p);header=list(rr[0]);assert all(k in header for k in ['WAR','PA','MLBAMID','PlayerId'])
  good={};unidentified=0;invalid=0;zero=0;negative=0
  for r in rr:
   if not r['MLBAMID'].strip() or not r['PlayerId'].strip():unidentified+=1;continue
   pid=int(float(r['MLBAMID']));assert pid not in good
   try:
    n=float(r['PA']);war=float(r['WAR']);assert math.isfinite(n) and n>=0 and math.isfinite(war)
   except Exception:invalid+=1;continue
   zero+=n==0;negative+=war<0;good[pid]=(war,n)
  native=[r for r in rows if r['year']==y];mapped=joins[str(y)]['joins'];assert {str(r['game_id']) for r in native}==set(mapped)
  info=csvrows(a.private_root/f'experiment-03/raw/{y}gameinfo.csv');bygid={r['gid']:r for r in info if r['gametype']=='regular'};assert len(bygid)==len([r for r in info if r['gametype']=='regular'])
  teams=csvrows(a.private_root/f'experiment-03/raw/{y}teamstats.csv');wanted=set(mapped.values());selected=[r for r in teams if r['gid'] in wanted];assert len(selected)==len(native)*2
  missing=0;bad_rate=0;both=0;needed=set();matched=set();missing_games=collections.Counter();slots=0
  for team in selected:
   for slot in range(1,10):
    rid=team[f'start_l{slot}'];assert rid in retro_to_mlb;pid=retro_to_mlb[rid];needed.add(pid);slots+=1
    if pid not in good:missing+=1;missing_games[team['gid']]+=1;continue
    war,n=good[pid]
    if n<=0:bad_rate+=1;missing_games[team['gid']]+=1;continue
    assert math.isfinite(600*war/n);matched.add(pid)
  exports[str(y)]={'filename':name,'sha256':digest,'rows':len(rr),'identified_usable_rows':len(good),'unidentified_rows':unidentified,'invalid_WAR_PA_rows':invalid,'zero_PA_identified_rows':zero,'negative_WAR_identified_rows':negative,'native_games':len(native),'initial_lineup_slots':slots,'required_player_ids':len(needed),'matched_required_player_ids':len(matched),'missing_projection_slots':missing,'zero_or_invalid_rate_target_slots':bad_rate,'matched_rate_slots':slots-missing-bad_rate,'games_both_nines_rate_available':len(native)-len(missing_games),'has_explicit_season_date_system_columns':[k for k in header if any(t in k.lower() for t in ['date','season','asof','system'])],'release_timestamp_verified':False,'archive_revision_verified':False,'season_association':'Owner year-labelled replacements; byte-identical to prior imported files'}
  pins['projection/'+name]=digest
  for p in sorted((a.private_root/'experiment-03/raw').glob(f'{y}*.csv')):
   with p.open(encoding='utf-8-sig',newline='') as f:columns=next(csv.reader(f))
   raw_inventory.append({'path_alias':'retrosheet_raw/'+p.name,'sha256':sha(p),'columns':len(columns),'WAR_columns':[k for k in columns if k.lower() in ['war','fwar','bwar']],'advanced_fielding_baserunning_columns':[k for k in columns if k.lower() in ['uzr','oaa','frv','xbr','framing','blocking','arm','rpos','rrep','rpw']]})
 # Existing downloaded bundles may contain unextracted traditional fielding;
 # header absence is not a claim that no fielding information exists anywhere.
 record={'scope':'Retained four year-labelled projection CSVs, all20extracted Retrosheet CSV headers and retained exact lineup/identity joins. No provider export acquisition, fitting or scoring.','status':'blocked_dated_observed_WAR_not_established','season_inputs':[2022,2023,2024,2025],'eligible_native_games':9704,'evaluation_games':{'2024':2426,'2025':2426},'evaluation_market_common':{'2024':2291,'2025':2425},'exports':exports,'raw_inventory':raw_inventory,'projection_pins':pins,'joins_sha256':sha(a.private_root/'projection-feasibility/private_candidates.json'),'bridge_sha256':sha(a.private_root/'projection-feasibility/slot_bridge_private.json'),'observed_WAR_snapshots_found_in_scoped_inputs':0,'observed_WAR_PA_columns_in_extracted_raw':[r['path_alias'] for r in raw_inventory if r['WAR_columns']],'projected_2026_export_in_scoped_inputs':False,'model_fits':0,'retained_raw_data_modified':False,'limitations':['Scope is retained inspected sources, not a global historical-data availability claim.','Some retained Retrosheet annual bundles contain unextracted traditional fielding; no FanGraphs advanced WAR component archive established.','Projection season provenance is Owner supplied; no original preseason publication/revision timestamp proved.']}
 a.output.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'exports':exports,'raw_files_checked':len(raw_inventory),'model_fits':0},indent=2))
if __name__=='__main__':main()
