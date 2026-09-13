"""Offline, read-only frozen source authority for successor MLB reporting.

A trusted boundary ID must be retained independently of a candidate being verified.
Hashes authenticate a retained freeze; they cannot prove a caller-invented history.
No persistence, transport, collector or publication entry point lives here.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Context, ROUND_HALF_EVEN, localcontext
from typing import Callable

from forecast_standalone_operations import (
    NamespaceArchive, OperationsError, ScientificArchiveState, _contracts_from_entry,
    _is_supporting_session_authority_rejection, canonical_bytes, reconcile_archive,
    replay_pr17_archive, sha256_bytes,
)
from forecast_standalone_publication import _source_authority

VERSION = "mlb-reporting-source-1"
ANALYTICAL_BUCKETS = frozenset({"historical_derivations", "market_derivations",
                              "measurements", "coverages", "performances", "reports"})


def _fail(detail: str) -> None:
    raise OperationsError("reporting-source-conflict", detail)


def _time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("reporting clock must be timezone-aware")
    return value


def _hash(value) -> str:
    return sha256_bytes(canonical_bytes(value))


def _inventory(archive: NamespaceArchive) -> tuple[str, ...]:
    # Every manifest is retained, including failed, non-authoritative and analytical
    # entries. It is the frozen namespace inventory, not a successful-source subset.
    return tuple(sorted(canonical_bytes(entry).decode() for entry in archive.entries()))


def _global_integrity(archive: NamespaceArchive) -> None:
    # Always use the actual namespace, never the reporting view or a checkpoint.
    if type(archive) is not NamespaceArchive:
        _fail("reporting requires the original namespace archive, not a filtered view")
    integrity = reconcile_archive(archive)
    if integrity.blocking:
        raise OperationsError("archive-integrity-failure", canonical_bytes(integrity).decode())


@dataclass(frozen=True, slots=True)
class FrozenReportingSource:
    version: str
    namespace: str
    mode: str
    evidence_cutoff_at: datetime
    frozen_at: datetime
    manifest_inventory: tuple[str, ...]
    source_manifest_ids: tuple[str, ...]
    dependency_manifest_ids: tuple[str, ...]
    manifest_roles: tuple[tuple[str, str], ...]
    session_dispositions: tuple[tuple[str, str], ...]
    graph_digest: str
    boundary_id: str

    def __post_init__(self):
        if self.version != VERSION:
            _fail("unknown reporting source version")
        _time(self.evidence_cutoff_at); _time(self.frozen_at)
        if self.frozen_at < self.evidence_cutoff_at:
            _fail("freeze completion predates source cutoff")
        for values in (self.manifest_inventory, self.source_manifest_ids,
                       self.dependency_manifest_ids, self.manifest_roles,
                       self.session_dispositions):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                _fail("source material must be immutable, unique and canonical")
        if self.boundary_id != "reporting-source:" + _hash(self.material()):
            _fail("source boundary identity conflict")

    def material(self):
        return {key: value for key, value in asdict(self).items() if key != "boundary_id"}

    def to_json(self) -> str:
        return canonical_bytes(asdict(self)).decode()

    @classmethod
    def from_json(cls, payload: str) -> FrozenReportingSource:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    _fail("duplicate source JSON key")
                result[key] = value
            return result
        try:
            raw = json.loads(payload, object_pairs_hook=pairs)
            if set(raw) != set(cls.__dataclass_fields__):
                _fail("unknown or missing source fields")
            for key in ("evidence_cutoff_at", "frozen_at"):
                if set(raw[key]) != {"datetime_utc"}:
                    _fail("invalid source chronology encoding")
                raw[key] = datetime.fromisoformat(raw[key]["datetime_utc"])
            for key in ("manifest_inventory", "source_manifest_ids", "dependency_manifest_ids"):
                raw[key] = tuple(raw[key])
            for key in ("manifest_roles", "session_dispositions"):
                raw[key] = tuple(tuple(item) for item in raw[key])
            return cls(**raw)
        except (ValueError, TypeError, KeyError) as exc:
            raise OperationsError("reporting-source-conflict", "malformed source boundary") from exc


@dataclass(frozen=True, slots=True)
class SourceVerificationReceipt:
    version: str
    boundary_id: str
    graph_digest: str
    verified_at: datetime


class _ReportingArchiveView:
    """Frozen inventory and read primitives only; no live selection or mutation."""
    def __init__(self, archive, inventory):
        self.config = archive.config
        self._archive = archive
        self._entries = tuple(sorted((json.loads(item) for item in inventory),
            key=lambda item: (item["acquired_at"]["datetime_utc"], item["manifest_entry_id"])))

    def entries(self):
        # Readers cannot mutate the inventory used by a later validator.
        return tuple(json.loads(canonical_bytes(item)) for item in self._entries)

    def prospective_entries(self):
        # Namespace-wide integrity already passed against the real archive. These
        # are all frozen entries, not a caller-selected successful subset.
        return self.entries()

    def read_verified(self, family, identity):
        return self._archive.read_verified(family, identity)

    def read_json_verified(self, family, identity):
        return json.loads(self.read_verified(family, identity))

    def replay_contracts(self, entry, prior_objects):
        return _contracts_from_entry(self, entry, prior_objects,
                                     _exclude_retrospective_publications=True)


def _source_chronology(state: ScientificArchiveState, cutoff: datetime) -> None:
    for name, values in state.graph:
        if name in ANALYTICAL_BUCKETS:
            continue
        for value in values:
            items = value.observations if name == "outcome_histories" else (value,)
            for item in items:
                for key in ("collected_at", "acquired_at", "effective_at", "analysis_boundary",
                            "retrieval_completed_at", "invocation_at"):
                    at = getattr(item, key, None)
                    if isinstance(at, datetime) and at > cutoff:
                        _fail(f"post-cutoff source fact: {name}.{key}")
                provenance = getattr(item, "provenance", None)
                for key in ("collected_at", "generated_at"):
                    at = getattr(provenance, key, None)
                    if isinstance(at, datetime) and at > cutoff:
                        _fail(f"post-cutoff source provenance: {name}.{key}")


def _reconstruct(archive, inventory, cutoff):
    view = _ReportingArchiveView(archive, inventory)
    entries = view.entries()
    if any(datetime.fromisoformat(x["acquired_at"]["datetime_utc"]) > cutoff for x in entries):
        _fail("post-cutoff manifest in frozen inventory")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        state = replay_pr17_archive(view, analysis_boundary=cutoff,
                                   _exclude_retrospective_publications=True)
        _source_chronology(state, cutoff)
        authority = _source_authority(view, state)
    roots = tuple(authority["source_manifest_ids"])
    dependencies = tuple(authority["dependency_manifest_ids"])
    roles = tuple(sorted((entry["manifest_entry_id"],
        "source-root" if entry["manifest_entry_id"] in roots else
        "source-dependency" if entry["manifest_entry_id"] in dependencies else
        "non-contributing") for entry in entries))
    from forecast_standalone_activation import verify_supporting_session_completion
    sessions = set()
    for entry in entries:
        if not entry.get("normalized_object_id"):
            continue
        value = view.read_json_verified("normalized", entry["normalized_object_id"])
        if value.get("record_kind", "").startswith("pr17c2-supporting-session-"):
            session = value.get("session_id")
            if isinstance(session, str):
                sessions.add(session)
    dispositions = []
    for session in sorted(sessions):
        try:
            verify_supporting_session_completion(view, session)
        except OperationsError as exc:
            if not _is_supporting_session_authority_rejection(exc):
                raise
            dispositions.append((session, "excluded:" + exc.code))
        else:
            dispositions.append((session, "verified-complete"))
    graph_digest = _hash(tuple(sorted(item.to_json() for item in state.objects)))
    return state, dict(source_manifest_ids=roots, dependency_manifest_ids=dependencies,
                      manifest_roles=roles, session_dispositions=tuple(dispositions),
                      graph_digest=graph_digest)


def freeze_reporting_source(*, archive: NamespaceArchive,
                            clock: Callable[[], datetime]) -> FrozenReportingSource:
    """Fresh freeze only. There is deliberately no caller-supplied historical K.

    Retain boundary_id through a trusted local handoff alongside the immutable
    boundary. Historical validation requires that independently retained ID.
    """
    _global_integrity(archive)
    inventory = _inventory(archive)
    cutoff = _time(clock())
    _, selection = _reconstruct(archive, inventory, cutoff)
    _global_integrity(archive)
    if _inventory(archive) != inventory:
        _fail("namespace changed during freeze; make a later independent attempt")
    completed = _time(clock())
    material = dict(version=VERSION, namespace=archive.config.namespace,
        mode=archive.config.mode.value, evidence_cutoff_at=cutoff, frozen_at=completed,
        manifest_inventory=inventory, **selection)
    return FrozenReportingSource(**material, boundary_id="reporting-source:" + _hash(material))


def verify_reporting_source(*, archive: NamespaceArchive, boundary: FrozenReportingSource,
                            expected_boundary_id: str, clock: Callable[[], datetime]
                            ) -> tuple[ScientificArchiveState, SourceVerificationReceipt]:
    """Reconstruct saved authority, using a separately retained trusted boundary ID.

    Never set expected_boundary_id from an untrusted candidate's own ID: that would
    check only self-consistency, not authentication of the original complete freeze.
    """
    if type(boundary) is not FrozenReportingSource:
        _fail("unknown reporting source type")
    boundary.__post_init__()
    if boundary.boundary_id != expected_boundary_id:
        _fail("candidate does not match retained source boundary")
    if (boundary.namespace, boundary.mode) != (archive.config.namespace, archive.config.mode.value):
        _fail("foreign reporting namespace or mode")
    _global_integrity(archive)
    current = set(_inventory(archive))
    if not set(boundary.manifest_inventory) <= current:
        _fail("retained manifest is missing or altered")
    state, selection = _reconstruct(archive, boundary.manifest_inventory, boundary.evidence_cutoff_at)
    if any(getattr(boundary, key) != value for key, value in selection.items()):
        _fail("complete source selection, dependencies or graph fails reconstruction")
    verified = _time(clock())
    if verified < boundary.frozen_at:
        _fail("verification receipt predates original freeze")
    return state, SourceVerificationReceipt(VERSION, boundary.boundary_id,
                                            boundary.graph_digest, verified)
