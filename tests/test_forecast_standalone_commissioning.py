"""Offline commissioning gates: travel outages never imply successful collection."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from forecast_standalone_activation import (
    APPROVED_ACTIVATION_AT, OperationalState, canonical_prospective_authority,
    initialize_activation, verify_acquisition_bundle,
)
from forecast_standalone_operations import (
    DeploymentConfig, NamespaceArchive, OperatingMode, OperationsError, RetryPolicy,
    inspect_archive, replay_pr17_archive,
)
from forecast_standalone_schedule_reconciliation import (
    COMMAND, reconcile_schedule, reconciliation_dates, validate_date_page,
)
from inspect_forecast_standalone_activation import fixtures
from operate_forecast_standalone_activation import execute, load_live_supporting, main


class CommissioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        _, protocol = canonical_prospective_authority()
        self.config = DeploymentConfig(
            'commissioning', 'commissioning', OperatingMode.ACTIVATED,
            root/'activated/commissioning/primary', root/'activated/commissioning/secondary',
            'https://fixture.invalid', RetryPolicy(1, 5, 5, (), 0), 1, root/'logs',
            research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),
            activation_at=APPROVED_ACTIVATION_AT)
        self.archive = NamespaceArchive(self.config)
        initialize_activation(self.archive, datetime(2026, 8, 28, tzinfo=timezone.utc))
        self.now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        self.calls = []

    def empty(self, base, path):
        self.calls.append((base, path))
        return b'{"dates":[],"totalGames":0}'

    def reconcile(self, first=date(2026, 9, 5), last=date(2026, 9, 8), get=None):
        return reconcile_schedule(archive=self.archive, started=self.now,
            start_date=first, end_date=last, public_get=get or self.empty, clock=lambda: self.now)

    def heartbeat(self):
        return OperationalState(self.config.log_root/'operational-state').entries()[-1]

    def test_all_scheduled_acquisition_commands_gate_before_provider_composition(self):
        before = tuple(self.archive.entries())
        def prohibited(*args):
            self.fail('pre-boundary provider/loader invoked')
        for command in ('capture-prospective', 'refresh-supporting', 'reconcile-outcomes'):
            out = execute(command, self.config, clock=lambda: APPROVED_ACTIVATION_AT-timedelta(microseconds=1),
                supporting_loader=prohibited, outcome_loader=prohibited, transport_factory=prohibited)
            self.assertEqual((out['disposition'], out['provider_calls']), ('pre-activation-no-call', 0))
        self.assertEqual(before, tuple(self.archive.entries()))
        self.assertTrue(all(h.disposition == 'pre-activation-no-call' and h.provider_calls == 0
            for h in OperationalState(self.config.log_root/'operational-state').entries()))

    def test_exact_boundary_permits_loader_and_records_failure_honestly(self):
        for command, loader_name in [('refresh-supporting', 'supporting_loader'), ('reconcile-outcomes', 'outcome_loader')]:
            def loader(at):
                self.assertEqual(at, APPROVED_ACTIVATION_AT)
                raise URLError('do not echo private diagnostics')
            with self.assertRaisesRegex(OperationsError, 'operational-io-failure'):
                execute(command, self.config, clock=lambda: APPROVED_ACTIVATION_AT, **{loader_name: loader})
        for item in OperationalState(self.config.log_root/'operational-state').entries():
            self.assertEqual((item.disposition, item.failure_code), ('failed', 'operational-io-failure'))
            self.assertIsNone(item.provider_calls)  # injected uninstrumented loader: never invent a count
            self.assertNotIn('private', item.to_json())

    def test_live_loader_failure_counts_include_failed_mlb_and_catalog_requests(self):
        for purpose, fail_at, exception in [('schedule', 1, URLError('offline')),
                ('schedule', 3, TimeoutError()), ('outcomes', 2, URLError('offline'))]:
            self.calls.clear()
            def get(base, path):
                self.calls.append(path)
                if len(self.calls) == fail_at:
                    raise exception
                return b'{"dates":[],"totalGames":0}'
            with self.assertRaises(OperationsError) as caught:
                load_live_supporting(archive=self.archive, purpose=purpose, at=self.now,
                    public_get=get, clock=lambda: self.now)
            self.assertEqual(caught.exception.provider_calls, fail_at)
            self.assertEqual(len(self.calls), fail_at)
            self.assertEqual(len(self.archive.entries()), 2)  # only original authority

    def test_counted_outage_then_later_independent_outcome_invocation(self):
        command = 'reconcile-outcomes'
        def get(base, path):
            raise URLError('offline')
        def loader(at):
            return load_live_supporting(archive=self.archive, purpose='outcomes', at=at,
                public_get=get, clock=lambda: self.now)
        with self.assertRaises(OperationsError):
            execute(command, self.config, clock=lambda: self.now, outcome_loader=loader)
        failed = self.heartbeat()
        self.assertEqual((failed.disposition, failed.provider_calls), ('failed', 1))
        self.now += timedelta(hours=1)
        def online_loader(at):
            return load_live_supporting(archive=self.archive, purpose='outcomes', at=at,
                public_get=self.empty, clock=lambda: self.now)
        result = execute(command, self.config, clock=lambda: self.now, outcome_loader=online_loader)
        self.assertEqual((result['disposition'], result['provider_calls']), ('unchanged', 2))
        self.assertIn(failed, OperationalState(self.config.log_root/'operational-state').entries())
        self.assertTrue(inspect_archive(self.archive).ready)

    def test_unknown_and_empty_dates_are_acquired_and_repeat_is_noop(self):
        expected = ('2026-09-05', '2026-09-06', '2026-09-07', '2026-09-08')
        result = self.reconcile()
        self.assertEqual(result['requested_dates'], expected)
        self.assertEqual((result['provider_calls'], result['contracts']), (4, 0))
        self.assertEqual(len(result['completed_manifest_ids']), 4)
        self.assertTrue(all(base == 'https://statsapi.mlb.com' for base, _ in self.calls))
        before = tuple(self.archive.entries())
        repeated = self.reconcile()
        self.assertEqual((repeated['disposition'], repeated['provider_calls']), ('unchanged', 0))
        self.assertEqual(before, tuple(self.archive.entries()))
        self.assertTrue(inspect_archive(self.archive).ready)
        self.assertEqual(replay_pr17_archive(self.archive, analysis_boundary=self.now).bucket('opportunities'), ())

    def test_later_date_failure_preserves_complete_dates_and_retries_only_missing(self):
        def get(base, path):
            day = parse_qs(urlparse(path).query)['date'][0]
            if day == '2026-09-06':
                self.calls.append((base, path))
                raise URLError('offline')
            return self.empty(base, path)
        def runner(archive, started):
            return self.reconcile(get=get)
        with self.assertRaises(OperationsError) as caught:
            execute(COMMAND, self.config, clock=lambda: self.now, schedule_reconciliation_runner=runner)
        self.assertEqual(caught.exception.provider_calls, 2)
        self.assertEqual((self.heartbeat().disposition, self.heartbeat().provider_calls), ('failed', 2))
        self.assertTrue(inspect_archive(self.archive).ready)
        result = self.reconcile()
        self.assertEqual(result['requested_dates'], ('2026-09-06', '2026-09-07', '2026-09-08'))

    def test_bounds_and_malformed_or_undeclared_empty_dates_fail_without_authority(self):
        for first, last in [(date(2026,9,4),date(2026,9,5)), (date(2026,9,5),date(2026,9,9)),
                (date(2026,9,6),date(2026,9,5)), (date(2026,9,5),date(2026,10,6))]:
            with self.assertRaises(OperationsError):
                self.reconcile(first,last)
        self.assertEqual(self.calls, [])
        before = tuple(self.archive.entries())
        for raw in (b'{}', b'{"dates":[]}', b'{"dates":[],"totalGames":1}',
                b'{"dates":[],"totalGames":false}', b'{"dates":[{"date":"2026-09-06","games":[]}],"totalGames":0}',
                b'{"dates":[{"date":"2026-09-05","games":[{}]}],"totalGames":1}'):
            self.now += timedelta(seconds=1)
            with self.assertRaises(OperationsError):
                self.reconcile(date(2026,9,5),date(2026,9,5),get=lambda *args:raw)
            authoritative = tuple(e for e in self.archive.entries() if e['disposition']=='success')
            self.assertEqual(before, authoritative)
            failures = tuple(e for e in self.archive.entries() if e['command']==COMMAND+'-failure')
            self.assertTrue(any(self.archive.read_verified('raw',e['raw_object_sha256'])==raw for e in failures))

    def test_exact_31_date_limit_and_eastern_midnight(self):
        self.now = datetime(2026,10,10,12,tzinfo=timezone.utc)
        dates = reconciliation_dates(archive=self.archive,started=self.now,
            start_date=date(2026,9,5),end_date=date(2026,10,5))
        self.assertEqual(len(dates),31)
        with self.assertRaises(OperationsError):
            reconciliation_dates(archive=self.archive,started=self.now,
                start_date=date(2026,9,5),end_date=date(2026,10,6))
        self.now = datetime(2026,9,9,3,59,59,tzinfo=timezone.utc)
        with self.assertRaises(OperationsError):
            self.reconcile(date(2026,9,8),date(2026,9,8))
        self.now += timedelta(seconds=1)
        self.assertEqual(self.reconcile(date(2026,9,8),date(2026,9,8))['provider_calls'],1)

    def test_late_discovery_creates_population_but_never_quote_or_backdated_observation(self):
        mlb, _, _ = fixtures()
        out = self.reconcile(date(2026,9,5),date(2026,9,5),get=lambda *args:mlb)
        self.assertGreater(out['contracts'], 0)
        state = replay_pr17_archive(self.archive, analysis_boundary=self.now)
        self.assertEqual(len(state.bucket('opportunities')), 2)
        self.assertTrue(all(h.latest.collected_at == self.now for h in state.bucket('outcome_histories')))
        self.assertEqual(state.bucket('market_observations'), ())
        def prohibited(*args):
            self.fail('expired slot made a provider call')
        capture = execute('capture-prospective', self.config, clock=lambda:self.now,
                          transport_factory=prohibited)
        self.assertEqual(capture['provider_calls'], 0)
        state = replay_pr17_archive(self.archive, analysis_boundary=self.now)
        self.assertFalse(any(a.provider_call_occurred for a in state.bucket('attempts')))
        from forecast_standalone_research import create_probability_source_coverage_v3
        from forecast_research_contracts import ResearchContractProvenance
        coverage = create_probability_source_coverage_v3(
            protocol=state.bucket('protocols')[0], activation=state.bucket('activation_boundaries')[0],
            analysis_boundary=self.now, opportunities=state.bucket('opportunities'),
            eligibility_contexts=state.bucket('eligibility_contexts'), eligibility_results=state.bucket('eligibility_results'),
            schedule_histories=state.bucket('outcome_histories'), classifications=state.bucket('classifications'),
            attempts=state.bucket('attempts'), snapshots=state.bucket('snapshots'),
            provenance=ResearchContractProvenance('commissioning-fixture','1'))
        self.assertEqual(len(coverage.coverage_universe_ids), 2)
        self.assertEqual(len(coverage.reconciliation.missed_window), 2)
        self.assertEqual(coverage.measurement_ids, ())

        self.assertEqual(state.bucket('market_observations'), ())

    def test_cli_offline_exit_and_heartbeat_agree(self):
        from types import SimpleNamespace
        from contextlib import redirect_stderr
        from io import StringIO
        def offline(*args):
            raise URLError("private transport detail")
        with patch('operate_forecast_standalone_activation.DeploymentConfig.from_json',return_value=self.config), \
                patch('operate_forecast_standalone_activation.configured_kalshi_transport',return_value=SimpleNamespace(requester=offline)):
            error = StringIO()
            with redirect_stderr(error):
                code = main(['--config','/fixture/config.json','--trusted-at',self.now.isoformat(),'refresh-supporting'])
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(error.getvalue())['provider_calls'], 1)
        self.assertNotIn('private transport', error.getvalue())
        self.assertEqual((self.heartbeat().disposition,self.heartbeat().provider_calls), ('failed',1))

    def test_derivation_rejection_preserves_received_raw_without_completion(self):
        mlb, _, _ = fixtures()
        with patch('forecast_standalone_schedule_reconciliation.schedule_contracts',
                   side_effect=OperationsError('provider-data-invalid','fixture invalid outcome')):
            with self.assertRaises(OperationsError) as caught:
                self.reconcile(date(2026,9,5),date(2026,9,5),get=lambda *args:mlb)
        self.assertEqual(caught.exception.provider_calls,1)
        failed = next(e for e in self.archive.entries() if e['command']==COMMAND+'-failure')
        self.assertEqual(self.archive.read_verified('raw',failed['raw_object_sha256']),mlb)
        self.assertFalse(any(e['command']==COMMAND for e in self.archive.entries()))
        self.assertTrue(inspect_archive(self.archive).ready)

    def test_replay_rejects_foreign_date_receipt(self):
        self.reconcile(date(2026,9,5),date(2026,9,5))
        entry = next(e for e in self.archive.entries() if e['command'] == COMMAND)
        value = json.loads(self.archive.read_verified('normalized', entry['normalized_object_id']))
        value['pages'][0]['request_identity'] = '2026-09-06'
        with self.assertRaises(OperationsError):
            verify_acquisition_bundle(self.archive, value)

    def test_manual_command_not_in_scheduler_and_cli_requires_explicit_bounds(self):
        from forecast_standalone_activation import render_launchd_jobs
        config_path = Path(self.temp.name)/'config.json'
        # CLI rejects missing bounds before any manual provider request.
        with patch('operate_forecast_standalone_activation.DeploymentConfig.from_json',return_value=self.config):
            config_path.write_text('{}')
            with patch('forecast_standalone_activation.DeploymentConfig.from_json',return_value=self.config):
                import plistlib,sys
                jobs = render_launchd_jobs(repository_root=Path(__file__).resolve().parents[1],
                    python_executable=Path(sys.executable),config_path=config_path,output_root=Path(self.temp.name)/'jobs')
                self.assertEqual(len(jobs),6)
                self.assertNotIn(COMMAND,[plistlib.loads(Path(p).read_bytes())['ProgramArguments'][-1] for p in jobs])
            self.assertNotEqual(main(['--config', str(config_path), COMMAND]), 0)
            self.assertNotEqual(main(['--config', str(config_path), '--trusted-at', self.now.isoformat(), COMMAND,
                '--start-date','2026-09-05','--end-date','2026-09-08']), 0)

    def ticking_clock(self):
        self.now += timedelta(seconds=1)
        return self.now

    def resume_pages(self):
        from tests.test_forecast_standalone_activation import ActivationTests
        original,resumed = ActivationTests()._resume_pair()
        original,resumed = (json.loads(json.dumps(x).replace('2026-06-16','2026-09-05')
            .replace('2026-06-17','2026-09-06')) for x in (original,resumed))
        return {day:ActivationTests()._schedule_page(day,game)
                for day,game in zip(('2026-09-05','2026-09-06'),(original,resumed))}

    def reconcile_pages(self, pages, first=date(2026,9,5), last=date(2026,9,6)):
        def get(base,path):
            day = parse_qs(urlparse(path).query)['date'][0]
            self.calls.append(day)
            if day not in pages:raise URLError('offline fixture')
            return pages[day]
        def runner(archive,started):
            return reconcile_schedule(archive=archive,started=started,start_date=first,end_date=last,
                                      public_get=get,clock=self.ticking_clock)
        return execute(COMMAND,self.config,clock=self.ticking_clock,schedule_reconciliation_runner=runner)

    def assert_resume_authority(self):
        state = replay_pr17_archive(self.archive,analysis_boundary=self.now)
        self.assertEqual(len(state.bucket('opportunities')),1)
        classification, = state.bucket('classifications')
        self.assertFalse(classification.ordinary_game)
        self.assertIn('explicit-mlb-resume-lineage',classification.limitations)
        history, = state.bucket('outcome_histories')
        self.assertEqual(len(history.observations),2)
        self.assertEqual(history.observations[0].scheduled_start.date(),date(2026,9,5))
        self.assertEqual(state.bucket('market_observations'),())
        self.assertTrue(inspect_archive(self.archive).ready)
        return state

    def test_resume_dates_equal_combined_page_science_and_repeat(self):
        from forecast_standalone_activation import merge_mlb_schedule_responses,refresh_supporting_from_raw
        prior = replay_pr17_archive(self.archive,analysis_boundary=self.now)
        pages = self.resume_pages();result = self.reconcile_pages(pages)
        self.assertEqual(result['provider_calls'],2)
        state = self.assert_resume_authority()
        completion, = (entry for entry in self.archive.entries() if entry['command']==COMMAND)
        value = json.loads(self.archive.read_verified('normalized',completion['normalized_object_id']))
        derived_at = datetime.fromisoformat(value['schedule_reconciled_at']['datetime_utc'])
        expected = refresh_supporting_from_raw(archive=None,mlb_raw=merge_mlb_schedule_responses(tuple(pages.values())),
            kalshi_raw=b'{"markets":[],"cursor":""}',collected_at=derived_at,prior_state=prior,
            derive_only=True,acquisition_command=COMMAND,union_rule=value['union_rule'])
        self.assertEqual(sorted(x.to_json() for x in expected),sorted(value['contracts']))
        self.assertEqual(len(value['dependencies']),2)
        before = tuple(self.archive.entries())
        repeat = self.reconcile_pages({})
        self.assertEqual((repeat['disposition'],repeat['provider_calls']),('unchanged',0))
        self.assertEqual(before,tuple(self.archive.entries()))
        self.assertEqual(state.objects,self.assert_resume_authority().objects)

    def test_resume_receipts_across_invocations_do_not_certify_incomplete_date(self):
        pages = self.resume_pages()
        with self.assertRaisesRegex(OperationsError,'schedule-lineage-incomplete.*2026-09-06') as caught:
            self.reconcile_pages(pages,last=date(2026,9,5))
        self.assertEqual(caught.exception.provider_calls,1)
        self.assertEqual(self.calls,['2026-09-05'])  # no silent expansion
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('opportunities'),())
        self.assertEqual(reconciliation_dates(archive=self.archive,started=self.now,
            start_date=date(2026,9,5),end_date=date(2026,9,5)),(date(2026,9,5),))
        before = {p:p.read_bytes() for folder in (self.archive.raw_root,self.archive.normalized_root,self.archive.manifest_root)
                  for p in folder.rglob('*') if p.is_file()}
        result = self.reconcile_pages(pages,first=date(2026,9,6))
        self.assertEqual(result['provider_calls'],1)
        self.assertEqual(result['reused_dates'],('2026-09-05',))
        self.assertEqual(result['scientifically_completed_dates'],('2026-09-05','2026-09-06'))
        self.assertEqual(self.calls,['2026-09-05','2026-09-06'])
        self.assert_resume_authority()
        self.assertTrue(all(p.read_bytes()==body for p,body in before.items()))
        self.assertEqual(self.reconcile_pages({})['provider_calls'],0)

    def test_resume_partial_transport_failure_stays_auditable_and_recovers(self):
        pages = self.resume_pages()
        with self.assertRaisesRegex(OperationsError,'transport-connection-failure') as caught:
            self.reconcile_pages({'2026-09-05':pages['2026-09-05']})
        self.assertEqual(caught.exception.provider_calls,2)
        failed = self.heartbeat()
        self.assertEqual((failed.disposition,failed.provider_calls),('failed',2))
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('opportunities'),())
        self.assertTrue(inspect_archive(self.archive).ready)
        result = self.reconcile_pages(pages)
        self.assertEqual(result['provider_calls'],1)
        self.assert_resume_authority()
        self.assertIn(failed,OperationalState(self.config.log_root/'operational-state').entries())

    def test_resume_conflicting_pair_cannot_publish_ordinary_authority(self):
        pages = self.resume_pages()
        value=json.loads(pages['2026-09-06']);value['dates'][0]['games'][0]['resumedFromDate']='2026-09-04'
        pages['2026-09-06']=json.dumps(value).encode()
        with self.assertRaises(OperationsError):self.reconcile_pages(pages)
        self.assertFalse(any(entry['command']==COMMAND for entry in self.archive.entries()))
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('classifications'),())

    def test_one_sided_resume_cannot_escape_incoming_lineage_dependency(self):
        pages=self.resume_pages();value=json.loads(pages['2026-09-06'])
        value['dates'][0]['games'][0].pop('resumedFrom')
        value['dates'][0]['games'][0].pop('resumedFromDate')
        pages['2026-09-06']=json.dumps(value).encode()
        with self.assertRaisesRegex(OperationsError,'multi-date-conflict'):self.reconcile_pages(pages)
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('opportunities'),())

    def test_resume_successor_arrives_in_first_invocation(self):
        pages=self.resume_pages()
        with self.assertRaisesRegex(OperationsError,'schedule-lineage-incomplete'):
            self.reconcile_pages(pages,first=date(2026,9,6))
        result=self.reconcile_pages(pages,last=date(2026,9,5))
        self.assertEqual(result['provider_calls'],1)
        self.assert_resume_authority()

    def test_declared_empty_related_date_does_not_complete_lineage(self):
        pages=self.resume_pages();pages['2026-09-06']=b'{"dates":[],"totalGames":0}'
        with self.assertRaisesRegex(OperationsError,'schedule-lineage-incomplete'):self.reconcile_pages(pages)
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('opportunities'),())
        self.assertIn(date(2026,9,5),reconciliation_dates(archive=self.archive,started=self.now,
            start_date=date(2026,9,5),end_date=date(2026,9,6)))

    def test_completion_requires_exact_preserved_receipt_dependencies(self):
        self.reconcile_pages(self.resume_pages())
        entry=next(x for x in self.archive.entries() if x['command']==COMMAND)
        value=json.loads(self.archive.read_verified('normalized',entry['normalized_object_id']))
        value['dependencies']=value['dependencies'][:1]
        with self.assertRaisesRegex(OperationsError,'schedule-date-conflict'):verify_acquisition_bundle(self.archive,value)

    def test_outcome_first_after_offline_then_manual_schedule_and_replay(self):
        from tests.test_forecast_standalone_activation import ActivationTests
        game=ActivationTests()._reschedule_game(990001,'2026-09-08','2026-09-08T23:05:00Z','Final')
        raw=ActivationTests()._schedule_page('2026-09-08',game)
        def get(base,path):
            self.calls.append(path)
            return raw if parse_qs(urlparse(path).query)['date'][0]=='2026-09-08' else b'{"dates":[],"totalGames":0}'
        def offline(base,path):raise URLError('fixture offline')
        def outcome(reader):
            return execute('reconcile-outcomes',self.config,clock=self.ticking_clock,
                outcome_loader=lambda at:load_live_supporting(archive=self.archive,purpose='outcomes',at=at,
                    public_get=reader,clock=self.ticking_clock))
        with self.assertRaises(OperationsError):outcome(offline)
        self.assertEqual((self.heartbeat().disposition,self.heartbeat().provider_calls),('failed',1))
        with self.assertRaisesRegex(OperationsError,'outcome-authority-deferred'):outcome(get)
        self.assertEqual((self.heartbeat().disposition,self.heartbeat().provider_calls),('failed',2))
        failures=tuple(x for x in self.archive.entries() if x['command']=='reconcile-outcomes-failure')
        self.assertEqual(len(failures),2)
        self.assertEqual({self.archive.read_verified('raw',x['raw_object_sha256']) for x in failures},
                         {raw,b'{"dates":[],"totalGames":0}'})
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).bucket('opportunities'),())
        self.reconcile_pages({'2026-09-08':raw},first=date(2026,9,8),last=date(2026,9,8))
        state=replay_pr17_archive(self.archive,analysis_boundary=self.now)
        self.assertEqual(len(state.bucket('opportunities')),1)
        self.assertEqual(len(state.bucket('outcome_histories')),1)
        before=tuple(self.archive.entries())
        repeat=self.reconcile_pages({},first=date(2026,9,8),last=date(2026,9,8))
        self.assertEqual((repeat['disposition'],repeat['provider_calls']),('unchanged',0))
        self.assertEqual(before,tuple(self.archive.entries()))
        self.assertEqual(outcome(get)['disposition'],'unchanged')
        self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=self.now).objects,state.objects)
        self.assertTrue(inspect_archive(self.archive).ready)


if __name__ == '__main__':
    unittest.main()
