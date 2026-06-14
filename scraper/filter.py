"""Keyword-based relevance scoring and eligibility filtering.

is_relevant  — topic filter: does this vacancy match IR/security keywords?
is_eligible  — seniority filter: is this position open to a master's graduate?
keyword_score — ranking helper: how many keywords matched?
"""
import re

from scraper.config import KEYWORDS

_LOWER = [kw.lower() for kw in KEYWORDS]

# Pre-compile regex patterns for short keywords (≤5 chars) to enforce word
# boundaries and avoid false positives.  Example: "nato" must not match
# "coordinator" (which contains the substring n-a-t-o inside the word).
# Longer keyword phrases are matched as plain substrings (fast + safe).
_SHORT_RE = {
    kw: re.compile(r"\b" + re.escape(kw) + r"\b")
    for kw in _LOWER if len(kw) <= 5
}


def _kw_matches(kw: str, haystack: str) -> bool:
    """Return True if *kw* is present in *haystack* with word-boundary enforcement
    for short (≤5-char) keywords."""
    pat = _SHORT_RE.get(kw)
    if pat:
        return bool(pat.search(haystack))
    return kw in haystack

# ── Eligibility filter ────────────────────────────────────────────────────────
# These title patterns indicate the position REQUIRES an existing PhD.
# Matched as substrings (case-insensitive).
_INELIGIBLE = [
    "professor",            # assistant / associate / full / visiting / adj. professor
    "postdoc",              # postdoctoral researcher
    "post-doc",
    "post doc",
    "postdoctoral",
    "post doctoral",
    "senior lecturer",      # UK/AU: faculty rank above lecturer
    "senior research",      # senior researcher / senior research fellow / associate
    "research fellow",      # fellowship programmes (post-PhD)
    "research director",
    "research group leader",
    "group leader",
    "chair in",             # chair-holder / endowed chair
    "faculty position",
    "faculty member",
    "lecturer",             # UK/NL: tenure-track faculty
    # Dutch academic titles (require PhD)
    "universitair docent",
    "universitair hoofddocent",
    "hoogleraar",
    "bijzonder hoogleraar",
    "gewoon hoogleraar",
    # German (for SWP / international sources)
    "wissenschaftliche leitung",
    "abteilungsleiter",
]

# If ANY of these appear in the title, the job is ALWAYS eligible regardless
# of other patterns.  Used to avoid false negatives on PhD/junior roles.
_ELIGIBLE_OVERRIDE = [
    "phd",
    "ph.d",
    "doctoral",         # doctoral fellow (UGent), doctoral researcher, doctoral candidate
    "promovendus",      # Dutch: PhD candidate
    "promotieonderzoeker",
    "doctoraatsbeurs",  # Belgian: doctoral scholarship
    "junior",           # junior researcher / junior analyst
    "internship",
    "stage",            # French/Belgian internship
    "trainee",
    "werkstudent",      # German: student worker
    "student assistant",
    "studentische",     # German: studentische Hilfskraft = student assistant
    "hilfskraft",       # German student assistant
    "research assistant",
    "onderzoeksassistent",
    "wetenschappelijk medewerker",  # NL: research staff (often master's level)
    "aio",              # NL: assistent in opleiding (PhD student)
]


def is_eligible(title: str) -> bool:
    """Return True if the position is likely accessible to a master's graduate.

    Blocks positions that typically require an existing PhD (professor, postdoc,
    research fellow, senior researcher, lecturer).  Gives benefit of the doubt
    to ambiguous titles like plain 'Researcher' or 'Policy Analyst'.
    """
    t = title.lower()
    # Explicit PhD / junior / intern markers — never exclude these
    if any(p in t for p in _ELIGIBLE_OVERRIDE):
        return True
    # Title clearly signals a post-PhD requirement
    if any(p in t for p in _INELIGIBLE):
        return False
    # Benefit of the doubt (e.g. 'Researcher', 'Analyst', 'Policy Officer')
    return True


def is_relevant(title: str, description: str = "", institution: str = "") -> bool:
    """Return True if the job matches at least one IR/security keyword."""
    haystack = f"{title} {description} {institution}".lower()
    return any(_kw_matches(kw, haystack) for kw in _LOWER)


def keyword_score(title: str, description: str = "") -> int:
    """Count distinct keyword matches — used to sort the digest by relevance."""
    haystack = f"{title} {description}".lower()
    return sum(1 for kw in _LOWER if _kw_matches(kw, haystack))
