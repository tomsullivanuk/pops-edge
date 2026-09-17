"""Explicit local report update. Reads research evidence; never acquires provider data."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import uuid

from performance_reader import safe_path


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    """Atomic local attempt publication, separate from scientific package authority."""
    raw=json.dumps(value,sort_keys=True).encode();temporary=path.with_name('.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def read(path):
    return json.loads(path.read_bytes())


def configured(path, reports):
    value=read(Path(path))
    if set(value)!={'checkout','revision','python','archive_config','operational_state','reports'}:
        raise ValueError('Invalid reporting update configuration')
    for key in ('checkout','python','archive_config','reports','operational_state'):
        if not isinstance(value[key],str) or not Path(value[key]).is_absolute():
            raise ValueError('Reporting paths must be explicit absolute paths')
    if Path(value['reports']).resolve()!=Path(reports).resolve():
        raise ValueError('Reporting output does not match the selected reader')
    if not re.fullmatch('[0-9a-f]{40}',value['revision']):raise ValueError('Reporting revision must be pinned')
    checkout=Path(value['checkout']).resolve()
    def git(*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    if git('rev-parse','HEAD')!=value['revision'] or git('status','--porcelain','--untracked-files=all'):
        raise ValueError('Reporting checkout must be clean at its pinned revision')
    if not (checkout/'mlb_performance_update.py').is_file():raise ValueError('Pinned reporting worker is unavailable')
    from forecast_standalone_operations import DeploymentConfig, NamespaceArchive
    from forecast_reporting_delivery import validate_output_root, _overlap
    archive=NamespaceArchive(DeploymentConfig.from_json(Path(value['archive_config'])))
    output=validate_output_root(reports,archive)
    if _overlap(output,checkout) or _overlap(output,archive.config.log_root.resolve()):
        raise ValueError('Reporting output overlaps reporting source or operational logs')
    if Path(value['operational_state']).resolve() != (archive.config.log_root/'operational-state').resolve():
        raise ValueError('Collection observation must use this archive deployment’s operational records')
    return value


class UpdateController:
    def __init__(self,reports,config=None):
        self.root=Path(reports).resolve();self.config=Path(config) if config else None
        self.guard=threading.Lock()

    def path(self,name):
        return safe_path(self.root,'updates/'+name)

    def status(self):
        result={'configured':self.config is not None,'status':'idle'}
        try:
            target=self.path('current.json')
            if not target.exists():return result
            saved=read(target)
            if (not isinstance(saved,dict) or saved.get('status') not in ('running','succeeded','failed')
                    or not isinstance(saved.get('attempt_id'),str)
                    or not re.fullmatch('[0-9a-f]{32}',saved['attempt_id'])):
                raise ValueError('Invalid saved update record')
            result.update(saved)
            if result['status']=='running':
                lockpath=self.path('writer.lock')
                if not lockpath.exists():result['status']='interrupted'
                else:
                    with lockpath.open('rb') as lock:
                        try:
                            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        except BlockingIOError:pass
                        else:result['status']='interrupted'
                if result['status']=='interrupted':result['message']='Update incomplete. The last selected report remains available; inspect Details before retrying.'
            return result
        except (OSError,ValueError,KeyError,TypeError) as exc:
            return {**result,'status':'unavailable','message':'Saved update status unavailable','error':str(exc)}

    def start(self):
        if self.config is None:raise ValueError('Performance updates have not been configured')
        with self.guard:
            config=configured(self.config,self.root)
            folder=self.path('');folder.mkdir(parents=True,exist_ok=True)
            lock=self.path('writer.lock').open('a+b')
            try:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:raise ValueError('A Performance update is already running') from None
                previous=self.status()
                if previous['status']=='unavailable':raise ValueError('Inspect unreadable update status before retrying')
                if previous['status']=='running':
                    # Our lock is held now, so inspect the persisted status directly.
                    raise ValueError('An earlier update is incomplete; follow manual recovery before retrying')
                attempt=uuid.uuid4().hex;target=self.path(attempt);target.mkdir()
                state=dict(attempt_id=attempt,status='running',started_at=now(),message='Updating Performance Report…',revision=config['revision'])
                write(target/'config.json',config);write(target/'attempt.json',state);write(self.path('current.json'),state)
                command=[config['python'],'-B',str(Path(config['checkout'])/'mlb_performance_update.py'),'--run',str(target/'config.json'),'--attempt',attempt,'--lock-fd',str(lock.fileno())]
                with (target/'worker.log').open('xb') as log:
                    try:
                        proc=subprocess.Popen(command,cwd=config['checkout'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lock.fileno(),),start_new_session=True)
                    except Exception as exc:
                        state.update(status='failed',completed_at=now(),message='Could not start report update',error=str(exc));write(target/'attempt.json',state);write(self.path('current.json'),state);raise
                threading.Thread(target=self._watch,args=(proc,attempt),daemon=True).start()
                return state
            finally:lock.close()

    def _watch(self,proc,attempt):
        proc.wait()
        # The child persists normal outcomes. On abrupt exit status() detects the
        # released lock without silently overwriting a newer attempt.

    def observation(self,state,package_id):
        if state.get('package',{}).get('package_id')!=package_id or not state.get('collection_sha256'):return None
        raw=self.download(state['attempt_id'])
        return json.loads(raw)

    def download(self,attempt):
        if not re.fullmatch('[0-9a-f]{32}',attempt):raise ValueError('Invalid update identity')
        state=read(self.path(attempt+'/attempt.json'))
        if state.get('attempt_id')!=attempt:raise ValueError('Saved observation attempt differs')
        raw=self.path(attempt+'/collection.json').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=state.get('collection_sha256'):raise ValueError('Saved collection observation is damaged')
        return raw


def run(config,attempt):
    """Called only by a configured pinned worker, with the inherited writer lock."""
    from forecast_standalone_operations import DeploymentConfig,NamespaceArchive
    import forecast_reporting_delivery as delivery
    from forecast_reporting_collection import snapshot
    controller=UpdateController(config['reports']);target=controller.path(attempt)
    state=read(target/'attempt.json')
    def save():
        write(target/'attempt.json',state);write(controller.path('current.json'),state)
    scientific_success=False
    try:
        delivery._revision(config['revision'])
        archive=NamespaceArchive(DeploymentConfig.from_json(Path(config['archive_config'])))
        old=delivery.read_entry(controller.root)['live']
        def scored(ref):
            if ref is None:return set()
            return set(read(safe_path(controller.root,'packages/'+ref['package_id']+'/projections.json'))['scopes'][0]['scored_ids'])
        before=scored(old)
        ref=delivery.generate_report(archive=archive,output=controller.root,study='live',expected_revision=config['revision'],update_live=True,prepare_matches=True)
        scientific_success=True
        state.update(package=ref,status='running',message='Report updated. Reading collection status…')
        # Scientific success is persisted before optional observation work. A later
        # failure cannot relabel a selected valid report as failed science.
        save()
        try:
            added=scored(ref)-before
            state['message']='Report updated.' if added else 'Report updated. No additional scored results are available.'
            observation=snapshot(Path(config['operational_state']),datetime.now(timezone.utc))
            write(target/'collection.json',observation)
            state['collection_sha256']=hashlib.sha256((target/'collection.json').read_bytes()).hexdigest()
            state['collection_availability']=observation['availability']
        except Exception as exc:
            state['collection_error']=str(exc)
        state.update(status='succeeded',completed_at=now())
        save()
        return 0
    except Exception as exc:
        if scientific_success:
            # Never report failure after scientific selection succeeded.
            print('REPORT UPDATED; UPDATE STATUS COULD NOT BE SAVED: '+str(exc),flush=True)
        else:
            state.update(status='failed',completed_at=now(),message='Report update failed. The previous report remains selected.',error=str(exc))
            try:save()
            except Exception as persistence:print('ATTEMPT STATUS COULD NOT BE SAVED: '+str(persistence),flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--attempt',required=True);parser.add_argument('--lock-fd',type=int,required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}',args.attempt):raise SystemExit('Invalid attempt identity')
    # Keep the inherited lock descriptor alive through the complete operation.
    with os.fdopen(args.lock_fd,'a+b') as lock:
        config=configured(args.run,read(args.run)['reports'])
        raise SystemExit(run(config,args.attempt))
