import unittest
from datetime import timedelta
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, getcontext
from pathlib import Path
from types import SimpleNamespace

from event_contracts import ContractError
from forecast_research_contracts import RuleParameter, RulePurpose, VersionedRuleSpecification
from forecast_standalone_performance import (
    CaptureBoundaryDisposition, CaptureBoundaryEligibility, ComparativePerformanceReportV2,
    ProbabilitySourceCoverage, ProbabilitySourcePerformance, ProbabilitySourceRole,
    ResearchProtocolV2, ResearchSnapshotV2, SourceCaptureDispositionV2, SourceCaptureV2,
    SourceEvidenceKind, SourceEvidenceReference, create_probability_source_coverage,
    SourceMeasurementInputKind,_measurement,
    create_source_performance_uncertainty, validate_standalone_research_graph,
    evaluate_capture_boundary_eligibility,
    create_market_backed_source_measurement,create_forecast_backed_source_measurement,create_market_probability_derivation,
    create_comparative_measurement_v2,create_pairwise_synchronization_v2,
    create_time_bounded_probability_source_performance,validate_research_snapshot_v2_authority,
    select_authoritative_snapshots_v2,validate_snapshot_lineages_v2,
)
from outcome_contracts import OutcomeHistory
from inspect_forecast_comparative_research import load_fixture as load_pr14_fixture
from inspect_forecast_standalone_performance import DEFAULT_FIXTURE, PR14_FIXTURE, build_graph, run


class ForecastStandalonePerformanceTests(unittest.TestCase):
    def setUp(self):
        self.graph = build_graph(DEFAULT_FIXTURE)
        g=self.graph
        self.coverage_authority=dict(market_observations=(g["observation"],),market_series=(g["series"],),
            forecast_observations=(g["challenger_observation"],g["challenger_two_observation"]),
            evaluation_eligibility_decisions=(g["challenger_eligibility_decision"],g["challenger_two_eligibility_decision"]),
            forecast_evaluations=(g["challenger_evaluation"],g["challenger_two_evaluation"]))
        self.schedule_evidence=next(item for item in g["outcome_history"].observations
            if item.observation_id==g["opportunity"].schedule_observation_id)

    def derivation_authority(self, observation=None, graph=None):
        g=self.graph if graph is None else graph;observation=g["observation"] if observation is None else observation
        return dict(opportunity=g["opportunity"],schedule_evidence=self.schedule_evidence,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=(observation,))

    def test_fixture_and_inspector_are_offline_deterministic(self):
        self.assertEqual(run(), run())
        self.assertIn("PR16B Standalone Market Benchmark: VALID", run())
        self.assertIn("descriptive findings only", run())

    def test_complete_v2_graph_validates_and_unknown_reference_fails_closed(self):
        g=self.graph
        kwargs=dict(protocols=(g["protocol"],),opportunities=(g["opportunity"],),
            eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),snapshots=(g["snapshot"],),
            market_observations=(g["observation"],),forecast_observations=(g["challenger_observation"],g["challenger_two_observation"]),
            evaluation_eligibility_decisions=(g["challenger_eligibility_decision"],g["challenger_two_eligibility_decision"]),
            forecast_evaluations=(g["challenger_evaluation"],g["challenger_two_evaluation"]),market_series=(g["series"],),
            derivations=(g["derivation"],),outcome_histories=(g["outcome_history"],),
            measurements=(g["measurement"],g["challenger_measurement"],g["challenger_two_measurement"]),
            comparative_measurements=(g["paired_measurement"],g["paired_measurement_two"]),
            coverages=(g["coverage"],),cumulative_performances=(g["performance"],),
            bounded_performances=(g["bounded"],),claims=(g["claim"],g["claim_two"]),protocol_claim_sets=(g["claim_set"],),
            paired_cumulative=(g["paired_historical"],g["paired_performance"],g["paired_historical_two"],g["paired_performance_two"]),
            paired_bounded=(g["paired_bounded"],g["paired_bounded_two"]),paired_drift=(g["paired_drift"],g["paired_drift_two"]),
            scheduled_start_by_opportunity={g["opportunity"].research_capture_opportunity_id:g["snapshot"].scheduled_start},
            scheduled_start_by_snapshot={g["snapshot"].research_snapshot_id:g["snapshot"].scheduled_start},reports=(g["report"],))
        validate_standalone_research_graph(**kwargs)
        with self.assertRaises(ContractError):
            validate_standalone_research_graph(**{**kwargs,"market_observations":()})
        with self.assertRaises(ContractError):
            validate_standalone_research_graph(**{**kwargs,"evaluation_eligibility_decisions":()})
        altered=replace(g["challenger_evaluation"],probability_distribution=(("team:a:away",Decimal("0.36")),("team:a:home",Decimal("0.64"))))
        with self.assertRaises(ContractError):
            validate_standalone_research_graph(**{**kwargs,"forecast_evaluations":(altered,g["challenger_two_evaluation"])})
        with self.assertRaises(ContractError):
            validate_standalone_research_graph(**{**kwargs,"comparative_measurements":(g["paired_measurement"],)})

    def test_midpoint_and_exact_complement(self):
        item = self.graph["derivation"]
        self.assertEqual(item.bid.canonical_price, Decimal("0.54"))
        self.assertEqual(item.offer.canonical_price, Decimal("0.56"))
        self.assertEqual(item.midpoint, Decimal("0.55"))
        self.assertEqual(item.complement_probability, Decimal("0.45"))
        self.assertNotIn("outcome_observation_id", item.__dataclass_fields__)

    def test_market_measurement_reconciles_derivation_exactly(self):
        derivation = self.graph["derivation"]; measurement = self.graph["measurement"]
        self.assertEqual(measurement.probability_distribution, derivation.probability_distribution)
        self.assertEqual(measurement.source_input_id, derivation.market_probability_derivation_id)
        self.assertEqual(measurement.source_role, ProbabilitySourceRole.MARKET_BENCHMARK)
        self.assertEqual(measurement.brier_score, Decimal("0.2025"))

    def test_outcome_correction_selects_matching_measurement_by_boundary(self):
        g=self.graph;old=g["outcome"];corrected=replace(old,observation_id="mlb-stats-api:a:corrected",
            collected_at=old.collected_at+timedelta(hours=1),winning_participant_id=old.losing_participant_id,
            losing_participant_id=old.winning_participant_id,raw_evidence_sha256="c"*64,canonical_evidence_sha256="d"*64)
        history=g["outcome_history"].append(corrected)
        new_measurement=create_market_backed_source_measurement(protocol=g["protocol"],snapshot=g["snapshot"],
            derivation=g["derivation"],outcome=corrected,effective_at=corrected.collected_at,provenance=g["provenance"])
        common=dict(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(g["snapshot"],),derivations=(g["derivation"],),outcome_histories=(history,),measurements=(g["measurement"],new_measurement),**self.coverage_authority)
        before=create_probability_source_coverage(analysis_boundary=old.collected_at,**common)
        after=create_probability_source_coverage(analysis_boundary=corrected.collected_at,**common)
        self.assertEqual(before.measurement_ids,(g["measurement"].probability_source_measurement_id,))
        self.assertEqual(after.measurement_ids,(new_measurement.probability_source_measurement_id,))

    def test_backdating_and_incomplete_schedule_fail_closed(self):
        g=self.graph
        with self.assertRaises(ContractError):create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],
            observation=g["observation"],series=g["series"],effective_at=g["observation"].collected_at-timedelta(seconds=1),provenance=g["provenance"],**self.derivation_authority())
        with self.assertRaises(ContractError):create_market_backed_source_measurement(protocol=g["protocol"],snapshot=g["snapshot"],
            derivation=g["derivation"],outcome=g["outcome"],effective_at=g["outcome"].collected_at-timedelta(seconds=1),provenance=g["provenance"])
        with self.assertRaises(ContractError):create_comparative_measurement_v2(protocol=g["protocol"],benchmark=g["measurement"],
            challenger=g["challenger_measurement"],snapshot=g["snapshot"],opportunity=g["opportunity"],
            schedule_evidence=self.schedule_evidence,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=self.coverage_authority["market_observations"],
            effective_at=g["measurement"].effective_at-timedelta(seconds=1),provenance=g["provenance"])
        with self.assertRaises(ContractError):create_time_bounded_probability_source_performance(protocol=g["protocol"],domain=g["domain"],
            source_reference_id=g["benchmark"].probability_source_reference_id,analysis_boundary=g["boundary"],scheduled_start_by_opportunity={},
            measurements=(g["measurement"],),coverage=g["coverage"],provenance=g["provenance"])

    def test_forecast_projection_and_paired_source_values_reconcile_exactly(self):
        g=self.graph; source=g["challenger_measurement"]; evaluation=g["challenger_evaluation"]; paired=g["paired_measurement"]
        self.assertEqual(source.probability_distribution,evaluation.probability_distribution)
        self.assertEqual(source.brier_score,evaluation.brier_score)
        self.assertEqual(source.log_loss,evaluation.log_loss)
        self.assertEqual(paired.benchmark_probability,g["derivation"].midpoint)
        self.assertEqual(paired.benchmark_brier_score,g["measurement"].brier_score)

    def test_two_claim_populations_are_isolated_and_report_complete(self):
        g=self.graph
        self.assertEqual(g["paired_performance"].comparative_measurement_ids,(g["paired_measurement"].comparative_measurement_id,))
        self.assertEqual(g["paired_performance_two"].comparative_measurement_ids,(g["paired_measurement_two"].comparative_measurement_id,))
        self.assertEqual({item.edge_claim_id for item in g["report"].claim_findings},{g["claim"].edge_claim_id,g["claim_two"].edge_claim_id})
        self.assertNotEqual(g["paired_performance"].challenger_source_reference_id,g["paired_performance_two"].challenger_source_reference_id)

    def test_coverage_rejects_cross_protocol_snapshot_and_measurement_authority(self):
        g=self.graph
        altered_statistical=VersionedRuleSpecification.create(RulePurpose.STANDALONE_STATISTICAL_METHOD,
            "one-sample-brier-bootstrap","1",(RuleParameter("confidence_level",Decimal("0.95")),RuleParameter("resamples",9999)))
        protocol_b=ResearchProtocolV2.create(base_protocol=g["base"],standalone_primary_measure_rule=g["protocol"].standalone_primary_measure_rule,
            standalone_statistical_method_rule=altered_statistical)
        opportunity_b=type(g["opportunity"]).create(protocol_b.research_protocol_id,g["opportunity"].schedule_observation_id,g["opportunity"].proposition_type)
        snapshot=g["snapshot"]
        values={name:getattr(snapshot,name) for name in snapshot.__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version",
                            "protocol_id","research_capture_opportunity_id")}
        snapshot_b=ResearchSnapshotV2.create(protocol_id=protocol_b.research_protocol_id,
            research_capture_opportunity_id=opportunity_b.research_capture_opportunity_id,**values)
        common=dict(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
            analysis_boundary=g["boundary"],opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),
            eligibility_contexts=(g["eligibility_context"],),derivations=(g["derivation"],),
            outcome_histories=(g["outcome_history"],),measurements=(g["measurement"],))
        with self.assertRaises(ContractError):create_probability_source_coverage(snapshots=(snapshot_b,),**common)
        derivation_b=create_market_probability_derivation(protocol=protocol_b,snapshot=snapshot_b,observation=g["observation"],
            series=g["series"],effective_at=g["derivation"].effective_at,provenance=g["provenance"],
            opportunity=opportunity_b,schedule_evidence=self.schedule_evidence,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=(g["observation"],))
        measurement_b=create_market_backed_source_measurement(protocol=protocol_b,snapshot=snapshot_b,derivation=derivation_b,
            outcome=g["outcome"],effective_at=g["measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage(snapshots=(snapshot,),measurements=(measurement_b,),
            **{key:value for key,value in common.items() if key!="measurements"})

    def test_snapshot_schedule_and_target_are_reconstructed(self):
        g=self.graph;snapshot=g["snapshot"]
        schedule=next(item for item in g["outcome_history"].observations if item.observation_id==g["opportunity"].schedule_observation_id)
        validate_research_snapshot_v2_authority(snapshot=snapshot,protocol=g["protocol"],opportunity=g["opportunity"],schedule=schedule,
            forecast_observations={g["challenger_observation"].observation_id:g["challenger_observation"],g["challenger_two_observation"].observation_id:g["challenger_two_observation"]},
            market_observations={g["observation"].observation_id:g["observation"]})
        values={name:getattr(snapshot,name) for name in snapshot.__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version","target_capture_at")}
        altered=ResearchSnapshotV2.create(target_capture_at=snapshot.target_capture_at+timedelta(seconds=1),**values)
        with self.assertRaises(ContractError):validate_research_snapshot_v2_authority(snapshot=altered,protocol=g["protocol"],
            opportunity=g["opportunity"],schedule=schedule,forecast_observations={},market_observations={})

    def test_protocol_invalid_snapshot_cannot_enter_direct_or_graph_analysis(self):
        g=self.graph;snapshot=g["snapshot"]
        values={name:getattr(snapshot,name) for name in snapshot.__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version","target_capture_at")}
        invalid=ResearchSnapshotV2.create(**values,target_capture_at=snapshot.target_capture_at+timedelta(seconds=1))
        with self.assertRaises(ContractError):create_market_probability_derivation(protocol=g["protocol"],snapshot=invalid,
            observation=g["observation"],series=g["series"],effective_at=g["derivation"].effective_at,
            provenance=g["provenance"],**self.derivation_authority())
        benchmark=_measurement(g["protocol"],invalid,g["benchmark"].probability_source_reference_id,
            SourceMeasurementInputKind.MARKET_PROBABILITY_DERIVATION,g["derivation"].market_probability_derivation_id,
            g["outcome"],g["measurement"].effective_at,g["derivation"].probability_distribution,
            g["measurement"].brier_score,g["measurement"].log_loss,g["measurement"].limitations,g["provenance"])
        challenger=create_forecast_backed_source_measurement(protocol=g["protocol"],snapshot=invalid,
            source_reference=g["challenger"],evaluation=g["challenger_evaluation"],outcome=g["outcome"],
            effective_at=g["challenger_measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_comparative_measurement_v2(protocol=g["protocol"],benchmark=benchmark,
            challenger=challenger,snapshot=invalid,opportunity=g["opportunity"],schedule_evidence=self.schedule_evidence,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=self.coverage_authority["market_observations"],
            effective_at=g["paired_measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],
            source_reference_id=g["benchmark"].probability_source_reference_id,analysis_boundary=g["boundary"],
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(invalid,),derivations=(),outcome_histories=(g["outcome_history"],),measurements=(benchmark,),
            **self.coverage_authority)
        with self.assertRaises(ContractError):validate_standalone_research_graph(protocols=(g["protocol"],),
            opportunities=(g["opportunity"],),eligibility_results=(),eligibility_contexts=(),snapshots=(invalid,),
            market_observations=(g["observation"],),forecast_observations=self.coverage_authority["forecast_observations"],
            evaluation_eligibility_decisions=(),forecast_evaluations=(),market_series=(g["series"],),derivations=(),
            outcome_histories=(g["outcome_history"],),measurements=(),coverages=(),cumulative_performances=(),
            bounded_performances=(),scheduled_start_by_opportunity={},scheduled_start_by_snapshot={},reports=())
        with self.assertRaises(ContractError):create_comparative_measurement_v2(protocol=g["protocol"],benchmark=g["measurement"],
            challenger=g["challenger_measurement"],snapshot=snapshot,opportunity=g["opportunity"],schedule_evidence=self.schedule_evidence,
            forecast_observations=(),market_observations=(),effective_at=g["paired_measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],
            source_reference_id=g["benchmark"].probability_source_reference_id,analysis_boundary=g["boundary"],
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(snapshot,),derivations=(g["derivation"],),outcome_histories=(g["outcome_history"],),measurements=(g["measurement"],))

    def test_market_benchmark_provider_and_native_series_lineage_fail_closed(self):
        g=self.graph
        foreign_provider="foreign-market-provider"
        foreign_provenance=replace(g["observation"].provenance,provider=foreign_provider)
        foreign_series_id=f"market-series:{foreign_provider}:{g['series'].provider_market_id}"
        foreign_observation=replace(g["observation"],series_id=foreign_series_id,provenance=foreign_provenance)
        foreign_series=replace(g["series"],series_id=foreign_series_id,provider=foreign_provider,
            provenance=replace(g["series"].provenance,provider="foreign-market-provider"))
        with self.assertRaises(ContractError):create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],
            observation=foreign_observation,series=foreign_series,effective_at=g["derivation"].effective_at,provenance=g["provenance"],
            **self.derivation_authority(foreign_observation))
        with self.assertRaises(ContractError):validate_research_snapshot_v2_authority(snapshot=g["snapshot"],protocol=g["protocol"],
            opportunity=g["opportunity"],schedule=self.schedule_evidence,
            forecast_observations={item.observation_id:item for item in self.coverage_authority["forecast_observations"]},
            market_observations={foreign_observation.observation_id:foreign_observation})
        with self.assertRaises(ContractError):validate_standalone_research_graph(protocols=(g["protocol"],),
            opportunities=(g["opportunity"],),eligibility_results=(),eligibility_contexts=(),snapshots=(g["snapshot"],),
            market_observations=(foreign_observation,),forecast_observations=self.coverage_authority["forecast_observations"],
            evaluation_eligibility_decisions=(),forecast_evaluations=(),market_series=(foreign_series,),derivations=(),
            outcome_histories=(g["outcome_history"],),measurements=(),coverages=(),cumulative_performances=(),
            bounded_performances=(),scheduled_start_by_opportunity={},scheduled_start_by_snapshot={},reports=())
        mismatched_native="different-native-market"
        mismatched_observation=replace(g["observation"],provider_market_id=mismatched_native,
            component_evidence=tuple(replace(item,provider_market_id=mismatched_native) for item in g["observation"].component_evidence))
        with self.assertRaises(ContractError):create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],
            observation=mismatched_observation,series=g["series"],effective_at=g["derivation"].effective_at,provenance=g["provenance"],
            **self.derivation_authority(mismatched_observation))

    def test_snapshot_correction_metadata_and_immutable_history_are_governed(self):
        g=self.graph;root=g["snapshot"]
        root_values={name:getattr(root,name) for name in root.__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version")}
        with self.assertRaises(ContractError):ResearchSnapshotV2.create(**{**root_values,"correction_reason":"invalid root"})
        with self.assertRaises(ContractError):ResearchSnapshotV2.create(**{**root_values,"supersedes_snapshot_id":root.research_snapshot_id})
        child_values={name:value for name,value in root_values.items()
            if name not in ("effective_at","supersedes_snapshot_id","correction_reason")}
        child=ResearchSnapshotV2.create(**child_values,effective_at=root.effective_at+timedelta(minutes=1),
            supersedes_snapshot_id=root.research_snapshot_id,correction_reason="correct accepted-record metadata")
        validate_snapshot_lineages_v2((root,child))
        self.assertEqual(select_authoritative_snapshots_v2((root,child),root.effective_at),(root,))
        self.assertEqual(select_authoritative_snapshots_v2((root,child),child.effective_at),(child,))
        unknown=ResearchSnapshotV2.create(**child_values,effective_at=root.effective_at+timedelta(minutes=1),
            supersedes_snapshot_id="research-snapshot-v2:unknown",correction_reason="unknown predecessor")
        with self.assertRaises(ContractError):validate_snapshot_lineages_v2((root,unknown))
        with self.assertRaises(ContractError):validate_standalone_research_graph(protocols=(g["protocol"],),
            opportunities=(g["opportunity"],),eligibility_results=(),eligibility_contexts=(),snapshots=(root,unknown),
            market_observations=(g["observation"],),forecast_observations=self.coverage_authority["forecast_observations"],
            evaluation_eligibility_decisions=(),forecast_evaluations=(),market_series=(g["series"],),derivations=(),
            outcome_histories=(g["outcome_history"],),measurements=(),coverages=(),cumulative_performances=(),
            bounded_performances=(),scheduled_start_by_opportunity={},scheduled_start_by_snapshot={},reports=())
        branch=ResearchSnapshotV2.create(**child_values,effective_at=root.effective_at+timedelta(minutes=2),
            supersedes_snapshot_id=root.research_snapshot_id,correction_reason="branch")
        with self.assertRaises(ContractError):validate_snapshot_lineages_v2((root,child,branch))
        for changed in ("capture_started_at","capture_completed_at","scheduled_start","target_capture_at"):
            with self.assertRaises(ContractError):
                altered=ResearchSnapshotV2.create(**{**child_values,changed:getattr(root,changed)+timedelta(microseconds=1)},
                    effective_at=root.effective_at+timedelta(minutes=1),supersedes_snapshot_id=root.research_snapshot_id,
                    correction_reason=f"alter {changed}")
                validate_snapshot_lineages_v2((root,altered))
        captures=list(root.source_captures);captures[0]=SourceCaptureV2(captures[0].probability_source_reference_id,
            SourceCaptureDispositionV2.MISSING,None,None,("replacement",))
        altered=ResearchSnapshotV2.create(**{**child_values,"source_captures":tuple(captures)},
            effective_at=root.effective_at+timedelta(minutes=1),supersedes_snapshot_id=root.research_snapshot_id,
            correction_reason="replace capture")
        with self.assertRaises(ContractError):validate_snapshot_lineages_v2((root,altered))

    def test_coverage_rejects_measurement_from_different_derivation(self):
        g=self.graph
        missing=create_probability_source_coverage(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
            analysis_boundary=g["boundary"],opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),
            eligibility_contexts=(g["eligibility_context"],),snapshots=(g["snapshot"],),derivations=(),
            outcome_histories=(g["outcome_history"],),measurements=(),**self.coverage_authority)
        self.assertEqual(missing.derivation_invalid_opportunity_ids,(g["opportunity"].research_capture_opportunity_id,))
        other=create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],observation=g["observation"],
            series=g["series"],effective_at=g["derivation"].effective_at+timedelta(microseconds=1),provenance=g["provenance"],**self.derivation_authority())
        other_measurement=create_market_backed_source_measurement(protocol=g["protocol"],snapshot=g["snapshot"],derivation=other,
            outcome=g["outcome"],effective_at=g["measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],
            source_reference_id=g["benchmark"].probability_source_reference_id,analysis_boundary=g["boundary"],
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(g["snapshot"],),derivations=(g["derivation"],),outcome_histories=(g["outcome_history"],),
            measurements=(other_measurement,),**self.coverage_authority)

    def test_forecast_coverage_replays_exact_evaluation_chain(self):
        g=self.graph
        coverage=create_probability_source_coverage(protocol=g["protocol"],
            source_reference_id=g["challenger"].probability_source_reference_id,analysis_boundary=g["boundary"],
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(g["snapshot"],),derivations=(),outcome_histories=(g["outcome_history"],),
            measurements=(g["challenger_measurement"],),**self.coverage_authority)
        self.assertEqual(coverage.measurement_ids,(g["challenger_measurement"].probability_source_measurement_id,))
        evaluation=g["challenger_evaluation"]
        wrong=_measurement(g["protocol"],g["snapshot"],g["challenger"].probability_source_reference_id,
            SourceMeasurementInputKind.FORECAST_EVALUATION,"forecast-evaluation:different",g["outcome"],
            g["challenger_measurement"].effective_at,evaluation.probability_distribution,evaluation.brier_score,
            evaluation.log_loss,evaluation.limitations,g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],
            source_reference_id=g["challenger"].probability_source_reference_id,analysis_boundary=g["boundary"],
            opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),
            snapshots=(g["snapshot"],),derivations=(),outcome_histories=(g["outcome_history"],),
            measurements=(wrong,),**self.coverage_authority)

    def test_synchronization_is_reproduced_and_forgery_fails(self):
        g=self.graph
        expected=create_pairwise_synchronization_v2(protocol=g["protocol"],snapshot=g["snapshot"],opportunity=g["opportunity"],
            challenger_source_reference_id=g["challenger"].probability_source_reference_id,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=self.coverage_authority["market_observations"])
        self.assertEqual(expected,g["synchronization"])
        forged=replace(expected,separation_microseconds=expected.separation_microseconds+1)
        values={name:getattr(g["snapshot"],name) for name in g["snapshot"].__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version","pairwise_synchronization")}
        forged_snapshot=ResearchSnapshotV2.create(**values,pairwise_synchronization=(forged,g["synchronization_two"]))
        with self.assertRaises(ContractError):create_comparative_measurement_v2(protocol=g["protocol"],benchmark=g["measurement"],
            challenger=g["challenger_measurement"],snapshot=forged_snapshot,opportunity=g["opportunity"],
            schedule_evidence=self.schedule_evidence,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=self.coverage_authority["market_observations"],
            effective_at=g["paired_measurement"].effective_at,provenance=g["provenance"])
        forged_capture=replace(g["challenger_capture"],observed_at=g["challenger_capture"].observed_at+timedelta(seconds=1))
        tamper_values={name:value for name,value in values.items() if name!="source_captures"}
        tampered=ResearchSnapshotV2.create(**tamper_values,source_captures=(g["source_capture"],forged_capture,g["challenger_two_capture"]),
            pairwise_synchronization=(g["synchronization"],g["synchronization_two"]))
        with self.assertRaises(ContractError):create_pairwise_synchronization_v2(protocol=g["protocol"],snapshot=tampered,
            opportunity=g["opportunity"],challenger_source_reference_id=g["challenger"].probability_source_reference_id,
            forecast_observations=self.coverage_authority["forecast_observations"],market_observations=self.coverage_authority["market_observations"])
        strict_rule=VersionedRuleSpecification.create(RulePurpose.SYNCHRONIZATION,"maximum-pair-separation","1",
            (RuleParameter("seconds",1),))
        base_values={name:getattr(g["base"],name) for name in g["base"].__dataclass_fields__
            if name not in ("research_protocol_id","input_digest","schema_version","identity_algorithm_version",
                            "protocol_version","synchronization_rule")}
        strict_base=type(g["base"]).create(protocol_version="2",synchronization_rule=strict_rule,**base_values)
        strict_protocol=ResearchProtocolV2.create(base_protocol=strict_base,
            standalone_primary_measure_rule=g["protocol"].standalone_primary_measure_rule,
            standalone_statistical_method_rule=g["protocol"].standalone_statistical_method_rule)
        strict_opportunity=type(g["opportunity"]).create(strict_protocol.research_protocol_id,
            g["opportunity"].schedule_observation_id,g["opportunity"].proposition_type)
        late_at=g["challenger_observation"].collected_at+timedelta(seconds=2)
        late_evidence=replace(g["challenger_observation"],collected_at=late_at,
            provenance=replace(g["challenger_observation"].provenance,collected_at=late_at))
        late_capture=replace(g["challenger_capture"],observed_at=late_evidence.collected_at)
        strict_values={name:getattr(g["snapshot"],name) for name in g["snapshot"].__dataclass_fields__
            if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version",
                            "protocol_id","research_capture_opportunity_id","source_captures","pairwise_synchronization")}
        strict_snapshot=ResearchSnapshotV2.create(protocol_id=strict_protocol.research_protocol_id,
            research_capture_opportunity_id=strict_opportunity.research_capture_opportunity_id,
            source_captures=(g["source_capture"],late_capture,g["challenger_two_capture"]),pairwise_synchronization=(),**strict_values)
        rejected=create_pairwise_synchronization_v2(protocol=strict_protocol,snapshot=strict_snapshot,
            opportunity=strict_opportunity,challenger_source_reference_id=g["challenger"].probability_source_reference_id,
            forecast_observations=(late_evidence,g["challenger_two_observation"]),market_observations=(g["observation"],))
        self.assertFalse(rejected.synchronized)

    def test_equal_price_depth_preserves_all_levels_and_is_order_independent(self):
        g=self.graph;yes=next(item for item in g["observation"].order_book if item.acquisition_side.value=="yes");no=next(item for item in g["observation"].order_book if item.acquisition_side.value=="no")
        derived_yes=replace(yes,quantity=Decimal("7"),evidence_kind=type(yes.evidence_kind).DERIVED_FROM_OPPOSITE_BID,
            provider_book_side=type(yes.acquisition_side).NO,provider_price=Decimal(1)-yes.acquisition_price,
            transformation="acquisition offer = 1 - opposite-side bid",source_endpoint="/fixture/orderbook/second")
        levels=(yes,derived_yes,
                no,replace(no,quantity=Decimal("9"),source_endpoint="/fixture/orderbook/second"))
        first_observation=replace(g["observation"],order_book=levels);second_observation=replace(g["observation"],order_book=tuple(reversed(levels)))
        first=create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],
            observation=first_observation,series=g["series"],effective_at=g["derivation"].effective_at,provenance=g["provenance"],**self.derivation_authority(first_observation))
        second=create_market_probability_derivation(protocol=g["protocol"],snapshot=g["snapshot"],
            observation=second_observation,series=g["series"],effective_at=g["derivation"].effective_at,provenance=g["provenance"],**self.derivation_authority(second_observation))
        self.assertEqual(first,second);self.assertEqual(first.to_json(),second.to_json())
        self.assertEqual(len(first.offer.contributing_levels),2);self.assertEqual(len(first.bid.contributing_levels),2)
        self.assertEqual({item.evidence_kind for item in first.offer.contributing_levels},{type(yes.evidence_kind).DIRECT_ASK,type(yes.evidence_kind).DERIVED_FROM_OPPOSITE_BID})
        self.assertTrue(any(item.evidence_transformation for item in first.offer.contributing_levels))
        self.assertEqual(first.offer.quantity,sum((item.quantity for item in first.offer.contributing_levels),Decimal(0)))
        self.assertEqual(first.bid.quantity,sum((item.quantity for item in first.bid.contributing_levels),Decimal(0)))

    def test_three_population_levels_reconcile(self):
        coverage = self.graph["coverage"]
        self.assertEqual(set(coverage.universe_opportunity_ids),
                         set(coverage.capture_not_yet_due_opportunity_ids)
                         | set(coverage.protocol_ineligible_opportunity_ids)
                         | set(coverage.eligible_denominator_opportunity_ids))
        self.assertEqual(coverage.measured_opportunity_ids, coverage.eligible_denominator_opportunity_ids)
        self.assertEqual(coverage.coverage_rate, Decimal("1"))

    def test_challenger_state_is_absent_from_standalone_coverage(self):
        fields = set(ProbabilitySourceCoverage.__dataclass_fields__)
        self.assertFalse(any("challenger" in name or "synchron" in name for name in fields))
        self.assertEqual(self.graph["performance"].measurement_ids, self.graph["coverage"].measurement_ids)

    def test_missing_capture_stays_in_eligible_denominator(self):
        graph = self.graph; snapshot = graph["snapshot"]
        values={name:getattr(snapshot,name) for name in snapshot.__dataclass_fields__
                if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version","snapshot_algorithm_version","source_captures","pairwise_synchronization")}
        captures=(SourceCaptureV2(
            graph["benchmark"].probability_source_reference_id,
            SourceCaptureDispositionV2.MISSING, None, None, ("synthetic missing",)),graph["challenger_capture"],graph["challenger_two_capture"])
        seed=type(snapshot).create(**values,source_captures=captures,pairwise_synchronization=())
        pairs=tuple(create_pairwise_synchronization_v2(protocol=graph["protocol"],snapshot=seed,opportunity=graph["opportunity"],
            challenger_source_reference_id=source.probability_source_reference_id)
            for source in graph["protocol"].alternative_sources)
        missing=type(snapshot).create(**values,source_captures=captures,pairwise_synchronization=pairs)
        coverage = create_probability_source_coverage(protocol=graph["protocol"],
            source_reference_id=graph["benchmark"].probability_source_reference_id,
            analysis_boundary=graph["boundary"], opportunities=(graph["opportunity"],),
            eligibility_results=(graph["eligibility"],),eligibility_contexts=(graph["eligibility_context"],), snapshots=(missing,), derivations=(),
            outcome_histories=(graph["outcome_history"],), measurements=(),**self.coverage_authority)
        self.assertEqual(coverage.eligible_denominator_opportunity_ids, (graph["opportunity"].research_capture_opportunity_id,))
        self.assertEqual(coverage.source_capture_missing_opportunity_ids, coverage.eligible_denominator_opportunity_ids)
        self.assertEqual(coverage.measurement_ids, ())

    def test_not_due_and_ineligible_never_enter_denominator(self):
        g=self.graph;target=g["snapshot"].target_capture_at
        before=create_probability_source_coverage(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
            analysis_boundary=target-timedelta(microseconds=1),opportunities=(g["opportunity"],),eligibility_results=(),eligibility_contexts=(),snapshots=(),derivations=(),outcome_histories=(g["outcome_history"],),measurements=())
        self.assertEqual(before.capture_not_yet_due_opportunity_ids,(g["opportunity"].research_capture_opportunity_id,));self.assertEqual(before.eligible_denominator_opportunity_ids,())
        stale_context=type(g["eligibility_context"]).create(opportunity=g["base_opportunity"],protocol=g["base"],canonical_event=g["canonical_event"],stage_evidence=g["stage_evidence"],outcome_history=g["outcome_history"],analysis_boundary=target-timedelta(microseconds=1))
        with self.assertRaises(ContractError):evaluate_capture_boundary_eligibility(protocol=g["protocol"],opportunity=g["opportunity"],context=stale_context,provenance=g["provenance"])
        for boundary in (target,target+timedelta(seconds=1)):
            due=create_probability_source_coverage(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
                analysis_boundary=boundary,opportunities=(g["opportunity"],),eligibility_results=(g["eligibility"],),eligibility_contexts=(g["eligibility_context"],),snapshots=(),derivations=(),outcome_histories=(g["outcome_history"],),measurements=())
            self.assertEqual(due.eligible_denominator_opportunity_ids,(g["opportunity"].research_capture_opportunity_id,));self.assertEqual(due.source_capture_missing_opportunity_ids,due.eligible_denominator_opportunity_ids)

    def test_caller_asserted_eligibility_is_rejected(self):
        g=self.graph;base=g["eligibility"]
        asserted=CaptureBoundaryEligibility._create_derived(protocol_id=base.protocol_id,opportunity_id=base.research_capture_opportunity_id,
            eligibility_boundary=base.eligibility_boundary,research_population_id=base.research_population_id,
            governing_rule_specification_ids=base.governing_rule_specification_ids,context_evidence_ids=base.context_evidence_ids,
            disposition=CaptureBoundaryDisposition.PROTOCOL_INELIGIBLE,reason_codes=("caller-asserted",),provenance=base.provenance)
        with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
            analysis_boundary=g["boundary"],opportunities=(g["opportunity"],),eligibility_results=(asserted,),eligibility_contexts=(g["eligibility_context"],),snapshots=(),derivations=(),outcome_histories=(g["outcome_history"],),measurements=())

    def test_duplicate_eligibility_fails_independent_of_order(self):
        g=self.graph
        for values in ((g["eligibility"],g["eligibility"]),tuple(reversed((g["eligibility"],g["eligibility"])))):
            with self.assertRaises(ContractError):create_probability_source_coverage(protocol=g["protocol"],source_reference_id=g["benchmark"].probability_source_reference_id,
                analysis_boundary=g["boundary"],opportunities=(g["opportunity"],),eligibility_results=values,eligibility_contexts=(g["eligibility_context"],),snapshots=(g["snapshot"],),derivations=(g["derivation"],),outcome_histories=(g["outcome_history"],),measurements=(g["measurement"],))

    def test_uncertainty_empty_singleton_identical_and_nondegenerate(self):
        graph=self.graph; kwargs=dict(protocol=graph["protocol"],domain=graph["domain"],
            source_reference_id=graph["benchmark"].probability_source_reference_id,
            role=ProbabilitySourceRole.MARKET_BENCHMARK,scope="cumulative",analysis_boundary=graph["boundary"])
        empty=create_source_performance_uncertainty(measurements=(),**kwargs)
        self.assertIsNone(empty.point_estimate); self.assertIsNone(empty.lower_bound)
        single=create_source_performance_uncertainty(measurements=(graph["measurement"],),**kwargs)
        self.assertEqual(single.lower_bound,single.upper_bound); self.assertTrue(single.limitations)
        identical=create_source_performance_uncertainty(measurements=(
            SimpleNamespace(probability_source_measurement_id="measurement:a",brier_score=Decimal("0.2")),
            SimpleNamespace(probability_source_measurement_id="measurement:b",brier_score=Decimal("0.2"))),**kwargs)
        self.assertEqual(identical.lower_bound,identical.upper_bound);self.assertTrue(identical.limitations)
        varied=create_source_performance_uncertainty(measurements=(
            SimpleNamespace(probability_source_measurement_id="measurement:a",brier_score=Decimal("0.1")),
            SimpleNamespace(probability_source_measurement_id="measurement:b",brier_score=Decimal("0.3"))),**kwargs)
        self.assertLessEqual(varied.lower_bound,varied.point_estimate);self.assertGreaterEqual(varied.upper_bound,varied.point_estimate)

    def test_ambient_decimal_context_is_nonmaterial(self):
        before=self.graph["performance"]
        old=getcontext().prec
        try:
            getcontext().prec=7
            again=build_graph(DEFAULT_FIXTURE)["performance"]
        finally:getcontext().prec=old
        self.assertEqual(before,again)

    def test_time_bounded_window_is_open_left_closed_right(self):
        bounded=self.graph["bounded"]
        self.assertLess(bounded.window_start,bounded.window_end)
        self.assertEqual(bounded.window_end,bounded.analysis_boundary)
        self.assertFalse(hasattr(bounded,"drift"))

    def test_report_v2_references_without_copying_metrics(self):
        report=self.graph["report"]
        self.assertEqual(report.contract_version,"2")
        self.assertEqual(report.cumulative_benchmark_reference.performance_id,
                         self.graph["performance"].probability_source_performance_id)
        self.assertNotIn("mean_brier_score", report.__dataclass_fields__)
        finding=report.claim_findings[0]
        self.assertEqual(finding.cumulative.contract_version,"2")
        self.assertEqual(finding.drift.current_bounded_performance_id,finding.time_bounded.performance_id)
        with self.assertRaises(ContractError):
            ComparativePerformanceReportV2.create(protocol=self.graph["protocol"],
                protocol_claim_set=self.graph["claim_set"],analysis_boundary=self.graph["boundary"],
                cumulative=self.graph["performance"],time_bounded=self.graph["bounded"],
                claims=(),paired_cumulative=(),paired_time_bounded=(),paired_drift=(),provenance=self.graph["provenance"])
        with self.assertRaises(ContractError):
            ComparativePerformanceReportV2.create(protocol=self.graph["protocol"],protocol_claim_set=self.graph["claim_set"],
                analysis_boundary=self.graph["boundary"],cumulative=self.graph["performance"],time_bounded=self.graph["bounded"],
                claims=(self.graph["claim"],),paired_cumulative=(self.graph["paired_historical"],self.graph["paired_performance"]),
                paired_time_bounded=(self.graph["paired_bounded"],),paired_drift=(),provenance=self.graph["provenance"])

    def test_v2_objects_are_immutable_and_round_trip(self):
        for item in (self.graph["protocol"],self.graph["snapshot"],self.graph["derivation"],
                     self.graph["measurement"],self.graph["coverage"],self.graph["performance"],self.graph["bounded"],
                     self.graph["paired_performance"],self.graph["paired_bounded"],self.graph["paired_drift"],self.graph["report"]):
            self.assertEqual(type(item).from_json(item.to_json()),item)
            with self.assertRaises(FrozenInstanceError): item.input_digest="changed"

    def test_v1_identity_and_serialization_are_unchanged(self):
        old=load_pr14_fixture(PR14_FIXTURE)
        for item in (old["protocols"][0],old["snapshots"][0],old["measurements"][0],old["performances"][0]):
            encoded=item.to_json(); self.assertEqual(type(item).from_json(encoded).to_json(),encoded)
            self.assertNotIn('"schema_version":"2"',encoded)

    def test_v1_protocol_cannot_authorize_standalone(self):
        old=load_pr14_fixture(PR14_FIXTURE)["protocols"][0]
        primary=VersionedRuleSpecification.create(RulePurpose.STANDALONE_PRIMARY_MEASURE,"mean-brier-score","1")
        statistical=VersionedRuleSpecification.create(RulePurpose.STANDALONE_STATISTICAL_METHOD,"one-sample-brier-bootstrap","1",(
            RuleParameter("confidence_level",Decimal("0.95")),RuleParameter("resamples",10)))
        with self.assertRaises(ContractError):ResearchProtocolV2.create(base_protocol=old,
            standalone_primary_measure_rule=primary,standalone_statistical_method_rule=statistical)

    def test_segmented_domain_fails_closed(self):
        segmented=next(item for item in self.graph["base"].research_domains if item.partition_selections)
        with self.assertRaises(ContractError):
            from forecast_standalone_performance import create_probability_source_performance
            create_probability_source_performance(protocol=self.graph["protocol"],domain=segmented,
                source_reference_id=self.graph["benchmark"].probability_source_reference_id,
                analysis_boundary=self.graph["boundary"],measurements=(self.graph["measurement"],),
                coverage=self.graph["coverage"],provenance=self.graph["provenance"])


if __name__ == "__main__": unittest.main()
