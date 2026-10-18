# Independent review — focused MLB correction

Date: October 17, 2026

Decision: **APPROVED**
Authoritative base: GitHub `main` at `9564b12dcd80f0b3347b4860b95984763f2e3061`

## Scope reviewed

This was a genuinely independent, read-only implementation review of the focused
candidate copied at
`pops-edge-focused-correction-20261017`. GitHub `main` was independently verified
at the beginning and end of review, and the complete root `AGENTS.md` from that
revision was read before the decision.

The reviewed implementation scope was limited to:

- versioning Outcome reconciliation from
  `mlb-outcome-sequential-history-2` to
  `mlb-outcome-sequential-history-3` while preserving exact replay behavior for
  saved version-2 and unversioned envelopes;
- recognizing an ordered multi-date provider-state replay that ends at the
  already-current semantic state without inventing new Schedule transitions;
- retaining normal append and fail-closed graph validation for genuinely new or
  reverted states; and
- limiting prospective market identity-rejection diagnostics to markets whose
  structured participant labels identify the target matchup, rather than
  aggregating parser errors from unrelated catalog markets.

The exact reviewed code/test files and SHA-256 digests were:

- `forecast_standalone_activation.py` —
  `5d57587a65524ad5a3cb560fccfe21c7a56729d587f55dce3e41bae05a305c86`
- `forecast_prospective_market_selection.py` —
  `caf223b7628f42b0b508687da9b7598a7903df121956cd4ce663498ca370d66b`
- `tests/test_forecast_standalone_activation.py` —
  `2fbdac6f2830397a1df4c3f218c03b588000f1552422bea0d2f259ed8ac2e67a`
- `tests/test_forecast_prospective_market_selection.py` —
  `331e972560b6a4f94d0c2ac90eb30d6354216e155a0d804b2125a9f5781900e5`

The final implementer-review note reviewed alongside them had SHA-256
`86848cc331ab23a39069d94e1e570341ce3785f05a68671fea03572a1e4542dc`;
the handoff note had SHA-256
`98fee069825e64464c7004d3d67bc709f0df09d9e8d7d2dcf5d1d93ee5753e2a`.

## Decision and findings

No P0 or P1 defect was found.

The Outcome change is acceptable. New publications declare version 3, replay
accepts version 2 and unversioned historical envelopes under their original
rules, and unknown rule versions continue to fail closed. Version 3 suppresses
only an ordered subsequence of already-recorded semantic states when the last
incoming state equals the current state. If the terminal state is new or
reverted, or a predecessor is not already present in the required order, normal
history construction and graph validation remain authoritative. Exact provider
pages remain preserved through the acquisition envelope even when the derived
contract set is unchanged.

The market-selection change is also acceptable. It does not relax settlement,
participant, schedule, date-only lineage, interval, ambiguity, archived-series,
or provider-request gates. It changes only which failed catalog parses may
contribute to the visible target no-call diagnostic. Unrelated participant
labels no longer create a false target identity-rejection reason.

### Non-blocking P2 caveat

The new diagnostic attribution is matchup-level rather than occurrence-level.
If another market involving the same two teams has settlement identity that is
too malformed to recover its scheduled occurrence, its structured labels can
still contribute `market-identity-rejected` to the current target instead of
`market-unavailable`. This is a bounded diagnostic-precision limitation: it
cannot select a market, authorize transport, create Evidence, alter Outcome
authority, or change failure-inclusive Coverage membership. It is therefore not
a P1 scientific-integrity defect and does not block this focused correction.

## Validation evidence

The independent reviewer ran only offline fixture validation:

- a focused 20-test Outcome versioning, replay, concurrency, and prospective
  selection run passed **20/20**;
- a broader four-module run passed **96/99**, with only three launch-job
  rehearsals blocked by the review sandbox's inability to read the kernel boot
  identity; and
- all four changed Python files passed independent syntax parsing.

Separately, the review coordinator reran the three environment-blocked launch-job
rehearsals with approved kernel boot-ID access and reported that all three
passed. The coordinator also reported a complete **100/100** offline suite and
**55/55** reporting, source-replay, projection, and phase-evaluation tests
passing. Those results are supporting evidence supplied by the coordinator, not
tests independently executed by this reviewer.

No provider call, production archive read or write, scheduler invocation,
deployment, credential access, report refresh, recovery retry, or external
state change was performed in this review. Retained live provider/archive bytes
were not independently inspected; the decision rests on the authoritative
baseline, governing documents, exact diff, code-path analysis, and offline
fixtures.

Generated `__pycache__/` and `tests/__pycache__/` files in the plain candidate
copy are test artifacts, not reviewed source, and must not be staged or deployed.

## Next gate

This approval authorizes no action by itself. The exact next gate is:

1. construct the accepted revision in version control from the reviewed source,
   tests, and review documents only, excluding generated cache artifacts;
2. independently verify the committed revision and use a clean, pinned
   deployment checkout;
3. verify deployed worker and scheduler compatibility with the new version-3
   writer and the version-2/unversioned replay readers; and
4. only after the clean pinned deployment is verified, perform any live Outcome
   reconciliation or prospective acquisition as a separate explicitly
   authorized acquisition action.

Commit, push, pull-request creation or merge, deployment, worker changes, and
provider acquisition remain separate gates outside this review artifact.
