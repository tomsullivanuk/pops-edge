"""Pinned local v3.5 synthetic capacity check; no baseball data or network."""
import argparse,hashlib,json,os,resource,signal,sys,time,traceback
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--rows',type=int,choices=[128,9704],required=True);args=parser.parse_args()
root=Path(__file__).resolve().parent;out=root/f'capacity_mps_{args.rows}.json';assert not out.exists()
for key,value in {'PYTHONDONTWRITEBYTECODE':'1','SKB_DATA_DIRECTORY':str(root/'cache/skrub'),'MPLCONFIGDIR':str(root/'cache/matplotlib'),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TABPFN_DISABLE_TELEMETRY':'1','TABPFN_NO_BROWSER':'1','TABPFN_MODEL_VERSION':'v3.5','TABPFN_MODEL_CACHE_DIR':str(root/'models'),'TABPFN_MPS_MEMORY_FRACTION':'0.5','TABPFN_MAX_BATCHED_ESTIMATOR_ROWS':'0','TABPFN_MAX_BATCHED_TEST_ROWS':'128'}.items():os.environ[key]=value
network_attempts=[]
def guard(event,params):
 if event in ['socket.connect','socket.getaddrinfo']:
  network_attempts.append(event);raise RuntimeError('Network prohibited during synthetic model use')
sys.addaudithook(guard)
def deadline(signum,frame):raise TimeoutError('1800-second synthetic process ceiling')
signal.signal(signal.SIGALRM,deadline);signal.alarm(1800)
receipt={'synthetic_only':True,'baseball_data_accessed':False,'rows':args.rows,'features':10,'prediction_rows':128,'n_estimators':4,'mps_memory_fraction':0.5,'wall_cap_seconds':1800,'credentials_created_or_configured':False,'no_network_model_use':True}
start=time.monotonic()
try:
 import numpy as np,torch,tabpfn
 from tabpfn import TabPFNClassifier
 from tabpfn.constants import ModelVersion
 assert torch.backends.mps.is_available()
 torch.set_num_threads(4);torch.set_num_interop_threads(1)
 cp=root/'models/tabpfn-v3.5-20260909.safetensors';expected='ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3'
 with cp.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
 rng=np.random.default_rng(20261012);x=rng.normal(size=(args.rows,10));eta=.3*x[:,0]-.2*x[:,1]+.1*x[:,2]*x[:,3];y=(rng.random(args.rows)<1/(1+np.exp(-eta))).astype(int);z=rng.normal(size=(128,10))
 model=TabPFNClassifier.create_default_for_version(ModelVersion.V3_5,model_path=str(cp),device='mps',n_estimators=4,random_state=20261012,fit_mode='fit_with_cache',inference_precision=torch.float32,memory_saving_mode='auto',n_preprocessing_jobs=1,show_progress_bar=False,balance_probabilities=False,average_before_softmax=False)
 t=time.monotonic();model.fit(x,y);torch.mps.synchronize();fit=time.monotonic()-t
 t=time.monotonic();p=model.predict_proba(z)[:,1];torch.mps.synchronize();predict=time.monotonic()-t
 assert np.isfinite(p).all() and ((p>0)&(p<1)).all()
 repeated=model.predict_proba(z)[:,1];torch.mps.synchronize();replay=float(np.max(np.abs(p-repeated)));assert replay<1e-6
 changed=z.copy();changed[64:]+=100;pm=model.predict_proba(changed)[:,1];torch.mps.synchronize();mutation=float(np.max(np.abs(p[:64]-pm[:64])));assert mutation<1e-6
 isolated=model.predict_proba(z[:64])[:,1];torch.mps.synchronize();batch=float(np.max(np.abs(p[:64]-isolated)));assert batch<1e-6
 receipt.update(status='passed',checkpoint_sha256=expected,fit_seconds=fit,predict_seconds=predict,replay_max_abs_difference=replay,later_test_mutation_max_abs_difference=mutation,batch_max_abs_difference=batch,resolved_softmax_temperature=float(model.softmax_temperature_),mps_driver_bytes_after_checks=torch.mps.driver_allocated_memory(),mps_tensor_bytes_after_checks=torch.mps.current_allocated_memory(),max_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,python=sys.version.split()[0],tabpfn=tabpfn.__version__,torch=torch.__version__,numpy=np.__version__)
except Exception as e:
 receipt.update(status='failed',error_type=type(e).__name__,error=str(e)[:1500]);traceback.print_exc()
finally:
 receipt.update(total_seconds=time.monotonic()-start,network_attempts_blocked=network_attempts);out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True);signal.alarm(0)
if receipt['status']!='passed':raise SystemExit(1)
