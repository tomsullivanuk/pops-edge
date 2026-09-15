"""Explicit bounded local odds acquisition and immutable saved operational views."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

import requests

import mlb_odds as odds

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 50
MAX_SECONDS = 240
HOSTS = {"mlb": "https://statsapi.mlb.com/api/v1", "kalshi": "https://external-api.kalshi.com/trade-api/v2"}


def utc():
    return datetime.now(timezone.utc).isoformat()


def public_get(provider, route, params):
    """Fixed read-only provider hosts; no redirects or retries or credentials."""
    with requests.get(HOSTS[provider] + route, params=params, timeout=(5, 10),
                      allow_redirects=False, stream=True) as response:
        chunks, size = [], 0
        deadline = time.monotonic() + 10
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_BYTES or time.monotonic() > deadline:
                raise ValueError("Provider response exceeded the bounded request")
            chunks.append(chunk)
        return response.status_code, b"".join(chunks)


class OddsStore:
    """Construction and reading never create a directory or trigger a provider call."""
    def __init__(self, root, *, fetch=public_get, clock=utc, monotonic=time.monotonic):
        self.root = Path(root).absolute()
        self.fetch, self.clock, self.monotonic = fetch, clock, monotonic
        self.lock = threading.Lock()
        self.thread = None
        self.active_day = None
        self.memory_error = None
        self.start_wall, self.start_mono = odds.aware(clock()), monotonic()
        self.clock_bad = False

    def clock_ok(self):
        elapsed = (odds.aware(self.clock()) - self.start_wall).total_seconds()
        monotonic_elapsed = self.monotonic() - self.start_mono
        if elapsed < 0 or abs(elapsed - monotonic_elapsed) > 5:
            self.clock_bad = True
        return not self.clock_bad

    def path(self, *parts):
        path = self.root.joinpath(*parts)
        # Refuse aliases in the dedicated output path, including its ancestors.
        # resolve() is only used for containment, never to follow a selected file.
        for parent in (path, *path.parents):
            if parent.is_symlink():
                raise ValueError("Odds storage cannot contain symbolic links")
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid odds path")
        return path

    def _write(self, path, raw, *, atomic=False):
        self.path(*path.relative_to(self.root).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial") if atomic else path
        try:
            with temporary.open("xb") as output:
                output.write(raw); output.flush(); os.fsync(output.fileno())
            if atomic:
                os.replace(temporary, path)
        finally:
            if atomic and temporary.exists():
                temporary.unlink()

    def _state(self, day):
        path = self.path("days", day + ".json")
        if not path.exists():
            return dict(schema=odds.VERSION, day=day, selected=None, attempt=None)
        state = odds.decode(path.read_bytes())
        if not isinstance(state, dict) or state.get("schema") != odds.VERSION or state.get("day") != day:
            raise ValueError("Saved day state is incompatible")
        if set(state) != {"schema", "day", "selected", "attempt"}:
            raise ValueError("Saved day state is incomplete")
        if state["selected"] is not None and not isinstance(state["selected"], dict):
            raise ValueError("Saved day selection is invalid")
        attempt = state["attempt"]
        if attempt is not None and (not isinstance(attempt, dict) or
                attempt.get("state") not in ("running", "complete", "partial", "failed") or
                not isinstance(attempt.get("id"), str)):
            raise ValueError("Saved attempt status is invalid")
        return state

    def _save_state(self, state):
        self._write(self.path("days", state["day"] + ".json"), odds.encode(state), atomic=True)

    @contextmanager
    def writer(self):
        # No mutation of a source checkout, including a nested directory in one.
        root = self.path()
        if any((p / ".git").exists() for p in (root, *root.parents)):
            raise ValueError("Odds outputs must be outside source checkouts")
        root.mkdir(parents=True, exist_ok=True)
        with self.path("writer.lock").open("a+b") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another MLB odds refresh is running") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _validate_day(self, day, *, refresh=False, mode="odds"):
        value = odds.day_value(day)
        today = odds.aware(self.clock()).astimezone(odds.CENTRAL).date()
        if mode not in ("odds", "results"):
            raise ValueError("Unknown MLB action")
        if refresh:
            if mode == "results":
                if value > today or value.year != today.year or not self._state(day)["selected"]:
                    raise ValueError("Refresh requires a saved date in the current season for past game results")
            elif value < today or value.year != today.year:
                raise ValueError("Odds refresh requires today or a future date in the current season; use the sheet refresh for saved past dates")

    def _refresh_mode(self, day):
        selected = odds.day_value(day)
        today = odds.aware(self.clock()).astimezone(odds.CENTRAL).date()
        return "results" if selected < today else "odds"

    def start(self, day):
        mode = self._refresh_mode(day)
        self._validate_day(day, refresh=True, mode=mode)
        if not self.clock_ok():
            raise ValueError("Local clock changed. Check it and restart the local application before refreshing")
        if not self.lock.acquire(False):
            raise ValueError("An MLB odds refresh is already running")
        try:
            self.active_day = day
            self.memory_error = None
            self.thread = threading.Thread(target=self._background, args=(day, mode), daemon=True)
            self.thread.start()
        except Exception:
            self.active_day = None; self.lock.release(); raise
        return dict(state="running", message="Refreshing the official schedule…")

    def _background(self, day, mode):
        try:
            self.refresh(day, mode=mode)
        except Exception as exc:
            self.memory_error = dict(day=day, message=str(exc))
        finally:
            self.active_day = None
            self.lock.release()

    def refresh(self, day, *, mode=None):
        """One selected-date action; explicit mode remains internal for replay tests."""
        mode = self._refresh_mode(day) if mode is None else mode
        self._validate_day(day, refresh=True, mode=mode)
        if not self.clock_ok():
            raise ValueError("Local clock is uncertain")
        with self.writer():
            state = self._state(day)
            prior = self._view(state["selected"], day) if state["selected"] else None
            prior_selection = state["selected"]
            attempt_id = uuid.uuid4().hex
            folder = self.path("attempts", attempt_id)
            attempt = dict(id=attempt_id, state="running", mode=mode, started_at=self.clock(),
                           message="Refreshing the official schedule…")
            self._write(folder / "started.json", odds.encode(dict(day=day, **attempt)))
            state["attempt"] = attempt; self._save_state(state)
            requests_seen = []
            try:
                result = self._collect(day, folder, requests_seen, state, mode=mode)
                self._retain_quotes(result, prior, prior_selection)
                result.update(schema=odds.VERSION, view_version=odds.VIEW_VERSION, mode=mode, day=day, completed_at=self.clock(), requests=requests_seen)
                if not self.clock_ok():
                    raise ValueError("Clock changed during refresh")
                self._write(folder / "result.json", odds.encode(result))
                inventory = {str(p.relative_to(folder)): odds.digest(p.read_bytes())
                             for p in folder.rglob("*") if p.is_file()}
                manifest = dict(schema=odds.VERSION, id=attempt_id, day=day, files=inventory)
                manifest_raw = odds.encode(manifest)
                self._write(folder / "complete.json", manifest_raw)
                state["selected"] = dict(id=attempt_id, digest=odds.digest(manifest_raw))
                count = sum(g[s + "_quote"] is not None for g in result["games"] for s in ("away", "home"))
                expected = result["expected_outcomes"]
                finals = sum(g["official_result"]["state"] == "final" for g in result["games"])
                gaps = sum(g["official_result"]["state"] == "unavailable" for g in result["games"])
                odds_error = result.get("odds_error")
                status = "partial" if count < expected or gaps or odds_error else "complete"
                message = f"{len(result['games'])} official games updated; {finals} verified final scores."
                if odds_error:
                    message += " Odds unavailable; previous compatible captures retained where available."
                elif mode == "results":
                    message += " Prices were not retrieved for this past date."
                elif expected:
                    message += f" {count} of {expected} supported pregame outcomes priced."
                else:
                    message += " No eligible pregame prices to retrieve."
                if gaps:
                    message += f" {gaps} results need review."
                if not result["games"]:
                    message = "Official schedule confirmed no games on this date."
                state["attempt"] = {**attempt, "state": status, "completed_at": self.clock(), "message": message}
                self._save_state(state)
                return result
            except Exception as exc:
                failed = {**attempt, "state": "failed", "completed_at": self.clock(), "message": str(exc),
                          "requests": requests_seen}
                # A completion may have been written but is not selected unless state publication succeeded.
                prior = self._state(day)
                prior["attempt"] = failed
                try:
                    self._write(folder / "failed.json", odds.encode(failed))
                    self._save_state(prior)
                except Exception:
                    raise ValueError("Refresh failed; ATTEMPT STATUS COULD NOT BE SAVED. Previous selection retained; inspect local storage") from exc
                raise

    def _collect(self, day, folder, receipts, state, *, mode="odds"):
        began = self.monotonic()
        last_end = odds.aware(self.clock())
        def progress(message):
            state["attempt"]["message"] = message
            self._save_state(state)

        def request(provider, route, params):
            nonlocal last_end
            if self.monotonic() - began >= MAX_SECONDS or not self.clock_ok():
                raise ValueError("Refresh time/clock bound reached; start a new manual refresh")
            start = self.clock()
            if odds.aware(start) < last_end:
                raise ValueError("Request chronology moved backwards")
            receipt = dict(sequence=len(receipts), provider=provider, route=route, parameters=params,
                           started_at=start, completed_at=None, status=None)
            receipts.append(receipt)
            try:
                status, raw = self.fetch(provider, route, params)
                receipt["status"] = status
                if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
                    raise ValueError("Provider response exceeded its size bound")
                receipt["raw_file"] = f"raw/{receipt['sequence']:03d}.body"
                receipt["raw_sha256"] = odds.digest(raw)
                self._write(folder / receipt["raw_file"], raw)
                end = self.clock(); receipt["completed_at"] = end
                last_end = odds.aware(end)
                if last_end < odds.aware(start) or (last_end - odds.aware(start)).total_seconds() > 20 or not self.clock_ok():
                    raise ValueError("Request chronology or time bound is invalid")
                if status != 200:
                    raise ValueError(f"Provider returned HTTP {status}")
                return raw, receipt
            except Exception as exc:
                receipt["completed_at"] = receipt["completed_at"] or self.clock()
                receipt["error"] = str(exc) if isinstance(exc, ValueError) else "Provider request failed (" + type(exc).__name__ + ")"
                raise ValueError(receipt["error"]) from None
            finally:
                self._write(folder / f"request-{receipt['sequence']:03d}.json", odds.encode(receipt))

        raw, schedule = request("mlb", "/schedule", dict(date=day, sportId="1", hydrate="team,venue"))
        games = odds.schedule_games(raw, day, schedule["completed_at"])
        result = dict(games=games, diagnostics=[], expected_outcomes=0,
                      schedule_started_at=schedule["started_at"], catalog_started_at=None)
        if mode == "results":
            return result
        eligible = []
        for game in games:
            if not game["reasons"] and odds.aware(game["start"]) <= odds.aware(self.clock()):
                game["reasons"].append("Scheduled start passed; pregame prices unavailable")
            if not game["reasons"]:
                eligible.append(game)
        result["expected_outcomes"] = len(eligible) * 2
        if not eligible:
            return result
        progress("Checking the complete MLB market catalog…")
        try:
            markets, seen, cursor = {}, set(), ""
            for page in range(MAX_PAGES):
                if cursor in seen:
                    raise ValueError("Catalog cursor repeats; discovery is incomplete")
                seen.add(cursor)
                params = dict(series_ticker="KXMLBGAME", status="open", limit="1000")
                if cursor:
                    params["cursor"] = cursor
                raw, receipt = request("kalshi", "/markets", params)
                result["catalog_started_at"] = result["catalog_started_at"] or receipt["started_at"]
                payload = odds.decode(raw)
                if not isinstance(payload, dict) or set(payload) != {"markets", "cursor"} or not isinstance(payload["markets"], list) or not isinstance(payload["cursor"], str):
                    raise ValueError("Catalog response is incomplete")
                for market in payload["markets"]:
                    if not isinstance(market, dict) or not isinstance(market.get("ticker"), str):
                        raise ValueError("Catalog market identity is missing")
                    ticker = market["ticker"]
                    if ticker in markets and markets[ticker] != market:
                        raise ValueError("Catalog contains conflicting market records")
                    markets[ticker] = market
                cursor = payload["cursor"]
                if not cursor:
                    break
            else:
                raise ValueError("Catalog exceeded page bound; discovery is incomplete")
            mapped, diagnostics = odds.map_markets(games, list(markets.values()))
            result["diagnostics"] = diagnostics
        except ValueError as exc:
            # Official observations remain valid; no partial catalog is admitted for
            # matching. Storage errors propagate, and the final clock gate still holds.
            result["odds_error"] = str(exc)
            result["diagnostics"] = []
            for game in eligible:
                for side in ("away", "home"):
                    game[side + "_reason"] = "Odds unavailable: " + str(exc)
            return result
        for index, game in enumerate(eligible, 1):
            progress(f"Reading prices for game {index} of {len(eligible)}…")
            for side in ("away", "home"):
                candidates = mapped[game["id"], side]
                if len(candidates) != 1:
                    game[side + "_reason"] = "Ambiguous team YES markets" if candidates else "No verified team YES market; see catalog Details"
                    continue
                market = candidates[0]
                game[side + "_market"] = {k: market[k] for k in ("ticker", "rules_primary", "rules_secondary")}
                if odds.aware(self.clock()) >= odds.aware(game["start"]):
                    game[side + "_reason"] = "Scheduled start passed during refresh"
                    continue
                try:
                    raw, receipt = request("kalshi", "/markets/" + market["ticker"] + "/orderbook", dict(depth="100"))
                    quote = odds.best_yes_offer(raw)
                    quote.update(ticker=market["ticker"], side="YES", started_at=receipt["started_at"],
                                 completed_at=receipt["completed_at"], schedule_started_at=schedule["started_at"],
                                 catalog_started_at=result["catalog_started_at"], raw_file=receipt["raw_file"],
                                 rules_primary=market["rules_primary"], rules_secondary=market["rules_secondary"])
                    game[side + "_quote"] = quote
                    game[side + "_reason"] = ""
                except ValueError as exc:
                    game[side + "_reason"] = str(exc)
        return result

    def _retain_quotes(self, result, prior, selection):
        """Reference original completed captures; never copy them as new observations."""
        result["retained_quotes"] = []
        if not prior:
            return
        previous = {g["id"]: g for g in prior["games"]}
        for game in result["games"]:
            old = previous.get(game["id"])
            if not old or not odds.same_game(game, old):
                continue
            allowed = (game["official_status"] + ": pregame prices unavailable",
                       "Scheduled start passed; pregame prices unavailable")
            if any(reason not in allowed for reason in game["reasons"]):
                continue
            for side in ("away", "home"):
                q = old.get(side + "_quote")
                if game[side + "_quote"] or not q:
                    continue
                market = game.get(side + "_market")
                reason = game.get(side + "_reason", "")
                if "Ambiguous" in reason or (market and any(market[k] != q[k] for k in market)):
                    continue
                # A new catalog that no longer verifies this market must not carry it
                # forward as the contract for a scheduled game.
                if not game["reasons"] and result["catalog_started_at"] and not result.get("odds_error") and not market:
                    continue
                result["retained_quotes"].append(dict(game_id=game["id"], side=side,
                    source=q.get("source_selection", selection)))

    def _view(self, selected, day):
        result, _ = self.verified(selected, day)
        refs = result.get("retained_quotes", [])
        if not isinstance(refs, list) or len(refs) > 100:
            raise ValueError("Retained price references exceed the daily bound")
        games = {g["id"]: g for g in result["games"]}
        sources, used = {}, set()
        for ref in refs:
            side, identity = ref["side"], ref["game_id"]
            if side not in ("away", "home") or identity not in games or (identity, side) in used:
                raise ValueError("Invalid retained price reference")
            used.add((identity, side))
            source = ref["source"]
            key = (source["id"], source["digest"])
            if key not in sources:
                sources[key], _ = self.verified(source, day)
            old = next((g for g in sources[key]["games"] if g["id"] == identity), None)
            game = games[identity]
            if not old or not odds.same_game(game, old) or game[side + "_quote"]:
                raise ValueError("Retained price identity conflicts with the selected game")
            q = old.get(side + "_quote")
            if not q or odds.aware(q["completed_at"]) > odds.aware(result["completed_at"]):
                raise ValueError("Retained price has no original capture or has invalid chronology")
            game[side + "_quote"] = {**q, "source_selection": source, "retained": True}
        return result

    def verified(self, selected, day):
        identity = selected.get("id", "")
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise ValueError("Invalid saved odds selection")
        folder = self.path("attempts", identity)
        manifest_raw = self.path("attempts", identity, "complete.json").read_bytes()
        if odds.digest(manifest_raw) != selected.get("digest"):
            raise ValueError("Saved odds manifest changed")
        manifest = odds.decode(manifest_raw)
        if not isinstance(manifest, dict) or manifest.get("schema") != odds.VERSION or manifest.get("id") != identity or manifest.get("day") != day:
            raise ValueError("Saved odds bundle has incompatible identity")
        if not isinstance(manifest.get("files"), dict):
            raise ValueError("Saved file inventory is missing")
        for name, expected in manifest["files"].items():
            if not re.fullmatch(r"(?:started\.json|result\.json|request-\d{3}\.json|raw/\d{3}\.body)", name):
                raise ValueError("Unsafe saved file inventory")
            path = self.path("attempts", identity, name)
            if odds.digest(path.read_bytes()) != expected:
                raise ValueError("Saved odds evidence changed")
        if not {"started.json", "result.json"}.issubset(manifest["files"]):
            raise ValueError("Saved odds bundle is incomplete")
        result = odds.decode((folder / "result.json").read_bytes())
        if not isinstance(result, dict) or result.get("schema") != odds.VERSION or result.get("day") != day:
            raise ValueError("Saved odds view has incompatible identity")
        if result.get("view_version") not in (None, odds.VIEW_VERSION):
            raise ValueError("Saved odds view version is unsupported")
        return result, manifest

    def read(self, day):
        self._validate_day(day)
        now = self.clock()
        value = dict(day=day, now=now, today=odds.aware(now).astimezone(odds.CENTRAL).date().isoformat(),
                     clock_ok=self.clock_ok(), selected=None, attempt=None, result=None,
                     running=self.active_day == day, error=None)
        try:
            state = self._state(day)
            value.update(selected=state["selected"], attempt=state["attempt"])
            if state["selected"]:
                value["result"] = self._view(state["selected"], day)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            value["error"] = str(exc)
        if self.memory_error and self.memory_error["day"] == day:
            value["error"] = self.memory_error["message"]
        if value["attempt"] and value["attempt"]["state"] == "running" and not value["running"]:
            value["attempt"] = {**value["attempt"], "state": "interrupted",
                                "message": "Previous refresh did not complete here. Check for another running app; start a new manual refresh when it has stopped."}
        return value

    def download(self, day, identity, name):
        self._validate_day(day)
        state = self._state(day)
        if not state["selected"]:
            raise ValueError("Download requires the explicitly selected saved sheet")
        view = self._view(state["selected"], day)
        selections = [state["selected"]] + [r["source"] for r in view.get("retained_quotes", [])]
        selected = next((s for s in selections if s["id"] == identity), None)
        if selected is None:
            raise ValueError("Download requires the selected sheet or its retained quote evidence")
        _, manifest = self.verified(selected, day)
        if name == "complete.json":
            return self.path("attempts", identity, name).read_bytes()
        if name not in manifest["files"]:
            raise ValueError("Unknown saved download")
        return self.path("attempts", identity, name).read_bytes()
