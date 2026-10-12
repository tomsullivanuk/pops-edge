"""Independent direct weighted histories and chronology checks; no model fitting."""
import argparse
import json
from pathlib import Path
import numpy as np


def main(root):
    a=dict(np.load(root/'features.npz'));errors=[];mutations=[];tested=0
    for year in [2022,2023,2024,2025]:
        dates=np.unique(a['date'][a['year']==year])
        for d in [dates[0],dates[len(dates)//2],dates[-1]]:
            past=(a['available']<d)&(a['available']>=d-365)
            weights=2.**(-(d-a['available'][past])/180)
            def calculate(labels,ids):
                league=np.bincount(labels[past],weights=weights,minlength=3)
                q=(league+1)/(league.sum()+3);z=[]
                for key in ['pid','bid']:
                    player=np.bincount(labels[past][a[key][past]==ids[key]],weights=weights[a[key][past]==ids[key]],minlength=3)
                    rate=(player+200*q)/(player.sum()+200)
                    z.extend(np.log(rate[:2]/rate[2])-np.log(q[:2]/q[2]))
                return np.array(z),q
            idx=np.flatnonzero(a['date']==d)[::max(1,int((a['date']==d).sum())//5)][:5]
            modified=a['y'].copy();modified[~past]=(modified[~past]+1)%3
            for i in idx:
                ids={key:a[key][i] for key in ['pid','bid']};x,q=calculate(a['y'],ids);mx,mq=calculate(modified,ids)
                errors.append(float(max(np.abs(x-a['x'][i,:4]).max(),np.abs(q-a['q'][i]).max())))
                mutations.append(float(max(np.abs(mx-x).max(),np.abs(mq-q).max())));tested+=1
    result={'rows_checked':tested,'direct_weighted_history_max_difference':max(errors),'same_future_outcome_mutation_max_difference':max(mutations),'passed':max(errors)<1e-8 and max(mutations)==0}
    assert result['passed'];(root/'feature_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);main(p.parse_args().root)
