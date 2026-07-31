import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from event_contracts import (
    CandidateEvaluation,
    CanonicalEvent,
    ContractError,
    Evidence,
    NativeIdentifier,
    ParticipantRef,
    Provenance,
    ReasonCode,
    ReconciliationResult,
    ValidationReason,
)
from forecast_contracts import (
    AssumptionDisclosure,
    CollectionTiming,
    DocumentationReference,
    ForecastDistribution,
    ForecastIssueCode,
    ForecastMethodology,
    ForecastModel,
    ForecastObservation,
    ForecastOutcome,
    ForecastProvider,
    ForecastRelationship,
    ForecastRelationshipType,
    ForecastTimingEvaluation,
    ForecastValidationIssue,
    ForecastValidationStatus,
    ForecastVersion,
    MarketIndependence,
    ProbabilityScale,
    ProviderAssumption,
    ProviderDisposition,
    ProviderReportedAssumptions,
    PublishedProbability,
    VersionDisclosure,
    derive_forecast_state,
    evaluate_collection_timing,
    validate_forecast_hierarchy,
    validate_forecast_bundle,
    validate_observation_version,
)


UTC = timezone.utc
COLLECTED = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "forecast_contract_cases.json"


def event(event_id="mlb:777"):
    return CanonicalEvent(
        sport="baseball",
        competition="MLB",
        season="2026",
        canonical_event_id=event_id,
        participants=(
            ParticipantRef("team:away", "Away"),
            ParticipantRef("team:home", "Home"),
        ),
    )


def probability(outcome_id, value, source, precision=0, scale=ProbabilityScale.PERCENT, event_id="mlb:777"):
    return PublishedProbability(
        outcome=ForecastOutcome(outcome_id, outcome_id, event_id),
        probability=Decimal(value),
        source_representation=source,
        published_precision=precision,
        scale=scale,
    )


def distribution(event_id="mlb:777"):
    return ForecastDistribution(
        (
            probability("home-win", "0.55", "55%", event_id=event_id),
            probability("away-win", "0.45", "45%", event_id=event_id),
        )
    )


def reconciliation(event_id="mlb:777"):
    return ReconciliationResult.matched(
        NativeIdentifier("forecast-record", "source:1"),
        event(event_id),
        evidence=(Evidence("matchup", "Away at Home"),),
    )


def provenance(event_id="mlb:777"):
    return Provenance(
        provider="provider:example",
        source_record_id="source:1",
        canonical_event_id=event_id,
        collected_at=COLLECTED,
        raw_evidence_ref="sha256:abc",
        source_url="https://example.test/forecast/1",
        collector_version="fixture-adapter:1",
    )


def observation(**changes):
    values = dict(
        observation_id="forecast:1",
        version_id="version:1",
        reconciliation=reconciliation(),
        distribution=distribution(),
        assumptions=ProviderReportedAssumptions(AssumptionDisclosure.UNKNOWN),
        collected_at=COLLECTED,
        provenance=provenance(),
    )
    values.update(changes)
    return ForecastObservation(**values)


def relationship(
    kind=ForecastRelationshipType.CORRECTED_BY,
    *,
    relationship_id="rel:1",
    source_observation_id="forecast:1",
    source_version_id="version:1",
    target_record_id="forecast:2",
    event_id="mlb:777",
):
    return ForecastRelationship(
        relationship_id,
        kind,
        source_observation_id,
        source_version_id,
        target_record_id,
        event_id,
    )


class ForecastIdentityTests(unittest.TestCase):
    def test_provider_model_version_and_hierarchy(self):
        provider = ForecastProvider(
            "provider:example",
            "Example Forecasts",
            organization_name="Example Org",
            documentation=(DocumentationReference("method", "https://example.test/method"),),
            supported_competitions=("soccer:EPL", "baseball:MLB", "baseball:MLB"),
        )
        model = ForecastModel(
            "model:example",
            provider.provider_id,
            "Example Model",
            ForecastMethodology.STATISTICAL,
            MarketIndependence.INDEPENDENT,
        )
        version = ForecastVersion(
            "version:1",
            model.model_id,
            VersionDisclosure.KNOWN,
            provider_version_name="1.0",
            effective_date=date(2026, 1, 1),
        )
        validate_forecast_hierarchy(provider, model, version)
        self.assertEqual(
            provider.supported_competitions, ("baseball:MLB", "soccer:EPL")
        )
        self.assertEqual(ForecastProvider.from_json(provider.to_json()), provider)
        self.assertEqual(ForecastModel.from_json(model.to_json()), model)
        self.assertEqual(ForecastVersion.from_json(version.to_json()), version)

    def test_methodology_and_market_independence_are_distinct(self):
        model = ForecastModel(
            "model:hybrid",
            "provider:example",
            "Hybrid",
            ForecastMethodology.HYBRID,
            MarketIndependence.PARTIALLY_MARKET_INFORMED,
        )
        self.assertEqual(model.methodology.value, "hybrid")
        self.assertEqual(
            model.market_independence.value, "partially-market-informed"
        )

    def test_unknown_version_is_explicit(self):
        version = ForecastVersion.unknown(
            version_id="version:unknown", model_id="model:example"
        )
        self.assertIs(version.disclosure, VersionDisclosure.UNKNOWN)
        self.assertIsNone(version.provider_version_name)

    def test_version_metadata_contradictions_rejected(self):
        with self.assertRaises(ContractError):
            ForecastVersion("v", "m", VersionDisclosure.KNOWN)
        with self.assertRaises(ContractError):
            ForecastVersion(
                "v", "m", VersionDisclosure.UNKNOWN, provider_version_name="invented"
            )
        with self.assertRaises(ContractError):
            ForecastVersion(
                "v",
                "m",
                VersionDisclosure.KNOWN,
                provider_version_name="1",
                effective_date=date(2026, 2, 1),
                retired_date=date(2026, 1, 1),
            )

    def test_empty_identifiers_and_wrong_hierarchy_rejected(self):
        with self.assertRaises(ContractError):
            ForecastProvider("", "Provider")
        with self.assertRaises(ContractError):
            validate_forecast_hierarchy(
                ForecastProvider("p1", "P"),
                ForecastModel("m", "p2", "M", ForecastMethodology.UNKNOWN, MarketIndependence.UNKNOWN),
                ForecastVersion.unknown(version_id="v", model_id="m"),
            )

    def test_complete_identity_chain_rejects_each_incompatible_reference(self):
        provider = ForecastProvider("provider:example", "Provider")
        model = ForecastModel(
            "model:example",
            provider.provider_id,
            "Model",
            ForecastMethodology.UNKNOWN,
            MarketIndependence.UNKNOWN,
        )
        version = ForecastVersion.unknown(
            version_id="version:1", model_id=model.model_id
        )
        validate_forecast_bundle(provider, model, version, observation())
        with self.assertRaises(ContractError):
            validate_forecast_bundle(
                ForecastProvider("provider:other", "Other"),
                model,
                version,
                observation(),
            )
        with self.assertRaises(ContractError):
            validate_forecast_bundle(
                provider,
                ForecastModel(
                    "model:other",
                    provider.provider_id,
                    "Other",
                    ForecastMethodology.UNKNOWN,
                    MarketIndependence.UNKNOWN,
                ),
                version,
                observation(),
            )
        with self.assertRaises(ContractError):
            validate_forecast_bundle(
                provider,
                model,
                ForecastVersion.unknown(
                    version_id="version:other", model_id=model.model_id
                ),
                observation(),
            )

    def test_primary_identity_contracts_are_immutable(self):
        provider = ForecastProvider("p", "Provider")
        with self.assertRaises(FrozenInstanceError):
            provider.name = "Changed"


class ForecastDistributionTests(unittest.TestCase):
    def test_fixture_precision_cases(self):
        cases = json.loads(FIXTURE.read_text())["distributions"]
        for case in cases:
            with self.subTest(case=case["name"]):
                values = tuple(
                    probability(
                        item["outcome"],
                        item["value"],
                        item["source"],
                        item["precision"],
                        ProbabilityScale(item["scale"]),
                        case["event_id"],
                    )
                    for item in case["values"]
                )
                actual = ForecastDistribution(values)
                self.assertEqual(actual.validation_status.value, case["status"])

    def test_three_outcomes_and_arbitrary_count(self):
        values = ForecastDistribution(
            tuple(
                probability(name, value, source, event_id="soccer:1")
                for name, value, source in (
                    ("home-win", "0.40", "40%"),
                    ("draw", "0.30", "30%"),
                    ("away-win", "0.30", "30%"),
                )
            )
        )
        self.assertEqual(len(values.probabilities), 3)
        self.assertEqual(values.observed_total, Decimal("1.00"))

    def test_outcome_order_is_non_semantic_and_serialization_canonical(self):
        first = distribution()
        second = ForecastDistribution(tuple(reversed(first.probabilities)))
        self.assertEqual(first, second)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(ForecastDistribution.from_json(first.to_json()), first)

    def test_duplicate_and_mixed_event_outcomes_rejected(self):
        with self.assertRaises(ContractError):
            ForecastDistribution((probability("home", "0.5", "50%"), probability("home", "0.5", "50%")))
        with self.assertRaises(ContractError):
            ForecastDistribution((probability("home", "0.5", "50%"), probability("away", "0.5", "50%", event_id="mlb:other")))

    def test_exact_value_source_and_precision_preserved(self):
        values = (
            probability("a", "0.55", "55%", 0),
            probability("b", "0.55", "55.0%", 1),
            probability("c", "0.55", "0.55", 2, ProbabilityScale.PROPORTION),
            probability("d", "0.550", "0.550", 3, ProbabilityScale.PROPORTION),
        )
        self.assertEqual({item.probability for item in values}, {Decimal("0.55")})
        self.assertEqual(
            [item.source_representation for item in values],
            ["55%", "55.0%", "0.55", "0.550"],
        )
        self.assertEqual(
            [item.published_precision for item in values], [0, 1, 2, 3]
        )
        self.assertEqual(
            [item.rounding_half_interval for item in values],
            [Decimal("0.005"), Decimal("0.0005"), Decimal("0.005"), Decimal("0.0005")],
        )
        self.assertIn('"__decimal__":"0.55"', values[0].to_json())

    def test_invalid_probability_values_rejected(self):
        for value in (Decimal("-0.1"), Decimal("1.1"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(ContractError):
                probability("x", str(value), str(value), scale=ProbabilityScale.PROPORTION)

    def test_precision_tolerance_is_aggregate_rounding_error(self):
        coarse = ForecastDistribution((probability("a", "0.50", "50%"), probability("b", "0.49", "49%")))
        fine = ForecastDistribution((probability("a", "0.500", "50.0%", 1), probability("b", "0.490", "49.0%", 1)))
        self.assertEqual(coarse.precision_tolerance, Decimal("0.01"))
        self.assertEqual(fine.precision_tolerance, Decimal("0.001"))
        self.assertIs(coarse.validation_status, ForecastValidationStatus.VALID)
        self.assertIs(fine.validation_status, ForecastValidationStatus.INVALID)
        self.assertEqual(fine.observed_total, Decimal("0.990"))
        self.assertEqual(fine.probabilities[0].probability + fine.probabilities[1].probability, Decimal("0.990"))


class ForecastEvidenceTests(unittest.TestCase):
    def test_assumption_disclosures_and_round_trip(self):
        reported = ProviderReportedAssumptions(
            AssumptionDisclosure.REPORTED,
            (
                ProviderAssumption("lineup", "Expected lineup", "Posted lineup", "expected-lineup"),
                ProviderAssumption("pitcher", "Starting pitcher", "A. Pitcher", "starting-pitcher", "A. Pitcher (R)"),
            ),
        )
        self.assertEqual(ProviderReportedAssumptions.from_json(reported.to_json()), reported)
        self.assertEqual(ProviderReportedAssumptions(AssumptionDisclosure.UNKNOWN).assumptions, ())
        self.assertEqual(ProviderReportedAssumptions(AssumptionDisclosure.UNDISCLOSED).assumptions, ())

    def test_missing_assumptions_do_not_invalidate_observation(self):
        self.assertIs(observation().validation_status, ForecastValidationStatus.VALID)

    def test_timestamps_are_distinct_optional_and_aware(self):
        published = datetime(2026, 7, 31, 14, 0, tzinfo=UTC)
        item = observation(provider_published_at=published)
        self.assertEqual(item.provider_published_at, published)
        self.assertIsNone(item.provider_effective_at)
        self.assertIsNone(item.provider_updated_at)
        self.assertEqual(item.provenance.collector_version, "fixture-adapter:1")
        self.assertEqual(
            item.provenance.source_url, "https://example.test/forecast/1"
        )
        with self.assertRaises(ContractError):
            observation(provider_published_at=datetime(2026, 7, 31, 14, 0))

    def test_validation_and_disposition_are_separate(self):
        issue = ForecastValidationIssue(ForecastIssueCode.MATERIAL_INFORMATION_MISSING, "missing detail")
        item = observation(validation_status=ForecastValidationStatus.INCOMPLETE, validation_issues=(issue,), provider_disposition=ProviderDisposition.WITHDRAWN)
        self.assertIs(item.validation_status, ForecastValidationStatus.INCOMPLETE)
        self.assertIs(item.provider_disposition, ProviderDisposition.WITHDRAWN)

    def test_invalid_distribution_is_preserved_but_cannot_be_marked_valid(self):
        bad = ForecastDistribution((probability("home", "0.70", "70%"), probability("away", "0.40", "40%")))
        self.assertEqual(bad.observed_total, Decimal("1.10"))
        with self.assertRaises(ContractError):
            observation(distribution=bad)
        item = observation(distribution=bad, validation_status=ForecastValidationStatus.INVALID, validation_issues=bad.validation_issues)
        self.assertEqual(item.distribution.observed_total, Decimal("1.10"))

    def test_revision_relationships_are_immutable_and_latest_is_derived(self):
        original = observation()
        relation = relationship()
        state = derive_forecast_state(original, (relation,))
        revised = observation(observation_id="forecast:2")
        self.assertFalse(state.latest_known)
        self.assertIs(state.provider_disposition, ProviderDisposition.CORRECTED)
        self.assertTrue(derive_forecast_state(revised).latest_known)
        self.assertNotEqual(original.observation_id, revised.observation_id)
        self.assertEqual(original.distribution, revised.distribution)
        self.assertIs(original.provider_disposition, ProviderDisposition.ACTIVE)
        for kind in (ForecastRelationshipType.SUPERSEDED_BY, ForecastRelationshipType.CORRECTED_BY, ForecastRelationshipType.WITHDRAWN_BY):
            self.assertEqual(kind.value.endswith("-by"), True)

    def test_self_and_incompatible_relationships_rejected(self):
        with self.assertRaises(ContractError):
            relationship(source_observation_id="same", target_record_id="same")
        with self.assertRaises(ContractError):
            derive_forecast_state(
                observation(), (relationship(source_version_id="version:other"),)
            )
        with self.assertRaises(ContractError):
            derive_forecast_state(observation(), (relationship(event_id="mlb:other"),))

    def test_disposition_and_appended_relationship_evidence_are_consistent(self):
        corrected_claim = observation(provider_disposition=ProviderDisposition.CORRECTED)
        withdrawn_claim = observation(provider_disposition=ProviderDisposition.WITHDRAWN)
        self.assertFalse(derive_forecast_state(corrected_claim).latest_known)
        self.assertFalse(derive_forecast_state(withdrawn_claim).latest_known)
        active = observation()
        withdrawn = derive_forecast_state(
            active,
            (relationship(ForecastRelationshipType.WITHDRAWN_BY),),
        )
        self.assertIs(withdrawn.provider_disposition, ProviderDisposition.WITHDRAWN)
        self.assertIs(active.provider_disposition, ProviderDisposition.ACTIVE)
        with self.assertRaises(ContractError):
            derive_forecast_state(
                active,
                (
                    relationship(
                        ForecastRelationshipType.CORRECTED_BY,
                        relationship_id="rel:corrected",
                    ),
                    relationship(
                        ForecastRelationshipType.WITHDRAWN_BY,
                        relationship_id="rel:withdrawn",
                    ),
                ),
            )

    def test_observation_version_integrity(self):
        version = ForecastVersion.unknown(version_id="version:1", model_id="model:example")
        validate_observation_version(observation(), version)
        with self.assertRaises(ContractError):
            validate_observation_version(observation(), ForecastVersion.unknown(version_id="other", model_id="model:example"))

    def test_observation_round_trip_and_immutability(self):
        item = observation()
        self.assertEqual(ForecastObservation.from_json(item.to_json()), item)
        self.assertEqual(item.to_json(), item.to_json())
        with self.assertRaises(FrozenInstanceError):
            item.version_id = "changed"


class ForecastReconciliationAndTimingTests(unittest.TestCase):
    def test_ambiguous_reconciliation_preserves_candidates_and_selects_none(self):
        candidates = (event("mlb:777"), event("mlb:778"))
        reason = ValidationReason(ReasonCode.AMBIGUOUS_CANDIDATES, "doubleheader game unknown")
        ambiguous = ReconciliationResult.ambiguous(
            NativeIdentifier("forecast-record", "source:ambiguous"),
            candidates,
            evidence=(Evidence("matchup", "Away at Home"),),
            reasons=(reason,),
            candidate_evaluations=tuple(
                CandidateEvaluation(item.canonical_event_id, evidence=(Evidence("date", "2026-07-31"),), reasons=(reason,))
                for item in reversed(candidates)
            ),
        )
        unresolved_distribution = ForecastDistribution((probability("home-win", "0.55", "55%", event_id=None), probability("away-win", "0.45", "45%", event_id=None)))
        item = observation(reconciliation=ambiguous, distribution=unresolved_distribution, provenance=provenance(None))
        self.assertIsNone(item.reconciliation.matched_event)
        self.assertEqual(len(item.reconciliation.candidate_events), 2)
        self.assertIs(item.validation_status, ForecastValidationStatus.VALID)
        self.assertEqual(ForecastObservation.from_json(item.to_json()), item)

    def test_rejected_mapping_is_independent_from_forecast_validation(self):
        rejected = ReconciliationResult.rejected(
            NativeIdentifier("forecast-record", "source:rejected"),
            evidence=(Evidence("raw", "preserved"),),
            reasons=(ValidationReason(ReasonCode.NO_MATCHING_EVENT, "no event"),),
        )
        unresolved_distribution = ForecastDistribution((probability("yes", "0.5", "50%", event_id=None), probability("no", "0.5", "50%", event_id=None)))
        item = observation(reconciliation=rejected, distribution=unresolved_distribution, provenance=provenance(None))
        self.assertIs(item.validation_status, ForecastValidationStatus.VALID)

    def test_mismatched_event_rejected(self):
        with self.assertRaises(ContractError):
            observation(distribution=distribution("mlb:other"))

    def test_matched_reconciliation_rejects_unresolved_outcomes(self):
        unresolved = ForecastDistribution(
            (
                probability("home", "0.5", "50%", event_id=None),
                probability("away", "0.5", "50%", event_id=None),
            )
        )
        with self.assertRaises(ContractError):
            observation(distribution=unresolved)

    def test_mixed_mapped_and_unmapped_outcomes_rejected(self):
        with self.assertRaises(ContractError):
            ForecastDistribution(
                (
                    probability("home", "0.5", "50%"),
                    probability("away", "0.5", "50%", event_id=None),
                )
            )

    def test_timing_facts_before_at_after_and_unknown(self):
        start = datetime(2026, 7, 31, 16, 0, tzinfo=UTC)
        before = evaluate_collection_timing(COLLECTED, start, schedule_observation_id="schedule:1")
        at_start = evaluate_collection_timing(start, start)
        after = evaluate_collection_timing(datetime(2026, 7, 31, 17, 0, tzinfo=UTC), start)
        unknown = evaluate_collection_timing(COLLECTED, None)
        self.assertIs(before.timing, CollectionTiming.COLLECTED_BEFORE_START)
        self.assertIs(at_start.timing, CollectionTiming.COLLECTED_AT_OR_AFTER_START)
        self.assertIs(after.timing, CollectionTiming.COLLECTED_AT_OR_AFTER_START)
        self.assertIs(unknown.timing, CollectionTiming.START_TIME_UNKNOWN)
        self.assertFalse(hasattr(before, "wager_eligible"))
        self.assertEqual(ForecastTimingEvaluation.from_json(before.to_json()), before)

    def test_timing_rejects_naive_values(self):
        with self.assertRaises(ContractError):
            evaluate_collection_timing(datetime(2026, 7, 31, 15, 0), None)


if __name__ == "__main__":
    unittest.main()
