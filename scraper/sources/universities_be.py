"""Scrapers for Flemish universities.

KU Leuven, UAntwerp: JS-rendered ATS portals -- appear on AcademicTransfer/EURAXESS.
UGent: doctoral-fellow listing at /en/work/scientific is static HTML (table rows).
VUB: SmartRecruiters portal at jobs.vub.be (times out from GitHub CI -- kept with
     short timeout so it fails fast; their jobs appear on AcademicTransfer too).
UHasselt: fully static listing.
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
# UGent -- doctoral-fellow listing (static HTML table)
# URL: https://www.ugent.be/en/work/scientific
# Each <tr> contains: [link "Doctoral fellow"] [department] [%] [deadline]
# The department cell is used as description for keyword matching.
# ---------------------------------------------------------------------------
_UGENT_BASE = "https://www.ugent.be"
_UGENT_URL  = f"{_UGENT_BASE}/en/work/scientific"


def _scrape_ugent() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_UGENT_URL)
    if not soup:
        logger.info("[UGent] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='doctoral-fellow-']"):
        href = a.get("href", "")
        if not href:
            continue
        full_url = make_absolute(href, _UGENT_BASE)

        # Grab department and deadline from sibling <td> elements in the same <tr>
        tr = a.find_parent("tr")
        dept = ""
        deadline = ""
        if tr:
            tds = tr.find_all("td")
            if len(tds) > 1:
                dept = clean_text(tds[1])
            if len(tds) > 3:
                # deadline format: "2026-07-08 23:59:00"  →  take first 10 chars
                raw_dl = clean_text(tds[3])
                deadline = raw_dl[:10] if raw_dl else ""

        jid = job_id("Doctoral Fellow " + dept, full_url)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append({
            "id":          jid,
            "title":       "Doctoral Fellow",
            "institution": "Ghent University",
            "location":    "Ghent, BE",
            "deadline":    deadline,
            "url":         full_url,
            "source":      "UGent",
            # Department is stored as description for keyword matching;
            # e.g. "Department of Political Sciences" matches "political science"
            "description": dept,
        })

    logger.info("[UGent] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_vub, _scrape_uhasselt, _scrape_ugent):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[universities_be] %s crashed: %s", fn.__name__, exc)
    return all_jobs
