"""Scrapers for German universities.

Confirmed working:
  Tübingen     -- uni-tuebingen.de RSS feed (/en/university/careers/job-vacancies/feed.xml)
                  Publishes English-language positions in all faculties.

JS-rendered / blocked / no suitable public listing (appear in MANUAL_PORTALS):
  FU Berlin    -- jobs.fu-berlin.de (German-language RSS only)
  HU Berlin    -- JS-rendered, bot-protection
  Potsdam      -- no working jobs page found
  Goethe Frankfurt  -- 404 on main listings
  LMU Munich   -- 404 on main listings
  Helmut Schmidt HSU  -- no jobs currently, RSS empty
  Bundeswehr Munich   -- faculty pages require login
  Cologne      -- JS-rendered
  Mannheim     -- 404
  Konstanz     -- JS-rendered
"""
import logging
import re
import xml.etree.ElementTree as ET

from scraper.utils import clean_text, fetch_raw, job_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# University of Tübingen -- English RSS feed
# Feed URL: uni-tuebingen.de/en/university/careers/job-vacancies/feed.xml
# Items are English-language (confirmed: 11 EN items in June 2026 test).
# We rely on the keyword relevance filter for topic matching.
# ---------------------------------------------------------------------------
_TUEBINGEN_RSS = (
    "https://uni-tuebingen.de/en/university/careers/job-vacancies/feed.xml"
)


def _scrape_tuebingen() -> list[dict]:
    jobs: list[dict] = []
    raw = fetch_raw(_TUEBINGEN_RSS)
    if not raw:
        logger.info("[Tübingen] 0 listings (feed unavailable).")
        return jobs

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        logger.warning("[Tübingen] RSS parse error: %s", exc)
        return jobs

    # Support both RSS 2.0 (<item>) and Atom (<entry>)
    ns_atom = "http://www.w3.org/2005/Atom"
    items = root.findall(".//item")
    if not items:
        items = root.findall(f".//{{{ns_atom}}}entry")

    for item in items:
        # Title
        title_el = item.find("title")
        if title_el is None:
            title_el = item.find(f"{{{ns_atom}}}title")
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Link
        link_el = item.find("link")
        if link_el is None:
            link_el = item.find(f"{{{ns_atom}}}link")
        if link_el is not None:
            link = (link_el.text or link_el.get("href", "")).strip()
        else:
            link = ""

        # Description / summary for keyword matching
        desc_el = item.find("description")
        if desc_el is None:
            desc_el = item.find(f"{{{ns_atom}}}summary")
        description = (desc_el.text or "").strip()[:220] if desc_el is not None else ""

        # Publication date
        pub_el = item.find("pubDate")
        if pub_el is None:
            pub_el = item.find(f"{{{ns_atom}}}updated")
        pub_date = (pub_el.text or "")[:10] if pub_el is not None else ""

        if not title or not link:
            continue

        jobs.append({
            "id":          job_id(title, link),
            "title":       title,
            "institution": "University of Tübingen",
            "location":    "Tübingen, DE",
            "deadline":    pub_date,
            "url":         link,
            "source":      "Tübingen",
            "description": description,
        })

    logger.info("[Tübingen] %d listings from RSS.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_tuebingen,):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[universities_de] %s crashed: %s", fn.__name__, exc)
    return all_jobs
