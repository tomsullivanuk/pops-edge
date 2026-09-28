"""Full-namespace supporting view: equality, rejection, and real process fences."""
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

from forecast_standalone_activation import refresh_supporting_from_raw, initialize_activation, canonical_prospective_authority
from forecast_standalone_operations import (
    NamespaceArchive, OperationsError, DeploymentConfig, OperatingMode, RetryPolicy,
    APPROVED_ACTIVATION_AT, canonical_bytes, replay_pr17_archive, reconcile_archive,
    Disposition, DesignAuthority, _entry_values, request_identity,
)
from forecast_prospective_projection import rebuild_projection, _scientific_state_bytes
from forecast_supporting_replay import SupportingReplayArchive
from inspect_forecast_standalone_activation import fixtures, FixtureOrderBook
from operate_forecast_standalone_activation import execute, load_live_supporting
from tests.test_forecast_supporting_replay import supporting_fixture


def changed_material():
    mlb, catalog, _ = fixtures()
    market = json.loads(catalog)
    market['markets'][0]['ticker'] = 'KXMLB-NEW-FIXTURE'
    return mlb, canonical_bytes(market)


def supporting_worker(config, at, ready, proceed, output, under_lock):
    """Actual command, fake loader, coordinated only at the publication fence."""
    original = SupportingReplayArchive.mutation_lock
    locks = []
    @contextmanager
    def coordinated(self):
        # Activation preflight has its own short fence. Coordinate the second
        # view, used for actual supporting publication, not the pre-call check.
        if not calls:
            with original(self): yield
            return
        if not under_lock:
            ready.set()
            if not proceed.wait(10):
                raise RuntimeError('collector did not finish')
        start = time.monotonic()
        with original(self):
            entered = time.monotonic()
            if under_lock:
                ready.set()
                if not proceed.wait(10):
                    raise RuntimeError('collector did not start')
            try:
                yield
            finally:
                locks.append((entered-start, time.monotonic()-entered))
    calls = []
    def loader(_):
        mlb, catalog = changed_material()
        def fake_get(base, path):
            calls.append((base, path))
            if 'statsapi.mlb.com' in base:
                from urllib.parse import parse_qs, urlsplit
                day = parse_qs(urlsplit(path).query)['date'][0]
                return canonical_bytes({'dates':[x for x in json.loads(mlb)['dates'] if x['date']==day]})
            return catalog
        return load_live_supporting(archive=NamespaceArchive(config), purpose='schedule',
            at=at, public_get=fake_get, clock=lambda:at)
    start = time.monotonic()
    try:
        with patch.object(SupportingReplayArchive, 'mutation_lock', coordinated):
            result = execute('refresh-supporting', config, clock=lambda: at, supporting_loader=loader)
        output.put(('supporting', result, locks, len(calls), time.monotonic()-start))
    except Exception as exc:
        output.put(('supporting', getattr(exc, 'code', str(exc)), locks, len(calls), time.monotonic()-start))


def collector_worker(config, at, proceed, output, under_lock):
    start = time.monotonic()
    transport = FixtureOrderBook(fixtures()[2])
    locks = []
    original = NamespaceArchive.mutation_lock
    @contextmanager
    def measured(source):
        waiting = time.monotonic()
        if under_lock:
            proceed.set()
        with original(source):
            entered = time.monotonic()
            try: yield
            finally: locks.append((entered-waiting, time.monotonic()-entered))
    try:
        with patch.object(NamespaceArchive, 'mutation_lock', measured):
            result = execute('capture-prospective', config,
                clock=lambda: at+timedelta(seconds=time.monotonic()-start),
                transport_factory=lambda *_: transport)
        output.put(('collector', result, transport.calls, time.monotonic()-start, locks))
    except Exception as exc:
        output.put(('collector', getattr(exc, 'code', str(exc)), transport.calls, time.monotonic()-start))
    finally:
        proceed.set()


class SupportingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive, self.at = supporting_fixture(self.root, sessions=2, markets=20)

    def refresh(self, archive=None):
        mlb, catalog = changed_material()
        return refresh_supporting_from_raw(archive=archive or self.archive,
            mlb_raw=mlb, kalshi_raw=catalog, collected_at=self.at)

    def snapshot(self):
        return {str(p.relative_to(self.archive.config.primary_root.resolve())): p.read_bytes()
                for directory in (self.archive.raw_root, self.archive.normalized_root, self.archive.manifest_root)
                for p in directory.rglob('*') if p.is_file()}

    def test_complete_replay_publication_and_failure_evidence_equal(self):
        self.archive.record_failure(entry_values=_entry_values(archive=self.archive,
            command='fixture-failure', request_id=request_identity({'failed': 1}),
            invoked_at=self.at, endpoint='fixture://failure', disposition=Disposition.TIMEOUT,
            protocol_id=None, design=DesignAuthority.SUPPORTING, diagnostics=('fixture timeout',)))
        expected = replay_pr17_archive(self.archive, analysis_boundary=self.at)
        view = SupportingReplayArchive(self.archive)
        self.assertEqual(replay_pr17_archive(view, analysis_boundary=self.at), expected)
        self.assertEqual(view.entries(), self.archive.entries())
        saved = self.root/'frozen'
        shutil.copytree(self.archive.config.primary_root, saved)
        with patch('forecast_supporting_replay.SupportingReplayArchive', side_effect=lambda x:x):
            reference = self.refresh()
        reference_files = self.snapshot()
        reference_state = _scientific_state_bytes(replay_pr17_archive(self.archive, analysis_boundary=self.at))
        shutil.rmtree(self.archive.config.primary_root)  # owned temporary fixture only
        shutil.copytree(saved, self.archive.config.primary_root)
        actual = self.refresh()
        self.assertGreater(actual['contracts'], 0)
        self.assertEqual(actual, reference)
        self.assertEqual(self.snapshot(), reference_files)
        self.assertEqual(_scientific_state_bytes(replay_pr17_archive(self.archive, analysis_boundary=self.at)), reference_state)

    def test_cached_changed_missing_added_and_same_size_replacement_reject(self):
        for change in ('changed', 'missing', 'added', 'replacement'):
            with self.subTest(change=change):
                view = SupportingReplayArchive(self.archive)
                replay_pr17_archive(view, analysis_boundary=self.at)
                path = next(self.archive.raw_root.glob('*/*'))
                original = path.read_bytes()
                path.chmod(0o600)
                extra = self.archive.raw_root/'unexpected'
                if change == 'changed': path.write_bytes(b'invalid')
                elif change == 'missing': path.unlink()
                elif change == 'added': extra.write_bytes(b'orphan')
                else:
                    path.unlink(); path.write_bytes(original)
                try:
                    with self.assertRaisesRegex(OperationsError, 'source changed'):
                        with view.mutation_lock(): self.fail('stale source published')
                finally:
                    if extra.exists(): extra.unlink()
                    path.write_bytes(original)
                with self.assertRaises(OperationsError): view.entries()

    def test_corrupt_source_rejected_by_fresh_view(self):
        path = next(self.archive.raw_root.glob('*/*'))
        path.chmod(0o600); path.write_bytes(b'corrupt')
        for source in (self.archive, SupportingReplayArchive(self.archive)):
            with self.assertRaises(OperationsError): replay_pr17_archive(source, analysis_boundary=self.at)

    def test_cache_budget_falls_back_without_changing_science(self):
        expected = replay_pr17_archive(self.archive, analysis_boundary=self.at)
        with patch('forecast_supporting_replay.MAX_SOURCE_BYTES', 0):
            view = SupportingReplayArchive(self.archive)
            self.assertEqual(replay_pr17_archive(view, analysis_boundary=self.at), expected)
            self.assertEqual(view._byte_count, 0)

    def test_duplicate_correction_rejected_equally(self):
        correction = next(x for x in self.archive.entries() if x['command'] == 'correct-retrospective-supporting-session')
        value = self.archive.read_json_verified('normalized', correction['normalized_object_id'])
        self.archive.commit(raw_body=canonical_bytes(value), normalized=value,
            entry_values=_entry_values(archive=self.archive, command='correct-retrospective-supporting-session',
                request_id=request_identity({'duplicate': 1}), invoked_at=self.at,
                endpoint='fixture://duplicate', disposition=Disposition.SUCCESS, protocol_id=None,
                design=DesignAuthority.SUPPORTING, diagnostics=('duplicate correction',)))
        errors = []
        for source in (self.archive, SupportingReplayArchive(self.archive)):
            with self.assertRaises(OperationsError) as caught:
                replay_pr17_archive(source, analysis_boundary=self.at)
            errors.append(str(caught.exception))
        self.assertEqual(*errors)

    def test_authority_source_change_rejected_before_loader(self):
        from dataclasses import replace
        _, protocol = canonical_prospective_authority()
        config = replace(self.archive.config, mode=OperatingMode.ACTIVATED,
            primary_root=self.root/'activated/supporting-shape/primary',
            secondary_root=self.root/'activated/supporting-shape/secondary',
            activation_at=APPROVED_ACTIVATION_AT,
            research_protocol_ids=(protocol.standalone_probability_source_protocol_id,))
        archive = NamespaceArchive(config)
        initialize_activation(archive, datetime(2026,8,28,tzinfo=timezone.utc))
        original = NamespaceArchive.mutation_lock
        @contextmanager
        def changed(source):
            with original(source):
                (source.raw_root/'unexplained').write_bytes(b'concurrent change')
                yield
        with patch.object(NamespaceArchive, 'mutation_lock', changed):
            with self.assertRaisesRegex(OperationsError, 'source changed'):
                execute('refresh-supporting', config, clock=lambda:self.at,
                    supporting_loader=lambda _:self.fail('stale authority called provider'))

    def test_nonempty_scored_unscored_failure_inclusive_coverage_equal(self):
        from inspect_forecast_standalone_research import build_synthetic_bundle
        from tests.test_forecast_standalone_research import graph_args
        from forecast_standalone_operations import archive_pr17_authority
        from dataclasses import replace
        from decimal import Decimal
        graph = graph_args(build_synthetic_bundle())
        at = graph.pop('analysis_boundary')
        archive = NamespaceArchive(replace(self.archive.config,
            primary_root=self.root/'coverage/dry-run/supporting-shape/primary',
            secondary_root=self.root/'coverage/dry-run/supporting-shape/secondary'))
        archive_pr17_authority(archive, (x for values in graph.values() for x in values), recorded_at=at)
        canonical = replay_pr17_archive(archive, analysis_boundary=at)
        actual = replay_pr17_archive(SupportingReplayArchive(archive), analysis_boundary=at)
        self.assertEqual(_scientific_state_bytes(actual), _scientific_state_bytes(canonical))
        self.assertTrue(actual.bucket('measurements'))
        self.assertTrue(actual.bucket('performances'))
        self.assertTrue(any(x.coverage_rate == Decimal('0.5') for x in actual.bucket('coverages')))

    def test_partial_publication_retains_identical_rejection(self):
        saved = self.root/'frozen'
        shutil.copytree(self.archive.config.primary_root, saved)
        outcomes = []
        original = NamespaceArchive._publish
        for candidate in (False, True):
            count = [0]
            def interrupted(source, target, body):
                count[0] += 1
                if count[0] == 4: raise OperationsError('injected-interruption', 'fixture publication')
                return original(source, target, body)
            with patch.object(NamespaceArchive, '_publish', interrupted):
                with patch('forecast_supporting_replay.SupportingReplayArchive',
                           SupportingReplayArchive if candidate else lambda x:x):
                    with self.assertRaises(OperationsError): self.refresh()
            outcomes.append((self.snapshot(), reconcile_archive(self.archive)))
            shutil.rmtree(self.archive.config.primary_root)
            shutil.copytree(saved, self.archive.config.primary_root)
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertTrue(outcomes[0][1].blocking)


class SupportingConcurrencyTests(unittest.TestCase):
    def test_actual_due_collector_with_supporting_publication_and_stale_preparation(self):
        for under_lock in (True, False):
            with self.subTest(under_lock=under_lock), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); _, protocol = canonical_prospective_authority()
                at = datetime(2026, 9, 5, 4, tzinfo=timezone.utc)
                config = DeploymentConfig('concurrency', 'concurrency', OperatingMode.ACTIVATED,
                    root/'activated/concurrency/primary', root/'activated/concurrency/secondary',
                    'https://fixture.invalid', RetryPolicy(1,1,1,(),0), 1, root/'logs',
                    research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),
                    activation_at=APPROVED_ACTIVATION_AT)
                archive = NamespaceArchive(config)
                initialize_activation(archive, datetime(2026,8,28,tzinfo=timezone.utc))
                mlb, catalog, _ = fixtures()
                refresh_supporting_from_raw(archive=archive, mlb_raw=mlb, kalshi_raw=catalog,
                    collected_at=at-timedelta(minutes=1))
                rebuild_projection(archive, at)
                context = multiprocessing.get_context('spawn')
                ready, proceed, output = context.Event(), context.Event(), context.Queue()
                supporting = context.Process(target=supporting_worker, args=(config,at,ready,proceed,output,under_lock))
                collector = context.Process(target=collector_worker, args=(config,at,proceed,output,under_lock))
                supporting.start()
                try:
                    self.assertTrue(ready.wait(10))
                    collector.start()
                    results = {row[0]:row for row in (output.get(timeout=15), output.get(timeout=15))}
                    supporting.join(5); collector.join(5)
                    self.assertEqual((supporting.exitcode, collector.exitcode), (0,0))
                finally:
                    for process in (supporting,collector):
                        if process.is_alive(): process.terminate(); process.join(5)
                self.assertEqual(results['collector'][2], 1, results)
                self.assertIsInstance(results['collector'][1], dict, results)
                self.assertLess(results['collector'][3], 20, results)  # existing preparation budget
                self.assertGreaterEqual(results['supporting'][3], 2, results)
                if under_lock:
                    self.assertIsInstance(results['supporting'][1], dict, results)
                    self.assertEqual(results['supporting'][1]['provider_calls'], results['supporting'][3])
                    self.assertLess(max(x[1] for x in results['supporting'][2]), 1, results)
                else:
                    self.assertEqual(results['supporting'][1], 'supporting-source-changed', results)
                state = replay_pr17_archive(archive, analysis_boundary=at+timedelta(seconds=30))
                attempts = [x for x in state.bucket('attempts') if x.provider_call_occurred]
                self.assertEqual(len(attempts), 1)
                self.assertEqual(attempts[0].slot, 0)
                self.assertEqual(type(attempts[0].result).__name__, 'CapturedValid')
                self.assertLess(attempts[0].effective_at, attempts[0].target_at+timedelta(minutes=1))
                print(json.dumps({'concurrency': results}, default=str))


if __name__ == '__main__': unittest.main()
