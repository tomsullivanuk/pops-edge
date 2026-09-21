"""One bounded, serialized local cycle; immutable Evidence is owned by phases."""
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import fcntl

from forecast_standalone_activation import OperationalHeartbeat, OperationalState
from forecast_standalone_operations import OperationsError, canonical_bytes

SUCCESS = frozenset({"success", "completed", "unchanged", "no-due-work", "pre-activation-no-call"})


class PhaseDisposition(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NOT_DUE = "not-due"
    DEPENDENCY_FAILED = "dependency-failed"


@dataclass(frozen=True)
class PhaseResult:
    command: str
    disposition: PhaseDisposition
    provider_calls: int | None = None
    failure_code: str | None = None
    health_blockers: tuple[str, ...] = ()


def health_failure_reasons(output):
    """Copy only bounded diagnostic codes, never arbitrary heartbeat text."""
    commands = {"capture-prospective", "refresh-supporting", "reconcile-outcomes",
                "rebuild-prospective-projection", "refresh-prospective-projection",
                "rebuild-index", "sync-secondary", "archive-audit", "index"}
    codes = {"stale-or-absent", "lock-timeout", "failed", "dependency-failed",
             "projection-invalid", "projection-stale", "projection-rejected",
             "projection-budget-exceeded", "prospective-publication-ambiguous",
             "integrity-unsafe", "transport-timeout", "transport-connection-failure"}
    allowed = {f"{command}:{code}" for command in commands for code in codes}
    allowed.update({"archive:integrity-unresolved", "secondary:conflict-or-unexplained",
                    "storage:insufficient", "prospective-projection:invalid",
                    "prospective-projection:absent", "prospective-projection:rejected"})
    values = output.get("current_blockers", ())
    if not isinstance(values, (list, tuple)):
        return ("health:unrecognized-blocker",)
    reasons = tuple(value if isinstance(value, str) and value in allowed
                    else "health:unrecognized-blocker" for value in values[:16])
    if len(values) > 16:
        reasons += ("health:additional-blockers-omitted",)
    return reasons or ("health:not-ready",)


def run_cycle(*, archive, state: OperationalState, clock, run):
    """The caller supplies existing typed commands, never a provider coordinator.

    Daily work is due after 04:00 host-local time, once per local date. Hourly
    supporting work is due once per local hour. Failed phases retry on a later
    invocation; skipped/failed records never count as valid completion.
    """
    archive._ensure_mutable()
    with (archive.root / "lifecycle-cycle.lock").open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"disposition": "skipped-cycle", "provider_calls": 0,
                    "reason": "whole-cycle-busy", "phases": ()}
        try:
            started = clock()
            entries = state.entries()
            if any(x.completed_at > started for x in entries):
                raise OperationsError("trusted-clock-invalid", "future cycle phase record")
            latest = {}
            for item in entries:
                if item.disposition in SUCCESS and item.failure_code is None:
                    latest[item.command] = max(item.completed_at, latest.get(item.command, item.completed_at))
            local = started.astimezone()
            def due(command, daily=False):
                prior = latest.get(command)
                if daily:
                    return local.hour >= 4 and (prior is None or prior.astimezone().date() < local.date())
                return prior is None or prior.astimezone().replace(minute=0, second=0, microsecond=0) < local.replace(minute=0, second=0, microsecond=0)
            phases = []
            skipped_hours = []
            next_hour = local.replace(minute=7, second=0, microsecond=0)
            if next_hour <= started: next_hour += timedelta(hours=1)
            def record_elapsed_hours():
                # launchd does not start a second instance of one running job.
                # Record scheduled hourly slots crossed by the live owner, with
                # truthful later detection time; these are not invented invocations.
                nonlocal next_hour
                observed = clock()
                while next_hour <= observed:
                    state.append(OperationalHeartbeat("1", "lifecycle-hour", next_hour, observed,
                        "skipped-cycle", 0, None, None, None))
                    skipped_hours.append(next_hour.isoformat())
                    next_hour += timedelta(hours=1)
            safe = True
            plan = (("refresh-supporting", due("refresh-supporting")),
                    ("reconcile-outcomes", due("reconcile-outcomes", True)),
                    ("rebuild-prospective-projection" if due("rebuild-prospective-projection", True) else "refresh-prospective-projection", True),
                    ("rebuild-index", due("rebuild-index", True)),
                    ("sync-secondary", due("sync-secondary", True)),
                    ("health-report", True))
            for command, is_due in plan:
                record_elapsed_hours()
                if not is_due:
                    phases.append(PhaseResult(command, PhaseDisposition.NOT_DUE))
                    continue
                if not safe and command != "health-report":
                    phases.append(PhaseResult(command, PhaseDisposition.DEPENDENCY_FAILED, 0, "prior-phase-failed"))
                    at = clock()
                    state.append(OperationalHeartbeat("1", command, at, at, "dependency-failed", 0, None, None, "prior-phase-failed"))
                    continue
                try:
                    output = run(command)
                    valid = output.get("disposition", "success" if output.get("ready") else "not-ready") in SUCCESS
                    result = PhaseResult(command, PhaseDisposition.SUCCESS if valid else PhaseDisposition.FAILED,
                                         output.get("provider_calls") if command in {"refresh-supporting", "reconcile-outcomes"} else 0, None if valid else "phase-not-ready",
                                         health_failure_reasons(output) if command == "health-report" and not valid else ())
                except OperationsError as exc:
                    result = PhaseResult(command, PhaseDisposition.FAILED, getattr(exc, "provider_calls", None), exc.code)
                phases.append(result)
                if result.disposition is PhaseDisposition.FAILED:
                    safe = False
            record_elapsed_hours()
            counts = [x.provider_calls for x in phases if x.disposition not in {PhaseDisposition.NOT_DUE, PhaseDisposition.DEPENDENCY_FAILED}]
            return {"disposition": "success" if safe else "failed", "provider_calls": sum(counts) if all(x is not None for x in counts) else None,
                    "skipped_scheduled_hours": tuple(skipped_hours), "phases": __import__('json').loads(canonical_bytes(phases))}
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
