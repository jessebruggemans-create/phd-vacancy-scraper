# PhD Vacancy Scraper

Automatically scrapes PhD vacancies in international relations, security studies,
and related fields from Belgian and Dutch institutions. Delivers a weekly HTML
digest to your inbox every Monday morning.

## Sources
| Category | Sources |
|---|---|
| Aggregators | AcademicTransfer · EURAXESS · jobs.ac.uk · ECPR |
| Belgian universities | KU Leuven · UGhent · UAntwerp · VUB |
| Dutch universities | Leiden · UvA · Utrecht · RUG · VU · Radboud · Maastricht |
| Departments | VUB-CSDS · Antwerp POLS · Leiden ISGA |
| Think tanks | Egmont · Clingendael · IISS · SWP |
| LinkedIn | Direct search link in every digest (not scraped) |

## One-time setup

### 1. Fork this repository on GitHub

### 2. Generate a Gmail App Password
> Required even if you already use 2FA.

1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable **2-Step Verification** if not already on
3. Go to **Security → App passwords**
4. Create a new app password (name it "PhD Scraper")
5. Copy the 16-character password

### 3. Add GitHub Secrets
Go to your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_SENDER` | your Gmail address |
| `GMAIL_RECIPIENT` | same Gmail address (or wherever you want the digest) |
| `GMAIL_APP_PASSWORD` | the 16-character password from step 2 |

### 4. Enable Actions
Go to the **Actions** tab in your repo and click **"I understand my workflows, go ahead and enable them"**.

### 5. Test it
Click **Actions → PhD Vacancy Scraper → Run workflow** to trigger a manual run.
Check your inbox — you should receive a digest within ~5 minutes.

## Running locally
```bash
git clone https://github.com/YOUR_USERNAME/phd-vacancy-scraper
cd phd-vacancy-scraper
pip install -r requirements.txt
cp .env.example .env   # fill in your Gmail credentials
python -m scraper.main
```

## Schedule
Runs every **Monday at 07:00 UTC** (08:00 CET / 09:00 CEST).
Only listings not seen in any previous run are included in the digest.
