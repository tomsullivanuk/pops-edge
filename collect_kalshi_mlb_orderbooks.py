"""Bounded public read-only collection of already identified Kalshi books."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from kalshi_mlb_adapter import KalshiReadOnlyClient


@dataclass(frozen=True,slots=True)
class OrderBookCapture:
    provider_market_id:str
    endpoint:str
    collected_at:datetime
    http_status:int
    raw_response_sha256:str
    canonical_sha256:str
    payload:dict

    def to_dict(self):
        return {"provider_market_id":self.provider_market_id,"endpoint":self.endpoint,"collected_at":self.collected_at.isoformat(),"http_status":self.http_status,"raw_response_sha256":self.raw_response_sha256,"canonical_sha256":self.canonical_sha256,"payload":self.payload}


def collect_orderbooks(market_ids,*,client=None,clock:Callable[[],datetime]=lambda:datetime.now(timezone.utc))->tuple[OrderBookCapture,...]:
    tickers=tuple(sorted(set(str(value).strip() for value in market_ids)))
    if not tickers or any(not ticker for ticker in tickers): raise ValueError("at least one explicit provider market ID is required")
    if len(tickers)>50: raise ValueError("bounded collection is limited to 50 explicitly identified markets")
    provider=client or KalshiReadOnlyClient(); captures=[]
    for ticker in tickers:
        response=provider.orderbook(ticker); collected=clock()
        if collected.tzinfo is None: raise ValueError("collection clock must be timezone-aware")
        raw=bytes(response.content); payload=response.json()
        if not isinstance(payload,dict): raise ValueError(f"order book response for {ticker} must be an object")
        normalized=dict(payload); normalized["ticker"]=ticker
        canonical=json.dumps(normalized,sort_keys=True,separators=(",",":"),default=str).encode()
        captures.append(OrderBookCapture(ticker,f"/markets/{ticker}/orderbook",collected,int(response.status_code),hashlib.sha256(raw).hexdigest(),hashlib.sha256(canonical).hexdigest(),normalized))
    return tuple(captures)


def collect_market_metadata(market_ids,*,client=None,clock:Callable[[],datetime]=lambda:datetime.now(timezone.utc))->tuple[OrderBookCapture,...]:
    tickers=tuple(sorted(set(str(value).strip() for value in market_ids)))
    if not tickers or len(tickers)>50: raise ValueError("bounded collection requires between 1 and 50 explicit market IDs")
    provider=client or KalshiReadOnlyClient(); captures=[]
    for ticker in tickers:
        response=provider.get(f"/markets/{ticker}"); collected=clock(); raw=bytes(response.content); envelope=response.json()
        market=envelope.get("market") if isinstance(envelope,dict) else None
        if not isinstance(market,dict) or str(market.get("ticker") or "")!=ticker: raise ValueError(f"market metadata response does not match {ticker}")
        canonical=json.dumps(market,sort_keys=True,separators=(",",":"),default=str).encode()
        captures.append(OrderBookCapture(ticker,f"/markets/{ticker}",collected,int(response.status_code),hashlib.sha256(raw).hexdigest(),hashlib.sha256(canonical).hexdigest(),market))
    return tuple(captures)


def write_captures(path:str|Path,captures:tuple[OrderBookCapture,...])->None:
    Path(path).write_text(json.dumps({"schema_version":"pops-edge-kalshi-orderbooks-v1","captures":[item.to_dict() for item in captures]},sort_keys=True,indent=2),encoding="utf-8")
