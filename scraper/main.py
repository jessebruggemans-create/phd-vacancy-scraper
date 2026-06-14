"""Main orchestrator — runs all scrapers and sends the weekly digest."""
import logging
import os
import sys

# Load .env for local development (no-op in GitHub Actions where secrets are env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from scraper.digest import send_digest
from scraper.filter import is_relevant, keyword_score
from scraper.state import cleanup_old, init_db, is_seen, mark_seen

# ── Source scrapers ───────────────────────────────────────────────────────────
# Uncomment each module as we build it in subsequent steps.
from scraper.sources import academic_transfer, euraxess

# from scraper.sources import universities_be  # Step 3
# from scraper.sources import universities_nl  # Step 4
# from scraper.sources import departments      # Step 5
# from scraper.sources import think_tanks      # Step 5

ALL_SCRAPERS = [
    academic_transfer.scrape,
    euraxess.scrape,
    # universities_be.scrape,
    # universities_nl.scrape,
    # departments.scrape,
    # think_tanks.scrape,
]


def main() -> None:
    logger.info("=== PhD Vacancy Scraper — starting ===")
    os.makedirs("data", exist_ok=True)
    init_db()
    cleanup_old(days=120)

    new_jobs: list[dict] = []

    for scrape_fn in ALL_SCRAPERS:
        name = scrape_fn.__module__.split(".")[-1]
        try:
            raw = scrape_fn()
        except Exception as exc:
            logger.exception("[%s] scraper crashed: %s", name, exc)
            continue

        for job in raw:
            if not is_relevant(
                job.get("title", ""),
                job.get("description", ""),
                job.get("institution", ""),
            ):
                continue
            if is_seen(job["id"]):
                continue

            mark_seen(job["id"], job["title"], job["url"], job["source"])
            new_jobs.append(job)

    # Sort by relevance score (most keyword matches first), then title
    new_jobs.sort(
        key=lambda j: (-keyword_score(j["title"], j.get("description", "")), j["title"])
    )

    logger.info("=== %d new relevant jobs found ===", len(new_jobs))
    send_digest(new_jobs)
    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
