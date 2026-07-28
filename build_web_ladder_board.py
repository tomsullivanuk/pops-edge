from datetime import datetime
from html import escape

import pandas as pd

from build_ladder_board import SHEET_LADDER_BOARD, format_cents
from config import LADDER_BOARD_FILE, WEB_LADDER_BOARD_FILE

INPUT_FILE = LADDER_BOARD_FILE
OUTPUT_FILE = WEB_LADDER_BOARD_FILE

WEB_COLUMNS = [
    "event_title",
    "market_title",
    "side",
    "contracts_held",
    "avg_price",
    "current_price",
    "silver_probability",
    "current_edge",
    "ladder_display",
    "estimated_gross_proceeds",
    "estimated_profit_if_all_filled",
    "market_type",
    "status",
    "action_flag",
]


def display_price(value):
    return format_cents(value)


def display_money(value):
    if pd.isna(value) or value == "":
        return ""
    return f"${float(value):,.2f}"


def display_edge(value):
    if pd.isna(value) or value == "":
        return ""
    return f"{float(value):+.0%}"


def render_html(frame, generated_at=None):
    frame = frame.copy()
    available_columns = [column for column in WEB_COLUMNS if column in frame.columns]
    frame = frame[available_columns].copy()

    for column in ["avg_price", "current_price", "silver_probability"]:
        if column in frame.columns:
            frame[column] = frame[column].map(display_price)

    if "current_edge" in frame.columns:
        frame["current_edge"] = frame["current_edge"].map(display_edge)

    for column in ["estimated_gross_proceeds", "estimated_profit_if_all_filled"]:
        if column in frame.columns:
            frame[column] = frame[column].map(display_money)

    frame = frame.fillna("")

    rows = []
    for _, row in frame.iterrows():
        flag = row.get("action_flag", "")
        css_class = f' class="{flag}"' if flag in {"urgent", "near"} else ""
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row.tolist())
        rows.append(f"<tr{css_class}>{cells}</tr>")

    headers = "".join(f"<th>{column}</th>" for column in frame.columns)
    body = "\n".join(rows)
    generated_at = generated_at or datetime.now()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>World Cup Ladder Board</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 24px;
            background: #f6f7f9;
            color: #222;
        }}
        h1 {{ margin: 0 0 4px; }}
        .subtitle {{
            color: #666;
            margin-bottom: 18px;
        }}
        .table-wrap {{
            overflow-x: auto;
            background: white;
            box-shadow: 0 2px 12px rgba(0,0,0,.08);
            border-radius: 8px;
        }}
        table.ladder {{
            border-collapse: collapse;
            width: 100%;
            min-width: 1120px;
            font-size: 13px;
        }}
        .ladder th {{
            background: #1f2937;
            color: white;
            padding: 9px 10px;
            text-align: left;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        .ladder th:hover {{ background: #374151; }}
        .ladder td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
        }}
        .ladder tr:hover {{ background: #f3f4f6; }}
        .ladder tr.near {{ background: #fff7d6; }}
        .ladder tr.urgent {{ background: #ffe4e6; font-weight: 600; }}
        .ladder td:nth-child(9) {{
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }}
        .sort-indicator {{
            font-size: 0.8em;
            opacity: 0.8;
            margin-left: 6px;
        }}
    </style>
</head>
<body>
    <h1>World Cup Ladder Board</h1>
    <div class="subtitle">Generated {generated_at.strftime("%Y-%m-%d %H:%M")}</div>
    <div class="table-wrap">
        <table class="ladder" id="ladder">
            <thead><tr>{headers}</tr></thead>
            <tbody>
                {body}
            </tbody>
        </table>
    </div>

<script>
function parseCell(value) {{
    value = value.trim().replace('¢', '').replace('%', '');
    let numeric = value.replace(/[$,+,]/g, '');
    if (!isNaN(numeric) && numeric !== '') {{
        return parseFloat(numeric);
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
    const table = document.getElementById("ladder");
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


def main():
    frame = pd.read_excel(INPUT_FILE, sheet_name=SHEET_LADDER_BOARD)
    html = render_html(frame)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as output:
        output.write(html)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
