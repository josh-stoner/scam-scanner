"""Scam Scanner configuration."""

import os
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "scam_scanner.db"

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"

# Google Sheets (optional — falls back to SQLite-only if not configured)
GOOGLE_SHEET_ID = os.environ.get("SCAM_SCANNER_SHEET_ID", "")
GOOGLE_CREDS_PATH = os.environ.get("SCAM_SCANNER_GOOGLE_CREDS", "")

# Scoring
RED_FLAG_PATTERNS = [
    "quantum",
    "frequency healing",
    "EMF protection",
    "detox",
    "alkaline",
    "negative ions",
    "scalar energy",
    "orgone",
    "NASA studied",
    "ancient wisdom",
    "vibrational",
    "grounding",
    "chakra",
    "bio-field",
    "cellular regeneration",
    "toxin removal",
    "immune boost",
    "miracle cure",
    "clinically proven",  # without citation
    "doctor recommended",  # without naming doctors
    "100% natural",
    "no side effects",
    "works instantly",
    "FDA disclaimer present but health claims made",
]

# Trust score thresholds
SCORE_LEGIT = 70       # 70-100: Appears legitimate
SCORE_CAUTION = 40     # 40-69: Proceed with caution
SCORE_SCAM = 0         # 0-39: Likely pseudoscience/scam
