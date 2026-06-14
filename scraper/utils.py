"""HTTP helpers, text cleaning, and job-ID generation."""
import hashlib
import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from scraper.config import MAX_RETRIES, REQUEST_DELAY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch(url: str, retries: int = MAX_RETRIES) -> BeautifulSoup | None:
    """GET *url* and return a BeautifulSoup object, or None on failure."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as exc:
            logger.warning(
                "Attempt %d/%d failed for %s: %s", attempt + 1, retries + 1, url, exc
            )
            if attempt < retries:
                time.sleep(REQUEST_DELAY * 2)
    logger.error("All retries exhausted for %s", url)
    return None


def fetch_raw(url: str) -> str | None:
    """Return raw response text, or None on failure (used for RSS/XML)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return resp.text
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def make_absolute(href: str | None, base_url: str) -> str:
    """Turn a relative href into an absolute URL."""
    if not href:
        return base_url
    return urljoin(base_url, href)


def clean_text(node: Tag | str | None) -> str:
    """Extract and normalise text from a BS4 tag or raw string."""
    if node is None:
        return ""
    text = node.get_text() if isinstance(node, Tag) else str(node)
    return re.sub(r"\s+", " ", text).strip()


def job_id(title: str, url: str) -> str:
    """Stable MD5 hash used as a deduplication key."""
    raw = f"{title.strip().lower()}|{url.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()
