"""Keyword-based relevance scoring.

A job passes the filter if its title or description contains at least one
keyword from config.KEYWORDS. Title matches are implicitly higher-value
(shorter text → denser signal), but we don't need to weight them here
because the keyword list already covers the important terms explicitly.
"""
from scraper.config import KEYWORDS

_LOWER = [kw.lower() for kw in KEYWORDS]


def is_relevant(title: str, description: str = "", institution: str = "") -> bool:
    """Return True if the job matches at least one keyword."""
    haystack = f"{title} {description} {institution}".lower()
    return any(kw in haystack for kw in _LOWER)


def keyword_score(title: str, description: str = "") -> int:
    """Count distinct keyword matches — used to sort the digest by relevance."""
    haystack = f"{title} {description}".lower()
    return sum(1 for kw in _LOWER if kw in haystack)
