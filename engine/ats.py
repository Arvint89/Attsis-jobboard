"""
ats.py -- ATS (Applicant Tracking System) fetch adapters.

WHY THIS EXISTS
---------------
Most companies serve their careers page from an ATS that ALSO exposes a public
JSON endpoint -- the exact data the page loads in your browser, no API key, no
login. Hitting that JSON directly is how this whole engine runs at (almost) zero
token cost: deterministic Python, no LLM reading web pages.

Each adapter takes the company's ATS identifiers and returns a list of NORMALIZED
job dicts with the same shape regardless of platform:

    {
      "company":  str,
      "title":    str,
      "location": str,
      "url":      str,          # public apply/detail link
      "posted":   str | None,   # ISO date if the ATS gives one
      "description": str,       # plain text (HTML stripped), may be ""
      "source":   str,          # which ATS it came from
    }

Adding a company later is just a registry line (companies.json); adding a NEW ATS
platform is one function here plus a line in FETCHERS.

Only Python stdlib + requests are used, so it runs anywhere (GitHub Actions,
BT's laptop, a cron box) without a heavy dependency tree.
"""
from __future__ import annotations
import html
import re
import sys
from datetime import datetime, timezone

import requests

# UTF-8 everywhere (Windows-safe, per project standing rule)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TIMEOUT = 25
HEADERS = {
    # A plain browser-ish UA. These are public endpoints; we are not evading auth.
    "User-Agent": "Mozilla/5.0 (compatible; bt-jobboard/1.0; +personal job search)",
    "Accept": "application/json, text/plain, */*",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _strip_html(raw: str) -> str:
    """Turn an HTML job description into plain, searchable text."""
    if not raw:
        return ""
    txt = html.unescape(raw)
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
    txt = re.sub(r"</(p|li|h[1-6]|div)>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)          # drop remaining tags
    txt = html.unescape(txt)                    # entities that were double-encoded
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()


def _get(url: str, method: str = "GET", **kw):
    r = requests.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _norm(company, title, location, url, posted, description, source, salary=""):
    return {
        "company": company,
        "title": (title or "").strip(),
        "location": (location or "").strip() or "n/a",
        "url": url or "",
        "posted": posted,
        "description": _strip_html(description or ""),
        "salary": salary or "",
        "source": source,
    }


# ---------------------------------------------------------------------------
# adapters -- one per ATS platform
# ---------------------------------------------------------------------------
def fetch_greenhouse(company, slug, **_):
    # https://developers.greenhouse.io/job-board.html
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    data = _get(url).json()
    out = []
    for j in data.get("jobs", []):
        out.append(_norm(
            company, j.get("title"),
            (j.get("location") or {}).get("name"),
            j.get("absolute_url"),
            j.get("updated_at") or j.get("first_published"),
            j.get("content"), "greenhouse"))
    return out


def fetch_lever(company, slug, **_):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = _get(url).json()
    out = []
    for j in data:
        posted = None
        if j.get("createdAt"):
            posted = datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc).isoformat()
        out.append(_norm(
            company, j.get("text"),
            (j.get("categories") or {}).get("location"),
            j.get("hostedUrl"),
            posted,
            j.get("descriptionPlain") or j.get("description"), "lever",
            salary=(j.get("salaryRange") or {}).get("text") if isinstance(j.get("salaryRange"), dict) else ""))
    return out


def fetch_ashby(company, slug, **_):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    data = _get(url).json()
    out = []
    for j in data.get("jobs", []):
        out.append(_norm(
            company, j.get("title"), j.get("location"),
            j.get("jobUrl") or j.get("applyUrl"),
            j.get("publishedAt"),
            j.get("descriptionPlain") or j.get("descriptionHtml"), "ashby",
            salary=j.get("compensation", {}).get("compensationTierSummary", "") if isinstance(j.get("compensation"), dict) else ""))
    return out


def fetch_smartrecruiters(company, slug, **_):
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
    data = _get(url).json()
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        location = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
        out.append(_norm(
            company, j.get("name"), location,
            f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
            j.get("releasedDate"), "", "smartrecruiters"))
    return out


def fetch_recruitee(company, slug, **_):
    url = f"https://{slug}.recruitee.com/api/offers/"
    data = _get(url).json()
    out = []
    for j in data.get("offers", []):
        out.append(_norm(
            company, j.get("title"), j.get("location"),
            j.get("careers_url") or j.get("url"),
            j.get("published_at"),
            j.get("description"), "recruitee"))
    return out


def fetch_workable(company, slug, **_):
    url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    data = _get(url, method="POST", json={"query": "", "location": []}).json()
    out = []
    for j in data.get("results", []):
        loc = j.get("location") or {}
        location = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
        out.append(_norm(
            company, j.get("title"), location,
            f"https://apply.workable.com/{slug}/j/{j.get('shortcode')}/",
            j.get("published_on") or j.get("created_at"),
            j.get("description"), "workable"))
    return out


def fetch_bamboohr(company, slug, **_):
    # BambooHR embed API. The list endpoint gives titles only; the per-job
    # /detail endpoint carries the description (JB-19).
    data = _get(f"https://{slug}.bamboohr.com/careers/list").json()
    out = []
    for j in (data.get("result") or []):
        jid = j.get("id")
        title = j.get("jobOpeningName")
        loc = j.get("location")
        if isinstance(loc, dict):
            location = ", ".join(x for x in [loc.get("city"), loc.get("state"), loc.get("country")] if x)
        else:
            location = loc or ""
        if j.get("isRemote") in (True, "true", 1):
            location = (location + " (Remote)").strip()
        description = ""
        posted = j.get("datePosted")
        url = f"https://{slug}.bamboohr.com/careers/{jid}"
        try:  # fetch the detail page for the real description
            det = _get(f"https://{slug}.bamboohr.com/careers/{jid}/detail").json()
            jo = (det.get("result") or {}).get("jobOpening") or {}
            description = jo.get("description") or ""
            posted = jo.get("datePosted") or posted
            url = jo.get("jobOpeningShareUrl") or url
            if not location and isinstance(jo.get("location"), str):
                location = jo["location"]
        except Exception:
            pass  # keep title-only if a detail fetch fails
        out.append(_norm(company, title, location or "n/a", url, posted, description, "bamboohr"))
    return out


def fetch_rippling(company, slug, **_):
    # Rippling ATS public board API.
    url = f"https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"
    data = _get(url).json()
    jobs = data if isinstance(data, list) else data.get("items", data.get("jobs", []))
    out = []
    for j in jobs:
        loc = j.get("workLocation") or {}
        location = j.get("location") or ", ".join(
            x for x in [loc.get("city"), loc.get("state"), loc.get("country")] if x)
        out.append(_norm(
            company, j.get("name") or j.get("title"), location,
            j.get("url") or j.get("jobUrl") or f"https://ats.rippling.com/{slug}/jobs/{j.get('uuid') or j.get('id')}",
            j.get("createdAt") or j.get("postedDate"),
            j.get("description"), "rippling"))
    return out


def fetch_workday(company, slug, tenant=None, site=None, dc="wd1", **_):
    # Workday CXS search endpoint (POST). tenant + site + data-center (wdN) required.
    tenant = tenant or slug
    site = site or slug
    url = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    out, offset = [], 0
    while True:
        data = _get(url, method="POST",
                    json={"appliedFacets": {}, "limit": 20, "offset": offset,
                          "searchText": ""}).json()
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for j in postings:
            path = j.get("externalPath", "")
            out.append(_norm(
                company, j.get("title"), j.get("locationsText"),
                f"https://{tenant}.{dc}.myworkdayjobs.com/{site}{path}",
                j.get("postedOn"), "", "workday"))
        offset += 20
        if offset >= data.get("total", 0) or offset > 200:
            break
    return out


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "recruitee": fetch_recruitee,
    "workable": fetch_workable,
    "bamboohr": fetch_bamboohr,
    "rippling": fetch_rippling,
    "workday": fetch_workday,
}


def fetch_company(entry: dict):
    """Fetch one registry entry. Returns (jobs, error_or_None)."""
    platform = entry.get("platform")
    if platform in (None, "", "resolve"):
        return [], "unresolved"
    fn = FETCHERS.get(platform)
    if not fn:
        return [], f"no adapter for platform '{platform}'"
    try:
        return fn(
            entry["name"], entry.get("slug", ""),
            tenant=entry.get("tenant"), site=entry.get("site"),
            dc=entry.get("dc", "wd1"),
        ), None
    except Exception as e:  # network / parse / shape drift -- never kill the run
        return [], f"{type(e).__name__}: {e}"
