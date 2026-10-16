"""Pinned v3.5 core, local-only inference configuration."""
import hashlib,os,sys
CHECKPOINT_SHA='ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3'
NETWORK_ATTEMPTS=[]
def configure(output):
 for key,value in {'PYTHONDONTWRITEBYTECODE':'1','SKB_DATA_DIRECTORY':str(output/'cache/skrub'),'MPLCONFIGDIR':str(output/'cache/matplotlib'),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TABPFN_DISABLE_TELEMETRY':'1','TABPFN_NO_BROWSER':'1','TABPFN_MODEL_VERSION':'v3.5','TABPFN_MODEL_CACHE_DIR':str(output/'models'),'TABPFN_MPS_MEMORY_FRACTION':'0.5','TABPFN_MAX_BATCHED_ESTIMATOR_ROWS':'0','TABPFN_MAX_BATCHED_TEST_ROWS':'128'}.items():os.environ[key]=value
 def guard(event,args):
  if event in ['socket.connect','socket.getaddrinfo']:
   NETWORK_ATTEMPTS.append(event);raise RuntimeError('Offline model use: network prohibited')
 sys.addaudithook(guard)
def classifier(checkpoint):
 import torch
 from tabpfn import TabPFNClassifier
 from tabpfn.constants import ModelVersion
 with checkpoint.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==CHECKPOINT_SHA
 return TabPFNClassifier.create_default_for_version(ModelVersion.V3_5,model_path=str(checkpoint),device='mps',n_estimators=4,random_state=20261012,fit_mode='fit_with_cache',inference_precision=torch.float32,memory_saving_mode='auto',n_preprocessing_jobs=1,show_progress_bar=False,softmax_temperature=1.0,balance_probabilities=False,average_before_softmax=False)
