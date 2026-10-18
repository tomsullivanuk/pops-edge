"""Direct histories versus incremental feature preparation; no fitting."""
import importlib.util,json,datetime as dt
from pathlib import Path
import numpy as np
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('run',ROOT/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def main(out):
    a=dict(np.load(out/'features.npz'));events=[]
    for year in [2022,2023,2024,2025]:
        info={r['gid']:r for r in m.csvrows(m.RAW/f'{year}gameinfo.csv') if r['gametype']=='regular'}
        available={g:max(m.day(r['date']),m.day(r['suspend']) if r['suspend'] else 0) for g,r in info.items()};temp=[]
        for r in m.csvrows(m.RAW/f'{year}plays.csv'):
            if r['gid'] not in info:continue
            available[r['gid']]=max(available[r['gid']],m.day(r['date']))
            if r['pa']=='1':
                # Independent formula, preserving integer event counts.
                v=lambda k:float(r[k] or 0);u=v('walk')-v('iw')
                n=.690*u+.722*v('hbp')+.888*v('single')+1.271*v('double')+1.616*v('triple')+2.101*v('hr')
                den=v('ab')+u+v('sf')+v('hbp');temp.append((r['gid'],r['batter'],n,den))
        events.extend((available[g],p,n,z) for g,p,n,z in temp)
    dates=np.array([e[0] for e in events]);pids=np.array([e[1] for e in events]);nums=np.array([e[2] for e in events]);dens=np.array([e[3] for e in events])
    bridge={int(k):v[0] for k,v in m.read(m.PRIVATE/'projection-feasibility/slot_bridge_private.json').items()}
    lineage={r['game_id']:r for r in m.read(m.SOURCE/'native_actual_lineup_2026-09-29/lineage.json')};lineage.update({r['game_id']:r for r in m.read(m.PRIVATE/'projection-feasibility/lineage_2025_private.json')})
    errors=[];count=0
    for year in [2022,2023,2024,2025]:
        idx=np.flatnonzero(a['year']==year)
        for i in [idx[0],idx[len(idx)//2],idx[-1]]:
            d=a['date'][i];past=(dates<d)&(dates>=d-365);w=2.**(-(d-dates[past])/180);num=np.dot(w,nums[past]);den=np.dot(w,dens[past]);q=num/den if den else .320
            # Same/future mutation is disjoint from every admitted direct history.
            changed=nums.copy();changed[dates>=d]+=1000;assert np.array_equal(changed[past],nums[past])
            g=lineage[int(a['game_id'][i])]
            for sidekey,s in [('home',0),('away',1)]:
                for t in g['sides'][sidekey]['terms']:
                    mask=pids[past]==bridge[t['mlb_player_id']];rate=(np.dot(w[mask],nums[past][mask])+200*q)/(np.dot(w[mask],dens[past][mask])+200)
                    errors.append(abs(rate-a['control'][i,s,t['slot']-1]));count+=1
    for year in [2024,2025]:
        assert np.array_equal(a[f'control_{year}'][:,:10],a['base']);assert np.array_equal(a[f'steamer_{year}'][:,:10],a['base'])
        assert np.array_equal(a[f'control_{year}'][:,-1],a[f'steamer_{year}'][:,-1])
    assert np.array_equal(a['control'][a['fallback']],a['steamer'][a['fallback']])
    result=dict(direct_player_slots_checked=count,max_control_rate_difference=float(max(errors)),same_future_mutation_independence=True,unchanged_native_columns=True,identical_shared_hand_columns=True,missing_projection_exact_control_fallback=True)
    assert max(errors)<1e-10;m.save(out/'feature_verification.json',result);print(result)

if __name__=='__main__':
    import sys;main(Path(sys.argv[1]))
