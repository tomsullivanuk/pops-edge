"""Frozen no-fit batting-information and saved-model accounting diagnostic."""
import csv,json,math,datetime as dt,collections,importlib.util
from pathlib import Path
import numpy as np
from scipy.special import expit,logit
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('existing',ROOT/'experiment_04/run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def main(out):
    data=dict(np.load(old.PRIVATE/'experiment-04/features.npz'));saved=old.read(old.PRIVATE/'experiment-04/predictions_private.json');saved={r['game_id']:r for r in saved}
    joins=old.read(old.PRIVATE/'projection-feasibility/private_candidates.json');weights=old.read(old.PRIVATE/'experiment-04/slot_weights.json')
    lineage={r['game_id']:r for r in old.read(old.SOURCE/'native_actual_lineup_2026-09-29/lineage.json')};lineage.update({r['game_id']:r for r in old.read(old.PRIVATE/'projection-feasibility/lineage_2025_private.json')})
    bridge={int(k):v[0] for k,v in old.read(old.PRIVATE/'projection-feasibility/slot_bridge_private.json').items()}
    tables={};coverage={};traces=[];event_private=[];hitter_private=[];side_private=[]
    for year in [2024,2025]:
        idx=np.flatnonzero(data['year']==year);slotmap={};players={};bygame={};counts=collections.Counter()
        info={r['gid']:r for r in old.csvrows(old.RAW/f'{year}gameinfo.csv')};w=np.array(weights[str(year)]['weights'])
        for i in idx:
            pk=int(data['game_id'][i]);gid=joins[str(year)]['joins'][str(pk)];meta=info[gid];h,v=(meta['visteam'],meta['hometeam']) if meta['htbf']=='true' else (meta['hometeam'],meta['visteam']);bygame[gid]=i
            for side,team in [(0,h),(1,v)]:
                key='home' if side==0 else 'away'
                for t in lineage[pk]['sides'][key]['terms']:
                    s=t['slot']-1;rid=bridge[t['mlb_player_id']];assert (gid,team,rid) not in slotmap;slotmap[(gid,team,rid)]=(i,side,s);players[(i,side,s)]=[0.,0.,0.]
        eventrows=[]
        for ordinal,r in enumerate(old.csvrows(old.RAW/f'{year}plays.csv'),1):
            if r['gid'] not in bygame:continue
            if r['pa']!='1':counts['non_PA_rows']+=1;continue
            key=(r['gid'],r['batteam'],r['batter'])
            if key not in slotmap:counts['substitute_PA']+=1;continue
            i,side,s=slotmap[key];n,d=old.numden(r);assert d in [0,1] and n>=0
            if d==0:
                assert n==0;counts['zero_denominator_PA']+=1
                for f in ['iw','sh','xi']:counts[f+'_zero_denominator']+=int(r[f] or 0)
                continue
            counts['eligible_initial_PA']+=1;c=float(data['control'][i,side,s]);p=float(data['steamer'][i,side,s]);eventrows.append((int(data['date'][i]),(c-n)**2,(p-n)**2));event_private.append(dict(year=year,game_id=int(data['game_id'][i]),source_row=ordinal,side=side,slot=s+1,observed=n,control=c,steamer=p));players[(i,side,s)][0]+=n;players[(i,side,s)][1]+=d;players[(i,side,s)][2]+=1
        hitterrows=[];siderows=[]
        for (i,side,s),(n,d,_) in players.items():
            if not d:counts['initial_hitter_games_zero_opportunity']+=1;continue
            actual=n/d;c=float(data['control'][i,side,s]);p=float(data['steamer'][i,side,s]);hitterrows.append((int(data['date'][i]),(c-actual)**2,(p-actual)**2));hitter_private.append(dict(year=year,game_id=int(data['game_id'][i]),side=side,slot=s+1,numerator=n,denominator=d,actual_mean=actual,control=c,steamer=p))
        for i in idx:
            for side in [0,1]:
                obs=[players[(i,side,s)] for s in range(9)]
                if any(d==0 for n,d,_ in obs):counts['side_aggregation_incomplete']+=1;continue
                actual=sum(w[s]*n/d for s,(n,d,_) in enumerate(obs));c=float(data['control'][i,side]@w);p=float(data['steamer'][i,side]@w);siderows.append((int(data['date'][i]),(c-actual)**2,(p-actual)**2));side_private.append(dict(year=year,game_id=int(data['game_id'][i]),side=side,actual_weighted_mean=actual,control=c,steamer=p))
        counts['scored_hitter_games']=len(hitterrows);counts['scored_complete_sides']=len(siderows);coverage[year]=dict(counts);tables[year]={'opportunity':eventrows,'hitter_game':hitterrows,'complete_side':siderows}
        cmod=old.read(old.PRIVATE/f'experiment-04/control_{year}_model.json');smod=old.read(old.PRIVATE/f'experiment-04/steamer_{year}_model.json');bc=np.array(cmod['coef'])/cmod['scale'];bs=np.array(smod['coef'])/smod['scale'];ac=cmod['intercept']-bc@cmod['mean'];ass=smod['intercept']-bs@smod['mean']
        for i in idx:
            pk=int(data['game_id'][i]);xc=data[f'control_{year}'][i];xs=data[f'steamer_{year}'][i];assert np.max(np.abs(xc[:10]-xs[:10]))==0 and xc[-1]==xs[-1]
            oc=float(data['control'][i,0]@w-data['control'][i,1]@w);os=float(data['steamer'][i,0]@w-data['steamer'][i,1]@w);assert abs(oc-xc[10])<1e-14 and abs(os-xs[10])<1e-14
            ec=ac+bc@xc;es=ass+bs@xs;assert abs(expit(ec)-saved[pk]['control'])<1e-12 and abs(expit(es)-saved[pk]['steamer'])<1e-12
            dat=bc[10]*(os-oc);coef=ass-ac+(bs-bc)@xs;assert abs(dat+coef-(es-ec))<1e-12
            traces.append(dict(year=year,game_id=pk,control_offense=oc,steamer_offense=os,control_logit=float(ec),steamer_logit=float(es),data_logit_change=float(dat),coefficient_logit_change=float(coef),probability_change=saved[pk]['steamer']-saved[pk]['control'],slot_contributions_control=(data['control'][i]*w).tolist(),slot_contributions_steamer=(data['steamer'][i]*w).tolist()))
    # Comparability checks all pass before publishing comparative scores.
    result={'coverage':coverage,'annual':{},'uncertainty':{},'trace':{}}
    for year,pops in tables.items():
        result['annual'][year]={k:dict(units=len(rr),control_mean_squared_error=float(np.mean([r[1] for r in rr])),steamer_mean_squared_error=float(np.mean([r[2] for r in rr])),gain=float(np.mean([r[1]-r[2] for r in rr]))) for k,rr in pops.items()}
        rr=[r for r in traces if r['year']==year];result['trace'][year]=dict(games=len(rr),mean_absolute_probability_change=float(np.mean([abs(r['probability_change']) for r in rr])),mean_data_logit_change=float(np.mean([r['data_logit_change'] for r in rr])),mean_absolute_data_logit_change=float(np.mean([abs(r['data_logit_change']) for r in rr])),mean_coefficient_logit_change=float(np.mean([r['coefficient_logit_change'] for r in rr])),mean_absolute_coefficient_logit_change=float(np.mean([abs(r['coefficient_logit_change']) for r in rr])),mean_absolute_lineup_offense_change=float(np.mean([abs(r['steamer_offense']-r['control_offense']) for r in rr])))
    result['equal_year']={k:{metric:float(np.mean([result['annual'][y][k][metric] for y in [2024,2025]])) for metric in ['control_mean_squared_error','steamer_mean_squared_error','gain']} for k in tables[2024]}
    for pop in tables[2024]:
        result['uncertainty'][pop]={}
        for block in [14,7]:
            rng=np.random.default_rng(20261012);draws=[]
            for year in [2024,2025]:
                rr=tables[year][pop];days=np.array([r[0] for r in rr]);L=int(days.max()-days.min()+1);ix=days-days.min();counts=np.bincount(ix,minlength=L);sums=np.bincount(ix,weights=[r[1]-r[2] for r in rr],minlength=L);annual=[]
                for _ in range(5000):
                    idx=(rng.integers(0,L-block+1,size=math.ceil(L/block))[:,None]+np.arange(block)).ravel()[:L];annual.append(float(sums[idx].sum()/counts[idx].sum()))
                draws.append(annual)
            result['uncertainty'][pop][block]={'annual':{y:np.quantile(a,[.025,.975]).tolist() for y,a in zip([2024,2025],draws)},'equal_year':np.quantile(np.mean(draws,axis=0),[.025,.975]).tolist()}
    old.save(out/'results.json',result);old.save(out/'events_private.json',event_private);old.save(out/'hitters_private.json',hitter_private);old.save(out/'sides_private.json',side_private);old.save(out/'traces_private.json',traces)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    import sys;main(Path(sys.argv[1]))
