# NFL recorded activity and settlements

The owner authorized local import/presentation of Kalshi activity. This supplies
recorded trades and supported settlements, not account access, order execution,
inferred open balances, position-based recommendations or realized P&L.

## Source and matching boundaries

Preserve the exact CSV and digest with actual import time. Only Trade rows count
as recorded fills; Order rows are not additional wagers. Parse UTF-8 BOM safely,
comma-grouped quantities, side, price, fees and timezone-aware Original_Date.
Associate YES with its named team and NO with the opponent using exact supported
market matching. Closed activity may match exact date/away/home/team ticker
identity even when absent from the open catalog; that does not validate any new
price or rule. The association is independent of the currently displayed route.

The export lacks an explicit buy/sell action. Do not infer net balances or offset
opposite directions. Preserve individual trades. Duplicate identical trades are
ambiguous and flagged rather than silently doubled or deduplicated. Unsupported
or unmatched NFL records remain diagnostics; other sports are outside the view.
Each import replaces the displayed export in a new bundle; imports do not
accumulate. Activity import time may postdate the unchanged saved quote times.

## Current presentation

Recorded wager (incl. fees) lists each trade's contract and recorded quantity ×
price + fee on separate lines. Ambiguous trade amounts request review. No matched
activity leaves a blank cell, not an assertion of no account position. Supported
settlement-only activity identifies its contract without inventing purchase cost.

For an unambiguous unsettled purchase illustration, ELWAY expected gross payout
is quantity × central contract value; gross payout on a win is quantity, a tie
half the quantity and a loss zero. These assume recorded purchases remain held;
current holdings are unconfirmed. Details can show expected net after recorded
cost. Gross payout includes returned stake and is not profit.

New overlays use nfl-activity-settlements-v2; legacy v1 remains replayable.
Supported YES/NO settlement result and owned quantity must reconcile with the
export amount before actual gross payout is shown. Profit_In_Dollars is not
labeled realized profit. Duplicate/unreconciled settlements are flagged;
settlement/trade cost-basis differences remain visible in Details. Settled trades
do not get assumed open-purchase payout totals, but their recorded trade costs
remain visible. Settled games lose current purchase routes in presentation while
original comparison data remains unchanged.

ELWAY Contract and Difference after fee are the compact comparison columns.
The latter controls default sorting and threshold filters. Original probabilities,
before-fee differences and all routes remain in Details. See the
[refresh guide](NFL_REFRESH_GUIDE.md) and [board guide](NFL_BOARD_GUIDE.md).

## Settlement-status correction (candidate)

New activity parsing uses nfl-activity-settlements-v3. A unique, exactly matched,
nonfuture YES/NO settlement event establishes game completion independently of
payout arithmetic. Unreconciled payout remains a diagnostic, not an active wager.
Closed activity with unresolved cash flow suppresses purchase-amount and expected
payout illustrations; original trade rows remain in Details. Opposite-side trades
alone do not establish a cash-out, and no realized profit is inferred. Legacy v1/v2
bundles retain their original parser for replay. This correction is not installed
in the pinned v1.1.0 release until separately integrated and deployed.
