from datetime import datetime

import pandas as pd

from config import BET_LOG_FILE, SHEET_WAGERS, WEB_BETLOG_FILE


INPUT_FILE = BET_LOG_FILE
OUTPUT_FILE = WEB_BETLOG_FILE

WEB_COLUMNS = [
    "Date Placed",
    "Match Date",
    "Match",
    "Outcome",
    "Action",
    "Silver Probability",
    "Edge",
    "Bucket",
    "Status",
    "Contract Won",
    "Entry Price",
    "Exit Price",
    "Closing Price",
    "CLV",
    "CLV %",
    "Realized P/L",
]


def build_web_betlog(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    df = pd.read_excel(input_file, sheet_name=SHEET_WAGERS)
    available_columns = [col for col in WEB_COLUMNS if col in df.columns]
    df = df[available_columns].fillna("")

    html_table = df.to_html(
        index=False,
        classes="betlog",
        border=0,
        table_id="betlog",
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>World Cup Bet Log</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 18px;
            background: #f6f7f9;
            color: #222;
        }}
        h1 {{
            margin: 0 0 4px;
            font-size: 24px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 14px;
            font-size: 13px;
        }}
        .table-wrap {{
            overflow-x: auto;
            background: white;
            box-shadow: 0 2px 12px rgba(0,0,0,.08);
            border-radius: 8px;
        }}
        table.betlog {{
            border-collapse: collapse;
            width: 100%;
            min-width: 1180px;
            background: white;
            font-size: 12px;
        }}
        .betlog th {{
            position: sticky;
            top: 0;
            background: #1f2937;
            color: white;
            padding: 8px 9px;
            text-align: left;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        .betlog th:hover {{
            background: #374151;
        }}
        .betlog td {{
            padding: 7px 9px;
            border-bottom: 1px solid #e5e7eb;
            white-space: nowrap;
        }}
        .betlog tr:hover {{
            background: #f3f4f6;
        }}
        .sort-indicator {{
            font-size: 0.8em;
            opacity: 0.8;
            margin-left: 6px;
        }}
        @media (min-width: 768px) {{
            body {{
                margin: 24px;
            }}
            table.betlog {{
                font-size: 13px;
            }}
        }}
    </style>
</head>
<body>
    <h1>World Cup Bet Log</h1>
    <div class="subtitle">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
    <div class="table-wrap">
        {html_table}
    </div>

<script>
function parseCell(value) {{
    value = value.trim();

    if (value.endsWith('%')) {{
        return parseFloat(value.replace('%', ''));
    }}

    let numeric = value.replace(/[$,]/g, '');
    let numericValue = Number(numeric);
    if (Number.isFinite(numericValue) && numeric !== '') {{
        return numericValue;
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
    const table = document.getElementById("betlog");
    const headers = table.querySelectorAll("th");

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

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return output_file


def main():
    output_file = build_web_betlog()
    print(f"Created {output_file}")


if __name__ == "__main__":
    main()
