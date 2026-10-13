import importlib.util,json,math,sys
from pathlib import Path
import numpy as np
r=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('run',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);a=dict(np.load(r/'features.npz'));results=json.loads((r/'results.json').read_text());receipt={};daily={}
for y in [2024,2025]:
 ix=np.flatnonzero(a['year']==y);s=a['starter'][ix];yy=a['y'][ix][s];p0=np.load(r/f'baseline_{y}_predictions.npy')[s];p1=np.load(r/f'challenger_{y}_predictions.npy')[s]
 for model,p in [('baseline',p0),('challenger',p1)]:
  b=math.fsum(sum((float(v[k])-(k==int(label)))**2 for k in range(3)) for v,label in zip(p,yy))/len(yy);assert abs(b-results['annual'][str(y)]['starter'][model]['brier'])<1e-12
 stats=json.loads((r/'models'/f'challenger_outer{y}.json').read_text())['stats'];w=np.load(r/'models'/f'challenger_outer{y}.npy');idx=ix[:128];orig=m.predict(a,idx,'challenger',w,stats);mut={k:v.copy() for k,v in a.items()};mut['x'][ix[-128:]]+=100;assert np.array_equal(orig,m.predict(mut,idx,'challenger',w,stats))
 cold={k:v.copy() for k,v in a.items()};cold['pid'][idx]=-1;cold['bid'][idx]=-1;z,_=m.matrix(cold,idx,'challenger',stats);assert z[:,10:].nnz==0;cp=m.predict(cold,idx,'challenger',w,stats);assert np.isfinite(cp).all() and np.max(np.abs(cp.sum(axis=1)-1))<1e-12
 dates=a['date'][ix][s];n=int(dates.max()-dates.min()+1);d=dates-dates.min();daily[y]=[np.bincount(d,weights=-np.log(p[np.arange(len(yy)),yy]),minlength=n) for p in [p0,p1]]
 receipt[y]={'independent_brier':'passed','later_row_prediction_mutation_difference':0,'unseen_ids_have_zero_residual_columns':True,'valid_cold_probabilities':True}
for block in [14,7]:
 rng=np.random.default_rng(20261012);samples=[]
 for _ in range(5000):
  gains=[]
  for y in [2024,2025]:
   b,c=daily[y];L=len(b);starts=rng.integers(0,L-block+1,size=math.ceil(L/block));weights=np.zeros(L,dtype=int);remaining=L
   for start in starts:
    size=min(block,remaining);weights[start:start+size]+=1;remaining-=size
   gains.append(float(np.dot(weights,b-c)/np.dot(weights,b)))
  samples.append(np.mean(gains))
 interval=np.quantile(samples,[.025,.975]);delta=float(np.max(np.abs(interval-results['intervals'][str(block)])));assert delta<1e-12;receipt[f'bootstrap_{block}_independent_weight_rebuild_max_difference']=delta
(r/'extra_verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)
