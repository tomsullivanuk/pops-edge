"""Offline equality and authority fences for outcome and live date replay."""
import json
import multiprocessing
import shutil
import tempfile
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests import test_reporting_outcome_compatibility as compatibility_tests
from forecast_standalone_activation import reconcile_outcomes_from_raw
from forecast_standalone_operations import NamespaceArchive, OperationsError, replay_pr17_archive
from forecast_supporting_replay import OutcomeReplayArchive, replay_for_request_dates
from forecast_prospective_projection import _scientific_state_bytes
from operate_forecast_standalone_activation import execute, load_live_supporting


def outcome_worker(config, at, ready, proceed, output):
    from inspect_forecast_standalone_activation import fixtures
    mlb=fixtures()[0];calls=[]
    def loader(started):
        def get(base,path):
            from urllib.parse import parse_qs,urlsplit
            if not calls:
                ready.set()
                if not proceed.wait(15):raise RuntimeError('collector did not finish')
            day=parse_qs(urlsplit(path).query)['date'][0];calls.append(day)
            return json.dumps({'dates':[x for x in json.loads(mlb)['dates'] if x['date']==day]}).encode()
        return load_live_supporting(archive=NamespaceArchive(config),purpose='outcomes',at=at,
            public_get=get,clock=lambda:at)
    begin=time.monotonic()
    try:
        result=execute('reconcile-outcomes',config,clock=lambda:at,outcome_loader=loader)
        output.put(('outcomes',result,len(calls),time.monotonic()-begin))
    except Exception as exc:output.put(('outcomes',getattr(exc,'code',str(exc)),len(calls)))


def due_collector(config, at, proceed, output):
    from inspect_forecast_standalone_activation import fixtures, FixtureOrderBook
    transport=FixtureOrderBook(fixtures()[2]);begin=time.monotonic()
    try:
        result=execute('capture-prospective',config,clock=lambda:at,transport_factory=lambda *_:transport)
        output.put(('collector',result,transport.calls,time.monotonic()-begin))
    except Exception as exc:output.put(('collector',getattr(exc,'code',str(exc)),transport.calls))
    finally:proceed.set()


class OutcomeReplayTests(unittest.TestCase):
    def setUp(self):
        fixture = compatibility_tests.ReportingOutcomeCompatibilityTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for key in ('archive','first','second','third','pages','union','corrected'):
            setattr(self, key, getattr(fixture, key))

    def inventory(self):
        return {str(p.relative_to(self.archive.root)):p.read_bytes()
                for root in (self.archive.raw_root,self.archive.normalized_root,self.archive.manifest_root)
                for p in root.rglob('*') if p.is_file()}

    def reconcile(self, raw=None, pages=None):
        return reconcile_outcomes_from_raw(archive=self.archive, mlb_raw=raw or self.corrected,
            mlb_pages=pages or (self.corrected,), collected_at=self.second)

    def test_reference_and_candidate_changed_and_unchanged_exactly_equal(self):
        frozen=self.archive.root.parent/'frozen'
        shutil.copytree(self.archive.root,frozen)
        for raw,pages in ((self.corrected,(self.corrected,)),(self.union,self.pages)):
            results=[]
            for cls in (lambda archive:archive, OutcomeReplayArchive):
                shutil.rmtree(self.archive.root)  # owned synthetic fixture only
                shutil.copytree(frozen,self.archive.root)
                with patch('forecast_supporting_replay.OutcomeReplayArchive',cls):
                    result=self.reconcile(raw,pages)
                state=replay_pr17_archive(self.archive,analysis_boundary=self.second)
                results.append((result,self.inventory(),_scientific_state_bytes(state)))
            self.assertEqual(results[0],results[1])
            self.assertEqual(results[0][0]['changed'],1 if raw==self.corrected else 0)

    def test_failed_graph_preserves_all_pages_through_view(self):
        before=set(self.inventory())
        with patch('forecast_standalone_schedule_reconciliation.validate_supporting_addition',
                   side_effect=OperationsError('outcome-history-conflict','fixture')):
            with self.assertRaisesRegex(OperationsError,'outcome-history-conflict'):
                self.reconcile(self.union,self.pages)
        entries=[e for e in self.archive.entries() if e['command']=='reconcile-outcomes-failure']
        self.assertEqual(len(entries),2)
        self.assertCountEqual([self.archive.read_verified('raw',e['raw_object_sha256']) for e in entries],self.pages)
        self.assertFalse(any(e['normalized_object_id'] for e in entries))
        self.assertTrue(before<=set(self.inventory()))
        self.assertEqual(self.reconcile()['changed'],1)  # later independent valid work

    def test_source_change_rejects_before_publication(self):
        before=self.inventory();original=OutcomeReplayArchive.mutation_lock
        @contextmanager
        def changed(view):
            (self.archive.raw_root/'unexplained').write_bytes(b'unexplained')
            with original(view):yield
        with patch.object(OutcomeReplayArchive,'mutation_lock',changed):
            with self.assertRaisesRegex(OperationsError,'supporting-source-changed'):
                self.reconcile()
        after=self.inventory();after.pop('raw/unexplained')
        self.assertEqual(after,before)

    def test_fresh_derivation_includes_writes_during_provider_stage(self):
        # Simulate independently committed evidence while acquisition is underway.
        # The command must see the new history, not append a competing successor.
        def loader(at):
            reconcile_outcomes_from_raw(archive=self.archive,mlb_raw=self.corrected,
                mlb_pages=(self.corrected,),collected_at=at-timedelta(seconds=1))
            return self.corrected,(self.corrected,),1
        out=execute('reconcile-outcomes',self.archive.config,clock=lambda:self.second,outcome_loader=loader)
        self.assertEqual((out['changed'],out['provider_calls']),(0,1))
        state=replay_pr17_archive(self.archive,analysis_boundary=self.second)
        self.assertEqual(state.bucket('outcome_histories')[0].latest.away_score,4)

    def test_date_selection_matches_full_replay_and_no_provider_under_lock(self):
        expected=replay_pr17_archive(self.archive,analysis_boundary=self.second)
        self.assertEqual(replay_for_request_dates(self.archive,self.second),expected)
        owned=[False];original=NamespaceArchive.mutation_lock;calls=[]
        @contextmanager
        def locked(source):
            with original(source):
                owned[0]=True
                try:yield
                finally:owned[0]=False
        def get(base,path):
            self.assertFalse(owned[0]);calls.append(path)
            return b'{"dates":[]}'
        with patch.object(NamespaceArchive,'mutation_lock',locked):
            result=load_live_supporting(archive=self.archive,purpose='outcomes',at=self.second,
                public_get=get,clock=lambda:self.second)
        self.assertEqual(result[2],len(calls));self.assertGreater(len(calls),0)

    def test_preflight_reuse_is_exact_boundary_single_use_and_invocation_local(self):
        from forecast_supporting_replay import begin_request_preparation, end_request_preparation, resolve_supporting_authority
        from forecast_standalone_operations import _entry_values, request_identity, Disposition, DesignAuthority
        for changed in (False,True):
            token=begin_request_preparation()
            try:
                resolve_supporting_authority(self.archive,self.second)
                if changed:
                    self.archive.record_failure(entry_values=_entry_values(archive=self.archive,
                        command='fixture-failure',request_id=request_identity({'changed':True}),invoked_at=self.second,
                        endpoint='fixture://failure',disposition=Disposition.TIMEOUT,protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=()))
                with patch('forecast_supporting_replay.replay_pr17_archive',wraps=replay_pr17_archive) as replay:
                    result=replay_for_request_dates(self.archive,self.second)
                    self.assertEqual(replay.call_count,1 if changed else 0)
                    replay_for_request_dates(self.archive,self.second)
                    self.assertEqual(replay.call_count,2 if changed else 1)
                self.assertEqual(result,replay_pr17_archive(self.archive,analysis_boundary=self.second))
            finally:end_request_preparation(token)
        with patch('forecast_supporting_replay.replay_pr17_archive',wraps=replay_pr17_archive) as replay:
            replay_for_request_dates(self.archive,self.second)
            self.assertEqual(replay.call_count,1)

    def test_post_acquisition_reuse_requires_exact_source_and_publication_fence(self):
        from forecast_supporting_replay import begin_request_preparation, end_request_preparation, resolve_supporting_authority
        token=begin_request_preparation()
        try:
            resolve_supporting_authority(self.archive,self.second)
            replay_for_request_dates(self.archive,self.second)
            with patch('forecast_standalone_operations.replay_pr17_archive',side_effect=AssertionError('unnecessary full replay')):
                self.assertEqual(self.reconcile()['changed'],1)
        finally:end_request_preparation(token)
        token=begin_request_preparation()
        try:
            resolve_supporting_authority(self.archive,self.third)
            replay_for_request_dates(self.archive,self.third)
            from forecast_standalone_operations import _entry_values, request_identity, Disposition, DesignAuthority
            self.archive.record_failure(entry_values=_entry_values(archive=self.archive,command='fixture-failure',
                request_id=request_identity({'during-acquisition':True}),invoked_at=self.third,endpoint='fixture://failure',
                disposition=Disposition.TIMEOUT,protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=()))
            with patch('forecast_standalone_operations.replay_pr17_archive',wraps=replay_pr17_archive) as replay:
                reconcile_outcomes_from_raw(archive=self.archive,mlb_raw=self.corrected,
                    mlb_pages=(self.corrected,),collected_at=self.third)
                self.assertEqual(replay.call_count,1)
        finally:end_request_preparation(token)

    def test_malformed_and_zero_cache_budget_preserve_behavior(self):
        with self.assertRaisesRegex(OperationsError,'malformed-response'):
            self.reconcile(b'not json',(b'not json',))
        expected=replay_pr17_archive(self.archive,analysis_boundary=self.second)
        with patch('forecast_supporting_replay.MAX_SOURCE_BYTES',0):
            self.assertEqual(replay_for_request_dates(self.archive,self.second),expected)

    def test_timing_receipts_separate_from_evidence_and_old_heartbeats(self):
        from forecast_standalone_activation import OperationalState
        out=execute('reconcile-outcomes',self.archive.config,clock=lambda:self.second,
            outcome_loader=lambda at:(self.union,self.pages,2))
        receipts=list((self.archive.config.log_root/'replay-timings').glob('*.json'))
        self.assertEqual(len(receipts),1)
        value=json.loads(receipts[0].read_bytes())
        self.assertEqual(value['disposition'],'unchanged')
        self.assertIn('authority',value['stages']);self.assertIn('derivation',value['stages'])
        self.assertTrue(all(v['seconds']>=0 for v in value['stages'].values()))
        self.assertEqual(OperationalState(self.archive.config.log_root/'operational-state').entries()[-1].provider_calls,2)

    def test_diagnostic_write_failure_does_not_reclassify_committed_work(self):
        import io
        from contextlib import redirect_stderr
        from forecast_standalone_activation import OperationalState
        original=Path.open
        def denied(path,*args,**kwargs):
            if 'replay-timings' in path.parts:raise PermissionError('fixture diagnostic denial')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',denied),redirect_stderr(io.StringIO()) as warnings:
            out=execute('reconcile-outcomes',self.archive.config,clock=lambda:self.second,
                outcome_loader=lambda at:(self.corrected,(self.corrected,),1))
        self.assertEqual(out['changed'],1)
        self.assertEqual(OperationalState(self.archive.config.log_root/'operational-state').entries()[-1].disposition,'success')
        self.assertEqual(warnings.getvalue().strip(),'replay-timing-receipt-unavailable')

    def test_reused_derivation_still_rejects_a_late_source_append(self):
        from forecast_supporting_replay import begin_request_preparation, end_request_preparation, resolve_supporting_authority
        from forecast_standalone_operations import _entry_values, request_identity, Disposition, DesignAuthority
        token=begin_request_preparation();original=OutcomeReplayArchive.mutation_lock
        @contextmanager
        def append(view):
            self.archive.record_failure(entry_values=_entry_values(archive=self.archive,command='fixture-failure',
                request_id=request_identity({'late':True}),invoked_at=self.second,endpoint='fixture://failure',
                disposition=Disposition.TIMEOUT,protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=()))
            with original(view):yield
        try:
            resolve_supporting_authority(self.archive,self.second)
            replay_for_request_dates(self.archive,self.second)
            with patch.object(OutcomeReplayArchive,'mutation_lock',append):
                with self.assertRaisesRegex(OperationsError,'supporting-source-changed'):self.reconcile()
        finally:end_request_preparation(token)
        self.assertFalse(any(e['command']=='reconcile-outcomes' for e in self.archive.entries()))
        self.assertEqual(self.reconcile()['changed'],1)

    def test_interrupted_publication_matches_reference_and_stays_non_authoritative(self):
        from forecast_standalone_operations import reconcile_archive
        frozen=self.archive.root.parent/'interruption-source'
        shutil.copytree(self.archive.root,frozen)
        original=NamespaceArchive._publish;results=[]
        for cls in (lambda archive:archive,OutcomeReplayArchive):
            shutil.rmtree(self.archive.root);shutil.copytree(frozen,self.archive.root)
            count=[0]
            def interrupted(source,target,body):
                count[0]+=1
                if count[0]==4:raise OperationsError('injected-interruption','fixture')
                return original(source,target,body)
            with patch('forecast_supporting_replay.OutcomeReplayArchive',cls),patch.object(NamespaceArchive,'_publish',interrupted):
                with self.assertRaisesRegex(OperationsError,'injected-interruption'):self.reconcile()
            results.append((self.inventory(),reconcile_archive(self.archive)))
        self.assertEqual(results[0],results[1]);self.assertTrue(results[0][1].blocking)

    def test_corrupt_source_blocks_before_provider(self):
        path=next(self.archive.raw_root.glob('*/*'));path.chmod(0o600);path.write_bytes(b'corrupt')
        with self.assertRaises(OperationsError):
            execute('reconcile-outcomes',self.archive.config,clock=lambda:self.second,
                outcome_loader=lambda _:self.fail('invalid authority reached provider'))


class OutcomeConcurrencyTests(unittest.TestCase):
    def test_real_due_capture_during_acquisition_and_successful_reconciliation(self):
        from forecast_standalone_activation import canonical_prospective_authority, initialize_activation, refresh_supporting_from_raw
        from forecast_standalone_operations import DeploymentConfig, OperatingMode, RetryPolicy, APPROVED_ACTIVATION_AT
        from forecast_prospective_projection import rebuild_projection
        from inspect_forecast_standalone_activation import fixtures
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,protocol=canonical_prospective_authority()
            config=DeploymentConfig('outcome-concurrency','outcome-concurrency',OperatingMode.ACTIVATED,
                root/'activated/outcome-concurrency/primary',root/'activated/outcome-concurrency/secondary',
                'https://fixture.invalid',RetryPolicy(1,1,1,(),0),1,root/'logs',
                research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT)
            archive=NamespaceArchive(config);at=datetime(2026,9,5,4,tzinfo=timezone.utc)
            initialize_activation(archive,datetime(2026,8,28,tzinfo=timezone.utc))
            mlb,catalog,_=fixtures()
            refresh_supporting_from_raw(archive=archive,mlb_raw=mlb,kalshi_raw=catalog,collected_at=at-timedelta(minutes=1))
            rebuild_projection(archive,at)
            context=multiprocessing.get_context('spawn');ready=context.Event();proceed=context.Event();output=context.Queue()
            outcome=context.Process(target=outcome_worker,args=(config,at,ready,proceed,output))
            collector=context.Process(target=due_collector,args=(config,at,proceed,output))
            outcome.start()
            try:
                self.assertTrue(ready.wait(15));collector.start()
                results=dict((row[0],row) for row in (output.get(timeout=20),output.get(timeout=20)))
                outcome.join(5);collector.join(5)
                self.assertEqual((outcome.exitcode,collector.exitcode),(0,0))
            finally:
                for worker in (outcome,collector):
                    if worker.is_alive():worker.terminate();worker.join(5)
            self.assertIsInstance(results['outcomes'][1],dict,results)
            self.assertIsInstance(results['collector'][1],dict,results)
            self.assertEqual(results['collector'][2],1,results)
            self.assertLess(results['collector'][3],20,results)
            state=replay_pr17_archive(archive,analysis_boundary=at)
            attempts=[x for x in state.bucket('attempts') if x.provider_call_occurred]
            self.assertEqual(len(attempts),1);self.assertEqual(type(attempts[0].result).__name__,'CapturedValid')
            self.assertEqual(attempts[0].slot,0)


if __name__=='__main__':unittest.main()
