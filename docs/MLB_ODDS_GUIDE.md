# MLB Bet Sheet operating guide

The local `/mlb` page is a market-only saved view governed by
[the adopted feature contract](MLB_BET_SHEET.md). This guide describes the unified
refresh/presentation follow-up to PR #59. Source integration, deployment and live
commissioning have separate Owner authorization; a source guide does not establish
which revision is running locally.

## Open and read

Use the existing local application and select **MLB**. The server remains
`nfl_refresh.py`, with the existing Python environment and explicit local data root:

```sh
python nfl_refresh.py --root "$HOME/PopsEdge" --port 8766
```

Open `http://127.0.0.1:8766/mlb`. Construction of the MLB store and every MLB read
are inert: they neither create MLB data directories nor acquire provider data.
The existing NFL application's startup behavior is unchanged.

**Date** selects the official MLB schedule date. Today/Tomorrow follow Central
Time; displayed times use Central with daylight-saving adjustments. This does
not change official game identity, stored UTC observations or market-rule wording.
**Team / All teams** filters the saved view. **Omit completed games**, unchecked
by default, hides verified completed games; in-progress and unresolved results
remain visible. Neither filter narrows retrieval or requests provider data.

Each side is that team's own YES contract. **Last captured** shows its saved buy
ask in cents before fees, with its original capture time. These are independent
observations, not simultaneous prices, guaranteed availability or closing prices.
Missing prices are not zero. The count line describes saved captures, not current
executable offers. No model, edge, holdings or order entry is supplied.

Status and verified final scores appear beneath Match. Only the winning YES
contract receives a green check. This denotes a sporting result, not Kalshi
settlement, payout or profit. Unknown or contradictory results receive no winner.
Elapsed scheduled start does not establish completion. Details show the saved
capture table and observation time; secondary evidence retains exact market rules,
request receipts and original calculations. Unrecognized rules withhold new prices.

## One explicit refresh

**Refresh MLB sheet** operates on the selected date:

- Today or a future date in the current calendar season: retrieve the complete
  official schedule/status/results, then the complete open KXMLBGAME catalog and
  supported team YES books for eligible pregame games. Skip Kalshi when no game
  is eligible. There is no in-play price retrieval.
- A past saved date in the current season: retrieve official schedule/results only
  and retain compatible original price captures. Never retrieve past prices.
- An unsaved past date or unsupported season: refresh is unavailable. Absence of
  saved prices is not repaired through retrospective acquisition.

While a refresh runs, the browser reads local progress; those reads do not repeat
acquisition. Completion has one visible outcome, including partial success.

A complete zero-game schedule is distinct from failed official discovery. A failed
schedule preserves the prior selected sheet and stops dependent price acquisition.
If official results succeed but Kalshi discovery fails, valid results may update
while the sheet reports odds unavailable and retains compatible older captures.
Partial catalogs never supply matching authority or book requests. Individual
missing/invalid books produce visible price gaps or explicitly dated prior captures.
Storage publication or clock validation failure preserves the prior selection.

Current-price eligibility ends at 300 seconds from the oldest required request
start (schedule, catalog or book), or scheduled start, whichever comes first.
Expired captures stay visible as dated history. Clock uncertainty cannot make
old prices current. All ordinary numeric displays use at most two decimal places;
downloads retain exact values.

## Saved material and recovery

The app uses `<root>/Data/MLB/odds/`, outside a source checkout. Each refresh has
an immutable attempt directory with original responses, request start/end receipts
and errors. Complete/partial result bundles have a hash inventory written last.
An atomic per-date record selects a result and records the latest attempt.
References to older price captures preserve their source bundles and times rather
than copying them as newly acquired quotes. Changed games, participants, starts,
doubleheaders or incompatible/ambiguous contracts cannot inherit an old quote.
These operational files confer no scientific or wagering authority and are not
inputs to the scientific collector.

Downloads expose the verified selected bundle and referenced price-source evidence.
Failed acquisition receipts remain in the attempt directory. No retention cleanup
is automated. Back up the odds directory with normal local data backups.

- **Saved read failure or uncertain action outcome:** use the conditional **Retry
  loading saved sheet** button. It reads local data only. While a different date
  loads or its read fails, the previous date's table is cleared. Failures persist
  through filtering and display updates. A successful local read resolves a read
  failure; a failed action remains visible until a new saved attempt establishes
  its outcome or a later explicit refresh succeeds.
- **Provider failure or missing price:** read the outcome and retry the main
  refresh manually. A new attempt has new source times; it does not repair history.
- **Interrupted refresh:** ensure another instance is not still refreshing before
  starting another manual attempt. Prior selected history remains available.
- **Clock warning:** check the clock, restart the app and reload the page. Do not
  adjust source timestamps to make prices current.
- **Storage/integrity warning:** preserve files, check disk access and free space,
  and investigate. Changed evidence is withheld. Never edit receipts/manifests to
  bypass validation.
- **Competing writer:** wait for it to finish or stop that instance. Lock-file
  presence alone is harmless; the operating system owns the lock.

Requests use fixed public MLB/Kalshi hosts without credentials, redirects or
automatic retries. Bounds remain 8 MiB per response, 50 catalog pages, 50 official
games and 240 seconds before another request starts; individual request chronology
is bounded at 20 seconds. A started request may finish after the overall bound.
Reaching a bound is visible failure or partial output, never complete discovery.

Accepted limits include manual local operation/recovery, current-season scope,
supported rule families, missing observations and trusted local files/clocks.
Offline tests do not claim live-provider commissioning. Scientific reporting,
collector state, model evaluation and financial settlement remain separate.

## Offline regression

`tests/mlb_odds_browser.cjs` exercises the actual page with intercepted fixtures.
With Playwright available to Node and Chrome installed, run
`node tests/mlb_odds_browser.cjs`. It covers failures, date ordering, conditional
recovery, completed-only filtering, unified refresh and saved-price presentation.
Python tests cover parsing, immutable lifecycle, source integrity, partial outcomes
and the real localhost action boundary without live provider acquisition.
