# NFL-2B — game matching and personal comparison board

The owner authorized progressing to game matching and the NFL comparison board
on September 9, 2026. This slice implements a manually refreshed, local comparison
surface, without stake sizing, bet signals, orders or research/Policy authority.
Commit, push, merge and deployment require subsequent authorization.

## Must hold

- Independently collect the official NFL weekly schedule from NFL.com, retaining
  raw HTML, request chronology and hashes. Parse exactly one matching weekly
  game-details query; validate season, REG week, unique official game IDs/teams,
  explicit timezone-aware kickoff and neutral status. Fail visibly if layout or
  scope changes. NFL game ID is identity; aliases never infer ambiguous teams.
- Validate the selected verified ELWAY transcription against its preserved image
  receipt and checked review. Match exact season/week/home/away/neutral fields.
  No fuzzy mapping, automatic reversal or implicit latest-file choice.
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
  the derivation. The HTML is a saved snapshot, with browser-time age/kickoff
  warnings; it never silently refreshes prices or claims it is live.

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

## Bet-sheet presentation amendment — September 9, 2026

The owner requested a refactor matching the World Cup Bet Sheet, focused on the
largest ELWAY–Kalshi discrepancies. Replace game cards with a compact sortable
table, one row per team outcome. Default order is descending signed difference
between central tie-adjusted ELWAY contract value and the lowest usable observed
offer, before fees. The separate After fee column shows central value minus
one-contract cost; Details retains rounding ranges and all quote routes.
Original ELWAY win percentages remain separate from contract values. A positive
raw difference is not automatically positive after fees.

The data bundle retains conservative after-fee game scores for traceability;
the table's before-fee order is a deterministic presentation derived from its
underlying routes. This supersedes earlier text describing the default visual
order by after-fee lower bound. All missing/stale/game-status guards remain.
Show both outcomes, a positive-difference filter, team search and sortable column
headings. Use available depth rather than historical volume. Positions, Kelly
and stake columns from the reference sheet remain outside this NFL slice.
Existing snapshots may be re-rendered as a new presentation without refreshing
or backdating their data. Preserve original source/build times and record the
new render time separately. Never overwrite the original snapshot.


NFL activity extension, September 9, 2026: the owner explicitly requested wager
identification from a supplied Kalshi activity CSV. Add read-only recorded-trade
markers and details, with separate provenance/import time and exact contract-to-
outcome matching. This supersedes the earlier exclusion only for activity display;
current-balance reconciliation, positions-based recommendations, P&L, execution
and sizing remain deferred. See the NFL_ACTIVITY_SLICE.md acceptance boundary.
