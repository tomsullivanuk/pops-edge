import os
import re
import glob
import shutil
import pandas as pd
from datetime import datetime

from config import (
    DOWNLOADS_DIR,
    PROJECT_DIR,
    SHEET_SILVER_FORECASTS,
    SHEET_SILVER_METADATA,
    SILVER_CURRENT_FILE,
    SILVER_PROCESSED_ARCHIVE_DIR,
    SILVER_RAW_ARCHIVE_DIR,
)

ARCHIVE_DIR = SILVER_RAW_ARCHIVE_DIR
OUTPUT_FILE = os.path.join(PROJECT_DIR, SILVER_CURRENT_FILE)
REQUIRED_COLUMNS = [
    "Date",
    "Team",
    "Win",
    "GF",
    "Opponent",
    "Win.1",
    "GF.1",
    "Draw",
]

os.makedirs(ARCHIVE_DIR, exist_ok=True)

def clean_team_code(value):
    text = str(value)
    match = re.search(r"\b[A-Z]{3}\b", text)
    if match:
        return match.group(0)
    return text.strip()

def archive_name_for(path):
    modified = datetime.fromtimestamp(
        os.path.getmtime(path)
    ).strftime("%Y-%m-%d_%H%M%S")
    return f"{modified}_{os.path.basename(path)}"

def has_match_columns(path):
    try:
        columns = pd.read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return False

    return all(column in columns for column in REQUIRED_COLUMNS)

candidate_files = (
    glob.glob(os.path.join(DOWNLOADS_DIR, "data-*.csv")) +
    glob.glob(os.path.join(PROJECT_DIR, "data-*.csv"))
)

candidate_files = [path for path in candidate_files if has_match_columns(path)]

if not candidate_files:
    raise FileNotFoundError(
        "No Silver match forecast CSV files found in Downloads or project folder."
    )

latest_file = max(candidate_files, key=os.path.getmtime)
latest_filename = os.path.basename(latest_file)
project_csv_path = os.path.join(PROJECT_DIR, latest_filename)

print(f"Latest Silver CSV found: {latest_file}")

if os.path.abspath(latest_file) != os.path.abspath(project_csv_path):
    shutil.copy2(latest_file, project_csv_path)
    print(f"Copied newest Silver CSV to project folder: {project_csv_path}")

all_csvs_after_copy = (
    glob.glob(os.path.join(DOWNLOADS_DIR, "data-*.csv")) +
    glob.glob(os.path.join(PROJECT_DIR, "data-*.csv"))
)

all_csvs_after_copy = [path for path in all_csvs_after_copy if has_match_columns(path)]

for csv_file in all_csvs_after_copy:
    if os.path.abspath(csv_file) == os.path.abspath(project_csv_path):
        continue

    if os.path.abspath(csv_file) == os.path.abspath(latest_file):
        continue

    archive_path = os.path.join(ARCHIVE_DIR, archive_name_for(csv_file))

    if not os.path.exists(archive_path):
        shutil.move(csv_file, archive_path)
        print(f"Archived old Silver CSV: {archive_path}")

df = pd.read_csv(project_csv_path)

# Some Silver downloads include non-World-Cup matches and mark World Cup
# rows with a trophy emoji in Date. Other downloads contain only World Cup
# rows and do not use the trophy marker. Apply the filter only if it leaves
# rows behind.
if "Date" in df.columns:
    trophy_rows = df[df["Date"].astype(str).str.contains("🏆", na=False)].copy()
    if len(trophy_rows) > 0:
        df = trophy_rows
        print(f"Filtered to trophy-marked rows: {len(df)}")
    else:
        print("No trophy-marked rows found; keeping all rows.")

# Silver has used both column names in different exports.
if "modal_score" in df.columns:
    score_col = "modal_score"
elif "Most likely score" in df.columns:
    score_col = "Most likely score"
else:
    score_col = None

if score_col:
    score_values = df[score_col]
else:
    score_values = ""

clean = pd.DataFrame({
    "Date": df["Date"],
    "Team": df["Team"].apply(clean_team_code),
    "Win": df["Win"],
    "GF": df["GF"],
    "Opponent": df["Opponent"].apply(clean_team_code),
    "OpponentWin": df["Win.1"],
    "OpponentGF": df["GF.1"],
    "Draw": df["Draw"],
    "MostLikelyScore": score_values,
})

clean["match_key"] = clean.apply(
    lambda row: "-".join(sorted([row["Team"], row["Opponent"]])),
    axis=1
)

before_count = len(clean)

clean = clean.drop_duplicates(
    subset=["match_key"],
    keep="first"
).copy()

after_count = len(clean)

if after_count < before_count:
    print(f"Removed {before_count - after_count} duplicate reversed match rows.")

clean = clean.drop(columns=["match_key"])

silver_source_modified = datetime.fromtimestamp(
    os.path.getmtime(project_csv_path)
).strftime("%Y-%m-%d %H:%M:%S")

metadata = pd.DataFrame([
    ["Silver Source File", latest_filename],
    ["Silver Source Path", project_csv_path],
    ["Silver Source Modified", silver_source_modified],
    ["Silver Processed At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["Silver Rows Output", len(clean)],
    ["Score Column Used", score_col if score_col else "None"],
], columns=["Field", "Value"])

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    clean.to_excel(writer, sheet_name=SHEET_SILVER_FORECASTS, index=False)
    metadata.to_excel(writer, sheet_name=SHEET_SILVER_METADATA, index=False)

archive_processed_dir = SILVER_PROCESSED_ARCHIVE_DIR

os.makedirs(archive_processed_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

archive_file = os.path.join(
    archive_processed_dir,
    f"{timestamp}_Silver_Current.xlsx"
)

shutil.copy2(OUTPUT_FILE, archive_file)

print(f"Archived processed Silver file: {archive_file}")
print(f"Saved {len(clean)} rows to {OUTPUT_FILE}")
print(f"Using Silver source: {latest_filename}")
print(f"Score column used: {score_col if score_col else 'None'}")
