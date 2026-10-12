# Next model proposal: predict the score pair, then the winner

October 12, 2026. **Read-only assessment and discussion proposal; no experiment
or implementation authorized.** The previous strength-rating challenger failed
its gate and stays unpromoted. The sportsbook opening consensus remains the
agreed historical proxy for Kalshi. Changing benchmark venue is not an answer
to the model's performance deficit, and there is no evidence it would rescue it.
Opening-versus-decision-time uncertainty remains a qualification, not an escape
from the stronger benchmark.

## Recommendation

If Tom wants another model experiment, propose **one probabilistic final-score
model**, trained on both teams' run counts, then converted to a winner probability.
This changes the learning target and preserves both sides' scoring context,
rather than adding a few columns to another winner logistic. Existing archives
support a bounded initial version without buying data. It is a credible research
hypothesis, not an evidence-supported improvement or a promise to beat the proxy.

Do not implement yet. First discuss whether this larger change is worth one
bounded test; then freeze its equations, source reconciliation, fitting controls
and evaluation before execution. Matched quote collection stays separate background
validation work, with no new live collector or paper alert implementation here.

## What the actual failures establish

| Read evidence | What was tested | What it does and does not tell us |
|---|---|---|
| Native starter / 2026 evaluation | Ten-input winner logistic with rolling team differences and three starter differences | Strongest retained native comparison loses to sportsbook opening consensus; chronology/arithmetic are credible, but predictive sufficiency is unestablished |
| Offense/prevention protocol and report | Four additional logistic dimensions allowing separate weights on unadjusted 60/10-game runs scored/allowed | 2024 Brier worsened 0.000469; this is not a run-count likelihood or score-distribution model |
| Actual-nine protocol, report and 2025 comparison | Equal-weight average of nine lagged OBP/ISO/hand ratings, replacing recent-usage proxy; batting order retained only as provenance | Small 2024 gain failed to generalize in 2025. Do not repeat this aggregate substitution or assume merely knowing nine names improves accuracy |
| Bullpen protocol/report | Team relief K−BB/HR and recent pitch-count proxies added to winner logistic | Tiny uncertain gain; not individual available-reliever inference or a full innings model |
| Diagnostic and calibration records | Starter/lineup/opponent group deletions, recalibration, regularization, GAM and market overlay | Starter information showed the clearest 2024 incremental contribution; more flexible fits and calibration did not establish market improvement |
| Experiment 01 | One opponent-adjusted, recency-weighted team run-difference rating substituted into winner logistic | Average annual Brier gain 0.000334 <0.001; improved 2025/2026, worsened 2024. Do not retune the rating or promote its best-year result |

These failures reject the tested specifications. They do not establish that
offense, starters, lineups or relievers carry no signal. Most retained experiments
compress game context into a few home-minus-away summaries and fit a binary winner
label. That structural observation follows from inspected code/protocols; the
claim that it causes the market deficit remains a hypothesis.

There is also a genuine data-quality/representation limitation: pitching audit
records same-name multiple provider IDs, invalid count rows and thin histories;
the batting audit records missing counts and no measured batter-versus-hand splits.
These can weaken ratings but have not been shown to cause the loss gap. Do not
merge namesakes automatically or buy a new feed before identifying a needed field.

## Why a score model is materially different

A binary winner label says who won but discards the margin and scoring environment.
A score-pair likelihood learns from the two final run counts. Retaining absolute
offensive/prevention levels permits low- and high-scoring games to have different
uncertainty even when their team-strength differences are similar. For example,
the same one-run expected advantage need not translate into the same winner
probability under different score distributions.

This could improve use of the existing counts; it could equally spend capacity
predicting score noise irrelevant to winners. Run-count likelihood improvement
alone would not qualify the model. Winner probabilities must still beat the
historical sportsbook proxy on paired proper scores.

## One proposed model family, not a search

Use a joint model for the **official final home/away run totals**, with two
negative-binomial marginals, shared learned dispersion and separate predicted
means. Condition the joint distribution on unequal scores because completed
binary MLB targets have a winner. For unequal observed scores:

`P(Rh=rh, Ra=ra | Rh != Ra) = NB(rh; mu_h,k) * NB(ra; mu_a,k) / (1 - P(tie))`.

Then `p_home = P(Rh > Ra) / (1 - P(tie))`, with tie probability and the score-tail
sum computed from the fitted marginals. This is a distribution of **final scores**,
not a nine-inning simulation; no unobserved nine-inning ties are treated as known.
Fit the conditional score-pair likelihood itself, not an unconditioned count model
whose generated ties are silently discarded only at prediction time. Independent
marginals before conditioning are a simplifying assumption; shared game conditions
and game-ending rules can violate it. Record that risk rather than implying a
mechanistically exact baseball simulator.

For each team's log mean, use its own lagged 60/10-game shrunk runs-scored rates,
the opponent's lagged 60/10-game runs-allowed rates, opposing starter K−BB and
HR deviations weighted by expected innings, and opposing expected starter innings.
Use the previously defined histories/shrinkage and training-only standardization;
both team sides retain their levels instead of collapsing to differences. Retain
centered season progress and designated-home intercept structure. Share feature
coefficients across home/away sides with a separate home effect. No market inputs.

This intentionally does not add lineup replacement, bullpen availability, new
park/weather features or a parameter sweep. It tests the target/distribution and
absolute scoring representation together; it cannot attribute gains separately
to those two changes. Regularization, parameter constraints, numerical tail bound,
convergence checks and any cold-start policy must be fixed before results, not
optimized after inspecting 2024–2026. The detailed protocol is not yet written.

## Existing-data feasibility and preconditions

Canonical outcomes provide verified team identities, final scores and completion
days from 2021 warm-up through September 27, 2026. Original offense/prevention
work reconstructed runs-scored/allowed from the exact rolling windows. Retained
starter lineage supplies each side's lagged league deviations and expected
innings before the existing home-minus-away calculation. These are the initial
model inputs; no pitch-by-pitch or new vendor archive is necessary to define them.

Before fitting, verify complete side-level starter lineage for every annual target
and compatibility across retained extensions. Quantify flagged provider-ID
fragmentation and missing/invalid history in the actual required joins. Correct
only demonstrably identical IDs using retained identity evidence, with explicit
provenance, or retain the original declared fallback and disclose it. If repairing
the bridge changes reference features, that repair needs an explicit separate
decision; do not hide it inside this model comparison. No target is removed simply
because its pitcher history is inconvenient.

Use strict prior-New-York-calendar-day histories and completion/resumption policy.
Target final run totals are labels **only**, never predictors; target/future/same-day
counts must fail mutation-independence tests. Keep the assumed actual-starter
identity limitation for offline development. No retrospective announcement time
is asserted. Official target winner is reconstructed solely for scoring, never
used as a run-rate input or calibration target in evaluation years.

We have not yet verified the complete input join for this new fit, implemented
the score likelihood, or measured its numerical runtime. A bounded pre-fit
readiness pass may reveal missing lineage or an unstable likelihood and should
stop with that finding rather than launch another family. No required additional
data purchase has been demonstrated at this point.

## Proposed evaluation and continuation discussion

Use chronological train-through-2023/evaluate-2024, through-2024/evaluate-2025,
and through-2025/evaluate-2026 fits. Within evaluation seasons, only previously
completed games update features; fitted parameters remain annual. All three
seasons remain reused development. No random game splits or restored-holdout claim.

Primary comparative question: converted home-win probabilities versus **the
retained sportsbook opening consensus** on identical eligible games each year.
Retain original quote eligibility and full coverage accounting; do not adopt the
previous outcome-inspected 13-game exclusion list as a new default. Report the
unchanged native reference and new score model on both the full native population
and the exact market intersection. The benchmark missingness cannot be repaired
with inferred Kalshi quotes.

Report annual/pooled Brier and log loss, paired calendar-block uncertainty,
calibration, source/fallback coverage and run-distribution diagnostics. Do not
select a phase, team, best year or alert policy from these results. Scores of run
means or likelihood are diagnostic, not substitutes for winner probability scores.

For discussion, require improvement against the market proxy itself, not merely
against our weaker reference, with no worse log loss, stable coverage and gains
that are not isolated to one season. Before authorization, agree the practical
effect threshold and effort cap and freeze the numerical protocol. The preceding
0.001-over-native gate does not silently become this new experiment's gate.
Even favorable reused-season results only justify fresh regular-season validation,
not demonstrated superiority or wagering authority. Failure ends this family
without automatically adding features or changing dispersion models.

## Evidence and decision boundary

Read original private `native_offense_prevention_2026-09-29/{PROTOCOL.md,RESULTS_REPORT.md}`,
`native_batting_unit_2026-09-29/{PROTOCOL.md,RESULTS_REPORT.md}`,
`native_actual_lineup_2026-09-29/{PROTOCOL.md,RESULTS_REPORT.md}`,
`native_bullpen_2026-09-28/{PROTOCOL.md,RESULTS_REPORT.md}`,
`native_diagnostics_2026-09-29/{PROTOCOL.md,RESULTS_REPORT.md}`,
2025 batting-audit code and 2026 pitching audit, alongside the independent
review/addendum and experiment 01. Those sources control the historical claims;
this proposal has no new fitted-model results. Raw licensed inputs remain private.

Next discussion: is this one score-model family worth a bounded development
test, given the greater modeling work and uncertain benefit? If so, write the
pre-fit protocol and concrete execution scope for Tom to approve. No experiment,
code implementation, provider acquisition, new credentials, T−6h change, paper
collector or policy is authorized by this assessment. PR #86 remains draft.
