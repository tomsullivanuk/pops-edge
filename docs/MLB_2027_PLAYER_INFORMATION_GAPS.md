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

Next discussion: agree that lineup-specific offensive quality is the priority,
then authorize only a bounded projection-vintage/access/identity readiness assessment and freeze
one game-level comparison protocol. No new experiment, data purchase, credential,
collector, production policy or merge follows from this document.
