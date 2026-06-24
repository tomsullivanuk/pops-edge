from datetime import datetime

import pandas as pd

from config import (
    FUTURES_VALUE_BOARD_FILE,
    SHEET_BET_SHEET,
    WEB_FUTURES_VALUE_BOARD_FILE,
)

INPUT_FILE = FUTURES_VALUE_BOARD_FILE
OUTPUT_FILE = WEB_FUTURES_VALUE_BOARD_FILE

df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_BET_SHEET)

WEB_COLUMNS = [
    "Stage",
    "Team",
    "champion_proxy_candidate",
    "strong_champion_proxy",
    "Action",
    "Silver",
    "Market Price",
    "Edge",
    "ROI",
    "Quarter Kelly",
    "Stake on $500",
    "Bucket",
    "Volume",
    "market_ticker",
    "Position",
    "Current Action",
    "Entry Price",
    "Current Value Change",
    "Stake",
    "Status",
]

available_columns = [col for col in WEB_COLUMNS if col in df.columns]
df = df[available_columns]


def format_percentage(value, signed=False):
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return ""
    return f"{numeric:+.1%}" if signed else f"{numeric:.1%}"


def format_decimal(value):
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return ""
    return f"{numeric:.2f}"


if "Silver" in df.columns:
    df["Silver"] = df["Silver"].map(format_percentage)
if "Edge" in df.columns:
    df["Edge"] = df["Edge"].map(lambda value: format_percentage(value, signed=True))

for col in [
    "ROI",
    "Quarter Kelly",
    "Stake on $500",
    "Entry Price",
    "Current Value Change",
    "Stake",
]:
    if col in df.columns:
        df[col] = df[col].map(format_decimal)

df = df.fillna("")
html_table = df.to_html(
    index=False,
    classes="betsheet",
    border=0,
    table_id="betsheet",
)

html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>World Cup Futures Value Board</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 28px;
            background: #f6f7f9;
            color: #222;
        }}
        h1 {{ margin-bottom: 4px; }}
        .subtitle {{
            color: #666;
            margin-bottom: 8px;
        }}
        .proxy-note {{
            color: #4b5563;
            margin: 0 0 18px;
            max-width: 980px;
            font-size: 13px;
            line-height: 1.4;
        }}
        .proxy-badge,
        .strong-proxy-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
        }}
        .proxy-badge {{
            background: #f3f4f6;
            color: #374151;
            border: 1px solid #d1d5db;
        }}
        .strong-proxy-badge {{
            background: #dcfce7;
            color: #166534;
        }}
        table.betsheet {{
            border-collapse: collapse;
            width: 100%;
            background: white;
            box-shadow: 0 2px 12px rgba(0,0,0,.08);
            border-radius: 8px;
            overflow: hidden;
            font-size: 13px;
        }}
        .betsheet th {{
            background: #1f2937;
            color: white;
            padding: 8px;
            text-align: left;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        .betsheet th:hover {{
            background: #374151;
        }}
        .betsheet td {{
            padding: 7px 8px;
            border-bottom: 1px solid #e5e7eb;
            white-space: nowrap;
        }}
        .betsheet tr:hover {{
            background: #f3f4f6;
        }}
        .sort-indicator {{
            font-size: 0.8em;
            opacity: 0.8;
            margin-left: 6px;
        }}
    </style>
</head>
<body>
    <h1>World Cup Futures Value Board</h1>
    <div class="subtitle">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
    <p class="proxy-note">Champion Proxy Candidate means R16/QF/SF/Champion all show positive BUY edge. Strong Champion Proxy means the Champion BUY edge is at least 35% of the average R16/QF/SF BUY edge.</p>
    {html_table}

<script>
function parseCell(value) {{
    value = value.trim();

    if (value.endsWith('%')) {{
        return parseFloat(value.replace('%', ''));
    }}

    let numeric = value.replace(/[$,]/g, '');
    let parsed = parseFloat(numeric);
    if (Number.isFinite(parsed) && numeric !== '') {{
        return parsed;
    }}

    return value.toLowerCase();
}}

function sortTable(table, columnIndex, ascending) {{
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);

    rows.sort((a, b) => {{
        const aValue = parseCell(a.cells[columnIndex].innerText);
        const bValue = parseCell(b.cells[columnIndex].innerText);

        if (aValue < bValue) return ascending ? -1 : 1;
        if (aValue > bValue) return ascending ? 1 : -1;
        return 0;
    }});

    rows.forEach(row => tbody.appendChild(row));
}}

document.addEventListener("DOMContentLoaded", () => {{
    const table = document.getElementById("betsheet");
    const headers = table.querySelectorAll("th");
    const badgeColumns = [
        ["champion_proxy_candidate", "proxy-badge"],
        ["strong_champion_proxy", "strong-proxy-badge"],
    ];

    badgeColumns.forEach(([columnName, badgeClass]) => {{
        const columnIndex = Array.from(headers).findIndex(
            header => header.textContent.trim() === columnName
        );
        if (columnIndex < 0) return;

        Array.from(table.tBodies[0].rows).forEach(row => {{
            const cell = row.cells[columnIndex];
            if (cell.textContent.trim() === "YES") {{
                cell.innerHTML = `<span class="${{badgeClass}}">YES</span>`;
            }}
        }});
    }});

    headers.forEach((header, index) => {{
        header.dataset.sortDirection = "desc";

        header.addEventListener("click", () => {{
            const ascending = header.dataset.sortDirection !== "asc";

            headers.forEach(h => {{
                h.dataset.sortDirection = "desc";
                h.innerHTML = h.innerHTML.replace(/ <span class="sort-indicator">.*?<\\/span>/, "");
            }});

            sortTable(table, index, ascending);

            header.dataset.sortDirection = ascending ? "asc" : "desc";
            header.innerHTML += ascending
                ? ' <span class="sort-indicator">▲</span>'
                : ' <span class="sort-indicator">▼</span>';
        }});
    }});
}});
</script>
</body>
</html>
"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Created {OUTPUT_FILE}")
