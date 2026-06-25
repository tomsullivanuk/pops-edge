# World Cup Betting System

## Purpose

This project identifies positive expected value betting opportunities in Kalshi World Cup markets by comparing Kalshi prices against Nate Silver's World Cup forecast model.

The system produces:

- A detailed Excel-based Value Board.
- A parallel Excel futures Value Board for advancement and title markets.
- A Portfolio worksheet summarizing active exposure.
- A sortable mobile-friendly web dashboard.
- A sortable futures web dashboard.
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
process_silver_futures.py
build_value_board.py
build_futures_value_board.py
build_web_betsheet.py
build_web_futures_betsheet.py
```

`update_worldcup.sh` refreshes Silver match and futures forecasts, Kalshi market data, both Value Boards, and both web dashboards.

It creates:

```text
Silver_Futures_Current.xlsx
WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.html
```

`build_futures_value_board.py` reads `Kalshi_Current.xlsx`, so the Kalshi workbook must include futures markets such as Round of 16 Qualifiers, Quarterfinals Qualifiers, Semifinals Qualifiers, and World Cup winner. The current match-board workflow is unchanged.

Both Excel boards and both HTML Value Boards are copied to the existing World Cup folder in iCloud Drive. The workflow opens the match HTML Value Board and creates/copies the futures HTML Value Board without opening a second browser window.

Wager imports can still be run separately:

```bash
./update_wagers.sh
```

`update_wagers.sh` refreshes the wager log from the latest Kalshi activity CSV, creates `World_Cup_Bet_Log.html`, and opens the web Bet Log.

To refresh everything in order:

```bash
./update_all.sh
```

`update_all.sh` refreshes wagers first, then refreshes the match and futures World Cup boards and dashboards by running:

```text
update_wagers.sh
update_worldcup.sh
```

After placing a wager:

1. Download Kalshi Activity -> All -> This Month.
2. Run `./update_all.sh` to refresh the Bet Log, match and futures Value Boards, and dashboards. On success it opens `World_Cup_Bet_Log.html`, `WorldCup_ValueBoard.html`, and `WorldCup_Futures_ValueBoard.html`.

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
WorldCup_ValueBoard.html
Silver_Futures_Current.xlsx
WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.html

World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.html

process_silver.py
process_silver_futures.py
kalshi_pull.py
build_value_board.py
build_futures_value_board.py
build_web_betsheet.py
build_web_futures_betsheet.py
build_web_betlog.py
import_wagers.py
update_all.sh
update_wagers.sh
update_worldcup.sh

archive/
    silver_raw/
    silver_processed/
    silver_futures_raw/
    silver_futures_processed/
    value_boards/
```

---

# Data Sources

## Nate Silver Forecast File

Source:

```text
Download from Silver's World Cup forecast page.
```

`process_silver.py` only considers CSVs with the required match columns. If a newer `data-*.csv` is a futures export, it skips that file and selects the newest valid match export.

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

## Nate Silver Futures File

The futures workflow uses a Silver CSV with:

```text
Team
R32
R16
Qtr
Semi
Final
Champ 🏆
3rd
```

`process_silver_futures.py` only considers CSVs with the required futures columns. If a newer `data-*.csv` is a match export, it skips that file and selects the newest valid futures export.

The processor normalizes team codes and converts percentage values to decimals. The futures board uses:

```text
R16 = reaches Round of 16
Qtr = reaches Quarterfinals
Semi = reaches Semifinals
Champ 🏆 = wins World Cup
```

Raw futures CSVs are archived under `archive/silver_futures_raw/`; processed workbooks are archived under `archive/silver_futures_processed/`.

---

# Futures Value Board

`WorldCup_Futures_ValueBoard.xlsx` compares Silver futures probabilities against Kalshi futures prices for:

```text
Round of 16 qualification
Quarterfinal qualification
Semifinal qualification
World Cup champion
```

The futures Bet Sheet uses the same BUY YES, SELL YES, edge, ROI, and bucket logic as the match board, but sizes new futures opportunities with Quarter Kelly. It also marks active futures wagers from the unified `World_Cup_Bet_Log.xlsx` when their status is `Open` or `Partially Closed`.

Important futures fields:

| Field | Description |
|---------|---------|
| Stage | Futures stage |
| Team | Normalized team code |
| champion_proxy_candidate | `YES` when R16, QF, SF, and Champion BUY edges are positive |
| strong_champion_proxy | `YES` when Champion BUY edge is at least 35% of average R16/QF/SF BUY edge |
| Action | BUY YES or SELL YES |
| Silver | Silver futures probability |
| Market Price | Relevant Kalshi price |
| Edge | Model edge |
| ROI | Expected return on capital |
| Quarter Kelly | Suggested Kelly fraction for futures |
| proxy_kelly_dollars | Advisory Champion proxy size in dollars |
| proxy_contracts | Champion contracts implied by Proxy Kelly |
| proxy_sell_ladder | Compact web display of the four resting sell orders |
| ladder_expected_return | Dollars returned if all proxy ladder orders fill |
| ladder_expected_profit | Ladder return minus Proxy Kelly dollars |
| Stake on $500 | Suggested position size |
| Bucket | A/B/C ranking |
| Volume | Market liquidity |
| event_ticker | Kalshi event ticker |
| market_ticker | Kalshi market ticker |

The futures HTML view omits `event_ticker` to stay compact, retains `market_ticker` for diagnostics, and displays `Position`, `Current Action`, `Entry Price`, `Current Value Change`, `Stake`, and `Status` for active futures wagers.

`champion_proxy_candidate` identifies teams whose staged advancement and Champion markets all have positive BUY edge. `strong_champion_proxy` applies the additional 35% relative-edge threshold. Final markets are normalized when available but are not part of either gate.

Proxy Kelly is shown only for Champion Proxy teams. It keeps the ordinary Champion Quarter Kelly stake and adds 60% of the R16/QF/SF Quarter Kelly stakes, reflecting that Champion is being used as a proxy for several correlated advancement bets.

Champion Proxy sell ladders use the Champion BUY price as entry, allocate Proxy Kelly into contracts, then suggest four resting sell orders at 1.5x, 2.25x, 3.25x, and 4.5x entry. Contract allocation is 30% / 30% / 20% / remainder.

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

The match Value Board calculates:

```text
Full Kelly
Half Kelly
```

The futures Value Board uses Quarter Kelly instead. Each board converts its Kelly fraction into a suggested stake using:

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

This applies to both match and futures Value Boards. Futures positions are matched by `market_ticker`; `Open` and `Partially Closed` wagers are considered active.

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
Market Type
Stage
Team
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

One unified Bet Log tracks both match and futures wagers. `Market Type` is
`Match` or `Futures`. Futures rows use `Stage` and `Team`, keep `Match` and
`Match Date` blank, and show the human-readable YES proposition in `Outcome`.
Match rows retain the existing match fields; `Team` identifies the normalized
YES proposition team and remains blank for tie contracts.

and closing line value fields:

```text
Closing Price
CLV
CLV %
```

Closing Price is manually entered in `World_Cup_Bet_Log.xlsx`. `update_wagers.sh` runs `import_wagers.py`, which preserves that manually entered Closing Price and automatically calculates CLV and CLV % when Closing Price is present.

`import_wagers.py` normalizes Match Date values to `YYYY-MM-DD` whenever possible. It preserves prior manual corrections first, then uses the current match Value Board date, then falls back to parsing the market ticker. Enrichment combines `WorldCup_ValueBoard.xlsx` and `WorldCup_Futures_ValueBoard.xlsx`; `Kalshi_Current.xlsx` supplies a fallback proposition name for futures tickers whose suffix does not encode a three-letter team code.

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
