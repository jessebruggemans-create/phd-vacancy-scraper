"""HTML email builder and Gmail SMTP sender."""
import logging
import smtplib
from collections import defaultdict
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from scraper.config import (
    GMAIL_APP_PASSWORD,
    GMAIL_RECIPIENT,
    GMAIL_SENDER,
    LINKEDIN_SEARCH_URL,
    MANUAL_PORTALS,
)

logger = logging.getLogger(__name__)

# ── Country metadata ──────────────────────────────────────────────────────────
_COUNTRY_ORDER  = ["BE", "NL", "DE", "FR", "Other"]
_COUNTRY_LABELS = {
    "BE":    "&#127463;&#127466; Belgium",
    "NL":    "&#127475;&#127473; Netherlands",
    "DE":    "&#127465;&#127466; Germany",
    "FR":    "&#127467;&#127479; France",
    "Other": "Other / International",
}


def _country_of(job: dict) -> str:
    loc = job.get("location", "")
    for code in ("BE", "NL", "DE", "FR"):
        if loc.endswith(f", {code}") or loc == code:
            return code
    return "Other"


# ── Deadline helpers ──────────────────────────────────────────────────────────

def _parse_deadline(s: str) -> date | None:
    if not s:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    # Try "22 June 2026" / "22 Jun 2026"
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s[:20].strip(), fmt).date()
        except ValueError:
            continue
    return None


def _deadline_sort_key(job: dict):
    dl = _parse_deadline(job.get("deadline", ""))
    return (1, date.max) if dl is None else (0, dl)


def _is_closing_soon(deadline: str, today: date, days: int = 14) -> bool:
    dl = _parse_deadline(deadline)
    if dl is None:
        return False
    return date.today() <= dl <= today + timedelta(days=days)


# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f2f3f7; color: #1a1a2e; }
.wrap { max-width: 700px; margin: 0 auto; background: #fff; }

/* Header */
.hdr { background: #1a3560; color: #fff; padding: 28px 32px; }
.hdr h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: -.3px; }
.hdr p  { margin: 4px 0 0; font-size: 13px; opacity: .7; }
.summary-line { margin-top: 12px; font-size: 14px; font-weight: 500;
                background: rgba(255,255,255,.15); border-radius: 6px;
                padding: 8px 14px; display: inline-block; }

/* Country sections */
.body { padding: 24px 32px; }
.country-hdr { font-size: 14px; font-weight: 700; color: #fff;
               background: #1a3560; padding: 8px 16px; border-radius: 5px;
               margin: 28px 0 12px; }
.country-hdr:first-child { margin-top: 0; }

/* Job cards */
.job { padding: 13px 0; border-bottom: 1px solid #f0f0f0; }
.job:last-child { border-bottom: none; }
.job-title a { font-size: 15px; font-weight: 600; color: #1a3560;
               text-decoration: none; }
.job-title a:hover { text-decoration: underline; }
.job-meta { font-size: 12px; color: #666; margin: 3px 0 0; }
.job-desc { font-size: 12px; color: #555; margin: 5px 0 0; line-height: 1.5; }

/* Badge row */
.badges { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.badge-new      { background: #d4edda; color: #155724; font-weight: 700; }
.badge-src      { background: #f0f0f0; color: #555; }
.badge-kw       { background: #eef2ff; color: #3d5af1; }
.badge-funded   { background: #d4edda; color: #155724; font-weight: 600; }
.badge-self     { background: #f8d7da; color: #721c24; font-weight: 600; }
.badge-unclear  { background: #e8e8e8; color: #666; }
.badge-closing  { background: #f8d7da; color: #c0392b; font-weight: 700; }

/* Deadline */
.dl         { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.dl-normal  { background: #fff5f5; color: #c0392b; }
.dl-soon    { background: #c0392b; color: #fff; font-weight: 700; }

/* LinkedIn & portals boxes */
.li-box { background: #f0f7ff; border-radius: 8px; padding: 14px 18px;
          margin: 24px 0; font-size: 13px; color: #444; }
.li-box a { color: #0077b5; font-weight: 600; text-decoration: none; }
.portals { background: #fff8e1; border-radius: 8px; padding: 14px 18px;
           margin: 20px 0; font-size: 12px; color: #555; line-height: 2; }
.portals strong { display: block; margin-bottom: 4px; font-size: 13px; color: #333; }
.portals .country-row { margin-bottom: 6px; }
.portals a { color: #0066cc; text-decoration: none; margin-right: 10px; white-space: nowrap; }

/* Health section */
.health { background: #f9f9f9; border-radius: 8px; padding: 14px 18px;
          margin: 20px 0; font-size: 12px; }
.health-title { font-size: 13px; font-weight: 700; color: #333; margin-bottom: 10px; }
.health-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
.health-row { display: flex; align-items: center; gap: 6px; }
.h-ok   { color: #155724; }
.h-err  { color: #721c24; }
.h-zero { color: #856404; }

/* Footer */
.footer { padding: 18px 32px; background: #f9f9f9; font-size: 11px;
          color: #aaa; border-top: 1px solid #eee; line-height: 1.7; }
.no-results { padding: 20px 0; color: #888; font-size: 13px; font-style: italic; }
"""


# ── Per-job renderer ──────────────────────────────────────────────────────────

def _render_job(job: dict, today: date) -> str:
    badges: list[str] = []

    if job.get("is_new"):
        badges.append('<span class="badge badge-new">NEW</span>')

    # Deadline / closing-soon
    dl_str = job.get("deadline", "")
    if dl_str:
        soon = _is_closing_soon(dl_str, today)
        if soon:
            badges.append(
                f'<span class="badge badge-closing">&#9888; Closing soon</span>'
                f'<span class="dl dl-soon">Deadline: {dl_str}</span>'
            )
        else:
            badges.append(f'<span class="dl dl-normal">Deadline: {dl_str}</span>')

    # Source
    badges.append(f'<span class="badge badge-src">{job.get("source","")}</span>')

    # Keyword match count
    kw = job.get("keyword_count", 0)
    if kw > 0:
        badges.append(
            f'<span class="badge badge-kw">Match: {kw} keyword{"s" if kw != 1 else ""}</span>'
        )

    # Funding
    funding = job.get("funding", "unclear")
    if funding == "funded":
        badges.append('<span class="badge badge-funded">&#10003; Funded</span>')
    elif funding == "self-funded":
        badges.append('<span class="badge badge-self">&#9888; Self-funded</span>')
    else:
        badges.append('<span class="badge badge-unclear">Funding unclear</span>')

    # Meta line (institution · location)
    meta_parts = []
    if job.get("institution"):
        meta_parts.append(job["institution"])
    if job.get("location"):
        meta_parts.append(job["location"])
    meta = " &middot; ".join(meta_parts)

    desc_html = (
        f'<div class="job-desc">{job["description"][:220]}…</div>'
        if job.get("description") else ""
    )

    return f"""
<div class="job">
  <div class="job-title"><a href="{job['url']}" target="_blank">{job['title']}</a></div>
  {'<div class="job-meta">' + meta + '</div>' if meta else ''}
  {desc_html}
  <div class="badges">{''.join(badges)}</div>
</div>"""


# ── Health section renderer ───────────────────────────────────────────────────

def _render_health(health: dict[str, dict]) -> str:
    if not health:
        return ""

    rows = []
    for src in sorted(health):
        h = health[src]
        if h["status"] == "error":
            err = h.get("error", "unknown error")[:80]
            rows.append(
                f'<div class="health-row">'
                f'<span class="h-err">&#10007;</span>'
                f'<span><strong>{src}</strong> — <em>{err}</em></span>'
                f'</div>'
            )
        else:
            raw = h.get("raw", 0)
            acc = h.get("accepted", 0)
            if raw == 0:
                icon = '<span class="h-zero">&#9711;</span>'
                detail = "no listings found"
            else:
                icon = '<span class="h-ok">&#10003;</span>'
                detail = f"{raw} fetched, {acc} accepted"
            rows.append(
                f'<div class="health-row">'
                f'{icon}'
                f'<span><strong>{src}</strong> &mdash; {detail}</span>'
                f'</div>'
            )

    grid = '<div class="health-grid">' + "".join(rows) + "</div>"
    return f"""
<div class="health">
  <div class="health-title">Scraper health this week</div>
  {grid}
</div>"""


# ── Main HTML builder ─────────────────────────────────────────────────────────

def build_html(jobs: list[dict], health: dict[str, dict]) -> str:
    today     = date.today()
    today_str = today.strftime("%d %B %Y")

    new_jobs = [j for j in jobs if j.get("is_new")]
    n_new    = len(new_jobs)

    # Summary stats (computed from new jobs only)
    n_inst = len({j.get("institution", "") for j in new_jobs if j.get("institution")})
    countries_with_new = {_country_of(j) for j in new_jobs} - {"Other"}
    n_countries = len(countries_with_new)

    if n_new == 0:
        summary_text = "No new vacancies found this week."
    else:
        vac_word = "vacancy" if n_new == 1 else "vacancies"
        inst_word = "institution" if n_inst == 1 else "institutions"
        ctr_word  = "country" if n_countries == 1 else "countries"
        summary_text = (
            f"{n_new} new {vac_word} this week "
            f"across {n_inst} {inst_word} in {n_countries} {ctr_word}."
        )

    # ── Group all jobs by country, sorted by deadline ─────────────────────────
    by_country: dict[str, list] = defaultdict(list)
    for j in jobs:
        by_country[_country_of(j)].append(j)

    country_sections_html = ""
    for code in _COUNTRY_ORDER:
        group = by_country.get(code)
        if not group:
            continue
        label = _COUNTRY_LABELS.get(code, code)
        # Sort: earliest deadline first, no-deadline last
        group_sorted = sorted(group, key=_deadline_sort_key)
        items_html = "".join(_render_job(j, today) for j in group_sorted)
        n = len(group)
        vword = "vacancy" if n == 1 else "vacancies"
        country_sections_html += f"""
<div class="country-hdr">{label} &mdash; {n} {vword}</div>
{items_html}"""

    if not country_sections_html:
        country_sections_html = '<div class="no-results">No relevant vacancies found this week.</div>'

    # ── LinkedIn box ──────────────────────────────────────────────────────────
    linkedin_box = f"""
<div class="li-box">
  <strong>LinkedIn</strong> &mdash; always worth a manual check:<br>
  <a href="{LINKEDIN_SEARCH_URL}" target="_blank">Open LinkedIn PhD search (past 7 days) &rarr;</a>
</div>"""

    # ── Manual portals box ────────────────────────────────────────────────────
    portals_by_country: dict[str, list] = defaultdict(list)
    for name, url, country in MANUAL_PORTALS:
        portals_by_country[country].append((name, url))

    portal_rows = ""
    for code in ("BE", "NL", "DE", "FR", "Other"):
        entries = portals_by_country.get(code, [])
        if not entries:
            continue
        flag = _COUNTRY_LABELS.get(code, code)
        links = " ".join(
            f'<a href="{u}" target="_blank">{n} &rarr;</a>'
            for n, u in entries
        )
        portal_rows += f'<div class="country-row"><strong>{flag}:</strong> {links}</div>\n'

    portals_box = f"""
<div class="portals">
  <strong>Check manually this week (not auto-scraped):</strong>
  {portal_rows}
</div>"""

    # ── Health section ────────────────────────────────────────────────────────
    health_section = _render_health(health)

    # ── Footer source list ────────────────────────────────────────────────────
    scraped_sources = (
        "AcademicTransfer &middot; EURAXESS (BE/NL/DE/FR) &middot; "
        "UGent &middot; VUB &middot; UHasselt &middot; "
        "Utrecht &middot; Groningen &middot; VU &middot; Radboud &middot; Maastricht &middot; "
        "EUR Rotterdam &middot; ISS Den Haag &middot; Twente &middot; "
        "T&uuml;bingen (RSS) &middot; "
        "Egmont &middot; HCSS &middot; Asser &middot; Flemish&nbsp;Peace&nbsp;Institute &middot; "
        "GRIP &middot; IRIS &middot; TNO &middot; NIOD &middot; "
        "SWP&nbsp;Berlin &middot; DGAP &middot; IFSH"
    )
    manual_list = " &middot; ".join(n for n, _, _ in MANUAL_PORTALS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhD Vacancy Digest &mdash; {today_str}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <h1>PhD Vacancy Digest</h1>
    <p>{today_str}</p>
    <div class="summary-line">{summary_text}</div>
  </div>

  <div class="body">
    {country_sections_html}
    {linkedin_box}
    {portals_box}
    {health_section}
  </div>

  <div class="footer">
    Auto-scraped: {scraped_sources}<br>
    Manual portals: {manual_list}
  </div>

</div>
</body>
</html>"""


# ── Email senders ─────────────────────────────────────────────────────────────

def _send_email(subject: str, html_body: str) -> bool:
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.error("GMAIL credentials not configured — email skipped.")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_RECIPIENT
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())
        logger.info("Email sent to %s: %s", GMAIL_RECIPIENT, subject)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)
        return False


def send_digest(jobs: list[dict], health: dict[str, dict]) -> bool:
    today_str = date.today().strftime("%d %b %Y")
    n_new     = sum(1 for j in jobs if j.get("is_new"))
    n_total   = len(jobs)
    subject   = f"PhD Digest {today_str} — {n_new} new, {n_total} total active"
    html      = build_html(jobs, health)
    return _send_email(subject, html)


def send_failure_alert(health: dict[str, dict]) -> bool:
    """Send a plain-text alert when the scraper is systemically broken."""
    today_str  = date.today().strftime("%d %b %Y")
    subject    = "PhD Scraper — needs attention"

    failed   = {k: v for k, v in health.items() if v.get("status") == "error"}
    zero_raw = {k: v for k, v in health.items()
                if v.get("status") == "ok" and v.get("raw", 0) == 0}
    total_raw = sum(v.get("raw", 0) for v in health.values())

    lines = [
        f"PhD Vacancy Scraper alert — {today_str}",
        "",
        f"Total raw results across all sources: {total_raw}",
        f"Sources that crashed: {len(failed)}",
        f"Sources returning zero results: {len(zero_raw)}",
        "",
    ]

    if failed:
        lines.append("CRASHED SOURCES:")
        for src, h in failed.items():
            lines.append(f"  - {src}: {h.get('error','unknown error')}")
        lines.append("")

    if total_raw == 0:
        lines.append("WARNING: No results at all — check network / site structure changes.")

    body_text = "\n".join(lines)

    # Wrap in minimal HTML
    body_html = f"""<!DOCTYPE html>
<html><body style="font-family:monospace;padding:20px;max-width:600px">
<h2 style="color:#c0392b">PhD Scraper &mdash; needs attention</h2>
<pre style="background:#f9f9f9;padding:16px;border-radius:6px">{body_text}</pre>
</body></html>"""

    return _send_email(subject, body_html)
