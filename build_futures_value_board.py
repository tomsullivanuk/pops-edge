import os
import re
from datetime import datetime

import pandas as pd

from config import (
    BET_LOG_FILE,
    COL_ACTION,
    COL_BUCKET,
    COL_CONTRACTS,
    COL_CURRENT_ACTION,
    COL_EDGE,
    COL_ENTRY_PRICE,
    COL_MARKET_TICKER,
    COL_MARKET_TICKER_TITLE,
    COL_POSITION,
    COL_SILVER,
    COL_STATUS,
    FUTURES_VALUE_BOARD_FILE,
    KALSHI_CURRENT_FILE,
    SHEET_BET_SHEET,
    SHEET_CANDIDATES,
    SHEET_DEFINITIONS,
    SHEET_KALSHI_NORMALIZED,
    SHEET_RUN_METADATA,
    SHEET_SILVER_FUTURES,
    SHEET_SILVER_METADATA,
    SHEET_SILVER_NORMALIZED,
    SHEET_VALUE_BOARD,
    SHEET_WAGERS,
    SILVER_FUTURES_CURRENT_FILE,
)

SILVER_FILE = SILVER_FUTURES_CURRENT_FILE
KALSHI_FILE = KALSHI_CURRENT_FILE
OUTPUT_FILE = FUTURES_VALUE_BOARD_FILE

BANKROLL = 500
MIN_EDGE = 0.05
ACTIVE_STATUSES = ["Open", "Partially Closed"]

CODE_MAP = {
    "ALG": "DZA",
    "IRN": "IRI",
    "HAI": "HTI",
}

TEAM_NAME_TO_CODE = {
    "ARGENTINA": "ARG",
    "AUSTRALIA": "AUS",
    "AUSTRIA": "AUT",
    "BELGIUM": "BEL",
    "BRAZIL": "BRA",
    "CANADA": "CAN",
    "COLOMBIA": "COL",
    "CROATIA": "CRO",
    "ENGLAND": "ENG",
    "FRANCE": "FRA",
    "GERMANY": "GER",
    "GHANA": "GHA",
    "JAPAN": "JPN",
    "MEXICO": "MEX",
    "MOROCCO": "MAR",
    "NETHERLANDS": "NED",
    "PORTUGAL": "POR",
    "SPAIN": "ESP",
    "SWEDEN": "SWE",
    "UNITED STATES": "USA",
    "USA": "USA",
    "URUGUAY": "URU",
}

STAGE_DEFINITIONS = {
    "R16": {
        "label": "Round of 16",
        "silver_column": "R16",
        "patterns": ["round of 16", "r16", "last 16"],
    },
    "Qtr": {
        "label": "Quarterfinals",
        "silver_column": "Qtr",
        "patterns": ["quarterfinal", "quarter-final", "quarter final"],
    },
    "Semi": {
        "label": "Semifinals",
        "silver_column": "Semi",
        "patterns": ["semifinal", "semi-final", "semi final"],
    },
    "Champ": {
        "label": "Champion",
        "silver_column": "Champ",
        "patterns": ["world cup winner", "world cup champion", "champion", "winner"],
    },
}

BET_COLUMNS = [
    "Stage",
    "Team",
    COL_ACTION,
    COL_SILVER,
    "Market Price",
    "Yes Bid",
    "Yes Ask",
    COL_EDGE,
    "ROI",
    "EV per $100",
    "Quarter Kelly",
    f"Stake on ${BANKROLL}",
    COL_BUCKET,
    "Volume",
    "event_ticker",
    COL_MARKET_TICKER,
    COL_POSITION,
    COL_CURRENT_ACTION,
    COL_ENTRY_PRICE,
    "Current Value Change",
    "Stake",
    COL_STATUS,
]


def normalize_code(value):
    text = str(value).strip()
    match = re.search(r"\b[A-Z]{3}\b", text.upper())
    if match:
        code = match.group(0)
        return CODE_MAP.get(code, code)

    normalized_name = re.sub(r"[^A-Z ]", "", text.upper()).strip()
    return TEAM_NAME_TO_CODE.get(normalized_name, normalized_name)


def bucket(edge):
    if edge >= 0.10:
        return "A"
    if edge >= 0.07:
        return "B"
    if edge >= 0.05:
        return "C"
    return ""


def numeric(value):
    return pd.to_numeric(value, errors="coerce")


def read_active_wagers():
    if not os.path.exists(BET_LOG_FILE):
        return pd.DataFrame()

    wager_log = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_WAGERS)
    required_columns = [
        COL_MARKET_TICKER_TITLE,
        COL_ACTION,
        COL_ENTRY_PRICE,
        COL_CONTRACTS,
        COL_STATUS,
    ]
    missing_columns = [column for column in required_columns if column not in wager_log.columns]
    if missing_columns:
        print(f"WARNING: Could not add futures positions; missing wager columns: {missing_columns}")
        return pd.DataFrame()

    return wager_log[wager_log[COL_STATUS].isin(ACTIVE_STATUSES)].copy()


def add_active_wager_exposure(bet_sheet):
    for column, default in [
        (COL_POSITION, "No"),
        (COL_CURRENT_ACTION, ""),
        (COL_ENTRY_PRICE, ""),
        ("Current Value Change", ""),
        ("Stake", ""),
        (COL_STATUS, ""),
    ]:
        bet_sheet[column] = default

    if bet_sheet.empty:
        return bet_sheet

    try:
        active_wagers = read_active_wagers()
    except Exception as error:
        print(f"WARNING: Could not add futures position exposure: {error}")
        return bet_sheet

    if active_wagers.empty:
        return bet_sheet

    active_wagers = active_wagers[[
        COL_MARKET_TICKER_TITLE,
        COL_ACTION,
        COL_ENTRY_PRICE,
        COL_CONTRACTS,
        COL_STATUS,
    ]].copy()
    active_wagers["Stake"] = active_wagers.apply(
        lambda row: (
            row[COL_CONTRACTS] * row[COL_ENTRY_PRICE]
            if row[COL_ACTION] == "BUY YES"
            else row[COL_CONTRACTS] * (1 - row[COL_ENTRY_PRICE])
        ),
        axis=1,
    ).round(2)
    active_wagers = active_wagers.rename(columns={
        COL_MARKET_TICKER_TITLE: COL_MARKET_TICKER,
        COL_ACTION: COL_CURRENT_ACTION,
    })
    active_wagers[COL_POSITION] = "Yes"

    bet_sheet = bet_sheet.drop(columns=[
        COL_POSITION,
        COL_CURRENT_ACTION,
        COL_ENTRY_PRICE,
        "Current Value Change",
        "Stake",
        COL_STATUS,
    ]).merge(
        active_wagers[[
            COL_MARKET_TICKER,
            COL_POSITION,
            COL_CURRENT_ACTION,
            COL_ENTRY_PRICE,
            "Stake",
            COL_STATUS,
        ]],
        on=COL_MARKET_TICKER,
        how="left",
    )
    bet_sheet[COL_POSITION] = bet_sheet[COL_POSITION].fillna("No")
    bet_sheet["Current Value Change"] = bet_sheet.apply(
        lambda row: (
            row["Market Price"] - row[COL_ENTRY_PRICE]
            if row[COL_POSITION] == "Yes" and row[COL_CURRENT_ACTION] == "BUY YES"
            else (
                row[COL_ENTRY_PRICE] - row["Market Price"]
                if row[COL_POSITION] == "Yes" and row[COL_CURRENT_ACTION] == "SELL YES"
                else ""
            )
        ),
        axis=1,
    )
    return bet_sheet


def classify_stage(row):
    event_ticker = str(row.get("event_ticker", ""))
    if event_ticker.startswith("KXWCGAME-"):
        return None

    text = " ".join(
        str(row.get(column, ""))
        for column in ["event_ticker", "market_ticker", "game", "sub_title", "market_title"]
    ).lower()

    if " vs " in text and "qualif" not in text:
        return None

    for stage, definition in STAGE_DEFINITIONS.items():
        if any(pattern in text for pattern in definition["patterns"]):
            if stage == "Champ" and any(
                pattern in text
                for pattern in ["game winner", "match winner", "winner?"]
            ):
                return None
            return stage

    return None


def team_from_market(row):
    market_ticker = str(row.get("market_ticker", "")).upper()
    suffix = market_ticker.split("-")[-1]
    if re.fullmatch(r"[A-Z]{3}", suffix):
        return normalize_code(suffix)

    outcome = row.get("outcome", "")
    outcome_code = normalize_code(outcome)
    if outcome_code:
        return outcome_code

    market_title = str(row.get("market_title", ""))
    return normalize_code(market_title)


print("Loading futures files...")

silver = pd.read_excel(SILVER_FILE, sheet_name=SHEET_SILVER_FUTURES)
silver_metadata = pd.read_excel(SILVER_FILE, sheet_name=SHEET_SILVER_METADATA)
kalshi = pd.read_excel(KALSHI_FILE)

silver_rows = []
for _, row in silver.iterrows():
    team = normalize_code(row["Team"])
    for stage, definition in STAGE_DEFINITIONS.items():
        silver_column = definition["silver_column"]
        if silver_column not in row.index:
            continue

        probability = numeric(row[silver_column])
        if pd.isna(probability):
            continue

        silver_rows.append({
            "stage_key": stage,
            "Stage": definition["label"],
            "Team": team,
            "silver_prob": probability,
        })

silver_norm = pd.DataFrame(silver_rows)
print(f"Silver futures rows: {len(silver_norm)}")

kalshi_rows = []
for _, row in kalshi.iterrows():
    stage = classify_stage(row)
    if not stage:
        continue

    team = team_from_market(row)
    if not team:
        continue

    kalshi_rows.append({
        "stage_key": stage,
        "Stage": STAGE_DEFINITIONS[stage]["label"],
        "Team": team,
        "kalshi_outcome": row.get("outcome", ""),
        "game": row.get("game", ""),
        "market_title": row.get("market_title", ""),
        "yes_bid": numeric(row.get("yes_bid_dollars")),
        "yes_ask": numeric(row.get("yes_ask_dollars")),
        "last_price": numeric(row.get("last_price_dollars")),
        "volume": numeric(row.get("volume_fp")),
        "open_interest": numeric(row.get("open_interest_fp")),
        "event_ticker": row.get("event_ticker", ""),
        "market_ticker": row.get("market_ticker", ""),
    })

kalshi_norm = pd.DataFrame(kalshi_rows)
print(f"Kalshi futures rows: {len(kalshi_norm)}")

if kalshi_norm.empty:
    value_board = pd.DataFrame(columns=[
        "stage_key", "Stage", "Team", "silver_prob", "yes_bid", "yes_ask",
        "last_price", "volume", "open_interest", "event_ticker", "market_ticker",
    ])
else:
    value_board = silver_norm.merge(
        kalshi_norm,
        on=["stage_key", "Stage", "Team"],
        how="inner",
    )

print(f"Merged futures rows: {len(value_board)}")

qc_status = "PASS"
qc_messages = []

if not kalshi_norm.empty and kalshi_norm["market_ticker"].nunique() != len(kalshi_norm):
    qc_status = "FAIL"
    qc_messages.append("Duplicate Kalshi futures market tickers detected.")

if not silver_norm.empty and silver_norm[["stage_key", "Team"]].drop_duplicates().shape[0] != len(silver_norm):
    qc_status = "FAIL"
    qc_messages.append("Duplicate Silver futures stage/team combinations detected.")

if qc_status == "PASS":
    qc_messages.append("All quality checks passed.")

if qc_status == "FAIL":
    raise ValueError("Futures quality checks failed. Review duplicate keys.")

if not value_board.empty:
    value_board["buy_edge"] = value_board["silver_prob"] - value_board["yes_ask"]
    value_board["buy_roi"] = value_board["buy_edge"] / value_board["yes_ask"]
    value_board["sell_edge"] = value_board["yes_bid"] - value_board["silver_prob"]
    value_board["sell_roi"] = value_board["sell_edge"] / (1 - value_board["yes_bid"])

bet_rows = []
for _, row in value_board.iterrows():
    if row["buy_edge"] >= MIN_EDGE:
        kelly = (row["silver_prob"] - row["yes_ask"]) / (1 - row["yes_ask"])
        quarter_kelly = max(kelly / 4, 0)
        bet_rows.append({
            "Stage": row["Stage"],
            "Team": row["Team"],
            COL_ACTION: "BUY YES",
            COL_SILVER: row["silver_prob"],
            "Market Price": row["yes_ask"],
            "Yes Bid": row["yes_bid"],
            "Yes Ask": row["yes_ask"],
            COL_EDGE: row["buy_edge"],
            "ROI": row["buy_roi"],
            "EV per $100": row["buy_edge"] * 100,
            "Quarter Kelly": quarter_kelly,
            f"Stake on ${BANKROLL}": quarter_kelly * BANKROLL,
            COL_BUCKET: bucket(row["buy_edge"]),
            "Volume": row["volume"],
            "event_ticker": row["event_ticker"],
            COL_MARKET_TICKER: row["market_ticker"],
        })

    if row["sell_edge"] >= MIN_EDGE:
        kelly = (row["yes_bid"] - row["silver_prob"]) / row["yes_bid"]
        quarter_kelly = max(kelly / 4, 0)
        bet_rows.append({
            "Stage": row["Stage"],
            "Team": row["Team"],
            COL_ACTION: "SELL YES",
            COL_SILVER: row["silver_prob"],
            "Market Price": row["yes_bid"],
            "Yes Bid": row["yes_bid"],
            "Yes Ask": row["yes_ask"],
            COL_EDGE: row["sell_edge"],
            "ROI": row["sell_roi"],
            "EV per $100": row["sell_edge"] * 100,
            "Quarter Kelly": quarter_kelly,
            f"Stake on ${BANKROLL}": quarter_kelly * BANKROLL,
            COL_BUCKET: bucket(row["sell_edge"]),
            "Volume": row["volume"],
            "event_ticker": row["event_ticker"],
            COL_MARKET_TICKER: row["market_ticker"],
        })

bet_sheet = pd.DataFrame(bet_rows, columns=BET_COLUMNS)

if not bet_sheet.empty:
    bet_sheet = bet_sheet[
        (bet_sheet["Market Price"] >= 0.05)
        & (bet_sheet["Market Price"] <= 0.95)
        & (bet_sheet["Volume"] > 0)
    ].copy()
    bet_sheet = bet_sheet.sort_values(COL_EDGE, ascending=False)
    bet_sheet["ROI"] = bet_sheet["ROI"].round(2)
    bet_sheet["Quarter Kelly"] = bet_sheet["Quarter Kelly"].round(2)
    bet_sheet[f"Stake on ${BANKROLL}"] = bet_sheet[f"Stake on ${BANKROLL}"].round(2)

bet_sheet = add_active_wager_exposure(bet_sheet)

candidates = bet_sheet.copy()

definitions = pd.DataFrame([
    ["Stage", "Futures market stage: Round of 16, Quarterfinals, Semifinals, or Champion."],
    ["Team", "Normalized three-letter team code."],
    [COL_ACTION, "BUY YES means Silver is above Kalshi Ask. SELL YES means Kalshi Bid is above Silver."],
    [COL_SILVER, "Silver model probability that the team reaches or wins this stage."],
    ["Market Price", "For BUY YES, this is the Yes Ask. For SELL YES, this is the Yes Bid."],
    [COL_EDGE, "Difference between Silver and market price on the selected side."],
    ["ROI", "Expected return relative to capital at risk."],
    ["Quarter Kelly", "A conservative bankroll allocation fraction based on Kelly sizing, divided by four."],
    [f"Stake on ${BANKROLL}", "Quarter Kelly multiplied by the assumed bankroll."],
    [COL_BUCKET, "A/B/C ranking based on edge size: A >= 10%, B >= 7%, C >= 5%."],
    [COL_POSITION, "Yes if there is an active open or partially closed wager on this contract."],
    [COL_CURRENT_ACTION, "The action of the existing wager from the unified Bet Log."],
    [COL_ENTRY_PRICE, "Entry price of the existing wager."],
    ["Current Value Change", "For BUY YES, current market price minus entry. For SELL YES, entry minus current market price."],
    ["Stake", "Approximate dollars at risk for the existing wager."],
    [COL_STATUS, "Open or partially closed status of the existing wager."],
], columns=["Field", "Plain-English Definition"])

run_metadata = pd.DataFrame([
    ["Futures Value Board Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["QC Status", qc_status],
    ["QC Messages", " | ".join(qc_messages)],
    ["Silver Futures Normalized Rows", len(silver_norm)],
    ["Kalshi Futures Normalized Rows", len(kalshi_norm)],
    ["Merged Rows", len(value_board)],
    ["Candidate Bets", len(candidates)],
    ["Bet Sheet Rows", len(bet_sheet)],
    ["Minimum Edge", MIN_EDGE],
    ["Bankroll", BANKROLL],
], columns=["Field", "Value"])

run_metadata = pd.concat([run_metadata, silver_metadata], ignore_index=True)

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    bet_sheet.to_excel(writer, sheet_name=SHEET_BET_SHEET, index=False)
    run_metadata.to_excel(writer, sheet_name=SHEET_RUN_METADATA, index=False)
    candidates.to_excel(writer, sheet_name=SHEET_CANDIDATES, index=False)
    value_board.to_excel(writer, sheet_name=SHEET_VALUE_BOARD, index=False)
    silver_norm.to_excel(writer, sheet_name=SHEET_SILVER_NORMALIZED, index=False)
    kalshi_norm.to_excel(writer, sheet_name=SHEET_KALSHI_NORMALIZED, index=False)
    definitions.to_excel(writer, sheet_name=SHEET_DEFINITIONS, index=False)

print()
print(f"Saved: {OUTPUT_FILE}")
print(f"Total futures rows: {len(value_board)}")
print(f"Candidate bets: {len(candidates)}")
print(f"Bet Sheet rows: {len(bet_sheet)}")
print(f"QC Status: {qc_status}")
