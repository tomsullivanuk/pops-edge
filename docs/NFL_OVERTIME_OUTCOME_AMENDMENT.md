# Weekly Performance outcome amendment — completed overtime

September 16, 2026 implementation candidate. Owner authorized the focused correction
for NO at DET. No activation, acquisition or production report publication is implied.

## Rule and scope

The new `nfl-weekly-outcome-v2` interpretation accepts official summary phase
`FINAL_OVERTIME` as well as `FINAL`, only with quarter `END_OF_GAME` and the existing
validated game/team identities, compatible outer status and valid reconciled scores.
An overtime home win has payout 1; away win 0; a supported genuine final tie 0.5.
A tie at the end of regulation is not a final tie when overtime supplies a winner.
Unknown phases or contradictory/invalid final evidence remain unscored.

This implements the weekly protocol's requirement that additional provider final
markers receive explicit support. It does not change cohort/capture eligibility,
contract-value formulas, reference arithmetic, source observation dates or settlement
and wagering authority. Bet Sheet completion already supports overtime finals and
remains unchanged. No other provider status is admitted by this amendment.

## Compatibility and correction provenance

`nfl_performance_sources.outcomes` retains its v1 default so existing callers and
legacy interpretations remain stable. New weekly report derivation explicitly uses
v2 and includes `outcome_rule` in its content-addressed report identity. Replay of a
report without that field uses v1; replay of a v2 report explicitly uses v2. Unknown
rule identifiers fail validation. The schema and activation digest are unchanged;
the pinned weekly protocol and starting-cohort documents are not edited.

Original saved reports remain immutable and replayable. A later explicitly generated
report can reinterpret the same retained raw outcome evidence under v2 with a new
analysis boundary and identity; its source IDs and observation timestamps remain
original. The outcome-rule field identifies this interpretation change. Do not edit
old reports, backdate new observations, reset forecasts or silently replace evidence.

## Production follow-through after review/authorization

Deploy the accepted source, then explicitly generate a new Week 1 report using the
existing manual report command and the actual current boundary. No fresh provider
acquisition is necessary for the retained NO at DET evidence. Confirm old report
replay, new v2 identity, 14 scored pairs rather than 13, Detroit 31–30 and unchanged
baseline/captures/cohort. The existing reader selects the later saved boundary.

Current implementation verification is read-only: no new production report was saved.
Accepted limits remain local/manual operation and visible failures; generalized
migration, report rewriting, collector changes and MLB redesign remain excluded.
