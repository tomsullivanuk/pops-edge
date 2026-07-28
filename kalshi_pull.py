from http.client import IncompleteRead
import time

import requests
import pandas as pd
from requests.exceptions import ChunkedEncodingError
from urllib3.exceptions import ProtocolError, ReadTimeoutError

from config import KALSHI_CURRENT_FILE

BASE = "https://external-api.kalshi.com/trade-api/v2"
REQUEST_TIMEOUT_SECONDS = 45
RETRY_BACKOFF_SECONDS = [2, 5, 10, 20]
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
KALSHI_COLUMNS = [
    "event_ticker",
    "game",
    "sub_title",
    "category",
    "market_ticker",
    "outcome",
    "market_title",
    "yes_bid_dollars",
    "yes_ask_dollars",
    "last_price_dollars",
    "volume_fp",
    "open_interest_fp",
    "close_time",
]


def is_world_cup_market_event(event):
    event_ticker = event.get("event_ticker", "")

    if event_ticker.startswith("KXWCGAME-"):
        return True

    if event_ticker.startswith("KXMENWORLDCUP-"):
        return True

    return is_world_cup_round_event(event_ticker)


def is_world_cup_round_event(event_ticker):
    return (
        event_ticker.startswith("KXWCROUND-")
        and event_ticker.endswith(("RO16", "QUAR", "SEMI"))
    )


def market_rows_for_event(event):
    event_ticker = event.get("event_ticker", "")
    rows = []

    for market in event.get("markets", []):
        rows.append({
            "event_ticker": event_ticker,
            "game": event.get("title"),
            "sub_title": event.get("sub_title"),
            "category": event.get("category"),
            "market_ticker": market.get("ticker"),
            "outcome": market.get("yes_sub_title"),
            "market_title": market.get("title"),
            "yes_bid_dollars": market.get("yes_bid_dollars"),
            "yes_ask_dollars": market.get("yes_ask_dollars"),
            "last_price_dollars": market.get("last_price_dollars"),
            "volume_fp": market.get("volume_fp"),
            "open_interest_fp": market.get("open_interest_fp"),
            "close_time": market.get("close_time"),
        })

    return rows


def should_retry_response(response):
    return getattr(response, "status_code", None) in RETRY_STATUS_CODES


def retry_message(error, retry_number, delay):
    if isinstance(error, requests.exceptions.Timeout):
        reason = "timed out"
    elif isinstance(error, requests.exceptions.ConnectionError):
        reason = "hit a connection error"
    elif isinstance(error, ReadTimeoutError):
        reason = "timed out"
    elif isinstance(error, (ChunkedEncodingError, ProtocolError, IncompleteRead)):
        reason = "received an incomplete response"
    else:
        reason = f"returned HTTP {getattr(error, 'status_code', 'error')}"

    return (
        f"Kalshi request {reason}; "
        f"retry {retry_number}/{len(RETRY_BACKOFF_SECONDS)} after {delay}s..."
    )


def get_with_retries(url, params, timeout=REQUEST_TIMEOUT_SECONDS):
    last_error = None

    for attempt in range(len(RETRY_BACKOFF_SECONDS) + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if should_retry_response(response):
                last_error = response
                raise requests.exceptions.HTTPError(
                    f"Retryable HTTP status {response.status_code}",
                    response=response,
                )

            response.raise_for_status()
            return response

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            ChunkedEncodingError,
            ProtocolError,
            IncompleteRead,
            ReadTimeoutError,
        ) as error:
            last_error = error

        except requests.exceptions.HTTPError as error:
            response = getattr(error, "response", None)
            if response is None or not should_retry_response(response):
                raise
            last_error = response

        if attempt == len(RETRY_BACKOFF_SECONDS):
            break

        delay = RETRY_BACKOFF_SECONDS[attempt]
        print(retry_message(last_error, attempt + 1, delay))
        time.sleep(delay)

    if hasattr(last_error, "raise_for_status"):
        last_error.raise_for_status()

    raise last_error


def pull_open_events():
    events = []
    cursor = None

    while True:
        params = {
            "status": "open",
            "limit": 200,
            "with_nested_markets": "true"
        }

        if cursor:
            params["cursor"] = cursor

        response = get_with_retries(f"{BASE}/events", params=params)
        data = response.json()

        batch = data.get("events", [])
        events.extend(batch)

        print(f"Pulled {len(events)} events so far...")

        cursor = data.get("cursor")
        if not cursor:
            break

    return events


def main():
    print("Pulling open events...")

    events = pull_open_events()

    rows = []

    for event in events:
        if not is_world_cup_market_event(event):
            continue

        rows.extend(market_rows_for_event(event))

    df = pd.DataFrame(rows, columns=KALSHI_COLUMNS)

    df.to_excel(KALSHI_CURRENT_FILE, index=False)

    print(f"Saved {len(df)} market rows to {KALSHI_CURRENT_FILE}")


if __name__ == "__main__":
    main()
