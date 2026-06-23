import os


PROJECT_DIR = os.path.expanduser("~/kalshi")
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

SILVER_CURRENT_FILE = "Silver_Current.xlsx"
KALSHI_CURRENT_FILE = "Kalshi_Current.xlsx"
VALUE_BOARD_FILE = "WorldCup_ValueBoard.xlsx"
SILVER_FUTURES_CURRENT_FILE = "Silver_Futures_Current.xlsx"
FUTURES_VALUE_BOARD_FILE = "WorldCup_Futures_ValueBoard.xlsx"
BET_LOG_FILE = "World_Cup_Bet_Log.xlsx"
WEB_BETSHEET_FILE = "WorldCup_BetSheet.html"
WEB_FUTURES_BETSHEET_FILE = "WorldCup_Futures_BetSheet.html"
WEB_BETLOG_FILE = "World_Cup_Bet_Log.html"

SILVER_RAW_ARCHIVE_DIR = os.path.join(PROJECT_DIR, "archive", "silver_raw")
SILVER_PROCESSED_ARCHIVE_DIR = os.path.join(PROJECT_DIR, "archive", "silver_processed")
SILVER_FUTURES_RAW_ARCHIVE_DIR = os.path.join(PROJECT_DIR, "archive", "silver_futures_raw")
SILVER_FUTURES_PROCESSED_ARCHIVE_DIR = os.path.join(PROJECT_DIR, "archive", "silver_futures_processed")
SILVER_RUN_ARCHIVE_DIR = os.path.join("archive", "silver")
KALSHI_RUN_ARCHIVE_DIR = os.path.join("archive", "kalshi")
VALUE_BOARDS_RUN_ARCHIVE_DIR = os.path.join("archive", "value_boards")
WAGER_LOGS_ARCHIVE_DIR = os.path.join(PROJECT_DIR, "archive", "wager_logs")

SHEET_SILVER_FORECASTS = "Silver Forecasts"
SHEET_SILVER_FUTURES = "Silver Futures"
SHEET_SILVER_METADATA = "Silver Metadata"
SHEET_BET_SHEET = "Bet Sheet"
SHEET_RUN_METADATA = "Run Metadata"
SHEET_CANDIDATES = "Candidates"
SHEET_VALUE_BOARD = "Value Board"
SHEET_PORTFOLIO = "Portfolio"
SHEET_SILVER_NORMALIZED = "Silver Normalized"
SHEET_KALSHI_NORMALIZED = "Kalshi Normalized"
SHEET_DEFINITIONS = "Definitions"
SHEET_WAGERS = "Wagers"
SHEET_SUMMARY = "Summary"

COL_DATE = "Date"
COL_MATCH = "Match"
COL_OUTCOME = "Outcome"
COL_ACTION = "Action"
COL_SILVER = "Silver"
COL_SILVER_PROBABILITY = "Silver Probability"
COL_EDGE = "Edge"
COL_BUCKET = "Bucket"
COL_STATUS = "Status"
COL_MARKET_TICKER = "market_ticker"
COL_MARKET_TICKER_TITLE = "Market Ticker"
COL_MATCH_DATE = "Match Date"
COL_CLOSING_PRICE = "Closing Price"
COL_CLV = "CLV"
COL_CLV_PCT = "CLV %"
COL_POSITION = "Position"
COL_CURRENT_ACTION = "Current Action"
COL_ENTRY = "Entry"
COL_ENTRY_PRICE = "Entry Price"
COL_CONTRACTS = "Contracts"
