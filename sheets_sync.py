"""Google Sheets sync layer for Scam Scanner.

Auto-pushes new evaluations to the shared Google Sheet.
Primary path: MCP (via Claude Code session).
Fallback: gspread with service account.
CLI fallback: exports CSV for manual import.
"""

import json
import csv
import io
from pathlib import Path
from db import get_all_evaluations, lookup_url

# Sheet config
SHEET_ID = "1VS9etn7njT3JasHpBkNEDlr1RDV7mJa985EqOLEb_nk"
SHEET_NAME = "Sheet1"
HEADER_ROW = 1
GUIDE_ROW = 2
DATA_START_ROW = 3  # Row 1 = headers, Row 2 = field guide, Row 3+ = data

CSV_EXPORT_PATH = Path(__file__).parent / "scam_scanner_export.csv"

HEADERS = [
    "URL", "Product Name", "Category", "Date Evaluated",
    "Trust Score (0-100)", "Verdict", "Red Flags", "Claims Extracted",
    "Evidence Check", "FDA Disclaimer Present?", "FTC Complaint Ready?",
    "Sources", "Verdict Summary",
]


def format_row(eval_data: dict) -> list[str]:
    """Convert an evaluation dict to a Sheet row."""
    data = dict(eval_data)  # Don't mutate original

    for field in ("red_flags", "claims_extracted", "sources"):
        val = data.get(field, [])
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                val = [val] if val else []
            data[field] = val

    analysis = {}
    if data.get("analysis_json"):
        try:
            analysis = json.loads(data["analysis_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return [
        data.get("url", ""),
        data.get("product_name", ""),
        data.get("category", ""),
        data.get("date_evaluated", ""),
        str(data.get("trust_score", "")),
        data.get("verdict", ""),
        "; ".join(data.get("red_flags", [])),
        "; ".join(data.get("claims_extracted", [])),
        data.get("evidence_check", ""),
        "Yes" if data.get("fda_disclaimer_present") else "No",
        "Yes" if data.get("ftc_complaint_ready") else "No",
        "; ".join(data.get("sources", [])),
        analysis.get("verdict_summary", data.get("verdict", "")),
    ]


def sync_single_row(eval_data: dict):
    """Sync a single new evaluation to the Sheet. Called after each scan.

    Tries gspread first, falls back to appending to CSV export.
    MCP sync happens at the orchestrator level (Claude Code session).
    """
    row = format_row(eval_data)

    # Try gspread
    try:
        from config import GOOGLE_CREDS_PATH
        if GOOGLE_CREDS_PATH:
            import gspread
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDS_PATH,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            gc = gspread.authorize(creds)
            sheet = gc.open_by_key(SHEET_ID).sheet1
            sheet.append_row(row, value_input_option="USER_ENTERED")
            print(f"  Synced to Google Sheet (gspread).")
            return True
    except Exception:
        pass

    # Fallback: append to CSV
    _append_to_csv(row)
    print(f"  Appended to {CSV_EXPORT_PATH} (import to Sheet manually or via MCP).")
    return False


def full_sync_to_csv():
    """Export all DB entries to CSV for Sheet import."""
    all_evals = get_all_evaluations()
    rows = [format_row(e) for e in all_evals]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    writer.writerows(rows)

    CSV_EXPORT_PATH.write_text(output.getvalue())
    print(f"  Exported {len(rows)} rows to {CSV_EXPORT_PATH}")
    return CSV_EXPORT_PATH


def _append_to_csv(row: list[str]):
    """Append a single row to the CSV export file."""
    file_exists = CSV_EXPORT_PATH.exists()
    with open(CSV_EXPORT_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADERS)
        writer.writerow(row)


def get_mcp_sync_payload() -> dict:
    """Return the full data payload formatted for MCP modify_sheet_values.

    Use this in a Claude Code session:
        from sheets_sync import get_mcp_sync_payload
        payload = get_mcp_sync_payload()
        # Then call mcp__google-workspace__modify_sheet_values with payload
    """
    all_evals = get_all_evaluations()
    rows = [format_row(e) for e in all_evals]
    end_row = DATA_START_ROW + len(rows) - 1
    return {
        "sheet_id": SHEET_ID,
        "range": f"{SHEET_NAME}!A{DATA_START_ROW}:M{end_row}",
        "values": rows,
    }
