import os
import runpy
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class PipelineTests(unittest.TestCase):
    def test_process_silver_builds_clean_workbook_from_sample_csv(self):
        with TemporaryDirectory() as home:
            project_dir = Path(home) / "kalshi"
            downloads_dir = Path(home) / "Downloads"
            project_dir.mkdir()
            downloads_dir.mkdir()
            shutil.copy2(FIXTURES / "sample_silver.csv", downloads_dir / "data-sample.csv")

            with patched_environ(HOME=home):
                run_pipeline_script(ROOT / "process_silver.py")

            output = project_dir / "Silver_Current.xlsx"
            self.assertTrue(output.exists())

            forecasts = pd.read_excel(output, sheet_name="Silver Forecasts")
            metadata = pd.read_excel(output, sheet_name="Silver Metadata")

            self.assertEqual(len(forecasts), 2)
            self.assertEqual(forecasts["Team"].tolist(), ["USA", "CAN"])
            self.assertEqual(forecasts["Opponent"].tolist(), ["MEX", "BRA"])
            self.assertEqual(metadata.loc[metadata["Field"] == "Silver Rows Output", "Value"].iloc[0], 2)
            self.assertTrue((project_dir / "archive" / "silver_processed").exists())

    def test_build_value_board_uses_sample_silver_kalshi_and_active_wager_files(self):
        with TemporaryDirectory() as workspace:
            workspace = Path(workspace)
            write_sample_silver_workbook(workspace / "Silver_Current.xlsx")
            write_sample_kalshi_workbook(workspace / "Kalshi_Current.xlsx")
            write_sample_wager_log(workspace / "World_Cup_Bet_Log.xlsx")

            with changed_dir(workspace):
                run_pipeline_script(ROOT / "build_value_board.py")

            output = workspace / "WorldCup_ValueBoard.xlsx"
            self.assertTrue(output.exists())

            bet_sheet = pd.read_excel(output, sheet_name="Bet Sheet")
            metadata = pd.read_excel(output, sheet_name="Run Metadata")
            value_board = pd.read_excel(output, sheet_name="Value Board")
            portfolio_sections = read_portfolio_sections(output)

            self.assertEqual(len(value_board), 3)
            self.assertEqual(metadata.loc[metadata["Field"] == "QC Status", "Value"].iloc[0], "PASS")

            usa = bet_sheet[bet_sheet["market_ticker"] == "KXWCGAME-26JUN13-USAMEX-USA"].iloc[0]
            self.assertEqual(usa["Action"], "BUY YES")
            self.assertEqual(usa["Bucket"], "A")
            self.assertAlmostEqual(usa["Edge"], 0.11)
            self.assertEqual(usa["Position"], "Yes")
            self.assertEqual(usa["Current Action"], "BUY YES")
            self.assertAlmostEqual(usa["Entry"], 0.45)
            self.assertAlmostEqual(usa["Current Value Change"], 0.04)

            mex = bet_sheet[bet_sheet["market_ticker"] == "KXWCGAME-26JUN13-USAMEX-MEX"].iloc[0]
            self.assertEqual(mex["Action"], "SELL YES")
            self.assertEqual(mex["Position"], "No")

            self.assertEqual(
                set(portfolio_sections),
                {
                    "Portfolio Summary",
                    "Open Positions",
                    "Exposure by Team",
                    "Exposure by Match Date",
                },
            )

            portfolio_summary = frame_for_section(portfolio_sections["Portfolio Summary"])
            open_positions = frame_for_section(portfolio_sections["Open Positions"])
            exposure_by_team = frame_for_section(portfolio_sections["Exposure by Team"])
            exposure_by_match_date = frame_for_section(portfolio_sections["Exposure by Match Date"])

            self.assertEqual(portfolio_summary.loc["Open Positions", "Value"], 1)
            self.assertAlmostEqual(portfolio_summary.loc["Total Stake", "Value"], 9.00)
            self.assertAlmostEqual(portfolio_summary.loc["Current Value", "Value"], 9.60)
            self.assertAlmostEqual(portfolio_summary.loc["Unrealized P/L", "Value"], 0.60)

            open_positions = open_positions.reset_index().set_index("Market Ticker")
            usa_position = open_positions.loc["KXWCGAME-26JUN13-USAMEX-USA"]
            self.assertEqual(usa_position["Match Date"], "2026-06-13")
            self.assertEqual(usa_position["Match"], "USA vs Mexico")
            self.assertEqual(usa_position["Outcome"], "United States")
            self.assertEqual(usa_position["Team"], "USA")
            self.assertEqual(usa_position["Position"], "Yes")
            self.assertAlmostEqual(usa_position["Current Price"], 0.48)
            self.assertAlmostEqual(usa_position["Stake"], 9.00)
            self.assertAlmostEqual(usa_position["Current Value"], 9.60)
            self.assertAlmostEqual(usa_position["Unrealized P/L"], 0.60)

            self.assertAlmostEqual(exposure_by_team.loc["USA", "Stake"], 9.00)
            self.assertAlmostEqual(exposure_by_match_date.loc["2026-06-13", "Current Value"], 9.60)

    def test_import_wagers_uses_sample_activity_and_value_board_lookup(self):
        with TemporaryDirectory() as home:
            project_dir = Path(home) / "kalshi"
            project_dir.mkdir()
            shutil.copy2(
                FIXTURES / "sample_kalshi_activity.csv",
                project_dir / "Kalshi-Recent-Activity-All-sample.csv",
            )
            write_sample_value_board_lookup(project_dir / "WorldCup_ValueBoard.xlsx")

            with patched_environ(HOME=home):
                run_pipeline_script(ROOT / "import_wagers.py")

            output = project_dir / "World_Cup_Bet_Log.xlsx"
            self.assertTrue(output.exists())

            wagers = pd.read_excel(output, sheet_name="Wagers")
            summary = pd.read_excel(output, sheet_name="Summary")

            self.assertEqual(len(wagers), 3)
            self.assertEqual(summary.loc[summary["Metric"] == "Total Wagers", "Value"].iloc[0], 3)
            self.assertEqual(len(wager_log_archives(project_dir)), 1)

            usa = wagers[wagers["Market Ticker"] == "KXWCGAME-26JUN13-USAMEX-USA"].iloc[0]
            self.assertEqual(usa["Action"], "BUY YES")
            self.assertEqual(usa["Status"], "Open")
            self.assertEqual(usa["Match"], "USA vs Mexico")
            self.assertEqual(usa["Outcome"], "United States")
            self.assertAlmostEqual(usa["Entry Price"], 0.45)

            mex = wagers[wagers["Market Ticker"] == "KXWCGAME-26JUN13-USAMEX-MEX"].iloc[0]
            self.assertEqual(mex["Action"], "SELL YES")
            self.assertEqual(mex["Status"], "Partially Closed")
            self.assertAlmostEqual(mex["Exit Price"], 0.30)

            bra = wagers[wagers["Market Ticker"] == "KXWCGAME-26JUN14-CANBRA-BRA"].iloc[0]
            self.assertEqual(bra["Status"], "Settled")
            self.assertEqual(bra["Contract Won"], "Yes")
            self.assertAlmostEqual(bra["Realized P/L"], 2.20)

    def test_import_wagers_covers_exits_settlements_multiple_fills_and_fallbacks(self):
        with TemporaryDirectory() as home:
            project_dir = Path(home) / "kalshi"
            project_dir.mkdir()

            activity = pd.DataFrame(
                [
                    trade("2026-06-01 09:00:00", "Yes", "KXWCGAME-26JUL01-AAAEEE-AAA", 10, 40, 0.10),
                    trade("2026-06-01 10:00:00", "No", "KXWCGAME-26JUL01-AAAEEE-AAA", 10, 55, 0.05),
                    trade("2026-06-02 09:00:00", "Yes", "KXWCGAME-26JUL02-BBBFFF-BBB", 8, 35, 0.08),
                    settlement("2026-07-03 18:00:00", "KXWCGAME-26JUL02-BBBFFF-BBB", "no"),
                    trade("2026-06-03 09:00:00", "No", "KXWCGAME-26JUL03-CCCGGG-CCC", 12, 62, 0.12),
                    settlement("2026-07-04 18:00:00", "KXWCGAME-26JUL03-CCCGGG-CCC", "no"),
                    trade("2026-06-04 09:00:00", "Yes", "KXWCGAME-26JUL04-DDDHHH-DDD", 10, 40, 0.10),
                    trade("2026-06-04 09:05:00", "Yes", "KXWCGAME-26JUL04-DDDHHH-DDD", 30, 50, 0.30),
                    trade("2026-06-05 09:00:00", "Yes", "KXWCGAME-26AUG05-IIIJJJ-III", 5, 25, 0.05),
                    trade("2026-06-06 09:00:00", "Yes", "KXWCGAME-26SEP06-KKKLLL-KKK", 7, 45, 0.07),
                ]
            )
            activity.to_csv(project_dir / "Kalshi-Recent-Activity-All-expanded.csv", index=False)

            write_expanded_value_board_lookup(project_dir / "WorldCup_ValueBoard.xlsx")
            write_prior_wager_log_for_preservation(project_dir / "World_Cup_Bet_Log.xlsx")

            with patched_environ(HOME=home):
                run_pipeline_script(ROOT / "import_wagers.py")

            output = project_dir / "World_Cup_Bet_Log.xlsx"
            wagers = pd.read_excel(output, sheet_name="Wagers")
            summary = pd.read_excel(output, sheet_name="Summary")

            self.assertEqual(len(wagers), 6)
            self.assertEqual(summary.loc[summary["Metric"] == "Total Wagers", "Value"].iloc[0], 6)
            self.assertEqual(summary.loc[summary["Metric"] == "Closed Early", "Value"].iloc[0], 1)
            self.assertEqual(summary.loc[summary["Metric"] == "Settled", "Value"].iloc[0], 2)
            self.assertEqual(summary.loc[summary["Metric"] == "Open", "Value"].iloc[0], 3)
            self.assertEqual(len(wager_log_archives(project_dir)), 1)

            closed = row_for(wagers, "KXWCGAME-26JUL01-AAAEEE-AAA")
            self.assertEqual(closed["Action"], "BUY YES")
            self.assertEqual(closed["Status"], "Closed Early")
            self.assertAlmostEqual(closed["Entry Price"], 0.40)
            self.assertAlmostEqual(closed["Exit Price"], 0.55)
            self.assertAlmostEqual(closed["Realized P/L"], 1.35)

            losing_buy = row_for(wagers, "KXWCGAME-26JUL02-BBBFFF-BBB")
            self.assertEqual(losing_buy["Action"], "BUY YES")
            self.assertEqual(losing_buy["Status"], "Settled")
            self.assertEqual(losing_buy["Market Result"], "no")
            self.assertEqual(losing_buy["Contract Won"], "No")
            self.assertAlmostEqual(losing_buy["Realized P/L"], -2.88)

            winning_sell = row_for(wagers, "KXWCGAME-26JUL03-CCCGGG-CCC")
            self.assertEqual(winning_sell["Action"], "SELL YES")
            self.assertEqual(winning_sell["Status"], "Settled")
            self.assertEqual(winning_sell["Market Result"], "no")
            self.assertEqual(winning_sell["Contract Won"], "Yes")
            self.assertAlmostEqual(winning_sell["Realized P/L"], 7.32)

            multiple_fill = row_for(wagers, "KXWCGAME-26JUL04-DDDHHH-DDD")
            self.assertEqual(multiple_fill["Action"], "BUY YES")
            self.assertEqual(multiple_fill["Status"], "Open")
            self.assertAlmostEqual(multiple_fill["Contracts"], 40)
            self.assertAlmostEqual(multiple_fill["Entry Price"], 0.475)
            self.assertAlmostEqual(multiple_fill["Fee In"], 0.40)

            preserved = row_for(wagers, "KXWCGAME-26AUG05-IIIJJJ-III")
            self.assertEqual(preserved["Match Date"], "2026-08-05")
            self.assertEqual(preserved["Match"], "Prior Match")
            self.assertEqual(preserved["Outcome"], "Prior Outcome")
            self.assertAlmostEqual(preserved["Silver Probability"], 0.42)
            self.assertAlmostEqual(preserved["Edge"], 0.08)
            self.assertEqual(preserved["Bucket"], "B")
            self.assertAlmostEqual(preserved["Closing Price"], 0.64)
            self.assertAlmostEqual(preserved["CLV"], 0.14)
            self.assertAlmostEqual(preserved["CLV %"], 0.28)

            fallback = row_for(wagers, "KXWCGAME-26SEP06-KKKLLL-KKK")
            self.assertEqual(fallback["Match Date"], "2026-09-06")
            self.assertTrue(pd.isna(fallback["Match"]))
            self.assertTrue(pd.isna(fallback["Outcome"]))


class changed_dir:
    def __init__(self, path):
        self.path = path
        self.previous = None

    def __enter__(self):
        self.previous = Path.cwd()
        os.chdir(self.path)

    def __exit__(self, exc_type, exc, tb):
        os.chdir(self.previous)


class patched_environ:
    def __init__(self, **updates):
        self.updates = updates
        self.previous = {}

    def __enter__(self):
        for key, value in self.updates.items():
            self.previous[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, exc_type, exc, tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_pipeline_script(path):
    sys.modules.pop("config", None)
    runpy.run_path(str(path), run_name="__main__")


def write_sample_silver_workbook(path):
    forecasts = pd.DataFrame(
        [
            {
                "Date": "2026-06-13",
                "Team": "USA",
                "Win": 60,
                "GF": 1.8,
                "Opponent": "MEX",
                "OpponentWin": 15,
                "OpponentGF": 0.9,
                "Draw": 25,
                "MostLikelyScore": "1-0",
            }
        ]
    )
    metadata = pd.DataFrame(
        [["Silver Source File", "sample_silver.csv"], ["Silver Rows Output", 1]],
        columns=["Field", "Value"],
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        forecasts.to_excel(writer, sheet_name="Silver Forecasts", index=False)
        metadata.to_excel(writer, sheet_name="Silver Metadata", index=False)


def write_sample_kalshi_workbook(path):
    pd.read_csv(FIXTURES / "sample_kalshi_current.csv").to_excel(path, index=False)


def write_sample_wager_log(path):
    wagers = pd.DataFrame(
        [
            {
                "Market Ticker": "KXWCGAME-26JUN13-USAMEX-USA",
                "Action": "BUY YES",
                "Entry Price": 0.45,
                "Contracts": 20,
                "Status": "Open",
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        wagers.to_excel(writer, sheet_name="Wagers", index=False)


def write_sample_value_board_lookup(path):
    bet_sheet = pd.DataFrame(
        [
            {
                "Date": "2026-06-13",
                "Match": "USA vs Mexico",
                "Outcome": "United States",
                "Action": "BUY YES",
                "Silver": 0.60,
                "Edge": 0.10,
                "Bucket": "A",
                "market_ticker": "KXWCGAME-26JUN13-USAMEX-USA",
            },
            {
                "Date": "2026-06-13",
                "Match": "USA vs Mexico",
                "Outcome": "Mexico",
                "Action": "SELL YES",
                "Silver": 0.15,
                "Edge": 0.10,
                "Bucket": "A",
                "market_ticker": "KXWCGAME-26JUN13-USAMEX-MEX",
            },
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        bet_sheet.to_excel(writer, sheet_name="Bet Sheet", index=False)


def trade(date, direction, market_ticker, amount, price_cents, fee):
    return {
        "type": "Trade",
        "Original_Date": date,
        "Direction": direction,
        "Market_Ticker": market_ticker,
        "Amount_In_Dollars": amount,
        "Price_In_Cents": price_cents,
        "Fee_In_Dollars": fee,
        "Result": "",
    }


def settlement(date, market_ticker, result):
    return {
        "type": "Settlement",
        "Original_Date": date,
        "Direction": "",
        "Market_Ticker": market_ticker,
        "Amount_In_Dollars": 0,
        "Price_In_Cents": 0,
        "Fee_In_Dollars": 0,
        "Result": result,
    }


def row_for(wagers, market_ticker):
    return wagers[wagers["Market Ticker"] == market_ticker].iloc[0]


def read_portfolio_sections(path):
    workbook = load_workbook(path, data_only=True)
    worksheet = workbook["Portfolio"]
    sections = {}
    current_title = None
    current_rows = []

    for values in worksheet.iter_rows(values_only=True):
        row = list(values)
        if all(value is None for value in row):
            if current_title is not None:
                sections[current_title] = current_rows
                current_title = None
                current_rows = []
            continue

        first_cell = row[0]
        if current_title is None:
            current_title = first_cell
            current_rows = []
        else:
            current_rows.append(row)

    if current_title is not None:
        sections[current_title] = current_rows

    return sections


def frame_for_section(rows):
    header = rows[0]
    body = rows[1:]
    frame = pd.DataFrame(body, columns=header).dropna(how="all")
    index_column = header[0]
    return frame.set_index(index_column)


def wager_log_archives(project_dir):
    return list((project_dir / "archive" / "wager_logs").glob("*_World_Cup_Bet_Log.xlsx"))


def write_expanded_value_board_lookup(path):
    bet_sheet = pd.DataFrame(
        [
            lookup_row("KXWCGAME-26JUL01-AAAEEE-AAA", "2026-07-01", "AAA vs EEE", "AAA", "BUY YES", 0.58, 0.08, "B"),
            lookup_row("KXWCGAME-26JUL02-BBBFFF-BBB", "2026-07-02", "BBB vs FFF", "BBB", "BUY YES", 0.48, 0.06, "C"),
            lookup_row("KXWCGAME-26JUL03-CCCGGG-CCC", "2026-07-03", "CCC vs GGG", "CCC", "SELL YES", 0.38, 0.12, "A"),
            lookup_row("KXWCGAME-26JUL04-DDDHHH-DDD", "2026-07-04", "DDD vs HHH", "DDD", "BUY YES", 0.55, 0.07, "B"),
            lookup_row("KXWCGAME-26AUG05-IIIJJJ-III", "2026-08-05", "Current Match", "Current Outcome", "BUY YES", 0.99, 0.01, "C"),
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        bet_sheet.to_excel(writer, sheet_name="Bet Sheet", index=False)


def lookup_row(market_ticker, date, match, outcome, action, silver, edge, bucket):
    return {
        "Date": date,
        "Match": match,
        "Outcome": outcome,
        "Action": action,
        "Silver": silver,
        "Edge": edge,
        "Bucket": bucket,
        "market_ticker": market_ticker,
    }


def write_prior_wager_log_for_preservation(path):
    wagers = pd.DataFrame(
        [
            {
                "Date Placed": "2026-05-01 09:00:00",
                "Match Date": "2026-08-05",
                "Match": "Prior Match",
                "Outcome": "Prior Outcome",
                "Action": "BUY YES",
                "Market Ticker": "KXWCGAME-26AUG05-IIIJJJ-III",
                "Silver Probability": 0.42,
                "Edge": 0.08,
                "Bucket": "B",
                "Market Result": "",
                "Contract Won": "",
                "Contracts": 5,
                "Entry Price": 0.25,
                "Exit Price": "",
                "Fee In": 0.05,
                "Fee Out": "",
                "Status": "Open",
                "Closing Price": 0.64,
                "CLV": 0.14,
                "CLV %": 0.28,
                "Realized P/L": "",
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        wagers.to_excel(writer, sheet_name="Wagers", index=False)


if __name__ == "__main__":
    unittest.main()
