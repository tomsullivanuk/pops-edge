import glob
import os
import re
import shutil
from datetime import datetime

import pandas as pd

from config import (
    DOWNLOADS_DIR,
    PROJECT_DIR,
    SHEET_SILVER_FUTURES,
    SHEET_SILVER_METADATA,
    SILVER_FUTURES_CURRENT_FILE,
    SILVER_FUTURES_PROCESSED_ARCHIVE_DIR,
    SILVER_FUTURES_RAW_ARCHIVE_DIR,
)

OUTPUT_FILE = os.path.join(PROJECT_DIR, SILVER_FUTURES_CURRENT_FILE)
REQUIRED_COLUMNS = ["Team", "R16", "Qtr", "Semi", "Final"]
CHAMP_COLUMN_CANDIDATES = ["Champ 🏆", "Champ", "Champion"]

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


def normalize_code(value):
    text = str(value).strip()
    match = re.search(r"\b[A-Z]{3}\b", text.upper())
    if match:
        code = match.group(0)
        return CODE_MAP.get(code, code)

    normalized_name = re.sub(r"[^A-Z ]", "", text.upper()).strip()
    return TEAM_NAME_TO_CODE.get(normalized_name, normalized_name)


def to_probability(value):
    if pd.isna(value) or value == "":
        return pd.NA

    text = str(value).strip().replace("%", "")
    number = pd.to_numeric(text, errors="coerce")
    if pd.isna(number):
        return pd.NA

    if number > 1:
        return number / 100
    return number


def archive_name_for(path):
    modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d_%H%M%S")
    return f"{modified}_{os.path.basename(path)}"


def has_futures_columns(path):
    try:
        columns = pd.read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return False

    has_required = all(column in columns for column in REQUIRED_COLUMNS)
    has_champ = any(column in columns for column in CHAMP_COLUMN_CANDIDATES)
    return has_required and has_champ


candidate_files = (
    glob.glob(os.path.join(DOWNLOADS_DIR, "data-*.csv"))
    + glob.glob(os.path.join(PROJECT_DIR, "data-*.csv"))
    + glob.glob(os.path.join(DOWNLOADS_DIR, "*futures*.csv"))
    + glob.glob(os.path.join(PROJECT_DIR, "*futures*.csv"))
)

candidate_files = [path for path in candidate_files if has_futures_columns(path)]

if not candidate_files:
    raise FileNotFoundError(
        "No Silver futures CSV files found in Downloads or project folder."
    )

latest_file = max(candidate_files, key=os.path.getmtime)
latest_filename = os.path.basename(latest_file)
project_csv_path = os.path.join(PROJECT_DIR, latest_filename)

print(f"Latest Silver futures CSV found: {latest_file}")

if os.path.abspath(latest_file) != os.path.abspath(project_csv_path):
    shutil.copy2(latest_file, project_csv_path)
    print(f"Copied newest Silver futures CSV to project folder: {project_csv_path}")

os.makedirs(SILVER_FUTURES_RAW_ARCHIVE_DIR, exist_ok=True)
raw_archive_path = os.path.join(SILVER_FUTURES_RAW_ARCHIVE_DIR, archive_name_for(project_csv_path))
if not os.path.exists(raw_archive_path):
    shutil.copy2(project_csv_path, raw_archive_path)
    print(f"Archived raw Silver futures CSV: {raw_archive_path}")

df = pd.read_csv(project_csv_path)

champ_column = next(
    column for column in CHAMP_COLUMN_CANDIDATES if column in df.columns
)

clean = pd.DataFrame({
    "Team": df["Team"].apply(normalize_code),
    "Team Raw": df["Team"],
    "R16": df["R16"].apply(to_probability),
    "Qtr": df["Qtr"].apply(to_probability),
    "Semi": df["Semi"].apply(to_probability),
    "Final": df["Final"].apply(to_probability),
    "Champ": df[champ_column].apply(to_probability),
})

if "R32" in df.columns:
    clean["R32"] = df["R32"].apply(to_probability)
if "3rd" in df.columns:
    clean["3rd"] = df["3rd"].apply(to_probability)

clean = clean.dropna(subset=["Team"]).drop_duplicates(subset=["Team"], keep="first")

silver_source_modified = datetime.fromtimestamp(
    os.path.getmtime(project_csv_path)
).strftime("%Y-%m-%d %H:%M:%S")

metadata = pd.DataFrame([
    ["Silver Futures Source File", latest_filename],
    ["Silver Futures Source Path", project_csv_path],
    ["Silver Futures Source Modified", silver_source_modified],
    ["Silver Futures Processed At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["Silver Futures Rows Output", len(clean)],
    ["Champion Column Used", champ_column],
], columns=["Field", "Value"])

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    clean.to_excel(writer, sheet_name=SHEET_SILVER_FUTURES, index=False)
    metadata.to_excel(writer, sheet_name=SHEET_SILVER_METADATA, index=False)

os.makedirs(SILVER_FUTURES_PROCESSED_ARCHIVE_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
archive_file = os.path.join(
    SILVER_FUTURES_PROCESSED_ARCHIVE_DIR,
    f"{timestamp}_Silver_Futures_Current.xlsx",
)
shutil.copy2(OUTPUT_FILE, archive_file)

print(f"Archived processed Silver futures file: {archive_file}")
print(f"Saved {len(clean)} rows to {OUTPUT_FILE}")
print(f"Using Silver futures source: {latest_filename}")
