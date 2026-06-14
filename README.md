# World Cup Betting System

## Purpose

This project identifies positive expected value betting opportunities in Kalshi World Cup markets by comparing Kalshi prices against Nate Silver's World Cup forecast model.

The system produces:

- A detailed Excel-based Value Board.
- A sortable mobile-friendly web dashboard.
- A wager log generated from Kalshi trading activity.
- Position monitoring for active wagers.
- Historical archives of Silver forecast files and Value Boards.

---

# Workflow

The main board workflow is:

1. Download the latest Nate Silver forecast data.
2. Pull current Kalshi market data.
3. Build the Value Board.
4. Generate the web dashboard.

Typical execution:

```bash
wcup
```

`wcup` refreshes Silver, Kalshi, the Value Board, and the web dashboard. It runs:

```text
process_silver.py
kalshi_pull.py
build_value_board.py
build_web_betsheet.py
```

Wager imports are intentionally run separately:

```bash
./update_wagers.sh
```

`update_wagers.sh` refreshes the wager log from the latest Kalshi activity CSV and opens `World_Cup_Bet_Log.xlsx`.

After placing a wager:

1. Download Kalshi Activity -> All -> This Month.
2. Run `./update_wagers.sh`.
3. Run `wcup` if you want the wager reflected on the Value Board.

Optional shell shortcut:

```bash
alias wagers='cd ~/kalshi && ./update_wagers.sh'
```

---

# Directory Structure

```text
kalshi/

Silver_Current.xlsx
Kalshi_Current.xlsx

WorldCup_ValueBoard.xlsx
WorldCup_BetSheet.html

World_Cup_Bet_Log.xlsx

process_silver.py
kalshi_pull.py
build_value_board.py
build_web_betsheet.py
import_wagers.py
update_wagers.sh

archive/
    silver_raw/
    silver_processed/
    value_boards/
```

---

# Data Sources

## Nate Silver Forecast File

Source:

```text
Download from Silver's World Cup forecast page.
```

Used fields:

```text
Date
Team
Opponent
Win
Draw
OpponentWin
```

The file is normalized into:

```text
Team Win
Draw
Opponent Win
```

for each match.

---

## Kalshi Market Data

Pulled automatically.

Used fields:

```text
event_ticker
market_ticker
yes_bid_dollars
yes_ask_dollars
volume_fp
```

Each Kalshi outcome is matched to the corresponding Silver forecast probability.

---

# Value Board Logic

The Value Board compares:

```text
Silver Probability
vs
Kalshi Market Price
```

and evaluates both:

```text
BUY YES
SELL YES
```

opportunities.

---

## BUY YES

Triggered when:

```text
Silver Probability > Kalshi Yes Ask
```

Edge:

```text
Silver - Yes Ask
```

---

## SELL YES

Triggered when:

```text
Kalshi Yes Bid > Silver Probability
```

Edge:

```text
Yes Bid - Silver
```

---

## Buckets

```text
A = Edge >= 10%
B = Edge >= 7%
C = Edge >= 5%
```

Only opportunities with:

```text
Edge >= 5%
```

appear on the Bet Sheet.

---

# Kelly Sizing

The system calculates:

```text
Full Kelly
Half Kelly
```

and converts Half Kelly into a suggested stake using:

```text
BANKROLL = $500
```

Current stake values are informational only.

They are not automatically constrained to sum to the bankroll.

---

# Bet Sheet

The Bet Sheet is the primary decision-making view.

Important fields:

| Field | Description |
|---------|---------|
| Action | BUY YES or SELL YES |
| Match | Match name |
| Outcome | Contract outcome |
| Silver | Silver probability |
| Market Price | Relevant Kalshi price |
| Edge | Model edge |
| ROI | Expected return on capital |
| Half Kelly | Suggested Kelly fraction |
| Stake on $500 | Suggested position size |
| Bucket | A/B/C ranking |
| Volume | Market liquidity |

---

# Active Position Tracking

The Bet Sheet also incorporates active positions from:

```text
World_Cup_Bet_Log.xlsx
```

Open positions are displayed using:

| Field | Description |
|---------|---------|
| Position | Yes/No |
| Current Action | Existing BUY YES or SELL YES |
| Entry | Original entry price |
| Current Value Change | Unrealized gain/loss in price terms |
| Stake | Approximate dollars at risk |
| Status | Open or Partially Closed |

---

# Current Value Change

For BUY YES positions:

```text
Current Market Price - Entry Price
```

For SELL YES positions:

```text
Entry Price - Current Market Price
```

Positive values indicate the market has moved in favor of the position.

---

# Wager Log

Generated from:

```text
Kalshi-Recent-Activity-All.csv
```

using:

```bash
./update_wagers.sh
```

The wager log tracks:

```text
Entry Price
Exit Price
Contracts
Fees
Status
Realized P/L
```

along with model metadata:

```text
Silver Probability
Edge
Bucket
```

and user-maintained fields:

```text
Closing Price
CLV
CLV %
```

---

# Closing Line Value (CLV)

For BUY YES:

```text
CLV = Closing Price - Entry Price
```

For SELL YES:

```text
CLV = Entry Price - Closing Price
```

Positive CLV indicates the position beat the market.

---

# Quality Checks

The Value Board performs validation before publishing.

Checks include:

```text
Silver row counts
Kalshi row counts
Merged row counts
Duplicate outcome detection
Duplicate market ticker detection
```

The build fails if validation fails.

---

# Mobile Dashboard

The HTML dashboard is generated from:

```bash
python build_web_betsheet.py
```

Features:

```text
Sortable columns
Compact mobile layout
iPad-friendly viewing
Active position visibility
Blank values displayed as empty fields
```

The dashboard is intended to be the primary interface during live matches.

---

# Future Enhancements

Potential improvements:

1. Archive wager logs automatically.
2. Recover model data from archived Value Boards.
3. Automatic Closing Price capture.
4. Automatic CLV calculation.
5. Position-level performance analytics.
6. Silver model calibration reporting.
7. Portfolio-level exposure reporting.
