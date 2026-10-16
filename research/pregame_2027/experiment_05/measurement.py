"""Frozen paired score and calendar-bootstrap calculations, reused from experiment02."""
import math
from datetime import date
def losses(y,p):
    import numpy as np
    return np.array([(p-y)**2,-y*np.log(p)-(1-y)*np.log1p(-p)])


def metrics(rows,name):
    import numpy as np
    p=np.array([r[name] for r in rows]);y=np.array([r['home_win'] for r in rows])
    loss=losses(y,p)
    return dict(games=len(rows),brier=float(loss[0].mean()),log_loss=float(loss[1].mean()))


def contrasts(rows,pairs,block):
    import numpy as np
    rng=np.random.default_rng(20261012)
    annual,draws={},[]
    for year in [2024,2025,2026]:
        rr=[r for r in rows if r['year']==year]
        start=date.fromisoformat(min(r['date'] for r in rr))
        days=(date.fromisoformat(max(r['date'] for r in rr))-start).days+1
        index=np.array([(date.fromisoformat(r['date'])-start).days for r in rr])
        count=np.bincount(index,minlength=days)
        y=np.array([r['home_win'] for r in rr])
        sums=[];means=[]
        for a,b in pairs:
            delta=losses(y,np.array([r[a] for r in rr]))-losses(y,np.array([r[b] for r in rr]))
            means.extend(delta.mean(axis=1))
            sums.extend([np.bincount(index,weights=v,minlength=days) for v in delta])
        sums=np.array(sums);replicates=[]
        for _ in range(5000):
            chosen=(rng.integers(0,days-block+1,size=math.ceil(days/block))[:,None]+np.arange(block)).ravel()[:days]
            n=count[chosen].sum();assert n>0
            replicates.append(sums[:,chosen].sum(axis=1)/n)
        dd=np.array(replicates);draws.append(dd)
        annual[str(year)]={}
        for i,(a,b) in enumerate(pairs):
            annual[str(year)][f'{a}_minus_{b}']={m:dict(difference=float(means[2*i+j]),
                       lower=float(np.quantile(dd[:,2*i+j],.025)),upper=float(np.quantile(dd[:,2*i+j],.975)))
                       for j,m in enumerate(['brier','log_loss'])}
    average=np.mean(draws,axis=0)
    mean={}
    for i,(a,b) in enumerate(pairs):
        mean[f'{a}_minus_{b}']={m:dict(
            difference=sum(annual[str(y)][f'{a}_minus_{b}'][m]['difference'] for y in [2024,2025,2026])/3,
            lower=float(np.quantile(average[:,2*i+j],.025)),upper=float(np.quantile(average[:,2*i+j],.975)))
            for j,m in enumerate(['brier','log_loss'])}
    return dict(block_days=block,replicates=5000,seed=20261012,
                sign='loss of first named learner minus second; positive favors second',
                annual=annual,equal_weight_annual=mean)


