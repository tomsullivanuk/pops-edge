# Prospective checkpoint and local lifecycle

`prospective-projection.json` is disposable, non-authoritative Operations state.
The immutable archive is the sole source of truth and recovery source. The
checkpoint does not create Evidence, change Coverage, approve Policy, or permit
backfill. It is local to one namespace, mode and filesystem; never copy it to a
new deployment archive and treat its signatures as verified there.

## Checkpoint format and use

Schema 4 / builder `compact-source-metadata-1` stores a checksum, exact
selected manifest IDs, build time, namespace/mode, compact verified source
metadata, raw/normalized object identities and filesystem signatures, and
canonical contract contributions for each manifest, and a local lineage ID.
Only independent full source replay creates a fresh lineage; incremental
publication retains the loaded lineage. Contributions retain earlier
history versions needed by deterministic subsequent derivation. The current graph
is reconstructed and validated at the invocation's trusted time. The metadata
omits only the duplicate `contracts` arrays from known acquisition and contract
bundles. It preserves other fields and record kinds for integrity, dependency and
session/correction scans. Metadata is accessed separately from full normalized
payloads: actual contribution derivation re-reads and digest-verifies the complete
source payload when needed. An unchanged replay uses signatures, metadata and
contributions without historical payload reads. No scientific validator receives
a compact bundle as though it were a complete source payload.

Schema 3 checkpoints are unsupported disposable cache, requiring an offline
rebuild before capture under schema 4. Immutable sources and durable markers are
not migrated or changed. Full replay also compares compact metadata at matching
boundaries; a disagreement rejects the cached lineage by the same durable fence.

A cold offline build verifies the complete archive's bytes and integrity, then
replays the complete relevant source set. Its budget is independent of the
collector's 20-second preparation limit. A usable same-boundary checkpoint must
produce identical canonical state **and per-manifest contributions** before the
cold build replaces it. A detected replay mismatch atomically persists a checksummed
rejection record containing the compared checkpoint at
`prospective-projection-rejected-<lineage>.json`, fsyncs it, then removes any current
checkpoint of that lineage under the mutation lock. The record's presence revokes
that lineage, including already-prepared collectors and incremental publishers;
replacing the checkpoint cannot undo rejection. These diagnostic rejection records
are durable negative Operations fences: preserve them, including after a later
full rebuild. They are not scientific authority or disposable checkpoint cache.
Interruption after the fence but before cache removal still blocks that lineage
in a fresh process. A later explicit full rebuild can publish a new independent
lineage without clearing any rejection or capture marker. Full source replay stays
outside the mutation lock. Immutable source material is never moved. Corrupt, missing or old-format disposable checkpoints may
be rebuilt from verified immutable sources. No build repairs source material or
clears transaction markers.

```sh
python operate_forecast_standalone_activation.py --config /absolute/config.json rebuild-prospective-projection
```

Hot preparation verifies the checksum and versions, independently discovers the
manifest boundary under the mutation lock, checks all recorded source signatures,
and checks durable request/publication markers. Historical payload bytes are not
reread when those signatures match. New sources are digest-verified. The full
acquisition-integrity scan uses cached normalized metadata and checks the exact
current source set; new group conflicts and incomplete publication remain blocking.

At most 256 new manifests and 256 replay-suffix manifests are permitted. The suffix
starts at the earliest insertion timestamp, including its entire timestamp cohort,
or at an earlier affected acquisition/session. This retains ordinary replay order
and prevents stale earlier contributions after a correction. Required old raw
pages are verified if suffix derivation needs them. The graph is always validated
by the existing scientific validator. Excessive suffixes require an offline build;
no source or population is truncated. Newly read payloads retain the 8,192-object /
256-MiB bounds. The checkpoint has a 128-MiB serialized format bound. This is the
2026-09-20 emergency capacity amendment to schema 3's former 64-MiB bound. Schema 4
removes duplicate bundle contract arrays but does not promise unlimited growth;
canonical contributions and source metadata still grow with archive history.
Finite capacity and explicit manual rebuild/design inspection remain accepted.
Both reading and
publication enforce the same bound. An oversized publication preserves the prior
complete checkpoint and fails visibly before replacement. Recovery requires a
reviewed pinned deployment and offline rebuild; missed windows stay missing.

Publication writes and fsyncs a unique temporary file, checks the final boundary
and source signatures and absence of its lineage's rejection fence under the
mutation lock, atomically replaces the checkpoint,
and fsyncs the directory. Interruption leaves either the old complete checkpoint or
the new complete checkpoint. An unreferenced `.prospective-*.partial` cache file
has no authority. A later independent invocation may use the complete checkpoint;
this does not adopt an incomplete archive acquisition.

Immediately before a prospective provider request, the existing collector path
checks the boundary, source signatures, markers, and lineage rejection again under the mutation lock,
then re-resolves trusted timing and slot authority. A separate collector lock
continues to prevent duplicate requests. Provider latency is outside preparation;
actual calls and their immutable dispositions are preserved unchanged.

| Status | Meaning / next action |
| --- | --- |
| absent | No checkpoint; explicit offline build required before collector calls. |
| current | Exact source boundary and signatures validate. The collector still checks current Protocol, activation, Schedule and slot authority. |
| stale | A bounded append delta is usable; the collector can verify/replay it and atomically publish an updated checkpoint. |
| invalid | Unsupported/corrupt checkpoint, source removal/change, future boundary, ambiguous or incomplete source authority; no collector transport. Inspect before rebuilding. |
| projection-budget-exceeded | Delta, suffix, serialized state, source work or time exceeds the bound; offline rebuild or design inspection required. |
| projection-rejected | Full replay rejected the loaded lineage; preparation cannot authorize transport or republish it, even if a newer checkpoint exists. Preserve rejection records and initiate an independent full rebuild. |
| prospective-publication-ambiguous | An unresolved request/publication marker blocks checkpoint use globally. Preserve records for manual inspection; do not retry unknown calls or relabel them as misses. |

This correction deliberately strengthens the earlier per-opportunity marker gate:
an unresolved marker now prevents all checkpoint-authorized requests. Completed
manifest-linked markers remain auditable and do not block later work. No automatic
marker repair, archive mutation, abandoned-call adoption, or quote reconstruction
is introduced. Scientific capture windows and missing Coverage remain unchanged.

## One non-collector cycle

### Bounded startup verification (September 21, 2026)

The Owner approved a narrow exception to manual-only checkpoint recovery:
both scheduled CLI entry points (`capture-prospective` and `lifecycle-cycle`)
must pass a shared startup gate before any provider work. The gate identifies
the host's kernel boot session (macOS `kern.bootsessionuuid`; Linux boot ID for
portable offline execution). An unavailable identity fails closed, rather than
guessing from wall time or treating a permissions failure as archive corruption.

On first use, or after a new boot, the gate performs full offline archive
verification and checkpoint rebuild, even when that calendar day's ordinary
rebuild already completed. It does not ignore or overwrite cached filesystem
signatures. Ordinary process/service restarts in the same verified boot reuse
the receipt; all existing per-invocation source, lineage, marker and timing
fences still apply. A receipt does not make an invalid checkpoint usable.

One nonblocking OS lock serializes this gate across the two jobs. A competing
invocation exits with `startup-recovery-busy` and zero provider calls. The normal
job schedule can try again after the owner completes. Durable `running` intent
is published before rebuilding; completion atomically publishes a checksummed
`verified` receipt. One startup invocation permits the existing maximum three
full preparations, retrying only `projection-stale`, not integrity failures.
This is an attempt bound, not a new wall-clock timeout for full replay.

Failure publishes `blocked`. Process interruption leaves `running`; after its
lock is released that state is treated as blocked, not retried automatically.
Neither a later scheduled tick nor another reboot clears a blocked/interrupted
attempt. Both jobs stop before provider work. A rejected current lineage, or an
unusable checkpoint with retained rejection records, requires explicit inspection
and the existing operator rebuild procedure. Request/publication markers are never
cleared, uncertain calls never repeated, and missed windows never reconstructed.

Receipts and the lock live under `LOG_ROOT/startup-recovery/<config-and-root-hash>/`,
outside the immutable archive and secondary copy. `verify-startup` and the calling
job record operational heartbeat outcomes; CLI failures include concrete failure
codes with zero provider calls during recovery. The original error and receipt
must be inspected before an operator explicitly invokes:

```sh
python operate_forecast_standalone_activation.py --config /absolute/config.json verify-startup --retry-startup
```

That command repeats full verification; it does not waive a rejection fence or
repair source Evidence. `verify-startup` without the flag checks the gate without
granting a retry. Routine job invocations must never use the retry flag. A manual
full rebuild alone does not clear a blocked startup receipt; explicit startup
retry is still required. Corrupt receipt bytes also require explicit retry.

First commissioning of this amendment requires the same startup verification
before reactivation. This does not install new jobs, alter hourly/daily schedules,
or authorize deployment. Independent review and controlled commissioning remain
separate gates. Mid-boot source corruption remains fail-closed under the existing
checks; generalized recovery, automatic marker repair and cloud watchdogs are
out of scope.

`lifecycle-cycle` is the only scheduled non-collector entry point. It takes a
nonblocking whole-cycle lock and runs typed phases sequentially:

1. Supporting refresh once per host-local clock hour.
2. Outcomes once per host-local date, due at/after 04:00.
3. Full checkpoint rebuild once per host-local date at/after 04:00; otherwise
   bounded checkpoint refresh after publication.
4. Index rebuild once per host-local date at/after 04:00.
5. Secondary synchronization once per host-local date at/after 04:00.
6. Health evaluation after all phase results are known.

Daily phases retry at a later hourly invocation if they lack a valid completion;
there is no queue or automatic repair. Missing a day does not cause one run per
missed date or retrospective quote acquisition. Failed phases produce typed
failure records; later dependent phases record `dependency-failed` without running.
Health still runs to expose the condition. Failed lifecycle results exit nonzero
even when returned rather than raised.
The health phase retains up to 16 allowlisted `health_blockers` codes, with an
explicit omission marker for excess entries. Unrecognized codes are redacted;
an empty blocker list on a not-ready report retains a generic health reason.
No provider payloads or checkpoint source boundaries are copied into this summary.
A collector lock timeout remains blocking until later independent successful work
supersedes it; a later recovery does not rewrite the original failed cycle.
`not-due` is a typed cycle result and never updates a last-valid-completion time.
Counts are summed only when known;
unknown accounting remains unknown rather than becoming zero.

A competing hourly invocation exits visibly as `skipped-cycle` with zero calls.
Because launchd itself does not start a second instance of a running job, the
live owner also records `lifecycle-hour:skipped-cycle` for each scheduled minute-7
slot it crosses, using the slot time and actual later detection time. These records
describe skipped schedule slots, not invented invocations. The live owner completes
its daily work. The next independent hourly cycle may
resume supporting acquisition. A process exit releases the OS lock. There is no
worker service, queue, distributed coordinator, or automatic acquisition repair.

## Health interpretation and recovery

Health separately reports current collector readiness, full archive integrity,
checkpoint usability/boundary, last valid phase completion/cadence, audit/index age,
secondary age/lag/conflicts, recent failures, superseded failures, skips and current
blockers. Historical failures remain append-only; later successful work can resolve
the current condition. A prior `health-report:not-ready` cannot permanently poison
readiness. None of these observations proves complete prospective Coverage.

A verified index whose published rows are intact and whose IDs are a strict subset
of the archive reports `append-only-lag`, not corruption. Index builder 2 checksums
its published rows; removed or altered rows are disagreement. Old builders require
rebuild. Expected secondary lag is separately visible between daily syncs; conflicts
or unexplained secondary objects are unsafe. Collector cadence is 90 seconds,
supporting 3,900 seconds (7,500 following a recent visible skipped hourly cycle),
and daily audit/index/outcomes/sync 90,000 seconds. Missing or failed current safety
preconditions keep readiness false even when historical successes exist.

Loss/corruption of a checkpoint is recovered by a full offline rebuild after
inspection, never by changing archive bytes. Missed windows stay missed. The Mac
being asleep, offline, logged out, or short of storage remains a visible operational
limitation. Full builds may take minutes; manual intervention for integrity failures
and markers remains accepted.

See [clean pinned commissioning](PINNED_DEPLOYMENT.md). Implementation and offline
validation do not authorize deployment, provider access or scheduler activation.
