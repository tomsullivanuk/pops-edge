# MLB v1.2.0 reporting implementation sequence

Product Owner decision, September 13, 2026: proceed with two separately reviewed
slices of the accepted reporting analytical context:

1. Frozen reporting source authority: offline immutable boundary, complete source
   selection/dependencies, historical verification and separate verification receipt.
2. Reporting context and successor Analysis: independent event windows, source cutoff
   and actual computation/report times, explicit versioned references and exact replay.

The Owner authorizes implementation, necessary focused corrections, branches,
commits, push, PR creation, review resolution, merge and applicable deployment
following acceptance gates. Each slice requires its own independent acceptance
review. Completion of slice 1 does not complete the capability.

Apply the [reporting contract](MLB_REPORTING_CONTRACT_v1.2.0.md) and
[release plan](RELEASE_PLAN_v1.2.0.md). All scientific invariants and accepted local
limitations remain unchanged. The split is sequencing, not new scientific semantics.

Excluded: HTML reader, operational report generation/publication, baseline display,
shared shell, provider acquisition, study closure, Evidence mutation, new collector
semantics and other release features. Do not repin/restart the live collector merely
to deploy an unused offline library. Evaluate runtime applicability and record an
explicit no-runtime-action disposition where appropriate. Do not tag or declare
v1.2 complete from these slices.
