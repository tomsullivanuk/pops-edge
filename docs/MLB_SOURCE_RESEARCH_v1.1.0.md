# MLB Source Research for Pops' Edge v1.1.0

**Status:** PR2 decision, 2026-07-28
**Production status:** no recurring MLB collection is authorized yet

**Roadmap amendment, 2026-09-01:** the Product Owner approved a separate PR19
self-hosted native-model track in parallel with PR18 external-supplier work.
[`gmalbert/baseball-predictions` at audited commit `685cdff`](https://github.com/gmalbert/baseball-predictions/tree/685cdff166df6eb84f69d8c0b6ac291713511aab)
was evaluated as a possible design and reproducibility reference, not an
admitted provider, licensed dependency, or trusted model artifact. The audited
tree has no apparent license;
its active [legacy feature path](https://github.com/gmalbert/baseball-predictions/blob/685cdff166df6eb84f69d8c0b6ac291713511aab/src/models/features.py)
explicitly uses same-season full-season aggregates, and its own
[quarantine policy](https://github.com/gmalbert/baseball-predictions/blob/685cdff166df6eb84f69d8c0b6ac291713511aab/config/model_quarantine.yaml)
rejects the packaged legacy models. PR19A selected the independently
implemented clean-room path in the
[rights decision](PR19A_RIGHTS_DECISION_v1.1.0.md): no upstream code, tests,
configuration, prose, model, data, asset, dependency lock, or generated output
may be copied, modified, executed, or used. The separate
[Model 0 protocol](PR19A_MODEL_0_PROTOCOL_v1.1.0.md) is native Pops' Edge
authority. No model implementation, activation, forecast collection, or
production authority is granted by this decision.

## 1. Executive conclusion

Use a licensed official-data feed for production MLB schedules, identity,
status, results, rosters, and pitchers. Evaluate Sportradar first: MLB names it
its official global data partner, and Sportradar's schedule schema includes the
MLB integer game ID as `reference`. Pops' Edge should use MLB `gamePk` as its
canonical key and preserve all vendor IDs and mapping evidence. SportsDataIO is
the commercial fallback.

The public MLB Stats API is the best technical reference but is not approved
for automation: MLB's terms prohibit automated scripts from collecting from or
interacting with MLB Digital Properties. PR3 may model `gamePk`; it must not add
a recurring Stats API client.

No public forecast site is approved for production. DRatings is the first
procurement candidate; FanGraphs Game Odds is the preferred comparison.
Automation, retention, stable delivery, timestamps, and model independence
must be confirmed in writing. Dimers is rejected for automation because its
terms prohibit scraping/robots and its model considers betting-market movement.
TeamRankings remains research-only.

Kalshi's public read-only API is suitable. `KXMLBGAME` is the MLB game series.
Observed events contained two mutually exclusive team markets. Preserve and
validate `rules_primary`, `yes_sub_title`, and structured strike data; never
infer YES from ticker text alone. Defer a sportsbook benchmark until one
licensed forecast adapter works; The Odds API is the preferred later candidate.

## 2. Research scope and methods

Research covered canonical games, schedule/status/results, pitchers, three-plus
forecast candidates, Kalshi current and historical data, sportsbook odds,
reconciliation, backfill, and provenance. Work included repository inspection,
official documentation/terms review, one read-only MLB schedule probe, public
read-only Kalshi probes, and observation of public forecast pages without
adding a scraper.

The representative slate was 2026-07-28 and included an ordinary game, a split
doubleheader created by a postponement, a separately postponed game, missing
pitchers, live markets, and recent settlements. Probes wrote only temporary
`/tmp` files and used no credentials, orders, subscriptions, or recurring jobs.
Observations were collected around `2026-07-28T17:43Z`.

Primary evidence:

- [MLB terms](https://www.mlb.com/official-information/terms-of-use?bpexternal=true)
- [MLB–Sportradar partnership](https://www.mlb.com/press-release/mlb-and-sportradar-announce-official-exclusive-global-partnership)
- [Sportradar MLB schedule workflow](https://developer.sportradar.com/baseball/docs/mlb-ig-pulling-schedules)
- [Sportradar lineup feed](https://developer.sportradar.com/sportradar-updates/changelog/global-baseball-api-lineups-endpoints)
- [FanGraphs Game Odds method](https://blogs.fangraphs.com/fangraphs-game-odds/)
- [DRatings MLB predictions](https://www.dratings.com/predictor/mlb-baseball-predictions/)
- [Dimers terms](https://www.dimers.com/terms-of-service)
- [Kalshi historical data](https://docs.kalshi.com/getting_started/historical_data)
- [Kalshi candles](https://docs.kalshi.com/api-reference/market/get-market-candlesticks)
- [The Odds API](https://the-odds-api.com/) and [terms](https://the-odds-api.com/terms-and-conditions.html)

This is product/technical research, not legal advice. “Not approved” means
sufficient permission evidence is absent from the repository.

## 3. Existing Pops' Edge architecture findings

`kalshi_pull.py` has reusable cursor pagination, bounded transient retry,
stable-ticker preservation, and price/volume/open-interest acquisition. Its
World Cup family filters, recognition, matching, filenames, workbook schemas,
and outputs are sport-specific. It does not provide a generic adapter, raw
snapshot reference, publication/collection timestamps, side-mapping evidence,
or immutable forecast-observation model.

Pagination/retry, validation, run metadata, fixed output contracts, and
fixture-backed offline tests are candidates for later reuse. MLB identity,
status, aliases, pitchers, settlement mapping, and freshness stay in MLB
adapters. No v1.0.0 behavior is changed by PR2.

## 4. MLB schedule and identity-source evaluation

The MLB schedule probe returned `gamePk`, UTC `gameDate`, `officialDate`, team
and venue IDs, `doubleHeader`, `gameNumber`, probable-pitcher IDs/names,
structured statuses/reasons, scores, and reschedule fields. On July 28 it
distinguished Cleveland–Cincinnati 824490 (split-doubleheader game 1,
rescheduled from July 27) from 824489 (game 2), and marked Atlanta–New York
823598 postponed with a July 29 reschedule.

MLB publishes no supported contract/rate limit for this use, and its terms
prohibit automated scripts. It is reference/schema evidence only.

Sportradar documents UUIDs plus MLB `reference`, UTC starts, venue time zones,
home/away IDs, doubleheader/game number, postponed/suspended statuses, change
logs, and lineup starters. Before approval obtain price, limits, official-data
entitlement, history, retention/display rights, and a guarantee that
`reference == gamePk`. SportsDataIO documents schedules/results,
projected/confirmed pitchers, odds movement, and historical Vault access, but
its vendor `GameID` needs a verified MLB bridge.

Canonical rules:

1. use `mlb_game_pk`;
2. retain vendor IDs and mapping observations;
3. never key solely by date/team;
4. retain original and current schedule plus lineage;
5. represent doubleheader game number; and
6. reject non-unique mappings.

## 5. Starting-pitcher source evaluation

| Source | Evidence | Decision |
|---|---|---|
| MLB Stats API | probable MLB person ID/name; actual starter reconstructable | reference only |
| Sportradar | lineup `starter: true`; official-data partner | primary candidate, contract-dependent |
| SportsDataIO | projected and confirmed lineups/pitchers | commercial fallback |
| Forecast sites | names or `UNDECIDED`, usually no durable ID | forecast context only |

Probable, confirmed, and actual are immutable observation states. Record
pitcher ID/name/state, source update time if supplied, collection time, and
previous state. Never overwrite a pregame assumption with the postgame starter.

## 6. Prediction-source comparison

**DRatings:** the observed slate showed both probabilities summing to 100%,
pitchers including `UNDECIDED`, game time, moneylines, page update age, and
completed probabilities/results. Its methodology cites previous score and
pitcher data. No supported API/native game ID, durable per-game publication
timestamp, automation/storage permission, or proof of market independence was
established. First procurement candidate only.

**FanGraphs:** Game Odds combines ZiPS and Steamer player projections,
starters, bullpens, and later lineups. It is the strongest transparent,
plausibly market-independent comparison. No supported feed, automation rights,
durable observation timestamps, or historical pregame archive was established.
Preferred comparison conditional on license.

**Dimers:** publishes every-game probabilities/pitchers and updates for
lineups, pitcher changes, weather, and market movement. Its terms limit use to
personal browsing and prohibit page scraping/robots. Reject automated use and
do not treat its blended model as the primary independent forecast.

**TeamRankings:** plausible, but supported API/IDs, timestamps, historical
snapshots, and permission were not established. Research-only.

There is no unconditional primary at PR2 close. If no provider grants written
machine access and retention, production forecast ingestion is blocked. Keep
each provider/model/version/method class and timestamp separate; define no
ensemble weights.

## 7. Kalshi MLB market findings

The series is `KXMLBGAME`, “Professional Baseball Game.” Observed event tickers
encoded original date/time and teams; markets appended a team. Events reported
`mutually_exclusive: true` and two binary team markets. `yes_sub_title`,
`rules_primary`, `custom_strike.baseball_team`, and suffix supported mapping.
`no_sub_title` repeated the YES team and cannot identify the opponent.

Twelve finalized markets were examined:

| Event | Winner YES market | Losing market |
|---|---|---|
| Houston–Los Angeles A | `...HOULAA-HOU` | `...HOULAA-LAA` |
| Boston–A's | `...BOSATH-BOS` | `...BOSATH-ATH` |
| Milwaukee–San Francisco | `...MILSF-SF` | `...MILSF-MIL` |
| Chicago C–St. Louis | `...CHCSTL-CHC` | `...CHCSTL-STL` |
| New York Y–Chicago WS | `...NYYCWS-NYY` | `...NYYCWS-CWS` |
| Atlanta–New York M | `...ATLNYM-NYM` | `...ATLNYM-ATL` |

Metadata exposed created/updated/open/close/expiration/occurrence times,
fixed-point bid/ask/last and sizes, volume, open interest, rules, status/result,
and settlement timer. Active Arizona YES was bid 0.49, ask 0.50; the public
order book returned YES and NO bid ladders. Preserve raw ladders and the exact
complement derivation used for asks.

Three settled hourly histories were retrieved:

| Winner market | Candles | Initial observed YES ask range | Final trade close |
|---|---:|---|---:|
| `...HOULAA-HOU` | 77 | 0.56–0.99 | 0.99 |
| `...BOSATH-BOS` | 75 | 0.57–0.99 | 0.99 |
| `...MILSF-SF` | 74 | 0.50–0.99 | 0.99 |

Candles include bid/ask and trade OHLC, mean/previous, volume, open interest,
and Unix end time; no-trade price objects may be empty.

Observed rules follow a postponed game completed within two days; cancellation
or a move beyond two days resolves to a “fair price.” The July 27
Cleveland–Cincinnati contract followed the game originally scheduled July 27
after it moved into July 28's doubleheader, while a separate July 28 evening
contract existed. Current date/team matching is unsafe.

Public read-only GETs worked; no trading/portfolio endpoint was called. Consume
cursor pagination. Kalshi targets a three-month live window; older settled
markets/candles use historical endpoints after `/historical/cutoff`, while old
events/series stay on original endpoints. Use the documented
`external-api.kalshi.com` base, retain fixed-point strings, and record
collection times.

## 8. Sportsbook benchmark findings

The Odds API provides JSON event IDs, UTC start, teams, bookmakers, bookmaker
update timestamps, and moneylines; historical snapshots reach back to 2020
subject to provider coverage. At research time the free plan offered 500
credits/month without history and paid history began at USD 30/month. Terms
permit analytical applications but prohibit raw-data redistribution.

No account, key, or purchase was created. Confirm retention, attribution,
coverage, cadence, delay, and outages before use. Store each book separately;
convert odds to implied probabilities and remove vig transparently, e.g.
`p_home=q_home/(q_home+q_away)`. Never average American odds. Defer this source.

## 9. Cross-source reconciliation examples

**Arizona at Pittsburgh:** MLB `gamePk` 823350 showed 22:40 UTC (18:40 EDT),
Pfaadt/Chandler. DRatings matched teams/pitchers and gave 46.5%/53.5%, but
displayed 17:40 local. Kalshi event `KXMLBGAME-26JUL281840AZPIT` rules said
18:40 EDT while `occurrence_datetime` was 01:40 UTC; Arizona YES was 0.49/0.50.
This is deliberately not a successful executable match: timestamps conflicted
materially and production must reject rather than normalize the conflict away.

**Cleveland at Cincinnati:** MLB 824490 was game 1 at 17:40 UTC, moved from
July 27, with Cecconi/Burns; 824489 was game 2 at 23:10 UTC, Williams/opponent
missing. DRatings had distinct probabilities and `UNDECIDED` for game 2.
Kalshi's July 27 event followed the originally scheduled game, while the July
28 event represented the evening game. Original date, lineage, game number,
and pitcher state are mandatory.

**Atlanta at New York:** MLB 823598 was postponed for weather to July 29 while
DRatings still displayed a July 28 forecast and Kalshi retained a within-two-
day-following contract. Reject while postponed and require new observations.

Normalize with a versioned 30-team alias table, source IDs, punctuation/name
variants (`A's`, Los Angeles A/D, New York M/Y, Chicago C/WS), UTC/source zone,
home/away, original/current schedule, game number, pitcher IDs, and explicit
YES-rule evidence.

## 10. Historical backfill assessment

| Evidence | Classification | Limitation |
|---|---|---|
| Licensed schedules/results | backfillable, entitlement-dependent | later state is not pregame state |
| Actual starters | backfillable | not prior probable evidence |
| Probable changes | prospective unless timestamped vendor history exists | look-ahead risk |
| DRatings completed rows | partial | need provable pre-first-pitch timestamp |
| Other forecasts | unknown/partial | do not label historical without timestamp |
| The Odds API | paid history from 2020 | coverage/cadence varies |
| Kalshi metadata/results/candles | backfillable across live/historical tiers | candles do not reconstruct depth |
| Kalshi book depth | prospective required | no historical depth established |

The defensible evaluation cohort begins with prospective timestamps, raw
evidence hashes, pitcher state, side mapping, and executable quotes.

## 11. Source decision matrix

| Source | Authority/independence | Identity/timestamp/history | Permission/operations | Decision |
|---|---|---|---|---|
| MLB Stats API | league reference | excellent IDs/schema; weak contract | terms prohibit automation | reference only |
| Sportradar | official partner | UUID + MLB reference; changes/lineups | paid terms unknown | preferred official feed |
| SportsDataIO | commercial secondary | broad feeds/vendor ID/history | paid | fallback |
| DRatings | statistical, independence unverified | full slate; weak durable ID/time | no API/license established | first forecast candidate |
| FanGraphs | transparent ZiPS/Steamer | good method; feed/history unclear | license needed | comparison candidate |
| Dimers | market-informed blend | good visible coverage | terms prohibit automation | reject automation |
| TeamRankings | unresolved | IDs/times/history unresolved | unknown | research only |
| `gmalbert/baseball-predictions` | evaluated external repository; no native-source authority | reinforces independently established chronology, calibration, manifest, and replay requirements; legacy model path is not point-in-time admissible | no project license; artifact and upstream-data rights unresolved | clean-room exclusion; no code, artifact, data, or dependency reuse |
| Kalshi | own-market authority | stable tickers/rules/live+history | documented public GETs | approved read-only strategy |
| The Odds API | market benchmark | IDs/update times/history | quota/subscription | deferred |

Permission is a veto; do not obscure distinct tradeoffs with one score.

## 12. Recommended source architecture

```text
Licensed official MLB feed -> canonical game/team/pitcher/status observations
Approved independent model -> immutable forecast observations
Approved comparison model  -> separate forecast observations
Admitted native Model 0     -> separate immutable forecast observations
Kalshi read-only API        -> rules/market/book/candle observations
Optional The Odds API       -> separate per-book observations
Canonical reconciliation   -> fail-closed gates -> later valuation
```

Adapters own transport/raw schemas/native IDs. Normalization owns `gamePk`,
crosswalks, UTC, schedule lineage, and typed observations. Reject unresolved
identity/side/time/pitcher/rules/freshness; never substitute market probability
for a missing model or silently swap providers. Keep bounded retries and
network smoke checks outside deterministic CI. Store content-addressed raw
evidence outside Git only where licensed.

## 13. Data provenance and preservation contract

**Event observations:** source/product/schema/endpoint; native ID and mapping
evidence; source update and collection times; raw reference/hash/license class;
`gamePk`; original/current start and zone; venue; team IDs/home-away;
doubleheader/lineage; status/reason/scores/outcome; validation/rejections.

**Forecast observations:** provider/model/version/method class/native matchup;
publication and collection times; mapped game and source-seen start; teams and
pitcher IDs/names/states; original-precision probabilities; raw hash;
transformations and validation.

**Market observations:** series/event/market; status and all relevant times;
titles, strike, rule snapshot; YES mapping/evidence; raw ladders plus derived
bid/ask method; last/sizes/volume/open interest as source strings; candles;
settlement result/time.

**Sportsbook observations:** provider event/book/market/outcome; provider/book
update and collection times; original odds; mapping; conversion/vig method and
derived probability without replacing raw odds.

Recommendations, Brier score, CLV, and hypothetical returns are downstream
records referencing immutable observations, exact prices, fees, policy
versions, and outcomes.

## 14. Data-quality and rejection gates

Reject on missing/conflicting `gamePk`, home/away, aliases, doubleheader or
reschedule identity; postponed/cancelled/suspended/unknown state; unresolved
time conflict (recommended tolerance 10 minutes without documented lineage);
missing forecast timestamps or collection at/after first pitch; stale forecast;
missing/undecided/changed starter under policy; probabilities outside `[0,1]`
or not summing within recommended ±0.005; missing/unsupported/inactive Kalshi
market; unresolved YES/rules; missing executable ask/depth, stale/crossed book
or excessive spread; incompatible settlement rules; expired permission;
unretainable evidence; or invalid schema/source failure.

Starter requirement, maximum ages/spread, minimum depth, and accepted
settlement classes are later policy parameters. Warnings cannot override a hard
rejection.

## 15. Licensing, terms, and operational constraints

- Reachable MLB JSON is not a free production API.
- Vendor trial schemas/rights may differ from production.
- Forecast sites need written automation, analysis, and retention rights.
- Dimers prohibits the contemplated automated collection.
- Kalshi GET access does not authorize trading or override API/account duties.
- The Odds API allows analytics but bars raw resale; confirm retention.
- Keep credentials and licensed payloads out of Git/logs/fixtures.
- Record terms URL/date/contract version and re-review periodically.

## 16. Risks and open questions

1. Sportradar price, limits, history, retention, and `gamePk` guarantee?
2. SportsDataIO affordability and MLB-ID bridge?
3. DRatings/FanGraphs licensed feed, native IDs, retention, and timestamps?
4. Is DRatings independent and are completed probabilities frozen pregame?
5. What starter confirmation/change window qualifies?
6. What does Kalshi “fair price” settlement produce?
7. Are paired team markets and structured team UUID mapping guaranteed?
8. Why did observed source times conflict?
9. What staleness/spread/depth/fee policy defines executable?
10. What observation cadence and retention horizon is affordable?
11. Does The Odds API support a defensible closing line?
12. Which derived work survives subscription termination?

## 17. Recommended scope for PR3

PR3 — Add Canonical MLB Game Identity should define offline contracts for
game/team/pitcher identity, schedule lineage, status, mappings, and provenance;
use `mlb_game_pk`; model original/current starts, zones, doubleheaders and
status transitions; preserve probable/confirmed/actual pitcher states; define
`matched`/`ambiguous`/`rejected`; and add small synthetic/redacted fixtures for
ordinary, split-doubleheader, postponed, missing-pitcher, and time-conflict
cases.

Do not add network clients, recurring collection, scraping, valuation, reports,
ensemble, subscriptions, wager recommendations, or World Cup refactoring. If
licenses are unresolved, use source-neutral fixtures and keep adapters blocked.

## 18. Explicit non-goals

PR2 does not authorize purchasing, scraping, scheduling, ingestion, domain
implementation, valuation, reports, fabricated historical forecasts, model
weights, Kelly/wagering, Kalshi mutations, World Cup changes, live workflows,
publishing/tagging, staging/commit/push, or PR3 implementation.
