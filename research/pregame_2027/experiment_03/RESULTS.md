# Experiment 03: stopped at numerical gate before evaluation

October 12, 2026. **Incomplete comparison; no predictive result and no promotion.**
Tom approved the bounded offline experiment. The frozen implementation was
published at commit `0e0f94f` before fitting. The first inner baseline fit failed
the protocol's convergence acceptance check; execution stopped as required.

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd.,
Newark, DE 19711.

## Data and feature readiness

Additional 2022/2024/2025 season bundles transferred 29,607,055 bytes, within the
100 MB additional cap. Required extracted files across 2022–2025 remain below
1 GB. Existing 2023 inputs were reused unchanged. No paid access or credentials.

Full regular-season PA audits: 182,052 / 184,104 / 182,449 / 182,926 annually.
After predeclared intentional-walk removal, 729,517 PA supply features/labels.
No count, label, unknown-hand or ID discrepancies remain. Three recorded starters
have zero completed-PA exposure; nine initial batters are replaced before any PA.
The starting-role/fielding records agree and replaced batters have no PA;
retain these cases and original identities, not first-completed-PA substitutions.
Detailed annual aggregates and exception-resolution receipts accompany the freeze.

Direct weighted history checks on 60 representative PA agree within 2.82e-13;
same/future outcome mutation changes those independently rebuilt features by zero.
The analytic objective gradient passes a synthetic finite-difference check within
2.64e-10. These are same-assistant validation checks, not external review.

## Why fitting stopped

The first fit is the gamma=0.1 baseline trained on 181,577 eligible 2022 PA for
2023 inner validation. L-BFGS returned after 61 iterations / about one second
with a relative-objective-change termination at floating-point precision. Its
reported summed objective is 140,416.50179047725; gradient infinity norm is
0.00010391837730386409. The frozen requirement is at most 0.000001, so the fit
does **not** meet acceptance even though the optimizer reports success.

No inner validation scores, outer forecasts, challenger fits or 2024/2025
performance results were produced. The incomplete baseline archive stays private;
the scrubbed numerical receipt contains no fitted player IDs or contexts.
This is a numerical-validity stop, not a failed component-accuracy gate.

The absolute summed-gradient requirement is sensitive to training population
size. Its observed value divided by N is about 5.72e-10 per PA, but that does not
retroactively satisfy the agreed rule. [A proposed numerical amendment](NUMERICAL_AMENDMENT.md)
rescales the same objective and penalties together; it remains for Tom's agreement.
No optimizer/model switch or hyperparameter expansion is proposed.

During inspection, the artifact filename helper also proved to strip suffixes
after decimal gamma values. A proposed append-suffix correction preserves full
gamma/year names before any additional fit. No existing evaluation was affected,
because execution stopped at the first training fit.

The original freeze and failure remain preserved. Draft PR #86 is unmerged;
production, prior experiments and T−6h studies remain untouched. The separate
3.5 inquiry remains pending and is not a dependency.
