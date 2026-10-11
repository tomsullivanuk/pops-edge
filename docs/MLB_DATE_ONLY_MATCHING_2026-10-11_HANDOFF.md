# Independent review handoff — date-only matching

Review candidate branch `codex/mlb-date-only-matching`, based on main 3ac474c3003b488d02228cb54420d3879a389f71, in `/Users/tom/Documents/Codex/2026-10-09/task-2/pops-edge-date-only-fix`. Resolve its exact commit from the parent receipt. Read AGENTS.md and linked design/implementer review. Do not self-certify implementation as independent review.

Owner authorized fixing the mapping and later controlled activation after independent review. Review now, read-only. No deploy, backfill, trading, archive rewriting or unrelated services.

Verify shared supporting/collector gates, complete-slate uniqueness, strict precise-time compatibility, ordered rule participants and date agreement, doubleheader/reschedule ambiguity rejection, preservation of historical union/derivation versions and old protocol IDs, clear rejection diagnostics, no quote reconstruction and unchanged five-slot T−6h capture. Challenge any unsupported inference from ticker/expiration/occurrence_datetime. Reproduce actual retained and fresh next-game mapping using supplied fixture/receipts; these are not historical forecasts.

Run relevant tests including tests.test_mlb_date_only_matching, tests.test_forecast_prospective_market_selection, tests.test_forecast_standalone_activation, tests.test_forecast_supporting_replay, tests.test_forecast_prospective_projection, tests.test_mlb_phase_evaluation and reporting/lifecycle regressions. Inspect task workspace full-production replay proof showing the October 11 missed snapshot remains unchanged. Write a separate review with exact head, findings/severity, acceptance scope and validation. Return it to the parent; only then may authorized commissioning proceed.
