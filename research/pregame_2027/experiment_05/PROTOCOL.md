# Experiment 05 / M16: frozen TabPFN-v3.5 core comparison

October 16, 2026. Owner explicitly authorized the bounded fixed-input research evaluation. Freeze this protocol, code, configuration, comparison/source pins and running register entry in a commit before baseball execution. Record that commit in the run receipt. No outer-year scoring was performed before this freeze. Independent preflight and final review are required before publishing conclusions. This is a new version campaign, distinct from experiment 02 / M14, whose predictions/results remain immutable.

## Access and scope

Tom personally reviewed and accepted the model license; official browser Licenses page subsequently showed TabPFN-3.5 Accepted. [Core acquisition and synthetic capacity](../v35_preparation/CAPACITY.md) verified the actual checksum and local viability. Official manual download required no credentials. This records acceptance, not a legal-status determination or commercial/production authority. No further terms acceptance, credential/grant creation, paid compute or upload is authorized. Do not use Thinking, Plus, Fast, experimental multiclass or hosted APIs. Payroll/WAR proposals remain separate and unexecuted.

Hypothesis: this pinned v3.5 core learner can obtain meaningful additional forecast accuracy from the same ten features. It does not test new information, current lineups, a score model or a selection policy. Prior results motivated this version comparison; all 2024–2026 seasons remain repeatedly reused development, not fresh holdouts. Synthetic-only pretraining is a vendor provenance claim, not an independently audited corpus or freedom from external benchmark selection.

## Fixed inputs, candidates and chronology

Reuse experiment 02's exact 38-file input manifest and experiment 01's hash-pinned loader/reference replay. Features in order: x_win60, x_rd60, x_rd10, progress_centered, progress_x_win60, progress_x_rd60, progress_x_rd10, starter_kbb, starter_hr, starter_ip. No IDs, dates, markets, payroll, WAR or additional player inputs enter the learner. Metadata are join/split only. Preserve original prior-New-York-calendar-day windows, fallbacks, resumed-target eligibility and historical actual-starter assumption. Training-only preprocessing/context; fit receives only earlier-season X/y. No outer labels for tuning, early stopping, calibration or estimator selection.

| Evaluate | Train seasons | Training games | Full evaluation | Market common |
| --- | --- | ---: | ---: | ---: |
| 2024 | 2022–2023 | 4,852 | 2,426 | 2,291 |
| 2025 | 2022–2024 | 7,278 | 2,426 | 2,425 |
| 2026 | 2022–2025 | 9,704 | 2,428 | 2,428 |

Total 7,280 paired targets and 7,144 original market-common games. No truncation, random split or additional exclusion. Retain original opening-consensus sportsbook proxy, including original 2024 cohort without the later 13-game exclusion. It is not an executable Kalshi or verified same-time quote comparison.

Primary comparator: original ten-input annual logistic (training-only StandardScaler, existing settings), replayed within 1e-9 against retained forecasts. Secondary: **saved** v2/CatBoost probabilities from experiment02/run-01, checksum pinned and joined by exact ID/date/year/label/market probability. Do not refit or retune those learners. Baseline proper scores must equal prior public experiment02 results exactly or stop. Frozen shared cohort prevents denominator changes from creating apparent improvement.

## Pinned learner and resource boundary

Official default core `Prior-Labs/tabpfn_3_5`, revision `06bf2ba35c80a92a3b9abb436b99cf49e7a0365e`, filename `tabpfn-v3.5-20260909.safetensors`, actual SHA-256 `ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3`, 876,027,932 bytes. One checkpoint, no search/fine-tuning/blending. [Settings](SETTINGS.json) are explicit: four intrinsic estimators, random_state20261012, float32 MPS, cached context, native temperature **1.0** (resolved in synthetic test, fixed here), no probability balancing, average probabilities after softmax, one preprocessing worker, memory-saving auto, batches≤128. Native training-context preprocessing only. V2's 0.9 temperature remains its original version-specific setting; the comparison is of the declared configurations, not an isolated architecture effect.

Existing isolated Python3.14.5, TabPFN9.1.0, torch2.14.1 and dependency lock retained. Both synthetic 128-row and largest9704×10 contexts passed at the same four-estimator configuration. Fixed 0.5 recommended-MPS-memory fraction, sequential estimator batching, four CPU threads, one interop thread and ≤1800 seconds per annual fit/prediction/save stage. Five focused working-day effort ceiling. Network/DNS blocked by Python audit hook during model use, offline settings, explicit existing local checkpoint; no automatic download/login. No telemetry/data transmission or paid compute. Stop on invalid inputs, changed pins, resource failure or unexplained parity failure. Preserve partial/failure receipts; do not alter caps, exclude games, change hardware/precision or try another configuration automatically.

## Measurement and continuation gate

Primary: equal-weight average of three annual reference-minus-v3.5 **Brier gains**, positive favors v3.5. Report every annual and pooled score, secondary natural-log loss, all secondary v2/CatBoost contrasts and original market-common scores. Diagnostic calibration intercept/slope and fixed ten-bin reliability are not applied to forecasts. Do not select years/phases after inspection.

All conditions required to continue: mean annual Brier gain≥0.001; positive Brier point gain in at least two years; pooled full-population log loss no worse than logistic; identical target coverage; no new hindsight dependence. These mirror experiment02; no threshold relaxation. Passing permits research consideration only, not deployment or profitability. Failure closes this tested configuration without automatic tuning. No separately invented v3.5-versus-v2 success rule. If sportsbook still wins, state it.

Paired moving-calendar-block bootstrap:5000 draws, seed20261012, 14-day primary and7-day sensitivity, percentile95% bounds. Same date draws for every contrast within a population/year; complete first/last target-day calendars include empty days, blocks never cross annual boundaries. Calendar-daily loss aggregation is inherited from experiment02; independently reconstruct all replicate results using per-game multiplicity weights. Conditional uncertainty does not cover repeated selection, training/model uncertainty or fresh-season variation.

## Verification and reporting

Before fitting: all38source hashes, retained-v2 prediction/provenance hashes, prior public protocol/results/loader/measurement pins, exact feature order, unique paired IDs and target labels; reference replay and chronological splits. Check source histories against stored lineage/canonical availability and recompute team inputs, preserving starter source hash/provenance. No new raw-feature builder claim unless actually rerun.

After fitting: finite probabilities strictly(0,1), persisted private fitted contexts, all annual saved-context predictions replay≤1e-6, first128outcome-blind later-test mutation and batch-isolation≤1e-6. No real-data feature perturbation changes parameters, no outer-label path into fit. Scalar Brier/log-loss, annual/pooled counts, all bootstrap replicates and gate independently reconstructed. Recheck original v2 hashes unchanged. Independent reviewer inspects exact code/source/output hashes, arithmetic/cohorts/intervals and conclusions without fitting another challenger.

Save raw/per-game predictions, fit contexts and weights privately. Publish permitted code, protocol/settings/pins, aggregate metrics, verification/review and failures to draft PR86 only after review. No merge, production/collector/pin/schedule/T−6h changes. Record M16 running before execution and completed with its actual outcome afterward; never add it to completed count until finished. No wagering or forecast-policy authority follows.
