"""Provider-neutral market identity and immutable evidence contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from event_contracts import ContractError, Provenance, ReasonCode, SerializableContract, _register, _require_aware, _require_identifier, _require_text


class PropositionType(str, Enum): WINNER = "winner"
class MarketSide(str, Enum): YES = "yes"; NO = "no"
class MarketStatus(str, Enum): OPEN="open"; CLOSED="closed"; SUSPENDED="suspended"; SETTLED="settled"; CANCELLED="cancelled"; UNKNOWN="unknown"; UNSUPPORTED="unsupported"
class MarketAdapterOutcome(str, Enum): COMPLETE="complete"; PARTIAL="partial"; AMBIGUOUS="ambiguous"; REJECTED="rejected"
class PriceEvidenceKind(str, Enum): DIRECT_ASK="direct-ask"; DERIVED_FROM_OPPOSITE_BID="derived-from-opposite-bid"


def _decimal(value: Decimal, label: str, *, minimum=Decimal(0), maximum=None) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < minimum or (maximum is not None and value > maximum):
        raise ContractError(ReasonCode.VALIDATION_FAILURE, f"{label} is outside its valid range")


@dataclass(frozen=True, slots=True)
class MarketProposition:
    proposition_type: PropositionType
    canonical_event_id: str
    participant_id: str
    proposition_id: str

    def __post_init__(self):
        if self.proposition_type is not PropositionType.WINNER:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "only winner propositions are supported")
        _require_identifier(self.canonical_event_id, "canonical_event_id"); _require_identifier(self.participant_id, "participant_id")
        expected = f"winner:{self.canonical_event_id}:{self.participant_id}"
        if self.proposition_id != expected: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY, "proposition_id is not canonical")

    @classmethod
    def winner(cls, event_id: str, participant_id: str):
        return cls(PropositionType.WINNER, event_id, participant_id, f"winner:{event_id}:{participant_id}")


@dataclass(frozen=True, slots=True, order=True)
class MarketIssue:
    code: str
    detail: str
    def __post_init__(self): _require_identifier(self.code, "issue code"); _require_text(self.detail, ReasonCode.VALIDATION_FAILURE, "issue detail")


@dataclass(frozen=True, slots=True, order=True)
class ComponentEvidence:
    component: str; provider_market_id: str; endpoint: str; collected_at: datetime; raw_response_sha256: str; canonical_evidence_sha256: str
    def __post_init__(self):
        _require_identifier(self.component, "component"); _require_identifier(self.provider_market_id, "component provider_market_id"); _require_text(self.endpoint, ReasonCode.VALIDATION_FAILURE, "endpoint"); _require_aware(self.collected_at, "component collected_at")
        _require_identifier(self.raw_response_sha256, "raw digest"); _require_identifier(self.canonical_evidence_sha256, "canonical digest")


@dataclass(frozen=True, slots=True, order=True)
class OrderBookLevel:
    acquisition_side: MarketSide; acquisition_price: Decimal; quantity: Decimal; level: int
    evidence_kind: PriceEvidenceKind; provider_book_side: MarketSide; provider_price: Decimal
    transformation: str|None; source_endpoint: str; collected_at: datetime
    def __post_init__(self):
        _decimal(self.acquisition_price, "acquisition price", maximum=Decimal(1)); _decimal(self.provider_price, "provider price", maximum=Decimal(1)); _decimal(self.quantity, "quantity")
        if self.quantity <= 0 or self.level < 1: raise ContractError(ReasonCode.VALIDATION_FAILURE, "book quantity and level must be positive")
        _require_text(self.source_endpoint, ReasonCode.VALIDATION_FAILURE, "source endpoint"); _require_aware(self.collected_at, "book collected_at")
        if self.evidence_kind is PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID:
            if self.provider_book_side is self.acquisition_side or self.acquisition_price != Decimal(1)-self.provider_price or not self.transformation:
                raise ContractError(ReasonCode.VALIDATION_FAILURE, "derived acquisition offer must preserve an exact opposite-side bid complement")
        elif self.provider_book_side is not self.acquisition_side or self.provider_price != self.acquisition_price or self.transformation is not None:
            raise ContractError(ReasonCode.VALIDATION_FAILURE, "direct offer evidence cannot claim a transformation")


@dataclass(frozen=True, slots=True)
class QuoteState:
    yes_bid: Decimal|None=None; yes_ask: Decimal|None=None; no_bid: Decimal|None=None; no_ask: Decimal|None=None; last_trade: Decimal|None=None
    price_scale: str="dollars"; source_representation: str="decimal"
    def __post_init__(self):
        for name in ("yes_bid","yes_ask","no_bid","no_ask","last_trade"):
            value=getattr(self,name)
            if value is not None: _decimal(value, name, maximum=Decimal(1))
        if self.yes_bid is not None and self.yes_ask is not None and self.yes_bid > self.yes_ask: raise ContractError(ReasonCode.VALIDATION_FAILURE, "crossed YES quote")
        if self.no_bid is not None and self.no_ask is not None and self.no_bid > self.no_ask: raise ContractError(ReasonCode.VALIDATION_FAILURE, "crossed NO quote")


@dataclass(frozen=True, slots=True)
class SideSemantic:
    side: MarketSide; proposition_id: str; participant_id: str; affirms_proposition: bool; provider_label: str
    def __post_init__(self): _require_identifier(self.proposition_id, "proposition_id"); _require_identifier(self.participant_id, "participant_id"); _require_text(self.provider_label, ReasonCode.VALIDATION_FAILURE, "provider label")


@dataclass(frozen=True, slots=True)
class ProviderMarketSeries:
    series_id: str; provider: str; provider_market_id: str; ticker: str; proposition_id: str
    yes_semantic: SideSemantic; no_semantic: SideSemantic; title: str; subtitle: str|None
    event_ticker: str|None; open_time: datetime|None; close_time: datetime|None
    settlement_evidence: tuple[str,...]; provenance: Provenance
    def __post_init__(self):
        for v,n in ((self.series_id,"series_id"),(self.provider,"provider"),(self.provider_market_id,"provider_market_id"),(self.ticker,"ticker"),(self.proposition_id,"proposition_id")): _require_identifier(v,n)
        expected=f"market-series:{self.provider}:{self.provider_market_id}"
        if self.series_id != expected: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"noncanonical market series identity")
        if {self.yes_semantic.side,self.no_semantic.side}!={MarketSide.YES,MarketSide.NO} or not self.yes_semantic.affirms_proposition or self.no_semantic.affirms_proposition: raise ContractError(ReasonCode.VALIDATION_FAILURE,"invalid complementary side semantics")
        if self.yes_semantic.proposition_id != self.proposition_id or self.no_semantic.proposition_id != self.proposition_id: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"side semantic proposition mismatch")
        if self.yes_semantic.participant_id == self.no_semantic.participant_id: raise ContractError(ReasonCode.IDENTICAL_PARTICIPANTS,"YES and NO must identify complementary participants")
        for t in (self.open_time,self.close_time):
            if t is not None: _require_aware(t,"market series time")


@dataclass(frozen=True, slots=True)
class MarketObservation:
    observation_id: str; series_id: str; provider_market_id: str; canonical_event_id: str; proposition_id: str; capture_session_id: str
    collected_at: datetime; status: MarketStatus; quotes: QuoteState; order_book: tuple[OrderBookLevel,...]
    component_evidence: tuple[ComponentEvidence,...]; provenance: Provenance; volume: Decimal|None=None; open_interest: Decimal|None=None
    issues: tuple[MarketIssue,...]=()
    def __post_init__(self):
        for v,n in ((self.observation_id,"observation_id"),(self.series_id,"series_id"),(self.provider_market_id,"provider_market_id"),(self.canonical_event_id,"canonical_event_id"),(self.proposition_id,"proposition_id"),(self.capture_session_id,"capture_session_id")): _require_identifier(v,n)
        _require_aware(self.collected_at,"collected_at")
        if self.provenance.collected_at != self.collected_at or self.provenance.canonical_event_id != self.canonical_event_id: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"observation provenance mismatch")
        for value in (self.volume,self.open_interest):
            if value is not None: _decimal(value,"trading statistic")
        if any(x.provider_market_id != self.provider_market_id for x in self.component_evidence): raise ContractError(ReasonCode.CONFLICTING_SOURCE_MAPPING,"capture components refer to a different provider market")
        if any(x.collected_at < self.collected_at for x in self.component_evidence): raise ContractError(ReasonCode.INVALID_TIMESTAMP_CHRONOLOGY,"component collection cannot precede capture-session start")
        object.__setattr__(self,"order_book",tuple(sorted(self.order_book,key=lambda x:(x.acquisition_side.value,x.acquisition_price,x.level))))
        object.__setattr__(self,"component_evidence",tuple(sorted(self.component_evidence)))
        object.__setattr__(self,"issues",tuple(sorted(self.issues)))

    @property
    def component_timing_spread_seconds(self) -> Decimal:
        times=[x.collected_at for x in self.component_evidence]
        return Decimal(str((max(times)-min(times)).total_seconds())) if times else Decimal(0)


@dataclass(frozen=True, slots=True)
class MarketAdapterResult:
    outcome: MarketAdapterOutcome; provider_market_id: str; proposition: MarketProposition|None; series: ProviderMarketSeries|None; observation: MarketObservation|None
    issues: tuple[MarketIssue,...]=(); candidate_event_ids: tuple[str,...]=(); raw_evidence_sha256: str|None=None
    def __post_init__(self):
        _require_identifier(self.provider_market_id,"provider_market_id")
        if self.outcome in (MarketAdapterOutcome.COMPLETE,MarketAdapterOutcome.PARTIAL):
            if self.proposition is None or self.series is None or self.observation is None: raise ContractError(ReasonCode.VALIDATION_FAILURE,"mapped result requires proposition, series, and first observation")
        elif any(x is not None for x in (self.proposition,self.series,self.observation)): raise ContractError(ReasonCode.VALIDATION_FAILURE,"unresolved result cannot expose authoritative contracts")
        object.__setattr__(self,"issues",tuple(sorted(self.issues))); object.__setattr__(self,"candidate_event_ids",tuple(sorted(set(self.candidate_event_ids))))


_CONTRACTS=(MarketProposition,MarketIssue,ComponentEvidence,OrderBookLevel,QuoteState,SideSemantic,ProviderMarketSeries,MarketObservation,MarketAdapterResult)
for _c in _CONTRACTS:
    _c.to_dict=SerializableContract.to_dict; _c.to_json=SerializableContract.to_json; _c.from_dict=SerializableContract.__dict__["from_dict"]; _c.from_json=SerializableContract.__dict__["from_json"]
_register(*_CONTRACTS,enums=(PropositionType,MarketSide,MarketStatus,MarketAdapterOutcome,PriceEvidenceKind))
