"""Central configuration — keywords, email settings, database path."""
import os

# ── Relevance keywords ────────────────────────────────────────────────────────
# A job is considered relevant if its title or description contains ≥1 keyword.
# Matched case-insensitively. Order does not matter.
KEYWORDS: list[str] = [
    # Core disciplines
    "international relations", "international politics", "world politics",
    "security studies", "strategic studies", "security policy",
    "defence studies", "defense studies", "defence policy", "defense policy",
    "military studies", "military affairs", "military history",
    "peace studies", "conflict studies", "conflict resolution",
    "peace and conflict", "war and peace",
    # Political science adjacent
    "political science", "comparative politics", "global governance",
    "foreign policy", "diplomacy", "geopolitics", "political theory",
    # NATO / deterrence / maritime
    "nato", "deterrence", "extended deterrence", "nuclear deterrence",
    "maritime security", "naval", "sea power", "seapower",
    "transatlantic", "alliance politics",
    "collective defence", "collective defense",
    # Arms control / non-proliferation
    "arms control", "non-proliferation", "nonproliferation",
    "nuclear security", "nuclear policy", "nuclear weapons",
    "disarmament", "wmd", "cbrn",
    # European security / CSDP
    "csdp", "european security", "eu security",
    "european defence", "european defense",
    "pesco", "common security and defence policy",
    # Hybrid warfare / cyber
    "hybrid warfare", "hybrid threats", "hybrid conflict",
    "cyber security", "cybersecurity", "information warfare",
    "disinformation", "grey zone", "gray zone", "lawfare",
    # Broader security
    "grand strategy", "crisis management", "crisis response",
    "intelligence studies",
    "terrorism", "counter-terrorism", "counterterrorism",
    "radicalisation", "radicalization", "extremism",
    "insurgency", "asymmetric warfare",
    "great power competition", "great power rivalry",
    "coercive diplomacy", "economic statecraft", "sanctions",
    "peacekeeping", "peacebuilding", "stabilisation", "stabilization",
    "strategic communication", "military sociology",
    # Area studies relevant to the field
    "russian foreign policy", "chinese foreign policy",
    "indo-pacific", "middle east security",
]

# ── Email ─────────────────────────────────────────────────────────────────────
# Set via GitHub Secrets (or .env for local runs).
GMAIL_SENDER       = os.getenv("GMAIL_SENDER", "")
GMAIL_RECIPIENT    = os.getenv("GMAIL_RECIPIENT", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "data/seen_jobs.db"

# ── LinkedIn manual-search link (included in every digest, not scraped) ───────
LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords=phd+international+relations+security+studies"
    "&location=Belgium%2C+Netherlands"
    "&f_TPR=r604800"   # past 7 days
)

# ── HTTP politeness ───────────────────────────────────────────────────────────
REQUEST_DELAY   = 2.0   # seconds between requests to the same domain
REQUEST_TIMEOUT = 15    # seconds per request
MAX_RETRIES     = 2
