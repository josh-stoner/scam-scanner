"""SQLite database layer for Scam Scanner."""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            domain TEXT NOT NULL,
            product_name TEXT,
            date_evaluated TEXT NOT NULL,
            trust_score INTEGER,
            verdict TEXT,
            category TEXT,
            red_flags TEXT,           -- JSON array
            claims_extracted TEXT,    -- JSON array
            evidence_check TEXT,
            fda_disclaimer_present INTEGER,
            ftc_complaint_ready INTEGER,
            sources TEXT,             -- JSON array
            raw_page_text TEXT,
            analysis_json TEXT,       -- full LLM response
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS red_flag_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE NOT NULL,
            category TEXT,
            severity TEXT DEFAULT 'medium',
            description TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_evaluations_domain ON evaluations(domain);
        CREATE INDEX IF NOT EXISTS idx_evaluations_trust_score ON evaluations(trust_score);
        CREATE INDEX IF NOT EXISTS idx_evaluations_date ON evaluations(date_evaluated);
    """)
    conn.commit()
    conn.close()


def lookup_url(url: str) -> dict | None:
    """Check if URL has already been evaluated. Returns row dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM evaluations WHERE url = ? OR url = ?",
        (url, url.rstrip("/"))
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        for field in ("red_flags", "claims_extracted", "sources"):
            if result.get(field):
                result[field] = json.loads(result[field])
        return result
    return None


def lookup_domain(domain: str) -> list[dict]:
    """Find all evaluations for a domain."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM evaluations WHERE domain = ? ORDER BY date_evaluated DESC",
        (domain,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_evaluation(data: dict):
    """Insert or update an evaluation."""
    now = datetime.now(timezone.utc).isoformat()
    for field in ("red_flags", "claims_extracted", "sources"):
        if isinstance(data.get(field), list):
            data[field] = json.dumps(data[field])

    conn = get_connection()
    conn.execute("""
        INSERT INTO evaluations (
            url, domain, product_name, date_evaluated, trust_score, verdict,
            category, red_flags, claims_extracted, evidence_check,
            fda_disclaimer_present, ftc_complaint_ready, sources,
            raw_page_text, analysis_json, created_at, updated_at
        ) VALUES (
            :url, :domain, :product_name, :date_evaluated, :trust_score, :verdict,
            :category, :red_flags, :claims_extracted, :evidence_check,
            :fda_disclaimer_present, :ftc_complaint_ready, :sources,
            :raw_page_text, :analysis_json, :created_at, :updated_at
        )
        ON CONFLICT(url) DO UPDATE SET
            trust_score = :trust_score,
            verdict = :verdict,
            red_flags = :red_flags,
            claims_extracted = :claims_extracted,
            evidence_check = :evidence_check,
            analysis_json = :analysis_json,
            updated_at = :updated_at
    """, {
        **data,
        "created_at": now,
        "updated_at": now,
    })
    conn.commit()
    conn.close()


def get_all_evaluations() -> list[dict]:
    """Return all evaluations, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM evaluations ORDER BY date_evaluated DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Return summary stats."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
    avg_score = conn.execute("SELECT AVG(trust_score) FROM evaluations").fetchone()[0]
    by_verdict = conn.execute(
        "SELECT verdict, COUNT(*) as cnt FROM evaluations GROUP BY verdict"
    ).fetchall()
    conn.close()
    return {
        "total_evaluated": total,
        "average_trust_score": round(avg_score, 1) if avg_score else 0,
        "by_verdict": {r["verdict"]: r["cnt"] for r in by_verdict},
    }


# Auto-init on import
init_db()
