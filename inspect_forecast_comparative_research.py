"""Offline deterministic inspector for the synthetic PR14 comparative fixture."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

from event_contracts import (CanonicalEvent, Evidence, NativeIdentifier, ParticipantRef,
                             Provenance, ReconciliationResult, ValidationStatus)
from forecast_contracts import (AssumptionDisclosure, ForecastDistribution, ForecastIssueCode,
                                ForecastObservation, ForecastOutcome, ForecastValidationIssue,
                                ForecastValidationStatus, ProbabilityScale,
                                ProviderReportedAssumptions, PublishedProbability)
from forecast_comparative_research import (
    CALIBRATION_BOUNDARIES,
    ComparativeMeasurement,
    ComparativePerformance,
    EventPhase,
    EventStageEvidence,
    PairwiseSynchronization,
    PopulationEligibilityResult,
    PopulationEligibilityDisposition,
    ResearchCaptureOpportunity,
    ResearchEventEligibilityContext,
    ResearchSnapshot,
    SnapshotDimensionClassification,
    SnapshotValidationStatus,
    SourceCapture,
    SourceCaptureDisposition,
    create_comparative_measurement,
    create_comparative_performance,
    create_pairwise_synchronization,
    evaluate_population_eligibility,
    select_authoritative_research_snapshots,
    validate_comparative_research_contracts,
)
from forecast_evaluation import EvaluationArithmeticInput, ForecastEvaluation
from forecast_research_contracts import (
    EdgeClaim,
    ResearchProtocol,
    RuleParameter,
    RulePurpose,
    VersionedRuleSpecification,
)
from inspect_forecast_research_contracts import load_fixture as load_pr13_fixture
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _outcome_observation(key: str, start: datetime, *, event_key: str | None = None, final: bool = False,
                         home_won: bool = False, collected_at: datetime | None = None) -> OutcomeObservation:
    event_key = event_key or key
    home, away = f"team:{event_key}:home", f"team:{event_key}:away"
    return OutcomeObservation(
        observation_id=f"mlb-stats-api:{key}:{'final' if final else 'schedule'}",
        canonical_event_id=f"canonical-event:{event_key}", authoritative_provider_id="mlb-stats-api",
        provider_event_id=f"mlb-game:{event_key}", provider_status=OutcomeStatus.FINAL if final else OutcomeStatus.SCHEDULED,
        provider_status_detail="Final" if final else "Scheduled", away_participant_id=away,
        home_participant_id=home, scheduled_start=start,
        collected_at=collected_at or start - timedelta(days=2), raw_evidence_sha256="1" * 64,
        canonical_evidence_sha256="2" * 64, source_url=f"https://fixture.invalid/{key}",
        collector_version="fixture-1", validation_status=ValidationStatus.VALID,
        away_score=2 if final and home_won else (4 if final else None),
        home_score=4 if final and home_won else (2 if final else None),
        winning_participant_id=(home if home_won else away) if final else None,
        losing_participant_id=(away if home_won else home) if final else None,
        unresolved=not final, completed_periods=9 if final else None,
        provider_result_at=(collected_at or start + timedelta(hours=4)) if final else None,
    )


def _evaluation(key: str, source: object, observation_id: str, outcome: OutcomeObservation,
                probability: Decimal, collected_at: datetime) -> ForecastEvaluation:
    home, away = outcome.home_participant_id, outcome.away_participant_id
    winner = outcome.winning_participant_id
    assert winner is not None
    probabilities = ((away, Decimal(1) - probability), (home, probability))
    realized = ((away, int(winner == away)), (home, int(winner == home)))
    realized_probability = dict(probabilities)[winner]
    with localcontext() as context:
        context.prec = 50
        log_loss = -realized_probability.ln()
    brier = (realized_probability - Decimal(1)) ** 2
    source_id = source.probability_source_reference_id
    digest = source_id.split(":")[-1][:12] + key
    return ForecastEvaluation(
        evaluation_id=f"forecast-evaluation:{digest}", algorithm_id="binary-outcome-evaluation",
        algorithm_version="1", eligibility_decision_id=f"eligibility:{digest}",
        forecast_observation_id=observation_id, outcome_observation_id=outcome.observation_id,
        canonical_event_id=outcome.canonical_event_id, provider_id=source.provider_id,
        model_id=source.model_or_product_id, model_version_id=source.model_or_product_version,
        forecast_collected_at=collected_at, probability_distribution=probabilities,
        realized_winning_participant_id=winner, realized_outcome_vector=realized,
        brier_score=brier, log_loss=log_loss,
        directional_correct=(probability >= Decimal("0.5")) == (winner == home),
        predicted_favorite_id=home if probability > Decimal("0.5") else away,
        calibration_bucket="fixture-calibration-input",
        arithmetic_inputs=tuple(EvaluationArithmeticInput(item, value, dict(realized)[item]) for item, value in probabilities),
        derivation_id=f"forecast-evaluation-derivation:{digest}",
    )


def _canonical_event(event_key: str) -> CanonicalEvent:
    return CanonicalEvent(
        "baseball", "MLB", "2026", f"canonical-event:{event_key}",
        (ParticipantRef(f"team:{event_key}:away", f"Away {event_key}"),
         ParticipantRef(f"team:{event_key}:home", f"Home {event_key}")),
    )


def _forecast_observation(*, key: str, source: object, event: CanonicalEvent,
                          schedule_id: str, probability: Decimal, collected_at: datetime,
                          invalid: bool = False) -> ForecastObservation:
    away, home = event.participants
    probabilities = (
        PublishedProbability(ForecastOutcome(away.canonical_id, f"participant-wins:{away.canonical_id}",
                                             event.canonical_event_id), Decimal(1) - probability,
                             str(Decimal(1) - probability), 3, ProbabilityScale.PROPORTION),
        PublishedProbability(ForecastOutcome(home.canonical_id, f"participant-wins:{home.canonical_id}",
                                             event.canonical_event_id), probability, str(probability),
                             3, ProbabilityScale.PROPORTION),
    )
    observation_id = f"forecast-observation:{key}"
    reconciliation = ReconciliationResult.matched(
        NativeIdentifier("synthetic-source", observation_id), event,
        evidence=(Evidence("fixture", "explicit synthetic PR14 Evidence"),))
    provenance = Provenance(source.provider_id, observation_id, event.canonical_event_id,
                            collected_at, validation_status=ValidationStatus.VALID)
    issues = ((ForecastValidationIssue(ForecastIssueCode.MATERIAL_INFORMATION_MISSING,
                                       "synthetic invalid capture"),) if invalid else ())
    return ForecastObservation(
        observation_id, source.model_or_product_version, reconciliation,
        ForecastDistribution(probabilities),
        ProviderReportedAssumptions(AssumptionDisclosure.UNDISCLOSED),
        collected_at, provenance, schedule_observation_id=schedule_id,
        validation_status=(ForecastValidationStatus.INVALID if invalid else ForecastValidationStatus.VALID),
        validation_issues=issues,
    )


def _protocol_and_claims(path: Path) -> tuple[ResearchProtocol, tuple[EdgeClaim, ...], object]:
    payload = json.loads(path.read_text())
    base_graph = load_pr13_fixture(Path("tests/fixtures/forecast_research_contract_cases.json"))
    base = base_graph["protocols"][0]
    calibration = VersionedRuleSpecification.create(
        RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "2",
        (RuleParameter("bin_boundaries", CALIBRATION_BOUNDARIES),),
    )
    protocol = ResearchProtocol.create(
        protocol_version="2", effective_at=base.effective_at,
        scientific_question=base.scientific_question, research_population=base.research_population,
        market_benchmark=base.market_benchmark, alternative_sources=base.alternative_sources,
        approved_dimensions=base.approved_dimensions, research_domains=base.research_domains,
        snapshot_timing_rule=base.snapshot_timing_rule, capture_tolerance_rule=base.capture_tolerance_rule,
        synchronization_rule=base.synchronization_rule, event_compatibility_rule=base.event_compatibility_rule,
        outcome_resolution_rule=base.outcome_resolution_rule, primary_measure_rule=base.primary_measure_rule,
        supporting_measure_rules=(next(item for item in base.supporting_measure_rules if item.rule_id == "log-loss-safeguard"), calibration),
        statistical_method_rule=VersionedRuleSpecification.create(
            RulePurpose.STATISTICAL_METHOD, "paired-bootstrap", "1", (
                RuleParameter("confidence_level", Decimal("0.95")), RuleParameter("resamples", 200))),
        practical_significance_rule=base.practical_significance_rule,
        burden_of_proof_rule=base.burden_of_proof_rule,
        surveillance_window_rules=((VersionedRuleSpecification.create(
            RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "2",
            (RuleParameter("days", int(payload["surveillance_days"])),)),)
            if "surveillance_days" in payload else base.surveillance_window_rules),
        drift_classification_rule=(VersionedRuleSpecification.create(
            RulePurpose.DRIFT_CLASSIFICATION, "brier-deterioration", "2",
            (RuleParameter("threshold", Decimal(payload["drift_threshold"])),))
            if "drift_threshold" in payload else base.drift_classification_rule),
        drift_material_event_rule=base.drift_material_event_rule,
        scheduled_review_boundaries=base.scheduled_review_boundaries,
        limitations=("synthetic PR14 fixture; no empirical finding",), provenance=base_graph["provenance"],
    )
    domains = (protocol.research_domains if payload.get("all_domains") else
               (next(item for item in protocol.research_domains if not item.partition_selections),))
    claims = tuple(EdgeClaim.create(
        protocol_id=protocol.research_protocol_id,
        challenger_source_reference_id=challenger.probability_source_reference_id,
        benchmark_source_reference_id=protocol.market_benchmark.probability_source_reference_id,
        research_domain_id=domain.research_domain_id,
        provenance=base_graph["provenance"],
    ) for domain in domains for challenger in protocol.alternative_sources)
    return protocol, claims, base_graph["provenance"]


def load_fixture(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text())
    protocol, claims, provenance = _protocol_and_claims(path)
    benchmark = protocol.market_benchmark
    challenger = protocol.alternative_sources[0]
    other = protocol.alternative_sources[1]
    dimension = protocol.approved_dimensions[0]
    schedules, outcomes, opportunities, snapshots, evaluations, measurements = [], [], [], [], [], []
    canonical_events: dict[str, CanonicalEvent] = {}
    stages, forecast_observations = [], []
    for spec in payload["events"]:
        key, start = spec["key"], _at(spec["start"])
        event_key = spec.get("event_key", key)
        event = canonical_events.setdefault(event_key, _canonical_event(event_key))
        schedule_collected_at = _at(spec["schedule_collected_at"]) if spec.get("schedule_collected_at") else start - timedelta(days=2)
        schedule = _outcome_observation(key, start, event_key=event_key, collected_at=schedule_collected_at)
        schedules.append(schedule)
        stages.append(EventStageEvidence.create(
            canonical_event_id=event.canonical_event_id, provider_id="mlb-stats-api",
            provider_event_id=schedule.provider_event_id,
            event_phase=EventPhase.POSTSEASON if spec.get("postseason") else EventPhase.REGULAR_SEASON,
            observed_at=schedule.collected_at, evidence_reference=f"synthetic-game-type:{key}",
        ))
        opportunity = ResearchCaptureOpportunity.create(protocol.research_protocol_id, schedule.observation_id, "winner")
        opportunities.append(opportunity)
        target = start - timedelta(hours=6)
        captures = []
        for source, label in ((benchmark, "benchmark"), (challenger, "challenger"), (other, "other")):
            missing = bool(spec.get("all_missing")) or (label == "challenger" and bool(spec.get("challenger_missing")))
            if missing:
                captures.append(SourceCapture(source.probability_source_reference_id,
                                              SourceCaptureDisposition.MISSING, reasons=("provider observation unavailable",)))
            else:
                invalid = label == "other" and bool(spec.get("other_invalid"))
                outside = ((label == "other" and bool(spec.get("other_outside")))
                           or (label == "challenger" and bool(spec.get("unsynchronized"))))
                observed_at = target + timedelta(seconds=700 if label == "challenger" and spec.get("unsynchronized")
                                                  else (301 if outside else 0))
                probability = Decimal(spec.get(label, "0.50"))
                observation = _forecast_observation(
                    key=f"{key}:{label}", source=source, event=event,
                    schedule_id=schedule.observation_id, probability=probability,
                    collected_at=observed_at, invalid=invalid)
                forecast_observations.append(observation)
                disposition = (SourceCaptureDisposition.CAPTURED_INVALID if invalid
                               else SourceCaptureDisposition.OUTSIDE_CAPTURE_TOLERANCE if outside
                               else SourceCaptureDisposition.CAPTURED_VALID)
                captures.append(SourceCapture(source.probability_source_reference_id,
                                              disposition, observation.observation_id, observed_at,
                                              reasons=(("captured distribution failed validation",) if invalid
                                                       else ("capture exceeded Protocol tolerance",) if outside else ())))
        sync = []
        for source, label in ((challenger, "challenger"), (other, "other")):
            sync.append(create_pairwise_synchronization(
                benchmark_capture=next(item for item in captures if item.probability_source_reference_id == benchmark.probability_source_reference_id),
                challenger_capture=next(item for item in captures if item.probability_source_reference_id == source.probability_source_reference_id),
                synchronization_rule=protocol.synchronization_rule))
        partition = spec.get("partition", "favorite")
        classification = SnapshotDimensionClassification(
            dimension.approved_dimension_id, partition, dimension.classification_rule.rule_id,
            dimension.classification_rule.rule_version)
        snapshot = ResearchSnapshot.create(
            research_capture_opportunity_id=opportunity.research_capture_opportunity_id,
            protocol_id=protocol.research_protocol_id, effective_at=target + timedelta(minutes=5),
            canonical_event_id=schedule.canonical_event_id, proposition_type="winner",
            canonical_proposition_outcome_id=f"team:{event_key}:home", scheduled_start=start,
            target_capture_at=target, capture_started_at=target, capture_completed_at=target + timedelta(minutes=1),
            source_captures=tuple(captures), pairwise_synchronization=tuple(sync),
            dimension_classifications=(classification,), validation_status=SnapshotValidationStatus.VALID,
            provenance=provenance,
        )
        snapshots.append(snapshot)
        if key == "a":
            corrected = ResearchSnapshot.create(
                research_capture_opportunity_id=opportunity.research_capture_opportunity_id,
                protocol_id=protocol.research_protocol_id, effective_at=_at(payload["analysis_before_correction"]) + timedelta(days=2),
                canonical_event_id=schedule.canonical_event_id, proposition_type="winner",
                canonical_proposition_outcome_id=f"team:{event_key}:home", scheduled_start=start,
                target_capture_at=target, capture_started_at=target, capture_completed_at=target + timedelta(minutes=1),
                source_captures=tuple(captures), pairwise_synchronization=tuple(sync),
                dimension_classifications=(classification,), validation_status=SnapshotValidationStatus.VALID,
                provenance=provenance, supersedes_snapshot_id=snapshot.research_snapshot_id,
                correction_reason="corrected deterministic event timezone representation",
                limitations=("capture chronology preserved from original Snapshot",),
            )
            snapshots.append(corrected)
        if "benchmark" in spec and not spec.get("unsynchronized") and not spec.get("unresolved"):
            outcome = _outcome_observation(key, start, event_key=event_key, final=True, home_won=bool(spec["home_won"]),
                                           collected_at=start + timedelta(hours=4))
            outcomes.append(outcome)
            b_eval = _evaluation(key, benchmark, f"forecast-observation:{key}:benchmark", outcome,
                                 Decimal(spec["benchmark"]), target)
            c_eval = _evaluation(key, challenger, f"forecast-observation:{key}:challenger", outcome,
                                 Decimal(spec["challenger"]), target)
            evaluations.extend((b_eval, c_eval))
            for version in tuple(item for item in snapshots if item.research_capture_opportunity_id == opportunity.research_capture_opportunity_id):
                measurements.append(create_comparative_measurement(
                    protocol=protocol, snapshot=version, benchmark_evaluation=b_eval,
                    challenger_evaluation=c_eval, outcome=outcome,
                    effective_at=max(outcome.collected_at, version.effective_at) + timedelta(seconds=1),
                    provenance=provenance,
                ))
            if payload.get("all_challengers"):
                other_capture = next(item for item in snapshot.source_captures
                                     if item.probability_source_reference_id == other.probability_source_reference_id)
                other_pair = next(item for item in snapshot.pairwise_synchronization
                                  if item.challenger_source_reference_id == other.probability_source_reference_id)
                if (other_capture.disposition is SourceCaptureDisposition.CAPTURED_VALID
                        and other_pair.synchronized):
                    other_eval = _evaluation(
                        f"{key}:other", other, f"forecast-observation:{key}:other", outcome,
                        Decimal(spec.get("other", "0.50")), target)
                    evaluations.append(other_eval)
                    for version in tuple(item for item in snapshots
                                         if item.research_capture_opportunity_id == opportunity.research_capture_opportunity_id):
                        measurements.append(create_comparative_measurement(
                            protocol=protocol, snapshot=version, benchmark_evaluation=b_eval,
                            challenger_evaluation=other_eval, outcome=outcome,
                            effective_at=max(outcome.collected_at, version.effective_at) + timedelta(seconds=1),
                            provenance=provenance,
                        ))
    before = _at(payload["analysis_before_correction"])
    after = _at(payload["analysis_after_correction"])
    observations_by_event: dict[str, list[OutcomeObservation]] = {}
    for observation in schedules + outcomes:
        observations_by_event.setdefault(observation.canonical_event_id, []).append(observation)
    histories = tuple(OutcomeHistory(event_id, "mlb-stats-api", tuple(values))
                      for event_id, values in sorted(observations_by_event.items()))
    history_by_event = {item.canonical_event_id: item for item in histories}
    stage_by_schedule = {item.evidence_reference.rsplit(":", 1)[-1]: item for item in stages}
    contexts, eligibility_results = [], []
    for boundary in (before, after):
        for opportunity in opportunities:
            schedule = next(item for item in schedules if item.observation_id == opportunity.schedule_observation_id)
            if schedule.collected_at > boundary:
                continue
            key = schedule.observation_id.split(":")[1]
            context = ResearchEventEligibilityContext.create(
                opportunity=opportunity, protocol=protocol,
                canonical_event=canonical_events[schedule.canonical_event_id.removeprefix("canonical-event:")],
                stage_evidence=stage_by_schedule[key],
                outcome_history=history_by_event[schedule.canonical_event_id], analysis_boundary=boundary)
            contexts.append(context)
            eligibility_results.append(evaluate_population_eligibility(
                protocol=protocol, opportunity=opportunity, context=context,
                provenance=provenance))
    broad = next(item for item in protocol.research_domains if not item.partition_selections)
    claim = next(item for item in claims if item.challenger_source_reference_id == challenger.probability_source_reference_id)
    performance_claims = claims if payload.get("all_challengers") else (claim,)
    performances = tuple(create_comparative_performance(
        protocol=protocol, edge_claim=performance_claim,
        research_domain=next(item for item in protocol.research_domains
                             if item.research_domain_id == performance_claim.research_domain_id),
        analysis_boundary=boundary,
        opportunities=opportunities, eligibility_contexts=contexts,
        eligibility_results=eligibility_results, snapshots=snapshots, measurements=measurements,
        outcome_histories=histories,
        provenance=provenance, limitations=("synthetic output; not an empirical conclusion",),
    ) for boundary in (before, after) for performance_claim in performance_claims)
    graph = dict(protocols=(protocol,), claims=claims, canonical_events=tuple(canonical_events.values()),
                 event_stage_evidence=tuple(stages), schedule_observations=tuple(schedules),
                 outcome_histories=histories, opportunities=tuple(opportunities),
                 eligibility_contexts=tuple(contexts), eligibility_results=tuple(eligibility_results),
                 snapshots=tuple(snapshots), forecast_observations=tuple(forecast_observations),
                 forecast_evaluations=tuple(evaluations), outcome_observations=tuple(outcomes),
                 measurements=tuple(measurements), performances=performances, provenance=provenance,
                 before=before, after=after)
    for name, contract_type in (("event_stage_evidence", EventStageEvidence),
                                ("eligibility_contexts", ResearchEventEligibilityContext),
                                ("eligibility_results", PopulationEligibilityResult),
                                ("opportunities", ResearchCaptureOpportunity), ("snapshots", ResearchSnapshot),
                                ("measurements", ComparativeMeasurement), ("performances", ComparativePerformance)):
        graph[name] = tuple(contract_type.from_json(item.to_json()) for item in graph[name])
    return graph


def run(path: Path) -> tuple[str, ...]:
    graph = load_fixture(path)
    validate_comparative_research_contracts(
        protocols=graph["protocols"], claims=graph["claims"],
        canonical_events=graph["canonical_events"], event_stage_evidence=graph["event_stage_evidence"],
        schedule_observations=graph["schedule_observations"], outcome_histories=graph["outcome_histories"],
        opportunities=graph["opportunities"], eligibility_contexts=graph["eligibility_contexts"],
        eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
        forecast_observations=graph["forecast_observations"], forecast_evaluations=graph["forecast_evaluations"],
        outcome_observations=graph["outcome_observations"], measurements=graph["measurements"],
        performances=graph["performances"],
    )
    before = select_authoritative_research_snapshots(graph["snapshots"], graph["before"])
    after = select_authoritative_research_snapshots(graph["snapshots"], graph["after"])
    latest = graph["performances"][-1]
    return (
        "PR14 Comparative Research: VALID",
        "Evidence flow: ResearchCaptureOpportunity -> ResearchEventEligibilityContext -> ResearchSnapshot",
        f"Capture opportunities: {len(graph['opportunities'])}",
        f"Authoritative Snapshots before/after correction: {len(before)}/{len(after)}",
        f"Comparative Measurements: {latest.paired_sample_size}",
        f"Mean paired Brier improvement: {latest.mean_paired_brier_improvement}",
        f"Paired bootstrap interval: [{latest.primary_uncertainty.lower_bound}, {latest.primary_uncertainty.upper_bound}]",
        f"Benchmark/challenger WACE: {latest.benchmark_calibration.weighted_absolute_calibration_error}/{latest.challenger_calibration.weighted_absolute_calibration_error}",
        f"Coverage opportunities/measurements: {len(latest.coverage.eligible_capture_opportunity_ids)}/{len(latest.coverage.comparative_measurement_ids)}",
        f"Protocol exclusions: {len(latest.coverage.protocol_excluded_opportunity_ids)}",
        "Scientific status: synthetic descriptive output; Research Review deferred",
        "Comparative Performance Report: deferred to PR15",
        "Current Scientific Applicability: deferred to PR16",
    )


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/forecast_comparative_research_cases.json")
    print("\n".join(run(path)))


if __name__ == "__main__":
    main()
