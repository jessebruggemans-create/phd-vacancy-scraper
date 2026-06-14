"""Quick smoke-test for both scrapers. Run: python test_scrapers.py"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(levelname)s %(name)s - %(message)s",
)

from scraper.sources import academic_transfer, euraxess


def show(name, jobs):
    print(f"\n=== {name}: {len(jobs)} jobs ===")
    for j in jobs[:5]:
        print(f"  title:       {j['title'][:70]}")
        print(f"  institution: {j['institution']}")
        print(f"  url:         {j['url'][:80]}")
        print()
    if not jobs:
        print("  (no jobs returned)")


if __name__ == "__main__":
    show("AcademicTransfer", academic_transfer.scrape())
    show("EURAXESS", euraxess.scrape())
