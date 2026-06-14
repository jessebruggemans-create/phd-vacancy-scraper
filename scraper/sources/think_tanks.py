"""Scrapers for security-studies think tanks and research institutes.

Egmont: scrapeable static HTML (currently "no vacancies" but will catch future ones).
Clingendael, HCSS: JS-rendered ATS -- return empty gracefully.
FPI, Asser: small static pages, scrape best-effort.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Egmont Institute (Brussels)
# Static page -- plainly says "no vacancies" when empty; lists jobs as prose
# links or <li> items when positions exist.
# ---------------------------------------------------------------------------
_EGMONT_BASE = "https://egmontinstitute.be"
_EGMONT_URL  = f"{_EGMONT_BASE}/jobs-internships-and-opportunities/"


def _scrape_egmont() -> list[dict]:
    jobs = []
    soup = fetch(_EGMONT_URL)
    if not soup:
        logger.info("[Egmont] 0 listings.")
        return jobs

    content = soup.select_one("main, [class*='content'], [class*='entry'], article")
    if not content:
        content = soup

    page_text = content.get_text().lower()
    if "no vacanc" in page_text or "currently no" in page_text:
        logger.info("[Egmont] no current vacancies.")
        return jobs

    for a in content.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 10:
            continue
        if any(skip in href for skip in ["#", "mailto:", "javascript:", "internship", "subscribe"]):
            continue
        full_url = make_absolute(href, _EGMONT_BASE)
        jobs.append({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "Egmont Institute",
            "location":    "Brussels, BE",
            "deadline":    "",
            "url":         full_url,
            "source":      "Egmont",
            "description": "",
        })

    logger.info("[Egmont] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Clingendael (The Hague) -- redirects to OutSite ATS (JS-rendered)
# We try to extract job links from whatever HTML is served.
# ---------------------------------------------------------------------------
_CLINGENDAEL_VACANCIES = "https://www.careers.clingendael.org/vacancy-jobs/overview-jobs-extern"


def _scrape_clingendael() -> list[dict]:
    """Scrape the Clingendael OutSite vacancy overview page.

    OutSite renders individual vacancy cards in static HTML as <article> or
    <li> elements containing <a> links to job detail pages.
    """
    jobs = []
    soup = fetch(_CLINGENDAEL_VACANCIES)
    if not soup:
        logger.info("[Clingendael] 0 listings.")
        return jobs

    # OutSite / Clingendael careers pages list jobs as links within a listing block.
    # Skip if the body is mostly a shell (JS-rendered).
    if len(soup.get_text()) < 600:
        logger.info("[Clingendael] page appears JS-rendered -- 0 listings.")
        return jobs

    for a in soup.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href.lower() for skip in ["javascript:", "mailto:", "#", "/overview", "locale", "spontan"]):
            continue
        if not any(kw in href.lower() for kw in ["/job/", "/vacanc", "/position", "/opening"]):
            continue
        full_url = make_absolute(href, "https://www.careers.clingendael.org")
        jobs.append({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "Clingendael Institute",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "Clingendael",
            "description": "",
        })

    logger.info("[Clingendael] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# HCSS (The Hague Centre for Strategic Studies)
# ---------------------------------------------------------------------------
_HCSS_URL = "https://hcss.nl/jobs/"


def _scrape_hcss() -> list[dict]:
    """Scrape HCSS job postings.

    HCSS posts vacancies as individual WordPress posts under /jobs/.
    Each post <article> has a title link and excerpt.
    """
    jobs = []
    soup = fetch(_HCSS_URL)
    if not soup:
        logger.info("[HCSS] 0 listings.")
        return jobs

    # WordPress archives list posts as <article> with <h2 class="entry-title">
    for art in soup.select("article"):
        title_el = art.select_one("h2.entry-title a, h1.entry-title a, h3.entry-title a")
        if not title_el:
            continue
        href  = title_el.get("href", "")
        title = clean_text(title_el)
        if not title or len(title) < 5:
            continue
        # Skip category/tag archive links
        if not href or "hcss.nl/jobs/" not in href:
            continue
        desc_el = art.select_one(".entry-content p, .entry-summary p")
        description = clean_text(desc_el)[:220] if desc_el else ""
        full_url = make_absolute(href, "https://hcss.nl")
        jobs.append({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "HCSS",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "HCSS",
            "description": description,
        })

    logger.info("[HCSS] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Flemish Peace Institute (Brussels)
# ---------------------------------------------------------------------------
_FPI_URL = "https://vlaamsvredesinstituut.eu/en/vacancies/"


def _scrape_fpi() -> list[dict]:
    jobs = []
    soup = fetch(_FPI_URL)
    if not soup:
        logger.info("[FPI] 0 listings.")
        return jobs

    main = soup.select_one("main, article, [class*='content']")
    if not main:
        main = soup

    for a in main.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href for skip in ["#", "mailto:", "javascript:", "/about", "/contact", "/news", "/publications"]):
            continue
        if "vlaamsvredesinstituut.eu" not in href and not href.startswith("/"):
            continue
        full_url = make_absolute(href, "https://vlaamsvredesinstituut.eu")
        jobs.append({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "Flemish Peace Institute",
            "location":    "Brussels, BE",
            "deadline":    "",
            "url":         full_url,
            "source":      "Flemish Peace Institute",
            "description": "",
        })

    logger.info("[FPI] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Asser Institute (The Hague) -- international law research
# ---------------------------------------------------------------------------
_ASSER_URL = "https://www.asser.nl/jobs-internships/"


def _scrape_asser() -> list[dict]:
    """Scrape the Asser Institute jobs & internships listing page.

    Individual positions are linked as /jobs-internships/<slug>/ paths.
    """
    jobs = []
    soup = fetch(_ASSER_URL)
    if not soup:
        logger.info("[Asser] 0 listings.")
        return jobs

    for a in soup.select("a[href*='/jobs-internships/']"):
        href  = a.get("href", "")
        title = clean_text(a)
        # Skip the self-link and bare index page links
        if not title or len(title) < 8:
            continue
        if href.rstrip("/").endswith("/jobs-internships"):
            continue
        full_url = make_absolute(href, "https://www.asser.nl")
        jobs.append({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "Asser Institute",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "Asser Institute",
            "description": "",
        })

    logger.info("[Asser] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_egmont, _scrape_clingendael, _scrape_hcss, _scrape_fpi, _scrape_asser):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[think_tanks] %s crashed: %s", fn.__name__, exc)
    return all_jobs
