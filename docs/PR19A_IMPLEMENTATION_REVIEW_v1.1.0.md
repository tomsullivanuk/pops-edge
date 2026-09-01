# PR19A Implementation Review and Handoff

**Decision:** ACCEPT for Product Owner review\
**Acceptance scope:** documentation-only PR19A rights, methodology, and gate
definition\
**Authoritative base:** GitHub `main` at
`e643e7fe5222d226457166bf47e45a2bddefc512`\
**Independent review:** completed 2026-09-01\
**Model or dataset admitted:** none

## 1. Review outcome

The PR19A candidate is review-ready. No P0 or P1 blocker, operational-fitness
blocker, or remaining P2/P3 finding exists within the approved scope.

The independent review initially identified one P3 ambiguity in how an exact
same-time tie at the recent-10 cutoff would be resolved. The protocol now
invalidates that target feature snapshot and expressly prohibits input order or
`gamePk` from selecting the recent set. The amendment review accepted that
correction without a new finding.

Acceptance means only that the candidate durably resolves PR19A's rights and
methodology questions for Product Owner review. It does not authorize commit,
push, pull-request creation, merge, data-source contact or acquisition,
dependency installation, dataset construction, model construction or training,
activation, deployment, wagering, trading, Policy, Governance, Opportunity
Analysis, or production behavior.

## 2. Accepted decisions

1. `gmalbert/baseball-predictions` was pinned at
   `685cdff166df6eb84f69d8c0b6ac291713511aab` and evaluated without cloning,
   copying into the workspace, modifying, or executing third-party code.
2. The pinned external tree has no detected project license or rights inventory;
   model, data, asset, dependency, and upstream-data authority is insufficient.
3. PR19 selects an independently implemented clean-room path. External code,
   tests, prose, schemas, configuration, models, data, assets, lock material,
   and generated outputs are excluded.
4. Model 0 estimates exactly one pregame MLB regular-season home-team win
   probability at a schedule-derived T-6h boundary.
5. Market independence is end-to-end and includes source admission, features,
   labels, missingness, preprocessing, selection, fitting, calibration,
   thresholds, retraining, and inference.
6. Model 0 is deliberately bounded to three point-in-time team-level features,
   a fixed logistic model, validation-only sigmoid calibration, two fixed
   baselines, and one untouched 2025 final test.
7. PR19B and PR19C have deterministic entry, exit, and admission gates. Failed
   gates reject the dataset or model without result-directed repair.
8. Current Pops' Edge foundations are reusable, but the presently gathered or
   authorized material is not a rights-cleared 2021–2025 point-in-time training
   population. PR19B entry is therefore `FAIL / NOT READY`.

## 3. Governing boundaries applied

The review applied, in authority order:

- [Empirical Research Methodology](../EMPIRICAL_RESEARCH_METHODOLOGY.md);
- [Product](PRODUCT.md);
- [Architecture](../ARCHITECTURE.md);
- [Roadmap](../ROADMAP.md) and
  [v1.1.0 Release Plan](RELEASE_PLAN_v1.1.0.md);
- the [rights decision](PR19A_RIGHTS_DECISION_v1.1.0.md); and
- the [Model 0 protocol](PR19A_MODEL_0_PROTOCOL_v1.1.0.md).

The candidate preserves Identity, Evidence, Measurement, Forecast
Intelligence, Policy Hypothesis, Product Owner Governance, Forecast Policy, and
Operations as separate authority boundaries. Feature snapshots, datasets,
models, calibration, and offline evaluation remain derived or reproducibility
material. Only a later prospectively emitted probability from one separately
admitted and activated pinned model could become Forecast Observation Evidence.

## 4. Evidence reviewed

### External rights and provenance

- remote `HEAD` and `main` resolved to the recorded pinned external revision;
- GitHub commit time and subject matched the rights record;
- GitHub repository metadata reported no license and the pinned license endpoint
  returned not found;
- the pinned tree inventory contained the recorded manifests, dependencies,
  model/data artifacts, and no `LICENSE`, `LICENCE`, `COPYING`, or `NOTICE`
  path; and
- no rights evidence overcame the default fail-closed disposition.

### Pops' Edge repository state

- canonical MLB `gamePk`, team, schedule, status, pitcher, doubleheader, and
  lineage contracts exist;
- immutable Forecast and Outcome Observation, provenance, chronology,
  correction, content identity, and replay foundations exist;
- provider-neutral Brier, Log Loss, Calibration/WACE, deterministic uncertainty,
  Coverage, standalone/comparative performance, and report foundations exist;
- committed MLB fixtures are bounded validation material rather than a
  multi-season research population;
- DRatings material is external forecast test material and Kalshi is
  market-derived, so neither is a native feature source; and
- the current repository has no admitted, rights-cleared 2021–2025 historical
  source with exact point-in-time availability and correction authority.

## 5. Validation

Completed validation:

- `git diff --check`: pass after the review amendment;
- referenced local document existence: pass;
- independent inspection of all tracked and untracked candidate content: pass;
- rights/provenance metadata verification: pass; and
- 244 targeted tests covering event identity, research contracts, comparative
  replay/reporting, and standalone replay/performance: pass.

The complete existing suite discovered 500 tests but could not produce a clean
regression result in this worktree because the runtime lacks existing
`requests` and `pandas` dependencies. The observed import failures cascade into
unrelated operational tests. No dependency was installed because PR19A is
documentation-only and the Product Owner did not authorize additional
third-party execution. This is a material validation limitation, not evidence
of a PR19A code regression.

## 6. Files in the candidate

New durable artifacts:

- `docs/PR19A_RIGHTS_DECISION_v1.1.0.md`;
- `docs/PR19A_MODEL_0_PROTOCOL_v1.1.0.md`; and
- `docs/PR19A_IMPLEMENTATION_REVIEW_v1.1.0.md`.

Minimal governing and navigation updates:

- `ARCHITECTURE.md`;
- `CHANGELOG.md`;
- `README.md`;
- `docs/MLB_SOURCE_RESEARCH_v1.1.0.md`; and
- `docs/RELEASE_PLAN_v1.1.0.md`.

`ROADMAP.md`, `docs/PRODUCT.md`, empirical contracts, runtime code, tests, and
operations are unchanged because their existing authority is sufficient and
PR19A authorizes no executable model boundary.

## 7. Material limitations and open risks

- The rights review is engineering due diligence, not legal advice or patent
  clearance.
- No historical MLB source is currently admitted for PR19B. Access, retention,
  model-training, derived-artifact, availability-history, and correction rights
  remain unresolved.
- The deliberately modest feature set may fail offline admission. That is an
  acceptable truthful PR19 outcome, not a reason to expand or tune the protocol
  after test access.
- Event-level bootstrap uncertainty does not capture every temporal, team,
  source, missing-population, or distribution-shift uncertainty.
- Full-suite execution remains to be repeated in the repository's approved
  dependency environment before any later code-bearing gate.

## 8. External and production state

The review fetched the authoritative Pops' Edge `main`, read public external
GitHub metadata and documentation, and fast-forwarded this detached local
worktree to the verified base before editing. It made no remote repository
change.

No commit, branch, push, pull request, tag, release, source contact, purchase,
credential use, live or historical data collection, third-party-code execution,
dependency installation, model construction, training, Forecast Observation,
activation, deployment, wager, trade, Policy, Governance, Opportunity Analysis,
or production change occurred.

## 9. Next gate and handoff

The immediate next step is Product Owner review of this PR19A candidate. If the
Product Owner accepts it, PR19A may be committed or proposed for merge only
under separate authorization.

No PR19B implementation prompt is included because a material prerequisite is
unresolved and PR19B entry currently fails. Before PR19B construction, the
Product Owner must decide whether to pursue a historical MLB source and
separately authorize the relevant rights/access investigation or acquisition.
That source must then pass every
[PR19B entry gate](PR19A_MODEL_0_PROTOCOL_v1.1.0.md#12-pr19b-entry-and-exit-gates).

If no source is pursued or admitted, PR19 may pause or close after PR19A with no
model. That is a valid, scientifically honest release outcome.
