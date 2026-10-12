# Modern ML: one proposed next comparison

October 12, 2026. **Setup due diligence now identifies a consumer-eligibility blocker for 3.5.** Read the [access/compute review](MLB_2027_MODEL_ACCESS_COMPUTE_REVIEW.md) before this conditional proposal; v2 is an explicit alternative requiring a new decision.

**Discussion proposal, not authorization to install, accept
licenses, create credentials, download weights or train.** This follows Tom's
hypothesis that recent AI/mathematical advances might provide an advantage against
well-resourced sportsbooks. The hypothesis is worth testing; neither the resource
gap nor a newer model establishes an edge. Keep sportsbook opening consensus as
the agreed historical Kalshi proxy. The failed strength challenger stays closed.

## Recommendation

Recommend one bounded **learner comparison on the existing frozen game table**:
retained native logistic, one competent CatBoost baseline and **one pinned
TabPFN-3.5 core checkpoint**. Do not run several foundation-model versions or an
AutoML tournament. This is the least costly direct test of whether a modern
learned representation extracts interactions our existing model misses, without
mixing that question with new feature acquisition. Execution is conditional on
access, permitted evaluation use, pretraining-provenance review and local compute.

Do not run TabPFN's hosted API with private licensed inputs. Do not assume code
availability grants weight access or product-use rights. If the chosen checkpoint
cannot be used under the current no-new-credentials/no-purchase boundary, stop
and present that blocker; do not silently switch to an older version or cloud job.

This becomes the recommended next **experiment proposal**, ahead of the earlier
simple score-pair proposal. The latter is preserved as a structural alternative;
the matched-price notes remain background, not the answer to weak forecasting.

## Why this is not repeating the previous nonlinear experiment

The team GAM used three team-history differences with additive splines and no
interactions; it did not improve 2024 Brier. The starter GAM kept team terms linear
and only splined three starter differences; its 2025 Brier was 0.244256 versus
0.243886 for the reference. Those negative results reject those candidates, not
all nonlinear learning. No retained completed CatBoost/LightGBM experiment was
identified in the inspected experiment inventory.

The fixed ten-column table can still contain interactions that additive curves
miss, for example starter strength changing the significance of recent team form.
That is a hypothesis, not an observed driver. A learner-only comparison can test
it cleanly. A foundation model cannot recover batting-order, injury, platoon or
tracking information already discarded by those columns; failure would not prove
all player-level models are useless.

## Current research, reconciled with our data

The [TabPFN-3.5 technical report](https://arxiv.org/html/2609.17895v1), released
September 15, 2026, describes a synthetic-prior tabular foundation model and
reports strong benchmark results, including small temporal/grouped tasks.
Its headline comparisons sometimes use proprietary Thinking/Plus variants;
the proposed downloadable **core** is a different configuration. Benchmark
success is a reason to test, not evidence of baseball or betting superiority.

The [official repository](https://github.com/PriorLabs/TabPFN) documents
Apple-Silicon support and warns about CPU scale; the largest current annual fit
has 9,704 rows, exceeding its stated 5,000-row default CPU limit for 3.5. Existing
hardware support, memory and package compatibility must be checked, not assumed.
First-use access involves login/license acceptance. The [weight license](https://huggingface.co/Prior-Labs/tabpfn_3_5/blob/main/LICENSE)
separates evaluation from restricted commercial/production uses; offline research
permission is not permission to use model outputs in a wagering product.

[TabArena](https://arxiv.org/abs/2506.16791) emphasizes reproducible, comparably
tuned tabular benchmarks and validation overfitting. Accordingly, beating only
our logistic would not establish that TabPFN adds anything beyond ordinary
boosting; include a bounded, competently configured boosting comparator.

| Route | Baseball/data fit | Recommendation now |
|---|---|---|
| Tabular foundation model plus boosting control | Direct fit to existing numeric game rows; materially different learner/interactions, minimal new data burden | First proposed test, conditional on access/compute; not yet approved |
| Hierarchical player-level plate-appearance model → run/win distribution | Fits baseball's actual participants and event units; can pool sparse player histories and preserve lineup order/platoons | Credible next structural route if the table is inadequate, but requires validated event/context data and more implementation |
| Pitch-sequence encoder or transferred player embeddings | Potential richer player-skill representation, but requires an acquired longitudinal pitch corpus and careful pregame aggregation | Defer; no evidence our aggregate boxes support this scale or that next-pitch metrics translate to pregame wins |

The [2025 baseball matchup paper](https://arxiv.org/html/2511.17733v1) demonstrates
hierarchical plate-appearance outcome models and game simulation. Its retrospective
43-playoff-game example lost 15.5% under the basic selection rule; better reported
returns at selected cushions are not confirmation of profitable pregame use.
It supports a mechanism to investigate, not adoption of its thresholds. Our
earlier actual-nine averages did not test this event-level hierarchy.

The [2026 Neural Sabermetrics paper](https://arxiv.org/html/2602.07030v1) trains a
Llama-based event model on roughly seven million pitch sequences/three billion
tokens using TPU-v4-64. Its evaluated tasks are pitch type and swing decisions,
not pregame winner probabilities. Some conditioning fields occur during games;
they cannot become pregame inputs. Its pitch-accuracy prose and table also differ,
so do not cite a headline as a reliable game-winning result. A small frozen
historical-only encoder would be a separate research project, not a cheap clone.

## What we actually own

The verified native game table has 12,132 eligible 2022–2026 targets; annual fits
have 4,852, 7,278 and 9,704 rows. These are correlated baseball games, not millions
of independent supervised examples. There is no demonstrated large-network
training dataset merely because aggregate stat rows contain many counts.

Retained batting-event rows total 202,701 across 2022–2025; pitching-appearance
rows total 103,937 across 2022–2026. These are **player-game aggregates**, not
paired pitch sequences or individual batter-versus-pitcher plate appearances.
The batting audit lists raw fields such as doubles/triples/HR/K, beyond the
processed OBP/ISO input subset, but field presence does not prove reliable,
complete count semantics. That offers a possible later event-rate model using
aggregated count likelihoods, not permission to fabricate within-game matchups.

A fully player-level generative model would need stable player identities,
outcome-category exposure denominators, opponent/hand context, lineup order,
starter-duration/reliever-usage assumptions and validated base/out transitions.
Pitch-sequence work additionally needs a cleaned tracking corpus and earlier-only
embedding training. We have not demonstrated those complete datasets. Raw ID
fragmentation and invalid-history counts deserve a fixed readiness check before
blaming or changing the learner, but no outcome-guided player/season removal.

AI-assisted coding, literature search and audit can reduce our cost of running
these tests. That is distinct from predictive signal. Asking a general LLM which
team wins, retrieving postgame news or using a memorized result is not this proposal.

## Proposed concrete comparison

1. **Freeze the exact existing ten-input table and eligible populations.** No new
   raw team names, game IDs, dates-as-features, market odds, actual outcomes or
   additional batting columns enter the learners. IDs/dates remain join/split
   metadata. Retain documented unknown-starter/invalid-history fallbacks and
   prior-New-York-calendar-day chronology. Target performance never enters inputs.
2. **Pin a single checkpoint and its provenance.** Review base pretraining,
   synthetic-prior construction and any benchmark tuning/real-data exposure.
   Annual splits of our table do not certify a pretrained model never saw the
   real games. Unresolved exposure limits retrospective claims; a frozen-before-
   2027 checkpoint and genuinely new 2027 outcomes remain the confirmation path.
3. **Compare reference logistic, one boosting baseline and one TabPFN core.**
   Use chronological train-through-2023/evaluate-2024, through-2024/evaluate-2025,
   through-2025/evaluate-2026. All evaluated seasons are already development.
   Allow only a predeclared small CatBoost configuration budget (at most eight),
   chosen inside each annual training set using earlier-season temporal folds.
   No outer-evaluation tuning, checkpoint sweep, learner ensemble or AutoML search.
   Freeze seeds, estimator count and model-native preprocessing before execution.
4. **Judge probabilities, not winner accuracy.** Brier primary, natural-log loss
   secondary; calibration and fixed bins diagnostic. No post-evaluation calibration.
   If calibration is included at all, its one method must be chosen beforehand and
   learned only from earlier out-of-time training predictions. Preserve uncalibrated
   results and the unchanged reference; do not recycle the failed prior calibrator.
5. **Keep the proxy comparison decisive and visible.** Report all learners against
   sportsbook opening consensus on the same original eligible market intersections
   and full native populations separately. No default re-adoption of the old
   outcome-inspected 13 exclusions. Paired 14-day block uncertainty with 7-day
   sensitivity, complete fallbacks/missingness, no phase or team policy selection.

For discussion, retain the existing practical **development** gate: average annual
Brier gain over reference at least 0.001, positive point gain in at least two
years, no worse pooled log loss, unchanged coverage/no new hindsight dependence.
Also report TabPFN-minus-boosting and each learner-minus-market contrasts. Passing
the native-reference gate alone earns further research consideration, not a claim
to beat the proxy. If the sportsbook gap remains, say so explicitly; do not use
different Kalshi pricing as the assumed remedy. Tom must approve this gate for
the new test; earlier experiment authorization does not carry over automatically.

## Cost, stopping and authorization

Proposed effort cap: five focused working days including compatibility/readiness,
bounded fits, validation and result documentation. No new data subscription,
paid hosted inference or cloud GPU. Existing licensed archives remain local.
Local runtime/memory at the full annual folds is unmeasured; vendor benchmark
GPU timings are not an estimate for this Mac. If compatible local inference is
unavailable or exceeds the fixed budget, stop with a feasibility result rather
than change the population, subsample silently or purchase compute.

Stop without a predictive run if weight/license/account requirements cannot be
satisfied within separately approved access, pretraining provenance undermines
the proposed historical inference, inputs fail integrity checks or hardware is
inadequate. Stop this learner comparison after the prescribed results if the gate
fails; do not try more checkpoints until one wins. A pass needs fresh regular-
season confirmation and separate cost-aware policy validation before live use.

No implementation, installation, download, access acceptance, fit, credential,
purchase, new observer or production change has occurred. The immediate decision
is whether Tom wants this one bounded modern-learner comparison, with access and
compute prerequisites made explicit. Any license acceptance/new account needs a
separate decision; this proposal does not conceal it inside experiment approval.

## Sources and durable status

Primary papers/docs above were read directly after the parent's independent
literature scan; no duplicate broad scan was launched. Local source inspection
covered retained team/starter GAM protocols/results, batting/pitching audits,
player-game fields and experiment 01, in addition to the independent model review.
No new predictive results support this proposal. [Product record](MLB_2027_PREGAME_MODEL.md)
and draft PR #86 preserve proposal versus authorization and failed-result history.
