# Paired NFL accounting imports

## Compact recorded trades — September 21, 2026

The Owner-approved season-table summary now shows direction/team, exact quantity
and price, e.g. YES ATL · 11.16 contracts · price $0.43. NO-direction rows explicitly
say YES-scale price; no complementary purchase price is inferred. Export YES-price
meaning, fees, timestamps, source row and holding/action caveats remain in Details.
The column heading and table-level explanation still identify recorded trades,
not verified current holdings. Genuine duplicate/accounting warnings remain visible.
Reconciled closed costs/proceeds/profit and legacy weekly rendering are unchanged.
This refines the September18 presentation, not accounting or import semantics.

## Recorded-trade presentation amendment — September 18, 2026

Owner approved displaying matched activity records even without closed-position
P&L. In accounting-enabled season views, the Recorded trades / closed cost column
shows each export row's direction/team, exact quantity, explicitly labeled export
YES-scale price, recorded fee and date. NO-direction export prices are not relabeled
as NO purchase prices. Purchase/sale action and current holdings are not inferred.
Trades appear separately from unchanged reconciled closed-position purchase cost.
They are never summed into holdings, proceeds, profit or expected payouts.

Clean matched trade-only missing-closure notices are informational: “Recorded trade ·
current holding unverified.” Their original reasons remain in `accounting_notes`;
only this presentation classification changes. Duplicates, unmatched identities,
settlement/closure discrepancies and conflicting accounting stay warnings. The raw
reconciliation result, imports, stored evidence and legacy weekly rendering remain
unchanged. Existing import summaries still describe reconciliation coverage; this
amendment changes the season table and its calculation notes, not import semantics.

Must hold: open trades visible, genuine issues visible, unchanged closed arithmetic,
no invented balances, no alteration of source or report evidence. Accepted limits:
export direction does not establish buy/sell and holdings remain unverified.
Deferred: missing Week 1 game retention, Season to Date, live holdings integration,
provider acquisition and deployment until separately reviewed and authorized.

## Product boundary

The Product Owner approved a focused accounting correction requiring both All
Activity and realized P&L exports. Week 2 market matching is explicitly deferred.
This extends the legacy activity slice for newly derived season views. Archived
weekly bundles and their legacy parser/rendering remain reproducible.

Must hold: preserve exact source files, reconcile decimal arithmetic and execution
identity, distinguish gross sale proceeds from settlement proceeds and net profit,
avoid duplicate accounting across repeated/overlapping imports, retain previously
verified closed positions after they leave a rolling export window, and expose
unmatched/conflicting inputs without guessed amounts. Sporting completion and
contract-result icons remain independent of financial profit. No quote/research
capture is part of the accounting action.

Accepted limitations: this local workflow uses manual inbox selection and a single
account. Complete closed ticker histories must reconcile within a supplied pair.
Partial positions, split histories across windows, ambiguous executions within a
second, unsupported settlement outcomes and conflicting provider corrections are
review cases. They do not receive inferred balances or automatic reconciliation.
Open holdings remain unconfirmed. Correcting conflicting immutable observations
requires a separately reviewed correction; a later import does not silently win.
No generalized ledger, tax accounting, account connector or automatic polling is
introduced. Those capabilities are deferred.

## User workflow

Place both CSVs in `~/PopsEdge/Downloads/NFL/`. Select **Kalshi All Activity CSV**
and **Kalshi realized P&L CSV**, then click **Update accounting**. The ELWAY
workbook is not required for the import; an existing season sheet is needed to
display matched games. The separate **Refresh Bet Sheet** action continues to
refresh quotes using the workbook/activity selection. It does not replace or
clear saved accounting. Accounting requires both CSVs even if one is unchanged.

The accounting action uses the same local-origin/token and inbox restrictions
as refresh. It archives the pair under `Data/NFL/accounting/<pair hash>/`, writes
the completion receipt last, and does not call any provider. Repeating an exact
pair is idempotent and preserves its original import timestamp. Monthly snapshots
are retained. Only complete, hash-verified snapshots participate in the view.

## Interpretation and reconciliation

The realized P&L source explicitly supplies closed-position side, quantity,
entry/exit prices, opening/closing fees and profit. Quantity multiplied by the
price difference must equal reported gross profit exactly, and subtracting both
fees must equal reported net profit exactly. Activity Trade amounts represent
quantities, not cash. Order rows must not be counted as additional executions.

The inspected All Activity format expresses trade prices on the YES scale.
For a NO position, reconcile to `1 − activity price`. The original position side
comes from P&L; its closing activity may have the opposite direction. This rule
is applied only to paired accounting, never to quote/order-book data or legacy
archive replay. P&L fees retain full precision; the inspected activity export
truncates fees to cents. Aggregated allocated fees must be at least the activity
fee and less than one cent above it. Other discrepancies stay under review.

P&L `type=trade` does not classify the close: match timestamps (UTC seconds),
ticker, direction, prices and quantities to an activity Trade for a sale or a
unique Settlement for settlement. All trade quantities must be fully allocated.
Multiple P&L lots can partition an execution, but may not exceed it. Confirmed
settlement proceeds must equal the activity settlement amount. A fully sold
position is not paid again at the later zero settlement event.

Across snapshots, compare lot multisets grouped by account, ticker, side, opening
and closing timestamp. Identical groups contribute once. Different observations
of the same group, or alternative closes reusing the same opening quantity,
withhold that ticker's amounts. Identical duplicate rows without unique IDs are
ambiguous rather than silently collapsed. Non-NFL records and unallocated credits
are excluded from NFL position accounting. Malformed/tampered history suppresses
financial results rather than falling back to a possibly contradicted snapshot.

The season view groups original positions under their actual contract outcome.
Recorded wager shows purchase cost including opening fees per contract. **Proceeds
/ profit** shows gross sale/settlement proceeds and net realized profit. Its
numeric sort uses gross proceeds. Details retain full-precision costs, fees,
proceeds, profit, source directory, and opening/closing/import times. Unmatched
activity does not gain an assumed purchase amount or expected payout.
