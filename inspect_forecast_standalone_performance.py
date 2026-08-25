"""Offline factual PR16B inspection over compact synthetic Evidence."""
from __future__ import annotations

import json
from datetime import timedelta, timezone
from decimal import Decimal
from pathlib import Path

from event_contracts import Provenance
from forecast_comparative_research import ResearchCaptureOpportunity, SnapshotValidationStatus
from forecast_research_contracts import (
    ProbabilitySourceReference, ProtocolClaimSet, ResearchProtocol, RuleParameter,
    RulePurpose, VersionedRuleSpecification,
)
from forecast_standalone_performance import *
from inspect_forecast_comparative_research import load_fixture as load_pr14_fixture
from market_contracts import (
    ComponentEvidence, MarketObservation, MarketSide, MarketStatus, OrderBookLevel,
    PriceEvidenceKind, ProviderMarketSeries, QuoteState, SideSemantic,
)


DEFAULT_FIXTURE = Path(__file__).parent / "tests/fixtures/forecast_standalone_performance_cases.json"
PR14_FIXTURE = Path(__file__).parent / "tests/fixtures/forecast_comparative_research_cases.json"


def _rules(case):
    representation = VersionedRuleSpecification.create(RulePurpose.PROBABILITY_REPRESENTATION, "positive-depth-two-sided-quote", "1")
    transformation = VersionedRuleSpecification.create(RulePurpose.PROBABILITY_TRANSFORMATION, "bid-offer-midpoint-complement", "1")
    primary = VersionedRuleSpecification.create(RulePurpose.STANDALONE_PRIMARY_MEASURE, "mean-brier-score", "1")
    statistical = VersionedRuleSpecification.create(RulePurpose.STANDALONE_STATISTICAL_METHOD, "one-sample-brier-bootstrap", "1", (
        RuleParameter("confidence_level", Decimal(case["standalone"]["confidence_level"])),
        RuleParameter("resamples", case["standalone"]["resamples"]),
    ))
    return representation, transformation, primary, statistical


def build_graph(path: Path = DEFAULT_FIXTURE):
    case = json.loads(path.read_text())
    old = load_pr14_fixture(PR14_FIXTURE); original = old["protocols"][0]; provenance = old["provenance"]
    representation, transformation, primary, statistical = _rules(case)
    benchmark = ProbabilitySourceReference.create(provider_id="kalshi", model_or_product_id="mlb-game-winner-market",
        model_or_product_version="2", proposition_type="winner", probability_representation_rule=representation,
        transformation_rule=transformation, availability_rule=original.market_benchmark.availability_rule)
    kwargs = {name: getattr(original, name) for name in original.__dataclass_fields__
              if name not in ("research_protocol_id", "input_digest", "schema_version", "identity_algorithm_version", "market_benchmark", "protocol_version")}
    kwargs["surveillance_window_rules"] = (VersionedRuleSpecification.create(
        RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "2",
        (RuleParameter("days", case["standalone"]["window_days"]),)),)
    kwargs["drift_classification_rule"] = VersionedRuleSpecification.create(
        RulePurpose.DRIFT_CLASSIFICATION,"brier-deterioration","2",
        (RuleParameter("threshold",Decimal("0.05")),))
    base = ResearchProtocol.create(protocol_version="2", market_benchmark=benchmark, **kwargs)
    protocol = ResearchProtocolV2.create(base_protocol=base, standalone_primary_measure_rule=primary,
                                         standalone_statistical_method_rule=statistical)
    old_snapshot = next(item for item in old["snapshots"] if item.canonical_event_id == "canonical-event:a" and item.supersedes_snapshot_id is None)
    old_opportunity = next(item for item in old["opportunities"]
                           if item.research_capture_opportunity_id == old_snapshot.research_capture_opportunity_id)
    base_opportunity = ResearchCaptureOpportunity.create(base.research_protocol_id,old_opportunity.schedule_observation_id,"winner")
    opportunity = ResearchCaptureOpportunity.create(protocol.research_protocol_id, old_opportunity.schedule_observation_id, "winner")
    at = old_snapshot.target_capture_at
    challenger = base.alternative_sources[0]
    challenger_two=base.alternative_sources[1]
    challenger_observation=next(item for item in old["forecast_observations"]
                                if item.observation_id.endswith(":challenger") and item.distribution.canonical_event_id==old_snapshot.canonical_event_id)
    challenger_two_observation=next(item for item in old["forecast_observations"]
        if item.observation_id.endswith(":other") and item.distribution.canonical_event_id==old_snapshot.canonical_event_id)
    source_capture = SourceCaptureV2(benchmark.probability_source_reference_id, SourceCaptureDispositionV2.CAPTURED_VALID,
                                     SourceEvidenceReference(SourceEvidenceKind.MARKET_OBSERVATION, "market-observation:synthetic-a"), at)
    challenger_capture = SourceCaptureV2(challenger.probability_source_reference_id, SourceCaptureDispositionV2.CAPTURED_VALID,
        SourceEvidenceReference(SourceEvidenceKind.FORECAST_OBSERVATION, challenger_observation.observation_id), at)
    challenger_two_capture=SourceCaptureV2(challenger_two.probability_source_reference_id,SourceCaptureDispositionV2.CAPTURED_VALID,
        SourceEvidenceReference(SourceEvidenceKind.FORECAST_OBSERVATION,challenger_two_observation.observation_id),at)
    snapshot_seed = ResearchSnapshotV2.create(research_capture_opportunity_id=opportunity.research_capture_opportunity_id,
        protocol_id=protocol.research_protocol_id, effective_at=old_snapshot.effective_at,
        supersedes_snapshot_id=None, correction_reason=None, canonical_event_id=old_snapshot.canonical_event_id,
        proposition_type="winner", canonical_proposition_outcome_id=old_snapshot.canonical_proposition_outcome_id,
        scheduled_start=old_snapshot.scheduled_start, target_capture_at=at, capture_started_at=at,
        capture_completed_at=old_snapshot.capture_completed_at, source_captures=(source_capture,challenger_capture,challenger_two_capture),
        pairwise_synchronization=(), dimension_classifications=old_snapshot.dimension_classifications,
        validation_status=SnapshotValidationStatus.VALID, validation_reasons=(), limitations=(), provenance=provenance)
    event_provenance = Provenance("kalshi", "synthetic-a", snapshot_seed.canonical_event_id, at, collector_version="fixture-1")
    proposition_id = f"winner:{snapshot_seed.canonical_event_id}:{snapshot_seed.canonical_proposition_outcome_id}"
    other = "team:a:away"
    series = ProviderMarketSeries("market-series:kalshi:synthetic-a", "kalshi", "synthetic-a", "SYNTH-A", proposition_id,
        SideSemantic(MarketSide.YES, proposition_id, snapshot_seed.canonical_proposition_outcome_id, True, "Home"),
        SideSemantic(MarketSide.NO, proposition_id, other, False, "Away"), "Synthetic winner", None, None, None, None,
        ("Pays $1 to the winner",), event_provenance)
    component = ComponentEvidence("orderbook", "synthetic-a", "/fixture/orderbook", at, "a"*64, "b"*64)
    market = case["market"]
    levels = (
        OrderBookLevel(MarketSide.YES, Decimal(market["yes_offer"]), Decimal(market["yes_offer_quantity"]), 1,
                       PriceEvidenceKind.DIRECT_ASK, MarketSide.YES, Decimal(market["yes_offer"]), None, "/fixture/orderbook", at),
        OrderBookLevel(MarketSide.NO, Decimal(market["no_offer"]), Decimal(market["no_offer_quantity"]), 1,
                       PriceEvidenceKind.DIRECT_ASK, MarketSide.NO, Decimal(market["no_offer"]), None, "/fixture/orderbook", at),
    )
    observation = MarketObservation("market-observation:synthetic-a", series.series_id, "synthetic-a", snapshot_seed.canonical_event_id,
        proposition_id, "capture:synthetic-a", at, MarketStatus.OPEN,
        QuoteState(Decimal("0.54"), Decimal("0.56"), Decimal("0.44"), Decimal("0.46")), levels,
        (component,), event_provenance)
    synchronization=create_pairwise_synchronization_v2(protocol=protocol,snapshot=snapshot_seed,opportunity=opportunity,
        challenger_source_reference_id=challenger.probability_source_reference_id,
        forecast_observations=(challenger_observation,challenger_two_observation),market_observations=(observation,))
    synchronization_two=create_pairwise_synchronization_v2(protocol=protocol,snapshot=snapshot_seed,opportunity=opportunity,
        challenger_source_reference_id=challenger_two.probability_source_reference_id,
        forecast_observations=(challenger_observation,challenger_two_observation),market_observations=(observation,))
    snapshot_values={name:getattr(snapshot_seed,name) for name in snapshot_seed.__dataclass_fields__
        if name not in ("research_snapshot_id","input_digest","schema_version","identity_algorithm_version",
                        "snapshot_algorithm_version","pairwise_synchronization")}
    snapshot=ResearchSnapshotV2.create(**snapshot_values,pairwise_synchronization=(synchronization,synchronization_two))
    outcome_history=next(item for item in old["outcome_histories"] if item.canonical_event_id==snapshot.canonical_event_id)
    schedule_evidence=next(item for item in outcome_history.observations
        if item.observation_id==opportunity.schedule_observation_id)
    derivation = create_market_probability_derivation(protocol=protocol, snapshot=snapshot, observation=observation,
        opportunity=opportunity,schedule_evidence=schedule_evidence,
        forecast_observations=(challenger_observation,challenger_two_observation),market_observations=(observation,),
        series=series, effective_at=snapshot.effective_at, provenance=provenance)
    outcome = next(item for item in old["outcome_observations"] if item.canonical_event_id == snapshot.canonical_event_id)
    challenger_eligibility_decision=decide_evaluation_eligibility(challenger_observation,outcome,outcome_history=outcome_history)
    challenger_evaluation=create_forecast_evaluation(challenger_observation,outcome,challenger_eligibility_decision,
        provider_id=challenger.provider_id,model_id=challenger.model_or_product_id,
        model_version_id=challenger.model_or_product_version)
    challenger_two_eligibility_decision=decide_evaluation_eligibility(challenger_two_observation,outcome,outcome_history=outcome_history)
    challenger_two_evaluation=create_forecast_evaluation(challenger_two_observation,outcome,challenger_two_eligibility_decision,
        provider_id=challenger_two.provider_id,model_id=challenger_two.model_or_product_id,
        model_version_id=challenger_two.model_or_product_version)
    measurement = create_market_backed_source_measurement(protocol=protocol, snapshot=snapshot, derivation=derivation,
        outcome=outcome, effective_at=outcome.collected_at, provenance=provenance)
    challenger_measurement = create_forecast_backed_source_measurement(protocol=protocol,snapshot=snapshot,
        source_reference=challenger,evaluation=challenger_evaluation,outcome=outcome,
        effective_at=outcome.collected_at,provenance=provenance)
    paired_measurement = create_comparative_measurement_v2(protocol=protocol,benchmark=measurement,
        challenger=challenger_measurement,snapshot=snapshot,opportunity=opportunity,
        schedule_evidence=schedule_evidence,forecast_observations=(challenger_observation,challenger_two_observation),market_observations=(observation,),
        effective_at=outcome.collected_at,provenance=provenance)
    challenger_two_measurement=create_forecast_backed_source_measurement(protocol=protocol,snapshot=snapshot,
        source_reference=challenger_two,evaluation=challenger_two_evaluation,outcome=outcome,effective_at=outcome.collected_at,provenance=provenance)
    paired_measurement_two=create_comparative_measurement_v2(protocol=protocol,benchmark=measurement,
        challenger=challenger_two_measurement,snapshot=snapshot,opportunity=opportunity,
        schedule_evidence=schedule_evidence,forecast_observations=(challenger_observation,challenger_two_observation),market_observations=(observation,),
        effective_at=outcome.collected_at,provenance=provenance)
    canonical_event=next(item for item in old["canonical_events"] if item.canonical_event_id==snapshot.canonical_event_id)
    stage_evidence=next(item for item in old["event_stage_evidence"] if item.canonical_event_id==snapshot.canonical_event_id)
    eligibility_context=ResearchEventEligibilityContext.create(opportunity=base_opportunity,protocol=base,
        canonical_event=canonical_event,stage_evidence=stage_evidence,outcome_history=outcome_history,
        analysis_boundary=at)
    eligibility=evaluate_capture_boundary_eligibility(protocol=protocol,opportunity=opportunity,
        context=eligibility_context,provenance=provenance)
    boundary = old["after"]
    coverage = create_probability_source_coverage(protocol=protocol, source_reference_id=benchmark.probability_source_reference_id,
        analysis_boundary=boundary, opportunities=(opportunity,), eligibility_results=(eligibility,),
        eligibility_contexts=(eligibility_context,),snapshots=(snapshot,),market_observations=(observation,),
        market_series=(series,),forecast_observations=(challenger_observation,challenger_two_observation),
        evaluation_eligibility_decisions=(challenger_eligibility_decision,challenger_two_eligibility_decision),
        forecast_evaluations=(challenger_evaluation,challenger_two_evaluation),derivations=(derivation,),
        outcome_histories=(outcome_history,),measurements=(measurement,))
    domain = next(item for item in base.research_domains if not item.partition_selections)
    performance = create_probability_source_performance(protocol=protocol, domain=domain,
        source_reference_id=benchmark.probability_source_reference_id, analysis_boundary=boundary,
        measurements=(measurement,), coverage=coverage, provenance=provenance)
    bounded = create_time_bounded_probability_source_performance(protocol=protocol, domain=domain,
        source_reference_id=benchmark.probability_source_reference_id, analysis_boundary=boundary,
        scheduled_start_by_opportunity={opportunity.research_capture_opportunity_id:snapshot.scheduled_start},
        measurements=(measurement,), coverage=coverage, provenance=provenance)
    claim=EdgeClaim.create(protocol_id=base.research_protocol_id,
        challenger_source_reference_id=challenger.probability_source_reference_id,
        benchmark_source_reference_id=benchmark.probability_source_reference_id,
        research_domain_id=domain.research_domain_id,provenance=provenance)
    claim_two=EdgeClaim.create(protocol_id=base.research_protocol_id,
        challenger_source_reference_id=challenger_two.probability_source_reference_id,
        benchmark_source_reference_id=benchmark.probability_source_reference_id,
        research_domain_id=domain.research_domain_id,provenance=provenance)
    claim_set = ProtocolClaimSet.create(protocol_id=base.research_protocol_id, effective_at=base.effective_at,
                                        edge_claim_ids=(claim.edge_claim_id,claim_two.edge_claim_id), provenance=provenance)
    window_rule=base.surveillance_window_rules[0];window_start=boundary-timedelta(days=dict((p.name,p.value) for p in window_rule.parameters)["days"])
    paired_historical=create_comparative_performance_v2(protocol=protocol,edge_claim=claim,domain=domain,
        analysis_boundary=window_start,measurements=(paired_measurement,),source_measurements=(measurement,challenger_measurement),provenance=provenance)
    paired_performance=create_comparative_performance_v2(protocol=protocol,edge_claim=claim,domain=domain,
        analysis_boundary=boundary,measurements=(paired_measurement,),source_measurements=(measurement,challenger_measurement),provenance=provenance)
    paired_bounded=create_time_bounded_comparative_performance_v2(protocol=protocol,edge_claim=claim,domain=domain,
        analysis_boundary=boundary,measurements=(paired_measurement,),source_measurements=(measurement,challenger_measurement),
        scheduled_start_by_snapshot={snapshot.research_snapshot_id:snapshot.scheduled_start},provenance=provenance)
    paired_drift=create_comparative_drift_analysis_v2(protocol=protocol,historical=paired_historical,current=paired_bounded,measurements=(paired_measurement,),provenance=provenance)
    all_paired=(paired_measurement,paired_measurement_two);all_sources=(measurement,challenger_measurement,challenger_two_measurement)
    paired_historical_two=create_comparative_performance_v2(protocol=protocol,edge_claim=claim_two,domain=domain,
        analysis_boundary=window_start,measurements=all_paired,source_measurements=all_sources,provenance=provenance)
    paired_performance_two=create_comparative_performance_v2(protocol=protocol,edge_claim=claim_two,domain=domain,
        analysis_boundary=boundary,measurements=all_paired,source_measurements=all_sources,provenance=provenance)
    paired_bounded_two=create_time_bounded_comparative_performance_v2(protocol=protocol,edge_claim=claim_two,domain=domain,
        analysis_boundary=boundary,measurements=all_paired,source_measurements=all_sources,
        scheduled_start_by_snapshot={snapshot.research_snapshot_id:snapshot.scheduled_start},provenance=provenance)
    paired_drift_two=create_comparative_drift_analysis_v2(protocol=protocol,historical=paired_historical_two,
        current=paired_bounded_two,measurements=all_paired,provenance=provenance)
    report = ComparativePerformanceReportV2.create(protocol=protocol, protocol_claim_set=claim_set,
        analysis_boundary=boundary, cumulative=performance, time_bounded=bounded,
        claims=(claim,claim_two),paired_cumulative=(paired_historical,paired_performance,paired_historical_two,paired_performance_two),
        paired_time_bounded=(paired_bounded,paired_bounded_two),paired_drift=(paired_drift,paired_drift_two),
        provenance=provenance)
    return locals()


def run(path: Path = DEFAULT_FIXTURE) -> str:
    graph = build_graph(path); coverage = graph["coverage"]; performance = graph["performance"]; bounded = graph["bounded"]
    lines = ["PR16B Standalone Market Benchmark: VALID",
        f"Coverage universe = {len(coverage.universe_opportunity_ids)}",
        f"Universe reconciliation = {len(coverage.capture_not_yet_due_opportunity_ids)} + {len(coverage.protocol_ineligible_opportunity_ids)} + {len(coverage.eligible_denominator_opportunity_ids)}",
        f"Eligible reconciliation = {len(coverage.source_capture_missing_opportunity_ids)} + {len(coverage.source_capture_invalid_opportunity_ids)} + {len(coverage.outside_capture_tolerance_opportunity_ids)} + {len(coverage.derivation_invalid_opportunity_ids)} + {len(coverage.outcome_ineligible_opportunity_ids)} + {len(coverage.measured_opportunity_ids)}",
        f"Coverage rate = {coverage.coverage_rate}", f"Measured sample size = {performance.sample_size}",
        f"Mean Brier = {performance.mean_brier_score}", f"Mean Log Loss = {performance.mean_log_loss}",
        f"WACE = {performance.calibration.weighted_absolute_calibration_error}",
        f"Uncertainty = [{performance.uncertainty.lower_bound}, {performance.uncertainty.upper_bound}]",
        f"Time-bounded sample size = {bounded.sample_size}",
        f"Paired reconciliation = benchmark probability {graph['paired_measurement'].benchmark_probability}, Brier {graph['paired_measurement'].benchmark_brier_score}",
        f"Paired claim findings = {len(graph['report'].claim_findings)} isolated challenger populations",
        f"Report cumulative reference = {graph['report'].cumulative_benchmark_reference.performance_id}",
        "Scientific status = descriptive findings only; PR17 operation and Research Review deferred"]
    return "\n".join(lines)


if __name__ == "__main__": print(run())
