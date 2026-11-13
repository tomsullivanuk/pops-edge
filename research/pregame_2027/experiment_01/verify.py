"""Read-only verification of saved measurements, lineage and independent solver."""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path
import numpy as np
from run import load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--replay', type=Path, required=True)
    a = ap.parse_args()
    read = lambda p: json.loads(p.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    names = ['reference_replay.json', 'reference_models.json', 'rating_lineage.json',
             'models.json', 'predictions.json', 'results.json', 'provenance.json']
    for n in names:
        assert (a.output/n).read_bytes() == (a.replay/n).read_bytes(), n
    predictions, result = read(a.output/'predictions.json'), read(a.output/'results.json')
    rows, labels, outcomes = load(a.source_root)
    expected_ids = {r['game_id'] for r in rows if r['year'] >= 2024}
    assert len(predictions) == len({r['game_id'] for r in predictions}) == len(expected_ids) == 7280
    assert {r['game_id'] for r in predictions} == expected_ids
    models = read(a.output/'models.json')
    lineage = read(a.output/'rating_lineage.json')
    by_date = {(d['year'], d['date']): d for d in lineage}
    for d in lineage:
        history = [g for g in outcomes if d['year']-1 <= g['year'] <= d['year'] and g['available_day'] < d['date']]
        assert sorted(g['game_id'] for g in history) == d['history_game_ids']
        assert all(g['valid'] and not g['issues'] for g in history)
        assert d['maximum_available_day'] < d['date']
        assert abs(math.fsum(d['ratings'].values())) < 1e-10
    feature_rows = {r['game_id']:r for r in rows}
    maximum_probability_difference = 0.
    for p in predictions:
        assert p['home_win'] == labels[p['game_id']]
        row = feature_rows[p['game_id']]
        d = by_date[(row['year'], row['date'])]
        assert row['game_id'] not in d['history_game_ids']
        row = dict(row, rating_difference=d['ratings'][str(row['home'])]-d['ratings'][str(row['away'])])
        m = models[str(row['year'])]
        eta = m['intercept'] + math.fsum((row[k]-mu)/scale*coef for k,mu,scale,coef in zip(m['features'],m['scaler_mean'],m['scaler_scale'],m['coefficients']))
        rebuilt = 1/(1+math.exp(-eta))
        maximum_probability_difference = max(maximum_probability_difference,abs(rebuilt-p['challenger']))
    assert maximum_probability_difference < 1e-14
    for year in [2024, 2025, 2026]:
        sub = [p for p in predictions if p['year']==year]
        for name in ['reference','challenger']:
            brier=math.fsum((p[name]-p['home_win'])**2 for p in sub)/len(sub)
            ll=math.fsum(-p['home_win']*math.log(p[name])-(1-p['home_win'])*math.log1p(-p[name]) for p in sub)/len(sub)
            assert abs(brier-result['annual'][str(year)][name]['brier'])<1e-14
            assert abs(ll-result['annual'][str(year)][name]['log_loss'])<1e-14
    # Outcome-blind validation dates: first/middle/last available rating date in each year.
    selected=[]
    for year in range(2022,2027):
        days=[d for d in lineage if d['year']==year]
        selected += [days[0],days[len(days)//2],days[-1]]
    teams=sorted({g[s] for g in outcomes for s in ['home','away']})
    index={t:i for i,t in enumerate(teams)}
    maximum_rating_difference=0.
    for d in selected:
        history=[g for g in outcomes if d['year']-1<=g['year']<=d['year'] and g['available_day']<d['date']]
        x=np.zeros((len(history),31)); y=[];w=[]
        for i,g in enumerate(history):
            x[i,index[g['home']]]=1.; x[i,index[g['away']]]=-1.; x[i,-1]=float(not g['neutral'])
            y.append(g['home_runs']-g['away_runs'])
            age=(date.fromisoformat(d['date'])-date.fromisoformat(g['available_day'])).days
            w.append(2**(-age/60)*(.5 if g['year']<d['year'] else 1.))
        square=np.sqrt(w)
        penalty=np.zeros((30,31));penalty[:,:30]=np.eye(30)*math.sqrt(20)
        matrix=np.vstack([x*square[:,None],penalty]);target=np.r_[np.array(y)*square,np.zeros(30)]
        independent=np.linalg.lstsq(matrix,target,rcond=None)[0]
        retained=np.array([d['ratings'][str(t)] for t in teams]+[d['home_advantage']])
        maximum_rating_difference=max(maximum_rating_difference,float(max(abs(independent-retained))))
    assert maximum_rating_difference<1e-10
    gain=math.fsum(result['annual'][str(y)]['reference']['brier']-result['annual'][str(y)]['challenger']['brier'] for y in [2024,2025,2026])/3
    assert abs(gain-result['equal_weight_annual_brier_gain'])<1e-14
    assert gain<.001 and not result['continuation_gate_passed']
    verification=dict(exact_replay_files={n:sha(a.output/n) for n in names},
                      annual_scores_independently_recomputed=True, unique_paired_games=7280,
                      lineage_days_checked=len(lineage), independent_rating_solver_dates=len(selected),
                      maximum_independent_rating_difference=maximum_rating_difference,
                      maximum_probability_reconstruction_difference=maximum_probability_difference,
                      reused_seasons_not_fresh_holdouts=True, gate_failed=True,
                      full_raw_player_feature_rebuild_performed=False)
    (a.output/'verification.json').write_text(json.dumps(verification,sort_keys=True,indent=2)+'\n')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    main()
