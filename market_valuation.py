"""Deterministic analysis of executable binary-market acquisition; no policy."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from event_contracts import ContractError, ReasonCode, SerializableContract, _register, _require_identifier
from forecast_contracts import ForecastObservation, ForecastValidationStatus
from market_contracts import MarketObservation, MarketProposition, MarketSide, MarketStatus, PriceEvidenceKind, ProviderMarketSeries

class ExecutionStatus(str,Enum): FULL="full"; INSUFFICIENT_DEPTH="insufficient-depth"; UNAVAILABLE="unavailable"
@dataclass(frozen=True,slots=True,order=True)
class ConsumedLevel:
    acquisition_price: Decimal; quantity: Decimal; level: int; evidence_kind: PriceEvidenceKind
    provider_book_side: MarketSide; provider_price: Decimal; transformation: str|None
@dataclass(frozen=True,slots=True)
class ExecutionAnalysis:
    side: MarketSide; requested_quantity: Decimal; filled_quantity: Decimal; unfilled_quantity: Decimal; total_cost: Decimal; average_price: Decimal|None; worst_price: Decimal|None; levels: tuple[ConsumedLevel,...]; status: ExecutionStatus; limitations: tuple[str,...]=()

class FeeModel:
    model_id: str
    def calculate(self, *, side: MarketSide, quantity: Decimal, gross_cost: Decimal) -> Decimal: raise NotImplementedError
    @property
    def parameters(self)->tuple[tuple[str,str],...]: return ()
    quantity_basis="executed-contracts"; price_basis="gross-executable-acquisition-cost-dollars"; rounding_rule="exact-no-rounding"
@dataclass(frozen=True,slots=True)
class ZeroFeeModel(FeeModel):
    model_id: str="zero-fee-fixture-v1"
    def calculate(self,*,side,quantity,gross_cost): return Decimal(0)
@dataclass(frozen=True,slots=True)
class FlatPerContractFeeModel(FeeModel):
    fee_per_contract: Decimal; model_id: str="flat-per-contract-v1"
    def __post_init__(self):
        if self.fee_per_contract<0: raise ContractError(ReasonCode.VALIDATION_FAILURE,"fee cannot be negative")
    def calculate(self,*,side,quantity,gross_cost): return self.fee_per_contract*quantity
    @property
    def parameters(self): return (("fee_per_contract",str(self.fee_per_contract)),)

def executable_acquisition(observation:MarketObservation, side:MarketSide, quantity:Decimal)->ExecutionAnalysis:
    if not isinstance(quantity,Decimal) or quantity<=0: raise ContractError(ReasonCode.VALIDATION_FAILURE,"requested quantity must be a positive Decimal")
    if observation.status is not MarketStatus.OPEN: return ExecutionAnalysis(side,quantity,Decimal(0),quantity,Decimal(0),None,None,(),ExecutionStatus.UNAVAILABLE,(f"market status {observation.status.value} is not executable",))
    levels=sorted((x for x in observation.order_book if x.acquisition_side is side),key=lambda x:(x.acquisition_price,x.level))
    if not levels: return ExecutionAnalysis(side,quantity,Decimal(0),quantity,Decimal(0),None,None,(),ExecutionStatus.UNAVAILABLE,("requested side has no visible executable depth",))
    remaining=quantity; cost=Decimal(0); consumed=[]
    for level in levels:
        take=min(remaining,level.quantity)
        if take>0: consumed.append(ConsumedLevel(level.acquisition_price,take,level.level,level.evidence_kind,level.provider_book_side,level.provider_price,level.transformation)); cost+=take*level.acquisition_price; remaining-=take
        if remaining==0: break
    filled=quantity-remaining
    status=ExecutionStatus.FULL if remaining==0 else ExecutionStatus.INSUFFICIENT_DEPTH
    limitations=() if status is ExecutionStatus.FULL else ("expected-value amounts apply only to the partially executed quantity",)
    return ExecutionAnalysis(side,quantity,filled,remaining,cost,cost/filled if filled else None,consumed[-1].acquisition_price if consumed else None,tuple(consumed),status,limitations)

@dataclass(frozen=True,slots=True)
class TimingEvidence:
    forecast_collected_at: datetime; forecast_provider_timestamp: datetime|None; market_collected_at: datetime; market_component_times: tuple[datetime,...]; event_scheduled_start: datetime|None; forecast_after_start: bool|None; market_after_start: bool|None; component_spread_seconds: Decimal
@dataclass(frozen=True,slots=True)
class MarketValuation:
    analysis_id:str; algorithm_version:str; forecast_observation_id:str; market_observation_id:str; proposition_id:str; side:MarketSide; acquired_participant_id:str; forecast_probability:Decimal; requested_quantity:Decimal; executable_quantity:Decimal; unfilled_quantity:Decimal; gross_acquisition_cost:Decimal; average_executable_price:Decimal|None; marginal_price:Decimal|None; total_fees:Decimal; effective_acquisition_cost:Decimal; gross_expected_payout:Decimal; expected_profit:Decimal; expected_value_per_contract:Decimal|None; expected_return_on_capital:Decimal|None; raw_probability_price_spread:Decimal|None; fee_model_id:str; fee_parameters:tuple[tuple[str,str],...]; fee_quantity_basis:str; fee_price_basis:str; fee_rounding_rule:str; monetary_unit:str; payout_per_winning_contract:Decimal; execution:ExecutionAnalysis; timing:TimingEvidence; issues:tuple[str,...]

def value_market(*,forecast:ForecastObservation,market:MarketObservation,proposition:MarketProposition,series:ProviderMarketSeries,side:MarketSide,quantity:Decimal,fee_model:FeeModel,event_scheduled_start:datetime|None=None)->MarketValuation:
    event_id=proposition.canonical_event_id
    if forecast.reconciliation.matched_event is None or forecast.reconciliation.matched_event.canonical_event_id!=event_id or market.canonical_event_id!=event_id: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"forecast, market, and proposition event mismatch")
    if market.proposition_id!=proposition.proposition_id or series.proposition_id!=proposition.proposition_id or market.series_id!=series.series_id: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"market proposition or series mismatch")
    if forecast.validation_status is not ForecastValidationStatus.VALID: raise ContractError(ReasonCode.VALIDATION_FAILURE,"forecast must be valid")
    semantic=series.yes_semantic if side is MarketSide.YES else series.no_semantic
    if series.yes_semantic.participant_id != proposition.participant_id: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"YES semantic does not affirm the supplied proposition participant")
    probability=None
    for item in forecast.distribution.probabilities:
        if item.outcome.outcome_id==semantic.participant_id or item.outcome.semantic==f"participant-wins:{semantic.participant_id}": probability=item.probability
    if probability is None: raise ContractError(ReasonCode.CONFLICTING_NATIVE_IDENTITY,"forecast lacks the acquired participant outcome")
    claim_probability=probability
    execution=executable_acquisition(market,side,quantity)
    if execution.status is ExecutionStatus.UNAVAILABLE: raise ContractError(ReasonCode.VALIDATION_FAILURE,"market observation is not currently executable on the requested side")
    fees=fee_model.calculate(side=side,quantity=execution.filled_quantity,gross_cost=execution.total_cost); effective=execution.total_cost+fees; payout=claim_probability*execution.filled_quantity; profit=payout-effective
    avg=execution.average_price; spread=claim_probability-avg if avg is not None else None
    issues=execution.limitations
    times=tuple(x.collected_at for x in market.component_evidence)
    timing=TimingEvidence(forecast.collected_at,forecast.provider_updated_at or forecast.provider_published_at,market.collected_at,times,event_scheduled_start,None if event_scheduled_start is None else forecast.collected_at>=event_scheduled_start,None if event_scheduled_start is None else market.collected_at>=event_scheduled_start,market.component_timing_spread_seconds)
    seed="|".join(("market-valuation-v1",forecast.observation_id,market.observation_id,series.series_id,proposition.proposition_id,semantic.participant_id,side.value,str(quantity),fee_model.model_id,str(fee_model.parameters),fee_model.quantity_basis,fee_model.price_basis,fee_model.rounding_rule,str(event_scheduled_start)))
    return MarketValuation("valuation:"+hashlib.sha256(seed.encode()).hexdigest(),"market-valuation-v1",forecast.observation_id,market.observation_id,proposition.proposition_id,side,semantic.participant_id,claim_probability,quantity,execution.filled_quantity,execution.unfilled_quantity,execution.total_cost,avg,execution.worst_price,fees,effective,payout,profit,profit/execution.filled_quantity if execution.filled_quantity else None,profit/effective if effective else None,spread,fee_model.model_id,fee_model.parameters,fee_model.quantity_basis,fee_model.price_basis,fee_model.rounding_rule,"USD",Decimal(1),execution,timing,issues)

_CONTRACTS=(ConsumedLevel,ExecutionAnalysis,ZeroFeeModel,FlatPerContractFeeModel,TimingEvidence,MarketValuation)
for _c in _CONTRACTS:
    _c.to_dict=SerializableContract.to_dict; _c.to_json=SerializableContract.to_json; _c.from_dict=SerializableContract.__dict__["from_dict"]; _c.from_json=SerializableContract.__dict__["from_json"]
_register(*_CONTRACTS,enums=(ExecutionStatus,))
