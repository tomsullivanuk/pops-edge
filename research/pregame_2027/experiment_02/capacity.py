"""Bounded, offline, non-baseball v2 capacity check. No real-data scoring."""
import argparse
import hashlib
import json
import os
import resource
import signal
import sys
import time
from pathlib import Path


def configure_local(output):
    os.environ['SKB_DATA_DIRECTORY'] = str(output / 'cache/skrub')
    os.environ['MPLCONFIGDIR'] = str(output / 'cache/matplotlib')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TABPFN_MODEL_VERSION'] = 'v2'
    os.environ['TABPFN_MODEL_CACHE_DIR'] = str(output / 'models')
    os.environ['TABPFN_MPS_MEMORY_FRACTION'] = '0.5'
    os.environ['TABPFN_MAX_BATCHED_ESTIMATOR_ROWS'] = '0'
    os.environ['TABPFN_MAX_BATCHED_TEST_ROWS'] = '128'
    def guard(event, args):
        if event in ['socket.connect', 'socket.getaddrinfo']:
            raise RuntimeError('Offline-only model use; network forbidden')
    sys.addaudithook(guard)


CHECKPOINT_SHA = 'cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49'


def v2_classifier(checkpoint, device):
    import torch
    from tabpfn import TabPFNClassifier
    from tabpfn.constants import ModelVersion
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == CHECKPOINT_SHA
    return TabPFNClassifier.create_default_for_version(
        ModelVersion.V2, model_path=str(checkpoint), device=device,
        n_estimators=4, random_state=20261012, fit_mode='fit_with_cache',
        inference_precision=torch.float32, memory_saving_mode='auto',
        n_preprocessing_jobs=1, show_progress_bar=False,
        softmax_temperature=0.9, balance_probabilities=False,
        average_before_softmax=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--device', choices=['cpu', 'mps'], required=True)
    parser.add_argument('--rows', type=int, required=True)
    args = parser.parse_args()
    assert args.rows in [128, 1024, 9704]
    assert args.rows == 128 or args.device == 'mps'
    args.output.mkdir(exist_ok=True, parents=True)
    configure_local(args.output)
    def deadline(signum, frame):
        raise TimeoutError('Synthetic capacity exceeded 900-second ceiling')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(900)
    import numpy as np
    import torch
    import tabpfn
    import catboost
    import sklearn
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    if args.device == 'mps':
        assert torch.backends.mps.is_available(), 'MPS unavailable'
    rng = np.random.default_rng(20261012)
    x = rng.normal(size=(args.rows, 10))
    eta = .3*x[:,0] - .2*x[:,1] + .1*x[:,2]*x[:,3]
    y = (rng.random(args.rows) < 1/(1+np.exp(-eta))).astype(int)
    z = rng.normal(size=(128, 10))
    start = time.monotonic()
    model = v2_classifier(args.checkpoint, args.device)
    model.fit(x, y)
    if args.device == 'mps':
        torch.mps.synchronize()
    fitted = time.monotonic()
    p = model.predict_proba(z)[:, 1]
    if args.device == 'mps':
        torch.mps.synchronize()
    predicted = time.monotonic()
    assert np.isfinite(p).all() and ((p > 0) & (p < 1)).all()
    # Repeat a prediction against the same frozen context to check numerical stability.
    replay = model.predict_proba(z)[:, 1]
    maximum_difference = float(max(abs(replay-p)))
    assert maximum_difference < 1e-6
    receipt = dict(synthetic_only=True, baseball_inputs_accessed=False,
                   rows=args.rows, features=10, prediction_rows=len(z),
                   device=args.device, estimators=4, checkpoint_sha256=CHECKPOINT_SHA,
                   fit_seconds=fitted-start, predict_seconds=predicted-fitted,
                   prediction_replay_max_absolute_difference=maximum_difference,
                   max_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,
                   mps_current_tensor_bytes=torch.mps.current_allocated_memory() if args.device=='mps' else None,
                   mps_driver_bytes_after_prediction=torch.mps.driver_allocated_memory() if args.device=='mps' else None,
                   mps_memory_fraction=0.5, annual_population_truncation=False,
                   python=sys.version.split()[0], torch=torch.__version__, tabpfn=tabpfn.__version__,
                   catboost=catboost.__version__, sklearn=sklearn.__version__, numpy=np.__version__,
                   no_network_model_use=True)
    name=f'capacity_{args.device}_{args.rows}.json'
    path=args.output/name
    assert not path.exists(), 'Use a new output directory for another capacity run'
    path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)
    signal.alarm(0)


if __name__ == '__main__':
    main()
