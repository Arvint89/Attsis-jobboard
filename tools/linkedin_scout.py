"""linkedin_scout.py -- LinkedIn job URL -> company registry proposal (JB-46).

We do NOT scrape LinkedIn for jobs. This tool takes a single LinkedIn job
posting URL (or a list file), reads the public preview page once, extracts
the hiring company name and (if visible) their careers/website link, and
prints a proposed engine/companies.json registry line for a human to
review and paste. Once the company is added with platform='resolve', the
next daily sweep resolves the ATS via engine/resolver.py (JB-43) and all
future roles for that company are fetched directly -- forever. This is
Layer 4 of the coverage funnel; it feeds Layer 1 (registry).

Design contract (see docs/decisions/ADR-003-linkedin-scout.md and JB-46):
- One HTTP GET per unique URL. Results cached in data/linkedin_scout_cache.json
  (gitignored) so re-runs are free.
- If LinkedIn blocks the unauth GET (HTTP 999 / 4xx), the tool falls back to a
  paste-HTML mode: `python tools/linkedin_scout.py --from-html <path>`.
- The tool NEVER edits companies.json -- it prints a proposal only.

CLI:
    python tools/linkedin_scout.py https://www.linkedin.com/jobs/view/4470987790
    python tools/linkedin_scout.py --from-html captured.html
    python tools/linkedin_scout.py --list urls.txt
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
CACHE_PATH = os.path.join(DATA_DIR, "linkedin_scout_cache.json")

TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bt-jobboard-scout/1.0; +personal job search)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_url(url: str) -> str:
    """Strip query/fragment; keep the /jobs/view/{id} canonical form."""
    if not url:
        return ""
    p = urlparse(url.strip())
    if not p.netloc:
        return url.strip()
    path = p.path.rstrip("/")
    # collapse /jobs/view/ID?refId=... -> /jobs/view/ID
    m = re.match(r"^(/jobs/view/\d+)", path)
    if m:
        path = m.group(1)
    return f"{p.scheme or 'https'}://{p.netloc}{path}"


def load_cache(path: str = CACHE_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict, path: str = CACHE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _default_fetcher(url: str) -> str:
    """Real network fetch. Overridable in tests."""
    import requests  # local import so unit tests don't need it
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def extract_company(html: str) -> dict:
    """Return {company, company_linkedin_url, careers_url} best-effort from a
    LinkedIn job page HTML. Missing fields come back as empty strings -- the
    caller decides whether it's usable."""
    out = {"company": "", "company_linkedin_url": "", "careers_url": ""}
    if not html:
        return out

    # 1. JSON-LD hiringOrganization (most reliable when present).
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    ):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        org = _find_hiring_org(data)
        if org:
            if isinstance(org, dict):
                out["company"] = out["company"] or (org.get("name") or "").strip()
                url = (org.get("sameAs") or org.get("url") or "").strip()
                if url:
                    if "linkedin.com/company" in url:
                        out["company_linkedin_url"] = out["company_linkedin_url"] or url
                    else:
                        out["careers_url"] = out["careers_url"] or url

    # 2. topcard org-name-link anchor.
    if not out["company"]:
        m = re.search(
            r'<a[^>]+class="[^"]*topcard__org-name-link[^"]*"[^>]*href="([^"]+)"[^>]*>\s*(.+?)\s*</a>',
            html, re.DOTALL | re.IGNORECASE,
        )
        if m:
            href, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
            out["company"] = name
            if "linkedin.com/company" in href:
                out["company_linkedin_url"] = out["company_linkedin_url"] or href

    # 3. og:title fallback ("Company hiring Title in Location | LinkedIn").
    if not out["company"]:
        m = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        )
        if m:
            title = m.group(1)
            mm = re.match(r"^\s*(.+?)\s+hiring\s+.+", title, re.IGNORECASE)
            if mm:
                out["company"] = mm.group(1).strip()

    return out


def _find_hiring_org(data):
    """Recursively locate a hiringOrganization value inside a JSON-LD blob."""
    if isinstance(data, dict):
        if "hiringOrganization" in data:
            return data["hiringOrganization"]
        for v in data.values():
            got = _find_hiring_org(v)
            if got:
                return got
    elif isinstance(data, list):
        for item in data:
            got = _find_hiring_org(item)
            if got:
                return got
    return None


def propose_registry_entry(info: dict, city: str = "", industry: str = "") -> dict:
    """Build the companies.json line a human can paste. platform='resolve'
    means JB-43 resolver picks it up on the next sweep."""
    return {
        "name": info.get("company") or "",
        "ring": 4,
        "platform": "resolve",
        "slug": "",
        "careers_url": info.get("careers_url") or "",
        "note": "seeded via LinkedIn scout (JB-46)",
        "flags": [],
        "industry": industry or "",
        "sponsors": None,
        "city": city or "",
    }


def scout(url: str, fetcher=None, cache_path: str = CACHE_PATH) -> dict:
    """Look up one URL and return the extracted info + proposed registry line."""
    fetcher = fetcher or _default_fetcher
    url = normalize_url(url)
    cache = load_cache(cache_path)
    entry = cache.get(url)
    if not entry or not entry.get("html"):
        html = fetcher(url)
        cache[url] = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "html": html,
        }
        save_cache(cache, cache_path)
    else:
        html = entry["html"]
    info = extract_company(html)
    return {
        "url": url,
        "cached": bool(entry),
        "info": info,
        "proposal": propose_registry_entry(info),
    }


def scout_from_html(html: str) -> dict:
    """Paste-fallback path: parse a locally-saved LinkedIn page."""
    info = extract_company(html)
    return {"url": "", "cached": False, "info": info, "proposal": propose_registry_entry(info)}


def _fmt(result: dict) -> str:
    info = result.get("info") or {}
    prop = result.get("proposal") or {}
    lines = [
        f"URL:              {result.get('url') or '(from html)'}",
        f"cache hit:        {result.get('cached')}",
        f"company:          {info.get('company') or '(not found)'}",
        f"company LinkedIn: {info.get('company_linkedin_url') or '(not found)'}",
        f"careers URL:      {info.get('careers_url') or '(not found -- human to fill)'}",
        "",
        "Proposed engine/companies.json entry (review, then paste):",
        json.dumps(prop, indent=2, ensure_ascii=False),
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", nargs="?", help="LinkedIn /jobs/view/{id} URL")
    ap.add_argument("--list", help="path to a text file with one URL per line")
    ap.add_argument("--from-html", help="parse a locally-saved LinkedIn HTML file instead of fetching")
    ap.add_argument("--cache", default=CACHE_PATH, help="cache file path")
    a = ap.parse_args(argv)

    if a.from_html:
        html = open(a.from_html, encoding="utf-8", errors="ignore").read()
        print(_fmt(scout_from_html(html)))
        return 0

    urls = []
    if a.list:
        with open(a.list, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    elif a.url:
        urls = [a.url]
    else:
        ap.error("give a URL, --list, or --from-html")

    for i, url in enumerate(urls):
        if i:
            print("\n" + "-" * 60 + "\n")
        try:
            print(_fmt(scout(url, cache_path=a.cache)))
        except Exception as e:
            print(f"URL: {url}\nERROR: {e}\nFallback: save the page and use --from-html <path>")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
