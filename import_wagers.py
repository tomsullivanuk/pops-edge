import os
import re
import glob
import shutil
import pandas as pd
from datetime import datetime

from config import (
    BET_LOG_FILE as BET_LOG_FILENAME,
    COL_ACTION,
    COL_BUCKET,
    COL_CLOSING_PRICE,
    COL_CLV,
    COL_CLV_PCT,
    COL_EDGE,
    COL_MARKET_TICKER,
    COL_MARKET_TICKER_TITLE,
    COL_MARKET_TYPE,
    COL_MATCH,
    COL_MATCH_DATE,
    COL_OUTCOME,
    COL_SILVER,
    COL_SILVER_PROBABILITY,
    COL_STAGE,
    COL_TEAM,
    COL_DATE,
    DOWNLOADS_DIR,
    FUTURES_VALUE_BOARD_FILE as FUTURES_VALUE_BOARD_FILENAME,
    KALSHI_CURRENT_FILE as KALSHI_CURRENT_FILENAME,
    PROJECT_DIR,
    SHEET_BET_SHEET,
    SHEET_SUMMARY,
    SHEET_WAGERS,
    VALUE_BOARD_FILE as VALUE_BOARD_FILENAME,
    WAGER_LOGS_ARCHIVE_DIR,
)

VALUE_BOARD_FILE = os.path.join(PROJECT_DIR, VALUE_BOARD_FILENAME)
FUTURES_VALUE_BOARD_FILE = os.path.join(PROJECT_DIR, FUTURES_VALUE_BOARD_FILENAME)
KALSHI_CURRENT_FILE = os.path.join(PROJECT_DIR, KALSHI_CURRENT_FILENAME)
BET_LOG_FILE = os.path.join(PROJECT_DIR, BET_LOG_FILENAME)

CODE_MAP = {
    "ALG": "DZA",
    "IRN": "IRI",
    "HAI": "HTI",
}

def money(value):
    if pd.isna(value) or value == "":
        return 0.0
    return float(value)

def weighted_avg_price(df):
    total_contracts = df["Amount_In_Dollars"].astype(float).sum()
    if total_contracts == 0:
        return None
    weighted = (
        df["Amount_In_Dollars"].astype(float)
        * df["Price_In_Cents"].astype(float)
    ).sum()
    return weighted / total_contracts / 100

def safe_first(series, default=""):
    if len(series) == 0:
        return default
    value = series.iloc[0]
    if pd.isna(value):
        return default
    return value

def is_blank(value):
    return pd.isna(value) or value == ""

def preserve_prior_then_current(prior_value, current_value):
    if not is_blank(prior_value):
        return prior_value
    if not is_blank(current_value):
        return current_value
    return ""

def get_prior_value(prior_row, column):
    if prior_row is None or column not in prior_row.index:
        return ""
    value = prior_row[column]
    if pd.isna(value):
        return ""
    return value

def numeric_value(value):
    if is_blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def calculate_clv(action, entry_price, closing_price, prior_clv="", prior_clv_pct=""):
    closing_price = numeric_value(closing_price)
    entry_price = numeric_value(entry_price)

    if closing_price is None:
        return prior_clv, prior_clv_pct

    if entry_price is None or entry_price == 0:
        return "", ""

    if action == "BUY YES":
        clv = closing_price - entry_price
    elif action == "SELL YES":
        clv = entry_price - closing_price
    else:
        return "", ""

    return round(clv, 4), round(clv / entry_price, 4)

def normalize_team_code(value):
    code = str(value).strip().upper()
    return CODE_MAP.get(code, code)

def classify_market_ticker(market_ticker):
    ticker = str(market_ticker).strip().upper()

    if ticker.startswith("KXWCGAME-"):
        return "Match", ""
    if re.match(r"^KXWCROUND-\d{2}RO16-", ticker):
        return "Futures", "Round of 16"
    if re.match(r"^KXWCROUND-\d{2}QUAR-", ticker):
        return "Futures", "Quarterfinals"
    if re.match(r"^KXWCROUND-\d{2}SEMI-", ticker):
        return "Futures", "Semifinals"
    if re.match(r"^KXMENWORLDCUP-\d{2}-", ticker):
        return "Futures", "Champion"

    return "", ""

def team_from_ticker(market_ticker):
    suffix = str(market_ticker).strip().upper().split("-")[-1]
    if suffix == "TIE":
        return ""
    if re.fullmatch(r"[A-Z]{3}", suffix):
        return normalize_team_code(suffix)
    return ""

def match_date_from_ticker(market_ticker):
    match = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", str(market_ticker))
    if not match:
        return ""

    year = 2000 + int(match.group(1))
    month_text = match.group(2)
    day = int(match.group(3))

    months = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
        "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
        "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    month = months.get(month_text)
    if not month:
        return ""

    return f"{year}-{month:02d}-{day:02d}"

def normalize_match_date(value):
    if is_blank(value):
        return ""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = pd.to_datetime(value, unit="D", origin="1899-12-30", errors="coerce")
    else:
        parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return ""

    if parsed.year < 2000:
        return ""

    return parsed.strftime("%Y-%m-%d")

# -----------------------------
# Find latest Kalshi Activity CSV
# -----------------------------

activity_files = (
    glob.glob(os.path.join(DOWNLOADS_DIR, "Kalshi-Recent-Activity-All*.csv")) +
    glob.glob(os.path.join(PROJECT_DIR, "Kalshi-Recent-Activity-All*.csv"))
)

if not activity_files:
    raise FileNotFoundError("No Kalshi activity CSV found in Downloads or project folder.")

activity_file = max(activity_files, key=os.path.getmtime)
print(f"Using Kalshi activity file: {activity_file}")

activity = pd.read_csv(activity_file)

# -----------------------------
# Load current Value Board lookups
# -----------------------------

LOOKUP_COLUMNS = [
    COL_DATE,
    COL_MARKET_TYPE,
    COL_STAGE,
    COL_TEAM,
    COL_MATCH,
    COL_OUTCOME,
    COL_ACTION,
    COL_SILVER,
    COL_EDGE,
    COL_BUCKET,
    COL_MARKET_TICKER,
]

def read_value_board_lookup(path, market_type):
    if not os.path.exists(path):
        return pd.DataFrame(columns=LOOKUP_COLUMNS)

    bet_sheet = pd.read_excel(path, sheet_name=SHEET_BET_SHEET)
    if COL_MARKET_TICKER not in bet_sheet.columns:
        print(f"WARNING: {path} Bet Sheet has no {COL_MARKET_TICKER} column.")
        return pd.DataFrame(columns=LOOKUP_COLUMNS)

    lookup = bet_sheet.copy()
    lookup[COL_MARKET_TYPE] = market_type

    if COL_STAGE not in lookup.columns:
        lookup[COL_STAGE] = ""
    if COL_TEAM not in lookup.columns:
        lookup[COL_TEAM] = lookup[COL_MARKET_TICKER].apply(team_from_ticker)

    for column in LOOKUP_COLUMNS:
        if column not in lookup.columns:
            lookup[column] = ""

    return lookup[LOOKUP_COLUMNS].drop_duplicates(
        subset=[COL_MARKET_TICKER],
        keep="first",
    )

value_lookup = pd.concat(
    [
        read_value_board_lookup(VALUE_BOARD_FILE, "Match"),
        read_value_board_lookup(FUTURES_VALUE_BOARD_FILE, "Futures"),
    ],
    ignore_index=True,
).drop_duplicates(subset=[COL_MARKET_TICKER], keep="first")

kalshi_outcome_lookup = pd.DataFrame(columns=[COL_MARKET_TICKER, "Kalshi Outcome"])
if os.path.exists(KALSHI_CURRENT_FILE):
    kalshi_current = pd.read_excel(KALSHI_CURRENT_FILE)
    if COL_MARKET_TICKER in kalshi_current.columns and "outcome" in kalshi_current.columns:
        kalshi_outcome_lookup = (
            kalshi_current[[COL_MARKET_TICKER, "outcome"]]
            .rename(columns={"outcome": "Kalshi Outcome"})
            .drop_duplicates(subset=[COL_MARKET_TICKER], keep="first")
        )

# -----------------------------
# Load existing Bet Log
# -----------------------------

prior_lookup = pd.DataFrame()

if os.path.exists(BET_LOG_FILE):
    try:
        prior = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_WAGERS)
        if COL_MARKET_TICKER_TITLE in prior.columns:
            prior_lookup = prior.drop_duplicates(
                subset=[COL_MARKET_TICKER_TITLE],
                keep="first"
            ).copy()
    except Exception as e:
        print(f"WARNING: Could not read prior bet log: {e}")

# -----------------------------
# Prepare activity rows
# -----------------------------

trade_rows = activity[activity["type"] == "Trade"].copy()
settlement_rows = activity[activity["type"] == "Settlement"].copy()

trade_rows["Original_Date"] = pd.to_datetime(
    trade_rows["Original_Date"],
    errors="coerce"
)

settlement_rows["Original_Date"] = pd.to_datetime(
    settlement_rows["Original_Date"],
    errors="coerce"
)

# -----------------------------
# Build Wager Rows
# -----------------------------

wager_rows = []

for market_ticker, trades in trade_rows.groupby("Market_Ticker"):

    trades = trades.sort_values("Original_Date").copy()

    yes_trades = trades[trades["Direction"].astype(str).str.strip() == "Yes"]
    no_trades = trades[trades["Direction"].astype(str).str.strip() == "No"]

    if yes_trades.empty and no_trades.empty:
        continue

    first_trade = trades.iloc[0]
    first_direction = str(first_trade["Direction"]).strip()

    if first_direction == "Yes":
        kalshi_action = "BUY YES"
        entry_trades = yes_trades
        exit_trades = no_trades
    else:
        kalshi_action = "SELL YES"
        entry_trades = no_trades
        exit_trades = yes_trades

    contracts = entry_trades["Amount_In_Dollars"].astype(float).sum()
    entry_price = weighted_avg_price(entry_trades)
    fee_in = entry_trades["Fee_In_Dollars"].apply(money).sum()

    exit_price = None
    fee_out = 0.0
    status = "Open"
    realized_pl = None

    if not exit_trades.empty:
        exit_contracts = exit_trades["Amount_In_Dollars"].astype(float).sum()
        exit_price = weighted_avg_price(exit_trades)
        fee_out = exit_trades["Fee_In_Dollars"].apply(money).sum()

        status = "Closed Early" if abs(exit_contracts - contracts) < 0.01 else "Partially Closed"

        if kalshi_action == "BUY YES":
            realized_pl = exit_contracts * (exit_price - entry_price) - fee_in - fee_out
        else:
            realized_pl = exit_contracts * (entry_price - exit_price) - fee_in - fee_out

    # -----------------------------
    # Existing Bet Log fields
    # -----------------------------

    prior_row = None

    if not prior_lookup.empty:
        old = prior_lookup[prior_lookup[COL_MARKET_TICKER_TITLE] == market_ticker]
        if not old.empty:
            prior_row = old.iloc[0]

    settlement = settlement_rows[
        settlement_rows["Market_Ticker"] == market_ticker
    ]

    market_result = get_prior_value(prior_row, "Market Result")
    contract_won = get_prior_value(prior_row, "Contract Won")

    if not settlement.empty:
        market_result = str(safe_first(settlement["Result"])).strip().lower()

        if kalshi_action == "BUY YES":
            contract_won = "Yes" if market_result == "yes" else "No"
        else:
            contract_won = "Yes" if market_result == "no" else "No"

        if status == "Open":
            status = "Settled"

            if kalshi_action == "BUY YES":
                realized_pl = contracts * (1 - entry_price) - fee_in if market_result == "yes" else -contracts * entry_price - fee_in
            else:
                realized_pl = contracts * entry_price - fee_in if market_result == "no" else -contracts * (1 - entry_price) - fee_in

    # -----------------------------
    # Current Value Board fields
    # -----------------------------

    current_match_date = ""
    current_market_type = ""
    current_stage = ""
    current_team = ""
    current_match = ""
    current_outcome = ""
    current_action = ""
    current_silver = ""
    current_edge = ""
    current_bucket = ""

    if not value_lookup.empty:
        vb = value_lookup[value_lookup[COL_MARKET_TICKER] == market_ticker]

        if not vb.empty:
            current_match_date = vb.iloc[0].get(COL_DATE, "")
            current_market_type = vb.iloc[0].get(COL_MARKET_TYPE, "")
            current_stage = vb.iloc[0].get(COL_STAGE, "")
            current_team = vb.iloc[0].get(COL_TEAM, "")
            current_match = vb.iloc[0].get(COL_MATCH, "")
            current_outcome = vb.iloc[0].get(COL_OUTCOME, "")
            current_action = vb.iloc[0].get(COL_ACTION, "")
            current_silver = vb.iloc[0].get(COL_SILVER, "")
            current_edge = vb.iloc[0].get(COL_EDGE, "")
            current_bucket = vb.iloc[0].get(COL_BUCKET, "")

    current_kalshi_outcome = ""
    if not kalshi_outcome_lookup.empty:
        kalshi_market = kalshi_outcome_lookup[
            kalshi_outcome_lookup[COL_MARKET_TICKER] == market_ticker
        ]
        if not kalshi_market.empty:
            current_kalshi_outcome = kalshi_market.iloc[0].get("Kalshi Outcome", "")

    prior_match_date = normalize_match_date(get_prior_value(prior_row, COL_MATCH_DATE))
    prior_market_type = get_prior_value(prior_row, COL_MARKET_TYPE)
    prior_stage = get_prior_value(prior_row, COL_STAGE)
    prior_team = get_prior_value(prior_row, COL_TEAM)
    prior_match = get_prior_value(prior_row, COL_MATCH)
    prior_outcome = get_prior_value(prior_row, COL_OUTCOME)
    prior_action = get_prior_value(prior_row, COL_ACTION)
    prior_silver = get_prior_value(prior_row, COL_SILVER_PROBABILITY)
    prior_edge = get_prior_value(prior_row, COL_EDGE)
    prior_bucket = get_prior_value(prior_row, COL_BUCKET)
    prior_closing_price = get_prior_value(prior_row, COL_CLOSING_PRICE)
    prior_clv = get_prior_value(prior_row, COL_CLV)
    prior_clv_pct = get_prior_value(prior_row, COL_CLV_PCT)

    current_match_date = normalize_match_date(current_match_date)
    ticker_match_date = normalize_match_date(match_date_from_ticker(market_ticker))
    classified_market_type, classified_stage = classify_market_ticker(market_ticker)
    ticker_team = team_from_ticker(market_ticker)

    market_type = classified_market_type or preserve_prior_then_current(
        prior_market_type,
        current_market_type,
    )
    stage = classified_stage or preserve_prior_then_current(prior_stage, current_stage)
    team = preserve_prior_then_current(
        prior_team,
        preserve_prior_then_current(current_team, ticker_team),
    )
    if str(market_ticker).strip().upper().endswith("-TIE"):
        team = ""

    match_date = preserve_prior_then_current(
        prior_match_date,
        preserve_prior_then_current(current_match_date, ticker_match_date)
    )

    match = preserve_prior_then_current(prior_match, current_match)
    outcome = preserve_prior_then_current(
        prior_outcome,
        preserve_prior_then_current(current_outcome, current_kalshi_outcome),
    )
    silver = preserve_prior_then_current(prior_silver, current_silver)
    edge = preserve_prior_then_current(prior_edge, current_edge)
    bucket = preserve_prior_then_current(prior_bucket, current_bucket)

    if market_type == "Futures":
        match_date = ""
        match = ""

    # Kalshi action is authoritative unless blank; prior/current only fill blanks.
    action = kalshi_action
    if is_blank(action):
        action = preserve_prior_then_current(prior_action, current_action)

    clv, clv_pct = calculate_clv(
        action,
        entry_price,
        prior_closing_price,
        prior_clv,
        prior_clv_pct,
    )

    wager_rows.append({
        "Date Placed": first_trade["Original_Date"].strftime("%Y-%m-%d %H:%M:%S")
            if pd.notna(first_trade["Original_Date"]) else "",
        COL_MARKET_TYPE: market_type,
        COL_STAGE: stage,
        COL_TEAM: team,
        COL_MATCH_DATE: match_date,
        COL_MATCH: match,
        COL_OUTCOME: outcome,
        COL_ACTION: action,
        COL_MARKET_TICKER_TITLE: market_ticker,
        COL_SILVER_PROBABILITY: silver,
        COL_EDGE: edge,
        COL_BUCKET: bucket,
        "Market Result": market_result,
        "Contract Won": contract_won,
        "Contracts": round(contracts, 2),
        "Entry Price": round(entry_price, 4) if entry_price is not None else "",
        "Exit Price": round(exit_price, 4) if exit_price is not None else "",
        "Fee In": round(fee_in, 2),
        "Fee Out": round(fee_out, 2),
        "Status": status,
        COL_CLOSING_PRICE: prior_closing_price,
        COL_CLV: clv,
        COL_CLV_PCT: clv_pct,
        "Realized P/L": round(realized_pl, 2) if realized_pl is not None else "",
    })

wagers = pd.DataFrame(wager_rows)

if not wagers.empty:
    wagers = wagers.sort_values("Date Placed")

# -----------------------------
# Summary
# -----------------------------

summary = pd.DataFrame([
    ["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["Kalshi Activity File", os.path.basename(activity_file)],
    ["Total Wagers", len(wagers)],
    ["Closed Early", (wagers["Status"] == "Closed Early").sum() if not wagers.empty else 0],
    ["Partially Closed", (wagers["Status"] == "Partially Closed").sum() if not wagers.empty else 0],
    ["Settled", (wagers["Status"] == "Settled").sum() if not wagers.empty else 0],
    ["Open", (wagers["Status"] == "Open").sum() if not wagers.empty else 0],
    ["Total Realized P/L", wagers["Realized P/L"].apply(money).sum() if not wagers.empty else 0],
], columns=["Metric", "Value"])

# -----------------------------
# Save
# -----------------------------

with pd.ExcelWriter(BET_LOG_FILE, engine="openpyxl") as writer:
    wagers.to_excel(writer, sheet_name=SHEET_WAGERS, index=False)
    summary.to_excel(writer, sheet_name=SHEET_SUMMARY, index=False)

os.makedirs(WAGER_LOGS_ARCHIVE_DIR, exist_ok=True)
archive_file = os.path.join(
    WAGER_LOGS_ARCHIVE_DIR,
    f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_{BET_LOG_FILENAME}",
)
shutil.copy2(BET_LOG_FILE, archive_file)

print(f"Saved wager log: {BET_LOG_FILE}")
print(f"Archived wager log: {archive_file}")
print(f"Wagers imported: {len(wagers)}")
