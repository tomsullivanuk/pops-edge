# Model Performance — independent capture/scoring review

Decision: **Approve the seven-file local candidate for commit, push, and pull-request creation.** No blocking P0/P1 findings or material P2 findings remain. This approval covers the isolated evidence/scoring service, adapters, CLI, tests, and supporting documentation. It does not approve production commissioning, deployment, refresh-handler integration, or a presentation tab.

## Authority and candidate

Authoritative baseline and reviewed parent: `c2fbc5b8daf6a4e35706ee326db4f522c14d09b6` (PR #38). The coordinating task verified current GitHub main; this reviewer read the complete root AGENTS.md from that revision and independently inspected the approved weekly protocol, scoring handoff, implementation, dependencies, tests, and documentation changes. The candidate was uncommitted during review; the fingerprints below identify it exactly.

Applied boundaries: immutable source evidence; explicit activation; publication-based weekly selection and semantic reimport identity; pre-first-kickoff capture; failure-inclusive official game coverage; no older per-game fallback; designated home YES midpoint; no fees; official outcomes rather than owner activity; deterministic paired squared contract-value errors; append-only correction history and saved report replay. Manual imports, visible missed captures, local operation, and a separately authorized later UI/activation slice remain accepted limitations.

## Independent evidence

- Ran all 24 tests in `tests.test_nfl_performance`: passed.
- Independently exercised a newer valid publication whose schedule request fails: it supersedes the previous selected publication while retaining missing market coverage, without older quote fallback.
- Independently exercised an opposite book containing only zero-quantity liquidity: no midpoint was admitted.
- Independently exercised a later official summary establishing an actual start before the import: prospective eligibility was invalidated and no game scored.
- Inspected designated market rule validation, positive book quantities, exact decimal scoring, request chronology, same-time forecast conflicts, cutoff correction behavior, source hash replay, activation isolation, and report-prefix pinning for equal-time corrections.
- `git diff --check` passed. The coordinating task is responsible for the final whole-repository regression result; this review does not represent its earlier reported full-suite count as independently rerun here.

The implementation is not connected to the existing Bet Sheet refresh path. Opening the module does not initialize a store; commissioning and data acquisition require explicit commands. No real-world collection completeness or browser/UI behavior is established by this fixture review. A future presentation slice must preserve the same coverage and source-time disclosures. Release version remains unassigned.

## Candidate SHA-256 fingerprints

| File | SHA-256 |
|---|---|
| nfl_performance.py | 524ec5b913a701593a952f895b29709cc010844144a9d5924cd6f553e6a1c3ff |
| nfl_performance_sources.py | 38ce1f680ca142a49464fc21473aeb4c660fd24a3c6539784ac3d459a1b193b2 |
| operate_nfl_performance.py | d05c6176a52d8de131c6b7fdb8337645a570f40d5458d7814e6e0a641551260e |
| tests/test_nfl_performance.py | 066078f005beacfba34b32e6a3690f707beaaed1768f9652c642fb401af61cb7 |
| docs/NFL_MODEL_PERFORMANCE_SOURCE_FEASIBILITY.md | a4cd5cd33649cc414df572ecc3e15002040afcd53960411cfdafe7e71ae4f621 |
| docs/NFL_RELEASE_PLAN_v1.1.0.md | 966de51bb179779c932da81f43ab2595182ff21c407789f9e69c3f031f724a57 |
| docs/NFL_MODEL_PERFORMANCE_IMPLEMENTATION.md | 3969ccf57b87d9b9b6b8fadb9ba2382db04db88ff68e85e61778ccf37652e870 |

## State changes and next gate

Review created only this separate review artifact and disposable offline fixture stores. No implementation files, live provider history, deployment, production data, trades, GitHub state, commits, or branches were changed by the reviewer.

The Product Owner already authorized commit, push, and PR creation conditional on approval. That condition is satisfied for this fingerprinted candidate, subject to the coordinating task's final integration checks. Merge, commissioning, and deployment require their corresponding authorization. The separate presentation handoff remains the guide for a subsequent implementation slice.
