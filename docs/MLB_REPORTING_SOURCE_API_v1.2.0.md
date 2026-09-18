# Frozen reporting source API

Slice 1 of the [approved sequence](MLB_REPORTING_IMPLEMENTATION_SEQUENCE_v1.2.0.md).
This offline library does not generate, publish or render operational reports.
It does not activate acquisition or modify the collector.

`forecast_reporting_source.freeze_reporting_source(archive=..., clock=...)`
returns immutable `FrozenReportingSource`. Call it against the actual
`NamespaceArchive`, never an existing filtered view or projection. The trusted
clock is the actual caller's clock (normally aware UTC wall time); injected clocks
are for deterministic offline fixtures, not permission to claim historical availability.
There is no historical cutoff parameter on fresh creation.

The freeze verifies the namespace-wide integrity gate, reads the complete manifest
inventory, samples K, reconstructs source contracts under original rules, verifies
integrity and unchanged inventory, and samples freeze completion. Concurrent changes
produce a visible failure; a later independent attempt is allowed. No locks, writes,
recovery, source normalization or provider calls are performed. Manifest inventory
retains all original dispositions, including non-contributing failed/abandoned
material and prior analytical entries. Source roots and dependency closure are
reconstructed independently; singleton retrospective publications do not contribute
source contracts. Session-specific rejection codes remain visible.

Retain the exact `boundary_id` through a trusted local handoff, independently from
the candidate boundary file being verified. Retain `boundary.to_json()` unchanged.
`FrozenReportingSource.from_json(...)` checks typed encoding and identity, but
self-consistency alone is not historical completeness or scientific acceptance.

`verify_reporting_source(archive=..., boundary=..., expected_boundary_id=...,
clock=...)` checks the independently retained ID, current namespace-wide integrity,
retained exact manifests, frozen source selection/closure/dispositions and the
original graph digest. It returns original-version `ScientificArchiveState` plus
a new `SourceVerificationReceipt` with actual verification time. It never admits
later additions to the old inventory, even if completion/correction manifests
retain original acquisition timestamps. Later namespace corruption still blocks.

**Trust boundary:** never obtain `expected_boundary_id` from the untrusted candidate
itself. A caller that fabricates both the historical boundary and its alleged
trusted ID has not supplied the retained proof required by this API. Hashes do not
prove a historical world state without the original trusted freeze. No signing
service, collector receipt or generalized persistence system is introduced. A
future delivery adapter must preserve this small explicit trust boundary.

All pinned original source objects retain their original identifiers, serialization,
selection and replay semantics. Returning a source graph does not authorize old
analytical objects under a successor context: slice 2 must reconstruct its own
complete compatible report-local Analysis and exclude post-K facts. This slice
neither scores results nor claims that a full report or calendar is available.

Accepted limitations: local/manual use, retained trusted boundary required for
historical verification, fail visibly on inconsistent source inventories, existing
namespace integrity failures and session-local exclusion semantics. No automatic
retry/recovery, snapshot database, publication pointer or background service.
Source storage retention remains necessary for replay.

### Invocation-local verification reuse

Report generation reconstructs each exact archive/inventory/cutoff once and reuses
that verified graph across its analytical and package checks. The scope is local
to that invocation, retains at most one graph, and is discarded on success or
failure. It does not persist trust or reuse an earlier report as Evidence.
Every source verification still checks the independent boundary ID, full current
namespace integrity, retained manifests, selection/closure/dispositions, graph
digest and chronology. Returned containers are independent copies. A changed
inventory or cutoff cannot reuse the graph. Separate explicit verification retains
its independent reconstruction behavior. One initial reconstruction remains
necessary; durable incremental source verification is outside this correction.

Within each reconstruction the read-only view keeps verified bytes, decoded JSON
and successful supporting/acquisition checks only for that complete frozen
inventory. Nested manifest values are immutable, avoiding repeated inventory
serialization. Original validators still check page completeness, lineage, union
identity and derivation; failure results are not cached. Before returning the
graph, every consumed source object is re-read and hash-verified through the real
archive, decoded values are checked for accidental mutation, and namespace-wide
integrity is checked again (including unconsumed objects). Corruption or
removal during reconstruction fails closed. These caches are discarded with the
view; memory scales with the consumed source bytes and parsed objects for one
reconstruction, not with a retained history of report runs.

Validation uses temporary synthetic namespaces, including late completion,
legacy completion followed by correction, rehashed omission/tampering, missing
and corrupt material outside contributing roots, concurrent append, independent
later work, unchanged source files, input permutations and Decimal changes.
The original protocols and public validators are untouched.
