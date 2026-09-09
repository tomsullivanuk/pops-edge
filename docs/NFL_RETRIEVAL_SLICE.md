# NFL-2A — public Kalshi retrieval

September 9, 2026: the Product Owner authorized moving on to Kalshi retrieval.
Implement a manually invoked local collector from merged NFL-1 main. This is
the acquisition half of NFL-2; schedule matching and the ranked board follow.

## Acceptance boundary

Select an inclusive date window of at most eight days using the originally
scheduled date explicitly published in Kalshi's game rules. This is a provider
catalog filter, not official schedule identity or pregame eligibility. Do not
use ticker dates, market close/expiration timestamps or occurrence time as a
substitute for kickoff. Collect only the KXNFLGAME full-game winner series.

Preserve series fee metadata and rule URLs, complete paginated open-market
catalog pages, selected market metadata and fixed-point order books. Record
actual start/completion times and exact response bytes/digests for every request.
YES acquisition offers derive from NO bids; NO acquisition offers derive from
YES bids. Preserve provider prices/quantities and use Decimal without guessing
units. Historical volume and last trade must not become executable prices.

States: started → complete, partial or failed. Missing terminal run receipt means
interrupted, not success. Catalog failure stops book retrieval; individual book
failures remain visible and later markets can proceed. Raw pages never become
market/forecast eligibility. No current pointer, backdating, automatic repair or
authoritative research collection is introduced. Retry means a new truthful run.

Must hold: read-only public requests, fixed host/routes, no account credentials;
complete bounded pagination before filtering; visible unsupported/ambiguous
rules and missing prices; positive finite depth, valid dollar prices, duplicate
levels and crossed books rejected; separate metadata/book times; deterministic
replay of derived output from saved responses; immutable run files; no change to
World Cup/MLB operational paths.

Accepted limitations: manual date window; sequential point-in-time snapshots,
not a simultaneous or streaming market; no server-side snapshot consistency
promise; original-rule date may differ after postponement; full-game rule
recognition supports only inspected templates and otherwise reports unsupported;
empty/one-sided books remain visible; any catalog ambiguity prevents complete
status; manual rerun after network failure. Date-filtered results are not the
universe of scheduled NFL games. Complete means this bounded acquisition worked,
not that every scheduled game has a market.

Deferred: authoritative NFL schedule, linking verified forecasts, kickoff gates,
validated payout/fee calculations, board rankings, positions, orders, background
collection, storage migration, commit/push/merge/deployment/release. Fee metadata
and tie text are preserved but do not authorize a valuation model.

## Validation

Offline injected HTTP tests cover pagination and repeated cursors, bounds,
request failures, malformed bodies, duplicate/foreign tickers, rule ambiguity,
fixed-point book semantics, empty depth, negative/nonfinite/crossed levels,
chronology, immutable raw retention and replay tamper detection. One explicitly
invoked live smoke run exercises the selected Week 1 window. No test makes
network calls. Full existing regression suite and syntax/whitespace checks apply.
