# Codex Review Prompt — PR19B Development-Only Native MLB Feasibility

Act as an independent implementation reviewer for Pops' Edge. Review the exact
uncommitted PR19B candidate in the current worktree; do not implement corrections,
rerun the sealed test, install dependencies, contact providers, or change archive,
repository, remote, operational, or production state.

## Authoritative state

Repository: `https://github.com/tomsullivanuk/pops-edge`  
Base commit: `29aebcc3ec8e2302014f54d8e842341d8997be82`  
Base tree: `22988010fc53f840185019c84f055761178f452a`

Read the complete root `AGENTS.md` from current GitHub `main`, then inspect:

- `EMPIRICAL_RESEARCH_METHODOLOGY.md`;
- `docs/PRODUCT.md`;
- `ARCHITECTURE.md`;
- `ROADMAP.md`;
- `docs/RELEASE_PLAN_v1.1.0.md`;
- `docs/PR19A_RIGHTS_DECISION_v1.1.0.md`;
- `docs/PR19A_MODEL_0_PROTOCOL_v1.1.0.md`;
- `docs/PR19A_IMPLEMENTATION_REVIEW_v1.1.0.md`;
- `docs/PR19B_FEASIBILITY_PROTOCOL_AND_RESULT_v1.1.0.md`;
- `docs/PR19B_IMPLEMENTATION_REPORT_v1.1.0.md`;
- `pr19b_feasibility.py`;
- `tests/test_pr19b_feasibility.py`; and
- every file under `artifacts/pr19b_feasibility_2026/`.

The governing Product Owner decision is
`/Users/tom/.codex/.chatgpt-projects/g-p-6a6cba0d8b288191820b710ce15a39e4/pr19b_feasibility_product_decision.md`.
Read it completely. The amendment governs this development-only study while the
PR19A 2021–2025 formal-admission protocol remains historical authority.

## Fixed candidate identity and reported result

- classification: `NO BASIC SIGNAL`;
- protocol digest:
  `d00d3c6ca9166e06d0ec0b65b283123c73687d758540309057435f6c1c313b58`;
- test-row identity/label digest:
  `87123bb82eea9e9d7d32c47fdcdae48f4d3665797f3e2c44816f2f99410acf3e`;
- dataset digest:
  `50f9d5265a29fba359a0fb976e239b98b09da62e0a5865ecd153b3832f669e58`;
- frozen implementation code digest:
  `ec5af048587d044a350e891a4199aedcb5a6fa1b0932dea61888cb9f60db7512`;
- model-bundle digest:
  `a2d74f8dfd01055f49fb8b6a659c5529aba7c9d51333fa12c6c4cdaff2e05672`;
- prediction digest:
  `dc4379a64edc60b8a8ccfe8e82d021e1ceba942ead7ccac46ba9f564fb8b971b`;
- result digest:
  `60a1a1c30b2982cb21d5489b29e47bbfd6320316912f5a3acdeee83e9ccc3a31`.

The test-open marker already exists and records the only authorized evaluation.
Do not call `evaluate`, delete or move the marker, create an alternate output
directory for scoring, or calculate a second test result.

## Required independent checks

1. Verify the exact base, worktree diff, candidate files, source-code digest, and
   all content-addressed protocol, dataset, model, prediction, and result digests.
2. Verify freeze chronology: protocol manifest at sequence 1; test-row
   identity/label digest at sequence 2 with no test-label aggregate or fit;
   model bundle at sequence 3; durable test-open marker at sequence 4 before
   labels; exactly one completed evaluation.
3. Inspect the archive adapter against the validated configured paths. Confirm it
   uses manifest authority and immutable digest-verified MLB schedule pages
   read-only, not the derived SQLite index as scientific input.
4. Verify end-to-end market independence. Trace every transitive population,
   feature, label, preprocessing, fitting, calibration, metric, bootstrap, and
   classification input. Confirm no Kalshi availability, mapping, ID, candle,
   price, probability, liquidity, volume, payout, or outcome can influence it.
5. Verify complete population accounting from the MLB schedule universe,
   including every game-level exclusion; confirm counts reconcile to 2,016 and
   that split membership follows scheduled New York dates only.
6. Verify identity, status, decisive outcome, postponed, rescheduled, suspended,
   resumed, cancelled, ambiguous, and doubleheader handling fails closed without
   incidental ordering or favorable-outcome selection.
7. Verify the target boundary, eight-hour prior-outcome proxy, same-season-only
   state, exact PR19A formulas, recent-ten equal-time tie rule, and physical
   target-outcome separation.
8. Verify training-only scaling and primary fitting, validation-only calibration,
   no test influence on parameters or baselines, solver objective and pinned
   numeric behavior, convergence reports, and frozen bundle serialization.
9. Independently recompute or inspect the already persisted prediction and metric
   artifacts without invoking a second evaluation. Verify Brier, Log Loss, fixed
   bins, WACE, both paired improvements, deterministic bootstrap seed material
   and intervals, and exact classifier semantics.
10. Verify deterministic input-order-independent feature, model, prediction,
    metric, bootstrap, and classification behavior through source inspection and
    temporary synthetic fixtures. A read-only reconstruction of the dataset seal
    is permitted only if it does not score or reopen the sealed test result.
11. Verify production archive immutability evidence and that tests use temporary
    fixtures, make no provider call, read no credentials, install no dependency,
    and change no production state.
12. Verify documentation consistently preserves PR19A as historical formal
    admission authority, identifies PR19B as development-only Derived Analysis,
    and keeps future rights-cleared admission and prospective collection
    separately gated.
13. Re-run the focused dependency-free tests and `git diff --check`. Inspect the
    reported full-suite limitation: 511 discovered, 469 passed, 13 failed, and 29
    errored because the existing runtime lacks `requests` and `pandas`. Do not
    install them.

## Review standard and output

Apply the Pops' Edge severity definitions and approved acceptance boundary. Do
not expand the study into formal admission, richer modeling, automatic recovery,
or future-stage architecture. Every blocking finding must state the concrete
trigger, incorrect observable consequence, violated must-hold invariant, and why
an accepted limitation or safe manual boundary is insufficient.

Produce a separate linked review artifact that states:

- ACCEPT or REJECT and the exact development-only scope;
- blocking findings, or confirmation none remain;
- scientific-integrity and operational-fitness conclusions separately;
- evidence and validation performed;
- material limitations, including the dependency-limited full suite;
- external or production state changed during review; and
- the next authorized gate.

Acceptance must not be described as model/dataset admission or authorization to
commit, push, open or merge a pull request, publish provider material, acquire
data, refit, take a second test look, activate, deploy, wager, create Policy or
Governance, or change production behavior.
