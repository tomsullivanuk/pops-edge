import inspect
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal
from pathlib import Path

from event_contracts import ContractError
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
    ResearchContractProvenance,
    ResearchDomain,
    ResearchProtocol,
    ResearchReview,
    ResearchReviewConclusion,
    ReviewObligationCoverage,
    ReviewObligationKind,
    ReviewObligationReference,
    RuleParameter,
    RulePurpose,
    ScheduledReviewBoundary,
    VersionedRuleSpecification,
    create_market_edge,
    drift_creates_material_event,
    validate_research_contracts,
)
from inspect_forecast_research_contracts import load_fixture, run


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_research_contract_cases.json"


class ForecastResearchContractTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_fixture(FIXTURE)
        self.protocol = self.graph["protocols"][0]
        self.claim = self.graph["claims"][0]
        self.supported, self.adverse = self.graph["reviews"]
        self.edge = self.graph["market_edges"][0]
        self.drifts = self.graph["drift_surveillance"]
        self.material_drift = next(item for item in self.drifts if item.disposition is DriftDisposition.MATERIAL_DRIFT)
        self.provenance = self.graph["provenance"]

    def validate(self, **changes):
        values = dict(protocols=self.graph["protocols"], claims=self.graph["claims"],
                      reviews=self.graph["reviews"], market_edges=self.graph["market_edges"],
                      drift_surveillance=self.graph["drift_surveillance"])
        values.update(changes)
        validate_research_contracts(**values)

    def recreate_review(self, base=None, **changes):
        base = base or self.supported
        values = dict(protocol_id=base.protocol_id, edge_claim_id=base.edge_claim_id,
                      report_reference=base.report_reference, conclusion=base.conclusion,
                      obligation_coverage=base.obligation_coverage, completed_at=base.completed_at,
                      rationale=base.rationale, provenance=base.provenance)
        values.update(changes)
        return ResearchReview.create(**values)

    def recreate_drift(self, base=None, **changes):
        base = base or self.material_drift
        values = dict(protocol_id=base.protocol_id, edge_claim_id=base.edge_claim_id,
                      drift_rule_id=base.drift_rule_id, drift_rule_version=base.drift_rule_version,
                      report_reference=base.report_reference, effective_at=base.effective_at,
                      disposition=base.disposition, provenance=base.provenance)
        values.update(changes)
        return DriftSurveillance.create(**values)

    def recreate_protocol(self, base=None, **changes):
        base = base or self.protocol
        values = dict(
            protocol_version=base.protocol_version, effective_at=base.effective_at,
            scientific_question=base.scientific_question, research_population=base.research_population,
            market_benchmark=base.market_benchmark, alternative_sources=base.alternative_sources,
            approved_dimensions=base.approved_dimensions, research_domains=base.research_domains,
            snapshot_timing_rule=base.snapshot_timing_rule, capture_tolerance_rule=base.capture_tolerance_rule,
            synchronization_rule=base.synchronization_rule, event_compatibility_rule=base.event_compatibility_rule,
            outcome_resolution_rule=base.outcome_resolution_rule, primary_measure_rule=base.primary_measure_rule,
            supporting_measure_rules=base.supporting_measure_rules,
            statistical_method_rule=base.statistical_method_rule,
            practical_significance_rule=base.practical_significance_rule,
            burden_of_proof_rule=base.burden_of_proof_rule,
            surveillance_window_rules=base.surveillance_window_rules,
            drift_classification_rule=base.drift_classification_rule,
            drift_material_event_rule=base.drift_material_event_rule,
            scheduled_review_boundaries=base.scheduled_review_boundaries,
            limitations=base.limitations, provenance=base.provenance,
        )
        values.update(changes)
        return ResearchProtocol.create(**values)

    def test_fixture_graph_and_inspector_are_valid_and_deterministic(self):
        self.validate()
        first = run(FIXTURE)
        self.assertEqual(first, run(FIXTURE))
        self.assertIn("PR13 Forecast Intelligence Research Contracts: VALID", first)

    def test_five_top_level_contracts_are_immutable_and_tagged_serializable(self):
        values = (self.protocol, self.claim, self.supported, self.edge, self.material_drift)
        for value in values:
            restored = type(value).from_json(value.to_json())
            self.assertEqual(restored, value)
            self.assertIn(f'"__type__":"{type(value).__name__}"', value.to_json())
            with self.assertRaises(FrozenInstanceError):
                value.input_digest = "changed"

    def test_nested_types_and_enums_round_trip(self):
        restored = ResearchReview.from_json(self.supported.to_json())
        self.assertIs(restored.conclusion, ResearchReviewConclusion.SUPPORTED)
        self.assertIs(restored.obligation_coverage.obligations[0].kind, ReviewObligationKind.MATERIAL_DRIFT)
        drift = DriftSurveillance.from_json(self.material_drift.to_json())
        self.assertIs(drift.disposition, DriftDisposition.MATERIAL_DRIFT)

    def test_tampered_id_and_digest_fail_closed(self):
        with self.assertRaises(ContractError):
            replace(self.claim, edge_claim_id="edge-claim:tampered")
        with self.assertRaises(ContractError):
            replace(self.claim, input_digest="0" * 64)

    def test_nonmaterial_metadata_does_not_change_identity(self):
        later = replace(self.provenance, generated_at=self.provenance.generated_at + timedelta(days=1),
                        notes=("different note",))
        claim = EdgeClaim.create(protocol_id=self.claim.protocol_id,
            challenger_source_reference_id=self.claim.challenger_source_reference_id,
            benchmark_source_reference_id=self.claim.benchmark_source_reference_id,
            research_domain_id=self.claim.research_domain_id, hypothesis_statement="Different wording", provenance=later)
        self.assertEqual(claim.edge_claim_id, self.claim.edge_claim_id)
        self.assertEqual(claim.input_digest, self.claim.input_digest)
        dimension = self.protocol.approved_dimensions[0]
        partitions = (replace(dimension.partitions[0], display_label="Different label"),
                      *dimension.partitions[1:])
        relabeled = ApprovedResearchDimension.create(
            dimension.dimension_key, dimension.classification_rule, partitions,
            dimension.limitations,
        )
        self.assertEqual(relabeled.approved_dimension_id, dimension.approved_dimension_id)
        self.assertEqual(relabeled.input_digest, dimension.input_digest)

    def test_provenance_generation_time_is_optional_aware_and_has_no_default_clock(self):
        ResearchContractProvenance("producer", "1", generated_at=None)
        with self.assertRaises(ContractError):
            ResearchContractProvenance("producer", "1", generated_at=self.supported.completed_at.replace(tzinfo=None))
        self.assertIs(inspect.signature(ResearchContractProvenance).parameters["generated_at"].default, None)

    def test_rule_decimal_is_exact_and_round_trips(self):
        rule = self.protocol.practical_significance_rule
        restored = VersionedRuleSpecification.from_json(rule.to_json())
        self.assertEqual(restored.parameters[0].value, Decimal("0.005"))
        self.assertIn('"__decimal__":"0.005"', rule.to_json())

    def test_rule_rejects_float_nonfinite_decimal_bool_as_int_and_unknown_parameter(self):
        with self.assertRaises(ContractError):
            RuleParameter("minimum_improvement", 0.1)
        with self.assertRaises(ContractError):
            RuleParameter("minimum_improvement", Decimal("NaN"))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.SNAPSHOT_TIMING, "pregame-offset", "1",
                                              (RuleParameter("seconds_before_start", True),))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.PROBABILITY_TRANSFORMATION, "identity-probability", "1",
                                              (RuleParameter("unknown", "x"),))

    def test_rule_rejects_missing_duplicate_wrong_type_and_bounds(self):
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.PRACTICAL_SIGNIFICANCE,
                                              "minimum-brier-improvement", "1")
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.PRACTICAL_SIGNIFICANCE,
                "minimum-brier-improvement", "1", (RuleParameter("minimum_improvement", Decimal("0.1")),
                                                     RuleParameter("minimum_improvement", Decimal("0.2"))))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.PRACTICAL_SIGNIFICANCE,
                "minimum-brier-improvement", "1", (RuleParameter("minimum_improvement", "0.1"),))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "1",
                                              (RuleParameter("days", 0),))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.STATISTICAL_METHOD, "paired-bootstrap", "1", (
                RuleParameter("confidence_level", Decimal("1.01")),
                RuleParameter("resamples", 1000),
            ))
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(
                RulePurpose.DRIFT_MATERIAL_EVENT_MAPPING,
                "drift-disposition-material-events",
                "1",
                (RuleParameter("qualifying_dispositions", ("not-a-disposition",)),),
            )

    def test_tuple_parameter_order_is_canonical_only_by_registered_schema(self):
        one = VersionedRuleSpecification.create(RulePurpose.EVENT_STATUS_ELIGIBILITY,
            "allowed-event-statuses", "1", (RuleParameter("statuses", ("scheduled", "final")),))
        two = VersionedRuleSpecification.create(RulePurpose.EVENT_STATUS_ELIGIBILITY,
            "allowed-event-statuses", "1", (RuleParameter("statuses", ("final", "scheduled")),))
        self.assertEqual(one, two)

    def test_version_tampering_fails_closed(self):
        with self.assertRaises(ContractError):
            replace(self.claim, schema_version="2")
        with self.assertRaises(ContractError):
            replace(self.claim, identity_algorithm_version="2")
        with self.assertRaises(ContractError):
            replace(self.material_drift, analysis_algorithm_version="2")

    def test_utc_equivalent_instants_produce_same_identity(self):
        shifted = self.material_drift.effective_at.astimezone(timezone(timedelta(hours=-6)))
        other = self.recreate_drift(effective_at=shifted)
        self.assertEqual(other.drift_surveillance_id, self.material_drift.drift_surveillance_id)

    def test_material_time_changes_identity(self):
        later = self.recreate_drift(effective_at=self.material_drift.effective_at + timedelta(seconds=1))
        self.assertNotEqual(later.drift_surveillance_id, self.material_drift.drift_surveillance_id)

    def test_source_role_is_not_intrinsic(self):
        source = self.protocol.market_benchmark
        self.assertNotIn("source_role", source.__dataclass_fields__)
        self.assertNotIn("benchmark", source.to_json())

    def test_protocol_has_broad_domain_and_explicit_population_rules(self):
        self.assertTrue(any(not item.partition_selections for item in self.protocol.research_domains))
        population = self.protocol.research_population
        self.assertIsNotNone(population.postponement_treatment_rule)
        self.assertTrue(population.inclusion_rules)

    def test_duplicate_boundary_dimension_partition_and_domain_selection_fail(self):
        with self.assertRaises(ContractError):
            replace(self.protocol, scheduled_review_boundaries=(self.protocol.scheduled_review_boundaries[0],) * 2)
        with self.assertRaises(ContractError):
            replace(self.protocol, approved_dimensions=(self.protocol.approved_dimensions[0],) * 2)
        partition = ApprovedDimensionPartition("favorite", "duplicate")
        with self.assertRaises(ContractError):
            replace(self.protocol.approved_dimensions[0], partitions=(partition, partition))
        partitioned = next(item for item in self.protocol.research_domains if item.partition_selections)
        selection = partitioned.partition_selections[0]
        with self.assertRaises(ContractError):
            replace(partitioned, partition_selections=(selection, selection))

    def test_protocol_rejects_missing_broad_domain_and_benchmark_as_challenger(self):
        with self.assertRaises(ContractError):
            replace(self.protocol, research_domains=tuple(item for item in self.protocol.research_domains if item.partition_selections))
        with self.assertRaises(ContractError):
            replace(self.protocol, alternative_sources=(self.protocol.market_benchmark,))

    def test_scheduled_boundary_grace_is_derived_and_bool_rejected(self):
        boundary = next(item for item in self.protocol.scheduled_review_boundaries if item.boundary_key == "june-review")
        self.assertEqual(boundary.obligation_due_at,
                         boundary.required_analysis_boundary_at + timedelta(seconds=boundary.grace_period_seconds))
        self.assertNotIn("obligation_due_at", boundary.__dataclass_fields__)
        with self.assertRaises(ContractError):
            ScheduledReviewBoundary("bad", boundary.required_analysis_boundary_at, True)

    def test_edge_claim_authorization_and_equivalence(self):
        equivalent = EdgeClaim.create(protocol_id=self.claim.protocol_id,
            challenger_source_reference_id=self.claim.challenger_source_reference_id,
            benchmark_source_reference_id=self.claim.benchmark_source_reference_id,
            research_domain_id=self.claim.research_domain_id, provenance=self.provenance)
        self.assertEqual(equivalent.edge_claim_id, self.claim.edge_claim_id)
        bad = EdgeClaim.create(protocol_id=self.claim.protocol_id,
            challenger_source_reference_id="probability-source-reference:unknown",
            benchmark_source_reference_id=self.claim.benchmark_source_reference_id,
            research_domain_id=self.claim.research_domain_id, provenance=self.provenance)
        with self.assertRaises(ContractError):
            self.validate(claims=(bad,))

    def test_report_reference_requires_nonempty_unique_claim_coverage(self):
        report = self.supported.report_reference
        with self.assertRaises(ContractError):
            replace(report, edge_claim_ids=())
        with self.assertRaises(ContractError):
            replace(report, edge_claim_ids=(self.claim.edge_claim_id, self.claim.edge_claim_id))
        unknown = replace(report, edge_claim_ids=(self.claim.edge_claim_id, "edge-claim:unknown"))
        review = self.recreate_review(report_reference=unknown)
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_review_requires_one_supported_conclusion_report_claim_and_chronology(self):
        self.assertNotIn("under-review", {item.value for item in ResearchReviewConclusion})
        report = replace(self.supported.report_reference, edge_claim_ids=(self.graph["claims"][1].edge_claim_id,))
        with self.assertRaises(ContractError):
            self.recreate_review(report_reference=report)
        with self.assertRaises(ContractError):
            self.recreate_review(completed_at=self.supported.report_reference.analysis_boundary - timedelta(seconds=1))

    def test_review_does_not_implement_assessment_or_applicability_state(self):
        fields = set(ResearchReview.__dataclass_fields__)
        self.assertFalse(fields & {"under_review", "current_applicability", "active_market_edge",
                                   "assessment_algorithm_version", "as_of"})

    def test_scheduled_coverage_at_boundary_during_grace_and_after_due_is_valid(self):
        boundary = next(item for item in self.protocol.scheduled_review_boundaries if item.boundary_key == "june-review")
        self.assertLess(self.supported.completed_at, boundary.obligation_due_at)
        self.validate()
        late = self.recreate_review(completed_at=boundary.obligation_due_at + timedelta(days=1))
        self.validate(reviews=(late, self.adverse), market_edges=())

    def test_scheduled_coverage_report_before_required_boundary_fails(self):
        boundary = next(item for item in self.protocol.scheduled_review_boundaries if item.boundary_key == "june-review")
        old_report = replace(self.supported.report_reference,
                             analysis_boundary=boundary.required_analysis_boundary_at - timedelta(seconds=1))
        review = self.recreate_review(report_reference=old_report)
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_explicit_coverage_may_be_empty_when_review_claims_no_obligations(self):
        review = self.recreate_review(obligation_coverage=ReviewObligationCoverage())
        self.validate(reviews=(review,), market_edges=())
        self.assertFalse(review.obligation_coverage.obligations)

    def test_all_drift_dispositions_are_valid_and_materiality_is_protocol_derived(self):
        self.assertEqual({item.disposition for item in self.drifts}, set(DriftDisposition))
        self.assertEqual([drift_creates_material_event(self.protocol, item) for item in self.drifts],
                         [False, True, False])
        self.assertNotIn("is_material_event", DriftSurveillance.__dataclass_fields__)

    def test_invalid_drift_input_produces_no_artifact(self):
        with self.assertRaises(ContractError):
            self.recreate_drift(report_reference=replace(self.material_drift.report_reference,
                                                         edge_claim_ids=(self.graph["claims"][1].edge_claim_id,)))
        with self.assertRaises(ContractError):
            self.recreate_drift(effective_at=self.material_drift.report_reference.analysis_boundary - timedelta(seconds=1))

    def test_nonqualifying_drift_cannot_be_covered(self):
        no_drift = next(item for item in self.drifts if item.disposition is DriftDisposition.NO_MATERIAL_DRIFT)
        reference = DriftSurveillanceReference(no_drift.protocol_id, no_drift.edge_claim_id,
                                               no_drift.drift_surveillance_id, no_drift.effective_at)
        obligation = ReviewObligationReference(ReviewObligationKind.MATERIAL_DRIFT, drift_surveillance=reference)
        review = self.recreate_review(obligation_coverage=ReviewObligationCoverage((obligation,)))
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_same_report_drift_coverage_succeeds_when_effective_after_report(self):
        self.assertLess(self.material_drift.report_reference.analysis_boundary, self.material_drift.effective_at)
        self.assertEqual(self.supported.report_reference, self.material_drift.report_reference)
        self.assertLessEqual(self.material_drift.effective_at, self.supported.completed_at)
        self.validate()

    def test_premature_review_drift_coverage_fails_even_with_later_report(self):
        later_but_premature_report = replace(
            self.supported.report_reference,
            analysis_boundary=self.material_drift.report_reference.analysis_boundary + timedelta(hours=1),
        )
        review = self.recreate_review(report_reference=later_but_premature_report,
                                      completed_at=self.material_drift.effective_at - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_older_covering_report_fails(self):
        old_report = replace(self.supported.report_reference,
                             analysis_boundary=self.material_drift.report_reference.analysis_boundary - timedelta(seconds=1))
        review = self.recreate_review(report_reference=old_report)
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_later_compatible_report_drift_coverage_succeeds(self):
        self.assertGreater(self.adverse.report_reference.analysis_boundary,
                           self.material_drift.report_reference.analysis_boundary)
        self.validate()

    def test_drift_boundary_equalities_succeed(self):
        drift = self.recreate_drift(effective_at=self.material_drift.report_reference.analysis_boundary)
        reference = DriftSurveillanceReference(drift.protocol_id, drift.edge_claim_id,
                                               drift.drift_surveillance_id, drift.effective_at)
        obligation = ReviewObligationReference(ReviewObligationKind.MATERIAL_DRIFT, drift_surveillance=reference)
        review = self.recreate_review(obligation_coverage=ReviewObligationCoverage((obligation,)),
                                      completed_at=drift.effective_at)
        self.validate(reviews=(review,), market_edges=(), drift_surveillance=(drift,))

    def test_drift_reference_validation_copies_must_match(self):
        obligations = list(self.supported.obligation_coverage.obligations)
        drift_obligation = next(item for item in obligations if item.drift_surveillance)
        bad_ref = replace(drift_obligation.drift_surveillance, effective_at=self.material_drift.effective_at + timedelta(seconds=1))
        obligations[obligations.index(drift_obligation)] = ReviewObligationReference(
            ReviewObligationKind.MATERIAL_DRIFT, drift_surveillance=bad_ref)
        review = self.recreate_review(obligation_coverage=ReviewObligationCoverage(tuple(obligations)))
        with self.assertRaises(ContractError):
            self.validate(reviews=(review,), market_edges=())

    def test_market_edge_uses_first_qualifying_review_and_survives_adverse_review(self):
        self.assertEqual(self.edge.establishing_review_id, self.supported.research_review_id)
        self.assertEqual(self.edge.established_at, self.supported.completed_at)
        self.validate()

    def test_no_qualifying_review_and_second_market_edge_fail(self):
        with self.assertRaises(ContractError):
            create_market_edge(edge_claim=self.claim, reviews=(self.adverse,), existing_market_edges=(),
                               provenance=self.provenance)
        with self.assertRaises(ContractError):
            create_market_edge(edge_claim=self.claim, reviews=(self.supported,), existing_market_edges=(self.edge,),
                               provenance=self.provenance)

    def test_repeated_identical_review_counts_once(self):
        edge = create_market_edge(edge_claim=self.claim, reviews=(self.supported, self.supported),
                                  existing_market_edges=(), provenance=self.provenance)
        self.assertEqual(edge.establishing_review_id, self.supported.research_review_id)

    def test_simultaneous_materially_distinct_qualifying_reviews_fail_closed(self):
        conflicting = self.recreate_review(rationale="A materially different simultaneous conclusion artifact")
        with self.assertRaises(ContractError):
            create_market_edge(edge_claim=self.claim, reviews=(conflicting, self.supported),
                               existing_market_edges=(), provenance=self.provenance)
        with self.assertRaises(ContractError):
            create_market_edge(edge_claim=self.claim, reviews=(self.supported, conflicting),
                               existing_market_edges=(), provenance=self.provenance)

    def test_duplicate_obligation_rejected(self):
        obligation = self.supported.obligation_coverage.obligations[0]
        with self.assertRaises(ContractError):
            ReviewObligationCoverage((obligation, obligation))

    def test_no_pr14_or_operational_authority_contracts(self):
        serialized = " ".join(item.to_json() for item in
                              (self.protocol, self.claim, self.supported, self.edge, self.material_drift)).lower()
        for forbidden in ("current_applicability", "currentscientificapplicability", "active_market_edge",
                          "under_review_state", "forecast_policy", "governance", "production_authority"):
            self.assertNotIn(forbidden, serialized)

    def test_invalid_obligation_kind_fails_direct_construction_and_tagged_reconstruction(self):
        scheduled = next(item.scheduled_boundary for item in self.supported.obligation_coverage.obligations
                         if item.scheduled_boundary is not None)
        with self.assertRaises(ContractError):
            ReviewObligationReference("not-a-kind", scheduled_boundary=scheduled)
        payload = self.supported.to_dict()
        obligation = next(item for item in payload["obligation_coverage"]["obligations"]
                          if item["scheduled_boundary"] is not None)
        obligation["kind"] = "not-a-kind"
        with self.assertRaises(ContractError):
            ResearchReview.from_dict(payload)

    def test_scheduled_coverage_exactly_at_due_is_valid(self):
        boundary = next(item for item in self.protocol.scheduled_review_boundaries
                        if item.boundary_key == "june-review")
        review = self.recreate_review(completed_at=boundary.obligation_due_at)
        self.validate(reviews=(review, self.adverse), market_edges=())

    def test_strongly_supported_first_review_establishes_market_edge(self):
        strong = self.recreate_review(conclusion=ResearchReviewConclusion.STRONGLY_SUPPORTED)
        edge = create_market_edge(edge_claim=self.claim, reviews=(strong, self.adverse),
                                  existing_market_edges=(), provenance=self.provenance)
        self.assertEqual(edge.establishing_review_id, strong.research_review_id)
        self.assertEqual(edge.established_at, strong.completed_at)

    def test_later_qualifying_reviews_preserve_original_market_edge(self):
        for conclusion in (ResearchReviewConclusion.SUPPORTED,
                           ResearchReviewConclusion.STRONGLY_SUPPORTED):
            later = self.recreate_review(
                conclusion=conclusion, completed_at=self.adverse.completed_at + timedelta(days=1),
                rationale=f"Later {conclusion.value} conclusion.",
            )
            validate_research_contracts(
                protocols=self.graph["protocols"], claims=self.graph["claims"],
                reviews=(self.supported, self.adverse, later), market_edges=(self.edge,),
                drift_surveillance=self.graph["drift_surveillance"],
            )
            self.assertEqual(self.edge.establishing_review_id, self.supported.research_review_id)
            self.assertEqual(self.edge.established_at, self.supported.completed_at)

    def test_review_rationale_and_protocol_scientific_question_are_material(self):
        review = self.recreate_review(rationale="A different completed scientific rationale.")
        self.assertNotEqual(review.research_review_id, self.supported.research_review_id)
        self.assertNotEqual(review.input_digest, self.supported.input_digest)
        protocol = self.recreate_protocol(scientific_question="A materially different prospective question?")
        self.assertNotEqual(protocol.research_protocol_id, self.protocol.research_protocol_id)
        self.assertNotEqual(protocol.input_digest, self.protocol.input_digest)

    def test_protocol_requires_unique_challengers_and_correct_rule_purposes(self):
        with self.assertRaises(ContractError):
            self.recreate_protocol(alternative_sources=())
        challenger = self.protocol.alternative_sources[0]
        with self.assertRaises(ContractError):
            self.recreate_protocol(alternative_sources=(challenger, challenger))
        with self.assertRaises(ContractError):
            self.recreate_protocol(alternative_sources=(self.protocol.market_benchmark,))
        with self.assertRaises(ContractError):
            self.recreate_protocol(burden_of_proof_rule=self.protocol.practical_significance_rule)

    def test_individually_approved_partitions_do_not_authorize_cross_products(self):
        second_rule = VersionedRuleSpecification.create(
            RulePurpose.DIMENSION_CLASSIFICATION, "snapshot-partition", "1",
            (RuleParameter("partition_keys", ("day", "night")),),
        )
        second_dimension = ApprovedResearchDimension.create(
            "start-time", second_rule,
            (ApprovedDimensionPartition("day", "Day"), ApprovedDimensionPartition("night", "Night")),
        )
        protocol = self.recreate_protocol(
            approved_dimensions=(*self.protocol.approved_dimensions, second_dimension),
        )
        first_dimension = self.protocol.approved_dimensions[0]
        unauthorized = ResearchDomain.create(
            sport=self.protocol.research_population.sport,
            competition=self.protocol.research_population.competition,
            proposition_type=self.protocol.research_population.proposition_type,
            partition_selections=(
                DimensionPartitionSelection(first_dimension.approved_dimension_id, "favorite"),
                DimensionPartitionSelection(second_dimension.approved_dimension_id, "day"),
            ),
        )
        claim = EdgeClaim.create(
            protocol_id=protocol.research_protocol_id,
            challenger_source_reference_id=protocol.alternative_sources[0].probability_source_reference_id,
            benchmark_source_reference_id=protocol.market_benchmark.probability_source_reference_id,
            research_domain_id=unauthorized.research_domain_id, provenance=self.provenance,
        )
        with self.assertRaises(ContractError):
            validate_research_contracts(protocols=(protocol,), claims=(claim,), reviews=(),
                                        market_edges=(), drift_surveillance=())

    def test_all_and_only_completed_review_conclusions_are_available(self):
        self.assertEqual(
            {item.value for item in ResearchReviewConclusion},
            {"insufficient-evidence", "emerging-evidence", "supported", "strongly-supported",
             "weakening", "no-longer-supported", "rejected"},
        )
        for conclusion in ResearchReviewConclusion:
            self.assertIs(self.recreate_review(conclusion=conclusion).conclusion, conclusion)
        with self.assertRaises(ContractError):
            self.recreate_review(conclusion="under-review")

    def test_graph_validation_is_independent_of_nonmaterial_input_order(self):
        self.validate()
        validate_research_contracts(
            protocols=tuple(reversed(self.graph["protocols"])),
            claims=tuple(reversed(self.graph["claims"])),
            reviews=tuple(reversed(self.graph["reviews"])),
            market_edges=tuple(reversed(self.graph["market_edges"])),
            drift_surveillance=tuple(reversed(self.graph["drift_surveillance"])),
        )


if __name__ == "__main__":
    unittest.main()
