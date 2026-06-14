"""Keyword-based relevance scoring, eligibility, language, and subject filtering.

Public API
----------
is_wrong_department   -- True if vacancy belongs to an excluded field (engineering, law…)
is_social_science     -- True if vacancy looks like a social-sciences position
is_eligible           -- True if position is open to master's graduates (no PhD required)
is_relevant           -- True if title/description matches IR/security keywords
is_english_or_dutch   -- True if text appears to be in English or Dutch
keyword_score         -- count of matched keywords (used for ranking)
detect_funding        -- 'funded' | 'self-funded' | 'unclear'
"""
import re

from scraper.config import KEYWORDS

_LOWER = [kw.lower() for kw in KEYWORDS]

# Pre-compile regex patterns for short keywords (≤5 chars) to enforce word
# boundaries and avoid false positives like "nato" inside "coordinator".
_SHORT_RE = {
    kw: re.compile(r"\b" + re.escape(kw) + r"\b")
    for kw in _LOWER if len(kw) <= 5
}


def _kw_matches(kw: str, haystack: str) -> bool:
    pat = _SHORT_RE.get(kw)
    if pat:
        return bool(pat.search(haystack))
    return kw in haystack


# ── Department / subject exclusion filter ─────────────────────────────────────
# Applied to ALL vacancies (including always_include sources).
# If the title, institution, or short dept snippet contains any of these terms,
# the vacancy is discarded.
#
# Note: we intentionally do NOT check the full description to avoid false
# positives from mentions like "bioterrorism" in a security-studies posting.

_DEPT_EXCLUDE_RE = re.compile(
    r"\b("
    r"engineer(?:ing)?|"
    r"law(?:yer)?|legal(?:ity)?|juridical|"
    r"medicine|medical|clinical|clinician|"
    r"dentistry|dental|pharmacy|pharmaceutical|"
    r"nursing|nurse|veterinary|"
    r"chemistry|chemical|biochem(?:istry)?|"
    r"physics|physical\s+science|biophysics|"
    r"biology|biological|biolog(?:ist|y)|"
    r"computer\s+science|informatics|information\s+systems|"
    r"data\s+science|machine\s+learning|artificial\s+intelligence|"
    r"architecture|"
    r"accounting|auditing|"
    r"finance|financial(?:\s+economics)?|"
    r"econom(?:ics|etrics|y|ist)?"
    r")\b",
    re.IGNORECASE,
)


def is_wrong_department(title: str, institution: str = "", department: str = "") -> bool:
    """Return True if the vacancy is in an excluded non-social-science field.

    Checks title, institution name, and an optional short department string.
    Does NOT check the full description to avoid false positives.
    """
    text = f"{title} {institution} {department}".strip()
    return bool(_DEPT_EXCLUDE_RE.search(text))


# ── Social-sciences inclusion filter ─────────────────────────────────────────
# Applied only to non-always_include sources (universities, EURAXESS, etc.).
# A vacancy must match at least one term to pass.
#
# This list is intentionally broad — universities name these departments
# differently (Political Science, Politics, International Studies, etc.).

_SOCIAL_SCIENCE_TERMS = [
    # Core disciplines
    "political science", "political studies", "politics",
    "international relations", "international studies", "global studies",
    "security", "defence", "defense",
    "peace", "conflict", "strategic",
    "social science", "social studies", "sociology",
    "governance", "public administration", "public policy",
    "area studies", "regional studies",
    "humanities", "liberal arts",
    "history", "historical",
    "anthropology",
    "human rights",
    "development studies", "development research",
    # Adjacent fields that our scrapers cover
    "military", "armed forces",
    "intelligence",
    "foreign policy", "diplomacy",
    "arms", "disarmament",
    "migration", "refugee",
    "geopolitics", "geostrategic",
    "european studies", "transatlantic",
    "criminology",
    "philosophy", "ethics",
    "communication", "media studies",
    "gender studies", "cultural studies",
]

# Pre-compiled for speed
_SS_PATTERN = re.compile(
    "|".join(re.escape(t) for t in sorted(_SOCIAL_SCIENCE_TERMS, key=len, reverse=True)),
    re.IGNORECASE,
)


def is_social_science(title: str, institution: str = "", department: str = "") -> bool:
    """Return True if the vacancy is plausibly in a social-sciences field.

    Checks title, institution, and short department snippet.
    Should only be called for non-always_include sources.
    """
    text = f"{title} {institution} {department}".strip()
    return bool(_SS_PATTERN.search(text))


# ── Eligibility filter ────────────────────────────────────────────────────────
_INELIGIBLE = [
    "professor",
    "postdoc", "post-doc", "post doc", "postdoctoral", "post doctoral",
    "senior lecturer", "senior research",
    "research fellow", "research director", "research group leader",
    "group leader", "chair in", "faculty position", "faculty member",
    "lecturer",
    # Dutch academic titles
    "universitair docent", "universitair hoofddocent",
    "hoogleraar", "bijzonder hoogleraar", "gewoon hoogleraar",
    # German
    "wissenschaftliche leitung", "abteilungsleiter",
]

_ELIGIBLE_OVERRIDE = [
    "phd", "ph.d", "doctoral", "promovendus", "promotieonderzoeker",
    "doctoraatsbeurs", "junior", "internship", "stage", "trainee",
    "werkstudent", "student assistant", "studentische", "hilfskraft",
    "research assistant", "onderzoeksassistent", "wetenschappelijk medewerker",
    "aio",
]


_POSTDOC_PATTERNS = ("postdoc", "post-doc", "post doc", "postdoctoral", "post doctoral")


def is_eligible(title: str) -> bool:
    """Return True if the position is likely open to a master's graduate."""
    t = title.lower()
    # Postdoc patterns must be checked BEFORE the 'doctoral' override,
    # because 'postdoctoral' contains 'doctoral' as a substring.
    if any(p in t for p in _POSTDOC_PATTERNS):
        return False
    if any(p in t for p in _ELIGIBLE_OVERRIDE):
        return True
    if any(p in t for p in _INELIGIBLE):
        return False
    return True


# ── Relevance filter ──────────────────────────────────────────────────────────

def is_relevant(title: str, description: str = "", institution: str = "") -> bool:
    """Return True if the job matches at least one IR/security keyword."""
    haystack = f"{title} {description} {institution}".lower()
    return any(_kw_matches(kw, haystack) for kw in _LOWER)


def keyword_score(title: str, description: str = "") -> int:
    """Count distinct keyword matches — used to sort the digest by relevance."""
    haystack = f"{title} {description}".lower()
    return sum(1 for kw in _LOWER if _kw_matches(kw, haystack))


# ── Language filter ───────────────────────────────────────────────────────────
_DE_CHARS  = re.compile(r"[äöüÄÖÜß]")
_DE_WORDS  = re.compile(
    r"\b(wissenschaftler|wissenschaftliche|wissenschaftlichen|"
    r"forscher|forscherin|doktorand|doktorandin|"
    r"mitarbeiter|mitarbeiterin|lehrstuhl|forschungsgruppe|"
    r"universität|hochschule|stiftung|bundesministerium|"
    r"forschungszentrum|graduiertenkolleg|stipendium)\b",
    re.IGNORECASE,
)
_FR_CHARS  = re.compile(r"[éèêëàâùûôîïçœæÉÈÊËÀÂÙÛÔÎÏÇŒÆ]")
_FR_WORDS  = re.compile(
    r"\b(chercheur|chercheuse|doctorant|doctorante|"
    r"université|recherche|candidature|candidat|"
    r"poste|concours|contrat|bourse|laboratoire|"
    r"chargé|maître|directeur|direction|"
    # Additional common French words not found in English
    r"projets|contenus|compétences|missions|"
    r"recrutement|emploi|formation|équipe|"
    r"événement|évènement|offre\s+d|"
    r"travaux|politiques|publiques|"
    r"collaborateur|collaboratrice|"
    r"responsable|coordinateur|coordinatrice)\b",
    re.IGNORECASE,
)
# French word *forms* that are unambiguously French even without accented chars.
# "internationales" (French adjective plural) vs English "international";
# "contenus" (French noun) vs English "content/contents".
# These trigger French detection on their own without needing _FR_CHARS.
_FR_FORMS  = re.compile(
    r"\b(internationales|contenus|postuler|recrutement"
    r"|responsable\s+de|coordinateur|coordinatrice"
    r"|politiques\s+publiques|sciences\s+politiques"
    r"|gestion\s+de|mise\s+en)\b",
    re.IGNORECASE,
)


def is_english_or_dutch(title: str, description: str = "") -> bool:
    """Return True if the posting appears to be in English or Dutch.

    Detects German via umlauts or German academic vocabulary.
    Detects French via accented characters AND French academic vocabulary.
    Anything else is assumed English/Dutch.
    """
    text = f"{title} {description}"
    if _DE_CHARS.search(text):
        return False
    if _DE_WORDS.search(text):
        return False
    if _FR_CHARS.search(text) and _FR_WORDS.search(text):
        return False
    if _FR_FORMS.search(text):          # distinctly French forms even without accents
        return False
    return True


# ── Funding indicator ─────────────────────────────────────────────────────────
_FUNDED_RE = re.compile(
    r"\b("
    r"fwo|nwo|dfg|anr|erc|"
    r"fully\s+funded|funded\s+position|funded\s+ph\.?d|"
    r"scholarship|stipend|bursary|"
    r"fellowship\s+stipend|doctoral\s+grant|"
    r"salary|salaries|paid\s+position"
    r")\b",
    re.IGNORECASE,
)

_SELF_FUNDED_RE = re.compile(
    r"\b("
    r"self[- ]fund(?:ed|ing)?|"
    r"own\s+fund(?:ing|s)?|"
    r"applicants?\s+(?:must|are\s+required\s+to)\s+(?:provide|have|secure|bring|source)\s+(?:their\s+own\s+)?fund|"
    r"unfunded"
    r")\b",
    re.IGNORECASE,
)


def detect_funding(description: str) -> str:
    """Scan description for funding signals.

    Returns:
        'funded'      -- grant/scholarship/stipend/salary mentioned
        'self-funded' -- applicant must supply own funding
        'unclear'     -- no clear signal found
    """
    if not description:
        return "unclear"
    # Self-funded check takes priority (more specific)
    if _SELF_FUNDED_RE.search(description):
        return "self-funded"
    if _FUNDED_RE.search(description):
        return "funded"
    return "unclear"
