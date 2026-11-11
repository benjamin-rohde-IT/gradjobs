#!/usr/bin/env python3
"""
Graduate & Entry-Level IT/Business Job Aggregator — Denmark
Collects graduate/junior positions mixing IT and business from:
  - Jobindex, IT-Jobbank, Akademikernes Jobbank (RSS)
  - Workday (Accenture, PwC)
  - HR-Manager / Talentech (KPMG)
  - SuccessFactors (Nordea)
  - WordPress (Valcon)
  - LinkedIn (best-effort guest API)
Filters to entry-level + IT/business hybrid roles in Denmark,
writes data/jobs.json (the website generator reads this).
"""
import requests, json, re, time, sys
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime, timezone
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
HEADERS = {**UA, "Accept-Language": "en-US,en;q=0.9,da;q=0.8"}

# ---------------------------------------------------------------- config
RSS_SOURCES = [
    ("Jobindex",      "https://www.jobindex.dk/jobsoegning?q={q}&format=rss"),
    ("IT-Jobbank",    "https://www.it-jobbank.dk/jobsoegning?q={q}&format=rss"),
    ("Akademikernes", "https://jobbank.dk/job/rss/?cvtype=6&key={q}"),
]

QUERIES = [
    "graduate business analyst", "graduate AI consultant",
    "graduate IT consultant", "graduate management consultant",
    "junior business analyst", "junior consultant data",
    "business intelligence graduate", "data analyst graduate",
    "digital consultant graduate", "technology consultant graduate",
    "graduate data", "graduate digital", "nyuddannet konsulent",
    "forretningsanalytiker", "graduate programme", "AI consultant junior",
    "business analyst", "junior consultant",
]

WORKDAY = [
    ("Accenture", "accenture", "wd103", "AccentureCareers"),
    ("PwC",       "pwc",       "wd3",   "Global_Experienced_Careers"),
]

HR_MANAGER = [
    ("KPMG", "kpmg"),
]

SUCCESSFACTORS = [
    ("Nordea", "https://careers.nordea.com/search/?q={q}"),
]

WORDPRESS = [
    ("Valcon", "https://www.valcon.com/careers/"),
]

# ------------------------------------------------------------- keywords
ENTRY_TERMS = [
    "graduate", "junior", "trainee", "nyuddannet", "nyuddannede",
    "early career", "early-career", "entry level", "entry-level",
    "talent programme", "talent program", "academy", "graduate program",
    "graduate programme", "young professional", "candidate programme",
    "postgraduate", "start din karriere", "start your career",
]

STUDENT_TERMS = [
    "studiejob", "studentermedhj", "student assistant", "student analyst",
    "praktikant", "intern", "internship", "deltid", "part-time", "part time",
    "student", "elev",
]

IT_TERMS = [
    " it ", " it-", "digital", "data", " ai ", "ai-", "artificial intelligence",
    "machine learning", "technology", "tech", "software", "systems",
    "information systems", "analytics", "automation", "cloud", "cyber",
    "sap", "erp", "crm", "business intelligence", "forretnings", "data science",
    "big data", "genai", "gen-ai", "robotics", "rpa", "newtech", "digitalisering",
]

BUSINESS_TERMS = [
    "business", "consultant", "consulting", "analyst", "strategy", "strategic",
    "management", "advisory", "transformation", "commercial", "finance",
    "operations", "customer", "insight", "modelling", "modelling", "konsulent",
    "forretnings", "økonomi", "strategy analyst", "management consulting",
]

NAMED_COMPANIES = [
    "deloitte", "pwc", "pricewaterhouse", "valcon", "nordea", "kpmg",
    "accenture", " ey", "ernst", "capgemini", "bearingpoint", "netcompany",
    "implement", "mckinsey", "bcg", "bain", "boston consulting", "pa consulting",
    "visma", "nnit", "kmd", "systematic", "columbus", "trifork", "cognizant",
]

# consulting houses where "Analyst" / unqualified "Consultant" are entry grades
CONSULTANCIES = [
    "deloitte", "pwc", "pricewaterhouse", "kpmg", "accenture", " ey", "ernst",
    "capgemini", "bearingpoint", "netcompany", "implement", "mckinsey", "bcg",
    "bain", "boston consulting", "pa consulting", "valcon", "visma", "nnit",
    "cognizant", "trifork",
]

DK_LOCATIONS = [
    "denmark", "danmark", "copenhagen", "københavn", "kobenhavn", "aarhus",
    "århus", "arhus", "aalborg", "ålborg", "alborg", "odense", "hellerup",
    "lyngby", "gentofte", "hørsholm", "hoersholm", "frederiksberg", "ballerup",
    "søborg", "soeborg", "kolding", "vejle", "roskilde", "esbjerg", "hvidovre",
    "storkøbenhavn", "østjylland", "sydjylland", "vestjylland", "nordsjælland",
    "sydsjælland", "øresundsregionen", "fyn", "dk",
]

FOREIGN_LOCATIONS = [
    "udlandet", "abroad", "international", "sverige", "norge", "nederland",
    "belgien", "tyskland", "germany", "poland", "polen", "finland", "spain",
    "spanien", "italy", "italien", "france", "frankrig", "united kingdom",
    "london", "stockholm", "oslo", "berlin", "brussels", "qld", "beijing",
    "brisbane", "schweiz", "switzerland", "austria", "østrig", "netherlands",
]

# foreign markers likely to appear in a title (used when location field is empty)
FOREIGN_TITLE_MARKERS = [
    "portugal", " oslo", "finland", "sweden", "sverige", "norway", "norge",
    "india", "poland", "polen", "helsinki", "stockholm", "germany", "tyskland",
    "netherlands", "nederland", "uk ", "london", "brussels", "france", "spain",
    "italy", "dubai", "singapore", "hong kong", "warsaw", "riga", "vilnius",
    "tallinn", "gdańsk", "gdansk", "budapest",
]

SENIOR_RE = re.compile(
    r'\b(senior|manager|managers|director|directors|partner|partners|head of|'
    r'lead|principal|chief|vp\b|vice\s*president|experienced|erfaren|'
    r'ekspert|expert|architect|specialist|chef|leder|afdelingsleder)\b', re.I)

def has_any(text, terms):
    t = f" {text.lower()} "
    return any(term.lower() in t for term in terms)

def named_company(company):
    c = f" {company.lower()} "
    return any(n in c for n in NAMED_COMPANIES)

def is_consultancy(company):
    c = f" {company.lower()} "
    return any(n in c for n in CONSULTANCIES)

def is_senior(title):
    return bool(SENIOR_RE.search(title or ""))

def is_student(title, desc):
    return has_any(title, STUDENT_TERMS) or has_any(desc[:200], STUDENT_TERMS)

def is_explicit_entry(title, desc):
    return has_any(title, ENTRY_TERMS) or has_any(desc[:300], ENTRY_TERMS)

def entry_signal(title, desc, company):
    if is_explicit_entry(title, desc):
        return True
    # at consulting firms, "Analyst" and unqualified "Consultant" are entry grades
    if is_consultancy(company) and not is_senior(title):
        tl = title.lower()
        if re.search(r'\banalyst\b', tl) or re.search(r'\bconsultant\b', tl):
            return True
    return False

def it_signal(title, desc):
    return has_any(title, IT_TERMS) or has_any(desc[:200], IT_TERMS)

def business_signal(title):
    return has_any(title, BUSINESS_TERMS)

def is_denmark(location):
    if not location:
        return True  # Danish board, assume DK
    loc = location.lower()
    has_dk = has_any(loc, DK_LOCATIONS)
    has_foreign = has_any(loc, FOREIGN_LOCATIONS)
    if has_foreign and not has_dk:
        return False
    return True

def match_score(title, desc, company, location):
    if not is_denmark(location):
        return 0
    # reject roles clearly located abroad (when location field is empty)
    if not location and has_any(title, FOREIGN_TITLE_MARKERS):
        return 0
    if is_senior(title):
        return 0
    if not entry_signal(title, desc, company):
        return 0
    it = it_signal(title, desc)
    biz = business_signal(title)
    named = named_company(company)
    # MUST be in the IT and/or business field (or a named consultancy house) —
    # entry-level alone is not enough (a "junior electrical engineer" or
    # "trainee pædagog" is entry-level but off-topic).
    if not (it or biz or named):
        return 0
    score = 0
    if it and biz:
        score += 3
    elif it:
        score += 2
    elif biz:
        score += 1
    if named:
        score += 2
    return score

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

# ------------------------------------------------------------- helpers
def fetch(url, **kw):
    for attempt in range(3):
        try:
            return requests.get(url, headers=HEADERS, timeout=25, **kw)
        except Exception as e:
            if attempt == 2:
                print(f"   !! fetch failed {url}: {e}", file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None

def fetch_post(url, **kw):
    for attempt in range(3):
        try:
            return requests.post(url, headers=HEADERS, timeout=25, **kw)
        except Exception as e:
            if attempt == 2:
                print(f"   !! post failed {url}: {e}", file=sys.stderr)
            time.sleep(1.5 * (attempt + 1))
    return None

def parse_date(s):
    if not s:
        return ""
    s = s.strip()
    m = re.match(r"/Date\((\d+)", s)
    if m:
        try:
            return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date().isoformat()
        except Exception:
            pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s[:10] if len(s) >= 10 else s

# ------------------------------------------------------------- RSS
def scrape_rss(name, url_tpl):
    jobs = []
    for q in QUERIES:
        url = url_tpl.format(q=quote(q))
        r = fetch(url)
        if not r or r.status_code != 200:
            continue
        try:
            text = r.content.decode(r.encoding or "iso-8859-1", errors="replace")
            root = ET.fromstring(text)
        except Exception:
            continue
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            desc = (it.findtext("description") or "").strip()
            pub = it.findtext("pubDate") or it.findtext("published") or ""
            company = ""
            m = re.search(r",\s*([^,]+(?:A/S|ApS|Aps|Group|Consulting|Bank|Deloitte|PwC|KPMG|EY|Accenture|Nordea|Valcon|Netcompany|Visma)[^,]*)$", title)
            if m:
                company = m.group(1).strip()
            location = ""
            if name == "Akademikernes":
                mm = re.search(r"hos\s+([^,]+),\s*([^(]+)", desc)
                if mm:
                    company = company or mm.group(1).strip()
                    location = mm.group(2).strip()
            sc = match_score(title, desc, company, location)
            if sc > 0:
                jtype = "Student" if is_student(title, desc) else "Graduate"
                jobs.append({
                    "title": title, "company": company or name, "location": location,
                    "url": link, "date": parse_date(pub), "source": name,
                    "type": jtype, "score": sc, "desc": desc[:300],
                })
        time.sleep(0.1)
    return jobs

# ------------------------------------------------------------- Workday
DK_FACET_TERMS = [
    "denmark", "danmark", "copenhagen", "københavn", "kobenhavn", "aarhus",
    "århus", "arhus", "aalborg", "ålborg", "alborg", "odense", "hellerup",
    "lyngby", "gentofte", "hørsholm", "hoersholm", "frederiksberg", "ballerup",
    "søborg", "soeborg", "kolding", "vejle", "roskilde", "esbjerg", "hvidovre",
    "holte", "birkerød", "birkerod", "taastrup", "tåstrup", "glostrup", "herlev",
    "rødovre", "rodovre", "hillerød", "hillerod", "horsens", "silkeborg",
    "randers", "herning", "viborg", "svendborg", "næstved", "naestved",
    "holbæk", "holbaek", "køge", "koge",
]

def find_dk_facets(facets, parent_param=None, out=None):
    """Recursively collect facet ids for Danish locations, returning {facetParam: [ids]}."""
    if out is None:
        out = {}
    if isinstance(facets, dict):
        dsc = (facets.get("descriptor") or "").lower()
        if facets.get("id") and any(t in dsc for t in DK_FACET_TERMS):
            fp = parent_param or facets.get("facetParameter")
            if fp:
                out.setdefault(fp, []).append(facets["id"])
        fp = facets.get("facetParameter") or parent_param
        find_dk_facets(facets.get("values", []), fp, out)
    elif isinstance(facets, list):
        for v in facets:
            find_dk_facets(v, parent_param, out)
    return out

def scrape_workday(name, tenant, sub, site):
    jobs = []
    base = f"https://{tenant}.{sub}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    # 1) discover the Denmark location facet ids
    r = fetch_post(base, json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""})
    if not r or r.status_code != 200:
        print(f"  [{name}] workday HTTP {getattr(r,'status_code','?')}", file=sys.stderr)
        return jobs
    d = r.json()
    dk_facets = find_dk_facets(d.get("facets", []))
    if not dk_facets:
        print(f"  [{name}] workday: no Denmark facet found", file=sys.stderr)
        return jobs
    # prefer a country-level facet, else the city facet
    fp = "locationCountry" if "locationCountry" in dk_facets else next(iter(dk_facets))
    dk_ids = dk_facets[fp]
    # 2) fetch only Denmark jobs
    limit, offset, total = 20, 0, None
    while True:
        body = {"appliedFacets": {fp: dk_ids}, "limit": limit, "offset": offset, "searchText": ""}
        rr = fetch_post(base, json=body)
        if not rr or rr.status_code != 200:
            break
        dd = rr.json()
        if total is None:
            total = dd.get("total", 0)
            print(f"  [{name}] workday Denmark={total}")
        postings = dd.get("jobPostings", [])
        if not postings:
            break
        for p in postings:
            title = p.get("title", "")
            path = p.get("externalPath", "")
            url = f"https://{tenant}.{sub}.myworkdayjobs.com/{site}{path}" if path else ""
            posted = p.get("postedOn", "")
            locs = " ".join(b for b in (p.get("bulletFields") or []) if isinstance(b, str))
            sc = match_score(title, "", name, locs)
            if sc > 0:
                jtype = "Student" if is_student(title, "") else "Graduate"
                jobs.append({
                    "title": title, "company": name, "location": "Denmark",
                    "url": url, "date": parse_date(posted), "source": f"{name} (Workday)",
                    "type": jtype, "score": sc, "desc": "",
                })
        offset += limit
        if offset >= total:
            break
        time.sleep(0.1)
    return jobs

# ------------------------------------------------------------- HR-Manager (KPMG)
def scrape_hrmanager(name, customer):
    jobs = []
    url = f"https://api.hr-manager.net/JobPortal.svc/{customer}/PositionList/json/?incads=true"
    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  [{name}] hr-manager HTTP {getattr(r,'status_code','?')}", file=sys.stderr)
        return jobs
    try:
        d = r.json()
    except Exception as e:
        print(f"  [{name}] hr-manager json error {e}", file=sys.stderr)
        return jobs
    for it in d.get("Items", []):
        title = it.get("Name") or ""
        loc = it.get("PositionLocation") or {}
        location = loc.get("Name", "") if isinstance(loc, dict) else str(loc)
        published = it.get("Published") or ""
        url = it.get("AdvertisementUrl") or ""
        short = it.get("ShortDescription") or ""
        content = ""
        for ad in (it.get("Advertisements") or []):
            content += re.sub(r"<[^>]+>", " ", ad.get("Content", "") or "")
        desc = (short + " " + content).strip()
        sc = match_score(title, desc, name, location)
        if sc > 0:
            jtype = "Student" if is_student(title, desc) else "Graduate"
            jobs.append({
                "title": title, "company": name, "location": location,
                "url": url, "date": parse_date(published), "source": f"{name}",
                "type": jtype, "score": sc, "desc": desc[:300],
            })
    return jobs

# ------------------------------------------------------------- SuccessFactors (Nordea)
def scrape_successfactors(name, url_tpl):
    jobs = []
    for q in ["graduate", "junior", "analyst", "business analyst", "trainee", "student", "consultant"]:
        url = url_tpl.format(q=quote(q))
        r = fetch(url)
        if not r or r.status_code != 200:
            continue
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"(/job/|jobId|job\?|/careers/)", href, re.I):
                continue
            title = a.get_text(strip=True)
            if len(title) < 4 or len(title) > 120:
                continue
            sc = match_score(title, "", name, "")
            if sc > 0:
                link = href if href.startswith("http") else "https://careers.nordea.com" + href
                jobs.append({
                    "title": title, "company": name, "location": "",
                    "url": link, "date": "", "source": f"{name}",
                    "type": "Graduate", "score": sc, "desc": "",
                })
        time.sleep(0.4)
    return jobs

# ------------------------------------------------------------- WordPress (Valcon)
def scrape_wordpress(name, url):
    jobs = []
    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  [{name}] wp HTTP {getattr(r,'status_code','?')}", file=sys.stderr)
        return jobs
    soup = BeautifulSoup(r.content, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/careers/" not in href or href.rstrip("/").endswith("/careers"):
            continue
        title = a.get_text(strip=True)
        if len(title) < 6 or len(title) > 120:
            continue
        sc = match_score(title, "", name, "Copenhagen")
        if sc > 0:
            jobs.append({
                "title": title, "company": name, "location": "Copenhagen",
                "url": href, "date": "", "source": f"{name}",
                "type": "Graduate", "score": sc, "desc": "",
            })
    return jobs

# ------------------------------------------------------------- LinkedIn (best-effort)
def scrape_linkedin():
    jobs = []
    urls = [
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=graduate%20consultant&location=Denmark&start=0",
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=business%20analyst&location=Denmark&start=0",
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=junior%20consultant&location=Denmark&start=0",
    ]
    for url in urls:
        r = fetch(url)
        if not r or r.status_code != 200:
            continue
        soup = BeautifulSoup(r.content, "html.parser")
        for card in soup.find_all("div", class_=re.compile("base-card")):
            a = card.find("a", class_=re.compile("base-card__full-link"))
            title_el = card.find("span", class_=re.compile("sr-only")) or card.find("h3")
            comp_el = card.find("a", class_=re.compile("hidden-nested-link"))
            loc_el = card.find("span", class_=re.compile("job-search-card__location"))
            title = title_el.get_text(strip=True) if title_el else ""
            company = comp_el.get_text(strip=True) if comp_el else ""
            location = loc_el.get_text(strip=True) if loc_el else ""
            link = a.get("href", "") if a else ""
            sc = match_score(title, "", company, location)
            if sc > 0:
                jtype = "Student" if is_student(title, "") else "Graduate"
                jobs.append({
                    "title": title, "company": company, "location": location,
                    "url": link, "date": "", "source": "LinkedIn",
                    "type": jtype, "score": sc, "desc": "",
                })
        time.sleep(0.5)
    return jobs

# ------------------------------------------------------------- main
COMPANY_SUFFIXES = {"a", "s", "aps", "ap", "ab", "as", "denmark", "danmark", "group",
                    "consulting", "revision", "skat", "international", "holding",
                    "inc", "llc", "ltd", "plc", "oy"}

def canonical_key(j):
    title = j.get("title", "")
    company = j.get("company", "")
    clow = company.lower().strip()
    # strip a trailing ", Company" suffix from RSS-style titles
    if clow and title.lower().endswith("," + clow):
        title = title[:-(len(company) + 1)]
    tw = [w for w in norm(title).split() if w not in COMPANY_SUFFIXES]
    cw = [w for w in norm(company).split() if w not in COMPANY_SUFFIXES]
    return "|".join([" ".join(cw), " ".join(tw)])

def dedupe(jobs):
    seen = {}
    for j in jobs:
        key = canonical_key(j)
        if key in seen and j["score"] <= seen[key]["score"]:
            continue
        seen[key] = j
    return list(seen.values())

def main():
    all_jobs = []
    print("RSS sources...")
    for name, tpl in RSS_SOURCES:
        j = scrape_rss(name, tpl)
        print(f"  {name}: {len(j)}")
        all_jobs.extend(j)

    print("Workday...")
    for name, tenant, sub, site in WORKDAY:
        all_jobs.extend(scrape_workday(name, tenant, sub, site))

    print("HR-Manager...")
    for name, cust in HR_MANAGER:
        all_jobs.extend(scrape_hrmanager(name, cust))

    print("SuccessFactors...")
    for name, tpl in SUCCESSFACTORS:
        all_jobs.extend(scrape_successfactors(name, tpl))

    print("WordPress...")
    for name, url in WORDPRESS:
        all_jobs.extend(scrape_wordpress(name, url))

    print("LinkedIn...")
    all_jobs.extend(scrape_linkedin())

    jobs = dedupe(all_jobs)
    jobs.sort(key=lambda x: (x.get("date") or "", x["score"]), reverse=True)

    import os
    os.makedirs("data", exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(jobs),
        "jobs": jobs,
    }
    with open("data/jobs.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"\nDONE: {len(jobs)} unique relevant jobs -> data/jobs.json")
    from collections import Counter
    for src, n in Counter(j["source"] for j in jobs).most_common():
        print(f"   {src}: {n}")

if __name__ == "__main__":
    main()
