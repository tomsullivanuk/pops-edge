# PR19A Native Model Rights and Provenance Decision

**Status:** selected clean-room path; PR19B entry blocked pending an authorized
point-in-time data source\
**Decision date:** 2026-09-01\
**Pops' Edge authority reviewed:** GitHub `main` at
`e643e7fe5222d226457166bf47e45a2bddefc512`\
**Nature of review:** engineering due diligence, not legal advice

## 1. Decision

Pops' Edge will use an **independently implemented clean-room design** for
Model 0. It will not copy, modify, translate, execute, package, redistribute,
or derive implementation material from `gmalbert/baseball-predictions` unless
a later written rights decision and separate Product Owner authorization permit
that specific use.

The repository remains useful only as evidence that certain engineering themes
are worth considering. Point-in-time chronology, immutable provenance,
deterministic replay, calibration, and pinned model identity were already
independently required by Pops' Edge's Methodology, Product, Architecture, and
Release Plan. Those Pops' Edge authorities—not the external implementation—own
the PR19 design.

This decision closes the third-party-code question for PR19A but does **not**
admit a training dataset. The presently gathered or authorized MLB material is
insufficient for PR19B, so no dataset construction, dependency installation,
model construction, or training is authorized by this record.

## 2. Candidate identity and inspected revision

| Field | Recorded value |
|---|---|
| Repository | [`gmalbert/baseball-predictions`](https://github.com/gmalbert/baseball-predictions) |
| Repository owner | `gmalbert` |
| Visibility | Public GitHub repository |
| Default branch at review | `main` |
| Pinned revision | [`685cdff166df6eb84f69d8c0b6ac291713511aab`](https://github.com/gmalbert/baseball-predictions/tree/685cdff166df6eb84f69d8c0b6ac291713511aab) |
| Pinned commit time | `2026-09-01T12:24:01Z` |
| Pinned commit subject | `chore: update best_bets_today [skip ci]` |
| Verification method | Git remote identity plus GitHub repository, commit, tree, and license metadata |
| Material copied into Pops' Edge or its workspace | None |
| Third-party code executed | None |

The pinned revision was also the remote `HEAD` and `main` revision when
reviewed. Future upstream changes do not amend this decision. Any later
revision requires a new pinned review.

## 3. Rights inventory

### 3.1 Repository code and documentation

The pinned tree contains no file named `LICENSE`, `LICENCE`, `COPYING`,
`NOTICE`, author-rights inventory, or third-party-notice file. GitHub reports
the repository license as `null`, and its license endpoint returns no detected
license for the pinned revision.

GitHub's own
[licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
states that absent a license, default copyright rules apply and others do not
receive permission to reproduce, distribute, or create derivative works. A
public repository and GitHub's fork control do not supply the rights needed by
Pops' Edge.

**Disposition:** no source code, tests, workflows, configuration, prose,
schemas, graphics, or other authored material may be reused.

### 3.2 Bundled models, data, and assets

The pinned tree includes, among other material:

- serialized `joblib` model artifacts;
- Parquet training, backtest, leader, park-factor, weather, and feature files;
- Retrosheet-named Parquet files;
- a logo and generated pick output; and
- model metrics and importances.

No per-artifact license, source grant, redistribution permission, attribution
record, or sufficiently complete provenance ledger was found in the pinned
tree. The repository's own quarantine configuration says its legacy model
artifacts lack feature, dependency, calibration, and checksum manifests and
were trained from a same-season aggregate matrix.

**Disposition:** all external models, data files, generated outputs, images,
and other artifacts are prohibited inputs to Pops' Edge. Their presence is not
evidence that their upstream data may be retained, transformed, or
redistributed.

### 3.3 Dependency manifests

The pinned tree contains `pyproject.toml`, `requirements.txt`, and `uv.lock`.
The declared direct packages include APScheduler, DuckDB, joblib, MLB-StatsAPI,
NumPy, pandas, Plotly, pybaseball, PyArrow, Pydantic, Requests, scikit-learn,
SciPy, statsmodels, Streamlit, XGBoost, LightGBM, and development, OCR, and API
extras. The two human-authored manifests are not an exact match, and neither is
a license bill of materials.

Package licenses are package-specific. They do not license the external
repository, and the external repository does not transfer a dependency choice
or dependency right to Pops' Edge.

**Disposition:** PR19 adopts none of the external project's dependency
selection or lock material. A later PR that proposes a new Pops' Edge
dependency must pin it, record its source and license, identify notice or
redistribution duties, and receive review on its own merits.

### 3.4 Declared data sources

The external README and file inventory identify or imply MLB Stats API,
PyBaseball/Statcast, Retrosheet, FanGraphs data, Chadwick registry data, ESPN
odds, The Odds API, weather, and other odds or lineup sources. The pinned tree
does not contain a consolidated grant establishing automation, historical-use,
retention, model-training, derived-artifact, attribution, or redistribution
rights for those sources.

Pops' Edge's existing
[MLB source research](MLB_SOURCE_RESEARCH_v1.1.0.md) independently records that:

- the public MLB Stats API is a technical reference and is not approved for
  automated production collection under the reviewed MLB terms;
- forecast sites and commercial sources require their own written automation,
  analysis, and retention authority;
- The Odds API has source-specific constraints and is market-derived in any
  case; and
- market or odds data is prohibited from the native-model path regardless of
  whether access rights exist.

**Disposition:** no data-source permission is inherited from the external
repository. No external source named there is admitted by this decision.

### 3.5 Attribution and redistribution

Because reuse is rejected, PR19A creates no upstream attribution or
redistribution obligation. That is not a finding that no such obligations
exist; it is a consequence of using none of the material. If explicit rights
are later offered, the new review must record the licensor, covered revision
and material, license text, attribution, notice, modification, model-output,
data, retention, and redistribution terms before use.

## 4. Accelerator assessment

The candidate does not accelerate PR19 through reusable implementation or
artifacts. The missing project license is sufficient to reject that path, and
the bundled model/data provenance would independently fail Pops' Edge's
scientific-admission boundary.

The inspection does reinforce several independently governed requirements:

- feature-time authority must be explicit rather than inferred from a final
  season aggregate;
- model and calibration artifacts need complete manifests and checksums;
- deterministic replay and leakage tests are first-class requirements; and
- market-facing selection and wagering functions must remain outside the
  native scientific path.

These are requirements of Pops' Edge's own protocol. PR19B and PR19C
implementers must use the Pops' Edge repository and
[Model 0 protocol](PR19A_MODEL_0_PROTOCOL_v1.1.0.md), and must not consult the
external source tree as an implementation guide.

## 5. Clean-room controls

The following controls are must-hold conditions for PR19B and PR19C:

1. No external repository file, snippet, test, schema, configuration, model,
   data artifact, graphic, prose, dependency lock, or generated output enters
   Pops' Edge.
2. No external code or model artifact is executed, imported, decompiled,
   translated, or behaviorally probed.
3. Implementers work from Pops' Edge governing documents, approved source
   contracts, and independently written acceptance tests.
4. New dependencies and data sources receive their own pinned rights and
   provenance records; a package name or upstream use is not authority.
5. A similarity concern or uncertain provenance fails closed and is returned
   for review before implementation continues.
6. A later upstream license does not retroactively amend this record. Reuse
   requires a new rights decision and separate Product Owner authorization.

This is a proportionate engineering clean-room boundary for a personal hobby
project, not a legal clean-room opinion or patent clearance.

## 6. Existing Pops' Edge foundation and data sufficiency

### 6.1 Reusable native Pops' Edge foundations

The current repository already provides native, reviewed foundations that
PR19 may extend rather than replace:

| Boundary | Existing foundation | PR19 relevance |
|---|---|---|
| Identity | `CanonicalEvent`, MLB `gamePk`, stable team identity, doubleheader and schedule-lineage contracts | Canonical game and participant identity |
| Evidence | Immutable provenance, raw digests, schedule/status/pitcher observations, Forecast and Outcome Observations | Point-in-time source and emitted-forecast authority |
| Chronology | Collected/effective times, append-only corrections, boundary-aware selection | Feature watermarks and late-correction handling |
| Replay | Content-derived identity and upstream-first graph reconstruction | Dataset, model-bundle, forecast, and result reproduction |
| Measurement | Brier Score, extended-real Log Loss, fixed-bin Calibration/WACE, deterministic bootstrap | Offline and prospective evaluation |
| Coverage | Schedule-derived opportunity universes and visible failure categories | No silent row or forecast removal |
| Reporting | Provider-neutral standalone and comparative report composition | Later PR19E reuse |

These are implementation foundations, not a training dataset and not authority
to acquire more data.

### 6.2 Material presently in the repository

The MLB JSON and contract fixtures are bounded test material. They demonstrate
ordinary games, doubleheaders, postponements, schedule facts, pitchers,
outcomes, validation, and replay behavior. They are not a multi-season research
population and do not become research Evidence merely because they are stored
in Git.

The DRatings snapshot is external forecast test material, not a native feature
source. Kalshi material is market-derived and is prohibited from every Model 0
construction and selection stage. Existing PR17 market Evidence may later be a
separately captured comparative benchmark after Model 0 is admitted and pinned;
it cannot repair the training dataset.

The existing MLB Stats API adapter establishes a replaceable technical
boundary. Its presence does not override the documented absence of approved
automation rights, and the repository has no complete 2021–2025 point-in-time
schedule/status/outcome archive with source-availability history.

### 6.3 PR19B readiness decision

**Current result: FAIL / NOT READY.**

The repository lacks all of the following required PR19B authority:

- an admitted data source with documented local automated access, historical
  use, retention, model-training, derived-artifact, and audit rights;
- a complete 2021–2025 MLB regular-season schedule/status/outcome universe;
- source-availability timestamps or watermarks sufficient to prove what was
  available before every T-6h forecast boundary;
- correction history sufficient for as-of replay; and
- a complete, rights-cleared input from which the precommitted features can be
  deterministically derived.

Later acquisition cannot be presented as prospective Evidence or used to
invent historical availability. It may support PR19B only when a licensed
historical source supplies independently defensible point-in-time authority.

## 7. Acceptance boundaries

### Must hold

- The clean-room controls remain intact.
- The canonical estimand, market-independence boundary, information-time
  contract, features, split, metrics, and admission gates are fixed by the
  Model 0 protocol before construction.
- PR19B remains closed until every entry gate in that protocol passes.
- Derived feature, training, model, calibration, and evaluation material never
  becomes Evidence.
- No finding creates Policy, Governance, Opportunity Analysis, wagering,
  trading, production, or activation authority.

### Accepted limitations

- The review is engineering due diligence, not legal advice.
- No formal patent search or legal clean-room certification was performed.
- The external dependency graph and every upstream data term were not fully
  audited because no external material or dependency choice is being adopted.
- Manual rights review and local operation are acceptable at the current
  product stage.

### Deferred improvements

- A machine-readable software/data bill of materials for an admitted native
  implementation belongs with the PR that introduces those dependencies.
- Automated license scanning may be added later but does not replace human
  review.
- Richer player, pitcher, park, weather, and lineup sources remain outside
  Model 0 unless a later protocol amendment is approved before test access.

## 8. Next authorized gate

PR19A may be reviewed and accepted as a clean-room methodology decision. The
next product gate is **not PR19B construction**. It is a Product Owner decision
on whether to pursue and authorize a rights-cleared historical MLB
schedule/status/outcome source satisfying the
[PR19B entry gates](PR19A_MODEL_0_PROTOCOL_v1.1.0.md#12-pr19b-entry-and-exit-gates).

Until that decision and source admission exist, PR19 may pause or close
truthfully after PR19A with no model.
