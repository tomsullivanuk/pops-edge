# MLB Performance — adopted NFL-style reader

September 16, 2026. The Owner authorized implementation and independent review of the adopted preview. Integration, deployment and release remain separate gates. This supersedes the Part2 acceptance of the existing MLB iframe and the deferral of this bounded MLB redesign.

## Presentation

Performance → MLB uses the NFL shell, navy headings, light metric labels and Central timestamps. Its cumulative summary compares saved Kalshi mean Brier score with the same-population 50% reference. Improvement is reference minus Kalshi, computed before display rounding. Two decimal places maximum, exact downloads unchanged. No admitted model column exists. MLB binary scoring remains distinct from NFL payout-adjusted scoring.

Eligible/captured/scored counts, material gaps, the saved uncertainty interval and failed/incomplete updates remain visible. Study status and the capture-bias explanation are in Report details and evidence; no repeated principal Study in progress badge. Original chronology, reference adoption, coverage and downloads remain readable. Calibration, log loss, bounded results and original supporting documents remain available through the original saved reader. Historical candle report is a separate link at the bottom; it retains its independent status, dates and population. Immutable historical and original saved HTML retain their original rendering and date conventions.

Collection status consumes only the current saved display's digest-bound observation, separately dated and explicitly not rechecked. A missing observation does not invalidate the saved scientific report.

## Match rows and filters

Every retained cumulative opportunity gets a row, including missing captures, unresolved results and not-yet-due captures. Rows show Match, Kalshi home-win probability, Kalshi score and readable Details. Scored final scores appear under Match. Unscored rows never infer a final outcome from a current Bet Sheet or current provider data. Their scores remain unavailable; a valid saved probability may still appear. Details explain the saved disposition. Distinct game/opportunity identities preserve doubleheaders; no team/date deduplication.

Period options: Last 7 Days, Last 14 Days, Last 60 Days, Last 90 Days, This Season (default), Custom Period. Custom reveals From/To native calendars; both endpoints inclusive, using Central scheduled-event dates. Presets include the saved evidence-cutoff Central date and preceding N−1 days. This Season includes all opportunities in the report, including future known opportunities, and never implies full-season evidence coverage. Custom dates cannot exceed the saved data date. Team intersects the selected period. Invalid and empty selections are explicit.

Filters narrow rows only. The cumulative summary/population/uncertainty stay unchanged, stated next to the table. These are display filters, not new analytical windows or claims. Existing Protocol bounded scopes remain unchanged.

## Legacy match preparation

Legacy validated report packages contain scores and identities but do not embed every readable schedule/outcome dependency. An explicit offline command prepares a deterministic supplementary display file:

```sh
python mlb_performance_matches.py --reports REPORTS --archive ARCHIVE_PRIMARY --destination REPORTS/matches
```

It verifies the retained selected package/anchor/receipt through the existing reader contract; reads only normalized dependencies named by its frozen source manifest inventory; checks normalized hashes, conflicting identities, schedule/outcome chronology and measurement binding; and creates a package-named, digest-protected display supplement. Every source opportunity is represented. Original scores/probabilities are copied, never rescored. Team names are a stable display-only provider ID dictionary; unknown IDs remain explicit rather than guessed. No fixture game data is used in production.

Preparation never initializes, locks or writes the archive, contacts providers, refreshes status or selects a report. Output is separate from archives/source repositories. Existing identical output is idempotent; conflicting output fails visibly and is preserved. Publication is atomic and create-only. A separately selected scientific package needs its own explicit preparation; no silent old-row fallback. The browser has no archive path or preparation command and performs no writes.

The reader checks supplemental digest, selected package/report binding, complete opportunity membership, score/probability and disposition reconciliation. Local prepared display material shares the existing local-trust limitation: digests detect damage, not an adversary replacing both material and its digest. Independent deployment verification should compare actual prepared rows with retained source references. Missing/corrupt supplemental data hides match rows with a clear message while preserving the valid scientific summary. Original packages/renderers and exact evidence bytes are unchanged.

## Acceptance and limits

Must hold: no evidence/report mutation or acquisition; retained verified selection; complete opportunity accounting; exact scored row/summary reconciliation; trustworthy dates and outcomes; visible missing/invalid states; safe path and asset boundaries; two-decimal readable metrics; unchanged NFL reader and Bet Sheets. Validate date boundaries, custom errors, team filters, failed/missing display dependencies, source corruption, duplicate identities, empty/unscored sets and read-only operations.

Accepted limits: explicit manual display preparation for each newly selected scientific report; local saved results; unknown names use provider ID labels; unmeasured opportunities have no inferred final scores; original evidence pages keep their original date conventions. Existing archived capture gaps remain.

Deferred: model/supplier admission, arbitrary recalculated filtered summaries, Administration/update controls, automatic refresh, new inference, collector changes, study closure, positions/profit, cloud/services and whole-v1.3 release. Earlier documentation-candidate headings remain historical; subsequent implemented reporting and activation amendments govern current capabilities.
