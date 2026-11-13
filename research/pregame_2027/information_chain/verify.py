"""Independent raw-event definition, scalar score, trace and block verification."""
import csv,json,math,hashlib,datetime as dt
from pathlib import Path
import numpy as np
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[1]
BASE=Path('/Users/tom/Documents/Codex/2026-10-12/task')
RAW=BASE/'experiment-03/raw'

def main(out):
    result=json.loads((out/'results.json').read_text());events=json.loads((out/'events_private.json').read_text());hitters=json.loads((out/'hitters_private.json').read_text());sides=json.loads((out/'sides_private.json').read_text());traces=json.loads((out/'traces_private.json').read_text());features=dict(np.load(BASE/'experiment-04/features.npz'))
    pins=json.loads((ROOT/'experiment_04/input_manifest.json').read_text());hashes={}
    for year in [2024,2025]:
        name=f'{year}plays.csv';digest=hashlib.sha256((RAW/name).read_bytes()).hexdigest();assert digest==pins[name];hashes[name]=digest
    event_map={(r['year'],r['source_row']):r for r in events};assert len(event_map)==len(events);aggregate={};checked=0;max_observed_error=0
    for year in [2024,2025]:
        with (RAW/f'{year}plays.csv').open(newline='') as f:
            for ordinal,row in enumerate(csv.DictReader(f),1):
                if (year,ordinal) not in event_map:continue
                r=event_map[(year,ordinal)];v=lambda k:int(row[k] or 0)
                assert row['pa']=='1' and sum(v(k) for k in ['single','double','triple','hr','sh','sf','hbp','walk','k','xi','roe','fc','othout','noout'])==1
                assert v('iw')==0 and v('ab')+v('walk')+v('sf')+v('hbp')==1
                values={'single':.888,'double':1.271,'triple':1.616,'hr':2.101,'hbp':.722,'walk':.690};actual=sum(v(k)*value for k,value in values.items());assert actual==r['observed'];checked+=1
                key=(year,r['game_id'],r['side'],r['slot']);aggregate.setdefault(key,[]).append(actual)
    for r in hitters:
        values=aggregate[(r['year'],r['game_id'],r['side'],r['slot'])];assert len(values)==r['denominator'];assert abs(math.fsum(values)-r['numerator'])<1e-12
    score_error=0.;tables={'opportunity':events,'hitter_game':hitters,'complete_side':sides}
    for pop,allrows in tables.items():
        for year in [2024,2025]:
            rr=[r for r in allrows if r['year']==year];key='observed' if pop=='opportunity' else 'actual_mean' if pop=='hitter_game' else 'actual_weighted_mean';record=result['annual'][str(year)][pop]
            for arm in ['control','steamer']:
                score=math.fsum((r[arm]-r[key])**2 for r in rr)/len(rr);error=abs(score-record[arm+'_mean_squared_error']);score_error=max(score_error,error);assert error<1e-12
    trace_error=0.;prob_error=0.
    for year in [2024,2025]:
        cm=json.loads((BASE/f'experiment-04/control_{year}_model.json').read_text());sm=json.loads((BASE/f'experiment-04/steamer_{year}_model.json').read_text());w=json.loads((BASE/'experiment-04/slot_weights.json').read_text())[str(year)]['weights'];lookup={int(g):i for i,g in enumerate(features['game_id'])}
        for r in [r for r in traces if r['year']==year]:
            i=lookup[r['game_id']]
            for arm,model in [('control',cm),('steamer',sm)]:
                x=features[f'{arm}_{year}'][i];eta=model['intercept']+math.fsum(model['coef'][j]*(x[j]-model['mean'][j])/model['scale'][j] for j in range(12));trace_error=max(trace_error,abs(eta-r[arm+'_logit']));assert abs(eta-r[arm+'_logit'])<1e-12
                contributions=features[arm][i]*np.array(w);assert np.max(np.abs(contributions-r['slot_contributions_'+arm]))<1e-14
            total=r['data_logit_change']+r['coefficient_logit_change'];assert abs(total-(r['steamer_logit']-r['control_logit']))<1e-12
            pchange=float(expit(r['steamer_logit'])-expit(r['control_logit']));prob_error=max(prob_error,abs(pchange-r['probability_change']));assert abs(pchange-r['probability_change'])<1e-12
    intervals={}
    for pop,allrows in tables.items():
        key='observed' if pop=='opportunity' else 'actual_mean' if pop=='hitter_game' else 'actual_weighted_mean'
        for block in [14,7]:
            rng=np.random.default_rng(20261012);draws=[]
            for year in [2024,2025]:
                rr=[r for r in allrows if r['year']==year];dates=np.array([features['date'][np.flatnonzero(features['game_id']==r['game_id'])[0]] for r in rr]) if pop!='opportunity' else None
                if dates is None:
                    byid={int(g):int(d) for g,d in zip(features['game_id'],features['date'])};dates=np.array([byid[r['game_id']] for r in rr])
                L=int(dates.max()-dates.min()+1);ix=dates-dates.min();counts=np.bincount(ix,minlength=L);c=np.bincount(ix,weights=[(r['control']-r[key])**2 for r in rr],minlength=L);s=np.bincount(ix,weights=[(r['steamer']-r[key])**2 for r in rr],minlength=L);annual=[]
                for _ in range(5000):
                    weights=np.zeros(L);left=L
                    for start in rng.integers(0,L-block+1,size=math.ceil(L/block)):
                        size=min(block,left);weights[start:start+size]+=1;left-=size
                    annual.append(float(np.dot(weights,c-s)/np.dot(weights,counts)))
                draws.append(annual)
            interval=np.quantile(np.mean(draws,axis=0),[.025,.975]);expected=result['uncertainty'][pop][str(block)]['equal_year'];delta=float(np.max(np.abs(interval-expected)));assert delta<1e-12;intervals[f'{pop}_{block}']=delta
    verification=dict(raw_event_values_verified=checked,source_hashes=hashes,duplicate_event_keys=0,hitter_totals_reconciled=len(hitters),scalar_score_max_difference=score_error,saved_trace_max_logit_difference=trace_error,saved_trace_probability_change_difference=prob_error,bootstrap_interval_max_differences=intervals,no_new_model_fits=True,scope='same-assistant independent raw-event/scalar/trace/multiplicity-weight checks; not external review')
    (out/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print(verification)

if __name__=='__main__':
    import sys;main(Path(sys.argv[1]))
