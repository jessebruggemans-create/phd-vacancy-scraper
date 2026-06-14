"""Central configuration — keywords, email settings, database path."""
import os

# ── Relevance keywords ────────────────────────────────────────────────────────
# A job is considered relevant if its title or description contains ≥1 keyword.
# Matched case-insensitively. Order does not matter.
KEYWORDS: list[str] = [
    # ── Core disciplines ──────────────────────────────────────────────────────
    "international relations", "international politics", "world politics",
    "international security", "global security", "human security",
    "security studies", "strategic studies", "security policy",
    "defence studies", "defense studies", "defence policy", "defense policy",
    "military studies", "military affairs", "military history",
    "peace studies", "conflict studies", "conflict resolution",
    "peace and conflict", "war and peace",
    # ── Political science / IR theory ─────────────────────────────────────────
    "political science", "comparative politics", "global governance",
    "foreign policy", "diplomacy", "geopolitics", "political theory",
    "securitisation", "securitization",
    "soft power", "hard power", "smart power",
    "multipolar", "multipolarity",
    "strategic competition", "great power competition", "great power rivalry",
    "geoeconomics", "geo-economics",
    "authoritarian", "democratic backsliding",
    # ── NATO / deterrence / maritime ──────────────────────────────────────────
    "nato", "deterrence", "extended deterrence", "nuclear deterrence",
    "maritime security", "naval", "sea power", "seapower",
    "transatlantic", "alliance politics",
    "collective defence", "collective defense",
    # ── Arms control / WMD / non-proliferation ────────────────────────────────
    "arms control", "non-proliferation", "nonproliferation",
    "nuclear security", "nuclear policy", "nuclear weapons",
    "disarmament", "wmd", "cbrn",
    "autonomous weapons", "lethal autonomous",
    # ── European security / CSDP ──────────────────────────────────────────────
    "csdp", "european security", "eu security",
    "european defence", "european defense",
    "pesco", "common security and defence policy",
    # ── Hybrid warfare / cyber / information ──────────────────────────────────
    "hybrid warfare", "hybrid threats", "hybrid conflict",
    "cyber security", "cybersecurity", "information warfare",
    "disinformation", "grey zone", "gray zone", "lawfare",
    # ── Conflict / crisis / peace ─────────────────────────────────────────────
    "grand strategy", "crisis management", "crisis response",
    "intelligence studies",
    "terrorism", "counter-terrorism", "counterterrorism",
    "radicalisation", "radicalization", "extremism",
    "insurgency", "asymmetric warfare", "counterinsurgency", "counter-insurgency",
    "coercive diplomacy", "economic statecraft", "sanctions",
    "peacekeeping", "peacebuilding", "stabilisation", "stabilization",
    "strategic communication", "military sociology",
    "humanitarian intervention", "responsibility to protect",
    "state fragility", "fragile states",
    "proxy war", "proxy conflict",
    # ── Area studies ──────────────────────────────────────────────────────────
    "russian foreign policy", "chinese foreign policy",
    "indo-pacific", "middle east security",
    # ── Dutch / Belgian academic terms (catches NL-language postings) ─────────
    "internationale betrekkingen",   # international relations
    "buitenlandse politiek",         # foreign policy
    "veiligheidsstudies",            # security studies
    "strategische studies",          # strategic studies
    "vredesonderzoek", "vredesstudies",  # peace research / peace studies
    "conflictstudies", "conflictresolutie",
    "politicologie",                 # political science
    "internationale veiligheid",     # international security
    "defensiestudies",               # defence studies
    # ── German terms (for SWP Berlin and other German sources) ───────────────
    "sicherheitspolitik",            # security policy
    "außenpolitik",                  # foreign policy
    "verteidigungspolitik",          # defence policy
    "friedensforschung",             # peace research
    "internationale beziehungen",    # international relations
    "rüstungskontrolle",             # arms control
    "europäische sicherheit",        # european security
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

# ── Portals that cannot be scraped (JS-rendered) — linked in every digest ─────
MANUAL_PORTALS: list[tuple[str, str]] = [
    ("KU Leuven", "https://www.kuleuven.be/personeel/jobsite/jobs/phd?lang=en"),
    ("UAntwerp", "https://www.uantwerpen.be/nl/jobs/vacatures/"),
    ("Leiden", "https://careers.universiteitleiden.nl/"),
    ("UvA", "https://www.uva.nl/en/about-the-uva/working-at-the-uva/vacancies/vacancies.html"),
    ("Tilburg", "https://www.tilburguniversity.edu/about/working-at-tilburg-university"),
    ("EUR", "https://www.eur.nl/en/about-eur/working-eur/vacancies"),
    ("IISS", "https://www.iiss.org/careers/"),
    ("Clingendael", "https://www.careers.clingendael.org/vacancy-jobs/overview-jobs-extern"),
]

# ── HTTP politeness ───────────────────────────────────────────────────────────
REQUEST_DELAY   = 2.0   # seconds between requests to the same domain
REQUEST_TIMEOUT = 15    # seconds per request
MAX_RETRIES     = 2
