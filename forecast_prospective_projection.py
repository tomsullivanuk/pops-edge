"""Disposable, non-authoritative replay checkpoint over immutable archive sources."""
from __future__ import annotations

import json
import fcntl
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from forecast_standalone_operations import (
    NamespaceArchive, OperationsError, canonical_bytes, reconcile_archive,
    replay_pr17_archive, sha256_bytes, ManifestEntry,
)

# Only these closed command families are independent of supporting / prospective
# authority. Supporting sessions (including retrospective ones) are deliberately
# retained: they can provide cross-activation predecessors.
INDEPENDENT_COMMANDS = frozenset({
    "acquire-retrospective", "acquire-retrospective-cutoff",
    "publish-retrospective-analysis", "reconcile-outcomes-failure",
})
MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_SOURCE_OBJECTS = 8192
MAX_PROJECTION_BYTES = 64 * 1024 * 1024
MAX_DELTA_MANIFESTS = 256
SCHEMA_VERSION = "3"
BUILDER_VERSION = "canonical-supporting-checkpoint-1"


def relevant_entries(entries):
    def independent(entry):
        command = entry["command"]
        if command == "acquire-retrospective-cutoff":
            return (entry["design_authority"] == "supporting" and
                    entry.get("provider_id") == "kalshi" and entry.get("protocol_id") is None)
        if command == "reconcile-outcomes-failure":
            return entry.get("normalized_object_id") is None
        return (command in INDEPENDENT_COMMANDS and
                entry["design_authority"] == "retrospective")
    return tuple(entry for entry in entries if not independent(entry))


class ProspectiveSourceBoundary(NamespaceArchive):
    """Read-only immutable source view; verified bytes live for one invocation."""

    def __init__(self, archive, entries):
        super().__init__(archive.config)
        self._entries = tuple(entries)
        self._bytes: dict[tuple[str, str], bytes] = {}
        self._json: dict[tuple[str, str], Any] = {}
        self._integrity = None
        self._supporting_verification = None
        self._signatures = {}
        self._started = time.monotonic()
        self.source_bytes = 0
        self.budget_seconds = 20
        self._contributions = {}
        self._reusable = set()
        self._verified_identities = set()
        # Full source replay starts a fresh lineage; incremental replay inherits
        # its checkpoint's lineage, including across atomic republication.
        self._checkpoint_lineage = uuid.uuid4().hex

    def _ensure_mutable(self):
        raise OperationsError("projection-read-only", "source boundary cannot publish")

    def entries(self):
        return self._entries

    def read_verified(self, family, identity):
        key = (family, identity.split(":")[-1])
        if time.monotonic() - self._started > self.budget_seconds:
            raise OperationsError("projection-budget-exceeded", "source verification exceeded preparation budget")
        if key not in self._bytes:
            path = self._path(family, identity)
            if (self.budget_seconds == 20 and (len(self._bytes) >= MAX_SOURCE_OBJECTS or
                    self.source_bytes + path.stat().st_size > MAX_SOURCE_BYTES)):
                raise OperationsError("projection-budget-exceeded", "explicit rebuild/design inspection required")
            before = _signature(path)
            body = super().read_verified(family, identity)
            if before != _signature(path):
                raise OperationsError("projection-invalid", "source changed during verification")
            self._signatures[key] = before
            self.source_bytes += len(body)
            self._bytes[key] = body
        return self._bytes[key]

    def read_json_verified(self, family, identity):
        if time.monotonic() - self._started > self.budget_seconds:
            raise OperationsError("projection-budget-exceeded", "source verification exceeded preparation budget")
        key = (family, identity.split(":")[-1])
        if key not in self._json:
            self._json[key] = json.loads(self.read_verified(family, identity))
        return self._json[key]

    def memoized_supporting_verification(self, key, verify):
        """Reuse successful canonical checks only during one immutable replay."""
        if self._supporting_verification is None:
            return verify()
        if time.monotonic() - self._started > self.budget_seconds:
            raise OperationsError("projection-budget-exceeded", "source verification exceeded preparation budget")
        if key not in self._supporting_verification:
            self._supporting_verification[key] = verify()
        return self._supporting_verification[key]

    def verify_source_identity(self, family, identity):
        key = (family, identity.split(":")[-1])
        if key in self._verified_identities:
            if _signature(self._path(*key)) != self._signatures[key]:
                raise OperationsError("projection-invalid", "checkpoint source changed")
            return True
        self.read_verified(family, identity)
        self._verified_identities.add(key)
        return True

    def replay_contracts(self, entry, prior):
        from forecast_standalone_operations import _contracts_from_entry
        from forecast_standalone_research import deserialize_v3
        identity = entry["manifest_entry_id"]
        if identity in self._reusable:
            return tuple(deserialize_v3(x) for x in self._contributions[identity])
        contracts = _contracts_from_entry(self, entry, prior)
        self._contributions[identity] = [x.to_json() for x in contracts]
        return contracts

    def prospective_entries(self):
        if self._integrity is None:
            self._integrity = reconcile_archive(self, _entries=self._entries)
        if self._integrity.blocking:
            raise OperationsError("projection-invalid", "required source acquisition is incomplete or corrupt")
        return self._entries


def capture_boundary(archive):
    with archive.mutation_lock():
        entries = relevant_entries(archive.entries())
    return ProspectiveSourceBoundary(archive, entries)


def replay_boundary(boundary, at):
    boundary._supporting_verification = {}
    try:
        if any(datetime.fromisoformat(entry["acquired_at"]["datetime_utc"]) > at for entry in boundary.entries()):
            raise OperationsError("projection-invalid", "required publication is future-effective")
        return replay_pr17_archive(boundary, analysis_boundary=at)
    except OperationsError:
        raise
    except (OSError, ValueError) as exc:
        raise OperationsError("projection-invalid", "required source cannot be verified") from exc
    finally:
        boundary._supporting_verification = None


def projection_path(archive):
    return archive.root / "prospective-projection.json"


def _material(archive, entries):
    return {"schema_version": SCHEMA_VERSION, "builder_version": BUILDER_VERSION,
            "namespace": archive.config.namespace, "mode": archive.config.mode.value,
            "source_manifest_ids": sorted(x["manifest_entry_id"] for x in entries)}


def _scientific_state_bytes(state):
    """Canonical replay equality without expanding Operations serialization."""
    def contracts(values):
        result=[]
        for value in values:
            serializer=getattr(value,"to_json",None)
            if not callable(serializer):
                raise OperationsError("projection-invalid", "scientific replay contains a non-contract value")
            payload=serializer()
            if not isinstance(payload,str):
                raise OperationsError("projection-invalid", "scientific contract serialization is not text")
            result.append((type(value).__name__,payload))
        return tuple(result)
    return canonical_bytes({
        "analysis_boundary": state.analysis_boundary,
        "objects": contracts(state.objects),
        "graph": tuple((name, contracts(values)) for name, values in state.graph),
        "reports": contracts(state.reports),
        "source_manifest_ids": state.source_manifest_ids,
    })


def _read(archive):
    try:
        with projection_path(archive).open("rb") as handle:
            body = handle.read(MAX_PROJECTION_BYTES + 1)
        if len(body) > MAX_PROJECTION_BYTES:
            raise ValueError("oversized projection")
        envelope = json.loads(body)
    except FileNotFoundError:
        raise OperationsError("projection-absent", "run rebuild-prospective-projection") from None
    except (ValueError, OSError):
        raise OperationsError("projection-invalid", "projection cannot be decoded") from None
    try:
        value = envelope["projection"]
        if (set(envelope) != {"projection", "sha256"} or
                sha256_bytes(canonical_bytes(value)) != envelope["sha256"] or
                set(value) != set(_material(archive, ())) | {"authority", "built_at", "normalized", "signatures", "contributions", "lineage"} or
                not isinstance(value["lineage"], str) or
                len(value["lineage"]) != 32 or
                any(c not in "0123456789abcdef" for c in value["lineage"]) or
                value["authority"] != "non-authoritative-operations-checkpoint" or
                value["schema_version"] != SCHEMA_VERSION or
                value["builder_version"] != BUILDER_VERSION or
                value["namespace"] != archive.config.namespace or
                value["mode"] != archive.config.mode.value or
                not isinstance(value["source_manifest_ids"], list) or
                value["source_manifest_ids"] != sorted(set(value["source_manifest_ids"]))):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise OperationsError("projection-invalid", "projection content or version is invalid") from None
    try:
        ids = set(value["source_manifest_ids"])
        if set(value["contributions"]) != ids or not isinstance(value["normalized"], dict):
            raise ValueError
        for key, signature in value["signatures"].items():
            family, digest = key.split(":")
            if family not in {"raw", "normalized"} or len(digest) != 64 or len(signature) != 5:
                raise ValueError
        for digest in value["normalized"]:
            if "normalized:" + digest not in value["signatures"]:
                raise ValueError
    except (KeyError, TypeError, ValueError):
        raise OperationsError("projection-invalid", "checkpoint state is malformed") from None
    return value


def assert_boundary(archive, boundary):
    """Caller owns the mutation lock. No scientific/object replay occurs here."""
    _assert_lineage(archive, boundary._checkpoint_lineage)
    if time.monotonic() - boundary._started > boundary.budget_seconds:
        raise OperationsError("projection-budget-exceeded", "preparation exceeded its budget")
    entries = relevant_entries(archive.entries())
    if _material(archive, entries) != _material(archive, boundary.entries()):
        raise OperationsError("projection-stale", "relevant publication changed during preparation")
    if check_capture_persistence(archive, entries):
        raise OperationsError("prospective-publication-ambiguous", "unresolved capture marker")
    # Immutable signatures bind cached verification to this exact local source.
    for key, signature in boundary._signatures.items():
        if _signature(boundary._path(*key)) != signature:
            raise OperationsError("projection-invalid", "required source changed during preparation")


def note_capture(archive, boundary, entry):
    """Extend only the owning collector's boundary with its published result.

    Provider latency is not part of the source-reconstruction budget and must
    never prevent preservation of an actual call's immutable disposition.
    """
    boundary._entries += (json.loads(canonical_bytes(entry)),)
    identities = [("normalized", entry.normalized_object_id)]
    if entry.raw_object_sha256:
        identities.append(("raw", entry.raw_object_sha256))
    for family, identity in identities:
        path = archive._path(family, identity)
        before = _signature(path)
        archive.read_verified(family, identity)
        if before != _signature(path):
            raise OperationsError("projection-invalid", "published capture source changed")
        boundary._signatures[(family, identity.split(":")[-1])] = before


def _signature(path):
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _rejected_path(archive, lineage):
    return archive.root / f"prospective-projection-rejected-{lineage}.json"


def _assert_lineage(archive, lineage):
    # Presence is a durable negative fence, even if diagnostic bytes are damaged.
    # No directory scan or historical source replay is needed on the hot path.
    if _rejected_path(archive, lineage).exists():
        raise OperationsError("projection-rejected", "checkpoint lineage was rejected by full replay; explicit rebuild required")


def _publish(archive, boundary, at):
    value = {**_material(archive, boundary.entries()),
             "lineage": boundary._checkpoint_lineage,
             "authority": "non-authoritative-operations-checkpoint", "built_at": at.isoformat(),
             "normalized": {key[1]: body for key, body in boundary._json.items() if key[0] == "normalized"},
             "signatures": {":".join(key): signature for key, signature in boundary._signatures.items()},
             "contributions": boundary._contributions}
    body = canonical_bytes({"projection": value, "sha256": sha256_bytes(canonical_bytes(value))})
    if len(body) > MAX_PROJECTION_BYTES:
        raise OperationsError("projection-budget-exceeded", "checkpoint exceeds format bound")
    temporary = archive.root / f".prospective-{uuid.uuid4().hex}.partial"
    try:
        with temporary.open("xb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        with archive.mutation_lock():
            assert_boundary(archive, boundary)
            os.replace(temporary, projection_path(archive))
            _sync_directory(archive.root)
    finally:
        temporary.unlink(missing_ok=True)


def rebuild_projection_with_retry(archive, *, clock):
    """At most three full preparations; only concurrent publication is retryable."""
    previous = None
    for attempt in range(1, 4):
        at = clock()
        if at.tzinfo is None or at.utcoffset() is None or (previous is not None and at < previous):
            raise OperationsError("trusted-clock-invalid", "rebuild retry requires an aware, nondecreasing clock")
        previous = at
        try:
            rebuild_projection(archive, at)
            return attempt
        except OperationsError as exc:
            if exc.code != "projection-stale" or attempt == 3:
                raise


def rebuild_projection(archive, at):
    integrity = reconcile_archive(archive)
    if not integrity.healthy:
        raise OperationsError("capture-persistence-unsafe", "offline rebuild requires a healthy archive")
    boundary = capture_boundary(archive)
    if check_capture_persistence(archive, boundary.entries()):
        raise OperationsError("prospective-publication-ambiguous", "rebuild cannot clear interrupted capture")
    boundary.budget_seconds = float("inf")
    state = replay_boundary(boundary, at)
    # Daily full replay independently checks any usable same-boundary checkpoint.
    # Invalid/old-format cache is disposable; immutable sources were verified above.
    try:
        cached, recorded, current = _prepare_checkpoint(archive, at)
    except OperationsError:
        cached = None
    if cached is not None and current != _material(archive, boundary.entries()):
        # A newer checkpoint is not evidence that the older full replay is wrong.
        raise OperationsError("projection-stale", "source boundary changed before replay comparison")
    if cached is not None and recorded["source_manifest_ids"] == current["source_manifest_ids"]:
        cached.budget_seconds = float("inf")
        if (_scientific_state_bytes(replay_boundary(cached, at)) != _scientific_state_bytes(state) or
                canonical_bytes(cached._contributions) != canonical_bytes(boundary._contributions)):
            # Revoke the loaded lineage even if a prepared incremental consumer
            # has already replaced the checkpoint with one of its descendants.
            # Persist the negative fence before removing the current cache, so
            # interruption cannot leave a rejected lineage loadable again.
            with archive.mutation_lock():
                assert_boundary(archive, boundary)
                rejected = _rejected_path(archive, recorded["lineage"])
                if not rejected.exists():
                    _write_transaction(archive, rejected, {
                        "schema_version": "1", "kind": "rejected-prospective-checkpoint",
                        "rejected_at": at.isoformat(), "checkpoint": recorded,
                    })
                try:
                    current_checkpoint = _read(archive)
                except OperationsError:
                    current_checkpoint = None
                if current_checkpoint is not None and current_checkpoint["lineage"] == recorded["lineage"]:
                    projection_path(archive).unlink()
                    _sync_directory(archive.root)
            raise OperationsError("projection-replay-conflict", "checkpoint differs from independent full replay; explicit rebuild required")
    _publish(archive, boundary, at)
    return state


def _prepare_checkpoint(archive, at):
    recorded = _read(archive)
    boundary = capture_boundary(archive)
    boundary._checkpoint_lineage = recorded["lineage"]
    _assert_lineage(archive, boundary._checkpoint_lineage)
    boundary.blocked_opportunities = check_capture_persistence(archive, boundary.entries())
    if boundary.blocked_opportunities:
        raise OperationsError("prospective-publication-ambiguous", "unresolved capture marker")
    current = _material(archive, boundary.entries())
    old_ids = set(recorded["source_manifest_ids"])
    if not old_ids <= set(current["source_manifest_ids"]):
        raise OperationsError("projection-invalid", "required source manifest disappeared")
    if datetime.fromisoformat(recorded["built_at"]) > at:
        raise OperationsError("projection-invalid", "checkpoint is future-effective")
    delta = tuple(x for x in boundary.entries() if x["manifest_entry_id"] not in old_ids)
    if len(delta) > MAX_DELTA_MANIFESTS:
        raise OperationsError("projection-budget-exceeded", "excessive append delta; offline rebuild required")
    boundary._signatures = {tuple(key.split(":")): tuple(sig) for key, sig in recorded["signatures"].items()}
    boundary._verified_identities = set(boundary._signatures)
    for key, signature in boundary._signatures.items():
        if _signature(boundary._path(*key)) != signature:
            raise OperationsError("projection-invalid", "checkpoint source changed or disappeared")
    boundary._json = {("normalized", key): value for key, value in recorded["normalized"].items()}
    boundary._contributions = recorded["contributions"]
    # Replay the entire timestamp cohort at the insertion point. Never infer a
    # substantive order from the manifest digest of a new same-time publication.
    cutoff = min((x["acquired_at"]["datetime_utc"] for x in delta), default=None)
    suffix = [x for x in boundary.entries() if cutoff is not None and x["acquired_at"]["datetime_utc"] >= cutoff]
    if len(suffix) > MAX_DELTA_MANIFESTS:
        raise OperationsError("projection-budget-exceeded", "append changes an excessive replay suffix")
    boundary._reusable = old_ids - {x["manifest_entry_id"] for x in suffix}
    # A completion/correction can change earlier session contributions. Rewind
    # to the earliest affected group/session and replay the complete suffix.
    touched_sessions = set()
    touched_groups = set()
    for entry in delta:
        if entry.get("normalized_object_id"):
            value = boundary.read_json_verified("normalized", entry["normalized_object_id"])
            session = value.get("session_id") or value.get("supporting_session_id")
            group = value.get("acquisition_id")
            if session: touched_sessions.add(session)
            if group: touched_groups.add(group)
    for entry in boundary.entries():
        if entry["manifest_entry_id"] not in old_ids or not entry.get("normalized_object_id"): continue
        value = boundary._json[("normalized", entry["normalized_object_id"].split(":")[-1])]
        if ((value.get("session_id") or value.get("supporting_session_id")) in touched_sessions or
                value.get("acquisition_id") in touched_groups):
            cutoff = min(cutoff, entry["acquired_at"]["datetime_utc"])
    suffix = [x for x in boundary.entries() if cutoff is not None and x["acquired_at"]["datetime_utc"] >= cutoff]
    if len(suffix) > MAX_DELTA_MANIFESTS:
        raise OperationsError("projection-budget-exceeded", "lineage delta requires an excessive replay suffix")
    boundary._reusable = old_ids - {x["manifest_entry_id"] for x in suffix}
    return boundary, recorded, current


def load_projection(archive, at):
    try:
        boundary, recorded, current = _prepare_checkpoint(archive, at)
        state = replay_boundary(boundary, at)
        if recorded["source_manifest_ids"] != current["source_manifest_ids"]:
            _publish(archive, boundary, at)
        return boundary, state
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise OperationsError("projection-invalid", "checkpoint source or replay state is invalid") from exc


def projection_status(archive, at):
    try:
        boundary, recorded, current = _prepare_checkpoint(archive, at)
        replay_boundary(boundary, at)
        return "current" if recorded["source_manifest_ids"] == current["source_manifest_ids"] else "stale"
    except OperationsError as exc:
        return "absent" if exc.code == "projection-absent" else "invalid"
    except (OSError, ValueError, KeyError, TypeError):
        return "invalid"


@contextmanager
def collector_lock(archive):
    """Serialize collectors only; supporting publication remains independent."""
    archive._ensure_mutable()
    with (archive.root / "prospective-collector.lock").open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise OperationsError("prospective-collector-busy", "another collector owns capture") from None
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_object_directory(path):
    _sync_directory(path.parent)
    _sync_directory(path.parent.parent)


def _read_transaction(path):
    try:
        with path.open("rb") as handle:
            body = handle.read(8193)
        if len(body) > 8192: raise ValueError
        envelope = json.loads(body)
        value = envelope["transaction"]
        if (set(envelope) != {"transaction", "sha256"} or not isinstance(value, dict) or
                value.get("schema_version") != "1" or
                envelope["sha256"] != sha256_bytes(canonical_bytes(value))):
            raise ValueError
        return value
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise OperationsError("prospective-publication-ambiguous", "transaction marker is invalid") from exc


def _write_transaction(archive, path, value):
    """Caller holds mutation lock. The fence is durable before transport/writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / (".transaction-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as handle:
            handle.write(canonical_bytes({"transaction": value, "sha256": sha256_bytes(canonical_bytes(value))}))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
        _sync_directory(archive.root)
    finally:
        temporary.unlink(missing_ok=True)


def check_capture_persistence(archive, entries):
    """Bounded metadata-only check; scientific verification still follows it.

    Unresolved request or publication ambiguity stops capture, including no-call
    dispositions: an unknown prior request must not be relabeled as a miss.
    """
    by_id = {entry["manifest_entry_id"]: entry for entry in entries}
    blocked = set()
    root = archive.root / "prospective-publications"
    for number, path in enumerate(root.glob("*.json")):
        if number >= MAX_SOURCE_OBJECTS:
            raise OperationsError("projection-budget-exceeded", "too many prospective publication intents")
        value = _read_transaction(path)
        expected = {"schema_version", "kind", "namespace", "mode", "invocation_id", "manifest_entry_id", "opportunity_id"}
        if (set(value) != expected or value["kind"] != "prospective-publication" or
                value["namespace"] != archive.config.namespace or value["mode"] != archive.config.mode.value or
                any(not isinstance(value[k], str) or not value[k] for k in ("invocation_id", "manifest_entry_id", "opportunity_id")) or path.stem != sha256_bytes(value["invocation_id"].encode())):
            raise OperationsError("prospective-publication-ambiguous", "publication intent identity is invalid")
        entry = by_id.get(value["manifest_entry_id"])
        if entry is None or entry["command"] != "capture-prospective" or entry["invocation_id"] != value["invocation_id"] or f"opportunity:{value['opportunity_id']}" not in entry["diagnostics"]:
            blocked.add(value["opportunity_id"])
    for number, path in enumerate((archive.root / "prospective-requests").glob("*.json")):
        if number >= MAX_SOURCE_OBJECTS:
            raise OperationsError("projection-budget-exceeded", "too many prospective request fences")
        value = _read_transaction(path)
        expected = {"schema_version", "kind", "namespace", "mode", "nonce", "protocol_id", "opportunity_id", "state", "manifest_entry_id"}
        if (set(value) != expected or value["kind"] != "prospective-request" or
                value["namespace"] != archive.config.namespace or value["mode"] != archive.config.mode.value or
                any(not isinstance(value[k], str) or not value[k] for k in ("nonce", "protocol_id", "opportunity_id", "state")) or
                (value["manifest_entry_id"] is not None and not isinstance(value["manifest_entry_id"], str)) or
                path != _request_path(archive, value["protocol_id"], value["opportunity_id"])):
            raise OperationsError("prospective-publication-ambiguous", "request fence identity is invalid")
        if value["state"] == "no-transport" and value["manifest_entry_id"] is None:
            continue
        entry = by_id.get(value["manifest_entry_id"])
        if (value["state"] != "publication" or entry is None or entry["command"] != "capture-prospective" or
                entry["protocol_id"] != value["protocol_id"] or
                f"opportunity:{value['opportunity_id']}" not in entry["diagnostics"]):
            blocked.add(value["opportunity_id"])
    return frozenset(blocked)


def _request_path(archive, protocol_id, opportunity_id):
    digest = sha256_bytes(canonical_bytes((protocol_id, opportunity_id)))
    return archive.root / "prospective-requests" / (digest + ".json")


def begin_request(archive, protocol_id, opportunity_id):
    """Called under both collector ownership and the short mutation lock."""
    if opportunity_id in check_capture_persistence(archive, archive.entries()):
        raise OperationsError("prospective-publication-ambiguous", "prior request cannot be repeated")
    value = {"schema_version": "1", "kind": "prospective-request", "namespace": archive.config.namespace,
             "mode": archive.config.mode.value, "nonce": uuid.uuid4().hex, "protocol_id": protocol_id,
             "opportunity_id": opportunity_id, "state": "pending", "manifest_entry_id": None}
    _write_transaction(archive, _request_path(archive, protocol_id, opportunity_id), value)
    return value


def _finish_request(archive, fence, manifest_id):
    path = _request_path(archive, fence["protocol_id"], fence["opportunity_id"])
    if _read_transaction(path) != fence:
        raise OperationsError("prospective-publication-ambiguous", "request ownership changed")
    _write_transaction(archive, path, {**fence, "state": "publication" if manifest_id else "no-transport",
                                      "manifest_entry_id": manifest_id})


def cancel_unissued_request(archive, fence):
    """Only the live owner knows that transport has not yet been entered."""
    with archive.mutation_lock():
        _finish_request(archive, fence, None)


def publish_capture(archive, *, normalized, entry_values, raw_body=None, request_fence=None):
    """Manifest-identical bounded publication after canonical capture validation.

    A durable intent precedes object writes. An interrupted intent cannot be
    retried or adopted; only an exact completed manifest proves idempotence.
    """
    opportunities = tuple(x.removeprefix("opportunity:") for x in entry_values["diagnostics"] if x.startswith("opportunity:"))
    if len(opportunities) != 1 or entry_values["command"] != "capture-prospective":
        raise OperationsError("capture-persistence-invalid", "capture publication requires one opportunity")
    opportunity_id = opportunities[0]
    body = canonical_bytes(normalized)
    digest = sha256_bytes(body)
    raw_digest = sha256_bytes(raw_body) if raw_body is not None else None
    entry = ManifestEntry.create(**entry_values, namespace=archive.config.namespace,
                                 operating_mode=archive.config.mode,
                                 raw_object_sha256=raw_digest,
                                 normalized_object_id=f"normalized:{digest}",
                                 normalized_schema_version=str(normalized["schema_version"]))
    with archive.mutation_lock():
        prior = tuple(x for x in archive.entries() if x["invocation_id"] == entry.invocation_id)
        if any(x["manifest_entry_id"] != entry.manifest_entry_id for x in prior):
            raise OperationsError("immutable-conflict", "prospective invocation has conflicting content")
        intent = {"schema_version": "1", "kind": "prospective-publication", "namespace": archive.config.namespace,
                  "mode": archive.config.mode.value, "invocation_id": entry.invocation_id,
                  "manifest_entry_id": entry.manifest_entry_id, "opportunity_id": opportunity_id}
        path = archive.root / "prospective-publications" / (sha256_bytes(entry.invocation_id.encode()) + ".json")
        if path.exists():
            if _read_transaction(path) != intent:
                raise OperationsError("immutable-conflict", "prospective publication intent conflicts")
            if not prior:
                raise OperationsError("prospective-publication-ambiguous", "publication interrupted before manifest")
        elif not prior:
            _write_transaction(archive, path, intent)
        if prior:
            if archive._path("manifest", entry.manifest_entry_id).read_bytes() != canonical_bytes(entry):
                raise OperationsError("immutable-conflict", "completed prospective manifest conflicts")
            if raw_body is not None: archive.read_verified("raw", raw_digest)
            archive.read_verified("normalized", digest)
            return entry
        if request_fence is not None:
            _finish_request(archive, request_fence, entry.manifest_entry_id)
        if raw_body is not None:
            path = archive._path("raw", raw_digest)
            archive._publish(path, raw_body)
            _sync_object_directory(path)
        path = archive._path("normalized", digest)
        archive._publish(path, body)
        _sync_object_directory(path)
        path = archive._path("manifest", entry.manifest_entry_id)
        archive._publish(path, canonical_bytes(entry))
        _sync_object_directory(path)
    return entry
