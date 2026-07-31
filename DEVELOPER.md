# Pops' Edge Developer Guide

Pops' Edge is the durable product name. The workflows documented below are the
World Cup implementation shipped as v1.0.0. World Cup-prefixed artifacts remain
unchanged for baseline compatibility.

The planned v1.1.0 work and the repository rename procedure are documented in
`docs/RELEASE_PLAN_v1.1.0.md` and `docs/REPOSITORY_RENAME.md`. The standard PR
workflow and completion-report format are in `docs/CODEX_WORKFLOW.md`.

## Offline event contracts

PR3 adds an offline contract layer without connecting it to the v1.0.0 World
Cup workflow:

- `event_contracts.py` defines reusable canonical event identity, native
  identifiers, independently discovered source mappings, participants,
  provenance, structured validation reasons, candidate evaluations, and
  matched/ambiguous/rejected reconciliation results.
- `mlb_contracts.py` defines MLB teams and games, preserves `gamePk`, and keeps
  schedule, pitcher, status, and explicit lineage evidence outside immutable
  event identity.
- `tests/fixtures/mlb_contract_cases.json` and
  `tests/test_event_contracts.py` exercise the contracts entirely offline.

`gamePk` is authoritative for MLB identity. A retained `gamePk` remains the
same event through schedule changes; a new `gamePk` creates a distinct event
that may be linked by explicit lineage. Similar teams, dates, or times never
override conflicting `gamePk` evidence.

`CanonicalEvent.native_identifiers` and participant native identifiers accept
only authoritative `SportNativeIdentifier` values. Forecast, market, and other
provider mappings use separate frozen `SourceMapping` records linked by
canonical entity ID. Discovering such a mapping therefore does not reconstruct
or mutate event identity. `MLBGame` repeats season, teams, and `gamePk` only as
MLB-specific convenience fields; construction rejects any disagreement with
the nested canonical event.

Observations are frozen, timezone-aware records. Missing pitchers create a
valid incomplete pitcher observation rather than invalidating the game.
Changed pitchers, schedule changes, and status changes create new observations
instead of replacing prior evidence. Same-identity postponements and
suspensions are represented by successive observations; lineage relates
distinct events only when a source explicitly supplies that relationship.
Suspension/resumption lineage is therefore valid only if the source explicitly
relates distinct event identities; self-lineage is rejected.

Rejected reconciliation retains no selected or eligible candidate.
`CandidateEvaluation` records may nevertheless preserve each considered
canonical event ID, mappings evaluated, evidence, and structured conflict
reasons. This audit information survives deterministic serialization without
making a candidate operationally available.

Deterministic tagged JSON is the adapter/fixture boundary. No database,
provider client, market contract, forecast ingestion, persistence, or World Cup
integration is part of PR3.

## Offline forecast contracts

PR4 adds `forecast_contracts.py` without connecting it to a provider or the
World Cup workflow. It defines immutable Forecast Provider, Model, Version,
Outcome, Published Probability, Distribution, provider-assumption, validation,
disposition, relationship, Observation, and collection-timing contracts.
Durable objects use one stable chain: Model references Provider, Version
references Model, and Observation references only Version. Observations do not
copy provider, model, or version metadata. A bundle validator checks the full
assembled hierarchy, including the provenance provider.

Published probabilities use exact `Decimal` values and separately preserve the
source representation, source scale, and declared decimal precision. A
distribution canonicalizes its non-semantic outcome order by outcome ID,
retains the exact observed total, and calculates its tolerance as the sum of
the half-rounding intervals implied by every published value. Percent values
convert their interval to probability scale. Totals outside that tolerance are
preserved and classified invalid; values are never rounded or normalized.

Forecast validation (`valid`, `incomplete`, `invalid`) remains separate from
provider disposition (`active`, `corrected`, `withdrawn`) and from PR3 event
reconciliation (`matched`, `ambiguous`, `rejected`). Unresolved observations
retain source evidence and candidate evaluations without claiming a Canonical
Event. Provider assumptions explicitly represent reported, undisclosed, or
unknown states. Revision relationships are separate immutable records rather
than fields on an observation; a helper validates appended evidence and derives
latest-known and effective disposition without rewriting history. Collection timing reports before-start,
at-or-after-start, or unknown-start facts from supplied schedule evidence; it
does not decide actionability.

The shared tagged serializer now supports exact decimals and dates in addition
to its existing timezone-aware datetimes and enums. Tuple-like collections are
canonicalized by their contracts before serialization, and round trips retain
the original published evidence. PR4 adds no network collection, provider
approval, persistence, weights, freshness rules, markets, edges, reports, or
wagering behavior.

## Series / Observation implementation guidance

PR5A establishes a general rule for time-varying evidence:

```text
Durable Identity -> Immutable Observations -> Derived Views
```

Canonical Event already owns successive schedule, pitcher, and status
observations; Current Game State is computed. PR6 will introduce Forecast
Series as the durable identity for one Provider, Model, Version, and Canonical
Event combination. Each provider update must append a Forecast Observation.
Current Forecast, Latest Pregame Forecast, Forecast History, and Forecast
Movement must be derived without mutating or replacing observations.

Keep probabilities, timestamps, assumptions, provenance, validation,
disposition, and observation relationships on Forecast Observation rather than
Forecast Series. Reference Provider, Model, Version, Canonical Event, and Series
instead of duplicating their durable metadata. Policy such as approval,
weighting, freshness, eligibility, edge thresholds, and sizing must remain
outside identity and evidence. PR5A changes no contracts; implementation begins
only in PR6.

## MLB Stats API facts adapter

`mlb_stats_api.py` contains the bounded read-only schedule client and facts
adapter. `MLBStatsAPIClient.schedule_request()` constructs the supported
`/api/v1/schedule` route and stable parameters. `fetch_schedule()` accepts an
injectable transport, uses an explicit timeout, retries only transient transport
failures and HTTP 429/500/502/503/504 responses, and treats other client errors
as permanent. Importing the module or constructing the adapter performs no
network request.

The client captures exact response bytes before JSON parsing. Raw evidence
stores `raw_response_sha256` for those bytes and `canonical_json_sha256` for
the parsed JSON serialized with sorted keys and compact separators. The raw
digest proves byte identity; the canonical digest supports deterministic
semantic comparison. Evidence also retains the endpoint, parameters, status,
collection time, record IDs, source URL, and adapter version.

The adapter uses source `gamePk` and MLB team IDs to construct the existing
`MLBGame`, then emits independent immutable `ScheduleObservation`,
`GameStatusObservation`, and `PitcherObservation` values. Each game result has
an explicit `complete`, `partial`, or `rejected` outcome. Rejected results
cannot expose a Canonical Event or normalized observations. Results and issues
are sorted deterministically and round-trip through tagged JSON.

Parsing is deliberately partial-success. Missing optional venue, probable
pitchers, source update time, or paired doubleheader metadata creates stable
issues and incomplete component provenance without invalidating trustworthy
event identity. Missing or malformed `gamePk`, team identity, or required
timezone-aware start time withholds the event and all dependent observations
while retaining raw evidence. Same-`gamePk` schedule and pitcher changes create
new observations. Collection time is always preserved, but source timestamps
remain `None` unless `lastUpdated` is explicitly present and valid; collection
time is never substituted. Unsupported status affects only status evidence.
`explicit_lineage()` requires a named direct relation field and the related
`gamePk`; it never infers lineage from similarity.

The offline fixture is `tests/fixtures/mlb_stats_api_schedule.json`, and
`tests/test_mlb_stats_api.py` covers client failures, identity, schedules,
status, pitchers, lineage, partial success, raw hashing, serialization, and
ordering. The separately invoked read-only smoke path is:

```bash
./venv/bin/python smoke_mlb_stats_api.py YYYY-MM-DD [--game-pk GAME_PK]
```

It is intentionally excluded from automated validation and must not be run
without explicit authorization. It requires a date, prints concise identifiers,
outcomes, and issue codes rather than payloads, writes nothing, and exits
nonzero on transport failure or unsafe rejection. PR5 does not persist raw
payloads or normalized contracts and does not schedule collection.

## Workflows

`update_all.sh` is the combined update workflow. It changes into the project directory, activates `venv/` when needed, then runs the standalone workflows in order:

1. `./update_wagers.sh`
2. `./update_worldcup.sh`

Keep this script thin. The wager and World Cup scripts remain usable on their own, so shared behavior should stay in the underlying Python modules or the standalone scripts unless there is a specific reason to coordinate it in `update_all.sh`.

`wcup` is the main board refresh workflow. It should run the same sequence as `update_worldcup.sh`:

1. `process_silver.py` normalizes the latest Silver forecast CSV into `Silver_Current.xlsx`.
2. `kalshi_pull.py` pulls current Kalshi World Cup markets into `Kalshi_Current.xlsx`.
3. `process_silver_futures.py` normalizes the latest Silver futures CSV into `Silver_Futures_Current.xlsx`.
4. `build_value_board.py` combines Silver probabilities, Kalshi prices, active wager exposure, and portfolio summaries into `WorldCup_ValueBoard.xlsx`.
5. `build_futures_value_board.py` creates `WorldCup_Futures_ValueBoard.xlsx`.
6. `build_ladder_board.py` creates `WorldCup_Ladder_Board.xlsx` from positions with positive remaining contracts.
7. `build_web_betsheet.py` creates `WorldCup_ValueBoard.html`.
8. `build_web_futures_betsheet.py` creates `WorldCup_Futures_ValueBoard.html`.
9. `build_web_ladder_board.py` creates `WorldCup_Ladder_Board.html`.

`update_worldcup.sh` refreshes both match and futures outputs plus the active-position Ladder Board. It archives both Silver workbooks and all board workbooks, copies Excel boards and HTML dashboards to the existing iCloud World Cup folder, and opens the three HTML boards when run standalone. `update_all.sh` suppresses the child-script open steps, then opens `World_Cup_Bet_Log.html`, `WorldCup_ValueBoard.html`, `WorldCup_Futures_ValueBoard.html`, and `WorldCup_Ladder_Board.html` exactly once. Its success notification reports wagers imported, match candidate bets, and futures candidate bets; unavailable workbook counts do not fail an otherwise successful run.

`build_futures_value_board.py` filters out `KXWCGAME-` match markets and classifies futures markets from the event ticker, market ticker, game, subtitle, and market title. `kalshi_pull.py` includes these World Cup event patterns:

```text
KXWCGAME-*              match winner markets
KXWCROUND-26RO16-*      Round of 16 qualifier markets
KXWCROUND-26QUAR-*      Quarterfinal qualifier markets
KXWCROUND-26SEMI-*      Semifinal qualifier markets
KXMENWORLDCUP-26-*      World Cup winner markets
```

The outright winner markets use two-letter ticker suffixes, such as `KXMENWORLDCUP-26-AR`, but include team names in `yes_sub_title`; the futures board matches them by normalized outcome name.

`update_wagers.sh` refreshes Bet Log outputs from the latest Kalshi activity export. It activates `venv/` when needed, runs `import_wagers.py`, builds `World_Cup_Bet_Log.html` with `build_web_betlog.py`, prints a short wager summary, and opens the web Bet Log. Closing Price is manually entered in `World_Cup_Bet_Log.xlsx`; `import_wagers.py` preserves it and automatically calculates CLV and CLV % when Closing Price is present.

After placing a wager, download Kalshi Activity -> All -> This Month, then run `./update_all.sh` to refresh wagers first and then refresh the World Cup board. You can still run `./update_wagers.sh` or `./update_worldcup.sh` independently for narrower updates.

## Pipeline Dependencies

The pipeline is file-based:

```text
data-*.csv -> process_silver.py -> Silver_Current.xlsx
Kalshi API -> kalshi_pull.py -> Kalshi_Current.xlsx
Silver_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_value_board.py -> WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.xlsx -> build_web_betsheet.py -> WorldCup_ValueBoard.html
futures CSV -> process_silver_futures.py -> Silver_Futures_Current.xlsx
Silver_Futures_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_futures_value_board.py -> WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.xlsx -> build_web_futures_betsheet.py -> WorldCup_Futures_ValueBoard.html
Kalshi-Recent-Activity-*.csv + match/futures Value Boards + Kalshi_Current.xlsx + prior World_Cup_Bet_Log.xlsx -> import_wagers.py -> World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.xlsx -> build_web_betlog.py -> World_Cup_Bet_Log.html
```

Shared filenames, sheet names, archive paths, and common column names live in `config.py`.

`import_wagers.py` writes one unified Bet Log for match and futures wagers. `Market Type` distinguishes `Match` from `Futures`; futures rows populate `Stage`, `Team`, and the human-readable YES proposition in `Outcome`, while `Match` and `Match Date` remain blank. Match rows retain their existing match fields, and `Team` is blank for tie contracts.

Enrichment combines `WorldCup_ValueBoard.xlsx` and `WorldCup_Futures_ValueBoard.xlsx` by `market_ticker`. `Kalshi_Current.xlsx` is the fallback source for proposition names, including champion tickers with two-letter suffixes. The importer normalizes match dates after reading prior manual values and current match Value Board values. The selection order remains prior manual value, current Value Board value, then ticker-derived fallback. It also carries forward manually entered Closing Price from the prior wager log, calculates CLV and CLV % for BUY YES and SELL YES positions, and leaves CLV fields blank when Closing Price is blank unless prior CLV values are available as a fallback.

The wager log records `Exit Contracts` and `Remaining Contracts`. Settlements
set remaining contracts to zero; early exits subtract exited contracts from
entry contracts. The Ladder Board accepts only `Open` and `Partially Closed`
rows with positive remaining contracts.

## Ladder Board

`build_ladder_board.py` combines active match and futures wagers with their
current Value Board rows. BUY YES positions use YES entry/current prices and
Silver probability. SELL YES positions are represented as NO positions using
one minus the YES entry, ask, and Silver probability.

For positive remaining edge, the three sell tiers are entry plus half the edge,
Silver fair value, and fair value plus 15 cents. Prices use half-up cent
rounding and are capped at 99 cents. Contracts are allocated 30% / 30% /
remainder, so the tiers sum to the open whole-contract count. Rows are ordered
by urgent/near status, descending current edge, event, market, ticker, and side.
`build_web_ladder_board.py` renders the same ordered data and supports both
empty and populated boards.

`kalshi_pull.py` retries timeouts, connection/incomplete-response failures, and
HTTP 429/500/502/503/504 responses with bounded backoff. Each retry repeats the
same cursor page so pagination does not skip events.

## Value Board Workbook

`build_value_board.py` writes the existing Bet Sheet outputs unchanged, then adds a `Portfolio` worksheet with four stacked sections:

```text
Portfolio Summary
Open Positions
Exposure by Team
Exposure by Match Date
```

The Portfolio worksheet reads active wagers from `World_Cup_Bet_Log.xlsx`, using `Open` and `Partially Closed` statuses, and enriches them with match, outcome, team, Silver probability, and current bid/ask data from the merged Value Board. BUY YES current value uses the current Yes Bid; SELL YES current value uses `1 - Yes Ask`.

## Futures Value Board Workbook

`build_futures_value_board.py` writes the same core workbook tabs as the match board:

```text
Bet Sheet
Run Metadata
Candidates
Value Board
Silver Normalized
Kalshi Normalized
Definitions
```

The futures Bet Sheet columns include `Stage`, `Team`, `champion_proxy_candidate`, `strong_champion_proxy`, `Action`, `Silver`, `Market Price`, `Edge`, `ROI`, `Quarter Kelly`, `proxy_kelly_dollars`, `proxy_contracts`, the four ladder price/contract pairs, `ladder_expected_return`, `ladder_expected_profit`, `Stake on $500`, `Bucket`, `Volume`, `event_ticker`, `market_ticker`, `Position`, `Current Action`, `Entry Price`, `Current Value Change`, `Stake`, and `Status`. It uses the same `BANKROLL = 500`, `MIN_EDGE = 0.05`, and A/B/C bucket thresholds as `build_value_board.py`, but divides full Kelly by four rather than two.

`champion_proxy_candidate` is `YES` when a team has positive BUY edge in R16, quarterfinal, semifinal, and Champion markets. `strong_champion_proxy` adds the requirement that Champion BUY edge is at least 35% of average R16/QF/SF BUY edge. Final markets are classified when available but are not part of either gate.

`proxy_kelly_dollars` is shown only for Champion Proxy teams. It keeps the ordinary Champion Quarter Kelly stake and adds 60% of the R16/QF/SF Quarter Kelly stakes, reflecting that Champion is being used as a proxy for several correlated advancement bets.

Champion Proxy sell ladders use the Champion BUY price as entry, allocate Proxy Kelly into contracts, then suggest four resting sell orders at 1.5x, 2.25x, 3.25x, and 4.5x entry. Contract allocation is 30% / 30% / 20% / remainder. The individual ladder price/contract columns stay in Excel for auditing, while the futures HTML shows a compact `proxy_sell_ladder` summary plus expected return/profit.

Active futures wagers come from the unified `World_Cup_Bet_Log.xlsx`, match on `market_ticker`, and include `Open` and `Partially Closed` statuses. The futures HTML view omits `event_ticker` to reduce width while retaining `market_ticker` and the active-position fields.

Silver futures CSV detection requires the columns `Team`, `R16`, `Qtr`, `Semi`, `Final`, and one of `Champ 🏆`, `Champ`, or `Champion`. The processor archives the selected source CSV under `archive/silver_futures_raw/` and the processed workbook under `archive/silver_futures_processed/`.

## Expected File Locations

The project expects to live at:

```text
~/pops-edge
```

Silver forecast downloads may be in either:

```text
~/Downloads/data-*.csv
~/pops-edge/data-*.csv
```

`process_silver.py` requires the match columns `Date`, `Team`, `Win`, `GF`, `Opponent`, `Win.1`, `GF.1`, and `Draw`. It selects the newest CSV with that schema and only archives other match-schema CSVs, so futures exports remain available to the futures processor.

Silver futures downloads may be named `data-*.csv` or include `futures` in the filename, but must have the futures columns listed above. They may be in either `~/Downloads` or `~/pops-edge`. `process_silver_futures.py` selects the newest CSV with the futures schema and skips newer match-schema files.

Kalshi activity exports may be in either:

```text
~/Downloads/Kalshi-Recent-Activity-*.csv
~/pops-edge/Kalshi-Recent-Activity-*.csv
```

Generated files are local outputs and should not be committed:

```text
Silver_Current.xlsx
Kalshi_Current.xlsx
WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.html
Silver_Futures_Current.xlsx
WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.html
WorldCup_Ladder_Board.xlsx
WorldCup_Ladder_Board.html
World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.html
archive/
```

## Tests

Run the full test suite with:

```bash
bash -n update_all.sh
bash -n update_wagers.sh
bash -n update_worldcup.sh
./venv/bin/python -m unittest discover -s tests
./venv/bin/python -m py_compile process_silver_futures.py build_futures_value_board.py build_web_futures_betsheet.py
```

Tests use temporary directories and sample fixtures under `tests/fixtures/` so they do not overwrite live workbooks. Silver processor tests include mixed match/futures downloads and verify that each processor selects the newest valid file for its own schema.

`tests/test_event_contracts.py` validates canonical MLB identity, team mappings,
doubleheaders, postponement and replacement semantics, suspension/resumption,
missing and changed pitchers, conflicting source observations, fail-closed
reconciliation, immutability, and deterministic serialization round trips.

`tests/test_forecast_contracts.py` and
`tests/fixtures/forecast_contract_cases.json` validate the provider/model/version
hierarchy, exact published probabilities, precision-aware distributions,
assumptions, timestamps, validation and disposition, immutable revision
relationships, matched/ambiguous/rejected reconciliation, neutral collection
timing, canonical serialization, and round trips entirely offline.

The Value Board pipeline test checks the Portfolio worksheet section layout, open-position enrichment, summary totals, and team/date exposure rollups while preserving the existing Bet Sheet assertions. Futures tests cover Silver futures processing, a champion edge example, an advancement edge example, and the generated sortable futures web Bet Sheet. Wager tests cover Match Date normalization, Round-of-16 settlement, two-letter champion ticker enrichment, and the generated sortable unified web Bet Log.

## Git Workflow

Use small commits. Before committing, run tests and inspect staged files:

```bash
./venv/bin/python -m unittest discover -s tests
git status
git diff --stat
git diff --cached --stat
```

Commit source, docs, tests, and fixtures. Do not commit generated workbooks, HTML reports, archives, virtualenvs, downloaded activity files, lock files, or secrets.
