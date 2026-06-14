"""SQLite-backed deduplication layer.

The database lives at data/seen_jobs.db and is cached between GitHub Actions
runs so each Monday's digest only contains genuinely new listings.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta

from scraper.config import DB_PATH

logger = logging.getLogger(__name__)


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Create the table if it doesn't exist."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id      TEXT PRIMARY KEY,
                title       TEXT,
                url         TEXT,
                source      TEXT,
                first_seen  TEXT
            )
        """)


def is_seen(job_id: str) -> bool:
    """Return True if this job has been sent in a previous digest."""
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None


def mark_seen(job_id: str, title: str, url: str, source: str) -> None:
    """Record that this job has been sent."""
    with _conn() as con:
        con.execute(
            """
            INSERT OR IGNORE INTO seen_jobs (job_id, title, url, source, first_seen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, title, url, source, datetime.utcnow().isoformat()),
        )


def cleanup_old(days: int = 120) -> None:
    """Remove entries older than *days* to keep the DB small."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _conn() as con:
        deleted = con.execute(
            "DELETE FROM seen_jobs WHERE first_seen < ?", (cutoff,)
        ).rowcount
    if deleted:
        logger.info("Pruned %d entries older than %d days.", deleted, days)
