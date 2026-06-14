"""Quick smoke-test for all scrapers. Run: python test_scrapers.py [scraper_name]"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(levelname)s %(name)s - %(message)s",
)

from scraper.sources import academic_transfer, euraxess, universities_be, universities_nl, think_tanks

ALL = {
    "academic_transfer": academic_transfer.scrape,
    "euraxess":          euraxess.scrape,
    "universities_be":   universities_be.scrape,
    "universities_nl":   universities_nl.scrape,
    "think_tanks":       think_tanks.scrape,
}

target = sys.argv[1].lower() if len(sys.argv) > 1 else None


def show(name, jobs):
    print(f"\n{'='*60}")
    print(f"  {name}: {len(jobs)} jobs")
    print('='*60)
    for j in jobs[:5]:
        print(f"  title:       {j['title'][:70]}")
        print(f"  institution: {j['institution']}")
        print(f"  url:         {j['url'][:80]}")
        print()
    if not jobs:
        print("  (no jobs returned)")


for name, fn in ALL.items():
    if target and target not in name:
        continue
    show(name, fn())
