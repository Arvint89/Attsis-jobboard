"""resolver.py -- JB-43: find the ATS behind a company's careers page.

resolve(url): detect_ats(url) first (free); otherwise fetch the page once and scan its HTML for
an ATS link / embed (detect_ats_in_html). Results are cached per page so a company's careers site
is fetched at most once a week (misses) or once a month (hits). The cache is published with the
site (data/resolver_cache.json) and read back next run, like history.json -- no git writes.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import ats_detect

CACHE_URL = os.getenv("JB_RESOLVER_CACHE_URL",
                      "https://arvint89.github.io/Attsis-jobboard/data/resolver_cache.json")
RECHECK_MISS_DAYS = 7
RECHECK_HIT_DAYS = 30
MAX_LOOKUPS = 200          # new page fetches per run (cached ones are free)
UA = {"User-Agent": "Mozilla/5.0 (compatible; bt-jobboard/1.0; +personal job search)"}


def cache_key(url: str) -> str:
    """One entry per careers site: host + first path segment ('careers.kpmg.ca/jobs')."""
    u = urlparse(url or "")
    seg = [s for s in (u.path or "").split("/") if s]
    return ((u.hostname or "").lower() + ("/" + seg[0] if seg else "")).strip("/")


def _now():
    return datetime.now(timezone.utc)


def _fresh(entry: dict, now) -> bool:
    try:
        t = datetime.fromisoformat(entry["checked"])
    except Exception:
        return False
    days = RECHECK_HIT_DAYS if entry.get("det") else RECHECK_MISS_DAYS
    return now - t < timedelta(days=days)


def _default_get(url: str) -> str:
    import requests
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return r.text


class Resolver:
    def __init__(self, cache: dict | None = None, get_text=None, max_lookups: int = MAX_LOOKUPS, now=None):
        self.cache = dict(cache or {})
        self.get_text = get_text or _default_get
        self.max_lookups = max_lookups
        self.lookups = 0
        self.now = now or _now()
        self.stats = {"cached": 0, "fetched": 0, "found": 0, "failed": 0, "skipped_cap": 0}

    def resolve(self, url: str) -> dict | None:
        """Supported/unsupported ATS dict, or None. Never raises."""
        det = ats_detect.detect_ats(url)
        if det:
            return det
        key = cache_key(url)
        if not key:
            return None
        hit = self.cache.get(key)
        if hit and _fresh(hit, self.now):
            self.stats["cached"] += 1
            return hit.get("det")
        if self.lookups >= self.max_lookups:
            self.stats["skipped_cap"] += 1
            return hit.get("det") if hit else None
        self.lookups += 1
        try:
            html = self.get_text(url)
            det = ats_detect.detect_ats_in_html(html)
            self.stats["fetched"] += 1
        except Exception:
            det = None
            self.stats["failed"] += 1
        if det:
            self.stats["found"] += 1
        self.cache[key] = {"det": det, "checked": self.now.isoformat(), "url": url}
        return det


def load_cache(fetch=None) -> dict:
    try:
        if fetch is None:
            import requests
            fetch = lambda u: requests.get(u, timeout=20, headers={"Cache-Control": "no-cache"}).json()
        d = fetch(CACHE_URL)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_cache(cache: dict, out_dir: str) -> None:
    with open(os.path.join(out_dir, "resolver_cache.json"), "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)
