import inspect
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal, getcontext, localcontext
from pathlib import Path
from types import SimpleNamespace

from event_contracts import ContractError
from forecast_comparative_research import (
    CALIBRATION_BOUNDARIES,
    CalibrationBin,
    CalibrationResult,
    ComparativePerformance,
    EventPhase,
    PopulationEligibilityDisposition,
    PopulationEligibilityResult,
    PopulationEligibilityValidationStatus,
    ResearchCaptureOpportunity,
    ResearchSnapshot,
    SnapshotValidationStatus,
    SourceCapture,
    SourceCaptureDisposition,
    create_comparative_measurement,
    create_pairwise_synchronization,
    create_comparative_performance,
    select_authoritative_research_snapshots,
    validate_comparative_research_contracts,
)
from forecast_research_contracts import EdgeClaim, RuleParameter, RulePurpose, VersionedRuleSpecification
from inspect_forecast_comparative_research import load_fixture, run


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_comparative_research_cases.json"


class ForecastComparativeResearchTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_fixture(FIXTURE)
        self.protocol = self.graph["protocols"][0]
        self.claim = next(item for item in self.graph["claims"]
                          if item.challenger_source_reference_id == self.protocol.alternative_sources[0].probability_source_reference_id)

    def validate(self, **changes):
        values = {name: self.graph[name] for name in (
            "protocols", "claims", "canonical_events", "event_stage_evidence", "schedule_observations",
            "outcome_histories", "opportunities", "eligibility_contexts", "eligibility_results", "snapshots",
            "forecast_observations", "forecast_evaluations", "outcome_observations", "measurements", "performances")}
        values.update(changes)
        validate_comparative_research_contracts(**values)

    def recreate_snapshot(self, base, **changes):
        values = dict(
            research_capture_opportunity_id=base.research_capture_opportunity_id,
            protocol_id=base.protocol_id, effective_at=base.effective_at,
            canonical_event_id=base.canonical_event_id, proposition_type=base.proposition_type,
            canonical_proposition_outcome_id=base.canonical_proposition_outcome_id,
            scheduled_start=base.scheduled_start, target_capture_at=base.target_capture_at,
            capture_started_at=base.capture_started_at, capture_completed_at=base.capture_completed_at,
            source_captures=base.source_captures, pairwise_synchronization=base.pairwise_synchronization,
            dimension_classifications=base.dimension_classifications,
            validation_status=base.validation_status, provenance=base.provenance,
            supersedes_snapshot_id=base.supersedes_snapshot_id, correction_reason=base.correction_reason,
            validation_reasons=base.validation_reasons, limitations=base.limitations,
        )
        values.update(changes)
        return ResearchSnapshot.create(**values)

    def performance(self, **changes):
        broad = next(item for item in self.protocol.research_domains if not item.partition_selections)
        values = dict(protocol=self.protocol, edge_claim=self.claim, research_domain=broad,
                      analysis_boundary=self.graph["after"], opportunities=self.graph["opportunities"],
                      eligibility_contexts=self.graph["eligibility_contexts"],
                      eligibility_results=self.graph["eligibility_results"], snapshots=self.graph["snapshots"],
                      measurements=self.graph["measurements"], outcome_histories=self.graph["outcome_histories"],
                      provenance=self.graph["provenance"])
        values.update(changes)
        return create_comparative_performance(**values)

    def recreate_performance(self, base, *, coverage):
        import forecast_comparative_research as module
        values = {field.name: getattr(base, field.name) for field in fields(ComparativePerformance)
                  if field.name not in ("comparative_performance_id", "input_digest")}
        values["coverage"] = coverage
        material = tuple(values[field.name] for field in fields(ComparativePerformance)
                         if field.name not in ("comparative_performance_id", "provenance",
                                               "input_digest", "limitations")) + (values["limitations"],)
        digest = module._digest(material)
        return ComparativePerformance(f"comparative-performance:{digest}", **values, input_digest=digest)

    def test_fixture_graph_and_inspector_are_valid_and_deterministic(self):
        self.validate()
        first = run(FIXTURE)
        self.assertEqual(first, run(FIXTURE))
        self.assertIn("PR14 Comparative Research: VALID", first)
        self.assertIn("Scientific status: synthetic descriptive output; Research Review deferred", first)

    def test_top_level_contracts_are_immutable_and_round_trip(self):
        values = (self.graph["opportunities"][0], self.graph["snapshots"][0],
                  self.graph["measurements"][0], self.graph["performances"][0])
        for value in values:
            self.assertEqual(type(value).from_json(value.to_json()), value)
            self.assertIn(f'"__type__":"{type(value).__name__}"', value.to_json())
            with self.assertRaises(FrozenInstanceError):
                value.input_digest = "changed"

    def test_tampered_content_addressed_artifacts_fail_closed(self):
        with self.assertRaises(ContractError):
            replace(self.graph["opportunities"][0], protocol_id="research-protocol:tampered")
        with self.assertRaises(ContractError):
            replace(self.graph["measurements"][0], brier_improvement=Decimal("0"))
        with self.assertRaises(ContractError):
            replace(self.graph["performances"][0], input_digest="0" * 64)

    def test_provenance_generation_time_is_nonmaterial(self):
        measurement = self.graph["measurements"][0]
        later = replace(measurement.provenance, generated_at=measurement.provenance.generated_at + timedelta(days=1))
        self.assertEqual(replace(measurement, provenance=later).comparative_measurement_id,
                         measurement.comparative_measurement_id)

    def test_no_wall_clock_defaults_and_aware_time_required(self):
        self.assertIs(inspect.signature(ResearchSnapshot.create).parameters["effective_at"].default, inspect.Parameter.empty)
        base = self.graph["snapshots"][0]
        with self.assertRaises(ContractError):
            self.recreate_snapshot(base, effective_at=base.effective_at.replace(tzinfo=None))

    def test_utc_equivalent_boundary_and_input_order_are_deterministic(self):
        shifted = self.graph["after"].astimezone(timezone(timedelta(hours=-6)))
        one = self.performance(analysis_boundary=shifted,
                               opportunities=tuple(reversed(self.graph["opportunities"])),
                               snapshots=tuple(reversed(self.graph["snapshots"])),
                               measurements=tuple(reversed(self.graph["measurements"])))
        two = self.performance()
        self.assertEqual(one, two)

    def test_calibration_v2_decimal_collection_round_trips_and_v1_remains(self):
        rule = next(item for item in self.protocol.supporting_measure_rules if item.rule_id == "calibration-safeguard")
        self.assertEqual(rule.rule_version, "2")
        self.assertEqual(rule.parameters[0].value, CALIBRATION_BOUNDARIES)
        self.assertEqual(VersionedRuleSpecification.from_json(rule.to_json()), rule)
        VersionedRuleSpecification.create(RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "1")
        with self.assertRaises(ContractError):
            VersionedRuleSpecification.create(RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "2",
                (RuleParameter("bin_boundaries", (Decimal("0"), Decimal("1"))),))

    def test_opportunity_identity_excludes_mapping_and_reschedule_creates_new_identity(self):
        opportunity = self.graph["opportunities"][0]
        same = ResearchCaptureOpportunity.create(opportunity.protocol_id, opportunity.schedule_observation_id,
                                                 opportunity.proposition_type)
        original_schedule = next(item for item in self.graph["opportunities"] if item.schedule_observation_id == "mlb-stats-api:c:schedule")
        rescheduled = next(item for item in self.graph["opportunities"] if item.schedule_observation_id == "mlb-stats-api:d:schedule")
        self.assertEqual(same, opportunity)
        self.assertNotEqual(rescheduled.research_capture_opportunity_id, original_schedule.research_capture_opportunity_id)
        schedules = {item.observation_id: item for item in self.graph["schedule_observations"]}
        self.assertEqual(schedules[rescheduled.schedule_observation_id].canonical_event_id,
                         schedules[original_schedule.schedule_observation_id].canonical_event_id)
        self.assertNotIn("canonical_event_id", opportunity.__dataclass_fields__)
        self.assertNotIn("retry", opportunity.__dataclass_fields__)

    def test_missing_and_total_failure_are_preserved_without_fake_observations(self):
        all_missing = next(item for item in self.graph["snapshots"] if item.canonical_event_id == "canonical-event:b")
        self.assertTrue(all(item.disposition is SourceCaptureDisposition.MISSING for item in all_missing.source_captures))
        self.assertTrue(all(item.forecast_observation_id is None for item in all_missing.source_captures))
        coverage = self.graph["performances"][-1].coverage
        self.assertIn(all_missing.research_snapshot_id, coverage.benchmark_capture_failure_snapshot_ids)
        self.assertIn(all_missing.research_snapshot_id, coverage.challenger_capture_failure_snapshot_ids)

    def test_pairwise_failure_is_challenger_specific(self):
        opportunity = next(item for item in self.graph["opportunities"] if item.schedule_observation_id == "mlb-stats-api:d:schedule")
        snapshot = next(item for item in self.graph["snapshots"]
                        if item.research_capture_opportunity_id == opportunity.research_capture_opportunity_id)
        pairs = {item.challenger_source_reference_id: item for item in snapshot.pairwise_synchronization}
        self.assertFalse(pairs[self.protocol.alternative_sources[0].probability_source_reference_id].synchronized)
        self.assertTrue(pairs[self.protocol.alternative_sources[1].probability_source_reference_id].synchronized)

    def test_invalid_and_outside_tolerance_captures_remain_evidence(self):
        captures = tuple(capture for snapshot in self.graph["snapshots"] for capture in snapshot.source_captures)
        invalid = next(item for item in captures if item.disposition is SourceCaptureDisposition.CAPTURED_INVALID)
        outside = next(item for item in captures if item.disposition is SourceCaptureDisposition.OUTSIDE_CAPTURE_TOLERANCE)
        self.assertIsNotNone(invalid.forecast_observation_id)
        self.assertIsNotNone(outside.forecast_observation_id)
        coverage = self.graph["performances"][-1].coverage
        outside_snapshot = next(item for item in self.graph["snapshots"] if outside in item.source_captures)
        self.assertIn(outside_snapshot.research_snapshot_id, coverage.capture_timing_failure_snapshot_ids)

    def test_historical_replay_uses_effective_at_and_correction_lineage(self):
        originals = [item for item in self.graph["snapshots"] if item.canonical_event_id == "canonical-event:a"]
        original = next(item for item in originals if item.supersedes_snapshot_id is None)
        correction = next(item for item in originals if item.supersedes_snapshot_id is not None)
        before = select_authoritative_research_snapshots(self.graph["snapshots"], self.graph["before"])
        after = select_authoritative_research_snapshots(self.graph["snapshots"], self.graph["after"])
        self.assertIn(original, before)
        self.assertNotIn(correction, before)
        self.assertIn(correction, after)
        self.assertNotIn(original, after)

    def test_correction_branch_and_cross_opportunity_fail_closed(self):
        original = next(item for item in self.graph["snapshots"]
                        if item.canonical_event_id == "canonical-event:a" and item.supersedes_snapshot_id is None)
        correction = next(item for item in self.graph["snapshots"] if item.supersedes_snapshot_id == original.research_snapshot_id)
        branch = self.recreate_snapshot(correction, correction_reason="different correction")
        with self.assertRaises(ContractError):
            select_authoritative_research_snapshots(self.graph["snapshots"] + (branch,), self.graph["after"])
        other = next(item for item in self.graph["snapshots"] if item.canonical_event_id == "canonical-event:e")
        crossed = self.recreate_snapshot(other, effective_at=self.graph["after"] - timedelta(hours=1),
                                         supersedes_snapshot_id=original.research_snapshot_id,
                                         correction_reason="invalid cross-opportunity correction")
        with self.assertRaises(ContractError):
            select_authoritative_research_snapshots((original, crossed), self.graph["after"])

    def test_correction_cannot_reconstruct_missing_evidence(self):
        original = next(item for item in self.graph["snapshots"] if item.canonical_event_id == "canonical-event:b")
        first = original.source_captures[0]
        captures = (SourceCapture(first.probability_source_reference_id, SourceCaptureDisposition.CAPTURED_VALID,
                                  "forecast-observation:retrospective", original.target_capture_at),) + original.source_captures[1:]
        correction = self.recreate_snapshot(original, effective_at=original.effective_at + timedelta(days=1),
                                            supersedes_snapshot_id=original.research_snapshot_id,
                                            correction_reason="invalid retrospective recovery",
                                            source_captures=captures)
        with self.assertRaises(ContractError):
            self.validate(snapshots=self.graph["snapshots"] + (correction,))

    def test_correction_rejects_observation_and_timestamp_substitution(self):
        original = next(item for item in self.graph["snapshots"]
                        if item.canonical_event_id == "canonical-event:e"
                        and item.supersedes_snapshot_id is None)
        captured = original.source_captures[0]
        substituted_observation = replace(
            captured, forecast_observation_id="forecast-observation:later-provider-update")
        observation_captures = (substituted_observation,) + original.source_captures[1:]
        observation_correction = self.recreate_snapshot(
            original, effective_at=original.effective_at + timedelta(days=1),
            supersedes_snapshot_id=original.research_snapshot_id,
            correction_reason="invalid observation substitution",
            source_captures=observation_captures)
        with self.assertRaises(ContractError):
            self.validate(snapshots=self.graph["snapshots"] + (observation_correction,))
        substituted_timestamp = replace(captured, observed_at=captured.observed_at + timedelta(microseconds=1))
        timestamp_captures = (substituted_timestamp,) + original.source_captures[1:]
        timestamp_correction = self.recreate_snapshot(
            original, effective_at=original.effective_at + timedelta(days=1),
            supersedes_snapshot_id=original.research_snapshot_id,
            correction_reason="invalid timestamp substitution",
            source_captures=timestamp_captures)
        with self.assertRaises(ContractError):
            self.validate(snapshots=self.graph["snapshots"] + (timestamp_correction,))
        observation_id = captured.forecast_observation_id
        observations = tuple(
            replace(item, version_id="later-model-version") if item.observation_id == observation_id else item
            for item in self.graph["forecast_observations"])
        with self.assertRaises(ContractError):
            self.validate(forecast_observations=observations)

    def test_measurement_reuses_evaluation_scores_and_orientation(self):
        measurement = self.graph["measurements"][0]
        evaluations = {item.evaluation_id: item for item in self.graph["forecast_evaluations"]}
        benchmark = evaluations[measurement.benchmark_evaluation_id]
        challenger = evaluations[measurement.challenger_evaluation_id]
        self.assertEqual(measurement.benchmark_brier_score, benchmark.brier_score)
        self.assertEqual(measurement.challenger_log_loss, challenger.log_loss)
        self.assertEqual(measurement.brier_improvement, benchmark.brier_score - challenger.brier_score)
        with localcontext() as context:
            context.prec = 50
            self.assertEqual(measurement.log_loss_improvement, benchmark.log_loss - challenger.log_loss)
        self.assertNotIn("edge_claim_id", measurement.__dataclass_fields__)

    def test_performance_primary_supporting_and_bootstrap_outputs(self):
        performance = self.graph["performances"][-1]
        self.assertEqual(performance.paired_sample_size, 2)
        self.assertEqual(performance.mean_paired_brier_improvement, Decimal("0.0970"))
        self.assertEqual(performance.primary_uncertainty.point_estimate, performance.mean_paired_brier_improvement)
        self.assertEqual(performance.practical_significance_threshold, Decimal("0.005"))
        self.assertEqual(performance.benchmark_calibration.sample_size, performance.paired_sample_size)
        self.assertEqual(performance.challenger_calibration.sample_size, performance.paired_sample_size)
        for forbidden in ("statistically_significant", "practically_significant", "burden_of_proof_met",
                          "edge_supported", "market_edge_exists"):
            self.assertNotIn(forbidden, performance.__dataclass_fields__)

    def test_empty_population_preserves_ten_bins_and_absent_wace(self):
        empty = self.performance(measurements=())
        self.assertEqual(empty.paired_sample_size, 0)
        for calibration in (empty.benchmark_calibration, empty.challenger_calibration):
            self.assertEqual(len(calibration.bins), 10)
            self.assertTrue(all(item.count == 0 and item.mean_probability is None for item in calibration.bins))
            self.assertIsNone(calibration.weighted_absolute_calibration_error)
        self.assertIsNone(empty.primary_uncertainty.point_estimate)

    def test_segmented_domain_uses_preserved_snapshot_classification(self):
        dimension = self.protocol.approved_dimensions[0]
        favorite_domain = next(item for item in self.protocol.research_domains
                               if any(selection.partition_key == "favorite" for selection in item.partition_selections))
        claim = EdgeClaim.create(protocol_id=self.protocol.research_protocol_id,
            challenger_source_reference_id=self.claim.challenger_source_reference_id,
            benchmark_source_reference_id=self.claim.benchmark_source_reference_id,
            research_domain_id=favorite_domain.research_domain_id, provenance=self.graph["provenance"])
        segmented = self.performance(edge_claim=claim, research_domain=favorite_domain)
        self.assertEqual(len(segmented.comparative_measurement_ids), 1)
        self.assertEqual(len(self.graph["performances"][-1].comparative_measurement_ids), 2)
        self.assertTrue(set(segmented.comparative_measurement_ids)
                        < set(self.graph["performances"][-1].comparative_measurement_ids))
        self.assertEqual(dimension.approved_dimension_id,
                         self.graph["measurements"][0].dimension_classifications[0].approved_dimension_id)

    def test_coverage_is_failure_inclusive_and_counts_reconcile(self):
        coverage = self.graph["performances"][-1].coverage
        self.assertEqual(len(coverage.eligible_capture_opportunity_ids), 5)
        self.assertEqual(len(coverage.authoritative_snapshot_ids), 7)
        self.assertEqual(len(coverage.comparative_measurement_ids), 2)
        self.assertEqual(len(coverage.protocol_excluded_opportunity_ids), 2)
        self.assertGreater(len(coverage.benchmark_capture_failure_snapshot_ids), 0)
        self.assertGreater(len(coverage.challenger_capture_failure_snapshot_ids), 0)
        self.assertGreater(len(coverage.unsynchronized_pair_snapshot_ids), 0)

    def test_same_id_different_content_registry_fails_closed(self):
        opportunity = self.graph["opportunities"][0]
        conflicting = object.__new__(ResearchCaptureOpportunity)
        for name in opportunity.__dataclass_fields__:
            object.__setattr__(conflicting, name, getattr(opportunity, name))
        object.__setattr__(conflicting, "protocol_id", "research-protocol:conflict")
        with self.assertRaises(ContractError):
            self.validate(opportunities=self.graph["opportunities"] + (conflicting,))

    def test_population_eligibility_is_boundary_scoped_and_rule_derived(self):
        after = tuple(item for item in self.graph["eligibility_results"]
                      if item.analysis_boundary == self.graph["after"])
        opportunities = {item.research_capture_opportunity_id: item for item in self.graph["opportunities"]}
        by_schedule = {opportunities[item.research_capture_opportunity_id].schedule_observation_id: item for item in after}
        self.assertNotIn("mlb-stats-api:g:schedule", by_schedule)
        self.assertEqual(by_schedule["mlb-stats-api:f:schedule"].disposition,
                         PopulationEligibilityDisposition.EXCLUDED)
        self.assertIn("postseason-excluded", by_schedule["mlb-stats-api:f:schedule"].reason_codes)
        self.assertIn("superseded-schedule-opportunity", by_schedule["mlb-stats-api:c:schedule"].reason_codes)
        self.assertEqual(by_schedule["mlb-stats-api:d:schedule"].disposition,
                         PopulationEligibilityDisposition.ELIGIBLE)

    def test_omitted_applicable_eligibility_decision_fails_factory_and_graph(self):
        result = next(item for item in self.graph["eligibility_results"]
                      if item.analysis_boundary == self.graph["after"]
                      and item.disposition is PopulationEligibilityDisposition.ELIGIBLE)
        contexts = tuple(item for item in self.graph["eligibility_contexts"]
                         if item.research_capture_opportunity_id != result.research_capture_opportunity_id)
        results = tuple(item for item in self.graph["eligibility_results"]
                        if item.research_capture_opportunity_id != result.research_capture_opportunity_id)
        for context_values, result_values in (
                (contexts, self.graph["eligibility_results"]),
                (self.graph["eligibility_contexts"], results),
                (contexts, results)):
            with self.assertRaises(ContractError):
                self.performance(eligibility_contexts=context_values,
                                 eligibility_results=result_values)
        with self.assertRaises(ContractError):
            self.validate(eligibility_contexts=contexts, eligibility_results=results)
        context = next(item for item in self.graph["eligibility_contexts"]
                       if item.research_capture_opportunity_id == result.research_capture_opportunity_id
                       and item.analysis_boundary == self.graph["after"])
        with self.assertRaises(ContractError):
            self.performance(eligibility_contexts=self.graph["eligibility_contexts"] + (context,))
        with self.assertRaises(ContractError):
            self.performance(eligibility_results=self.graph["eligibility_results"] + (result,))

    def test_graph_rejects_identical_and_reconstructed_eligibility_duplicates(self):
        context = self.graph["eligibility_contexts"][0]
        result = self.graph["eligibility_results"][0]
        reconstructed_context = type(context).from_json(context.to_json())
        reconstructed_result = type(result).from_json(result.to_json())
        for context_duplicate in (context, reconstructed_context):
            with self.assertRaises(ContractError):
                self.validate(eligibility_contexts=self.graph["eligibility_contexts"] + (context_duplicate,))
        for result_duplicate in (result, reconstructed_result):
            with self.assertRaises(ContractError):
                self.validate(eligibility_results=self.graph["eligibility_results"] + (result_duplicate,))
        conflicting_context = object.__new__(type(context))
        for name in context.__dataclass_fields__:
            object.__setattr__(conflicting_context, name, getattr(context, name))
        object.__setattr__(conflicting_context, "protocol_id", "research-protocol:conflict")
        conflicting_result = object.__new__(type(result))
        for name in result.__dataclass_fields__:
            object.__setattr__(conflicting_result, name, getattr(result, name))
        object.__setattr__(conflicting_result, "protocol_id", "research-protocol:conflict")
        with self.assertRaises(ContractError):
            self.validate(eligibility_contexts=self.graph["eligibility_contexts"] + (conflicting_context,))
        with self.assertRaises(ContractError):
            self.validate(eligibility_results=self.graph["eligibility_results"] + (conflicting_result,))

    def test_future_opportunity_requires_no_early_eligibility_decision(self):
        before = self.graph["performances"][0]
        future = next(item for item in self.graph["opportunities"]
                      if item.schedule_observation_id == "mlb-stats-api:g:schedule")
        self.assertNotIn(future.research_capture_opportunity_id,
                         before.coverage.eligible_capture_opportunity_ids)

    def test_synchronization_is_derived_from_capture_timestamps_and_validity(self):
        benchmark_id = self.protocol.market_benchmark.probability_source_reference_id
        challenger_id = self.protocol.alternative_sources[0].probability_source_reference_id
        at = self.graph["after"]
        benchmark = SourceCapture(benchmark_id, SourceCaptureDisposition.CAPTURED_VALID, "forecast:b", at)
        exact = SourceCapture(challenger_id, SourceCaptureDisposition.CAPTURED_VALID, "forecast:c", at + timedelta(seconds=600))
        pair = create_pairwise_synchronization(benchmark_capture=benchmark, challenger_capture=exact,
                                               synchronization_rule=self.protocol.synchronization_rule)
        self.assertTrue(pair.synchronized)
        self.assertEqual(pair.separation_microseconds, 600_000_000)
        fractional_inside = SourceCapture(challenger_id, SourceCaptureDisposition.CAPTURED_VALID,
                                          "forecast:c", at + timedelta(seconds=599, microseconds=999999))
        self.assertTrue(create_pairwise_synchronization(
            benchmark_capture=benchmark, challenger_capture=fractional_inside,
            synchronization_rule=self.protocol.synchronization_rule).synchronized)
        outside = SourceCapture(challenger_id, SourceCaptureDisposition.CAPTURED_VALID,
                                "forecast:c", at + timedelta(seconds=600, microseconds=1))
        self.assertFalse(create_pairwise_synchronization(
            benchmark_capture=benchmark, challenger_capture=outside,
            synchronization_rule=self.protocol.synchronization_rule).synchronized)
        invalid = SourceCapture(challenger_id, SourceCaptureDisposition.CAPTURED_INVALID, "forecast:c", at,
                                reasons=("invalid",))
        self.assertFalse(create_pairwise_synchronization(
            benchmark_capture=benchmark, challenger_capture=invalid,
            synchronization_rule=self.protocol.synchronization_rule).synchronized)

    def test_capture_tolerance_microseconds_through_public_graph_validation(self):
        import forecast_comparative_research as module
        snapshot = next(item for item in self.graph["snapshots"]
                        if item.canonical_event_id == "canonical-event:h")
        benchmark_id = self.protocol.market_benchmark.probability_source_reference_id
        threshold = module._parameter(self.protocol.capture_tolerance_rule, "seconds")

        def graph_at(deviation, disposition=SourceCaptureDisposition.CAPTURED_VALID, reasons=()):
            captures = []
            observation_id = None
            observed_at = snapshot.target_capture_at + deviation
            for capture in snapshot.source_captures:
                if capture.probability_source_reference_id == benchmark_id:
                    observation_id = capture.forecast_observation_id
                    captures.append(SourceCapture(benchmark_id, disposition, observation_id,
                                                  observed_at, reasons=reasons))
                else:
                    captures.append(capture)
            capture_map = {item.probability_source_reference_id: item for item in captures}
            pairs = tuple(create_pairwise_synchronization(
                benchmark_capture=capture_map[benchmark_id],
                challenger_capture=capture_map[item.challenger_source_reference_id],
                synchronization_rule=self.protocol.synchronization_rule)
                for item in snapshot.pairwise_synchronization)
            changed_snapshot = self.recreate_snapshot(
                snapshot, source_captures=tuple(captures), pairwise_synchronization=pairs)
            changed_snapshots = tuple(changed_snapshot if item == snapshot else item
                                      for item in self.graph["snapshots"])
            changed_observations = tuple(
                replace(item, collected_at=observed_at,
                        provenance=replace(item.provenance, collected_at=observed_at))
                if item.observation_id == observation_id else item
                for item in self.graph["forecast_observations"])
            return changed_snapshots, changed_observations

        for deviation in (timedelta(seconds=threshold),
                          timedelta(seconds=threshold - 1, microseconds=500000)):
            snapshots, observations = graph_at(deviation)
            self.validate(snapshots=snapshots, forecast_observations=observations, performances=())
        snapshots, observations = graph_at(timedelta(seconds=threshold, microseconds=1))
        with self.assertRaises(ContractError):
            self.validate(snapshots=snapshots, forecast_observations=observations, performances=())

    def test_eligibility_provenance_validation_and_coverage_lineage_are_material(self):
        result = next(item for item in self.graph["eligibility_results"]
                      if item.analysis_boundary == self.graph["after"]
                      and item.disposition is PopulationEligibilityDisposition.EXCLUDED)
        coverage = self.graph["performances"][-1].coverage
        self.assertIn(result.population_eligibility_result_id,
                      coverage.applicable_population_eligibility_result_ids)
        self.assertIn(result.population_eligibility_result_id,
                      coverage.excluded_population_eligibility_result_ids)
        later = replace(result.provenance, generated_at=result.provenance.generated_at + timedelta(days=1))
        self.assertEqual(replace(result, provenance=later).population_eligibility_result_id,
                         result.population_eligibility_result_id)
        invalid = PopulationEligibilityResult.create(
            research_capture_opportunity_id=result.research_capture_opportunity_id,
            research_event_eligibility_context_id=result.research_event_eligibility_context_id,
            protocol_id=result.protocol_id, research_population_id=result.research_population_id,
            analysis_boundary=result.analysis_boundary, disposition=result.disposition,
            governing_rule_specification_ids=result.governing_rule_specification_ids,
            reason_codes=result.reason_codes,
            validation_status=PopulationEligibilityValidationStatus.INVALID,
            validation_reasons=("synthetic invalid derivation",), provenance=result.provenance)
        self.assertNotEqual(invalid.population_eligibility_result_id,
                            result.population_eligibility_result_id)
        changed_coverage = replace(
            coverage,
            applicable_population_eligibility_result_ids=tuple(
                invalid.population_eligibility_result_id if item == result.population_eligibility_result_id else item
                for item in coverage.applicable_population_eligibility_result_ids),
            excluded_population_eligibility_result_ids=tuple(
                invalid.population_eligibility_result_id if item == result.population_eligibility_result_id else item
                for item in coverage.excluded_population_eligibility_result_ids),
        )
        with self.assertRaises(ContractError):
            replace(self.graph["performances"][-1], coverage=changed_coverage)
        with self.assertRaises(ContractError):
            self.performance(eligibility_results=tuple(
                invalid if item == result else item for item in self.graph["eligibility_results"]))

        alternate_reason = PopulationEligibilityResult.create(
            research_capture_opportunity_id=result.research_capture_opportunity_id,
            research_event_eligibility_context_id=result.research_event_eligibility_context_id,
            protocol_id=result.protocol_id, research_population_id=result.research_population_id,
            analysis_boundary=result.analysis_boundary, disposition=result.disposition,
            governing_rule_specification_ids=result.governing_rule_specification_ids,
            reason_codes=result.reason_codes + ("event-status-not-eligible",),
            validation_status=PopulationEligibilityValidationStatus.VALID,
            validation_reasons=(), provenance=result.provenance)
        self.assertNotEqual(alternate_reason.population_eligibility_result_id,
                            result.population_eligibility_result_id)
        reason_coverage = replace(
            coverage,
            applicable_population_eligibility_result_ids=tuple(
                alternate_reason.population_eligibility_result_id
                if item == result.population_eligibility_result_id else item
                for item in coverage.applicable_population_eligibility_result_ids),
            excluded_population_eligibility_result_ids=tuple(
                alternate_reason.population_eligibility_result_id
                if item == result.population_eligibility_result_id else item
                for item in coverage.excluded_population_eligibility_result_ids))
        reason_performance = self.recreate_performance(
            self.graph["performances"][-1], coverage=reason_coverage)
        self.assertNotEqual(reason_performance.comparative_performance_id,
                            self.graph["performances"][-1].comparative_performance_id)
        with self.assertRaises(ContractError):
            self.validate(
                eligibility_results=tuple(alternate_reason if item == result else item
                                          for item in self.graph["eligibility_results"]),
                performances=(reason_performance,))

    def test_coverage_eligibility_references_fail_closed_through_graph_validation(self):
        base = self.graph["performances"][-1]
        coverage = base.coverage
        eligible_id = coverage.eligible_population_eligibility_result_ids[0]
        excluded_id = coverage.excluded_population_eligibility_result_ids[0]

        unknown = "population-eligibility-result:" + "0" * 64
        unknown_coverage = replace(
            coverage,
            applicable_population_eligibility_result_ids=tuple(
                unknown if item == excluded_id else item
                for item in coverage.applicable_population_eligibility_result_ids),
            excluded_population_eligibility_result_ids=tuple(
                unknown if item == excluded_id else item
                for item in coverage.excluded_population_eligibility_result_ids))
        with self.assertRaises(ContractError):
            self.validate(performances=(self.recreate_performance(base, coverage=unknown_coverage),))

        wrong_category = replace(
            coverage,
            eligible_population_eligibility_result_ids=tuple(
                excluded_id if item == eligible_id else item
                for item in coverage.eligible_population_eligibility_result_ids),
            excluded_population_eligibility_result_ids=tuple(
                eligible_id if item == excluded_id else item
                for item in coverage.excluded_population_eligibility_result_ids))
        with self.assertRaises(ContractError):
            self.validate(performances=(self.recreate_performance(base, coverage=wrong_category),))

        result_map = {item.population_eligibility_result_id: item
                      for item in self.graph["eligibility_results"]}
        source = result_map[excluded_id]
        other_opportunity = next(item for item in self.graph["opportunities"]
                                 if item.research_capture_opportunity_id != source.research_capture_opportunity_id)
        variants = (
            PopulationEligibilityResult.create(
                research_capture_opportunity_id=other_opportunity.research_capture_opportunity_id,
                research_event_eligibility_context_id=source.research_event_eligibility_context_id,
                protocol_id=source.protocol_id, research_population_id=source.research_population_id,
                analysis_boundary=source.analysis_boundary, disposition=source.disposition,
                governing_rule_specification_ids=source.governing_rule_specification_ids,
                reason_codes=source.reason_codes,
                validation_status=source.validation_status, validation_reasons=source.validation_reasons,
                provenance=source.provenance),
            PopulationEligibilityResult.create(
                research_capture_opportunity_id=source.research_capture_opportunity_id,
                research_event_eligibility_context_id=source.research_event_eligibility_context_id,
                protocol_id="research-protocol:other", research_population_id=source.research_population_id,
                analysis_boundary=source.analysis_boundary, disposition=source.disposition,
                governing_rule_specification_ids=source.governing_rule_specification_ids,
                reason_codes=source.reason_codes,
                validation_status=source.validation_status, validation_reasons=source.validation_reasons,
                provenance=source.provenance),
            PopulationEligibilityResult.create(
                research_capture_opportunity_id=source.research_capture_opportunity_id,
                research_event_eligibility_context_id=source.research_event_eligibility_context_id,
                protocol_id=source.protocol_id, research_population_id=source.research_population_id,
                analysis_boundary=source.analysis_boundary - timedelta(microseconds=1),
                disposition=source.disposition,
                governing_rule_specification_ids=source.governing_rule_specification_ids,
                reason_codes=source.reason_codes,
                validation_status=source.validation_status, validation_reasons=source.validation_reasons,
                provenance=source.provenance),
        )
        for variant in variants:
            variant_coverage = replace(
                coverage,
                applicable_population_eligibility_result_ids=tuple(
                    variant.population_eligibility_result_id if item == excluded_id else item
                    for item in coverage.applicable_population_eligibility_result_ids),
                excluded_population_eligibility_result_ids=tuple(
                    variant.population_eligibility_result_id if item == excluded_id else item
                    for item in coverage.excluded_population_eligibility_result_ids))
            variant_results = tuple(variant if item == source else item
                                    for item in self.graph["eligibility_results"])
            with self.assertRaises(ContractError):
                self.validate(eligibility_results=variant_results,
                              performances=(self.recreate_performance(base, coverage=variant_coverage),))

    def test_invalid_snapshot_and_wrong_outcome_provider_fail_measurement(self):
        measurement = self.graph["measurements"][0]
        snapshots = {item.research_snapshot_id: item for item in self.graph["snapshots"]}
        evaluations = {item.evaluation_id: item for item in self.graph["forecast_evaluations"]}
        outcomes = {item.observation_id: item for item in self.graph["outcome_observations"]}
        snapshot = snapshots[measurement.research_snapshot_id]
        invalid = self.recreate_snapshot(snapshot, validation_status=SnapshotValidationStatus.INVALID,
                                         validation_reasons=("structurally invalid",))
        kwargs = dict(protocol=self.protocol, snapshot=invalid,
                      benchmark_evaluation=evaluations[measurement.benchmark_evaluation_id],
                      challenger_evaluation=evaluations[measurement.challenger_evaluation_id],
                      outcome=outcomes[measurement.outcome_observation_id],
                      effective_at=measurement.effective_at, provenance=measurement.provenance)
        with self.assertRaises(ContractError):
            create_comparative_measurement(**kwargs)
        kwargs["snapshot"] = snapshot
        kwargs["outcome"] = replace(kwargs["outcome"], authoritative_provider_id="wrong-provider")
        with self.assertRaises(ContractError):
            create_comparative_measurement(**kwargs)

    def test_complete_dimensions_and_forecast_registry_fail_closed(self):
        base = next(item for item in self.graph["snapshots"] if item.supersedes_snapshot_id is None)
        missing_dimension = self.recreate_snapshot(base, dimension_classifications=())
        snapshots = tuple(missing_dimension if item == base else item for item in self.graph["snapshots"])
        with self.assertRaises(ContractError):
            self.validate(snapshots=snapshots)
        with self.assertRaises(ContractError):
            self.validate(forecast_observations=self.graph["forecast_observations"][1:])

    def test_decimal_outputs_ignore_ambient_context(self):
        original = getcontext().copy()
        try:
            getcontext().prec = 6
            getcontext().rounding = "ROUND_DOWN"
            low = self.performance()
            getcontext().prec = 28
            getcontext().rounding = "ROUND_HALF_EVEN"
            normal = self.performance()
            self.assertEqual(low, normal)
        finally:
            getcontext().prec = original.prec
            getcontext().rounding = original.rounding

    def test_extended_log_loss_event_and_aggregate_semantics_and_serialization(self):
        base = self.graph["measurements"][0]
        snapshots = {item.research_snapshot_id: item for item in self.graph["snapshots"]}
        evaluations = {item.evaluation_id: item for item in self.graph["forecast_evaluations"]}
        outcomes = {item.observation_id: item for item in self.graph["outcome_observations"]}
        benchmark = evaluations[base.benchmark_evaluation_id]
        challenger = evaluations[base.challenger_evaluation_id]
        common = dict(protocol=self.protocol, snapshot=snapshots[base.research_snapshot_id],
                      outcome=outcomes[base.outcome_observation_id], effective_at=base.effective_at,
                      provenance=base.provenance)
        plus = create_comparative_measurement(
            benchmark_evaluation=replace(benchmark, log_loss=Decimal("Infinity")),
            challenger_evaluation=challenger, **common)
        minus = create_comparative_measurement(
            benchmark_evaluation=benchmark,
            challenger_evaluation=replace(challenger, log_loss=Decimal("Infinity")), **common)
        absent = create_comparative_measurement(
            benchmark_evaluation=replace(benchmark, log_loss=Decimal("Infinity")),
            challenger_evaluation=replace(challenger, log_loss=Decimal("Infinity")), **common)
        self.assertEqual(plus.log_loss_improvement, Decimal("Infinity"))
        self.assertEqual(minus.log_loss_improvement, Decimal("-Infinity"))
        self.assertIsNone(absent.log_loss_improvement)
        self.assertEqual(type(minus).from_json(minus.to_json()), minus)
        self.assertIn("negative-infinity", minus.to_json())
        import forecast_comparative_research as module
        self.assertEqual(module._mean((Decimal("1"), Decimal("Infinity"))), Decimal("Infinity"))
        self.assertEqual(module._mean_log_loss_improvement((Decimal("Infinity"), Decimal("2"))),
                         Decimal("Infinity"))
        self.assertEqual(module._mean_log_loss_improvement((Decimal("-Infinity"), Decimal("-2"))),
                         Decimal("-Infinity"))
        self.assertIsNone(module._mean_log_loss_improvement((None, Decimal("1"))))
        self.assertIsNone(module._mean_log_loss_improvement(
            (Decimal("Infinity"), Decimal("-Infinity"))))
        with self.assertRaises(ContractError):
            replace(benchmark, log_loss=Decimal("-Infinity"))
        with self.assertRaises(ContractError):
            replace(benchmark, log_loss=Decimal("NaN"))

    def test_calibration_all_boundaries_and_tamper_detection(self):
        import forecast_comparative_research as module
        rule = next(item for item in self.protocol.supporting_measure_rules
                    if item.rule_id == "calibration-safeguard")
        values = tuple(SimpleNamespace(benchmark_probability=value,
                                       challenger_probability=value, realized_outcome=index % 2)
                       for index, value in enumerate(CALIBRATION_BOUNDARIES))
        result = module._calibration(values, "benchmark", rule)
        self.assertEqual(tuple(item.count for item in result.bins), (1,) * 9 + (2,))
        with self.assertRaises(ContractError):
            replace(result.bins[0], calibration_gap=Decimal("0.1"))
        with self.assertRaises(ContractError):
            replace(result, weighted_absolute_calibration_error=Decimal("0"))
        altered_bin = replace(result.bins[0], upper_bound=Decimal("0.11"))
        with self.assertRaises(ContractError):
            replace(result, bins=(altered_bin,) + result.bins[1:])

    def test_bootstrap_is_nontrivial_and_materially_sensitive(self):
        performance = self.performance()
        self.assertNotEqual(performance.primary_uncertainty.lower_bound,
                            performance.primary_uncertainty.upper_bound)
        selected_ids = set(performance.comparative_measurement_ids)
        base = next(item for item in self.graph["measurements"]
                    if item.comparative_measurement_id in selected_ids)
        snapshots = {item.research_snapshot_id: item for item in self.graph["snapshots"]}
        evaluations = {item.evaluation_id: item for item in self.graph["forecast_evaluations"]}
        outcomes = {item.observation_id: item for item in self.graph["outcome_observations"]}
        changed = create_comparative_measurement(
            protocol=self.protocol, snapshot=snapshots[base.research_snapshot_id],
            benchmark_evaluation=replace(evaluations[base.benchmark_evaluation_id], brier_score=Decimal("0.5")),
            challenger_evaluation=evaluations[base.challenger_evaluation_id],
            outcome=outcomes[base.outcome_observation_id], effective_at=base.effective_at,
            provenance=base.provenance)
        changed_performance = self.performance(
            measurements=tuple(changed if item == base else item for item in self.graph["measurements"]))
        self.assertNotEqual(changed_performance.primary_uncertainty,
                            performance.primary_uncertainty)

    def test_no_pr15_or_pr16_contract_is_implemented(self):
        import forecast_comparative_research as module
        self.assertFalse(hasattr(module, "ComparativePerformanceReport"))
        self.assertFalse(hasattr(module, "CurrentScientificApplicability"))
        self.assertFalse(hasattr(module, "PolicyRecommendation"))


if __name__ == "__main__":
    unittest.main()
