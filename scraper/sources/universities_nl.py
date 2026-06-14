"""Scrapers for Dutch universities.

Confirmed working:
  Utrecht      -- uu.nl (HTML, paginated)
  Groningen    -- werkenbij.rug.nl (HTML, paginated)
  VU Amsterdam -- workingat.vu.nl (HTML)
  Radboud      -- ru.nl RSS feed (/werken-bij/vacatures/feed)
  Maastricht   -- vacancies.maastrichtuniversity.nl (HTML, ?q=phd+student)
  EUR Rotterdam-- eur.nl/en/working-at-eur/vacancies/overview (HTML)
  ISS Den Haag -- iss.nl/en/about-iss/vacancies (HTML, Erasmus/EUR graduate school)
  Twente       -- utwentecareers.nl/en/vacancies/?type=WP (HTML)

JS-rendered / blocked (appear on AcademicTransfer/EURAXESS instead):
  Leiden, UvA, Tilburg
"""
import logging
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from scraper.utils import clean_text, fetch, fetch_raw, job_id, make_absolute

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
# Radboud University -- RSS feed (static XML, all departments)
# The feed contains all vacancies; we rely on the relevance filter to keep
# only IR/security/political-science positions.
# Deadline is embedded in the HTML description as "Reageer uiterlijk: YYYY-MM-DD"
# ---------------------------------------------------------------------------
_RADBOUD_RSS = "https://www.ru.nl/werken-bij/vacatures/feed"


def _scrape_radboud() -> list[dict]:
    jobs: list[dict] = []
    raw = fetch_raw(_RADBOUD_RSS)
    if not raw:
        logger.info("[Radboud] 0 listings (feed unavailable).")
        return jobs

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        logger.warning("[Radboud] RSS parse error: %s", exc)
        return jobs

    channel = root.find("channel")
    items   = channel.findall("item") if channel is not None else root.findall(".//item")

    for item in items:
        title    = (item.findtext("title") or "").strip()
        link     = (item.findtext("link")  or "").strip()
        desc_html = item.findtext("description") or ""

        # Strip HTML tags from the description
        desc_text = BeautifulSoup(desc_html, "lxml").get_text(" ").strip()

        # Extract deadline from "Reageer uiterlijk: YYYY-MM-DD"
        dl_match = re.search(r"Reageer uiterlijk:\s*(\d{4}-\d{2}-\d{2})", desc_text)
        deadline = dl_match.group(1) if dl_match else ""

        description = desc_text[:220]

        if not title or not link:
            continue

        jobs.append({
            "id":          job_id(title, link),
            "title":       title,
            "institution": "Radboud University",
            "location":    "Nijmegen, NL",
            "deadline":    deadline,
            "url":         link,
            "source":      "Radboud",
            "description": description,
        })

    logger.info("[Radboud] %d listings from RSS.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Maastricht University -- static HTML search filtered by "phd student"
# URL: vacancies.maastrichtuniversity.nl/search/?q=phd+student
# Jobs listed as: span.jobTitle.visible-phone > a.jobTitle-link
# Department: span.jobFacility (closest ancestor that contains it)
# ---------------------------------------------------------------------------
_UM_BASE = "https://vacancies.maastrichtuniversity.nl"
_UM_URL  = f"{_UM_BASE}/search/?q=phd+student"


def _scrape_maastricht() -> list[dict]:
    jobs: list[dict] = []
    # Simple single-page fetch (agent confirmed 25 results, 1 page for this query)
    soup = fetch(_UM_URL)
    if not soup:
        logger.info("[Maastricht] 0 listings.")
        return jobs

    seen: set[str] = set()
    # visible-phone variant avoids desktop duplicates
    for a in soup.select("span.jobTitle.visible-phone a.jobTitle-link"):
        href  = make_absolute(a.get("href", ""), _UM_BASE)
        title = clean_text(a)
        if not title:
            continue

        # Department from nearest ancestor <li> or <tr>
        ancestor = a.find_parent("li") or a.find_parent("tr") or a.find_parent("div")
        dept_el  = ancestor.select_one("span.jobFacility") if ancestor else None
        dept     = clean_text(dept_el) if dept_el else ""

        jid = job_id(title, href)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append({
            "id":          jid,
            "title":       title,
            "institution": "Maastricht University",
            "location":    "Maastricht, NL",
            "deadline":    "",
            "url":         href,
            "source":      "Maastricht",
            "description": dept,
        })

    logger.info("[Maastricht] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# EUR Rotterdam (Erasmus University Rotterdam)
# Vacancies overview page; job cards link to /en/working-at-eur/vacancies/{slug}
# ---------------------------------------------------------------------------
_EUR_BASE = "https://www.eur.nl"
_EUR_URL  = f"{_EUR_BASE}/en/working-at-eur/vacancies/overview"


def _scrape_eur() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_EUR_URL)
    if not soup:
        logger.info("[EUR] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='/en/working-at-eur/vacancies/']"):
        href = a.get("href", "")
        # skip the overview page itself and any anchor/filter links
        if not href or href.rstrip("/").endswith("/vacancies/overview"):
            continue
        if any(skip in href for skip in ["#", "?", "javascript:", "mailto:"]):
            continue
        title = clean_text(a)
        if not title or len(title) < 5:
            continue
        full_url = make_absolute(href, _EUR_BASE)
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append({
            "id":          jid,
            "title":       title,
            "institution": "Erasmus University Rotterdam",
            "location":    "Rotterdam, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "EUR Rotterdam",
            "description": "",
        })

    logger.info("[EUR] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# ISS The Hague (International Institute of Social Studies, Erasmus/EUR)
# Vacancies page: iss.nl/en/about-iss/vacancies
# ---------------------------------------------------------------------------
_ISS_BASE = "https://www.iss.nl"
_ISS_URL  = f"{_ISS_BASE}/en/about-iss/vacancies"


def _scrape_iss() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_ISS_URL)
    if not soup:
        logger.info("[ISS] 0 listings.")
        return jobs

    text = soup.get_text().lower()
    if any(phrase in text for phrase in
           ["no current vacancies", "no vacancies", "no open positions",
            "currently no", "geen vacatures"]):
        logger.info("[ISS] no current vacancies on page.")
        return jobs

    seen: set[str] = set()
    # Look for job links in page content -- ISS typically posts as content links
    main = soup.select_one("main, article, [class*='content'], [class*='entry']") or soup
    for a in main.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href for skip in ["#", "mailto:", "javascript:", "tel:"]):
            continue
        if href.rstrip("/") in [_ISS_URL, "/en/about-iss/vacancies"]:
            continue
        # Only follow links to iss.nl, eur.nl, or academictransfer
        if not any(domain in href for domain in
                   ["iss.nl", "eur.nl", "academictransfer", "utwentecareers"]):
            if not href.startswith("/"):
                continue
        full_url = make_absolute(href, _ISS_BASE)
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append({
            "id":          jid,
            "title":       title,
            "institution": "ISS Den Haag (Erasmus)",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "ISS Den Haag",
            "description": "",
        })

    logger.info("[ISS] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# University of Twente -- utwentecareers.nl (static HTML, all on one page)
# Job links follow pattern /en/vacancies/{id}/{slug}/
# ---------------------------------------------------------------------------
_TWENTE_BASE = "https://utwentecareers.nl"
_TWENTE_URL  = f"{_TWENTE_BASE}/en/vacancies/?type=WP"


def _scrape_twente() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_TWENTE_URL)
    if not soup:
        logger.info("[Twente] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='/en/vacancies/']"):
        href = a.get("href", "")
        # Skip the listing page, filter tabs, and non-vacancy links
        if not href:
            continue
        # Must have a numeric vacancy ID in the path
        if not re.search(r"/en/vacancies/\d+/", href):
            continue
        title_raw = clean_text(a)
        if not title_raw or len(title_raw) < 5:
            continue
        # The link text often includes metadata after the actual title
        # (e.g. "PhD position in XAcademic staffPhDMasterEEMCS40 hr.")
        # Strip suffix starting with common category markers
        title = re.sub(
            r"(?i)(Academic\s+staff|Support\s+staff|PhD\b|Postdoc\b|\d{2,3}\s*hr\.?|"
            r"Master\b|Bachelor\b|EEMCS|BMS|TNW|ITC|BMS).*$",
            "",
            title_raw,
        ).strip().rstrip("A")  # trailing "A" from "Academic staffA"

        if not title or len(title) < 5:
            title = title_raw[:120]

        full_url = make_absolute(href, _TWENTE_BASE)
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append({
            "id":          jid,
            "title":       title,
            "institution": "University of Twente",
            "location":    "Enschede, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "Twente",
            "description": "",
        })

    logger.info("[Twente] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_utrecht, _scrape_groningen, _scrape_vu,
               _scrape_radboud, _scrape_maastricht,
               _scrape_eur, _scrape_iss, _scrape_twente):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[universities_nl] %s crashed: %s", fn.__name__, exc)
    return all_jobs
