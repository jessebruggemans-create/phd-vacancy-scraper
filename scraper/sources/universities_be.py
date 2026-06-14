"""Scrapers for Flemish universities.

KU Leuven, UGent, UAntwerp: all use JS-rendered ATS portals and are not
directly scrapeable -- their vacancies appear on AcademicTransfer / EURAXESS.

VUB: the SmartRecruiters PhD listing page renders job links in static HTML.
UHasselt: fully static listing, confirmed working.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VUB -- jobs.vub.be PhD category
# SmartRecruiters renders job links as <a href="/job/..."> in static HTML.
# ---------------------------------------------------------------------------
_VUB_URL = "https://jobs.vub.be/go/NL_PHD/3776201/"


def _scrape_vub() -> list[dict]:
    jobs = []
    seen: set[str] = set()
    soup = fetch(_VUB_URL, retries=0, timeout=8)
    if not soup:
        logger.info("[VUB] 0 listings.")
        return jobs

    for a in soup.select("a[href*='/job/']"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 5:
            continue
        full_url = make_absolute(href, "https://jobs.vub.be")
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append({
            "id":          jid,
            "title":       title,
            "institution": "Vrije Universiteit Brussel",
            "location":    "Brussels, BE",
            "deadline":    "",
            "url":         full_url,
            "source":      "VUB",
            "description": "",
        })

    logger.info("[VUB] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# UHasselt -- static vacancy listing, fully confirmed working
# ---------------------------------------------------------------------------
_UHASSELT_BASE = "https://www.uhasselt.be"
_UHASSELT_URL  = (
    f"{_UHASSELT_BASE}/en/about-hasselt-university"
    "/working-at-hasselt-university/vacancies"
)


def _scrape_uhasselt() -> list[dict]:
    jobs = []
    soup = fetch(_UHASSELT_URL)
    if not soup:
        logger.info("[UHasselt] 0 listings.")
        return jobs

    for item in soup.select("section.vacancy-item"):
        title_el = item.select_one("h3.heading")
        title = clean_text(title_el) if title_el else ""
        if not title:
            continue

        link = item.select_one("a.button-red")
        href = make_absolute(link.get("href", ""), _UHASSELT_BASE) if link else _UHASSELT_URL

        deadline = ""
        for li in item.select("ul li"):
            if "apply up to" in clean_text(li).lower():
                strong = li.select_one("strong")
                if strong:
                    raw = clean_text(strong)
                    try:
                        from datetime import datetime
                        deadline = datetime.strptime(raw, "%d.%m.%Y").strftime("%Y-%m-%d")
                    except ValueError:
                        deadline = raw

        jobs.append({
            "id":          job_id(title, href),
            "title":       title,
            "institution": "Hasselt University",
            "location":    "Hasselt, BE",
            "deadline":    deadline,
            "url":         href,
            "source":      "UHasselt",
            "description": "",
        })

    logger.info("[UHasselt] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_vub, _scrape_uhasselt):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[universities_be] %s crashed: %s", fn.__name__, exc)
    return all_jobs
