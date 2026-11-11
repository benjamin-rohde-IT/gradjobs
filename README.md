# Graduate IT · Business Jobs — Denmark

A self-updating job board that collects **entry-level / graduate positions at the
intersection of IT and business** (AI consultant, business analyst, digital &
technology consulting) across Denmark — tailored for a CBS MSc in Business
Administration & Information Systems.

## Live site

**https://benjamin-rohde-it.github.io/gradjobs/** — auto-deployed to GitHub Pages
by GitHub Actions.

## What it does

Every morning at **06:00** (Europe/Copenhagen) a GitHub Actions workflow runs the
scraper, filters for graduate/entry IT+business roles in Denmark, regenerates the
website (`index.html`), commits the fresh data back to `main`, and deploys to
GitHub Pages.

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
- `data/jobs.json` — the raw collected data (committed so the site has content)
- `data/scrape.log` — rolling run log
- `run.sh` — manual full refresh (scrape + generate, prints summary)
- `requirements.txt` — `requests`, `beautifulsoup4`
- `.github/workflows/refresh.yml` — CI: scrape → generate → commit → deploy Pages

## Run manually

```bash
pip install -r requirements.txt
cd ~/gradjobs && bash run.sh
```

## Deployment & schedule

Hosted on GitHub Pages from the **GitHub Actions** build type (repo is public).
Workflow: `.github/workflows/refresh.yml`.

- **Schedule**: runs daily at **06:00 Europe/Copenhagen**. GitHub's cron is UTC,
  so the workflow triggers at `04:00` *and* `05:00` UTC and a local-hour guard
  lets exactly one through — this keeps 06:00 correct across both CET and CEST
  (no manual daylight-saving edits).
- **Also runs** on every push to `main` and via manual `workflow_dispatch`
  (Actions tab → *Run workflow*).
- The workflow commits refreshed `data/jobs.json` + `index.html` back to `main`
  as `github-actions[bot]` with `[skip ci]` (pushes made with `GITHUB_TOKEN`
  don't re-trigger workflows, so there is no loop).
- A failed/dead scrape source is non-fatal — the deploy still ships the site.
- Pages URL: https://benjamin-rohde-it.github.io/gradjobs/

## Adding a source

- **Workday company** (most consultancies): add a `(name, tenant, subdomain, site)`
  tuple to `WORKDAY` in `scraper.py`. The Denmark location is auto-discovered from
  the site's facets.
- **HR-Manager / Talentech company**: add `(name, customerId)` to `HR_MANAGER`.
- **SmartRecruiters / Teamtailor / other ATS**: add a scraper function following the
  existing patterns and wire it into `main()`.
