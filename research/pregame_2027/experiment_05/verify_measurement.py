"""Independent per-game bootstrap weights, pooled scores and calibration equations."""
import argparse
import json
import math
from datetime import date
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    read=lambda p:json.loads(p.read_text())
    rows=read(a.output/'predictions.json');result=read(a.output/'results.json')
    maximum_bootstrap_error=0.;maximum_calibration_residual=0.
    for common in [False,True]:
        population=[r for r in rows if not common or r['sportsbook'] is not None]
        names=['reference','catboost','tabpfn_v2','tabpfn_v35']+(['sportsbook'] if common else [])
        expected=result['pooled_market_common' if common else 'pooled_full']
        for n in names:
            brier=math.fsum((r[n]-r['home_win'])**2 for r in population)/len(population)
            ll=math.fsum(-r['home_win']*math.log(r[n])-(1-r['home_win'])*math.log1p(-r[n]) for r in population)/len(population)
            assert abs(brier-expected[n]['brier'])<1e-14 and abs(ll-expected[n]['log_loss'])<1e-14
        for year in [2024,2025,2026]:
            sub=[r for r in population if r['year']==year]
            calibration=result['calibration_market_common' if common else 'calibration_full'][str(year)]
            for n in names:
                c=calibration[n];intercept,slope=c['intercept'],c['slope']
                residual=[];weighted=[]
                for r in sub:
                    z=math.log(r[n]/(1-r[n]));p=1/(1+math.exp(-intercept-slope*z))
                    residual.append(p-r['home_win']);weighted.append((p-r['home_win'])*z)
                error=max(abs(math.fsum(residual)),abs(math.fsum(weighted)))
                maximum_calibration_residual=max(maximum_calibration_residual,error)
                assert error<1e-6
        for length in [14,7]:
            target=result['bootstrap_market_common' if common else 'bootstrap_full'][str(length)]
            keys=sorted(target['equal_weight_annual'])
            rng=np.random.default_rng(20261012);yearly=[]
            for year in [2024,2025,2026]:
                sub=[r for r in population if r['year']==year]
                first=date.fromisoformat(min(r['date'] for r in sub));last=date.fromisoformat(max(r['date'] for r in sub));days=(last-first).days+1
                game_days=np.array([(date.fromisoformat(r['date'])-first).days for r in sub])
                y=np.array([r['home_win'] for r in sub]);deltas=[]
                for key in keys:
                    n1,n2=key.split('_minus_')
                    p1=np.array([r[n1] for r in sub]);p2=np.array([r[n2] for r in sub])
                    deltas.extend([(p1-y)**2-(p2-y)**2,
                                   -y*np.log(p1)-(1-y)*np.log1p(-p1)+y*np.log(p2)+(1-y)*np.log1p(-p2)])
                deltas=np.array(deltas).T
                # Different aggregation from runner: sampled day multiplicities are
                # applied to each individual game, not daily loss sums.
                weights=np.empty((5000,len(sub)),dtype=np.int16)
                for rep in range(5000):
                    starts=rng.integers(0,days-length+1,size=math.ceil(days/length))
                    chosen=(starts[:,None]+np.arange(length)).ravel()[:days]
                    multiples=np.bincount(chosen,minlength=days)
                    weights[rep]=multiples[game_days]
                totals=weights.sum(axis=1);assert (totals>0).all()
                draws=(weights.astype(float)@deltas)/totals[:,None]
                yearly.append(draws)
                for i,key in enumerate(keys):
                    for j,metric in enumerate(['brier','log_loss']):
                        actual=target['annual'][str(year)][key][metric]
                        values=draws[:,2*i+j]
                        for boundary,q in [('lower',.025),('upper',.975)]:
                            err=abs(float(np.quantile(values,q))-actual[boundary]);maximum_bootstrap_error=max(maximum_bootstrap_error,err);assert err<1e-12
            average=np.mean(yearly,axis=0)
            for i,key in enumerate(keys):
                for j,metric in enumerate(['brier','log_loss']):
                    for boundary,q in [('lower',.025),('upper',.975)]:
                        err=abs(float(np.quantile(average[:,2*i+j],q))-target['equal_weight_annual'][key][metric][boundary]);maximum_bootstrap_error=max(maximum_bootstrap_error,err);assert err<1e-12
    receipt=dict(pooled_scores_independently_verified=True,
                 bootstrap_all_5000_replicates_independently_reweighted_by_game=True,
                 maximum_bootstrap_bound_difference=maximum_bootstrap_error,
                 maximum_calibration_score_equation_residual=maximum_calibration_residual,
                 calibration_score_equations_verified=True)
    (a.output/'measurement_verification.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
