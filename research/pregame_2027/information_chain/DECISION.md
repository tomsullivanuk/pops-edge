# Information-chain diagnostic: valid comparison, inconclusive advantage

**Recommendation: stop this path here. Do not fit a fifth model or rewrite the
winner translation on the strength of this diagnostic.** Tom approved one focused
session, with calculation frozen at `b87d364` before comparative losses were
observed. No learner, calibration, tuning, acquisition or market-residual test ran.
All experiment 04 information/market gates remain failed.

## Did Steamer predict the batting events better?

Not consistently across the two years. We scored the same saved initial-nine
player forecasts against actual eligible opportunities, using precisely the
2013 event values and denominator from experiment 04. Lower squared error is
better; positive gain favors Steamer. This is **mean event-value squared error,
not winner Brier or a categorical-probability score**.

| Year | Eligible opportunities | Own-rate MSE | Steamer MSE | Own minus Steamer |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 174,413 | 0.270720527 | 0.270733015 | −0.000012487 |
| 2025 | 174,612 | 0.273597563 | 0.273444527 | +0.000153035 |
| Equal-year average | 349,025 total | 0.272159045 | 0.272088771 | +0.000070274 |

The primary equal-year 14-day 95% interval is **[−0.000049266,+0.000172273]**;
seven-day sensitivity is [−0.000032053,+0.000159846]. Both include zero.
2025's individual 14-day interval is just above zero, but 2024's spans zero and
its point estimate is slightly unfavorable. Do not select the favorable year.
These are conditional reused-development diagnostics, not fresh confirmation.

## Was information lost in aggregation or ignored by the winner model?

The hitter-game mean comparison is similarly uncertain: equal-year MSE gain
+0.000026090, 14-day interval [−0.000097683,+0.000132734].

The predeclared complete-nine **side-level** weighted comparison is worse for
Steamer in both years: gains −0.000237554 and −0.000101009; equal-year interval
[−0.000223975,−0.000127079]. This does not prove aggregation destroyed useful
signal. It measures absolute side-level weighted means on a conditional subset;
the game model uses a **home-minus-away difference**. Common level errors can
cancel there, and changing exposure/noise weighting changes the question. We
did not add a post-result differential score or calibrate away that difference.

The saved models clearly respond. Mean absolute winner-probability changes are
**2.228 percentage points in 2024 and 2.231 in 2025**. The fixed-control-coefficient
data contribution averages 0.0711 / 0.0776 absolute log-odds; the coefficient/refit
contribution averages 0.0317 / 0.0253. These absolute magnitudes need not add to
the total because contributions can offset. Every eighteen-player lineup sum,
raw-unit coefficient/intercept decomposition and saved probability replays within
floating-point precision. This refutes “the input never reached the forecast,”
but does not prove the fitted response is optimal or causally explain win losses.

## Definition, coverage and verification

Comparability accepted within scope. Numerator and opportunity denominator agree
with experiment 04. We scored only completed PA by the initial-nine identities
with denominator one. Explicitly unscored initial-nine PA: 985 in 2024 and 1,118
in 2025, comprising IBB, sacrifice bunts and interference. They are not ordinary
zero-valued outcomes. Substitute PA are excluded by identity (6,843 / 6,898);
no actual mean is invented for zero-opportunity initial hitters (12 / 19).
All 4,852 games remain in the saved winner trace.

Hitter-game coverage is 43,656 / 43,649. Complete-nine side coverage is 4,840 /
4,834, with 12 / 18 incomplete sides visible. The fixed missing-projection
control fallback is retained exactly. Raw source hashes match experiment 04.
The earlier lineup-availability and historical archive-release/revision
limitations remain; no claim of live pregame forecast capture follows.

Independent checks rebuilt all 349,025 actual values from raw event categories,
reconciled 87,305 hitter totals and scalar scores, and verified every saved model
trace. Maximum scalar score difference is 1.74e-18; maximum logit trace difference
4.45e-16. All 5,000 paired calendar-block draws for all three populations, with
14/7-day blocks, were rebuilt using multiplicity weights; endpoints agree within
1.35e-16. This is same-assistant separate verification, not external review.

## What the evidence justifies

There is no established stable upstream batting advantage to explain away as
failed winner translation. Nor do we prove Steamer lacks useful information:
2025 shows a small event-level gain, while winner improvement occurred mainly
in 2024. The stages do not align sufficiently to locate a cause. Per-event skill,
weighted lineup mean skill and winner skill are different targets.

**Explicit stop:** preserve these findings and the prior failed gates. No
automatic blend, recency adjustment, new aggregation, threshold relaxation or
score model. A further experiment would need a distinct supported hypothesis
and a new Owner decision; this memo does not provide that support. These losses
and probability changes establish neither market edge nor profitability.

Supporting [table](supporting_table.csv), [results](results.json),
[protocol](PROTOCOL.md), [calculation](run.py), [verification code](verify.py),
[verification receipt](verification.json) and [existing artifact hashes](existing_artifact_hashes.json).
Raw licensed events/player rates, per-event records and game/slot traces remain
private outside Git. Only the authorized draft PR documentation changed;
production, collectors, pins, schedules and T−6h studies remain intact. No merge.
