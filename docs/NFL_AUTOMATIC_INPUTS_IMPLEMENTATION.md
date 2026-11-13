# Automatic NFL inputs — implementation report

## 1. Summary

Implemented the Owner-approved compact import screen, automatic discovery of the
latest saved ELWAY workbook, Kalshi All Activity and realized P&L exports, explicit
refresh/accounting actions, and a configurable shared iCloud input directory.
The two actions share automatic activity discovery. Exact input bytes, archived
Evidence, weekly eligibility/cutoffs and existing accounting validation remain.
This is local implementation completion, not independent review or Mini deployment.

## 2. Repository State Before PR

Authoritative GitHub main was verified as
f15fd6af138dc7f55438e59c22c054f75152a150 on November 13, 2026; the complete
root AGENTS.md and relevant Product, Architecture, refresh and Codex workflow
documentation were read. An existing old checkout was clean but intentionally
left at 39271c9b2df8068f482984be6418c34c5e5455b5. Work was integrated into a new
clean detached worktree at current main: import-workflow-integration-20261113.
There were no pre-existing modifications in that worktree. No PR exists.

## 3. Files Changed

Modified:

- nfl_refresh.py: separate input directory, visible catalog failures, automatic
  fixed-action endpoints, selection metadata and failed-baseline feedback.
- nfl_refresh.html: approved compact layout, one automatic file table, action
  readiness, visible failures and active weekly baseline checks.
- Open NFL Bet Sheet.command: trusted input-folder environment option and CLI
  argument forwarding; existing interpreter/data defaults retained.
- README.md, docs/PRODUCT.md, ARCHITECTURE.md, docs/NFL_REFRESH_GUIDE.md: current
  workflow and configuration, with historical manual-selection text identified.
- tests/navigation_browser.cjs: automatic rows and invalid-newest-file behavior.
- tests/test_nfl_performance_workflow.py: approved Details & options label.

Created:

- nfl_inbox.py: CSV classification and modification-time selection.
- tests/test_nfl_automatic_inputs.py: discovery, ambiguity, rescan, invalid input,
  provenance, baseline attention and real localhost request-guard coverage.
- tests/test_nfl_shared_inbox.py: shared-folder boundaries and visible failures.
- docs/NFL_AUTOMATIC_INPUTS.md: governing approved scope and limitations.
- This report and NFL_AUTOMATIC_INPUTS_REVIEW_HANDOFF.md: bounded review handoff.

## 4. Key Decisions

Newest means local filesystem modification time, as stated during the preview
work, not filename order or publisher chronology. This timestamp does not confer
scientific publication authority. The dedicated folder's .xlsx files remain
subject to existing ELWAY validation. CSV headings distinguish renamed exports;
known malformed Kalshi filenames remain invalid candidates. Ties block rather
than guess. The newest invalid recognized file never causes older-file fallback.

Source discovery performs no import/acquisition or store activation. Each update
rescans and checks byte fingerprints. Missing/unreadable configured folders do
not create an empty substitute. The local data root and performance/report
configuration stay independent. Failure before refresh input validation marks
an active weekly baseline check unconfirmed, preserving its previous Evidence.

One implementation with its documentation is sufficient. Sync services, automatic
ingestion/acquisition, vendor-time ranking and MLB redesign remain deferred.

## 5. Acceptance Criteria

- ✓ No required file selectors; compact approved screen and one activity row.
- ✓ Latest saved copy discovered for each type and rescanned on action.
- ✓ Missing, invalid, tied, unreadable or changed inputs remain visible.
- ✓ Missing P&L alone does not block refreshing the Bet Sheet.
- ✓ Browser cannot supply paths to automatic endpoints; origin/token guards stay.
- ✓ Shared input directory is separate from local archives and activated stores.
- ✓ Page/catalog requests do not acquire provider data or initialize studies.
- ✓ Failed discovery cannot leave a previous weekly check presented as current.
- ✗ Mini deployment/sync/production refresh not verified: its hostname cannot
  resolve from this restricted session. No production changes made.

## 6. Tests and Validation

43 targeted tests pass using the existing project Python environment:

```sh
python -m unittest tests.test_nfl_automatic_inputs tests.test_nfl_shared_inbox \
  tests.test_nfl_refresh tests.test_nfl_performance_workflow tests.test_nfl_accounting
python -m py_compile *.py tests/*.py
bash -n update_all.sh update_wagers.sh update_worldcup.sh 'Open NFL Bet Sheet.command'
git diff --check
```

Python compilation, shell syntax and diff whitespace checks pass. Preview HTML
is byte-identical to the page the Owner tested. Source review confirmed that
provider/capture/accounting implementations and saved Evidence were not changed.
The navigation Playwright test was updated but not executed in this session;
the approved desktop preview and Details & options were previously checked in
Safari and the in-app browser. Live refresh is not verified; NFL.com DNS is not
available to the preview process in this restricted environment.

Initial full unittest discovery ran 1,318 tests and reported three startup
identity failures plus the old Advanced options label assertion. The label was
updated and passes in the targeted suite. All three startup failures reproduce
on an untouched current-main worktree: kernel boot identity cannot be read in
this restricted session. They are not changed or suppressed in repository code.
A stdin-based repeat runner was interrupted because macOS multiprocessing cannot
spawn that entrypoint. A final file-based run explicitly skips only those three
verified environment-dependent cases; its final result is recorded below.

Final file-based discovery: **1,320 tests run; 1,317 passed; 3 explicitly skipped;
0 failures and 0 errors**, in 143.6 seconds. Only the three boot-identity cases
listed above were skipped in memory by the test runner; repository tests retain
their original checks. This final run includes the newest HTTP/baseline regression
checks. No provider requests or production workflow actions were run.

## 7. Risks and Open Questions

No blocking issue identified in the scoped local checks. This is implementation
validation, not an independent acceptance review. iCloud sync delay and local
saved-time recency are accepted limitations; local edits can make an old export
the newest saved file. Verify Mini input bytes and Keep Downloaded behavior when
that host is reachable. Inspect its exact runtime and optional uploader/launcher
customizations rather than replacing a running pinned checkout. Its launcher
currently identifies the app using old upload text and needs a coordinated change
at a separately authorized rollout.

No commit, push, branch creation, PR, merge, tag, release, deployment, job change,
production archive change or live provider acquisition was performed. Read-only
main discovery and detached worktrees, local source edits and isolated fixture
tests are the state changes in this turn. Next gate: scoped independent review
and explicit authorization for subsequent repository/publication actions.
