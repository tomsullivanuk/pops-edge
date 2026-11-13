import importlib.util,json,math,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1])
code=Path(__file__).with_name('run.py');spec=importlib.util.spec_from_file_location('runner',code);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=dict(np.load(root/'features.npz'));results={};replay={};daily={};receipts=[]
for year in [2024,2025]:
 ix=np.flatnonzero(a['year']==year);target=a['starter'][ix];pred={}
 for model in ['baseline','challenger']:
  p=np.load(root/f'{model}_{year}_predictions.npy');w=np.load(root/'models'/f'{model}_outer{year}.npy');receipt=json.loads((root/'models'/f'{model}_outer{year}.json').read_text());rp=m.predict(a,ix,model,w,receipt['stats']);delta=float(np.abs(p-rp).max());assert delta==0;replay[f'{year}_{model}']=delta;pred[model]=p
 pred['league']=a['q'][ix];annual={}
 for population,mask in [('starter',target),('all_roles',np.ones(len(ix),bool)),('initial_batter_starter',target&a['initial'][ix])]:
  metrics={}
  for model,p in pred.items():
   ll,br=m.losses(p[mask],a['y'][ix][mask]);games=a['game'][ix][mask];unique,inverse=np.unique(games,return_inverse=True);counts=np.bincount(inverse);llgame=np.bincount(inverse,weights=ll)/counts;brgame=np.bincount(inverse,weights=br)/counts
   metrics[model]={'PA':int(mask.sum()),'games':len(unique),'log_loss':float(ll.mean()),'brier':float(br.mean()),'equal_game_log_loss':float(llgame.mean()),'equal_game_brier':float(brgame.mean()),'mean_probabilities':p[mask].mean(axis=0).tolist(),'observed_class_rates':np.bincount(a['y'][ix][mask],minlength=3).astype(float).__truediv__(mask.sum()).tolist()}
   assert abs(math.fsum(-math.log(float(v[y])) for v,y in zip(p[mask],a['y'][ix][mask]))/mask.sum()-ll.mean())<1e-12
  annual[population]=metrics
 results[year]=annual
 days=a['date'][ix][target];lo=int(days.min());hi=int(days.max());ll0=m.losses(pred['baseline'][target],a['y'][ix][target])[0];ll1=m.losses(pred['challenger'][target],a['y'][ix][target])[0]
 daily[year]=(np.bincount(days-lo,weights=ll0,minlength=hi-lo+1),np.bincount(days-lo,weights=ll1,minlength=hi-lo+1),np.bincount(days-lo,minlength=hi-lo+1))
 for model in ['baseline','challenger']:
  receipt=json.loads((root/'models'/f'{model}_outer{year}.json').read_text());replay[f'{year}_{model}_unseen_pitcher_rows']=int(sum(int(v) not in set(receipt['stats']['pids']) for v in a['pid'][ix]));replay[f'{year}_{model}_unseen_batter_rows']=int(sum(int(v) not in set(receipt['stats']['bids']) for v in a['bid'][ix]))
for p in (root/'models').glob('*.json'):
 x=json.loads(p.read_text());x.pop('stats');assert x['success'] and x['gradient_infinity']<=1e-8;receipts.append(x)
gains=[(results[y]['starter']['baseline']['log_loss']-results[y]['starter']['challenger']['log_loss'])/results[y]['starter']['baseline']['log_loss'] for y in [2024,2025]]
intervals={}
for block in [14,7]:
 rng=np.random.default_rng(20261012);samples=[]
 for _ in range(5000):
  gg=[]
  for y in [2024,2025]:
   b,c,n=daily[y];L=len(n);starts=rng.integers(0,L-block+1,size=math.ceil(L/block));idx=np.concatenate([np.arange(s,s+block) for s in starts])[:L];gg.append(float((b[idx].sum()-c[idx].sum())/b[idx].sum()))
  samples.append(np.mean(gg))
 intervals[block]=np.quantile(samples,[.025,.975]).tolist()
gate={'average_relative_log_loss_gain':float(np.mean(gains)),'annual_relative_gains':gains,'at_least_0_005':float(np.mean(gains))>=.005,'both_years_positive':min(gains)>0,'no_worse_average_brier':bool(np.mean([results[y]['starter']['challenger']['brier']-results[y]['starter']['baseline']['brier'] for y in [2024,2025]])<=0),'primary_interval_positive':intervals[14][0]>0};gate['passes']=all(gate[k] for k in ['at_least_0_005','both_years_positive','no_worse_average_brier','primary_interval_positive'])
(root/'results.json').write_text(json.dumps({'annual':results,'gate':gate,'intervals':intervals},indent=2)+'\n');(root/'verification.json').write_text(json.dumps({'saved_forecast_replay':replay,'independent_log_loss_arithmetic':'passed all three populations/models/years','fit_receipts':receipts},indent=2)+'\n');print(json.dumps({'annual':results,'gate':gate,'intervals':intervals},indent=2))
