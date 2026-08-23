"""Immutable PR13 Forecast Intelligence research contracts.

This module defines scientific specifications and historical research artifacts.
It deliberately contains no provider acquisition, applicability replay, policy,
governance, workspace, opportunity, or execution behavior.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Mapping

from event_contracts import (
    ContractError,
    ReasonCode,
    SerializableContract,
    _register,
    _require_aware,
    _require_identifier,
)


RESEARCH_CONTRACT_SCHEMA_VERSION = "1"
RESEARCH_IDENTITY_ALGORITHM_VERSION = "1"
DRIFT_ANALYSIS_ALGORITHM_VERSION = "1"


def _fail(detail: str, code: ReasonCode = ReasonCode.VALIDATION_FAILURE) -> None:
    raise ContractError(code, detail)


def _utc(value: datetime) -> str:
    _require_aware(value, "identity datetime")
    return value.astimezone(timezone.utc).isoformat()


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"datetime_utc": _utc(value)}
    if isinstance(value, Decimal):
        if not value.is_finite():
            _fail("scientific Decimal values must be finite")
        return {"decimal": str(value)}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, float):
        _fail("binary float cannot participate in PR13 scientific identity")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported PR13 identity value: {type(value).__name__}")


def _digest(material: object) -> str:
    payload = json.dumps(_canonical(material), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ordered_unique(values: Iterable[Any], label: str, *, key=lambda item: item) -> tuple[Any, ...]:
    supplied = tuple(values)
    keys = tuple(key(item) for item in supplied)
    if len(keys) != len(set(keys)):
        _fail(f"{label} contains duplicate values")
    return tuple(item for _, item in sorted(zip(keys, supplied), key=lambda pair: pair[0]))


def _require_versions(schema_version: str, identity_algorithm_version: str) -> None:
    if schema_version != RESEARCH_CONTRACT_SCHEMA_VERSION:
        _fail("unsupported research contract schema version")
    if identity_algorithm_version != RESEARCH_IDENTITY_ALGORITHM_VERSION:
        _fail("unsupported research identity algorithm version")


class RulePurpose(str, Enum):
    PROBABILITY_REPRESENTATION = "probability-representation"
    PROBABILITY_TRANSFORMATION = "probability-transformation"
    SOURCE_AVAILABILITY = "source-availability"
    POPULATION_TEMPORAL_SCOPE = "population-temporal-scope"
    EVENT_STATUS_ELIGIBILITY = "event-status-eligibility"
    POSTSEASON_TREATMENT = "postseason-treatment"
    POSTPONEMENT_TREATMENT = "postponement-treatment"
    CANCELLATION_TREATMENT = "cancellation-treatment"
    RESCHEDULING_TREATMENT = "rescheduling-treatment"
    POPULATION_INCLUSION = "population-inclusion"
    POPULATION_EXCLUSION = "population-exclusion"
    SNAPSHOT_TIMING = "snapshot-timing"
    CAPTURE_TOLERANCE = "capture-tolerance"
    SYNCHRONIZATION = "synchronization"
    EVENT_COMPATIBILITY = "event-compatibility"
    OUTCOME_RESOLUTION = "outcome-resolution"
    DIMENSION_CLASSIFICATION = "dimension-classification"
    PRIMARY_MEASURE = "primary-measure"
    SUPPORTING_MEASURE = "supporting-measure"
    STATISTICAL_METHOD = "statistical-method"
    PRACTICAL_SIGNIFICANCE = "practical-significance"
    BURDEN_OF_PROOF = "burden-of-proof"
    SURVEILLANCE_WINDOW = "surveillance-window"
    DRIFT_CLASSIFICATION = "drift-classification"
    DRIFT_MATERIAL_EVENT_MAPPING = "drift-material-event-mapping"


@dataclass(frozen=True, slots=True)
class _ParameterDefinition:
    value_type: type | tuple[type, ...]
    required: bool = True
    minimum: int | Decimal | None = None
    maximum: int | Decimal | None = None
    allowed: tuple[Any, ...] = ()
    tuple_order_nonmaterial: bool = False


_RULE_SCHEMAS: dict[tuple[RulePurpose, str, str], dict[str, _ParameterDefinition]] = {
    (RulePurpose.PROBABILITY_REPRESENTATION, "direct-probability", "1"): {},
    (RulePurpose.PROBABILITY_TRANSFORMATION, "identity-probability", "1"): {},
    (RulePurpose.SOURCE_AVAILABILITY, "required-at-snapshot", "1"): {},
    (RulePurpose.POPULATION_TEMPORAL_SCOPE, "season-range", "1"): {
        "first_season": _ParameterDefinition(str), "last_season": _ParameterDefinition(str),
    },
    (RulePurpose.EVENT_STATUS_ELIGIBILITY, "allowed-event-statuses", "1"): {
        "statuses": _ParameterDefinition(tuple, tuple_order_nonmaterial=True),
    },
    (RulePurpose.POSTSEASON_TREATMENT, "postseason-treatment", "1"): {
        "include": _ParameterDefinition(bool),
    },
    (RulePurpose.POSTPONEMENT_TREATMENT, "postponement-treatment", "1"): {
        "action": _ParameterDefinition(str, allowed=("exclude", "retain-if-rescheduled")),
    },
    (RulePurpose.CANCELLATION_TREATMENT, "cancellation-treatment", "1"): {
        "action": _ParameterDefinition(str, allowed=("exclude",)),
    },
    (RulePurpose.RESCHEDULING_TREATMENT, "rescheduling-treatment", "1"): {
        "action": _ParameterDefinition(str, allowed=("use-current-schedule", "exclude")),
    },
    (RulePurpose.POPULATION_INCLUSION, "include-all-otherwise-eligible", "1"): {},
    (RulePurpose.POPULATION_EXCLUSION, "exclude-none-additional", "1"): {},
    (RulePurpose.SNAPSHOT_TIMING, "pregame-offset", "1"): {
        "seconds_before_start": _ParameterDefinition(int, minimum=0),
    },
    (RulePurpose.CAPTURE_TOLERANCE, "symmetric-capture-tolerance", "1"): {
        "seconds": _ParameterDefinition(int, minimum=0),
    },
    (RulePurpose.SYNCHRONIZATION, "maximum-pair-separation", "1"): {
        "seconds": _ParameterDefinition(int, minimum=0),
    },
    (RulePurpose.EVENT_COMPATIBILITY, "canonical-event-proposition", "1"): {},
    (RulePurpose.OUTCOME_RESOLUTION, "authoritative-outcome-source", "1"): {
        "source_id": _ParameterDefinition(str),
    },
    (RulePurpose.DIMENSION_CLASSIFICATION, "snapshot-partition", "1"): {
        "partition_keys": _ParameterDefinition(tuple, tuple_order_nonmaterial=True),
    },
    (RulePurpose.PRIMARY_MEASURE, "brier-score-improvement", "1"): {
        "favorable_direction": _ParameterDefinition(str, allowed=("positive",)),
    },
    (RulePurpose.SUPPORTING_MEASURE, "log-loss-safeguard", "1"): {},
    (RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "1"): {},
    (RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "2"): {
        "bin_boundaries": _ParameterDefinition(tuple),
    },
    (RulePurpose.STATISTICAL_METHOD, "paired-bootstrap", "1"): {
        "confidence_level": _ParameterDefinition(
            Decimal, minimum=Decimal("0"), maximum=Decimal("1")
        ),
        "resamples": _ParameterDefinition(int, minimum=1),
    },
    (RulePurpose.PRACTICAL_SIGNIFICANCE, "minimum-brier-improvement", "1"): {
        "minimum_improvement": _ParameterDefinition(Decimal, minimum=Decimal("0")),
    },
    (RulePurpose.BURDEN_OF_PROOF, "complete-empirical-burden", "1"): {
        "required_checks": _ParameterDefinition(tuple, tuple_order_nonmaterial=True),
    },
    (RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "1"): {
        "days": _ParameterDefinition(int, minimum=1),
    },
    (RulePurpose.SURVEILLANCE_WINDOW, "rolling-days", "2"): {
        "days": _ParameterDefinition(int, minimum=1),
    },
    (RulePurpose.DRIFT_CLASSIFICATION, "brier-deterioration", "1"): {
        "threshold": _ParameterDefinition(Decimal, minimum=Decimal("0")),
    },
    (RulePurpose.DRIFT_CLASSIFICATION, "brier-deterioration", "2"): {
        "threshold": _ParameterDefinition(Decimal, minimum=Decimal("0"), maximum=Decimal("2")),
    },
    (RulePurpose.DRIFT_MATERIAL_EVENT_MAPPING, "drift-disposition-material-events", "1"): {
        "qualifying_dispositions": _ParameterDefinition(tuple, tuple_order_nonmaterial=True),
    },
}


RuleParameterValue = str | int | bool | Decimal | tuple[str, ...] | tuple[Decimal, ...]


@dataclass(frozen=True, slots=True, order=True)
class RuleParameter:
    name: str
    value: RuleParameterValue

    def __post_init__(self) -> None:
        _require_identifier(self.name, "rule parameter name")
        if isinstance(self.value, float):
            _fail("rule parameters do not accept binary float")
        if isinstance(self.value, Decimal) and not self.value.is_finite():
            _fail("rule Decimal parameter must be finite")
        if isinstance(self.value, tuple):
            if not self.value:
                _fail("rule tuple parameters must not be empty")
            if all(isinstance(item, str) and item for item in self.value):
                pass
            elif all(isinstance(item, Decimal) and item.is_finite() for item in self.value):
                pass
            else:
                _fail("rule tuple parameters require homogeneous nonempty strings or finite Decimals")
        elif not isinstance(self.value, (str, int, bool, Decimal)):
            _fail("unsupported rule parameter type")


def _validated_parameters(purpose: RulePurpose, rule_id: str, rule_version: str,
                          parameters: Iterable[RuleParameter]) -> tuple[RuleParameter, ...]:
    try:
        schema = _RULE_SCHEMAS[(purpose, rule_id, rule_version)]
    except KeyError as error:
        raise ContractError(ReasonCode.UNSUPPORTED_STATUS, "unsupported PR13 scientific rule") from error
    supplied = tuple(parameters)
    names = tuple(item.name for item in supplied)
    if len(names) != len(set(names)):
        _fail("rule contains duplicate parameter names")
    if set(names) != {name for name, definition in schema.items() if definition.required}:
        unknown = set(names) - set(schema)
        missing = {name for name, definition in schema.items() if definition.required} - set(names)
        _fail(f"rule parameter schema mismatch; unknown={sorted(unknown)} missing={sorted(missing)}")
    normalized = []
    for item in supplied:
        definition = schema[item.name]
        value = item.value
        if definition.value_type is int:
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        elif definition.value_type is bool:
            valid_type = isinstance(value, bool)
        else:
            valid_type = isinstance(value, definition.value_type)
        if not valid_type:
            _fail(f"rule parameter {item.name} has the wrong type")
        if definition.minimum is not None and value < definition.minimum:
            _fail(f"rule parameter {item.name} is below its minimum")
        if definition.maximum is not None and value > definition.maximum:
            _fail(f"rule parameter {item.name} is above its maximum")
        if isinstance(value, str) and not value:
            _fail(f"rule parameter {item.name} must not be empty")
        if definition.allowed and value not in definition.allowed:
            _fail(f"rule parameter {item.name} has an unsupported value")
        if isinstance(value, tuple):
            if len(value) != len(set(value)):
                _fail(f"rule parameter {item.name} contains duplicates")
            if definition.tuple_order_nonmaterial:
                value = tuple(sorted(value))
        normalized.append(RuleParameter(item.name, value))
    if purpose is RulePurpose.DRIFT_MATERIAL_EVENT_MAPPING:
        dispositions = {item.name: item.value for item in normalized}[
            "qualifying_dispositions"
        ]
        valid_dispositions = {item.value for item in DriftDisposition}
        if not dispositions or any(item not in valid_dispositions for item in dispositions):
            _fail("drift material-event mapping must identify valid Drift dispositions")
    if (purpose, rule_id, rule_version) == (
        RulePurpose.SUPPORTING_MEASURE, "calibration-safeguard", "2"
    ):
        boundaries = {item.name: item.value for item in normalized}["bin_boundaries"]
        expected = tuple(Decimal(f"{index / 10:.1f}") for index in range(11))
        if boundaries != expected:
            _fail("calibration-safeguard version 2 requires canonical decile boundaries")
    return tuple(sorted(normalized, key=lambda item: item.name))


@dataclass(frozen=True, slots=True)
class VersionedRuleSpecification:
    rule_specification_id: str
    schema_version: str
    identity_algorithm_version: str
    purpose: RulePurpose
    rule_id: str
    rule_version: str
    parameters: tuple[RuleParameter, ...]
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, purpose: RulePurpose, rule_id: str, rule_version: str,
               parameters: tuple[RuleParameter, ...] = (), limitations: tuple[str, ...] = (),
               *, schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "VersionedRuleSpecification":
        normalized = _validated_parameters(purpose, rule_id, rule_version, parameters)
        ordered_limits = _ordered_unique(limitations, "rule limitations")
        material = _rule_material(schema_version, identity_algorithm_version, purpose, rule_id,
                                  rule_version, normalized, ordered_limits)
        digest = _digest(material)
        return cls(f"rule-specification:{digest}", schema_version, identity_algorithm_version,
                   purpose, rule_id, rule_version, normalized, ordered_limits, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.rule_id, "rule_id")
        _require_identifier(self.rule_version, "rule_version")
        parameters = _validated_parameters(self.purpose, self.rule_id, self.rule_version, self.parameters)
        limits = _ordered_unique(self.limitations, "rule limitations")
        digest = _digest(_rule_material(self.schema_version, self.identity_algorithm_version,
                                       self.purpose, self.rule_id, self.rule_version, parameters, limits))
        if self.input_digest != digest or self.rule_specification_id != f"rule-specification:{digest}":
            _fail("rule identity conflicts with canonical material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "limitations", limits)


def _rule_material(schema: str, identity: str, purpose: RulePurpose, rule_id: str,
                   version: str, parameters: tuple[RuleParameter, ...], limitations: tuple[str, ...]) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "purpose": purpose.value,
            "rule": [rule_id, version], "parameters": parameters, "limitations": limitations}


@dataclass(frozen=True, slots=True)
class ResearchContractProvenance:
    producer_id: str
    producer_version: str
    additional_input_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.producer_id, "provenance producer_id")
        _require_identifier(self.producer_version, "provenance producer_version")
        if self.generated_at is not None:
            _require_aware(self.generated_at, "provenance generated_at")
        object.__setattr__(self, "additional_input_ids", _ordered_unique(self.additional_input_ids, "provenance input IDs"))
        object.__setattr__(self, "notes", _ordered_unique(self.notes, "provenance notes"))


@dataclass(frozen=True, slots=True)
class ProbabilitySourceReference:
    probability_source_reference_id: str
    schema_version: str
    identity_algorithm_version: str
    provider_id: str
    model_or_product_id: str
    model_or_product_version: str
    proposition_type: str
    probability_representation_rule: VersionedRuleSpecification
    transformation_rule: VersionedRuleSpecification
    availability_rule: VersionedRuleSpecification
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, provider_id: str, model_or_product_id: str, model_or_product_version: str,
               proposition_type: str, probability_representation_rule: VersionedRuleSpecification,
               transformation_rule: VersionedRuleSpecification, availability_rule: VersionedRuleSpecification,
               limitations: tuple[str, ...] = (), schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ProbabilitySourceReference":
        limits = _ordered_unique(limitations, "source limitations")
        material = _source_material(schema_version, identity_algorithm_version, provider_id,
                                    model_or_product_id, model_or_product_version, proposition_type,
                                    probability_representation_rule, transformation_rule, availability_rule, limits)
        digest = _digest(material)
        return cls(f"probability-source-reference:{digest}", schema_version, identity_algorithm_version,
                   provider_id, model_or_product_id, model_or_product_version, proposition_type,
                   probability_representation_rule, transformation_rule, availability_rule, limits, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        for value, label in ((self.provider_id, "provider_id"), (self.model_or_product_id, "model_or_product_id"),
                             (self.model_or_product_version, "model_or_product_version"),
                             (self.proposition_type, "source proposition_type")):
            _require_identifier(value, label)
        _require_purpose(self.probability_representation_rule, RulePurpose.PROBABILITY_REPRESENTATION)
        _require_purpose(self.transformation_rule, RulePurpose.PROBABILITY_TRANSFORMATION)
        _require_purpose(self.availability_rule, RulePurpose.SOURCE_AVAILABILITY)
        limits = _ordered_unique(self.limitations, "source limitations")
        digest = _digest(_source_material(self.schema_version, self.identity_algorithm_version,
                                         self.provider_id, self.model_or_product_id,
                                         self.model_or_product_version, self.proposition_type,
                                         self.probability_representation_rule, self.transformation_rule,
                                         self.availability_rule, limits))
        if self.input_digest != digest or self.probability_source_reference_id != f"probability-source-reference:{digest}":
            _fail("Probability Source identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "limitations", limits)


def _source_material(schema: str, identity: str, provider: str, product: str, version: str,
                     proposition: str, representation: VersionedRuleSpecification,
                     transformation: VersionedRuleSpecification, availability: VersionedRuleSpecification,
                     limitations: tuple[str, ...]) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "provider": provider, "product": [product, version],
            "proposition": proposition, "rules": [representation.rule_specification_id,
            transformation.rule_specification_id, availability.rule_specification_id], "limitations": limitations}


def _require_purpose(rule: VersionedRuleSpecification, purpose: RulePurpose) -> None:
    if not isinstance(rule, VersionedRuleSpecification) or rule.purpose is not purpose:
        _fail(f"rule must have purpose {purpose.value}")


@dataclass(frozen=True, slots=True)
class ResearchPopulationSpecification:
    research_population_id: str
    schema_version: str
    identity_algorithm_version: str
    sport: str
    competition: str
    proposition_type: str
    temporal_scope_rule: VersionedRuleSpecification
    event_status_rule: VersionedRuleSpecification
    postseason_treatment_rule: VersionedRuleSpecification
    postponement_treatment_rule: VersionedRuleSpecification
    cancellation_treatment_rule: VersionedRuleSpecification
    rescheduling_treatment_rule: VersionedRuleSpecification
    inclusion_rules: tuple[VersionedRuleSpecification, ...]
    exclusion_rules: tuple[VersionedRuleSpecification, ...]
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, sport: str, competition: str, proposition_type: str,
               temporal_scope_rule: VersionedRuleSpecification, event_status_rule: VersionedRuleSpecification,
               postseason_treatment_rule: VersionedRuleSpecification, postponement_treatment_rule: VersionedRuleSpecification,
               cancellation_treatment_rule: VersionedRuleSpecification, rescheduling_treatment_rule: VersionedRuleSpecification,
               inclusion_rules: tuple[VersionedRuleSpecification, ...], exclusion_rules: tuple[VersionedRuleSpecification, ...],
               limitations: tuple[str, ...] = (), schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ResearchPopulationSpecification":
        values = (schema_version, identity_algorithm_version, sport, competition, proposition_type,
                  temporal_scope_rule, event_status_rule, postseason_treatment_rule, postponement_treatment_rule,
                  cancellation_treatment_rule, rescheduling_treatment_rule,
                  _ordered_unique(inclusion_rules, "population inclusion rules", key=lambda x: x.rule_specification_id),
                  _ordered_unique(exclusion_rules, "population exclusion rules", key=lambda x: x.rule_specification_id),
                  _ordered_unique(limitations, "population limitations"))
        digest = _digest(_population_material(*values))
        return cls(f"research-population:{digest}", *values, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        for value, label in ((self.sport, "population sport"), (self.competition, "population competition"),
                             (self.proposition_type, "population proposition_type")):
            _require_identifier(value, label)
        purposes = ((self.temporal_scope_rule, RulePurpose.POPULATION_TEMPORAL_SCOPE),
                    (self.event_status_rule, RulePurpose.EVENT_STATUS_ELIGIBILITY),
                    (self.postseason_treatment_rule, RulePurpose.POSTSEASON_TREATMENT),
                    (self.postponement_treatment_rule, RulePurpose.POSTPONEMENT_TREATMENT),
                    (self.cancellation_treatment_rule, RulePurpose.CANCELLATION_TREATMENT),
                    (self.rescheduling_treatment_rule, RulePurpose.RESCHEDULING_TREATMENT))
        for rule, purpose in purposes:
            _require_purpose(rule, purpose)
        if not self.inclusion_rules:
            _fail("Research Population requires an explicit inclusion rule")
        for rule in self.inclusion_rules:
            _require_purpose(rule, RulePurpose.POPULATION_INCLUSION)
        for rule in self.exclusion_rules:
            _require_purpose(rule, RulePurpose.POPULATION_EXCLUSION)
        inclusion = _ordered_unique(self.inclusion_rules, "population inclusion rules", key=lambda x: x.rule_specification_id)
        exclusion = _ordered_unique(self.exclusion_rules, "population exclusion rules", key=lambda x: x.rule_specification_id)
        limits = _ordered_unique(self.limitations, "population limitations")
        digest = _digest(_population_material(self.schema_version, self.identity_algorithm_version, self.sport,
                                             self.competition, self.proposition_type, self.temporal_scope_rule,
                                             self.event_status_rule, self.postseason_treatment_rule,
                                             self.postponement_treatment_rule, self.cancellation_treatment_rule,
                                             self.rescheduling_treatment_rule, inclusion, exclusion, limits))
        if self.input_digest != digest or self.research_population_id != f"research-population:{digest}":
            _fail("Research Population identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "inclusion_rules", inclusion)
        object.__setattr__(self, "exclusion_rules", exclusion)
        object.__setattr__(self, "limitations", limits)


def _population_material(*values: Any) -> dict[str, Any]:
    schema, identity, sport, competition, proposition, *rest = values
    rules = rest[:6]
    inclusion, exclusion, limitations = rest[6:]
    return {"schema": schema, "identity": identity, "domain": [sport, competition, proposition],
            "rules": [rule.rule_specification_id for rule in rules],
            "inclusion": [rule.rule_specification_id for rule in inclusion],
            "exclusion": [rule.rule_specification_id for rule in exclusion], "limitations": limitations}


@dataclass(frozen=True, slots=True, order=True)
class ApprovedDimensionPartition:
    partition_key: str
    display_label: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.partition_key, "partition_key")
        if not self.display_label.strip():
            _fail("partition display_label is required")
        object.__setattr__(self, "limitations", _ordered_unique(self.limitations, "partition limitations"))


@dataclass(frozen=True, slots=True)
class ApprovedResearchDimension:
    approved_dimension_id: str
    schema_version: str
    identity_algorithm_version: str
    dimension_key: str
    classification_rule: VersionedRuleSpecification
    partitions: tuple[ApprovedDimensionPartition, ...]
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, dimension_key: str, classification_rule: VersionedRuleSpecification,
               partitions: tuple[ApprovedDimensionPartition, ...], limitations: tuple[str, ...] = (),
               *, schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ApprovedResearchDimension":
        ordered = _ordered_unique(partitions, "dimension partitions", key=lambda item: item.partition_key)
        limits = _ordered_unique(limitations, "dimension limitations")
        material = _dimension_material(schema_version, identity_algorithm_version, dimension_key, classification_rule, ordered, limits)
        digest = _digest(material)
        return cls(f"approved-research-dimension:{digest}", schema_version, identity_algorithm_version,
                   dimension_key, classification_rule, ordered, limits, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.dimension_key, "dimension_key")
        _require_purpose(self.classification_rule, RulePurpose.DIMENSION_CLASSIFICATION)
        if not self.partitions:
            _fail("Approved Research Dimension requires partitions")
        ordered = _ordered_unique(self.partitions, "dimension partitions", key=lambda item: item.partition_key)
        expected_keys = next(item.value for item in self.classification_rule.parameters if item.name == "partition_keys")
        if tuple(item.partition_key for item in ordered) != expected_keys:
            _fail("dimension partitions conflict with classification rule outputs")
        limits = _ordered_unique(self.limitations, "dimension limitations")
        digest = _digest(_dimension_material(self.schema_version, self.identity_algorithm_version,
                                            self.dimension_key, self.classification_rule, ordered, limits))
        if self.input_digest != digest or self.approved_dimension_id != f"approved-research-dimension:{digest}":
            _fail("dimension identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "partitions", ordered)
        object.__setattr__(self, "limitations", limits)


def _dimension_material(schema: str, identity: str, key: str, rule: VersionedRuleSpecification,
                        partitions: tuple[ApprovedDimensionPartition, ...], limitations: tuple[str, ...]) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "key": key, "rule": rule.rule_specification_id,
            "partitions": [(item.partition_key, item.limitations) for item in partitions], "limitations": limitations}


@dataclass(frozen=True, slots=True, order=True)
class DimensionPartitionSelection:
    approved_dimension_id: str
    partition_key: str

    def __post_init__(self) -> None:
        _require_identifier(self.approved_dimension_id, "approved_dimension_id")
        _require_identifier(self.partition_key, "selected partition_key")


@dataclass(frozen=True, slots=True)
class ResearchDomain:
    research_domain_id: str
    schema_version: str
    identity_algorithm_version: str
    sport: str
    competition: str
    proposition_type: str
    partition_selections: tuple[DimensionPartitionSelection, ...]
    limitations: tuple[str, ...]
    input_digest: str

    @classmethod
    def create(cls, *, sport: str, competition: str, proposition_type: str,
               partition_selections: tuple[DimensionPartitionSelection, ...] = (), limitations: tuple[str, ...] = (),
               schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ResearchDomain":
        selections = _ordered_unique(partition_selections, "domain partition selections",
                                     key=lambda item: (item.approved_dimension_id, item.partition_key))
        limits = _ordered_unique(limitations, "domain limitations")
        material = _domain_material(schema_version, identity_algorithm_version, sport, competition,
                                    proposition_type, selections, limits)
        digest = _digest(material)
        return cls(f"research-domain:{digest}", schema_version, identity_algorithm_version,
                   sport, competition, proposition_type, selections, limits, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.sport, "Research Domain sport")
        _require_identifier(self.competition, "Research Domain competition")
        _require_identifier(self.proposition_type, "Research Domain proposition_type")
        selections = _ordered_unique(self.partition_selections, "domain partition selections",
                                     key=lambda item: (item.approved_dimension_id, item.partition_key))
        if len({item.approved_dimension_id for item in selections}) != len(selections):
            _fail("Research Domain cannot select multiple partitions from one dimension")
        limits = _ordered_unique(self.limitations, "domain limitations")
        digest = _digest(_domain_material(self.schema_version, self.identity_algorithm_version,
                                         self.sport, self.competition, self.proposition_type, selections, limits))
        if self.input_digest != digest or self.research_domain_id != f"research-domain:{digest}":
            _fail("Research Domain identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "partition_selections", selections)
        object.__setattr__(self, "limitations", limits)


def _domain_material(schema: str, identity: str, sport: str, competition: str, proposition: str,
                     selections: tuple[DimensionPartitionSelection, ...], limitations: tuple[str, ...]) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "domain": [sport, competition, proposition],
            "selections": selections, "limitations": limitations}


@dataclass(frozen=True, slots=True, order=True)
class ScheduledReviewBoundary:
    boundary_key: str
    required_analysis_boundary_at: datetime
    grace_period_seconds: int

    def __post_init__(self) -> None:
        _require_identifier(self.boundary_key, "scheduled boundary_key")
        _require_aware(self.required_analysis_boundary_at, "required_analysis_boundary_at")
        if isinstance(self.grace_period_seconds, bool) or not isinstance(self.grace_period_seconds, int) or self.grace_period_seconds < 0:
            _fail("grace_period_seconds must be an explicitly supplied nonnegative integer")

    @property
    def obligation_due_at(self) -> datetime:
        return self.required_analysis_boundary_at + timedelta(seconds=self.grace_period_seconds)


@dataclass(frozen=True, slots=True, order=True)
class ScheduledReviewBoundaryReference:
    protocol_id: str
    boundary_key: str

    def __post_init__(self) -> None:
        _require_identifier(self.protocol_id, "scheduled reference protocol_id")
        _require_identifier(self.boundary_key, "scheduled reference boundary_key")


@dataclass(frozen=True, slots=True)
class ComparativePerformanceReportReference:
    schema_version: str
    identity_algorithm_version: str
    report_id: str
    contract_version: str
    protocol_id: str
    analysis_boundary: datetime
    edge_claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        for value, label in ((self.report_id, "report_id"), (self.contract_version, "report contract_version"),
                             (self.protocol_id, "report protocol_id")):
            _require_identifier(value, label)
        _require_aware(self.analysis_boundary, "report analysis_boundary")
        if not self.edge_claim_ids:
            _fail("Comparative Performance Report reference requires Edge Claim coverage")
        object.__setattr__(self, "edge_claim_ids", _ordered_unique(self.edge_claim_ids, "report Edge Claim IDs"))


class ResearchReviewConclusion(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    EMERGING_EVIDENCE = "emerging-evidence"
    SUPPORTED = "supported"
    STRONGLY_SUPPORTED = "strongly-supported"
    WEAKENING = "weakening"
    NO_LONGER_SUPPORTED = "no-longer-supported"
    REJECTED = "rejected"


class DriftDisposition(str, Enum):
    NO_MATERIAL_DRIFT = "no-material-drift"
    MATERIAL_DRIFT = "material-drift"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence-to-determine-drift"


@dataclass(frozen=True, slots=True, order=True)
class DriftSurveillanceReference:
    protocol_id: str
    edge_claim_id: str
    drift_surveillance_id: str
    effective_at: datetime

    def __post_init__(self) -> None:
        for value, label in ((self.protocol_id, "Drift reference protocol_id"),
                             (self.edge_claim_id, "Drift reference edge_claim_id"),
                             (self.drift_surveillance_id, "drift_surveillance_id")):
            _require_identifier(value, label)
        _require_aware(self.effective_at, "Drift reference effective_at")


class ReviewObligationKind(str, Enum):
    SCHEDULED_BOUNDARY = "scheduled-boundary"
    MATERIAL_DRIFT = "material-drift"


@dataclass(frozen=True, slots=True)
class ReviewObligationReference:
    kind: ReviewObligationKind
    scheduled_boundary: ScheduledReviewBoundaryReference | None = None
    drift_surveillance: DriftSurveillanceReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ReviewObligationKind):
            _fail("unsupported Review obligation kind", ReasonCode.UNSUPPORTED_STATUS)
        scheduled = self.scheduled_boundary is not None
        drift = self.drift_surveillance is not None
        if scheduled == drift:
            _fail("Review obligation must contain exactly one typed reference")
        if self.kind is ReviewObligationKind.SCHEDULED_BOUNDARY and not scheduled:
            _fail("scheduled obligation requires ScheduledReviewBoundaryReference")
        if self.kind is ReviewObligationKind.MATERIAL_DRIFT and not drift:
            _fail("material Drift obligation requires DriftSurveillanceReference")

    @property
    def canonical_key(self) -> tuple[str, ...]:
        if self.scheduled_boundary is not None:
            return (self.kind.value, self.scheduled_boundary.protocol_id, self.scheduled_boundary.boundary_key)
        assert self.drift_surveillance is not None
        return (self.kind.value, self.drift_surveillance.protocol_id,
                self.drift_surveillance.edge_claim_id, self.drift_surveillance.drift_surveillance_id,
                _utc(self.drift_surveillance.effective_at))


@dataclass(frozen=True, slots=True)
class ReviewObligationCoverage:
    obligations: tuple[ReviewObligationReference, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "obligations", _ordered_unique(
            self.obligations, "Review obligation coverage", key=lambda item: item.canonical_key))


@dataclass(frozen=True, slots=True)
class ResearchProtocol:
    research_protocol_id: str
    schema_version: str
    identity_algorithm_version: str
    protocol_version: str
    effective_at: datetime
    scientific_question: str
    research_population: ResearchPopulationSpecification
    market_benchmark: ProbabilitySourceReference
    alternative_sources: tuple[ProbabilitySourceReference, ...]
    approved_dimensions: tuple[ApprovedResearchDimension, ...]
    research_domains: tuple[ResearchDomain, ...]
    snapshot_timing_rule: VersionedRuleSpecification
    capture_tolerance_rule: VersionedRuleSpecification
    synchronization_rule: VersionedRuleSpecification
    event_compatibility_rule: VersionedRuleSpecification
    outcome_resolution_rule: VersionedRuleSpecification
    primary_measure_rule: VersionedRuleSpecification
    supporting_measure_rules: tuple[VersionedRuleSpecification, ...]
    statistical_method_rule: VersionedRuleSpecification
    practical_significance_rule: VersionedRuleSpecification
    burden_of_proof_rule: VersionedRuleSpecification
    surveillance_window_rules: tuple[VersionedRuleSpecification, ...]
    drift_classification_rule: VersionedRuleSpecification
    drift_material_event_rule: VersionedRuleSpecification
    scheduled_review_boundaries: tuple[ScheduledReviewBoundary, ...]
    limitations: tuple[str, ...]
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, protocol_version: str, effective_at: datetime, scientific_question: str,
               research_population: ResearchPopulationSpecification, market_benchmark: ProbabilitySourceReference,
               alternative_sources: tuple[ProbabilitySourceReference, ...],
               approved_dimensions: tuple[ApprovedResearchDimension, ...], research_domains: tuple[ResearchDomain, ...],
               snapshot_timing_rule: VersionedRuleSpecification, capture_tolerance_rule: VersionedRuleSpecification,
               synchronization_rule: VersionedRuleSpecification, event_compatibility_rule: VersionedRuleSpecification,
               outcome_resolution_rule: VersionedRuleSpecification, primary_measure_rule: VersionedRuleSpecification,
               supporting_measure_rules: tuple[VersionedRuleSpecification, ...], statistical_method_rule: VersionedRuleSpecification,
               practical_significance_rule: VersionedRuleSpecification, burden_of_proof_rule: VersionedRuleSpecification,
               surveillance_window_rules: tuple[VersionedRuleSpecification, ...],
               drift_classification_rule: VersionedRuleSpecification, drift_material_event_rule: VersionedRuleSpecification,
               scheduled_review_boundaries: tuple[ScheduledReviewBoundary, ...], limitations: tuple[str, ...],
               provenance: ResearchContractProvenance, schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ResearchProtocol":
        values = _normalize_protocol_values(alternative_sources, approved_dimensions, research_domains,
                                            supporting_measure_rules, surveillance_window_rules,
                                            scheduled_review_boundaries, limitations)
        material = _protocol_material(schema_version, identity_algorithm_version, protocol_version, effective_at,
                                      scientific_question, research_population, market_benchmark, *values,
                                      snapshot_timing_rule, capture_tolerance_rule, synchronization_rule,
                                      event_compatibility_rule, outcome_resolution_rule, primary_measure_rule,
                                      statistical_method_rule, practical_significance_rule, burden_of_proof_rule,
                                      drift_classification_rule, drift_material_event_rule)
        digest = _digest(material)
        alternatives, dimensions, domains, supporting, surveillance, boundaries, limits = values
        return cls(f"research-protocol:{digest}", schema_version, identity_algorithm_version, protocol_version,
                   effective_at, scientific_question, research_population, market_benchmark, alternatives,
                   dimensions, domains, snapshot_timing_rule, capture_tolerance_rule, synchronization_rule,
                   event_compatibility_rule, outcome_resolution_rule, primary_measure_rule, supporting,
                   statistical_method_rule, practical_significance_rule, burden_of_proof_rule, surveillance,
                   drift_classification_rule, drift_material_event_rule, boundaries, limits, provenance, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.protocol_version, "protocol_version")
        _require_aware(self.effective_at, "protocol effective_at")
        if not self.scientific_question.strip():
            _fail("scientific_question is required")
        values = _normalize_protocol_values(self.alternative_sources, self.approved_dimensions,
                                            self.research_domains, self.supporting_measure_rules,
                                            self.surveillance_window_rules, self.scheduled_review_boundaries,
                                            self.limitations)
        alternatives, dimensions, domains, supporting, surveillance, boundaries, limits = values
        if not alternatives or not domains or not supporting or not surveillance or not boundaries:
            _fail("Research Protocol requires challengers, domains, supporting measures, surveillance, and review boundaries")
        if self.market_benchmark.probability_source_reference_id in {item.probability_source_reference_id for item in alternatives}:
            _fail("Market Benchmark cannot also be an Alternative Probability Source")
        expected = self.research_population.proposition_type
        if any(item.proposition_type != expected for item in (self.market_benchmark,) + alternatives):
            _fail("protocol Probability Source proposition conflicts with Research Population")
        domain_key = (self.research_population.sport, self.research_population.competition,
                      self.research_population.proposition_type)
        if any((item.sport, item.competition, item.proposition_type) != domain_key for item in domains):
            _fail("Research Domain conflicts with Research Population")
        if not any(not item.partition_selections for item in domains):
            _fail("Research Protocol requires an explicit broad Research Domain")
        dimension_map = {item.approved_dimension_id: item for item in dimensions}
        for domain in domains:
            for selection in domain.partition_selections:
                dimension = dimension_map.get(selection.approved_dimension_id)
                if dimension is None or selection.partition_key not in {item.partition_key for item in dimension.partitions}:
                    _fail("Research Domain selects an unapproved dimension partition")
        purpose_checks = ((self.snapshot_timing_rule, RulePurpose.SNAPSHOT_TIMING),
                          (self.capture_tolerance_rule, RulePurpose.CAPTURE_TOLERANCE),
                          (self.synchronization_rule, RulePurpose.SYNCHRONIZATION),
                          (self.event_compatibility_rule, RulePurpose.EVENT_COMPATIBILITY),
                          (self.outcome_resolution_rule, RulePurpose.OUTCOME_RESOLUTION),
                          (self.primary_measure_rule, RulePurpose.PRIMARY_MEASURE),
                          (self.statistical_method_rule, RulePurpose.STATISTICAL_METHOD),
                          (self.practical_significance_rule, RulePurpose.PRACTICAL_SIGNIFICANCE),
                          (self.burden_of_proof_rule, RulePurpose.BURDEN_OF_PROOF),
                          (self.drift_classification_rule, RulePurpose.DRIFT_CLASSIFICATION),
                          (self.drift_material_event_rule, RulePurpose.DRIFT_MATERIAL_EVENT_MAPPING))
        for rule, purpose in purpose_checks:
            _require_purpose(rule, purpose)
        for rule in supporting:
            _require_purpose(rule, RulePurpose.SUPPORTING_MEASURE)
        for rule in surveillance:
            _require_purpose(rule, RulePurpose.SURVEILLANCE_WINDOW)
        material = _protocol_material(self.schema_version, self.identity_algorithm_version,
                                      self.protocol_version, self.effective_at, self.scientific_question,
                                      self.research_population, self.market_benchmark, *values,
                                      self.snapshot_timing_rule, self.capture_tolerance_rule,
                                      self.synchronization_rule, self.event_compatibility_rule,
                                      self.outcome_resolution_rule, self.primary_measure_rule,
                                      self.statistical_method_rule, self.practical_significance_rule,
                                      self.burden_of_proof_rule, self.drift_classification_rule,
                                      self.drift_material_event_rule)
        digest = _digest(material)
        if self.input_digest != digest or self.research_protocol_id != f"research-protocol:{digest}":
            _fail("Research Protocol identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "alternative_sources", alternatives)
        object.__setattr__(self, "approved_dimensions", dimensions)
        object.__setattr__(self, "research_domains", domains)
        object.__setattr__(self, "supporting_measure_rules", supporting)
        object.__setattr__(self, "surveillance_window_rules", surveillance)
        object.__setattr__(self, "scheduled_review_boundaries", boundaries)
        object.__setattr__(self, "limitations", limits)


def _normalize_protocol_values(alternatives: tuple[ProbabilitySourceReference, ...],
                               dimensions: tuple[ApprovedResearchDimension, ...], domains: tuple[ResearchDomain, ...],
                               supporting: tuple[VersionedRuleSpecification, ...], surveillance: tuple[VersionedRuleSpecification, ...],
                               boundaries: tuple[ScheduledReviewBoundary, ...], limitations: tuple[str, ...]) -> tuple[Any, ...]:
    return (_ordered_unique(alternatives, "Alternative Probability Sources", key=lambda item: item.probability_source_reference_id),
            _ordered_unique(dimensions, "approved dimensions", key=lambda item: item.dimension_key),
            _ordered_unique(domains, "Research Domains", key=lambda item: item.research_domain_id),
            _ordered_unique(supporting, "supporting measures", key=lambda item: item.rule_specification_id),
            _ordered_unique(surveillance, "surveillance rules", key=lambda item: item.rule_specification_id),
            _ordered_unique(boundaries, "scheduled review boundaries", key=lambda item: item.boundary_key),
            _ordered_unique(limitations, "protocol limitations"))


def _protocol_material(schema: str, identity: str, version: str, effective: datetime, question: str,
                       population: ResearchPopulationSpecification, benchmark: ProbabilitySourceReference,
                       alternatives: tuple[ProbabilitySourceReference, ...], dimensions: tuple[ApprovedResearchDimension, ...],
                       domains: tuple[ResearchDomain, ...], supporting: tuple[VersionedRuleSpecification, ...],
                       surveillance: tuple[VersionedRuleSpecification, ...], boundaries: tuple[ScheduledReviewBoundary, ...],
                       limitations: tuple[str, ...], snapshot: VersionedRuleSpecification,
                       capture: VersionedRuleSpecification, synchronization: VersionedRuleSpecification,
                       compatibility: VersionedRuleSpecification, outcome: VersionedRuleSpecification,
                       primary: VersionedRuleSpecification, statistical: VersionedRuleSpecification,
                       practical: VersionedRuleSpecification, burden: VersionedRuleSpecification,
                       drift: VersionedRuleSpecification, material_event: VersionedRuleSpecification) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "version": version, "effective": effective,
            "question": question, "population": population.research_population_id,
            "benchmark": benchmark.probability_source_reference_id,
            "alternatives": [item.probability_source_reference_id for item in alternatives],
            "dimensions": [item.approved_dimension_id for item in dimensions],
            "domains": [item.research_domain_id for item in domains],
            "rules": [snapshot.rule_specification_id, capture.rule_specification_id,
                      synchronization.rule_specification_id, compatibility.rule_specification_id,
                      outcome.rule_specification_id, primary.rule_specification_id,
                      *[item.rule_specification_id for item in supporting], statistical.rule_specification_id,
                      practical.rule_specification_id, burden.rule_specification_id,
                      *[item.rule_specification_id for item in surveillance], drift.rule_specification_id,
                      material_event.rule_specification_id],
            "boundaries": boundaries, "limitations": limitations}


@dataclass(frozen=True, slots=True)
class EdgeClaim:
    edge_claim_id: str
    schema_version: str
    identity_algorithm_version: str
    protocol_id: str
    challenger_source_reference_id: str
    benchmark_source_reference_id: str
    research_domain_id: str
    hypothesis_statement: str | None
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, protocol_id: str, challenger_source_reference_id: str,
               benchmark_source_reference_id: str, research_domain_id: str,
               provenance: ResearchContractProvenance, hypothesis_statement: str | None = None,
               schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "EdgeClaim":
        material = _claim_material(schema_version, identity_algorithm_version, protocol_id,
                                   challenger_source_reference_id, benchmark_source_reference_id, research_domain_id)
        digest = _digest(material)
        return cls(f"edge-claim:{digest}", schema_version, identity_algorithm_version, protocol_id,
                   challenger_source_reference_id, benchmark_source_reference_id, research_domain_id,
                   hypothesis_statement, provenance, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        for value in (self.protocol_id, self.challenger_source_reference_id,
                      self.benchmark_source_reference_id, self.research_domain_id):
            _require_identifier(value, "Edge Claim reference")
        if self.challenger_source_reference_id == self.benchmark_source_reference_id:
            _fail("Edge Claim challenger must differ from Market Benchmark")
        if self.hypothesis_statement is not None and not self.hypothesis_statement.strip():
            _fail("hypothesis_statement must be nonempty when supplied")
        digest = _digest(_claim_material(self.schema_version, self.identity_algorithm_version,
                                        self.protocol_id, self.challenger_source_reference_id,
                                        self.benchmark_source_reference_id, self.research_domain_id))
        if self.input_digest != digest or self.edge_claim_id != f"edge-claim:{digest}":
            _fail("Edge Claim identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


def _claim_material(schema: str, identity: str, protocol: str, challenger: str,
                    benchmark: str, domain: str) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "protocol": protocol,
            "challenger": challenger, "benchmark": benchmark, "domain": domain}


@dataclass(frozen=True, slots=True)
class ProtocolClaimSet:
    protocol_claim_set_id: str
    schema_version: str
    identity_algorithm_version: str
    protocol_id: str
    effective_at: datetime
    edge_claim_ids: tuple[str, ...]
    predecessor_protocol_claim_set_id: str | None
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, protocol_id: str, effective_at: datetime,
               edge_claim_ids: Iterable[str], provenance: ResearchContractProvenance,
               predecessor_protocol_claim_set_id: str | None = None,
               schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ProtocolClaimSet":
        claims = _ordered_unique(edge_claim_ids, "Protocol Claim Set Edge Claim IDs")
        material = _protocol_claim_set_material(
            schema_version, identity_algorithm_version, protocol_id, effective_at,
            claims, predecessor_protocol_claim_set_id)
        digest = _digest(material)
        return cls(f"protocol-claim-set:{digest}", schema_version, identity_algorithm_version,
                   protocol_id, effective_at, claims, predecessor_protocol_claim_set_id,
                   provenance, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.protocol_id, "Protocol Claim Set protocol_id")
        _require_aware(self.effective_at, "Protocol Claim Set effective_at")
        if self.predecessor_protocol_claim_set_id is not None:
            _require_identifier(self.predecessor_protocol_claim_set_id,
                                "predecessor_protocol_claim_set_id")
        claims = _ordered_unique(self.edge_claim_ids, "Protocol Claim Set Edge Claim IDs")
        if not claims:
            _fail("Protocol Claim Set membership must be nonempty")
        material = _protocol_claim_set_material(
            self.schema_version, self.identity_algorithm_version, self.protocol_id,
            self.effective_at, claims, self.predecessor_protocol_claim_set_id)
        digest = _digest(material)
        if self.input_digest != digest or self.protocol_claim_set_id != f"protocol-claim-set:{digest}":
            _fail("Protocol Claim Set identity conflicts with material",
                  ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        object.__setattr__(self, "edge_claim_ids", claims)


def _protocol_claim_set_material(schema: str, identity: str, protocol: str,
                                 effective_at: datetime, claim_ids: tuple[str, ...],
                                 predecessor_id: str | None) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "protocol": protocol,
            "effective_at": effective_at, "edge_claim_ids": claim_ids,
            "predecessor_protocol_claim_set_id": predecessor_id}


def _protocol_claim_set_registry(values: Iterable[ProtocolClaimSet]) -> dict[str, ProtocolClaimSet]:
    result: dict[str, ProtocolClaimSet] = {}
    for value in values:
        if value.protocol_claim_set_id in result:
            detail = "conflicting content" if result[value.protocol_claim_set_id] != value else "duplicate entry"
            _fail(f"Protocol Claim Set registry contains {detail} for {value.protocol_claim_set_id}",
                  ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        result[value.protocol_claim_set_id] = value
    return result


def _validated_protocol_claim_set_lineage(*, protocol_id: str,
        protocol_claim_sets: Iterable[ProtocolClaimSet]) -> tuple[ProtocolClaimSet, ...]:
    registry = _protocol_claim_set_registry(protocol_claim_sets)
    lineage = tuple(item for item in registry.values() if item.protocol_id == protocol_id)
    if not lineage:
        return ()
    by_id = {item.protocol_claim_set_id: item for item in lineage}
    initial = tuple(item for item in lineage if item.predecessor_protocol_claim_set_id is None)
    if len(initial) != 1:
        _fail("Protocol Claim Set lineage requires exactly one initial set")
    successors: dict[str, list[ProtocolClaimSet]] = {}
    for item in lineage:
        predecessor_id = item.predecessor_protocol_claim_set_id
        if predecessor_id is None:
            continue
        predecessor = registry.get(predecessor_id)
        if predecessor is None:
            _fail("Protocol Claim Set references unknown predecessor")
        if predecessor.protocol_id != protocol_id:
            _fail("Protocol Claim Set predecessor belongs to another Protocol")
        if item.effective_at <= predecessor.effective_at:
            _fail("Protocol Claim Set successor must become effective strictly later")
        if not set(predecessor.edge_claim_ids) < set(item.edge_claim_ids):
            _fail("Protocol Claim Set successor must retain all claims and add at least one")
        successors.setdefault(predecessor_id, []).append(item)
    if any(len(values) != 1 for values in successors.values()):
        _fail("Protocol Claim Set lineage branches")
    ordered: list[ProtocolClaimSet] = []
    current = initial[0]
    visited: set[str] = set()
    while True:
        if current.protocol_claim_set_id in visited:
            _fail("Protocol Claim Set lineage contains a cycle")
        visited.add(current.protocol_claim_set_id)
        ordered.append(current)
        children = successors.get(current.protocol_claim_set_id, [])
        if not children:
            break
        current = children[0]
    if visited != set(by_id):
        _fail("Protocol Claim Set lineage is disconnected or has competing terminals")
    return tuple(ordered)


def replay_protocol_claim_set(*, protocol_id: str, analysis_boundary: datetime,
        protocol_claim_sets: Iterable[ProtocolClaimSet]) -> ProtocolClaimSet | None:
    """Return the unique authoritative Claim Set effective at the boundary."""
    _require_identifier(protocol_id, "Protocol Claim Set replay protocol_id")
    _require_aware(analysis_boundary, "Protocol Claim Set replay boundary")
    effective_values = tuple(
        item for item in protocol_claim_sets if item.effective_at <= analysis_boundary)
    lineage = _validated_protocol_claim_set_lineage(
        protocol_id=protocol_id, protocol_claim_sets=effective_values)
    return lineage[-1] if lineage else None


def scheduled_review_boundary_applies(*, protocol_id: str, edge_claim_id: str,
        boundary: ScheduledReviewBoundary,
        protocol_claim_sets: Iterable[ProtocolClaimSet]) -> bool:
    claim_set = replay_protocol_claim_set(
        protocol_id=protocol_id,
        analysis_boundary=boundary.required_analysis_boundary_at,
        protocol_claim_sets=protocol_claim_sets)
    return claim_set is not None and edge_claim_id in claim_set.edge_claim_ids


@dataclass(frozen=True, slots=True)
class ResearchReview:
    research_review_id: str
    schema_version: str
    identity_algorithm_version: str
    protocol_id: str
    edge_claim_id: str
    report_reference: ComparativePerformanceReportReference
    conclusion: ResearchReviewConclusion
    obligation_coverage: ReviewObligationCoverage
    completed_at: datetime
    rationale: str
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, protocol_id: str, edge_claim_id: str,
               report_reference: ComparativePerformanceReportReference,
               conclusion: ResearchReviewConclusion, obligation_coverage: ReviewObligationCoverage,
               completed_at: datetime, rationale: str, provenance: ResearchContractProvenance,
               schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> "ResearchReview":
        if not isinstance(conclusion, ResearchReviewConclusion):
            _fail("Research Review requires one completed scientific conclusion",
                  ReasonCode.UNSUPPORTED_STATUS)
        material = _review_material(schema_version, identity_algorithm_version, protocol_id, edge_claim_id,
                                    report_reference, conclusion, obligation_coverage, completed_at, rationale)
        digest = _digest(material)
        return cls(f"research-review:{digest}", schema_version, identity_algorithm_version, protocol_id,
                   edge_claim_id, report_reference, conclusion, obligation_coverage, completed_at,
                   rationale, provenance, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.protocol_id, "Research Review protocol_id")
        _require_identifier(self.edge_claim_id, "Research Review edge_claim_id")
        _require_aware(self.completed_at, "Research Review completed_at")
        if not isinstance(self.conclusion, ResearchReviewConclusion):
            _fail("Research Review requires one completed scientific conclusion")
        if self.protocol_id != self.report_reference.protocol_id or self.edge_claim_id not in self.report_reference.edge_claim_ids:
            _fail("Research Review report does not cover its protocol and Edge Claim")
        if self.report_reference.analysis_boundary > self.completed_at:
            _fail("Research Review cannot precede its report analysis boundary")
        if not self.rationale.strip():
            _fail("Research Review rationale is required")
        digest = _digest(_review_material(self.schema_version, self.identity_algorithm_version,
                                         self.protocol_id, self.edge_claim_id, self.report_reference,
                                         self.conclusion, self.obligation_coverage, self.completed_at, self.rationale))
        if self.input_digest != digest or self.research_review_id != f"research-review:{digest}":
            _fail("Research Review identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


def _review_material(schema: str, identity: str, protocol: str, claim: str,
                     report: ComparativePerformanceReportReference, conclusion: ResearchReviewConclusion,
                     coverage: ReviewObligationCoverage, completed: datetime, rationale: str) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "protocol": protocol, "claim": claim,
            "report": report, "conclusion": conclusion.value, "coverage": coverage,
            "completed": completed, "rationale": rationale}


@dataclass(frozen=True, slots=True)
class DriftSurveillance:
    drift_surveillance_id: str
    schema_version: str
    identity_algorithm_version: str
    analysis_algorithm_version: str
    protocol_id: str
    edge_claim_id: str
    drift_rule_id: str
    drift_rule_version: str
    report_reference: ComparativePerformanceReportReference
    effective_at: datetime
    disposition: DriftDisposition
    provenance: ResearchContractProvenance
    input_digest: str

    @classmethod
    def create(cls, *, protocol_id: str, edge_claim_id: str, drift_rule_id: str,
               drift_rule_version: str, report_reference: ComparativePerformanceReportReference,
               effective_at: datetime, disposition: DriftDisposition, provenance: ResearchContractProvenance,
               schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
               identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION,
               analysis_algorithm_version: str = DRIFT_ANALYSIS_ALGORITHM_VERSION) -> "DriftSurveillance":
        material = _drift_material(schema_version, identity_algorithm_version, analysis_algorithm_version,
                                   protocol_id, edge_claim_id, drift_rule_id, drift_rule_version,
                                   report_reference, effective_at, disposition)
        digest = _digest(material)
        return cls(f"drift-surveillance:{digest}", schema_version, identity_algorithm_version,
                   analysis_algorithm_version, protocol_id, edge_claim_id, drift_rule_id,
                   drift_rule_version, report_reference, effective_at, disposition, provenance, digest)

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        if self.analysis_algorithm_version != DRIFT_ANALYSIS_ALGORITHM_VERSION:
            _fail("unsupported Drift analysis algorithm version")
        _require_identifier(self.protocol_id, "Drift protocol_id")
        _require_identifier(self.edge_claim_id, "Drift edge_claim_id")
        _require_identifier(self.drift_rule_id, "Drift rule_id")
        _require_identifier(self.drift_rule_version, "Drift rule_version")
        _require_aware(self.effective_at, "Drift effective_at")
        if not isinstance(self.disposition, DriftDisposition):
            _fail("unsupported Drift disposition")
        if self.protocol_id != self.report_reference.protocol_id or self.edge_claim_id not in self.report_reference.edge_claim_ids:
            _fail("Drift report does not cover its protocol and Edge Claim")
        if self.report_reference.analysis_boundary > self.effective_at:
            _fail("Drift cannot become effective before its report analysis boundary")
        digest = _digest(_drift_material(self.schema_version, self.identity_algorithm_version,
                                        self.analysis_algorithm_version, self.protocol_id, self.edge_claim_id,
                                        self.drift_rule_id, self.drift_rule_version, self.report_reference,
                                        self.effective_at, self.disposition))
        if self.input_digest != digest or self.drift_surveillance_id != f"drift-surveillance:{digest}":
            _fail("Drift identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


def _drift_material(schema: str, identity: str, analysis: str, protocol: str, claim: str,
                    rule_id: str, rule_version: str, report: ComparativePerformanceReportReference,
                    effective: datetime, disposition: DriftDisposition) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "analysis": analysis, "protocol": protocol,
            "claim": claim, "rule": [rule_id, rule_version], "report": report,
            "effective": effective, "disposition": disposition.value}


@dataclass(frozen=True, slots=True)
class MarketEdge:
    market_edge_id: str
    schema_version: str
    identity_algorithm_version: str
    edge_claim_id: str
    establishing_review_id: str
    established_at: datetime
    provenance: ResearchContractProvenance
    input_digest: str

    def __post_init__(self) -> None:
        _require_versions(self.schema_version, self.identity_algorithm_version)
        _require_identifier(self.edge_claim_id, "Market Edge edge_claim_id")
        _require_identifier(self.establishing_review_id, "Market Edge establishing_review_id")
        _require_aware(self.established_at, "Market Edge established_at")
        digest = _digest(_market_edge_material(self.schema_version, self.identity_algorithm_version,
                                              self.edge_claim_id, self.establishing_review_id, self.established_at))
        if self.input_digest != digest or self.market_edge_id != f"market-edge:{digest}":
            _fail("Market Edge identity conflicts with material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)


def _market_edge_material(schema: str, identity: str, claim: str, review: str, established: datetime) -> dict[str, Any]:
    return {"schema": schema, "identity": identity, "claim": claim, "review": review, "established": established}


def _qualifying_reviews(claim_id: str, reviews: Iterable[ResearchReview]) -> tuple[ResearchReview, ...]:
    by_id: dict[str, ResearchReview] = {}
    for review in reviews:
        if review.edge_claim_id != claim_id:
            continue
        prior = by_id.get(review.research_review_id)
        if prior is not None and prior.input_digest != review.input_digest:
            _fail("same Research Review ID has conflicting material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        by_id[review.research_review_id] = review
    qualifying = tuple(item for item in by_id.values() if item.conclusion in {
        ResearchReviewConclusion.SUPPORTED, ResearchReviewConclusion.STRONGLY_SUPPORTED})
    if not qualifying:
        _fail("Market Edge requires a qualifying completed Research Review")
    earliest = min(item.completed_at for item in qualifying)
    first = tuple(item for item in qualifying if item.completed_at == earliest)
    if len(first) != 1:
        _fail("materially different qualifying Reviews share the earliest completion instant")
    return first


def create_market_edge(*, edge_claim: EdgeClaim, reviews: Iterable[ResearchReview],
                       existing_market_edges: Iterable[MarketEdge], provenance: ResearchContractProvenance,
                       schema_version: str = RESEARCH_CONTRACT_SCHEMA_VERSION,
                       identity_algorithm_version: str = RESEARCH_IDENTITY_ALGORITHM_VERSION) -> MarketEdge:
    if any(item.edge_claim_id == edge_claim.edge_claim_id for item in existing_market_edges):
        _fail("at most one historical Market Edge may exist per Edge Claim")
    review = _qualifying_reviews(edge_claim.edge_claim_id, reviews)[0]
    digest = _digest(_market_edge_material(schema_version, identity_algorithm_version,
                                          edge_claim.edge_claim_id, review.research_review_id,
                                          review.completed_at))
    return MarketEdge(f"market-edge:{digest}", schema_version, identity_algorithm_version,
                      edge_claim.edge_claim_id, review.research_review_id, review.completed_at,
                      provenance, digest)


def drift_creates_material_event(protocol: ResearchProtocol, drift: DriftSurveillance) -> bool:
    if drift.protocol_id != protocol.research_protocol_id:
        _fail("Drift references the wrong Research Protocol")
    rule = protocol.drift_classification_rule
    if (drift.drift_rule_id, drift.drift_rule_version) != (rule.rule_id, rule.rule_version):
        _fail("Drift rule conflicts with governing Research Protocol")
    qualifying = next(item.value for item in protocol.drift_material_event_rule.parameters
                      if item.name == "qualifying_dispositions")
    return drift.disposition.value in qualifying


def _index(values: Iterable[Any], id_attribute: str, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in values:
        object_id = getattr(value, id_attribute)
        prior = result.get(object_id)
        if prior is not None and prior.input_digest != value.input_digest:
            _fail(f"same {label} ID has conflicting material", ReasonCode.CONFLICTING_NATIVE_IDENTITY)
        result[object_id] = value
    return result


def validate_research_contracts(*, protocols: Iterable[ResearchProtocol], claims: Iterable[EdgeClaim],
                                reviews: Iterable[ResearchReview], market_edges: Iterable[MarketEdge],
                                drift_surveillance: Iterable[DriftSurveillance],
                                protocol_claim_sets: Iterable[ProtocolClaimSet] = ()) -> None:
    protocol_map = _index(protocols, "research_protocol_id", "Research Protocol")
    claim_map = _index(claims, "edge_claim_id", "Edge Claim")
    review_map = _index(reviews, "research_review_id", "Research Review")
    edge_map = _index(market_edges, "market_edge_id", "Market Edge")
    drift_map = _index(drift_surveillance, "drift_surveillance_id", "Drift Surveillance")
    claim_set_values = tuple(protocol_claim_sets)
    claim_set_map = _protocol_claim_set_registry(claim_set_values)

    semantic_claims: dict[tuple[str, str, str, str], str] = {}
    for claim in claim_map.values():
        protocol = protocol_map.get(claim.protocol_id)
        if protocol is None:
            _fail("Edge Claim references unknown Research Protocol")
        if claim.benchmark_source_reference_id != protocol.market_benchmark.probability_source_reference_id:
            _fail("Edge Claim benchmark conflicts with Research Protocol")
        if claim.challenger_source_reference_id not in {item.probability_source_reference_id for item in protocol.alternative_sources}:
            _fail("Edge Claim challenger is not authorized by Research Protocol")
        if claim.research_domain_id not in {item.research_domain_id for item in protocol.research_domains}:
            _fail("Edge Claim Research Domain is not authorized by Research Protocol")
        key = (claim.protocol_id, claim.challenger_source_reference_id,
               claim.benchmark_source_reference_id, claim.research_domain_id)
        prior = semantic_claims.get(key)
        if prior is not None and prior != claim.edge_claim_id:
            _fail("equivalent Edge Claims have different deterministic identities")
        semantic_claims[key] = claim.edge_claim_id

    for claim_set in claim_set_map.values():
        protocol = protocol_map.get(claim_set.protocol_id)
        if protocol is None:
            _fail("Protocol Claim Set references unknown Research Protocol")
        for claim_id in claim_set.edge_claim_ids:
            claim = claim_map.get(claim_id)
            if claim is None:
                _fail("Protocol Claim Set references unknown Edge Claim")
            if claim.protocol_id != claim_set.protocol_id:
                _fail("Protocol Claim Set contains a foreign-Protocol Edge Claim")
    for protocol_id in {item.protocol_id for item in claim_set_values}:
        _validated_protocol_claim_set_lineage(
            protocol_id=protocol_id, protocol_claim_sets=claim_set_values)

    def validate_report_reference(report: ComparativePerformanceReportReference) -> None:
        if report.protocol_id not in protocol_map:
            _fail("Comparative Performance Report references unknown Research Protocol")
        for edge_claim_id in report.edge_claim_ids:
            covered_claim = claim_map.get(edge_claim_id)
            if covered_claim is None:
                _fail("Comparative Performance Report references unknown Edge Claim")
            if covered_claim.protocol_id != report.protocol_id:
                _fail("Comparative Performance Report covers an incompatible Edge Claim")

    for drift in drift_map.values():
        protocol = protocol_map.get(drift.protocol_id)
        claim = claim_map.get(drift.edge_claim_id)
        if protocol is None or claim is None or claim.protocol_id != drift.protocol_id:
            _fail("Drift references incompatible protocol or Edge Claim")
        if protocol.effective_at > drift.report_reference.analysis_boundary:
            _fail("Drift report predates Research Protocol")
        validate_report_reference(drift.report_reference)
        drift_creates_material_event(protocol, drift)

    for review in review_map.values():
        protocol = protocol_map.get(review.protocol_id)
        claim = claim_map.get(review.edge_claim_id)
        if protocol is None or claim is None or claim.protocol_id != review.protocol_id:
            _fail("Research Review references incompatible protocol or Edge Claim")
        if protocol.effective_at > review.report_reference.analysis_boundary:
            _fail("Research Review report predates Research Protocol")
        validate_report_reference(review.report_reference)
        boundaries = {item.boundary_key: item for item in protocol.scheduled_review_boundaries}
        for obligation in review.obligation_coverage.obligations:
            if obligation.scheduled_boundary is not None:
                reference = obligation.scheduled_boundary
                boundary = boundaries.get(reference.boundary_key)
                if reference.protocol_id != protocol.research_protocol_id or boundary is None:
                    _fail("scheduled obligation reference is incompatible")
                if boundary.required_analysis_boundary_at > review.report_reference.analysis_boundary:
                    _fail("Review report predates scheduled required analysis boundary")
                if claim_set_values and not scheduled_review_boundary_applies(
                        protocol_id=protocol.research_protocol_id,
                        edge_claim_id=review.edge_claim_id, boundary=boundary,
                        protocol_claim_sets=claim_set_values):
                    _fail("scheduled Review boundary predates Edge Claim admission")
            else:
                reference = obligation.drift_surveillance
                assert reference is not None
                drift = drift_map.get(reference.drift_surveillance_id)
                if drift is None:
                    _fail("Review references unknown Drift Surveillance")
                if (reference.protocol_id, reference.edge_claim_id, reference.effective_at) != (
                        drift.protocol_id, drift.edge_claim_id, drift.effective_at):
                    _fail("Drift obligation validation copies conflict with authoritative artifact")
                if not drift_creates_material_event(protocol, drift):
                    _fail("nonqualifying Drift cannot appear in material-event obligation coverage")
                if drift.edge_claim_id != review.edge_claim_id:
                    _fail("Review and Drift concern different Edge Claims")
                if review.completed_at < drift.effective_at:
                    _fail("Research Review completed before Drift became effective")
                if review.report_reference.analysis_boundary < drift.report_reference.analysis_boundary:
                    _fail("covering Review report predates Drift report")

    edges_by_claim: dict[str, list[MarketEdge]] = {}
    for edge in edge_map.values():
        edges_by_claim.setdefault(edge.edge_claim_id, []).append(edge)
    for claim_id, edges in edges_by_claim.items():
        if claim_id not in claim_map:
            _fail("Market Edge references unknown Edge Claim")
        if len(edges) != 1:
            _fail("at most one historical Market Edge may exist per Edge Claim")
        first = _qualifying_reviews(claim_id, review_map.values())[0]
        edge = edges[0]
        if edge.establishing_review_id != first.research_review_id or edge.established_at != first.completed_at:
            _fail("Market Edge is not established by the first qualifying Review")


_CONTRACTS = (
    RuleParameter, VersionedRuleSpecification, ResearchContractProvenance,
    ProbabilitySourceReference, ResearchPopulationSpecification, ApprovedDimensionPartition,
    ApprovedResearchDimension, DimensionPartitionSelection, ResearchDomain,
    ScheduledReviewBoundary, ScheduledReviewBoundaryReference,
    ComparativePerformanceReportReference, DriftSurveillanceReference,
    ReviewObligationReference, ReviewObligationCoverage, ResearchProtocol,
    EdgeClaim, ProtocolClaimSet, ResearchReview, MarketEdge, DriftSurveillance,
)
for _contract in _CONTRACTS:
    _contract.to_dict = SerializableContract.to_dict  # type: ignore[attr-defined]
    _contract.to_json = SerializableContract.to_json  # type: ignore[attr-defined]
    _contract.from_dict = SerializableContract.__dict__["from_dict"]  # type: ignore[attr-defined]
    _contract.from_json = SerializableContract.__dict__["from_json"]  # type: ignore[attr-defined]

_register(*_CONTRACTS, enums=(RulePurpose, ResearchReviewConclusion, DriftDisposition, ReviewObligationKind))
