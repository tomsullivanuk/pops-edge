import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal, getcontext, localcontext

import forecast_standalone_research as fsr
from event_contracts import ContractError
from forecast_comparative_research import PopulationEligibilityDisposition, PopulationEligibilityResult, PopulationEligibilityValidationStatus
from forecast_standalone_research import *
from inspect_forecast_standalone_research import build_synthetic_bundle, run


def graph_args(g, path="both", reports=True):
    retro=path in ("retro","both");pros=path in ("pros","both")
    pick=lambda items:tuple(value for enabled,value in items if enabled)
    return dict(activation_boundaries=(g["activation"],),protocols=pick(((retro,g["retrospective"]),(pros,g["prospective"]))),
        opportunities=pick(((retro,g["retro_opportunity"]),(retro,g["retro_failure"]),(pros,g["opportunity"]),(pros,g["prospective_failure"]))),
        classifications=pick(((retro,g["retro_classification"]),(retro,g["retro_failure_classification"]),(pros,g["prospective_classification"]),(pros,g["prospective_failure_classification"]))),
        eligibility_contexts=pick(((retro,g["retro_context"]),(retro,g["retro_failure_context"]),(pros,g["prospective_context"]),(pros,g["prospective_failure_context"]))),
        eligibility_results=pick(((retro,g["retro_eligibility"]),(retro,g["retro_failure_eligibility"]),(pros,g["prospective_eligibility"]),(pros,g["prospective_failure_eligibility"]))),
        manifests=(g["manifest"],) if retro else (),candles=(g["candle"],) if retro else (),historical_derivations=(g["retrospective_derivation"],) if retro else (),
        attempts=tuple(g["attempts"])+g["prospective_failure_attempts"] if pros else (),snapshots=(g["snapshot"],g["prospective_failure_snapshot"]) if pros else (),market_observations=(g["observation"],) if pros else (),
        market_series=(g["series"],) if pros else (),market_derivations=(g["prospective_derivation"],) if pros else (),
        outcome_histories=pick(((retro,g["retro_history"]),(retro,g["retro_failure_history"]),(pros,g["legacy"]["outcome_history"]),(pros,g["prospective_failure_history"]))),
        measurements=pick(((retro,g["retro_measurement"]),(pros,g["prospective_measurement"]))),coverages=pick(((retro,g["retro_coverage"]),(retro,g["retro_bounded_coverage"]),(pros,g["prospective_coverage"]),(pros,g["prospective_bounded_coverage"]))),
        performances=pick(((retro,g["retro_performance"]),(retro,g["retro_bounded_performance"]),(pros,g["prospective_performance"]),(pros,g["prospective_bounded_performance"]))),reports=pick(((retro and reports,g["retro_report"]),(pros and reports,g["prospective_report"]))),
        analysis_boundary=max(value.report_boundary for enabled,value in ((retro,g["retro_report"]),(pros,g["prospective_report"])) if enabled))


def measurement_variant(base,p,index):
    values={name:getattr(base,name) for name in base.__dataclass_fields__ if name not in
        ("probability_source_measurement_v3_id","input_digest","provenance","probability_distribution","realized_outcome_id","brier_score","log_loss","calibration_probability","arithmetic_inputs","opportunity_id","schedule_observation_id")}
    home=base.canonical_proposition_outcome_id;away=next(x for x,_ in base.probability_distribution if x!=home);distribution=tuple(sorted(((home,p),(away,Decimal(1)-p))))
    with localcontext() as context:context.prec=50;brier=(p-1)**2;log=-p.ln()
    values.update(opportunity_id=f"synthetic-bootstrap-opportunity:{index}",schedule_observation_id=f"synthetic-bootstrap-schedule:{index}",
        probability_distribution=distribution,realized_outcome_id=home,brier_score=brier,log_loss=log,calibration_probability=p,
        arithmetic_inputs=tuple((key,value,int(key==home)) for key,value in distribution),provenance=base.provenance)
    return fsr._identity(ProbabilitySourceMeasurementV3,"probability_source_measurement_v3",values,("probability_source_measurement_v3_id","provenance","input_digest"))


def prospective_coverage_args(g,**overrides):
    values=dict(protocol=g["prospective"],analysis_boundary=g["prospective_coverage"].analysis_boundary,activation=g["activation"],
        opportunities=(g["opportunity"],g["prospective_failure"]),eligibility_contexts=(g["prospective_context"],g["prospective_failure_context"]),
        eligibility_results=(g["prospective_eligibility"],g["prospective_failure_eligibility"]),schedule_histories=(g["legacy"]["outcome_history"],g["prospective_failure_history"]),
        classifications=(g["prospective_classification"],g["prospective_failure_classification"]),
        attempts=tuple(g["attempts"])+g["prospective_failure_attempts"],snapshots=(g["snapshot"],g["prospective_failure_snapshot"]),market_observations=(g["observation"],),market_series=(g["series"],),
        market_derivations=(g["prospective_derivation"],),measurements=(g["prospective_measurement"],),provenance=g["provenance"])
    values.update(overrides);return values


def retro_coverage_args(g,**overrides):
    values=dict(protocol=g["retrospective"],analysis_boundary=g["retro_coverage"].analysis_boundary,activation=g["activation"],
        opportunities=(g["retro_opportunity"],g["retro_failure"]),eligibility_contexts=(g["retro_context"],g["retro_failure_context"]),
        eligibility_results=(g["retro_eligibility"],g["retro_failure_eligibility"]),schedule_histories=(g["retro_history"],g["retro_failure_history"]),
        classifications=(g["retro_classification"],g["retro_failure_classification"]),
        manifests=(g["manifest"],),candles=(g["candle"],),historical_derivations=(g["retrospective_derivation"],),
        measurements=(g["retro_measurement"],),provenance=g["provenance"])
    values.update(overrides);return values


def classification_variant(base,**overrides):
    values={name:getattr(base,name) for name in base.__dataclass_fields__ if name not in ("standalone_event_classification_evidence_id","input_digest","schema_version","identity_algorithm_version")}
    values.update(overrides);return StandaloneEventClassificationEvidence.create(**values)


def prospective_success_variant(g,first_result,called):
    first=g["attempts"][0];kwargs={name:getattr(first,name) for name in first.__dataclass_fields__ if name not in ("prospective_capture_attempt_id","input_digest","schema_version","identity_algorithm_version","result","provider_call_occurred")}
    changed=ProspectiveCaptureAttempt.create(**kwargs,result=first_result,provider_call_occurred=called)
    attempts=(changed,)+tuple(g["attempts"][1:])
    snapshot=reconcile_prospective_snapshot(protocol=g["prospective"],opportunity=g["opportunity"],activation=g["activation"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=g["snapshot"].effective_at,attempts=attempts,window_closed_at=g["prospective_target"]+timedelta(minutes=5),provenance=g["provenance"])
    derivation=create_standalone_market_probability_derivation(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=snapshot.effective_at,snapshot=snapshot,snapshots=(snapshot,g["prospective_failure_snapshot"]),attempts=attempts,observation=g["observation"],market_observations=(g["observation"],),series=g["series"],effective_at=snapshot.effective_at,provenance=g["provenance"])
    measurement=create_probability_source_measurement_v3(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],snapshots=(snapshot,),derivations=(derivation,),outcome=g["legacy"]["outcome"],outcome_histories=(g["legacy"]["outcome_history"],),effective_at=g["legacy"]["outcome"].collected_at,provenance=g["provenance"])
    coverage=create_probability_source_coverage_v3(**prospective_coverage_args(g,attempts=attempts+g["prospective_failure_attempts"],snapshots=(snapshot,g["prospective_failure_snapshot"]),market_derivations=(derivation,),measurements=(measurement,)))
    return attempts,snapshot,derivation,measurement,coverage


class StandaloneResearchV3Tests(unittest.TestCase):
    def setUp(self):self.g=build_synthetic_bundle()

    def test_01_inspector_deterministic_separate_and_failure_visible(self):
        self.assertEqual(run(),run());self.assertIn("NON-AUTHORITATIVE",run());self.assertIn('"combined_metric":null',run())
        self.assertEqual(self.g["retro_coverage"].coverage_rate,Decimal("0.5"));self.assertEqual(self.g["prospective_coverage"].coverage_rate,Decimal("0.5"))

    def test_02_immutable_and_v3_round_trip(self):
        with self.assertRaises(FrozenInstanceError):self.g["activation"].timezone_name="UTC"
        for value in (self.g["manifest"],self.g["snapshot"],self.g["retro_report"]):self.assertEqual(deserialize_v3(value.to_json()),value)

    def test_03_unknown_type_and_version_rejected(self):
        with self.assertRaises(ContractError):deserialize_v3('{"__type__":"UnknownV3"}')
        with self.assertRaises(ContractError):deserialize_v3(self.g["retro_report"].to_json().replace('"schema_version":"3"','"schema_version":"99"'))

    def test_04_activation_partition_exact(self):
        b=self.g["activation"].activation_at;validate_population_side(self.g["retrospective"],self.g["activation"],b-timedelta(microseconds=1));validate_population_side(self.g["prospective"],self.g["activation"],b)
        with self.assertRaises(ContractError):validate_population_side(self.g["retrospective"],self.g["activation"],b)
        with self.assertRaises(ContractError):validate_population_side(self.g["prospective"],self.g["activation"],b-timedelta(microseconds=1))

    def test_05_hybrid_and_foreign_activation_rejected(self):
        g=self.g
        with self.assertRaises(ContractError):StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.RETROSPECTIVE,design=g["prospective"].design,source=g["legacy"]["benchmark"],provenance=g["provenance"],**g["rules"])
        foreign=StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.PROSPECTIVE,design=replace(g["prospective"].design,activation_boundary_id="foreign"),source=g["legacy"]["benchmark"],provenance=g["provenance"],**g["rules"])
        with self.assertRaises(ContractError):validate_population_side(foreign,g["activation"],g["activation"].activation_at)

    def test_06_manifest_empty_completed_page(self):
        g=self.g;page=HistoricalCandleRetrievalPage("initial",0,None,True,"synthetic-empty","f"*64,g["acquired"],(),ManifestValidationStatus.COMPLETE)
        manifest=HistoricalCandleQueryManifest.create(protocol_id=g["retrospective"].standalone_probability_source_protocol_id,opportunity_id=g["retro_opportunity"].research_capture_opportunity_id,canonical_event_id=g["retro_schedule"].canonical_event_id,proposition_id=g["candle"].proposition_id,provider_id="kalshi",endpoint="synthetic://empty",provider_market_id="empty",interval="1m",requested_start_at=g["target"]-timedelta(minutes=5),requested_end_at=g["target"],pages=(page,),retrieval_started_at=g["acquired"],retrieval_completed_at=g["acquired"],returned_candle_evidence_ids=(),validation_status=ManifestValidationStatus.COMPLETE,limitations=(),effective_at=g["acquired"],supersedes_manifest_id=None,correction_reason=None,provenance=g["provenance"])
        self.assertEqual(manifest.returned_candle_evidence_ids,())

    def test_07_manifest_cursor_position_and_completion_fail_closed(self):
        g=self.g;t=g["acquired"];first=HistoricalCandleRetrievalPage("initial",0,"next",False,"a","1"*64,t,(),ManifestValidationStatus.COMPLETE)
        bad_pages=((first,HistoricalCandleRetrievalPage("wrong",1,None,True,"b","2"*64,t+timedelta(seconds=1),(),ManifestValidationStatus.COMPLETE)),(first,HistoricalCandleRetrievalPage("next",0,None,True,"b","2"*64,t+timedelta(seconds=1),(),ManifestValidationStatus.COMPLETE)))
        for pages in bad_pages:
            with self.subTest(pages=pages),self.assertRaises(ContractError):HistoricalCandleQueryManifest.create(protocol_id=g["retrospective"].standalone_probability_source_protocol_id,opportunity_id=g["retro_opportunity"].research_capture_opportunity_id,canonical_event_id=g["retro_schedule"].canonical_event_id,proposition_id=g["candle"].proposition_id,provider_id="kalshi",endpoint="x",provider_market_id="x",interval="1m",requested_start_at=g["target"]-timedelta(minutes=5),requested_end_at=g["target"],pages=pages,retrieval_started_at=t,retrieval_completed_at=t+timedelta(seconds=1),returned_candle_evidence_ids=(),validation_status=ManifestValidationStatus.COMPLETE,limitations=(),effective_at=t+timedelta(seconds=1),supersedes_manifest_id=None,correction_reason=None,provenance=g["provenance"])
        with self.assertRaises(ContractError):replace(g["manifest"],retrieval_completed_at=None)

    def test_08_manifest_orphan_and_boundary_replay(self):
        g=self.g;m=g["manifest"];kwargs={name:getattr(m,name) for name in m.__dataclass_fields__ if name not in ("historical_candle_query_manifest_id","input_digest","schema_version","identity_algorithm_version","supersedes_manifest_id","correction_reason","effective_at")}
        orphan=HistoricalCandleQueryManifest.create(**kwargs,effective_at=m.effective_at+timedelta(seconds=1),supersedes_manifest_id="unknown",correction_reason="fix")
        with self.assertRaises(ContractError):validate_manifest_lineage((m,orphan),orphan.effective_at)
        child=HistoricalCandleQueryManifest.create(**kwargs,effective_at=m.effective_at+timedelta(seconds=1),supersedes_manifest_id=m.historical_candle_query_manifest_id,correction_reason="fix")
        self.assertEqual(validate_manifest_lineage((m,child),m.effective_at),(m,));self.assertEqual(validate_manifest_lineage((m,child),child.effective_at),(child,))

    def test_09_historical_target_and_complete_candidates(self):
        g=self.g;self.assertEqual(g["retrospective_derivation"].target_at,g["retro_schedule"].scheduled_start-timedelta(hours=6))
        with self.assertRaises(ContractError):create_historical_candle_probability_derivation(protocol=g["retrospective"],activation=g["activation"],opportunity=g["retro_opportunity"],eligibility_context=g["retro_context"],eligibility_result=g["retro_eligibility"],schedule_history=g["retro_history"],analysis_boundary=g["manifest"].effective_at,manifest=g["manifest"],manifests=(g["manifest"],),candles=(),home_participant_id=g["candle"].home_participant_id,complement_outcome_id="synthetic-team:retro-away",effective_at=g["retrospective_derivation"].effective_at,provenance=g["provenance"])

    def test_10_foreign_schedule_opportunity_rejected(self):
        g=self.g;foreign=ResearchCaptureOpportunity.create(g["retrospective"].standalone_probability_source_protocol_id,"foreign-schedule","winner")
        with self.assertRaises(ContractError):resolve_standalone_schedule_authority(protocol=g["retrospective"],activation=g["activation"],opportunity=foreign,eligibility_context=g["retro_context"],eligibility_result=g["retro_eligibility"],outcome_history=g["retro_history"],analysis_boundary=g["retro_report"].analysis_boundary)

    def test_11_exact_five_slots(self):
        target=self.g["prospective_target"];self.assertEqual([slot_for_time(target,target+timedelta(minutes=x)) for x in range(5)],[0,1,2,3,4]);self.assertEqual(slot_for_time(target,target+timedelta(minutes=5)),4)
        with self.assertRaises(ContractError):slot_for_time(target,target+timedelta(minutes=5,microseconds=1))

    def test_12_attempt_idempotency_and_conflicting_slot(self):
        g=self.g;common=dict(protocol=g["prospective"],opportunity=g["opportunity"],activation=g["activation"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=g["snapshot"].effective_at,window_closed_at=g["prospective_target"]+timedelta(minutes=5),provenance=g["provenance"])
        self.assertEqual(reconcile_prospective_snapshot(attempts=tuple(g["attempts"])+(g["attempts"][0],),**common),g["snapshot"])
        item=g["attempts"][1];conflict=ProspectiveCaptureAttempt.create(**{name:getattr(item,name) for name in item.__dataclass_fields__ if name not in ("prospective_capture_attempt_id","input_digest","schema_version","identity_algorithm_version","result","provider_call_occurred")},result=AcquisitionFailed(AttemptFailureCategory.TIMEOUT,"synthetic-call"),provider_call_occurred=True)
        with self.assertRaises(ContractError):reconcile_prospective_snapshot(attempts=tuple(g["attempts"])+(conflict,),**common)

    def test_13_shifted_target_rejected(self):
        g=self.g;item=g["attempts"][0]
        with self.assertRaises(ContractError):ProspectiveCaptureAttempt.create(**{name:getattr(item,name) for name in item.__dataclass_fields__ if name not in ("prospective_capture_attempt_id","input_digest","schema_version","identity_algorithm_version","target_at","slot")},target_at=item.target_at+timedelta(minutes=1),slot=0)

    def test_14_snapshot_correction_earlier_later(self):
        g=self.g;s=g["snapshot"];kwargs={name:getattr(s,name) for name in s.__dataclass_fields__ if name not in ("prospective_standalone_snapshot_id","input_digest","schema_version","identity_algorithm_version","effective_at","supersedes_snapshot_id","correction_reason")}
        child=fsr._identity(ProspectiveStandaloneSnapshot,"prospective_standalone_snapshot",dict(schema_version="3",identity_algorithm_version="1",**kwargs,effective_at=s.effective_at+timedelta(minutes=1),supersedes_snapshot_id=s.prospective_standalone_snapshot_id,correction_reason="metadata correction"),("prospective_standalone_snapshot_id","provenance","input_digest"))
        self.assertEqual(select_authoritative_prospective_snapshots((s,child),s.effective_at),(s,));self.assertEqual(select_authoritative_prospective_snapshots((s,child),child.effective_at),(child,))

    def test_15_market_registry_and_snapshot_authority(self):
        g=self.g
        with self.assertRaises(ContractError):create_standalone_market_probability_derivation(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=g["snapshot"].effective_at,snapshot=g["snapshot"],snapshots=(g["snapshot"],),attempts=g["attempts"],observation=g["observation"],market_observations=(),series=g["series"],effective_at=g["prospective_derivation"].effective_at,provenance=g["provenance"])

    def test_16_measurement_exact_opportunity_schedule(self):
        g=self.g;m=g["prospective_measurement"];self.assertEqual((m.opportunity_id,m.schedule_observation_id),(g["opportunity"].research_capture_opportunity_id,g["opportunity"].schedule_observation_id))
        with self.assertRaises(ContractError):create_probability_source_measurement_v3(protocol=g["prospective"],activation=g["activation"],opportunity=g["prospective_failure"],eligibility_context=g["prospective_failure_context"],eligibility_result=g["prospective_failure_eligibility"],schedule_history=g["prospective_failure_history"],snapshots=(g["snapshot"],),derivations=(g["prospective_derivation"],),outcome=g["legacy"]["outcome"],outcome_histories=(g["legacy"]["outcome_history"],),effective_at=m.effective_at,provenance=g["provenance"])

    def test_17_measurement_wrong_kind_multiple_outcome(self):
        g=self.g;common=dict(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],snapshots=(g["snapshot"],),outcome=g["legacy"]["outcome"],outcome_histories=(g["legacy"]["outcome_history"],),effective_at=g["prospective_measurement"].effective_at,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_measurement_v3(derivations=(g["retrospective_derivation"],),**common)
        with self.assertRaises(ContractError):create_probability_source_measurement_v3(derivations=(),**common)

    def test_18_coverage_exact_measurement_mapping(self):
        g=self.g;self.assertEqual(g["prospective_coverage"].measured_opportunity_ids,(g["opportunity"].research_capture_opportunity_id,))
        with self.assertRaises(ContractError):create_probability_source_coverage_v3(**prospective_coverage_args(g,opportunities=(g["prospective_failure"],)))

    def test_19_coverage_duplicate_measurement_rejected(self):
        g=self.g
        with self.assertRaises(ContractError):create_probability_source_coverage_v3(**prospective_coverage_args(g,measurements=(g["prospective_measurement"],g["prospective_measurement"])))

    def test_20_bootstrap_empty_singleton_zero_variation(self):
        g=self.g;b=g["retro_report"].analysis_boundary;empty=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=());self.assertIsNone(empty.point_estimate)
        single=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=(g["retro_measurement"],));self.assertEqual(single.lower,single.upper)
        a=measurement_variant(g["retro_measurement"],Decimal("0.7"),1);c=measurement_variant(g["retro_measurement"],Decimal("0.7"),2);zero=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=(a,c));self.assertEqual(zero.lower,zero.upper)

    def test_21_bootstrap_deterministic_order_invariant_non_minmax(self):
        g=self.g;b=g["retro_report"].analysis_boundary;items=tuple(measurement_variant(g["retro_measurement"],p,i) for i,p in enumerate((Decimal("0.1"),Decimal("0.35"),Decimal("0.6"),Decimal("0.9")),1));one=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=items);two=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=reversed(items));self.assertEqual(one,two);self.assertNotEqual((one.lower,one.upper),(min(x.brier_score for x in items),max(x.brier_score for x in items)))
        prior=getcontext().prec
        try:
            getcontext().prec=9;ambient=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=items)
        finally:getcontext().prec=prior
        self.assertEqual(one,ambient)

    def test_22_bootstrap_seed_scope_sensitivity(self):
        g=self.g;b=g["retro_report"].analysis_boundary;items=(g["retro_measurement"],);c=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=items);w=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.TIME_BOUNDED,analysis_boundary=b,analysis_start=b-timedelta(days=30),measurements=items);self.assertNotEqual(c.seed_digest,w.seed_digest)

    def test_23_open_left_bounded_coverage(self):
        g=self.g;scheduled=g["legacy"]["outcome"].scheduled_start;end=g["prospective_coverage"].analysis_boundary
        open_left=create_probability_source_coverage_v3(**prospective_coverage_args(g,analysis_boundary=end,coverage_scope="time-bounded",window_start=scheduled))
        self.assertNotIn(g["opportunity"].research_capture_opportunity_id,open_left.coverage_universe_ids)
        closed_right=create_probability_source_coverage_v3(**prospective_coverage_args(g,analysis_boundary=scheduled,coverage_scope="time-bounded",window_start=scheduled-timedelta(minutes=1),opportunities=(g["opportunity"],),eligibility_contexts=(g["prospective_context"],),eligibility_results=(g["prospective_eligibility"],),schedule_histories=(g["legacy"]["outcome_history"],)))
        self.assertIn(g["opportunity"].research_capture_opportunity_id,closed_right.coverage_universe_ids)
        self.assertNotEqual(g["prospective_coverage"].coverage_universe_ids,g["prospective_bounded_coverage"].coverage_universe_ids)

    def test_24_bounded_performance_rejects_cumulative_coverage(self):
        g=self.g
        with self.assertRaises(ContractError):create_probability_source_performance_v3(protocol=g["prospective"],coverage=g["prospective_coverage"],measurements=(g["prospective_measurement"],),scope=PerformanceScope.TIME_BOUNDED,analysis_boundary=g["prospective_coverage"].analysis_boundary,analysis_start=g["prospective_coverage"].analysis_boundary-timedelta(days=30),provenance=g["provenance"])

    def test_25_report_requires_matching_coverage_registry(self):
        g=self.g
        with self.assertRaises(ContractError):create_probability_source_performance_report(protocol=g["prospective"],cumulative=g["prospective_performance"],time_bounded=(),performances=(g["prospective_performance"],),coverages=(),analysis_boundary=g["prospective_report"].analysis_boundary,report_boundary=g["prospective_report"].report_boundary,descriptive_findings=(),limitations=(),provenance=g["provenance"])

    def test_26_graph_retrospective_only(self):self.assertEqual(len(validate_standalone_research_graph(**graph_args(self.g,"retro"))),1)
    def test_27_graph_prospective_pre_report(self):self.assertEqual(validate_standalone_research_graph(**graph_args(self.g,"pros",False)),())
    def test_28_graph_prospective_only(self):self.assertEqual(len(validate_standalone_research_graph(**graph_args(self.g,"pros"))),1)
    def test_29_graph_combined(self):self.assertEqual(len(validate_standalone_research_graph(**graph_args(self.g,"both"))),2)

    def test_30_graph_missing_upstream_and_duplicate_report_rejected(self):
        args=graph_args(self.g);args["candles"]=()
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_31_graph_rejects_superseded_manifest_derivation(self):
        g=self.g;m=g["manifest"];kwargs={name:getattr(m,name) for name in m.__dataclass_fields__ if name not in ("historical_candle_query_manifest_id","input_digest","schema_version","identity_algorithm_version","effective_at","supersedes_manifest_id","correction_reason")}
        child=HistoricalCandleQueryManifest.create(**kwargs,effective_at=m.effective_at+timedelta(seconds=1),supersedes_manifest_id=m.historical_candle_query_manifest_id,correction_reason="synthetic correction")
        args=graph_args(g,"retro");args["manifests"]=(m,child);args["analysis_boundary"]=child.effective_at+timedelta(hours=2)
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_32_graph_rejects_superseded_snapshot_derivation(self):
        g=self.g;s=g["snapshot"];kwargs={name:getattr(s,name) for name in s.__dataclass_fields__ if name not in ("prospective_standalone_snapshot_id","input_digest","schema_version","identity_algorithm_version","effective_at","supersedes_snapshot_id","correction_reason")}
        child=fsr._identity(ProspectiveStandaloneSnapshot,"prospective_standalone_snapshot",dict(schema_version="3",identity_algorithm_version="1",**kwargs,effective_at=s.effective_at+timedelta(minutes=1),supersedes_snapshot_id=s.prospective_standalone_snapshot_id,correction_reason="metadata correction"),("prospective_standalone_snapshot_id","provenance","input_digest"))
        args=graph_args(g,"pros");args["snapshots"]=(s,child);args["analysis_boundary"]=g["prospective_report"].analysis_boundary
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_33_incomplete_manifest_cannot_authorize_derivation(self):
        g=self.g;m=g["manifest"];values={name:getattr(m,name) for name in m.__dataclass_fields__ if name not in ("historical_candle_query_manifest_id","input_digest","schema_version","identity_algorithm_version","validation_status")}
        incomplete=HistoricalCandleQueryManifest.create(**values,validation_status=ManifestValidationStatus.INCOMPLETE)
        with self.assertRaises(ContractError):create_historical_candle_probability_derivation(protocol=g["retrospective"],activation=g["activation"],opportunity=g["retro_opportunity"],eligibility_context=g["retro_context"],eligibility_result=g["retro_eligibility"],schedule_history=g["retro_history"],analysis_boundary=incomplete.effective_at,manifest=incomplete,manifests=(incomplete,),candles=(g["candle"],),home_participant_id=g["candle"].home_participant_id,complement_outcome_id="synthetic-team:retro-away",effective_at=g["retrospective_derivation"].effective_at,provenance=g["provenance"])

    def test_34_graph_rejects_internally_identified_shifted_derivation(self):
        g=self.g;d=g["retrospective_derivation"];values={name:getattr(d,name) for name in d.__dataclass_fields__ if name not in ("historical_candle_probability_derivation_id","input_digest","provenance","target_at")}
        shifted=fsr._identity(HistoricalCandleProbabilityDerivation,"historical_candle_probability_derivation",dict(**values,target_at=d.target_at+timedelta(minutes=1),provenance=d.provenance),("historical_candle_probability_derivation_id","provenance","input_digest"))
        args=graph_args(g,"retro");args["historical_derivations"]=(shifted,);args["measurements"]=();args["coverages"]=();args["performances"]=();args["reports"]=()
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_35_bootstrap_seed_boundary_and_membership_sensitivity(self):
        g=self.g;b=g["retro_report"].analysis_boundary;m=g["retro_measurement"];variant=measurement_variant(m,Decimal("0.8"),9)
        first=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=(m,))
        later=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b+timedelta(seconds=1),analysis_start=None,measurements=(m,))
        members=create_one_sample_uncertainty_v3(protocol=g["retrospective"],scope=PerformanceScope.CUMULATIVE,analysis_boundary=b,analysis_start=None,measurements=(m,variant))
        self.assertNotEqual(first.seed_digest,later.seed_digest);self.assertNotEqual(first.seed_digest,members.seed_digest)
        args=graph_args(self.g);args["reports"]=(self.g["retro_report"],self.g["retro_report"])
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_36_coverage_relabeling_rejected_by_graph_replay(self):
        g=self.g;c=g["prospective_coverage"];r=c.reconciliation
        relabeled=replace(r,missed_window=(),acquisition_failed=r.missed_window)
        values={name:getattr(c,name) for name in c.__dataclass_fields__ if name not in ("probability_source_coverage_v3_id","input_digest","provenance","reconciliation")}
        forged=fsr._identity(ProbabilitySourceCoverageV3,"probability_source_coverage_v3",dict(**values,reconciliation=relabeled,provenance=c.provenance),("probability_source_coverage_v3_id","provenance","input_digest"))
        args=graph_args(g,"pros");args["coverages"]=(forged,g["prospective_bounded_coverage"]);args["performances"]=();args["reports"]=()
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_37_schedule_universe_omission_and_unexpected_opportunity_rejected(self):
        g=self.g
        with self.assertRaises(ContractError):create_probability_source_coverage_v3(**retro_coverage_args(g,opportunities=(g["retro_opportunity"],)))
        foreign=ResearchCaptureOpportunity.create(g["retrospective"].standalone_probability_source_protocol_id,"invented-schedule","winner")
        with self.assertRaises(ContractError):create_probability_source_coverage_v3(**retro_coverage_args(g,opportunities=(g["retro_opportunity"],g["retro_failure"],foreign)))

    def test_38_cancelled_event_is_visible_and_false_eligibility_rejected(self):
        g=self.g;s=g["retro_failure_schedule"]
        cancelled=replace(s,observation_id="synthetic-cancelled",provider_status=fsr.OutcomeStatus.CANCELLED,provider_status_detail="Cancelled",collected_at=s.collected_at+timedelta(hours=1),raw_evidence_sha256="7"*64,canonical_evidence_sha256="8"*64)
        history=fsr.OutcomeHistory(s.canonical_event_id,s.authoritative_provider_id,(s,cancelled))
        context,result=create_standalone_eligibility_authority(protocol=g["retrospective"],opportunity=g["retro_failure"],outcome_history=history,classification=g["retro_failure_classification"],classifications=(g["retro_failure_classification"],),analysis_boundary=cancelled.collected_at,provenance=g["provenance"])
        self.assertIs(result.disposition,PopulationEligibilityDisposition.EXCLUDED);self.assertIn("cancelled",result.reason_codes)
        false=PopulationEligibilityResult.create(research_capture_opportunity_id=result.research_capture_opportunity_id,research_event_eligibility_context_id=context.research_event_eligibility_context_id,protocol_id=result.protocol_id,research_population_id=result.research_population_id,analysis_boundary=result.analysis_boundary,disposition=PopulationEligibilityDisposition.ELIGIBLE,governing_rule_specification_ids=result.governing_rule_specification_ids,reason_codes=(),validation_status=PopulationEligibilityValidationStatus.VALID,validation_reasons=(),provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_coverage_v3(**retro_coverage_args(g,schedule_histories=(g["retro_history"],history),eligibility_contexts=(g["retro_context"],context),eligibility_results=(g["retro_eligibility"],false)))

    def test_39_protocol_scientific_rules_fail_closed(self):
        g=self.g;base=g["retro_rules"]
        changes=(dict(scoring_rule=replace(base["scoring_rule"],rule_id="unsupported")),dict(calibration_rule=replace(base["calibration_rule"],rule_id="unsupported")),dict(calibration_rule=replace(base["calibration_rule"],parameters=(("boundaries","0,0.5,0.4,1"),("empty_bins","omit"),("endpoint_semantics","left-closed-right-open-final-closed"),("weighting","sample-share-absolute-gap")))),dict(uncertainty_rule=replace(base["uncertainty_rule"],rule_id="unsupported")),dict(uncertainty_rule=replace(base["uncertainty_rule"],parameters=(("confidence_level","0.90"),("resamples","0")))))
        for change in changes:
            kwargs=dict(base);kwargs.update(change)
            with self.subTest(change=change),self.assertRaises(ContractError):StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.RETROSPECTIVE,design=g["retrospective"].design,source=g["legacy"]["benchmark"],provenance=g["provenance"],**kwargs)

    def test_40_report_rejects_correct_count_wrong_window(self):
        g=self.g;start=g["retro_report"].analysis_boundary-timedelta(days=18)
        coverage=create_probability_source_coverage_v3(**retro_coverage_args(g,coverage_scope="time-bounded",window_start=start))
        performance=create_probability_source_performance_v3(protocol=g["retrospective"],coverage=coverage,measurements=(g["retro_measurement"],),scope=PerformanceScope.TIME_BOUNDED,analysis_boundary=g["retro_report"].analysis_boundary,analysis_start=start,provenance=g["provenance"])
        with self.assertRaises(ContractError):create_probability_source_performance_report(protocol=g["retrospective"],cumulative=g["retro_performance"],time_bounded=(performance,),performances=(g["retro_performance"],performance),coverages=(g["retro_coverage"],coverage),analysis_boundary=g["retro_report"].analysis_boundary,report_boundary=g["retro_report"].report_boundary,descriptive_findings=(),limitations=(),provenance=g["provenance"])

    def test_41_candle_must_match_exact_retrieval_page_archive(self):
        g=self.g;c=g["candle"];kwargs={name:getattr(c,name) for name in c.__dataclass_fields__ if name not in ("historical_market_candle_observation_id","input_digest","schema_version","identity_algorithm_version","raw_archive_reference")}
        changed=HistoricalMarketCandleObservation.create(**kwargs,raw_archive_reference="synthetic-archive:elsewhere")
        page=replace(g["page"],returned_candle_evidence_ids=(changed.historical_market_candle_observation_id,))
        m=g["manifest"];mkwargs={name:getattr(m,name) for name in m.__dataclass_fields__ if name not in ("historical_candle_query_manifest_id","input_digest","schema_version","identity_algorithm_version","pages","returned_candle_evidence_ids")}
        manifest=HistoricalCandleQueryManifest.create(**mkwargs,pages=(page,),returned_candle_evidence_ids=(changed.historical_market_candle_observation_id,))
        changed=replace(changed,manifest_id=manifest.historical_candle_query_manifest_id)
        with self.assertRaises(ContractError):reconcile_manifest_candles(manifest,(changed,))

    def test_42_successor_registry_explicit_legacy_delegation(self):
        g=self.g
        for value in (g["retro_opportunity"],g["retro_context"],g["retro_eligibility"],g["observation"],g["series"],g["prospective_derivation"],g["retro_schedule"],g["retro_history"],g["legacy"]["benchmark"],g["provenance"]):
            with self.subTest(type=type(value).__name__):self.assertEqual(deserialize_v3(value.to_json()),value)
        payload=g["retro_opportunity"].to_json().replace('"schema_version":"1"','"schema_version":"99"')
        with self.assertRaises(ContractError):deserialize_v3(payload)

    def test_43_input_order_nonmaterial_for_coverage(self):
        g=self.g
        reversed_coverage=create_probability_source_coverage_v3(**retro_coverage_args(g,opportunities=reversed((g["retro_opportunity"],g["retro_failure"])),eligibility_contexts=reversed((g["retro_context"],g["retro_failure_context"])),eligibility_results=reversed((g["retro_eligibility"],g["retro_failure_eligibility"])),schedule_histories=reversed((g["retro_history"],g["retro_failure_history"]))))
        self.assertEqual(reversed_coverage,g["retro_coverage"])

    def test_44_archive_digest_duplicate_membership_and_missing_candle_rejected(self):
        g=self.g;c=g["candle"]
        kwargs={name:getattr(c,name) for name in c.__dataclass_fields__ if name not in ("historical_market_candle_observation_id","input_digest","schema_version","identity_algorithm_version","raw_archive_sha256")}
        changed=HistoricalMarketCandleObservation.create(**kwargs,raw_archive_sha256="9"*64)
        page=replace(g["page"],returned_candle_evidence_ids=(changed.historical_market_candle_observation_id,))
        m=g["manifest"];mkwargs={name:getattr(m,name) for name in m.__dataclass_fields__ if name not in ("historical_candle_query_manifest_id","input_digest","schema_version","identity_algorithm_version","pages","returned_candle_evidence_ids")}
        manifest=HistoricalCandleQueryManifest.create(**mkwargs,pages=(page,),returned_candle_evidence_ids=(changed.historical_market_candle_observation_id,))
        with self.assertRaises(ContractError):reconcile_manifest_candles(manifest,(replace(changed,manifest_id=manifest.historical_candle_query_manifest_id),))
        with self.assertRaises(ContractError):reconcile_manifest_candles(g["manifest"],())
        first=replace(g["page"],next_cursor="next",terminal=False)
        second=HistoricalCandleRetrievalPage("next",1,None,True,"second","3"*64,g["page"].retrieved_at+timedelta(seconds=1),g["page"].returned_candle_evidence_ids,ManifestValidationStatus.COMPLETE)
        with self.assertRaises(ContractError):HistoricalCandleQueryManifest.create(**mkwargs,pages=(first,second),returned_candle_evidence_ids=g["manifest"].returned_candle_evidence_ids)

    def test_45_cross_activation_reschedule_preserves_both_opportunities(self):
        g=self.g;activation=g["activation"].activation_at
        original=replace(g["retro_schedule"],observation_id="cross-schedule:original",canonical_event_id="cross-event",provider_event_id="cross-provider-event",scheduled_start=activation-timedelta(days=1),collected_at=activation-timedelta(days=2),raw_evidence_sha256="1"*64,canonical_evidence_sha256="2"*64)
        moved=replace(original,observation_id="cross-schedule:rescheduled",scheduled_start=activation+timedelta(days=1),collected_at=activation+timedelta(hours=1),raw_evidence_sha256="3"*64,canonical_evidence_sha256="4"*64)
        status_only=replace(moved,observation_id="cross-status-only",provider_status=fsr.OutcomeStatus.POSTPONED,provider_status_detail="Postponed",collected_at=moved.collected_at+timedelta(hours=1),raw_evidence_sha256="5"*64,canonical_evidence_sha256="6"*64)
        history=fsr.OutcomeHistory("cross-event","mlb-stats-api",(original,moved,status_only));boundary=status_only.collected_at
        retro=expected_schedule_opportunities(protocol=g["retrospective"],activation=g["activation"],schedule_histories=(history,),analysis_boundary=boundary)
        pros=expected_schedule_opportunities(protocol=g["prospective"],activation=g["activation"],schedule_histories=(history,),analysis_boundary=boundary)
        self.assertEqual(tuple(x.schedule_observation_id for x in retro),(original.observation_id,));self.assertEqual(tuple(x.schedule_observation_id for x in pros),(moved.observation_id,))
        self.assertEqual(expected_schedule_opportunities(protocol=g["retrospective"],activation=g["activation"],schedule_histories=(history,),analysis_boundary=original.collected_at),retro)
        self.assertEqual(expected_schedule_opportunities(protocol=g["prospective"],activation=g["activation"],schedule_histories=reversed((history,)),analysis_boundary=boundary),pros)
        classification=classification_variant(g["retro_classification"],provider_event_id=original.provider_event_id,canonical_event_id=original.canonical_event_id,participant_ids=tuple(sorted((original.away_participant_id,original.home_participant_id))),home_participant_id=original.home_participant_id,away_participant_id=original.away_participant_id,collected_at=original.collected_at,effective_at=original.collected_at)
        rc,rr=create_standalone_eligibility_authority(protocol=g["retrospective"],opportunity=retro[0],outcome_history=history,classification=classification,classifications=(classification,),analysis_boundary=boundary,provenance=g["provenance"])
        pc,pr=create_standalone_eligibility_authority(protocol=g["prospective"],opportunity=pros[0],outcome_history=history,classification=classification,classifications=(classification,),analysis_boundary=boundary,provenance=g["provenance"])
        self.assertIs(rr.disposition,PopulationEligibilityDisposition.EXCLUDED);self.assertIn("rescheduled",rr.reason_codes);self.assertIs(pr.disposition,PopulationEligibilityDisposition.ELIGIBLE)
        retro_coverage=create_probability_source_coverage_v3(protocol=g["retrospective"],analysis_boundary=boundary,activation=g["activation"],opportunities=retro,eligibility_contexts=(rc,),eligibility_results=(rr,),schedule_histories=(history,),classifications=(classification,),provenance=g["provenance"])
        pros_coverage=create_probability_source_coverage_v3(protocol=g["prospective"],analysis_boundary=boundary,activation=g["activation"],opportunities=pros,eligibility_contexts=(pc,),eligibility_results=(pr,),schedule_histories=(history,),classifications=(classification,),provenance=g["provenance"])
        self.assertEqual(retro_coverage.reconciliation.protocol_ineligible,(retro[0].research_capture_opportunity_id,));self.assertEqual(pros_coverage.reconciliation.capture_not_yet_due,(pros[0].research_capture_opportunity_id,))

    def test_46_classification_drives_retrospective_and_prospective_eligibility(self):
        g=self.g
        cases=((dict(season="2025"),"wrong-season"),(dict(event_phase=EventPhase.POSTSEASON),"postseason"),(dict(doubleheader_id="dh-1",game_number=1,ordinary_game=False),"doubleheader"),(dict(mapping_validation_status=EventClassificationValidationStatus.AMBIGUOUS,validation_reasons=("ambiguous-home-away",)),"ambiguous-mapping"))
        for change,reason in cases:
            classification=classification_variant(g["retro_classification"],**change)
            _,result=create_standalone_eligibility_authority(protocol=g["retrospective"],opportunity=g["retro_opportunity"],outcome_history=g["retro_history"],classification=classification,classifications=(classification,),analysis_boundary=g["retro_context"].analysis_boundary,provenance=g["provenance"])
            with self.subTest(reason=reason):self.assertIs(result.disposition,PopulationEligibilityDisposition.EXCLUDED);self.assertIn(reason,result.reason_codes)
        doubleheader=classification_variant(g["prospective_classification"],doubleheader_id="dh-2",game_number=2,ordinary_game=False)
        _,result=create_standalone_eligibility_authority(protocol=g["prospective"],opportunity=g["opportunity"],outcome_history=g["legacy"]["outcome_history"],classification=doubleheader,classifications=(doubleheader,),analysis_boundary=g["prospective_context"].analysis_boundary,provenance=g["provenance"])
        self.assertIs(result.disposition,PopulationEligibilityDisposition.ELIGIBLE)

    def test_47_classification_correction_is_boundary_aware_and_graph_required(self):
        g=self.g;root=g["retro_classification"];later=root.effective_at+timedelta(days=20)
        child=classification_variant(root,event_phase=EventPhase.POSTSEASON,effective_at=later,supersedes_classification_id=root.standalone_event_classification_evidence_id,correction_reason="synthetic phase correction")
        self.assertEqual(select_authoritative_event_classifications((child,root),root.effective_at),(root,));self.assertEqual(select_authoritative_event_classifications((root,child),later),(child,))
        args=graph_args(g,"retro");args["classifications"]=()
        with self.assertRaises(ContractError):validate_standalone_research_graph(**args)

    def test_48_earlier_unsuccessful_attempts_do_not_override_later_success(self):
        g=self.g;variants=((CapturedInvalid("raw-invalid","7"*64,(AttemptValidationFailure.MALFORMED,)),True),(AcquisitionFailed(AttemptFailureCategory.NETWORK,"call-failed"),True),(Missed(),False))
        for result,called in variants:
            attempts,snapshot,derivation,measurement,coverage=prospective_success_variant(g,result,called)
            with self.subTest(result=type(result).__name__):self.assertIn(g["opportunity"].research_capture_opportunity_id,coverage.reconciliation.measured)
            reversed_coverage=create_probability_source_coverage_v3(**prospective_coverage_args(g,attempts=tuple(reversed(attempts+g["prospective_failure_attempts"])),snapshots=(snapshot,g["prospective_failure_snapshot"]),market_derivations=(derivation,),measurements=(measurement,)))
            self.assertEqual(reversed_coverage,coverage)
        attempts,snapshot,derivation,_,_=prospective_success_variant(g,AcquisitionFailed(AttemptFailureCategory.NETWORK,"unresolved-case"),True)
        unresolved=create_probability_source_coverage_v3(**prospective_coverage_args(g,attempts=attempts+g["prospective_failure_attempts"],snapshots=(snapshot,g["prospective_failure_snapshot"]),market_derivations=(derivation,),measurements=()))
        self.assertIn(g["opportunity"].research_capture_opportunity_id,unresolved.reconciliation.outcome_unresolved)

    def test_49_no_success_precedence_is_explicit(self):
        g=self.g;self.assertIn(g["prospective_failure"].research_capture_opportunity_id,g["prospective_coverage"].reconciliation.missed_window)
        def classify(result,called,expected):
            target=g["prospective_failure_target"];common=g["failure_common"]
            attempts=tuple(ProspectiveCaptureAttempt.create(slot=i,invocation_at=target+timedelta(minutes=i),provider_call_occurred=called,result=result(i),effective_at=target+timedelta(minutes=i),diagnostics=(),**common) for i in range(5))
            snapshot=reconcile_prospective_snapshot(protocol=g["prospective"],opportunity=g["prospective_failure"],activation=g["activation"],eligibility_context=g["prospective_failure_context"],eligibility_result=g["prospective_failure_eligibility"],schedule_history=g["prospective_failure_history"],analysis_boundary=g["prospective_coverage"].analysis_boundary,attempts=attempts,window_closed_at=target+timedelta(minutes=5),provenance=g["provenance"])
            coverage=create_probability_source_coverage_v3(**prospective_coverage_args(g,attempts=tuple(g["attempts"])+attempts,snapshots=(g["snapshot"],snapshot)))
            self.assertIn(g["prospective_failure"].research_capture_opportunity_id,getattr(coverage.reconciliation,expected))
        classify(lambda _:AcquisitionFailed(AttemptFailureCategory.TIMEOUT,"failed-call"),True,"acquisition_failed")
        classify(lambda _:CapturedInvalid("invalid-raw","8"*64,(AttemptValidationFailure.MALFORMED,)),True,"captured_invalid")

    def test_50_future_and_ambiguous_derivations_fail_closed_without_order_dependence(self):
        g=self.g;d=g["retrospective_derivation"];values={name:getattr(d,name) for name in d.__dataclass_fields__ if name not in ("historical_candle_probability_derivation_id","input_digest","provenance","effective_at")}
        future=fsr._identity(HistoricalCandleProbabilityDerivation,"historical_candle_probability_derivation",dict(**values,effective_at=g["retro_coverage"].analysis_boundary+timedelta(days=1),provenance=d.provenance),("historical_candle_probability_derivation_id","provenance","input_digest"))
        self.assertEqual(create_probability_source_coverage_v3(**retro_coverage_args(g,historical_derivations=(future,d))),g["retro_coverage"])
        second=create_standalone_market_probability_derivation(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=g["snapshot"].effective_at,snapshot=g["snapshot"],snapshots=(g["snapshot"],g["prospective_failure_snapshot"]),attempts=g["attempts"],observation=g["observation"],market_observations=(g["observation"],),series=g["series"],effective_at=g["prospective_derivation"].effective_at,provenance=g["provenance"],limitations=("conflicting compatible derivation",))
        for order in ((g["prospective_derivation"],second),(second,g["prospective_derivation"])):
            with self.subTest(order=order),self.assertRaises(ContractError):create_probability_source_coverage_v3(**prospective_coverage_args(g,market_derivations=order))

    def test_51_classification_v3_round_trip(self):
        self.assertEqual(deserialize_v3(self.g["retro_classification"].to_json()),self.g["retro_classification"])


if __name__=="__main__":unittest.main()
