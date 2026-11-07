# MLB empty interval integration handoff

The Product Owner authorized integrating the independently accepted empty-interval
correction and opening a PR, preserving scope and production pins. See the
[accepted review](MLB_EMPTY_INTERVAL_2026-11-07_REVIEW.md) and
[operating contract](../operations/PROSPECTIVE_PROJECTION.md#validated-empty-supporting-intervals).

Baseline: `0086b91ad0f58f7ca840ef0c38d4aad3bb140b37`. Integration contains the exact
eight reviewed source/test/documentation files plus these durable review/handoff
records. No generated caches, private operational data, credentials, production
archives or reports belong in this PR.

## Acceptance and validation

Complete explicit-zero MLB pages for all unchanged required request dates and a
complete validated catalog are required. Empty unions alone confer no authority.
New zero-contract envelopes declare their rule and must independently replay with
matching dependencies and chronology. Invalid/partial material continues to fail.
Existing objects, unresolved outcomes, failure history and Coverage gaps persist.

The code passed 205 implementer offline regressions, the retained-fixture correction
tests and 188 separate-review regressions, plus eight independent rejection probes.
At integration, recheck the exact reviewed hashes, baseline and committed paths;
rerun the correction tests and reader compatibility checks in the clean checkout.
Any code amendment requires its own review against the approved boundaries.

## Separate future gates

The production pin remains `9564b12dcd80f0b3347b4860b95984763f2e3061`. Neither that
old reader nor unmodified main can consume the new empty acquisitions. Before a
separately authorized rollout, establish compatible actual collector, source-reader
and reporting-worker pins and verify the relevant writer/reader combinations.
Frozen-source fixture compatibility is not report-worker commissioning or a live
report update. Keep those reporting actions separate.

Polling/cadence, date selection, retry policy, startup gates and job topology remain
unchanged. Reduced off-season polling, calendar-gap reconciliation, generalized
failure retention, study closure and next-season enrolment remain deferred.

Current authorization ends at integration and PR creation. Do not merge, tag,
release, deploy, repin jobs, run providers, retry startup, repair archives or refresh
reports based on this handoff. The running lifecycle is not repaired by opening
the PR; that requires a later controlled, compatible deployment.
