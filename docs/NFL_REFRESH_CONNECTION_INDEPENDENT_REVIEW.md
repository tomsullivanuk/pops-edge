# NFL weekly capture refresh connection — independent review

Decision: **Approved within the six-file local candidate scope. No blocking findings.**
Reviewed independently on September 12, 2026. This approves implementation fitness,
not commit, push, PR creation, merge, deployment, provider capture, or activation.

## Authority and exact scope

Read the complete root AGENTS.md from verified current origin/main
`a655334ca8b12e4378cbc61536c0db5bfe892db0`, the owner-approved
`docs/NFL_MODEL_PERFORMANCE_PROTOCOL.md`, and
`NFL_REFRESH_CONNECTION_HANDOFF.md`. Reviewed the uncommitted candidate against
parent `c8aa2afb654fa14eb69a2ea37bda3e192b536778`.
Current main advances that parent through MLB outcome monotonicity changes to
ARCHITECTURE.md, DEVELOPER.md, forecast_standalone_activation.py and its tests.
None overlap the six candidate files. This review is of the local parent-based
candidate; future integrated-main validation remains an integration responsibility.

Applied boundaries: immutable prospective evidence, explicit commissioning,
explicit official target week, semantic reimport preservation, fee-free scoring,
weekly cutoff, no retrospective price repair, visible partial/failure states,
separation from operational Bet Sheet success, and proportionate local operation.
No results-tab, automation, profit/loss, hosting or activation scope was added.

## Findings

No P0/P1 findings remain.

**P2, nonblocking — page reload can hide comparison attention.** In
`nfl_refresh.html`, the initial `load().then(...)` switches to the Bet Sheet when
operational status is complete, without the comparison-attention check used in
`poll()`. After a comparison failure alongside a successful board refresh, a page
reload can therefore put the user on Bet Sheet while the comparison message
remains on Import & Refresh. The safe manual path is to select Import & Refresh;
the status message and saved refresh diagnostics remain available. This neither
changes evidence nor grants an invalid baseline authority. Aligning initial-load
navigation with polling is a follow-up refinement, not a blocker for this slice.

**P3, nonblocking — stale descriptive text.** The module and refresh method
docstrings in nfl_performance.py still say there is no UI/production caller, and
the earlier future-design paragraph in NFL_REFRESH_GUIDE.md still says the
connection is not implemented. The appended implementation sections clarify the
current source status and separate deployment/activation. Clean up superseded
wording in a later documentation pass.

## Independent validation

- Inspected all changed implementation, HTML, tests, and both documentation updates.
- Executed `tests.test_nfl_performance_workflow` and
  `tests.test_nfl_performance`: **31 tests passed**.
- These include the real service through the workflow with fixture transports:
  first capture, identical-import price preservation, explicit retry, official
  outcome scoring, target-week/type validation, comparison failure isolation, and
  absence of automatic store initialization.
- Independently probed new `record_schedule_capture`: a valid saved official
  schedule decoded successfully; altered raw bytes and a receipt completing in
  the future were rejected. Neither invalid probe appended an authoritative event.
- Verified `git diff --check` and all six file hashes below.
- Reviewed the previously reported 825-test full suite / final 39 focused tests
  as implementer evidence; did not represent those as independently rerun here.

Testing used disposable local stores and injected provider responses. No real
provider acquisition, production data write, running-app change, branch change,
commit, push, PR, merge, deployment, or activation occurred. Only this review
artifact and disposable test artifacts were written. No browser visual QA was
performed; UI conclusions are based on source inspection.

Accepted limitations remain manual collection, partial/missed captures, a separate
commissioning gate, and no Model Performance results tab yet. The operational
season refresh and research capture remain distinct acquisitions with truthful
individual timestamps. Historical outcome updates do not enroll old prices.

## Candidate fingerprints (SHA-256)

| File | SHA-256 |
|---|---|
| nfl_refresh.py | 03118aff568040bc6a9a699a89613fb413771c6c01d2fcf7d5aadb434fbeaa3e |
| nfl_refresh.html | 3ab9274645b49c2d5ddf67b75b1705428b1f8d0b6582137071bb1c7b363012af |
| nfl_performance.py | 2137f0eb630ddeb8840d06345cad20ac138cdabce0dffdc3f924a405ee9c51dd |
| tests/test_nfl_performance_workflow.py | 5a4cb8e5d11ff4d31ef5c275144bc95d2540371087c557bf5fe46d976e288ded |
| docs/NFL_REFRESH_GUIDE.md | d1eee4df279b6d280986244958974053580795c5b23a6d205742fbf04c3663e2 |
| docs/NFL_MODEL_PERFORMANCE_IMPLEMENTATION.md | c33893acb171d9ecd9453b5b190f5e7ecf6434b9ddd0d57f12317698614fcbd6 |

## Next gate

Review-only authorization is exhausted by this assessment. Seek corresponding
owner authorization before commit, push, and PR creation; merge/deploy and explicit
commissioning remain separate gates. Use the separate
[NFL_REFRESH_CONNECTION_HANDOFF.md](NFL_REFRESH_CONNECTION_HANDOFF.md) for
integration context. No backdated activation is permissible.
