"""Separate cohort, chronology, scalar score and saved-context replay checks."""
import argparse,gc,hashlib,json,math,zipfile
from pathlib import Path
from local_model import configure,CHECKPOINT_SHA,NETWORK_ATTEMPTS
read=lambda p:json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def close(a,b,tol=1e-12):assert abs(a-b)<=tol,(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--v2-output',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--checkpoint',type=Path,required=True);a=ap.parse_args();configure(a.output)
 import numpy as np,torch
 from tabpfn.model_loading import load_fitted_tabpfn_model
 from run import reference_module
 torch.set_num_threads(4);torch.set_num_interop_threads(1)
 here=Path(__file__).resolve().parent;ref=reference_module();source_rows,labels,_=ref.load(a.source_root);source={r['game_id']:r for r in source_rows};rows=read(a.output/'predictions.json');result=read(a.output/'results.json');old=read(a.v2_output/'predictions.json');before={r['game_id']:r for r in old};provenance=read(a.output/'provenance.json')
 assert sha(a.checkpoint)==CHECKPOINT_SHA==provenance['checkpoint_sha256']
 for name,digest in provenance['outputs'].items():assert sha(a.output/name)==digest,name
 for name,digest in read(here/'pre_execution_files.json')['files'].items():assert sha(here/name)==digest,name
 for name,digest in read(here/'comparison_pins.json')['retained_v2_output'].items():assert sha(a.v2_output/name)==digest,name
 assert len(rows)==len({r['game_id'] for r in rows})==7280
 assert {r['game_id'] for r in rows}=={r['game_id'] for r in source_rows if r['year']>=2024}==set(before)
 for r in rows:
  assert all(r[k]==v for k,v in before[r['game_id']].items());assert labels[r['game_id']]==r['home_win']
  assert 0<r['tabpfn_v35']<1 and math.isfinite(r['tabpfn_v35'])
 names=['reference','catboost','tabpfn_v2','tabpfn_v35'];score_error=0.
 for market in [False,True]:
  population=[r for r in rows if not market or r['sportsbook'] is not None];ns=names+(['sportsbook'] if market else [])
  for year in [None,2024,2025,2026]:
   sub=[r for r in population if year is None or r['year']==year]
   expected=result[('pooled_' if year is None else 'annual_')+('market_common' if market else 'full')]
   if year is not None:expected=expected[str(year)]
   for n in ns:
    b=math.fsum((r[n]-r['home_win'])**2 for r in sub)/len(sub);ll=math.fsum(-r['home_win']*math.log(r[n])-(1-r['home_win'])*math.log1p(-r[n]) for r in sub)/len(sub)
    assert expected[n]['games']==len(sub)
    for key,value in [('brier',b),('log_loss',ll)]:score_error=max(score_error,abs(value-expected[n][key]));close(value,expected[n][key],1e-14)
 # Reconstruct all team histories independently from pinned canonical IDs/availability.
 d=a.source_root/'native_model_dataset_2026-09-28/dataset';canon={r['game_id']:r for r in map(json.loads,(d/'canonical_outcomes.jsonl').read_text().splitlines())};lineage=[json.loads(l) for l in (d/'history_lineage.jsonl').read_text().splitlines()];team_checks=0
 for h in lineage:
  if h['game_id'] not in source:continue
  row=source[h['game_id']];val={}
  for side in ['home','away']:
   val[side]={}
   for size in ['10','60']:
    window=h['windows'][side][size];events=[canon[k] for k in window['game_ids']];assert len(events)==window['count']>=int(size)
    assert all(e['valid'] and e['available_day']<row['date'] and row['year']-1<=e['year']<=row['year'] and row[side] in [e['home'],e['away']] and e['game_id']!=row['game_id'] for e in events)
    n=w=rd=0.
    for e in events:
     weight=1 if e['year']==row['year'] else .5;diff=(e['home_runs']-e['away_runs'])*(1 if e['home']==row[side] else -1);n+=weight;w+=weight*(diff>0);rd+=weight*diff
    close(n,window['N']);close(w,window['W']);close(rd,window['R']);val[side]['rd'+size]=rd/(n+10)
    if size=='60':val[side]['win60']=(w+1)/(n+2)
  for k in ['win60','rd60','rd10']:close(row['x_'+k],val['home'][k]-val['away'][k])
  q=min(1,sum(h['prior_current_season_counts'].values())/324)-.5;close(row['progress_centered'],q)
  for k in ['x_win60','x_rd60','x_rd10']:close(row['progress_'+k],q*row[k])
  team_checks+=1
 assert team_checks==len(source_rows)==12132
 # Stored starter lineage chronology, including zero-history cases. No raw rate-builder rerun claimed.
 pitcher_checks=0;pitcher_sources=[]
 for directory,filename,years in [('native_starter_2026-09-28','lineage.json',{2022,2023,2024}),('native_2025_comparison_2026-09-29','starter_lineage.json',{2025}),('native_2026_evaluation_2026-09-30','starter_lineage.json',{2026})]:
  p=a.source_root/directory/filename;pitcher_sources.append({'path':str(p.relative_to(a.source_root)),'sha256':sha(p)})
  for h in read(p):
   if h['game_id'] not in source or source[h['game_id']]['year'] not in years:continue
   row=source[h['game_id']]
   for side in ['home','away']:
    z=h['sides'][side];latest=z['history_max_available_day'];assert latest is None or latest<row['date']
    assert row['game_id'] not in z['history_game_ids']
    for k in z['history_game_ids']:assert canon[k]['available_day']<row['date']
   pitcher_checks+=1
 assert pitcher_checks==len(source_rows)
 records=[]
 for year in [2024,2025,2026]:
  held=[r for r in source_rows if r['year']==year];train=[r for r in source_rows if r['year']<year];assert max(r['date'] for r in train)<min(r['date'] for r in held)
  predicted={r['game_id']:r for r in rows if r['year']==year};z=np.array([[r[k] for k in ref.REFERENCE] for r in held]);file=a.output/f'tabpfn_v35_{year}.tabpfn_fit'
  with zipfile.ZipFile(file) as archive:init=json.loads(archive.read('init_params.json'))
  assert init['n_estimators']==4 and init['random_state']==20261012 and init['softmax_temperature']==1.0 and init['tuning_config'] is None and init['fit_mode']=='fit_with_cache' and not init['balance_probabilities'];assert Path(init['model_path']).name==a.checkpoint.name
  model=load_fitted_tabpfn_model(file,device='mps');assert model.softmax_temperature_==1.0 and model.tuned_classification_thresholds_ is None
  replay=np.concatenate([model.predict_proba(z[i:i+128])[:,1] for i in range(0,len(z),128)]);expected=np.array([predicted[r['game_id']]['tabpfn_v35'] for r in held]);difference=float(np.max(np.abs(replay-expected)));assert difference<=1e-6
  original=model.predict_proba(z[:128])[:16,1];mutated=z[:128].copy();mutated[16:]=1000;independence=float(np.max(np.abs(model.predict_proba(mutated)[:16,1]-original)));assert independence<=1e-6
  isolated=model.predict_proba(z[:16])[:,1];batch=float(np.max(np.abs(isolated-original)));assert batch<=1e-6
  records.append({'year':year,'training_games':len(train),'evaluation_games':len(held),'saved_context_replay_max_difference':difference,'later_test_mutation_max_difference':independence,'batch_isolation_max_difference':batch,'outer_labels_not_used_by_fit':True,'no_calibration_or_tuning':True})
  del model;gc.collect();torch.mps.empty_cache()
 gains={str(y):result['annual_full'][str(y)]['reference']['brier']-result['annual_full'][str(y)]['tabpfn_v35']['brier'] for y in [2024,2025,2026]};avg=sum(gains.values())/3
 tests={'average_brier_gain_at_least_0_001':avg>=.001,'positive_gain_in_at_least_two_years':sum(v>0 for v in gains.values())>=2,'pooled_log_loss_no_worse':result['pooled_full']['tabpfn_v35']['log_loss']<=result['pooled_full']['reference']['log_loss'],'unchanged_target_coverage':True,'no_new_hindsight_dependence':True}
 assert result['gate']['conditions']==tests and result['gate']['passed']==all(tests.values());close(avg,result['gate']['equal_weight_annual_brier_gain'])
 assert not NETWORK_ATTEMPTS
 receipt={'status':'passed','full_unique_games':len(rows),'market_common_games':sum(r['sportsbook'] is not None for r in rows),'baseline_saved_columns_unchanged':True,'original_v2_hashes_unchanged':True,'freeze_files_verified':True,'scalar_score_max_difference':score_error,'team_histories_independently_reconstructed':team_checks,'starter_stored_lineage_chronology_checked':pitcher_checks,'starter_lineage_sources':pitcher_sources,'raw_starter_rate_builder_rerun':False,'folds':records,'gate_reconstructed':True,'network_attempts':NETWORK_ATTEMPTS,'same_assistant_separate_verification':True}
 (a.output/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
if __name__=='__main__':main()
