"""Explicit read-only, non-persisting Kalshi MLB market inspection."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from kalshi_mlb_adapter import KalshiReadOnlyClient, adapt_markets
from market_contracts import MarketAdapterOutcome
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse

def run(argv=None, *, client=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mlb_fixture",type=Path,help="separately captured MLB Stats API schedule JSON")
    parser.add_argument("--limit",type=int,default=10)
    args=parser.parse_args(argv); collected=datetime.now(timezone.utc)
    raw=args.mlb_fixture.read_bytes(); payload=json.loads(raw)
    response=MLBStatsAPIResponse("/api/v1/schedule",(),collected,200,"local-fixture",payload,raw)
    facts=MLBStatsAPIAdapter().parse_response(response)
    games=tuple(x.game for x in facts.games if x.game is not None)
    schedules=tuple(x.schedule_observation for x in facts.games if x.schedule_observation is not None)
    provider_response=(client or KalshiReadOnlyClient()).markets(limit=args.limit)
    provider_payload=provider_response.json(); markets=provider_payload.get("markets")
    if not isinstance(markets,list): print("unsafe Kalshi response: markets list missing"); return 2
    results=adapt_markets(markets,games=games,schedules=schedules,collected_at=collected)
    for item in results:
        event=item.proposition.canonical_event_id if item.proposition else "unmapped"
        quote=item.observation.quotes if item.observation else None
        issue_codes=",".join(x.code for x in item.issues) or "none"
        print(f"market={item.provider_market_id} outcome={item.outcome.value} event={event} yes_ask={quote.yes_ask if quote else None} no_ask={quote.no_ask if quote else None} issues={issue_codes}")
    unsafe=not results or any(x.outcome in (MarketAdapterOutcome.AMBIGUOUS,MarketAdapterOutcome.REJECTED) for x in results)
    return 1 if unsafe else 0

def main(): raise SystemExit(run())
if __name__=="__main__": main()
