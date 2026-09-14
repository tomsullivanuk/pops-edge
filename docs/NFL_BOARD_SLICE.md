# NFL-2B — game matching and personal comparison board

The owner authorized progressing to game matching and the NFL comparison board
on September 9, 2026. This slice implements a manually refreshed, local comparison
surface, without stake sizing, bet signals, orders or research/Policy authority.
The slice merged through PR #33; deployment and release remain separate actions.

## Must hold

- Independently collect the official NFL weekly schedule from NFL.com, retaining
  raw HTML, request chronology and hashes. Parse exactly one matching weekly
  game-details query; validate season, REG week, unique official game IDs/teams,
  explicit timezone-aware kickoff when known and neutral status (TBD handling
  below). Fail visibly if layout or scope changes. NFL game ID is identity; aliases never infer ambiguous teams.
- Validate the selected ELWAY record against its preserved source: image receipt
  and checked review for legacy imports, or workbook bytes and automated
  validation for Excel. Match exact season/week/home/away/neutral fields. Each
  comparison binds an explicit source; no fuzzy mapping or automatic reversal.
- Replay the selected Kalshi run. Match full-game rules by both participants and
  original date in America/New_York to scheduled kickoff. Require exact inspected
  primary and secondary rule templates for comparisons, not substring matching.
  Ambiguous/duplicate mappings, unsupported rules and missing markets stay visible.
- Display all official scheduled games, including missing forecasts/markets and
  excluded states. Rank only usable pregame comparisons at actual build time.
  Require schedule SCHEDULED state and kickoff later than build and quote times.
  Future input timestamps fail. Default maximum ages: quotes/catalog 5 minutes,
  schedule 24 hours, ELWAY source 8 days. These are conservative display guards,
  not endorsed wagering policy. They are recorded in each output.
- A team YES contract and the opposing team NO contract have the same normal
  full-game payout: 1 on team win, 0 on loss, 0.5 on tie. Expected payout is
  (1 + team win probability - opponent win probability)/2. Preserve displayed
  ELWAY percentages and a range assuming rounding to nearest displayed unit,
  bounded to feasible probabilities summing to at most one. Do not manufacture
  exact tie probability or imply model calibration is established.
- Compare observed offers for a one-contract illustration only, requiring at
  least one contract at the best level. Estimate standard taker fee using 0.07,
  captured multiplier 1, and centicent trade-fee rounding plus cent-aligned total
  acquisition cost. No maker discount, accumulator rebate from other fills,
  third-party fees or fractional sizing is assumed. Preserve both routes and
  choose the cheaper usable cost deterministically; do not combine depth.
- Rank games by the largest lower-bound model-payout-minus-cost difference among
  usable team routes, descending. Equal values share rank; ID orders presentation
  only. Show signed differences even when negative. Call these comparisons, not
  demonstrated edges, profits or recommendations. Postponement/fair-price
  settlement is not forecast by ELWAY; exclude non-scheduled/date-mismatched games.
- Preserve complete inputs in an immutable board bundle with explicit generated
  time, hashes and derived JSON/HTML. Offline replay revalidates and regenerates
  the derivation. Standalone weekly HTML has age/kickoff warnings. The season
  view has the load-time-only limitation below. Neither silently refreshes
  prices or claims live acquisition.

## Accepted limitations and deferred scope

Public website layout can change; failures require a new manual run. No service,
background polling or broad schedule abstraction. Archived HTML records observed
schedule state, not a promise against later rescheduling. Rule and fee support is
versioned and limited; rates must be revisited if published terms change.
Single-contract cost is an illustration, not expected realized execution.
Manual file selection and local backup remain. No portfolio, Kelly, futures,
spreads, totals, outcome scoring, rights determination or production policy.

## Sources checked September 9, 2026

- https://www.nfl.com/schedules/2026/by-week/week-1
- https://kalshi.com/docs/kalshi-fee-schedule.pdf (effective July 7, 2026;
  KXNFLGAME multiplier 1)
- https://docs.kalshi.com/getting_started/fee_rounding
- Exact KXNFLGAME catalog rules archived by NFL-2A; contract link preserved:
  https://assets.kalshi.com/contract_terms/FOOTBALLGAMEWIN.pdf

## Validation

Offline synthetic tests for schedule parsing/identity, neutral sites, ambiguous
matches, roles, dates, rule additions, provenance/replay tampering, rounded-value
bounds, YES/NO route cost equivalence, fee rounding, depth, stale/future inputs,
kickoff exclusion, missing coverage and deterministic ranks. Exercise owner’s
verified Week 1 forecast plus separately captured schedule and fresh books.
Inspect the generated HTML, run focused/full regressions and whitespace/syntax.

## Current presentation and input extensions

PR #33 merged the later owner-approved Excel, activity and full-season workflow.
The original acquisition/measurement invariants above remain; these extensions
supersede the earlier screenshot-only and card/presentation assumptions:

- Excel records validate automatically against preserved workbook bytes and
  never attest human review. Legacy screenshot records retain manual verification.
- Schedule rows may have TBD kickoff. Keep them in the correct week without a
  price comparison; never invent a timestamp. The app processes every workbook
  week and reports real partial failures independently of TBD dates.
- The visible table sorts central signed difference after the one-contract fee.
  Internal conservative game ranks remain for replay; they do not control the
  table's initial sort. Routes select lower usable price, then total cost and
  contract identity. No depth pooling or sizing is introduced.
- Main comparison columns are ELWAY Contract, Kalshi price and Difference after
  fee. Original probabilities and ranges remain in Details. Dollars display to
  two decimals; times round to the nearest minute; calculations retain precision.
- The app filters by week, team, completion and strict after-fee thresholds. There
  is no text search or individual-game omission in the season view. Standalone
  weekly CLI HTML retains its own search/positive controls.
- Recorded wager (incl. fees) combines each trade's contract/cost; multiple trades
  appear separately, absent matches are blank. Supported settlements show gross
  payout without implying realized profit or confirmed holdings. See the
  [activity boundary](NFL_ACTIVITY_SLICE.md).
- Season-view freshness is checked on load/reload. The original standalone
  weekly warning remains, but the season view has no ongoing browser-time expiry.
  This known P2 limitation and manual reload/refresh path were accepted by the
  [independent review](NFL_PR33_INDEPENDENT_REVIEW.md). It is not live retrieval.

Current operator details are in the [refresh guide](NFL_REFRESH_GUIDE.md).
Existing source bundles are not rewritten by a presentation update. These
changes do not authorize research activation, execution, release or deployment.

## Historical season comparisons — September 14, 2026 correction

Owner-approved scope: when a season outcome has no current eligible comparison,
display its latest valid saved pregame comparison as historical. Preserve the
original contract, offer, ELWAY probability/value, estimated fee and source dates
as one comparison. Label history and its capture date (including year and Central
timezone) in the principal table. Historical values must not count as current
comparisons or participate in current difference filters/ranking.

Read complete saved board bundles and replay before using historical values.
Match the exact game ID, participants, neutral designation, kickoff and outcome.
Select the latest saved comparison by original generation time; same-time
conflicting comparisons remain unavailable. Keep missing history explicit and
disclose invalid historical bundles. Do not make fresh provider requests or
rewrite earlier reports, imports or research baselines. Keep the original weekly
renderer and saved JSON/HTML replay unchanged. Current activity/accounting and
game-completion decisions remain independent of historical comparison selection.

Accepted limitations: history requires retained bundles and unchanged game
identity/kickoff. A rescheduled or undated game does not borrow the former date's
comparison. Selection remains on load/reload, with no new background polling,
database or generalized archive service. Cash-flow accounting, completion sources,
research baseline changes and deployment are separate slices.

Validation must cover fresh current precedence, aging without refresh, a later
empty snapshot, per-outcome history, changed forecast values, identity/date
mismatch, missing/invalid/conflicting history, completed-game display, current
filter/count exclusion, and exact preservation/replay of saved reports.
