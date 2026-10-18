# 2023 PA readiness: sample checks passed

October 12, 2026. Tom approved the previously proposed one-season readiness pass.
**No blocking discrepancy in the frozen 100-game sample; a bounded component
experiment is feasible. Whole-season readiness is not established by this sample.**

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd.,
Newark, DE 19711.

## Acquisition and scope

Obtained the 2023 parsed-play archive and same-season CSV bundle from the links
on [Retrosheet's PA downloads](https://retrosheet.org/downloads/plays.html) and
[season metadata downloads](https://www.retrosheet.org/downloads/csvdownloads.html).
The annual metadata bundle also contains plays and unused batting/fielding files;
only required metadata was extracted, and its duplicate plays were hash-compared.
No broader-season collection, accounts, payments, API keys or fitting occurred.

Transferred 17,438,021 bytes (17.44 MB); extracted 114,285,832 bytes (114.29 MB).
Both bounds remain below the approved 100 MB compressed / 1 GB expanded caps.
Acquisition URLs, times, archive/file hashes and receipts accompany this report.
Raw files stay in the private readiness workspace, outside Git.

## Frozen sample and findings

Before inspecting play outcomes, froze 100 IDs at evenly spaced integer positions
in the sorted unique metadata game-ID list: `floor(i*(N-1)/99)`, `i=0..99`.
The denominator is 2,472 games: 2,430 regular-season and 42 other games. Selection
by sorted home-team game ID is deterministic, not random or temporally uniform.
The sample has 98 regular-season games, one wildcard game and one All-Star game;
none was replaced after inspection. The fitting proposal uses regular-season only.

| Check | Result |
| --- | --- |
| Play rows / completed PA | 7,760 / 7,496; 264 non-PA events distinguished |
| Regular-season PA in sample | 7,343 |
| K / unintentional BB / other, excluding 13 intentional walks | 1,733 / 590 / 5,160 |
| PA against initial starters | 4,375; four intentional walks excluded leaves 4,371 component labels |
| Starter K / unintentional BB / other | 997 / 307 / 3,067 |
| Starters and initial orders | 200 recorded starters agree with first opposing PA pitcher; 200 initial orders agree with team metadata |
| IDs / hands / order integrity | No missing player IDs, unknown hands or non-unique nine-player orders in sampled PA |
| Outcome integrity | No non-exclusive outcome labels or invalid intentional-walk/safe-strikeout subsets; one K with safe reach retained as K |
| Pitcher reconciliation | 834 pitcher summaries; PA/K/walk/IW/HR/HBP reconcile exactly |
| Team reconciliation | 200 summaries; same six counts reconcile exactly |
| Identical rows / unexplained play dates | None in sample |
| Initial-batter exposure | 7,176 PA by initial-lineup batters; substitutes remain identifiable |

Six suspended games in full-season metadata each have separate original and
resumption play dates; one is in the sample. The sample counts reconcile across
both dates. A conservative future feature policy releases the entire game's
history only after its latest played date, avoiding premature combined-count use.
The six date checks are a targeted chronology check, not an expanded outcome audit.
Intraday announcement/publication times are not supplied or inferred.

## Verification and acceptance

[Audit code](audit.py) checks IDs, categorical labels, initial starters/orders,
counts and dates. A separate streaming check reproduced PA/K/walk totals, verified
positive-BF pitcher-key coverage, and found byte-identical plays in the two
archives. [Verification receipt](verification.json) records this same-assistant
check; it is not external independent review. [Aggregate findings](audit_results.json)
and [sample pin](sample_pin.json) make the scope inspectable.

Accept **sample-level data feasibility only**. Full multi-season checks must precede
any fitting and fail visibly on label/identity/chronology discrepancies. No claim
of regular-season completeness, pregame actual-matchup knowledge, live provider
availability, or market advantage follows. No existing supplier identity bridge
was constructed; same-source IDs suffice for the component but later game-level
integration still requires one.

The [proposed fitting protocol](../component_experiment/PROTOCOL.md) is ready for
Tom's agreement. It does not authorize more seasons or a fit. Production and
T−6h studies remain untouched; PR #86 remains draft.
