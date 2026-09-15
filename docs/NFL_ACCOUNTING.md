# Paired NFL accounting imports

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
