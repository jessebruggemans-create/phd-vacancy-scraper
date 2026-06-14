"""Scraper for AcademicTransfer.com.

AcademicTransfer is a Nuxt.js SPA: only the first 10 results are server-rendered;
there is no working page-number parameter. We work around this by running a set
of targeted keyword searches that each return the top 10 most relevant results,
then merging and deduplicating the results.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)

BASE = "https://www.academictransfer.com"

# Each search returns the 10 best-matching NL/BE jobs for that query.
# Together they cover the full breadth of our keyword list.
SEARCHES = [
    "phd",
    "international+relations",
    "security+studies",
    "political+science",
    "peace+conflict",
    "governance+policy",
    "defence+military",
    "european+security",
    "terrorism+radicalisation",
    "intelligence",
]

def _search_url(q: str) -> str:
    return f"{BASE}/en/jobs/?q={q}&active=1&country_list=NL%2CBE"


def _parse_page(soup) -> list[dict]:
    jobs = []
    for art in soup.select("article"):
        link = art.select_one("a[href*='/jobs/']") or art.select_one("a")
        if not link:
            continue
        url = make_absolute(link.get("href", ""), BASE)

        heading = (
            art.select_one("h3")
            or art.select_one("h2")
            or art.select_one("[class*='title']")
            or link
        )
        title = clean_text(heading)
        if not title:
            continue

        logo = art.select_one("img[alt]")
        institution = logo["alt"].strip() if logo and logo.get("alt") else ""

        location = "NL / BE"
        for sp in reversed(art.select("span.text-at-small")):
            txt = clean_text(sp)
            if txt and not sp.select("time"):
                location = txt
                break

        deadline_tag = art.select_one("time[datetime]")
        deadline = deadline_tag.get("datetime", "")[:10] if deadline_tag else ""

        desc_el = art.select_one("p.text-at-body") or art.select_one("p")
        description = clean_text(desc_el)[:220] if desc_el else ""

        jobs.append({
            "id":          job_id(title, url),
            "title":       title,
            "institution": institution,
            "location":    location,
            "deadline":    deadline,
            "url":         url,
            "source":      "AcademicTransfer",
            "description": description,
        })
    return jobs


def scrape() -> list[dict]:
    seen: dict[str, dict] = {}  # id -> job, for deduplication

    for q in SEARCHES:
        url = _search_url(q)
        logger.info("[AcademicTransfer] search '%s' -> %s", q, url)
        soup = fetch(url)
        if soup is None:
            continue
        for job in _parse_page(soup):
            seen.setdefault(job["id"], job)

    all_jobs = list(seen.values())
    logger.info("[AcademicTransfer] collected %d unique listings.", len(all_jobs))
    return all_jobs
