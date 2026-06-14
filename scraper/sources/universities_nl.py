"""Scrapers for Dutch universities.

Confirmed working: Utrecht (uu.nl), Groningen (werkenbij.rug.nl), VU (workingat.vu.nl).
Sites that require JavaScript (Leiden, UvA, Radboud, Maastricht, Tilburg, EUR)
return empty lists gracefully -- their vacancies appear on AcademicTransfer/EURAXESS.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utrecht University -- fully confirmed working
# ---------------------------------------------------------------------------
_UU_BASE = "https://www.uu.nl"
_UU_URL  = f"{_UU_BASE}/en/organisation/working-at-utrecht-university/jobs"


def _scrape_utrecht() -> list[dict]:
    jobs = []
    url: str | None = _UU_URL
    page = 0
    while url and page < 15:
        page += 1
        logger.info("[Utrecht] page %d -> %s", page, url)
        soup = fetch(url)
        if not soup:
            break

        for card in soup.select("div[class*='vacancy']"):
            title_a = card.select_one("h3.list-item__title a") or card.select_one("h3 a") or card.select_one("a")
            if not title_a:
                continue
            href  = make_absolute(title_a.get("href", ""), _UU_BASE)
            title = clean_text(title_a)
            if not title:
                continue

            dept_el = card.select_one(".department, [class*='department'], [class*='faculty']")
            institution = clean_text(dept_el) if dept_el else "Utrecht University"

            desc_el = card.select_one("p")
            description = clean_text(desc_el)[:220] if desc_el else ""

            # Deadline in meta dl
            dl_el = card.select_one("dd, time, [class*='deadline'], [class*='date']")
            deadline = ""
            if dl_el:
                dt = dl_el.get("datetime") or clean_text(dl_el)
                deadline = dt[:10] if dt else ""

            jobs.append({
                "id":          job_id(title, href),
                "title":       title,
                "institution": institution,
                "location":    "Utrecht, NL",
                "deadline":    deadline,
                "url":         href,
                "source":      "Utrecht University",
                "description": description,
            })

        # Pagination
        next_a = soup.select_one("a[rel='next'], [class*='pager'] a[aria-label*='Next'], [class*='next'] > a")
        url = make_absolute(next_a["href"], _UU_BASE) if next_a and next_a.get("href") else None

    logger.info("[Utrecht] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# University of Groningen -- fully confirmed working
# Cards are wrapped in <a class="ano-link"> containing <article class="vacature">
# ---------------------------------------------------------------------------
_RUG_BASE = "https://werkenbij.rug.nl"
_RUG_URL  = f"{_RUG_BASE}/en/all-vacancies/"


def _scrape_groningen() -> list[dict]:
    jobs = []
    url: str | None = _RUG_URL
    page = 0
    while url and page < 15:
        page += 1
        logger.info("[Groningen] page %d -> %s", page, url)
        soup = fetch(url)
        if not soup:
            break

        cards = soup.select("a.ano-link")
        if not cards and page > 1:
            break

        for card in cards:
            href  = card.get("href", "")
            title = clean_text(card.select_one("h3.entry-title") or card.select_one("h3"))
            if not title:
                continue
            desc_el = card.select_one(".summary p") or card.select_one("p")
            description = clean_text(desc_el)[:220] if desc_el else ""

            # Language label -- skip NL-only listings when they contain no EN title
            lang_label = card.select_one(".lang-label")
            lang = clean_text(lang_label) if lang_label else ""

            jobs.append({
                "id":          job_id(title, href),
                "title":       title,
                "institution": "University of Groningen",
                "location":    "Groningen, NL",
                "deadline":    "",
                "url":         href,
                "source":      "Groningen",
                "description": description,
            })

        next_a = soup.select_one("a.next, a[rel='next'], [class*='next'] a")
        url = make_absolute(next_a["href"], _RUG_BASE) if next_a and next_a.get("href") else None

    logger.info("[Groningen] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# VU Amsterdam -- confirmed working
# Vacancy links appear inside [class*='vacancy-list'] as <a href="/vacancies/...">
# ---------------------------------------------------------------------------
_VU_BASE = "https://workingat.vu.nl"
_VU_URL  = f"{_VU_BASE}/vacancies"


def _scrape_vu() -> list[dict]:
    jobs = []
    url: str | None = _VU_URL
    page = 0
    while url and page < 15:
        page += 1
        logger.info("[VU] page %d -> %s", page, url)
        soup = fetch(url)
        if not soup:
            break

        found = False
        for a in soup.select("a[href*='/vacancies/']"):
            href = a.get("href", "")
            if "/vacancies/favorites" in href or href.rstrip("/") == f"{_VU_BASE}/vacancies":
                continue
            title = clean_text(a)
            if not title or len(title) < 5:
                continue
            full_url = make_absolute(href, _VU_BASE)
            jobs.append({
                "id":          job_id(title, full_url),
                "title":       title,
                "institution": "Vrije Universiteit Amsterdam",
                "location":    "Amsterdam, NL",
                "deadline":    "",
                "url":         full_url,
                "source":      "VU Amsterdam",
                "description": "",
            })
            found = True

        if not found and page > 1:
            break

        next_a = soup.select_one("a[rel='next'], [class*='pagination'] a[aria-label*='Next']")
        url = make_absolute(next_a["href"], _VU_BASE) if next_a and next_a.get("href") else None

    logger.info("[VU] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_utrecht, _scrape_groningen, _scrape_vu):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[universities_nl] %s crashed: %s", fn.__name__, exc)
    return all_jobs
