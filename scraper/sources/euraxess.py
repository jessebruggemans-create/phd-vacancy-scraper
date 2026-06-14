"""Scraper for EURAXESS - EU research mobility portal.

EURAXESS uses ECL (Europa Component Library) markup. We scrape the filtered
HTML search page directly (the RSS feed has been discontinued).
Covers Belgium (BE), Netherlands (NL), Germany (DE) and France (FR).
"""
import logging
import re as _re

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)

BASE = "https://euraxess.ec.europa.eu"

# Map full country names (as returned by EURAXESS) to 2-letter codes.
_COUNTRY_MAP = {
    "netherlands": "NL",
    "belgium": "BE",
    "germany": "DE",
    "france": "FR",
}


def _parse_location(secondary_meta_text: str) -> str:
    """Extract the 2-letter country code from EURAXESS secondary-meta text.

    The field looks like:
        "Work Locations:Number of offers: 1, Netherlands, Wageningen University & Research, ..."
    We extract only the country name (first token after "Number of offers: N,") and map
    it to a 2-letter code.  The institution already appears in the institution field, so
    we avoid duplicating it in location.
    """
    m = _re.search(
        r"Number of offers:\s*\d+,\s*([^,]+)",
        secondary_meta_text,
        _re.IGNORECASE,
    )
    if m:
        country_name = m.group(1).strip().lower()
        code = _COUNTRY_MAP.get(country_name)
        if code:
            return code
    # Fallback: scan for known country names
    lower = secondary_meta_text.lower()
    for name, code in _COUNTRY_MAP.items():
        if name in lower:
            return code
    return "Europe"


# Covers Belgium, Netherlands, Germany and France.
# Add more country_id params here to expand scope further.
SEARCH_URL = (
    f"{BASE}/jobs/search"
    "?country_id%5B%5D=BE"
    "&country_id%5B%5D=NL"
    "&country_id%5B%5D=DE"
    "&country_id%5B%5D=FR"
    "&type_of_jobs%5B%5D=phd-scholarship-fellowship"
)


def _parse_html(soup) -> list[dict]:
    """Parse the EURAXESS ECL-based HTML search results page."""
    jobs = []

    # Job cards use class="ecl-content-item"; the first <article> on the page
    # is the filter sidebar wrapper and has no class — skip it.
    cards = soup.select("article.ecl-content-item")

    for card in cards:
        # ── Title + URL ───────────────────────────────────────────────────────
        title_a = card.select_one("h3.ecl-content-block__title a")
        if not title_a:
            continue
        url = make_absolute(title_a.get("href", ""), BASE)
        title = clean_text(title_a)
        if not title:
            continue

        # ── Institution ───────────────────────────────────────────────────────
        # First <li> in the primary meta list links to the organisation profile.
        inst_li = card.select_one(
            "ul.ecl-content-block__primary-meta-container "
            "li.ecl-content-block__primary-meta-item:first-child"
        )
        institution = clean_text(inst_li) if inst_li else ""

        # ── Deadline ──────────────────────────────────────────────────────────
        dl_el = card.select_one("[class*='deadline'], [class*='date'], time")
        deadline = clean_text(dl_el) if dl_el else ""

        # ── Location (country + city from secondary meta) ─────────────────────
        sec_li = card.select_one(
            "ul.ecl-content-block__secondary-meta-container "
            "li.ecl-content-block__secondary-meta-item:first-child"
        )
        location = _parse_location(clean_text(sec_li)) if sec_li else "Europe"

        # ── Short description ─────────────────────────────────────────────────
        desc_el = card.select_one("div.ecl-content-block__description p")
        description = clean_text(desc_el)[:220] if desc_el else ""

        jobs.append({
            "id":          job_id(title, url),
            "title":       title,
            "institution": institution,
            "location":    location,
            "deadline":    deadline,
            "url":         url,
            "source":      "EURAXESS",
            "description": description,
        })

    return jobs


def scrape() -> list[dict]:
    """Scrape the EURAXESS filtered search page for PhD positions in NL/BE.

    EURAXESS uses &page=N (0-indexed) URL parameter for pagination;
    there is no rel=next link in the HTML.
    """
    all_jobs: list[dict] = []
    seen_ids: set[str] = set()
    max_pages = 100  # EURAXESS returns ~10 cards/page; 100 pages = 1,000 max listings

    for page_num in range(max_pages):
        if page_num == 0:
            url = SEARCH_URL
        else:
            url = f"{SEARCH_URL}&page={page_num}"

        logger.info("[EURAXESS] page %d -> %s", page_num + 1, url)
        soup = fetch(url)
        if soup is None:
            break

        jobs = _parse_html(soup)
        if not jobs:
            break

        new_ids = {j["id"] for j in jobs}
        if new_ids <= seen_ids:
            break  # repeated page -- stop
        seen_ids |= new_ids
        all_jobs.extend(jobs)

    logger.info("[EURAXESS] collected %d listings.", len(all_jobs))
    return all_jobs
