# Abbreviated NFL market names

The Bet Sheet matcher now recognizes the explicit abbreviated team names observed
in the saved Week 2 Kalshi rules, including IND Colts, KC Chiefs and JAC Jaguars.
JAC Jaguars maps to the canonical schedule code JAX. Existing LA/NY aliases are
retained. No fuzzy matching, ticker-only identity, or relaxed settlement wording
is introduced. Team pair, YES label, date, event ambiguity, quote freshness and
full settlement-rule checks still apply.

Newly built Bet Sheets record `matching_version: nfl-market-aliases-v2`. Replay
uses the recorded matcher; boards without that field retain the legacy alias
set. Activity matching inside a versioned board uses that board's matcher too.
Unknown matching versions are rejected.

Must hold: the saved Week 2 example matches all 16 games/32 outcomes under the
new matcher; old archives replay without changes; unknown/conflicting names,
wrong dates, altered settlement rules and stale quotes remain rejected or
unavailable under the existing guards.

The correction is prospective for newly generated Bet Sheets. It does not
reinterpret stored research baselines or modify the legacy matcher used by
`nfl_performance_sources`. Expanding research matching is a separate decision.
Saved prices used in offline validation retain their original timestamps and
are not current offers. After deployment, a separately initiated normal refresh
can generate new comparisons using the corrected matcher. No source refresh,
baseline backfill, accounting change or deployment is part of implementation.
