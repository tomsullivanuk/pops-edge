"""PR17B2 local Kalshi MLB acquisition and durable Evidence operations.

The module is deliberately inactive by default.  It provides provider-facing
mechanics, an immutable local archive, rebuildable discovery, secondary copy,
and diagnostics.  Scientific timing and validation remain in
``forecast_standalone_research``; callers must supply its Protocol and
opportunity identities rather than operational overrides.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, DecimalException
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Union, get_args, get_origin, get_type_hints
import types

from event_contracts import ContractError


OPERATIONS_SCHEMA_VERSION = "1"
INDEX_SCHEMA_VERSION = "1"
INDEX_BUILDER_VERSION = "1"
PROVIDER_ID = "kalshi"
APPROVED_ACTIVATION_AT = datetime.fromisoformat("2026-09-05T00:00:00-04:00")
PROHIBITED_KEYS = frozenset({"authorization", "cookie", "password", "secret", "token", "api_key", "private_key"})


class OperationsError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


class RetrospectiveAcquisitionError(OperationsError):
    def __init__(self, detail: str, provider_calls: int):
        self.provider_calls=provider_calls
        super().__init__("retrospective-acquisition-failed",detail)


class SupportingAcquisitionError(OperationsError):
    def __init__(self, code: str, detail: str, provider_calls: int):
        self.provider_calls=provider_calls
        super().__init__(code,detail)


class OperatingMode(str, Enum):
    DRY_RUN = "dry-run"
    ACTIVATED = "activated"


class DesignAuthority(str, Enum):
    RETROSPECTIVE = "retrospective"
    PROSPECTIVE = "prospective"
    SUPPORTING = "supporting"


class Disposition(str, Enum):
    SUCCESS = "success"
    DERIVED = "derived"
    TIMEOUT = "timeout"
    CONNECTION_FAILURE = "connection-failure"
    RATE_LIMITED = "rate-limited"
    PROVIDER_ERROR = "provider-error"
    LATE_RESPONSE = "late-response"
    MALFORMED_RESPONSE = "malformed-response"
    INCOMPLETE_RESPONSE = "incomplete-response"
    VALIDATION_FAILURE = "validation-failure"
    NOT_DUE = "not-due"
    MISSED = "missed"
    SKIPPED_AFTER_SUCCESS = "skipped-after-success"


class ExitCode(IntEnum):
    SUCCESS = 0
    NOT_READY = 2
    INTEGRITY_FAILURE = 3
    CONFIGURATION_ERROR = 4
    OPERATIONAL_FAILURE = 5


def _utc(value: datetime, label: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise OperationsError("naive-timestamp", label)
    return value.astimezone(timezone.utc).isoformat()


def _plain(value: Any) -> Any:
    if isinstance(value, datetime): return {"datetime_utc": _utc(value, "canonical datetime")}
    if isinstance(value, date): return {"date": value.isoformat()}
    if isinstance(value, Enum): return value.value
    if is_dataclass(value): return _plain(asdict(value))
    if isinstance(value, Mapping): return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)): return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)): return value
    raise OperationsError("unsupported-canonical-value", type(value).__name__)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_secrets(value: Any, path: str = "request") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in PROHIBITED_KEYS or any(word in normalized for word in ("credential", "auth_header")):
                raise OperationsError("secret-material", f"{path}.{key}")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value): _reject_secrets(child, f"{path}[{index}]")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    maximum_attempts: int
    request_timeout_seconds: int
    total_timeout_seconds: int
    backoff_seconds: tuple[int, ...]
    maximum_retry_after_seconds: int
    def __post_init__(self) -> None:
        if self.maximum_attempts < 1 or self.request_timeout_seconds < 1 or self.total_timeout_seconds < self.request_timeout_seconds:
            raise OperationsError("configuration-error", "invalid retry bounds")
        if len(self.backoff_seconds) != self.maximum_attempts - 1 or any(x < 0 for x in self.backoff_seconds):
            raise OperationsError("configuration-error", "retry schedule must be explicit and bounded")
        if self.maximum_retry_after_seconds < 0: raise OperationsError("configuration-error", "invalid Retry-After bound")


RETROSPECTIVE_SUPPORTING_RETRY_POLICY=RetryPolicy(3,5,20,(1,2),2)


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    config_id: str
    namespace: str
    mode: OperatingMode
    primary_root: Path
    secondary_root: Path
    provider_base_url: str
    retry_policy: RetryPolicy
    lock_timeout_seconds: float
    log_root: Path
    timezone_name: str = "America/New_York"
    schedule_parameters: tuple[tuple[str, str], ...] = ()
    research_protocol_ids: tuple[str,...] = ()
    fixture_response_path: Path | None = None
    activation_at: datetime | None = None
    schema_version: str = OPERATIONS_SCHEMA_VERSION
    def __post_init__(self) -> None:
        if self.schema_version != OPERATIONS_SCHEMA_VERSION or not self.config_id or not self.namespace:
            raise OperationsError("configuration-error", "invalid configuration identity")
        if self.lock_timeout_seconds < 0 or self.provider_base_url.startswith("http://"):
            raise OperationsError("configuration-error", "unsafe timeout or endpoint")
        roots = (self.primary_root.resolve(), self.secondary_root.resolve(), self.log_root.resolve())
        if len(set(roots)) != 3 or any(a in b.parents or b in a.parents for i, a in enumerate(roots) for b in roots[i + 1:]):
            raise OperationsError("namespace-overlap", "primary, secondary, and logs must be physically separate")
        marker = f"/{self.mode.value}/{self.namespace}/"
        for root in roots[:2]:
            if marker not in f"/{root.as_posix().strip('/')}/":
                raise OperationsError("namespace-overlap", "archive paths must include mode and namespace")
        _reject_secrets(dict(self.schedule_parameters), "schedule_parameters")
        object.__setattr__(self,"research_protocol_ids",tuple(sorted(set(self.research_protocol_ids))))
        if self.mode is OperatingMode.ACTIVATED:
            if self.activation_at is None or self.activation_at.isoformat() != APPROVED_ACTIVATION_AT.isoformat() or self.timezone_name != "America/New_York":
                raise OperationsError("activation-authority-invalid","activated configuration requires the exact approved Eastern boundary")
        elif self.activation_at is not None:raise OperationsError("activation-authority-invalid","dry-run configuration cannot carry activation authority")

    @classmethod
    def from_json(cls, path: Path) -> "DeploymentConfig":
        raw = json.loads(path.read_text(encoding="utf-8")); _reject_secrets(raw, "configuration")
        retry = RetryPolicy(**raw.pop("retry_policy"))
        for key in ("primary_root", "secondary_root", "log_root"): raw[key] = Path(raw[key])
        if raw.get("fixture_response_path") is not None:raw["fixture_response_path"]=Path(raw["fixture_response_path"])
        if raw.get("activation_at") is not None:raw["activation_at"]=datetime.fromisoformat(raw["activation_at"])
        raw["mode"] = OperatingMode(raw["mode"]); raw["retry_policy"] = retry
        raw["schedule_parameters"] = tuple(sorted((str(k), str(v)) for k, v in raw.get("schedule_parameters", {}).items()))
        return cls(**raw)

    @property
    def identity(self) -> str:
        material = {"schema_version": self.schema_version, "config_id": self.config_id, "namespace": self.namespace,
                    "mode": self.mode.value, "primary_root": str(self.primary_root.resolve()), "secondary_root": str(self.secondary_root.resolve()),
                    "provider_base_url": self.provider_base_url, "retry_policy": self.retry_policy,
                    "lock_timeout_seconds": str(self.lock_timeout_seconds), "log_root": str(self.log_root.resolve()),
                    "timezone_name": self.timezone_name, "schedule_parameters": self.schedule_parameters,
                    "research_protocol_ids":self.research_protocol_ids,"fixture_response_path":str(self.fixture_response_path) if self.fixture_response_path else None}
        # Preserve every historical PR17B2 dry-run configuration identity.  The
        # activation field participates only in the new activated schema shape.
        if self.activation_at is not None: material["activation_at"] = self.activation_at
        return f"operations-config:{sha256_bytes(canonical_bytes(material))}"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    manifest_entry_id: str
    schema_version: str
    namespace: str
    operating_mode: OperatingMode
    command: str
    invocation_id: str
    provider_id: str
    endpoint: str
    sanitized_request_id: str
    acquired_at: datetime
    provider_effective_at: datetime | None
    raw_object_sha256: str | None
    normalized_object_id: str | None
    normalized_schema_version: str | None
    predecessor_id: str | None
    correction_reason: str | None
    disposition: Disposition
    protocol_id: str | None
    design_authority: DesignAuthority
    diagnostics: tuple[str, ...]

    @classmethod
    def create(cls, **values: Any) -> "ManifestEntry":
        values.setdefault("schema_version", OPERATIONS_SCHEMA_VERSION)
        values["diagnostics"] = tuple(sorted(set(values.get("diagnostics", ()))))
        material = {k: v for k, v in values.items() if k != "manifest_entry_id"}
        values["manifest_entry_id"] = f"operations-manifest:{sha256_bytes(canonical_bytes(material))}"
        return cls(**values)

    def __post_init__(self) -> None:
        if self.schema_version != OPERATIONS_SCHEMA_VERSION: raise OperationsError("unknown-version", self.schema_version)
        if not all((self.namespace,self.command,self.invocation_id,self.provider_id,self.endpoint,self.sanitized_request_id)):
            raise OperationsError("incomplete-manifest","required manifest authority is absent")
        _utc(self.acquired_at, "manifest acquisition")
        if self.provider_effective_at is not None: _utc(self.provider_effective_at, "provider effective time")
        if (self.predecessor_id is None) != (self.correction_reason is None):
            raise OperationsError("ambiguous-correction", "predecessor and correction reason must appear together")
        if self.disposition is Disposition.SUCCESS and not (self.raw_object_sha256 and self.normalized_object_id):
            raise OperationsError("incomplete-success", "successful entries require raw and normalized authority")
        if self.disposition is Disposition.DERIVED and (self.command!="publish-retrospective-analysis" or self.raw_object_sha256 is not None or not self.normalized_object_id or self.provider_id!="pops-edge-archive-analysis"):
            raise OperationsError("invalid-derived-publication", "derived publication requires normalized-only archive Analysis")
        if self.raw_object_sha256 is not None and (len(self.raw_object_sha256)!=64 or any(ch not in "0123456789abcdef" for ch in self.raw_object_sha256)):
            raise OperationsError("invalid-identity","raw object digest")
        if self.normalized_object_id is not None and not self.normalized_object_id.startswith("normalized:"):
            raise OperationsError("invalid-identity","normalized object identity")
        material={k:getattr(self,k) for k in self.__dataclass_fields__ if k!="manifest_entry_id"}
        expected=f"operations-manifest:{sha256_bytes(canonical_bytes(material))}"
        if self.manifest_entry_id != expected: raise OperationsError("identity-conflict", "manifest identity")


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    attempt: int
    started_at: datetime
    completed_at: datetime
    disposition: Disposition
    status_code: int | None
    retry_after_seconds: int | None
    retry_scheduled_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    disposition: Disposition
    raw_body: bytes | None
    normalized: Mapping[str, Any] | None
    attempts: tuple[AttemptRecord, ...]
    detail: str
    attempt_raw_bodies: tuple[bytes | None, ...] = ()


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str]


class Transport(Protocol):
    def request(self, method: str, url: str, *, params: Mapping[str, str], timeout: int,
                allow_redirects: bool) -> HTTPResponse: ...


def classify_response(response: HTTPResponse) -> Disposition:
    if response.status_code == 429: return Disposition.RATE_LIMITED
    if 500 <= response.status_code <= 599: return Disposition.PROVIDER_ERROR
    if response.status_code != 200: return Disposition.VALIDATION_FAILURE
    return Disposition.SUCCESS


def _decode_json(body: bytes) -> Mapping[str, Any]:
    try: value = json.loads(body,object_pairs_hook=_provider_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise OperationsError("malformed-response", str(exc)) from exc
    if not isinstance(value, dict): raise OperationsError("incomplete-response", "top-level object required")
    _reject_secrets(value, "provider_response")
    return value


_SCALAR_SERIALIZATION_MARKERS=frozenset({"__enum__","__date__","__datetime__","__decimal__","__non_finite_decimal__"})
_MAX_PROVIDER_SERIALIZATION_DEPTH=64


def _provider_object(pairs:list[tuple[str,Any]])->dict[str,Any]:
    value={}
    for key,item in pairs:
        if key in value:raise OperationsError("validation-failure","provider contract_json contains duplicate object keys")
        value[key]=item
    return value


def _validate_provider_serialization(value:Any,depth:int=0)->None:
    if depth>_MAX_PROVIDER_SERIALIZATION_DEPTH:raise OperationsError("validation-failure","provider contract_json exceeds the serialization nesting limit")
    if isinstance(value,list):
        for item in value:_validate_provider_serialization(item,depth+1)
        return
    if not isinstance(value,dict):return
    scalar_markers=tuple(sorted(_SCALAR_SERIALIZATION_MARKERS.intersection(value)))
    if len(scalar_markers)>1:raise OperationsError("validation-failure","provider contract_json contains conflicting scalar markers")
    if scalar_markers:
        marker=scalar_markers[0]
        if set(value)!={marker}:raise OperationsError("validation-failure",f"provider {marker} marker has incompatible companion keys")
        item=value[marker]
        if not isinstance(item,str):raise OperationsError("validation-failure",f"provider {marker} marker must contain a string")
        if marker=="__enum__":
            if ":" not in item:raise OperationsError("validation-failure","provider __enum__ marker lacks its type separator")
            enum_type,enum_value=item.split(":",1)
            if not enum_type or not enum_value:raise OperationsError("validation-failure","provider __enum__ marker has an empty type or value")
        elif marker=="__date__":
            try:date.fromisoformat(item)
            except ValueError as exc:raise OperationsError("validation-failure","provider __date__ marker is not a valid date") from exc
        elif marker=="__datetime__":
            try:timestamp=datetime.fromisoformat(item)
            except ValueError as exc:raise OperationsError("validation-failure","provider __datetime__ marker is not a valid datetime") from exc
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:raise OperationsError("validation-failure","provider __datetime__ marker must be timezone-aware")
        elif marker=="__decimal__":
            if not item:raise OperationsError("validation-failure","provider __decimal__ marker is empty")
            try:number=Decimal(item)
            except DecimalException as exc:raise OperationsError("validation-failure","provider __decimal__ marker is not a valid Decimal") from exc
            if not number.is_finite():raise OperationsError("validation-failure","provider __decimal__ marker must be finite")
        elif item not in {"positive-infinity","negative-infinity"}:
            raise OperationsError("validation-failure","provider __non_finite_decimal__ marker is unsupported")
        return
    if "__type__" in value:
        declared=value["__type__"]
        if not isinstance(declared,str) or not declared:raise OperationsError("validation-failure","provider __type__ marker must contain a non-empty string")
    for key in sorted(value):
        if key!="__type__":_validate_provider_serialization(value[key],depth+1)


def _schema_failure(path:str,detail:str,*,incomplete:bool=False)->None:
    raise OperationsError("incomplete-response" if incomplete else "validation-failure",f"provider contract schema {path}: {detail}")


def _validate_provider_schema(value:Any,expected:Any,path:str)->None:
    origin=get_origin(expected);arguments=get_args(expected)
    if origin in (Union,types.UnionType):
        non_null=tuple(item for item in arguments if item is not type(None))
        if len(non_null)==1 and len(non_null)!=len(arguments):
            if value is None:return
            _validate_provider_schema(value,non_null[0],path);return
        for alternative in arguments:
            try:_validate_provider_schema(value,alternative,path);return
            except OperationsError:pass
        _schema_failure(path,"does not match any permitted union shape")
    if origin is tuple:
        if not isinstance(value,list):_schema_failure(path,"must be an encoded tuple array")
        member=arguments[0]
        if len(arguments)!=2 or arguments[1] is not Ellipsis:raise RuntimeError("unsupported provider schema tuple annotation")
        for index,item in enumerate(value):_validate_provider_schema(item,member,f"{path}[{index}]")
        return
    if expected is Any:return
    if expected is type(None):
        if value is not None:_schema_failure(path,"must be null")
        return
    if isinstance(expected,type) and is_dataclass(expected):
        if not isinstance(value,dict):_schema_failure(path,"must be a tagged contract object")
        if value.get("__type__")!=expected.__name__:_schema_failure(path,f"must declare {expected.__name__}")
        expected_fields={item.name for item in fields(expected)};actual_fields=set(value)-{"__type__"}
        missing=sorted(expected_fields-actual_fields);unknown=sorted(actual_fields-expected_fields)
        if missing:_schema_failure(path,"is missing required canonical fields",incomplete=True)
        if unknown:_schema_failure(path,"contains unknown fields")
        hints=get_type_hints(expected)
        if set(hints)!=expected_fields:raise RuntimeError(f"incomplete runtime schema hints for {expected.__name__}")
        for item in fields(expected):_validate_provider_schema(value[item.name],hints[item.name],f"{path}.{item.name}")
        return
    if isinstance(expected,type) and issubclass(expected,Enum):
        if not isinstance(value,dict) or set(value)!={"__enum__"}:_schema_failure(path,f"must be a tagged {expected.__name__} enum")
        marker=value["__enum__"]
        if not isinstance(marker,str) or ":" not in marker:_schema_failure(path,f"must be a tagged {expected.__name__} enum")
        enum_name,enum_value=marker.split(":",1)
        if enum_name!=expected.__name__:_schema_failure(path,f"must use enum {expected.__name__}")
        try:expected(enum_value)
        except ValueError as exc:raise OperationsError("validation-failure",f"provider contract schema {path}: contains an unknown {expected.__name__} value") from exc
        return
    marker={datetime:"__datetime__",date:"__date__",Decimal:"__decimal__"}.get(expected)
    if marker is not None:
        permitted={marker}
        if expected is Decimal:permitted.add("__non_finite_decimal__")
        if not isinstance(value,dict) or len(value)!=1 or not set(value)<=permitted:_schema_failure(path,f"must use the canonical {expected.__name__} marker")
        return
    if expected is bool:
        if type(value) is not bool:_schema_failure(path,"must be a boolean")
        return
    if expected is int:
        if type(value) is not int:_schema_failure(path,"must be an integer")
        return
    if expected is str:
        if type(value) is not str:_schema_failure(path,"must be a string")
        return
    raise RuntimeError(f"unsupported provider schema annotation at {path}")


def decode_provider_pr17_contract(payload:str)->Any:
    """Decode provider-controlled PR17 material through a narrow, sanitized boundary."""
    try:raw=json.loads(payload,object_pairs_hook=_provider_object)
    except json.JSONDecodeError as exc:raise OperationsError("malformed-response","provider contract_json is malformed JSON") from exc
    if not isinstance(raw,dict) or "__type__" not in raw:raise OperationsError("incomplete-response","provider contract_json lacks a declared contract type")
    _validate_provider_serialization(raw)
    from market_contracts import MarketObservation
    _validate_provider_schema(raw,MarketObservation,"MarketObservation")
    try:
        from forecast_standalone_research import deserialize_v3
        return deserialize_v3(payload)
    except ContractError as exc:raise OperationsError("validation-failure","provider contract_json failed contract validation") from exc
    except TypeError as exc:raise OperationsError("incomplete-response","provider contract_json has missing or invalid fields") from exc
    except (ValueError,KeyError) as exc:raise OperationsError("validation-failure","provider contract_json contains incompatible encoded values") from exc


def _safe_raw(body: bytes) -> bytes | None:
    lowered=body.lower()
    if any(marker.encode() in lowered for marker in ("authorization","api_key","api-key","private_key","private-key","password","secret","token")):
        return None
    return body


def _permitted_response_raw(response: HTTPResponse) -> bytes | None:
    if response.status_code==413 and response.body==b"":return None
    return _safe_raw(response.body)


def acquire_prospective_once(*, transport: Transport, endpoint: str, request: Mapping[str, str],
                             timeout_seconds: int, now: Callable[[], datetime],
                             validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
                             started_at: datetime | None = None,
                             chronology_validator: Callable[[Mapping[str,Any],datetime,datetime],None] | None = None,
                             raw_validator:Callable[[Mapping[str,Any],bytes,datetime,datetime],Mapping[str,Any]]|None=None) -> AcquisitionResult:
    """Issue exactly one request. Redirects and transport-level retries are disabled by contract."""
    started = started_at if started_at is not None else now();_utc(started,"request start")
    def finish()->datetime:
        completed=now();_utc(completed,"request completion")
        if completed<started:raise OperationsError("trusted-clock-reversed","provider completion precedes request start")
        return completed
    try:
        response = transport.request("GET", endpoint, params=request, timeout=timeout_seconds, allow_redirects=False)
    except TimeoutError:
        completed = finish(); return AcquisitionResult(Disposition.TIMEOUT, None, None, (AttemptRecord(1, started, completed, Disposition.TIMEOUT, None, None),), "request timed out")
    except (ConnectionError, OSError):
        completed = finish(); return AcquisitionResult(Disposition.CONNECTION_FAILURE, None, None, (AttemptRecord(1, started, completed, Disposition.CONNECTION_FAILURE, None, None),), "connection failed")
    disposition = classify_response(response); completed = finish()
    if disposition is not Disposition.SUCCESS:
        return AcquisitionResult(disposition, _permitted_response_raw(response), None, (AttemptRecord(1, started, completed, disposition, response.status_code, None),), "provider response rejected")
    try: decoded = _decode_json(response.body)
    except OperationsError as exc:
        disp = Disposition.MALFORMED_RESPONSE if exc.code == "malformed-response" else Disposition.INCOMPLETE_RESPONSE
        preserved=None if exc.code=="secret-material" else response.body
        return AcquisitionResult(disp, preserved, None, (AttemptRecord(1, started, completed, disp, 200, None),), exc.detail)
    try:
        normalized = raw_validator(decoded,response.body,started,completed) if raw_validator is not None else validator(decoded)
        if chronology_validator is not None:chronology_validator(normalized,started,completed)
    except OperationsError as exc:
        disp = Disposition.MALFORMED_RESPONSE if exc.code == "malformed-response" else (Disposition.INCOMPLETE_RESPONSE if exc.code == "incomplete-response" else Disposition.VALIDATION_FAILURE)
        return AcquisitionResult(disp, _safe_raw(response.body), None, (AttemptRecord(1, started, completed, disp, 200, None),), exc.detail)
    return AcquisitionResult(Disposition.SUCCESS, response.body, normalized, (AttemptRecord(1, started, completed, Disposition.SUCCESS, 200, None),), "accepted")


def acquire_with_retries(*, transport: Transport, endpoint: str, request: Mapping[str, str], policy: RetryPolicy,
                         now: Callable[[], datetime], sleeper: Callable[[float], None],
                         validator: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> AcquisitionResult:
    records: list[AttemptRecord] = []; attempt_bodies: list[bytes | None] = []; last_body: bytes | None = None;retry_scheduled_at=None;first_start=None
    for number in range(1, policy.maximum_attempts + 1):
        started=now();first_start=first_start or started;status = None; retry_after = None
        if number>1 and (started-first_start).total_seconds()+policy.request_timeout_seconds>policy.total_timeout_seconds:break
        try:
            response = transport.request("GET", endpoint, params=request, timeout=policy.request_timeout_seconds, allow_redirects=False)
            last_body = _permitted_response_raw(response); status = response.status_code; disposition = classify_response(response)
        except TimeoutError: disposition = Disposition.TIMEOUT; response = None;last_body=None
        except (ConnectionError, OSError): disposition = Disposition.CONNECTION_FAILURE; response = None;last_body=None
        completed=now()
        if completed<started:raise OperationsError("trusted-clock-reversed","provider completion precedes request start")
        if response is not None and (completed-started).total_seconds()>policy.request_timeout_seconds:
            # A transport timeout is not a trustworthy wall-clock guarantee.  Preserve
            # any permitted late bytes and their real status, but never accept them.
            if disposition is Disposition.RATE_LIMITED:
                text=response.headers.get("Retry-After","0")
                try:retry_after=min(max(int(text),0),policy.maximum_retry_after_seconds)
                except ValueError:retry_after=0
            disposition=Disposition.LATE_RESPONSE
        if response is not None and disposition is Disposition.SUCCESS:
            try: normalized = validator(_decode_json(response.body))
            except OperationsError as exc:
                if exc.code=="secret-material": last_body=None
                disposition = Disposition.MALFORMED_RESPONSE if exc.code == "malformed-response" else (Disposition.INCOMPLETE_RESPONSE if exc.code == "incomplete-response" else Disposition.VALIDATION_FAILURE)
            else:
                records.append(AttemptRecord(number, started, completed, Disposition.SUCCESS, status, None,retry_scheduled_at))
                attempt_bodies.append(response.body)
                return AcquisitionResult(Disposition.SUCCESS, response.body, normalized, tuple(records), "accepted",tuple(attempt_bodies))
        if response is not None and disposition is Disposition.RATE_LIMITED:
            text = response.headers.get("Retry-After", "0")
            try: retry_after = min(max(int(text), 0), policy.maximum_retry_after_seconds)
            except ValueError: retry_after = 0
        records.append(AttemptRecord(number, started, completed, disposition, status, retry_after,retry_scheduled_at))
        attempt_bodies.append(last_body)
        retryable = disposition in {Disposition.TIMEOUT, Disposition.CONNECTION_FAILURE, Disposition.RATE_LIMITED, Disposition.PROVIDER_ERROR} or (disposition is Disposition.LATE_RESPONSE and status is not None and (status in {200,429} or 500<=status<=599))
        if not retryable or number == policy.maximum_attempts: break
        delay = max(policy.backoff_seconds[number - 1], retry_after or 0)
        elapsed = (now()-first_start).total_seconds()
        if elapsed + delay + policy.request_timeout_seconds > policy.total_timeout_seconds: break
        retry_scheduled_at=completed+timedelta(seconds=delay)
        sleeper(delay)
    return AcquisitionResult(records[-1].disposition, last_body, None, tuple(records), "bounded acquisition failed",tuple(attempt_bodies))


def validate_kalshi_payload(value: Mapping[str, Any], *, expected_kind: str, expected: Mapping[str, str]) -> Mapping[str, Any]:
    required = ("provider", "kind", "canonical_event_id", "provider_market_id", "scheduled_start", "effective_at", "payload")
    if any(key not in value for key in required): raise OperationsError("incomplete-response", "required provider fields missing")
    expected_provider="mlb-stats-api" if expected_kind in {"schedule","classification","outcome"} else PROVIDER_ID
    if value["provider"] != expected_provider or value["kind"] != expected_kind:
        raise OperationsError("validation-failure", "provider or acquisition kind conflicts")
    for key, wanted in expected.items():
        if str(value.get(key)) != wanted: raise OperationsError("validation-failure", f"{key} conflicts with expected authority")
    for key in ("scheduled_start", "effective_at"):
        try: parsed = datetime.fromisoformat(str(value[key]).replace("Z", "+00:00")); _utc(parsed, key)
        except (ValueError, OperationsError) as exc: raise OperationsError("validation-failure", f"invalid {key}") from exc
    payload = value["payload"]
    if not isinstance(payload, dict) or not payload: raise OperationsError("incomplete-response", "provider payload is empty")
    if expected_kind == "order-book":
        for side in ("yes", "no"):
            levels = payload.get(side)
            if not isinstance(levels, list) or not levels: raise OperationsError("incomplete-response", "two positive-depth sides required")
            if any(not isinstance(x, dict) or x.get("quantity", 0) <= 0 for x in levels): raise OperationsError("validation-failure", "non-positive order-book depth")
    elif expected_kind == "historical-candles":
        pages=payload.get("pages")
        if not isinstance(pages,list): raise OperationsError("incomplete-response","historical pagination is absent")
        validate_pagination(pages)
    elif expected_kind == "schedule":
        participants=payload.get("participant_ids")
        if not isinstance(participants,list) or len(set(participants))!=2 or not payload.get("status"):
            raise OperationsError("incomplete-response","schedule participants or status are incomplete")
    elif expected_kind == "classification":
        if not isinstance(payload.get("ordinary_game"),bool) or not all(payload.get(key) for key in ("native_event_id","event_phase","game_type","home_participant_id","away_participant_id")):
            raise OperationsError("incomplete-response","classification authority is incomplete")
        if payload["home_participant_id"]==payload["away_participant_id"]: raise OperationsError("validation-failure","classification participants conflict")
    elif expected_kind == "outcome":
        if payload.get("status")!="final" or not payload.get("winner_participant_id"):
            raise OperationsError("incomplete-response","authoritative final Outcome is incomplete")
    else: raise OperationsError("validation-failure","unsupported acquisition kind")
    normalized={key:value[key] for key in sorted(value)}
    normalized["schema_version"]=OPERATIONS_SCHEMA_VERSION
    normalized["normalization_version"]="1"
    return normalized


def validate_pagination(pages: Iterable[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    values = tuple(pages)
    if not values: raise OperationsError("pagination-incomplete", "no pages")
    positions, cursors, members = set(), set(), set()
    expected_cursor: str | None = "initial"
    canonical: list[Mapping[str, Any]] = []
    for expected_position, page in enumerate(values):
        if page.get("position") != expected_position or page.get("cursor") != expected_cursor:
            raise OperationsError("pagination-gap", "positions or cursor chain are discontinuous")
        cursor = str(page["cursor"])
        if cursor in cursors or expected_position in positions: raise OperationsError("pagination-cycle", "cursor or position repeated")
        positions.add(expected_position); cursors.add(cursor)
        items = page.get("candle_ids")
        if not isinstance(items, list): raise OperationsError("pagination-incomplete", "candle membership missing")
        for item in items:
            if item in members: raise OperationsError("pagination-conflict", "duplicate candle membership")
            members.add(item)
        expected_cursor = page.get("next_cursor")
        terminal = bool(page.get("terminal"))
        if terminal != (expected_cursor is None): raise OperationsError("pagination-incomplete", "terminal cursor conflict")
        if terminal and expected_position != len(values) - 1: raise OperationsError("pagination-conflict", "content follows terminal page")
        canonical.append(dict(page))
    if expected_cursor is not None: raise OperationsError("pagination-incomplete", "terminal page absent")
    return tuple(canonical)


class NamespaceArchive:
    def __init__(self, config: DeploymentConfig):
        self.config = config; self.root = config.primary_root.resolve()
        self.raw_root = self.root / "raw"; self.normalized_root = self.root / "normalized"
        self.manifest_root = self.root / "manifest"; self.temporary_root = self.root / ".partial"
        self.lock_path = self.root / "mutation.lock"; self.index_path = self.root / "index.sqlite3"

    def _ensure_mutable(self) -> None:
        if self.config.mode is OperatingMode.ACTIVATED and self.config.activation_at!=APPROVED_ACTIVATION_AT:
            raise OperationsError("activation-prohibited", "activated mutation requires exact PR17C1 authority")
        for path in (self.raw_root, self.normalized_root, self.manifest_root, self.temporary_root): path.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def mutation_lock(self):
        self._ensure_mutable(); self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+b"); deadline = time.monotonic() + self.config.lock_timeout_seconds
        while True:
            try: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.monotonic() >= deadline: handle.close(); raise OperationsError("lock-timeout", "live namespace mutation lock")
                time.sleep(min(0.01, max(deadline - time.monotonic(), 0)))
        try: yield
        finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN); handle.close()

    def _path(self, family: str, identity: str) -> Path:
        digest = identity.split(":")[-1]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest): raise OperationsError("invalid-identity", identity)
        root = {"raw": self.raw_root, "normalized": self.normalized_root, "manifest": self.manifest_root}[family]
        return root / digest[:2] / f"{digest}.json" if family != "raw" else root / digest[:2] / digest

    def _publish(self, target: Path, body: bytes) -> bool:
        target.parent.mkdir(parents=True, exist_ok=True); self.temporary_root.mkdir(parents=True, exist_ok=True)
        temporary = self.temporary_root / f"{uuid.uuid4().hex}.partial"
        with temporary.open("xb") as handle:
            handle.write(body); handle.flush(); os.fsync(handle.fileno())
        try:
            os.link(temporary, target); created = True
            with target.open("rb") as handle:
                if sha256_bytes(handle.read()) != sha256_bytes(body): raise OperationsError("publication-digest-mismatch", str(target))
            target.chmod(0o444)
        except FileExistsError:
            if target.read_bytes() != body: raise OperationsError("immutable-conflict", str(target))
            created = False
        finally:
            temporary.unlink(missing_ok=True)
        return created

    def commit(self, *, raw_body: bytes, normalized: Mapping[str, Any], entry_values: Mapping[str, Any], failpoint: str | None = None, auxiliary_raw_bodies: Iterable[bytes] = ()) -> ManifestEntry:
        with self.mutation_lock():
            return self._commit_locked(raw_body=raw_body, normalized=normalized, entry_values=entry_values,failpoint=failpoint,auxiliary_raw_bodies=auxiliary_raw_bodies)

    def _commit_locked(self, *, raw_body: bytes, normalized: Mapping[str, Any], entry_values: Mapping[str, Any], failpoint: str | None = None, auxiliary_raw_bodies: Iterable[bytes] = ()) -> ManifestEntry:
        auxiliary=tuple(auxiliary_raw_bodies)
        raw_digest = sha256_bytes(raw_body); raw_identity = f"raw:{raw_digest}"
        normalized_body = canonical_bytes(normalized); normalized_digest = sha256_bytes(normalized_body)
        normalized_id = f"normalized:{normalized_digest}"
        entry = ManifestEntry.create(**dict(entry_values), namespace=self.config.namespace,
            operating_mode=self.config.mode, raw_object_sha256=raw_digest, normalized_object_id=normalized_id,
            normalized_schema_version=str(normalized.get("schema_version", OPERATIONS_SCHEMA_VERSION)))
        integrity=reconcile_archive(self)
        candidate={f"raw:{raw_digest}",f"normalized:{normalized_digest}",*(f"raw:{sha256_bytes(body)}" for body in auxiliary)}
        if integrity.orphaned and not set(integrity.orphaned)<=candidate:
            raise OperationsError("orphan-conflict","unreferenced interrupted material conflicts with retry")
        for prior in self.entries():
            if prior["invocation_id"]==entry.invocation_id and (prior.get("raw_object_sha256"),prior.get("normalized_object_id"))!=(raw_digest,normalized_id):
                raise OperationsError("immutable-conflict","invocation identity already resolves different material")
        if failpoint=="before-raw":raise OperationsError("injected-interruption",failpoint)
        for body in auxiliary:self._publish(self._path("raw",f"raw:{sha256_bytes(body)}"),body)
        self._publish(self._path("raw", raw_identity), raw_body)
        if failpoint=="after-raw":raise OperationsError("injected-interruption",failpoint)
        self._publish(self._path("normalized", normalized_id), normalized_body)
        if failpoint in {"after-normalized","before-manifest"}:raise OperationsError("injected-interruption",failpoint)
        self._publish(self._path("manifest", entry.manifest_entry_id), canonical_bytes(entry))
        if failpoint=="after-manifest":raise OperationsError("injected-interruption",failpoint)
        return entry

    def commit_normalized(self, *, normalized: Mapping[str,Any], entry_values: Mapping[str,Any]) -> ManifestEntry:
        """Publish a canonical no-provider-call PR17B1 disposition."""
        with self.mutation_lock():
            return self._commit_normalized_locked(normalized=normalized,entry_values=entry_values)

    def _commit_normalized_locked(self,*,normalized:Mapping[str,Any],entry_values:Mapping[str,Any],auxiliary_raw_bodies:Iterable[bytes]=())->ManifestEntry:
        body=canonical_bytes(normalized);digest=sha256_bytes(body);identity=f"normalized:{digest}"
        entry=ManifestEntry.create(**dict(entry_values),namespace=self.config.namespace,operating_mode=self.config.mode,
            raw_object_sha256=None,normalized_object_id=identity,normalized_schema_version=str(normalized.get("schema_version",OPERATIONS_SCHEMA_VERSION)))
        for raw in auxiliary_raw_bodies:self._publish(self._path("raw",f"raw:{sha256_bytes(raw)}"),raw)
        self._publish(self._path("normalized",identity),body)
        self._publish(self._path("manifest",entry.manifest_entry_id),canonical_bytes(entry));return entry

    def record_failure(self, *, entry_values: Mapping[str, Any], raw_body: bytes | None = None) -> ManifestEntry:
        with self.mutation_lock():
            return self._record_failure_locked(entry_values=entry_values, raw_body=raw_body)

    def _record_failure_locked(self, *, entry_values: Mapping[str, Any], raw_body: bytes | None = None) -> ManifestEntry:
        digest = sha256_bytes(raw_body) if raw_body is not None else None
        entry = ManifestEntry.create(**dict(entry_values), namespace=self.config.namespace,
            operating_mode=self.config.mode, raw_object_sha256=digest, normalized_object_id=None,
            normalized_schema_version=None)
        for prior in self.entries():
            if prior["invocation_id"]==entry.invocation_id and prior["manifest_entry_id"]!=entry.manifest_entry_id:raise OperationsError("immutable-conflict","failure invocation identity conflicts with archived evidence")
        if raw_body is not None: self._publish(self._path("raw", f"raw:{digest}"), raw_body)
        self._publish(self._path("manifest", entry.manifest_entry_id), canonical_bytes(entry)); return entry

    def read_verified(self, family: str, identity: str) -> bytes:
        path = self._path(family, identity); body = path.read_bytes(); digest = identity.split(":")[-1]
        if sha256_bytes(body) != digest: raise OperationsError("archive-corrupt", str(path))
        return body

    def entries(self) -> tuple[Mapping[str, Any], ...]:
        if not self.manifest_root.exists(): return ()
        values=[]
        for path in sorted(self.manifest_root.glob("*/*.json")):
            values.append(self._decode_manifest_path(path))
        ordered=tuple(sorted(values,key=lambda item:(item["acquired_at"]["datetime_utc"],item["manifest_entry_id"])))
        by_id={item["manifest_entry_id"]:item for item in ordered};children:dict[str,list[str]]={}
        for item in ordered:
            predecessor=item.get("predecessor_id")
            if predecessor is None: continue
            parent=by_id.get(predecessor)
            if parent is None: raise OperationsError("ambiguous-correction","orphaned manifest predecessor")
            if (parent.get("protocol_id"),parent["design_authority"],parent["namespace"],parent["operating_mode"])!=(item.get("protocol_id"),item["design_authority"],item["namespace"],item["operating_mode"]):
                raise OperationsError("ambiguous-correction","correction crosses authority")
            if item["acquired_at"]["datetime_utc"]<=parent["acquired_at"]["datetime_utc"]:
                raise OperationsError("ambiguous-correction","correction chronology is not increasing")
            children.setdefault(predecessor,[]).append(item["manifest_entry_id"])
        if any(len(items)>1 for items in children.values()): raise OperationsError("ambiguous-correction","correction lineage branches")
        return ordered

    def _decode_manifest_path(self,path:Path)->Mapping[str,Any]:
        try:
            value=json.loads(path.read_bytes());decoded=dict(value)
            for key in ("acquired_at","provider_effective_at"):
                if decoded.get(key) is not None:decoded[key]=datetime.fromisoformat(decoded[key]["datetime_utc"])
            decoded["operating_mode"]=OperatingMode(decoded["operating_mode"]);decoded["disposition"]=Disposition(decoded["disposition"])
            decoded["design_authority"]=DesignAuthority(decoded["design_authority"]);decoded["diagnostics"]=tuple(decoded["diagnostics"])
            contract=ManifestEntry(**decoded);expected=contract.manifest_entry_id.split(":")[-1]
        except (TypeError,ValueError,KeyError,json.JSONDecodeError,OperationsError) as exc:raise OperationsError("manifest-corrupt",str(path)) from exc
        if expected!=path.stem or value.get("manifest_entry_id")!=f"operations-manifest:{expected}":raise OperationsError("manifest-corrupt",str(path))
        if contract.namespace!=self.config.namespace or contract.operating_mode is not self.config.mode:raise OperationsError("namespace-crossing",str(path))
        return value

    def temporary_files(self) -> tuple[str, ...]:
        if not self.temporary_root.exists(): return ()
        return tuple(str(path.relative_to(self.root)) for path in sorted(self.temporary_root.glob("*.partial")))

    def reject_promotion(self, source: "NamespaceArchive") -> None:
        if source.config.namespace != self.config.namespace or source.config.mode != self.config.mode:
            raise OperationsError("promotion-prohibited", "artifacts cannot cross namespace or operating mode")
        raise OperationsError("promotion-prohibited", "archive promotion is never supported")


def _verify_entry_objects(archive: NamespaceArchive, entry: Mapping[str, Any]) -> None:
    if entry.get("raw_object_sha256"):archive.read_verified("raw",f"raw:{entry['raw_object_sha256']}")
    if entry.get("normalized_object_id"):archive.read_verified("normalized",entry["normalized_object_id"])


@dataclass(frozen=True,slots=True)
class ArchiveIntegrityResult:
    referenced_valid:tuple[str,...]
    referenced_missing:tuple[str,...]
    referenced_corrupt:tuple[str,...]
    orphaned:tuple[str,...]
    malformed:tuple[str,...]
    incompatible:tuple[str,...]
    partial:tuple[str,...]
    authoritative_manifest_ids:tuple[str,...]
    @property
    def healthy(self)->bool:return not any((self.referenced_missing,self.referenced_corrupt,self.orphaned,self.malformed,self.incompatible,self.partial))
    @property
    def blocking(self)->bool:return bool(self.referenced_missing or self.referenced_corrupt or self.malformed or self.incompatible or self.partial)


def reconcile_archive(archive:NamespaceArchive)->ArchiveIntegrityResult:
    valid=[];malformed=[];incompatible=[]
    paths=tuple(sorted(archive.manifest_root.glob("*/*.json"))) if archive.manifest_root.exists() else ()
    for path in paths:
        try:valid.append(archive._decode_manifest_path(path))
        except OperationsError as exc:
            relative=str(path.relative_to(archive.root))
            (incompatible if exc.code=="namespace-crossing" else malformed).append(relative)
    expected_raw={item["raw_object_sha256"] for item in valid if item.get("raw_object_sha256")}
    expected_normalized={item["normalized_object_id"].split(":")[-1] for item in valid if item.get("normalized_object_id")}
    for item in valid:
        normalized_id=item.get("normalized_object_id")
        if not normalized_id:continue
        try:value=json.loads(archive._path("normalized",normalized_id).read_bytes())
        except (FileNotFoundError,UnicodeDecodeError,json.JSONDecodeError):continue
        if value.get("record_kind")=="pr17c2-supporting-session-page" and value.get("schema_version")=="2":
            for attempt in value.get("attempts",()):
                if isinstance(attempt,dict) and isinstance(attempt.get("raw_sha256"),str):expected_raw.add(attempt["raw_sha256"])
    actual_raw={p.name:p for p in sorted(archive.raw_root.glob("*/*")) if p.is_file()} if archive.raw_root.exists() else {}
    actual_normalized={p.stem:p for p in sorted(archive.normalized_root.glob("*/*.json")) if p.is_file()} if archive.normalized_root.exists() else {}
    missing=[];corrupt=[];referenced=[]
    for family,expected,actual in (("raw",expected_raw,actual_raw),("normalized",expected_normalized,actual_normalized)):
        for digest in sorted(expected):
            label=f"{family}:{digest}";path=actual.get(digest)
            if path is None:missing.append(label)
            elif sha256_bytes(path.read_bytes())!=digest:corrupt.append(label)
            else:referenced.append(label)
    orphaned=tuple(sorted([f"raw:{key}" for key in set(actual_raw)-expected_raw]+[f"normalized:{key}" for key in set(actual_normalized)-expected_normalized]))
    malformed_paths=[]
    for family,root,suffix in (("raw",archive.raw_root,""),("normalized",archive.normalized_root,".json"),("manifest",archive.manifest_root,".json")):
        if not root.exists():continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            name=path.name[:-len(suffix)] if suffix and path.name.endswith(suffix) else path.name
            if len(name)!=64 or any(ch not in "0123456789abcdef" for ch in name) or path.parent.name!=name[:2] or (suffix and not path.name.endswith(suffix)):
                malformed_paths.append(f"{family}:{path.relative_to(root)}")
    acquisition_pages={};acquisition_envelopes={};acquisition_reconciliations={};acquisition_entry_ids={};acquisition_partial=[]
    for item in valid:
        identity=item.get("normalized_object_id")
        if not identity or identity.split(":")[-1] not in actual_normalized:continue
        try:value=json.loads(actual_normalized[identity.split(":")[-1]].read_bytes())
        except (OSError,json.JSONDecodeError):continue
        group=value.get("acquisition_id");kind=value.get("record_kind")
        if not isinstance(group,str):continue
        acquisition_entry_ids.setdefault(group,set()).add(item["manifest_entry_id"])
        if kind=="pr17c1-provider-page":acquisition_pages.setdefault(group,set()).add(item["manifest_entry_id"])
        elif kind=="pr17c1-acquisition-bundle":acquisition_envelopes.setdefault(group,[]).append((item["manifest_entry_id"],value))
        elif kind=="pr17c1-acquisition-reconciliation":acquisition_reconciliations.setdefault(group,[]).append((item["manifest_entry_id"],value,item))
    for group in sorted(set(acquisition_pages)|set(acquisition_envelopes)|set(acquisition_reconciliations)):
        pages=acquisition_pages.get(group,set());envelopes=acquisition_envelopes.get(group,[])
        reconciliations=acquisition_reconciliations.get(group,[])
        if len(envelopes)>1:acquisition_partial.append(f"acquisition:{group}:competing-envelopes");continue
        if envelopes and reconciliations:acquisition_partial.append(f"acquisition:{group}:reconciliation-targets-complete-group");continue
        if not envelopes:
            if not reconciliations:acquisition_partial.append(f"acquisition:{group}:missing-envelope");continue
            if len(reconciliations)!=1:acquisition_partial.append(f"acquisition:{group}:competing-reconciliations");continue
            _,reconciliation,manifest=reconciliations[0]
            covered=set(reconciliation.get("page_manifest_ids",()))
            page_values=[]
            for item in valid:
                if item["manifest_entry_id"] not in pages:continue
                page_values.append((item,json.loads(actual_normalized[item["normalized_object_id"].split(":")[-1]].read_bytes())))
            providers={value.get("provider") for _,value in page_values};families={item.get("command","")[:-5] for item,_ in page_values if item.get("command","").endswith("-page")}
            expected_authority=[{"position":value.get("position"),"request_identity":value.get("request_identity"),"endpoint":value.get("endpoint"),"raw_sha256":value.get("raw_sha256"),"started_at":value.get("started_at"),"completed_at":value.get("completed_at")} for _,value in sorted(page_values,key=lambda pair:pair[1].get("position",-1))]
            latest=max((datetime.fromisoformat(item["acquired_at"]["datetime_utc"]) for item,_ in page_values),default=None)
            reconciled_at_raw=reconciliation.get("reconciled_at");reconciled_at=datetime.fromisoformat(reconciled_at_raw["datetime_utc"]) if isinstance(reconciled_at_raw,dict) else None
            valid_reconciliation=(reconciliation.get("schema_version")=="1" and reconciliation.get("recovery_rule")=="abandon-incomplete-acquisition-1" and reconciliation.get("disposition")=="abandoned-non-authoritative" and covered==pages and reconciliation.get("request_authority")==expected_authority and len(providers)==1 and reconciliation.get("provider") in providers and len(families)==1 and reconciliation.get("family") in families and latest is not None and reconciled_at is not None and reconciled_at>=latest and manifest.get("acquired_at",{}).get("datetime_utc")==reconciled_at_raw.get("datetime_utc"))
            if not valid_reconciliation:acquisition_partial.append(f"acquisition:{group}:invalid-reconciliation")
            continue
        referenced_pages={x.get("manifest_entry_id") for x in envelopes[0][1].get("pages",()) if isinstance(x,dict)}
        if envelopes[0][1].get("page_record_kind")!="pr17c2-supporting-session-page" and referenced_pages!=pages:acquisition_partial.append(f"acquisition:{group}:page-set-conflict")
    authoritative=[]
    bad=set(missing)|set(corrupt)
    for item in valid:
        labels=set()
        if item.get("raw_object_sha256"):labels.add(f"raw:{item['raw_object_sha256']}")
        if item.get("normalized_object_id"):labels.add(item["normalized_object_id"])
        if not labels&bad:authoritative.append(item["manifest_entry_id"])
    return ArchiveIntegrityResult(tuple(referenced),tuple(missing),tuple(corrupt),orphaned,
        tuple(sorted(set(malformed+malformed_paths))),tuple(sorted(incompatible)),tuple(sorted(set(archive.temporary_files())|set(acquisition_partial))),tuple(sorted(authoritative)))


def reconcile_incomplete_acquisitions(archive:NamespaceArchive,*,reconciled_at:datetime)->tuple[str,...]:
    """Immutably abandon every unambiguous page-only acquisition after restart."""
    _utc(reconciled_at,"acquisition reconciliation")
    entries=archive.entries();groups={};existing=set()
    for entry in entries:
        identity=entry.get("normalized_object_id")
        if not identity:continue
        value=json.loads(archive.read_verified("normalized",identity));kind=value.get("record_kind");group=value.get("acquisition_id")
        if kind=="pr17c1-provider-page" and isinstance(group,str):groups.setdefault(group,[]).append((entry,value))
        elif kind in {"pr17c1-acquisition-bundle","pr17c1-acquisition-reconciliation"} and isinstance(group,str):existing.add(group)
    created=[]
    for group,page_values in sorted(groups.items()):
        if group in existing:continue
        ordered=tuple(sorted(page_values,key=lambda pair:pair[1].get("position",-1)));providers={value.get("provider") for _,value in ordered};families={entry.get("command","")[:-5] for entry,_ in ordered if entry.get("command","").endswith("-page")}
        positions=tuple(value.get("position") for _,value in ordered);latest=max(datetime.fromisoformat(entry["acquired_at"]["datetime_utc"]) for entry,_ in ordered)
        if len(providers)!=1 or len(families)!=1 or positions!=tuple(range(len(ordered))) or reconciled_at<latest:raise OperationsError("acquisition-reconciliation-ambiguous",group)
        provider=next(iter(providers));family=next(iter(families));page_ids=tuple(entry["manifest_entry_id"] for entry,_ in ordered)
        request_authority=tuple({"position":value.get("position"),"request_identity":value.get("request_identity"),"endpoint":value.get("endpoint"),"raw_sha256":value.get("raw_sha256"),"started_at":value.get("started_at"),"completed_at":value.get("completed_at")} for _,value in ordered)
        normalized={"schema_version":"1","record_kind":"pr17c1-acquisition-reconciliation","acquisition_id":group,"provider":provider,"family":family,"page_manifest_ids":page_ids,"request_authority":request_authority,"detected_incompleteness":"missing-envelope","disposition":"abandoned-non-authoritative","reason":"fresh-process retry requires truthful new chronology","recovery_rule":"abandon-incomplete-acquisition-1","reconciled_at":reconciled_at}
        values=_entry_values(archive=archive,command="reconcile-acquisition",request_id=request_identity({"acquisition_id":group,"pages":page_ids,"recovery_rule":"abandon-incomplete-acquisition-1"}),invoked_at=reconciled_at,endpoint="local://archive/acquisition-reconciliation",disposition=Disposition.SUCCESS,protocol_id=ordered[0][0].get("protocol_id"),design=DesignAuthority.SUPPORTING,diagnostics=("immutable non-authoritative acquisition abandonment",),provider_effective_at=reconciled_at);values["provider_id"]="archive-reconciliation"
        entry=archive.commit(raw_body=canonical_bytes(normalized),normalized=normalized,entry_values=values);created.append(entry.manifest_entry_id)
    return tuple(created)


def authoritative_entries(archive:NamespaceArchive)->tuple[Mapping[str,Any],...]:
    integrity=reconcile_archive(archive)
    if integrity.blocking:raise OperationsError("archive-integrity-failure",canonical_bytes(integrity).decode())
    allowed=set(integrity.authoritative_manifest_ids)
    return tuple(item for item in archive.entries() if item["manifest_entry_id"] in allowed)


def rebuild_index(archive: NamespaceArchive) -> str:
    with archive.mutation_lock():
        integrity=reconcile_archive(archive)
        if integrity.blocking:raise OperationsError("archive-integrity-failure","referenced archive authority is incomplete or corrupt")
        entries=authoritative_entries(archive)
        temporary = archive.root / f".index-{uuid.uuid4().hex}.sqlite3"
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE manifest (id TEXT PRIMARY KEY, command TEXT NOT NULL, disposition TEXT NOT NULL, acquired_at TEXT NOT NULL, raw_digest TEXT, normalized_id TEXT, protocol_id TEXT, design TEXT NOT NULL)")
            connection.executemany("INSERT INTO metadata VALUES (?,?)", (("schema_version",INDEX_SCHEMA_VERSION),("builder_version",INDEX_BUILDER_VERSION),("namespace",archive.config.namespace),("mode",archive.config.mode.value)))
            for entry in sorted(entries, key=lambda x: x["manifest_entry_id"]):
                connection.execute("INSERT INTO manifest VALUES (?,?,?,?,?,?,?,?)", (entry["manifest_entry_id"],entry["command"],entry["disposition"],entry["acquired_at"]["datetime_utc"],entry.get("raw_object_sha256"),entry.get("normalized_object_id"),entry.get("protocol_id"),entry["design_authority"]))
            connection.commit(); connection.execute("PRAGMA integrity_check").fetchone()
        finally: connection.close()
        os.replace(temporary, archive.index_path)
        return sha256_bytes(archive.index_path.read_bytes())


def index_health(archive: NamespaceArchive) -> tuple[str, tuple[str, ...]]:
    if not archive.index_path.exists(): return "missing", ("rebuild required",)
    connection=None
    try:
        connection=sqlite3.connect(f"file:{archive.index_path}?mode=ro", uri=True)
        metadata=dict(connection.execute("SELECT key,value FROM metadata")); ids={row[0] for row in connection.execute("SELECT id FROM manifest")}
        integrity=connection.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.DatabaseError as exc: return "corrupt", (str(exc),)
    finally:
        if connection is not None: connection.close()
    try:expected={entry["manifest_entry_id"] for entry in authoritative_entries(archive)}
    except OperationsError as exc:return "archive-invalid",(exc.detail,)
    if metadata.get("schema_version")!=INDEX_SCHEMA_VERSION or metadata.get("builder_version")!=INDEX_BUILDER_VERSION: return "stale", ("version mismatch",)
    if ids!=expected: return "disagreement", ("index/full-scan mismatch",)
    if integrity!="ok": return "corrupt", (integrity,)
    return "healthy", ()


def sync_secondary(archive: NamespaceArchive) -> Mapping[str, int]:
    copied=identical=conflicts=missing=0
    with archive.mutation_lock():
        integrity=reconcile_archive(archive)
        if integrity.blocking:raise OperationsError("archive-integrity-failure","secondary synchronization requires complete referenced authority")
        destination=archive.config.secondary_root.resolve(); destination.mkdir(parents=True, exist_ok=True)
        entries=authoritative_entries(archive);sources=[]
        for entry in entries:
            if entry.get("raw_object_sha256"):sources.append(archive._path("raw",f"raw:{entry['raw_object_sha256']}"))
            if entry.get("normalized_object_id"):sources.append(archive._path("normalized",entry["normalized_object_id"]))
            sources.append(archive._path("manifest",entry["manifest_entry_id"]))
        for source in sorted(set(sources)):
                relative=source.relative_to(archive.root); target=destination/relative; target.parent.mkdir(parents=True,exist_ok=True)
                body=source.read_bytes()
                if not source.exists(): missing+=1; continue
                temporary=target.parent/f".{target.name}.{uuid.uuid4().hex}.partial"
                try:
                    with temporary.open("xb") as handle: handle.write(body); handle.flush(); os.fsync(handle.fileno())
                    os.link(temporary,target)
                    copied+=1
                except FileExistsError:
                    if target.read_bytes()==body: identical+=1
                    else: conflicts+=1; continue
                finally: temporary.unlink(missing_ok=True)
                if sha256_bytes(target.read_bytes())!=sha256_bytes(body): conflicts+=1
    return {"copied":copied,"identical":identical,"conflicts":conflicts,"missing":missing}


def secondary_status(archive: NamespaceArchive) -> Mapping[str, int]:
    try:entries=authoritative_entries(archive)
    except OperationsError:return {"lag":0,"conflicts":0,"unexplained":0,"archive_invalid":1}
    paths=[]
    for entry in entries:
        if entry.get("raw_object_sha256"):paths.append(archive._path("raw",f"raw:{entry['raw_object_sha256']}"))
        if entry.get("normalized_object_id"):paths.append(archive._path("normalized",entry["normalized_object_id"]))
        paths.append(archive._path("manifest",entry["manifest_entry_id"]))
    primary={str(p.relative_to(archive.root)):sha256_bytes(p.read_bytes()) for p in sorted(set(paths))}
    secondary_root=archive.config.secondary_root
    secondary={str(p.relative_to(secondary_root)):sha256_bytes(p.read_bytes()) for p in secondary_root.glob("*/*/*") if p.is_file()} if secondary_root.exists() else {}
    conflicts=sum(1 for key,value in primary.items() if key in secondary and secondary[key]!=value)
    unexplained=sum(1 for key in secondary if key not in primary)
    return {"lag":sum(1 for key,value in primary.items() if secondary.get(key)!=value),"conflicts":conflicts,"unexplained":unexplained,"archive_invalid":0}


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    schema_version: str
    command: str
    configuration_id: str
    namespace: str
    mode: OperatingMode
    ready: bool
    state: str
    facts: tuple[tuple[str, Any], ...]
    issues: tuple[str, ...]
    def to_json(self) -> str: return canonical_bytes(self).decode("utf-8")
    def to_text(self) -> str:
        lines=[f"{self.command}: {self.state}",f"namespace: {self.mode.value}/{self.namespace}",f"configuration: {self.configuration_id}"]
        lines.extend(f"{key}: {value}" for key,value in self.facts); lines.extend(f"issue: {item}" for item in self.issues)
        return "\n".join(lines)


def status(archive: NamespaceArchive) -> DiagnosticResult:
    integrity=reconcile_archive(archive)
    try:entries=authoritative_entries(archive)
    except OperationsError:entries=()
    health,index_issues=index_health(archive); secondary=secondary_status(archive)
    successes=[x for x in entries if x["disposition"] in {Disposition.SUCCESS.value,Disposition.DERIVED.value}]; failures=[x for x in entries if x["disposition"] not in {Disposition.SUCCESS.value,Disposition.DERIVED.value}]
    issues=list(index_issues)
    for name,values in (("missing",integrity.referenced_missing),("corrupt",integrity.referenced_corrupt),("orphaned",integrity.orphaned),("malformed",integrity.malformed),("incompatible",integrity.incompatible),("partial",integrity.partial)):
        issues.extend(f"archive {name}: {item}" for item in values)
    if secondary["lag"]: issues.append("secondary synchronization lag")
    if secondary["conflicts"]: issues.append("secondary conflict")
    prospective=[x for x in entries if x["command"]=="capture-prospective"]
    facts=(("manifest_entries",len(entries)),("archive_integrity","healthy" if integrity.healthy else "attention"),("archive_orphans",len(integrity.orphaned)),("latest_success",successes[-1]["manifest_entry_id"] if successes else "none"),("latest_failure",failures[-1]["manifest_entry_id"] if failures else "none"),("prospective_slot_dispositions",tuple(sorted((x["disposition"],tuple(d for d in x["diagnostics"] if d.startswith("slot:"))) for x in prospective))),("index",health),("secondary_lag",secondary["lag"]),("secondary_conflicts",secondary["conflicts"]),("temporary_files",len(integrity.partial)))
    return DiagnosticResult(OPERATIONS_SCHEMA_VERSION,"status",archive.config.identity,archive.config.namespace,archive.config.mode,not issues,"ready" if not issues else "attention",facts,tuple(sorted(issues)))


def preflight(archive: NamespaceArchive, *, requested_mode: OperatingMode, credentials_configured: bool,
              protocol_ids: Iterable[str] = ()) -> DiagnosticResult:
    issues=[]
    if requested_mode is not archive.config.mode: issues.append("requested mode conflicts with namespace")
    if requested_mode is OperatingMode.ACTIVATED: issues.append("activation state is prohibited in PR17B2")
    if not credentials_configured: issues.append("provider credentials are not configured")
    if not tuple(protocol_ids): issues.append("required Protocol/design authority absent")
    integrity=reconcile_archive(archive);health,_=index_health(archive)
    if not integrity.healthy:issues.append("primary archive reconciliation is not healthy")
    if health not in ("healthy","missing"): issues.append(f"index is {health}")
    secondary=secondary_status(archive)
    if secondary["conflicts"] or secondary["lag"]: issues.append("secondary destination is not synchronized")
    facts=(("index",health),("lock_available",_lock_available(archive)),("secondary_lag",secondary["lag"]),("protocol_count",len(tuple(protocol_ids))),("timezone",archive.config.timezone_name))
    if not facts[1][1]: issues.append("namespace lock unavailable")
    return DiagnosticResult(OPERATIONS_SCHEMA_VERSION,"preflight",archive.config.identity,archive.config.namespace,archive.config.mode,not issues,"ready" if not issues else "not-ready",facts,tuple(sorted(set(issues))))


def _lock_available(archive: NamespaceArchive) -> bool:
    if not archive.root.exists() or not archive.lock_path.exists(): return True
    handle=archive.lock_path.open("rb")
    try:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.flock(handle.fileno(),fcntl.LOCK_UN); return True
    except BlockingIOError: return False
    finally: handle.close()


def _is_supporting_session_authority_rejection(exc:OperationsError)->bool:
    """Localize only completion or selected acquisition-envelope authority failures."""
    return exc.code.startswith("supporting-session") or exc.code in {
        "acquisition-chronology-conflict",
        "acquisition-contract-conflict",
        "acquisition-contract-reconstruction-conflict",
        "acquisition-dependency-conflict",
        "acquisition-incompatible",
        "acquisition-incomplete",
        "acquisition-page-conflict",
        "acquisition-union-conflict",
    }


def inspect_archive(archive: NamespaceArchive) -> DiagnosticResult:
    integrity=reconcile_archive(archive)
    try:entries=authoritative_entries(archive)
    except OperationsError:entries=()
    for entry in entries: _verify_entry_objects(archive,entry)
    if any(entry.get("command")=="publish-retrospective-analysis" for entry in entries):
        from forecast_standalone_publication import _published
        _published(archive)
    by_design={tag.value:sum(1 for item in entries if item["design_authority"]==tag.value) for tag in DesignAuthority}
    kinds=[];session_pages=[];completion_sessions=set();retrospective_bundles=[]
    for entry in archive.entries():
        if entry.get("normalized_object_id"):
            value=json.loads(archive.read_verified("normalized",entry["normalized_object_id"]));kinds.append(value.get("record_kind"))
            if value.get("record_kind")=="pr17c2-supporting-session-page":session_pages.append(value)
            if value.get("record_kind")=="pr17c2-supporting-session-completion":completion_sessions.add(value.get("session_id"))
            if value.get("record_kind")=="pr17c1-acquisition-bundle" and value.get("family")=="refresh-retrospective-supporting":retrospective_bundles.append(value)
    failed_session_pages=sum(1 for item in archive.entries() if item.get("command")=="refresh-retrospective-supporting-page" and item.get("disposition")!="success")
    session_ids={value.get("session_id") for value in session_pages};valid_sessions=set();authoritative_bundle_manifests=set();completion_issues=[]
    from forecast_standalone_activation import verify_supporting_session_completion
    for session_id in sorted(completion_sessions):
        try:
            verified=verify_supporting_session_completion(archive,session_id);valid_sessions.add(session_id);authoritative_bundle_manifests.update((verified["mlb_manifest_id"],verified["kalshi_manifest_id"]))
        except OperationsError as exc:
            if not _is_supporting_session_authority_rejection(exc):raise
            completion_issues.append(f"supporting session completion invalid: {session_id}: {exc.code}")
    unresolved=sum(1 for item in integrity.partial if item.endswith(":missing-envelope"));abandoned=kinds.count("pr17c1-acquisition-reconciliation");complete=kinds.count("pr17c1-acquisition-bundle")
    retrospective_manifest_ids={entry["manifest_entry_id"] for entry in entries if entry.get("normalized_object_id") and json.loads(archive.read_verified("normalized",entry["normalized_object_id"])).get("record_kind")=="pr17c1-acquisition-bundle" and json.loads(archive.read_verified("normalized",entry["normalized_object_id"])).get("family")=="refresh-retrospective-supporting"}
    non_authoritative=len(retrospective_manifest_ids-authoritative_bundle_manifests)
    facts=(("verified_entries",len(entries)),("orphaned_objects",len(integrity.orphaned)),("missing_objects",len(integrity.referenced_missing)),("corrupt_objects",len(integrity.referenced_corrupt)),("unresolved_partial_acquisitions",unresolved),("preserved_supporting_session_pages",len(session_pages)),("supporting_session_pages",len(session_pages)),("incomplete_supporting_sessions",len(session_ids-valid_sessions)),("rejected_supporting_sessions",len(completion_issues)),("valid_complete_supporting_sessions",len(valid_sessions)),("complete_supporting_sessions",len(valid_sessions)),("non_authoritative_retrospective_provider_bundles",non_authoritative),("authoritative_completed_retrospective_sessions",len(valid_sessions)),("failed_supporting_pages",failed_session_pages),("reconciled_abandoned_acquisitions",abandoned),("complete_authoritative_acquisitions",complete-len(retrospective_bundles)+2*len(valid_sessions)))+tuple((f"{key}_entries",value) for key,value in sorted(by_design.items()))
    issues=tuple(f"archive orphaned: {item}" for item in integrity.orphaned)+tuple(f"archive missing: {item}" for item in integrity.referenced_missing)+tuple(f"archive corrupt: {item}" for item in integrity.referenced_corrupt)+tuple(f"archive malformed: {item}" for item in integrity.malformed)+tuple(f"archive incompatible: {item}" for item in integrity.incompatible)+tuple(f"archive partial: {item}" for item in integrity.partial)+tuple(completion_issues)
    ready=integrity.healthy
    state="verified-with-rejected-sessions" if ready and completion_issues else ("verified" if ready else "attention")
    return DiagnosticResult(OPERATIONS_SCHEMA_VERSION,"inspect",archive.config.identity,archive.config.namespace,archive.config.mode,ready,state,facts,issues)


COMMAND_CAPABILITIES={
    "acquire-schedule":"provider+primary", "acquire-classification":"provider+primary", "acquire-retrospective":"provider+primary",
    "capture-prospective":"single-provider-request+primary", "reconcile-outcomes":"provider+primary", "sync-secondary":"secondary-only",
    "reconcile-acquisitions":"primary-operational-integrity", "rebuild-index":"derived-index-only", "status":"read-only", "preflight":"read-only", "inspect":"read-only",
}


PR17_GRAPH_BUCKETS={
    "StandaloneResearchActivationBoundary":"activation_boundaries","StandaloneProbabilitySourceProtocol":"protocols",
    "ResearchCaptureOpportunity":"opportunities","StandaloneEventClassificationEvidence":"classifications",
    "ResearchEventEligibilityContext":"eligibility_contexts","PopulationEligibilityResult":"eligibility_results",
    "HistoricalCandleQueryManifest":"manifests","HistoricalMarketCandleObservation":"candles",
    "HistoricalCandleProbabilityDerivation":"historical_derivations","ProspectiveCaptureAttempt":"attempts",
    "ProspectiveStandaloneSnapshot":"snapshots","MarketObservation":"market_observations","ProviderMarketSeries":"market_series",
    "MarketProbabilityDerivation":"market_derivations","OutcomeHistory":"outcome_histories",
    "ProbabilitySourceMeasurementV3":"measurements","ProbabilitySourceCoverageV3":"coverages",
    "ProbabilitySourcePerformanceV3":"performances","ProbabilitySourcePerformanceReport":"reports",
}


@dataclass(frozen=True,slots=True)
class ScientificArchiveState:
    analysis_boundary:datetime
    objects:tuple[Any,...]
    graph:tuple[tuple[str,tuple[Any,...]],...]
    reports:tuple[Any,...]
    source_manifest_ids:tuple[str,...]=()
    def bucket(self,name:str)->tuple[Any,...]:return dict(self.graph).get(name,())


def pr17_contract_bundle(*contracts:Any)->Mapping[str,Any]:
    if not contracts:raise OperationsError("empty-contract-bundle","PR17B1 bundle")
    values=[]
    for contract in contracts:
        if type(contract).__name__ not in PR17_GRAPH_BUCKETS or not hasattr(contract,"to_json"):
            raise OperationsError("unsupported-pr17-contract",type(contract).__name__)
        payload=contract.to_json();
        from forecast_standalone_research import deserialize_v3
        if deserialize_v3(payload)!=contract:raise OperationsError("pr17-serialization-conflict",type(contract).__name__)
        values.append(payload)
    return {"schema_version":OPERATIONS_SCHEMA_VERSION,"record_kind":"pr17b1-contract-bundle","contracts":tuple(sorted(values))}


def archive_pr17_authority(archive:NamespaceArchive,contracts:Iterable[Any],*,recorded_at:datetime)->tuple[ManifestEntry,...]:
    """Persist approved synthetic PR17B1 authority; never invent or reinterpret it."""
    entries=[]
    with archive.mutation_lock():
        for contract in sorted(tuple(contracts),key=lambda item:(type(item).__name__,item.to_json())):
            normalized=pr17_contract_bundle(contract);raw=canonical_bytes(normalized)
            protocol_id=getattr(contract,"protocol_id",getattr(contract,"standalone_probability_source_protocol_id",None))
            design=getattr(contract,"design_tag",None)
            design_authority=DesignAuthority(design.value) if design is not None else DesignAuthority.SUPPORTING
            request_id=request_identity({"contract_type":type(contract).__name__,"contract_sha256":sha256_bytes(contract.to_json().encode())})
            values=_entry_values(archive=archive,command="archive-authority",request_id=request_id,invoked_at=recorded_at,
                endpoint="fixture://approved-pr17b1-authority",disposition=Disposition.SUCCESS,protocol_id=protocol_id,
                design=design_authority,diagnostics=("approved synthetic PR17B1 authority",),provider_effective_at=getattr(contract,"effective_at",None))
            values["provider_id"]="approved-synthetic-authority"
            entries.append(archive._commit_locked(raw_body=raw,normalized=normalized,entry_values=values))
    return tuple(entries)


def _contracts_from_entry(archive:NamespaceArchive,entry:Mapping[str,Any],prior_objects:Iterable[Any]=(),excluded_supporting_sessions:Iterable[str]=(),_exclude_retrospective_publications:bool=False)->tuple[Any,...]:
    identity=entry.get("normalized_object_id")
    if not identity:return ()
    value=json.loads(archive.read_verified("normalized",identity))
    if value.get("record_kind")=="pr17c3-retrospective-publication" or entry.get("command")=="publish-retrospective-analysis":
        if _exclude_retrospective_publications:return ()
        from forecast_standalone_publication import _published,verify_publication
        publications=_published(archive)
        if len(publications)!=1 or publications[0][0]["manifest_entry_id"]!=entry["manifest_entry_id"]:
            raise OperationsError("retrospective-publication-conflict","publication manifest selection is ambiguous")
        return verify_publication(archive,value)
    if value.get("record_kind")=="pr17c1-acquisition-bundle":
        if value.get("family")=="refresh-retrospective-supporting" and value.get("page_record_kind")=="pr17c2-supporting-session-page":
            session=value.get("supporting_session_id") or value.get("acquisition_id","").rsplit(":",1)[0]
            if session in set(excluded_supporting_sessions):return ()
            from forecast_standalone_activation import verify_supporting_session_completion
            try:verified=verify_supporting_session_completion(archive,session)
            except OperationsError as exc:
                if _is_supporting_session_authority_rejection(exc):return ()
                raise
            if entry.get("manifest_entry_id") not in {verified["mlb_manifest_id"],verified["kalshi_manifest_id"]}:return ()
        from forecast_standalone_activation import refresh_supporting_from_raw,reconcile_outcomes_from_raw,verify_acquisition_bundle
        union,payloads=verify_acquisition_bundle(archive,value,include_union=True)
        from forecast_standalone_research import deserialize_v3
        stored=tuple(deserialize_v3(payload) for payload in payloads)
        if len(payloads)!=len(set(payloads)):raise OperationsError("acquisition-contract-conflict","acquisition contains duplicate contracts")
        class PriorState:
            def bucket(self,name):return tuple(x for x in prior_objects if PR17_GRAPH_BUCKETS.get(type(x).__name__)==name)
        prior=PriorState();started=datetime.fromisoformat(value["command_started_at_iso"]);family=value.get("family");provider=value.get("provider")
        if family=="reconcile-outcomes" and provider=="mlb-stats-api":expected=reconcile_outcomes_from_raw(archive=None,mlb_raw=union,collected_at=started,prior_state=prior,derive_only=True)
        elif family in {"refresh-supporting","refresh-retrospective-supporting"} and provider=="mlb-stats-api":expected=tuple(x for x in refresh_supporting_from_raw(archive=None,mlb_raw=union,kalshi_raw=b'{"cursor":"","markets":[]}',collected_at=started,prior_state=prior,derive_only=True,acquisition_command=family,union_rule=value.get("union_rule")) if type(x).__name__!="ProviderMarketSeries")
        elif family in {"refresh-supporting","refresh-retrospective-supporting"} and provider=="kalshi":
            dependencies=value.get("dependencies",())
            if not isinstance(dependencies,list) or len(dependencies)!=1:raise OperationsError("acquisition-dependency-conflict","Kalshi acquisition requires one MLB dependency")
            mlb_union=None;mlb_union_rule=None
            for candidate_entry in authoritative_entries(archive):
                normalized_id=candidate_entry.get("normalized_object_id")
                if not normalized_id:continue
                candidate=json.loads(archive.read_verified("normalized",normalized_id))
                if candidate.get("record_kind")=="pr17c1-acquisition-bundle" and candidate.get("acquisition_id")==dependencies[0] and candidate.get("provider")=="mlb-stats-api":mlb_union,_=verify_acquisition_bundle(archive,candidate,include_union=True);mlb_union_rule=candidate.get("union_rule");break
            if mlb_union is None:raise OperationsError("acquisition-dependency-conflict","MLB dependency is absent")
            expected=tuple(x for x in refresh_supporting_from_raw(archive=None,mlb_raw=mlb_union,kalshi_raw=union,collected_at=started,prior_state=prior,derive_only=True,acquisition_command=family,union_rule=mlb_union_rule) if type(x).__name__=="ProviderMarketSeries")
        else:raise OperationsError("acquisition-incompatible","unsupported PR17C1 acquisition family")
        expected_payloads=tuple(sorted(x.to_json() for x in expected))
        if tuple(sorted(payloads))!=expected_payloads:
            stored_set=set(payloads);expected_set=set(expected_payloads)
            def contract_type(payload):
                try:
                    value=json.loads(payload)
                    return value.get("__type__","unknown")
                except json.JSONDecodeError:return "invalid"
            detail=f"{family}/{provider}: stored-only {tuple(sorted(contract_type(x) for x in stored_set-expected_set))}; page-derived-only {tuple(sorted(contract_type(x) for x in expected_set-stored_set))}"
            raise OperationsError("acquisition-contract-reconstruction-conflict",detail)
        return tuple(expected)
    if entry.get("command") in {"refresh-supporting","reconcile-outcomes"}:
        raise OperationsError("acquisition-page-authority-missing","PR17C1 provider contracts require a verified acquisition envelope")
    if value.get("record_kind")!="pr17b1-contract-bundle" or value.get("schema_version")!=OPERATIONS_SCHEMA_VERSION:return ()
    from forecast_standalone_research import deserialize_v3
    contracts=tuple(deserialize_v3(payload) for payload in value.get("contracts",()))
    if canonical_bytes(pr17_contract_bundle(*contracts))!=canonical_bytes(value):raise OperationsError("pr17-reconstruction-conflict",entry["manifest_entry_id"])
    return contracts


def replay_pr17_archive(archive:NamespaceArchive,*,analysis_boundary:datetime,excluded_supporting_sessions:Iterable[str]=(),_exclude_retrospective_publications:bool=False)->ScientificArchiveState:
    _utc(analysis_boundary,"archive replay boundary")
    entries=authoritative_entries(archive);objects=[];source_manifest_ids=[]
    for entry in entries:
        if _exclude_retrospective_publications and datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])>analysis_boundary:continue
        if entry.get("command")=="publish-retrospective-analysis" and datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])>analysis_boundary:continue
        contracts=_contracts_from_entry(archive,entry,objects,excluded_supporting_sessions,_exclude_retrospective_publications)
        if contracts:source_manifest_ids.append(entry["manifest_entry_id"])
        objects.extend(contracts)
    keyed={}
    for item in objects:
        key=(type(item).__name__,item.to_json())
        keyed[key]=item
    objects=tuple(value for _,value in sorted(keyed.items()))
    histories={}
    for item in tuple(x for x in objects if type(x).__name__=="OutcomeHistory"):
        prior=histories.get(item.canonical_event_id)
        if prior is not None:
            shorter,longer=sorted((prior,item),key=lambda value:len(value.observations))
            if longer.observations[:len(shorter.observations)]!=shorter.observations:raise OperationsError("outcome-history-conflict",item.canonical_event_id)
            histories[item.canonical_event_id]=longer
        else:histories[item.canonical_event_id]=item
    if histories:objects=tuple(x for x in objects if type(x).__name__!="OutcomeHistory")+tuple(histories[key] for key in sorted(histories))
    buckets={name:[] for name in set(PR17_GRAPH_BUCKETS.values())}
    for item in objects:buckets[PR17_GRAPH_BUCKETS[type(item).__name__]].append(item)
    canonical={name:tuple(sorted(values,key=lambda item:item.to_json())) for name,values in buckets.items()}
    from forecast_standalone_research import validate_standalone_research_graph
    reports=validate_standalone_research_graph(**canonical,analysis_boundary=analysis_boundary)
    return ScientificArchiveState(analysis_boundary,objects,tuple(sorted(canonical.items())),reports,tuple(sorted(source_manifest_ids)))


def request_identity(request: Mapping[str, Any]) -> str:
    _reject_secrets(request); return f"sanitized-request:{sha256_bytes(canonical_bytes(request))}"


def invocation_identity(*, command: str, config: DeploymentConfig, invoked_at: datetime,
                        request_id: str, protocol_id: str | None) -> str:
    return f"operations-invocation:{sha256_bytes(canonical_bytes((command,config.identity,_utc(invoked_at,'invocation'),request_id,protocol_id)))}"


def _entry_values(*, archive: NamespaceArchive, command: str, request_id: str, invoked_at: datetime,
                  endpoint: str, disposition: Disposition, protocol_id: str | None,
                  design: DesignAuthority, diagnostics: Iterable[str] = (),
                  provider_effective_at: datetime | None = None) -> dict[str, Any]:
    provider_id="mlb-stats-api" if command in {"acquire-schedule","acquire-classification","reconcile-outcomes"} else PROVIDER_ID
    return dict(command=command, invocation_id=invocation_identity(command=command,config=archive.config,invoked_at=invoked_at,request_id=request_id,protocol_id=protocol_id),
        provider_id=provider_id,endpoint=endpoint,sanitized_request_id=request_id,acquired_at=invoked_at,
        provider_effective_at=provider_effective_at,predecessor_id=None,correction_reason=None,
        disposition=disposition,protocol_id=protocol_id,design_authority=design,diagnostics=tuple(diagnostics))


def _provider_effective(normalized: Mapping[str,Any] | None) -> datetime | None:
    if normalized is None or normalized.get("effective_at") is None:return None
    try:value=datetime.fromisoformat(str(normalized["effective_at"]).replace("Z","+00:00"));_utc(value,"provider effective time");return value
    except (ValueError,OperationsError) as exc:raise OperationsError("validation-failure","invalid provider effective timestamp") from exc


def run_supporting_acquisition(*, archive: NamespaceArchive, command: str, design: DesignAuthority,
                               transport: Transport, endpoint: str, request: Mapping[str, str],
                               invoked_at: datetime, now: Callable[[], datetime], sleeper: Callable[[float], None],
                               validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
                               protocol_id: str | None = None) -> tuple[AcquisitionResult, ManifestEntry]:
    if command not in {"acquire-schedule","acquire-classification","acquire-retrospective","reconcile-outcomes"}:
        raise OperationsError("command-boundary", command)
    request_id=request_identity(request)
    with archive.mutation_lock():
        result=acquire_with_retries(transport=transport,endpoint=endpoint,request=request,policy=archive.config.retry_policy,now=now,sleeper=sleeper,validator=validator)
        diagnostics=tuple(f"attempt:{item.attempt}:{_utc(item.started_at,'attempt start')}:{_utc(item.completed_at,'attempt completion')}:{item.disposition.value}:{item.status_code}:{item.retry_after_seconds}" for item in result.attempts)+(result.detail,)
        values=_entry_values(archive=archive,command=command,request_id=request_id,invoked_at=invoked_at,endpoint=endpoint,
            disposition=result.disposition,protocol_id=protocol_id,design=design,diagnostics=diagnostics,
            provider_effective_at=_provider_effective(result.normalized))
        if result.disposition is Disposition.SUCCESS:
            assert result.raw_body is not None and result.normalized is not None
            entry=archive._commit_locked(raw_body=result.raw_body,normalized=result.normalized,entry_values=values)
        else: entry=archive._record_failure_locked(entry_values=values,raw_body=result.raw_body)
        return result,entry


@dataclass(frozen=True,slots=True)
class ProspectiveDiscoveryResult:
    configuration_id:str
    namespace:str
    trusted_now:datetime
    due_opportunity_ids:tuple[str,...]
    provider_request_count:int
    created_attempt_ids:tuple[str,...]
    created_snapshot_ids:tuple[str,...]
    disposition:str


def discover_and_capture_prospective(*,archive:NamespaceArchive,
        transport_factory:Callable[[Any,Any],Transport],clock:Callable[[],datetime],
        observation_adapter:Callable[[Mapping[str,Any],bytes,datetime,datetime,Any,Any],Any]|None=None)->ProspectiveDiscoveryResult:
    """Discover PR17B1-authorized work from archive state using only a trusted clock."""
    from forecast_comparative_research import PopulationEligibilityDisposition,PopulationEligibilityValidationStatus
    from forecast_standalone_research import (AcquisitionFailed,AttemptFailureCategory,AttemptValidationFailure,CapturedInvalid,
        CapturedValid,Missed,ProspectiveCaptureAttempt,SkippedAfterSuccess,StandaloneDesignTag,
        reconcile_prospective_snapshot,resolve_standalone_schedule_authority,slot_for_time)
    from market_contracts import MarketObservation
    now=clock();_utc(now,"trusted execution clock")
    created=[];snapshots=[];due=[];calls=0
    with archive.mutation_lock():
        state=replay_pr17_archive(archive,analysis_boundary=now)
        protocols=tuple(item for item in state.bucket("protocols") if item.design_tag is StandaloneDesignTag.PROSPECTIVE)
        configured=set(archive.config.research_protocol_ids)
        protocols=tuple(item for item in protocols if item.standalone_probability_source_protocol_id in configured)
        if len(protocols)!=1:raise OperationsError("prospective-authority-invalid","configuration must resolve exactly one archived prospective Protocol")
        protocol=protocols[0];activations={x.standalone_research_activation_boundary_id:x for x in state.bucket("activation_boundaries")};activation=activations.get(protocol.activation_boundary_id)
        if activation is None or activation.decision_effective_at>now:raise OperationsError("prospective-authority-invalid","activation authority is absent or future-effective")
        histories={x.canonical_event_id:x for x in state.bucket("outcome_histories")};contexts={x.research_capture_opportunity_id:x for x in state.bucket("eligibility_contexts")};results={x.research_capture_opportunity_id:x for x in state.bucket("eligibility_results")}
        series_values=state.bucket("market_series");existing=list(state.bucket("attempts"));existing_snapshots=list(state.bucket("snapshots"))
        opportunities=tuple(x for x in state.bucket("opportunities") if x.protocol_id==protocol.standalone_probability_source_protocol_id)
        for opportunity in sorted(opportunities,key=lambda item:item.research_capture_opportunity_id):
            context=contexts.get(opportunity.research_capture_opportunity_id);result=results.get(opportunity.research_capture_opportunity_id)
            if context is None or result is None or result.analysis_boundary>now:raise OperationsError("prospective-authority-invalid","eligibility authority is absent or future-effective")
            if result.disposition is not PopulationEligibilityDisposition.ELIGIBLE or result.validation_status is not PopulationEligibilityValidationStatus.VALID:continue
            history=histories.get(context.canonical_event_id)
            if history is None:raise OperationsError("prospective-authority-invalid","Schedule authority does not resolve")
            schedule,target=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,
                eligibility_context=context,eligibility_result=result,outcome_history=history,analysis_boundary=now)
            proposition=f"winner:{schedule.canonical_event_id}:{schedule.home_participant_id}"
            matching_series=tuple(item for item in series_values if item.provider==PROVIDER_ID and item.proposition_id==proposition)
            series=matching_series[0] if len(matching_series)==1 else None
            provider_market_id=series.provider_market_id if series is not None else f"unmapped-kalshi:{schedule.canonical_event_id}"
            mapping_diagnostic="unique-market" if series is not None else ("no-unambiguous-market" if not matching_series else "ambiguous-market")
            owned=[item for item in existing if item.opportunity_id==opportunity.research_capture_opportunity_id]
            if any(item.effective_at>now for item in owned):raise OperationsError("prospective-authority-invalid","future-effective attempt authority")
            by_slot={item.slot:item for item in owned};success=next((item for item in owned if isinstance(item.result,CapturedValid)),None)
            if existing_snapshots and any(item.opportunity_id==opportunity.research_capture_opportunity_id for item in existing_snapshots):continue
            at_terminal=now>target+timedelta(minutes=5);current=None;decision_time=now
            if not at_terminal and now>=target:
                due.append(opportunity.research_capture_opportunity_id)
                request_start=clock();_utc(request_start,"request authorization")
                if request_start<now:raise OperationsError("trusted-clock-reversed","request authorization precedes discovery")
                # Re-resolve the exact authority at the fresh pre-request boundary while the namespace lock is held.
                refreshed_schedule,refreshed_target=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,
                    eligibility_context=context,eligibility_result=result,outcome_history=history,analysis_boundary=request_start)
                if (refreshed_schedule.observation_id,refreshed_target)!=(schedule.observation_id,target):raise OperationsError("prospective-authority-invalid","authority changed before request authorization")
                decision_time=request_start;at_terminal=request_start>target+timedelta(minutes=5)
                if not at_terminal:current=slot_for_time(target,request_start)
            elapsed=max(-1,min(4,int((decision_time-target).total_seconds()//60))) if decision_time>=target else -1
            upper=4 if at_terminal else elapsed

            def persist_no_call(slot:int,at:datetime)->Any:
                nonlocal success
                invocation=max(at,target+timedelta(minutes=slot));attempt_result=SkippedAfterSuccess(success.prospective_capture_attempt_id) if success else Missed()
                attempt=ProspectiveCaptureAttempt.create(protocol_id=protocol.standalone_probability_source_protocol_id,opportunity_id=opportunity.research_capture_opportunity_id,
                    schedule_observation_id=schedule.observation_id,canonical_event_id=schedule.canonical_event_id,proposition_id=proposition,home_participant_id=schedule.home_participant_id,
                    provider_market_id=provider_market_id,target_at=target,slot=slot,invocation_at=invocation,provider_call_occurred=False,result=attempt_result,
                    effective_at=invocation,diagnostics=("authority-derived no-call disposition",mapping_diagnostic),provenance=result.provenance)
                values=_entry_values(archive=archive,command="capture-prospective",request_id=request_identity({"opportunity_id":opportunity.research_capture_opportunity_id,"slot":slot,"no_call":type(attempt_result).__name__}),invoked_at=invocation,
                    endpoint=archive.config.provider_base_url,disposition=Disposition.SKIPPED_AFTER_SUCCESS if success else Disposition.MISSED,protocol_id=protocol.standalone_probability_source_protocol_id,
                    design=DesignAuthority.PROSPECTIVE,diagnostics=(f"opportunity:{opportunity.research_capture_opportunity_id}",f"slot:{slot}","canonical no-call"))
                archive._commit_normalized_locked(normalized=pr17_contract_bundle(attempt),entry_values=values)
                existing.append(attempt);owned.append(attempt);by_slot[slot]=attempt;created.append(attempt.prospective_capture_attempt_id)
                return attempt

            completion_time=decision_time
            for slot in range(upper+1):
                if slot in by_slot:continue
                if slot==current and success is None and series is not None:
                    transport=transport_factory(opportunity,series)
                    decoded_observation:dict[str,MarketObservation]={}
                    def validate(value:Mapping[str,Any])->Mapping[str,Any]:
                        payload=value.get("contract_json")
                        if not isinstance(payload,str):raise OperationsError("incomplete-response","MarketObservation contract is absent")
                        observation=decode_provider_pr17_contract(payload)
                        if not isinstance(observation,MarketObservation):raise OperationsError("validation-failure","response is not MarketObservation")
                        if (observation.series_id,observation.provider_market_id,observation.canonical_event_id,observation.proposition_id)!=(series.series_id,series.provider_market_id,schedule.canonical_event_id,proposition):raise OperationsError("validation-failure","MarketObservation conflicts with archived authority")
                        decoded_observation["value"]=observation
                        return {"schema_version":OPERATIONS_SCHEMA_VERSION,"contract_json":payload,"record_kind":"prospective-provider-observation"}
                    def adapt_live(value:Mapping[str,Any],raw:bytes,started:datetime,completed:datetime)->Mapping[str,Any]:
                        if observation_adapter is None:return validate(value)
                        observation=observation_adapter(value,raw,started,completed,series,schedule)
                        decoded_observation["value"]=observation
                        return {"schema_version":OPERATIONS_SCHEMA_VERSION,"contract_json":observation.to_json(),"record_kind":"prospective-provider-observation"}
                    def validate_chronology(normalized:Mapping[str,Any],started:datetime,completed:datetime)->None:
                        observation=decoded_observation["value"]
                        if observation.collected_at<started or observation.collected_at>completed:raise OperationsError("validation-failure","MarketObservation collected_at is outside the inclusive trusted request interval")
                    acquired=acquire_prospective_once(transport=transport,endpoint=archive.config.provider_base_url,request={"market_id":series.provider_market_id},timeout_seconds=archive.config.retry_policy.request_timeout_seconds,now=clock,validator=validate,started_at=decision_time,chronology_validator=validate_chronology,raw_validator=adapt_live if observation_adapter is not None else None);calls+=len(acquired.attempts)
                    started=acquired.attempts[0].started_at;completed=acquired.attempts[-1].completed_at;completion_time=completed
                    if started!=decision_time or completed<started:raise OperationsError("trusted-clock-reversed","provider chronology conflicts with authorization")
                    raw_digest=sha256_bytes(acquired.raw_body) if acquired.raw_body is not None else None
                    if acquired.disposition is Disposition.SUCCESS:
                        observation=decoded_observation["value"]
                        attempt_result=CapturedValid(f"raw:{raw_digest}",raw_digest,observation.observation_id);contracts=(observation,)
                    elif acquired.raw_body is not None and acquired.disposition in {Disposition.MALFORMED_RESPONSE,Disposition.INCOMPLETE_RESPONSE,Disposition.VALIDATION_FAILURE}:
                        failure=AttemptValidationFailure.MALFORMED if acquired.disposition is Disposition.MALFORMED_RESPONSE else (AttemptValidationFailure.INCOMPLETE if acquired.disposition is Disposition.INCOMPLETE_RESPONSE else AttemptValidationFailure.MAPPING)
                        attempt_result=CapturedInvalid(f"raw:{raw_digest}",raw_digest,(failure,));contracts=()
                    else:
                        category=AttemptFailureCategory.TIMEOUT if acquired.disposition is Disposition.TIMEOUT else (AttemptFailureCategory.NETWORK if acquired.disposition is Disposition.CONNECTION_FAILURE else AttemptFailureCategory.PROVIDER)
                        attempt_result=AcquisitionFailed(category,f"invocation:{opportunity.research_capture_opportunity_id}:{slot}");contracts=()
                    attempt=ProspectiveCaptureAttempt.create(protocol_id=protocol.standalone_probability_source_protocol_id,opportunity_id=opportunity.research_capture_opportunity_id,
                        schedule_observation_id=schedule.observation_id,canonical_event_id=schedule.canonical_event_id,proposition_id=proposition,home_participant_id=schedule.home_participant_id,
                        provider_market_id=series.provider_market_id,target_at=target,slot=slot,invocation_at=started,provider_call_occurred=True,result=attempt_result,
                        effective_at=completed,diagnostics=("trusted-clock authority-derived capture",acquired.detail),provenance=result.provenance)
                    normalized=pr17_contract_bundle(*(contracts+(attempt,)));request_id=request_identity({"opportunity_id":opportunity.research_capture_opportunity_id,"slot":slot,"market_id":series.provider_market_id})
                    values=_entry_values(archive=archive,command="capture-prospective",request_id=request_id,invoked_at=completed,endpoint=archive.config.provider_base_url,
                        disposition=acquired.disposition,protocol_id=protocol.standalone_probability_source_protocol_id,design=DesignAuthority.PROSPECTIVE,
                        diagnostics=(f"opportunity:{opportunity.research_capture_opportunity_id}",f"slot:{slot}","authority-derived trusted-clock capture"),provider_effective_at=completed)
                    if acquired.raw_body is None:archive._commit_normalized_locked(normalized=normalized,entry_values=values)
                    else:archive._commit_locked(raw_body=acquired.raw_body,normalized=normalized,entry_values=values)
                else:attempt=persist_no_call(slot,decision_time)
                if slot==current and success is None and series is not None:
                    existing.append(attempt);owned.append(attempt);by_slot[slot]=attempt;created.append(attempt.prospective_capture_attempt_id)
                if isinstance(attempt.result,CapturedValid):success=attempt

            # A slow call never changes its slot and never triggers another call. It may only close
            # newly elapsed slots with canonical no-call dispositions.
            completion_terminal=completion_time>target+timedelta(minutes=5)
            completion_elapsed=4 if completion_terminal else (max(-1,min(4,int((completion_time-target).total_seconds()//60))) if completion_time>=target else -1)
            for slot in range(completion_elapsed+1):
                if slot not in by_slot:persist_no_call(slot,completion_time)
            if len(by_slot)==5 and (completion_terminal or at_terminal or success is not None):
                snapshot=reconcile_prospective_snapshot(protocol=protocol,opportunity=opportunity,activation=activation,eligibility_context=context,eligibility_result=result,
                    schedule_history=history,analysis_boundary=completion_time,attempts=tuple(by_slot.values()),window_closed_at=max(completion_time,target+timedelta(minutes=5)),provenance=result.provenance,limitations=("fixture-only inactive acquisition",))
                values=_entry_values(archive=archive,command="capture-prospective",request_id=request_identity({"snapshot_id":snapshot.prospective_standalone_snapshot_id}),invoked_at=completion_time,
                    endpoint="local://snapshot-replay",disposition=Disposition.SKIPPED_AFTER_SUCCESS if success else Disposition.MISSED,protocol_id=protocol.standalone_probability_source_protocol_id,
                    design=DesignAuthority.PROSPECTIVE,diagnostics=(f"opportunity:{opportunity.research_capture_opportunity_id}","terminal-snapshot"))
                archive._commit_normalized_locked(normalized=pr17_contract_bundle(snapshot),entry_values=values);snapshots.append(snapshot.prospective_standalone_snapshot_id)
    return ProspectiveDiscoveryResult(archive.config.identity,archive.config.namespace,now,tuple(sorted(due)),calls,tuple(sorted(created)),tuple(sorted(snapshots)),"completed" if (created or snapshots) else "no-due-work")


def discover_and_acquire_retrospective(*,archive:NamespaceArchive,
        transport_factory:Callable[[Any,Any],Transport],clock:Callable[[],datetime],sleeper:Callable[[float],None],
        request_builder:Callable[[Any,Any,datetime],tuple[str,Mapping[str,str]]]|None=None,
        response_adapter:Callable[[Mapping[str,Any],bytes,Any,Any,datetime],Mapping[str,Any]]|None=None,
        maximum_opportunities:int|None=None)->tuple[str,...]:
    """Acquire historical pages and construct the exact PR17B1 manifest/candle chain."""
    from decimal import Decimal
    from forecast_comparative_research import PopulationEligibilityDisposition,PopulationEligibilityValidationStatus
    from forecast_standalone_research import (HistoricalCandleQueryManifest,HistoricalCandleRetrievalPage,HistoricalMarketCandleObservation,
        ManifestValidationStatus,StandaloneDesignTag,resolve_standalone_schedule_authority)
    now=clock();_utc(now,"trusted retrospective clock");created=[]
    with archive.mutation_lock():
        state=replay_pr17_archive(archive,analysis_boundary=now)
        configured=set(archive.config.research_protocol_ids);protocols=tuple(x for x in state.bucket("protocols") if x.design_tag is StandaloneDesignTag.RETROSPECTIVE and x.standalone_probability_source_protocol_id in configured)
        if len(protocols)!=1:raise OperationsError("retrospective-authority-invalid","configuration must resolve exactly one archived retrospective Protocol")
        protocol=protocols[0];activation=next((x for x in state.bucket("activation_boundaries") if x.standalone_research_activation_boundary_id==protocol.activation_boundary_id),None)
        if activation is None:raise OperationsError("retrospective-authority-invalid","activation boundary does not resolve")
        histories={x.canonical_event_id:x for x in state.bucket("outcome_histories")};contexts={x.research_capture_opportunity_id:x for x in state.bucket("eligibility_contexts")};results={x.research_capture_opportunity_id:x for x in state.bucket("eligibility_results")};existing={x.opportunity_id for x in state.bucket("manifests")}
        series_values=state.bucket("market_series")
        pending=sorted((x for x in state.bucket("opportunities") if x.protocol_id==protocol.standalone_probability_source_protocol_id),key=lambda x:x.research_capture_opportunity_id)
        if maximum_opportunities is not None:
            if maximum_opportunities<1 or maximum_opportunities>100:raise OperationsError("retrospective-bound-invalid","maximum opportunities must be between 1 and 100")
        provider_calls=0
        retrospective_limitations=("later-acquired retrospective archive Evidence","historical provider availability, survivorship, and revision limitations","post-event schedule-history limitations","one-minute provider aggregation","bid and ask closes are same-candle aggregates, not documented simultaneous quotes","no quote quantity, positive depth, or executable spread is established","acquisition time differs from historical effective time","no synthetic continuity, fallback, or prospective repair")
        for opportunity in pending:
            if opportunity.research_capture_opportunity_id in existing:continue
            context=contexts.get(opportunity.research_capture_opportunity_id);result=results.get(opportunity.research_capture_opportunity_id);history=histories.get(context.canonical_event_id) if context else None
            if context is None or result is None or history is None or result.analysis_boundary>now:raise OperationsError("retrospective-authority-invalid","complete boundary-visible eligibility authority is required")
            if result.disposition is not PopulationEligibilityDisposition.ELIGIBLE or result.validation_status is not PopulationEligibilityValidationStatus.VALID:continue
            schedule,target=resolve_standalone_schedule_authority(protocol=protocol,activation=activation,opportunity=opportunity,eligibility_context=context,eligibility_result=result,outcome_history=history,analysis_boundary=now)
            proposition=f"winner:{schedule.canonical_event_id}:{schedule.home_participant_id}";series=tuple(x for x in series_values if x.provider==PROVIDER_ID and x.proposition_id==proposition)
            if not series:continue
            if len(series)!=1:raise OperationsError("retrospective-authority-invalid","provider Market Series is ambiguous")
            if maximum_opportunities is not None and provider_calls>=maximum_opportunities:break
            endpoint,request=(request_builder(opportunity,series[0],target) if request_builder is not None else (archive.config.provider_base_url,{"market_id":series[0].provider_market_id}))
            def validate(value):return response_adapter(value,b"",opportunity,series[0],target) if response_adapter is not None else value
            acquired=acquire_with_retries(transport=transport_factory(opportunity,series[0]),endpoint=endpoint,request=request,policy=archive.config.retry_policy,now=clock,sleeper=sleeper,validator=validate)
            provider_calls+=len(acquired.attempts)
            completed=acquired.attempts[-1].completed_at
            if acquired.disposition is not Disposition.SUCCESS or acquired.raw_body is None or acquired.normalized is None:
                diagnostics=(f"opportunity:{opportunity.research_capture_opportunity_id}",f"market:{series[0].provider_market_id}",f"attempts:{len(acquired.attempts)}",*(f"attempt-{index+1}:{attempt.disposition.value}" for index,attempt in enumerate(acquired.attempts)))
                values=_entry_values(archive=archive,command="acquire-retrospective",request_id=request_identity({"opportunity_id":opportunity.research_capture_opportunity_id,"market_id":series[0].provider_market_id,"target_at":_utc(target,"target")}),invoked_at=completed,
                    endpoint=endpoint,disposition=acquired.disposition,protocol_id=protocol.standalone_probability_source_protocol_id,design=DesignAuthority.RETROSPECTIVE,diagnostics=diagnostics,provider_effective_at=None)
                archive._record_failure_locked(entry_values=values,raw_body=acquired.raw_body)
                raise RetrospectiveAcquisitionError("bounded retrospective provider acquisition failed",provider_calls)
            raw_digest=sha256_bytes(acquired.raw_body);raw_reference=f"raw:{raw_digest}"
            supplied_pages=tuple({**page,"candle_ids":[str(item.get("candle_end_at")) for item in page.get("candles",())]} for page in acquired.normalized.get("pages",()))
            page_values=validate_pagination(supplied_pages)
            candles=[];pages=[]
            for page_value in page_values:
                page_candles=[]
                for candle_value in page_value.get("candles",()):
                    candle=HistoricalMarketCandleObservation.create(protocol_id=protocol.standalone_probability_source_protocol_id,manifest_id="pending",provider_id=PROVIDER_ID,
                        provider_market_id=series[0].provider_market_id,canonical_event_id=schedule.canonical_event_id,proposition_id=proposition,home_participant_id=schedule.home_participant_id,
                        contract_side="yes",interval="1m",candle_end_at=datetime.fromisoformat(candle_value["candle_end_at"].replace("Z","+00:00")),acquired_at=completed,
                        close_yes_bid=Decimal(str(candle_value["close_yes_bid"])) if candle_value.get("close_yes_bid") is not None else None,
                        close_yes_ask=Decimal(str(candle_value["close_yes_ask"])) if candle_value.get("close_yes_ask") is not None else None,
                        is_real=True,is_synthetic=False,is_repaired=False,retrieval_page_position=page_value["position"],raw_archive_reference=raw_reference,raw_archive_sha256=raw_digest,
                        limitations=retrospective_limitations,provenance=result.provenance)
                    page_candles.append(candle);candles.append(candle)
                pages.append(HistoricalCandleRetrievalPage(page_value["cursor"],page_value["position"],page_value.get("next_cursor"),page_value["terminal"],raw_reference,raw_digest,completed,
                    tuple(x.historical_market_candle_observation_id for x in page_candles),ManifestValidationStatus.COMPLETE,retrospective_limitations))
            manifest=HistoricalCandleQueryManifest.create(protocol_id=protocol.standalone_probability_source_protocol_id,opportunity_id=opportunity.research_capture_opportunity_id,
                canonical_event_id=schedule.canonical_event_id,proposition_id=proposition,provider_id=PROVIDER_ID,endpoint=endpoint,provider_market_id=series[0].provider_market_id,
                interval="1m",requested_start_at=target-timedelta(minutes=5),requested_end_at=target,retrieval_started_at=acquired.attempts[0].started_at,retrieval_completed_at=completed,pages=tuple(pages),
                returned_candle_evidence_ids=tuple(x.historical_market_candle_observation_id for x in candles),validation_status=ManifestValidationStatus.COMPLETE,limitations=retrospective_limitations,
                effective_at=completed,supersedes_manifest_id=None,correction_reason=None,provenance=result.provenance)
            candles=tuple(HistoricalMarketCandleObservation.create(**{name:getattr(item,name) for name in item.__dataclass_fields__ if name not in ("historical_market_candle_observation_id","schema_version","identity_algorithm_version","input_digest","manifest_id")},manifest_id=manifest.historical_candle_query_manifest_id) for item in candles)
            normalized=pr17_contract_bundle(manifest,*candles);values=_entry_values(archive=archive,command="acquire-retrospective",request_id=request_identity({"opportunity_id":opportunity.research_capture_opportunity_id,"target_at":_utc(target,"target")}),invoked_at=completed,
                endpoint=endpoint,disposition=Disposition.SUCCESS,protocol_id=protocol.standalone_probability_source_protocol_id,design=DesignAuthority.RETROSPECTIVE,
                diagnostics=(f"opportunity:{opportunity.research_capture_opportunity_id}","authority-derived historical acquisition"),provider_effective_at=completed)
            archive._commit_locked(raw_body=acquired.raw_body,normalized=normalized,entry_values=values);created.append(manifest.historical_candle_query_manifest_id)
    return tuple(sorted(created))


def acquire_typed_supporting_fixture(*,archive:NamespaceArchive,command:str,transport:Transport,
        clock:Callable[[],datetime],sleeper:Callable[[float],None])->tuple[Any,...]:
    """Version-dispatch fixture schedule, classification, or Outcome authority."""
    allowed={"acquire-schedule":{"OutcomeHistory"},"acquire-classification":{"StandaloneEventClassificationEvidence"},"reconcile-outcomes":{"OutcomeHistory"}}
    if command not in allowed:raise OperationsError("command-boundary",command)
    with archive.mutation_lock():
        acquired=acquire_with_retries(transport=transport,endpoint=archive.config.provider_base_url,request={"command":command},policy=archive.config.retry_policy,now=clock,sleeper=sleeper,validator=lambda value:value)
        completed=acquired.attempts[-1].completed_at
        if acquired.disposition is not Disposition.SUCCESS or acquired.raw_body is None or acquired.normalized is None:raise OperationsError("supporting-acquisition-failed",acquired.detail)
        payloads=acquired.normalized.get("contract_jsons")
        if not isinstance(payloads,list) or not payloads:raise OperationsError("incomplete-response","typed supporting contracts absent")
        from forecast_standalone_research import deserialize_v3
        contracts=tuple(deserialize_v3(payload) for payload in payloads)
        if any(type(item).__name__ not in allowed[command] for item in contracts):raise OperationsError("validation-failure","supporting contract type conflicts with command")
        normalized=pr17_contract_bundle(*contracts);values=_entry_values(archive=archive,command=command,request_id=request_identity({"command":command,"contracts":tuple(sorted(payloads))}),invoked_at=completed,
            endpoint=archive.config.provider_base_url,disposition=Disposition.SUCCESS,protocol_id=None,design=DesignAuthority.SUPPORTING,
            diagnostics=("typed version-dispatched supporting acquisition",),provider_effective_at=completed)
        archive._commit_locked(raw_body=acquired.raw_body,normalized=normalized,entry_values=values)
        return contracts


def capture_prospective(*, archive: NamespaceArchive, transport: Transport, endpoint: str,
                        request: Mapping[str, str], invoked_at: datetime, target_at: datetime,
                        opportunity_id: str, protocol_id: str, now: Callable[[], datetime],
                        validator: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> tuple[AcquisitionResult | None, ManifestEntry]:
    """Removed unsafe caller-authorized surface; use discovery from archived authority."""
    raise OperationsError("direct-capture-prohibited","prospective capture requires archived-authority discovery and a trusted clock")
