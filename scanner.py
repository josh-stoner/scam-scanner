#!/usr/bin/env python3
"""Scam Scanner — DTC Wellness Product Evaluator.

Inference is performed by Claude Code, not the Anthropic SDK. A scan is a
two-step pipeline:

    1. python scanner.py --prepare <url>
       Scrapes the URL, writes the analysis prompt + page data to .scan-cache/,
       and prints next-step instructions.

    2. python scanner.py --finalize <url>
       Reads the matching analysis JSON Claude Code wrote to .scan-cache/,
       saves the evaluation to SQLite, syncs to Sheets, and prints the verdict.

Other commands:
    python scanner.py --lookup <url>     Check if URL was already evaluated
    python scanner.py --rescan <url>     Re-prepare a URL (forces fresh scrape)
    python scanner.py --stats            Show database stats
    python scanner.py --list             List all evaluations
    python scanner.py --export           Export all evaluations as JSON
    python scanner.py --sync-sheet       Full sync all DB entries to Google Sheet CSV
"""

import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from scraper import scrape_page, normalize_url, extract_domain
from analyzer import build_prompt, parse_response
from db import lookup_url, save_evaluation, get_all_evaluations, get_stats
from config import PROJECT_DIR

CACHE_DIR = PROJECT_DIR / ".scan-cache"


def _slug(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _cache_paths(url: str) -> tuple[Path, Path, Path]:
    CACHE_DIR.mkdir(exist_ok=True)
    s = _slug(url)
    return (
        CACHE_DIR / f"pagedata-{s}.json",
        CACHE_DIR / f"prompt-{s}.txt",
        CACHE_DIR / f"analysis-{s}.json",
    )


def format_verdict(eval_data: dict) -> str:
    score = eval_data.get("trust_score", "?")
    verdict = eval_data.get("verdict", "UNKNOWN")

    if isinstance(score, int):
        if score >= 70:
            color = "\033[92m"
        elif score >= 40:
            color = "\033[93m"
        else:
            color = "\033[91m"
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

    if eval_data.get("verdict_summary"):
        lines.append(f"  {eval_data['verdict_summary']}")
        lines.append("")

    red_flags = eval_data.get("red_flags", [])
    if isinstance(red_flags, str):
        red_flags = json.loads(red_flags)
    if red_flags:
        lines.append(f"  RED FLAGS ({len(red_flags)}):")
        for flag in red_flags:
            lines.append(f"    - {flag}")
        lines.append("")

    claims = eval_data.get("claims_extracted", [])
    if isinstance(claims, str):
        claims = json.loads(claims)
    if claims:
        lines.append(f"  CLAIMS EXTRACTED ({len(claims)}):")
        for claim in claims:
            lines.append(f"    - {claim}")
        lines.append("")

    if eval_data.get("evidence_check"):
        lines.append(f"  EVIDENCE CHECK:")
        lines.append(f"    {eval_data['evidence_check']}")
        lines.append("")

    if eval_data.get("ftc_complaint_ready"):
        lines.append(f"  \033[93mFTC COMPLAINT READY\033[0m")
        if eval_data.get("ftc_complaint_basis"):
            lines.append(f"    Basis: {eval_data['ftc_complaint_basis']}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def prepare_scan(url: str, force: bool = False) -> dict:
    """Scrape URL and write the analysis prompt + page data to .scan-cache/.

    Returns the page_data dict. Prints next-step instructions for Claude Code.
    """
    url = normalize_url(url)
    pagedata_path, prompt_path, analysis_path = _cache_paths(url)

    cached = lookup_url(url)
    if cached and not force:
        print(f"\n  Found cached evaluation from {cached['date_evaluated']}")
        print(format_verdict(cached))
        print(f"\n  To force a fresh scan: python scanner.py --rescan {url}")
        return cached

    print(f"\n  Scraping {url}...")
    page_data = scrape_page(url)
    print(f"  Extracted {len(page_data['body_text'])} chars, {len(page_data['disclaimers'])} disclaimers")

    pagedata_path.write_text(json.dumps(page_data, indent=2, default=str))
    prompt_path.write_text(build_prompt(page_data))

    print(f"\n  Prompt:    {prompt_path}")
    print(f"  Page data: {pagedata_path}")
    print(f"\n  Next steps for Claude Code:")
    print(f"    1. Read the prompt at the path above")
    print(f"    2. Produce the analysis JSON and write it to:")
    print(f"         {analysis_path}")
    print(f"    3. Run: python scanner.py --finalize {url}")
    return page_data


def finalize_scan(url: str) -> dict:
    """Load Claude Code's analysis JSON + cached page data, save to DB, display."""
    url = normalize_url(url)
    pagedata_path, _, analysis_path = _cache_paths(url)

    if not pagedata_path.exists():
        print(f"  No cached page data for {url}. Run --prepare first.")
        sys.exit(1)
    if not analysis_path.exists():
        print(f"  No analysis at {analysis_path}.")
        print(f"  Have Claude Code write the analysis JSON there, then re-run --finalize.")
        sys.exit(1)

    page_data = json.loads(pagedata_path.read_text())
    analysis = parse_response(analysis_path.read_text())

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

    save_evaluation(eval_data)
    print(f"  Saved to database.")

    try:
        from sheets_sync import sync_single_row
        sync_single_row(eval_data)
    except Exception as e:
        print(f"  Sheet sync skipped: {e}")

    eval_data.update({
        "verdict_summary": analysis.get("verdict_summary", ""),
        "ftc_complaint_basis": analysis.get("ftc_complaint_basis", ""),
    })
    print(format_verdict(eval_data))
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

    elif arg == "--lookup":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --lookup <url>")
            sys.exit(1)
        result = lookup_url(normalize_url(sys.argv[2]))
        if result:
            print(format_verdict(result))
        else:
            print(f"\n  No evaluation found for {sys.argv[2]}")

    elif arg == "--prepare":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --prepare <url>")
            sys.exit(1)
        prepare_scan(sys.argv[2])

    elif arg == "--rescan":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --rescan <url>")
            sys.exit(1)
        prepare_scan(sys.argv[2], force=True)

    elif arg == "--finalize":
        if len(sys.argv) < 3:
            print("  Usage: python scanner.py --finalize <url>")
            sys.exit(1)
        finalize_scan(sys.argv[2])

    elif arg == "--sync-sheet":
        from sheets_sync import full_sync_to_csv
        full_sync_to_csv()

    else:
        # Default: bare URL → run prepare step
        prepare_scan(arg)


if __name__ == "__main__":
    main()
