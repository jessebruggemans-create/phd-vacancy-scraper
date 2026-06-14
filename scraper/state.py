"""SQLite-backed job tracking.

Stores every relevant job with first_seen and last_seen timestamps.
Each run upserts all found jobs (updating last_seen), so the digest
can distinguish genuinely new listings from ones already reported.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta

from scraper.config import DB_PATH

logger = logging.getLogger(__name__)

_RUN_TS = datetime.utcnow().isoformat()  # single timestamp for this run


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id      TEXT PRIMARY KEY,
                title       TEXT,
                url         TEXT,
                source      TEXT,
                first_seen  TEXT,
                last_seen   TEXT
            )
        """)
        # Migrate: add last_seen if the DB was created by an older version
        cols = {r[1] for r in con.execute("PRAGMA table_info(seen_jobs)")}
        if "last_seen" not in cols:
            con.execute("ALTER TABLE seen_jobs ADD COLUMN last_seen TEXT")
            con.execute("UPDATE seen_jobs SET last_seen = first_seen WHERE last_seen IS NULL")


def is_new(job_id: str) -> bool:
    """Return True if this job has never been recorded before."""
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is None


def upsert_job(job_id: str, title: str, url: str, source: str) -> None:
    """Insert a new job or update last_seen for a known one."""
    with _conn() as con:
        con.execute(
            """
            INSERT INTO seen_jobs (job_id, title, url, source, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                title     = excluded.title
            """,
            (job_id, title, url, source, _RUN_TS, _RUN_TS),
        )


def cleanup_old(days: int = 120) -> None:
    """Remove entries not seen in *days* to keep the DB small."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _conn() as con:
        deleted = con.execute(
            "DELETE FROM seen_jobs WHERE last_seen < ?", (cutoff,)
        ).rowcount
    if deleted:
        logger.info("Pruned %d entries not seen in %d days.", deleted, days)
