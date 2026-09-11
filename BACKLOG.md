# Pops' Edge Backlog

This backlog records uncommitted work. Inclusion does not authorize
implementation or assign a release.

## Product and analytics

- Forecast calibration and closing-line performance reporting.
- Cross-sport portfolio exposure and correlated-risk views.
- Source comparison and disagreement analysis.
- Additional providers and sports after source/licensing research.
- Configurable bankroll and sizing policies without changing historical
  defaults.

## Operations

- Derive the project path dynamically instead of assuming `~/pops-edge`.
- Define dependency management and supported Python versions explicitly.
- Add structured logging and clearer recovery diagnostics.
- Separate deterministic validation from authorized live smoke tests.
- Inventory and test scheduled/local automation.
- Obtain and record licensed official MLB access, including price, limits,
  history, retention, and `gamePk` mapping guarantees.
- Obtain written machine-access and evidence-retention terms from an
  independent MLB forecast provider; evaluate DRatings then FanGraphs.
- Define restricted raw-evidence storage and retention outside Git.

## Architecture

- Extract shared contracts only after World Cup and MLB demonstrate them.
- Isolate sport outputs, archives, and configuration.
- Evaluate packaging and command-line entry points.
- Reduce workbook-schema coupling where it blocks a proven use case.

## Deferred from the MLB foundation (now v1.2.0)

- Automated trading or order placement.
- Broad World Cup architecture rewrite.
- Further sports beyond the existing World Cup/NFL workflows and planned MLB foundation.
- Hosted multi-user service.
- Repository/local-directory rename without separate authorization.
- Sportsbook consensus ingestion until canonical identity and one licensed
  forecast adapter operate; evaluate The Odds API first.

## NFL v1.1.0 — nonblocking review follow-ups

- **P2: open-page freshness.** An open season sheet retains load-time eligibility
  after quotes age or kickoff. Reload to reassess saved prices; Refresh Bet Sheet
  obtains new captures. A bounded future change can expire/mark rows and update
  counts without retrieving data or resetting filters.
- **P2: rejected-workbook restoration.** An invalid archived workbook can prevent
  restoration after restart. Select a valid workbook and activity file, then
  Refresh Bet Sheet to recover the in-session view. Preserve rejected evidence;
  do not delete it as a workaround. A bounded future change can restore an
  explicit successful selection while retaining rejection diagnostics.

Both were nonblocking in the [independent PR #33 review](docs/NFL_PR33_INDEPENDENT_REVIEW.md).
They are follow-ups, not authorization to implement a new recovery subsystem.
