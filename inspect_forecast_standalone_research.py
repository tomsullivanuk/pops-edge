"""Deterministic, non-authoritative inspector for the synthetic PR17B1 graph."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from event_contracts import ValidationStatus
from forecast_comparative_research import ResearchCaptureOpportunity
from forecast_standalone_research import *
from inspect_forecast_standalone_performance import DEFAULT_FIXTURE, build_graph
from outcome_contracts import OutcomeHistory, OutcomeObservation, OutcomeStatus


def _rules(window_seconds="1641600"):
    return dict(scope_rule=StandaloneRule("scope","synthetic-2026-mlb-regular-season","1",(("competition","mlb"),("event_phase","regular-season"),("ordinary_game","required"),("schedule_provider_id","mlb-stats-api"),("season","2026"),("sport","baseball"),("target_offset_minutes","-360"))),
        representation_rule=StandaloneRule("representation","home-team-yes","1"),
        scoring_rule=StandaloneRule("scoring","binary-brier-log-loss","1",(("decimal_precision","50"),("distribution","binary-complete"),("log_loss","extended-real"))),
        calibration_rule=StandaloneRule("calibration","fixed-bin-wace","1",(("boundaries","0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1"),("empty_bins","omit"),("endpoint_semantics","left-closed-right-open-final-closed"),("weighting","sample-share-absolute-gap"))),
        uncertainty_rule=StandaloneRule("uncertainty","deterministic-one-sample-bootstrap","1",(("confidence_level","0.95"),("resamples","200"))),
        report_rule=StandaloneRule("report","separate-standalone-report","1",(("bounded_window_durations",window_seconds),)))


def _classification(schedule,provenance,**overrides):
    values=dict(authoritative_provider_id=schedule.authoritative_provider_id,provider_event_id=schedule.provider_event_id,
        canonical_event_id=schedule.canonical_event_id,sport="baseball",competition="mlb",season="2026",
        event_phase=EventPhase.REGULAR_SEASON,game_type="regular",ordinary_game=True,doubleheader_id=None,game_number=None,
        participant_ids=tuple(sorted((schedule.away_participant_id,schedule.home_participant_id))),home_participant_id=schedule.home_participant_id,
        away_participant_id=schedule.away_participant_id,mapping_validation_status=EventClassificationValidationStatus.VALID,
        validation_reasons=(),collected_at=schedule.collected_at,effective_at=schedule.collected_at,
        supersedes_classification_id=None,correction_reason=None,limitations=("synthetic classification",),provenance=provenance)
    values.update(overrides);return StandaloneEventClassificationEvidence.create(**values)


def build_synthetic_bundle():
    legacy=build_graph(DEFAULT_FIXTURE); provenance=legacy["provenance"]
    activation=StandaloneResearchActivationBoundary.create(approved_calendar_date=date(2026,6,1),
        activation_at=datetime(2026,6,1,0,0,tzinfo=ZoneInfo(TIMEZONE_NAME)),timezone_name=TIMEZONE_NAME,
        timezone_rule_version="synthetic-tzdb-1",conversion_rule_version="synthetic-midnight-1",
        product_owner_decision_reference="synthetic-decision-pr17b1-fixture",
        decision_effective_at=datetime(2026,5,30,12,tzinfo=timezone.utc),provenance=provenance)
    retro_rules=_rules();pros_rules=_rules("18000");rules=pros_rules
    retrospective=StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.RETROSPECTIVE,
        design=RetrospectiveStandaloneDesign(activation.standalone_research_activation_boundary_id,
            StandaloneRule("selection","latest-real-one-minute-candle-before-target","1"),
            StandaloneRule("manifest","complete-archive-query-manifest","1"),("synthetic archive fixture",)),
        source=legacy["benchmark"],provenance=provenance,**retro_rules)
    prospective=StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.PROSPECTIVE,
        design=ProspectiveStandaloneDesign(activation.standalone_research_activation_boundary_id,
            StandaloneRule("capture","five-slot-inclusive-upper-endpoint","1"),("synthetic point-in-time fixture",)),
        source=legacy["benchmark"],provenance=provenance,**pros_rules)

    target=datetime(2026,5,20,19,tzinfo=timezone.utc);acquired=datetime(2026,6,3,12,tzinfo=timezone.utc)
    candle_seed=dict(protocol_id=retrospective.standalone_probability_source_protocol_id,manifest_id="pending",
        provider_id=PROVIDER_ID,provider_market_id="synthetic-retro-market",canonical_event_id="synthetic-event:retro",
        proposition_id="winner:synthetic-event:retro:synthetic-team:retro-home",home_participant_id="synthetic-team:retro-home",
        contract_side="yes",interval="1m",candle_end_at=target,acquired_at=acquired,close_yes_bid=Decimal("0.48"),
        close_yes_ask=Decimal("0.52"),is_real=True,is_synthetic=False,is_repaired=False,
        retrieval_page_position=0,raw_archive_reference="synthetic-archive:manifest",raw_archive_sha256="b"*64,limitations=("not simultaneous or executable",),provenance=provenance)
    # Manifest identity includes its complete Evidence set, so create the candle with the
    # deterministic manifest identity after computing a manifest with the final candle ID.
    provisional=HistoricalMarketCandleObservation.create(**candle_seed)
    page=HistoricalCandleRetrievalPage("initial",0,None,True,"synthetic-archive:manifest","b"*64,acquired,
        (provisional.historical_market_candle_observation_id,),ManifestValidationStatus.COMPLETE,("synthetic page",))
    manifest=HistoricalCandleQueryManifest.create(protocol_id=retrospective.standalone_probability_source_protocol_id,
        opportunity_id=ResearchCaptureOpportunity.create(retrospective.standalone_probability_source_protocol_id,"synthetic-schedule:retro","winner").research_capture_opportunity_id,
        canonical_event_id="synthetic-event:retro",proposition_id="winner:synthetic-event:retro:synthetic-team:retro-home",
        provider_id=PROVIDER_ID,endpoint="synthetic://candles",provider_market_id="synthetic-retro-market",interval="1m",
        requested_start_at=target-timedelta(minutes=5),requested_end_at=target,retrieval_started_at=acquired,
        retrieval_completed_at=acquired,pages=(page,),
        returned_candle_evidence_ids=(provisional.historical_market_candle_observation_id,),validation_status=ManifestValidationStatus.COMPLETE,
        limitations=("synthetic archive",),effective_at=acquired,supersedes_manifest_id=None,correction_reason=None,provenance=provenance)
    candle=HistoricalMarketCandleObservation.create(**{**candle_seed,"manifest_id":manifest.historical_candle_query_manifest_id})
    assert candle.historical_market_candle_observation_id==provisional.historical_market_candle_observation_id
    retro_schedule=OutcomeObservation("synthetic-schedule:retro",candle.canonical_event_id,"mlb-stats-api","synthetic-game:retro",
        OutcomeStatus.SCHEDULED,"Scheduled","synthetic-team:retro-away",candle.home_participant_id,target+timedelta(hours=6),
        target-timedelta(days=1),"1"*64,"2"*64,"https://fixture.invalid/retro-schedule","synthetic-1",ValidationStatus.VALID)
    retro_outcome=OutcomeObservation("synthetic-outcome:retro",candle.canonical_event_id,"mlb-stats-api","synthetic-game:retro",
        OutcomeStatus.FINAL,"Final","synthetic-team:retro-away",candle.home_participant_id,target+timedelta(hours=6),
        acquired+timedelta(hours=1),"c"*64,"d"*64,"https://fixture.invalid/retro","synthetic-1",ValidationStatus.VALID,
        1,3,candle.home_participant_id,"synthetic-team:retro-away",False,False,9,acquired+timedelta(hours=1),())
    retro_history=OutcomeHistory(candle.canonical_event_id,"mlb-stats-api",(retro_schedule,retro_outcome))
    retro_classification=_classification(retro_schedule,provenance)
    retro_opportunity=ResearchCaptureOpportunity.create(retrospective.standalone_probability_source_protocol_id,retro_schedule.observation_id,"winner")
    retro_context,retro_eligibility=create_standalone_eligibility_authority(protocol=retrospective,opportunity=retro_opportunity,
        outcome_history=retro_history,classification=retro_classification,classifications=(retro_classification,),analysis_boundary=acquired+timedelta(seconds=1),provenance=provenance)
    retrospective_derivation=create_historical_candle_probability_derivation(protocol=retrospective,activation=activation,
        opportunity=retro_opportunity,eligibility_context=retro_context,eligibility_result=retro_eligibility,schedule_history=retro_history,
        analysis_boundary=acquired+timedelta(seconds=1),manifest=manifest,manifests=(manifest,),candles=(candle,),home_participant_id=candle.home_participant_id,
        complement_outcome_id="synthetic-team:retro-away",effective_at=acquired+timedelta(seconds=2),provenance=provenance)
    retro_measurement=create_probability_source_measurement_v3(protocol=retrospective,activation=activation,opportunity=retro_opportunity,
        eligibility_context=retro_context,eligibility_result=retro_eligibility,schedule_history=retro_history,derivations=(retrospective_derivation,),
        outcome=retro_outcome,outcome_histories=(retro_history,),
        effective_at=retro_outcome.collected_at,provenance=provenance)
    retro_failure_schedule=replace(retro_schedule,observation_id="synthetic-schedule:retro-failure",canonical_event_id="synthetic-event:retro-failure",
        provider_event_id="synthetic-game:retro-failure",scheduled_start=retro_schedule.scheduled_start-timedelta(days=20),raw_evidence_sha256="3"*64,canonical_evidence_sha256="4"*64)
    retro_failure_history=OutcomeHistory(retro_failure_schedule.canonical_event_id,"mlb-stats-api",(retro_failure_schedule,))
    retro_failure_classification=_classification(retro_failure_schedule,provenance)
    retro_failure=ResearchCaptureOpportunity.create(retrospective.standalone_probability_source_protocol_id,retro_failure_schedule.observation_id,"winner")
    retro_failure_context,retro_failure_eligibility=create_standalone_eligibility_authority(protocol=retrospective,opportunity=retro_failure,
        outcome_history=retro_failure_history,classification=retro_failure_classification,classifications=(retro_failure_classification,),analysis_boundary=acquired+timedelta(seconds=1),provenance=provenance)
    retro_coverage=create_probability_source_coverage_v3(protocol=retrospective,analysis_boundary=retro_outcome.collected_at,activation=activation,
        opportunities=(retro_opportunity,retro_failure),eligibility_contexts=(retro_context,retro_failure_context),
        eligibility_results=(retro_eligibility,retro_failure_eligibility),schedule_histories=(retro_history,retro_failure_history,),
        classifications=(retro_classification,retro_failure_classification),
        manifests=(manifest,),candles=(candle,),historical_derivations=(retrospective_derivation,),measurements=(retro_measurement,),provenance=provenance)
    retro_performance=create_probability_source_performance_v3(protocol=retrospective,coverage=retro_coverage,
        measurements=(retro_measurement,),scope=PerformanceScope.CUMULATIVE,analysis_boundary=retro_outcome.collected_at,
        analysis_start=None,provenance=provenance)
    retro_window_start=retro_outcome.collected_at-timedelta(days=19)
    retro_bounded_coverage=create_probability_source_coverage_v3(protocol=retrospective,analysis_boundary=retro_outcome.collected_at,
        coverage_scope="time-bounded",window_start=retro_window_start,activation=activation,opportunities=(retro_opportunity,retro_failure),
        eligibility_contexts=(retro_context,retro_failure_context),eligibility_results=(retro_eligibility,retro_failure_eligibility),
        schedule_histories=(retro_history,retro_failure_history),classifications=(retro_classification,retro_failure_classification),manifests=(manifest,),candles=(candle,),historical_derivations=(retrospective_derivation,),measurements=(retro_measurement,),provenance=provenance)
    retro_bounded_performance=create_probability_source_performance_v3(protocol=retrospective,coverage=retro_bounded_coverage,
        measurements=(retro_measurement,),scope=PerformanceScope.TIME_BOUNDED,analysis_boundary=retro_outcome.collected_at,
        analysis_start=retro_window_start,provenance=provenance)
    retro_report=create_probability_source_performance_report(protocol=retrospective,cumulative=retro_performance,time_bounded=(retro_bounded_performance,),
        performances=(retro_performance,retro_bounded_performance),coverages=(retro_coverage,retro_bounded_coverage),analysis_boundary=retro_outcome.collected_at,
        report_boundary=retro_outcome.collected_at,descriptive_findings=("synthetic retrospective illustration only",),
        limitations=("not empirical research Evidence",),provenance=provenance)

    original_observation=legacy["observation"];series=legacy["series"];prospective_target=original_observation.collected_at
    captured_at=prospective_target+timedelta(minutes=1)
    observation=replace(original_observation,observation_id="synthetic-market-observation:slot-1",collected_at=captured_at,
        order_book=tuple(replace(x,collected_at=captured_at) for x in original_observation.order_book),
        component_evidence=tuple(replace(x,collected_at=captured_at) for x in original_observation.component_evidence),
        provenance=replace(original_observation.provenance,collected_at=captured_at))
    opportunity=ResearchCaptureOpportunity.create(prospective.standalone_probability_source_protocol_id,legacy["opportunity"].schedule_observation_id,"winner")
    prospective_schedule=next(x for x in legacy["outcome_history"].observations if x.observation_id==opportunity.schedule_observation_id)
    prospective_classification=_classification(prospective_schedule,provenance)
    prospective_context,prospective_eligibility=create_standalone_eligibility_authority(protocol=prospective,opportunity=opportunity,
        outcome_history=legacy["outcome_history"],classification=prospective_classification,classifications=(prospective_classification,),analysis_boundary=legacy["snapshot"].effective_at,provenance=provenance)
    prospective_failure_schedule=replace(next(x for x in legacy["outcome_history"].observations if x.observation_id==legacy["opportunity"].schedule_observation_id),
        observation_id="synthetic-schedule:prospective-failure",canonical_event_id="synthetic-event:prospective-failure",
        provider_event_id="synthetic-game:prospective-failure",scheduled_start=activation.activation_at+timedelta(hours=1),raw_evidence_sha256="5"*64,canonical_evidence_sha256="6"*64)
    prospective_failure_history=OutcomeHistory(prospective_failure_schedule.canonical_event_id,"mlb-stats-api",(prospective_failure_schedule,))
    prospective_failure_classification=_classification(prospective_failure_schedule,provenance)
    prospective_failure=ResearchCaptureOpportunity.create(prospective.standalone_probability_source_protocol_id,prospective_failure_schedule.observation_id,"winner")
    prospective_failure_context,prospective_failure_eligibility=create_standalone_eligibility_authority(protocol=prospective,opportunity=prospective_failure,
        outcome_history=prospective_failure_history,classification=prospective_failure_classification,classifications=(prospective_failure_classification,),analysis_boundary=legacy["snapshot"].effective_at,provenance=provenance)
    common=dict(protocol_id=prospective.standalone_probability_source_protocol_id,opportunity_id=opportunity.research_capture_opportunity_id,
        schedule_observation_id=opportunity.schedule_observation_id,canonical_event_id=observation.canonical_event_id,
        proposition_id=observation.proposition_id,home_participant_id=series.yes_semantic.participant_id,
        provider_market_id=observation.provider_market_id,target_at=prospective_target,provenance=provenance)
    first=ProspectiveCaptureAttempt.create(slot=0,invocation_at=prospective_target,provider_call_occurred=True,
        result=AcquisitionFailed(AttemptFailureCategory.TIMEOUT,"synthetic-call:slot-0"),effective_at=prospective_target,diagnostics=(),**common)
    success=ProspectiveCaptureAttempt.create(slot=1,invocation_at=captured_at,provider_call_occurred=True,
        result=CapturedValid("synthetic-raw:prospective","e"*64,observation.observation_id),effective_at=captured_at,diagnostics=(),**common)
    attempts=[first,success]
    for slot in range(2,5):
        at=prospective_target+timedelta(minutes=slot)
        attempts.append(ProspectiveCaptureAttempt.create(slot=slot,invocation_at=at,provider_call_occurred=False,
            result=SkippedAfterSuccess(success.prospective_capture_attempt_id),effective_at=at,diagnostics=(),**common))
    snapshot=reconcile_prospective_snapshot(protocol=prospective,opportunity=opportunity,activation=activation,
        eligibility_context=prospective_context,eligibility_result=prospective_eligibility,schedule_history=legacy["outcome_history"],
        analysis_boundary=legacy["snapshot"].effective_at,attempts=attempts,
        window_closed_at=prospective_target+timedelta(minutes=5),provenance=provenance)
    prospective_failure_target=prospective_failure_schedule.scheduled_start-timedelta(hours=6)
    failure_common=dict(protocol_id=prospective.standalone_probability_source_protocol_id,opportunity_id=prospective_failure.research_capture_opportunity_id,
        schedule_observation_id=prospective_failure.schedule_observation_id,canonical_event_id=prospective_failure_schedule.canonical_event_id,
        proposition_id=f"winner:{prospective_failure_schedule.canonical_event_id}:{prospective_failure_schedule.home_participant_id}",
        home_participant_id=prospective_failure_schedule.home_participant_id,provider_market_id="synthetic-prospective-failure-market",
        target_at=prospective_failure_target,provenance=provenance)
    prospective_failure_attempts=tuple(ProspectiveCaptureAttempt.create(slot=slot,invocation_at=prospective_failure_target+timedelta(minutes=5),
        provider_call_occurred=False,result=Missed(),effective_at=prospective_failure_target+timedelta(minutes=5),diagnostics=(),**failure_common) for slot in range(5))
    prospective_failure_snapshot=reconcile_prospective_snapshot(protocol=prospective,opportunity=prospective_failure,activation=activation,
        eligibility_context=prospective_failure_context,eligibility_result=prospective_failure_eligibility,schedule_history=prospective_failure_history,
        analysis_boundary=legacy["snapshot"].effective_at,attempts=prospective_failure_attempts,
        window_closed_at=prospective_failure_target+timedelta(minutes=5),provenance=provenance)
    prospective_derivation=create_standalone_market_probability_derivation(protocol=prospective,activation=activation,opportunity=opportunity,
        eligibility_context=prospective_context,eligibility_result=prospective_eligibility,schedule_history=legacy["outcome_history"],
        analysis_boundary=snapshot.effective_at,snapshot=snapshot,snapshots=(snapshot,),attempts=attempts,
        observation=observation,market_observations=(observation,),series=series,effective_at=snapshot.effective_at,provenance=provenance)
    prospective_measurement=create_probability_source_measurement_v3(protocol=prospective,activation=activation,opportunity=opportunity,
        eligibility_context=prospective_context,eligibility_result=prospective_eligibility,schedule_history=legacy["outcome_history"],snapshots=(snapshot,),
        derivations=(prospective_derivation,),outcome=legacy["outcome"],outcome_histories=(legacy["outcome_history"],),
        effective_at=legacy["outcome"].collected_at,provenance=provenance)
    prospective_coverage=create_probability_source_coverage_v3(protocol=prospective,analysis_boundary=legacy["outcome"].collected_at,
        activation=activation,opportunities=(opportunity,prospective_failure),eligibility_contexts=(prospective_context,prospective_failure_context),
        eligibility_results=(prospective_eligibility,prospective_failure_eligibility),schedule_histories=(legacy["outcome_history"],prospective_failure_history),
        classifications=(prospective_classification,prospective_failure_classification),attempts=tuple(attempts)+prospective_failure_attempts,
        snapshots=(snapshot,prospective_failure_snapshot),market_observations=(observation,),market_series=(series,),market_derivations=(prospective_derivation,),measurements=(prospective_measurement,),provenance=provenance)
    prospective_performance=create_probability_source_performance_v3(protocol=prospective,coverage=prospective_coverage,
        measurements=(prospective_measurement,),scope=PerformanceScope.CUMULATIVE,analysis_boundary=legacy["outcome"].collected_at,
        analysis_start=None,provenance=provenance)
    prospective_window_start=legacy["outcome"].scheduled_start-timedelta(hours=1)
    prospective_bounded_coverage=create_probability_source_coverage_v3(protocol=prospective,analysis_boundary=legacy["outcome"].collected_at,
        coverage_scope="time-bounded",window_start=prospective_window_start,activation=activation,opportunities=(opportunity,prospective_failure),
        eligibility_contexts=(prospective_context,prospective_failure_context),eligibility_results=(prospective_eligibility,prospective_failure_eligibility),
        schedule_histories=(legacy["outcome_history"],prospective_failure_history),classifications=(prospective_classification,prospective_failure_classification),attempts=tuple(attempts)+prospective_failure_attempts,snapshots=(snapshot,prospective_failure_snapshot),
        market_observations=(observation,),market_series=(series,),market_derivations=(prospective_derivation,),measurements=(prospective_measurement,),provenance=provenance)
    prospective_bounded_performance=create_probability_source_performance_v3(protocol=prospective,coverage=prospective_bounded_coverage,
        measurements=(prospective_measurement,),scope=PerformanceScope.TIME_BOUNDED,analysis_boundary=legacy["outcome"].collected_at,
        analysis_start=prospective_window_start,provenance=provenance)
    prospective_report=create_probability_source_performance_report(protocol=prospective,cumulative=prospective_performance,time_bounded=(prospective_bounded_performance,),
        performances=(prospective_performance,prospective_bounded_performance),coverages=(prospective_coverage,prospective_bounded_coverage),analysis_boundary=legacy["outcome"].collected_at,
        report_boundary=legacy["outcome"].collected_at,descriptive_findings=("synthetic prospective illustration only",),
        limitations=("not empirical research Evidence",),provenance=provenance)
    return locals()


def run()->str:
    g=build_synthetic_bundle()
    payload={"authority":"NON-AUTHORITATIVE SYNTHETIC PRODUCT PRESENTATION","combined_metric":None,
        "reports":[{"design":tag.value,"report_id":g[("retro" if tag is StandaloneDesignTag.RETROSPECTIVE else "prospective")+"_report"].probability_source_performance_report_id,
                    "sample_size":g[("retro" if tag is StandaloneDesignTag.RETROSPECTIVE else "prospective")+"_performance"].sample_size,
                    "coverage_rate":str(g[("retro" if tag is StandaloneDesignTag.RETROSPECTIVE else "prospective")+"_coverage"].coverage_rate)}
                   for tag in (StandaloneDesignTag.RETROSPECTIVE,StandaloneDesignTag.PROSPECTIVE)]}
    return json.dumps(payload,sort_keys=True,separators=(",",":"))


if __name__=="__main__": print(run())
