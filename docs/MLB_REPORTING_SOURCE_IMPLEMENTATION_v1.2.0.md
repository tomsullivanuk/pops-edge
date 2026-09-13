# Reporting source authority — slice 1 implementation

Implemented against `6b74140cce63243e59722cd6661d24fb2377c6e5` (verified GitHub main,
PR #48). This is slice 1 of the [approved two-slice sequence](MLB_REPORTING_IMPLEMENTATION_SEQUENCE_v1.2.0.md),
not completion of the reporting capability or v1.2 release.

`forecast_reporting_source.py` adds an immutable complete-inventory source freeze,
a restricted read-only replay view, original-rule source reconstruction and closure,
visible supporting-session exclusions and a separate actual-time verification receipt.
A fresh freeze fails if the inventory changes. Saved verification uses the independently
retained trusted boundary ID and frozen inventory, while source integrity is still
checked against the entire current namespace. See [API and trust preconditions](MLB_REPORTING_SOURCE_API_v1.2.0.md).

No existing code or public validator changed. The exact candidate code/test/API/
sequence hashes are recorded in the separate [independent acceptance review](MLB_REPORTING_SOURCE_REVIEW_v1.2.0.md).
The review was performed by a separate reviewer agent, not this implementation report.

Validation using Python 3.14.5 and repository-pinned dependencies:

- 89 focused tests passed: new freeze tests, original publication, activation and
  supporting/correction replay suites.
- Full repository regression: 856 tests passed, preserving MLB/NFL/World Cup behavior.
- Independent reviewer: 26 new source and original publication tests passed.
- Synthetic freeze/replay tests forbid socket creation and mutation/lock APIs and
  compare input files before/after. Late completion, legacy correction, rehashed
  omission, namespace corruption outside contributing roots, concurrent append,
  later independent freeze, input-order and Decimal changes are covered.

All acquisition/correction activity in validation used disposable synthetic
namespaces. No deployed Evidence, provider data, indexes, checkpoints or scheduler
state was used or changed. No empirical completeness or live health was assessed.
Historical validation requires the original trusted boundary ID; fabricated clocks
or a candidate-provided replacement trust anchor are outside the API trust contract.
Manual retry after visible inconsistency remains accepted; no recovery service exists.

The Owner already authorized commit, push, PR, merge and applicable deployment after
acceptance. The next implementation gate after this slice's acceptance is slice 2:
context-specific Analysis, complete Coverage, distinct event windows and K/C/R,
unchanged statistics with explicit successor seed/reference identity, and all original
observable validation. Operational report delivery, HTML and baseline remain excluded.
Runtime activation of this library is not needed to operate the existing collector;
final integration will record the deployment disposition without repinning it.
