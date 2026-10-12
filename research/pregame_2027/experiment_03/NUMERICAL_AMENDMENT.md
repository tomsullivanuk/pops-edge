# Proposed numerical amendment: normalize the same PA objective

Status: **for Tom's agreement; no restart authorized by this document**.
The [original run stopped](RESULTS.md) before validation/evaluation scores.

Propose divide **the entire penalized summed objective and its gradient** by
training PA count N. This leaves the minimizer and all relative penalties
mathematically unchanged: `(sum(NLL) + penalty)/N`. Do not divide just the data
loss while retaining an unscaled penalty, which would change the model.

Keep float64, analytic gradient, L-BFGS, zero initialization, max 1,000 iterations,
line-search bound 40 and relative-objective tolerance zero. Use normalized
gradient infinity tolerance 1e-9, require both optimizer success and gradient
at most 1e-9, and record normalized and equivalent summed values. This is a
changed numerical acceptance rule, not a retroactive pass of the original fit.
Validate it on the existing synthetic fixture before fitting.

Also append `.json`/`.npy` to artifact paths instead of replacing a suffix, so
decimal gamma and inner year remain in filenames. The exact reviewable patch is
[proposed_numerical.patch](proposed_numerical.patch). Preserve the original runner
commit, receipt and failed-fit archive; restart in a separate private fit directory.

All data, populations, inputs, baseline/challenger equations, 200-count history
shrinkage, fixed 100 player penalty, three gamma values, inner chronology, outer
seasons and continuation gate remain as frozen. No new variant, calibration,
evaluation population, additional source, cost or production change. No evaluation
scores have informed this proposal. The original five-day cap still applies.

If approved, apply this patch, record a separate amended pre-fit commit, rerun
synthetic checks, and execute the bounded comparison. Any new numerical failure
again stops visibly; do not change optimizers or tolerance automatically.
