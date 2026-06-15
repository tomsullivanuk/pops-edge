import os
import re
import pandas as pd
from datetime import datetime
from openpyxl.utils.dataframe import dataframe_to_rows

from config import (
    BET_LOG_FILE,
    COL_ACTION,
    COL_BUCKET,
    COL_CONTRACTS,
    COL_CURRENT_ACTION,
    COL_DATE,
    COL_EDGE,
    COL_ENTRY,
    COL_ENTRY_PRICE,
    COL_MARKET_TICKER,
    COL_MARKET_TICKER_TITLE,
    COL_MATCH,
    COL_OUTCOME,
    COL_POSITION,
    COL_SILVER,
    COL_STATUS,
    KALSHI_CURRENT_FILE,
    SHEET_BET_SHEET,
    SHEET_CANDIDATES,
    SHEET_DEFINITIONS,
    SHEET_KALSHI_NORMALIZED,
    SHEET_PORTFOLIO,
    SHEET_RUN_METADATA,
    SHEET_SILVER_FORECASTS,
    SHEET_SILVER_METADATA,
    SHEET_SILVER_NORMALIZED,
    SHEET_VALUE_BOARD,
    SHEET_WAGERS,
    SILVER_CURRENT_FILE,
    VALUE_BOARD_FILE,
)

SILVER_FILE = SILVER_CURRENT_FILE
KALSHI_FILE = KALSHI_CURRENT_FILE
OUTPUT_FILE = VALUE_BOARD_FILE

BANKROLL = 500
MIN_EDGE = 0.05
ACTIVE_STATUSES = ["Open", "Partially Closed"]

CODE_MAP = {
    "ALG": "DZA",
    "IRN": "IRI",
    "HAI": "HTI",
}

def normalize_code(code):
    code = str(code).strip().upper()
    return CODE_MAP.get(code, code)

def make_match_key(team, opponent):
    teams = sorted([team, opponent])
    return f"{teams[0]}-{teams[1]}"

def bucket(edge):
    if edge >= 0.10:
        return "A"
    if edge >= 0.07:
        return "B"
    if edge >= 0.05:
        return "C"
    return ""

def empty_portfolio_tables():
    open_positions = pd.DataFrame(columns=[
        "Match Date",
        COL_MATCH,
        COL_OUTCOME,
        "Team",
        COL_POSITION,
        COL_ACTION,
        COL_MARKET_TICKER_TITLE,
        COL_CONTRACTS,
        COL_ENTRY_PRICE,
        "Current Price",
        "Stake",
        "Current Value",
        "Unrealized P/L",
        "Value Change",
        COL_SILVER,
        COL_EDGE,
        COL_STATUS,
    ])
    exposure_by_team = pd.DataFrame(columns=[
        "Team",
        "Positions",
        COL_CONTRACTS,
        "Stake",
        "Current Value",
        "Unrealized P/L",
    ])
    exposure_by_match_date = pd.DataFrame(columns=[
        "Match Date",
        "Positions",
        COL_CONTRACTS,
        "Stake",
        "Current Value",
        "Unrealized P/L",
    ])
    summary = pd.DataFrame([
        ["Open Positions", 0],
        ["Total Contracts", 0],
        ["Total Stake", 0],
        ["Current Value", 0],
        ["Unrealized P/L", 0],
        ["BUY YES Positions", 0],
        ["SELL YES Positions", 0],
        ["Matches with Exposure", 0],
        ["Teams with Exposure", 0],
    ], columns=["Metric", "Value"])
    return summary, open_positions, exposure_by_team, exposure_by_match_date

def read_active_wagers():
    try:
        wager_log = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_WAGERS)
    except FileNotFoundError:
        return pd.DataFrame()

    required_columns = [
        COL_MARKET_TICKER_TITLE,
        COL_ACTION,
        COL_ENTRY_PRICE,
        COL_CONTRACTS,
        COL_STATUS,
    ]
    missing_columns = [col for col in required_columns if col not in wager_log.columns]
    if missing_columns:
        print(f"WARNING: Could not build portfolio; missing wager columns: {missing_columns}")
        return pd.DataFrame()

    return wager_log[wager_log[COL_STATUS].isin(ACTIVE_STATUSES)].copy()

def first_present(row, columns):
    for column in columns:
        if column in row.index and pd.notna(row[column]) and row[column] != "":
            return row[column]
    return ""

def build_portfolio_tables(active_wagers, value_board):
    if active_wagers.empty:
        return empty_portfolio_tables()

    optional_columns = ["Match Date", COL_MATCH, COL_OUTCOME]
    for column in optional_columns:
        if column not in active_wagers.columns:
            active_wagers[column] = pd.NA

    lookup = value_board[[
        "date",
        "game",
        "kalshi_outcome",
        "outcome_code",
        "silver_prob",
        "yes_bid",
        "yes_ask",
        COL_MARKET_TICKER,
    ]].copy()
    lookup = lookup.rename(columns={
        COL_MARKET_TICKER: COL_MARKET_TICKER_TITLE,
        "date": "Value Board Match Date",
        "game": "Value Board Match",
        "kalshi_outcome": "Value Board Outcome",
        "outcome_code": "Team",
        "silver_prob": COL_SILVER,
    })

    positions = active_wagers.merge(
        lookup,
        on=COL_MARKET_TICKER_TITLE,
        how="left",
    )

    rows = []
    for _, row in positions.iterrows():
        action = row[COL_ACTION]
        entry_price = pd.to_numeric(row[COL_ENTRY_PRICE], errors="coerce")
        contracts = pd.to_numeric(row[COL_CONTRACTS], errors="coerce")
        yes_bid = pd.to_numeric(row["yes_bid"], errors="coerce")
        yes_ask = pd.to_numeric(row["yes_ask"], errors="coerce")
        silver_prob = pd.to_numeric(row[COL_SILVER], errors="coerce")

        if action == "BUY YES":
            position = "Yes"
            stake = contracts * entry_price
            current_price = yes_bid
            current_value = contracts * current_price
            edge = silver_prob - yes_ask
            value_change = current_price - entry_price
        else:
            position = "No"
            stake = contracts * (1 - entry_price)
            current_price = yes_ask
            current_value = contracts * (1 - current_price)
            edge = yes_bid - silver_prob
            value_change = entry_price - current_price

        rows.append({
            "Match Date": first_present(row, ["Match Date", "Value Board Match Date"]),
            COL_MATCH: first_present(row, [COL_MATCH, "Value Board Match"]),
            COL_OUTCOME: first_present(row, [COL_OUTCOME, "Value Board Outcome"]),
            "Team": first_present(row, ["Team", COL_OUTCOME, "Value Board Outcome"]),
            COL_POSITION: position,
            COL_ACTION: action,
            COL_MARKET_TICKER_TITLE: row[COL_MARKET_TICKER_TITLE],
            COL_CONTRACTS: contracts,
            COL_ENTRY_PRICE: entry_price,
            "Current Price": current_price,
            "Stake": stake,
            "Current Value": current_value,
            "Unrealized P/L": current_value - stake,
            "Value Change": value_change,
            COL_SILVER: silver_prob,
            COL_EDGE: edge,
            COL_STATUS: row[COL_STATUS],
        })

    open_positions = pd.DataFrame(rows)
    money_columns = [
        COL_ENTRY_PRICE,
        "Current Price",
        "Stake",
        "Current Value",
        "Unrealized P/L",
        "Value Change",
        COL_SILVER,
        COL_EDGE,
    ]
    for column in money_columns:
        open_positions[column] = pd.to_numeric(open_positions[column], errors="coerce").round(4)

    summary = pd.DataFrame([
        ["Open Positions", len(open_positions)],
        ["Total Contracts", open_positions[COL_CONTRACTS].sum()],
        ["Total Stake", open_positions["Stake"].sum().round(2)],
        ["Current Value", open_positions["Current Value"].sum().round(2)],
        ["Unrealized P/L", open_positions["Unrealized P/L"].sum().round(2)],
        ["BUY YES Positions", (open_positions[COL_ACTION] == "BUY YES").sum()],
        ["SELL YES Positions", (open_positions[COL_ACTION] == "SELL YES").sum()],
        ["Matches with Exposure", open_positions[COL_MATCH].nunique()],
        ["Teams with Exposure", open_positions["Team"].nunique()],
    ], columns=["Metric", "Value"])

    exposure_by_team = summarize_exposure(open_positions, "Team")
    exposure_by_match_date = summarize_exposure(open_positions, "Match Date")

    return summary, open_positions, exposure_by_team, exposure_by_match_date

def summarize_exposure(open_positions, group_column):
    return (
        open_positions
        .groupby(group_column, dropna=False)
        .agg(
            Positions=(COL_MARKET_TICKER_TITLE, "count"),
            Contracts=(COL_CONTRACTS, "sum"),
            Stake=("Stake", "sum"),
            **{"Current Value": ("Current Value", "sum")},
            **{"Unrealized P/L": ("Unrealized P/L", "sum")},
        )
        .reset_index()
        .sort_values(group_column)
        .round(2)
    )

def write_portfolio_sheet(writer, summary, open_positions, exposure_by_team, exposure_by_match_date):
    worksheet = writer.book.create_sheet(SHEET_PORTFOLIO)
    sections = [
        ("Portfolio Summary", summary),
        ("Open Positions", open_positions),
        ("Exposure by Team", exposure_by_team),
        ("Exposure by Match Date", exposure_by_match_date),
    ]

    for title, frame in sections:
        worksheet.append([title])
        for row in dataframe_to_rows(frame, index=False, header=True):
            worksheet.append(row)
        worksheet.append([])

print("Loading files...")

silver = pd.read_excel(SILVER_FILE, sheet_name=SHEET_SILVER_FORECASTS)
silver_metadata = pd.read_excel(SILVER_FILE, sheet_name=SHEET_SILVER_METADATA)
kalshi = pd.read_excel(KALSHI_FILE)

# -----------------------------
# Normalize Silver
# -----------------------------

silver_rows = []

for _, row in silver.iterrows():
    team = normalize_code(row["Team"])
    opponent = normalize_code(row["Opponent"])
    match_key = make_match_key(team, opponent)

    silver_rows.append({
        "match_key": match_key,
        "date": row["Date"],
        "silver_team": team,
        "silver_opponent": opponent,
        "outcome_code": team,
        "silver_prob": row["Win"] / 100,
    })

    silver_rows.append({
        "match_key": match_key,
        "date": row["Date"],
        "silver_team": team,
        "silver_opponent": opponent,
        "outcome_code": "TIE",
        "silver_prob": row["Draw"] / 100,
    })

    silver_rows.append({
        "match_key": match_key,
        "date": row["Date"],
        "silver_team": team,
        "silver_opponent": opponent,
        "outcome_code": opponent,
        "silver_prob": row["OpponentWin"] / 100,
    })

silver_norm = pd.DataFrame(silver_rows)
print(f"Silver rows: {len(silver_norm)}")

# -----------------------------
# Normalize Kalshi
# -----------------------------

kalshi_rows = []

for _, row in kalshi.iterrows():
    event_ticker = str(row["event_ticker"])
    market_ticker = str(row["market_ticker"])

    match = re.search(r"([A-Z]{6})$", event_ticker)
    if not match:
        continue

    codes = match.group(1)
    team = normalize_code(codes[:3])
    opponent = normalize_code(codes[3:])
    match_key = make_match_key(team, opponent)

    outcome_code = normalize_code(market_ticker.split("-")[-1].upper())

    kalshi_rows.append({
        "match_key": match_key,
        "kalshi_team": team,
        "kalshi_opponent": opponent,
        "outcome_code": outcome_code,
        "game": row["game"],
        "market_title": row["market_title"],
        "kalshi_outcome": row["outcome"],
        "yes_bid": row["yes_bid_dollars"],
        "yes_ask": row["yes_ask_dollars"],
        "last_price": row["last_price_dollars"],
        "volume": row["volume_fp"],
        "open_interest": row["open_interest_fp"],
        "event_ticker": event_ticker,
        "market_ticker": market_ticker,
    })

kalshi_norm = pd.DataFrame(kalshi_rows)
print(f"Kalshi rows: {len(kalshi_norm)}")

# -----------------------------
# Merge
# -----------------------------

value_board = silver_norm.merge(
    kalshi_norm,
    on=["match_key", "outcome_code"],
    how="inner",
)

print(f"Merged rows: {len(value_board)}")

# -----------------------------
# Quality Checks
# -----------------------------

qc_status = "PASS"
qc_messages = []

if len(value_board) != len(kalshi_norm):
    qc_status = "FAIL"
    qc_messages.append(
        f"Row count mismatch: Kalshi rows={len(kalshi_norm)}, merged rows={len(value_board)}"
    )

if kalshi_norm["market_ticker"].nunique() != len(kalshi_norm):
    qc_status = "FAIL"
    qc_messages.append("Duplicate Kalshi market tickers detected.")

if silver_norm[["match_key", "outcome_code"]].drop_duplicates().shape[0] != len(silver_norm):
    qc_status = "FAIL"
    qc_messages.append("Duplicate Silver match/outcome combinations detected.")

if qc_status == "PASS":
    qc_messages.append("All quality checks passed.")

print()
print("Quality Checks")
for message in qc_messages:
    print(f"{qc_status}: {message}")

if qc_status == "FAIL":
    raise ValueError("Quality checks failed. Review row counts and duplicate keys.")

# -----------------------------
# Buy/Sell Calculations
# -----------------------------

value_board["buy_edge"] = value_board["silver_prob"] - value_board["yes_ask"]
value_board["buy_roi"] = value_board["buy_edge"] / value_board["yes_ask"]

value_board["sell_edge"] = value_board["yes_bid"] - value_board["silver_prob"]
value_board["sell_roi"] = value_board["sell_edge"] / (1 - value_board["yes_bid"])

# -----------------------------
# Build Bet Sheet Rows
# -----------------------------

bet_rows = []

for _, row in value_board.iterrows():

    if row["buy_edge"] >= MIN_EDGE:
        kelly = (row["silver_prob"] - row["yes_ask"]) / (1 - row["yes_ask"])
        half_kelly = max(kelly / 2, 0)

        bet_rows.append({
            COL_DATE: row["date"],
            COL_ACTION: "BUY YES",
            COL_MATCH: row["game"],
            COL_OUTCOME: row["kalshi_outcome"],
            COL_SILVER: row["silver_prob"],
            "Market Price": row["yes_ask"],
            "Yes Bid": row["yes_bid"],
            "Yes Ask": row["yes_ask"],
            COL_EDGE: row["buy_edge"],
            "ROI": row["buy_roi"],
            "EV per $100": row["buy_edge"] * 100,
            "Half Kelly": half_kelly,
            f"Stake on ${BANKROLL}": half_kelly * BANKROLL,
            COL_BUCKET: bucket(row["buy_edge"]),
            "Volume": row["volume"],
            "event_ticker": row["event_ticker"],
            COL_MARKET_TICKER: row["market_ticker"],
        })

    if row["sell_edge"] >= MIN_EDGE:
        kelly = (row["yes_bid"] - row["silver_prob"]) / row["yes_bid"]
        half_kelly = max(kelly / 2, 0)

        bet_rows.append({
            COL_DATE: row["date"],
            COL_ACTION: "SELL YES",
            COL_MATCH: row["game"],
            COL_OUTCOME: row["kalshi_outcome"],
            COL_SILVER: row["silver_prob"],
            "Market Price": row["yes_bid"],
            "Yes Bid": row["yes_bid"],
            "Yes Ask": row["yes_ask"],
            COL_EDGE: row["sell_edge"],
            "ROI": row["sell_roi"],
            "EV per $100": row["sell_edge"] * 100,
            "Half Kelly": half_kelly,
            f"Stake on ${BANKROLL}": half_kelly * BANKROLL,
            COL_BUCKET: bucket(row["sell_edge"]),
            "Volume": row["volume"],
            "event_ticker": row["event_ticker"],
            COL_MARKET_TICKER: row["market_ticker"],
        })

bet_sheet = pd.DataFrame(bet_rows)

if not bet_sheet.empty:
    bet_sheet = bet_sheet[
        (bet_sheet["Market Price"] >= 0.05)
        & (bet_sheet["Market Price"] <= 0.95)
        & (bet_sheet["Volume"] > 0)
    ].copy()

    bet_sheet = bet_sheet.sort_values(COL_EDGE, ascending=False)

    bet_sheet["ROI"] = bet_sheet["ROI"].round(2)
    bet_sheet["Half Kelly"] = bet_sheet["Half Kelly"].round(2)
    bet_sheet[f"Stake on ${BANKROLL}"] = bet_sheet[f"Stake on ${BANKROLL}"].round(2)

# -----------------------------
# Add Active Wager Exposure
# -----------------------------

if not bet_sheet.empty:
    try:
        active_wagers = read_active_wagers()

        if not active_wagers.empty:
            active_wagers = active_wagers[[
                COL_MARKET_TICKER_TITLE,
                COL_ACTION,
                COL_ENTRY_PRICE,
                COL_CONTRACTS,
                COL_STATUS,
            ]].copy()

            active_wagers["Stake"] = active_wagers.apply(
                lambda r:
                    r[COL_CONTRACTS] * r[COL_ENTRY_PRICE]
                    if r[COL_ACTION] == "BUY YES"
                    else r[COL_CONTRACTS] * (1 - r[COL_ENTRY_PRICE]),
                axis=1
            )

            active_wagers["Stake"] = active_wagers["Stake"].round(2)

            active_wagers = active_wagers.rename(columns={
                COL_MARKET_TICKER_TITLE: COL_MARKET_TICKER,
                COL_ACTION: COL_CURRENT_ACTION,
                COL_ENTRY_PRICE: COL_ENTRY,
                COL_STATUS: COL_STATUS,
            })

            active_wagers[COL_POSITION] = "Yes"

            bet_sheet = bet_sheet.merge(
                active_wagers[[
                    COL_MARKET_TICKER,
                    COL_POSITION,
                    COL_CURRENT_ACTION,
                    COL_ENTRY,
                    "Stake",
                    COL_STATUS,
                ]],
                on=COL_MARKET_TICKER,
                how="left"
            )

            bet_sheet[COL_POSITION] = bet_sheet[COL_POSITION].fillna("No")

            bet_sheet["Current Value Change"] = bet_sheet.apply(
                lambda r:
                    r["Market Price"] - r[COL_ENTRY]
                    if r[COL_POSITION] == "Yes" and r[COL_CURRENT_ACTION] == "BUY YES"
                    else (
                        r[COL_ENTRY] - r["Market Price"]
                        if r[COL_POSITION] == "Yes" and r[COL_CURRENT_ACTION] == "SELL YES"
                        else ""
                    ),
                axis=1
            )

        else:
            bet_sheet[COL_POSITION] = "No"
            bet_sheet[COL_CURRENT_ACTION] = ""
            bet_sheet[COL_ENTRY] = ""
            bet_sheet["Current Value Change"] = ""
            bet_sheet["Stake"] = ""
            bet_sheet[COL_STATUS] = ""

    except FileNotFoundError:
        bet_sheet[COL_POSITION] = "No"
        bet_sheet[COL_CURRENT_ACTION] = ""
        bet_sheet[COL_ENTRY] = ""
        bet_sheet["Current Value Change"] = ""
        bet_sheet["Stake"] = ""
        bet_sheet[COL_STATUS] = ""

    except Exception as e:
        print(f"WARNING: Could not add active wager exposure: {e}")
        bet_sheet[COL_POSITION] = "No"
        bet_sheet[COL_CURRENT_ACTION] = ""
        bet_sheet[COL_ENTRY] = ""
        bet_sheet["Current Value Change"] = ""
        bet_sheet["Stake"] = ""
        bet_sheet[COL_STATUS] = ""

candidates = bet_sheet.copy()

# -----------------------------
# Portfolio
# -----------------------------

portfolio_summary, portfolio_open_positions, exposure_by_team, exposure_by_match_date = build_portfolio_tables(
    read_active_wagers(),
    value_board,
)

# -----------------------------
# Definitions
# -----------------------------

definitions = pd.DataFrame([
    [COL_DATE, "Scheduled match date from Silver’s forecast file."],
    [COL_ACTION, "BUY YES means Silver is above Kalshi Ask. SELL YES means Kalshi Bid is above Silver."],
    [COL_MATCH, "The game being evaluated."],
    [COL_OUTCOME, "The Kalshi contract outcome: one team or Tie."],
    [COL_SILVER, "Silver model probability that this outcome happens."],
    ["Market Price", "For BUY YES, this is the Yes Ask. For SELL YES, this is the Yes Bid."],
    ["Yes Bid", "Current price at which you can sell a Yes contract."],
    ["Yes Ask", "Current price at which you can buy a Yes contract."],
    [COL_EDGE, "Difference between Silver and market price on the selected side."],
    ["ROI", "Expected return relative to capital at risk."],
    ["EV per $100", "Expected profit per $100 of contract exposure."],
    ["Half Kelly", "A conservative bankroll allocation fraction based on Kelly sizing, cut in half."],
    [f"Stake on ${BANKROLL}", "Half Kelly multiplied by the assumed bankroll. These stakes do not necessarily sum to the bankroll."],
    [COL_BUCKET, "A/B/C ranking based on edge size: A ≥ 10%, B ≥ 7%, C ≥ 5%."],
    ["Volume", "Kalshi trading volume for the contract."],
    [COL_POSITION, "Yes if there is an active open or partially closed wager on this contract."],
    [COL_CURRENT_ACTION, "The action of the existing wager from the Bet Log."],
    [COL_ENTRY, "Entry price of the existing wager."],
    ["Current Value Change", "For BUY YES, current market price minus entry. For SELL YES, entry minus current market price. Positive means the position moved in your favor."],
    ["Stake", "Approximate dollars at risk for the existing wager."],
    [COL_STATUS, "Open or partially closed status of the existing wager."],
], columns=["Field", "Plain-English Definition"])

# -----------------------------
# Run Metadata
# -----------------------------

run_metadata = pd.DataFrame([
    ["Value Board Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["QC Status", qc_status],
    ["QC Messages", " | ".join(qc_messages)],
    ["Silver Normalized Rows", len(silver_norm)],
    ["Kalshi Normalized Rows", len(kalshi_norm)],
    ["Merged Rows", len(value_board)],
    ["Candidate Bets", len(candidates)],
    ["Bet Sheet Rows", len(bet_sheet)],
    ["Minimum Edge", MIN_EDGE],
    ["Bankroll", BANKROLL],
], columns=["Field", "Value"])

run_metadata = pd.concat(
    [run_metadata, silver_metadata],
    ignore_index=True
)

# -----------------------------
# Save
# -----------------------------

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:

    bet_sheet.to_excel(writer, sheet_name=SHEET_BET_SHEET, index=False)
    run_metadata.to_excel(writer, sheet_name=SHEET_RUN_METADATA, index=False)
    candidates.to_excel(writer, sheet_name=SHEET_CANDIDATES, index=False)
    value_board.to_excel(writer, sheet_name=SHEET_VALUE_BOARD, index=False)
    write_portfolio_sheet(
        writer,
        portfolio_summary,
        portfolio_open_positions,
        exposure_by_team,
        exposure_by_match_date,
    )
    silver_norm.to_excel(writer, sheet_name=SHEET_SILVER_NORMALIZED, index=False)
    kalshi_norm.to_excel(writer, sheet_name=SHEET_KALSHI_NORMALIZED, index=False)
    definitions.to_excel(writer, sheet_name=SHEET_DEFINITIONS, index=False)

print()
print(f"Saved: {OUTPUT_FILE}")
print(f"Total rows: {len(value_board)}")
print(f"Candidate bets: {len(candidates)}")
print(f"Bet Sheet rows: {len(bet_sheet)}")
print(f"QC Status: {qc_status}")
