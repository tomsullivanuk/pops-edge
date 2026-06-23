import os
import runpy
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
            match_csv = downloads_dir / "data-match.csv"
            futures_csv = downloads_dir / "data-futures.csv"
            shutil.copy2(FIXTURES / "sample_silver.csv", match_csv)
            shutil.copy2(FIXTURES / "sample_silver_futures.csv", futures_csv)
            os.utime(match_csv, (1_700_000_000, 1_700_000_000))
            os.utime(futures_csv, (1_700_000_100, 1_700_000_100))

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
            self.assertEqual(
                metadata.loc[metadata["Field"] == "Silver Source File", "Value"].iloc[0],
                "data-match.csv",
            )
            self.assertTrue(futures_csv.exists())
            self.assertTrue((project_dir / "archive" / "silver_processed").exists())

    def test_process_silver_futures_builds_clean_workbook_from_sample_csv(self):
        with TemporaryDirectory() as home:
            project_dir = Path(home) / "kalshi"
            downloads_dir = Path(home) / "Downloads"
            project_dir.mkdir()
            downloads_dir.mkdir()
            futures_csv = downloads_dir / "data-futures.csv"
            match_csv = downloads_dir / "data-match.csv"
            shutil.copy2(
                FIXTURES / "sample_silver_futures.csv",
                futures_csv,
            )
            shutil.copy2(FIXTURES / "sample_silver.csv", match_csv)
            os.utime(futures_csv, (1_700_000_000, 1_700_000_000))
            os.utime(match_csv, (1_700_000_100, 1_700_000_100))

            with patched_environ(HOME=home):
                run_pipeline_script(ROOT / "process_silver_futures.py")

            output = project_dir / "Silver_Futures_Current.xlsx"
            self.assertTrue(output.exists())

            futures = pd.read_excel(output, sheet_name="Silver Futures")
            metadata = pd.read_excel(output, sheet_name="Silver Metadata")

            self.assertEqual(len(futures), 3)
            self.assertEqual(futures["Team"].tolist(), ["ARG", "USA", "BRA"])
            self.assertAlmostEqual(futures.loc[futures["Team"] == "ARG", "Champ"].iloc[0], 0.241)
            self.assertAlmostEqual(futures.loc[futures["Team"] == "USA", "R16"].iloc[0], 0.72)
            self.assertEqual(
                metadata.loc[metadata["Field"] == "Silver Futures Rows Output", "Value"].iloc[0],
                3,
            )
            self.assertEqual(
                metadata.loc[metadata["Field"] == "Silver Futures Source File", "Value"].iloc[0],
                "data-futures.csv",
            )
            self.assertTrue(match_csv.exists())
            self.assertEqual(len(list((project_dir / "archive" / "silver_futures_raw").glob("*.csv"))), 1)
            self.assertTrue((project_dir / "archive" / "silver_futures_processed").exists())

    def test_kalshi_pull_includes_match_and_world_cup_futures_markets(self):
        with TemporaryDirectory() as workspace:
            workspace = Path(workspace)

            with changed_dir(workspace), patch("requests.get") as get:
                get.return_value = fake_kalshi_response({
                    "events": [
                        kalshi_event(
                            "KXWCGAME-26JUN13-USAMEX",
                            "KXWCGAME",
                            "USA vs Mexico",
                            [
                                kalshi_market("KXWCGAME-26JUN13-USAMEX-USA", "United States", "USA vs Mexico Winner?"),
                            ],
                        ),
                        kalshi_event(
                            "KXWCROUND-26RO16",
                            "KXWCROUND",
                            "World Soccer Cup Round of 16 Qualifiers",
                            [
                                kalshi_market("KXWCROUND-26RO16-USA", "USA", "Will USA qualify for FIFA World Cup Round of 16?"),
                            ],
                        ),
                        kalshi_event(
                            "KXWCROUND-26QUAR",
                            "KXWCROUND",
                            "World Soccer Cup Quarterfinals Qualifiers",
                            [
                                kalshi_market("KXWCROUND-26QUAR-USA", "USA", "Will USA qualify for FIFA World Cup Quarterfinals?"),
                            ],
                        ),
                        kalshi_event(
                            "KXWCROUND-26SEMI",
                            "KXWCROUND",
                            "World Soccer Cup Semifinals Qualifiers",
                            [
                                kalshi_market("KXWCROUND-26SEMI-USA", "USA", "Will USA qualify for FIFA World Cup Semifinals?"),
                            ],
                        ),
                        kalshi_event(
                            "KXMENWORLDCUP-26",
                            "KXMENWORLDCUP",
                            "2026 World Soccer Cup Winner",
                            [
                                kalshi_market("KXMENWORLDCUP-26-AR", "Argentina", "Will the Argentina win the 2026 Men's World Cup?"),
                            ],
                        ),
                        kalshi_event(
                            "KXWCROUND-26FINAL",
                            "KXWCROUND",
                            "World Soccer Cup Final Qualifiers",
                            [
                                kalshi_market("KXWCROUND-26FINAL-USA", "USA", "Will USA qualify for FIFA World Cup Final?"),
                            ],
                        ),
                        kalshi_event(
                            "KXWCHOST-2038",
                            "KXWCHOST",
                            "Who will host the 2038 World Soccer Cup?",
                            [
                                kalshi_market("KXWCHOST-2038-GER", "Germany", "Will Germany host?"),
                            ],
                        ),
                    ],
                    "cursor": None,
                })

                run_pipeline_script(ROOT / "kalshi_pull.py")

            output = workspace / "Kalshi_Current.xlsx"
            self.assertTrue(output.exists())

            pulled = pd.read_excel(output)
            self.assertEqual(
                pulled["market_ticker"].tolist(),
                [
                    "KXWCGAME-26JUN13-USAMEX-USA",
                    "KXWCROUND-26RO16-USA",
                    "KXWCROUND-26QUAR-USA",
                    "KXWCROUND-26SEMI-USA",
                    "KXMENWORLDCUP-26-AR",
                ],
            )
            self.assertIn("World Soccer Cup Round of 16 Qualifiers", pulled["game"].tolist())
            self.assertIn("2026 World Soccer Cup Winner", pulled["game"].tolist())
            self.assertNotIn("KXWCROUND-26FINAL-USA", pulled["market_ticker"].tolist())
            self.assertNotIn("KXWCHOST-2038-GER", pulled["market_ticker"].tolist())

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

    def test_build_futures_value_board_matches_champion_and_advancement_markets(self):
        with TemporaryDirectory() as workspace:
            workspace = Path(workspace)
            write_sample_silver_futures_workbook(workspace / "Silver_Futures_Current.xlsx")
            write_sample_kalshi_futures_workbook(workspace / "Kalshi_Current.xlsx")

            with changed_dir(workspace):
                run_pipeline_script(ROOT / "build_futures_value_board.py")

            output = workspace / "WorldCup_Futures_ValueBoard.xlsx"
            self.assertTrue(output.exists())

            bet_sheet = pd.read_excel(output, sheet_name="Bet Sheet")
            metadata = pd.read_excel(output, sheet_name="Run Metadata")
            value_board = pd.read_excel(output, sheet_name="Value Board")

            self.assertEqual(metadata.loc[metadata["Field"] == "QC Status", "Value"].iloc[0], "PASS")
            self.assertEqual(len(value_board), 3)

            argentina = bet_sheet[bet_sheet["market_ticker"] == "KXMENWORLDCUP-26-AR"].iloc[0]
            self.assertEqual(argentina["Stage"], "Champion")
            self.assertEqual(argentina["Team"], "ARG")
            self.assertEqual(argentina["Action"], "BUY YES")
            self.assertAlmostEqual(argentina["Silver"], 0.241)
            self.assertAlmostEqual(argentina["Market Price"], 0.15)
            self.assertAlmostEqual(argentina["Edge"], 0.091)
            self.assertEqual(argentina["Bucket"], "B")

            usa = bet_sheet[bet_sheet["market_ticker"] == "KXWCROUND-26RO16-USA"].iloc[0]
            self.assertEqual(usa["Stage"], "Round of 16")
            self.assertEqual(usa["Action"], "BUY YES")
            self.assertAlmostEqual(usa["Silver"], 0.72)
            self.assertAlmostEqual(usa["Market Price"], 0.61)
            self.assertAlmostEqual(usa["Edge"], 0.11)

    def test_build_web_futures_betsheet_creates_sortable_html_with_expected_rows(self):
        with TemporaryDirectory() as workspace:
            workspace = Path(workspace)
            write_sample_futures_value_board(workspace / "WorldCup_Futures_ValueBoard.xlsx")

            with changed_dir(workspace):
                run_pipeline_script(ROOT / "build_web_futures_betsheet.py")

            output = workspace / "WorldCup_Futures_BetSheet.html"
            self.assertTrue(output.exists())

            html = output.read_text(encoding="utf-8")
            self.assertIn("World Cup Futures Value Board", html)
            self.assertIn("sortTable(table, columnIndex, ascending)", html)
            self.assertIn("Champion", html)
            self.assertIn("ARG", html)
            self.assertIn("KXMENWORLDCUP-26-AR", html)
            self.assertNotIn("NaN", html)

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
            self.assertEqual(usa["Match Date"], "2026-06-13")
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
            self.assertEqual(closed["Match Date"], "2026-07-01")
            self.assertEqual(closed["Action"], "BUY YES")
            self.assertEqual(closed["Status"], "Closed Early")
            self.assertEqual(closed["Market Result"], "yes")
            self.assertEqual(closed["Contract Won"], "Yes")
            self.assertAlmostEqual(closed["Entry Price"], 0.40)
            self.assertAlmostEqual(closed["Exit Price"], 0.55)
            self.assertAlmostEqual(closed["Realized P/L"], 1.35)

            losing_buy = row_for(wagers, "KXWCGAME-26JUL02-BBBFFF-BBB")
            self.assertEqual(losing_buy["Match Date"], "2026-07-02")
            self.assertEqual(losing_buy["Action"], "BUY YES")
            self.assertEqual(losing_buy["Status"], "Settled")
            self.assertEqual(losing_buy["Market Result"], "no")
            self.assertEqual(losing_buy["Contract Won"], "No")
            self.assertAlmostEqual(losing_buy["Realized P/L"], -2.88)
            self.assertAlmostEqual(losing_buy["Closing Price"], 0.45)
            self.assertAlmostEqual(losing_buy["CLV"], 0.10)
            self.assertAlmostEqual(losing_buy["CLV %"], 0.2857)

            winning_sell = row_for(wagers, "KXWCGAME-26JUL03-CCCGGG-CCC")
            self.assertEqual(winning_sell["Action"], "SELL YES")
            self.assertEqual(winning_sell["Status"], "Settled")
            self.assertEqual(winning_sell["Market Result"], "no")
            self.assertEqual(winning_sell["Contract Won"], "Yes")
            self.assertAlmostEqual(winning_sell["Realized P/L"], 7.32)
            self.assertAlmostEqual(winning_sell["Closing Price"], 0.50)
            self.assertAlmostEqual(winning_sell["CLV"], 0.12)
            self.assertAlmostEqual(winning_sell["CLV %"], 0.1935)

            multiple_fill = row_for(wagers, "KXWCGAME-26JUL04-DDDHHH-DDD")
            self.assertEqual(multiple_fill["Action"], "BUY YES")
            self.assertEqual(multiple_fill["Status"], "Open")
            self.assertAlmostEqual(multiple_fill["Contracts"], 40)
            self.assertAlmostEqual(multiple_fill["Entry Price"], 0.475)
            self.assertAlmostEqual(multiple_fill["Fee In"], 0.40)
            self.assertTrue(pd.isna(multiple_fill["Closing Price"]))
            self.assertAlmostEqual(multiple_fill["CLV"], 0.03)
            self.assertAlmostEqual(multiple_fill["CLV %"], 0.0632)

            preserved = row_for(wagers, "KXWCGAME-26AUG05-IIIJJJ-III")
            self.assertEqual(preserved["Match Date"], "2026-08-05")
            self.assertEqual(preserved["Match"], "Prior Match")
            self.assertEqual(preserved["Outcome"], "Prior Outcome")
            self.assertAlmostEqual(preserved["Silver Probability"], 0.42)
            self.assertAlmostEqual(preserved["Edge"], 0.08)
            self.assertEqual(preserved["Bucket"], "B")
            self.assertAlmostEqual(preserved["Closing Price"], 0.64)
            self.assertAlmostEqual(preserved["CLV"], 0.39)
            self.assertAlmostEqual(preserved["CLV %"], 1.56)

            fallback = row_for(wagers, "KXWCGAME-26SEP06-KKKLLL-KKK")
            self.assertEqual(fallback["Match Date"], "2026-09-06")
            self.assertTrue(pd.isna(fallback["Match"]))
            self.assertTrue(pd.isna(fallback["Outcome"]))
            self.assertTrue(pd.isna(fallback["Market Result"]))
            self.assertTrue(pd.isna(fallback["Contract Won"]))
            self.assertTrue(pd.isna(fallback["Closing Price"]))
            self.assertTrue(pd.isna(fallback["CLV"]))
            self.assertTrue(pd.isna(fallback["CLV %"]))

    def test_import_wagers_normalizes_match_dates_from_strings_timestamps_and_tickers(self):
        with TemporaryDirectory() as home:
            project_dir = Path(home) / "kalshi"
            project_dir.mkdir()

            activity = pd.DataFrame(
                [
                    trade("2026-06-01 09:00:00", "Yes", "KXWCGAME-26JUN14-STRONE-STR", 10, 40, 0.10),
                    trade("2026-06-02 09:00:00", "Yes", "KXWCGAME-26JUN14-TIMTWO-TIM", 8, 35, 0.08),
                    trade("2026-06-03 09:00:00", "Yes", "KXWCGAME-26JUN14-FALBAK-FAL", 7, 45, 0.07),
                    trade("2026-06-04 09:00:00", "Yes", "KXWCGAME-26JUN12-BADOLD-BAD", 6, 44, 0.06),
                ]
            )
            activity.to_csv(project_dir / "Kalshi-Recent-Activity-All-dates.csv", index=False)
            write_date_format_value_board_lookup(project_dir / "WorldCup_ValueBoard.xlsx")
            write_prior_timestamp_match_date_log(project_dir / "World_Cup_Bet_Log.xlsx")

            with patched_environ(HOME=home):
                run_pipeline_script(ROOT / "import_wagers.py")

            wagers = pd.read_excel(project_dir / "World_Cup_Bet_Log.xlsx", sheet_name="Wagers")

            string_date = row_for(wagers, "KXWCGAME-26JUN14-STRONE-STR")
            self.assertEqual(string_date["Match Date"], "2026-06-14")

            timestamp_date = row_for(wagers, "KXWCGAME-26JUN14-TIMTWO-TIM")
            self.assertEqual(timestamp_date["Match Date"], "2026-06-14")

            ticker_date = row_for(wagers, "KXWCGAME-26JUN14-FALBAK-FAL")
            self.assertEqual(ticker_date["Match Date"], "2026-06-14")

            invalid_prior_date = row_for(wagers, "KXWCGAME-26JUN12-BADOLD-BAD")
            self.assertEqual(invalid_prior_date["Match Date"], "2026-06-12")

    def test_build_web_betlog_creates_sortable_html_with_expected_rows_and_blanks(self):
        with TemporaryDirectory() as workspace:
            workspace = Path(workspace)
            write_sample_web_wager_log(workspace / "World_Cup_Bet_Log.xlsx")

            with changed_dir(workspace):
                run_pipeline_script(ROOT / "build_web_betlog.py")

            output = workspace / "World_Cup_Bet_Log.html"
            self.assertTrue(output.exists())

            html = output.read_text(encoding="utf-8")
            self.assertIn("World Cup Bet Log", html)
            self.assertIn("sortTable(table, index, ascending)", html)
            self.assertIn("USA vs Mexico", html)
            self.assertIn("Canada vs Brazil", html)
            self.assertIn("BUY YES", html)
            self.assertNotIn("NaN", html)
            self.assertIn('data-sort="2026-06-14"', html)
            self.assertIn('data-sort="2026-06-11 10:00:00"', html)
            self.assertIn('data-sort="0.60">0.60</td>', html)
            self.assertIn('data-sort="0.12">0.12</td>', html)
            self.assertIn('data-sort="2.20">2.20</td>', html)


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


class fake_kalshi_response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def kalshi_event(event_ticker, series_ticker, title, markets):
    return {
        "event_ticker": event_ticker,
        "series_ticker": series_ticker,
        "title": title,
        "sub_title": "",
        "category": "Sports",
        "markets": markets,
    }


def kalshi_market(ticker, yes_sub_title, title):
    return {
        "ticker": ticker,
        "yes_sub_title": yes_sub_title,
        "title": title,
        "yes_bid_dollars": 0.48,
        "yes_ask_dollars": 0.49,
        "last_price_dollars": 0.49,
        "volume_fp": 100,
        "open_interest_fp": 50,
        "close_time": "2026-07-19T23:59:00Z",
    }


def write_sample_silver_futures_workbook(path):
    futures = pd.DataFrame(
        [
            {"Team": "ARG", "Team Raw": "ARG Argentina", "R16": 0.864, "Qtr": 0.552, "Semi": 0.376, "Final": 0.293, "Champ": 0.241},
            {"Team": "USA", "Team Raw": "USA United States", "R16": 0.72, "Qtr": 0.35, "Semi": 0.18, "Final": 0.08, "Champ": 0.03},
        ]
    )
    metadata = pd.DataFrame(
        [["Silver Futures Source File", "sample_silver_futures.csv"], ["Silver Futures Rows Output", 2]],
        columns=["Field", "Value"],
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        futures.to_excel(writer, sheet_name="Silver Futures", index=False)
        metadata.to_excel(writer, sheet_name="Silver Metadata", index=False)


def write_sample_kalshi_futures_workbook(path):
    rows = pd.DataFrame(
        [
            {
                "event_ticker": "KXMENWORLDCUP-26",
                "game": "World Cup winner",
                "sub_title": "",
                "category": "Sports",
                "market_ticker": "KXMENWORLDCUP-26-AR",
                "outcome": "Argentina",
                "market_title": "Will Argentina win the World Cup?",
                "yes_bid_dollars": 0.14,
                "yes_ask_dollars": 0.15,
                "last_price_dollars": 0.15,
                "volume_fp": 1000,
                "open_interest_fp": 500,
                "close_time": "2026-07-19T23:59:00Z",
            },
            {
                "event_ticker": "KXWCROUND-26RO16",
                "game": "Round of 16 Qualifiers",
                "sub_title": "",
                "category": "Sports",
                "market_ticker": "KXWCROUND-26RO16-USA",
                "outcome": "United States",
                "market_title": "Will USA qualify for the Round of 16?",
                "yes_bid_dollars": 0.60,
                "yes_ask_dollars": 0.61,
                "last_price_dollars": 0.61,
                "volume_fp": 800,
                "open_interest_fp": 300,
                "close_time": "2026-07-01T23:59:00Z",
            },
            {
                "event_ticker": "KXWCROUND-26QUAR",
                "game": "Quarterfinals Qualifiers",
                "sub_title": "",
                "category": "Sports",
                "market_ticker": "KXWCROUND-26QUAR-USA",
                "outcome": "United States",
                "market_title": "Will USA qualify for the Quarterfinals?",
                "yes_bid_dollars": 0.42,
                "yes_ask_dollars": 0.43,
                "last_price_dollars": 0.43,
                "volume_fp": 600,
                "open_interest_fp": 200,
                "close_time": "2026-07-05T23:59:00Z",
            },
            {
                "event_ticker": "KXWCGAME-26JUN13-USAMEX",
                "game": "USA vs Mexico",
                "sub_title": "",
                "category": "Sports",
                "market_ticker": "KXWCGAME-26JUN13-USAMEX-USA",
                "outcome": "United States",
                "market_title": "USA vs Mexico Winner?",
                "yes_bid_dollars": 0.48,
                "yes_ask_dollars": 0.49,
                "last_price_dollars": 0.49,
                "volume_fp": 100,
                "open_interest_fp": 50,
                "close_time": "2026-06-13T23:59:00Z",
            },
        ]
    )
    rows.to_excel(path, index=False)


def write_sample_futures_value_board(path):
    bet_sheet = pd.DataFrame(
        [
            {
                "Stage": "Champion",
                "Team": "ARG",
                "Action": "BUY YES",
                "Silver": 0.241,
                "Market Price": 0.15,
                "Edge": 0.091,
                "ROI": 0.61,
                "Half Kelly": 0.05,
                "Stake on $500": 26.76,
                "Bucket": "B",
                "Volume": 1000,
                "event_ticker": "KXMENWORLDCUP-26",
                "market_ticker": "KXMENWORLDCUP-26-AR",
            },
            {
                "Stage": "Round of 16",
                "Team": "USA",
                "Action": "BUY YES",
                "Silver": 0.72,
                "Market Price": 0.61,
                "Edge": 0.11,
                "ROI": 0.18,
                "Half Kelly": 0.14,
                "Stake on $500": 70.51,
                "Bucket": "A",
                "Volume": 800,
                "event_ticker": "KXWCROUND-26RO16",
                "market_ticker": "KXWCROUND-26RO16-USA",
            },
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        bet_sheet.to_excel(writer, sheet_name="Bet Sheet", index=False)


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
            lookup_row("KXWCGAME-26JUL01-AAAEEE-AAA", "Jul 1, 2026", "AAA vs EEE", "AAA", "BUY YES", 0.58, 0.08, "B"),
            lookup_row("KXWCGAME-26JUL02-BBBFFF-BBB", "07/02/2026", "BBB vs FFF", "BBB", "BUY YES", 0.48, 0.06, "C"),
            lookup_row("KXWCGAME-26JUL03-CCCGGG-CCC", "2026-07-03", "CCC vs GGG", "CCC", "SELL YES", 0.38, 0.12, "A"),
            lookup_row("KXWCGAME-26JUL04-DDDHHH-DDD", "2026-07-04", "DDD vs HHH", "DDD", "BUY YES", 0.55, 0.07, "B"),
            lookup_row("KXWCGAME-26AUG05-IIIJJJ-III", "2026-08-05", "Current Match", "Current Outcome", "BUY YES", 0.99, 0.01, "C"),
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        bet_sheet.to_excel(writer, sheet_name="Bet Sheet", index=False)


def write_date_format_value_board_lookup(path):
    bet_sheet = pd.DataFrame(
        [
            lookup_row("KXWCGAME-26JUN14-STRONE-STR", "6/14/26", "STR vs ONE", "STR", "BUY YES", 0.58, 0.08, "B"),
            lookup_row("KXWCGAME-26JUN14-TIMTWO-TIM", "2026-06-01", "TIM vs TWO", "TIM", "BUY YES", 0.48, 0.06, "C"),
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
                "Date Placed": "2026-05-01 08:00:00",
                "Market Ticker": "KXWCGAME-26JUL01-AAAEEE-AAA",
                "Market Result": "yes",
                "Contract Won": "Yes",
            },
            {
                "Date Placed": "2026-05-01 09:00:00",
                "Match Date": "August 5, 2026",
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
            },
            {
                "Date Placed": "2026-05-02 09:00:00",
                "Market Ticker": "KXWCGAME-26JUL02-BBBFFF-BBB",
                "Market Result": "yes",
                "Contract Won": "Yes",
                "Closing Price": 0.45,
                "CLV": 0.01,
                "CLV %": 0.02,
            },
            {
                "Date Placed": "2026-05-03 09:00:00",
                "Market Ticker": "KXWCGAME-26JUL03-CCCGGG-CCC",
                "Closing Price": 0.50,
                "CLV": 0.01,
                "CLV %": 0.02,
            },
            {
                "Date Placed": "2026-05-04 09:00:00",
                "Market Ticker": "KXWCGAME-26JUL04-DDDHHH-DDD",
                "Closing Price": "",
                "CLV": 0.03,
                "CLV %": 0.0632,
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        wagers.to_excel(writer, sheet_name="Wagers", index=False)


def write_prior_timestamp_match_date_log(path):
    wagers = pd.DataFrame(
        [
            {
                "Date Placed": "2026-05-01 09:00:00",
                "Match Date": pd.Timestamp("2026-06-14"),
                "Market Ticker": "KXWCGAME-26JUN14-TIMTWO-TIM",
                "Match": "Prior Timestamp Match",
                "Outcome": "Prior Timestamp Outcome",
                "Action": "BUY YES",
            },
            {
                "Date Placed": "2026-05-02 09:00:00",
                "Match Date": "0001-06-12",
                "Market Ticker": "KXWCGAME-26JUN12-BADOLD-BAD",
                "Match": "Prior Invalid Date Match",
                "Outcome": "Prior Invalid Date Outcome",
                "Action": "BUY YES",
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        wagers.to_excel(writer, sheet_name="Wagers", index=False)


def write_sample_web_wager_log(path):
    wagers = pd.DataFrame(
        [
            {
                "Date Placed": "2026-06-10 09:00:00",
                "Match Date": "2026-06-13",
                "Match": "USA vs Mexico",
                "Outcome": "United States",
                "Action": "BUY YES",
                "Silver Probability": 0.6000000000001,
                "Edge": 0.123456,
                "Bucket": "A",
                "Status": "Open",
                "Contract Won": None,
                "Entry Price": 0.456789,
                "Exit Price": None,
                "Closing Price": None,
                "CLV": None,
                "CLV %": None,
                "Realized P/L": None,
            },
            {
                "Date Placed": "2026-06-11 10:00:00",
                "Match Date": "6/14/26",
                "Match": "Canada vs Brazil",
                "Outcome": "Brazil",
                "Action": "SELL YES",
                "Silver Probability": 0.35,
                "Edge": 0.08,
                "Bucket": "B",
                "Status": "Settled",
                "Contract Won": "Yes",
                "Entry Price": 0.58,
                "Exit Price": "",
                "Closing Price": 0.501234,
                "CLV": 0.083333,
                "CLV %": 0.141592,
                "Realized P/L": 2.2,
            },
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        wagers.to_excel(writer, sheet_name="Wagers", index=False)


if __name__ == "__main__":
    unittest.main()
