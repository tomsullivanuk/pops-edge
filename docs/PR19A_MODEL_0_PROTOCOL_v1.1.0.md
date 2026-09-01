# PR19A Model 0 Methodology and Protocol

**Status:** precommitted specification; no dataset or model constructed\
**Protocol version:** `pr19a-model-0-v1`\
**Decision date:** 2026-09-01\
**Rights path:** independently implemented clean-room design\
**Rights record:** [PR19A Native Model Rights and Provenance Decision](PR19A_RIGHTS_DECISION_v1.1.0.md)

## 1. Purpose and authority

This protocol defines the smallest defensible offline path for deciding whether
one native MLB Model 0 is fit to enter prospective research. It fixes the
estimand, population, information boundary, feature set, model family,
calibration, chronological split, baselines, metrics, uncertainty, and pass/fail
rules before dataset construction or test access.

The protocol is subordinate to the
[Empirical Research Methodology](../EMPIRICAL_RESEARCH_METHODOLOGY.md),
[Product](PRODUCT.md), [Architecture](../ARCHITECTURE.md), and
[v1.1.0 Release Plan](RELEASE_PLAN_v1.1.0.md). Where this document is silent,
those authorities govern. A change to a precommitted value below requires a new
version approved before the untouched test period is evaluated.

## 2. Canonical estimand

For each eligible MLB regular-season game, Model 0 estimates:

> The probability that the canonical home team wins the game, including extra
> innings, conditional only on admissible information available strictly before
> the game's forecast boundary.

The canonical proposition is `home-team-win`. The outcome is `1` when
authoritative final Outcome Evidence records the canonical home team as winner
and `0` when it records the canonical away team as winner. A tie, no contest,
cancellation, unresolved result, conflicting final, or forfeit does not receive
a fabricated binary label. It remains visible in population reconciliation and
does not enter model fitting or scoring.

The estimand is a probability, not a pick, edge, expected value, recommended
wager, or market-relative conclusion.

## 3. Population and forecast opportunity

### 3.1 Fixed offline seasons

The protocol uses complete MLB regular seasons as follows:

| Split | Seasons | Permitted use |
|---|---|---|
| Training | 2021, 2022, 2023 | Feature scaling and primary-model fitting only |
| Validation | 2024 | Calibration fitting and pre-test mechanical validation only |
| Final test | 2025 | One protocol-defined admission evaluation after the model bundle is frozen |

Spring training, exhibitions, All-Star games, postseason games, and 2026 games
are excluded. The split may not roll forward to obtain a more favorable result.

### 3.2 Canonical game and boundary

Each game is identified by authoritative MLB `gamePk`, canonical home and away
team IDs, season, and complete schedule lineage. Doubleheader games are distinct
games and may enter when their `gamePk`, participants, game number, and schedule
lineage are unambiguous.

For an authoritative scheduled-start observation `T`, the forecast boundary is:

```text
B = T - 6 hours
```

The schedule observation establishing `T` must itself have been available
strictly before `B`. The game must be in a supported pregame scheduled state at
`B`, with complete home/away identity and no evidence at that boundary that it
is postponed, cancelled, already started, suspended, or a resumed continuation.

Every schedule revision creates visible lineage. If a later pre-start revision
changes `T`, the earlier opportunity remains auditable but cannot silently
become the training row. A revised opportunity is eligible only if the revision
was available strictly before its own revised `B`. A late revision for which
T-6h has already passed produces no retrospective feature snapshot. Exactly one
unambiguous eligible opportunity may represent a `gamePk`; zero remains a
visible exclusion and more than one fails closed.

A postponement never permits features from the original boundary to be
relabeled as if observed at a later boundary. A rescheduled game needs its own
valid schedule-derived opportunity. A game that is later delayed after a valid
boundary retains that truthful boundary; its feature snapshot is not updated.

### 3.3 Population accounting

Replay begins with the complete authoritative schedule/status universe for each
fixed season. It derives, rather than accepts from a caller:

1. all schedule-derived candidate opportunities;
2. the eligible binary-outcome denominator;
3. valid feature snapshots;
4. missing, invalid, late, ambiguous, or unsupported dispositions; and
5. the measured population.

No unavailable row may be dropped from Coverage, and no row may be added
because the eventual Outcome or model prediction is convenient.

## 4. End-to-end market-independence boundary

No sportsbook, exchange, Kalshi, betting line, odds, implied probability,
consensus forecast, pick, payout, volume, liquidity, spread, moneyline, market
movement, closing line, bookmaker identity, market-derived ranking, or
market-informed external model value may enter or influence:

- source admission for native features;
- labels or population eligibility;
- feature definitions, values, transformations, or missingness treatment;
- exploratory feature or model selection;
- training, validation, or test matrices;
- scaling, regularization, fitting, or calibration;
- hyperparameters, thresholds, retraining, or rejection decisions; or
- offline or prospective inference.

Market-derived columns must not merely be ignored at fit time; they must be
absent from the native dataset namespace and its transitive inputs. Automated
field-name and provenance-class scans are necessary but not sufficient: source
contracts must affirm that each admitted value is non-market-derived.

Kalshi Evidence may later be joined only after an admitted Model 0 is frozen
and prospectively emits Forecast Observation Evidence under separately
authorized PR19D authority. It cannot affect Model 0 retrospectively.

## 5. Point-in-time information contract

### 5.1 Required source chronology

Every atomic source observation capable of affecting a feature must preserve:

- source and product identity;
- source-native record and event identity;
- source event/effective time when supplied;
- the earliest defensible `source_available_at` for that exact version;
- Pops' Edge `ingested_at` or collection time;
- raw reference and digest permitted by the source rights;
- schema/adapter version;
- validation status and limitations; and
- correction or supersession lineage.

`source_available_at` may come only from a source-supplied timestamp or an
audited publication/delivery rule. It may not be guessed from a game date,
current aggregate, file modification time, later retrieval time, or knowledge
that a fact was probably public. `ingested_at` remains distinct. A historical
archive retrieved later may support point-in-time use only when its source
authority proves when each exact version was available.

### 5.2 Admissibility at a forecast boundary

An input version is feature-eligible only when all of the following hold:

```text
source_available_at < B
source event/effective chronology is compatible with B
identity and correction lineage resolve uniquely as of B
validation is authoritative for the intended fact
source rights permit the intended use and retention
```

Strict inequality applies. A timestamp equal to `B` is late. Unknown,
date-only, local-time-without-zone, ambiguous, conflicting, or inferred
availability is late/invalid rather than silently normalized.

### 5.3 Corrections and late data

Corrections are append-only. Replay at `B` selects the latest unique valid
version whose own availability precedes `B`. A later correction may affect
features for later games but never rewrites a prior feature snapshot. Branched,
cyclic, conflicting, or equal-time correction authority fails closed without
input ordering as a tie-breaker.

A late record remains visible but contributes no value to that boundary.
Historical retrieval cannot repair missing prospective information-time
authority.

### 5.4 Labels

The target game's final Outcome necessarily occurs after `B`. Labels therefore
live in a physically and logically separate outcome path. Feature construction
must complete and be content-addressed before the target Outcome is joined.
Only authoritative decisive final Outcome Evidence may create the binary label.

### 5.5 Team and player identity

Team identity uses the authoritative stable IDs mapped through existing MLB
contracts; names, abbreviations, dates, or incidental row order never establish
identity. Franchise-name changes do not create a new team when authoritative
identity is continuous.

Model 0 has **no player, pitcher, lineup, injury, park, umpire, or weather
feature**. Any such source material remains outside the matrix. If a later
model proposes player-derived information, authoritative player identity,
observation state, point-in-time availability, missingness, and correction
rules require a new protocol version before final-test access.

## 6. Precommitted Model 0 features

Only authoritative decisive regular-season games from the same season whose
final Outcome was available strictly before the target `B` may update team
state. For a team and target boundary, define:

```text
season_games       = prior qualifying games in that season
season_wins        = wins among season_games
season_run_diff    = runs_for - runs_against across season_games
recent_games       = latest at most 10 season_games, ordered by scheduled_start
recent_wins        = wins among recent_games

season_win_rate    = (season_wins + 1) / (count(season_games) + 2)
season_run_rate    = season_run_diff / (count(season_games) + 10)
recent_win_rate    = (recent_wins + 1) / (count(recent_games) + 2)
```

If two qualifying games for the same team have the same authoritative
`scheduled_start` and that tie straddles the 10-game cutoff, the target feature
snapshot is invalid. Input order or `gamePk` must not choose the recent set.

For the canonical home and away teams, Model 0 uses exactly three numeric
features:

1. `season_win_rate_home - season_win_rate_away`;
2. `season_run_rate_home - season_run_rate_away`; and
3. `recent_win_rate_home - recent_win_rate_away`.

The additive constants are fixed shrinkage rules, not fitted hyperparameters.
They define valid neutral values at the start of a season. There is no missing
value imputation: if the authoritative schedule/outcome history required to
construct team state is incomplete or ambiguous, the target snapshot is
invalid and remains visible in Coverage.

No other feature, interaction, transformed target, prior-season value, or
feature selection is permitted in protocol version 1.

## 7. Primary model and preprocessing

The primary model is one binary logistic regression:

```text
logit(p_raw) = beta_0
             + beta_1 * standardized_season_win_difference
             + beta_2 * standardized_season_run_difference
             + beta_3 * standardized_recent_win_difference
```

Feature means and population standard deviations are fitted on the 2021–2023
training split only. A zero training standard deviation uses scale `1` and the
feature remains present. The estimator uses L2 regularization with fixed
inverse strength `C = 1`, an intercept, no class weights, and no hyperparameter
search. The implementation must pin the exact solver, tolerance, iteration
limit, numeric representation, dependency versions, and deterministic settings
before fitting. Failure to converge is rejection, not permission to change the
model.

The primary estimator is fitted once on training data. It is not refitted on
validation or test data.

## 8. Calibration

After the primary estimator is frozen, one sigmoid calibrator is fitted on the
2024 validation split only:

```text
logit(p_calibrated) = alpha + gamma * logit(p_raw)
```

The two-parameter calibrator uses no penalty and no market information. It may
not choose bins, features, or transformations. Failure to fit a finite unique
solution rejects Model 0. The calibrated output must satisfy
`0 < p_calibrated < 1`; rounding to exactly `0` or `1` is invalid.

The estimator, scaler, and calibrator together are Model 0. Their identities
and digests are inseparable in any later bundle or Forecast Observation.

## 9. Baselines

Two baselines are fixed before validation or test evaluation:

1. **Even probability:** `p = 0.5` for every game.
2. **Training home rate:** one constant probability
   `(training_home_wins + 1) / (training_games + 2)`, computed only from the
   2021–2023 training labels and used unchanged for validation and test.

No market, external forecast, Elo system, tuned heuristic, or post-result
baseline may be added to protocol version 1. Model 0 must pass against both
baselines; the more favorable comparison cannot be selected after seeing the
test result.

## 10. Evaluation metrics

The primary metric is mean Brier Score on the untouched 2025 test population.
For each game with home-win outcome `y` and probability `p`:

```text
Brier = (p - y)^2
```

The protocol also reports:

- mean extended-real Log Loss without replacing exact `0` or `1` outputs;
- the existing canonical ten bins `[0.0,0.1)`, ..., `[0.9,1.0]`;
- mean predicted probability, observed home-win frequency, and calibration gap
  in each populated bin;
- weighted absolute calibration error (WACE) using the existing Methodology;
- schedule universe, eligible denominator, valid snapshot count, measured
  count, and every visible exclusion category; and
- the same descriptive metrics for both baselines.

Accuracy, ROC-AUC, return, profit, Kelly sizing, odds-relative performance, and
market comparison have no admission authority.

## 11. Uncertainty

For each baseline, calculate per-game paired Brier improvement:

```text
baseline_brier - model_0_brier
```

Use the existing deterministic event-level paired-bootstrap semantics with
`10,000` resamples and a two-sided `95%` percentile interval. The seed commits
to the protocol version, dataset digest, test Measurement IDs, model-bundle
digest, baseline identity, confidence level, resample count, and algorithm
version. Input ordering, wall-clock randomness, filesystem state, and ambient
numeric context must be immaterial.

The interval represents empirical event-sampling uncertainty only. It does not
resolve temporal dependence, source-rights uncertainty, missing population,
distribution shift, or future prospective performance; those remain explicit
limitations.

## 12. PR19B entry and exit gates

### 12.1 Entry gate

PR19B may begin dataset construction only when every item passes:

1. The Product Owner has authorized PR19B implementation and the contemplated
   local historical data access or import.
2. Each source has a pinned rights record covering automated or delivered
   access, 2021–2025 historical use, local retention, model training, derived
   reproducibility artifacts, audit, and any attribution/redistribution duty.
3. The source contract can provide the complete schedule/status/outcome
   universe plus defensible historical availability and correction authority.
4. Raw licensed material can be preserved or referenced with immutable digests
   without violating source terms.
5. The source is non-market-derived for every native input.
6. No third-party clean-room prohibition in the rights decision is weakened.

An unknown or conditional answer is a fail. As of PR19A, this entry gate
**fails** because no admitted source satisfies items 1–4.

### 12.2 Exit gate

PR19B passes to PR19C only when all of the following are demonstrated without
fitting a model:

1. Every schedule-derived opportunity for 2021–2025 reconciles into exactly one
   visible disposition; included rows have unique game, team, schedule, status,
   boundary, feature, and outcome authority.
2. At least `95%` of decisive eligible games in each split have valid feature
   snapshots, and at least `90%` of each franchise-season's decisive eligible
   games are represented. The denominator is source/schedule-derived, not
   caller-authored.
3. Training has at least `6,000` measured games, validation at least `2,000`,
   and final test at least `2,000`. Counts below a threshold fail; seasons are
   not changed to compensate.
4. Every feature is exactly one of the three precommitted features and every
   transitive observation passes the strict `< B` availability rule.
5. Outcome material is excluded from feature construction and joined only
   after content-addressed snapshots exist.
6. Market-derived fields and provenance classes are absent from every native
   dataset layer; an allowlist and a prohibited-term/provenance scan both pass.
7. Missing, late, invalid, corrected, postponed, rescheduled, doubleheader, and
   ambiguous cases pass fixture-backed leakage and population tests.
8. Rebuilding from identical admitted observations reproduces byte-identical
   canonical row content, split membership, Coverage, and dataset manifests,
   independent of input order.
9. The final-test row/label digest is sealed before any model fitting and no
   test aggregate, label distribution, feature summary, or model score has been
   inspected for model or threshold decisions.
10. The manifest pins source, schema, chronology, identity, feature, split,
    dataset-builder, dependency, and source-code versions and records all
    rights references and material limitations.

Any failed item rejects the dataset for PR19C. Visible exclusions are honest
Coverage; they are not permission to relax a threshold after inspection.

## 13. PR19C construction and admission gates

### 13.1 Before final-test access

PR19C must freeze and content-address:

- the accepted PR19B dataset and split manifest;
- the exact three-feature schema and formulas;
- scaler parameters fitted only on training;
- fitted logistic-regression coefficients and solver report;
- fitted 2024 sigmoid calibrator;
- dependency and source-code identities;
- serialization and inference algorithms;
- both baseline identities and probabilities;
- metric, calibration, bootstrap, and threshold versions; and
- a single evaluation command that cannot retrain or alter the bundle.

Validation may reveal a mechanical failure, such as non-convergence or invalid
probabilities. It may not authorize feature, model, calibration, threshold, or
split changes inside this protocol. A material change requires a new protocol
version before test access.

### 13.2 Offline admission

On the first protocol-authorized test evaluation, Model 0 is admitted only if
every condition passes:

1. All PR19B gates and pre-test bundle checks still pass.
2. Every test probability is finite and strictly between `0` and `1`.
3. Identical admitted inputs reproduce byte-identical probabilities,
   per-game Measurements, aggregate metrics, uncertainty, and admission result.
4. Against **each** baseline, mean paired Brier improvement is at least
   `0.002` and the deterministic `95%` paired-bootstrap lower bound is strictly
   greater than `0`.
5. Mean test Log Loss is no greater than the Log Loss of **each** baseline.
6. Model 0 test WACE is no greater than `0.03` under the fixed ten-bin rule.
7. Test population and per-franchise Coverage still satisfy the PR19B
   thresholds, with all failures and exclusions visible.
8. Rights, clean-room, market-independence, chronology, and test-seal audits
   contain no unresolved exception.

There is no rounded-score tolerance and no secondary override. Equality fails
conditions that say "strictly greater" and passes conditions that say "at
least" or "no greater."

If any condition fails, Model 0 is rejected. PR19 may close truthfully with no
admitted model. The result may inform a future, separately approved protocol,
but it may not trigger same-protocol tuning or a second look at the 2025 test
period.

## 14. Deterministic identity and replay

The dataset manifest and later model bundle must make all material identity
explicit, including:

- protocol and rights-decision versions;
- source, source terms, raw references, schema, and adapter versions;
- canonical game/team mappings and schedule/correction lineage;
- feature formulas, ordering, numeric precision, and snapshot digests;
- training cutoff and exact split membership;
- scaler, estimator, calibrator, solver, and dependency identities;
- source-code revision and build environment relevant to numeric results;
- baseline, metric, calibration-bin, bootstrap, and admission-rule versions;
  and
- canonical serialization and artifact digests.

Replay must start from admitted source observations and reconstruct derived
state upstream-first. A stored matrix, model binary, or report is not sufficient
authority by itself. Unknown, duplicated, foreign, conflicting, or multiple
compatible-looking authorities fail closed.

## 15. Accepted limitations

- One MLB regular-season home-team game-winner model only.
- Deliberately modest team-level feature set with no player or contextual
  features.
- Fixed 2021–2025 offline seasons and a single untouched final test.
- Simple logistic model and sigmoid calibration; no claim of optimality.
- Event-level bootstrap does not model every temporal or team dependence.
- Bounded local-Mac self-hosting, manual intervention, visible missed
  forecasts, and no automatic recovery if later authorized.
- No retraining during one prospective Protocol.
- A passing offline gate does not establish prospective superiority, a Market
  Edge, profitability, or operational trust.

## 16. Exclusions and non-authority

This protocol authorizes none of the following:

- third-party code, model, data, or artifact copying, modification, or
  execution;
- data collection, source contact, purchase, subscription, or credential use;
- dataset or model construction under PR19A;
- totals, run lines, player props, postseason, or other sports;
- player/pitcher, lineup, injury, weather, park, umpire, or market features;
- ensemble, broad hyperparameter search, automatic weighting, online learning,
  scheduled retraining, or result-directed protocol changes;
- retrospective repair of missing prospective Evidence;
- cloud hosting, high availability, or generalized recovery infrastructure;
- PR19D activation or prospective collection;
- wagering, trading, Opportunity Analysis, Policy, Governance, or production
  authority; or
- a claim that Model 0 outperforms Kalshi or any other Probability Source.

An offline pass makes one pinned bundle eligible for a separate Product Owner
decision about PR19D. It does not make that decision.
