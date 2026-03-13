#!/usr/bin/env python3
"""Build the static GitHub Pages site from the SQLite database.

Usage:
    python build_site.py

Reads all evaluations from scam_scanner.db and writes:
    docs/data.json  — evaluation data for the frontend
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from db import get_all_evaluations, get_stats


def parse_json_field(val):
    """Parse a JSON string field, return list."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return [val] if val else []
    return []


def build_data():
    """Export DB to docs/data.json."""
    evals = get_all_evaluations()
    stats = get_stats()

    products = []
    for e in evals:
        analysis = {}
        if e.get("analysis_json"):
            try:
                analysis = json.loads(e["analysis_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        products.append({
            "id": e["id"],
            "url": e["url"],
            "domain": e["domain"],
            "product_name": e["product_name"],
            "category": e["category"],
            "date_evaluated": e["date_evaluated"],
            "trust_score": e["trust_score"],
            "verdict": e["verdict"],
            "red_flags": parse_json_field(e.get("red_flags", [])),
            "claims_extracted": parse_json_field(e.get("claims_extracted", [])),
            "evidence_check": e.get("evidence_check", ""),
            "fda_disclaimer_present": bool(e.get("fda_disclaimer_present")),
            "ftc_complaint_ready": bool(e.get("ftc_complaint_ready")),
            "sources": parse_json_field(e.get("sources", [])),
            "verdict_summary": analysis.get("verdict_summary", ""),
        })

    data = {
        "generated": str(Path(__file__).parent / "build_site.py"),
        "total": stats["total_evaluated"],
        "average_score": stats["average_trust_score"],
        "by_verdict": stats["by_verdict"],
        "products": products,
    }

    out_path = Path(__file__).parent / "docs" / "data.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Wrote {len(products)} products to {out_path}")


if __name__ == "__main__":
    build_data()
