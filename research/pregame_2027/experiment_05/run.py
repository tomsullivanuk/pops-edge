"""One frozen v3.5 core comparison; private predictions and fit contexts stay local."""
import argparse,gc,hashlib,importlib.util,json,resource,signal,sys,time
from pathlib import Path
from local_model import configure,classifier,CHECKPOINT_SHA,NETWORK_ATTEMPTS
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,value):
 assert not p.exists(),f'Output exists; preserve it: {p.name}'
 p.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
def reference_module():
 p=HERE.parent/'experiment_01/run.py';spec=importlib.util.spec_from_file_location('frozen_reference',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def summarize(rows,ref):
 from measurement import metrics,contrasts
 names=['reference','catboost','tabpfn_v2','tabpfn_v35'];common=[r for r in rows if r['sportsbook'] is not None]
 annual={str(y):{n:metrics([r for r in rows if r['year']==y],n) for n in names} for y in [2024,2025,2026]}
 pooled={n:metrics(rows,n) for n in names};gains={str(y):annual[str(y)]['reference']['brier']-annual[str(y)]['tabpfn_v35']['brier'] for y in [2024,2025,2026]}
 tests={'average_brier_gain_at_least_0_001':sum(gains.values())/3>=.001,'positive_gain_in_at_least_two_years':sum(v>0 for v in gains.values())>=2,'pooled_log_loss_no_worse':pooled['tabpfn_v35']['log_loss']<=pooled['reference']['log_loss'],'unchanged_target_coverage':len(rows)==7280,'no_new_hindsight_dependence':True}
 pairs=[('reference','tabpfn_v35'),('tabpfn_v2','tabpfn_v35'),('catboost','tabpfn_v35')]
 cpairs=pairs+[('sportsbook',n) for n in names]
 return {'annual_full':annual,'pooled_full':pooled,'annual_market_common':{str(y):{n:metrics([r for r in common if r['year']==y],n) for n in names+['sportsbook']} for y in [2024,2025,2026]},'pooled_market_common':{n:metrics(common,n) for n in names+['sportsbook']},'gate':{'annual_brier_gains':gains,'equal_weight_annual_brier_gain':sum(gains.values())/3,'conditions':tests,'passed':all(tests.values())},'bootstrap_full':{str(b):contrasts(rows,pairs,b) for b in [14,7]},'bootstrap_market_common':{str(b):contrasts(common,cpairs,b) for b in [14,7]},'calibration_full':{str(y):{n:ref.calibration([r for r in rows if r['year']==y],n) for n in names} for y in [2024,2025,2026]},'calibration_market_common':{str(y):{n:ref.calibration([r for r in common if r['year']==y],n) for n in names+['sportsbook']} for y in [2024,2025,2026]},'coverage':{'full_games':len(rows),'market_common_games':len(common),'missing_market_games':len(rows)-len(common),'target_drop_count':0},'reused_development_seasons':[2024,2025,2026],'kalshi_or_return_test_performed':False,'post_fit_calibration_applied':False}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--v2-output',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--checkpoint',type=Path,required=True);ap.add_argument('--stage',choices=['fit','summarize'],required=True);ap.add_argument('--freeze-commit',required=True);a=ap.parse_args();assert len(a.freeze_commit)==40 and all(c in '0123456789abcdef' for c in a.freeze_commit);a.output.mkdir(parents=True,exist_ok=True);configure(a.output)
 import numpy as np,torch,tabpfn
 from tabpfn.model_loading import save_fitted_tabpfn_model
 torch.set_num_threads(4);torch.set_num_interop_threads(1)
 ref=reference_module();settings=read(HERE/'SETTINGS.json');pins=read(HERE/'comparison_pins.json')
 if a.stage=='fit':save(a.output/'execution_start.json',{'freeze_commit':a.freeze_commit,'protocol_sha256':sha(HERE/'PROTOCOL.md'),'settings_sha256':sha(HERE/'SETTINGS.json'),'code_sha256':sha(Path(__file__)),'model_sha256':sha(HERE/'local_model.py'),'measurement_sha256':sha(HERE/'measurement.py'),'comparison_pins_sha256':sha(HERE/'comparison_pins.json'),'no_baseball_outputs_examined_before_freeze':True})
 for name,h in read(HERE/'input_manifest.json').items():assert sha(a.source_root/name)==h,name
 for name,h in pins['repository'].items():assert sha(HERE.parent.parent.parent/name)==h,name
 for name,h in pins['retained_v2_output'].items():assert sha(a.v2_output/name)==h,name
 if a.stage=='summarize':
  rows=read(a.output/'predictions.json');result=summarize(rows,ref)
  prior=read(HERE.parent/'experiment_02/results.json')
  for group in ['annual_full','annual_market_common']:
   for y in ['2024','2025','2026']:
    for n,v in prior[group][y].items():assert result[group][y][n]==v,(group,y,n)
  save(a.output/'results.json',result);print(json.dumps({k:result[k] for k in ['annual_full','annual_market_common','gate']},indent=2),flush=True);return
 rows,labels,_=ref.load(a.source_root);assert settings['features']==ref.REFERENCE
 baseline,models,replay=ref.reference_replay(a.source_root,rows,labels);save(a.output/'reference_replay.json',replay);save(a.output/'reference_models.json',models)
 retained=read(a.v2_output/'predictions.json');old={r['game_id']:r for r in retained};assert len(old)==len(retained)==7280
 assert set(old)=={r['game_id'] for r in rows if r['year']>=2024}
 assert all(abs(baseline[i]-r['reference'])<1e-9 for i,r in old.items())
 print('REFERENCE_REPLAY',json.dumps(replay),flush=True)
 assert torch.backends.mps.is_available()
 def deadline(signum,frame):raise TimeoutError('1800-second annual fold ceiling')
 signal.signal(signal.SIGALRM,deadline);predictions=[];timings=[]
 for year,counts in [(2024,(4852,2426)),(2025,(7278,2426)),(2026,(9704,2428))]:
  signal.alarm(1800);train=[r for r in rows if r['year']<year];held=[r for r in rows if r['year']==year];assert (len(train),len(held))==counts
  assert max(r['date'] for r in train)<min(r['date'] for r in held)
  x=np.array([[r[k] for k in settings['features']] for r in train]);y=np.array([labels[r['game_id']] for r in train]);z=np.array([[r[k] for k in settings['features']] for r in held]);assert np.isfinite(x).all() and np.isfinite(z).all()
  start=time.monotonic();model=classifier(a.checkpoint);model.fit(x,y);torch.mps.synchronize();fitted=time.monotonic();assert model.softmax_temperature_==1.0 and model.tuned_classification_thresholds_ is None
  p=np.concatenate([model.predict_proba(z[i:i+128])[:,1] for i in range(0,len(z),128)]);torch.mps.synchronize();predicted=time.monotonic();assert len(p)==len(held) and np.isfinite(p).all() and ((p>0)&(p<1)).all()
  save_fitted_tabpfn_model(model,a.output/f'tabpfn_v35_{year}.tabpfn_fit')
  context={r['game_id']:r for r in map(json.loads,(a.source_root/f'historical_opening_odds_2026-09-28/season_{year}/derived/consensus.jsonl').read_text().splitlines())}
  annual=[]
  for r,value in zip(held,p):
   before=old[r['game_id']];market=context[r['game_id']];q=market['opening_consensus_home'] if market['native_comparison_eligible'] else None
   assert (before['year'],before['date'],before['home_win'])==(year,r['date'],labels[r['game_id']]);assert market['date']==r['date'] and before['sportsbook']==q
   annual.append({**before,'tabpfn_v35':float(value)})
  assert sum(r['sportsbook'] is not None for r in annual)=={2024:2291,2025:2425,2026:2428}[year]
  timing={'year':year,'training_games':len(train),'evaluation_games':len(held),'fit_seconds':fitted-start,'predict_seconds':predicted-fitted,'mps_driver_bytes_after_prediction':torch.mps.driver_allocated_memory(),'max_process_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,'training_years':sorted({r['year'] for r in train}),'no_outer_labels_in_fit':True,'resolved_temperature':model.softmax_temperature_}
  save(a.output/f'predictions_{year}.json',annual);save(a.output/f'timing_{year}.json',timing);predictions+=annual;timings.append(timing);print('V35_FOLD',json.dumps(timing),flush=True)
  del model;gc.collect();torch.mps.empty_cache();signal.alarm(0)
 save(a.output/'predictions.json',predictions);save(a.output/'timings.json',timings)
 assert not NETWORK_ATTEMPTS
 save(a.output/'provenance.json',{'freeze_commit':a.freeze_commit,'checkpoint_sha256':sha(a.checkpoint),'script_sha256':sha(Path(__file__)),'model_script_sha256':sha(HERE/'local_model.py'),'protocol_sha256':sha(HERE/'PROTOCOL.md'),'settings_sha256':sha(HERE/'SETTINGS.json'),'input_manifest_sha256':sha(HERE/'input_manifest.json'),'comparison_pins_sha256':sha(HERE/'comparison_pins.json'),'python':sys.version.split()[0],'torch':torch.__version__,'tabpfn':tabpfn.__version__,'network_attempts':NETWORK_ATTEMPTS,'outputs':{p.name:sha(p) for p in sorted(a.output.iterdir()) if p.is_file()}})
if __name__=='__main__':
 try:main()
 except BaseException as e:
  if '--output' in sys.argv:
   target=Path(sys.argv[sys.argv.index('--output')+1]);target.mkdir(parents=True,exist_ok=True)
   failure=target/('failure_'+str(time.time_ns())+'.json');failure.write_text(json.dumps({'error_type':type(e).__name__,'message':str(e),'partial_outputs_preserved':True},indent=2)+'\n')
  raise
