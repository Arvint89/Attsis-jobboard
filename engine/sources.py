"""
sources.py -- board-SOURCE fetchers (aggregators), the second coverage tier.

WHY THIS EXISTS (JB-3)
----------------------
ats.py is company-centric: one registry line -> one ATS -> that company's jobs.
It only reaches companies on an auto-probeable ATS. Most of BT's *fit* companies
(small medical/embedded shops) are NOT on those platforms, so the board looked empty.

A board SOURCE is different: a regional aggregator that already collects many
companies' postings regardless of ATS. One call -> many companies. Still fully
deterministic, near-zero token (no LLM).

Two source types (see docs/design/DESIGN_board_sources.md):
  - getro : the JSON API behind most Canadian innovation-hub boards
            (MaRS 383, Communitech 8936, + hundreds more by network_id).
  - ledc  : London Economic Dev Corp boards (custom ASP.NET, server-rendered HTML).  [fetch_ledc: TODO]

Every adapter returns the SAME normalized job dict as ats.py (+ optional
enrichment fields the source can supply directly), and is FAILURE-SAFE: a broken
board returns [] and never kills the build.

Only stdlib + requests (+ ats helpers). Runs anywhere the ATS engine runs.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone

import re

import requests
import ats  # reuse _strip_html; same normalized shape

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bt-jobboard/1.0; +personal job search)",
    "Accept": "application/json",            # REQUIRED by Getro (else HTTP 406)
    "Content-Type": "application/json",
}

# Keyword queries when the caller gives none. Getro search is relevance-ranked,
# so we run a small on-profile set and merge. Broad enough for tech + adjacent.
DEFAULT_QUERIES = [
    "embedded", "firmware", "hardware", "electronics", "PCB", "electrical",
    "FPGA", "altium", "test engineer", "signal", "power",
]


# ---------------------------------------------------------------------------
# transport (patched out in tests)
# ---------------------------------------------------------------------------
def _post(url: str, body: dict) -> dict:
    r = requests.post(url, headers=HEADERS, json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _point_to_latlng(point: str):
    """'POINT (-80.49 43.45)' -> (43.45, -80.49). Getro stores lng first."""
    try:
        inside = point[point.index("(") + 1: point.index(")")].strip()
        lng, lat = (float(x) for x in inside.split())
        return lat, lng
    except Exception:
        return None, None


def _salary(job: dict) -> str:
    if not job.get("compensation_public"):
        return ""
    lo = job.get("compensation_amount_min_cents")
    hi = job.get("compensation_amount_max_cents")
    cur = job.get("compensation_currency") or ""
    per = job.get("compensation_period") or ""
    def dollars(cents):
        return f"${cents // 100:,.0f}"
    if lo and hi:
        span = f"{dollars(lo)}–{dollars(hi)}"
    elif lo or hi:
        span = dollars(lo or hi)
    else:
        return ""
    return " ".join(x for x in [span, cur, ("/" + per) if per else ""] if x).replace(" /", "/")


def _iso(unix_secs):
    try:
        return datetime.fromtimestamp(int(unix_secs), timezone.utc).isoformat()
    except Exception:
        return None


_WORK_MODE = {"on_site": "onsite", "onsite": "onsite", "remote": "remote", "hybrid": "hybrid"}


def _norm_getro(job: dict, board: str) -> dict:
    org = job.get("organization") or {}
    locs = job.get("searchable_locations") or []
    lat, lng = (None, None)
    ld = job.get("location_details") or []
    if ld and isinstance(ld[0], dict) and ld[0].get("point"):
        lat, lng = _point_to_latlng(ld[0]["point"])
    skills = job.get("skills") or []
    tags = org.get("industry_tags") or []
    return {
        "company": (org.get("name") or "").strip() or "n/a",
        "title": (job.get("title") or "").strip(),
        "location": (locs[0] if locs else "") or "n/a",
        "url": job.get("url") or "",
        "posted": _iso(job.get("created_at")),
        # search payload omits the body; skills are the scorable text we do get
        "description": ats._strip_html(" ".join(skills)),
        "salary": _salary(job),
        "source": f"getro:{board}",
        # optional enrichments (build_board prefers these over its heuristics)
        "arrangement": _WORK_MODE.get(job.get("work_mode")),
        "lat": lat, "lng": lng,
        "industry": tags[0] if tags else None,
    }


# ---------------------------------------------------------------------------
# adapters
# ---------------------------------------------------------------------------
def fetch_getro(name: str, network_id, queries=None, per_page: int = 100) -> list:
    """Pull a Getro board by network_id. Runs each keyword query, merges, dedupes by job id.

    Failure-safe: any network/parse error -> []. Confirmed shapes: MaRS 383, Communitech 8936.
    """
    url = f"https://api.getro.com/api/v2/collections/{network_id}/search/jobs"
    queries = queries or DEFAULT_QUERIES
    seen, out = set(), []
    try:
        for q in queries:
            data = _post(url, {"hitsPerPage": per_page, "page": 0, "query": q})
            for job in (data.get("results", {}) or {}).get("jobs", []) or []:
                jid = job.get("id") or (job.get("url"), job.get("title"))
                if jid in seen:
                    continue
                seen.add(jid)
                out.append(_norm_getro(job, name))
    except Exception:
        return []          # never kill the build over one board
    return out


def _get_text(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


# LEDC job cards are regular server-rendered blocks (confirmed 2026-09-17):
#   <div class="gm-card"> <a href="job.aspx?jid=UUID"> …
#     <h4 class="gm-card-title">Title</h4> <h3 class="gm-card-subtitle">Company</h3>
#     <i class="fa fa-map-marker"></i>London, ON <i class="fa fa-clock-o"></i>Sep 14, 2026
_RE_JID = re.compile(r'job\.aspx\?jid=([0-9a-fA-F\-]+)')
_RE_TITLE = re.compile(r'gm-card-title"[^>]*>\s*(.*?)\s*</h4>', re.S)
_RE_COMPANY = re.compile(r'gm-card-subtitle"[^>]*>\s*(.*?)\s*</h3>', re.S)
_RE_LOC = re.compile(r'fa-map-marker"></i>\s*([^<]+)')
_RE_DATE = re.compile(r'fa-clock-o"></i>\s*([A-Za-z]{3}\s+\d{1,2},\s*\d{4})')


def parse_ledc_cards(html_text: str, base: str, board: str) -> list:
    """Parse gm-card blocks out of a joblist.aspx page. Pure function (testable, no I/O)."""
    out = []
    for chunk in html_text.split('class="gm-card"')[1:]:     # one piece per card
        mjid = _RE_JID.search(chunk)
        mtitle = _RE_TITLE.search(chunk)
        if not (mjid and mtitle):
            continue
        mcomp, mloc, mdate = _RE_COMPANY.search(chunk), _RE_LOC.search(chunk), _RE_DATE.search(chunk)
        title = ats._strip_html(mtitle.group(1))
        company = ats._strip_html(mcomp.group(1)) if mcomp else ""
        loc = mloc.group(1).strip() if mloc else ""
        posted = mdate.group(1) if mdate else None
        out.append({
            "company": company or "n/a",
            "title": title,
            "location": ats._strip_html(loc) or "n/a",
            "url": f"{base}/job.aspx?jid={mjid.group(1)}",
            "posted": posted,
            "description": "",                # detail body not fetched (would be N extra requests)
            "salary": "",
            "source": f"ledc:{board}",
            "arrangement": None, "lat": None, "lng": None, "industry": None,
        })
    return out


def fetch_ledc(name: str, base: str, max_pages: int = 20, **_) -> list:
    """London EDC boards (server-rendered HTML). Paginated joblist.aspx (50/page), scored by our engine.

    Failure-safe: keeps whatever pages succeeded; any error -> return what we have.
    """
    base = base.rstrip("/")
    out, seen = [], set()
    try:
        for page in range(1, max_pages + 1):
            cards = parse_ledc_cards(_get_text(f"{base}/joblist.aspx?page={page}"), base, name)
            fresh = [c for c in cards if c["url"] not in seen]
            for c in fresh:
                seen.add(c["url"])
            out += fresh
            if len(cards) < 50 or not fresh:     # last page, or no new rows
                break
    except Exception:
        return out
    return out


FETCH_SOURCES = {
    "getro": lambda e: fetch_getro(e["name"], e["network_id"], e.get("queries")),
    "ledc": lambda e: fetch_ledc(e["name"], e["base"]),
}


def load_sources():
    path = os.path.join(HERE, "sources.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("sources", [])
    except Exception:
        return []


def fetch_source(entry: dict):
    """Fetch one source registry entry. Returns (jobs, error_or_None) -- mirrors ats.fetch_company."""
    fn = FETCH_SOURCES.get(entry.get("platform"))
    if not fn:
        return [], f"no adapter for source platform '{entry.get('platform')}'"
    try:
        return fn(entry), None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"
