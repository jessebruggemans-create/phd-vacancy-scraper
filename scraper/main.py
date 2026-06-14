"""Main orchestrator -- runs all scrapers and sends the weekly digest."""
import logging
import os
import sys

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

from scraper.digest import send_digest
from scraper.filter import is_eligible, is_english_or_dutch, is_relevant, keyword_score
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


def main() -> None:
    logger.info("=== PhD Vacancy Scraper -- starting ===")
    os.makedirs("data", exist_ok=True)
    init_db()
    cleanup_old(days=120)

    active_jobs: list[dict] = []

    for scrape_fn in ALL_SCRAPERS:
        name = scrape_fn.__module__.split(".")[-1]
        try:
            raw = scrape_fn()
        except Exception as exc:
            logger.exception("[%s] scraper crashed: %s", name, exc)
            continue

        for job in raw:
            title = job.get("title", "")
            desc  = job.get("description", "")

            # ── Language: English and Dutch only ──────────────────────────────
            if not is_english_or_dutch(title, desc):
                continue

            # ── Eligibility: skip positions requiring an existing PhD ──────────
            if not is_eligible(title):
                continue

            # ── Relevance: topic must match IR/security keywords ──────────────
            # think-tank jobs bypass this (curated source, always on-topic)
            if not job.get("always_include") and not is_relevant(
                title,
                desc,
                job.get("institution", ""),
            ):
                continue

            job["is_new"] = is_new(job["id"])
            upsert_job(job["id"], job["title"], job["url"], job["source"])
            active_jobs.append(job)

    # Deduplicate by job id (same vacancy may appear on multiple sources)
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for job in active_jobs:
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            deduped.append(job)

    # Sort: new first, then by keyword relevance, then title
    deduped.sort(
        key=lambda j: (
            0 if j["is_new"] else 1,
            -keyword_score(j["title"], j.get("description", "")),
            j["title"],
        )
    )

    new_count = sum(1 for j in deduped if j["is_new"])
    logger.info(
        "=== %d active relevant jobs (%d new) ===", len(deduped), new_count
    )
    send_digest(deduped)
    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
