"""Immutable, provider-neutral external forecast contracts.

The contracts preserve provider evidence. They contain no provider approval,
weighting, freshness, market, edge, sizing, or wagering policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from event_contracts import (
    ContractError,
    Provenance,
    ReasonCode,
    ReconciliationOutcome,
    ReconciliationResult,
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)


class ForecastMethodology(str, Enum):
    STATISTICAL = "statistical"
    MARKET_DERIVED = "market-derived"
    HYBRID = "hybrid"
    EXPERT_JUDGMENT = "expert-judgment"
    COMPOSITE_EXTERNAL_FORECASTS = "composite-external-forecasts"
    UNKNOWN = "unknown"


class MarketIndependence(str, Enum):
    INDEPENDENT = "independent"
    PARTIALLY_MARKET_INFORMED = "partially-market-informed"
    MARKET_DERIVED = "market-derived"
    UNKNOWN = "unknown"


class ProviderLifecycle(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VersionDisclosure(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class ProbabilityScale(str, Enum):
    PROPORTION = "proportion"
    PERCENT = "percent"


class ForecastValidationStatus(str, Enum):
    VALID = "valid"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class ProviderDisposition(str, Enum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    WITHDRAWN = "withdrawn"


class AssumptionDisclosure(str, Enum):
    REPORTED = "reported"
    UNDISCLOSED = "undisclosed"
    UNKNOWN = "unknown"


class ForecastRelationshipType(str, Enum):
    SUPERSEDED_BY = "superseded-by"
    CORRECTED_BY = "corrected-by"
    WITHDRAWN_BY = "withdrawn-by"


class CollectionTiming(str, Enum):
    COLLECTED_BEFORE_START = "collected-before-start"
    COLLECTED_AT_OR_AFTER_START = "collected-at-or-after-start"
    START_TIME_UNKNOWN = "start-time-unknown"


class ForecastIssueCode(str, Enum):
    DISTRIBUTION_TOTAL_OUTSIDE_TOLERANCE = (
        "distribution-total-outside-precision-tolerance"
    )
    MATERIAL_INFORMATION_MISSING = "material-information-missing"
    MALFORMED_EXTERNAL_EVIDENCE = "malformed-external-evidence"


@dataclass(frozen=True, slots=True, order=True)
class DocumentationReference:
    label: str
    location: str

    def __post_init__(self) -> None:
        _require_text(self.label, ReasonCode.VALIDATION_FAILURE, "reference label")
        _require_text(
            self.location, ReasonCode.VALIDATION_FAILURE, "reference location"
        )


@dataclass(frozen=True, slots=True)
class ForecastProvider:
    provider_id: str
    name: str
    organization_name: str | None = None
    website: str | None = None
    documentation: tuple[DocumentationReference, ...] = ()
    supported_competitions: tuple[str, ...] = ()
    collection_method: str | None = None
    permitted_use_status: str | None = None
    typical_update_cadence: str | None = None
    lifecycle: ProviderLifecycle = ProviderLifecycle.ACTIVE

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "provider_id")
        _require_text(self.name, ReasonCode.VALIDATION_FAILURE, "provider name")
        _validate_optional_texts(
            self.organization_name,
            self.website,
            self.collection_method,
            self.permitted_use_status,
            self.typical_update_cadence,
        )
        object.__setattr__(
            self, "documentation", tuple(sorted(set(self.documentation)))
        )
        object.__setattr__(
            self,
            "supported_competitions",
            _canonical_text_values(self.supported_competitions, "competition"),
        )


@dataclass(frozen=True, slots=True)
class ForecastModel:
    model_id: str
    provider_id: str
    name: str
    methodology: ForecastMethodology
    market_independence: MarketIndependence
    description: str | None = None
    supported_competitions: tuple[str, ...] = ()
    documentation: tuple[DocumentationReference, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.model_id, "model_id")
        _require_identifier(self.provider_id, "provider_id")
        _require_text(self.name, ReasonCode.VALIDATION_FAILURE, "model name")
        _validate_optional_texts(self.description)
        object.__setattr__(
            self,
            "supported_competitions",
            _canonical_text_values(self.supported_competitions, "competition"),
        )
        object.__setattr__(
            self, "documentation", tuple(sorted(set(self.documentation)))
        )


@dataclass(frozen=True, slots=True)
class ForecastVersion:
    version_id: str
    model_id: str
    disclosure: VersionDisclosure
    provider_version_name: str | None = None
    effective_date: date | None = None
    retired_date: date | None = None
    methodology_notes: str | None = None
    release_notes: str | None = None
    calibration_notes: str | None = None
    documentation: tuple[DocumentationReference, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.version_id, "version_id")
        _require_identifier(self.model_id, "model_id")
        if self.disclosure is VersionDisclosure.KNOWN:
            if self.provider_version_name is None:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "known forecast versions require a provider version name",
                )
        elif self.provider_version_name is not None:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "unknown forecast versions cannot claim a provider version name",
            )
        _validate_optional_texts(
            self.provider_version_name,
            self.methodology_notes,
            self.release_notes,
            self.calibration_notes,
        )
        if (
            self.effective_date is not None
            and self.retired_date is not None
            and self.retired_date < self.effective_date
        ):
            raise ContractError(
                ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY,
                "forecast version retirement cannot precede its effective date",
            )
        object.__setattr__(
            self, "documentation", tuple(sorted(set(self.documentation)))
        )

    @classmethod
    def unknown(cls, *, version_id: str, model_id: str) -> "ForecastVersion":
        return cls(
            version_id=version_id,
            model_id=model_id,
            disclosure=VersionDisclosure.UNKNOWN,
        )


@dataclass(frozen=True, slots=True, order=True)
class ForecastOutcome:
    outcome_id: str
    semantic: str
    canonical_event_id: str | None
    provider_label: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.outcome_id, "outcome_id")
        _require_identifier(self.semantic, "outcome semantic")
        if self.canonical_event_id is not None:
            _require_identifier(self.canonical_event_id, "canonical_event_id")
        _validate_optional_texts(self.provider_label)


@dataclass(frozen=True, slots=True)
class PublishedProbability:
    outcome: ForecastOutcome
    probability: Decimal
    source_representation: str
    published_precision: int
    scale: ProbabilityScale

    def __post_init__(self) -> None:
        if not isinstance(self.probability, Decimal) or not self.probability.is_finite():
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "published probability must be a finite Decimal",
            )
        if self.probability < 0 or self.probability > 1:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "published probability must be between zero and one",
            )
        _require_text(
            self.source_representation,
            ReasonCode.VALIDATION_FAILURE,
            "probability source representation",
        )
        if (
            not isinstance(self.published_precision, int)
            or isinstance(self.published_precision, bool)
            or self.published_precision < 0
        ):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "published_precision must be a non-negative integer",
            )

    @property
    def rounding_half_interval(self) -> Decimal:
        """Maximum rounding error implied by the declared source precision.

        Precision is decimal places in the published scale. A value published
        to ``p`` places has quantum ``10**-p`` and may be displaced by half a
        quantum. Percent-scale values are divided by 100 when converted to the
        stored [0, 1] probability.
        """

        quantum = Decimal(1).scaleb(-self.published_precision)
        if self.scale is ProbabilityScale.PERCENT:
            quantum /= Decimal(100)
        return quantum / Decimal(2)


@dataclass(frozen=True, slots=True)
class ForecastDistribution:
    probabilities: tuple[PublishedProbability, ...]

    def __post_init__(self) -> None:
        if len(self.probabilities) < 2:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "a contest forecast requires at least two outcomes",
            )
        outcome_ids = [item.outcome.outcome_id for item in self.probabilities]
        if len(set(outcome_ids)) != len(outcome_ids):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "forecast outcome identifiers must be unique",
            )
        event_ids = {item.outcome.canonical_event_id for item in self.probabilities}
        if len(event_ids) != 1:
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "all forecast outcomes must share one event reference",
            )
        object.__setattr__(
            self,
            "probabilities",
            tuple(sorted(self.probabilities, key=lambda item: item.outcome.outcome_id)),
        )

    @property
    def canonical_event_id(self) -> str | None:
        return self.probabilities[0].outcome.canonical_event_id

    @property
    def observed_total(self) -> Decimal:
        return sum(
            (item.probability for item in self.probabilities), start=Decimal(0)
        )

    @property
    def precision_tolerance(self) -> Decimal:
        return sum(
            (item.rounding_half_interval for item in self.probabilities),
            start=Decimal(0),
        )

    @property
    def validation_status(self) -> ForecastValidationStatus:
        if abs(self.observed_total - Decimal(1)) <= self.precision_tolerance:
            return ForecastValidationStatus.VALID
        return ForecastValidationStatus.INVALID

    @property
    def validation_issues(self) -> tuple["ForecastValidationIssue", ...]:
        if self.validation_status is ForecastValidationStatus.VALID:
            return ()
        return (
            ForecastValidationIssue(
                code=ForecastIssueCode.DISTRIBUTION_TOTAL_OUTSIDE_TOLERANCE,
                detail=(
                    f"observed total {self.observed_total} differs from 1 by more "
                    f"than precision tolerance {self.precision_tolerance}"
                ),
            ),
        )


@dataclass(frozen=True, slots=True, order=True)
class ProviderAssumption:
    assumption_id: str
    provider_label: str
    provider_value: str
    assumption_type: str | None = None
    source_representation: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.assumption_id, "assumption_id")
        _require_text(
            self.provider_label, ReasonCode.VALIDATION_FAILURE, "assumption label"
        )
        _require_text(
            self.provider_value, ReasonCode.VALIDATION_FAILURE, "assumption value"
        )
        if self.assumption_type is not None:
            _require_identifier(self.assumption_type, "assumption_type")
        _validate_optional_texts(self.source_representation)


@dataclass(frozen=True, slots=True)
class ProviderReportedAssumptions:
    disclosure: AssumptionDisclosure
    assumptions: tuple[ProviderAssumption, ...] = ()
    source_representation: str | None = None

    def __post_init__(self) -> None:
        if self.disclosure is AssumptionDisclosure.REPORTED and not self.assumptions:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "reported assumptions require at least one preserved assumption",
            )
        if self.disclosure is not AssumptionDisclosure.REPORTED and self.assumptions:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "unknown or undisclosed assumptions cannot contain reported values",
            )
        ids = [item.assumption_id for item in self.assumptions]
        if len(ids) != len(set(ids)):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE, "assumption identifiers must be unique"
            )
        object.__setattr__(self, "assumptions", tuple(sorted(self.assumptions)))
        _validate_optional_texts(self.source_representation)


@dataclass(frozen=True, slots=True, order=True)
class ForecastValidationIssue:
    code: ForecastIssueCode
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "issue detail")


@dataclass(frozen=True, slots=True)
class ForecastRelationship:
    relationship_id: str
    relationship_type: ForecastRelationshipType
    from_observation_id: str
    from_version_id: str
    to_record_id: str
    canonical_event_id: str | None

    def __post_init__(self) -> None:
        for value, label in (
            (self.relationship_id, "relationship_id"),
            (self.from_observation_id, "from_observation_id"),
            (self.from_version_id, "from_version_id"),
            (self.to_record_id, "to_record_id"),
        ):
            _require_identifier(value, label)
        if self.canonical_event_id is not None:
            _require_identifier(self.canonical_event_id, "canonical_event_id")
        if self.from_observation_id == self.to_record_id:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "forecast relationships cannot reference themselves",
            )


@dataclass(frozen=True, slots=True)
class ForecastObservation:
    observation_id: str
    version_id: str
    reconciliation: ReconciliationResult
    distribution: ForecastDistribution
    assumptions: ProviderReportedAssumptions
    collected_at: datetime
    provenance: Provenance
    provider_published_at: datetime | None = None
    provider_effective_at: datetime | None = None
    provider_updated_at: datetime | None = None
    schedule_observation_id: str | None = None
    validation_status: ForecastValidationStatus = ForecastValidationStatus.VALID
    validation_issues: tuple[ForecastValidationIssue, ...] = ()
    provider_disposition: ProviderDisposition = ProviderDisposition.ACTIVE

    def __post_init__(self) -> None:
        for value, label in (
            (self.observation_id, "observation_id"),
            (self.version_id, "version_id"),
        ):
            _require_identifier(value, label)
        _require_aware(self.collected_at, "collected_at")
        for timestamp, label in (
            (self.provider_published_at, "provider_published_at"),
            (self.provider_effective_at, "provider_effective_at"),
            (self.provider_updated_at, "provider_updated_at"),
        ):
            if timestamp is not None:
                _require_aware(timestamp, label)
        if self.schedule_observation_id is not None:
            _require_identifier(self.schedule_observation_id, "schedule_observation_id")
        if self.provenance.collected_at != self.collected_at:
            raise ContractError(
                ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY,
                "forecast collection timestamp conflicts with provenance",
            )
        if self.reconciliation.outcome is ReconciliationOutcome.MATCHED:
            matched_id = self.reconciliation.matched_event.canonical_event_id
            if self.distribution.canonical_event_id != matched_id:
                raise ContractError(
                    ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                    "forecast distribution conflicts with matched event",
                )
            if self.provenance.canonical_event_id != matched_id:
                raise ContractError(
                    ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                    "forecast provenance conflicts with matched event",
                )
        elif self.distribution.canonical_event_id is not None:
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "unresolved reconciliation cannot claim a canonical event",
            )
        if self.validation_status is ForecastValidationStatus.VALID:
            if self.validation_issues:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "valid forecast observations cannot carry validation issues",
                )
            if self.distribution.validation_status is not ForecastValidationStatus.VALID:
                raise ContractError(
                    ReasonCode.VALIDATION_FAILURE,
                    "an inconsistent distribution cannot be marked valid",
                )
        elif not self.validation_issues:
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "incomplete or invalid observations require validation issues",
            )
        if (
            self.distribution.validation_status is ForecastValidationStatus.INVALID
            and self.validation_status is not ForecastValidationStatus.INVALID
        ):
            raise ContractError(
                ReasonCode.VALIDATION_FAILURE,
                "a materially inconsistent distribution requires invalid validation",
            )
        object.__setattr__(
            self, "validation_issues", tuple(sorted(self.validation_issues))
        )


@dataclass(frozen=True, slots=True)
class DerivedForecastState:
    latest_known: bool
    provider_disposition: ProviderDisposition
    relationships: tuple[ForecastRelationship, ...]


def derive_forecast_state(
    observation: ForecastObservation,
    relationships: tuple[ForecastRelationship, ...] = (),
) -> DerivedForecastState:
    """Validate appended relationship evidence and derive current local state.

    Relationships are separate immutable records, so discovering a correction
    or withdrawal never rewrites the original Forecast Observation. This helper
    validates only the supplied offline evidence; global graph validation
    remains a future persistence concern.
    """

    ordered = tuple(sorted(relationships, key=lambda item: item.relationship_id))
    relationship_ids = [item.relationship_id for item in ordered]
    if len(relationship_ids) != len(set(relationship_ids)):
        raise ContractError(
            ReasonCode.CONTRADICTORY_LINEAGE,
            "forecast relationship identifiers must be unique",
        )
    kinds = {item.relationship_type for item in ordered}
    if (
        ForecastRelationshipType.CORRECTED_BY in kinds
        and ForecastRelationshipType.WITHDRAWN_BY in kinds
    ):
        raise ContractError(
            ReasonCode.CONTRADICTORY_LINEAGE,
            "an observation cannot be both corrected and withdrawn by appended evidence",
        )
    for relationship in ordered:
        if relationship.from_observation_id != observation.observation_id:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "relationship source must be the supplied forecast observation",
            )
        if relationship.from_version_id != observation.version_id:
            raise ContractError(
                ReasonCode.CONFLICTING_SOURCE_MAPPING,
                "relationship version conflicts with the forecast observation",
            )
        if relationship.canonical_event_id != observation.distribution.canonical_event_id:
            raise ContractError(
                ReasonCode.CONFLICTING_NATIVE_IDENTITY,
                "relationship event conflicts with the forecast observation",
            )
    disposition = observation.provider_disposition
    if ForecastRelationshipType.WITHDRAWN_BY in kinds:
        if disposition is ProviderDisposition.CORRECTED:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "corrected provider disposition conflicts with withdrawal evidence",
            )
        disposition = ProviderDisposition.WITHDRAWN
    elif ForecastRelationshipType.CORRECTED_BY in kinds:
        if disposition is ProviderDisposition.WITHDRAWN:
            raise ContractError(
                ReasonCode.CONTRADICTORY_LINEAGE,
                "withdrawn provider disposition conflicts with correction evidence",
            )
        disposition = ProviderDisposition.CORRECTED
    latest_known = disposition is ProviderDisposition.ACTIVE and not kinds.intersection(
        {
            ForecastRelationshipType.SUPERSEDED_BY,
            ForecastRelationshipType.CORRECTED_BY,
            ForecastRelationshipType.WITHDRAWN_BY,
        }
    )
    return DerivedForecastState(latest_known, disposition, ordered)


@dataclass(frozen=True, slots=True)
class ForecastTimingEvaluation:
    timing: CollectionTiming
    collected_at: datetime
    scheduled_start: datetime | None
    schedule_observation_id: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.collected_at, "collected_at")
        if self.scheduled_start is not None:
            _require_aware(self.scheduled_start, "scheduled_start")
        if self.schedule_observation_id is not None:
            _require_identifier(self.schedule_observation_id, "schedule_observation_id")


def evaluate_collection_timing(
    collected_at: datetime,
    scheduled_start: datetime | None,
    *,
    schedule_observation_id: str | None = None,
) -> ForecastTimingEvaluation:
    _require_aware(collected_at, "collected_at")
    if scheduled_start is None:
        timing = CollectionTiming.START_TIME_UNKNOWN
    else:
        _require_aware(scheduled_start, "scheduled_start")
        timing = (
            CollectionTiming.COLLECTED_BEFORE_START
            if collected_at < scheduled_start
            else CollectionTiming.COLLECTED_AT_OR_AFTER_START
        )
    return ForecastTimingEvaluation(
        timing=timing,
        collected_at=collected_at,
        scheduled_start=scheduled_start,
        schedule_observation_id=schedule_observation_id,
    )


def validate_forecast_hierarchy(
    provider: ForecastProvider, model: ForecastModel, version: ForecastVersion
) -> None:
    """Validate references when a durable hierarchy is assembled offline."""

    if model.provider_id != provider.provider_id:
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "forecast model does not reference the supplied provider",
        )
    if version.model_id != model.model_id:
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "forecast version does not reference the supplied model",
        )


def validate_observation_version(
    observation: ForecastObservation, version: ForecastVersion
) -> None:
    if observation.version_id != version.version_id:
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "forecast observation does not reference the supplied version",
        )


def validate_forecast_bundle(
    provider: ForecastProvider,
    model: ForecastModel,
    version: ForecastVersion,
    observation: ForecastObservation,
) -> None:
    """Validate the complete Provider → Model → Version → Observation chain."""

    validate_forecast_hierarchy(provider, model, version)
    validate_observation_version(observation, version)
    if observation.provenance.provider != provider.provider_id:
        raise ContractError(
            ReasonCode.CONFLICTING_SOURCE_MAPPING,
            "forecast provenance does not reference the supplied provider",
        )


def _canonical_text_values(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    for value in values:
        _require_identifier(value, label)
    return tuple(sorted(set(values)))


def _validate_optional_texts(*values: str | None) -> None:
    for value in values:
        if value is not None:
            _require_text(value, ReasonCode.VALIDATION_FAILURE, "optional metadata")


_CONTRACTS = (
    DocumentationReference,
    ForecastProvider,
    ForecastModel,
    ForecastVersion,
    ForecastOutcome,
    PublishedProbability,
    ForecastDistribution,
    ProviderAssumption,
    ProviderReportedAssumptions,
    ForecastValidationIssue,
    ForecastRelationship,
    ForecastObservation,
    DerivedForecastState,
    ForecastTimingEvaluation,
)

for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(
    *_CONTRACTS,
    enums=(
        ForecastMethodology,
        MarketIndependence,
        ProviderLifecycle,
        VersionDisclosure,
        ProbabilityScale,
        ForecastValidationStatus,
        ProviderDisposition,
        AssumptionDisclosure,
        ForecastRelationshipType,
        CollectionTiming,
        ForecastIssueCode,
    ),
)
