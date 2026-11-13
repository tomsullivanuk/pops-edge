"""Approved fixed-feature Steamer comparison. Private raw data and predictions."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,csv,collections,datetime as dt,hashlib,importlib.util,json,math,warnings
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from scipy.special import expit

HERE=Path(__file__).resolve().parent
SOURCE=Path('/Users/tom/.codex/.chatgpt-projects/g-p-6a6cba0d8b288191820b710ce15a39e4')
PRIVATE=Path('/Users/tom/Documents/Codex/2026-10-12/task')
RAW=PRIVATE/'experiment-03/raw'
PROJ=PRIVATE/'projection-feasibility/replacement-import'
NAMES=['x_win60','x_rd60','x_rd10','progress_centered','progress_x_win60','progress_x_rd60','progress_x_rd10','starter_kbb','starter_hr','starter_ip']
SETTINGS=dict(C=1.,fit_intercept=True,class_weight=None,solver='lbfgs',tol=1e-8,max_iter=10000,l1_ratio=0.)
FILES={2022:'fangraphs-leaderboard-projections-2022.csv',2023:'fangraphs-leaderboard-projections-2023.csv',2024:'fangraphs-leaderboard-projections- 2024.csv',2025:'fangraphs-leaderboard-projections-2025.csv'}

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def day(s):return dt.datetime.strptime(s,'%Y%m%d').date().toordinal()
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)
def numden(r,projected=False):
    v=lambda k:float(r[k] or 0)
    bb=v('BB')-v('IBB') if projected else v('walk')-v('iw')
    keys=['HBP','1B','2B','3B','HR'] if projected else ['hbp','single','double','triple','hr']
    numerator=.690*bb+sum(w*v(k) for w,k in zip([.722,.888,1.271,1.616,2.101],keys))
    denominator=v('AB' if projected else 'ab')+bb+v('SF' if projected else 'sf')+v('HBP' if projected else 'hbp')
    return numerator,denominator

def prepare(out):
    rows=read(SOURCE/'native_starter_2026-09-28/features.json')+[r for r in read(SOURCE/'native_2025_comparison_2026-09-29/starter_features.json') if r['year']==2025]
    rows.sort(key=lambda r:(r['date'],r['game_id']));assert len(rows)==9704
    labels={r['game_id']:r for r in map(json.loads,(SOURCE/'native_model_dataset_2026-09-28/dataset/canonical_outcomes.jsonl').read_text().splitlines())}
    joins=read(PRIVATE/'projection-feasibility/private_candidates.json')
    bridge={int(k):v[0] for k,v in read(PRIVATE/'projection-feasibility/slot_bridge_private.json').items()}
    lineage=read(SOURCE/'native_actual_lineup_2026-09-29/lineage.json');lineage={r['game_id']:r for r in lineage}
    later={r['game_id']:r for r in read(SOURCE/'native_2025_comparison_2026-09-29/actual_lineage.json') if r['date'].startswith('2025-')}
    flat=read(SOURCE/'native_2025_comparison_2026-09-29/validation_2025_20260930T000626Z/lineups.json')
    for r in flat:
        if r['game_id'] not in later:continue
        g=r['game_id'];side=r['side'];terms=later[g]['sides'][side]['terms'];match=next(t['matchup'] for t in terms if int(t['player_key'].split('/')[0])==r['bdl_player_id'])
        lineage.setdefault(g,dict(game_id=g,date=later[g]['date'],sides={'home':{'terms':[]},'away':{'terms':[]}}))['sides'][side]['terms'].append(dict(slot=r['slot'],mlb_player_id=r['mlb_player_id'],matchup=match))
    pidset=set();events=[];slotcounts={y:np.zeros(9) for y in [2022,2023,2024]};manifest={}
    for y in [2022,2023,2024,2025]:
        info={r['gid']:r for r in csvrows(RAW/f'{y}gameinfo.csv') if r['gametype']=='regular'}
        available={g:max(day(r['date']),day(r['suspend']) if r['suspend'] else 0) for g,r in info.items()}
        temp=[];nativeg=set(joins[str(y)]['joins'].values())
        for r in csvrows(RAW/f'{y}plays.csv'):
            if r['gid'] not in info:continue
            available[r['gid']]=max(available[r['gid']],day(r['date']))
            if r['pa']!='1':continue
            if y<2025 and r['gid'] in nativeg:slotcounts[y][int(r['lp'])-1]+=1
            n,d=numden(r);assert n>=0 and d>=0
            pidset.add(r['batter']);temp.append((r['gid'],r['batter'],n,d))
        events.extend((available[g],p,n,d) for g,p,n,d in temp)
        for p in RAW.glob(f'{y}*.csv'):manifest[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    ids=sorted(pidset|set(bridge.values()));pm={v:i for i,v in enumerate(ids)}
    releases=collections.defaultdict(list)
    for d,p,n,z in events:releases[d].append((pm[p],n,z))
    proj={};excluded={}
    for y,name in FILES.items():
        p=PROJ/name;manifest[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();forecast={};excluded[y]=0
        for r in csvrows(p):
            if not r['MLBAMID'] or not r['PlayerId']:excluded[y]+=1;continue
            pid=int(float(r['MLBAMID']));assert pid not in forecast;n,d=numden(r,True);assert d>0;forecast[pid]=n/d
        proj[y]=forecast
    controls=np.zeros((len(rows),2,9));forecasts=np.zeros_like(controls);hands=np.zeros_like(controls);fallback=np.zeros_like(controls,dtype=bool);cold=np.zeros_like(controls,dtype=bool)
    targets=collections.defaultdict(list)
    for i,r in enumerate(rows):targets[dt.date.fromisoformat(r['date']).toordinal()].append(i)
    state=np.zeros((len(ids),2));daily={};factor=2**(-1/180)
    for d in range(min(targets),max(targets)+1):
        state*=factor
        if d-1 in releases:
            counts=np.zeros_like(state)
            for p,n,z in releases[d-1]:counts[p]+=[n,z]
            state+=factor*counts;daily[d-1]=counts
        if d-366 in daily:state-=factor**366*daily.pop(d-366)
        assert state.min()>-1e-8;np.maximum(state,0,out=state)
        league=state.sum(axis=0);q=league[0]/league[1] if league[1]>0 else .320
        for i in targets.get(d,[]):
            r=rows[i];g=lineage[r['game_id']];assert g['date']==r['date']
            for s,side in enumerate(['home','away']):
                ts=g['sides'][side]['terms'];assert sorted(t['slot'] for t in ts)==list(range(1,10))
                for t in ts:
                    slot=t['slot']-1;pid=t['mlb_player_id'];n,z=state[pm[bridge[pid]]];control=(n+200*q)/(z+200)
                    controls[i,s,slot]=control;forecasts[i,s,slot]=proj[r['year']].get(pid,control);hands[i,s,slot]=t['matchup'];fallback[i,s,slot]=pid not in proj[r['year']];cold[i,s,slot]=z<1e-10
    base=np.array([[r[n] for n in NAMES] for r in rows]);y=np.array([int(labels[r['game_id']]['home_runs']>labels[r['game_id']]['away_runs']) for r in rows]);years=np.array([r['year'] for r in rows]);dates=np.array([dt.date.fromisoformat(r['date']).toordinal() for r in rows])
    arrays=dict(base=base,y=y,year=years,date=dates,game_id=np.array([r['game_id'] for r in rows]),control=controls,steamer=forecasts,hands=hands,fallback=fallback,cold=cold)
    weights={}
    for outer in [2024,2025]:
        count=sum(slotcounts[z] for z in range(2022,outer));w=count/count.sum();weights[outer]={'counts':count.tolist(),'weights':w.tolist(),'training_years':list(range(2022,outer))}
        for arm,rates in [('control',controls),('steamer',forecasts)]:
            offense=rates@w;hand=hands@w;arrays[f'{arm}_{outer}']=np.column_stack((base,offense[:,0]-offense[:,1],hand[:,0]-hand[:,1]))
    np.savez_compressed(out/'features.npz',**arrays);save(out/'slot_weights.json',weights);save(out/'input_manifest_private.json',manifest)
    save(out/'feature_coverage.json',{str(z):dict(games=int((years==z).sum()),fallback_slots=int(fallback[years==z].sum()),fallback_games=int(fallback[years==z].any(axis=(1,2)).sum()),cold_control_slots=int(cold[years==z].sum()),unidentified_projection_rows=excluded[z]) for z in [2022,2023,2024,2025]})
    print('prepared 9704 games, four confirmed projection vintages',flush=True)

def fit(out):
    a=dict(np.load(out/'features.npz'));predictions=[];replays={}
    for year in [2024,2025]:
        train=a['year']<year;test=a['year']==year;pred={}
        for arm in ['control','steamer']:
            x=a[f'{arm}_{year}'];scaler=StandardScaler();tx=scaler.fit_transform(x[train]);model=LogisticRegression(**SETTINGS)
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning);model.fit(tx,a['y'][train])
            p=model.predict_proba(scaler.transform(x[test]))[:,1];saved=dict(coef=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),iterations=int(model.n_iter_[0]),train_games=int(train.sum()),settings=SETTINGS)
            save(out/f'{arm}_{year}_model.json',saved);manual=expit((x[test]-scaler.mean_)/scaler.scale_@model.coef_[0]+model.intercept_[0]);delta=float(np.abs(p-manual).max());assert delta<1e-12;replays[f'{arm}_{year}']=delta;pred[arm]=p
        native_dir,native_key=('native_starter_2026-09-28','starter') if year==2024 else ('native_2025_retraining_2026-09-29','new_starter')
        native={r['game_id']:r for r in read(SOURCE/native_dir/'predictions.json')};book={r['game_id']:r for r in map(json.loads,(SOURCE/f'historical_opening_odds_2026-09-28/season_{year}/derived/consensus.jsonl').read_text().splitlines())}
        for j,i in enumerate(np.flatnonzero(test)):
            gid=int(a['game_id'][i]);assert native[gid]['home_win']==int(a['y'][i]);b=book[gid];predictions.append(dict(game_id=gid,year=year,date=dt.date.fromordinal(int(a['date'][i])).isoformat(),home_win=int(a['y'][i]),control=float(pred['control'][j]),steamer=float(pred['steamer'][j]),native=native[gid][native_key],sportsbook=b['opening_consensus_home'] if b['native_comparison_eligible'] else None,fallback=bool(a['fallback'][i].any()),cold=bool(a['cold'][i].any())))
        print('fit',year,int(train.sum()),int(test.sum()),flush=True)
    save(out/'predictions_private.json',predictions);save(out/'probability_replay.json',replays)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','fit']);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=True);prepare(a.output) if a.stage=='prepare' else fit(a.output)
