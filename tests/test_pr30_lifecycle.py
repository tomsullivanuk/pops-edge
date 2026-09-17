"""Offline PR30 checkpoint, lifecycle, health and commissioning acceptance gates."""
import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from forecast_operational_lifecycle import PhaseDisposition, run_cycle
from forecast_prospective_projection import load_projection, rebuild_projection, projection_path, assert_boundary
from forecast_standalone_activation import OperationalHeartbeat, OperationalState, health_from_operational_state, verify_pinned_checkout
from forecast_standalone_operations import OperationsError, canonical_bytes, rebuild_index, index_health, sha256_bytes
from operate_forecast_standalone_activation import execute
from tests import test_forecast_standalone_commissioning as commissioning
from tests import test_forecast_standalone_operations as operations


class CheckpointAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=operations.OperationsTest();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.g,self.at=self.fixture.seed_prospective();self.archive=self.fixture.archive

    def capture(self):
        self.transport=operations.SequenceTransport(TimeoutError())
        from forecast_standalone_operations import discover_and_capture_prospective
        return discover_and_capture_prospective(archive=self.archive,clock=lambda:self.at,transport_factory=lambda *_:self.transport)

    def test_exact_match_reuses_verified_sources_and_full_state_is_identical(self):
        cold=rebuild_projection(self.archive,self.at)
        with patch('forecast_standalone_operations._contracts_from_entry',side_effect=AssertionError('cold replay in hot path')):
            boundary,hot=load_projection(self.archive,self.at)
        self.assertEqual(canonical_bytes(cold),canonical_bytes(hot))
        self.assertEqual(boundary.source_bytes,0)
        with self.archive.mutation_lock():assert_boundary(self.archive,boundary)

    def test_decimal_bearing_state_passes_full_rebuild_without_broadening_operations_canonicalization(self):
        from dataclasses import replace
        from decimal import Decimal
        from forecast_standalone_operations import archive_pr17_authority
        archive_pr17_authority(self.archive,(self.g['observation'],),recorded_at=self.at)
        with self.assertRaisesRegex(OperationsError,'unsupported-canonical-value'):
            canonical_bytes(Decimal('0.54'))
        rebuild_projection(self.archive,self.at)
        cold=rebuild_projection(self.archive,self.at)
        from forecast_prospective_projection import _scientific_state_bytes
        _,hot=load_projection(self.archive,self.at)
        observations=hot.bucket('market_observations')
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0].quotes.yes_bid,Decimal('0.54'))
        self.assertEqual(_scientific_state_bytes(cold),_scientific_state_bytes(hot))
        changed_states=(
            replace(cold,analysis_boundary=cold.analysis_boundary+timedelta(microseconds=1)),
            replace(cold,objects=cold.objects[:-1]),
            replace(cold,graph=cold.graph[:-1]),
            replace(cold,reports=(self.g['observation'],)),
            replace(cold,source_manifest_ids=cold.source_manifest_ids[:-1]),
        )
        self.assertTrue(all(_scientific_state_bytes(cold)!=_scientific_state_bytes(changed) for changed in changed_states))

    def test_decimal_bearing_state_difference_revokes_checkpoint_lineage(self):
        from dataclasses import replace
        from decimal import Decimal
        import forecast_prospective_projection as projection
        from forecast_standalone_operations import archive_pr17_authority
        archive_pr17_authority(self.archive,(self.g['observation'],),recorded_at=self.at)
        rebuild_projection(self.archive,self.at)
        rebuild_projection(self.archive,self.at)
        path=projection_path(self.archive);lineage=json.loads(path.read_bytes())['projection']['lineage'];changed=[]
        original=projection.replay_boundary
        def replay(boundary,at):
            state=original(boundary,at)
            if boundary._checkpoint_lineage!=lineage:return state
            observation=next(value for value in state.objects if type(value).__name__=='MarketObservation')
            replacement=replace(observation,quotes=replace(observation.quotes,yes_bid=Decimal('0.53')))
            objects=tuple(replacement if value is observation else value for value in state.objects)
            graph=tuple((name,tuple(replacement if value is observation else value for value in values)) for name,values in state.graph)
            changed.append(1);return replace(state,objects=objects,graph=graph)
        with patch.object(projection,'replay_boundary',side_effect=replay),self.assertRaisesRegex(OperationsError,'projection-replay-conflict'):
            projection.rebuild_projection(self.archive,self.at)
        self.assertEqual(changed,[1])
        self.assertFalse(path.exists())
        self.assertTrue((self.archive.root/f'prospective-projection-rejected-{lineage}.json').exists())

    def test_excessive_delta_fails_before_transport(self):
        self.capture()
        with patch('forecast_prospective_projection.MAX_DELTA_MANIFESTS',0):
            with self.assertRaisesRegex(OperationsError,'projection-budget-exceeded'):self.capture()
        self.assertEqual(self.transport.calls,[])

    def test_future_checkpoint_and_bad_checksum_fail_before_transport(self):
        path=projection_path(self.archive);original=path.read_bytes()
        for future in (False,True):
            value=json.loads(original)
            if future:
                value['projection']['built_at']=(self.at+timedelta(days=1)).isoformat()
                value['sha256']=sha256_bytes(canonical_bytes(value['projection']))
            else:value['sha256']='0'*64
            path.write_bytes(canonical_bytes(value))
            with self.assertRaises(OperationsError):self.capture()
            self.assertEqual(self.transport.calls,[])

    def test_atomic_publish_interruption_preserves_last_complete_checkpoint(self):
        path=projection_path(self.archive);original=path.read_bytes()
        self.capture()
        with patch('forecast_prospective_projection.os.replace',side_effect=OSError('synthetic interruption')):
            with self.assertRaises(OperationsError):load_projection(self.archive,self.at)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(list(self.archive.root.glob('.prospective-*.partial')),[])
        # A later independent invocation replays the still immutable delta.
        _,hot=load_projection(self.archive,self.at)
        cold=rebuild_projection(self.archive,self.at)
        self.assertEqual(canonical_bytes(hot),canonical_bytes(cold))

    def test_ambiguous_manifest_lineage_fails_before_transport(self):
        from forecast_standalone_operations import ManifestEntry, Disposition, DesignAuthority
        parent=self.archive.entries()[0]
        for number in range(2):
            values=self.fixture.entry_values(Disposition.TIMEOUT)
            values.update(command='fixture-correction',invocation_id=f'branch-{number}',
                protocol_id=parent.get('protocol_id'),design_authority=DesignAuthority(parent['design_authority']),
                acquired_at=self.at,predecessor_id=parent['manifest_entry_id'],correction_reason='synthetic branch')
            entry=ManifestEntry.create(**values,namespace=self.archive.config.namespace,operating_mode=self.archive.config.mode,
                raw_object_sha256=None,normalized_object_id=None,normalized_schema_version=None)
            self.archive._publish(self.archive._path('manifest',entry.manifest_entry_id),canonical_bytes(entry))
        with self.assertRaisesRegex(OperationsError,'ambiguous-correction'):self.capture()
        self.assertEqual(self.transport.calls,[])

    def test_interruption_after_atomic_replace_leaves_usable_complete_state(self):
        self.capture()
        with patch('forecast_prospective_projection._sync_directory',side_effect=OSError('synthetic fsync interruption')):
            with self.assertRaises(OperationsError):load_projection(self.archive,self.at)
        _,state=load_projection(self.archive,self.at)
        self.assertEqual(canonical_bytes(state),canonical_bytes(rebuild_projection(self.archive,self.at)))
        self.assertEqual(self.capture().provider_request_count,0)

    def test_daily_replay_detects_checksumming_an_incorrect_contribution(self):
        path=projection_path(self.archive);value=json.loads(path.read_bytes())
        contributions=value['projection']['contributions']
        for identity,objects in contributions.items():
            if objects:
                objects.append(objects[0]);break
        value['sha256']=sha256_bytes(canonical_bytes(value['projection']))
        path.write_bytes(canonical_bytes(value))
        # Even a semantically deduplicated altered prefix is detected by the
        # explicit per-manifest contribution comparison at full rebuild.
        with self.assertRaisesRegex(OperationsError,'projection-replay-conflict'):rebuild_projection(self.archive,self.at)
        self.assertFalse(path.exists())
        self.assertEqual(len(list(self.archive.root.glob('prospective-projection-rejected-*.json'))),1)
        with self.assertRaisesRegex(OperationsError,'projection-absent'):self.capture()
        self.assertEqual(self.transport.calls,[])

    def corrupt_contribution(self):
        path = projection_path(self.archive)
        value = json.loads(path.read_bytes())
        for objects in value['projection']['contributions'].values():
            if objects:
                objects.append(objects[0])
                break
        value['sha256'] = sha256_bytes(canonical_bytes(value['projection']))
        path.write_bytes(canonical_bytes(value))
        return path.read_bytes()

    def immutable_bytes(self):
        return {str(path): path.read_bytes()
                for root in (self.archive.raw_root, self.archive.normalized_root, self.archive.manifest_root)
                for path in root.glob('*/*') if path.is_file()}

    def test_rejection_after_collector_preparation_revokes_request_and_allows_independent_rebuild(self):
        from forecast_standalone_operations import discover_and_capture_prospective
        self.corrupt_contribution()
        before = self.immutable_bytes()
        transport = operations.SequenceTransport(TimeoutError())
        events = []

        def factory(*_):
            with self.assertRaisesRegex(OperationsError, 'projection-replay-conflict'):
                rebuild_projection(self.archive, self.at)
            events.append(projection_path(self.archive).exists())
            return transport

        with self.assertRaisesRegex(OperationsError, 'projection-rejected'):
            discover_and_capture_prospective(archive=self.archive, clock=lambda: self.at,
                                             transport_factory=factory)
        self.assertEqual(events, [False])
        self.assertEqual(transport.calls, [])
        self.assertEqual(self.immutable_bytes(), before)
        self.assertEqual(list((self.archive.root / 'prospective-requests').glob('*.json')), [])
        rejected = {p: p.read_bytes() for p in self.archive.root.glob('prospective-projection-rejected-*.json')}
        cold = rebuild_projection(self.archive, self.at)
        _, hot = load_projection(self.archive, self.at)
        self.assertEqual(canonical_bytes(cold), canonical_bytes(hot))
        self.assertEqual(self.immutable_bytes(), before)
        self.assertEqual(self.capture().provider_request_count, 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.capture().provider_request_count, 0)
        self.assertEqual(self.transport.calls, [])
        self.assertEqual({p: p.read_bytes() for p in rejected}, rejected)

    def test_prepared_delta_cannot_republish_rejected_lineage_even_after_full_rebuild(self):
        from forecast_prospective_projection import _prepare_checkpoint, _publish, replay_boundary
        self.capture()  # Real fixture capture supplies a bounded append delta.
        self.corrupt_contribution()
        prepared, recorded, current = _prepare_checkpoint(self.archive, self.at)
        self.assertNotEqual(recorded['source_manifest_ids'], current['source_manifest_ids'])
        replay_boundary(prepared, self.at)
        _publish(self.archive, prepared, self.at)
        self.assertEqual(json.loads(projection_path(self.archive).read_bytes())['projection']['lineage'], recorded['lineage'])
        before = self.immutable_bytes()
        markers = {p: p.read_bytes() for p in self.archive.root.glob('prospective-*/*.json')}
        with self.assertRaisesRegex(OperationsError, 'projection-replay-conflict'):
            rebuild_projection(self.archive, self.at)
        for rebuilt in (False, True):
            if rebuilt:
                rebuild_projection(self.archive, self.at)
            with self.assertRaisesRegex(OperationsError, 'projection-rejected'):
                _publish(self.archive, prepared, self.at)
            with self.archive.mutation_lock(), self.assertRaisesRegex(OperationsError, 'projection-rejected'):
                assert_boundary(self.archive, prepared)
        self.assertNotEqual(json.loads(projection_path(self.archive).read_bytes())['projection']['lineage'], recorded['lineage'])
        self.assertEqual(self.immutable_bytes(), before)
        self.assertEqual({p: p.read_bytes() for p in markers}, markers)
        self.assertEqual(self.capture().provider_request_count, 0)
        self.assertEqual(self.transport.calls, [])

    def test_rejection_revokes_replacement_published_during_full_comparison(self):
        from forecast_prospective_projection import _publish, replay_boundary
        original = self.corrupt_contribution()
        lineage = json.loads(original)['projection']['lineage']
        published = []

        def replay(view, at):
            state = replay_boundary(view, at)
            if view._checkpoint_lineage == lineage:
                _publish(self.archive, view, at + timedelta(microseconds=1))
                published.append(projection_path(self.archive).read_bytes())
            return state

        with patch('forecast_prospective_projection.replay_boundary', side_effect=replay):
            with self.assertRaisesRegex(OperationsError, 'projection-replay-conflict'):
                rebuild_projection(self.archive, self.at)
        self.assertEqual(len(published), 1)
        self.assertNotEqual(published[0], original)
        self.assertFalse(projection_path(self.archive).exists())
        with self.assertRaisesRegex(OperationsError, 'projection-absent'):
            self.capture()
        self.assertEqual(self.transport.calls, [])

    def test_durable_rejection_survives_interruption_before_cache_removal(self):
        original = self.corrupt_contribution()
        path = projection_path(self.archive)
        unlink = Path.unlink

        def interrupted(target, *args, **kwargs):
            if target == path:
                raise OSError('synthetic interruption before cache removal')
            return unlink(target, *args, **kwargs)

        with patch.object(Path, 'unlink', interrupted):
            with self.assertRaisesRegex(OSError, 'synthetic interruption'):
                rebuild_projection(self.archive, self.at)
        self.assertEqual(path.read_bytes(), original)
        # A fresh local process must observe the persisted revocation too.
        import multiprocessing
        context = multiprocessing.get_context('spawn')
        result = context.Queue()
        worker = context.Process(target=check_rejected_in_process,
                                 args=(self.archive.config, self.at, result))
        worker.start()
        worker.join(10)
        if worker.is_alive():
            worker.terminate(); worker.join()
            self.fail('rejection check deadlocked')
        self.assertEqual(worker.exitcode, 0)
        self.assertEqual(result.get(timeout=2), ('projection-rejected', 0))
        result.close(); result.join_thread()
        rebuild_projection(self.archive, self.at)
        self.assertEqual(self.capture().provider_request_count, 1)


def check_rejected_in_process(config, at, result):
    archive = operations.NamespaceArchive(config)
    transport = operations.SequenceTransport(TimeoutError())
    try:
        operations.discover_and_capture_prospective(
            archive=archive, clock=lambda: at, transport_factory=lambda *_: transport)
    except OperationsError as exc:
        result.put((exc.code, len(transport.calls)))
    else:
        result.put(('unexpected-success', len(transport.calls)))


class LifecycleAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=commissioning.CommissioningTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.archive=self.fixture.archive;self.config=self.fixture.config;self.at=datetime(2026,9,9,18,tzinfo=timezone.utc)
        self.state=OperationalState(self.config.log_root/'operational-state')

    def heartbeat(self,command,at=None,disposition='success',failure=None):
        at=at or self.at
        self.state.append(OperationalHeartbeat('1',command,at,at,disposition,0,0,0,failure))

    def test_rebuild_retry_allows_downstream_maintenance_and_records_exhaustion(self):
        import forecast_prospective_projection as projection
        original = projection.rebuild_projection
        attempts = []
        outputs = {}
        def rebuild(archive, at):
            attempts.append(at)
            if len(attempts) == 1:
                raise OperationsError('projection-stale', 'concurrent publication')
            return original(archive, at)
        def run(command):
            if command in ('rebuild-prospective-projection', 'rebuild-index', 'sync-secondary'):
                outputs[command] = execute(command, self.config, clock=lambda:self.at)
                return outputs[command]
            return {'disposition':'success', 'provider_calls':0}
        with patch.object(projection, 'rebuild_projection', side_effect=rebuild):
            result = run_cycle(archive=self.archive, state=self.state, clock=lambda:self.at, run=run)
        self.assertEqual(result['disposition'], 'success')
        self.assertEqual(outputs['rebuild-prospective-projection']['rebuild_attempts'], 2)
        self.assertEqual(outputs['sync-secondary']['disposition'], 'success')
        later = self.at + timedelta(days=1)
        with patch.object(projection, 'rebuild_projection', side_effect=OperationsError('projection-stale', 'continuous contention')) as rebuild:
            with self.assertRaisesRegex(OperationsError, 'projection-stale'):
                execute('rebuild-prospective-projection', self.config, clock=lambda:later)
            self.assertEqual(rebuild.call_count, 3)
        last = self.state.entries()[-1]
        self.assertEqual((last.failure_code, last.provider_calls), ('projection-stale', 0))

    def test_sequential_typed_phases_and_dependency_failure(self):
        order=[]
        def run(command):
            order.append(command)
            if command=='reconcile-outcomes':raise OperationsError('synthetic-failure','offline fixture')
            return {'disposition':'success','provider_calls':0}
        result=run_cycle(archive=self.archive,state=self.state,clock=lambda:self.at,run=run)
        self.assertEqual(order,['refresh-supporting','reconcile-outcomes','health-report'])
        self.assertEqual([x['disposition'] for x in result['phases']],['success','failed','dependency-failed','dependency-failed','dependency-failed','success'])
        self.assertEqual(result['disposition'],'failed')
        self.assertEqual(len([x for x in self.state.entries() if x.disposition=='dependency-failed']),3)

    def test_whole_cycle_exclusion_visible_skipped_hour_and_collector_independence(self):
        entered=threading.Event();release=threading.Event();errors=[]
        def run(command):
            if command=='rebuild-prospective-projection':
                entered.set()
                if not release.wait(10):raise AssertionError('timeout')
            return {'disposition':'success','provider_calls':0}
        def worker():
            try:run_cycle(archive=self.archive,state=self.state,clock=lambda:self.at,run=run)
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=worker);thread.start()
        try:
            self.assertTrue(entered.wait(5))
            result=execute('lifecycle-cycle',self.config,clock=lambda:self.at+timedelta(hours=1))
            self.assertEqual(result['disposition'],'skipped-cycle')
            self.assertEqual(result['provider_calls'],0)
            self.assertIn('skipped-cycle',[x.disposition for x in self.state.entries()])
            from forecast_prospective_projection import collector_lock
            with collector_lock(self.archive):load_projection(self.archive,self.at)
        finally:release.set();thread.join(10)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])

    def test_long_owner_records_hours_that_launchd_cannot_invoke(self):
        current=[self.at.replace(minute=7)]
        def run(command):
            if command=='rebuild-prospective-projection':current[0]+=timedelta(hours=2,minutes=10)
            return {'disposition':'success','provider_calls':0}
        result=run_cycle(archive=self.archive,state=self.state,clock=lambda:current[0],run=run)
        skipped=[x for x in self.state.entries() if x.command=='lifecycle-hour']
        self.assertEqual(len(skipped),2)
        self.assertEqual(len(result['skipped_scheduled_hours']),2)
        self.assertTrue(all(x.disposition=='skipped-cycle' and x.provider_calls==0 for x in skipped))
        self.assertTrue(all(x.started_at<x.completed_at for x in skipped))

    def test_successful_phase_completion_controls_hourly_daily_due(self):
        for command in ('refresh-supporting','reconcile-outcomes','rebuild-prospective-projection','rebuild-index','sync-secondary'):
            self.heartbeat(command)
        order=[]
        def run(command):order.append(command);return {'disposition':'success','provider_calls':0}
        result=run_cycle(archive=self.archive,state=self.state,clock=lambda:self.at+timedelta(minutes=1),run=run)
        self.assertEqual(order,['refresh-prospective-projection','health-report'])
        self.assertEqual(sum(x['disposition']=='not-due' for x in result['phases']),4)

    def test_health_recovers_retains_failures_and_allows_expected_index_lag(self):
        rebuild_index(self.archive)
        earlier=self.at-timedelta(minutes=1)
        self.heartbeat('capture-prospective',earlier,'failed','projection-budget-exceeded')
        for command in ('capture-prospective','refresh-supporting','reconcile-outcomes','rebuild-prospective-projection','rebuild-index','sync-secondary'):
            self.heartbeat(command)
        # Append an immutable no-authority failure: index legitimately lags, and
        # this does not disappear from the archive or become scientific Evidence.
        from forecast_standalone_operations import _entry_values,Disposition,DesignAuthority
        values=_entry_values(archive=self.archive,command='reconcile-outcomes-failure',request_id='fixture',invoked_at=self.at,
            endpoint='fixture://offline',disposition=Disposition.TIMEOUT,protocol_id=None,design=DesignAuthority.SUPPORTING)
        self.archive.record_failure(entry_values=values)
        health=health_from_operational_state(archive=self.archive,state=self.state,trusted_at=self.at,free_disk=lambda _:10**9)
        self.assertTrue(health.ready,health.current_blockers)
        self.assertEqual(health.index_state,'append-only-lag')
        self.assertIn('capture-prospective:projection-budget-exceeded',health.recent_failures)
        self.assertIn('capture-prospective:projection-budget-exceeded',health.superseded_failures)
        self.assertGreater(health.secondary_lag,0)
        self.heartbeat('capture-prospective',self.at+timedelta(seconds=1),'failed','projection-invalid')
        health=health_from_operational_state(archive=self.archive,state=self.state,trusted_at=self.at+timedelta(seconds=2),free_disk=lambda _:10**9)
        self.assertFalse(health.ready)
        self.assertIn('capture-prospective:projection-invalid',health.current_blockers)

    def test_pinned_checkout_guard_refuses_dirty_branch_or_wrong_revision(self):
        import subprocess
        def result(code,text):return subprocess.CompletedProcess([],code,text,'')
        revision='a'*40
        with patch('subprocess.run',side_effect=[result(0,revision),result(1,''),result(0,'')]):
            self.assertEqual(verify_pinned_checkout(Path('/synthetic'),revision),revision)
        for values in ([result(0,revision),result(0,'refs/heads/main'),result(0,'')],
                       [result(0,revision),result(1,''),result(0,' M modified.py')],
                       [result(0,'b'*40),result(1,''),result(0,'')]):
            with patch('subprocess.run',side_effect=values),self.assertRaisesRegex(OperationsError,'deployment-checkout-unsafe'):
                verify_pinned_checkout(Path('/synthetic'),revision)
