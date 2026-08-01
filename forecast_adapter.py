"""Provider-neutral local forecast snapshot boundary and append-only history."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from event_contracts import (
    CanonicalEvent,
    ContractError,
    ReasonCode,
    ReconciliationResult,
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
    _require_text,
)
from forecast_contracts import ForecastModel, ForecastObservation, ForecastProvider, ForecastVersion


@dataclass(frozen=True, slots=True)
class ForecastSeries:
    """Pops' Edge identity for one version's forecast of one event."""

    series_id: str
    provider_id: str
    model_id: str
    version_id: str
    canonical_event_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.series_id, "series_id"),
            (self.provider_id, "provider_id"),
            (self.model_id, "model_id"),
            (self.version_id, "version_id"),
            (self.canonical_event_id, "canonical_event_id"),
        ):
            _require_identifier(value, label)

    @classmethod
    def create(
        cls,
        provider: ForecastProvider,
        model: ForecastModel,
        version: ForecastVersion,
        event: CanonicalEvent,
    ) -> "ForecastSeries":
        if model.provider_id != provider.provider_id:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "forecast model does not belong to provider")
        if version.model_id != model.model_id:
            raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "forecast version does not belong to model")
        identity = f"forecast-series:{provider.provider_id}:{model.model_id}:{version.version_id}:{event.canonical_event_id}"
        return cls(identity, provider.provider_id, model.model_id, version.version_id, event.canonical_event_id)


@dataclass(frozen=True, slots=True)
class ForecastHistory:
    series: ForecastSeries
    observations: tuple[ForecastObservation, ...]

    def __post_init__(self) -> None:
        if not self.observations:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "a forecast series requires at least one observation")
        identifiers = [item.observation_id for item in self.observations]
        if len(identifiers) != len(set(identifiers)):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "forecast observation identifiers must be unique")
        for item in self.observations:
            if (
                item.provenance.provider != self.series.provider_id
                or item.version_id != self.series.version_id
                or item.distribution.canonical_event_id != self.series.canonical_event_id
            ):
                raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "observation conflicts with forecast series identity")
        object.__setattr__(self, "observations", tuple(sorted(self.observations, key=lambda item: (item.collected_at, item.observation_id))))

    def append(self, observation: ForecastObservation) -> "ForecastHistory":
        return ForecastHistory(self.series, self.observations + (observation,))

    @property
    def current(self) -> ForecastObservation:
        """Derived latest observation; it is not separately stored mutable state."""
        return self.observations[-1]


@dataclass(frozen=True, slots=True)
class RawForecastSnapshot:
    provider_id: str
    local_source_ref: str
    captured_at: datetime
    raw_sha256: str
    canonical_evidence_sha256: str
    parser_version: str
    canonical_source_url: str | None = None
    access_url: str | None = None
    provider_page_updated_at: datetime | None = None
    transformations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.provider_id, "snapshot provider_id")
        _require_text(self.local_source_ref, ReasonCode.VALIDATION_FAILURE, "local source reference")
        _require_aware(self.captured_at, "captured_at")
        if self.provider_page_updated_at is not None:
            _require_aware(self.provider_page_updated_at, "provider_page_updated_at")
        for label, digest in (("raw_sha256", self.raw_sha256), ("canonical_evidence_sha256", self.canonical_evidence_sha256)):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ContractError(ReasonCode.VALIDATION_FAILURE, f"{label} must be lowercase SHA-256")
        _require_identifier(self.parser_version, "parser_version")
        for value in (self.canonical_source_url, self.access_url):
            if value is not None:
                _require_text(value, ReasonCode.VALIDATION_FAILURE, "source URL")
        for value in self.transformations:
            _require_text(value, ReasonCode.VALIDATION_FAILURE, "snapshot transformation")


class ForecastAdapterOutcome(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True, order=True)
class ForecastAdapterIssue:
    code: str
    detail: str

    def __post_init__(self) -> None:
        _require_identifier(self.code, "adapter issue code")
        _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "adapter issue detail")


@dataclass(frozen=True, slots=True)
class ForecastAdapterResult:
    source_locator: str
    raw_evidence: RawForecastSnapshot
    outcome: ForecastAdapterOutcome
    reconciliation: ReconciliationResult | None = None
    series: ForecastSeries | None = None
    observation: ForecastObservation | None = None
    issues: tuple[ForecastAdapterIssue, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.source_locator, "source locator")
        object.__setattr__(self, "issues", tuple(sorted(set(self.issues))))
        if (self.series is None) != (self.observation is None):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "series and first observation must be emitted together")
        if self.outcome in (ForecastAdapterOutcome.AMBIGUOUS, ForecastAdapterOutcome.REJECTED) and self.series is not None:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "unresolved evidence cannot create a series")
        if self.outcome is ForecastAdapterOutcome.COMPLETE and (self.series is None or self.issues):
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "complete result requires an observation and no issues")
        if self.outcome is not ForecastAdapterOutcome.COMPLETE and not self.issues:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "non-complete result requires structured issues")


class ForecastAdapter(ABC):
    """Offline adapters parse supplied evidence and make no policy decisions."""

    @abstractmethod
    def parse_snapshot(self, path: str, *, captured_at: datetime, access_url: str | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def transform(self, evidence: Any, *, canonical_events: tuple[Any, ...]) -> tuple[ForecastAdapterResult, ...]:
        raise NotImplementedError


_CONTRACTS = (ForecastSeries, ForecastHistory, RawForecastSnapshot, ForecastAdapterIssue, ForecastAdapterResult)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict
    _contract.to_json = SerializableContract.to_json
    _contract.from_dict = SerializableContract.__dict__["from_dict"]
    _contract.from_json = SerializableContract.__dict__["from_json"]
_register(*_CONTRACTS, enums=(ForecastAdapterOutcome,))
