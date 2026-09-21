"""Offline startup acceptance: no production files, scheduler or providers."""
import fcntl
import json
import base64
import pickle
import subprocess
import sys
from datetime import timedelta
import unittest
from pathlib import Path
from unittest.mock import patch

import forecast_startup_recovery as startup
import forecast_prospective_projection as projection
from forecast_standalone_operations import OperationsError, canonical_bytes, sha256_bytes
from forecast_standalone_activation import OperationalState
from operate_forecast_standalone_activation import execute, main
from tests import test_forecast_standalone_operations as fixtures
from tests import test_forecast_standalone_commissioning as commissioning


class StartupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OperationsTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        _, self.at = self.fixture.seed_prospective()
        self.archive = self.fixture.archive
        self.boot = patch.object(startup, 'current_boot_id', return_value='boot-one').start()
        self.addCleanup(patch.stopall)

    def run_gate(self, **kwargs):
        return startup.ensure_startup(self.archive, clock=lambda:self.at, **kwargs)

    def sources(self):
        return {str(p):p.read_bytes() for family in ('raw','normalized','manifest')
                for p in (self.archive.root/family).rglob('*') if p.is_file()}

    def test_first_boot_verifies_then_process_restarts_reuse_receipt(self):
        before = self.sources()
        real = startup.rebuild_projection_with_retry
        with patch.object(startup, 'rebuild_projection_with_retry', wraps=real) as rebuild:
            self.assertEqual(self.run_gate()['startup'], 'rebuilt')
            for _ in range(3):
                self.assertEqual(self.run_gate()['startup'], 'already-verified')
            self.assertEqual(rebuild.call_count, 1)
        self.assertEqual(before, self.sources())

    def test_new_boot_device_change_rebuilds_without_weakening_signature_check(self):
        self.run_gate()
        before = self.sources()
        original = projection._signature
        self.boot.return_value = 'boot-two'
        def changed_device(path):
            signature = original(path)
            return (signature[0]+1, *signature[1:])
        with patch.object(projection, '_signature', side_effect=changed_device):
            with self.assertRaisesRegex(OperationsError, 'projection-invalid'):
                projection.load_projection(self.archive, self.at)
            self.assertEqual(self.run_gate()['startup'], 'rebuilt')
            boundary, hot = projection.load_projection(self.archive, self.at)
            self.assertEqual(boundary.source_bytes, 0)
            self.assertEqual(projection._scientific_state_bytes(hot),
                             projection._scientific_state_bytes(projection.rebuild_projection(self.archive,self.at)))
        self.assertEqual(before, self.sources())

    def test_corrupt_source_blocks_and_never_automatically_retries_even_next_boot(self):
        entry = self.archive.entries()[0]
        path = self.archive._path('normalized', entry['normalized_object_id'])
        path.chmod(0o644)
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(OperationsError, 'capture-persistence-unsafe'):
            self.run_gate()
        with patch.object(startup, 'rebuild_projection_with_retry') as rebuild:
            for boot in ('boot-one','boot-two'):
                self.boot.return_value=boot
                with self.assertRaisesRegex(OperationsError, 'startup-recovery-blocked'):
                    self.run_gate()
            rebuild.assert_not_called()

    def test_interrupted_rebuild_stays_blocked_until_explicit_operator_retry(self):
        with patch.object(startup, 'rebuild_projection_with_retry', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_gate()
        self.assertEqual(startup._load(startup.receipt_directory(self.archive)/'current.json')['status'],'running')
        with self.assertRaisesRegex(OperationsError,'startup-recovery-blocked'):self.run_gate()
        self.assertEqual(self.run_gate(retry=True)['startup'],'rebuilt')

    def test_rejected_lineage_never_automatically_rebuilt(self):
        value = projection._read(self.archive)
        rejected = self.archive.root/f"prospective-projection-rejected-{value['lineage']}.json"
        rejected.write_text('negative fence remains authoritative even if diagnostic bytes damaged')
        before=projection.projection_path(self.archive).read_bytes()
        with self.assertRaisesRegex(OperationsError,'projection-rejected'):self.run_gate()
        with self.assertRaisesRegex(OperationsError,'projection-rejected'):self.run_gate(retry=True)
        self.assertEqual(before,projection.projection_path(self.archive).read_bytes())
        self.assertTrue(rejected.exists())

    def test_absent_checkpoint_with_rejection_record_is_not_rehabilitated(self):
        checkpoint=projection._read(self.archive)
        (self.archive.root/f"prospective-projection-rejected-{checkpoint['lineage']}.json").write_text('{}')
        projection.projection_path(self.archive).unlink()
        with self.assertRaisesRegex(OperationsError,'projection-rejected'):self.run_gate()
        self.assertFalse(projection.projection_path(self.archive).exists())

    def test_corrupt_disposable_cache_rebuilt_from_unchanged_sources(self):
        before=self.sources()
        projection.projection_path(self.archive).write_bytes(b'invalid cache')
        self.assertEqual(self.run_gate()['startup'],'rebuilt')
        projection.load_projection(self.archive,self.at)
        self.assertEqual(before,self.sources())

    def test_unresolved_request_marker_blocks_without_clearing_it(self):
        with self.archive.mutation_lock():
            projection.begin_request(self.archive,'prior-protocol','prior-opportunity')
        marker=projection._request_path(self.archive,'prior-protocol','prior-opportunity')
        before=marker.read_bytes()
        with self.assertRaisesRegex(OperationsError,'prospective-publication-ambiguous'):self.run_gate()
        self.assertEqual(marker.read_bytes(),before)

    def test_concurrent_job_returns_busy_without_rebuild_or_receipt(self):
        folder=startup.receipt_directory(self.archive)
        folder.mkdir(parents=True)
        with (folder/'recovery.lock').open('a+b') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(startup,'rebuild_projection_with_retry') as rebuild:
                with self.assertRaisesRegex(OperationsError,'startup-recovery-busy'):self.run_gate()
                rebuild.assert_not_called()
            self.assertFalse((folder/'current.json').exists())
        self.assertEqual(self.run_gate()['startup'],'rebuilt')

    def test_publication_failure_is_sticky_and_preserves_checkpoint(self):
        before=projection.projection_path(self.archive).read_bytes()
        with patch.object(projection.os,'replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):self.run_gate()
        self.assertEqual(before,projection.projection_path(self.archive).read_bytes())
        # Specifically fail checkpoint publication after intent is durable.
        with patch.object(projection,'_publish',side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(OperationsError,'startup-recovery-io-failure'):self.run_gate()
        with self.assertRaisesRegex(OperationsError,'startup-recovery-blocked'):self.run_gate()

    def test_bad_receipt_fails_closed_and_explicit_retry_still_checks_archive(self):
        self.run_gate()
        receipt=startup.receipt_directory(self.archive)/'current.json'
        receipt.write_bytes(b'broken')
        with self.assertRaisesRegex(OperationsError,'startup-receipt-invalid'):self.run_gate()
        self.assertEqual(self.run_gate(retry=True)['startup'],'rebuilt')

    def test_success_receipt_cannot_authorize_reversed_clock(self):
        self.run_gate()
        with self.assertRaisesRegex(OperationsError,'trusted-clock-invalid'):
            startup.ensure_startup(self.archive,clock=lambda:self.at-timedelta(seconds=1))

    def test_interruption_after_rebuild_before_receipt_is_still_blocked(self):
        original=startup._save
        def save(path,value):
            if value['status']=='verified':raise KeyboardInterrupt
            original(path,value)
        with patch.object(startup,'_save',side_effect=save):
            with self.assertRaises(KeyboardInterrupt):self.run_gate()
        # The checkpoint is complete, but startup completion was never accepted.
        projection.load_projection(self.archive,self.at)
        with self.assertRaisesRegex(OperationsError,'startup-recovery-blocked'):self.run_gate()

    def test_stale_publication_retry_is_bounded_and_then_sticky(self):
        with patch.object(projection,'rebuild_projection',side_effect=OperationsError('projection-stale','race')) as rebuild:
            with self.assertRaisesRegex(OperationsError,'projection-stale'):self.run_gate()
            self.assertEqual(rebuild.call_count,3)
            with self.assertRaisesRegex(OperationsError,'startup-recovery-blocked'):self.run_gate()
            self.assertEqual(rebuild.call_count,3)

    def child(self, boot, *, interrupt=False, retry=False):
        # Configuration is generated entirely by this fixture, never external input.
        program = '''
import base64, pickle, sys, os
from datetime import datetime
from unittest.mock import patch
import forecast_startup_recovery as startup
from forecast_standalone_operations import NamespaceArchive, OperationsError
archive=NamespaceArchive(pickle.loads(base64.b64decode(sys.argv[1])))
with patch.object(startup, 'current_boot_id', return_value=sys.argv[3]):
    if sys.argv[4]=='True':
        startup.rebuild_projection_with_retry=lambda *a,**k:os._exit(71)
    try:
        result=startup.ensure_startup(archive,clock=lambda:datetime.fromisoformat(sys.argv[2]),retry=sys.argv[5]=='True')
        print(result['startup'])
    except OperationsError as exc:
        print(exc.code)
        sys.exit(72)
'''
        return subprocess.run([sys.executable,'-c',program,
            base64.b64encode(pickle.dumps(self.archive.config)).decode(),self.at.isoformat(),boot,str(interrupt),str(retry)],
            capture_output=True,text=True,timeout=30,cwd=Path(__file__).resolve().parents[1])

    def test_separate_process_restart_and_new_boot(self):
        for boot,expected in (('first','rebuilt'),('first','already-verified'),('second','rebuilt')):
            result=self.child(boot)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),expected)

    def test_actual_process_death_after_intent_is_sticky(self):
        self.assertEqual(self.child('first',interrupt=True).returncode,71)
        result=self.child('first')
        self.assertEqual(result.returncode,72)
        self.assertEqual(result.stdout.strip(),'startup-recovery-blocked')
        self.assertEqual(self.child('second').returncode,72)
        result=self.child('second',retry=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'rebuilt')


class StartupCompositionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=commissioning.CommissioningTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_failed_gate_prevents_both_job_bodies_and_records_zero_calls(self):
        for command in ('capture-prospective','lifecycle-cycle'):
            with self.subTest(command=command), patch.object(startup,'ensure_startup',side_effect=OperationsError('startup-recovery-blocked','fixture')), \
                    patch('forecast_operational_lifecycle.run_cycle') as cycle, \
                    patch('operate_forecast_standalone_activation.invoke_activated_prospective') as capture:
                with self.assertRaisesRegex(OperationsError,'startup-recovery-blocked'):
                    execute(command,self.fixture.config,clock=lambda:self.fixture.now,startup_check=True)
                cycle.assert_not_called();capture.assert_not_called()
        entries=OperationalState(self.fixture.config.log_root/'operational-state').entries()
        self.assertEqual({x.command for x in entries},{'verify-startup','capture-prospective','lifecycle-cycle'})
        self.assertTrue(all(x.provider_calls==0 and x.disposition=='failed' for x in entries))

    def test_main_enables_gate_for_both_scheduled_commands(self):
        config=self.fixture.config
        for command in ('capture-prospective','lifecycle-cycle'):
            with patch('operate_forecast_standalone_activation.DeploymentConfig.from_json',return_value=config), \
                    patch('operate_forecast_standalone_activation.execute',return_value={'disposition':'success'}) as run:
                self.assertEqual(main(['--config','unused',command]),0)
                self.assertTrue(run.call_args.kwargs['startup_check'])

    def test_manual_retry_is_restricted_to_startup_command(self):
        self.assertNotEqual(main(['--config','unused','capture-prospective','--retry-startup']),0)

    def test_kernel_identity_unavailable_stops_without_rebuild(self):
        with patch.object(startup,'current_boot_id',side_effect=OperationsError('startup-identity-unavailable','fixture')), \
                patch.object(startup,'rebuild_projection_with_retry') as rebuild:
            with self.assertRaisesRegex(OperationsError,'startup-identity-unavailable'):
                execute('verify-startup',self.fixture.config,clock=lambda:self.fixture.now)
            rebuild.assert_not_called()

    def test_successful_offline_startup_then_real_collector_does_not_invent_requests(self):
        config=self.fixture.config
        with patch.object(startup,'current_boot_id',return_value='first'):
            result=execute('capture-prospective',config,clock=lambda:self.fixture.now,
                transport_factory=lambda *_:self.fail('No scheduled opportunities; no request permitted'),startup_check=True)
        self.assertEqual(result['provider_calls'],0)
        before={str(p):p.read_bytes() for p in (self.fixture.archive.root/'manifest').rglob('*.json')}
        with patch.object(startup,'current_boot_id',return_value='second'):
            result=execute('capture-prospective',config,clock=lambda:self.fixture.now,
                transport_factory=lambda *_:self.fail('Restart cannot invent a request'),startup_check=True)
        self.assertEqual(result['provider_calls'],0)
        self.assertEqual(before,{str(p):p.read_bytes() for p in (self.fixture.archive.root/'manifest').rglob('*.json')})

    def test_lifecycle_enters_only_after_verified_startup_even_same_day(self):
        from forecast_standalone_activation import OperationalHeartbeat
        state=OperationalState(self.fixture.config.log_root/'operational-state')
        now=self.fixture.now
        state.append(OperationalHeartbeat('1','rebuild-prospective-projection',now,now,'success',0,None,None,None))
        def cycle(**kwargs):
            receipt=startup._load(startup.receipt_directory(self.fixture.archive)/'current.json')
            self.assertEqual(receipt['status'],'verified')
            return {'disposition':'success','provider_calls':0}
        with patch.object(startup,'current_boot_id',return_value='new-boot'), \
                patch('forecast_operational_lifecycle.run_cycle',side_effect=cycle) as run:
            execute('lifecycle-cycle',self.fixture.config,clock=lambda:now,startup_check=True)
            run.assert_called_once()


if __name__=='__main__':unittest.main()
