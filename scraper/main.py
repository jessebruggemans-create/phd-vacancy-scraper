"""Main orchestrator -- runs all scrapers and sends the weekly digest."""
import logging
import os
import sys
from difflib import SequenceMatcher

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from scraper.digest import send_digest, send_failure_alert
from scraper.filter import (
    detect_funding,
    is_eligible,
    is_english_or_dutch,
    is_relevant,
    is_social_science,
    is_wrong_department,
    keyword_score,
)
from scraper.state import cleanup_old, init_db, is_new, upsert_job

from scraper.sources import academic_transfer, euraxess
from scraper.sources import universities_be, universities_nl, universities_de, think_tanks

ALL_SCRAPERS = [
    academic_transfer.scrape,
    euraxess.scrape,
    universities_be.scrape,
    universities_nl.scrape,
    universities_de.scrape,
    think_tanks.scrape,
]


# ── Cross-source deduplication ────────────────────────────────────────────────
# Aggregator sources where the same vacancy may also appear on the
# university's own page.  When a duplicate is found we prefer the direct URL.
_AGGREGATOR_SOURCES = {"AcademicTransfer", "EURAXESS"}

# Common words that appear in virtually every institution name and should be
# ignored when checking whether two institution names refer to the same place.
_INST_STOPWORDS = {
    "university", "universiteit", "universität", "institute", "institution",
    "school", "college", "faculty", "centre", "center", "academy",
    "hochschule", "research", "national", "european", "international",
    "foundation", "stiftung", "the", "and", "van", "voor", "voor", "und",
}


def _sig_words(text: str) -> set[str]:
    return {
        w.lower() for w in text.split()
        if len(w) > 3 and w.lower() not in _INST_STOPWORDS
    }


def _institutions_match(a: str, b: str) -> bool:
    """Return True if two institution names likely refer to the same place."""
    wa, wb = _sig_words(a), _sig_words(b)
    if not wa or not wb:
        return True   # unknown name → assume possible duplicate
    return bool(wa & wb)


def _title_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _cross_deduplicate(jobs: list[dict]) -> list[dict]:
    """Remove cross-source duplicates: same title (≥80% similar) + same institution.

    When choosing which copy to keep:
    1. Direct university URL beats aggregator (AcademicTransfer / EURAXESS).
    2. Among ties: prefer the entry with more complete information
       (non-empty description + deadline score).
    """
    n = len(jobs)
    removed: set[int] = set()

    for i in range(n):
        if i in removed:
            continue
        for j in range(i + 1, n):
            if j in removed:
                continue
            ja, jb = jobs[i], jobs[j]

            # Same source is already deduplicated by job_id; skip
            if ja["source"] == jb["source"]:
                continue

            # Title similarity gate
            if _title_sim(ja["title"], jb["title"]) < 0.80:
                continue

            # Institution match gate
            if not _institutions_match(
                ja.get("institution", ""), jb.get("institution", "")
            ):
                continue

            # Duplicate confirmed — decide which to keep
            agg_a = ja["source"] in _AGGREGATOR_SOURCES
            agg_b = jb["source"] in _AGGREGATOR_SOURCES

            if agg_b and not agg_a:
                removed.add(j)
            elif agg_a and not agg_b:
                removed.add(i)
                break
            else:
                # Both aggregators or both direct — keep the more complete entry
                score_a = bool(ja.get("description")) + bool(ja.get("deadline"))
                score_b = bool(jb.get("description")) + bool(jb.get("deadline"))
                if score_b > score_a:
                    removed.add(i)
                    break
                else:
                    removed.add(j)

    kept = [j for k, j in enumerate(jobs) if k not in removed]
    n_removed = n - len(kept)
    if n_removed:
        logger.info("Cross-source dedup removed %d duplicate(s).", n_removed)
    return kept


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("=== PhD Vacancy Scraper -- starting ===")
    os.makedirs("data", exist_ok=True)
    init_db()
    cleanup_old(days=120)

    active_jobs: list[dict] = []

    # Per-source health tracking
    # Key: job["source"] string (e.g. "AcademicTransfer", "Utrecht University")
    # Value: {"status": "ok"|"error", "raw": N, "accepted": N, "error": str}
    source_health: dict[str, dict] = {}

    for scrape_fn in ALL_SCRAPERS:
        module_name = scrape_fn.__module__.split(".")[-1]
        try:
            raw = scrape_fn()
        except Exception as exc:
            logger.exception("[%s] scraper crashed: %s", module_name, exc)
            source_health[f"[{module_name} CRASHED]"] = {
                "status": "error",
                "raw": 0,
                "accepted": 0,
                "error": str(exc)[:200],
            }
            continue

        # Tally raw counts per source name
        for job in raw:
            src = job.get("source", module_name)
            if src not in source_health:
                source_health[src] = {"status": "ok", "raw": 0, "accepted": 0}
            source_health[src]["raw"] += 1

        # ── Filter chain ──────────────────────────────────────────────────────
        for job in raw:
            title = job.get("title", "")
            desc  = job.get("description", "")
            inst  = job.get("institution", "")
            src   = job.get("source", module_name)
            always = job.get("always_include", False)

            # Department proxy: if description is short (≤120 chars) it's
            # typically a department name (e.g. UGent), not a full description.
            # Used ONLY for the department EXCLUSION check to avoid false
            # positives (e.g. "bioterrorism" in a security-studies description).
            dept_proxy = desc if len(desc) <= 120 else ""

            # Aggregator sources (AcademicTransfer, EURAXESS) already apply
            # their own keyword/topic filtering upstream; we skip the social-
            # sciences inclusion check for them and rely on is_relevant instead.
            is_aggregator = src in _AGGREGATOR_SOURCES

            # 1. Department exclusion — applies to ALL sources
            if is_wrong_department(title, inst, dept_proxy):
                continue

            # 2. Social-sciences inclusion — skipped for aggregators and
            #    always_include sources.  For direct scrapers we check title,
            #    institution AND the full description (catches e.g. UGent posts
            #    where the field is in the description snippet, not the title).
            if not always and not is_aggregator and not is_social_science(title, inst, desc):
                continue

            # 3. Language: English / Dutch only
            if not is_english_or_dutch(title, desc):
                continue

            # 4. Eligibility: position must be open to master's graduates
            if not is_eligible(title):
                continue

            # 5. Keyword relevance — skipped for always_include sources
            if not always and not is_relevant(title, desc, inst):
                continue

            # ── Enrich job with computed fields ───────────────────────────────
            job["keyword_count"] = keyword_score(title, desc)
            job["funding"]       = detect_funding(desc)
            job["is_new"]        = is_new(job["id"])

            upsert_job(job["id"], title, job["url"], src)
            active_jobs.append(job)
            source_health[src]["accepted"] += 1

    # ── Cross-source deduplication ────────────────────────────────────────────
    active_jobs = _cross_deduplicate(active_jobs)

    # ── Final ID-level dedup (safety net) ────────────────────────────────────
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for job in active_jobs:
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            deduped.append(job)

    new_count = sum(1 for j in deduped if j["is_new"])
    logger.info(
        "=== %d active relevant jobs (%d new) after all filters ===",
        len(deduped), new_count,
    )

    # ── Send regular digest ───────────────────────────────────────────────────
    send_digest(deduped, source_health)

    # ── Failure alert ─────────────────────────────────────────────────────────
    total_raw  = sum(h["raw"]  for h in source_health.values())
    n_failed   = sum(1 for h in source_health.values() if h["status"] == "error")
    n_sources  = len(source_health)
    threshold  = n_sources // 2 if n_sources else 0

    if total_raw == 0 or n_failed > threshold:
        logger.warning(
            "Alert condition: total_raw=%d, failed=%d/%d", total_raw, n_failed, n_sources
        )
        send_failure_alert(source_health)

    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
