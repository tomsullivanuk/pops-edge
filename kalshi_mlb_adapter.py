"""Bounded read-only Kalshi MLB winner-market adapter."""
from __future__ import annotations
import hashlib, json, time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable
import requests
from event_contracts import ContractError, Provenance
from market_contracts import *
from mlb_contracts import MLBGame, ScheduleObservation

BASE="https://external-api.kalshi.com/trade-api/v2"; ADAPTER_VERSION="kalshi-mlb-v1"; RETRY_CODES={429,500,502,503,504}
ALIASES={
    "arizona":"arizona diamondbacks","d-backs":"arizona diamondbacks","diamondbacks":"arizona diamondbacks",
    "a's":"athletics","oakland athletics":"athletics","atlanta":"atlanta braves","baltimore":"baltimore orioles",
    "boston":"boston red sox","red sox":"boston red sox","chicago c":"chicago cubs",
    "chicago ws":"chicago white sox","white sox":"chicago white sox","cincinnati":"cincinnati reds",
    "cleveland":"cleveland guardians","colorado":"colorado rockies","detroit":"detroit tigers",
    "houston":"houston astros","kansas city":"kansas city royals","los angeles a":"los angeles angels",
    "los angeles d":"los angeles dodgers","miami":"miami marlins","milwaukee":"milwaukee brewers",
    "minnesota":"minnesota twins","new york m":"new york mets","new york y":"new york yankees",
    "philadelphia":"philadelphia phillies","pittsburgh":"pittsburgh pirates","san diego":"san diego padres",
    "san francisco":"san francisco giants","seattle":"seattle mariners","st. louis":"st. louis cardinals",
    "tampa bay":"tampa bay rays","texas":"texas rangers","toronto":"toronto blue jays",
    "washington":"washington nationals",
}

def _canon(name): return ALIASES.get(str(name).strip().lower(),str(name).strip().lower())
def _dt(value): return datetime.fromisoformat(value.replace("Z","+00:00")) if value else None
def _dec(value):
    if value is None or value=="": return None
    return Decimal(str(value))
def _price(m,key):
    if key+"_dollars" in m: return _dec(m.get(key+"_dollars"))
    value=_dec(m.get(key)); return value/Decimal(100) if value is not None else None
def _digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

class KalshiReadOnlyClient:
    def __init__(self,transport:Callable=requests.get,timeout=15,retries=2): self.transport=transport; self.timeout=timeout; self.retries=retries
    def get(self,route,params=None):
        for attempt in range(self.retries+1):
            try:
                response=self.transport(BASE+route,params=params or {},timeout=self.timeout)
                if response.status_code in RETRY_CODES: raise requests.HTTPError(response=response)
                response.raise_for_status(); return response
            except (requests.Timeout,requests.ConnectionError,requests.HTTPError):
                if attempt==self.retries: raise
                time.sleep(2**attempt)
    def markets(self,limit=100,cursor=None): return self.get("/markets",{"limit":min(limit,1000),"cursor":cursor or "","status":"open"})
    def orderbook(self,ticker): return self.get(f"/markets/{ticker}/orderbook",{"depth":100})

def reconcile_market(market:dict,games:tuple[MLBGame,...],schedules:tuple[ScheduleObservation,...]):
    yes_label=market.get("yes_sub_title") or market.get("yes_label")
    if not yes_label: return None,(),(MarketIssue("ambiguous-side","YES participant is not explicitly identified"),)
    yes_name=_canon(yes_label); date_text=(market.get("expected_expiration_time") or market.get("close_time") or "")[:10]
    schedule_by_event={x.canonical_event_id:x for x in schedules}; participant_candidates=[]; dated_candidates=[]
    for game in games:
        names={_canon(game.home_team.display_name),_canon(game.away_team.display_name)}
        participant=None
        if yes_name==_canon(game.home_team.display_name): participant=game.home_team.canonical_team_id
        elif yes_name==_canon(game.away_team.display_name): participant=game.away_team.canonical_team_id
        schedule=schedule_by_event.get(game.event.canonical_event_id)
        if participant:
            participant_candidates.append((game,participant))
            if not date_text or (schedule and schedule.scheduled_start.date().isoformat()==date_text): dated_candidates.append((game,participant))
    candidates=dated_candidates or participant_candidates
    if len(candidates)==1: return candidates[0],(candidates[0][0].event.canonical_event_id,),()
    code="ambiguous-event" if len(candidates)>1 else "no-matching-event"
    return None,tuple(x[0].event.canonical_event_id for x in candidates),(MarketIssue(code,"market cannot be uniquely reconciled from explicit participant/date evidence"),)

def _book_levels(payload,at,endpoint):
    book=payload.get("orderbook_fp",payload.get("orderbook",payload)); levels=[]
    # Kalshi books commonly publish resting bids. Complement opposing bids into executable asks, labeled as a transformation by component provenance.
    direct=(book.get("yes_asks") or book.get("yes_ask") or [])
    for side,key in ((MarketSide.YES,"yes_asks"),(MarketSide.NO,"no_asks")):
        rows=book.get(key,[]) or []
        for i,row in enumerate(rows,1):
            p,q=row if isinstance(row,list) else (row.get("price"),row.get("quantity")); p=Decimal(str(p)); p=p/100 if p>1 else p
            levels.append(OrderBookLevel(side,p,Decimal(str(q)),i,PriceEvidenceKind.DIRECT_ASK,side,p,None,endpoint,at))
    for side,opposite_keys in ((MarketSide.YES,("no_dollars","no")),(MarketSide.NO,("yes_dollars","yes"))):
        if any(x.acquisition_side is side for x in levels): continue
        rows=[]
        for opposite in opposite_keys:
            if book.get(opposite): rows=book[opposite]; break
        converted=[]
        for row in rows:
            p,q=row if isinstance(row,list) else (row.get("price"),row.get("quantity")); p=Decimal(str(p)); p=p/100 if p>1 else p; converted.append((Decimal(1)-p,Decimal(str(q))))
        for i,(p,q) in enumerate(sorted(converted),1):
            provider_side=MarketSide.NO if side is MarketSide.YES else MarketSide.YES
            levels.append(OrderBookLevel(side,p,q,i,PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID,provider_side,Decimal(1)-p,"acquisition_price = 1 - opposite_side_bid",endpoint,at))
    return tuple(levels)

def _settlement_evidence(market):
    raw=market.get("rules_primary") or market.get("rules") or market.get("settlement_sources")
    if isinstance(raw,str): evidence=(raw,)
    elif isinstance(raw,list): evidence=tuple(str(x) for x in raw)
    else: evidence=()
    notional=market.get("notional_value_dollars")
    return evidence + ((f"notional_value_dollars={notional}",) if notional not in (None,"") else ())

def adapt_market(market:dict,*,games:tuple[MLBGame,...],schedules:tuple[ScheduleObservation,...],collected_at:datetime,orderbook_payload:dict|None=None,orderbook_collected_at:datetime|None=None,metadata_collected_at:datetime|None=None)->MarketAdapterResult:
    raw=_digest(market); market_id=str(market.get("ticker") or market.get("id") or "unknown")
    required=(market.get("ticker"),market.get("title"))
    if not all(required): return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("malformed-market","ticker and title are required"),),raw_evidence_sha256=raw)
    matched,candidates,issues=reconcile_market(market,games,schedules)
    if matched is None:
        outcome=MarketAdapterOutcome.AMBIGUOUS if candidates or any(x.code=="ambiguous-side" for x in issues) else MarketAdapterOutcome.REJECTED
        return MarketAdapterResult(outcome,market_id,None,None,None,issues,candidates,raw)
    game,participant_id=matched
    other=game.away_team if participant_id==game.home_team.canonical_team_id else game.home_team
    yes_label=market.get("yes_sub_title") or market.get("yes_label")
    no_label=market.get("no_sub_title") or market.get("no_label")
    settlement=_settlement_evidence(market)
    no_name=_canon(no_label) if no_label else None
    if no_name not in (_canon(yes_label),_canon(other.display_name)):
        return MarketAdapterResult(MarketAdapterOutcome.AMBIGUOUS,market_id,None,None,None,(MarketIssue("ambiguous-no-side","NO participant is not the explicit complementary event participant"),),candidates,raw)
    if not settlement:
        return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("missing-settlement-evidence","winner payout semantics require settlement evidence"),),candidates,raw)
    settlement_text=" ".join(settlement).lower()
    if not any(marker in settlement_text for marker in ("$1","one dollar","100 cents","notional_value_dollars=1.0000","notional_value_dollars=1")):
        return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("ambiguous-settlement-economics","settlement evidence does not establish a one-dollar winning payout"),),candidates,raw)
    if "win" in settlement_text and _canon(other.display_name) in settlement_text and _canon(market.get("yes_sub_title") or market.get("yes_label")) not in settlement_text:
        return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("settlement-side-conflict","settlement text contradicts the structured YES participant"),),candidates,raw)
    proposition=MarketProposition.winner(game.event.canonical_event_id,participant_id)
    status_map={"active":MarketStatus.OPEN,"open":MarketStatus.OPEN,"unopened":MarketStatus.CLOSED,"initialized":MarketStatus.CLOSED,"closed":MarketStatus.CLOSED,"paused":MarketStatus.SUSPENDED,"suspended":MarketStatus.SUSPENDED,"settled":MarketStatus.SETTLED,"finalized":MarketStatus.SETTLED,"cancelled":MarketStatus.CANCELLED,"canceled":MarketStatus.CANCELLED}
    status=status_map.get(str(market.get("status","")).lower(),MarketStatus.UNKNOWN)
    quote=QuoteState(_price(market,"yes_bid"),_price(market,"yes_ask"),_price(market,"no_bid"),_price(market,"no_ask"),_price(market,"last_price"),"dollars","provider values")
    metadata_at=metadata_collected_at or collected_at
    book_at=orderbook_collected_at or collected_at
    if orderbook_payload is not None and metadata_collected_at is None and book_at < collected_at:
        return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("incoherent-capture","order-book evidence predates its capture session"),),candidates,raw)
    capture_start=min(collected_at,metadata_at,book_at) if orderbook_payload is not None else min(collected_at,metadata_at)
    endpoint="/markets"; components=[ComponentEvidence("metadata-quotes",market_id,endpoint,metadata_at,raw,_digest(market))]
    book=()
    if orderbook_payload is not None:
        book_market_id=orderbook_payload.get("ticker") or orderbook_payload.get("market_ticker") or market_id
        if book_market_id != market_id: return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("component-market-mismatch","order book refers to a different provider market"),),candidates,raw)
        try: book=_book_levels(orderbook_payload,book_at,f"/markets/{market_id}/orderbook")
        except (ContractError,InvalidOperation,ValueError,TypeError,KeyError): return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("malformed-orderbook","order book contains malformed price or quantity evidence"),),candidates,raw)
        bd=_digest(orderbook_payload); components.append(ComponentEvidence("orderbook",market_id,f"/markets/{market_id}/orderbook",book_at,bd,bd))
    local_issues=list(issues)
    if not book: local_issues.append(MarketIssue("missing-depth","order-book depth was not supplied"))
    elif not any(x.acquisition_side is MarketSide.YES for x in book): local_issues.append(MarketIssue("missing-yes-depth","YES has no visible executable depth"))
    elif not any(x.acquisition_side is MarketSide.NO for x in book): local_issues.append(MarketIssue("missing-no-depth","NO has no visible executable depth"))
    intended_ask={MarketSide.YES:quote.yes_ask,MarketSide.NO:quote.no_ask}
    for side in MarketSide:
        side_levels=[x for x in book if x.acquisition_side is side]
        if side_levels and intended_ask[side] is not None and min(x.acquisition_price for x in side_levels)!=intended_ask[side]:
            return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("conflicting-quote-book",f"{side.value} ask conflicts with executable book"),),candidates,raw)
    prov=Provenance("kalshi",market_id,game.event.canonical_event_id,capture_start,transformations=("parsed-provider-market","complemented-resting-bids-when-direct-asks-absent") if orderbook_payload else ("parsed-provider-market",),raw_evidence_ref=raw,source_url=BASE+f"/markets/{market_id}",collector_version=ADAPTER_VERSION)
    series=ProviderMarketSeries(f"market-series:kalshi:{market_id}","kalshi",market_id,market["ticker"],proposition.proposition_id,SideSemantic(MarketSide.YES,proposition.proposition_id,participant_id,True,str(yes_label)),SideSemantic(MarketSide.NO,proposition.proposition_id,other.canonical_team_id,False,other.display_name),str(market["title"]),market.get("subtitle") or market.get("sub_title"),market.get("event_ticker"),_dt(market.get("open_time")),_dt(market.get("close_time")),settlement,prov)
    obs_seed=f"{market_id}|{capture_start.isoformat()}|{metadata_at.isoformat()}|{book_at.isoformat() if orderbook_payload else ''}|{raw}|{_digest(orderbook_payload) if orderbook_payload else ''}"
    try: obs=MarketObservation("market-observation:"+hashlib.sha256(obs_seed.encode()).hexdigest(),series.series_id,market_id,game.event.canonical_event_id,proposition.proposition_id,"capture:"+hashlib.sha256(obs_seed.encode()).hexdigest(),capture_start,status,quote,book,tuple(components),prov,_dec(market.get("volume_fp") or market.get("volume")),_dec(market.get("open_interest_fp") or market.get("open_interest")),tuple(local_issues))
    except ContractError as error: return MarketAdapterResult(MarketAdapterOutcome.REJECTED,market_id,None,None,None,(MarketIssue("incoherent-capture",error.detail),),candidates,raw)
    executable=status is MarketStatus.OPEN and bool(book)
    outcome=MarketAdapterOutcome.COMPLETE if executable and not local_issues else MarketAdapterOutcome.PARTIAL
    return MarketAdapterResult(outcome,market_id,proposition,series,obs,tuple(local_issues),candidates,raw)

def adapt_markets(markets,**kwargs): return tuple(adapt_market(m,**kwargs) for m in markets)
