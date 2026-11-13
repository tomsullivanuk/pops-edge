# Independent v3.5 campaign review

October 16, 2026. Reviewer: delegated read-only Codex agent `v35_review`, separate from implementation. Scope: preflight scientific design, frozen code/pins, shared cohorts, scalar scores, paired bootstrap, gate and final report/register claims.

## Decision

**Accepted for the bounded scientific/reporting scope; no blockers remain.** Exact accepted RESULTS SHA-256 `96f3db7382aac2eb03aba59b9943aa0f075050283995cc7a6ef9e22af4928093`; register SHA-256 `615a47e5d2ce66dbf192ac323ef88fa45e0f3bb3e4083810e0fe079eb77fbb89`. Final review corrected stale register count/date/chronology wording and added M16 source provenance before acceptance. Independent numerical checks pass: 7,280 unique forecasts retain every saved v2 control column; scalar annual/pooled Brier and natural-log loss reconcile on full/common populations. Every 5,000-draw interval at 14/7 days reconstructed with per-game multiplicity weights; maximum difference 1.12e−16. Primary average gain −0.000026672, interval [−0.000269930,+0.000185215]; gate correctly fails average-size and pooled-log-loss conditions.

[Results](RESULTS.md), [protocol](PROTOCOL.md), [register](../../../docs/MLB_MODEL_EXPERIMENT_REGISTER.md), [preflight review](PREFLIGHT_REVIEW.md). Source predictions/weights/fitted contexts remain private. Reviewer did not fit or independently refit models, acquire data, contact third parties or mutate files. Author's separate saved-context replay and source-lineage checks are recorded in verification.json; do not attribute those model-use checks to the read-only reviewer.

## Limits and next gate

Repeated development/selection, actual-starter/as-of timing and opening-consensus proxy limitations persist. This review does not establish Kalshi accuracy, executable-price profitability or future-season generalization. No raw-provider revalidation, independent training rerun or pretraining audit is claimed. No production/external state was changed during review. After acceptance, publish only permitted code/aggregates/docs to existing draft PR #86; no merge, deployment, new tuning or follow-on experiment.
