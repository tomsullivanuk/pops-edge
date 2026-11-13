"""Frozen paired measurements and two distinct gates; aggregate outputs only."""
import importlib.util,json,math,datetime as dt
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('reference',Path(__file__).resolve().parents[1]/'experiment_01/run.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def scores(rows,name):return ref.metrics(rows,name)
def bootstrap(rows,first,second,length):
    rng=np.random.default_rng(20261012);annual=[]
    for year in [2024,2025]:
        rr=[r for r in rows if r['year']==year];days=[dt.date.fromisoformat(r['date']).toordinal() for r in rr];lo=min(days);n=max(days)-lo+1;ix=np.array(days)-lo
        y=np.array([r['home_win'] for r in rr]);pa=np.array([r[first] for r in rr]);pb=np.array([r[second] for r in rr]);a=ref.losses(y,pa);b=ref.losses(y,pb);counts=np.bincount(ix,minlength=n);sums=np.array([np.bincount(ix,weights=x-z,minlength=n) for x,z in zip(a,b)]);draws=[]
        for _ in range(5000):
            idx=(rng.integers(0,n-length+1,size=math.ceil(n/length))[:,None]+np.arange(length)).ravel()[:n];draws.append(sums[:,idx].sum(axis=1)/counts[idx].sum())
        annual.append(np.array(draws))
    interval=lambda x:np.quantile(x,[.025,.975]).tolist()
    return {'sign':f'{first} loss minus {second} loss; positive favors {second}','equal_average_annual_brier':interval(np.mean([a[:,0] for a in annual],axis=0)),'annual':{str(y):{'brier':interval(a[:,0]),'log_loss':interval(a[:,1])} for y,a in zip([2024,2025],annual)},'replicates':5000,'seed':20261012,'block_days':length}

def main(out):
    rows=json.loads((out/'predictions_private.json').read_text());assert len(rows)==4852 and len({r['game_id'] for r in rows})==4852
    common=[r for r in rows if r['sportsbook'] is not None];assert [sum(r['year']==y for r in common) for y in [2024,2025]]==[2291,2425]
    names=['native','control','steamer'];annual={str(y):{n:scores([r for r in rows if r['year']==y],n) for n in names} for y in [2024,2025]};book={str(y):{n:scores([r for r in common if r['year']==y],n) for n in names+['sportsbook']} for y in [2024,2025]};pooled={n:scores(rows,n) for n in names};pc={n:scores(common,n) for n in names+['sportsbook']}
    bs={str(b):bootstrap(rows,'control','steamer',b) for b in [14,7]};market_bs={str(b):bootstrap(common,'sportsbook','steamer',b) for b in [14,7]};gains=[annual[str(y)]['control']['brier']-annual[str(y)]['steamer']['brier'] for y in [2024,2025]]
    info={'average_annual_brier_gain':float(np.mean(gains)),'annual_brier_gains':gains,'gain_at_least_0_001':np.mean(gains)>=.001,'positive_both_years':min(gains)>0,'no_worse_pooled_log_loss':pooled['steamer']['log_loss']<=pooled['control']['log_loss'],'primary_interval_positive':bs['14']['equal_average_annual_brier'][0]>0,'same_coverage':True};info={k:bool(v) if isinstance(v,np.bool_) else v for k,v in info.items()};info['passes']=all(info[k] for k in ['gain_at_least_0_001','positive_both_years','no_worse_pooled_log_loss','primary_interval_positive','same_coverage'])
    mg={'lower_pooled_brier':pc['steamer']['brier']<pc['sportsbook']['brier'],'lower_pooled_log_loss':pc['steamer']['log_loss']<pc['sportsbook']['log_loss'],'no_worse_annual_brier':all(book[str(y)]['steamer']['brier']<=book[str(y)]['sportsbook']['brier'] for y in [2024,2025])};mg['passes']=all(mg.values())
    strata={}
    for y in [2024,2025]:
        strata[y]={}
        for field in ['fallback','cold']:
            for value in [True,False]:
                subset=[r for r in rows if r['year']==y and r[field]==value]
                if subset:strata[y][f'{field}_{value}']={n:scores(subset,n) for n in names}
    result=dict(annual_full=annual,pooled_full=pooled,annual_market_common=book,pooled_market_common=pc,bootstrap=bs,market_bootstrap=market_bs,information_gate=info,market_gate=mg,calibration={str(y):{n:ref.calibration([r for r in rows if r['year']==y],n) for n in names} for y in [2024,2025]},strata_diagnostic_only=strata,coverage=dict(full=4852,market_common=len(common),dropped=0),reused_development=True,kalshi_or_returns_tested=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['annual_full','annual_market_common','information_gate','market_gate']},indent=2))

if __name__=='__main__':
    import sys;main(Path(sys.argv[1]))
