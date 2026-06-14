"""Scraper for EURAXESS - EU research mobility portal.

EURAXESS uses ECL (Europa Component Library) markup. We scrape the filtered
HTML search page directly (the RSS feed has been discontinued).
Country codes: BE = Belgium, NL = Netherlands.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)

BASE = "https://euraxess.ec.europa.eu"

SEARCH_URL = (
    f"{BASE}/jobs/search"
    "?country_id%5B%5D=BE"
    "&country_id%5B%5D=NL"
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

        # ── Short description ─────────────────────────────────────────────────
        desc_el = card.select_one("div.ecl-content-block__description p")
        description = clean_text(desc_el)[:220] if desc_el else ""

        jobs.append({
            "id":          job_id(title, url),
            "title":       title,
            "institution": institution,
            "location":    "BE / NL",
            "deadline":    deadline,
            "url":         url,
            "source":      "EURAXESS",
            "description": description,
        })

    return jobs


def scrape() -> list[dict]:
    """Scrape the EURAXESS filtered search page for PhD positions in NL/BE."""
    all_jobs: list[dict] = []
    url: str | None = SEARCH_URL
    page = 0
    max_pages = 10

    while url and page < max_pages:
        page += 1
        logger.info("[EURAXESS] page %d -> %s", page, url)
        soup = fetch(url)
        if soup is None:
            break

        jobs = _parse_html(soup)
        if not jobs and page > 1:
            break

        all_jobs.extend(jobs)

        # Next-page link (ECL pagination uses rel="next" or aria-label="Next page")
        next_a = soup.select_one(
            "a[rel='next'], "
            "[class*='ecl-pagination'] a[aria-label*='Next'], "
            "[class*='pager'] a[title='Go to next page']"
        )
        if next_a and next_a.get("href"):
            url = make_absolute(next_a["href"], BASE)
        else:
            url = None

    logger.info("[EURAXESS] collected %d listings.", len(all_jobs))
    return all_jobs
