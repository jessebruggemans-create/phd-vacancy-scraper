"""Scraper for AcademicTransfer.com.

AcademicTransfer is the primary Dutch/Belgian academic jobs portal.
We request the NL+BE job listings page and walk pagination.
"""
import logging

from scraper.utils import clean_text, fetch, job_id, make_absolute

logger = logging.getLogger(__name__)

BASE = "https://www.academictransfer.com"
START_URL = f"{BASE}/en/jobs/?q=&active=1&country_list=NL%2CBE"


def _parse_page(soup, base: str) -> list[dict]:
    jobs = []

    # AcademicTransfer renders job cards as <article> elements (Tailwind-based layout).
    articles = soup.select("article") or soup.select("li.search-result")

    for art in articles:
        # ── URL + title ───────────────────────────────────────────────────────
        link = art.select_one("a[href*='/jobs/']") or art.select_one("a")
        if not link:
            continue
        url = make_absolute(link.get("href", ""), base)

        heading = (
            art.select_one("h3")
            or art.select_one("h2")
            or art.select_one("[class*='title']")
            or link
        )
        title = clean_text(heading)
        if not title:
            continue

        # ── Institution ───────────────────────────────────────────────────────
        # Logo img has alt text = institution name (most reliable).
        logo = art.select_one("img[alt]")
        institution = logo["alt"].strip() if logo and logo.get("alt") else ""

        # ── Location ──────────────────────────────────────────────────────────
        # Location span contains an inline SVG icon + city name as trailing text.
        # Select the span that sits alongside the SVG location icon.
        loc_span = art.select_one("span.text-at-small svg ~ *") or None
        if loc_span:
            location = clean_text(loc_span)
        else:
            # Fallback: last text-at-small span that isn't a time element
            spans = art.select("span.text-at-small")
            # The location span is the last one with a plain text child
            loc_text = ""
            for sp in reversed(spans):
                txt = clean_text(sp)
                if txt and not sp.select("time"):
                    loc_text = txt
                    break
            location = loc_text or "NL / BE"

        # ── Deadline ──────────────────────────────────────────────────────────
        deadline_time = art.select_one("time[datetime]")
        if deadline_time:
            deadline = deadline_time.get("datetime", "")[:10]
        else:
            dl_el = art.select_one("[class*='deadline'], [class*='closing']")
            deadline = clean_text(dl_el) if dl_el else ""

        # ── Short description ─────────────────────────────────────────────────
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
    """Fetch all pages and return a flat list of job dicts."""
    all_jobs: list[dict] = []
    url: str | None = START_URL
    page = 0
    max_pages = 15  # safety ceiling

    while url and page < max_pages:
        page += 1
        logger.info("[AcademicTransfer] page %d -> %s", page, url)
        soup = fetch(url)
        if soup is None:
            break

        jobs = _parse_page(soup, BASE)
        if not jobs and page > 1:
            break  # past the last page

        all_jobs.extend(jobs)

        # Next-page link
        next_a = soup.select_one(
            "a[rel='next'], [class*='pagination'] a[aria-label='Next'], "
            "[class*='next'] a, a.next-page"
        )
        if next_a and next_a.get("href"):
            url = make_absolute(next_a["href"], BASE)
        else:
            url = None

    logger.info("[AcademicTransfer] collected %d listings.", len(all_jobs))
    return all_jobs
