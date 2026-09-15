# MLB Bet Sheet — v1.3 adopted feature contract

Adopted by the Product Owner September 15, 2026; implementation explicitly authorized.
Baseline: `c8e72cbad7e0f84628e525ef2e1c4f73bb8b3409`. Methodology → Product →
Architecture governs. This operational presentation does not change research.

## September 15 presentation and unified-refresh amendment

The Owner approved NFL-style Match status/final score, a rightmost Details/Close
button, compact Details and last-captured prices retained in the main row. Display a
green check only beside the winning team's YES contract; no visible winner label or
losing icon. Its accessible description denotes a game result, not financial settlement.

Use the NFL pale rounded filter bar, compact inline Date/Team controls, All teams,
Today/Tomorrow and unchecked Omit completed games. Omission requires verified sporting
completion; in-progress games and unresolved final information remain visible. Show one
compact summary of games, captured prices and prices not captured. These counts describe
the filtered saved view, not current executable availability.

One Refresh MLB sheet action operates on the selected official schedule date. Today
and future current-season dates retrieve schedule/status/results, then eligible pregame
books. Past saved current-season dates update official results only, never past prices.
Team/completion filters do not narrow acquisition. Opening dates remains read-only.
Remove the routine reload control; offer Retry loading saved sheet only for a read
failure or uncertain action outcome. That recovery is a local read, not acquisition.

A complete valid schedule/result observation may be published when later Kalshi discovery
fails. Report a partial update with odds unavailable, no new market completeness or
price authority, and compatible older captures retained with their original dates.
Partial catalogs are not used for market matching. Failed official discovery, storage
publication or clock validation preserves the prior complete selection. Failed receipts
remain immutable alongside valid observations; no partial operational output gains
scientific authority.

All ordinary times use America/Chicago (Central, with DST), rounded to minutes.
Today/Tomorrow follow the Central calendar; Date still selects the official MLB schedule
date. Do not reassign games or alter provider rule wording and stored UTC timestamps.
Last captured means the latest valid saved observation for the exact compatible game
and contract, not a closing price or an available offer. Preserve five-minute/start-time
current-price eligibility even when expired dated history remains visible.

Final scores require explicit final status, consistent fields, nonnegative integer
scores and supported identity/chronology. Missing, conflicting, tied or exceptional
unresolved outcomes never manufacture a winner. Separate result and price observation
times and immutable references. Changed participants, doubleheader, scheduled start or
incompatible/ambiguous market identity cannot inherit a quote.

Ordinary Details retain the compact capture table, observation time and useful missing
information. Omit the generic settlement-summary paragraph. Exact rules, provenance,
receipts and original calculations remain available in secondary evidence/downloads;
contract validation and settlement meaning are unchanged. Important failures remain
visible outside Details.

This amendment replaces the earlier separate result action, Eastern display,
started/completed combined filter, historical-price placement and all-or-nothing
schedule/catalog publication behavior. Old bundles remain readable and immutable.
No automatic refresh, live scoreboard, in-play odds, accounting or scientific scoring.

## Product and price

One official schedule date, default Today Central; Today/Tomorrow and a date selector,
team filter, completed-game omission, and Refresh MLB sheet. Filters do not limit
retrieval. Preserve every returned official game even when unsupported/unpriced.
Distinct doubleheaders retain MLB game identity, game number and schedule instant.

One row per game: start, away at home, each team's YES buy price and visible status.
Show the best ask in cents before fees only with at least one contract of positive
depth at that price. Same-contract opposite-bid complements retain provenance;
another team's NO contract is not a fallback. No normalization, last-trade/midpoint
substitution, model-derived edge, confirmed holdings or guaranteed execution.

Only supported regular-season pregame full-game markets. Complete settlement wording,
explicit $1 notional, exact participants/date/time/side and an open market are required.
Unknown/contradictory clauses and ambiguous identity withhold prices. A missing side
does not erase an independently valid other side. Unknown, postponed, suspended,
resumed, cancelled and unsupported games remain visible without pregame offers.

Five-minute eligibility is conservative from actual request start, including schedule
and catalog chronology; at 300 seconds or scheduled start the offer ceases to be current.
Load, visible timer and focus return reassess without acquisition. Clock reversal or
uncertainty must not rejuvenate quotes. Elapsed kickoff is not sporting completion.
Retain historical prices only as dated history. Exact calculations remain unrounded;
every readable metric, including Details, has at most two decimal places.

## Acquisition, storage and authority

The fixed local action retrieves a complete schedule and bounded complete MLB catalog
before independent per-contract books. Zero games is valid only with complete schedule
authority. Incomplete catalog cannot prove no market. No browser read collects data.
No forecasts, account credentials, orders, research commands or automated retry.

Retain actual request start/end, raw bytes/digests and errors in a dedicated operational
odds directory. Interrupted candidates have no completed-view authority. Publish a
complete bundle last, then atomically select it with the last attempt outcome.
Book failures may produce a complete partial-coverage bundle. Failed official schedule acquisition keeps the prior saved result/dates and a visible failed attempt. Failed catalog acquisition may publish valid schedule/results with explicit unavailable odds and dated retained quotes as specified above; no silent old-price substitution. Repeated explicit refresh creates new chronology, not evidence repair.
Only one writer may use an output root at a time; manual independent retry is sufficient.

No writes to scientific archives, activation, capture markers, checkpoints, indexes,
collector configuration, selected research reports or operational authority. Old
adapters/replay stay unchanged; new operational rule versions are explicit.

## Must hold

Validate correct sides/prices/depth; ambiguous doubleheaders/relisted markets; complete
settlement clauses; missing/invalid books; incomplete catalog; no-games versus failed
schedule; partial/failed/interrupted publication; expiry/start/sleep/clock reversal;
read-only navigation; two-decimal display; safe local routes and origin checks;
immutable bundle/download consistency; unchanged NFL and MLB scientific behavior.
Important failure/coverage notices remain visible outside Details. Test offline before
any separately authorized live acquisition; browser-check filters, expiry and downloads.

## Accepted limitations and deferred work

Local manual operation; selected-day current-season acquisition; supported regular-season
pregame markets only; missing observations; one-contract best-ask before-fee illustration;
no model or holdings; trusted local files/clocks with visible uncertainty and manual recovery.
Live-provider commissioning remains separate from fixture validation.

Defer in-play, postseason, other bet types, multi-level fills/route optimization, fees,
models, accounting, scoring, cross-sport ranking, shared-shell completion, automatic
refresh/recovery, hosting migration, wagering and study closure. No new service required.

## Authorization

The Owner adopted scope and authorized implementation, including governing documentation.
The documentation adoption precedes code in the working change; it can be split for
integration review. Commits, push/PR/merge, live acquisition, initialization of live data,
deployment and publication require their separate authorization.
