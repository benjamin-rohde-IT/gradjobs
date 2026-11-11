#!/usr/bin/env python3
"""Generate the static website (index.html) from data/jobs.json."""
import json, os
from datetime import datetime, timezone
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "jobs.json")
OUT = os.path.join(HERE, "index.html")

with open(DATA, encoding="utf-8") as f:
    payload = json.load(f)

jobs = payload["jobs"]
generated = payload.get("generated", "")

# pretty "last updated" in Europe/Copenhagen-ish (approx: UTC+1)
def pretty_generated(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso

updated = pretty_generated(generated)
n_jobs = len(jobs)
companies = sorted({j["company"] for j in jobs})
sources = sorted({j["source"] for j in jobs})

# stats
src_counts = Counter(j["source"] for j in jobs)
type_counts = Counter(j["type"] for j in jobs)

# build filter options
company_opts = "".join(f'<option value="{c}">{c}</option>' for c in companies)
source_opts = "".join(f'<option value="{s}">{s}</option>' for s in sources)

# source summary chips
src_chips = "".join(
    f'<span class="chip">{s} · {n}</span>' for s, n in src_counts.most_common()
)

# escape a string for safe HTML embedding
def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# embed jobs as JSON for client-side filtering (escape </ to avoid script break)
jobs_json = json.dumps(jobs, ensure_ascii=False).replace("</", "<\\/")

# human-friendly date label
def fmt_date(d):
    if not d:
        return ""
    try:
        dt = datetime.fromisoformat(d)
        return dt.strftime("%d %b %Y")
    except Exception:
        return d

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Graduate IT · Business Jobs — Denmark</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --panel2: #1c2430; --border: #2b3440;
    --text: #e6edf3; --muted: #8b949e; --accent: #3b82f6; --accent2: #22c55e;
    --gold: #f59e0b; --purple: #a78bfa;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 32px 20px 80px; }
  header { margin-bottom: 24px; }
  h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: -0.02em; }
  h1 .grad { color: var(--accent); }
  .sub { color: var(--muted); font-size: 14px; margin: 0 0 16px; }
  .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
  .chip {
    background: var(--panel); border: 1px solid var(--border); color: var(--muted);
    border-radius: 999px; padding: 3px 12px; font-size: 12px;
  }
  .chip b { color: var(--text); font-weight: 600; }
  .filters {
    display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 24px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px;
  }
  .filters input, .filters select {
    background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    border-radius: 8px; padding: 9px 12px; font-size: 14px; outline: none;
  }
  .filters input { flex: 1; min-width: 180px; }
  .filters input:focus, .filters select:focus { border-color: var(--accent); }
  .type-toggle { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .type-toggle button {
    background: var(--panel2); border: none; color: var(--muted); padding: 9px 16px;
    font-size: 14px; cursor: pointer;
  }
  .type-toggle button.active { background: var(--accent); color: #fff; }
  .count { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
  .grid { display: flex; flex-direction: column; gap: 12px; }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 20px; text-decoration: none; color: var(--text); display: block;
    transition: border-color .15s, transform .05s;
  }
  .card:hover { border-color: var(--accent); }
  .card .row { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .card h2 { font-size: 16px; margin: 0; font-weight: 600; line-height: 1.35; }
  .card .company { color: var(--accent); font-weight: 600; font-size: 13px; margin-top: 3px; }
  .card .badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; align-items: center; }
  .badge { font-size: 11px; padding: 2px 9px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); }
  .badge.grad { color: var(--accent2); border-color: rgba(34,197,94,.4); }
  .badge.student { color: var(--gold); border-color: rgba(245,158,11,.4); }
  .badge.src { color: var(--purple); border-color: rgba(167,139,250,.35); }
  .card .desc { color: var(--muted); font-size: 13px; margin-top: 8px; }
  .empty { color: var(--muted); text-align: center; padding: 40px; }
  footer { color: var(--muted); font-size: 12px; text-align: center; margin-top: 40px; }
  a.card:focus-visible { outline: 2px solid var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Graduate <span class="grad">IT · Business</span> Jobs — Denmark</h1>
    <p class="sub">Entry-level &amp; graduate positions at the intersection of IT and business — AI consultant, business analyst, digital &amp; technology consulting. For a CBS MSc in Business Administration &amp; Information Systems.</p>
    <div class="meta">
      <span class="chip"><b>__N_JOBS__</b> positions</span>
      <span class="chip">Updated <b>__UPDATED__</b></span>
      <span class="chip"><b>__N_COMPANIES__</b> companies</span>
      <span class="chip"><b>__N_SOURCES__</b> sources</span>
    </div>
    <div class="meta">__SRC_CHIPS__</div>
  </header>

  <div class="filters">
    <input id="q" type="text" placeholder="Search title, company, keyword…">
    <div class="type-toggle" id="typeToggle">
      <button data-t="all" class="active">All</button>
      <button data-t="Graduate">Graduate</button>
      <button data-t="Student">Student</button>
    </div>
    <select id="company"><option value="">All companies</option>__COMPANY_OPTS__</select>
    <select id="source"><option value="">All sources</option>__SOURCE_OPTS__</select>
  </div>

  <div class="count" id="count"></div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">No matching positions. Try clearing filters.</div>

  <footer>Auto-refreshed daily at 06:00 · Sources: Jobindex, IT-Jobbank, Akademikernes Jobbank, Accenture &amp; PwC (Workday), KPMG, Nordea, Valcon, LinkedIn.</footer>
</div>

<script>
const JOBS = __JOBS__;
let activeType = "all";
let q = "", company = "", source = "";

function card(j) {
  const t = j.type === "Student" ? "student" : "grad";
  const loc = j.location ? ` · ${esc(j.location)}` : "";
  const date = j.date ? esc(j.date) : "";
  const desc = j.desc ? `<div class="desc">${esc(j.desc).slice(0,220)}</div>` : "";
  return `<a class="card" href="${esc(j.url)}" target="_blank" rel="noopener">
    <div class="row">
      <div>
        <h2>${esc(j.title)}</h2>
        <div class="company">${esc(j.company)}${loc}</div>
      </div>
      <div style="color:var(--muted);font-size:12px">${date}</div>
    </div>
    <div class="badges">
      <span class="badge ${t}">${esc(j.type)}</span>
      <span class="badge src">${esc(j.source)}</span>
    </div>
    ${desc}
  </a>`;
}

function render() {
  const ql = q.toLowerCase();
  const list = JOBS.filter(j => {
    if (activeType !== "all" && j.type !== activeType) return false;
    if (company && j.company !== company) return false;
    if (source && j.source !== source) return false;
    if (ql) {
      const hay = (j.title + " " + j.company + " " + j.desc).toLowerCase();
      if (!hay.includes(ql)) return false;
    }
    return true;
  });
  document.getElementById("count").textContent = `Showing ${list.length} of ${JOBS.length} positions`;
  document.getElementById("grid").innerHTML = list.map(card).join("");
  document.getElementById("empty").style.display = list.length ? "none" : "block";
}

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

document.getElementById("q").addEventListener("input", e => { q = e.target.value; render(); });
document.getElementById("company").addEventListener("change", e => { company = e.target.value; render(); });
document.getElementById("source").addEventListener("change", e => { source = e.target.value; render(); });
document.querySelectorAll("#typeToggle button").forEach(b => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#typeToggle button").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    activeType = b.dataset.t;
    render();
  });
});

render();
</script>
</body>
</html>
"""

# substitute placeholders
for token, val in [
    ("__N_JOBS__", str(n_jobs)),
    ("__UPDATED__", esc(updated)),
    ("__N_COMPANIES__", str(len(companies))),
    ("__N_SOURCES__", str(len(sources))),
    ("__SRC_CHIPS__", src_chips),
    ("__COMPANY_OPTS__", company_opts),
    ("__SOURCE_OPTS__", source_opts),
    ("__JOBS__", jobs_json),
]:
    HTML = HTML.replace(token, val)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"Wrote {OUT} ({len(HTML)} bytes, {n_jobs} jobs)")
