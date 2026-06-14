"""Unit tests for filter.py and digest.py logic."""
import sys
sys.path.insert(0, '.')

from scraper.filter import (
    is_wrong_department, is_social_science, is_eligible,
    is_english_or_dutch, detect_funding, keyword_score,
)
from scraper.digest import build_html, _is_closing_soon, _parse_deadline
from datetime import date

PASS = FAIL = 0

def check(label, result, expected):
    global PASS, FAIL
    ok = result == expected
    mark = 'OK' if ok else 'FAIL'
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{mark}] {label}")
    if not ok:
        print(f"         got={result!r}, expected={expected!r}")

print("=== Department exclusion filter ===")
check("PhD Chemistry → excluded",       is_wrong_department("PhD in Chemistry"), True)
check("PhD Engineering → excluded",     is_wrong_department("PhD in Engineering"), True)
check("PhD Medical Science → excluded", is_wrong_department("PhD Medical Science"), True)
check("PhD in Law → excluded",          is_wrong_department("PhD in Law"), True)
check("PhD Economics → excluded",       is_wrong_department("PhD in Economics"), True)
check("PhD Computer Science → excluded",is_wrong_department("PhD Computer Science"), True)
check("PhD Security Studies → kept",    is_wrong_department("PhD Security Studies"), False)
check("PhD in IR → kept",               is_wrong_department("PhD in International Relations"), False)
check("Policy Analyst → kept",          is_wrong_department("Policy Analyst Security"), False)
check("Military Consultant → kept",     is_wrong_department("Military Consultant Operations"), False)

print()
print("=== Social sciences inclusion filter ===")
check("Political science → yes",        is_social_science("PhD Political Science"), True)
check("International Relations → yes",  is_social_science("PhD International Relations"), True)
check("Security studies → yes",         is_social_science("Security Policy Researcher"), True)
check("Military → yes",                 is_social_science("Military Consultant Operations"), True)
check("History → yes",                  is_social_science("PhD in History"), True)
check("Random PhD → no",               is_social_science("PhD Candidate"), False)
check("Research Assistant → no",       is_social_science("Research Assistant"), False)
check("Machine learning → no",          is_social_science("Machine Learning Researcher"), False)

print()
print("=== Funding detection ===")
check("NWO → funded",          detect_funding("Supported by NWO grant."), "funded")
check("Stipend → funded",      detect_funding("Monthly stipend of €2,400."), "funded")
check("Salary → funded",       detect_funding("Competitive salary provided."), "funded")
check("FWO → funded",          detect_funding("FWO doctoral scholarship."), "funded")
check("Fully funded → funded", detect_funding("This is a fully funded position."), "funded")
check("Self-funded → self",    detect_funding("Candidates must be self-funded."), "self-funded")
check("Own funding → self",    detect_funding("Applicants must have their own funding."), "self-funded")
check("Unclear → unclear",     detect_funding("We are looking for a motivated PhD."), "unclear")
check("Empty → unclear",       detect_funding(""), "unclear")

print()
print("=== Language filter ===")
check("English → ok",          is_english_or_dutch("PhD Security Studies", ""), True)
check("Dutch → ok",            is_english_or_dutch("Promovendus Internationale Betrekkingen", ""), True)
check("German umlaut → no",    is_english_or_dutch("Wissenschaftliche Mitarbeiter/in", ""), False)
check("French accent+word → no", is_english_or_dutch("Chargé de recherche", "politiques"), False)
check("English with names → ok", is_english_or_dutch("PhD on EU Defence Policy", "IRIS"), True)

print()
print("=== Eligibility filter ===")
check("PhD position → eligible",     is_eligible("PhD Candidate Security Studies"), True)
check("Junior researcher → eligible",is_eligible("Junior Researcher Policy"), True)
check("Professor → ineligible",      is_eligible("Assistant Professor"), False)
check("Postdoc → ineligible",        is_eligible("Postdoctoral Researcher"), False)
check("Research fellow → ineligible",is_eligible("Research Fellow"), False)
check("Lecturer → ineligible",       is_eligible("Lecturer in IR"), False)

print()
print("=== Closing soon logic ===")
today = date.today()
from datetime import timedelta
check("Today → closing soon",        _is_closing_soon(today.isoformat(), today), True)
check("+7 days → closing soon",      _is_closing_soon((today+timedelta(7)).isoformat(), today), True)
check("+14 days → closing soon",     _is_closing_soon((today+timedelta(14)).isoformat(), today), True)
check("+15 days → not soon",         _is_closing_soon((today+timedelta(15)).isoformat(), today), False)
check("Empty → not soon",            _is_closing_soon("", today), False)

print()
print("=== build_html smoke test ===")
jobs = [
    {'id':'1','title':'PhD Security Studies','institution':'HCSS',
     'location':'The Hague, NL','deadline':today.isoformat(),
     'url':'https://hcss.nl/1','source':'HCSS',
     'description':'Fully funded NWO PhD position on cybersecurity.',
     'is_new':True,'keyword_count':5,'funding':'funded','always_include':True},
    {'id':'2','title':'Doctoral Researcher International Relations',
     'institution':'Utrecht University','location':'Utrecht, NL',
     'deadline':(today+timedelta(60)).isoformat(),
     'url':'https://uu.nl/2','source':'Utrecht University',
     'description':'','is_new':False,'keyword_count':3,'funding':'unclear'},
    {'id':'3','title':'PhD Conflict Studies','institution':'UGent',
     'location':'Ghent, BE','deadline':'',
     'url':'https://ugent.be/3','source':'UGent',
     'description':'Applicants must be self-funded.','is_new':True,
     'keyword_count':2,'funding':'self-funded'},
]
health = {
    'HCSS':   {'status':'ok',    'raw':3,  'accepted':2},
    'Utrecht University': {'status':'ok','raw':12,'accepted':4},
    'VUB':    {'status':'error', 'raw':0,  'accepted':0, 'error':'Connection timeout'},
    'EURAXESS':{'status':'ok',   'raw':42,'accepted':10},
}
html = build_html(jobs, health)

needles = {
    'summary line':         'new vacanc',
    'Netherlands section':  'Netherlands',
    'Belgium section':      'Belgium',
    'closing soon badge':   'Closing soon',
    'funded badge':         '&#10003; Funded',
    'self-funded badge':    '&#9888; Self-funded',
    'match badge':          'Match:',
    'health section':       'Scraper health this week',
    'health error shown':   'Connection timeout',
    'NATO portal link':     'NATO',
    'check manually header':'Check manually this week',
    'deadline text':        'Deadline:',
}
for label, needle in needles.items():
    check(f"HTML contains {label}", needle in html, True)

print()
print(f"=== Results: {PASS} passed, {FAIL} failed ===")
if FAIL:
    sys.exit(1)
