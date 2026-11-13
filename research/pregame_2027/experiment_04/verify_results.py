"""Separate scalar scoring, saved-model replay and bootstrap weight rebuild."""
import importlib.util,json,math,datetime as dt
from pathlib import Path
import numpy as np
from scipy.special import expit
spec=importlib.util.spec_from_file_location('run',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def main(out):
    rows=m.read(out/'predictions_private.json');result=m.read(out/'results.json');a=dict(np.load(out/'features.npz'));replay={};max_score_error=0.
    for year in [2024,2025]:
        ix=a['year']==year;rr=[r for r in rows if r['year']==year]
        for arm in ['control','steamer']:
            model=m.read(out/f'{arm}_{year}_model.json');x=a[f'{arm}_{year}'][ix];w=np.array(model['coef']);p=expit((x-np.array(model['mean']))/np.array(model['scale'])@w+model['intercept']);expected=np.array([r[arm] for r in rr]);delta=float(np.abs(p-expected).max());assert delta==0;replay[f'{arm}_{year}']=delta
        for pop,selected in [('full',rr),('market_common',[r for r in rr if r['sportsbook'] is not None])]:
            for name in ['native','control','steamer']+(['sportsbook'] if pop=='market_common' else []):
                n=len(selected);b=math.fsum((r[name]-r['home_win'])**2 for r in selected)/n;ll=math.fsum(-math.log(r[name] if r['home_win'] else 1-r[name]) for r in selected)/n;record=result['annual_'+pop][str(year)][name];err=max(abs(b-record['brier']),abs(ll-record['log_loss']));max_score_error=max(max_score_error,err);assert err<1e-12
    checks={}
    for market in [False,True]:
        selected=[r for r in rows if not market or r['sportsbook'] is not None];first='sportsbook' if market else 'control'
        for block in [14,7]:
            rng=np.random.default_rng(20261012);annual=[]
            for year in [2024,2025]:
                rr=[r for r in selected if r['year']==year];days=np.array([dt.date.fromisoformat(r['date']).toordinal() for r in rr]);lo=int(days.min());L=int(days.max())-lo+1;d=days-lo;count=np.bincount(d,minlength=L)
                b0=np.array([(r[first]-r['home_win'])**2 for r in rr]);b1=np.array([(r['steamer']-r['home_win'])**2 for r in rr]);s0=np.bincount(d,weights=b0,minlength=L);s1=np.bincount(d,weights=b1,minlength=L);draw=[]
                for _ in range(5000):
                    starts=rng.integers(0,L-block+1,size=math.ceil(L/block));weights=np.zeros(L);left=L
                    for start in starts:
                        size=min(left,block);weights[start:start+size]+=1;left-=size
                    draw.append(np.dot(weights,s0-s1)/np.dot(weights,count))
                annual.append(draw)
            interval=np.quantile(np.mean(annual,axis=0),[.025,.975]);expected=result['market_bootstrap' if market else 'bootstrap'][str(block)]['equal_average_annual_brier'];delta=float(np.max(np.abs(interval-expected)));assert delta<1e-12;checks[f'{first}_vs_steamer_block{block}']=delta
    checks.update(saved_probability_replay=replay,scalar_score_max_difference=max_score_error,coverage_all_games_retained=len(rows)==4852,verification_scope='same-assistant independent arithmetic/replay and all bootstrap Brier draws; no external reviewer')
    m.save(out/'result_verification.json',checks);print(checks)

if __name__=='__main__':
    import sys;main(Path(sys.argv[1]))
