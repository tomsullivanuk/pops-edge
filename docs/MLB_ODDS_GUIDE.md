# MLB Bet Sheet operating guide

This v1.3 candidate adds `/mlb` to the existing local NFL application. It is a
market-only view, governed by [the adopted contract](MLB_BET_SHEET.md).
Integration and live commissioning require separate Owner authorization.

## Open and read

Use the existing local application entry point and select **MLB**. The server
entry remains `nfl_refresh.py`; no second server or deployment is required. A
separately authorized launch uses the existing Python environment and explicit
local data root, for example:

```sh
python nfl_refresh.py --root "$HOME/PopsEdge" --port 8766
```

Open `http://127.0.0.1:8766/mlb`. Construction of the MLB store and every MLB read
are inert: they neither create MLB data directories nor acquire provider data.
The existing NFL application's own startup behavior is unchanged.

Today is Eastern time. Select another date, a team, or whether to include games
that have started. These are saved-view operations. A date without saved data
shows that absence. **Reload saved sheet** retries a local read without collecting
provider data. While a different date is loading or its read has failed, the
previous date's table is cleared. Read failures and refresh-request failures
remain visible through filtering and price expiry. A successful read resolves a
read failure; a failed refresh request remains visible until a new saved attempt
establishes its outcome or a later explicit refresh succeeds. Past dates may be
read but cannot be refreshed. Future
acquisition is limited to the current calendar season; unsupported postseason,
changed schedules and unresolved games remain visible without prices.

Each side is that team's own YES contract. The principal price is an observed
buy offer for at least one contract, in cents before fees. Prices are independent
captures. Missing is never zero. This view has no model, edge, holdings or order
entry. The market's complete retained rules remain readable in Details; unusual
or unrecognized rules withhold the quote.

## Refresh explicitly

**Refresh MLB odds** retrieves the official selected-date schedule, then every
page of the open KXMLBGAME market catalog, then supported team YES order books.
Team/view filters do not narrow collection. The browser polls the local attempt
status while the action runs; those reads do not repeat acquisition.

A complete schedule with zero games is distinct from a failed schedule request.
Failure of schedule or complete catalog discovery preserves the previous saved
sheet and its original dates, with a visible failed outcome. Previous prices
are available as history in Details, never passed off as results of that attempt.
An individual missing/invalid book permits a completed sheet with visible gaps.
An independently valid other side remains usable until its own expiry.

Current eligibility ends at 300 seconds from the oldest required request start
(schedule, catalog or book), or scheduled start, whichever comes first. The
screen reassesses while open and on focus return without retrieving data. A
scheduled start passing does not claim that the official game is completed.
Clock uncertainty withholds current prices. Display rounding is at most two
decimals; downloads retain exact values.

## Saved material and manual recovery

The application uses `<root>/Data/MLB/odds/`, outside a source checkout. Each
refresh has a unique immutable attempt directory with original response bodies,
request start/end receipts and errors. Successful or partial results have a
hash inventory completed last. A separate atomic per-date record selects the
result and records the latest attempt. These operational files confer no
scientific or wagering authority and are not inputs to the scientific collector.

Downloads expose the validated selected sheet, its manifest and original source
responses. Failed-attempt receipts remain in the local attempt directory;
failed outcome and time remain visible on the screen. No retention cleanup is
automated. Back up the dedicated odds directory with normal local data backups.

- Provider failure or missing price: read the visible reason and retry manually.
  A new attempt has new source times; it does not repair past observations.
- Interrupted refresh: ensure another local instance is not still running, then
  perform a new refresh. Prior selected history remains available.
- Clock warning: check the computer clock, restart the local application and
  reload the page. Do not adjust source timestamps to make old prices current.
- Storage/integrity warning: preserve existing files, check disk access and free
  space, and investigate before retrying. Changed evidence is withheld. Do not
  edit receipts or manifests to bypass validation.
- Competing writer: wait for it to finish or stop that local instance, then retry.
  Stale lock-file presence alone is harmless; the operating system owns the lock.

Requests use fixed public MLB/Kalshi hosts without credentials, retries or
redirects. Bounds are 8 MiB per response, 50 catalog pages, 50 official games and
240 seconds before starting another request. An already-started request may
finish after the overall bound; individual request chronology is bounded at
20 seconds. Reaching a bound is visible missing/failure, not complete discovery.

Accepted limitations include manual operation and recovery, supported rule
families only, missing observations, trusted local files/clocks, and no live
commissioning claim from offline tests. See [release sequencing](RELEASE_PLAN_v1.3.md).

## Offline browser regression

`tests/mlb_odds_browser.cjs` runs against the actual page with intercepted fixture
responses only. With Playwright available to Node and Chrome installed, run
`node tests/mlb_odds_browser.cjs`. No live local app or provider connection is
needed. It asserts request-failure persistence, date/read ordering, manual
recovery, cross-date actions and existing unavailable-price states.
