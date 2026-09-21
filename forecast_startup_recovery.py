"""Bounded local boot gate; receipts are Operations state, never Evidence."""
import fcntl
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from forecast_standalone_operations import OperationsError, canonical_bytes, sha256_bytes
from forecast_prospective_projection import (
    _read, _assert_lineage, _sync_directory, rebuild_projection_with_retry,
)


def current_boot_id():
    """Use the kernel's boot-session identity, not wall-clock inference."""
    try:
        if sys.platform == "darwin":
            value = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"],
                                   check=True, capture_output=True, text=True, timeout=5).stdout.strip()
        elif sys.platform.startswith("linux"):
            value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        else:
            raise ValueError("unsupported host")
        return str(uuid.UUID(value))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise OperationsError("startup-identity-unavailable", "Cannot establish kernel boot identity; no acquisition permitted") from exc


def receipt_directory(archive):
    # Different namespaces/configurations must not share startup approval.
    identity = sha256_bytes(canonical_bytes({"config": archive.config.identity,
                                           "root": str(archive.root)}))
    return archive.config.log_root / "startup-recovery" / identity


def _save(path, value):
    raw = canonical_bytes({"receipt": value, "sha256": sha256_bytes(canonical_bytes(value))})
    temporary = path.parent / ("." + uuid.uuid4().hex + ".partial")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _load(path):
    try:
        if path.stat().st_size > 16384:
            raise ValueError("oversized receipt")
        envelope = json.loads(path.read_bytes())
        value = envelope["receipt"]
        if (set(envelope) != {"receipt", "sha256"} or
                envelope["sha256"] != sha256_bytes(canonical_bytes(value)) or
                set(value) != {"version", "boot_id", "status", "started_at", "completed_at", "failure_code", "rebuild_attempts"} or
                value["version"] != "1" or value["status"] not in {"running", "verified", "blocked"} or
                not isinstance(value["boot_id"], str) or not value["boot_id"]):
            raise ValueError("invalid receipt")
        started = datetime.fromisoformat(value["started_at"])
        if started.tzinfo is None or started.utcoffset() is None:
            raise ValueError("invalid receipt time")
        if value["status"] == "verified":
            completed = datetime.fromisoformat(value["completed_at"])
            if (completed.tzinfo is None or completed.utcoffset() is None or completed < started or
                    value["failure_code"] is not None or type(value["rebuild_attempts"]) is not int or
                    not 1 <= value["rebuild_attempts"] <= 3):
                raise ValueError("invalid completion")
        elif value["status"] == "running":
            if any(value[k] is not None for k in ("completed_at", "failure_code", "rebuild_attempts")):
                raise ValueError("invalid intent")
        elif not isinstance(value["failure_code"], str) or not value["failure_code"]:
            raise ValueError("invalid failure")
        return value
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError) as exc:
        raise OperationsError("startup-receipt-invalid", "Startup receipt is damaged; inspect before explicit retry") from exc


def _check_rejection(archive, at):
    # Full rebuild intentionally supports operator recovery from rejected caches.
    # Automatic startup must NOT silently exercise that authority.
    try:
        checkpoint = _read(archive)
    except OperationsError as exc:
        if exc.code not in {"projection-absent", "projection-invalid"}:
            raise
        if any(archive.root.glob("prospective-projection-rejected-*.json")):
            raise OperationsError("projection-rejected", "Unusable checkpoint with retained rejection fence; explicit inspection/rebuild required") from exc
        return
    _assert_lineage(archive, checkpoint["lineage"])
    if datetime.fromisoformat(checkpoint["built_at"]) > at:
        raise OperationsError("trusted-clock-invalid", "Startup precedes checkpoint build time")


def ensure_startup(archive, *, clock, retry=False):
    """One rebuild invocation per boot; failure/interruption requires operator retry.

    Both scheduled entry points use this gate before any provider work.
    Normal hot-path validation remains mandatory after a successful receipt.
    """
    boot_id = current_boot_id()
    directory = receipt_directory(archive)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "recovery.lock").open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise OperationsError("startup-recovery-busy", "Another job is verifying startup; no acquisition permitted") from exc
        try:
            path = directory / "current.json"
            try:
                previous = _load(path)
            except OperationsError:
                if not retry:
                    raise
                previous = None
            if previous and previous["status"] != "verified" and not retry:
                raise OperationsError("startup-recovery-blocked", "Prior recovery failed or was interrupted (" +
                                      str(previous["failure_code"] or previous["status"]) + "); inspect and explicitly retry startup")
            if previous and previous["boot_id"] == boot_id and previous["status"] == "verified" and not retry:
                if datetime.fromisoformat(previous["completed_at"]) > clock():
                    raise OperationsError("trusted-clock-invalid", "Startup receipt is future-effective")
                return {"disposition": "success", "provider_calls": 0, "startup": "already-verified", "boot_id": boot_id}
            started = clock()
            if started.tzinfo is None or started.utcoffset() is None:
                raise OperationsError("trusted-clock-invalid", "Startup clock must be timezone-aware")
            receipt = dict(version="1", boot_id=boot_id, status="running", started_at=started.isoformat(),
                           completed_at=None, failure_code=None, rebuild_attempts=None)
            # Durable intent precedes expensive work. Process death leaves a
            # negative fence, never permission to retry on every collector tick.
            _save(path, receipt)
            try:
                _check_rejection(archive, started)
                attempts = rebuild_projection_with_retry(archive, clock=clock)
                completed = clock()
                if completed < started:
                    raise OperationsError("trusted-clock-invalid", "Startup clock reversed")
                receipt.update(status="verified", completed_at=completed.isoformat(), rebuild_attempts=attempts)
                _save(path, receipt)
            except Exception as exc:
                code = exc.code if isinstance(exc, OperationsError) else "startup-recovery-io-failure"
                receipt.update(status="blocked", failure_code=code, completed_at=None)
                _save(path, receipt)
                if isinstance(exc, OperationsError):
                    raise
                raise OperationsError(code, "Startup verification failed; inspect before retry") from exc
            return {"disposition": "success", "provider_calls": 0, "startup": "rebuilt", "boot_id": boot_id,
                    "rebuild_attempts": attempts}
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
