"""Frozen local v2/CatBoost comparison. Raw inputs and predictions stay private."""
import argparse
import hashlib
import importlib.util
import json
import math
import resource
import signal
import sys
import time
from datetime import date
from pathlib import Path

from capacity import configure_local, v2_classifier

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    assert not path.exists(), f'Existing output: {path.name}; use a new run directory'
    path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')


def setup_reference():
    path = HERE.parent / 'experiment_01/run.py'
    spec = importlib.util.spec_from_file_location('experiment_01_reference', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sha(path)


def arrays(rows, names, labels):
    import numpy as np
    x = np.array([[r[k] for k in names] for r in rows])
    y = np.array([labels[r['game_id']] for r in rows])
    assert x.shape == (len(rows),10) and np.isfinite(x).all()
    return x,y


def boosting(train, year, names, labels, settings, output):
    import numpy as np
    from catboost import CatBoostClassifier
    conf = settings['catboost']
    common = {k:conf[k] for k in ['random_seed','thread_count','loss_function','eval_metric',
                                  'task_type','bootstrap_type','subsample','random_strength','boosting_type']}
    common.update(verbose=False,allow_writing_files=False)
    records=[]
    for index, parameters in enumerate(conf['grid']):
        folds=[]
        for validation_year in range(2023,year):
            before=[r for r in train if r['year']<validation_year]
            held=[r for r in train if r['year']==validation_year]
            assert max(r['year'] for r in before)<validation_year<year
            assert max(r['date'] for r in before)<min(r['date'] for r in held)
            x,y=arrays(before,names,labels);z,v=arrays(held,names,labels)
            model=CatBoostClassifier(**common,**parameters,iterations=conf['max_iterations'])
            model.fit(x,y,eval_set=(z,v),early_stopping_rounds=conf['early_stopping_rounds'],use_best_model=True)
            p=model.predict_proba(z)[:,1]
            assert ((p>0)&(p<1)).all()
            folds.append(dict(validation_year=validation_year,training_years=sorted({r['year'] for r in before}),
                              games=len(held),brier=float(np.mean((p-v)**2)),
                              log_loss=float(np.mean(-v*np.log(p)-(1-v)*np.log1p(-p))),
                              iterations=int(model.tree_count_)))
        count=sum(f['games'] for f in folds)
        records.append(dict(grid_index=index,parameters=parameters,folds=folds,
                            pooled_brier=sum(f['games']*f['brier'] for f in folds)/count,
                            pooled_log_loss=sum(f['games']*f['log_loss'] for f in folds)/count))
    selected=min(records,key=lambda r:(r['pooled_brier'],r['pooled_log_loss'],r['grid_index']))
    rounds=max(1,round(sum(f['games']*f['iterations'] for f in selected['folds'])/sum(f['games'] for f in selected['folds'])))
    model=CatBoostClassifier(**common,**selected['parameters'],iterations=rounds)
    x,y=arrays(train,names,labels)
    model.fit(x,y)  # No outer-year eval_set or early stopping.
    model.save_model(str(output/f'catboost_{year}.cbm'))
    receipt=dict(outer_year=year,training_years=sorted({r['year'] for r in train}),
                 selected_grid_index=selected['grid_index'],final_iterations=rounds,
                 selected_parameters=selected['parameters'],all_inner_results=records,
                 outer_evaluation_used_in_selection=False)
    save(output/f'catboost_selection_{year}.json',receipt)
    return model,receipt


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


def summarize(predictions,reference_module):
    full_names=['reference','catboost','tabpfn_v2']
    common=[r for r in predictions if r['sportsbook'] is not None]
    assert [sum(r['year']==y for r in common) for y in [2024,2025,2026]]==[2291,2425,2428]
    annual={str(y):{n:metrics([r for r in predictions if r['year']==y],n) for n in full_names} for y in [2024,2025,2026]}
    market_annual={str(y):{n:metrics([r for r in common if r['year']==y],n) for n in full_names+['sportsbook']} for y in [2024,2025,2026]}
    pooled={n:metrics(predictions,n) for n in full_names}
    gates={}
    for n in ['catboost','tabpfn_v2']:
        gains={str(y):annual[str(y)]['reference']['brier']-annual[str(y)][n]['brier'] for y in [2024,2025,2026]}
        avg=sum(gains.values())/3
        tests=dict(average_brier_gain_at_least_0_001=avg>=.001,
                   positive_gain_in_at_least_two_years=sum(v>0 for v in gains.values())>=2,
                   pooled_log_loss_no_worse=pooled[n]['log_loss']<=pooled['reference']['log_loss'],
                   unchanged_target_coverage=len(predictions)==7280,no_new_hindsight_dependence=True)
        gates[n]=dict(annual_brier_gains=gains,equal_weight_annual_brier_gain=avg,
                      conditions=tests,passed=all(tests.values()))
    full_pairs=[('reference','catboost'),('reference','tabpfn_v2'),('catboost','tabpfn_v2')]
    common_pairs=full_pairs+[('sportsbook','reference'),('sportsbook','catboost'),('sportsbook','tabpfn_v2')]
    return dict(annual_full=annual,annual_market_common=market_annual,
                pooled_full=pooled,pooled_market_common={n:metrics(common,n) for n in full_names+['sportsbook']},
                gates=gates,bootstrap_full={str(b):contrasts(predictions,full_pairs,b) for b in [14,7]},
                bootstrap_market_common={str(b):contrasts(common,common_pairs,b) for b in [14,7]},
                calibration_full={str(y):{n:reference_module.calibration([r for r in predictions if r['year']==y],n) for n in full_names} for y in [2024,2025,2026]},
                calibration_market_common={str(y):{n:reference_module.calibration([r for r in common if r['year']==y],n) for n in full_names+['sportsbook']} for y in [2024,2025,2026]},
                coverage=dict(full_games=len(predictions),market_common_games=len(common),missing_market_games=len(predictions)-len(common),target_drop_count=0),
                seasons_reused_development=[2024,2025,2026],post_fit_calibration_applied=False,
                bookmaker_opening_is_historical_kalshi_proxy=True,kalshi_or_return_test_performed=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--stage',choices=['fit','summarize'],required=True)
    args=parser.parse_args()
    args.output.mkdir(exist_ok=True,parents=True)
    configure_local(args.output)
    import numpy as np
    import torch
    import scipy
    import sklearn
    import catboost
    import tabpfn
    from tabpfn.model_loading import save_fitted_tabpfn_model
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    settings=read(HERE/'SETTINGS.json')
    reference_module,reference_script_sha=setup_reference()
    if args.stage=='summarize':
        predictions=read(args.output/'predictions.json')
        result=summarize(predictions,reference_module)
        save(args.output/'results.json',result)
        print(json.dumps({k:result[k] for k in ['annual_full','annual_market_common','gates']},indent=2),flush=True)
        return
    pins=read(HERE/'input_manifest.json')
    for name,h in pins.items():assert sha(args.source_root/name)==h,name
    rows,labels,_=reference_module.load(args.source_root)
    assert settings['features']==reference_module.REFERENCE
    reference,reference_models,replay=reference_module.reference_replay(args.source_root,rows,labels)
    save(args.output/'reference_replay.json',replay)
    save(args.output/'reference_models.json',reference_models)
    print('REFERENCE_REPLAY',json.dumps(replay),flush=True)
    assert torch.backends.mps.is_available()
    def deadline(signum,frame):raise TimeoutError('Outer fold exceeded 1800-second ceiling')
    signal.signal(signal.SIGALRM,deadline)
    predictions=[];timings=[]
    for year in [2024,2025,2026]:
        signal.alarm(1800)
        train=[r for r in rows if r['year']<year]
        evaluation=[r for r in rows if r['year']==year]
        assert max(r['date'] for r in train)<min(r['date'] for r in evaluation)
        x,y=arrays(train,settings['features'],labels);z,_=arrays(evaluation,settings['features'],labels)
        start=time.monotonic()
        forest,selection=boosting(train,year,settings['features'],labels,settings,args.output)
        forest_p=forest.predict_proba(z)[:,1]
        forest_done=time.monotonic()
        print('BOOSTING_FIT',json.dumps(dict(year=year,training_games=len(train),selected_grid=selection['selected_grid_index'],trees=selection['final_iterations'],seconds=forest_done-start)),flush=True)
        model=v2_classifier(args.checkpoint,'mps')
        model.fit(x,y)
        torch.mps.synchronize();fitted=time.monotonic()
        assert 'tabpfn_v2' in type(model.models_[0]).__module__
        p=np.concatenate([model.predict_proba(z[i:i+128])[:,1] for i in range(0,len(z),128)])
        torch.mps.synchronize();predicted=time.monotonic()
        assert len(p)==len(evaluation) and np.isfinite(p).all() and ((p>0)&(p<1)).all()
        assert ((forest_p>0)&(forest_p<1)).all()
        save_fitted_tabpfn_model(model,args.output/f'tabpfn_v2_{year}.tabpfn_fit')
        context={
            r['game_id']:r for r in map(json.loads,(args.source_root/f'historical_opening_odds_2026-09-28/season_{year}/derived/consensus.jsonl').read_text().splitlines())}
        for i,r in enumerate(evaluation):
            market=context[r['game_id']]
            assert market['date']==r['date']
            q=market['opening_consensus_home'] if market['native_comparison_eligible'] else None
            assert q is None or 0<q<1
            predictions.append(dict(game_id=r['game_id'],year=year,date=r['date'],home_win=labels[r['game_id']],
                                    reference=reference[r['game_id']],catboost=float(forest_p[i]),tabpfn_v2=float(p[i]),sportsbook=q))
        timing=dict(year=year,training_games=len(train),evaluation_games=len(evaluation),
                    catboost_fit_predict_seconds=forest_done-start,tabpfn_fit_seconds=fitted-forest_done,
                    tabpfn_predict_seconds=predicted-fitted,
                    max_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,
                    mps_driver_bytes_after_prediction=torch.mps.driver_allocated_memory(),
                    training_years=sorted({r['year'] for r in train}),no_outer_labels_in_fit=True)
        timings.append(timing)
        save(args.output/f'predictions_{year}.json',[r for r in predictions if r['year']==year])
        print('V2_FIT',json.dumps(timing),flush=True)
        del model
        import gc
        gc.collect();torch.mps.empty_cache();signal.alarm(0)
    save(args.output/'predictions.json',predictions)
    save(args.output/'timings.json',timings)
    save(args.output/'provenance.json',dict(script_sha256=sha(Path(__file__)),
         capacity_script_sha256=sha(HERE/'capacity.py'),reference_loader_sha256=reference_script_sha,
         settings_sha256=sha(HERE/'SETTINGS.json'),protocol_sha256=sha(HERE/'PROTOCOL.md'),
         input_manifest_sha256=sha(HERE/'input_manifest.json'),checkpoint_sha256=sha(args.checkpoint),
         python=sys.version.split()[0],torch=torch.__version__,tabpfn=tabpfn.__version__,catboost=catboost.__version__,
         numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,
         no_model_network_calls=True,output_hashes={p.name:sha(p) for p in sorted(args.output.iterdir()) if p.is_file()}))


if __name__=='__main__':main()
