# Scam Scanner

AI-powered evaluation database for DTC wellness products. Identifies pseudoscience, hidden drugs, and deceptive marketing using claim extraction, red flag analysis, and cross-referencing against FDA, FTC, and TINA.org enforcement databases.

## Live Site

**[scam-scanner on GitHub Pages](https://josh-stoner.github.io/scam-scanner/)**

## How It Works

1. **Scrape** — Extract product page content, disclaimers, and claims
2. **Analyze** — AI evaluates claims against scientific evidence, identifies red flags, checks mechanism plausibility
3. **Score** — Trust score (0-100) based on evidence quality, claim plausibility, and regulatory history
4. **Cross-reference** — Compare against FDA tainted products database, FTC enforcement actions, and TINA.org investigations

## Verdicts

| Verdict | Score Range | Meaning |
|---------|-----------|---------|
| **LEGIT** | 70-100 | Evidence-supported claims, transparent practices |
| **CAUTION** | 40-69 | Some unsupported claims, proceed carefully |
| **LIKELY SCAM** | 20-39 | Multiple red flags, minimal evidence |
| **SCAM** | 0-19 | Confirmed fraud, hidden drugs, or enforcement action |

## Database

Currently tracking **36 products** across categories:
- Sexual enhancement supplements (hidden prescription drugs)
- Weight loss supplements (hidden controlled substances)
- MLM wellness lines (unsubstantiated health claims)
- Frequency/EMF devices (pseudoscience)
- Detox and menopause supplements

All seeded entries are sourced from federal enforcement actions (FDA Public Notifications, FTC settlements, FDA Warning Letters) and TINA.org investigations.

## CLI Usage

```bash
python scanner.py <url>              # Scan a product URL
python scanner.py --rescan <url>     # Force re-evaluation
python scanner.py --lookup <url>     # Check if already evaluated
python scanner.py --stats            # Database stats
python scanner.py --list             # List all evaluations
python scanner.py --export           # Export as JSON
python scanner.py --sync-sheet       # Export CSV for Google Sheets
```

## Rebuilding the Site

```bash
python build_site.py    # Regenerates docs/data.json from SQLite
```

## Testing

```bash
pytest tests/
```

## Stack

- **Backend**: Python, SQLite, httpx, BeautifulSoup
- **Analysis**: Claude API (Sonnet) for claim extraction and evaluation
- **Frontend**: Static HTML/CSS/JS (no framework)
- **Deployment**: GitHub Pages from `docs/`

## Submit a Product

[Open an issue](https://github.com/josh-stoner/scam-scanner/issues/new) with the product URL and we'll evaluate it.

---

Built by [Josh Stoner](https://josh-stoner.github.io) with Claude Code.
