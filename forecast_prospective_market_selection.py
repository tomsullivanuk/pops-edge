"""Current live-catalog selection over a verified prospective source boundary.

Historical series remain Evidence. Their presence alone is never permission to
query a market for a later schedule occurrence.
"""
import json
from datetime import datetime

from forecast_standalone_operations import OperationsError


def load_prospective_catalog(boundary):
    """Read only the latest completed live catalog and its schedule dependency.

The caller has loaded/verified the checkpoint. Re-verify the selected provider
pages before interpreting their current status; never select individual pages,
retrospective catalogs, or fall back to an older nonempty catalog.
"""
    from forecast_standalone_activation import verify_acquisition_bundle
    from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse

    bundles = []
    for entry in boundary.entries():
        if entry.get("command") != "refresh-supporting" or entry.get("provider_id") != "kalshi":
            continue
        identity = entry.get("normalized_object_id")
        if not identity:
            continue
        value = boundary.read_normalized_metadata(identity)
        if value.get("record_kind") == "pr17c1-acquisition-bundle" and value.get("family") == "refresh-supporting":
            completed = datetime.fromisoformat(value["acquisition_completed_at"]["datetime_utc"])
            bundles.append((completed, identity, value))
    if not bundles:
        return (), (), "market-catalog-unavailable"
    latest_at = max(item[0] for item in bundles)
    latest = [item for item in bundles if item[0] == latest_at]
    if len(latest) != 1:
        return (), (), "market-catalog-ambiguous"
    _, identity, metadata = latest[0]
    value = boundary.read_json_verified("normalized", identity)
    catalog_raw, _ = verify_acquisition_bundle(boundary, value, include_union=True)
    dependencies = metadata.get("dependencies", ())
    if len(dependencies) != 1:
        raise OperationsError("acquisition-dependency-conflict", "live catalog requires one schedule dependency")
    matches = []
    for entry in boundary.entries():
        identity = entry.get("normalized_object_id")
        if not identity:
            continue
        candidate = boundary.read_normalized_metadata(identity)
        if (candidate.get("record_kind") == "pr17c1-acquisition-bundle" and
                candidate.get("provider") == "mlb-stats-api" and
                candidate.get("acquisition_id") == dependencies[0]):
            matches.append(identity)
    if len(matches) != 1:
        raise OperationsError("acquisition-dependency-conflict", "live catalog schedule dependency is ambiguous or absent")
    mlb = boundary.read_json_verified("normalized", matches[0])
    raw, _ = verify_acquisition_bundle(boundary, mlb, include_union=True)
    at = datetime.fromisoformat(mlb["command_started_at_iso"])
    endpoint = "https://statsapi.mlb.com/api/v1/schedule"
    response = MLBStatsAPIResponse(endpoint, (), at, 200, endpoint, json.loads(raw), raw)
    facts = MLBStatsAPIAdapter().parse_response(response)
    # Repeated schedule observations refer to one game identity. Participant
    # identity must agree; current occurrence comes from the capture's schedule.
    games = {}
    for fact in facts.games:
        if fact.game is None:
            continue
        game = fact.game
        key = game.event.canonical_event_id
        prior = games.get(key)
        if prior and (prior.home_team.canonical_team_id, prior.away_team.canonical_team_id) != (game.home_team.canonical_team_id, game.away_team.canonical_team_id):
            raise OperationsError("market-catalog-conflict", "schedule participants conflict")
        games[key] = game
    return tuple(json.loads(catalog_raw)["markets"]), tuple(games.values()), "latest-completed-live-catalog"


def prepare_prospective_markets(catalog, series_values, schedule):
    """Finish parsing, identity matching and series lookup before request time."""
    from kalshi_mlb_adapter import reconcile_market, _dt

    markets, games, diagnostic = catalog
    if diagnostic != "latest-completed-live-catalog":
        return (), diagnostic
    candidates = {}
    proposition = f"winner:{schedule.canonical_event_id}:{schedule.home_participant_id}"
    for market in markets:
        matched, _, _ = reconcile_market(market, games, (schedule,))
        if matched is None:
            continue
        game, yes_participant = matched
        if (game.event.canonical_event_id != schedule.canonical_event_id or
                yes_participant != schedule.home_participant_id or
                game.home_team.canonical_team_id != schedule.home_participant_id or
                game.away_team.canonical_team_id != schedule.away_participant_id):
            continue
        try:
            opened, closed = _dt(market.get("open_time")), _dt(market.get("close_time"))
            trading = (opened is not None and closed is not None and
                       opened.utcoffset() is not None and closed.utcoffset() is not None and opened < closed)
        except (TypeError, ValueError):
            trading = False
        if str(market.get("status", "")).lower() not in {"open", "active"} or not trading:
            continue
        market_id = market.get("ticker")
        if market_id:
            series = tuple(item for item in series_values if
                           item.provider == "kalshi" and item.provider_market_id == market_id and
                           item.proposition_id == proposition and
                           item.provenance.canonical_event_id == schedule.canonical_event_id and
                           item.yes_semantic.participant_id == schedule.home_participant_id and
                           item.no_semantic.participant_id == schedule.away_participant_id)
            candidates[market_id] = (opened, closed, series)
    return tuple(candidates.values()), diagnostic


def select_prepared_market(prepared, at):
    """Only interval comparisons over identity-qualified candidates remain."""
    candidates, diagnostic = prepared
    if diagnostic != "latest-completed-live-catalog":
        return None, diagnostic
    eligible = tuple(series for opened, closed, series in candidates if opened <= at < closed)
    if len(eligible) != 1:
        return None, "market-unavailable" if not eligible else "ambiguous-market"
    series = eligible[0]
    if len(series) != 1:
        return None, "market-series-unavailable" if not series else "ambiguous-market"
    return series[0], "current-schedule-open-market"


def select_prospective_market(catalog, series_values, schedule, at):
    """Read-only convenience selector; capture prepares before its final clock."""
    return select_prepared_market(prepare_prospective_markets(catalog, series_values, schedule), at)
