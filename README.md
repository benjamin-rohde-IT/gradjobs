# Graduate IT · Business Jobs — Denmark

A self-updating job board that collects **entry-level / graduate positions at the
intersection of IT and business** (AI consultant, business analyst, digital &
technology consulting) across Denmark — tailored for a CBS MSc in Business
Administration & Information Systems.

## What it does

Every morning at **06:00** (Europe/Copenhagen) a scheduled job runs the scraper,
filters for graduate/entry IT+business roles in Denmark, and regenerates the
website (`index.html`).

## Sources

| Source | Method | Companies / coverage |
|---|---|---|
| Jobindex.dk | RSS | Denmark's largest job board |
| IT-Jobbank.dk | RSS | IT-specific vertical |
| Akademikernes Jobbank (jobbank.dk) | RSS (graduate filter) | Graduate/trainee postings incl. Deloitte, PwC, KPMG |
| Workday API | JSON + location facet | Accenture, PwC |
| HR-Manager (Talentech) | JSON API | KPMG |
| SuccessFactors | HTML search | Nordea |
| WordPress listing | HTML | Valcon |
| LinkedIn | guest API (best-effort) | graduate/business-analyst/junior-consultant queries |

## Matching logic

A job is kept when it:
1. Is located in **Denmark** (or unknown location on a Danish board), and
2. Is **entry-level** — an explicit term (`graduate`, `junior`, `trainee`,
   `academy`, `nyuddannet`, …) *or* an `Analyst`/unqualified `Consultant` title at
   a consultancy (those are entry grades there), and
3. Has an **IT and/or business** signal (IT/business hybrid scores highest), and
4. Is **not senior** (`senior`, `manager`, `director`, `expert`, `architect`, …).

## Files

- `scraper.py` — collects and filters jobs → `data/jobs.json`
- `generate_site.py` — builds `index.html` from `data/jobs.json`
- `index.html` — the website (open in any browser)
- `data/jobs.json` — the raw collected data
- `data/scrape.log` — daily run log
- `run.sh` — manual full refresh (scrape + generate, prints summary)

## Run manually

```bash
cd ~/gradjobs && bash run.sh
```

## Schedule

Cron job `Graduate IT/Business jobs refresh` (id `ce6104f377bd`), `0 6 * * *`
Europe/Copenhagen, runs `~/AppData/Local/hermes/scripts/graduate_jobs.sh`.
Manage it with the Hermes cron tool (`/cron` or ask the agent).

## Adding a source

- **Workday company** (most consultancies): add a `(name, tenant, subdomain, site)`
  tuple to `WORKDAY` in `scraper.py`. The Denmark location is auto-discovered from
  the site's facets.
- **HR-Manager / Talentech company**: add `(name, customerId)` to `HR_MANAGER`.
- **SmartRecruiters / Teamtailor / other ATS**: add a scraper function following the
  existing patterns and wire it into `main()`.
