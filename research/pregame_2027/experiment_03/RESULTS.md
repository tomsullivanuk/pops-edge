# Experiment 03 complete: small component gain, continuation gate failed

October 12, 2026. **Do not promote or integrate this challenger automatically.**
Tom approved the experiment and both numerical amendments. The final pre-fit freeze is `71aadb0`. All sixteen fits passed; earlier stops remain in [numerical history](NUMERICAL_HISTORY.md).

The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.

## Primary comparison

Conditional three-class PA prediction against initial starters, excluding intentional walks identically. Lower log loss and multiclass Brier are better. These are reused development seasons, not untouched holdouts or game-win targets.

| Season | Starter PA | Baseline log loss | Challenger log loss | Relative reduction |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 106,845 | 0.759468030 | 0.758812781 | 0.086277% |
| 2025 | 106,429 | 0.760425012 | 0.759635649 | 0.103805% |

| Season | Baseline multiclass Brier | Challenger multiclass Brier |
| --- | ---: | ---: |
| 2024 | 0.440725151 | 0.440406684 |
| 2025 | 0.440743290 | 0.440433716 |

Equal-average annual relative log-loss reduction is **0.095041%**, versus the agreed **0.5%** requirement. Its paired 14-day 95% interval is **[0.077841%, 0.113720%]**; 7-day sensitivity is **[0.077313%, 0.113910%]**. Both years improve and Brier is lower, but the practical-size gate fails. An interval above zero does not override that gate. This is a small conditional component gain, not a probability-point winner advantage, economic return, selection-adjusted discovery or market edge.

Equal-game log loss also improves: 0.763215 to 0.762539 in 2024 and 0.763918 to 0.763172 in 2025. Neither a different weighting nor the initial-batter/all-role diagnostics rescues the failed primary gate. [Full diagnostic results](results.json) remain visible. League-only log loss is substantially worse (0.775166 / 0.777104), supporting the stronger continuation comparator.

## Data, fits and calibration

Regular-season source audits covered 182,052 / 184,104 / 182,449 / 182,926 PA in 2022–2025. The fixed intentional-walk rule leaves 729,517 feature/label rows. Known zero-exposure starters and early batter substitutions are reconciled and preserved, without outcome-driven game removal. Actual matchup occurrence is outside this conditional task.

Both models select gamma=10 from the three-value training-only grid in both outer years. Final training populations are 365,207 and 547,147 all-role PA. The challenger keeps the fixed 100 individual-effect penalty; no pair table, new feature or calibration was applied. Sixteen fits took 55.3 CPU fit seconds total, excluding parsing, predictions and verification. Whole-objective rescaling includes penalties, preserving mathematical minimizers. No paid compute or model API.

Class calibration remains imperfect. Challenger mean K probabilities are 22.34% / 22.31%, versus observed 21.98% / 21.84%; mean BB probabilities are 7.84% / 7.87%, versus observed 7.55% / 7.72%. [Class reliability bins](calibration.json) are diagnostic only. No calibrator was fitted or player-level certainty inferred.

## Verification and limitations

- All 213,274 primary PA use identical paired populations. Saved coefficients replay every annual all-role forecast exactly (maximum difference zero).
- Separate scalar log-loss arithmetic agrees for all three populations/models/years; independent scalar Brier agrees on primary starter PA.
- All 5,000 paired bootstrap replicates were rebuilt with block-multiplicity weights; interval endpoints agree within 2.19e-16.
- Later test-row changes leave earlier predictions unchanged. Unseen IDs have zero residual columns and valid categorical probabilities.
- Direct history/future-mutation and synthetic gradient checks pass; every fit meets normalized gradient infinity <=1e-8.

[Fit/replay verification](verification.json), [additional checks](extra_verification.json), [selection](selection.json), [runner](run.py), [measurement](measure.py) and [verification code](verify_extra.py) support these claims. These are same-assistant checks, not external review or a full independent fit rerun. Raw data, per-PA predictions and fitted contexts remain private outside Git.

No full-game simulation, sportsbook/Kalshi comparison or economic evaluation occurred. These categories omit contact severity, baserunning, starter duration and reliever selection. Even a passed component gate would not establish winner improvement; this one fails its agreed gate.

## Decision

Close this tested specification without promotion, automatic retuning, weaker thresholds or new families. Preserve the small improvement as conditional matchup evidence of insufficient measured size under the agreed rule. Any further work requires a distinct hypothesis and discussion; no game-level integration follows. Draft PR #86 stays unmerged; production collectors/pins/schedules and T−6h studies remain untouched.
