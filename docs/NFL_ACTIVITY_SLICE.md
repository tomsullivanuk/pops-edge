# NFL activity markers — owner-requested extension

The owner supplied a Kalshi activity CSV and requested identifying existing wagers
within the NFL Bet Sheet. This authorizes a local import/presentation extension,
not account access, orders, inferred current balances, or deployment.

Retain the exact supplied CSV in the immutable board bundle with its digest and
actual import time. Count Trade rows only; Order rows are not additional fills.
Read UTF-8 BOM safely, comma-grouped decimal quantities, side, price, fees and
aware Original_Date. Match exact tickers to the preserved supported market rules,
then associate YES with that team and NO with its opponent. This association is
independent of which equivalent route the table currently displays.

The export does not carry an explicit buy/sell action. Therefore show recorded
wager activity, not open positions, net quantity, remaining stake or P&L. Retain
individual trades, including both directions and any visible subsequent settlement.
Never collapse opposite-side trades into an inferred balance. Duplicate identical
Trade rows are ambiguous and must be flagged rather than silently doubled or
deduplicated. Unsupported/unmatched NFL records remain visible diagnostics.
Other sports are counted as outside this NFL view. Missing export means not
loaded; no matching rows means none recorded in this file, not no account position.

All annotations have their own import time; a new activity export can postdate
the quote snapshot without backdating it. An activity-only update creates a new
bundle, preserves the original comparison/build times, and records overlay time.
It does not rerank games, change probabilities, refresh quotes or place orders.
No accumulation across exports; each import replaces the displayed activity
snapshot in a new bundle. Current-position reconciliation remains future work.

## Owner-requested wager and payout display

The table now shows outcome-level recorded purchase illustrations: Wagered
(including actual recorded fees), ELWAY expected gross payout, and gross payout
if the row's team wins. Quantity × recorded price + actual fee determines paid
amount; quantity × ELWAY central contract value determines expected gross return.
Tie return is half the quantity; loss return is zero. Details include expected net
return after recorded cost. These figures explicitly assume purchases still held,
not independently established current holdings. Settled or duplicate-flagged
records suppress totals and request review. Missing records display a dash, not
zero. Equivalent route selection does not change the recorded purchase price.

ELWAY Contract and Difference after fee replace the former four comparison
columns. Win probability and before-fee difference move into Details. The default
presentation order and positive filter now use the after-fee difference; preserved
comparison evidence and internal game scores remain unchanged.

## September 10 settlement extension

New activity overlays use nfl-activity-settlements-v2; legacy v1 data remains
replayable. Preserve supported YES/NO settlement rows, owned quantities, result,
reported average prices and derived gross payout reconciled with the export
amount. Do not label Profit_In_Dollars as realized profit. Flag duplicate or
unreconciled settlement amounts; show cost-basis discrepancies in Details and
suppress assumed open-stake totals for settled trades. Settled games lose their
current purchase route in presentation, preserving original comparison data.
Exact date/away/home/team ticker matching can identify closed activity even when
absent from the open-market catalog; this does not validate pricing/settlement
rules for any new quote. See NFL_REFRESH_GUIDE.md.
