from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext, localcontext
import inspect
from pathlib import Path
import unittest

from event_contracts import ContractError
from forecast_comparative_reporting import (
    ComparativePerformanceReport, TimeBoundedComparativePerformance,
    _classify_drift,
    create_comparative_drift_analysis, create_comparative_performance_report,
    create_time_bounded_comparative_performance, replay_historical_comparative_performance,
    validate_comparative_reporting_contracts,
)
from forecast_research_contracts import (
    DriftDisposition, DriftSurveillance, DriftSurveillanceReference, ResearchContractProvenance,
    ProtocolClaimSet, ResearchProtocol, ResearchReview, ResearchReviewConclusion, ReviewObligationCoverage,
    ReviewObligationKind, ReviewObligationReference, RuleParameter, RulePurpose,
    ScheduledReviewBoundaryReference, VersionedRuleSpecification,
    replay_protocol_claim_set, scheduled_review_boundary_applies,
)
from forecast_comparative_research import create_comparative_performance
from inspect_forecast_comparative_reporting import load_fixture, run
from inspect_forecast_comparative_research import load_fixture as load_pr14_fixture
from outcome_contracts import OutcomeHistory


FIXTURE = Path(__file__).parent / "fixtures" / "forecast_comparative_reporting_cases.json"


class _Raises:
    def __init__(self, error):
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type is None:
            raise AssertionError(f"{self.error.__name__} was not raised")
        return issubclass(error_type, self.error)


class _PytestCompatibility:
    @staticmethod
    def fixture(**_kwargs):
        return lambda function: function

    raises = _Raises


pytest = _PytestCompatibility()


@pytest.fixture(scope="module")
def graph():
    return load_fixture(FIXTURE)


def _parts(graph, index=0):
    protocol = graph["protocols"][0]
    domain_by_id = {item.research_domain_id: item for item in protocol.research_domains}
    challenger_order = {item.probability_source_reference_id: position
                        for position, item in enumerate(protocol.alternative_sources)}
    ordered = sorted(graph["claims"], key=lambda item: (
        bool(domain_by_id[item.research_domain_id].partition_selections),
        challenger_order[item.challenger_source_reference_id]))
    claim = ordered[index]
    current = next(item for item in graph["bounded_performances"] if item.edge_claim_id == claim.edge_claim_id)
    historical = next(item for item in graph["performances"]
                      if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == graph["before"])
    cumulative = next(item for item in graph["performances"]
                      if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == graph["after"])
    drift = next(item for item in graph["drift_analyses"] if item.edge_claim_id == claim.edge_claim_id)
    return protocol, claim, historical, current, cumulative, drift


def _validate(graph, **extra):
    values = dict(
        protocols=graph["protocols"], claims=graph["claims"],
        protocol_claim_sets=graph["protocol_claim_sets"],
        cumulative_performances=graph["performances"],
        bounded_performances=graph["bounded_performances"],
        drift_analyses=graph["drift_analyses"], reports=graph["reports"],
        opportunities=graph["opportunities"], eligibility_contexts=graph["eligibility_contexts"],
        eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
        measurements=graph["measurements"], outcome_histories=graph["outcome_histories"])
    values.update(extra)
    validate_comparative_reporting_contracts(**values)


def _recreate_bounded(graph, item, **changes):
    protocol = graph["protocols"][0]
    claim = next(value for value in graph["claims"] if value.edge_claim_id == item.edge_claim_id)
    domain = next(value for value in protocol.research_domains
                  if value.research_domain_id == item.research_domain_id)
    values = dict(
        protocol=protocol, edge_claim=claim, research_domain=domain,
        analysis_boundary=item.analysis_boundary, opportunities=graph["opportunities"],
        eligibility_contexts=graph["eligibility_contexts"],
        eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
        measurements=graph["measurements"], outcome_histories=graph["outcome_histories"],
        provenance=item.provenance, limitations=item.limitations)
    values.update(changes)
    return create_time_bounded_comparative_performance(**values)


def _additional_history(graph, *, provider_id, observation_id="foreign-schedule-observation"):
    source = graph["outcome_histories"][0].observations[0]
    canonical_event_id = f"additional-event:{provider_id}"
    observation = replace(
        source, observation_id=observation_id, canonical_event_id=canonical_event_id,
        authoritative_provider_id=provider_id,
        provider_event_id=f"additional-provider-event:{provider_id}")
    return OutcomeHistory(canonical_event_id, provider_id, (observation,))


def _clone_protocol(protocol, *, surveillance_window_rules=None):
    return ResearchProtocol.create(
        protocol_version=protocol.protocol_version, effective_at=protocol.effective_at,
        scientific_question=protocol.scientific_question, research_population=protocol.research_population,
        market_benchmark=protocol.market_benchmark, alternative_sources=protocol.alternative_sources,
        approved_dimensions=protocol.approved_dimensions, research_domains=protocol.research_domains,
        snapshot_timing_rule=protocol.snapshot_timing_rule, capture_tolerance_rule=protocol.capture_tolerance_rule,
        synchronization_rule=protocol.synchronization_rule, event_compatibility_rule=protocol.event_compatibility_rule,
        outcome_resolution_rule=protocol.outcome_resolution_rule, primary_measure_rule=protocol.primary_measure_rule,
        supporting_measure_rules=protocol.supporting_measure_rules,
        statistical_method_rule=protocol.statistical_method_rule,
        practical_significance_rule=protocol.practical_significance_rule,
        burden_of_proof_rule=protocol.burden_of_proof_rule,
        surveillance_window_rules=(protocol.surveillance_window_rules if surveillance_window_rules is None
                                   else surveillance_window_rules),
        drift_classification_rule=protocol.drift_classification_rule,
        drift_material_event_rule=protocol.drift_material_event_rule,
        scheduled_review_boundaries=protocol.scheduled_review_boundaries,
        limitations=protocol.limitations, provenance=protocol.provenance)


def test_inspector_is_deterministic():
    assert run(FIXTURE) == run(FIXTURE)


def test_fixture_covers_multiple_challengers(graph):
    assert len(graph["claims"]) == len(graph["reports"][0].claim_findings)
    assert len({item.challenger_source_reference_id for item in graph["claims"]}) == 2
    assert {bool(item.partition_selections) for item in graph["protocols"][0].research_domains} == {False, True}


def test_time_bounded_round_trip(graph):
    item = graph["bounded_performances"][0]
    assert TimeBoundedComparativePerformance.from_json(item.to_json()) == item


def test_report_round_trip(graph):
    item = graph["reports"][0]
    assert ComparativePerformanceReport.from_json(item.to_json()) == item


def test_protocol_claim_set_round_trip_and_canonical_identity(graph):
    item = graph["protocol_claim_sets"][0]
    assert ProtocolClaimSet.from_json(item.to_json()) == item
    recreated = ProtocolClaimSet.create(
        protocol_id=item.protocol_id, effective_at=item.effective_at,
        edge_claim_ids=reversed(item.edge_claim_ids), provenance=item.provenance)
    assert recreated == item
    for memberships in ((), (item.edge_claim_ids[0], item.edge_claim_ids[0])):
        with pytest.raises(ContractError):
            ProtocolClaimSet.create(
                protocol_id=item.protocol_id, effective_at=item.effective_at,
                edge_claim_ids=memberships, provenance=item.provenance)
    assert replay_protocol_claim_set(
        protocol_id=item.protocol_id,
        analysis_boundary=item.effective_at - timedelta(microseconds=1),
        protocol_claim_sets=(item,)) is None


def test_protocol_claim_set_replay_and_additive_lineage(graph):
    initial = ProtocolClaimSet.create(
        protocol_id=graph["protocols"][0].research_protocol_id,
        effective_at=graph["before"] - timedelta(days=1),
        edge_claim_ids=(graph["claims"][0].edge_claim_id,), provenance=graph["provenance"])
    successor = ProtocolClaimSet.create(
        protocol_id=initial.protocol_id, effective_at=graph["before"],
        edge_claim_ids=(item.edge_claim_id for item in graph["claims"]),
        predecessor_protocol_claim_set_id=initial.protocol_claim_set_id,
        provenance=graph["provenance"])
    lineage = (successor, initial)
    assert replay_protocol_claim_set(
        protocol_id=initial.protocol_id, analysis_boundary=initial.effective_at,
        protocol_claim_sets=lineage) == initial
    assert replay_protocol_claim_set(
        protocol_id=initial.protocol_id, analysis_boundary=successor.effective_at,
        protocol_claim_sets=lineage) == successor
    future_branch = ProtocolClaimSet.create(
        protocol_id=initial.protocol_id, effective_at=successor.effective_at + timedelta(days=1),
        edge_claim_ids=successor.edge_claim_ids,
        predecessor_protocol_claim_set_id=initial.protocol_claim_set_id,
        provenance=graph["provenance"])
    assert replay_protocol_claim_set(
        protocol_id=initial.protocol_id, analysis_boundary=initial.effective_at,
        protocol_claim_sets=lineage + (future_branch,)) == initial


def test_protocol_claim_set_lineage_failures_are_closed(graph):
    protocol_id = graph["protocols"][0].research_protocol_id
    claim_ids = tuple(item.edge_claim_id for item in graph["claims"])
    initial = ProtocolClaimSet.create(
        protocol_id=protocol_id, effective_at=graph["before"] - timedelta(days=2),
        edge_claim_ids=claim_ids[:1], provenance=graph["provenance"])
    invalid_successors = (
        ProtocolClaimSet.create(
            protocol_id=protocol_id, effective_at=graph["before"] - timedelta(days=1),
            edge_claim_ids=claim_ids[:1], predecessor_protocol_claim_set_id=initial.protocol_claim_set_id,
            provenance=graph["provenance"]),
        ProtocolClaimSet.create(
            protocol_id=protocol_id, effective_at=graph["before"] - timedelta(days=1),
            edge_claim_ids=claim_ids, predecessor_protocol_claim_set_id="protocol-claim-set:unknown",
            provenance=graph["provenance"]),
    )
    for successor in invalid_successors:
        with pytest.raises(ContractError):
            replay_protocol_claim_set(
                protocol_id=protocol_id, analysis_boundary=graph["after"],
                protocol_claim_sets=(initial, successor))
    first_branch = ProtocolClaimSet.create(
        protocol_id=protocol_id, effective_at=graph["before"] - timedelta(days=1),
        edge_claim_ids=claim_ids, predecessor_protocol_claim_set_id=initial.protocol_claim_set_id,
        provenance=graph["provenance"])
    second_branch = ProtocolClaimSet.create(
        protocol_id=protocol_id, effective_at=graph["before"], edge_claim_ids=claim_ids,
        predecessor_protocol_claim_set_id=initial.protocol_claim_set_id, provenance=graph["provenance"])
    with pytest.raises(ContractError):
        replay_protocol_claim_set(
            protocol_id=protocol_id, analysis_boundary=graph["after"],
            protocol_claim_sets=(initial, first_branch, second_branch))


def test_scheduled_review_boundary_respects_claim_admission(graph):
    protocol = graph["protocols"][0]
    boundary = protocol.scheduled_review_boundaries[0]
    claim = graph["claims"][0]
    admitted_later = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=boundary.required_analysis_boundary_at + timedelta(microseconds=1),
        edge_claim_ids=(claim.edge_claim_id,), provenance=graph["provenance"])
    assert not scheduled_review_boundary_applies(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        boundary=boundary, protocol_claim_sets=(admitted_later,))


def test_window_is_open_left_closed_right(graph):
    _, _, _, current, _, _ = _parts(graph)
    schedules = {observation.observation_id: observation
                 for history in graph["outcome_histories"] for observation in history.observations}
    eligible = set(current.coverage.eligible_capture_opportunity_ids)
    by_start = {schedules[item.schedule_observation_id].scheduled_start: item.research_capture_opportunity_id
                for item in graph["opportunities"]}
    assert by_start[current.window_start_at] not in eligible
    assert by_start[current.window_end_at] in eligible


def test_window_microsecond_boundaries(graph):
    _, _, _, current, _, _ = _parts(graph)
    schedules = {observation.observation_id: observation
                 for history in graph["outcome_histories"] for observation in history.observations}
    eligible = set(current.coverage.eligible_capture_opportunity_ids)
    by_start = {schedules[item.schedule_observation_id].scheduled_start: item.research_capture_opportunity_id
                for item in graph["opportunities"]}
    assert by_start[current.window_start_at + timedelta(microseconds=1)] in eligible
    assert by_start[current.analysis_boundary + timedelta(microseconds=1)] not in eligible


def test_window_membership_ignores_measurement_effective_time(graph):
    _, _, _, current, _, _ = _parts(graph)
    assert all(item.effective_at <= current.analysis_boundary for item in graph["measurements"]
               if item.comparative_measurement_id in current.comparative_measurement_ids)
    assert current.paired_sample_size == 2


def test_bounded_coverage_keeps_zero_capture_opportunity(graph):
    _, _, _, current, _, _ = _parts(graph)
    assert current.coverage.benchmark_capture_failure_snapshot_ids
    assert len(current.coverage.eligible_capture_opportunity_ids) > current.paired_sample_size


def test_valid_empty_window_is_an_artifact(graph):
    current = next(item for item in graph["bounded_performances"] if item.paired_sample_size == 0)
    assert current.paired_sample_size == 0
    assert current.mean_paired_brier_improvement is None
    assert current.primary_uncertainty.lower_bound is None


def test_historical_replay_at_window_start(graph):
    protocol, claim, historical, current, _, _ = _parts(graph)
    broad = next(item for item in protocol.research_domains if not item.partition_selections)
    replay = replay_historical_comparative_performance(
        window_start_at=current.window_start_at, protocol=protocol, edge_claim=claim,
        research_domain=broad, opportunities=graph["opportunities"],
        eligibility_contexts=graph["eligibility_contexts"], eligibility_results=graph["eligibility_results"],
        snapshots=graph["snapshots"], measurements=graph["measurements"],
        outcome_histories=graph["outcome_histories"], provenance=graph["provenance"],
        limitations=historical.limitations)
    assert replay == historical


def test_drift_sign_is_historical_minus_current(graph):
    _, _, historical, current, _, drift = _parts(graph)
    assert drift.measured_deterioration == (
        historical.mean_paired_brier_improvement - current.mean_paired_brier_improvement)


def test_two_population_bootstrap_is_deterministic(graph):
    protocol, _, historical, current, _, drift = _parts(graph)
    recreated = create_comparative_drift_analysis(
        protocol=protocol, historical=historical, current=current,
        measurements=graph["measurements"], provenance=graph["provenance"],
        limitations=drift.limitations)
    assert recreated == drift


def test_empty_drift_is_valid_insufficient_evidence(graph):
    drift = graph["drift_analyses"][1]
    assert drift.measured_deterioration is None
    assert drift.disposition.value == "insufficient-evidence-to-determine-drift"


def test_report_reference_is_exact_projection(graph):
    report = graph["reports"][0]
    reference = report.to_reference()
    assert reference.report_id == report.comparative_performance_report_id
    assert reference.contract_version == report.contract_version
    assert reference.edge_claim_ids == tuple(item.edge_claim_id for item in report.claim_findings)


def test_generated_at_is_nonmaterial(graph):
    report = graph["reports"][0]
    provenance = replace(report.provenance, generated_at=report.analysis_boundary + timedelta(days=1))
    changed = replace(report, provenance=provenance)
    assert changed.comparative_performance_report_id == report.comparative_performance_report_id
    assert changed.input_digest == report.input_digest


def test_report_rejects_claim_subset(graph):
    protocol = graph["protocols"][0]
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=protocol, claims=graph["claims"],
            protocol_claim_sets=graph["protocol_claim_sets"],
            cumulative_performances=graph["performances"][:1],
            bounded_performances=graph["bounded_performances"],
            drift_analyses=graph["drift_analyses"], provenance=graph["provenance"],
            analysis_boundary=graph["after"])


def test_report_rejects_consistently_truncated_claim_package(graph):
    claim = graph["claims"][0]
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=graph["protocols"][0], claims=(claim,),
            protocol_claim_sets=graph["protocol_claim_sets"],
            cumulative_performances=tuple(item for item in graph["performances"]
                                          if item.edge_claim_id == claim.edge_claim_id),
            bounded_performances=tuple(item for item in graph["bounded_performances"]
                                       if item.edge_claim_id == claim.edge_claim_id),
            drift_analyses=tuple(item for item in graph["drift_analyses"]
                                 if item.edge_claim_id == claim.edge_claim_id),
            provenance=graph["provenance"], analysis_boundary=graph["after"])


def test_report_cannot_substitute_older_nonterminal_claim_set(graph):
    protocol = graph["protocols"][0]
    claim = graph["claims"][0]
    initial = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=protocol.effective_at,
        edge_claim_ids=(claim.edge_claim_id,), provenance=graph["provenance"])
    successor = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=protocol.effective_at + timedelta(microseconds=1),
        edge_claim_ids=(item.edge_claim_id for item in graph["claims"]),
        predecessor_protocol_claim_set_id=initial.protocol_claim_set_id,
        provenance=graph["provenance"])
    old_report = create_comparative_performance_report(
        protocol=protocol, claims=(claim,), protocol_claim_sets=(initial,),
        cumulative_performances=tuple(item for item in graph["performances"]
                                      if item.edge_claim_id == claim.edge_claim_id),
        bounded_performances=tuple(item for item in graph["bounded_performances"]
                                   if item.edge_claim_id == claim.edge_claim_id),
        drift_analyses=tuple(item for item in graph["drift_analyses"]
                             if item.edge_claim_id == claim.edge_claim_id),
        provenance=graph["provenance"], analysis_boundary=graph["after"])
    with pytest.raises(ContractError):
        _validate(graph, protocol_claim_sets=(initial, successor), reports=(old_report,))


def test_report_rejects_duplicate_analytical_input(graph):
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=graph["protocols"][0], claims=graph["claims"],
            protocol_claim_sets=graph["protocol_claim_sets"],
            cumulative_performances=graph["performances"] + (graph["performances"][-1],),
            bounded_performances=graph["bounded_performances"], drift_analyses=graph["drift_analyses"],
            provenance=graph["provenance"], analysis_boundary=graph["after"])


def test_report_has_no_mutable_usage_state(graph):
    names = {field.name for field in __import__("dataclasses").fields(graph["reports"][0])}
    assert not names & {"reviewed", "used_for_scheduled_review", "used_for_drift_review", "review_ids"}


def test_graph_validation_accepts_matching_pr13_drift(graph):
    protocol, claim, _, _, _, analysis = _parts(graph)
    report = graph["reports"][0]
    surveillance = DriftSurveillance.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        drift_rule_id=analysis.drift_rule_id, drift_rule_version=analysis.drift_rule_version,
        report_reference=report.to_reference(), effective_at=report.analysis_boundary + timedelta(seconds=1),
        disposition=analysis.disposition, provenance=graph["provenance"])
    _validate(graph, drift_surveillance=(surveillance,))


def test_graph_validation_rejects_drift_disposition_mismatch(graph):
    protocol, claim, _, _, _, analysis = _parts(graph)
    report = graph["reports"][0]
    wrong = next(item for item in type(analysis.disposition) if item is not analysis.disposition)
    surveillance = DriftSurveillance.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        drift_rule_id=analysis.drift_rule_id, drift_rule_version=analysis.drift_rule_version,
        report_reference=report.to_reference(), effective_at=report.analysis_boundary + timedelta(seconds=1),
        disposition=wrong, provenance=graph["provenance"])
    with pytest.raises(ContractError):
        _validate(graph, drift_surveillance=(surveillance,))


def test_v2_rule_parameter_validation():
    with pytest.raises(ContractError):
        VersionedRuleSpecification.create(RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "2",
                                          (RuleParameter("days", 0),))
    with pytest.raises(ContractError):
        VersionedRuleSpecification.create(RulePurpose.DRIFT_CLASSIFICATION, "brier-deterioration", "2",
                                          (RuleParameter("threshold", Decimal("2.01")),))


def test_prospective_factory_rejects_v1_protocol():
    old = load_pr14_fixture(Path("tests/fixtures/forecast_comparative_research_cases.json"))["protocols"][0]
    with pytest.raises(ContractError):
        create_time_bounded_comparative_performance(
            protocol=old, edge_claim=(), research_domain=(), analysis_boundary=old.effective_at,
            opportunities=(), eligibility_contexts=(), eligibility_results=(), snapshots=(),
            measurements=(), outcome_histories=(), provenance=ResearchContractProvenance("test", "1"))


def test_surveillance_rule_cardinality_fails_closed(graph):
    protocol = graph["protocols"][0]
    for rules in ((), protocol.surveillance_window_rules * 2):
        with pytest.raises(ContractError):
            candidate = _clone_protocol(protocol, surveillance_window_rules=rules)
            create_time_bounded_comparative_performance(
                protocol=candidate, edge_claim=(), research_domain=(), analysis_boundary=graph["after"],
                opportunities=(), eligibility_contexts=(), eligibility_results=(), snapshots=(),
                measurements=(), outcome_histories=(), provenance=graph["provenance"])
    assert isinstance(protocol.surveillance_window_rules, tuple)
    assert len(protocol.surveillance_window_rules) == 1


def test_historical_replay_excludes_later_correction_and_measurement(graph):
    _, _, historical, current, _, _ = _parts(graph)
    later_snapshot_ids = {item.research_snapshot_id for item in graph["snapshots"]
                          if item.effective_at > current.window_start_at}
    later_measurement_ids = {item.comparative_measurement_id for item in graph["measurements"]
                             if item.effective_at > current.window_start_at}
    assert not set(historical.coverage.authoritative_snapshot_ids) & later_snapshot_ids
    assert not set(historical.comparative_measurement_ids) & later_measurement_ids


def test_drift_is_independent_of_ambient_decimal_context(graph):
    protocol, _, historical, current, _, _ = _parts(graph)
    original = getcontext().copy()
    try:
        results = []
        for precision, rounding in ((2, ROUND_DOWN), (60, ROUND_UP)):
            getcontext().prec, getcontext().rounding = precision, rounding
            results.append(create_comparative_drift_analysis(
                protocol=protocol, historical=historical, current=current,
                measurements=reversed(graph["measurements"]), provenance=graph["provenance"]))
        assert results[0] == results[1]
        assert results[0].to_json() == results[1].to_json()
    finally:
        getcontext().prec, getcontext().rounding = original.prec, original.rounding


def test_omitted_window_opportunity_fails_closed(graph):
    current = next(item for item in graph["bounded_performances"] if item.paired_sample_size)
    omitted = current.coverage.eligible_capture_opportunity_ids[0]
    opportunities = tuple(item for item in graph["opportunities"]
                          if item.research_capture_opportunity_id != omitted)
    with pytest.raises(ContractError):
        _recreate_bounded(graph, current, opportunities=opportunities)


def test_consistently_omitted_opportunity_graph_fails_closed(graph):
    current = next(item for item in graph["bounded_performances"] if item.paired_sample_size)
    omitted = current.coverage.eligible_capture_opportunity_ids[0]
    with pytest.raises(ContractError):
        _recreate_bounded(
            graph, current,
            opportunities=tuple(item for item in graph["opportunities"]
                                if item.research_capture_opportunity_id != omitted),
            eligibility_contexts=tuple(item for item in graph["eligibility_contexts"]
                                       if item.research_capture_opportunity_id != omitted),
            eligibility_results=tuple(item for item in graph["eligibility_results"]
                                      if item.research_capture_opportunity_id != omitted))


def test_foreign_provider_schedule_history_is_nonmaterial(graph):
    current = graph["bounded_performances"][0]
    foreign = _additional_history(graph, provider_id="foreign-outcome-provider")
    histories = graph["outcome_histories"] + (foreign,)
    recreated = _recreate_bounded(graph, current, outcome_histories=histories)
    assert recreated == current
    assert recreated.coverage == current.coverage
    _validate(graph, outcome_histories=histories)


def test_foreign_provider_identity_collision_cannot_override_schedule(graph):
    current = graph["bounded_performances"][0]
    authoritative_id = graph["outcome_histories"][0].observations[0].observation_id
    foreign = _additional_history(
        graph, provider_id="foreign-outcome-provider", observation_id=authoritative_id)
    assert _recreate_bounded(
        graph, current,
        outcome_histories=graph["outcome_histories"] + (foreign,)) == current


def test_conflicting_authoritative_schedule_evidence_fails_closed(graph):
    current = graph["bounded_performances"][0]
    authoritative = graph["outcome_histories"][0]
    conflicting = _additional_history(
        graph, provider_id=authoritative.authoritative_provider_id,
        observation_id=authoritative.observations[0].observation_id)
    with pytest.raises(ContractError):
        _recreate_bounded(
            graph, current,
            outcome_histories=graph["outcome_histories"] + (conflicting,))


def test_total_capture_failure_opportunity_cannot_disappear(graph):
    current = next(item for item in graph["bounded_performances"]
                   if item.coverage.benchmark_capture_failure_snapshot_ids)
    snapshot_id = current.coverage.benchmark_capture_failure_snapshot_ids[0]
    snapshot = next(item for item in graph["snapshots"] if item.research_snapshot_id == snapshot_id)
    omitted = snapshot.research_capture_opportunity_id
    with pytest.raises(ContractError):
        _recreate_bounded(
            graph, current,
            opportunities=tuple(item for item in graph["opportunities"]
                                if item.research_capture_opportunity_id != omitted),
            eligibility_contexts=tuple(item for item in graph["eligibility_contexts"]
                                       if item.research_capture_opportunity_id != omitted),
            eligibility_results=tuple(item for item in graph["eligibility_results"]
                                      if item.research_capture_opportunity_id != omitted))


def test_omitted_eligibility_context_fails_closed(graph):
    current = next(item for item in graph["bounded_performances"] if item.paired_sample_size)
    opportunity = current.coverage.eligible_capture_opportunity_ids[0]
    contexts = tuple(item for item in graph["eligibility_contexts"]
                     if not (item.research_capture_opportunity_id == opportunity
                             and item.analysis_boundary == current.analysis_boundary))
    with pytest.raises(ContractError):
        _recreate_bounded(graph, current, eligibility_contexts=contexts)


def test_omitted_eligibility_result_fails_closed(graph):
    current = next(item for item in graph["bounded_performances"] if item.paired_sample_size)
    opportunity = current.coverage.eligible_capture_opportunity_ids[0]
    results = tuple(item for item in graph["eligibility_results"]
                    if not (item.research_capture_opportunity_id == opportunity
                            and item.analysis_boundary == current.analysis_boundary))
    with pytest.raises(ContractError):
        _recreate_bounded(graph, current, eligibility_results=results)


def test_duplicate_population_registries_fail_closed(graph):
    current = graph["bounded_performances"][0]
    for name, values in (("opportunities", graph["opportunities"]),
                         ("eligibility_contexts", graph["eligibility_contexts"]),
                         ("eligibility_results", graph["eligibility_results"])):
        with pytest.raises(ContractError):
            _recreate_bounded(graph, current, **{name: values + (values[0],)})


def test_direct_claim_subset_fails_closed(graph):
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=graph["protocols"][0], claims=(graph["claims"][0],),
            protocol_claim_sets=graph["protocol_claim_sets"],
            cumulative_performances=graph["performances"],
            bounded_performances=graph["bounded_performances"],
            drift_analyses=graph["drift_analyses"], provenance=graph["provenance"],
            analysis_boundary=graph["after"])


def test_duplicate_and_foreign_claims_fail_closed(graph):
    protocol = graph["protocols"][0]
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=protocol, claims=graph["claims"] + (graph["claims"][0],),
            protocol_claim_sets=graph["protocol_claim_sets"],
            cumulative_performances=graph["performances"], bounded_performances=graph["bounded_performances"],
            drift_analyses=graph["drift_analyses"], provenance=graph["provenance"], analysis_boundary=graph["after"])
    foreign = load_pr14_fixture(Path("tests/fixtures/forecast_comparative_research_cases.json"))["claims"][0]
    foreign_claim_set = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=protocol.effective_at,
        edge_claim_ids=tuple(item.edge_claim_id for item in graph["claims"]) + (foreign.edge_claim_id,),
        provenance=graph["provenance"])
    with pytest.raises(ContractError):
        create_comparative_performance_report(
            protocol=protocol, claims=graph["claims"] + (foreign,),
            protocol_claim_sets=(foreign_claim_set,),
            cumulative_performances=graph["performances"], bounded_performances=graph["bounded_performances"],
            drift_analyses=graph["drift_analyses"], provenance=graph["provenance"], analysis_boundary=graph["after"])


def test_report_input_order_is_nonmaterial(graph):
    report = graph["reports"][0]
    recreated = create_comparative_performance_report(
        protocol=graph["protocols"][0], claims=reversed(graph["claims"]),
        protocol_claim_sets=reversed(graph["protocol_claim_sets"]),
        cumulative_performances=reversed(graph["performances"]),
        bounded_performances=reversed(graph["bounded_performances"]),
        drift_analyses=reversed(graph["drift_analyses"]), provenance=report.provenance,
        analysis_boundary=report.analysis_boundary, limitations=report.limitations)
    assert recreated == report


def test_material_report_limitation_changes_identity(graph):
    report = graph["reports"][0]
    changed = create_comparative_performance_report(
        protocol=graph["protocols"][0], claims=graph["claims"],
        protocol_claim_sets=graph["protocol_claim_sets"],
        cumulative_performances=graph["performances"], bounded_performances=graph["bounded_performances"],
        drift_analyses=graph["drift_analyses"], provenance=report.provenance,
        analysis_boundary=report.analysis_boundary, limitations=report.limitations + ("material addition",))
    assert changed.comparative_performance_report_id != report.comparative_performance_report_id


def test_protocol_claim_set_lineage_is_material_report_identity(graph):
    protocol = graph["protocols"][0]
    claim_ids = tuple(sorted(item.edge_claim_id for item in graph["claims"]))
    initial_a = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id, effective_at=protocol.effective_at,
        edge_claim_ids=claim_ids[:1], provenance=graph["provenance"])
    final_a = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=protocol.effective_at + timedelta(microseconds=1),
        edge_claim_ids=claim_ids,
        predecessor_protocol_claim_set_id=initial_a.protocol_claim_set_id,
        provenance=graph["provenance"])
    initial_b = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id, effective_at=protocol.effective_at,
        edge_claim_ids=claim_ids[:2], provenance=graph["provenance"])
    final_b = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id,
        effective_at=protocol.effective_at + timedelta(microseconds=1),
        edge_claim_ids=claim_ids,
        predecessor_protocol_claim_set_id=initial_b.protocol_claim_set_id,
        provenance=graph["provenance"])
    common = dict(
        protocol=protocol, claims=graph["claims"],
        cumulative_performances=graph["performances"],
        bounded_performances=graph["bounded_performances"],
        drift_analyses=graph["drift_analyses"], provenance=graph["provenance"],
        analysis_boundary=graph["after"], limitations=graph["reports"][0].limitations)
    report_a = create_comparative_performance_report(
        protocol_claim_sets=(initial_a, final_a), **common)
    report_b = create_comparative_performance_report(
        protocol_claim_sets=(initial_b, final_b), **common)
    assert final_a.edge_claim_ids == final_b.edge_claim_ids == claim_ids
    assert final_a.protocol_claim_set_id != final_b.protocol_claim_set_id
    assert report_a.protocol_claim_set_id == final_a.protocol_claim_set_id
    assert report_b.protocol_claim_set_id == final_b.protocol_claim_set_id
    for name in ("schema_version", "identity_algorithm_version", "contract_version",
                 "report_algorithm_version", "protocol_id", "analysis_boundary",
                 "claim_findings", "limitations"):
        assert getattr(report_a, name) == getattr(report_b, name)
    assert report_a.comparative_performance_report_id != report_b.comparative_performance_report_id
    reference_a, reference_b = report_a.to_reference(), report_b.to_reference()
    assert reference_a.report_id == report_a.comparative_performance_report_id
    assert reference_b.report_id == report_b.comparative_performance_report_id
    assert reference_a.report_id != reference_b.report_id
    assert reference_a.edge_claim_ids == reference_b.edge_claim_ids == claim_ids


def test_tampered_top_level_identities_fail(graph):
    bounded = graph["bounded_performances"][0]
    drift = graph["drift_analyses"][0]
    report = graph["reports"][0]
    for item, field in ((bounded, "time_bounded_comparative_performance_id"),
                        (drift, "comparative_drift_analysis_id"),
                        (report, "comparative_performance_report_id")):
        with pytest.raises(ContractError):
            replace(item, **{field: "tampered:identity"})


def test_truthful_empty_and_complete_challenger_measurements(graph):
    protocol = graph["protocols"][0]
    for challenger in protocol.alternative_sources:
        assert any(item.challenger_source_reference_id == challenger.probability_source_reference_id
                   for item in graph["measurements"])
    empty = next(item for item in graph["bounded_performances"] if item.paired_sample_size == 0)
    assert not empty.coverage.synchronized_pair_snapshot_ids
    assert not empty.coverage.resolved_outcome_snapshot_ids
    _validate(graph)


def test_every_drift_classification_boundary():
    threshold = Decimal("0.10")
    cases = (
        (Decimal("0.11"), Decimal("0.12"), DriftDisposition.MATERIAL_DRIFT),
        (threshold, Decimal("0.12"), DriftDisposition.MATERIAL_DRIFT),
        (Decimal("0.01"), Decimal("0.09"), DriftDisposition.NO_MATERIAL_DRIFT),
        (Decimal("0.01"), threshold, DriftDisposition.INSUFFICIENT_EVIDENCE),
        (Decimal("0.01"), Decimal("0.11"), DriftDisposition.INSUFFICIENT_EVIDENCE),
        (None, None, DriftDisposition.INSUFFICIENT_EVIDENCE),
    )
    for lower, upper, expected in cases:
        assert _classify_drift(lower, upper, threshold) is expected


def test_graph_validation_reproduces_every_pr15_artifact(graph):
    _validate(graph)


def test_graph_validation_reproduces_pr14_cumulative_authority(graph):
    protocol, claim, _, _, cumulative, _ = _parts(graph)
    domain = next(item for item in protocol.research_domains
                  if item.research_domain_id == claim.research_domain_id)
    omitted_measurement = next(item for item in graph["measurements"]
                               if item.comparative_measurement_id in cumulative.comparative_measurement_ids)
    altered = create_comparative_performance(
        protocol=protocol, edge_claim=claim, research_domain=domain,
        analysis_boundary=cumulative.analysis_boundary, opportunities=graph["opportunities"],
        eligibility_contexts=graph["eligibility_contexts"],
        eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
        measurements=tuple(item for item in graph["measurements"] if item != omitted_measurement),
        outcome_histories=graph["outcome_histories"], provenance=cumulative.provenance,
        limitations=cumulative.limitations)
    performances = tuple(altered if item == cumulative else item for item in graph["performances"])
    with pytest.raises(ContractError):
        _validate(graph, cumulative_performances=performances)


def test_graph_validation_rejects_duplicate_authority(graph):
    with pytest.raises(ContractError):
        _validate(graph, claims=graph["claims"] + (graph["claims"][0],))
    with pytest.raises(ContractError):
        _validate(graph, measurements=graph["measurements"] + (graph["measurements"][0],))


def test_same_report_later_drift_review_chronology(graph):
    protocol, claim, _, _, _, analysis = _parts(graph)
    report = graph["reports"][0]
    surveillance = DriftSurveillance.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        drift_rule_id=analysis.drift_rule_id, drift_rule_version=analysis.drift_rule_version,
        report_reference=report.to_reference(), effective_at=report.analysis_boundary + timedelta(seconds=1),
        disposition=analysis.disposition, provenance=graph["provenance"])
    coverage = ReviewObligationCoverage((ReviewObligationReference(
        ReviewObligationKind.MATERIAL_DRIFT,
        drift_surveillance=DriftSurveillanceReference(
            protocol.research_protocol_id, claim.edge_claim_id,
            surveillance.drift_surveillance_id, surveillance.effective_at)),))
    review = ResearchReview.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        report_reference=report.to_reference(), conclusion=ResearchReviewConclusion.WEAKENING,
        obligation_coverage=coverage, completed_at=surveillance.effective_at + timedelta(seconds=1),
        rationale="synthetic same-report chronology", provenance=graph["provenance"])
    assert review.report_reference == surveillance.report_reference


def test_combined_obligation_coverage_remains_representable(graph):
    protocol, claim, _, _, _, analysis = _parts(graph)
    report = graph["reports"][0]
    surveillance = DriftSurveillance.create(
        protocol_id=protocol.research_protocol_id, edge_claim_id=claim.edge_claim_id,
        drift_rule_id=analysis.drift_rule_id, drift_rule_version=analysis.drift_rule_version,
        report_reference=report.to_reference(), effective_at=report.analysis_boundary + timedelta(seconds=1),
        disposition=analysis.disposition, provenance=graph["provenance"])
    boundary = protocol.scheduled_review_boundaries[0]
    coverage = ReviewObligationCoverage((
        ReviewObligationReference(ReviewObligationKind.SCHEDULED_BOUNDARY,
            scheduled_boundary=ScheduledReviewBoundaryReference(protocol.research_protocol_id, boundary.boundary_key)),
        ReviewObligationReference(ReviewObligationKind.MATERIAL_DRIFT,
            drift_surveillance=DriftSurveillanceReference(protocol.research_protocol_id, claim.edge_claim_id,
                surveillance.drift_surveillance_id, surveillance.effective_at)),
    ))
    assert len(coverage.obligations) == 2


def load_tests(_loader, _tests, _pattern):
    fixture_graph = graph()
    suite = unittest.TestSuite()
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            parameters = inspect.signature(function).parameters
            suite.addTest(unittest.FunctionTestCase(
                (lambda function=function, parameters=parameters:
                 function(fixture_graph) if parameters else function()),
                description=name))
    return suite
