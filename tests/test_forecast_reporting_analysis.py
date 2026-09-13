"""Observable reporting-context acceptance; all source archives are synthetic."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext, ROUND_UP
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_analysis as a
import forecast_standalone_research as legacy
from forecast_reporting_source import freeze_reporting_source
from forecast_standalone_operations import DeploymentConfig, NamespaceArchive, OperatingMode, RetryPolicy, archive_pr17_authority
from tests.reporting_fixtures import at, event_sources, archive_events

REVISION = 'a658233dd218638025232630540c8044afb65a35'


class ReportingAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.archive = NamespaceArchive(DeploymentConfig('analysis', 'analysis', OperatingMode.DRY_RUN,
            root/'dry-run/analysis/primary', root/'dry-run/analysis/secondary',
            'https://fixture.invalid', RetryPolicy(1,1,1,(),0), 1, root/'logs'))
        self.cutoff = at('2026-09-12T15:00:00-04:00')
        self.computed = self.cutoff+timedelta(hours=1)

    def freeze(self, events):
        archive_events(self.archive, events, self.cutoff-timedelta(seconds=1))
        return freeze_reporting_source(archive=self.archive, clock=lambda:self.cutoff)

    def create(self, source, protocol, **overrides):
        args = dict(archive=self.archive, source=source, expected_source_boundary_id=source.boundary_id,
                    protocol_id=protocol.standalone_probability_source_protocol_id,
                    software_revision=REVISION, clock=lambda:self.computed)
        args.update(overrides)
        return a.create_standalone_report_analysis(**args)

    def verify(self, source, report, **overrides):
        args = dict(archive=self.archive, source=source, expected_source_boundary_id=source.boundary_id,
                    report=report, clock=lambda:self.computed+timedelta(days=1))
        args.update(overrides)
        return a.verify_standalone_report_analysis(**args)

    def test_valid_empty_calendar_receipt_and_later_date_remain_frozen(self):
        from forecast_standalone_activation import (canonical_mlb_schedule_request,
            merge_mlb_schedule_responses, reconcile_outcomes_from_raw)
        from datetime import date
        event, protocol, _ = event_sources()
        archive_events(self.archive, (event,), self.cutoff-timedelta(seconds=5))
        raw = b'{"dates":[],"totalGames":0}'
        def receipt(day, acquired):
            reconcile_outcomes_from_raw(archive=self.archive,
                mlb_raw=merge_mlb_schedule_responses((raw,)), collected_at=acquired,
                mlb_pages=((day, canonical_mlb_schedule_request(day)[1], raw),))
        receipt('2026-08-21', self.cutoff-timedelta(seconds=1))
        source = freeze_reporting_source(archive=self.archive, clock=lambda:self.cutoff)
        report = self.create(source, protocol)
        self.assertEqual(report.coverages[0].verified_calendar_dates, (date(2026,8,21),))
        self.assertNotIn(date(2026,8,21), report.coverages[0].unknown_calendar_dates)
        receipt('2026-08-22', self.cutoff+timedelta(seconds=1))
        self.verify(source, report)
        self.assertIn(date(2026,8,22), report.coverages[0].unknown_calendar_dates)
        self.assertEqual(report.to_json(), self.create(source, protocol).to_json())

    def test_late_historical_fixed_interval_and_actual_times(self):
        event, protocol, _ = event_sources()
        source = self.freeze((event,))
        ticks = iter(self.computed+timedelta(seconds=i) for i in range(5))
        report = self.create(source, protocol, clock=lambda:next(ticks))
        context = report.context; spec = context.computation
        self.assertEqual(spec.evidence_cutoff_at, self.cutoff)
        self.assertGreater(spec.computation_started_at, self.cutoff)
        self.assertGreater(context.computation_completed_at, spec.computation_started_at)
        self.assertGreater(context.report_generated_at, context.computation_completed_at)
        scope, = spec.bounded_scopes
        self.assertEqual(scope.start, at('2026-03-25T00:00:00-04:00'))
        self.assertEqual(scope.end, at('2026-09-05T00:00:00-04:00'))
        self.assertEqual(int((scope.end-scope.start).total_seconds()), 14169600)
        self.assertEqual([x.sample_size for x in report.performances], [1,1])
        self.assertNotEqual(report.performances[0].object_id, report.performances[1].object_id)
        self.assertEqual(report.measurements[0].calculation.effective_at, spec.computation_started_at)
        self.assertGreater(report.derivations[0].calculation.effective_at, self.cutoff)
        self.assertTrue(report.coverages[0].unknown_calendar_dates)
        self.verify(source, report)

    def test_post_cutoff_outcome_correction_preserves_old_report(self):
        event, protocol, history = event_sources(probability=Decimal('0.8'))
        source = self.freeze((event,)); old = self.create(source, protocol)
        correction_at = self.cutoff+timedelta(hours=2)
        final = history.observations[-1]
        correction = replace(final, observation_id=final.observation_id+':correction',
                             winning_participant_id=final.away_participant_id, losing_participant_id=final.home_participant_id, collected_at=correction_at)
        corrected = replace(history, observations=history.observations+(correction,))
        archive_pr17_authority(self.archive, (corrected,), recorded_at=correction_at)
        self.assertEqual(self.verify(source, old).report_id, old.object_id)
        later = freeze_reporting_source(archive=self.archive, clock=lambda:correction_at+timedelta(seconds=1))
        new = self.create(later, protocol, clock=lambda:correction_at+timedelta(minutes=1))
        self.assertEqual(old.performances[0].mean_brier_score, Decimal('0.04'))
        self.assertEqual(new.performances[0].mean_brier_score, Decimal('0.64'))
        self.assertNotEqual(old.object_id, new.object_id)
        self.assertEqual(a.deserialize_reporting_analysis(old.to_json()).to_json(), old.to_json())

    def test_missed_future_due_and_not_yet_due_are_separate(self):
        missed, protocol, _ = event_sources(design='prospective', name='missed',
            start='2026-09-10T20:00:00-04:00', acquired='2026-09-09T12:00:00Z', missed=True)
        due, _, _ = event_sources(design='prospective', name='future-due',
            start='2026-09-12T20:00:00-04:00', acquired='2026-09-11T12:00:00Z', final=False)
        not_due, _, _ = event_sources(design='prospective', name='not-due',
            start='2026-09-13T20:00:00-04:00', acquired='2026-09-11T12:00:00Z', final=False, capture=False)
        source = self.freeze((missed,due,not_due)); report = self.create(source, protocol)
        coverage = report.coverages[0]
        self.assertEqual(len(coverage.coverage_universe_ids), 3)
        self.assertEqual(len(coverage.eligible_denominator_ids), 2)
        self.assertEqual(len(coverage.reconciliation.capture_not_yet_due), 1)
        self.assertEqual(len(coverage.reconciliation.missed_window), 1)
        self.assertEqual(len(coverage.reconciliation.outcome_unresolved), 1)
        self.assertFalse(coverage.measurement_ids)
        self.assertEqual(len(report.derivations), 1)
        self.assertFalse(report.coverages[1].coverage_universe_ids)
        scope = report.context.computation.bounded_scopes[0]
        self.assertEqual(scope.end, self.cutoff)
        self.assertEqual(scope.end-scope.start, timedelta(seconds=18000))
        self.verify(source, report)

    def test_nonempty_bounded_and_cumulative_are_independent(self):
        old, protocol, _ = event_sources(design='prospective', name='old',
            start='2026-09-10T20:00:00-04:00', acquired='2026-09-09T12:00:00Z')
        recent, _, _ = event_sources(design='prospective', name='recent',
            start='2026-09-12T11:00:00-04:00', acquired='2026-09-11T12:00:00Z')
        source=self.freeze((old,recent)); report=self.create(source,protocol)
        self.assertEqual([x.sample_size for x in report.performances], [2,1])
        self.verify(source,report)

    def test_empty_singleton_constant_and_infinite_scores(self):
        for probabilities in ((), (Decimal('0.5'),), (Decimal('0.5'),Decimal('0.5')), (Decimal('0'),)):
            with self.subTest(probabilities=probabilities), tempfile.TemporaryDirectory() as directory:
                previous=self.archive
                self.archive=NamespaceArchive(replace(previous.config,
                    primary_root=Path(directory)/'dry-run/analysis/primary',
                    secondary_root=Path(directory)/'dry-run/analysis/secondary'))
                generated=[event_sources(name='game-'+str(i),probability=p) for i,p in enumerate(probabilities)]
                if not generated:
                    activation,protocol=__import__('forecast_standalone_activation').canonical_retrospective_authority()
                    events=((activation,protocol),)
                else:
                    protocol=generated[0][1];events=tuple(x[0] for x in generated)
                source=self.freeze(events);report=self.create(source,protocol);performance=report.performances[0]
                self.assertEqual(performance.sample_size,len(probabilities))
                self.assertEqual(performance.uncertainty.confidence_level,Decimal('0.95'))
                self.assertEqual(performance.uncertainty.resample_count,200)
                if not probabilities:
                    self.assertIsNone(performance.mean_brier_score);self.assertIsNone(performance.uncertainty.lower)
                else:
                    self.assertEqual(performance.uncertainty.lower,performance.uncertainty.upper)
                    self.assertTrue(performance.uncertainty.limitations)
                    if probabilities[0]==0:self.assertEqual(performance.mean_log_loss,Decimal('Infinity'))
                self.verify(source,report);self.archive=previous

    def test_exact_replay_under_order_and_decimal_changes(self):
        events=[event_sources(name='varied-'+str(i),probability=p) for i,p in enumerate(
            (Decimal('0.12345678901234567890123456789'),Decimal('0.7'),Decimal('0.9')))]
        source=self.freeze(tuple(x[0] for x in events));protocol=events[0][1]
        original=self.create(source,protocol)
        inventory=self.inventory()
        with patch('socket.socket',side_effect=AssertionError('network forbidden')), \
             patch.object(self.archive,'commit',side_effect=AssertionError('source writes forbidden')), \
             localcontext() as context:
            context.prec=6;context.rounding=ROUND_UP
            entries=self.archive.entries()
            with patch.object(self.archive,'entries',return_value=tuple(reversed(entries))):
                repeated=self.create(source,protocol)
                receipt=self.verify(source,original)
                decoded=a.deserialize_reporting_analysis(original.to_json())
        self.assertEqual(original.to_json(),repeated.to_json())
        self.assertEqual(original.to_json(),decoded.to_json())
        self.assertEqual(original.object_id,receipt.report_id)
        self.assertEqual(inventory,self.inventory())
        self.assertEqual(sum(original.performances[0].calibration.bin_counts),3)

    def inventory(self):
        return {str(p.relative_to(self.archive.root)):p.read_bytes()
                for p in self.archive.root.rglob('*') if p.is_file()}

    def test_foreign_mixed_altered_and_arbitrary_analytical_objects_rejected(self):
        event,protocol,_=event_sources();source=self.freeze((event,));report=self.create(source,protocol)
        material={f.name:getattr(report,f.name) for f in a.fields(report) if f.name!='object_id'}
        for update in ({'measurements':()}, {'measurements':report.measurements*2},
                       {'derivations':()}, {'performances':tuple(reversed(report.performances))},
                       {'coverages':report.coverages[:1]}, {'measurements':(report.measurements[0].calculation,)}):
            forged=a._make(a.StandaloneAnalyticalReport,**{**material,**update})
            with self.assertRaises(legacy.ContractError):self.verify(source,forged)
        other=self.create(source,protocol,clock=lambda:self.computed+timedelta(seconds=1))
        forged=a._make(a.StandaloneAnalyticalReport,**{**material,'measurements':other.measurements})
        with self.assertRaises(legacy.ContractError):self.verify(source,forged)
        with self.assertRaises(legacy.ContractError):a.deserialize_reporting_analysis(report.to_json().replace(
            '"version":"mlb-reporting-analysis-1"','"version":"unknown"'))
        with self.assertRaises(legacy.ContractError):legacy.deserialize_v3(report.to_json())
        with self.assertRaises(legacy.ContractError):a.deserialize_reporting_analysis(report.measurements[0].calculation.to_json())
        with self.assertRaises(legacy.ContractError):self.create(source,protocol,report_status='final')
        with self.assertRaises(legacy.ContractError):self.create(source,protocol,protocol_id='foreign')

    def test_original_fixture_bytes_ids_and_seeds_match_prechange_fingerprint(self):
        import hashlib
        from inspect_forecast_standalone_research import build_synthetic_bundle
        fixture=build_synthetic_bundle()
        values=tuple(x for x in fixture.values() if hasattr(x,'to_json'))
        for value in values:
            self.assertEqual(legacy.deserialize_v3(value.to_json()).to_json(),value.to_json())
        digest=hashlib.sha256('\n'.join(sorted(x.to_json() for x in values)).encode()).hexdigest()
        # Captured from pristine PR #48 main before any helper extraction.
        self.assertEqual(len(values),53)
        self.assertEqual(digest,'ad6dfb171191f074605d56bb9959300e0922ea9b6358095040e8c6c70387dd79')

    def test_omitted_and_invented_opportunities_fail_before_scoring(self):
        event,protocol,_=event_sources()
        opportunity=next(x for x in event if type(x) is legacy.ResearchCaptureOpportunity)
        without=tuple(x for x in event if x is not opportunity)
        archive_events(self.archive,(without,),self.cutoff-timedelta(seconds=1))
        with self.assertRaisesRegex(legacy.ContractError,'omits or invents'):
            freeze_reporting_source(archive=self.archive,clock=lambda:self.cutoff)
        archive_pr17_authority(self.archive,(opportunity,),recorded_at=self.cutoff)
        invented=legacy.ResearchCaptureOpportunity.create(protocol.standalone_probability_source_protocol_id,
                                                         'invented-schedule','winner')
        archive_pr17_authority(self.archive,(invented,),recorded_at=self.cutoff)
        with self.assertRaisesRegex(legacy.ContractError,'omits or invents'):
            freeze_reporting_source(archive=self.archive,clock=lambda:self.cutoff)

    def test_historical_origin_excludes_prior_events_without_sliding(self):
        before,protocol,_=event_sources(name='too-early',start='2026-03-24T20:00:00-04:00')
        within,_,_=event_sources(name='inside',start='2026-03-25T20:00:00-04:00')
        source=self.freeze((before,within));report=self.create(source,protocol)
        self.assertEqual([x.sample_size for x in report.performances],[1,1])
        self.assertEqual(len(report.coverages[0].coverage_universe_ids),1)
        self.verify(source,report)

    def test_invalid_candle_failure_and_unknown_dates_remain_visible(self):
        event,protocol,_=event_sources()
        # No capture is also a valid failure-inclusive source population.
        missing,_,_=event_sources(name='missing',capture=False)
        invalid,_,_=event_sources(name='invalid',probability=None)
        source=self.freeze((event,missing,invalid));report=self.create(source,protocol)
        coverage=report.coverages[0]
        self.assertEqual(len(coverage.coverage_universe_ids),3)
        self.assertEqual(len(coverage.eligible_denominator_ids),3)
        self.assertEqual(len(coverage.reconciliation.archive_unavailable),1)
        self.assertEqual(len(coverage.reconciliation.candle_invalid),1)
        with localcontext() as ctx:
            ctx.prec=50
            self.assertEqual(coverage.coverage_rate,Decimal(1)/3)
        self.assertEqual(len(coverage.unknown_calendar_dates),164)
        self.assertFalse(coverage.verified_calendar_dates)
        self.verify(source,report)

    def test_prospective_required_window_is_not_clamped_to_activation(self):
        from forecast_standalone_activation import canonical_prospective_authority
        activation,protocol=canonical_prospective_authority()
        self.cutoff=activation.activation_at+timedelta(hours=1)
        self.computed=self.cutoff+timedelta(minutes=1)
        source=self.freeze(((activation,protocol),));report=self.create(source,protocol)
        scope=report.context.computation.bounded_scopes[0]
        self.assertLess(scope.start,activation.activation_at)
        self.assertEqual(scope.end-scope.start,timedelta(seconds=18000))
        self.assertEqual(report.performances[0].sample_size,0)
        self.verify(source,report)

    def test_post_cutoff_source_fact_and_market_mapping_provenance_rejected(self):
        from forecast_standalone_operations import OperationsError
        event,_,_=event_sources(design='prospective',name='future-source',
            start='2026-09-10T20:00:00-04:00',acquired='2026-09-09T12:00:00Z')
        series=next(x for x in event if type(x) is legacy.ProviderMarketSeries)
        later=replace(series,provenance=replace(series.provenance,collected_at=self.cutoff+timedelta(days=1)))
        with self.assertRaisesRegex(OperationsError,'post-cutoff source provenance'):
            self.freeze((tuple(later if x is series else x for x in event),))

    def test_late_acquisition_cannot_enter_earlier_empty_historical_report(self):
        from forecast_standalone_activation import canonical_retrospective_authority
        activation,protocol=canonical_retrospective_authority()
        later_cutoff=self.cutoff;later_computed=self.computed
        self.cutoff=activation.activation_at;self.computed=self.cutoff+timedelta(minutes=1)
        early=self.freeze(((activation,protocol),));old=self.create(early,protocol)
        self.assertEqual(old.performances[0].sample_size,0)
        self.cutoff=later_cutoff;self.computed=later_computed
        event,_,_=event_sources()
        later=self.freeze((event,));new=self.create(later,protocol)
        self.assertEqual(new.performances[0].sample_size,1)
        self.assertEqual(old.context.computation.bounded_scopes,new.context.computation.bounded_scopes)
        self.verify(early,old)

    def test_context_scope_rule_and_chronology_tampering_are_rejected(self):
        event,protocol,_=event_sources();source=self.freeze((event,));report=self.create(source,protocol)
        def changed(value,**updates):
            material={f.name:getattr(value,f.name) for f in a.fields(value) if f.name!='object_id'}
            return a._make(type(value),**{**material,**updates})
        spec=report.context.computation
        scope=spec.bounded_scopes[0]
        for replacement in (changed(spec,bounded_scopes=(changed(scope,end=self.cutoff),)),
                            changed(spec,source_boundary_id='foreign'),
                            changed(spec,rule_references=spec.rule_references[:-1]),
                            changed(spec,source_role='market-benchmark')):
            forged=changed(report,context=changed(report.context,computation=replacement))
            with self.assertRaises(legacy.ContractError):self.verify(source,forged)
        with self.assertRaises(legacy.ContractError):
            changed(report.context,computation_completed_at=spec.computation_started_at-timedelta(seconds=1))
        ticks=iter((self.computed+timedelta(seconds=1),self.computed))
        with self.assertRaisesRegex(legacy.ContractError,'clock precedes'):
            self.create(source,protocol,clock=lambda:next(ticks))

    def test_fixed_bin_endpoints_and_unavailable_empty_bins(self):
        events=[event_sources(name='bin-'+str(i),probability=p) for i,p in enumerate(
            (Decimal('0'),Decimal('0.1'),Decimal('0.9'),Decimal('1')))]
        source=self.freeze(tuple(x[0] for x in events));report=self.create(source,events[0][1])
        calibration=report.performances[0].calibration
        self.assertEqual(calibration.bin_counts,(1,1,0,0,0,0,0,0,0,2))
        self.assertEqual(calibration.sample_size,4)
        self.assertEqual(calibration.wace,Decimal('0.5'))
        self.verify(source,report)
