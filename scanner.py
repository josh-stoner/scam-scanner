#!/usr/bin/env python3
"""Scam Scanner — DTC Wellness Product Evaluator.

Usage:
    python scanner.py <url>              Scan a product URL (cached if already evaluated)
    python scanner.py --rescan <url>     Force re-evaluation and compare to previous score
    python scanner.py --lookup <url>     Check if URL was already evaluated
    python scanner.py --stats            Show database stats
    python scanner.py --list             List all evaluations
    python scanner.py --export           Export all evaluations as JSON
    python scanner.py --sync-sheet       Full sync all DB entries to Google Sheet CSV
"""

import sys
import json
from datetime import datetime, timezone

from scraper import scrape_page, normalize_url, extract_domain
from analyzer import analyze_page
from db import lookup_url, lookup_domain, save_evaluation, get_all_evaluations, get_stats


def format_verdict(eval_data: dict) -> str:
    """Format an evaluation for terminal display."""
    score = eval_data.get("trust_score", "?")
    verdict = eval_data.get("verdict", "UNKNOWN")

    # Color coding for terminal
    if isinstance(score, int):
        if score >= 70:
            color = "\033[92m"  # green
        elif score >= 40:
            color = "\033[93m"  # yellow
        else:
            color = "\033[91m"  # red
    else:
        color = "\033[0m"
    reset = "\033[0m"

    lines = [
        "",
        f"{'=' * 60}",
        f"  SCAM SCANNER REPORT",
        f"{'=' * 60}",
        f"",
        f"  URL:      {eval_data.get('url', 'N/A')}",
        f"  Product:  {eval_data.get('product_name', 'N/A')}",
        f"  Category: {eval_data.get('category', 'N/A')}",
        f"  Date:     {eval_data.get('date_evaluated', 'N/A')}",
        f"",
        f"  {color}TRUST SCORE: {score}/100{reset}",
        f"  {color}VERDICT: {verdict}{reset}",
        f"",
    ]

    # Verdict summary
    if eval_data.get("verdict_summary"):
        lines.append(f"  {eval_data['verdict_summary']}")
        lines.append("")

    # Red flags
    red_flags = eval_data.get("red_flags", [])
    if isinstance(red_flags, str):
        red_flags = json.loads(red_flags)
    if red_flags:
        lines.append(f"  RED FLAGS ({len(red_flags)}):")
        for flag in red_flags:
            lines.append(f"    - {flag}")
        lines.append("")

    # Claims
    claims = eval_data.get("claims_extracted", [])
    if isinstance(claims, str):
        claims = json.loads(claims)
    if claims:
        lines.append(f"  CLAIMS EXTRACTED ({len(claims)}):")
        for claim in claims:
            lines.append(f"    - {claim}")
        lines.append("")

    # Evidence
    if eval_data.get("evidence_check"):
        lines.append(f"  EVIDENCE CHECK:")
        lines.append(f"    {eval_data['evidence_check']}")
        lines.append("")

    # FTC
    if eval_data.get("ftc_complaint_ready"):
        lines.append(f"  \033[93mFTC COMPLAINT READY\033[0m")
        if eval_data.get("ftc_complaint_basis"):
            lines.append(f"    Basis: {eval_data['ftc_complaint_basis']}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def scan_url(url: str, rescan: bool = False) -> dict:
    """Full scan pipeline: check cache -> scrape -> analyze -> store -> return.

    If rescan=True, skips cache and forces a fresh evaluation.
    The old score is preserved for comparison.
    """
    url = normalize_url(url)

    # Check cache first (unless rescan forced)
    cached = lookup_url(url)
    if cached and not rescan:
        print(f"\n  Found cached evaluation from {cached['date_evaluated']}")
        print(format_verdict(cached))
        return cached

    if cached and rescan:
        print(f"\n  Re-scanning (previous: {cached['trust_score']}/100 on {cached['date_evaluated']})")

    # Scrape
    print(f"\n  Scraping {url}...")
    page_data = scrape_page(url)
    print(f"  Extracted {len(page_data['body_text'])} chars, {len(page_data['disclaimers'])} disclaimers")

    # Analyze
    print(f"  Analyzing claims with {__import__('config').MODEL}...")
    analysis = analyze_page(page_data)

    # Build evaluation record
    eval_data = {
        "url": url,
        "domain": extract_domain(url),
        "product_name": analysis.get("product_name", ""),
        "date_evaluated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "trust_score": analysis.get("trust_score", 0),
        "verdict": analysis.get("verdict", "UNKNOWN"),
        "category": analysis.get("category", ""),
        "red_flags": analysis.get("red_flags", []),
        "claims_extracted": analysis.get("claims_extracted", []),
        "evidence_check": analysis.get("evidence_check", ""),
        "fda_disclaimer_present": 1 if analysis.get("fda_disclaimer_present") else 0,
        "ftc_complaint_ready": 1 if analysis.get("ftc_complaint_ready") else 0,
        "sources": [],
        "raw_page_text": page_data["body_text"][:5000],
        "analysis_json": json.dumps(analysis, indent=2),
    }

    # Store
    save_evaluation(eval_data)
    print(f"  Saved to database.")

    # Auto-sync to Google Sheet
    try:
        from sheets_sync import sync_single_row
        sync_single_row(eval_data)
    except Exception as e:
        print(f"  Sheet sync skipped: {e}")

    # Display
    # Merge analysis fields for display
    eval_data.update({
        "verdict_summary": analysis.get("verdict_summary", ""),
        "ftc_complaint_basis": analysis.get("ftc_complaint_basis", ""),
    })
    print(format_verdict(eval_data))

    # Show score change on rescan
    if cached and rescan:
        old_score = cached.get("trust_score", "?")
        new_score = eval_data.get("trust_score", "?")
        old_verdict = cached.get("verdict", "?")
        new_verdict = eval_data.get("verdict", "?")
        if old_score != new_score or old_verdict != new_verdict:
            print(f"\n  CHANGE DETECTED:")
            print(f"    Score: {old_score} -> {new_score}")
            print(f"    Verdict: {old_verdict} -> {new_verdict}")
        else:
            print(f"\n  No change from previous evaluation.")

    return eval_data


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--stats":
        stats = get_stats()
        print(f"\n  Total evaluated: {stats['total_evaluated']}")
        print(f"  Average trust score: {stats['average_trust_score']}")
        print(f"  By verdict: {json.dumps(stats['by_verdict'], indent=4)}")

    elif arg == "--list":
        evals = get_all_evaluations()
        if not evals:
            print("\n  No evaluations yet. Scan a URL to get started.")
            return
        print(f"\n  {'URL':<40} {'Score':>5}  {'Verdict':<12} {'Date'}")
        print(f"  {'-'*40} {'-'*5}  {'-'*12} {'-'*10}")
        for e in evals:
            url_short = e['url'][:40]
            print(f"  {url_short:<40} {e['trust_score']:>5}  {e['verdict']:<12} {e['date_evaluated']}")

    elif arg == "--export":
        evals = get_all_evaluations()
        print(json.dumps(evals, indent=2, default=str))

    elif arg == "--rescan":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --rescan <url>")
            sys.exit(1)
        scan_url(sys.argv[2], rescan=True)

    elif arg == "--lookup":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --lookup <url>")
            sys.exit(1)
        result = lookup_url(normalize_url(sys.argv[2]))
        if result:
            print(format_verdict(result))
        else:
            print(f"\n  No evaluation found for {sys.argv[2]}")

    elif arg == "--sync-sheet":
        from sheets_sync import full_sync_to_csv
        full_sync_to_csv()

    else:
        scan_url(arg)


if __name__ == "__main__":
    main()
