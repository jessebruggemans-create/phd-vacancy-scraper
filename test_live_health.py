"""Live health check: run all scrapers, apply the full filter chain, report per-source stats.
This is the equivalent of what main.py does but without sending email or touching the DB.
"""
import sys, os, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING, format='%(name)s -- %(message)s')

from scraper.filter import (
    detect_funding, is_eligible, is_english_or_dutch,
    is_relevant, is_social_science, is_wrong_department, keyword_score,
)
from scraper.sources import academic_transfer, euraxess
from scraper.sources import universities_be, universities_nl, universities_de, think_tanks

ALL_SCRAPERS = [
    academic_transfer.scrape,
    euraxess.scrape,
    universities_be.scrape,
    universities_nl.scrape,
    universities_de.scrape,
    think_tanks.scrape,
]

source_health = {}
active_jobs = []

for scrape_fn in ALL_SCRAPERS:
    module_name = scrape_fn.__module__.split('.')[-1]
    try:
        raw = scrape_fn()
    except Exception as exc:
        print(f"CRASH [{module_name}]: {exc}")
        source_health[f"[{module_name} CRASHED]"] = {'status':'error','raw':0,'accepted':0,'error':str(exc)}
        continue

    for job in raw:
        src = job.get('source', module_name)
        if src not in source_health:
            source_health[src] = {'status':'ok','raw':0,'accepted':0}
        source_health[src]['raw'] += 1

    _AGGREGATORS = {"AcademicTransfer", "EURAXESS"}

    for job in raw:
        title = job.get('title','')
        desc  = job.get('description','')
        inst  = job.get('institution','')
        src   = job.get('source', module_name)
        always = job.get('always_include', False)
        dept_proxy = desc if len(desc) <= 120 else ''
        is_agg = src in _AGGREGATORS

        if is_wrong_department(title, inst, dept_proxy): continue
        if not always and not is_agg and not is_social_science(title, inst, desc): continue
        if not is_english_or_dutch(title, desc): continue
        if not is_eligible(title): continue
        if not always and not is_relevant(title, desc, inst): continue

        source_health[src]['accepted'] += 1
        job['keyword_count'] = keyword_score(title, desc)
        job['funding'] = detect_funding(desc)
        active_jobs.append(job)

print(f"\n{'Source':<35} {'Raw':>5} {'Accepted':>9} {'Status'}")
print("-" * 60)
total_raw = total_acc = 0
problems = []
for src in sorted(source_health):
    h = source_health[src]
    raw = h.get('raw', 0)
    acc = h.get('accepted', 0)
    total_raw += raw
    total_acc += acc
    if h['status'] == 'error':
        status = f"ERROR: {h.get('error','')[:40]}"
        problems.append(src)
    elif raw == 0:
        status = "no listings found"
        # Only flag as problem if expected to have results
    else:
        status = "ok"
    print(f"{src:<35} {raw:>5} {acc:>9}   {status}")

print("-" * 60)
print(f"{'TOTAL':<35} {total_raw:>5} {total_acc:>9}")
print()

if problems:
    print(f"Problems ({len(problems)}): {', '.join(problems)}")
else:
    print("No errors detected.")

print()
print("=== Sample accepted jobs ===")
import random
sample = random.sample(active_jobs, min(10, len(active_jobs)))
for j in sorted(sample, key=lambda x: x.get('source','')):
    print(f"  [{j['source'][:20]:<20}] {j['title'][:60]}")
