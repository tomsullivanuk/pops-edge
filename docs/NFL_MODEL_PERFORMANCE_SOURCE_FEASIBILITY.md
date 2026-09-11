# NFL Model Performance — archived-source feasibility

Inspected September 11, 2026, read-only. No new provider request. Sources are local
immutable inputs, not fixtures added to Git. This is field feasibility, not
production-adapter validation or admission of historical research observations.

## Official NFL outcome

Archive relative to `/Users/tom/PopsEdge/Data/NFL/`:
`schedules/schedule-9499ae796d584f9caa57d2859fbaf2eb/source.html`.
Receipt completed `2026-09-11T20:54:42.339455+00:00`.
Raw SHA256: `4ba7d7892edac4ab7307ed667c9729c0034439f43de1c1c5d58552a78fba9ff4`.

The embedded Next.js `useFetchFootballWeeklyGameDetails` query contains the
2026 REG Week 1 game `a8fc08da-4feb-11f1-abca-2c54536568a9`, SF at LAR:

- Outer status: `SCHEDULED`.
- `summary.gameId`: matches the game ID.
- `summary.phase`: `FINAL`; `summary.quarter`: `END_OF_GAME`.
- `summary.homeTeam.score.total`: 7; away total: 27.
- Summary home/away team IDs match their corresponding game team IDs.
- `summary.startTime`: `2026-09-11T00:37:25Z`; scheduled time:
  `2026-09-11T00:35:00Z`. These are distinct fields, not interchangeable times.

The current `nfl_schedule.parse` extracts outer status but discards the summary.
A new versioned outcome derivation can use the preserved raw source; do not
change old schedule replay semantics. This example explains why outer status
alone is insufficient. Apply explicit summary-field precedence only after
identity, final-phase and score validation; retain the metadata discrepancy.

## Kalshi midpoint

Archive relative to the same data root:
`boards/board-450cf67ab8a44ef9be1f7b3d9ca83aa5/inputs/kalshi/response-003.body`.
Raw SHA256 verified against request manifest:
`1ac27e5cd786b97e72f764df98caae7f4594ce7d0693ff8cf5a2e9a053188e4b`.
Ticker: `KXNFLGAME-26SEP10SFLAR-LAR`.
Request: `2026-09-11T02:12:30.957805+00:00` through
`2026-09-11T02:12:31.175117+00:00`, HTTP 200.

`orderbook_fp.yes_dollars` and `.no_dollars` contain price/quantity bid levels.
Best YES bid = .4100; best NO bid = .5800; YES ask = .4200;
midpoint = .4150, without fees. Decimal arithmetic was checked. This particular
capture is AFTER the game's start and is therefore **ineligible** for a pregame
baseline. It establishes field availability only; do not backfill research with it.
Catalog rules, game matching and open-market state must still be validated for
each future observation, using the existing retrieval/matching boundaries.

## Conclusion and remaining validation

Both required field families exist in saved official/provider responses. A new
provider service is not demonstrated to be necessary. Readiness is limited to
these observed examples: production implementation still needs fixtures for
nonfinal, missing-summary, contradictory IDs, score corrections, ties, missing
books and unsupported rules, plus existing replay regressions. No claim is made
that all archived games have valid final results or qualifying pregame prices.

The documentation slice can proceed to review. The next implementation can build
a versioned outcome adapter and weekly selection/scoring against saved fixtures;
live capture activation remains a separate authorization gate.
