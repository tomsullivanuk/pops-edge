# Player information assessment: WAR and richer pregame inputs

October 12, 2026. **Read-only assessment; no new experiment or acquisition authorized.**
Main verified as `9564b12dcd80f0b3347b4860b95984763f2e3061`. Examine information
quality before another learner change. Existing failed specifications stay closed.

## Recommendation

Do not append retrospective season WAR as a catch-all feature. Prioritize one
**lineup offensive-projection comparison**, keeping the game learner fixed: our
lagged batting rates versus timestamped preseason Steamer batting-rate projections.
Use identical initial lineups, batting-order exposure and handedness treatment in
both arms. This is conditional on verifying projection vintage/access and is a
discussion proposal, not a fit protocol.

The useful addition is external player forecast information, including longer
histories/aging and potentially projected platoon skill, not a new metric name alone. wOBA and OBP/ISO summarize overlapping outcomes;
merely renaming or linearly recombining them may add little. Whether the richer
information improves winner forecasts remains untested.

## What is encoded, and what is missing

| Area | Promoted native reference | Tested or retained elsewhere | Likely incremental gap / duplication |
| --- | --- | --- | --- |
| Team context | Prior 60-game win and run-difference, 10-game run-difference, season progress/interactions | Separate offense/prevention and opponent-adjusted ratings tested without promotion | Team results indirectly contain offense, defense and bullpen; not individual game-day attribution |
| Player offense | No explicit batter feature in the ten-input reference | Usage-weighted and equal-nine OBP/ISO; actual-nine batting-order IDs retained as provenance; failed 2025 generalization | Measured opposite-hand rates, outcome-specific contact value and initial-order exposure absent from winner fits |
| Handedness | Starter identity informs starter features, not batter-specific offense | Opposite-handed share proxy; experiment 03 models conditional K/BB with hand-pair indicators | A hand indicator is not a measured batter-versus-hand offensive split; small K/BB component gain does not cover hit severity |
| Contact quality | No exit-velocity, launch-angle or expected-contact-value feature | Retrosheet hit severity is now retained; four earlier pitch samples are not a tracking corpus | Lagged hard-hit/barrel/expected contact rates could add information beyond realized OBP/ISO, but target-game contact is unavailable pregame and retrospective expected metrics need versioning |
| Defense | No explicit projected fielding/catching quality | Raw fielding counts, positions and Retrosheet defensive assignments available | Range, positioning, catcher receiving/throwing quality could add information; errors/fielding percentage alone cannot supply those measures |
| Baserunning | No player-level baserunning predictor | Raw SB/CS/GIDP and PA runner transitions retained | Success/advance rates conditional on opportunities may add information; SB totals mix skill and exposure; full tracking-based run value not retained |
| Starting pitching | Lagged shrunk K−BB, HR and expected innings differences | Opponent-specific K/BB component tested; small positive gain below its gate | Pitch mix/velocity/movement, contact quality and duration distributions absent. FIP largely repackages K/BB/HR already encoded, adding HBP and weighting rather than wholly new signal |
| Bullpen | Recent team results absorb some relief performance | Team relief K−BB/HR and yesterday/three-day pitches tested without strong gain | Individual likely relievers, roles, roster/injury state, rest and availability not explicitly forecast; pitcher WAR cannot resolve who pitches today |
| Projections and context | No external preseason/rolling player projections, explicit park/weather terms or injury snapshots | Provider historical totals and lagged same-source player history | Pregame projections can add longer/minor-league histories and aging adjustments; need genuine pregame versions and identity joins |

Repository evidence: [ten reference inputs](../research/pregame_2027/experiment_01/run.py),
[original feature-test synthesis](MLB_2027_SCORE_MODEL_PROPOSAL.md#what-the-actual-failures-establish),
[actual archive inventory](MLB_2027_COMPONENT_FEASIBILITY.md#what-is-actually-retained),
[experiment 03 equations](../research/pregame_2027/experiment_03/PROTOCOL.md),
and [its completed results](../research/pregame_2027/experiment_03/RESULTS.md).
Prior original batting/actual-nine/bullpen protocols were reread privately; their
licensed inputs remain outside Git. Tested features are not silently promoted
into the retained reference.

## WAR is a summary, not today's player forecast

[FanGraphs position-player WAR](https://library.fangraphs.com/war/war-position-players/)
combines batting, baserunning, fielding and positional/league/replacement
adjustments, expressed in wins. Accumulated WAR incorporates exposure: a good
player with less playing time can have lower season WAR. A sum across today's
nine would mix accumulated exposure, expected contributions and position effects.
It can also double-count offense/starter information already represented.

Fielding/baserunning components may provide information absent from our explicit
features, but keep those components and their uncertainty visible instead of
assuming aggregate WAR isolates the gap. FanGraphs pitcher WAR is FIP-based;
[FIP's published formula](https://library.fangraphs.com/pitching/fip/) shows its
substantial overlap with our K, BB, HR and innings inputs. Do not interpret either
WAR convention as a one-game winner probability.

“WAR+” has no provider/formula specified in Tom's question. Obtain that definition
before choosing a feed or treating the label as a standardized feature. If the
intended metric is [wRC+](https://library.fangraphs.com/offense/wrc/), it is a
park/league-adjusted offensive rate index with average 100, not overall WAR.
[wOBA](https://library.fangraphs.com/offense/woba/) weights distinct offensive
events by run value; it does not itself adjust for park. Distinguish these quantities.

Never use a target season's final WAR/wRC+ for earlier games. Even year-to-date
statistics need a prior-game cutoff; current retrospective downloads may carry
later corrections or full-season league constants. Prior-season values are
chronologically safer but can be stale and are not projections. Timestamped
preseason/in-season projections available before the decision are the right
forecasting objects if we use an external source. FanGraphs describes
[Steamer/ZiPS/Depth Charts](https://library.fangraphs.com/principles/projections/)
as projection systems; current pages do not establish historical daily snapshots.

## One focused comparison, if Tom wants to pursue it

Hold the ten-input reference's other inputs and logistic learner/settings fixed.
Compare a lineup block based on **our shrunk lagged batting outcome rates** with
one based on **published preseason Steamer batting-rate forecasts**, both expressed
as the same offensive run-value rate. Both arms use identical initial-nine IDs,
training-only batting-order PA weights, league normalization, denominators and
handedness treatment. Do not compare a new weighted lineup with an old equal-nine
baseline and attribute all gains to the provider's player forecasts.

The actual data contrast is estimated future skill from an external projection
system versus our short, single-source realized history. It may incorporate aging,
longer history and minor-league information missing from our rates. Confirm the
chosen system's documented inputs rather than presume every system includes
Statcast. If authenticated preseason platoon projections are unavailable in an
evaluation year, do not mix overall and split vintages opportunistically: use
one agreed common overall-rate scope, retaining the same preexisting hand treatment
in both arms. A later platoon extension would require its own explicit decision.

This is not a repeat of replacing usage weights with an equal actual nine's
OBP/ISO; identities and weights are held common, while the player-quality forecast
changes. It also differs from experiment 03's conditional K/BB target: contact
outcomes are included and the final target is game winners. Defense/baserunning,
bullpen projections and WAR are not bundled into this initial comparison.

Use only a preseason file demonstrably released before that season's evaluated
games. Hold it fixed through the season for an honest initial comparison; do not
present it as the current updated projection. Daily rest-of-season vintages are
not verified. If usable 2024/2025 preseason vintages and model-training-year files
cannot be authenticated, stop with that data-readiness finding rather than use
current or final-season forecasts retrospectively. Prospective 2027 capture of
permitted forecast snapshots is possible in principle, but not launched here.

Retained Retrosheet PA data can reconstruct outcome rates and shared batting-order
exposure without another raw-data subscription. Audit the projection-to-Retrosheet-
to-canonical identity bridge, initial orders, missing-player coverage and scale.
No such bridge was constructed by experiment 03. Historical initial lineups
retain the assumed-available limitation; exact announcement times remain unknown.
Prospective timely lineups remain a working assumption supported by the
[completed two-game observation](MLB_2027_LINEUP_OBSERVATION_FINAL.md), not a
reason to block useful offline modeling.

Propose chronological 2024/2025 development only if vintages/training years are
ready, exact paired coverage, full winner Brier/log loss, unchanged native and
sportsbook proxy, calendar-block uncertainty and cold-player coverage. All seasons
are reused development. Agree a practical market-comparison threshold and effort
cap before execution; component/native improvements do not establish market edge.
No WAR benchmark is required for this one controlled comparison. Lagged or
preseason projected WAR could be a later simple diagnostic, but mixing it into
this test would expand scope and obscure which information helped.

## Sources and incremental access

Owned 2022–2025 Retrosheet PA/metadata support the control and common lineup
weights, without more source acquisition. Its [use notice](https://www.retrosheet.org/game.htm)
permits use with attribution; raw records remain private under project policy.
The projection challenger needs permitted external preseason files and identity
mapping; it is not already available in our archive.

FanGraphs' [January 2025 announcement](https://blogs.fangraphs.com/instagraphs/introducing-new-steamer-split-projections-and-more/)
documents historical full-season Steamer (from 2012), ZiPS (from 2010), enhanced
platoon/role projections and one-click exports as membership features. It says
current standard full-season and updated projections remain accessible to
non-members. That establishes offered products, not existing account entitlement,
release-vintage integrity, daily archives or redistribution rights. The actual
projection and terms pages failed retrieval here. Price, Tom's access and allowed
export/storage still need verification; no purchase, signup or download occurred.

Official [Statcast CSV fields](https://baseballsavant.mlb.com/csv-docs) document
pitch/contact telemetry and terminal PA outcomes. Those could supply a distinct
later contact-quality test, but public availability is not unrestricted automated
collection permission. No season-scale tracking data was acquired or searched
through an authenticated account here. Batting run-value recalculation alone is
available from owned data, but mostly repackages existing outcomes; it is a weaker
answer to the question of genuinely richer external player information.

## The scientific question, our checks and Tom's decisions

**Scientific question:** do established preseason player forecasts improve
paired game-win probability scores over our own lagged batting rates when
lineups, exposure weights and the learner are held fixed? WAR is not the question
Tom needs to settle, and a projection product's existence does not answer it.

**Already authorized research:** source discovery, vintage/schema inspection,
identity reconciliation, expected coverage and permitted access/cost verification.
These are our tasks; Tom need not supply the technical answers or approve each
routine read. The following repository-side assessment is now complete.

### Exact minimum seasons and populations

Require **four frozen preseason hitter files: 2022, 2023, 2024 and 2025**.
Train through 2023/evaluate 2024; train through 2024/evaluate 2025. If inner
selection is used, train 2022/evaluate 2023, then rolling earlier years only.
Thus evaluation-year files alone are insufficient. No 2026 file or historical
daily rest-of-season archive is required for this first fixed-preseason test.
Existing 2021 team warm-up remains unchanged; it does not require 2021 projections.

| Season | Native games | Unique retained game joins | Initial-lineup slots | Distinct initial batter RetroIDs |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 2,429 | 2,429 | 43,722 | 678 |
| 2023 | 2,423 | 2,423 | 43,614 | 643 |
| 2024 | 2,426 | 2,426 | 43,668 | 645 |
| 2025 | 2,426 | 2,426 | 43,668 | 661 |

This is 9,704 game joins and 174,672 lineup slots, covering 1,022 distinct batter
RetroIDs across years (2,627 player-season requirements). No historical game was
dropped. [Coverage code/aggregates](../research/pregame_2027/projection_feasibility/repository_coverage.json)
and [separate validation](../research/pregame_2027/projection_feasibility/join_verification.json)
record these facts. Private ID lists and candidate joins are retained locally,
not published as raw player records.

Match original game date and explicit season/team aliases; resolve doubleheaders
using retained **final official schedule gameNumber**, not final scores or
incidental order. That resolves 136 / 70 / 58 / 56 games annually requiring the
number. The 2025 Athletics code is ATH rather than OAK. One 2022 makeup game
has Retrosheet home-bats-first/site-home semantics; its explicit `htbf` field
reconciles designated home with the official team identity. No original source
or native input was rewritten. All joins are one-to-one. Separately checked final
scores agree for all 9,704; scores were not used to select joins. Two team sides,
unique nine-player orders and same-season player registry IDs validate throughout.
This is an identity-feasibility result, not a newly fitted dataset acceptance.

### Minimum external file contract

Each year's **full offered hitter projection table**, with no retrospective
filter to successful/known MLB participants, needs:

- System, target season, preseason/version label, release/vintage evidence,
  source URL, acquisition time and content hash. Release must precede its
  evaluated games; acquisition today does not prove historic availability.
- Stable provider player ID plus an auditable mapping to Retrosheet ID; preferably
  MLBAM IDs as an intermediate. Names are display/disambiguation evidence only,
  never an automatic namesake merge. No FanGraphs/Steamer player bridge exists yet.
- Projected overall offensive rate (preferably wOBA) with documented scale,
  context/park convention and denominator, and projected PA for coverage/precision
  diagnostics. Annual projected PA will not replace common game-day slot weights.
- If the file lacks a comparable rate: sufficient projected event counts and
  denominators to reconstruct the same run-value index in both arms. Do not
  silently treat OPS, wRC+, WAR and wOBA as interchangeable. A real sample is
  needed to choose this representation; no schema is presumed verified.

Platoon forecasts, defense/WAR, bullpen projections and tracking fields are not
minimum requirements. Retain the same hand handling in both arms. For each year,
report coverage by batter IDs, lineup slots and entire-game both-side availability,
plus missing/new-player counts. The table above is required demand, **not expected
100% projection coverage**: preseason tables may omit later debutants/call-ups.
Preserve every target with a predeclared shared fallback or explicit unavailable
forecast; agree that policy before fitting. Never drop missing players/games to
make the provider look stronger. Actual matched projection coverage cannot be
computed without the external files and ID crosswalk.

### What exists and what is still missing

Retained source data already supply game identities, initial orders, batter
RetroIDs, batting outcomes/hand histories, canonical winner labels, original
native features and sportsbook proxy records. This controlled projection test
needs no new pitch corpus, live collector or Kalshi history acquisition.
Filename/provider discovery across the inspected project archive found no
Steamer/ZiPS/FanGraphs/Depth Charts projection files. Existing software artifacts
called “projection” concern internal forecast reporting, not preseason hitter
estimates. This finding is scoped to the inspected repository/project archive,
not every private folder or account. No external file was obtained here.

The coordinating public-source researcher reports indexed **Historical Preseason
Projections** entries for Steamer/ZiPS 2022–2025. This supports candidate year
availability; it does not verify sample content, full coverage or release vintage.
The [official FanGraphs membership page](https://plus.fangraphs.com/product/fangraphs-membership/)
was read: $15/month, $80/year or $200/three years, automatically renewing, with
historical/platoon projections and exports included. No purchase or account
entitlement check was performed. The [Steamer preseason archive](https://www.steamerprojections.com/index.php/projections/pre-season-projections)
visibly lists 2022–2024 hitter files; the researcher reports free registration
for access. No new registration is authorized or made, and a usable 2025 file
has not been verified on that route. Do not combine different systems or assume
registration provides the missing year. Prices are source-page listings, not a
budget commitment or verified personal-use/export/redistribution rights.

**Remaining blockers:** inspect permitted sample files and release evidence;
confirm all four seasons and rate fields; build the provider player-ID bridge;
measure projection coverage and freeze missing-player treatment; then write the
concrete pre-fit protocol and market-comparison value gate. Provider investigation
is proceeding separately; do not duplicate it with acquisition or an account.

**Tom's actual decisions:** none is needed to continue already-authorized read-only
feasibility checks. If the verified route needs new registration or paid access,
present that specific option/cost for agreement first. After readiness is resolved,
Tom decides whether to run one bounded, frozen comparison. No vague blanket
approval, purchase, new credential, model fit, collector or merge is implied.


## First Owner-supplied export: fields and 2024 coverage verified

The uploaded `fangraphs-leaderboard-projections.csv` was materialized through the supported Library route into this task's private executor workspace. Local readable bytes and Library identity metadata were verified: 3,213,054 bytes, SHA256 `9ca0ec996bd1c8d8174a202d6b64b3e36c3af7c86531f60f322a36ef8892fcc8`. The raw licensed file remains outside Git. No browser credentials, databases or account settings were accessed.

Actual content is comma-separated UTF-8 CSV: 3,711 rows, comprising 3,710 rows with unique nonblank FanGraphs PlayerId and MLBAMID, plus one unnamed record with blank IDs. Keep that unidentified row visible and out of player joins; its nature is not inferred. No exact duplicate rows. Required PA/AB/hit-event/BB/IBB/HBP/SF/wOBA fields are finite and nonnegative. Projected PA, wOBA, event counts, wRC+, WAR and additional fields exist; their existence does not authorize adding every metric to the comparison.

A direct MLBAMID join to the preserved 2024 actual-lineup lineage matches all 645 required batters, all 43,668 slots, and both nines in all 2,426 native games. No namesake inference or prospective coverage assumption is involved. The preserved lineage provides a supported direct projection-ID route for this check, even though the new Retrosheet-to-provider control bridge is not yet finalized. [Reproducible audit](../research/pregame_2027/projection_feasibility/audit_export.py) and [aggregate receipt](../research/pregame_2027/projection_feasibility/first_export_audit.json) record the exact scope. This is coverage of 2024 players, not proof that the forecast values are from 2024.

**Remaining file blocker: source/vintage evidence.** The CSV has no season, system or release field. The reported user export path (Historical Preseason, Steamer, 2024, Batters) is provenance context, not independently verified content metadata. The page URL has not been supplied. Request that exact URL and its displayed archive/system/year selection; no credentials are needed. Then reconcile the archive's preseason/version meaning and obtain the remaining 2022/2023/2025 files through permitted UI/file transfers. Do not treat membership signup or an export's generic filename as historic-vintage proof.

The signed-in Mac browser could not be controlled from this task's exposed capabilities; the in-app open action only queued a tab, and screen-reading is voice-only. No Safari-specific or OS permission denial was observed. The Library file transfer itself succeeded locally; there is no materialization blocker and no retry was needed. Membership/session entitlement was not independently inspected, although an Owner-supplied readable export now exists. No training or additional paid acquisition occurred.


## First export provenance reconciled

Tom supplied the exact export-page URL. Its query selects `type=steamer_2024`, `stats=bat`, all positions/teams/players/leagues. Combined with the uploaded file and reported supported-UI export, this supports treating it as the Owner-supplied historical 2024 Steamer hitter export for readiness. The generic “2026 Projections” page title is navigation context, not the selected projection vintage. [Provenance receipt](../research/pregame_2027/projection_feasibility/first_export_provenance.json) links the URL to the audited CSV hash.

This supersedes the preceding request for the page URL: **no additional blocking Owner question is needed for this file**. The original publication timestamp and archive revision/immutability history remain unverified limitations, not another vague approval request. Do not claim contemporaneously saved 2024 bytes or verified daily as-of history. The concrete pre-fit proposal should state that limitation explicitly. The parent has requested similarly selected 2022/2023/2025 exports with year-specific filenames; their actual schema, IDs, coverage and provenance will be checked on arrival. No training is authorized.


## All four files imported; one bounded comparison proposed

The three additional Owner-supplied CSVs were materialized through the supported Library helper and verified as readable local bytes. All have required fields, finite nonnegative values and unique identified player IDs. Their filenames remain numbered, with no year fields: proposed association `-2=2022`, `-3=2023`, `-4=2025` needs one specific confirmation, already requested. No source year is inferred solely from attachment order or player/team examples.

Under that mapping, projection coverage is 676/678 batters and 43,612/43,722 slots in 2022; 641/643 and 43,571/43,614 in 2023; complete 645/645 and 43,668/43,668 in 2024; 660/661 and 43,552/43,668 in 2025. A direct archived initial-slot bridge maps 1,022 MLBAM IDs to 1,022 RetroIDs one-to-one across all 174,672 slots, without name inference. The initially absent player bridge is now reconciled from retained evidence. Raw exports, Library transfer metadata and individual ID lists stay private.

[The concrete comparison proposal](MLB_2027_PROJECTION_COMPARISON_PROPOSAL.md) holds the winner learner, lineups, order exposure and hand treatment fixed; compares our lagged rate with a common run-value index derived from preseason projected event counts; retains every game using the control rate when projections are missing. It distinguishes a 0.001-over-control information gate from sportsbook market competitiveness. Five focused working days are proposed only after agreement. Field/identity readiness passes; numbered-file year confirmation and experiment agreement remain. No training or purchase occurred.


## Labelled replacement exports resolve year assignment

Tom supplied four new exports labelled by the selected 2022/2023/2024/2025 year. The exact Library-resolved filenames were verified, including the space before 2024 in that filename. All four are readable locally and match the corresponding originals byte-for-byte and by normalized CSV records. Thus `-2=2022`, `-3=2023`, `-4=2025` is now reconciled as Owner-supplied provenance, with no correction needed. Original and replacement files are both preserved outside Git. [Reconciliation receipt](../research/pregame_2027/projection_feasibility/replacement_reconciliation.json) records filenames, hashes and scope.

Year-specific schema/coverage audits were rerun against the labelled copies; counts and missing-player gaps are unchanged. Data, IDs and year association are ready for the bounded proposal. Original publication timestamps and retrospective archive revision/immutability remain unverified limitations, without another generic provenance approval request. No source-year question remains. The [updated experiment proposal](MLB_2027_PROJECTION_COMPARISON_PROPOSAL.md) awaits explicit experiment agreement; uploading these files does not authorize training. No model fit or purchase occurred.


## Approved Steamer comparison completed

Tom approved the matched winner comparison at `1d64e15`; implementation was frozen at `43d8161` before fitting. [Experiment 04 results](../research/pregame_2027/experiment_04/RESULTS.md): 2024 control-minus-Steamer Brier +0.001005688, 2025 −0.000057538; average +0.000474075 versus required +0.001, with 14-day interval [−0.000423151,+0.001021038]. Both information-improvement and sportsbook-competitiveness gates fail. Exact prediction replay and separate measurement/bootstrap checks pass, with every game retained and declared missing-player fallbacks. Close this tested specification without retuning, promotion or integration. Reused-development and archive-vintage limitations remain explicit; production/T−6h protocols stay intact.
