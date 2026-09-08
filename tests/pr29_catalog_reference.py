"""Frozen pre-correction catalog oracle from main d0bad81699371d4a6898c60254da88af571ada5d.

Tests deliberately retain the original repeated serialization to independently
compare exact bytes and failure decisions with the optimized merger.
"""
import json
from datetime import datetime
from typing import Any, Iterable, Mapping
from forecast_standalone_activation import KalshiCatalogPage
from forecast_standalone_operations import OperationsError, canonical_bytes

def merge_kalshi_catalog_pages(pages:Iterable[KalshiCatalogPage])->bytes:
    """Produce a deterministic catalog union without concealing page conflicts."""
    ordered=tuple(sorted(pages,key=lambda x:x.position))
    if not ordered or ordered[0].position!=0 or ordered[0].request_cursor!="":raise OperationsError("pagination-incomplete","catalog chain lacks its first page")
    for prior,current in zip(ordered,ordered[1:]):
        if current.position!=prior.position+1 or current.request_cursor!=prior.next_cursor:raise OperationsError("pagination-incomplete","catalog cursor chain has a missing page")
    if ordered[-1].next_cursor!="":raise OperationsError("pagination-incomplete","catalog cursor chain lacks a terminal page")
    markets={}
    for page in ordered:
        for market in page.markets:
            if not isinstance(market,dict):raise OperationsError("malformed-response","catalog market is not an object")
            identity=market.get("ticker") or market.get("id")
            if not isinstance(identity,str) or not identity:raise OperationsError("provider-data-invalid","catalog market identity is absent")
            encoded=canonical_bytes(market);prior=markets.get(identity)
            if prior is not None and prior!=encoded:raise OperationsError("pagination-conflict","provider market conflicts across pages")
            markets[identity]=encoded
    union=[json.loads(markets[key]) for key in sorted(markets)]
    return canonical_bytes({"markets":union,"cursor":""})


def _market_settlement_at(market:Mapping[str,Any])->datetime|None:
    raw=market.get("settlement_ts")
    if raw is None:return None
    if not isinstance(raw,str):raise OperationsError("partition-integrity","market settlement timestamp is not text")
    try:value=datetime.fromisoformat(raw.replace("Z","+00:00"))
    except ValueError as exc:raise OperationsError("partition-integrity","market settlement timestamp is malformed") from exc
    if value.tzinfo is None or value.utcoffset() is None:raise OperationsError("partition-integrity","market settlement timestamp is naive")
    return value


def merge_retrospective_catalog_pages(pages:Iterable[KalshiCatalogPage],market_settled_at:datetime)->bytes:
    """Validate independent chains and select cross-partition records by cutoff."""
    if market_settled_at.tzinfo is None or market_settled_at.utcoffset() is None:raise OperationsError("partition-integrity","historical cutoff is naive")
    values=tuple(pages);partition_markets={}
    for partition in ("historical","live"):
        selected=tuple(sorted((x for x in values if x.partition==partition),key=lambda x:x.partition_position if x.partition_position is not None else -1))
        if not selected or any(x.partition_position!=position for position,x in enumerate(selected)):raise OperationsError("pagination-incomplete",f"{partition} catalog partition is incomplete")
        chain=tuple(KalshiCatalogPage(x.partition_position,x.request_cursor,x.next_cursor,x.raw,x.markets) for x in selected)
        partition_markets[partition]={((item.get("ticker") or item.get("id"))):item for item in json.loads(merge_kalshi_catalog_pages(chain))["markets"]}
    if any(x.partition not in {"historical","live"} for x in values):raise OperationsError("pagination-incomplete","retrospective catalog has a foreign partition")
    markets={}
    for identity in sorted(set(partition_markets["historical"])|set(partition_markets["live"])):
        historical=partition_markets["historical"].get(identity);live=partition_markets["live"].get(identity)
        if historical is None:
            settled=_market_settlement_at(live)
            if settled is not None and settled<market_settled_at:raise OperationsError("partition-integrity","live-only market belongs to historical storage")
            selected=live
        elif live is None:
            settled=_market_settlement_at(historical)
            if settled is None or settled>=market_settled_at:raise OperationsError("partition-integrity","historical-only market conflicts with cutoff authority")
            selected=historical
        elif canonical_bytes(historical)==canonical_bytes(live):
            settled=_market_settlement_at(historical)
            if settled is None:raise OperationsError("partition-integrity","duplicated market lacks settlement authority")
            selected=historical if settled<market_settled_at else live
        else:
            historical_settled=_market_settlement_at(historical);live_settled=_market_settlement_at(live)
            if historical_settled is None or live_settled is None:raise OperationsError("partition-integrity","conflicting duplicate lacks settlement authority")
            if historical_settled==live_settled:selected=historical if historical_settled<market_settled_at else live
            else:
                candidates=((historical,historical_settled<market_settled_at),(live,live_settled>=market_settled_at))
                valid=tuple(item for item,consistent in candidates if consistent)
                if len(valid)!=1:raise OperationsError("partition-integrity","conflicting duplicate settlement authority is ambiguous")
                selected=valid[0]
        markets[identity]=canonical_bytes(selected)
    return canonical_bytes({"markets":[json.loads(markets[key]) for key in sorted(markets)],"cursor":""})
