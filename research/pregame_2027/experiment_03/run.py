"""Bounded conditional PA experiment. Private arrays/models; public aggregate scores."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.optimize import minimize
from scipy.special import logsumexp


def day(s):
    return dt.datetime.strptime(s,'%Y%m%d').date().toordinal()


def prepare(root):
    records=[]; sources={}; suspended={}
    for year in [2022,2023,2024,2025]:
        raw=root/'raw'
        def read(kind):
            with (raw/f'{year}{kind}.csv').open(newline='') as f:
                yield from csv.DictReader(f)
        info={r['gid']:r for r in read('gameinfo') if r['gametype']=='regular'}
        pitchers={(r['gid'],r['team']):r['id'] for r in read('pitching') if r['gid'] in info and r['p_gs']=='1'}
        teams={(r['gid'],r['team']):r for r in read('teamstats') if r['gid'] in info}
        latest={g:max(day(r['date']),day(r['suspend']) if r['suspend'] else 0) for g,r in info.items()}
        per=[]
        for ordinal,r in enumerate(read('plays'),1):
            if r['gid'] not in info:continue
            latest[r['gid']]=max(latest[r['gid']],day(r['date']))
            if r['pa']!='1' or r['iw']=='1':continue
            label=0 if r['k']=='1' else 1 if r['walk']=='1' else 2
            assert r['bathand'] in 'LRB' and r['pithand'] in 'LR'
            hand=['RR','RL','LR','LL','BR','BL'].index(r['bathand']+r['pithand'])
            initial={teams[(r['gid'],r['batteam'])][f'start_l{i}'] for i in range(1,10)}
            per.append((year,r['gid'],day(info[r['gid']]['date']),r['pitcher'],r['batter'],label,hand,r['pitcher']==pitchers[(r['gid'],r['pitteam'])],r['batter'] in initial,ordinal))
        records.extend((*r,latest[r[1]]) for r in per)
        sources.update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob(f'{year}*.csv')})
    records.sort(key=lambda r:(r[2],r[1],r[9]))
    pids=sorted({r[3] for r in records});bids=sorted({r[4] for r in records});games=sorted({r[1] for r in records})
    pm={v:i for i,v in enumerate(pids)};bm={v:i for i,v in enumerate(bids)};gm={v:i for i,v in enumerate(games)}
    data={'year':np.array([r[0] for r in records]),'game':np.array([gm[r[1]] for r in records]),'date':np.array([r[2] for r in records]),'pid':np.array([pm[r[3]] for r in records]),'bid':np.array([bm[r[4]] for r in records]),'y':np.array([r[5] for r in records]),'hand':np.array([r[6] for r in records]),'starter':np.array([r[7] for r in records]),'initial':np.array([r[8] for r in records]),'row':np.array([r[9] for r in records]),'available':np.array([r[10] for r in records])}
    release=collections.defaultdict(list);target=collections.defaultdict(list)
    for i in range(len(records)):release[int(data['available'][i])].append(i);target[int(data['date'][i])].append(i)
    ps=np.zeros((len(pids),3));bs=np.zeros((len(bids),3));league=np.zeros(3);factor=2**(-1/180)
    daily={};x=np.zeros((len(records),9));q=np.zeros((len(records),3));cold=np.zeros((len(records),2),bool)
    for d in range(int(data['date'].min()),int(data['date'].max())+1):
        ps*=factor;bs*=factor;league*=factor
        if d-1 in release:
            idx=np.array(release[d-1]); pa=np.zeros_like(ps);ba=np.zeros_like(bs);lc=np.bincount(data['y'][idx],minlength=3).astype(float)
            np.add.at(pa,(data['pid'][idx],data['y'][idx]),1);np.add.at(ba,(data['bid'][idx],data['y'][idx]),1)
            ps+=factor*pa;bs+=factor*ba;league+=factor*lc;daily[d-1]=(pa,ba,lc)
        if d-366 in daily:
            pa,ba,lc=daily.pop(d-366);ps-=factor**366*pa;bs-=factor**366*ba;league-=factor**366*lc
        # Roundoff only; true counts cannot be negative.
        assert ps.min()>-1e-8 and bs.min()>-1e-8
        np.maximum(ps,0,out=ps);np.maximum(bs,0,out=bs);np.maximum(league,0,out=league)
        if d not in target:continue
        ix=np.array(target[d]);lq=(league+1)/(league.sum()+3);q[ix]=lq
        p=ps[data['pid'][ix]];b=bs[data['bid'][ix]];cold[ix,0]=p.sum(axis=1)<1e-10;cold[ix,1]=b.sum(axis=1)<1e-10
        pr=(p+200*lq)/(p.sum(axis=1)[:,None]+200);br=(b+200*lq)/(b.sum(axis=1)[:,None]+200)
        x[ix,:2]=np.log(pr[:,:2]/pr[:,2,None])-np.log(lq[:2]/lq[2])
        x[ix,2:4]=np.log(br[:,:2]/br[:,2,None])-np.log(lq[:2]/lq[2])
        for h in range(1,6):x[ix,3+h]=(data['hand'][ix]==h)
    data.update(x=x,q=q,cold=cold)
    np.savez_compressed(root/'features.npz',**data)
    (root/'feature_manifest.json').write_text(json.dumps({'rows':len(records),'sources':sources,'history_decay_day':'complete-game availability date','window':'D-365 through D-1 inclusive','pid_count':len(pids),'bid_count':len(bids),'game_count':len(games)},indent=2)+'\n')
    print('prepared',len(records),'rows',flush=True)


def objective(theta,z,y,penalty):
    w=theta.reshape(z.shape[1],2);eta=np.column_stack((z@w,np.zeros(len(y))))
    norm=logsumexp(eta,axis=1);loss=np.sum(norm-eta[np.arange(len(y)),y])+0.5*np.sum(penalty[:,None]*w*w)
    p=np.exp(eta-norm[:,None]);p[np.arange(len(y)),y]-=1
    grad=z.T@p[:,:2]+penalty[:,None]*w
    return float(loss)/len(y),np.asarray(grad).ravel()/len(y)


def matrix(a,idx,model,stats=None):
    if stats is None:
        stats={'mean':a['x'][idx].mean(axis=0).tolist(),'scale':np.where(a['x'][idx].std(axis=0)==0,1,a['x'][idx].std(axis=0)).tolist(),'pids':np.unique(a['pid'][idx]).tolist(),'bids':np.unique(a['bid'][idx]).tolist()}
    # Scale continuous predictors only; hand indicators stay in their documented units.
    mean=np.array(stats['mean']);scale=np.array(stats['scale']);mean[4:]=0;scale[4:]=1
    z=sparse.csr_matrix(np.column_stack((np.ones(len(idx)),(a['x'][idx]-mean)/scale)))
    if model=='challenger':
        for key in ['pid','bid']:
            mapping={v:i for i,v in enumerate(stats[key+'s'])};rr=[];cc=[]
            for i,v in enumerate(a[key][idx]):
                if int(v) in mapping:rr.append(i);cc.append(mapping[int(v)])
            z=sparse.hstack((z,sparse.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(idx),len(mapping)))),format='csr')
    return z,stats


def fit(a,train,model,gamma,path):
    z,stats=matrix(a,train,model);pen=np.full(z.shape[1],100.);pen[:10]=gamma;pen[0]=0
    start=time.monotonic();res=minimize(objective,np.zeros(2*z.shape[1]),args=(z,a['y'][train],pen),jac=True,method='L-BFGS-B',options={'maxiter':1000,'gtol':1e-8,'ftol':0,'maxls':40})
    receipt={'model':model,'gamma':gamma,'rows':len(train),'iterations':int(res.nit),'seconds':time.monotonic()-start,'success':bool(res.success),'message':str(res.message),'gradient_infinity':float(np.abs(res.jac).max()),'objective':float(res.fun),'equivalent_summed_objective':float(res.fun)*len(train),'equivalent_summed_gradient_infinity':float(np.abs(res.jac).max())*len(train),'stats':stats}
    Path(str(path)+'.json').write_text(json.dumps(receipt,indent=2)+'\n');np.save(Path(str(path)+'.npy'),res.x)
    print(model,gamma,len(train),'iter',res.nit,'gradient',receipt['gradient_infinity'],'seconds',round(receipt['seconds'],1),flush=True)
    if not res.success or receipt['gradient_infinity']>1e-8 or not np.isfinite(res.fun):raise RuntimeError('Frozen convergence requirement failed; stop specification')
    return res.x,stats


def predict(a,idx,model,w,stats):
    z,_=matrix(a,idx,model,stats);eta=np.column_stack((z@w.reshape(z.shape[1],2),np.zeros(len(idx))))
    return np.exp(eta-logsumexp(eta,axis=1)[:,None])


def losses(p,y):
    return -np.log(p[np.arange(len(y)),y]),np.sum((p-np.eye(3)[y])**2,axis=1)


def execute(root):
    a=dict(np.load(root/'features.npz'));selection={};models=root/'models';models.mkdir(exist_ok=True)
    cache={}
    for outer in [2024,2025]:
        for model in ['baseline','challenger']:
            scores={}
            for gamma in [0.1,1.,10.]:
                loss=[]
                for valyear in range(2023,outer):
                    key=(model,gamma,valyear)
                    if key not in cache:
                        tr=np.flatnonzero(a['year']<valyear);va=np.flatnonzero(a['year']==valyear)
                        w,stats=fit(a,tr,model,gamma,models/f'{model}_g{gamma}_inner{valyear}')
                        p=predict(a,va,model,w,stats);cache[key]=losses(p,a['y'][va])[0]
                    loss.append(cache[key])
                scores[gamma]=float(np.concatenate(loss).mean())
            best=min(scores.values());gamma=max(g for g,v in scores.items() if v<=best+1e-12)
            selection[f'{outer}_{model}']={'inner_log_loss':scores,'gamma':gamma}
            tr=np.flatnonzero(a['year']<outer);va=np.flatnonzero(a['year']==outer)
            w,stats=fit(a,tr,model,gamma,models/f'{model}_outer{outer}')
            np.save(root/f'{model}_{outer}_predictions.npy',predict(a,va,model,w,stats))
        (root/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')


def synthetic():
    rng=np.random.default_rng(20261012);z=sparse.csr_matrix(rng.normal(size=(17,8)));y=rng.integers(0,3,17);pen=np.arange(8,dtype=float);w=rng.normal(size=16)*.1
    _,g=objective(w,z,y,pen);h=1e-5;fd=[]
    for i in range(len(w)):
        delta=np.zeros(len(w));delta[i]=h;fd.append((objective(w+delta,z,y,pen)[0]-objective(w-delta,z,y,pen)[0])/(2*h))
    error=float(np.abs(g-fd).max());assert error<1e-7;return {'finite_difference_gradient_max_error':error,'passed':True}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','fit','synthetic']);p.add_argument('root',type=Path);args=p.parse_args()
    if args.stage=='prepare':prepare(args.root)
    elif args.stage=='fit':execute(args.root)
    else:
        result=synthetic();(args.root/'synthetic_check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
