import requests
import pandas as pd

from config import KALSHI_CURRENT_FILE

BASE = "https://external-api.kalshi.com/trade-api/v2"

print("Pulling open events...")

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

    response = requests.get(f"{BASE}/events", params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    batch = data.get("events", [])
    events.extend(batch)

    print(f"Pulled {len(events)} events so far...")

    cursor = data.get("cursor")
    if not cursor:
        break

rows = []

for event in events:
    event_ticker = event.get("event_ticker", "")

    # Keep only World Cup full-game winner markets
    if not event_ticker.startswith("KXWCGAME-"):
        continue

    markets = event.get("markets", [])

    for market in markets:
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

df = pd.DataFrame(rows)

df.to_excel(KALSHI_CURRENT_FILE, index=False)

print(f"Saved {len(df)} market rows to {KALSHI_CURRENT_FILE}")
