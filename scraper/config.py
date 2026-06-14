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
    "&location=Belgium%2C+Netherlands%2C+Germany%2C+France"
    "&f_TPR=r604800"   # past 7 days
)

# ── Portals that cannot be scraped (JS-rendered) — linked in every digest ─────
# Grouped by country: Belgium (BE), Netherlands (NL), Germany (DE), France (FR)
# Scraped automatically: KU Leuven / UAntwerp via AcademicTransfer; EUR + ISS + Twente
#   via universities_nl.py scrapers; Tübingen via universities_de.py RSS.
MANUAL_PORTALS: list[tuple[str, str, str]] = [
    # ── Belgium ──────────────────────────────────────────────────────────────
    ("KU Leuven",           "https://www.kuleuven.be/personeel/jobsite/jobs/phd?lang=en",                     "BE"),
    ("UAntwerp",            "https://www.uantwerpen.be/nl/jobs/vacatures/",                                    "BE"),
    # ── Netherlands ──────────────────────────────────────────────────────────
    ("Leiden",              "https://careers.universiteitleiden.nl/",                                          "NL"),
    ("UvA",                 "https://www.uva.nl/en/about-the-uva/working-at-the-uva/vacancies/vacancies.html", "NL"),
    ("Tilburg",             "https://www.tilburguniversity.edu/about/working-at-tilburg-university",            "NL"),
    ("Clingendael",         "https://www.careers.clingendael.org/vacancy-jobs/overview-jobs-extern",           "NL"),
    ("IISS",                "https://www.iiss.org/careers/",                                                   "NL"),
    ("ICCT",                "https://www.icct.nl/about/",                                                      "NL"),
    ("NLDA",                "https://www.defensie.nl/onderwerpen/werken-bij-defensie",                         "NL"),
    # ── Germany ──────────────────────────────────────────────────────────────
    ("Hertie School",       "https://www.hertie-school.org/en/jobs",                                           "DE"),
    ("FU Berlin",           "https://www.fu-berlin.de/universitaet/beruf-karriere/jobs/wiss/gesamtliste/index.html", "DE"),
    ("HU Berlin",           "https://www.hu-berlin.de/en/about/working-at-hu/vacancies",                       "DE"),
    ("Potsdam",             "https://www.uni-potsdam.de/de/stellenangebote",                                   "DE"),
    ("Goethe Frankfurt",    "https://www.uni-frankfurt.de/karriere",                                           "DE"),
    ("LMU Munich",          "https://www.lmu.de/de/die-lmu/arbeiten-an-der-lmu/stellenangebote/",             "DE"),
    ("Helmut Schmidt HSU",  "https://www.hsu-hh.de/karriere",                                                  "DE"),
    ("Bundeswehr Munich",   "https://www.unibw.de/stellenausschreibungen",                                     "DE"),
    ("Cologne",             "https://verwaltung.uni-koeln.de/stellenausschreibungen/content/e3/index_eng.html","DE"),
    ("Mannheim",            "https://www.uni-mannheim.de/en/university/working-at-the-university-of-mannheim/","DE"),
    ("Konstanz",            "https://www.uni-konstanz.de/en/university/jobs-and-career/",                      "DE"),
    ("PRIF/HSFK",           "https://www.prif.org/karriere",                                                   "DE"),
    ("BICC Bonn",           "https://www.bicc.de/about-us/jobs/",                                              "DE"),
    # ── France ───────────────────────────────────────────────────────────────
    ("Sciences Po Paris",   "https://www.sciencespo.fr/admissions/en/phd/",                                    "FR"),
    ("Sciences Po Bordeaux","https://www.sciencespobordeaux.fr/en/institution/jobs-training/",                  "FR"),
    ("Sciences Po Grenoble","https://www.sciencespo-grenoble.fr/en/jobs/",                                     "FR"),
    ("Sciences Po Toulouse","https://www.sciencespo-toulouse.fr/recrutement-offres-demploi/",                  "FR"),
    ("Sciences Po Rennes",  "https://www.sciencespo-rennes.fr/en/jobs/",                                       "FR"),
    ("Paris I Sorbonne",    "https://www.univ-paris1.fr/universite/recrutement/",                              "FR"),
    ("Paris II Assas",      "https://www.u-paris2.fr/fr/recrutement/offres-demploi",                          "FR"),
    ("EHESS",               "https://www.ehess.fr/fr/recrutement",                                             "FR"),
    ("Strasbourg",          "https://www.unistra.fr/universite/recrutement",                                   "FR"),
    ("IRSEM",               "https://www.irsem.fr/en/",                                                        "FR"),
    ("FRS",                 "https://www.frstrategie.org/frs/emplois-stages",                                  "FR"),
    ("IFRI",                "https://www.ifri.org/en/recruitment",                                             "FR"),
    # ── International ────────────────────────────────────────────────────────
    ("NATO",                "https://www.nato.int/cps/en/natohq/71700.htm",                                    "Other"),
]

# ── HTTP politeness ───────────────────────────────────────────────────────────
REQUEST_DELAY   = 2.0   # seconds between requests to the same domain
REQUEST_TIMEOUT = 15    # seconds per request
MAX_RETRIES     = 2
