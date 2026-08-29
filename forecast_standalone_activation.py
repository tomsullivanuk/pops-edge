"""PR17C1 activation and live-read-only operational seams.

No function in this module performs network, Keychain, or scheduler activity at
import time.  All external effects sit behind explicit replaceable interfaces.
"""
from __future__ import annotations

import hashlib
import base64
import json
import os
import plistlib
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal,InvalidOperation
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.parse import urlencode,urlparse
from zoneinfo import ZoneInfo

from forecast_standalone_operations import (
    APPROVED_ACTIVATION_AT, DeploymentConfig, NamespaceArchive, OperatingMode,
    OperationsError, ProspectiveDiscoveryResult, authoritative_entries,
    canonical_bytes, discover_and_capture_prospective, index_health,
    reconcile_archive, secondary_status,
)

ACTIVATION_SCHEMA_VERSION="1"
APPROVED_EASTERN_DATE=date(2026,9,5)
APPROVED_ACTIVATION_UTC=datetime(2026,9,5,4,tzinfo=timezone.utc)
APPROVED_TIMEZONE="America/New_York"
ACTIVATION_DECISION_REFERENCE="product-owner:pr17c1:2026-09-05"
MAX_RESPONSE_BYTES=2_000_000
MAX_CATALOG_PAGES=100
KALSHI_CATALOG_PAGE_LIMIT=100
KALSHI_MLB_SERIES_TICKER="KXMLBGAME"
RETROSPECTIVE_WINDOW_START=datetime(2026,3,25,0,0,tzinfo=ZoneInfo("America/New_York"))
RETROSPECTIVE_WINDOW_SECONDS=14_169_600
MLB_DATE_RULE_VERSION="eastern-unresolved-obligations-lookback-2"
MLB_CORRECTION_LOOKBACK_DAYS=7
ACQUISITION_UNION_RULE_VERSION="provider-pages-canonical-union-1"
HEARTBEAT_SCHEMA_VERSION="1"


@dataclass(frozen=True,slots=True)
class ProspectiveActivationAuthority:
    authority_id:str;schema_version:str;eastern_date:date;timezone_name:str
    activation_at:datetime;activation_utc:datetime;decision_reference:str
    def __post_init__(self)->None:
        if self.schema_version!=ACTIVATION_SCHEMA_VERSION or self.eastern_date!=APPROVED_EASTERN_DATE or self.timezone_name!=APPROVED_TIMEZONE:raise OperationsError("activation-authority-invalid","approved date or timezone conflicts")
        if self.activation_at.isoformat()!=APPROVED_ACTIVATION_AT.isoformat() or self.activation_utc.isoformat()!=APPROVED_ACTIVATION_UTC.isoformat() or self.activation_at.astimezone(timezone.utc)!=self.activation_utc:raise OperationsError("activation-authority-invalid","Eastern and UTC boundaries do not reconcile exactly")
        expected=f"activation-authority:{hashlib.sha256(canonical_bytes({k:v for k,v in asdict(self).items() if k!='authority_id'})).hexdigest()}"
        if self.authority_id!=expected:raise OperationsError("activation-authority-invalid","activation identity conflicts")
    @classmethod
    def approved(cls)->"ProspectiveActivationAuthority":
        values=dict(schema_version=ACTIVATION_SCHEMA_VERSION,eastern_date=APPROVED_EASTERN_DATE,timezone_name=APPROVED_TIMEZONE,activation_at=APPROVED_ACTIVATION_AT,activation_utc=APPROVED_ACTIVATION_UTC,decision_reference=ACTIVATION_DECISION_REFERENCE)
        return cls(f"activation-authority:{hashlib.sha256(canonical_bytes(values)).hexdigest()}",**values)
    def to_json(self)->str:return canonical_bytes(self).decode()


APPROVED_ACTIVATION=ProspectiveActivationAuthority.approved()


def canonical_prospective_authority()->tuple[Any,Any]:
    """Construct the single reviewed PR17C1 activation/Protocol authority."""
    from forecast_research_contracts import ProbabilitySourceReference,ResearchContractProvenance,RulePurpose,VersionedRuleSpecification
    from forecast_standalone_research import ProspectiveStandaloneDesign,StandaloneDesignTag,StandaloneProbabilitySourceProtocol,StandaloneResearchActivationBoundary,StandaloneRule
    source=ProbabilitySourceReference.create(provider_id="kalshi",model_or_product_id="mlb-game-winner-market",model_or_product_version="2",proposition_type="winner",probability_representation_rule=VersionedRuleSpecification.create(RulePurpose.PROBABILITY_REPRESENTATION,"positive-depth-two-sided-quote","1"),transformation_rule=VersionedRuleSpecification.create(RulePurpose.PROBABILITY_TRANSFORMATION,"bid-offer-midpoint-complement","1"),availability_rule=VersionedRuleSpecification.create(RulePurpose.SOURCE_AVAILABILITY,"required-at-snapshot","1"))
    provenance=ResearchContractProvenance("pops-edge:pr17c1","1",notes=("reviewed prospective activation authority",),generated_at=datetime(2026,8,27,12,tzinfo=timezone.utc))
    activation=StandaloneResearchActivationBoundary.create(approved_calendar_date=APPROVED_EASTERN_DATE,activation_at=datetime(2026,9,5,0,0,tzinfo=ZoneInfo(APPROVED_TIMEZONE)),timezone_name=APPROVED_TIMEZONE,timezone_rule_version="iana-2026a",conversion_rule_version="eastern-midnight-1",product_owner_decision_reference=ACTIVATION_DECISION_REFERENCE,decision_effective_at=datetime(2026,8,27,12,tzinfo=timezone.utc),provenance=provenance)
    rules=dict(scope_rule=StandaloneRule("scope","2026-mlb-regular-season","2",(("competition","mlb"),("event_phase","regular-season"),("schedule_provider_id","mlb-stats-api"),("season","2026"),("scheduled_state_population","complete"),("sport","baseball"),("target_offset_minutes","-360"))),representation_rule=StandaloneRule("representation","home-team-yes","1"),scoring_rule=StandaloneRule("scoring","binary-brier-log-loss","1",(("decimal_precision","50"),("distribution","binary-complete"),("log_loss","extended-real"))),calibration_rule=StandaloneRule("calibration","fixed-bin-wace","1",(("boundaries","0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1"),("empty_bins","omit"),("endpoint_semantics","left-closed-right-open-final-closed"),("weighting","sample-share-absolute-gap"))),uncertainty_rule=StandaloneRule("uncertainty","deterministic-one-sample-bootstrap","1",(("confidence_level","0.95"),("resamples","200"))),report_rule=StandaloneRule("report","separate-standalone-report","1",(("bounded_window_durations","18000"),)))
    protocol=StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.PROSPECTIVE,design=ProspectiveStandaloneDesign(activation.standalone_research_activation_boundary_id,StandaloneRule("capture","five-slot-inclusive-upper-endpoint","1"),("prospective point-in-time capture",)),source=source,provenance=provenance,**rules)
    return activation,protocol


def canonical_retrospective_authority()->tuple[Any,Any]:
    """Construct the precommitted PR17C2 retrospective sibling authority."""
    from forecast_research_contracts import ResearchContractProvenance
    from forecast_standalone_research import RetrospectiveStandaloneDesign,StandaloneDesignTag,StandaloneProbabilitySourceProtocol,StandaloneRule
    activation,prospective=canonical_prospective_authority()
    provenance=ResearchContractProvenance("pops-edge:pr17c2","1",notes=("reviewed retrospective acquisition authority","164-day precommitted report window"),generated_at=datetime(2026,8,28,18,tzinfo=timezone.utc))
    scope=StandaloneRule("scope","2026-mlb-regular-season-retrospective","1",(("competition","mlb"),("event_phase","regular-season"),("ordinary_game","required"),("schedule_provider_id","mlb-stats-api"),("season","2026"),("sport","baseball"),("target_offset_minutes","-360"),("window_start","2026-03-25T00:00:00-04:00")))
    protocol=StandaloneProbabilitySourceProtocol.create(design_tag=StandaloneDesignTag.RETROSPECTIVE,design=RetrospectiveStandaloneDesign(activation.standalone_research_activation_boundary_id,StandaloneRule("selection","latest-real-one-minute-candle-before-target","1"),StandaloneRule("manifest","complete-archive-query-manifest","1"),("historical archive availability and provider revision limitations","same-candle aggregates are not simultaneous executable quotes")),source=prospective.source,scope_rule=scope,representation_rule=prospective.representation_rule,scoring_rule=prospective.scoring_rule,calibration_rule=prospective.calibration_rule,uncertainty_rule=prospective.uncertainty_rule,report_rule=StandaloneRule("report","separate-standalone-report","1",(("bounded_window_durations",str(RETROSPECTIVE_WINDOW_SECONDS)),)),provenance=provenance)
    return activation,protocol


def canonical_activation_authorities()->tuple[Any,Any,Any]:
    activation,prospective=canonical_prospective_authority();retro_activation,retrospective=canonical_retrospective_authority()
    if activation!=retro_activation:raise OperationsError("activation-authority-conflict","retrospective and prospective boundaries differ")
    return activation,retrospective,prospective


def initialize_activation(archive:NamespaceArchive,at:datetime)->tuple[str,str]:
    from forecast_standalone_operations import DesignAuthority,Disposition,_entry_values,pr17_contract_bundle,replay_pr17_archive,request_identity
    activation,retrospective,protocol=canonical_activation_authorities()
    if archive.config.mode is not OperatingMode.ACTIVATED or archive.config.activation_at.isoformat()!=APPROVED_ACTIVATION_AT.isoformat():raise OperationsError("activation-authority-invalid","initialization requires exact activated namespace")
    configured_ids=set(archive.config.research_protocol_ids);prospective_id=protocol.standalone_probability_source_protocol_id;retrospective_id=retrospective.standalone_probability_source_protocol_id
    if configured_ids not in ({prospective_id},{prospective_id,retrospective_id}):raise OperationsError("activation-authority-invalid","configuration names noncanonical Protocol authority")
    if archive.entries():
        state=replay_pr17_archive(archive,analysis_boundary=at);existing=state.bucket("activation_boundaries")+state.bucket("protocols")
    else:existing=()
    if existing and not set(existing).issubset({activation,retrospective,protocol}):raise OperationsError("activation-authority-conflict","initialized authority conflicts")
    with archive.mutation_lock():
        contracts=(activation,protocol) if configured_ids=={prospective_id} else (activation,retrospective,protocol)
        for contract in contracts:
            if contract in existing:continue
            normalized=pr17_contract_bundle(contract);raw=canonical_bytes(normalized);design=DesignAuthority.PROSPECTIVE if contract is protocol else DesignAuthority.RETROSPECTIVE if contract is retrospective else DesignAuthority.SUPPORTING;values=_entry_values(archive=archive,command="initialize-activation",request_id=request_identity({"contract_type":type(contract).__name__,"contract_sha256":hashlib.sha256(contract.to_json().encode()).hexdigest()}),invoked_at=at,endpoint="local://canonical-pr17c1-authority",disposition=Disposition.SUCCESS,protocol_id=getattr(contract,"standalone_probability_source_protocol_id",None),design=design,diagnostics=("canonical reviewed PR17C authority",),provider_effective_at=getattr(contract,"decision_effective_at",None));values["provider_id"]="canonical-pr17c-authority";archive._commit_locked(raw_body=raw,normalized=normalized,entry_values=values)
    return activation.standalone_research_activation_boundary_id,protocol.standalone_probability_source_protocol_id


def refresh_supporting_from_raw(*,archive:NamespaceArchive|None,mlb_raw:bytes,kalshi_raw:bytes,collected_at:datetime,catalog_pages:Iterable[KalshiCatalogPage]=(),mlb_pages:Iterable[bytes]=(),prior_state:Any=None,derive_only:bool=False,acquisition_command:str="refresh-supporting")->Mapping[str,Any]|tuple[Any,...]:
    """Decode live-shaped MLB/Kalshi material into established PR17 authority."""
    from event_contracts import ValidationStatus
    from forecast_comparative_research import ResearchCaptureOpportunity
    from forecast_research_contracts import ResearchContractProvenance
    from forecast_standalone_operations import DesignAuthority,Disposition,_entry_values,pr17_contract_bundle,replay_pr17_archive,request_identity
    from forecast_standalone_research import EventClassificationValidationStatus,EventPhase,StandaloneEventClassificationEvidence,create_standalone_eligibility_authority
    from kalshi_mlb_adapter import adapt_markets
    from mlb_outcome_adapter import MLBOutcomeAdapter
    from mlb_stats_api import MLBStatsAPIAdapter,MLBStatsAPIResponse
    from outcome_contracts import OutcomeHistory
    mlb_digest=hashlib.sha256(mlb_raw).hexdigest();kalshi_digest=hashlib.sha256(kalshi_raw).hexdigest();entries=archive.entries() if archive is not None else ()
    if not derive_only and any(x.get("provider_id")=="mlb-stats-api" and x.get("raw_object_sha256")==mlb_digest for x in entries) and any(x.get("provider_id")=="kalshi" and x.get("raw_object_sha256")==kalshi_digest for x in entries):return {"events":0,"contracts":0,"disposition":"unchanged"}
    try:mlb_payload=json.loads(mlb_raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"MLB"));kalshi_payload=json.loads(kalshi_raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"Kalshi"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","provider JSON is malformed") from exc
    if not isinstance(mlb_payload,dict) or not isinstance(kalshi_payload,dict) or set(kalshi_payload)!={"markets","cursor"} or not isinstance(kalshi_payload["markets"],list):raise OperationsError("incomplete-response","supporting provider shape is incomplete")
    response=MLBStatsAPIResponse("https://statsapi.mlb.com/api/v1/schedule",(),collected_at,200,"https://statsapi.mlb.com/api/v1/schedule",mlb_payload,mlb_raw)
    facts=MLBStatsAPIAdapter().parse_response(response);games=tuple(x.game for x in facts.games if x.game and x.schedule_observation);schedules=tuple(x.schedule_observation for x in facts.games if x.game and x.schedule_observation)
    if not games or len(games)!=len(schedules):raise OperationsError("provider-data-invalid","MLB schedule authority is incomplete")
    outcomes=MLBOutcomeAdapter().parse_response(response,canonical_games=games)
    if any(x.observation is None or x.observation.validation_status is not ValidationStatus.VALID for x in outcomes):raise OperationsError("provider-data-invalid","MLB outcome/status authority is invalid")
    state=prior_state or replay_pr17_archive(archive,analysis_boundary=collected_at)
    prior_histories={x.canonical_event_id:x for x in state.bucket("outcome_histories")}
    histories={};changed_histories=[]
    for result in outcomes:
        observation=result.observation;prior=prior_histories.get(observation.canonical_event_id)
        if prior is None:history=OutcomeHistory(observation.canonical_event_id,"mlb-stats-api",(observation,));changed=True
        else:
            latest=prior.latest
            if observation.collected_at<latest.collected_at:raise OperationsError("supporting-clock-reversed","MLB supporting observation is backdated")
            fields=("provider_status","scheduled_start","away_score","home_score","winning_participant_id","tie","unresolved","validation_status")
            changed=any(getattr(latest,key)!=getattr(observation,key) for key in fields)
            history=prior.append(observation) if changed else prior
        histories[observation.canonical_event_id]=history
        if changed:changed_histories.append(history)
    provenance=ResearchContractProvenance("pops-edge:pr17c1-supporting","1",notes=("provider-decoded supporting authority",),generated_at=collected_at)
    prior_classifications=tuple(state.bucket("classifications"));classifications={};changed_classifications=[]
    result_by_event={x.game.event.canonical_event_id:x for x in facts.games if x.game and x.schedule_observation}
    for event_id,result in sorted(result_by_event.items()):
        game=result.game;schedule=result.schedule_observation
        phase=EventPhase.REGULAR_SEASON if game.game_type=="R" else EventPhase.POSTSEASON if game.game_type in {"F","D","L","W","S","C","P"} else EventPhase.OTHER
        doubleheader=game.doubleheader_designation not in (None,"N","S") or (game.game_number or 1)>1
        doubleheader_id=(f"mlb-doubleheader:{game.season}:{'-'.join(sorted((game.away_team.canonical_team_id,game.home_team.canonical_team_id)))}:{schedule.scheduled_start.date().isoformat()}" if doubleheader else None)
        mapping=EventClassificationValidationStatus.VALID if phase is not EventPhase.OTHER else EventClassificationValidationStatus.INVALID
        reasons=() if mapping is EventClassificationValidationStatus.VALID else ("unsupported MLB game type",)
        prior=tuple(x for x in prior_classifications if x.canonical_event_id==event_id)
        current=max(prior,key=lambda x:(x.effective_at,x.standalone_event_classification_evidence_id)) if prior else None
        values=dict(authoritative_provider_id="mlb-stats-api",provider_event_id=str(game.game_pk),canonical_event_id=event_id,sport=game.event.sport.lower(),competition=game.event.competition.lower(),season=game.season,event_phase=phase,game_type=game.game_type,ordinary_game=phase is EventPhase.REGULAR_SEASON and not doubleheader,doubleheader_id=doubleheader_id,game_number=(game.game_number or 1) if doubleheader else None,participant_ids=tuple(sorted((game.away_team.canonical_team_id,game.home_team.canonical_team_id))),home_participant_id=game.home_team.canonical_team_id,away_participant_id=game.away_team.canonical_team_id,mapping_validation_status=mapping,validation_reasons=reasons,collected_at=collected_at,effective_at=collected_at,supersedes_classification_id=None,correction_reason=None,limitations=tuple(issue.code.value for issue in result.issues),provenance=provenance)
        scientific=(values["season"],values["event_phase"],values["game_type"],values["ordinary_game"],values["doubleheader_id"],values["game_number"],values["participant_ids"],mapping,reasons)
        before=None if current is None else (current.season,current.event_phase,current.game_type,current.ordinary_game,current.doubleheader_id,current.game_number,current.participant_ids,current.mapping_validation_status,current.validation_reasons)
        if current is not None and scientific==before:classification=current
        else:
            if current is not None:values.update(supersedes_classification_id=current.standalone_event_classification_evidence_id,correction_reason="authoritative MLB classification changed")
            classification=StandaloneEventClassificationEvidence.create(**values);changed_classifications.append(classification)
        classifications[event_id]=classification
    market_results=adapt_markets(kalshi_payload["markets"],games=games,schedules=schedules,collected_at=collected_at)
    complete=tuple(x for x in market_results if x.series and x.observation and x.series.yes_semantic.participant_id==next(g.home_team.canonical_team_id for g in games if g.event.canonical_event_id==x.observation.canonical_event_id))
    by_event={}
    for item in complete:by_event.setdefault(item.observation.canonical_event_id,[]).append(item)
    activation,canonical_retrospective,canonical_prospective=canonical_activation_authorities();archived_protocols={x.standalone_probability_source_protocol_id:x for x in state.bucket("protocols")};protocols=tuple(x for x in (canonical_retrospective,canonical_prospective) if x.standalone_probability_source_protocol_id in archived_protocols);contracts=list(changed_histories)+list(changed_classifications);opportunities=[];mapped=[];missing=[];ambiguous=[];prior_opportunity_ids={x.research_capture_opportunity_id for x in state.bucket("opportunities")};prior_series={x.series_id:x for x in state.bucket("market_series")}
    all_classifications=prior_classifications+tuple(changed_classifications)
    for event_id,history in sorted(histories.items()):
        classification=classifications[event_id]
        schedule_states=[]
        for observation in history.observations:
            if not schedule_states or observation.scheduled_start!=schedule_states[-1].scheduled_start:schedule_states.append(observation)
        for observation in schedule_states:
            for protocol in protocols:
                retrospective=protocol.design_tag.value=="retrospective"
                if retrospective and not (RETROSPECTIVE_WINDOW_START<=observation.scheduled_start<activation.activation_at):continue
                if not retrospective and observation.scheduled_start<activation.activation_at:continue
                opportunity=ResearchCaptureOpportunity.create(protocol.standalone_probability_source_protocol_id,observation.observation_id,"winner")
                if opportunity.research_capture_opportunity_id in prior_opportunity_ids:continue
                context,eligibility=create_standalone_eligibility_authority(protocol=protocol,opportunity=opportunity,outcome_history=history,classification=classification,classifications=all_classifications,analysis_boundary=collected_at,provenance=provenance)
                opportunities.append(opportunity);contracts.extend((opportunity,context,eligibility))
        items=by_event.get(event_id,())
        if len(items)==1:
            mapped.append(event_id);candidate=items[0].series;prior=prior_series.get(candidate.series_id)
            if prior is None:contracts.append(candidate)
            else:
                fields=tuple(name for name in candidate.__dataclass_fields__ if name!="provenance")
                if any(getattr(prior,name)!=getattr(candidate,name) for name in fields):raise OperationsError("market-series-correction-conflict",candidate.series_id)
        elif not items:missing.append(event_id)
        else:ambiguous.append(event_id)
    mlb_contracts=tuple(x for x in contracts if type(x).__name__!="ProviderMarketSeries");market_contracts=tuple(x for x in contracts if type(x).__name__=="ProviderMarketSeries")
    if derive_only:return tuple(contracts)
    page_values=tuple(catalog_pages) or (KalshiCatalogPage(0,"",json.loads(kalshi_raw)["cursor"],kalshi_raw,tuple(json.loads(kalshi_raw)["markets"])),)
    raw_mlb_pages=tuple(mlb_pages) or (mlb_raw,);mlb_page_values=tuple(_mlb_page_tuple(item,index) for index,item in enumerate(raw_mlb_pages))
    kalshi_page_values=page_values
    with archive.mutation_lock():
        protocol_id=protocols[0].standalone_probability_source_protocol_id if len(protocols)==1 else None
        mlb_acquisition=publish_verified_acquisition(archive=archive,provider="mlb-stats-api",union_raw=mlb_raw,pages=mlb_page_values,contracts=mlb_contracts,collected_at=collected_at,protocol_id=protocol_id,command=acquisition_command)
        kalshi_acquisition=publish_verified_acquisition(archive=archive,provider="kalshi",union_raw=kalshi_raw,pages=kalshi_page_values,contracts=market_contracts,collected_at=collected_at,protocol_id=protocol_id,command=acquisition_command,dependencies=(mlb_acquisition["acquisition_id"],))
    return {"mlb_manifest_id":mlb_acquisition["manifest_entry_id"],"kalshi_manifest_id":kalshi_acquisition["manifest_entry_id"],"events":len(games),"contracts":len(contracts),"mapped":len(mapped),"missing":len(missing),"ambiguous":len(ambiguous),"catalog_pages":len(page_values),"mlb_pages":len(mlb_page_values),"disposition":"success" if contracts else "unchanged"}


def _unique_object(pairs,label):
    value={}
    for key,item in pairs:
        if key in value:raise OperationsError("malformed-response",f"{label} response contains duplicate keys")
        value[key]=item
    return value


@dataclass(frozen=True,slots=True)
class KalshiCatalogPage:
    position:int;request_cursor:str;next_cursor:str;raw:bytes;markets:tuple[Mapping[str,Any],...]
    started_at:datetime|None=None;completed_at:datetime|None=None;endpoint:str|None=None
    partition:str|None=None;partition_position:int|None=None


@dataclass(frozen=True,slots=True)
class ProviderPageAcquisition:
    """A provider response page with its real request chronology."""
    request_identity:str;endpoint:str;raw:bytes;started_at:datetime;completed_at:datetime
    position:int=0;provider:str="mlb-stats-api";acquisition_context:str="command-start-fixed";request_authority:str|None=None
    def __post_init__(self)->None:
        if not isinstance(self.request_identity,str) or not self.endpoint or not isinstance(self.raw,bytes):raise OperationsError("acquisition-page-invalid","typed provider page is incomplete")
        if any(value.tzinfo is None or value.utcoffset() is None for value in (self.started_at,self.completed_at)) or self.completed_at<self.started_at:raise OperationsError("trusted-clock-reversed","typed provider page chronology is invalid")


def acquire_kalshi_catalog_pages(fetch:Callable[[str],bytes],*,maximum_pages:int=MAX_CATALOG_PAGES,clock:Callable[[],datetime]|None=None,command_start:datetime|None=None,path_builder:Callable[[str],str]|None=None)->tuple[KalshiCatalogPage,...]:
    """Follow and validate the complete documented cursor chain."""
    if maximum_pages<1 or maximum_pages>MAX_CATALOG_PAGES:raise OperationsError("pagination-bound","catalog page bound is invalid")
    pages=[];cursor="";requested=set()
    for position in range(maximum_pages):
        if cursor in requested:raise OperationsError("pagination-loop","catalog cursor repeats")
        requested.add(cursor);started=clock() if clock else command_start;raw=fetch(cursor);completed=clock() if clock else command_start
        if started is not None:
            if command_start is None or any(x.tzinfo is None or x.utcoffset() is None for x in (command_start,started,completed)):raise OperationsError("trusted-clock-invalid","page chronology requires aware trusted times")
            if started<command_start or completed<started or (pages and started<pages[-1].completed_at):raise OperationsError("trusted-clock-reversed","catalog page chronology is not monotonic")
        if len(raw)>MAX_RESPONSE_BYTES:raise OperationsError("transport-oversized","catalog page exceeds the response bound")
        try:value=json.loads(raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"Kalshi"))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","catalog page is malformed") from exc
        if not isinstance(value,dict) or set(value)!={"markets","cursor"} or not isinstance(value["markets"],list) or not isinstance(value["cursor"],str):raise OperationsError("incomplete-response","catalog page shape is incomplete")
        next_cursor=value["cursor"]
        if next_cursor and next_cursor in requested:raise OperationsError("pagination-loop","catalog cursor repeats")
        pages.append(KalshiCatalogPage(position,cursor,next_cursor,raw,tuple(value["markets"]),started,completed,(path_builder or encoded_kalshi_catalog_path)(cursor)))
        if not next_cursor:return tuple(pages)
        cursor=next_cursor
    raise OperationsError("pagination-bound","catalog did not terminate within its page bound")


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


def merge_retrospective_catalog_pages(pages:Iterable[KalshiCatalogPage])->bytes:
    """Validate historical and live cursor chains independently, then union them."""
    values=tuple(pages);unions=[]
    for partition in ("historical","live"):
        selected=tuple(sorted((x for x in values if x.partition==partition),key=lambda x:x.partition_position if x.partition_position is not None else -1))
        if not selected or any(x.partition_position!=position for position,x in enumerate(selected)):raise OperationsError("pagination-incomplete",f"{partition} catalog partition is incomplete")
        chain=tuple(KalshiCatalogPage(x.partition_position,x.request_cursor,x.next_cursor,x.raw,x.markets) for x in selected)
        unions.append(json.loads(merge_kalshi_catalog_pages(chain))["markets"])
    if any(x.partition not in {"historical","live"} for x in values):raise OperationsError("pagination-incomplete","retrospective catalog has a foreign partition")
    markets={}
    for union in unions:
        for market in union:
            identity=market.get("ticker") or market.get("id");encoded=canonical_bytes(market);prior=markets.get(identity)
            if prior is not None and prior!=encoded:raise OperationsError("pagination-conflict","provider market conflicts across catalog partitions")
            markets[identity]=encoded
    return canonical_bytes({"markets":[json.loads(markets[key]) for key in sorted(markets)],"cursor":""})


def required_mlb_query_dates(*,trusted_at:datetime,histories:Iterable[Any]=(),purpose:str="schedule",lookback_days:int=MLB_CORRECTION_LOOKBACK_DAYS)->tuple[date,...]:
    """Versioned, bounded Eastern-date selection for obligations and corrections."""
    if trusted_at.tzinfo is None or trusted_at.utcoffset() is None:raise OperationsError("trusted-clock-invalid","MLB date selection requires an aware clock")
    if purpose not in {"schedule","outcomes"} or not 1<=lookback_days<=31:raise OperationsError("date-rule-invalid",MLB_DATE_RULE_VERSION)
    local=trusted_at.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date();values={local}
    if purpose=="schedule":values.add(local+timedelta(days=1))
    else:values.add(local-timedelta(days=1))
    lower=local-timedelta(days=lookback_days)
    for history in histories:
        latest=history.latest
        scheduled=latest.scheduled_start.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date()
        if purpose=="outcomes":
            terminal_non_played=latest.provider_status.value=="cancelled"
            if latest.unresolved and not terminal_non_played:values.add(scheduled)
            elif not latest.unresolved and lower<=scheduled<=local:values.add(scheduled)
        elif lower<=scheduled<=local+timedelta(days=1):values.add(scheduled)
    return tuple(sorted(values))


def merge_mlb_schedule_responses(responses:Iterable[bytes])->bytes:
    """Merge a complete multi-date acquisition, rejecting conflicting games."""
    games={}
    for raw in responses:
        if len(raw)>MAX_RESPONSE_BYTES:raise OperationsError("transport-oversized","MLB response exceeds the bound")
        try:value=json.loads(raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"MLB"))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","MLB response is malformed") from exc
        if not isinstance(value,dict) or not isinstance(value.get("dates"),list):raise OperationsError("incomplete-response","MLB multi-date response is incomplete")
        for day in value["dates"]:
            if not isinstance(day,dict) or not isinstance(day.get("games"),list):raise OperationsError("incomplete-response","MLB date response is incomplete")
            for game in day["games"]:
                identity=game.get("gamePk") if isinstance(game,dict) else None
                if not isinstance(identity,int):raise OperationsError("provider-data-invalid","MLB game identity is absent")
                encoded=canonical_bytes(game);prior=games.get(identity)
                if prior is not None and prior!=encoded:raise OperationsError("multi-date-conflict","MLB game conflicts across date responses")
                games[identity]=encoded
    if not games:return canonical_bytes({"dates":[]})
    grouped={}
    for identity in sorted(games):
        game=json.loads(games[identity]);day=str(game.get("officialDate") or game.get("gameDate","")[:10]);grouped.setdefault(day,[]).append(game)
    return canonical_bytes({"dates":[{"date":day,"games":grouped[day]} for day in sorted(grouped)]})


def encoded_kalshi_catalog_path(cursor:str)->str:
    if not isinstance(cursor,str):raise OperationsError("pagination-cursor-invalid","catalog cursor must be text")
    return "/markets?"+urlencode({"series_ticker":KALSHI_MLB_SERIES_TICKER,"status":"open","limit":str(KALSHI_CATALOG_PAGE_LIMIT),**({"cursor":cursor} if cursor else {})})


def encoded_kalshi_retrospective_catalog_path(cursor:str,*,historical:bool)->str:
    if not isinstance(cursor,str):raise OperationsError("pagination-cursor-invalid","catalog cursor must be text")
    route="/historical/markets" if historical else "/markets"
    return route+"?"+urlencode({"series_ticker":KALSHI_MLB_SERIES_TICKER,"limit":str(KALSHI_CATALOG_PAGE_LIMIT),**({"cursor":cursor} if cursor else {})})


def acquire_retrospective_catalog_pages(fetch:Callable[[str],bytes],*,clock:Callable[[],datetime],command_start:datetime)->tuple[KalshiCatalogPage,...]:
    """Acquire both moving Kalshi catalog partitions within independent caps."""
    combined=[]
    for historical,partition in ((True,"historical"),(False,"live")):
        builder=lambda cursor,historical=historical:encoded_kalshi_retrospective_catalog_path(cursor,historical=historical)
        pages=acquire_kalshi_catalog_pages(lambda cursor,builder=builder:fetch(builder(cursor)),clock=clock,command_start=command_start,path_builder=builder)
        for page in pages:combined.append(KalshiCatalogPage(len(combined),page.request_cursor,page.next_cursor,page.raw,page.markets,page.started_at,page.completed_at,page.endpoint,partition,page.position))
    return tuple(combined)


def canonical_kalshi_candle_path(market_ticker:str,target_at:datetime,*,historical:bool)->str:
    """Return the exact real-candle query for the strict five-minute window."""
    if target_at.tzinfo is None or target_at.utcoffset() is None:raise OperationsError("trusted-clock-invalid","retrospective target must be aware")
    if not market_ticker or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for ch in market_ticker):raise OperationsError("transport-configuration","provider market identity is invalid")
    start_ts=int((target_at.astimezone(timezone.utc)-timedelta(minutes=5)).timestamp())+1
    end_ts=int(target_at.astimezone(timezone.utc).timestamp())
    prefix="/historical/markets" if historical else f"/series/{KALSHI_MLB_SERIES_TICKER}/markets"
    return f"{prefix}/{market_ticker}/candlesticks?"+urlencode((("start_ts",start_ts),("end_ts",end_ts),("period_interval",1)))


def adapt_kalshi_candles(payload:Mapping[str,Any],*,market_ticker:str,target_at:datetime)->Mapping[str,Any]:
    """Normalize either documented Kalshi candle shape without synthesizing data."""
    if not isinstance(payload,dict) or set(payload)!={"ticker","candlesticks"} or payload.get("ticker")!=market_ticker or not isinstance(payload.get("candlesticks"),list):raise OperationsError("incomplete-response","historical candle response shape conflicts")
    candles=[]
    for value in payload["candlesticks"]:
        if not isinstance(value,dict) or not isinstance(value.get("end_period_ts"),int):raise OperationsError("provider-data-invalid","candle timestamp is invalid")
        ended=datetime.fromtimestamp(value["end_period_ts"],timezone.utc)
        if not target_at-timedelta(minutes=5)<ended<=target_at:raise OperationsError("provider-data-invalid","candle falls outside the authorized strict window")
        def close(side):
            item=value.get(side)
            if not isinstance(item,dict):return None
            raw=item.get("close_dollars",item.get("close"))
            if raw is None:return None
            try:result=Decimal(str(raw))
            except InvalidOperation as exc:raise OperationsError("provider-data-invalid","candle close is not decimal") from exc
            if not Decimal(0)<=result<=Decimal(1):raise OperationsError("provider-data-invalid","candle close is outside probability bounds")
            return str(result)
        candles.append({"candle_end_at":ended.isoformat(),"close_yes_bid":close("yes_bid"),"close_yes_ask":close("yes_ask")})
    candles.sort(key=lambda x:x["candle_end_at"])
    return {"pages":[{"position":0,"cursor":"initial","next_cursor":None,"terminal":True,"candles":candles}]}


def canonical_mlb_schedule_request(query_date:date|str)->tuple[str,str]:
    """Return the canonical bounded-transport path and absolute MLB endpoint."""
    from mlb_stats_api import MLBStatsAPIClient
    if isinstance(query_date,str):
        parsed=date.fromisoformat(query_date)
        if parsed.isoformat()!=query_date:raise ValueError("MLB request date is not canonical ISO")
    elif isinstance(query_date,date):parsed=query_date
    else:raise TypeError("MLB request date must be a date or canonical ISO text")
    endpoint,parameters=MLBStatsAPIClient.schedule_request(parsed);query=urlencode(parameters)
    return urlparse(endpoint).path+"?"+query,endpoint+"?"+query


def _canonical_json_digest(raw:bytes)->str:
    try:return hashlib.sha256(canonical_bytes(json.loads(raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"provider")))).hexdigest()
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","acquisition material is malformed") from exc


def _mlb_page_tuple(item:Any,index:int)->tuple[str,str,bytes]:
    if isinstance(item,ProviderPageAcquisition):return item
    if not isinstance(item,bytes):return item
    payload=json.loads(item);dates=tuple(str(x.get("date")) for x in payload.get("dates",()) if isinstance(x,dict) and x.get("date"))
    identity=dates[0] if len(set(dates))==1 else f"page-{index}"
    return identity,canonical_mlb_schedule_request(identity)[1],item


def _page_material(item:Any,index:int,collected_at:datetime)->tuple[str,str,bytes,datetime,datetime]:
    if isinstance(item,KalshiCatalogPage):return item.request_cursor,item.endpoint or encoded_kalshi_catalog_path(item.request_cursor),item.raw,item.started_at or collected_at,item.completed_at or collected_at
    if isinstance(item,ProviderPageAcquisition):return item.request_identity,item.endpoint,item.raw,item.started_at,item.completed_at
    values=_mlb_page_tuple(item,index)
    if len(values)==3:return (*values,collected_at,collected_at)
    return values


def publish_verified_acquisition(*,archive:NamespaceArchive,provider:str,union_raw:bytes,pages:Iterable[Any],contracts:Iterable[Any],collected_at:datetime,protocol_id:str|None,command:str,dependencies:Iterable[str]=(),fail_after_pages:int|None=None)->Mapping[str,Any]:
    """Preserve exact pages, then bind contracts to their verified derived union."""
    from forecast_standalone_operations import DesignAuthority,Disposition,_entry_values,pr17_contract_bundle,request_identity
    page_items=tuple(pages);page_values=tuple(_page_material(item,index,collected_at) for index,item in enumerate(page_items))
    if not page_values:raise OperationsError("acquisition-incomplete","provider acquisition has no exact pages")
    for index,item in enumerate(page_items):
        if isinstance(item,ProviderPageAcquisition) and (item.position!=index or item.provider!=provider or item.acquisition_context not in {"command-start-fixed",collected_at.isoformat()}):raise OperationsError("acquisition-page-conflict","typed provider-page identity context conflicts")
    if collected_at.tzinfo is None or collected_at.utcoffset() is None:raise OperationsError("trusted-clock-invalid","acquisition command start must be aware")
    prior_completion=collected_at
    for identity,endpoint,raw,started,completed in page_values:
        if started.tzinfo is None or started.utcoffset() is None or completed.tzinfo is None or completed.utcoffset() is None or started<collected_at or completed<started or started<prior_completion:raise OperationsError("trusted-clock-reversed","provider page chronology conflicts with command start")
        prior_completion=completed
    partitions=tuple((item.partition,item.partition_position) if isinstance(item,KalshiCatalogPage) else (None,None) for item in page_items)
    group_material={"provider":provider,"command":command,"collected_at":collected_at,"pages":tuple((identity,endpoint,started,completed,hashlib.sha256(raw).hexdigest(),*partitions[index]) for index,(identity,endpoint,raw,started,completed) in enumerate(page_values)),"union_rule":ACQUISITION_UNION_RULE_VERSION}
    group_id="provider-acquisition:"+hashlib.sha256(canonical_bytes(group_material)).hexdigest();descriptors=[]
    for position,(identity,endpoint,raw,started,completed) in enumerate(page_values):
        digest=hashlib.sha256(raw).hexdigest();descriptor={"position":position,"request_identity":identity,"endpoint":endpoint,"raw_sha256":digest,"raw_ref":f"raw:{digest}","started_at":started,"completed_at":completed}
        if partitions[position][0] is not None:descriptor.update(partition=partitions[position][0],partition_position=partitions[position][1])
        normalized={"schema_version":"1","record_kind":"pr17c1-provider-page","acquisition_id":group_id,"provider":provider,**descriptor}
        values=_entry_values(archive=archive,command=command+"-page",request_id=request_identity({"acquisition_id":group_id,"position":position,"request_identity":identity,"raw_sha256":digest}),invoked_at=completed,endpoint=endpoint,disposition=Disposition.SUCCESS,protocol_id=protocol_id,design=DesignAuthority.SUPPORTING,diagnostics=("exact create-only provider response page",),provider_effective_at=completed);values["provider_id"]=provider
        entry=archive._commit_locked(raw_body=raw,normalized=normalized,entry_values=values);descriptors.append({**descriptor,"manifest_entry_id":entry.manifest_entry_id})
        if fail_after_pages==position+1:raise OperationsError("injected-acquisition-interruption",group_id)
    contract_values=tuple(contracts);serialized=tuple(sorted(x.to_json() for x in contract_values))
    acquisition_completed_at=page_values[-1][4];normalized={"schema_version":"1","record_kind":"pr17c1-acquisition-bundle","acquisition_id":group_id,"family":command,"provider":provider,"dependencies":tuple(sorted(set(dependencies))),"command_started_at":collected_at,"command_started_at_iso":collected_at.isoformat(),"acquisition_completed_at":acquisition_completed_at,"pages":tuple(descriptors),"union_rule":ACQUISITION_UNION_RULE_VERSION,"normalized_union_sha256":_canonical_json_digest(union_raw),"contracts":serialized}
    values=_entry_values(archive=archive,command=command,request_id=request_identity({"acquisition_id":group_id,"normalized_union_sha256":normalized["normalized_union_sha256"],"contracts_sha256":hashlib.sha256(canonical_bytes(serialized)).hexdigest()}),invoked_at=acquisition_completed_at,endpoint=f"derived://{provider}/{ACQUISITION_UNION_RULE_VERSION}",disposition=Disposition.SUCCESS,protocol_id=protocol_id,design=DesignAuthority.SUPPORTING,diagnostics=("typed authority bound to complete provider-page manifest","normalized union is derived, not provider-native raw"),provider_effective_at=acquisition_completed_at);values["provider_id"]=provider
    # The acquisition entry references an exact contributing provider page as
    # its immutable raw object; the normalized union exists only in the envelope.
    entry=archive._commit_locked(raw_body=page_values[0][2],normalized=normalized,entry_values=values)
    return {"manifest_entry_id":entry.manifest_entry_id,"acquisition_id":group_id,"page_count":len(page_values),"contract_count":len(contract_values)}


def verify_acquisition_bundle(archive:NamespaceArchive,value:Mapping[str,Any],*,include_union:bool=False)->Any:
    """Replay gate for page completeness, lineage, raw bytes and union identity."""
    if value.get("schema_version")!="1" or value.get("union_rule")!=ACQUISITION_UNION_RULE_VERSION:raise OperationsError("acquisition-incompatible","unknown acquisition envelope")
    provider=value.get("provider");pages=value.get("pages");group=value.get("acquisition_id")
    if provider not in {"kalshi","mlb-stats-api"} or not isinstance(pages,list) or not pages:raise OperationsError("acquisition-incomplete","acquisition page manifest is incomplete")
    def dt(raw):return datetime.fromisoformat(raw["datetime_utc"]) if isinstance(raw,dict) else datetime.fromisoformat(raw) if isinstance(raw,str) else raw
    command_start=dt(value.get("command_started_at"));acquisition_completed=dt(value.get("acquisition_completed_at"))
    if not isinstance(command_start,datetime) or not isinstance(acquisition_completed,datetime) or command_start.tzinfo is None or acquisition_completed<command_start:raise OperationsError("acquisition-chronology-conflict","acquisition chronology is invalid")
    original_start=datetime.fromisoformat(value.get("command_started_at_iso",""))
    if original_start.tzinfo is None or original_start.astimezone(timezone.utc)!=command_start.astimezone(timezone.utc):raise OperationsError("acquisition-chronology-conflict","command-start offset representation conflicts")
    entries={x["manifest_entry_id"]:x for x in authoritative_entries(archive)};raw_pages=[];prior_completion=command_start
    if len({(page.get("partition"),page.get("request_identity")) for page in pages if isinstance(page,dict)})!=len(pages):raise OperationsError("acquisition-page-conflict","duplicate page request identity")
    for position,page in enumerate(pages):
        if not isinstance(page,dict) or page.get("position")!=position or page.get("manifest_entry_id") not in entries:raise OperationsError("acquisition-page-conflict","page ordering or reference conflicts")
        if provider=="kalshi":
            identity=page.get("request_identity");family=value.get("family")
            if family=="refresh-retrospective-supporting":
                partition=page.get("partition")
                if partition not in {"historical","live"} or not isinstance(page.get("partition_position"),int):raise OperationsError("acquisition-page-conflict","retrospective catalog partition identity is invalid")
                expected=encoded_kalshi_retrospective_catalog_path(identity,historical=partition=="historical")
            else:expected=encoded_kalshi_catalog_path(identity)
            if page.get("endpoint")!=expected:raise OperationsError("acquisition-page-conflict","Kalshi page endpoint conflicts with canonical discovery authority")
        if provider=="mlb-stats-api":
            try:expected_endpoint=canonical_mlb_schedule_request(page.get("request_identity"))[1]
            except (TypeError,ValueError):raise OperationsError("acquisition-page-conflict","MLB page request identity is not a canonical date") from None
            if page.get("endpoint")!=expected_endpoint:raise OperationsError("acquisition-page-conflict","MLB page endpoint conflicts with canonical schedule authority")
        entry=entries[page["manifest_entry_id"]]
        if entry.get("provider_id")!=provider or entry.get("raw_object_sha256")!=page.get("raw_sha256") or entry.get("endpoint")!=page.get("endpoint"):raise OperationsError("acquisition-page-conflict","foreign or altered page authority")
        raw=archive.read_verified("raw",page["raw_sha256"])
        if hashlib.sha256(raw).hexdigest()!=page["raw_sha256"]:raise OperationsError("acquisition-page-conflict","page digest conflicts")
        page_normalized=json.loads(archive.read_verified("normalized",entry["normalized_object_id"]));
        if page_normalized.get("acquisition_id")!=group or page_normalized.get("request_identity")!=page.get("request_identity") or page_normalized.get("partition")!=page.get("partition") or page_normalized.get("partition_position")!=page.get("partition_position"):raise OperationsError("acquisition-page-conflict","cross-acquisition page substitution")
        started,completed=dt(page.get("started_at")),dt(page.get("completed_at"))
        if started.tzinfo is None or completed.tzinfo is None or started<prior_completion or completed<started:raise OperationsError("acquisition-chronology-conflict","page chronology is reversed or overlapping")
        manifest_at=datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])
        if manifest_at!=completed:raise OperationsError("acquisition-chronology-conflict","page manifest chronology conflicts")
        prior_completion=completed
        raw_pages.append(raw)
    referenced={page["manifest_entry_id"] for page in pages};group_pages=set()
    for entry_id,entry in entries.items():
        normalized_id=entry.get("normalized_object_id")
        if not normalized_id:continue
        candidate=json.loads(archive.read_verified("normalized",normalized_id))
        if candidate.get("record_kind")=="pr17c1-provider-page" and candidate.get("acquisition_id")==group:group_pages.add(entry_id)
    if group_pages!=referenced:raise OperationsError("acquisition-page-conflict","acquisition has missing or unreferenced pages")
    if acquisition_completed!=prior_completion:raise OperationsError("acquisition-chronology-conflict","acquisition completion conflicts with pages")
    if provider=="kalshi":
        typed_pages=[]
        for i,(page,raw) in enumerate(zip(pages,raw_pages)):
            payload=json.loads(raw);typed_pages.append(KalshiCatalogPage(i,page["request_identity"],payload["cursor"],raw,tuple(payload["markets"]),partition=page.get("partition"),partition_position=page.get("partition_position")))
        derived=merge_retrospective_catalog_pages(typed_pages) if value.get("family")=="refresh-retrospective-supporting" else merge_kalshi_catalog_pages(typed_pages)
    else:
        for page,raw in zip(pages,raw_pages):
            payload=json.loads(raw);reported={str(x.get("date")) for x in payload.get("dates",()) if isinstance(x,dict)}
            if reported and reported!={page["request_identity"]}:raise OperationsError("acquisition-page-conflict","MLB requested date conflicts with response")
        derived=merge_mlb_schedule_responses(raw_pages)
    if _canonical_json_digest(derived)!=value.get("normalized_union_sha256"):raise OperationsError("acquisition-union-conflict","normalized union is inconsistent with pages")
    contracts=value.get("contracts")
    if not isinstance(contracts,list):raise OperationsError("acquisition-incomplete","typed contracts are absent")
    return (derived,tuple(contracts)) if include_union else tuple(contracts)


def reconcile_outcomes_from_raw(*,archive:NamespaceArchive|None,mlb_raw:bytes,collected_at:datetime,mlb_pages:Iterable[Any]=(),prior_state:Any=None,derive_only:bool=False)->Mapping[str,Any]|tuple[Any,...]:
    from forecast_standalone_operations import DesignAuthority,Disposition,_entry_values,pr17_contract_bundle,replay_pr17_archive,request_identity
    from mlb_outcome_adapter import MLBOutcomeAdapter
    from mlb_stats_api import MLBStatsAPIAdapter,MLBStatsAPIResponse
    from outcome_contracts import OutcomeHistory
    try:payload=json.loads(mlb_raw,object_pairs_hook=lambda pairs:_unique_object(pairs,"MLB"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","MLB response is malformed") from exc
    response=MLBStatsAPIResponse("https://statsapi.mlb.com/api/v1/schedule",(),collected_at,200,"https://statsapi.mlb.com/api/v1/schedule",payload,mlb_raw);facts=MLBStatsAPIAdapter().parse_response(response);games=tuple(x.game for x in facts.games if x.game)
    results=MLBOutcomeAdapter().parse_response(response,canonical_games=games);state=prior_state or replay_pr17_archive(archive,analysis_boundary=collected_at);prior={x.canonical_event_id:x for x in state.bucket("outcome_histories")};changed=[]
    for result in results:
        if result.observation is None:raise OperationsError("provider-data-invalid","MLB outcome is invalid")
        observation=result.observation;history=prior.get(observation.canonical_event_id)
        if history is not None:
            latest=history.latest;semantic=(latest.provider_status,latest.scheduled_start,latest.away_score,latest.home_score,latest.winning_participant_id,latest.unresolved);current=(observation.provider_status,observation.scheduled_start,observation.away_score,observation.home_score,observation.winning_participant_id,observation.unresolved)
            if semantic==current:continue
            history=history.append(observation)
        else:history=OutcomeHistory(observation.canonical_event_id,"mlb-stats-api",(observation,))
        changed.append(history)
    if derive_only:return tuple(changed)
    raw_pages=tuple(mlb_pages) or (mlb_raw,);pages=tuple(_mlb_page_tuple(item,index) for index,item in enumerate(raw_pages))
    with archive.mutation_lock():acquisition=publish_verified_acquisition(archive=archive,provider="mlb-stats-api",union_raw=mlb_raw,pages=pages,contracts=changed,collected_at=collected_at,protocol_id=None,command="reconcile-outcomes")
    return {"changed":len(changed),"mlb_pages":len(pages),"outcome_manifest_id":acquisition["manifest_entry_id"],"disposition":"success" if changed else "unchanged"}


def resolve_activated_authority(archive:NamespaceArchive,at:datetime)->tuple[Any,Any]:
    """Resolve exactly one archived prospective Protocol and its approved boundary."""
    from forecast_standalone_research import StandaloneDesignTag
    if at.tzinfo is None or at.utcoffset() is None:raise OperationsError("trusted-clock-invalid","trusted time must be timezone-aware")
    if archive.config.mode is not OperatingMode.ACTIVATED or archive.config.activation_at!=APPROVED_ACTIVATION_AT:raise OperationsError("activation-authority-invalid","activated namespace configuration is absent")
    from forecast_standalone_operations import replay_pr17_archive
    state=replay_pr17_archive(archive,analysis_boundary=at)
    configured=set(archive.config.research_protocol_ids)
    protocols=tuple(x for x in state.bucket("protocols") if x.design_tag is StandaloneDesignTag.PROSPECTIVE and x.standalone_probability_source_protocol_id in configured)
    if len(protocols)!=1:raise OperationsError("activation-authority-invalid","exactly one configured prospective Protocol is required")
    boundaries=tuple(x for x in state.bucket("activation_boundaries") if x.standalone_research_activation_boundary_id==protocols[0].activation_boundary_id)
    if len(boundaries)!=1 or boundaries[0].activation_at.isoformat()!=APPROVED_ACTIVATION_AT.isoformat() or boundaries[0].approved_calendar_date!=APPROVED_EASTERN_DATE or boundaries[0].timezone_name!=APPROVED_TIMEZONE:raise OperationsError("activation-authority-invalid","archived activation boundary conflicts with approval")
    return protocols[0],boundaries[0]


def invoke_activated_prospective(*,archive:NamespaceArchive,transport_factory:Callable[[Any,Any],Any],clock:Callable[[],datetime],observation_adapter=None)->ProspectiveDiscoveryResult:
    now=clock()
    resolve_activated_authority(archive,now)
    if now<APPROVED_ACTIVATION_AT:
        return ProspectiveDiscoveryResult(archive.config.identity,archive.config.namespace,now,(),0,(),(),"pre-activation-no-call")
    # The downstream workflow owns immediately-pre-request authorization,
    # request-start, and completion reads.  Never freeze the precheck value.
    return discover_and_capture_prospective(archive=archive,transport_factory=transport_factory,clock=clock,observation_adapter=observation_adapter)


class CredentialProvider(Protocol):
    def credential(self)->bytes:...


@dataclass(frozen=True,slots=True)
class StaticCredentialProvider:
    value:bytes
    def credential(self)->bytes:
        if not self.value:raise OperationsError("credential-unavailable","credential is empty")
        return bytes(self.value)


@dataclass(frozen=True,slots=True)
class MacOSKeychainCredentialProvider:
    service:str;account:str;runner:Callable[...,subprocess.CompletedProcess[bytes]]=subprocess.run
    def credential(self)->bytes:
        if not self.service or not self.account:raise OperationsError("credential-unavailable","Keychain selector is incomplete")
        result=self.runner(("security","find-generic-password","-s",self.service,"-a",self.account,"-w"),capture_output=True,check=False)
        value=result.stdout.rstrip(b"\r\n") if result.returncode==0 else b""
        if not value:raise OperationsError("credential-unavailable","Keychain credential unavailable")
        if b"\x00" in value or len(value)>16384:raise OperationsError("credential-malformed","Keychain credential is malformed")
        return value


class RequestSigner(Protocol):
    def headers(self, method:str, path:str, timestamp_ms:int)->Mapping[str,str]: ...


@dataclass(frozen=True,slots=True)
class KalshiRequestSigner:
    """Official RSA-PSS/SHA-256 Kalshi authentication boundary."""
    key_id:str
    private_key_provider:CredentialProvider
    signer:Callable[[bytes,bytes],bytes]
    def headers(self,method:str,path:str,timestamp_ms:int)->Mapping[str,str]:
        if method!="GET" or not path.startswith("/") or timestamp_ms<0:raise OperationsError("signing-invalid","only canonical read-only requests may be signed")
        clean_path=path.split("?",1)[0]
        private_key=self.private_key_provider.credential()
        try: signature=self.signer(private_key,f"{timestamp_ms}{method}{clean_path}".encode())
        except Exception as exc:raise OperationsError("credential-incompatible","Kalshi signing failed") from exc
        finally: private_key=b""
        if not self.key_id or not signature:raise OperationsError("credential-incompatible","Kalshi signing authority is incomplete")
        return {"KALSHI-ACCESS-KEY":self.key_id,"KALSHI-ACCESS-TIMESTAMP":str(timestamp_ms),"KALSHI-ACCESS-SIGNATURE":base64.b64encode(signature).decode("ascii")}


def rsa_pss_sha256_sign(private_key_pem:bytes,message:bytes)->bytes:
    """Narrow provider signing primitive; imports crypto only when invoked."""
    try:
        from cryptography.hazmat.primitives import hashes,serialization
        from cryptography.hazmat.primitives.asymmetric import padding,rsa
        key=serialization.load_pem_private_key(private_key_pem,password=None)
        if not isinstance(key,rsa.RSAPrivateKey):raise ValueError("not RSA")
        return key.sign(message,padding.PSS(mgf=padding.MGF1(hashes.SHA256()),salt_length=padding.PSS.DIGEST_LENGTH),hashes.SHA256())
    except Exception as exc:raise OperationsError("credential-incompatible","Kalshi private signing key is incompatible") from exc


class ReadOnlyRequester(Protocol):
    def __call__(self,url:str,headers:Mapping[str,str],timeout:int,allow_redirects:bool)->tuple[int,bytes,Mapping[str,str]]:...


@dataclass(frozen=True,slots=True)
class BoundedLiveReadOnlyTransport:
    base_url:str;requester:ReadOnlyRequester;credential_provider:CredentialProvider|None=None;timeout_seconds:int=5;maximum_bytes:int=MAX_RESPONSE_BYTES;request_signer:RequestSigner|None=None;timestamp_ms:Callable[[],int]|None=None
    def __post_init__(self)->None:
        parsed=urlparse(self.base_url)
        if parsed.scheme!="https" or not parsed.netloc or self.timeout_seconds<1 or self.maximum_bytes<1:raise OperationsError("transport-configuration","live transport requires bounded TLS-only configuration")
    def get(self,path:str)->bytes:
        if not path.startswith("/") or ".." in path:raise OperationsError("transport-configuration","read-only path is invalid")
        headers={"Accept":"application/json"}
        if self.request_signer is not None:
            if self.timestamp_ms is None:raise OperationsError("trusted-clock-invalid","signing clock is absent")
            headers.update(self.request_signer.headers("GET",urlparse(self.base_url+path).path,self.timestamp_ms()))
        elif self.credential_provider is not None:
            secret=self.credential_provider.credential()
            # Generic credentials exist for fixture providers only; live Kalshi
            # must use the explicit RSA signer above.
            if "kalshi" in self.base_url.lower():raise OperationsError("credential-incompatible","Kalshi RSA signing authority is absent")
            headers["X-Fixture-Credential"]=secret.decode("ascii")
        status,body,response_headers=self.requester(self.base_url+path,headers,self.timeout_seconds,False)
        if 300<=status<400:raise OperationsError("transport-redirect","redirects are prohibited")
        if status!=200:raise OperationsError("transport-status","provider returned an unexpected status")
        if len(body)>self.maximum_bytes:raise OperationsError("transport-oversized","provider response exceeds the configured bound")
        try:value=json.loads(body)
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise OperationsError("malformed-response","provider JSON is malformed") from exc
        if not isinstance(value,(dict,list)):raise OperationsError("incomplete-response","provider response has no structured content")
        return body

    def request(self,method:str,url:str,*,params:Mapping[str,str],timeout:int,allow_redirects:bool):
        from forecast_standalone_operations import HTTPResponse
        if method!="GET" or allow_redirects or timeout>self.timeout_seconds:raise OperationsError("transport-configuration","request exceeds read-only bounds")
        market_id=params.get("market_id")
        if not isinstance(market_id,str) or not market_id or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for ch in market_id):raise OperationsError("transport-configuration","provider market identity is invalid")
        path=f"/markets/{market_id}/orderbook"
        raw=self.get(path)
        return HTTPResponse(200,raw,{})


@dataclass(frozen=True,slots=True)
class KalshiMarketCandidate:
    market_id:str;series_id:str;canonical_event_id:str;home_participant_id:str;away_participant_id:str
    scheduled_start:datetime;proposition_id:str;yes_participant_id:str;state:str;provider:str="kalshi"


def discover_unique_home_yes_market(*,candidates:Iterable[KalshiMarketCandidate],canonical_event_id:str,home_participant_id:str,away_participant_id:str,scheduled_start:datetime,proposition_id:str)->KalshiMarketCandidate:
    values=tuple(x for x in candidates if x.provider=="kalshi" and x.canonical_event_id==canonical_event_id and x.home_participant_id==home_participant_id and x.away_participant_id==away_participant_id and x.scheduled_start==scheduled_start and x.proposition_id==proposition_id and x.yes_participant_id==home_participant_id and x.state=="open")
    unique={x.market_id:x for x in values}
    if len(unique)!=1:raise OperationsError("market-discovery-ambiguous","exactly one open home-team YES market is required")
    return next(iter(unique.values()))


def adapt_kalshi_orderbook(*,payload:Mapping[str,Any],raw:bytes,started_at:datetime,completed_at:datetime,series:Any,schedule:Any):
    """Translate the documented ``orderbook_fp`` response without replacing raw bytes."""
    from event_contracts import Provenance
    from market_contracts import ComponentEvidence,MarketObservation,MarketSide,MarketStatus,OrderBookLevel,PriceEvidenceKind,QuoteState
    if completed_at<started_at:raise OperationsError("trusted-clock-reversed","order-book completion precedes request start")
    if series.provider!="kalshi" or series.provenance.provider!="kalshi":raise OperationsError("validation-failure","order book series authority is foreign or inconsistent")
    if series.provenance.canonical_event_id!=schedule.canonical_event_id or not series.proposition_id.startswith(f"winner:{schedule.canonical_event_id}:"):raise OperationsError("validation-failure","order book event or proposition authority conflicts")
    if set(payload)!={"orderbook_fp"} or not isinstance(payload["orderbook_fp"],dict) or set(payload["orderbook_fp"])!={"yes_dollars","no_dollars"}:raise OperationsError("incomplete-response","unsupported Kalshi orderbook response family")
    def levels(name):
        rows=payload["orderbook_fp"][name]
        if not isinstance(rows,list) or not rows:raise OperationsError("incomplete-response",f"{name} requires positive depth")
        seen=set();values=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=2 or not all(isinstance(x,str) for x in row):raise OperationsError("malformed-response",f"{name} level is malformed")
            if tuple(row) in seen:raise OperationsError("validation-failure",f"{name} contains duplicate levels")
            seen.add(tuple(row))
            if not re.fullmatch(r"(?:0|1)\.[0-9]{4}",row[0]) or not re.fullmatch(r"[0-9]+\.[0-9]{2}",row[1]):raise OperationsError("malformed-response",f"{name} fixed-point value is malformed")
            try:price,quantity=Decimal(row[0]),Decimal(row[1])
            except InvalidOperation as exc:raise OperationsError("malformed-response",f"{name} fixed-point value is malformed") from exc
            if not Decimal(0)<price<Decimal(1) or quantity<=0:raise OperationsError("validation-failure",f"{name} price or quantity is invalid")
            values.append((price,quantity))
        return tuple(values)
    yes,no=levels("yes_dollars"),levels("no_dollars");endpoint=f"/markets/{series.provider_market_id}/orderbook";book=[]
    # The provider publishes resting bids, not asks.  The executable offer on
    # either canonical side is the complement of the opposing provider bid.
    for index,(price,quantity) in enumerate(no,1):book.append(OrderBookLevel(MarketSide.YES,Decimal(1)-price,quantity,index,PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID,MarketSide.NO,price,"canonical_yes_offer = 1 - provider_no_bid",endpoint,completed_at))
    for index,(price,quantity) in enumerate(yes,1):book.append(OrderBookLevel(MarketSide.NO,Decimal(1)-price,quantity,index,PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID,MarketSide.YES,price,"canonical_no_offer = 1 - provider_yes_bid",endpoint,completed_at))
    yes_ask=min(x.acquisition_price for x in book if x.acquisition_side is MarketSide.YES)
    no_ask=min(x.acquisition_price for x in book if x.acquisition_side is MarketSide.NO)
    yes_bid=Decimal(1)-no_ask
    if yes_bid>yes_ask:raise OperationsError("validation-failure","canonical order book is crossed")
    digest=hashlib.sha256(raw).hexdigest();event_id=schedule.canonical_event_id
    provenance=Provenance("kalshi",series.provider_market_id,event_id,started_at,transformations=("documented-orderbook-fp-bids","canonical-offers-from-opposite-bid-complements",),raw_evidence_ref=f"raw:{digest}",source_url=endpoint,collector_version="pr17c1-kalshi-orderbook-2")
    component=ComponentEvidence("orderbook",series.provider_market_id,endpoint,completed_at,digest,digest)
    identity=hashlib.sha256(canonical_bytes({"series":series.series_id,"event":event_id,"started":started_at,"completed":completed_at,"raw":digest})).hexdigest()
    return MarketObservation(f"market-observation:{identity}",series.series_id,series.provider_market_id,event_id,series.proposition_id,f"capture:{identity}",started_at,MarketStatus.OPEN,QuoteState(yes_bid=yes_bid,yes_ask=yes_ask,no_bid=Decimal(1)-yes_ask,no_ask=no_ask,price_scale="dollars",source_representation="orderbook_fp resting bids normalized to canonical offers"),tuple(book),(component,),provenance)


@dataclass(frozen=True,slots=True)
class RefreshResult:
    changed:bool;identity:str;diagnostic:str


def classify_refresh(previous:Any,current:Any)->RefreshResult:
    before=canonical_bytes(previous);after=canonical_bytes(current);digest=hashlib.sha256(after).hexdigest()
    return RefreshResult(before!=after,f"refresh:{digest}","authority-changed" if before!=after else "unchanged-no-scientific-write")


@dataclass(frozen=True,slots=True)
class HealthReport:
    schema_version:str;configuration_id:str;namespace:str;trusted_at:datetime;timezone_name:str;activation_status:str
    scheduler_age_seconds:int|None;last_collector_at:datetime|None;due_opportunities:int|None;provider_calls:int|None;typed_dispositions:int|None
    archive_healthy:bool;missing:int;corrupt:int;malformed:int;incompatible:int;partial:int;orphaned:int;index_state:str
    secondary_lag:int;secondary_age_seconds:int|None;free_disk_bytes:int;recent_failures:tuple[str,...];ready:bool;authority:str="non-authoritative-operations-health"
    supporting_age_seconds:int|None=None;outcome_age_seconds:int|None=None;inspection_age_seconds:int|None=None;index_rebuild_age_seconds:int|None=None
    health_generated_at:datetime|None=None;command_dispositions:tuple[tuple[str,str],...]=()
    def to_json(self)->str:return canonical_bytes(self).decode()


@dataclass(frozen=True,slots=True)
class OperationalHeartbeat:
    schema_version:str;command:str;started_at:datetime;completed_at:datetime;disposition:str
    provider_calls:int|None;typed_dispositions:int|None;due_opportunities:int|None;failure_code:str|None
    def __post_init__(self)->None:
        if self.schema_version!=HEARTBEAT_SCHEMA_VERSION or self.completed_at<self.started_at:raise OperationsError("heartbeat-invalid","operational chronology is invalid")
        if self.failure_code and any(x in self.failure_code.lower() for x in ("secret","token","password","signature","authorization")):raise OperationsError("secret-material","unsafe heartbeat failure")
    def to_json(self)->str:return canonical_bytes(self).decode()


class OperationalState:
    """Append-only, explicitly non-scientific invocation state."""
    def __init__(self,root):self.root=root
    def append(self,item:OperationalHeartbeat)->None:
        self.root.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(item.to_json().encode()).hexdigest();path=self.root/f"{item.completed_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}-{digest}.json"
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as stream:stream.write(item.to_json()+"\n")
        except FileExistsError:pass
    def entries(self)->tuple[OperationalHeartbeat,...]:
        values=[]
        for path in sorted(self.root.glob("*.json")) if self.root.exists() else ():
            try:
                content=path.read_text();expected=path.stem.rsplit("-",1)[-1]
                raw=json.loads(content)
                for key in ("started_at","completed_at"):raw[key]=datetime.fromisoformat(raw[key]["datetime_utc"])
                item=OperationalHeartbeat(**raw)
                if hashlib.sha256(item.to_json().encode()).hexdigest()!=expected:raise OperationsError("heartbeat-corrupt","heartbeat digest conflicts")
            except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:raise OperationsError("heartbeat-corrupt","heartbeat file is malformed") from exc
            values.append(item)
        identities=set()
        for item in values:
            identity=(item.command,item.started_at,item.completed_at)
            if identity in identities:raise OperationsError("heartbeat-conflict","duplicate command chronology")
            identities.add(identity)
        return tuple(values)


JOB_SCHEDULES={"prospective":{"StartInterval":30},"supporting":{"StartCalendarInterval":{"Minute":7}},"outcomes":{"StartCalendarInterval":{"Hour":4,"Minute":17}},"maintenance":{"StartCalendarInterval":{"Hour":4,"Minute":29}},"secondary":{"StartCalendarInterval":{"Hour":4,"Minute":41}},"health":{"StartCalendarInterval":{"Hour":7,"Minute":5}}}


def render_launchd_jobs(*,repository_root,python_executable,config_path,output_root)->tuple[str,...]:
    """Render six inert, absolute-path jobs; never installs or loads them."""
    original=tuple(map(lambda p:p if hasattr(p,"is_absolute") else __import__('pathlib').Path(p),(repository_root,python_executable,config_path,output_root)))
    if not all(p.is_absolute() for p in original):raise OperationsError("deployment-path-invalid","installation paths must be absolute")
    repository_root,python_executable,config_path,output_root=original
    repository_root,config_path,output_root=repository_root.resolve(),config_path.resolve(),output_root.resolve()
    if not repository_root.is_dir() or not python_executable.is_file() or not os.access(python_executable,os.X_OK) or not config_path.is_file():raise OperationsError("deployment-path-invalid","installation paths must be absolute, existing, and executable where required")
    config=DeploymentConfig.from_json(config_path)
    if config.mode is not OperatingMode.ACTIVATED:raise OperationsError("deployment-mode-invalid","rendering requires activated configuration")
    state_roots=tuple(p.resolve() for p in (config.primary_root,config.secondary_root,config.log_root))
    if any(output_root==p or output_root in p.parents or p in output_root.parents for p in state_roots):raise OperationsError("deployment-path-invalid","render output overlaps deployment state")
    output_root.mkdir(parents=True,exist_ok=True);created=[]
    command_by_job={"prospective":"capture-prospective","supporting":"refresh-supporting","outcomes":"reconcile-outcomes","maintenance":"maintain","secondary":"sync-secondary","health":"health-report"}
    cli=repository_root/"operate_forecast_standalone_activation.py"
    if not cli.is_file():raise OperationsError("deployment-path-invalid","typed CLI is absent")
    for name,schedule in JOB_SCHEDULES.items():
        label=f"com.popsedge.pr17c1.{name}"
        arguments=[str(python_executable),str(cli),"--config",str(config_path)]
        if config.fixture_response_path is not None:arguments.extend(("--fixture",str(config.fixture_response_path.resolve())))
        trusted=dict(config.schedule_parameters).get("fixture_trusted_at")
        if trusted is not None:
            if config.fixture_response_path is None:raise OperationsError("deployment-path-invalid","trusted fixture time requires fixture composition")
            datetime.fromisoformat(trusted);arguments.extend(("--trusted-at",trusted))
        arguments.append(command_by_job[name]);payload={"Label":label,"ProgramArguments":arguments,**schedule}
        path=output_root/f"{label}.plist";path.write_bytes(plistlib.dumps(payload,sort_keys=True));created.append(str(path))
    return tuple(created)


def build_health_report(*,archive:NamespaceArchive,trusted_at:datetime,scheduler_at:datetime|None,last_collector_at:datetime|None,due_opportunities:int|None,provider_calls:int|None,typed_dispositions:int|None,secondary_synced_at:datetime|None,free_disk_bytes:int,recent_failures:Iterable[str])->HealthReport:
    if trusted_at.tzinfo is None or trusted_at.utcoffset() is None:raise OperationsError("trusted-clock-invalid","health clock must be aware")
    failures=tuple(sorted(set(str(x) for x in recent_failures)))
    if any(any(term in x.lower() for term in ("authorization","password","secret","token","api_key","private_key")) for x in failures):raise OperationsError("secret-material","health failure detail is unsafe")
    integrity=reconcile_archive(archive);idx,_=index_health(archive);secondary=secondary_status(archive)
    age=lambda value:None if value is None else max(0,int((trusted_at-value).total_seconds()))
    if free_disk_bytes < 0: raise OperationsError("storage-invalid", "free disk value must be non-negative")
    scheduler_age=age(scheduler_at);secondary_age=age(secondary_synced_at)
    ready=bool(integrity.healthy and idx=="healthy" and scheduler_age is not None and scheduler_age<=120 and last_collector_at is not None and secondary_age is not None and free_disk_bytes>100_000_000 and not failures)
    return HealthReport(ACTIVATION_SCHEMA_VERSION,archive.config.identity,archive.config.namespace,trusted_at,APPROVED_TIMEZONE,"active" if trusted_at>=APPROVED_ACTIVATION_AT else "staged",scheduler_age,last_collector_at,due_opportunities,provider_calls,typed_dispositions,integrity.healthy,len(integrity.referenced_missing),len(integrity.referenced_corrupt),len(integrity.malformed),len(integrity.incompatible),len(integrity.partial),len(integrity.orphaned),idx,secondary.get("lag",0),secondary_age,free_disk_bytes,failures,ready)


def health_from_operational_state(*,archive:NamespaceArchive,state:OperationalState,trusted_at:datetime,free_disk:Callable[[Any],int])->HealthReport:
    entries=state.entries();latest={}
    for item in entries:
        if item.started_at>item.completed_at or item.completed_at>trusted_at:raise OperationsError("trusted-clock-invalid","heartbeat chronology is future-dated or reversed")
        if item.command not in latest or latest[item.command].completed_at<item.completed_at:latest[item.command]=item
    collector=latest.get("capture-prospective");secondary=latest.get("sync-secondary")
    age=lambda command:None if command not in latest else int((trusted_at-latest[command].completed_at).total_seconds())
    failures=tuple(sorted(f"{x.command}:{x.failure_code or x.disposition}" for x in entries if (trusted_at-x.completed_at).total_seconds()<=90_000 and (x.failure_code or x.disposition not in ("success","completed","unchanged","no-due-work","pre-activation-no-call"))))
    base=build_health_report(archive=archive,trusted_at=trusted_at,scheduler_at=collector.completed_at if collector else None,last_collector_at=collector.completed_at if collector else None,due_opportunities=collector.due_opportunities if collector else None,provider_calls=collector.provider_calls if collector else None,typed_dispositions=collector.typed_dispositions if collector else None,secondary_synced_at=secondary.completed_at if secondary and secondary.disposition=="success" else None,free_disk_bytes=free_disk(archive.root),recent_failures=failures)
    supporting,outcome=age("refresh-supporting"),age("reconcile-outcomes")
    inspection=age("inspect") if age("inspect") is not None else age("maintain");index_age=age("rebuild-index") if age("rebuild-index") is not None else age("maintain")
    required=((base.scheduler_age_seconds,90),(supporting,3900),(outcome,90000),(inspection,90000),(index_age,90000),(base.secondary_age_seconds,90000))
    dispositions=tuple(sorted((name,item.disposition) for name,item in latest.items()))
    ready=base.ready and all(value is not None and value<=limit for value,limit in required)
    return __import__('dataclasses').replace(base,ready=ready,supporting_age_seconds=supporting,outcome_age_seconds=outcome,inspection_age_seconds=inspection,index_rebuild_age_seconds=index_age,health_generated_at=trusted_at,command_dispositions=dispositions)
