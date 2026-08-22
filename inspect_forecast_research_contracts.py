"""Offline inspector for the compact PR13 research-contract fixture."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from forecast_research_contracts import (
    ApprovedDimensionPartition,
    ApprovedResearchDimension,
    ComparativePerformanceReportReference,
    DimensionPartitionSelection,
    DriftDisposition,
    DriftSurveillance,
    DriftSurveillanceReference,
    EdgeClaim,
    MarketEdge,
    ProbabilitySourceReference,
    ResearchContractProvenance,
    ResearchDomain,
    ResearchPopulationSpecification,
    ResearchProtocol,
    ResearchReview,
    ResearchReviewConclusion,
    ReviewObligationCoverage,
    ReviewObligationKind,
    ReviewObligationReference,
    RuleParameter,
    RulePurpose,
    ScheduledReviewBoundary,
    ScheduledReviewBoundaryReference,
    VersionedRuleSpecification,
    create_market_edge,
    drift_creates_material_event,
    validate_research_contracts,
)


def _at(payload: dict[str, object], name: str) -> datetime:
    return datetime.fromisoformat(str(payload[name]))


def _rule(purpose: RulePurpose, rule_id: str, parameters: tuple[RuleParameter, ...] = ()) -> VersionedRuleSpecification:
    return VersionedRuleSpecification.create(purpose, rule_id, "1", parameters)


def load_fixture(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text())
    provenance = ResearchContractProvenance(
        "fixture:forecast-research-contracts", str(payload["fixture_version"]),
        notes=("synthetic contract-validation fixture",), generated_at=_at(payload, "generated_at"),
    )
    representation = _rule(RulePurpose.PROBABILITY_REPRESENTATION, "direct-probability")
    transformation = _rule(RulePurpose.PROBABILITY_TRANSFORMATION, "identity-probability")
    availability = _rule(RulePurpose.SOURCE_AVAILABILITY, "required-at-snapshot")

    def source(provider: str, product: str) -> ProbabilitySourceReference:
        return ProbabilitySourceReference.create(
            provider_id=provider, model_or_product_id=product, model_or_product_version="1",
            proposition_type="winner", probability_representation_rule=representation,
            transformation_rule=transformation, availability_rule=availability,
        )

    benchmark = source("kalshi", "mlb-game-winner-market")
    challenger_a = source("dratings", "mlb-winner-probability")
    challenger_b = source("fixture-consensus", "mlb-winner-probability")

    population = ResearchPopulationSpecification.create(
        sport="baseball", competition="MLB", proposition_type="winner",
        temporal_scope_rule=_rule(RulePurpose.POPULATION_TEMPORAL_SCOPE, "season-range", (
            RuleParameter("first_season", "2026"), RuleParameter("last_season", "2026"))),
        event_status_rule=_rule(RulePurpose.EVENT_STATUS_ELIGIBILITY, "allowed-event-statuses", (
            RuleParameter("statuses", ("final", "scheduled")),)),
        postseason_treatment_rule=_rule(RulePurpose.POSTSEASON_TREATMENT, "postseason-treatment", (
            RuleParameter("include", False),)),
        postponement_treatment_rule=_rule(RulePurpose.POSTPONEMENT_TREATMENT, "postponement-treatment", (
            RuleParameter("action", "retain-if-rescheduled"),)),
        cancellation_treatment_rule=_rule(RulePurpose.CANCELLATION_TREATMENT, "cancellation-treatment", (
            RuleParameter("action", "exclude"),)),
        rescheduling_treatment_rule=_rule(RulePurpose.RESCHEDULING_TREATMENT, "rescheduling-treatment", (
            RuleParameter("action", "use-current-schedule"),)),
        inclusion_rules=(_rule(RulePurpose.POPULATION_INCLUSION, "include-all-otherwise-eligible"),),
        exclusion_rules=(_rule(RulePurpose.POPULATION_EXCLUSION, "exclude-none-additional"),),
    )
    dimension_rule = _rule(RulePurpose.DIMENSION_CLASSIFICATION, "snapshot-partition", (
        RuleParameter("partition_keys", ("favorite", "underdog")),))
    dimension = ApprovedResearchDimension.create(
        "market-position", dimension_rule,
        (ApprovedDimensionPartition("favorite", "Market favorite"),
         ApprovedDimensionPartition("underdog", "Market underdog")),
    )
    broad = ResearchDomain.create(sport="baseball", competition="MLB", proposition_type="winner")
    favorite = ResearchDomain.create(
        sport="baseball", competition="MLB", proposition_type="winner",
        partition_selections=(DimensionPartitionSelection(dimension.approved_dimension_id, "favorite"),),
    )
    underdog = ResearchDomain.create(
        sport="baseball", competition="MLB", proposition_type="winner",
        partition_selections=(DimensionPartitionSelection(dimension.approved_dimension_id, "underdog"),),
    )
    drift_classification = _rule(RulePurpose.DRIFT_CLASSIFICATION, "brier-deterioration", (
        RuleParameter("threshold", Decimal("0.010")),))
    protocol = ResearchProtocol.create(
        protocol_version="1", effective_at=_at(payload, "protocol_effective_at"),
        scientific_question="Do the supplied challengers outperform the Kalshi MLB winner benchmark?",
        research_population=population, market_benchmark=benchmark,
        alternative_sources=(challenger_a, challenger_b), approved_dimensions=(dimension,),
        research_domains=(broad, favorite, underdog),
        snapshot_timing_rule=_rule(RulePurpose.SNAPSHOT_TIMING, "pregame-offset", (
            RuleParameter("seconds_before_start", 21600),)),
        capture_tolerance_rule=_rule(RulePurpose.CAPTURE_TOLERANCE, "symmetric-capture-tolerance", (
            RuleParameter("seconds", 300),)),
        synchronization_rule=_rule(RulePurpose.SYNCHRONIZATION, "maximum-pair-separation", (
            RuleParameter("seconds", 600),)),
        event_compatibility_rule=_rule(RulePurpose.EVENT_COMPATIBILITY, "canonical-event-proposition"),
        outcome_resolution_rule=_rule(RulePurpose.OUTCOME_RESOLUTION, "authoritative-outcome-source", (
            RuleParameter("source_id", "mlb-stats-api"),)),
        primary_measure_rule=_rule(RulePurpose.PRIMARY_MEASURE, "brier-score-improvement", (
            RuleParameter("favorable_direction", "positive"),)),
        supporting_measure_rules=(
            _rule(RulePurpose.SUPPORTING_MEASURE, "log-loss-safeguard"),
            _rule(RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard"),
        ),
        statistical_method_rule=_rule(RulePurpose.STATISTICAL_METHOD, "paired-bootstrap", (
            RuleParameter("confidence_level", Decimal("0.95")), RuleParameter("resamples", 1000))),
        practical_significance_rule=_rule(RulePurpose.PRACTICAL_SIGNIFICANCE, "minimum-brier-improvement", (
            RuleParameter("minimum_improvement", Decimal("0.005")),)),
        burden_of_proof_rule=_rule(RulePurpose.BURDEN_OF_PROOF, "complete-empirical-burden", (
            RuleParameter("required_checks", ("calibration", "log-loss", "practical-significance", "statistical-significance")),)),
        surveillance_window_rules=(_rule(RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", (
            RuleParameter("days", 30),)),),
        drift_classification_rule=drift_classification,
        drift_material_event_rule=_rule(RulePurpose.DRIFT_MATERIAL_EVENT_MAPPING,
                                        "drift-disposition-material-events", (
            RuleParameter("qualifying_dispositions", ("material-drift",)),)),
        scheduled_review_boundaries=(
            ScheduledReviewBoundary("june-review", _at(payload, "first_required_analysis_at"),
                                    int(payload["positive_grace_seconds"])),
            ScheduledReviewBoundary("july-review", _at(payload, "second_required_analysis_at"), 0),
        ),
        limitations=("synthetic fixture; no empirical finding",), provenance=provenance,
    )
    claim_a = EdgeClaim.create(
        protocol_id=protocol.research_protocol_id,
        challenger_source_reference_id=challenger_a.probability_source_reference_id,
        benchmark_source_reference_id=benchmark.probability_source_reference_id,
        research_domain_id=broad.research_domain_id, provenance=provenance,
        hypothesis_statement="DRatings outperforms the Kalshi benchmark in the broad MLB population.",
    )
    claim_b = EdgeClaim.create(
        protocol_id=protocol.research_protocol_id,
        challenger_source_reference_id=challenger_b.probability_source_reference_id,
        benchmark_source_reference_id=benchmark.probability_source_reference_id,
        research_domain_id=favorite.research_domain_id, provenance=provenance,
    )
    first_report = ComparativePerformanceReportReference(
        "1", "1", "comparative-performance-report:june", "1", protocol.research_protocol_id,
        _at(payload, "first_report_analysis_at"), (claim_a.edge_claim_id, claim_b.edge_claim_id),
    )
    later_report = ComparativePerformanceReportReference(
        "1", "1", "comparative-performance-report:july", "1", protocol.research_protocol_id,
        _at(payload, "later_report_analysis_at"), (claim_a.edge_claim_id,),
    )
    drifts = tuple(DriftSurveillance.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim_a.edge_claim_id,
        drift_rule_id=drift_classification.rule_id, drift_rule_version=drift_classification.rule_version,
        report_reference=first_report, effective_at=_at(payload, "drift_effective_at"),
        disposition=disposition, provenance=provenance,
    ) for disposition in DriftDisposition)
    material_drift = next(item for item in drifts if item.disposition is DriftDisposition.MATERIAL_DRIFT)
    scheduled_coverage = ReviewObligationReference(
        ReviewObligationKind.SCHEDULED_BOUNDARY,
        scheduled_boundary=ScheduledReviewBoundaryReference(protocol.research_protocol_id, "june-review"),
    )
    drift_coverage = ReviewObligationReference(
        ReviewObligationKind.MATERIAL_DRIFT,
        drift_surveillance=DriftSurveillanceReference(
            material_drift.protocol_id, material_drift.edge_claim_id,
            material_drift.drift_surveillance_id, material_drift.effective_at),
    )
    supported = ResearchReview.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim_a.edge_claim_id,
        report_reference=first_report, conclusion=ResearchReviewConclusion.SUPPORTED,
        obligation_coverage=ReviewObligationCoverage((scheduled_coverage, drift_coverage)),
        completed_at=_at(payload, "timely_review_completed_at"),
        rationale="The fixture records a completed Supported conclusion under the protocol.", provenance=provenance,
    )
    adverse = ResearchReview.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim_a.edge_claim_id,
        report_reference=later_report, conclusion=ResearchReviewConclusion.WEAKENING,
        obligation_coverage=ReviewObligationCoverage((
            ReviewObligationReference(ReviewObligationKind.SCHEDULED_BOUNDARY,
                scheduled_boundary=ScheduledReviewBoundaryReference(protocol.research_protocol_id, "july-review")),
            drift_coverage,
        )), completed_at=_at(payload, "late_review_completed_at"),
        rationale="The later fixture Review records an adverse conclusion without erasing history.", provenance=provenance,
    )
    market_edge = create_market_edge(edge_claim=claim_a, reviews=(supported, adverse),
                                     existing_market_edges=(), provenance=provenance)
    graph = {"protocols": (protocol,), "claims": (claim_a, claim_b), "reviews": (supported, adverse),
             "market_edges": (market_edge,), "drift_surveillance": drifts,
             "reports": (first_report, later_report), "provenance": provenance}
    # Exercise normal tagged reconstruction for every durable top-level artifact.
    for key, contract_type in (("protocols", ResearchProtocol), ("claims", EdgeClaim),
                               ("reviews", ResearchReview), ("market_edges", MarketEdge),
                               ("drift_surveillance", DriftSurveillance)):
        graph[key] = tuple(contract_type.from_json(item.to_json()) for item in graph[key])
    return graph


def run(path: Path) -> tuple[str, ...]:
    graph = load_fixture(path)
    validate_research_contracts(
        protocols=graph["protocols"], claims=graph["claims"], reviews=graph["reviews"],
        market_edges=graph["market_edges"], drift_surveillance=graph["drift_surveillance"],
    )
    protocol = graph["protocols"][0]
    lines = [
        "PR13 Forecast Intelligence Research Contracts: VALID",
        f"Research Protocol: {protocol.research_protocol_id}",
        f"Edge Claims: {len(graph['claims'])}",
        f"Research Reviews: {', '.join(item.conclusion.value for item in graph['reviews'])}",
        f"Drift dispositions: {', '.join(item.disposition.value for item in graph['drift_surveillance'])}",
        f"Material Drift artifacts: {sum(drift_creates_material_event(protocol, item) for item in graph['drift_surveillance'])}",
        f"Historical Market Edge: {graph['market_edges'][0].market_edge_id}",
        "Current Scientific Applicability: deferred to PR16",
    ]
    return tuple(lines)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/forecast_research_contract_cases.json")
    print("\n".join(run(path)))


if __name__ == "__main__":
    main()
