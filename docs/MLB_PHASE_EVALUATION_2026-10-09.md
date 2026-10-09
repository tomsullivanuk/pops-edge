# MLB phase evaluation — October 9, 2026

## Owner direction and scope

Implement local code and tests for winner-probability evaluation in regular season and postseason. Preserve the accepted regular-season study. The new prospective postseason cohort includes scheduled starts at or after `2026-10-11T00:00:00-05:00` in `America/Chicago`, equivalent to `2026-10-11T05:00:00Z`. No historical backfill, retrospective postseason study, native-model fitting or operational activation is authorized by this implementation.

## Must hold

- Original regular-season Protocol identity and retained package bytes remain unchanged.
- Phase and game identity derive from authoritative MLB Evidence, independently of market availability.
- Postseason receives a separate immutable Protocol and report; no pooled metrics or denominators.
- T−6h and the five-slot/five-minute capture rules, home YES probability, Brier/log loss/calibration/uncertainty are inherited without alteration.
- Earlier postseason schedules are outside the new opportunity universe. Late activation produces visible missed opportunities, never reconstructed prices.
- The canonical prospective cohorts are disjoint. Repeated collector invocation cannot acquire the same slot twice.
- Saved phase navigation performs no acquisition or report regeneration. Missing packages and failed updates stay visible.

## Accepted limitations and deferred work

Small postseason samples, manual commissioning, local-machine availability, uncertain/rescheduled official starts, missing market mappings and visible capture failures remain accepted. Native models, historical repair, generic cohort configuration, in-play/other propositions, wagering policy, automatic recovery, publication/version changes and study closure are deferred.

## Official activation planning evidence

The complete public MLB Stats API slate was rechecked October 9 at 21:17:52 UTC via `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-11&hydrate=team`. HTTP 200 returned one declared and one observed game; request/retrieval timestamps, response headers and body SHA256 are retained in `../mlb-phase-evaluation-evidence/mlb-oct11-schedule-recheck-receipt.json`. The response returned gamePk 849809, Dodgers at Brewers, scheduled `2026-10-12T00:00:00Z` (October 11 19:00 CDT). Its T−6h target is October 11 13:00 CDT / 18:00 UTC. This is a provisional schedule observation, not a fixed deadline or capture. Recheck the official full slate before commissioning; an admitted midnight Central start would require capture from October 10 18:00 CDT / 23:00 UTC. Prepare before the earliest actual admitted T−6h target.

## Authority and implementation

Baseline main verified October 9: `50790ad82d7080553ca11a16eba28897bf4a290a`. Methodology, Product and Architecture amendments are part of this candidate. Existing historical scope statements describe the original studies and are superseded only by this explicit new prospective scope.

[PM/Chief Architect review](MLB_PHASE_EVALUATION_2026-10-09_REVIEW.md) · [Independent review handoff and commissioning plan](MLB_PHASE_EVALUATION_2026-10-09_HANDOFF.md).

## Owner authorization amendment — October 9, 2026

After independent acceptance and the P2 commissioning-order correction, Tom explicitly authorized the remaining commit/push/draft PR, exact-commit CI and review gates, ready/merge, controlled deployment/activation and necessary phase-report generation/publication for this specific change. This supersedes the earlier local-only action restriction; scientific scope, raw-evidence immutability, October 11 game-start boundary, T−6h, no retrospective backfill/candle acquisition and exclusion of unrelated native/NFL/vendor changes remain unchanged. Serious integrity, architecture or rollout issues require a pause; routine recoverable failures may be corrected within scope. No credential/access/security changes or purchases are authorized. Follow the corrected quiesce/pin/upgrade/verify/resume order and record exact old/new pins and preservation evidence.
