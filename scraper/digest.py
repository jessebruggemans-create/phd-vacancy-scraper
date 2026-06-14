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

# ── Inline CSS ─────────────────────────────────────────────────────────────────
_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     margin:0;padding:0;background:#f2f3f7;color:#1a1a2e}
.wrap{max-width:680px;margin:0 auto;background:#fff}
.hdr{background:#1a3560;color:#fff;padding:28px 32px}
.hdr h1{margin:0;font-size:20px;font-weight:600;letter-spacing:-.3px}
.hdr p{margin:6px 0 0;font-size:13px;opacity:.7}
.body{padding:24px 32px}
.section{margin-bottom:32px}
.sec-label{font-size:11px;font-weight:600;letter-spacing:.08em;
           text-transform:uppercase;color:#888;
           border-bottom:1px solid #eee;padding-bottom:8px;margin-bottom:16px}
.job{padding:14px 0;border-bottom:1px solid #f2f2f2}
.job:last-child{border-bottom:none}
.job-title a{font-size:15px;font-weight:600;color:#1a3560;text-decoration:none}
.job-meta{font-size:13px;color:#666;margin:4px 0 0}
.job-desc{font-size:13px;color:#555;margin:6px 0 0;line-height:1.5}
.badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;
       background:#eef2ff;color:#3d5af1;margin-top:8px}
.dl{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;
    background:#fff5f5;color:#c0392b;margin-top:8px;margin-left:4px}
.li-box{background:#f0f7ff;border-radius:8px;padding:16px 20px;
        margin:8px 0 24px;font-size:13px;color:#444}
.li-box a{color:#0077b5;font-weight:600;text-decoration:none}
.no-jobs{padding:48px 32px;text-align:center;color:#aaa;font-size:14px}
.footer{padding:20px 32px;background:#f9f9f9;font-size:12px;color:#aaa;
        border-top:1px solid #eee;line-height:1.6}
"""


def _render_job(job: dict) -> str:
    deadline = (
        f'<span class="dl">Deadline: {job["deadline"]}</span>'
        if job.get("deadline")
        else ""
    )
    loc = f" · {job['location']}" if job.get("location") else ""
    desc = (
        f'<p class="job-desc">{job["description"][:220]}…</p>'
        if job.get("description")
        else ""
    )
    return f"""
<div class="job">
  <div class="job-title"><a href="{job['url']}" target="_blank">{job['title']}</a></div>
  <div class="job-meta">{job.get('institution', '')}{loc}</div>
  {desc}
  <span class="badge">{job['source']}</span>{deadline}
</div>"""


def build_html(jobs: list[dict]) -> str:
    today = date.today().strftime("%d %B %Y")
    n = len(jobs)
    summary = (
        f"{n} new PhD vacanci{'es' if n != 1 else 'y'}"
        if n
        else "No new vacancies this week"
    )

    if jobs:
        by_source: dict[str, list] = defaultdict(list)
        for j in jobs:
            by_source[j["source"]].append(j)

        body = ""
        for source, src_jobs in sorted(by_source.items()):
            items = "".join(_render_job(j) for j in src_jobs)
            body += f"""
<div class="section">
  <div class="sec-label">{source} · {len(src_jobs)} new</div>
  {items}
</div>"""
    else:
        body = '<div class="no-jobs"><p>No new vacancies found this week — check back next Monday.</p></div>'

    linkedin_box = f"""
<div class="li-box">
  <strong>LinkedIn</strong> — always worth a manual check:<br>
  <a href="{LINKEDIN_SEARCH_URL}" target="_blank">Open LinkedIn PhD job search (past 7 days) →</a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PhD Vacancy Digest — {today}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>PhD Vacancy Digest</h1>
    <p>{today} · {summary}</p>
  </div>
  <div class="body">
    {body}
    {linkedin_box}
  </div>
  <div class="footer">
    Sources: AcademicTransfer · EURAXESS · KU Leuven · UGhent · UAntwerp · VUB ·
    Leiden · UvA · Utrecht · RUG · VU · Radboud · Maastricht ·
    VUB-CSDS · Antwerp POLS · Leiden ISGA ·
    Egmont · Clingendael · IISS · SWP · ECPR
  </div>
</div>
</body>
</html>"""


def send_digest(jobs: list[dict]) -> bool:
    """Send the weekly digest via Gmail SMTP. Returns True on success."""
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_SENDER or GMAIL_APP_PASSWORD not configured — email skipped.")
        return False

    today = date.today().strftime("%d %b %Y")
    n = len(jobs)
    subject = (
        f"PhD Digest {today} — {n} new listing{'s' if n != 1 else ''}"
        if n
        else f"PhD Digest {today} — no new listings"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECIPIENT
    msg.attach(MIMEText(build_html(jobs), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())
        logger.info("Digest sent to %s (%d jobs).", GMAIL_RECIPIENT, n)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)
        return False
