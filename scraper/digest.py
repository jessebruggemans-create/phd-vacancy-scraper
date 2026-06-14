"""HTML email builder and Gmail SMTP sender."""
import logging
import smtplib
from collections import defaultdict
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from scraper.config import (
    GMAIL_APP_PASSWORD,
    GMAIL_RECIPIENT,
    GMAIL_SENDER,
    LINKEDIN_SEARCH_URL,
)

logger = logging.getLogger(__name__)

_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     margin:0;padding:0;background:#f2f3f7;color:#1a1a2e}
.wrap{max-width:700px;margin:0 auto;background:#fff}
.hdr{background:#1a3560;color:#fff;padding:28px 32px}
.hdr h1{margin:0;font-size:20px;font-weight:600;letter-spacing:-.3px}
.hdr p{margin:6px 0 0;font-size:13px;opacity:.7}
.stats{display:flex;gap:24px;margin-top:14px}
.stat{background:rgba(255,255,255,.12);border-radius:6px;padding:8px 16px;text-align:center}
.stat-n{font-size:22px;font-weight:700;display:block}
.stat-l{font-size:11px;opacity:.75;text-transform:uppercase;letter-spacing:.06em}
.body{padding:24px 32px}
.sec-hdr{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
         color:#fff;background:#1a3560;padding:8px 14px;border-radius:4px;
         margin:28px 0 14px;display:inline-block}
.sec-hdr.active{background:#4a5568;color:#e2e8f0}
.job{padding:14px 0;border-bottom:1px solid #f0f0f0}
.job:last-child{border-bottom:none}
.job-title a{font-size:15px;font-weight:600;color:#1a3560;text-decoration:none}
.job-meta{font-size:12px;color:#666;margin:3px 0 0}
.job-desc{font-size:12px;color:#555;margin:5px 0 0;line-height:1.5}
.badges{margin-top:7px;display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.badge{font-size:11px;padding:2px 8px;border-radius:10px;
       background:#eef2ff;color:#3d5af1}
.badge.new{background:#d4edda;color:#155724;font-weight:700}
.badge.src{background:#f0f0f0;color:#555}
.dl{font-size:11px;padding:2px 8px;border-radius:10px;
    background:#fff5f5;color:#c0392b}
.src-label{font-size:10px;font-weight:600;letter-spacing:.06em;
           text-transform:uppercase;color:#999;
           border-bottom:1px solid #eee;padding-bottom:6px;
           margin:16px 0 10px}
.li-box{background:#f0f7ff;border-radius:8px;padding:14px 18px;
        margin:24px 0;font-size:13px;color:#444}
.li-box a{color:#0077b5;font-weight:600;text-decoration:none}
.no-new{padding:20px 0;color:#888;font-size:13px;font-style:italic}
.footer{padding:18px 32px;background:#f9f9f9;font-size:11px;color:#aaa;
        border-top:1px solid #eee;line-height:1.7}
"""


def _render_job(job: dict, show_new_badge: bool = True) -> str:
    badges = []
    if show_new_badge and job.get("is_new"):
        badges.append('<span class="badge new">NEW</span>')
    badges.append(f'<span class="badge src">{job["source"]}</span>')
    if job.get("deadline"):
        badges.append(f'<span class="dl">Deadline: {job["deadline"]}</span>')

    meta_parts = []
    if job.get("institution"):
        meta_parts.append(job["institution"])
    if job.get("location"):
        meta_parts.append(job["location"])
    meta = " &middot; ".join(meta_parts)

    desc = (
        f'<div class="job-desc">{job["description"][:220]}...</div>'
        if job.get("description")
        else ""
    )

    return f"""
<div class="job">
  <div class="job-title"><a href="{job['url']}" target="_blank">{job['title']}</a></div>
  {'<div class="job-meta">' + meta + '</div>' if meta else ''}
  {desc}
  <div class="badges">{''.join(badges)}</div>
</div>"""


def build_html(jobs: list[dict]) -> str:
    today = date.today().strftime("%d %B %Y")
    new_jobs   = [j for j in jobs if j.get("is_new")]
    known_jobs = [j for j in jobs if not j.get("is_new")]
    n_new   = len(new_jobs)
    n_total = len(jobs)

    # ── Stats header ──────────────────────────────────────────────────────────
    stats = f"""
<div class="stats">
  <div class="stat">
    <span class="stat-n">{n_new}</span>
    <span class="stat-l">New this week</span>
  </div>
  <div class="stat">
    <span class="stat-n">{n_total}</span>
    <span class="stat-l">Total active</span>
  </div>
</div>"""

    # ── New vacancies section ─────────────────────────────────────────────────
    if new_jobs:
        new_items = "".join(_render_job(j, show_new_badge=False) for j in new_jobs)
        new_section = f"""
<div class="sec-hdr">New this week &mdash; {n_new} listing{'s' if n_new != 1 else ''}</div>
{new_items}"""
    else:
        new_section = """
<div class="sec-hdr">New this week</div>
<div class="no-new">No new listings found this week.</div>"""

    # ── All active vacancies section (grouped by source) ─────────────────────
    if known_jobs:
        by_source: dict[str, list] = defaultdict(list)
        for j in known_jobs:
            by_source[j["source"]].append(j)

        active_body = ""
        for source in sorted(by_source):
            items = "".join(_render_job(j) for j in by_source[source])
            active_body += f"""
<div class="src-label">{source} &middot; {len(by_source[source])}</div>
{items}"""

        active_section = f"""
<div class="sec-hdr active">Still active &mdash; {len(known_jobs)} listing{'s' if len(known_jobs) != 1 else ''}</div>
{active_body}"""
    else:
        active_section = ""

    linkedin_box = f"""
<div class="li-box">
  <strong>LinkedIn</strong> &mdash; always worth a manual check:<br>
  <a href="{LINKEDIN_SEARCH_URL}" target="_blank">Open LinkedIn PhD search (past 7 days) &rarr;</a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhD Vacancy Digest -- {today}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>PhD Vacancy Digest</h1>
    <p>{today}</p>
    {stats}
  </div>
  <div class="body">
    {new_section}
    {active_section}
    {linkedin_box}
  </div>
  <div class="footer">
    Sources: AcademicTransfer &middot; EURAXESS &middot;
    KU&nbsp;Leuven &middot; UGent &middot; UAntwerp &middot; VUB &middot; UHasselt &middot;
    Leiden &middot; UvA &middot; Utrecht &middot; Groningen &middot; VU &middot;
    Radboud &middot; Maastricht &middot; Tilburg &middot; EUR &middot;
    Clingendael &middot; HCSS &middot; Egmont &middot; Asser &middot; Flemish&nbsp;Peace&nbsp;Institute
  </div>
</div>
</body>
</html>"""


def send_digest(jobs: list[dict]) -> bool:
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_SENDER or GMAIL_APP_PASSWORD not configured -- email skipped.")
        return False

    today = date.today().strftime("%d %b %Y")
    n_new   = sum(1 for j in jobs if j.get("is_new"))
    n_total = len(jobs)
    subject = f"PhD Digest {today} -- {n_new} new, {n_total} total active"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_RECIPIENT
    msg.attach(MIMEText(build_html(jobs), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())
        logger.info("Digest sent to %s (%d new, %d total).", GMAIL_RECIPIENT, n_new, n_total)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)
        return False
