"""Deterministic Kalshi activity-to-current-position normalization.

Raw activity remains source evidence.  This adapter emits the authoritative
current-position summaries consumed by the PR8 Opportunity Board boundary.
"""
from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from market_contracts import MarketAdapterOutcome, MarketAdapterResult, MarketSide
from opportunity_board import Position

REQUIRED_HEADERS = frozenset({
    "type", "Original_Date", "Fee_In_Dollars", "Market_Ticker",
    "Direction", "Price_In_Cents", "Amount_In_Dollars",
})


def _decimal(value: str, label: str) -> Decimal:
    try: result=Decimal(str(value).strip())
    except InvalidOperation as error: raise ValueError(f"{label} must be an exact decimal") from error
    if not result.is_finite() or result < 0: raise ValueError(f"{label} must be a non-negative exact decimal")
    return result


def _timestamp(value: str) -> datetime:
    try: result=datetime.fromisoformat(str(value).strip().replace("Z","+00:00"))
    except ValueError as error: raise ValueError("activity Original_Date must be ISO-8601") from error
    if result.tzinfo is None: raise ValueError("activity Original_Date must include a timezone")
    return result


def read_activity_positions(path: str | Path, market_results: tuple[MarketAdapterResult,...]) -> tuple[Position,...]:
    source=Path(path); raw=source.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    with source.open(newline="",encoding="utf-8-sig") as handle:
        reader=csv.DictReader(handle); headers=frozenset(reader.fieldnames or ()); rows=list(reader)
    missing=REQUIRED_HEADERS-headers
    if missing: raise ValueError(f"activity export is missing required headers: {', '.join(sorted(missing))}")
    signatures=set()
    for row in rows:
        signature=tuple((header,row.get(header,"")) for header in sorted(headers))
        if signature in signatures: raise ValueError("activity export contains a duplicate row")
        signatures.add(signature)
    mapped={result.provider_market_id:result for result in market_results if result.outcome in (MarketAdapterOutcome.COMPLETE,MarketAdapterOutcome.PARTIAL) and result.series and result.observation}
    settlements={str(row.get("Market_Ticker") or "").strip() for row in rows if str(row.get("type") or "").strip()=="Settlement"}
    trades=defaultdict(list)
    for row in rows:
        if str(row.get("type") or "").strip()!="Trade": continue
        ticker=str(row.get("Market_Ticker") or "").strip()
        if not ticker: raise ValueError("Trade activity requires Market_Ticker")
        direction=str(row.get("Direction") or "").strip().lower()
        if direction not in ("yes","no"): raise ValueError("Trade Direction must be Yes or No")
        quantity=_decimal(row.get("Amount_In_Dollars") or "","Trade quantity")
        price_cents=_decimal(row.get("Price_In_Cents") or "","Trade price")
        if quantity <= 0 or price_cents > 100: raise ValueError("Trade quantity or price is outside its valid range")
        fee=_decimal(row.get("Fee_In_Dollars") or "0","Trade fee")
        trades[ticker].append((_timestamp(row.get("Original_Date") or ""),direction,quantity,price_cents/Decimal(100),fee))
    positions=[]
    for ticker in sorted(trades):
        if ticker in settlements: continue
        if ticker not in mapped: raise ValueError(f"activity references unknown or unreconciled market {ticker}")
        activity=sorted(trades[ticker]); opening_side=activity[0][1]
        entries=[item for item in activity if item[1]==opening_side]; exits=[item for item in activity if item[1]!=opening_side]
        entry_quantity=sum((item[2] for item in entries),Decimal(0)); exit_quantity=sum((item[2] for item in exits),Decimal(0))
        if exit_quantity > entry_quantity: raise ValueError(f"activity closes more contracts than were opened for {ticker}")
        open_quantity=entry_quantity-exit_quantity
        if open_quantity == 0: continue
        average=sum((item[2]*item[3] for item in entries),Decimal(0))/entry_quantity
        result=mapped[ticker]; side=MarketSide.YES if opening_side=="yes" else MarketSide.NO
        positions.append(Position(
            result.series.series_id,result.series.proposition_id,result.observation.canonical_event_id,
            side,open_quantity,average,max(item[0] for item in activity),f"kalshi-activity:{source.name}",
            sum((item[4] for item in entries),Decimal(0)),sum((item[4] for item in exits),Decimal(0)),digest,
        ))
    return tuple(positions)


def write_position_summary(path: str | Path, positions: tuple[Position,...]) -> None:
    fields=("Provider","Provider Market ID","Proposition ID","Canonical Event ID","Side","Open Quantity","Average Entry Cost","Captured At","Status","Entry Fees","Exit Fees","Evidence SHA256","Source Reference")
    with Path(path).open("w",newline="",encoding="utf-8") as output:
        writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader()
        for position in positions:
            writer.writerow({"Provider":"kalshi","Provider Market ID":position.series_id.removeprefix("market-series:kalshi:"),"Proposition ID":position.proposition_id,"Canonical Event ID":position.canonical_event_id,"Side":position.side.value,"Open Quantity":str(position.quantity),"Average Entry Cost":str(position.average_cost),"Captured At":position.captured_at.isoformat() if position.captured_at else "","Status":"Open","Entry Fees":str(position.entry_fees),"Exit Fees":str(position.exit_fees),"Evidence SHA256":position.evidence_sha256 or "","Source Reference":position.source_reference})
