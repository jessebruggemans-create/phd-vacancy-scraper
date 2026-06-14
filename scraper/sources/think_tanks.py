"""Scrapers for security-studies think tanks and research institutes.

All think-tank jobs receive always_include=True so they bypass the keyword
relevance filter (these are curated security-policy sources).
The eligibility filter (is_eligible) still applies.

Scrapeable:
  Egmont Institute  -- static WordPress page (Brussels, BE)
  SWP Berlin        -- static /karriere listing (Berlin, DE)
  Asser Institute   -- static /jobs-internships/ page (The Hague, NL)
  HCSS              -- WordPress archive (The Hague, NL)
  Flemish Peace Inst-- static /vacancies/ page (Brussels, BE)
  GRIP Brussels     -- static /travailler-au-gripi/ page (Brussels, BE)
  IRIS Paris        -- static /recrutement/ page with /job/ links (Paris, FR)
  TNO               -- static careers listing (The Hague, NL)
  NIOD              -- static vacancies page (Amsterdam, NL)

JS-rendered / blocked (linked in digest for manual check):
  Clingendael       -- AFAS OutSite ATS, JS-rendered
  IISS              -- React SPA + Cloudflare
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)


# Admin / support roles at think tanks that are NOT research positions.
# These won't get always_include=True and must pass the keyword filter instead.
_SUPPORT_PATTERNS = [
    "sachbearbeiter",           # German clerk/admin (Sachbearbeiter:in Personal = HR admin)
    "buchhalter",               # accountant
    "sekretär", "sekretärin",   # secretary
    "empfangsmitarbeiter",      # receptionist
    "facility manager",
    "it administrator", "it-administrator",
    "finance officer", "finance manager",
    "hr officer", "human resources officer",
    "payroll",
]


def _tag(job: dict) -> dict:
    """Attach always_include flag if the job is a research/policy role.

    Pure admin / support titles at think tanks still need to match a keyword.
    """
    t = job.get("title", "").lower()
    if not any(p in t for p in _SUPPORT_PATTERNS):
        job["always_include"] = True
    return job


# ---------------------------------------------------------------------------
# Egmont Institute (Brussels) -- static WordPress page
# Lists jobs as <h3> headings when positions are open.
# ---------------------------------------------------------------------------
_EGMONT_BASE = "https://egmontinstitute.be"
_EGMONT_URL  = f"{_EGMONT_BASE}/jobs-internships-and-opportunities/"


def _scrape_egmont() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_EGMONT_URL)
    if not soup:
        logger.info("[Egmont] 0 listings.")
        return jobs

    content = soup.select_one("main, [class*='entry-content'], article")
    if not content:
        content = soup

    page_text = content.get_text().lower()
    if "no vacanc" in page_text or "currently no" in page_text or "no current" in page_text:
        logger.info("[Egmont] no current vacancies stated on page.")
        return jobs

    seen: set[str] = set()
    for h3 in content.select("h3"):
        a = h3.select_one("a[href]") or h3.find_next_sibling("a")
        title = clean_text(h3)
        if not title or len(title) < 8:
            continue

        full_url = make_absolute(a.get("href", ""), _EGMONT_BASE) if a and a.get("href") else _EGMONT_URL
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "Egmont Institute",
            "location":    "Brussels, BE",
            "deadline":    "",
            "url":         full_url,
            "source":      "Egmont",
            "description": "",
        }))

    logger.info("[Egmont] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Clingendael (The Hague) -- AFAS OutSite ATS, JS-rendered; returns 0 gracefully
# ---------------------------------------------------------------------------
_CLINGENDAEL_VACANCIES = "https://www.careers.clingendael.org/vacancy-jobs/overview-jobs-extern"


def _scrape_clingendael() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_CLINGENDAEL_VACANCIES)
    if not soup:
        logger.info("[Clingendael] 0 listings.")
        return jobs

    if len(soup.get_text()) < 800:
        logger.info("[Clingendael] page appears JS-rendered -- 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href.lower() for skip in
               ["javascript:", "mailto:", "#", "/overview", "locale", "spontan"]):
            continue
        if not any(kw in href.lower() for kw in ["/job/", "/vacanc", "/position", "/opening"]):
            continue

        full_url = make_absolute(href, "https://www.careers.clingendael.org")
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "Clingendael Institute",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "Clingendael",
            "description": "",
        }))

    logger.info("[Clingendael] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# HCSS (The Hague Centre for Strategic Studies) -- WordPress archive
# ---------------------------------------------------------------------------
_HCSS_URL = "https://hcss.nl/jobs/"


def _scrape_hcss() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_HCSS_URL)
    if not soup:
        logger.info("[HCSS] 0 listings.")
        return jobs

    for art in soup.select("article"):
        title_el = art.select_one("h2.entry-title a, h1.entry-title a, h3.entry-title a")
        if not title_el:
            continue
        href  = title_el.get("href", "")
        title = clean_text(title_el)
        if not title or len(title) < 5 or not href or "hcss.nl/jobs/" not in href:
            continue

        desc_el     = art.select_one(".entry-content p, .entry-summary p")
        description = clean_text(desc_el)[:220] if desc_el else ""
        full_url    = make_absolute(href, "https://hcss.nl")

        jobs.append(_tag({
            "id":          job_id(title, full_url),
            "title":       title,
            "institution": "HCSS",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "HCSS",
            "description": description,
        }))

    logger.info("[HCSS] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Flemish Peace Institute (Brussels) -- static vacancies page
# ---------------------------------------------------------------------------
_FPI_URL = "https://vlaamsvredesinstituut.eu/en/vacancies/"


def _scrape_fpi() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_FPI_URL)
    if not soup:
        logger.info("[FPI] 0 listings.")
        return jobs

    main = soup.select_one("main, article, [class*='content']") or soup
    seen: set[str] = set()
    for a in main.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href for skip in
               ["#", "mailto:", "javascript:", "/about", "/contact", "/news", "/publications"]):
            continue
        if "vlaamsvredesinstituut.eu" not in href and not href.startswith("/"):
            continue

        full_url = make_absolute(href, "https://vlaamsvredesinstituut.eu")
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "Flemish Peace Institute",
            "location":    "Brussels, BE",
            "deadline":    "",
            "url":         full_url,
            "source":      "Flemish Peace Institute",
            "description": "",
        }))

    logger.info("[FPI] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Asser Institute (The Hague) -- international law research
# ---------------------------------------------------------------------------
_ASSER_URL = "https://www.asser.nl/jobs-internships/"


def _scrape_asser() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_ASSER_URL)
    if not soup:
        logger.info("[Asser] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='/jobs-internships/']"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if href.rstrip("/").endswith("/jobs-internships"):
            continue

        full_url = make_absolute(href, "https://www.asser.nl")
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "Asser Institute",
            "location":    "The Hague, NL",
            "deadline":    "",
            "url":         full_url,
            "source":      "Asser Institute",
            "description": "",
        }))

    logger.info("[Asser] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# SWP Berlin (Stiftung Wissenschaft und Politik)
# One of Europe's leading IR/security think tanks -- German language.
# Vacancy listing: swp-berlin.org/karriere
# Each job is an <h3><a href="/karriere/stellenangebot/...">
# always_include=True so German titles pass without keyword matching.
# ---------------------------------------------------------------------------
_SWP_BASE = "https://www.swp-berlin.org"
_SWP_URL  = f"{_SWP_BASE}/karriere"


def _scrape_swp() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_SWP_URL)
    if not soup:
        logger.info("[SWP] 0 listings.")
        return jobs

    seen: set[str] = set()
    for h3 in soup.select("h3"):
        a = h3.select_one("a[href*='/karriere/stellenangebot/']")
        if not a:
            continue
        href  = make_absolute(a.get("href", ""), _SWP_BASE)
        title = clean_text(a)
        if not title:
            continue

        jid = job_id(title, href)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "SWP Berlin",
            "location":    "Berlin, DE",
            "deadline":    "",
            "url":         href,
            "source":      "SWP Berlin",
            "description": "",
        }))

    logger.info("[SWP] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# DGAP (Deutsche Gesellschaft für Auswärtige Politik) -- Berlin, DE
# Static Drupal page; job cards use class 'node--type-dgap-job'.
# German-language titles will be caught by is_english_or_dutch(); English
# positions (e.g. research fellowships) pass through.
# ---------------------------------------------------------------------------
_DGAP_BASE = "https://dgap.org"
_DGAP_URL  = f"{_DGAP_BASE}/de/karriere-in-der-dgap-jobs-stellen"


def _scrape_dgap() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_DGAP_URL)
    if not soup:
        logger.info("[DGAP] 0 listings.")
        return jobs

    seen: set[str] = set()
    for art in soup.select("article[class*='node--type-dgap-job']"):
        a = art.select_one("h3 a[href*='/de/dgap/jobs/'], h2 a[href*='/de/dgap/jobs/']")
        if not a:
            # Fallback: any link pointing to /de/dgap/jobs/
            a = art.select_one("a[href*='/de/dgap/jobs/']")
        if not a:
            continue
        href  = make_absolute(a.get("href", ""), _DGAP_BASE)
        title = clean_text(a)
        if not title or len(title) < 5:
            continue

        jid = job_id(title, href)
        if jid in seen:
            continue
        seen.add(jid)

        # Extract deadline if shown (e.g. "Bewerbungsfrist 14. Juni 2026")
        dl_el = art.select_one("[class*='deadline'], [class*='date']")
        deadline = ""
        if not dl_el:
            card_text = art.get_text()
            import re as _re2
            m = _re2.search(r"Bewerbungsfrist\s+(.{5,25}?)(?:\n|$|\|)", card_text)
            deadline = m.group(1).strip() if m else ""

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "DGAP",
            "location":    "Berlin, DE",
            "deadline":    deadline,
            "url":         href,
            "source":      "DGAP",
            "description": "",
        }))

    logger.info("[DGAP] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# IFSH Hamburg (Institut für Friedensforschung und Sicherheitspolitik) -- DE
# Static page with job links at /karriere/details/...
# Focuses on arms control, European security, peace research.
# ---------------------------------------------------------------------------
_IFSH_BASE = "https://www.ifsh.de"
_IFSH_URL  = f"{_IFSH_BASE}/karriere"


def _scrape_ifsh() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_IFSH_URL)
    if not soup:
        logger.info("[IFSH] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='/karriere/details/']"):
        href  = make_absolute(a.get("href", ""), _IFSH_BASE)
        title = clean_text(a)
        if not title or len(title) < 8:
            continue

        jid = job_id(title, href)
        if jid in seen:
            continue
        seen.add(jid)

        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "IFSH Hamburg",
            "location":    "Hamburg, DE",
            "deadline":    "",
            "url":         href,
            "source":      "IFSH",
            "description": "",
        }))

    logger.info("[IFSH] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# GRIP Brussels (Groupe de Recherche et d'Information sur la Paix et la Sécurité)
# Static jobs page; when open, positions appear as content links.
# Page explicitly states "Aucun poste n'est actuellement à pourvoir" when empty.
# always_include=True: a curated peace/security research institute.
# ---------------------------------------------------------------------------
_GRIP_BASE = "https://www.grip.org"
_GRIP_URL  = f"{_GRIP_BASE}/travailler-au-gripi/"


def _scrape_grip() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_GRIP_URL)
    if not soup:
        logger.info("[GRIP] 0 listings.")
        return jobs

    text = soup.get_text().lower()
    if "aucun poste" in text or "no current" in text or "no position" in text:
        logger.info("[GRIP] no current vacancies stated on page.")
        return jobs

    seen: set[str] = set()
    main = soup.select_one("main, article, [class*='entry-content'], [class*='content']") or soup
    for a in main.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href for skip in ["#", "mailto:", "javascript:", "tel:"]):
            continue
        # Skip navigation links
        if any(nav in href.lower() for nav in
               ["/about", "/contact", "/news", "/publication", "/media",
                "/programme", "/fr/", "/en/", "/recherche", "/category"]):
            continue
        if "grip.org" in href or href.startswith("/"):
            full_url = make_absolute(href, _GRIP_BASE)
            jid = job_id(title, full_url)
            if jid in seen:
                continue
            seen.add(jid)
            jobs.append(_tag({
                "id":          jid,
                "title":       title,
                "institution": "GRIP Brussels",
                "location":    "Brussels, BE",
                "deadline":    "",
                "url":         full_url,
                "source":      "GRIP",
                "description": "",
            }))

    logger.info("[GRIP] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# IRIS Paris (Institut de Relations Internationales et Stratégiques)
# Static /recrutement/ page; jobs link to /job/{slug}/
# always_include=True: curated security/IR think tank (Paris, FR)
# Note: French-language postings are filtered out by is_english_or_dutch()
# unless they happen to be in English.
# ---------------------------------------------------------------------------
_IRIS_BASE = "https://www.iris-france.org"
_IRIS_URL  = f"{_IRIS_BASE}/recrutement/"


def _scrape_iris() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_IRIS_URL)
    if not soup:
        logger.info("[IRIS] 0 listings.")
        return jobs

    seen: set[str] = set()
    for a in soup.select("a[href*='/job/']"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 5:
            continue
        full_url = make_absolute(href, _IRIS_BASE)
        jid = job_id(title, full_url)
        if jid in seen:
            continue
        seen.add(jid)
        jobs.append(_tag({
            "id":          jid,
            "title":       title,
            "institution": "IRIS Paris",
            "location":    "Paris, FR",
            "deadline":    "",
            "url":         full_url,
            "source":      "IRIS",
            "description": "",
        }))

    logger.info("[IRIS] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# TNO (Nederlandse Organisatie voor Toegepast-Natuurwetenschappelijk Onderzoek)
# Static careers listing with pagination via ?page=N (0-indexed)
# Defence, Safety & Security is one of TNO's core units (The Hague).
# ---------------------------------------------------------------------------
_TNO_BASE = "https://www.tno.nl"
_TNO_URL  = f"{_TNO_BASE}/en/careers/vacancies/"


def _scrape_tno() -> list[dict]:
    jobs: list[dict] = []
    seen: set[str] = set()

    for page in range(20):  # cap at 20 pages (generous)
        url = _TNO_URL if page == 0 else f"{_TNO_URL}?page={page}"
        soup = fetch(url)
        if not soup:
            break

        found_any = False
        import re as _re_tno
        for a in soup.select("a[href]"):
            href  = a.get("href", "")
            title_raw = clean_text(a)
            if not title_raw or len(title_raw) < 5:
                continue
            # TNO job detail links contain '/en/careers/vacancies/' + slug
            if not (("/en/careers/vacancies/" in href or "/carriere/vacatures/" in href)
                    and href.rstrip("/") != _TNO_URL.rstrip("/")):
                continue
            if any(skip in href for skip in ["#", "?", "javascript:", "mailto:"]):
                continue
            # Strip Dutch metadata appended to title text
            # e.g. "Engineer werklocatie: Den Haag werkenopafstand: Hybrid"
            title = _re_tno.split(
                r"\s+(?:werklocatie|werkenopafstand|vacaturenummer|uur\s+per\s+week):",
                title_raw,
                maxsplit=1,
            )[0].strip()
            if not title:
                title = title_raw[:100]
            full_url = make_absolute(href, _TNO_BASE)
            jid = job_id(title, full_url)
            if jid in seen:
                continue
            seen.add(jid)
            found_any = True
            # TNO is a broad applied-science organisation — do NOT set
            # always_include so that keyword / social-science filters apply.
            jobs.append({
                "id":          jid,
                "title":       title,
                "institution": "TNO",
                "location":    "The Hague, NL",
                "deadline":    "",
                "url":         full_url,
                "source":      "TNO",
                "description": "",
            })

        if not found_any:
            break

    logger.info("[TNO] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# NIOD (Institute for War, Holocaust and Genocide Studies) -- Amsterdam
# Static vacancies page; links to individual vacancy detail pages.
# Also lists positions on Academic Transfer.
# ---------------------------------------------------------------------------
_NIOD_BASE = "https://www.niod.nl"
_NIOD_URL  = f"{_NIOD_BASE}/en/about-niod/vacancies-niod"


def _scrape_niod() -> list[dict]:
    jobs: list[dict] = []
    soup = fetch(_NIOD_URL)
    if not soup:
        logger.info("[NIOD] 0 listings.")
        return jobs

    text = soup.get_text().lower()
    if any(phrase in text for phrase in
           ["no vacancies", "no current", "currently no", "geen vacatures"]):
        logger.info("[NIOD] no current vacancies stated on page.")
        return jobs

    seen: set[str] = set()
    main = soup.select_one("main, article, [class*='content']") or soup
    for a in main.select("a[href]"):
        href  = a.get("href", "")
        title = clean_text(a)
        if not title or len(title) < 8:
            continue
        if any(skip in href for skip in ["#", "mailto:", "javascript:", "tel:"]):
            continue
        # Skip navigation / about-page links
        if any(nav in href.lower() for nav in
               ["/about-niod/staff", "/about-niod/organization", "/about-niod/history",
                "/about-niod/contact", "/publications", "/projects", "/events",
                "facebook", "twitter", "linkedin", "/nl/over-niod"]):
            continue
        # Only follow niod.nl internal links and Academic Transfer links
        if "niod.nl" in href or "academictransfer" in href or href.startswith("/"):
            full_url = make_absolute(href, _NIOD_BASE)
            # Don't link back to the vacancies listing page
            if full_url.rstrip("/") == _NIOD_URL.rstrip("/"):
                continue
            jid = job_id(title, full_url)
            if jid in seen:
                continue
            seen.add(jid)
            jobs.append(_tag({
                "id":          jid,
                "title":       title,
                "institution": "NIOD Amsterdam",
                "location":    "Amsterdam, NL",
                "deadline":    "",
                "url":         full_url,
                "source":      "NIOD",
                "description": "",
            }))

    logger.info("[NIOD] %d listings.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def scrape() -> list[dict]:
    all_jobs: list[dict] = []
    for fn in (_scrape_egmont, _scrape_clingendael, _scrape_hcss,
               _scrape_fpi, _scrape_asser, _scrape_swp,
               _scrape_dgap, _scrape_ifsh,
               _scrape_grip, _scrape_iris, _scrape_tno, _scrape_niod):
        try:
            all_jobs.extend(fn())
        except Exception as exc:
            logger.exception("[think_tanks] %s crashed: %s", fn.__name__, exc)
    return all_jobs
