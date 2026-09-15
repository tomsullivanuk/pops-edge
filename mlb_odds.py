"""Versioned operational MLB odds interpretation; no acquisition or research writes."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from kalshi_mlb_adapter import _canon
from mlb_stats_api import MLBStatsAPIAdapter, MLBStatsAPIResponse

VERSION = "mlb-operational-odds-1"
EASTERN = ZoneInfo("America/New_York")
MAX_AGE = 300
RULE = re.compile(
    r"If (?P<winner>[A-Za-z .'-]+) wins the (?P<away>[A-Za-z .'-]+) vs "
    r"(?P<home>[A-Za-z .'-]+?)(?: \(Game (?P<number>[12])\))? professional baseball game "
    r"originally scheduled for (?P<day>[A-Z][a-z]{2} \d{1,2}, \d{4}) at "
    r"(?P<clock>\d{1,2}:\d{2} [AP]M) (?P<zone>EDT|EST), then the market resolves to Yes\."
)
DISCLAIMER = ("Kalshi is not affiliated, associated, authorized, endorsed by, or in any way "
              "officially connected with the Governing League. All trademarks, logos, and brand "
              "names are the property of their respective owners.")
SETTLEMENT = ("The following market refers to the {match} professional baseball game originally "
              "scheduled for {day} at {clock} {zone}. If this game is postponed or delayed, the "
              "market will remain open and close after the rescheduled game has finished (within "
              "two days). If the game is cancelled or rescheduled to over two days away, the market "
              "will resolve to a fair price in accordance with the rules.")


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def aware(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp has no timezone")
    return result.astimezone(timezone.utc)


def day_value(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Select one calendar date")
    return date.fromisoformat(value)


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate source field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite source value")))


def schedule_games(raw, selected_day, received_at):
    """Keep the complete official date universe, including unpriceable records."""
    day_value(selected_day)
    payload = decode(raw)
    if not isinstance(payload, dict) or type(payload.get("totalGames")) is not int:
        raise ValueError("Official schedule completeness is unavailable")
    dates = payload.get("dates")
    if not isinstance(dates, list):
        raise ValueError("Official schedule date list is missing")
    records = []
    for block in dates:
        if not isinstance(block, dict) or block.get("date") != selected_day or not isinstance(block.get("games"), list):
            raise ValueError("Official schedule returned an incompatible date")
        if "totalGames" in block and (type(block["totalGames"]) is not int or block["totalGames"] != len(block["games"])):
            raise ValueError("Official date count is incomplete")
        records.extend(block["games"])
    if len(records) != payload["totalGames"] or not 0 <= len(records) <= 50:
        raise ValueError("Official schedule count is incomplete or exceeds the daily bound")
    if any(not isinstance(r, dict) for r in records):
        raise ValueError("Malformed official game record")
    ids = [r.get("gamePk") for r in records]
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Official game identities are missing or conflicting")
    response = MLBStatsAPIResponse("/schedule", (("date", selected_day),), aware(received_at),
                                  200, "https://statsapi.mlb.com/api/v1/schedule", payload, raw)
    adapted = MLBStatsAPIAdapter().parse_response(response)
    if len(adapted.games) != len(records):
        raise ValueError("Official schedule could not retain every game")
    result = []
    by_source = {item.source_record_id: item for item in adapted.games}
    for record in records:
        item = by_source[f"mlb-game:{record['gamePk']}"]
        def team(side):
            value = record.get("teams", {}).get(side, {}).get("team", {})
            return dict(id=value.get("id"), name=value.get("name") or "Unknown team")
        row = dict(id=f"mlb:{record['gamePk']}", game_pk=record["gamePk"],
                   away=team("away"), home=team("home"), start=record.get("gameDate"),
                   number=record.get("gameNumber") if record.get("doubleHeader") not in (None, "N", "n", "") else None,
                   official_status=(record.get("status") or {}).get("detailedState", "Unknown"),
                   reasons=[], away_quote=None, home_quote=None,
                   away_reason="No verified team YES market", home_reason="No verified team YES market")
        if not item.game or not item.schedule_observation or not item.status_observation:
            row["reasons"].append("Official identity or start time is unavailable")
        else:
            row["id"] = item.game.event.canonical_event_id
            row["start"] = item.schedule_observation.scheduled_start.isoformat()
            if item.status_observation.status.value != "scheduled":
                row["reasons"].append(row["official_status"] + ": pregame prices unavailable")
        if record.get("gameType") != "R" or str(record.get("season")) != selected_day[:4]:
            row["reasons"].append("Outside supported regular-season scope")
        if any(record.get(key) for key in ("resumeDate", "resumeGameDate", "resumedFrom", "resumedFromDate", "rescheduledFrom", "rescheduledFromDate", "rescheduleDate", "rescheduleGameDate")):
            row["reasons"].append("Changed schedule requires a separately supported market")
        if record.get("status", {}).get("startTimeTBD") or record.get("startTimeTBD"):
            row["reasons"].append("Start time is TBD")
        if record.get("doubleHeader") not in (None, "N", "n", "") and (type(row["number"]) is not int or row["number"] not in (1, 2)):
            row["reasons"].append("Doubleheader game number is unresolved")
        if row["away"]["id"] == row["home"]["id"]:
            row["reasons"].append("Conflicting team identities")
        result.append(row)
    return result


def market_identity(market):
    """Admit only the full observed two-day MLB rule family, never a prefix."""
    if not isinstance(market, dict) or market.get("market_type") != "binary":
        raise ValueError("Not an explicitly binary market")
    ticker = market.get("ticker", "")
    if not isinstance(ticker, str) or not re.fullmatch(r"KXMLBGAME-[A-Z0-9-]{1,100}", ticker):
        raise ValueError("Unsupported market identity")
    if market.get("status") not in ("open", "active"):
        raise ValueError("Market is not open")
    try:
        notional = Decimal(market.get("notional_value_dollars", ""))
    except (InvalidOperation, TypeError):
        raise ValueError("Winning payout is unavailable") from None
    if not notional.is_finite() or notional != 1:
        raise ValueError("Winning payout is not one dollar")
    def text(key):
        value = market.get(key)
        if not isinstance(value, str):
            raise ValueError("Complete settlement rules are required")
        return " ".join(value.split())
    match = RULE.fullmatch(text("rules_primary"))
    if not match:
        raise ValueError("Unsupported complete primary settlement rule")
    fields = match.groupdict()
    matchup = fields["away"] + " vs " + fields["home"]
    if fields["number"]:
        matchup += " (Game " + fields["number"] + ")"
    expected = SETTLEMENT.format(match=matchup, **fields)
    if text("rules_secondary") not in (expected, expected + " " + DISCLAIMER):
        raise ValueError("Unsupported complete secondary settlement rule")
    instant = datetime.strptime(fields["day"] + " " + fields["clock"], "%b %d, %Y %I:%M %p").replace(tzinfo=EASTERN)
    if instant.tzname() != fields["zone"]:
        raise ValueError("Settlement timezone conflicts with the calendar")
    home, away, winner = (_canon(fields[k]) for k in ("home", "away", "winner"))
    if home == away or winner not in (home, away):
        raise ValueError("Settlement participants conflict")
    other = away if winner == home else home
    if _canon(market.get("yes_sub_title", "")) != winner or _canon(market.get("no_sub_title", "")) not in (winner, other):
        raise ValueError("Structured contract labels conflict with settlement")
    return dict(ticker=ticker, home=home, away=away, winner=winner,
                start=instant.astimezone(timezone.utc).isoformat(), number=int(fields["number"]) if fields["number"] else None)


def map_markets(games, markets):
    candidates = {(g["id"], side): [] for g in games for side in ("away", "home")}
    diagnostics = []
    for market in markets:
        try:
            identity = market_identity(market)
            matches = [g for g in games if not g["reasons"] and
                       _canon(g["home"]["name"]) == identity["home"] and
                       _canon(g["away"]["name"]) == identity["away"] and
                       aware(g["start"]) == aware(identity["start"]) and
                       (identity["number"] is None or g["number"] == identity["number"])]
            if len(matches) != 1:
                raise ValueError("Market does not identify one supported scheduled game")
            game = matches[0]
            side = "home" if identity["winner"] == identity["home"] else "away"
            candidates[game["id"], side].append(market)
        except (ValueError, TypeError, KeyError) as exc:
            diagnostics.append(dict(ticker=str(market.get("ticker", "Unknown")), reason=str(exc)))
    return candidates, diagnostics


def best_yes_offer(raw):
    payload = decode(raw)
    if not isinstance(payload, dict) or set(payload) != {"orderbook_fp"}:
        raise ValueError("Unsupported order-book response family")
    book = payload["orderbook_fp"]
    if not isinstance(book, dict) or set(book) != {"yes_dollars", "no_dollars"}:
        raise ValueError("Incomplete order-book shape")
    levels = {}
    for name in ("yes_dollars", "no_dollars"):
        rows = book[name]
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError("Invalid order-book levels")
        parsed, seen = [], set()
        for row in rows:
            if not isinstance(row, list) or len(row) != 2 or not all(isinstance(v, str) for v in row):
                raise ValueError("Invalid fixed-point level")
            if not re.fullmatch(r"(?:0|1)\.[0-9]{4}", row[0]) or not re.fullmatch(r"[0-9]{1,12}\.[0-9]{2}", row[1]):
                raise ValueError("Invalid fixed-point value")
            price, quantity = map(Decimal, row)
            if not 0 < price < 1 or quantity <= 0 or tuple(row) in seen:
                raise ValueError("Invalid or duplicate order-book level")
            seen.add(tuple(row)); parsed.append((price, quantity))
        levels[name] = parsed
    no = levels["no_dollars"]
    if not no:
        raise ValueError("No YES purchase offer")
    bid = max(p for p, _ in no)
    price = Decimal(1) - bid
    if levels["yes_dollars"] and max(p for p, _ in levels["yes_dollars"]) > price:
        raise ValueError("Crossed order book")
    quantity = sum((q for p, q in no if p == bid), Decimal(0))
    if quantity < 1:
        raise ValueError("Less than one contract available at the best ask")
    return dict(price=str(price), cents=str(price * 100), quantity=str(quantity),
                source_no_bid=str(bid), transformation="YES ask = 1 − this contract's best NO bid")


def quote_state(row, quote, now, *, clock_ok=True):
    if not quote:
        return "unavailable"
    if not clock_ok:
        return "clock-uncertain"
    try:
        at = aware(now)
        times = [aware(quote[k]) for k in ("started_at", "completed_at", "schedule_started_at", "catalog_started_at")]
        if any(t > at for t in times) or times[1] < times[0]:
            return "clock-uncertain"
        if at >= aware(row["start"]):
            return "pregame-ended"
        if any((at - t).total_seconds() >= MAX_AGE for t in times):
            return "stale"
        if row["reasons"]:
            return "unavailable"
        return "current"
    except (ValueError, KeyError, TypeError):
        return "clock-uncertain"
