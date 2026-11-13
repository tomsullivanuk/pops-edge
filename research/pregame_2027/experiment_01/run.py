"""One frozen offline challenger. Inputs and per-game outputs remain private."""
import argparse
import hashlib
import json
import math
import sys
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy.optimize import least_squares
from scipy.special import expit, logit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
REFERENCE = ['x_win60', 'x_rd60', 'x_rd10', 'progress_centered',
             'progress_x_win60', 'progress_x_rd60', 'progress_x_rd10',
             'starter_kbb', 'starter_hr', 'starter_ip']
CHALLENGER = ['rating_difference', 'progress_centered', 'starter_kbb',
              'starter_hr', 'starter_ip']
NEUTRAL_VENUES = {5445, 2735, 5340, 5381, 5150, 3949, 2397, 6130}
SETTINGS = dict(C=1., fit_intercept=True, class_weight=None, solver='lbfgs',
                tol=1e-8, max_iter=10000, l1_ratio=0.)
SEED = 20261012
REPLICATES = 5000


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if path.exists():
        assert path.read_bytes() == payload, f'Replay mismatch: {path.name}'
    else:
        path.write_bytes(payload)


def load(root):
    pins = read(HERE / 'input_manifest.json')
    for name, digest in pins.items():
        assert sha(root / name) == digest, f'Input changed: {name}'
    rows = read(root / 'native_starter_2026-09-28/features.json')
    extra = read(root / 'native_2025_comparison_2026-09-29/starter_features.json')
    old = {r['game_id']: r for r in rows}
    for r in extra:
        if r['year'] == 2024:
            assert all(abs(r[k] - old[r['game_id']][k]) < 1e-12 for k in REFERENCE)
    rows += [r for r in extra if r['year'] == 2025]
    extra = read(root / 'native_2026_evaluation_2026-09-30/starter_features.json')
    old = {r['game_id']: r for r in rows}
    for r in extra:
        if r['year'] == 2025:
            assert all(abs(r[k] - old[r['game_id']][k]) < 1e-12 for k in REFERENCE)
    rows += [r for r in extra if r['year'] == 2026]
    rows.sort(key=lambda r: (r['date'], r['game_id']))
    assert len(rows) == len({r['game_id'] for r in rows}) == 12132
    dataset = root / 'native_model_dataset_2026-09-28/dataset'
    labels = {}
    for year in range(2022, 2027):
        part = 'training' if year < 2024 else 'development' if year == 2024 else 'evaluation'
        rr = [json.loads(line) for line in (dataset / f'{part}/{year}_labels.jsonl').read_text().splitlines()]
        assert {r['game_id'] for r in rows if r['year'] == year} == {r['game_id'] for r in rr}
        labels.update({r['game_id']: r['home_win'] for r in rr})
    outcomes = [json.loads(line) for line in (dataset / 'canonical_outcomes.jsonl').read_text().splitlines()]
    assert len(outcomes) == len({r['game_id'] for r in outcomes})
    schedules = {}
    for year in range(2021, 2027):
        schedule = read(root / f'historical_data_readiness/season_{year}/official_schedule.json')
        for d in schedule['dates']:
            for g in d['games']:
                if g['status']['detailedState'] not in {'Final', 'Completed Early', 'Game Over'}:
                    continue
                if g['gamePk'] in schedules:
                    prior = schedules[g['gamePk']]
                    if prior['venue']['id'] != g['venue']['id']:
                        assert prior.get('resumeDate') and g.get('resumedFrom')
                        assert (prior['venue']['id'] in NEUTRAL_VENUES) == (g['venue']['id'] in NEUTRAL_VENUES)
                schedules[g['gamePk']] = g
    for g in outcomes:
        official = schedules[g['game_id']]
        assert all(g[s] == official['teams'][s]['team']['id'] for s in ['home', 'away'])
        g['neutral'] = official['venue']['id'] in NEUTRAL_VENUES
    by_id = {g['game_id']: g for g in outcomes}
    for r in rows:
        g = by_id[r['game_id']]
        assert g['valid'] and not g['resumed']
        assert (r['date'], r['home'], r['away']) == (g['date'], g['home'], g['away'])
        assert labels[r['game_id']] == int(g['home_runs'] > g['away_runs'])
    return rows, labels, outcomes


def fit_predict(train, evaluation, names, labels):
    x = np.array([[r[k] for k in names] for r in train])
    z = np.array([[r[k] for k in names] for r in evaluation])
    y = np.array([labels[r['game_id']] for r in train])
    assert np.isfinite(x).all() and np.isfinite(z).all()
    scaler = StandardScaler()
    x = scaler.fit_transform(x)
    z = scaler.transform(z)
    with warnings.catch_warnings(), threadpool_limits(limits=1):
        warnings.simplefilter('error', ConvergenceWarning)
        fitted = LogisticRegression(**SETTINGS).fit(x, y)
    p = fitted.predict_proba(z)[:, 1]
    assert ((p > 0) & (p < 1)).all()
    gradient = np.r_[x.T @ (fitted.predict_proba(x)[:, 1] - y) + fitted.coef_[0],
                     (fitted.predict_proba(x)[:, 1] - y).sum()] / len(y)
    assert max(abs(gradient)) < 1e-6
    model = dict(features=names, settings=SETTINGS, scaler_mean=scaler.mean_.tolist(),
                 scaler_scale=scaler.scale_.tolist(), coefficients=fitted.coef_[0].tolist(),
                 intercept=float(fitted.intercept_[0]), training_games=len(train),
                 iterations=int(fitted.n_iter_[0]), gradient_max_abs=float(max(abs(gradient))))
    return p, model


def reference_replay(root, rows, labels):
    predictions, models, checks = {}, {}, {}
    sources = {2024: ('native_starter_2026-09-28', 'starter'),
               2025: ('native_2025_retraining_2026-09-29', 'new_starter'),
               2026: ('native_2026_evaluation_2026-09-30', 'native')}
    for year, (directory, key) in sources.items():
        train = [r for r in rows if r['year'] < year]
        evaluation = [r for r in rows if r['year'] == year]
        p, model = fit_predict(train, evaluation, REFERENCE, labels)
        retained = {r['game_id']: r for r in read(root / directory / 'predictions.json')}
        assert {r['game_id'] for r in evaluation} == set(retained)
        expected = np.array([retained[r['game_id']][key] for r in evaluation])
        assert all(labels[r['game_id']] == retained[r['game_id']]['home_win'] for r in evaluation)
        difference = float(max(abs(p - expected)))
        assert difference < 1e-9, f'Unexplained reference discrepancy {year}: {difference}'
        for r, value in zip(evaluation, p):
            predictions[r['game_id']] = float(value)
        models[str(year)] = model
        checks[str(year)] = dict(games=len(evaluation), max_probability_difference=difference)
    return predictions, models, checks


def rating_at(outcomes, target_date, year, teams):
    history = [g for g in outcomes if year - 1 <= g['year'] <= year and g['available_day'] < target_date]
    assert all(g['valid'] and not g['issues'] for g in history), 'Invalid required history'
    day = date.fromisoformat(target_date).toordinal()
    index = {t: i for i, t in enumerate(teams)}
    x = np.zeros((len(history), len(teams) + 1))
    y, weights = [], []
    for i, g in enumerate(history):
        x[i, index[g['home']]] = 1.
        x[i, index[g['away']]] = -1.
        x[i, -1] = float(not g['neutral'])
        y.append(g['home_runs'] - g['away_runs'])
        age = day - date.fromisoformat(g['available_day']).toordinal()
        assert age >= 1
        weights.append(2. ** (-age / 60.) * (1. if g['year'] == year else .5))
    if not history:
        return {t: 0. for t in teams}, dict(history_games=0, fallback=True, home_advantage=None)
    w = np.array(weights)
    normal = x.T @ (w[:, None] * x)
    normal += np.diag([20.] * len(teams) + [0.])
    rhs = x.T @ (w * np.array(y))
    # Sum-zero equality constraint, with an unpenalized home-advantage term.
    constraint = np.r_[np.ones(len(teams)), 0.]
    matrix = np.zeros((len(teams) + 2, len(teams) + 2))
    matrix[:-1, :-1] = normal
    matrix[-1, :-1] = matrix[:-1, -1] = constraint
    solution = np.linalg.solve(matrix, np.r_[rhs, 0.])
    assert abs(solution[:len(teams)].sum()) < 1e-10
    assert max(abs(matrix @ solution - np.r_[rhs, 0.])) < 1e-8
    return dict(zip(teams, solution[:len(teams)])), dict(
        history_games=len(history), fallback=False,
        maximum_available_day=max(g['available_day'] for g in history),
        home_advantage=float(solution[len(teams)]),
        neutral_games=sum(g['neutral'] for g in history),
        resumed_games=sum(g['resumed'] for g in history),
        history_game_ids=sorted(g['game_id'] for g in history),
        sum_weights=float(w.sum()))


def build_ratings(rows, outcomes):
    teams = sorted({g[s] for g in outcomes for s in ['home', 'away']})
    assert len(teams) == 30
    cached, lineage = {}, []
    for r in rows:
        key = (r['year'], r['date'])
        if key not in cached:
            cached[key] = rating_at(outcomes, r['date'], r['year'], teams)
            rating, details = cached[key]
            lineage.append(dict(year=r['year'], date=r['date'], ratings=rating, **details))
        ratings, details = cached[key]
        assert r['game_id'] not in details.get('history_game_ids', [])
        r['rating_difference'] = float(ratings[r['home']] - ratings[r['away']])
    return lineage


def losses(y, p):
    return (p - y) ** 2, np.logaddexp(0, logit(p)) - y * logit(p)


def metrics(rr, name):
    y = np.array([r['home_win'] for r in rr])
    p = np.array([r[name] for r in rr])
    brier, logloss = losses(y, p)
    return dict(games=len(rr), brier=float(brier.mean()), log_loss=float(logloss.mean()))


def calibration(rr, name):
    y = np.array([r['home_win'] for r in rr])
    p = np.array([r[name] for r in rr])
    x = np.column_stack([np.ones(len(p)), logit(p)])
    fit = least_squares(lambda b: x.T @ (expit(x @ b) - y), [0., 1.],
                        xtol=1e-12, ftol=1e-12, gtol=1e-12)
    assert fit.success and max(abs(fit.fun)) < 1e-6
    bins = []
    for b in range(10):
        mask = (p >= b / 10) & (p < (b + 1) / 10)
        bins.append(dict(lower=b/10, upper=(b+1)/10, games=int(mask.sum()),
                         mean_probability=float(p[mask].mean()) if mask.any() else None,
                         home_win_rate=float(y[mask].mean()) if mask.any() else None))
    return dict(intercept=float(fit.x[0]), slope=float(fit.x[1]),
                mean_probability=float(p.mean()), home_win_rate=float(y.mean()),
                diagnostic_only=True, bins=bins)


def bootstrap(rr, length):
    rng = np.random.default_rng(SEED)
    annual_draws = []
    for year in [2024, 2025, 2026]:
        sub = [r for r in rr if r['year'] == year]
        first = date.fromisoformat(min(r['date'] for r in sub))
        days = (date.fromisoformat(max(r['date'] for r in sub)) - first).days + 1
        ix = np.array([(date.fromisoformat(r['date']) - first).days for r in sub])
        y = np.array([r['home_win'] for r in sub])
        ref = losses(y, np.array([r['reference'] for r in sub]))
        new = losses(y, np.array([r['challenger'] for r in sub]))
        counts = np.bincount(ix, minlength=days)
        sums = np.array([np.bincount(ix, weights=a-b, minlength=days) for a, b in zip(ref, new)])
        draws = []
        for _ in range(REPLICATES):
            chosen = (rng.integers(0, days-length+1, size=math.ceil(days/length))[:, None] + np.arange(length)).ravel()[:days]
            draws.append(sums[:, chosen].sum(axis=1) / counts[chosen].sum())
        annual_draws.append(np.array(draws))
    def interval(values):
        return dict(lower=float(np.quantile(values, .025)), upper=float(np.quantile(values, .975)))
    return dict(block_days=length, replicates=REPLICATES, seed=SEED,
                sign='reference loss minus challenger loss; positive favors challenger',
                equal_weight_annual_brier=interval(np.mean([x[:, 0] for x in annual_draws], axis=0)),
                annual={str(y):dict(brier=interval(x[:, 0]), log_loss=interval(x[:, 1]))
                        for y, x in zip([2024, 2025, 2026], annual_draws)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['reference', 'experiment'], required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    def guard(event, _args):
        if event in ['socket.connect', 'socket.getaddrinfo']:
            raise RuntimeError('Offline experiment: network prohibited')
    sys.addaudithook(guard)
    rows, labels, outcomes = load(args.source_root)
    reference, reference_models, replay = reference_replay(args.source_root, rows, labels)
    save(args.output / 'reference_replay.json', replay)
    save(args.output / 'reference_models.json', reference_models)
    print('REFERENCE', json.dumps(replay), flush=True)
    if args.stage == 'reference':
        return
    lineage = build_ratings(rows, outcomes)
    save(args.output / 'rating_lineage.json', lineage)
    models, predictions = {}, []
    for year in [2024, 2025, 2026]:
        train = [r for r in rows if r['year'] < year]
        evaluation = [r for r in rows if r['year'] == year]
        p, model = fit_predict(train, evaluation, CHALLENGER, labels)
        models[str(year)] = model
        for r, value in zip(evaluation, p):
            predictions.append(dict(game_id=r['game_id'], year=year, date=r['date'],
                                    home_win=labels[r['game_id']], reference=reference[r['game_id']],
                                    challenger=float(value)))
    annual = {str(year): {n: metrics([r for r in predictions if r['year'] == year], n)
                         for n in ['reference', 'challenger']} for year in [2024, 2025, 2026]}
    gains = {year: s['reference']['brier'] - s['challenger']['brier'] for year, s in annual.items()}
    pooled = {n: metrics(predictions, n) for n in ['reference', 'challenger']}
    average = float(np.mean(list(gains.values())))
    gate = dict(average_annual_brier_gain_at_least_0_001=average >= .001,
                positive_gain_in_at_least_two_years=sum(v > 0 for v in gains.values()) >= 2,
                pooled_log_loss_no_worse=pooled['challenger']['log_loss'] <= pooled['reference']['log_loss'],
                unchanged_target_coverage=len(predictions) == 7280,
                no_new_hindsight_dependence=True)
    result = dict(annual=annual, annual_brier_gains=gains,
                  equal_weight_annual_brier_gain=average, pooled=pooled,
                  gate=gate, continuation_gate_passed=all(gate.values()),
                  bootstrap={str(l): bootstrap(predictions, l) for l in [14, 7]},
                  calibration={str(year): {n: calibration([r for r in predictions if r['year'] == year], n)
                                          for n in ['reference', 'challenger']} for year in [2024, 2025, 2026]},
                  coverage=dict(targets_by_year=dict(Counter(str(r['year']) for r in rows)),
                                invalid_outcomes=sum(not g['valid'] for g in outcomes),
                                rating_days=len(lineage), fallback_days=sum(d['fallback'] for d in lineage)),
                  reused_development_seasons=[2024, 2025, 2026], market_comparison_performed=False)
    save(args.output / 'models.json', models)
    save(args.output / 'predictions.json', predictions)
    save(args.output / 'results.json', result)
    save(args.output / 'provenance.json', dict(
        script_sha256=sha(Path(__file__)), input_manifest_sha256=sha(HERE/'input_manifest.json'),
        protocol_sha256=sha(HERE/'PROTOCOL.md'), python=sys.version,
        numpy=np.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__,
        output_hashes={p.name:sha(p) for p in sorted(args.output.iterdir()) if p.suffix=='.json'}))
    print(json.dumps({k:result[k] for k in ['annual', 'equal_weight_annual_brier_gain', 'gate', 'continuation_gate_passed']}, indent=2))


if __name__ == '__main__':
    main()
