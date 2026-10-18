# Experiment 02: frozen v2 learner comparison

October 12, 2026. Frozen before any new baseball-model fitting/scoring. Tom
authorized proceeding with TabPFN-v2 while the 3.5 personal-research inquiry is
pending. The parent confirmed isolated setup, synthetic capacity testing, then
the bounded comparison with the retained reference and boosting baseline. This
does not authorize 3.5, account creation, hosted API upload, paid compute, wagering,
production changes or merging PR #86.

## Hypothesis, data and fixed learners

Can one tabular foundation learner extract useful nonlinear interactions from the
existing ten-input game table? This is a learner comparison, not a new feature
family or confirmation that modern AI beats a sportsbook. All 2024–2026 seasons
remain reused development. Keep the failed strength-rating experiment intact.

One row per eligible game. Retain the reference's features, actual-starter
assumption, strict prior-New-York-calendar-day histories and shrinkage/fallbacks.
No target/future/same-day performance, team/game IDs, dates, market prices, lineups
or additional raw data enter any learner. IDs/dates are join/split metadata only.
The 38-file `input_manifest.json` pins the prior verified table/labels/reference
artifacts and original eligible sportsbook opening-consensus files. No previously
outcome-inspected 13-game exclusion is introduced. No new provider data acquisition.

Reference: original ten-input L2 logistic, annual expanding fits and training-only
StandardScaler. Reproduce saved annual probabilities within 1e-9 or stop. Preserve
the original input order and fit settings through the experiment 01 reference
loader; pin that script's digest in the execution receipt.

Foundation learner: **only** `tabpfn-v2-classifier-v2_default.ckpt` from official
`Prior-Labs/TabPFN-v2-clf`, revision `f851f2a3c941544733b712d8c0f96dfae9b28862`,
SHA256 `cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49`.
The exact Prior Labs v1.1 license was verified unchanged from previously reviewed
text (SHA256 `08b1851b4b6136b5fb0cb124d3258e0d91e3e1623f1be5904b77e4d270d112d8`).
Acquisition under the Owner's v2 approval needed no new account/credential.
No other checkpoint, fine-tuning or learned-model blend is allowed.

Built with PriorLabs-TabPFN. The standalone v2 license has Apache-derived terms
and additional attribution obligations; private weights/fitted contexts are not
redistributed. [License](https://huggingface.co/Prior-Labs/TabPFN-v2-clf/raw/main/LICENSE.txt).
The v2 [Nature paper](https://www.nature.com/articles/s41586-024-08328-6) describes
synthetic-task pretraining; the model card identifies the default as a base model,
including content-identical aliases labelled finetuned. This reduces the specific
memorized-game concern but is not our independent pretraining-corpus audit.
Prior benchmark selection and repeated local season use still limit inference.

## Verified local readiness

Isolated environment: Python 3.14.5, TabPFN 9.1.0 executing explicit **v2**,
PyTorch 2.14.1, CatBoost 1.2.10, NumPy 2.5.3, SciPy 1.18.1, sklearn 1.9.1;
full dependencies in `requirements.lock.txt`. Existing reference environment and
production dependencies are unchanged. Default v3.5 auto-selection is disabled;
pass the local checksum-verified checkpoint explicitly.

CPU and Metal synthetic 128-row tests passed. Metal 9,704 × 10 synthetic context
fit took about 27.8 seconds; 128-row prediction about 0.51 seconds; driver memory
after prediction about 2.24 GB. These are capacity findings, not measured baseball
timings or full peak GPU memory. Exact repeat predictions passed. Mutation of later
synthetic test features changed earlier probabilities by zero; batch-versus-isolated
maximum difference was 1.49e-7, within the fixed 1e-6 device tolerance. No baseball
data was accessed in these checks. Metal device access needed sandbox escalation;
model processes still disable network/DNS via audit hook and offline settings.

## Annual fits and bounded boosting control

Train 2022–2023/evaluate 2024 (4,852/2,426), train 2022–2024/evaluate 2025
(7,278/2,426), train 2022–2025/evaluate 2026 (9,704/2,428). No subsampling, random
game holdout, phase switches or later checkpoint update. Fit each annual learner
once on all its admitted training rows; no evaluation labels are passed to it.

TabPFN: four intrinsic preprocessing/ICL estimators using this one checkpoint;
random_state 20261012, float32 Metal, cached-context mode, one preprocessing job,
default v2 temperature 0.9, no class balancing or post-fit calibration. Use model-
native transforms fitted on the training context. Prediction batches contain at
most 128 test rows; cached train state and documented attention masks separate
test rows. Fixed 0.5 recommended-MPS-memory fraction, sequential estimator batching
(`TABPFN_MAX_BATCHED_ESTIMATOR_ROWS=0`), no CUDA/cloud. No estimator-count or
temperature tuning. Save predictions and fitted context privately for replay.

CatBoost: exactly eight combinations, depth {3,5}, l2_leaf_reg {3,10}, learning_rate
{0.03,0.08}; CPU four threads, maximum 1,000 iterations, Logloss objective/stopping
metric, early-stopping patience 50 on inner training-only validation, seed 20261012,
Bernoulli bootstrap subsample 0.8, random_strength 1, Plain boosting, no class weights.
No preprocessing fitted outside training. This bounded control is not an unlimited
optimized AutoML benchmark.

For each outer year Y, inner validation years are all 2023 through Y−1; train
each inner candidate on eligible seasons 2022 through the preceding inner year.
Pool inner losses by validation game count. Select lowest inner Brier, tie-break
by log loss then declared grid order. Final tree count is the validation-game-
weighted mean of that configuration's inner best iteration counts, rounded to
nearest integer and at least one. Refit that chosen configuration on the full
outer training set, with no outer eval_set or early stopping. Save every inner
configuration score/count and selection receipt. Outer 2024 results may enter
outer 2025 training because that season is earlier; they never select parameters
for their own outer fold. No tuning after outer results.

## Scoring, uncertainty and decision

One home-win probability per game; target y is 0/1. Require finite values strictly
inside (0,1); fail invalid values, never silently clip or remove a hard game.
Brier mean (p−y)^2 is primary; natural-log loss secondary. Report full-native
and original market-common populations separately, annual and pooled proper scores,
calibration intercept/slope and fixed ten-bin reliability diagnostics. Calibration
is not applied. Expected market-common counts: 2,291/2,425/2,428; total 7,144,
versus 7,280 full eligible outer games. Opening consensus is the intended historical
Kalshi proxy, not replaced by claims about potentially different Kalshi pricing.

For each new learner, continuation requires all original development conditions:
equal-weight average annual reference-minus-new Brier >=0.001, positive annual
Brier gain in at least two of three years, pooled full-native log loss no worse,
identical target coverage, and no new hindsight dependence. Report both learners'
gates without choosing the best after results. A pass earns research consideration,
not market superiority. Report v2-versus-boosting and all learner-versus-sportsbook
contrasts explicitly; if the proxy still wins, say so.

Paired uncertainty: 5,000 moving-calendar-block resamples, seed 20261012, 14-day
primary and 7-day sensitivity, percentile 95% bounds. For each comparison/population,
resample dates within each annual first/last target interval, include empty days,
truncate concatenated blocks to that calendar length, then compute sampled game-
weighted loss differences. Never cross annual boundaries. Primary three-season
gain averages annual differences equally per replicate. Market contrasts use only
their fixed common population. Bounds condition on chosen fits/selection and omit
training, model-selection and future-regime uncertainty; no significance hunting.

No paper entries, return simulation, alert threshold, trading action or selective
subset claim. A favorable historical result still needs frozen 2027 regular-season
confirmation and separate cost-aware policy validation.

## Validation, privacy and stopping

Verify source/checkpoint hashes; reproduce reference; keep feature/label joins exact;
save split metadata proving max training season <evaluation season and outer labels
absent from all fitting contexts. Recompute proper scores independently. Replay
CatBoost predictions from saved model; replay each v2 fold from pinned checkpoint,
context, seed and settings with maximum probability difference <=1e-6. Differences
from GPU arithmetic are reported, not mislabelled byte-identical fits. Verify
later-test-feature independence and unchanged reference full population.

Save fitted models/context, row-level predictions and input lineage privately;
publish code, protocol, configuration, aggregate results and verification only.
Public record carries attribution but no licensed raw data, weights, credentials,
personal correspondence or exact private machine profile. No model API calls.

Effort cap five focused working days. Per outer-fold model stage maximum 1,800
seconds; keep conservative memory limits. If a genuine runtime/rights requirement
changes, report it; do not increase memory caps, create credentials, accept 3.5
terms, buy compute, drop rows or silently switch models. Failure stops the named
learner branch; unaffected approved work may complete with a visible missing
comparison, never a replaced denominator. After prescribed results, stop tuning
regardless of the outcome and update draft PR #86 without merging it.
