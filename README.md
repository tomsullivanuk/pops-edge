# World Cup Betting System

## Purpose

This project identifies positive expected value betting opportunities in Kalshi World Cup markets by comparing Kalshi prices against Nate Silver's World Cup forecast model.

The system produces:

- A detailed Excel-based Value Board.
- A Portfolio worksheet summarizing active exposure.
- A sortable mobile-friendly web dashboard.
- A sortable web wager log.
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

`wcup` refreshes Silver, Kalshi, the Value Board, and the web dashboard. It runs the same workflow as `update_worldcup.sh`:

```text
process_silver.py
kalshi_pull.py
build_value_board.py
build_web_betsheet.py
```

`update_worldcup.sh` refreshes Silver forecasts, Kalshi market data, the Value Board, and the web dashboard.

Wager imports can still be run separately:

```bash
./update_wagers.sh
```

`update_wagers.sh` refreshes the wager log from the latest Kalshi activity CSV, creates `World_Cup_Bet_Log.html`, and opens the web Bet Log.

To refresh everything in order:

```bash
./update_all.sh
```

`update_all.sh` refreshes wagers first, then refreshes the World Cup board and dashboard by running:

```text
update_wagers.sh
update_worldcup.sh
```

After placing a wager:

1. Download Kalshi Activity -> All -> This Month.
2. Run `./update_all.sh` to refresh the Bet Log, Value Board, and dashboard.

You can still run `./update_wagers.sh` by itself when only the Bet Log needs updating, or `./update_worldcup.sh` by itself when only the Silver/Kalshi/Value Board/dashboard workflow needs updating.

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
World_Cup_Bet_Log.html

process_silver.py
kalshi_pull.py
build_value_board.py
build_web_betsheet.py
build_web_betlog.py
import_wagers.py
update_all.sh
update_wagers.sh
update_worldcup.sh

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

# Portfolio Worksheet

`WorldCup_ValueBoard.xlsx` includes a `Portfolio` worksheet built from active rows in:

```text
World_Cup_Bet_Log.xlsx
```

and current prices from the merged Value Board data.

The worksheet contains:

```text
Portfolio Summary
Open Positions
Exposure by Team
Exposure by Match Date
```

Open positions include wagers with:

```text
Status = Open
Status = Partially Closed
```

For BUY YES positions, current value uses the current Yes Bid. For SELL YES positions, current value uses the value of the opposing No position based on the current Yes Ask.

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
Date Placed
Match Date
Match
Outcome
Action
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

and closing line value fields:

```text
Closing Price
CLV
CLV %
```

Closing Price is manually entered in `World_Cup_Bet_Log.xlsx`. `update_wagers.sh` runs `import_wagers.py`, which preserves that manually entered Closing Price and automatically calculates CLV and CLV % when Closing Price is present.

`import_wagers.py` normalizes Match Date values to `YYYY-MM-DD` whenever possible. It preserves prior manual corrections first, then uses the current Value Board date, then falls back to parsing the market ticker.

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

If Closing Price is blank, CLV and CLV % remain blank unless prior manually entered CLV values exist, in which case they are preserved as a fallback.

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

The web Bet Log is generated from:

```bash
python build_web_betlog.py
```

It creates `World_Cup_Bet_Log.html` with sortable columns and blank display for missing values. `./update_wagers.sh` builds it automatically after importing wagers.

---

# Future Enhancements

Potential improvements:

1. Archive wager logs automatically.
2. Recover model data from archived Value Boards.
3. Automatic Closing Price capture.
4. Position-level performance analytics.
5. Silver model calibration reporting.
