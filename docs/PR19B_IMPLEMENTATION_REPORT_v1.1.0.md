# PR19B Development-Only Native MLB Feasibility Implementation Report

## Outcome

**NO BASIC SIGNAL.** The bounded PR19B implementation is complete and ready for
independent review. This is a development-only feasibility result. It admits no
dataset, model, or Probability Source and creates no scientific, Forecast,
Policy, Governance, wagering, deployment, or production authority.

The model improved on constant `p = 0.5` but did not improve on the smoothed
training home-win-rate baseline. The fixed BASIC SIGNAL condition therefore
fails; the paired intervals also cross zero.

## Exact candidate and authority

- authoritative GitHub `main` commit:
  `29aebcc3ec8e2302014f54d8e842341d8997be82`;
- authoritative tree:
  `22988010fc53f840185019c84f055761178f452a`;
- worktree state: detached at that exact commit, with the uncommitted PR19B
  candidate listed below;
- Product Owner decision: `pr19b_feasibility_product_decision.md`, dated
  2026-09-01;
- historical authority preserved:
  [PR19A Model 0 protocol](PR19A_MODEL_0_PROTOCOL_v1.1.0.md) and
  [rights decision](PR19A_RIGHTS_DECISION_v1.1.0.md);
- current amendment and result:
  [PR19B feasibility protocol and result](PR19B_FEASIBILITY_PROTOCOL_AND_RESULT_v1.1.0.md).

No branch was created or switched. No commit, push, pull request, tag, merge,
deployment, activation, or publication occurred.

## Candidate files

Implementation and focused validation:

- `pr19b_feasibility.py`;
- `tests/test_pr19b_feasibility.py`.

Durable documentation:

- `ROADMAP.md`;
- `ARCHITECTURE.md`;
- `docs/RELEASE_PLAN_v1.1.0.md`;
- `docs/PR19B_FEASIBILITY_PROTOCOL_AND_RESULT_v1.1.0.md`;
- `README.md`;
- `CHANGELOG.md`;
- this report; and
- `docs/PR19B_INDEPENDENT_REVIEW_PROMPT_v1.1.0.md`.

Local, content-addressed Derived Analysis is under
`artifacts/pr19b_feasibility_2026/`. It includes the protocol and dataset seals,
source descriptor, complete Coverage reconciliation, physically separated test
features and sealed labels, model bundle and seal, predictions, exact metrics,
test-open marker, and completion statement. These private artifacts must not be
published as raw provider material. The exact path is excluded by `.gitignore`
and is not part of the public-safe candidate file set.

The sealed package is preserved byte-for-byte at the approved private local
destination
`/Users/tom/PopsEdgeData/private-derived-analysis/pr19b_feasibility_2026/`.
Both the worktree source and private copy contain 15 files and 1,115,435 bytes.
Under `sha256(canonical-json(sorted [{path,bytes,sha256}]))`, both inventories
have digest
`e4348a9c249eb70711271f04fcdc0e62a1bf79a642211ef3830defd4005ff287`.
The worktree copy was not deleted or altered.

### Exact public-safe candidate file set

Only these repository files are eligible for a future bounded commit:

- `.gitignore`;
- `ARCHITECTURE.md`;
- `CHANGELOG.md`;
- `README.md`;
- `ROADMAP.md`;
- `docs/RELEASE_PLAN_v1.1.0.md`;
- `docs/PR19B_FEASIBILITY_PROTOCOL_AND_RESULT_v1.1.0.md`;
- `docs/PR19B_IMPLEMENTATION_REPORT_v1.1.0.md`;
- `docs/PR19B_INDEPENDENT_REVIEW_PROMPT_v1.1.0.md`;
- `docs/PR19B_POST_REVIEW_AMENDMENT_HANDOFF_v1.1.0.md`;
- `pr19b_feasibility.py`; and
- `tests/test_pr19b_feasibility.py`.

Every file beneath `artifacts/pr19b_feasibility_2026/`, and every unrelated or
private file, is outside that boundary and must not be staged, committed, or
pushed.

## Freeze and deterministic identity

The machine-readable protocol manifest was written before archive labels were
used. The test-row identity/label digest was then frozen without calculating a
test-label aggregate. No model was fitted before both seals existed.

- protocol digest:
  `d00d3c6ca9166e06d0ec0b65b283123c73687d758540309057435f6c1c313b58`;
- test-row identity/label digest:
  `87123bb82eea9e9d7d32c47fdcdae48f4d3665797f3e2c44816f2f99410acf3e`;
- dataset digest:
  `50f9d5265a29fba359a0fb976e239b98b09da62e0a5865ecd153b3832f669e58`;
- implementation code digest at freeze:
  `ec5af048587d044a350e891a4199aedcb5a6fa1b0932dea61888cb9f60db7512`;
- model-bundle digest:
  `a2d74f8dfd01055f49fb8b6a659c5529aba7c9d51333fa12c6c4cdaff2e05672`;
- prediction digest:
  `dc4379a64edc60b8a8ccfe8e82d021e1ceba942ead7ccac46ba9f564fb8b971b`;
- result digest:
  `60a1a1c30b2982cb21d5489b29e47bbfd6320316912f5a3acdeee83e9ccc3a31`.

The model bundle was frozen at sequence 3. The durable test-open marker was
written at sequence 4 before sealed labels were read. The completion artifact
records exactly one evaluation. The implementation refuses a second look.

## Population and Coverage

The adapter used only content-addressed archive pages with provider
`mlb-stats-api` and purpose `schedule`. It extracted game/team identity,
schedule, game type, status, score, and winner facts through an allowlist and
performed a prohibited-field scan. No Kalshi page, mapping, market ID, candle,
price, probability, liquidity, volume, or outcome entered a native input.

| Population | Count |
|---|---:|
| Schedule universe | 2,016 |
| Training rows | 1,270 |
| Validation rows | 361 |
| Test rows | 356 |
| Total measured rows | 1,987 |

All 30 franchises appear in every split. The complete disjoint exclusions are:

| Disposition | Count |
|---|---:|
| Ambiguous identity | 18 |
| Ambiguous schedule evolution | 6 |
| Postponed | 4 |
| Unsupported game type | 1 |

Every schedule-universe game has one visible reconciliation disposition.
An additional read-only reconciliation compared every raw positive `gamePk`
with the extracted adapter population: all 2,016 unique raw identities were
present, with no missing/invalid record-level identity and no valid identity
silently omitted.

## Model and dependency settings

The implementation uses the Python standard library only:

- CPython `3.14.5`;
- macOS `26.6.2`, arm64;
- SQLite `3.50.4` for identity reporting only; immutable manifests and objects,
  not the derived SQLite index, are source authority;
- IEEE-754 binary64 model arithmetic;
- deterministic damped Newton solver, tolerance `1e-12`, limit 200 iterations,
  fixed halving line search;
- L2 logistic objective with `C = 1`, unpenalized intercept, no class weights;
- training-only means and population standard deviations;
- validation-only unpenalized two-parameter sigmoid calibration; and
- no dependency installation, search, retuning, alternate model, or refit.

Scaler means are `[-0.00092534111001781646, -0.031083772022720651,
-0.0074141300519253274]`; scales are `[0.14842768173794388,
1.015631392731662, 0.21285806103283245]`.

The primary estimator converged in four iterations with parameters
`[0.10473763033189655, -0.15435549937866452, 0.17762368593570402,
0.1204890064099208]`. The calibrator converged in three iterations with
parameters `[-0.072237904839559969, 1.0638022664104914]`.

## One-look result

Baseline probabilities are `0.5` and `0.52594339622641506`.

| Source | Brier Score | Log Loss | WACE |
|---|---:|---:|---:|
| Model 0 | 0.24824815789596828011462149504304157584269662921348 | 0.68968363791382095919585282599548251917166735200278 | 0.057311410986174247078651685393258426966292134831459 |
| Constant 0.5 | 0.25 | 0.69314718055994530941723212145817656807550013436 | 0.05898876404494382022471910112359550561797752808989 |
| Smoothed training home rate | 0.24761232205071179942234231063075865617977528089888 | 0.68836813757510797513332399648259730524279575158278 | 0.03304536781852876022471910112359550561797752808989 |

| Baseline | Mean paired Brier improvement | 95% paired-bootstrap interval |
|---|---:|---:|
| Constant 0.5 | 0.001751842104031719885378504954 | [-0.0024496680362020156717858296402501474719101123595505, 0.0059372367631287193643212803312277738764044943820225] |
| Smoothed training home rate | -0.0006358358452564806922791844174 | [-0.0048994793157810605449766702695056109550561797752809, 0.0035309777058708467688399581959112640449438202247191] |

The exact ten-bin Calibration tables and deterministic SHA-256-counter bootstrap
seed digests are preserved in `result.json`.

## Validation

Focused PR19B validation: 11 of 11 tests pass. They cover:

- complete market-independent population accounting and archive byte preservation;
- market-field/provenance rejection;
- eight-hour chronology equality and strict exclusion after the cutoff;
- same-season state and recent-ten tie handling;
- target-outcome separation;
- invalid, postponed, suspended, cancelled, schedule-revision, doubleheader, and
  conflicting-outcome visibility;
- training/validation isolation;
- input-order-independent model and metric behavior;
- deterministic bootstrap and exact classification boundaries; and
- refusal of a second sealed-test evaluation.

The implementation-time repository discovery ran 511 tests: 469 passed, 13
failed, and 29 errored. All 29 errors report unavailable dependencies in the
interpreter used for that original run
(`requests`, or `pandas` for the pipeline module). The 13 failures are downstream
commissioning/activation expectations whose code paths also cannot import
`requests`; they are not PR19B assertions. No package was installed or updated,
as required. This remains truthful implementation-time evidence rather than a
clean result from that interpreter.

The independent review subsequently located the existing repository environment
at `/Users/tom/pops-edge/venv`. Without installing or updating anything, it ran
the complete candidate suite: all 688 tests passed in 33.546 seconds. That clean
review run supersedes the earlier dependency limitation for release-readiness
evidence while preserving the original run in this report.

Python compilation and `git diff --check` also pass.

## Material limitations

- One partial 2026 season, not a multi-season population.
- Schedule/status/outcome material was mostly retrieved retrospectively.
- Prior outcomes use an eight-hour scheduled-start proxy, not proven historical
  publication time.
- Source rights remain uncertain for formal model training and distribution.
- The deliberately simple team-level model cannot establish prospective
  stationarity, market advantage, supplier replacement, or production fitness.
- Event-level bootstrap intervals do not resolve temporal dependence, missing
  population, rights uncertainty, or distribution shift.
- The original implementation interpreter was dependency-limited; the later
  independent-review run passed all 688 tests in the existing repository
  environment without installation.

These are accepted feasibility limitations. They do not convert NO BASIC SIGNAL
into another classification and do not authorize a second look.

## External and production state

The work fetched GitHub `main` read-only and read the validated local PR17C1
configuration and existing archive. Selected immutable source bytes matched
before and after derivation. Tests used temporary fixtures. The implementation
made no provider call, read no credential, installed no dependency, acquired no
data, repaired or mutated no archive, reconstructed no Evidence, and changed no
production behavior.

Only this local worktree, its local Derived Analysis output directory, and the
explicitly approved private preservation directory changed. The private copy is
not production Evidence or operational state. No remote repository or production
behavior changed.

## Next authorized gate

The independent scientific review accepted the candidate for the correctness,
reproducibility, and truthful reporting of the development-only NO BASIC SIGNAL
result. The immediate next gate is bounded amendment review of the private
preservation, exact ignore rule, report update, public-safe file boundary, and
fresh validation. Neither that review nor its acceptance authorizes branch
creation, commit, push, pull-request creation, merge, publication, data
acquisition, model admission, refitting, another test look, PR19C admission work,
prospective collection, activation, deployment, wagering, Policy, Governance,
or production behavior.
