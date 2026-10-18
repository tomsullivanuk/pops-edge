"""Synthetic cached-context invariance checks; never loads baseball inputs."""
import argparse
import json
from pathlib import Path
from capacity import configure_local, v2_classifier


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    args=ap.parse_args()
    configure_local(args.output)
    import numpy as np
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    rng=np.random.default_rng(20261012)
    x=rng.normal(size=(128,10));y=(rng.random(128)<.5).astype(int)
    z=rng.normal(size=(128,10))
    model=v2_classifier(args.checkpoint,'mps').fit(x,y)
    original=model.predict_proba(z)[:,1]
    isolated=model.predict_proba(z[:16])[:,1]
    changed=z.copy();changed[16:]=rng.normal(size=(112,10))*100+1000
    mutated=model.predict_proba(changed)[:16,1]
    diffs={'later_test_row_mutation_max_absolute_difference':float(max(abs(mutated-original[:16]))),
           'batch_vs_isolated_max_absolute_difference':float(max(abs(isolated-original[:16])))}
    assert max(diffs.values())<1e-6,diffs
    result=dict(synthetic_only=True,baseball_inputs_accessed=False,device='mps',
                tolerance=1e-6,**diffs,passed=True)
    (args.output/'prediction_independence.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
