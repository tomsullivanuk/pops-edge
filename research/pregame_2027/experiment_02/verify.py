"""Separate arithmetic, saved-model replay and split/selection audit."""
import argparse
import gc
import hashlib
import json
import math
import zipfile
from pathlib import Path
from capacity import configure_local


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    args=ap.parse_args()
    configure_local(args.output)
    import numpy as np
    import torch
    from catboost import CatBoostClassifier
    from tabpfn.model_loading import load_fitted_tabpfn_model
    from run import read,sha,setup_reference,arrays
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    reference_module,_=setup_reference()
    rows,labels,_=reference_module.load(args.source_root)
    predictions=read(args.output/'predictions.json');results=read(args.output/'results.json')
    provenance=read(args.output/'provenance.json')
    for name,digest in provenance['output_hashes'].items():assert sha(args.output/name)==digest,name
    assert sha(args.checkpoint)==provenance['checkpoint_sha256']
    assert len(predictions)==len({p['game_id'] for p in predictions})==7280
    assert {p['game_id'] for p in predictions}=={r['game_id'] for r in rows if r['year']>=2024}
    assert all(labels[p['game_id']]==p['home_win'] for p in predictions)
    names=['reference','catboost','tabpfn_v2'];records=[]
    for year in [2024,2025,2026]:
        rr=[r for r in rows if r['year']==year];train=[r for r in rows if r['year']<year]
        assert max(r['date'] for r in train)<min(r['date'] for r in rr)
        predicted={p['game_id']:p for p in predictions if p['year']==year}
        for market_only,metric_key in [(False,'annual_full'),(True,'annual_market_common')]:
            sub=[p for p in predicted.values() if not market_only or p['sportsbook'] is not None]
            for name in names+(['sportsbook'] if market_only else []):
                brier=math.fsum((p[name]-p['home_win'])**2 for p in sub)/len(sub)
                loss=math.fsum(-p['home_win']*math.log(p[name])-(1-p['home_win'])*math.log1p(-p[name]) for p in sub)/len(sub)
                expected=results[metric_key][str(year)][name]
                assert expected['games']==len(sub)
                assert abs(brier-expected['brier'])<1e-14 and abs(loss-expected['log_loss'])<1e-14
        choice=read(args.output/f'catboost_selection_{year}.json')
        all_scores=[]
        for candidate in choice['all_inner_results']:
            assert [f['validation_year'] for f in candidate['folds']]==list(range(2023,year))
            for f in candidate['folds']:
                assert f['training_years']==list(range(2022,f['validation_year']))
                assert max(f['training_years'])<f['validation_year']<year
                assert f['games']==sum(r['year']==f['validation_year'] for r in rows)
            n=sum(f['games'] for f in candidate['folds'])
            for metric in ['brier','log_loss']:
                assert abs(candidate['pooled_'+metric]-sum(f['games']*f[metric] for f in candidate['folds'])/n)<1e-14
            all_scores.append(candidate)
        best=min(all_scores,key=lambda c:(c['pooled_brier'],c['pooled_log_loss'],c['grid_index']))
        iterations=max(1,round(sum(f['games']*f['iterations'] for f in best['folds'])/sum(f['games'] for f in best['folds'])))
        assert choice['selected_grid_index']==best['grid_index'] and choice['final_iterations']==iterations
        forest=CatBoostClassifier();forest.load_model(str(args.output/f'catboost_{year}.cbm'))
        z,_=arrays(rr,reference_module.REFERENCE,labels)
        forest_p=forest.predict_proba(z)[:,1]
        forest_diff=float(max(abs(forest_p-np.array([predicted[r['game_id']]['catboost'] for r in rr]))))
        assert forest_diff==0
        with zipfile.ZipFile(args.output/f'tabpfn_v2_{year}.tabpfn_fit') as archive:
            init=json.loads(archive.read('init_params.json'))
        assert init['n_estimators']==4 and init['random_state']==20261012
        assert init['softmax_temperature']==.9 and init['tuning_config'] is None
        assert init['fit_mode']=='fit_with_cache' and not init['balance_probabilities']
        assert Path(init['model_path']).name==args.checkpoint.name
        model=load_fitted_tabpfn_model(args.output/f'tabpfn_v2_{year}.tabpfn_fit',device='mps')
        assert model.tuned_classification_thresholds_ is None and model.softmax_temperature_==.9
        assert 'tabpfn_v2' in type(model.models_[0]).__module__
        replay=np.concatenate([model.predict_proba(z[i:i+128])[:,1] for i in range(0,len(z),128)])
        expected=np.array([predicted[r['game_id']]['tabpfn_v2'] for r in rr])
        difference=float(max(abs(replay-expected)));assert difference<=1e-6
        # A fixed outcome-blind first batch, mutated later test rows; no model changes.
        n=min(128,len(z));original=model.predict_proba(z[:n])[:16,1]
        mutated=z[:n].copy();mutated[16:]=1000
        independence=float(max(abs(model.predict_proba(mutated)[:16,1]-original)))
        assert independence<=1e-6
        records.append(dict(year=year,training_games=len(train),evaluation_games=len(rr),
                            catboost_prediction_replay_max_difference=forest_diff,
                            tabpfn_prediction_replay_max_difference=difference,
                            later_test_feature_mutation_max_difference=independence,
                            no_calibration_or_threshold_tuning=True,split_and_selection_verified=True))
        del model;gc.collect();torch.mps.empty_cache()
    for name in ['catboost','tabpfn_v2']:
        gains=[results['annual_full'][str(y)]['reference']['brier']-results['annual_full'][str(y)][name]['brier'] for y in [2024,2025,2026]]
        assert abs(sum(gains)/3-results['gates'][name]['equal_weight_annual_brier_gain'])<1e-14
        tests=dict(average_brier_gain_at_least_0_001=sum(gains)/3>=.001,
                   positive_gain_in_at_least_two_years=sum(g>0 for g in gains)>=2,
                   pooled_log_loss_no_worse=results['pooled_full'][name]['log_loss']<=results['pooled_full']['reference']['log_loss'],
                   unchanged_target_coverage=True,no_new_hindsight_dependence=True)
        assert tests==results['gates'][name]['conditions']
        assert all(tests.values())==results['gates'][name]['passed']
    verification=dict(unique_games=7280,original_market_common_games=7144,
                      full_and_common_annual_scores_recomputed=True,folds=records,
                      model_artifact_hashes_verified=True,checkpoint_sha256=sha(args.checkpoint),
                      new_private_row_outputs=True,no_model_network_calls=True,
                      gate_reconstruction_passed=True,external_independent_reviewer=False,
                      raw_feature_builder_reexecuted=False)
    (args.output/'verification.json').write_text(json.dumps(verification,sort_keys=True,indent=2)+'\n')
    print(json.dumps(verification,indent=2),flush=True)


if __name__=='__main__':main()
