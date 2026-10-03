"""tenants.py -- JB-62 regional-licence tenant filter.

A tenant config is a static JSON at site/data/tenants/<slug>.json that
white-labels the board to a region + partner brand. The browser loads
?tenant=<slug>, filters jobs.json to tenant.region_cities, and swaps
the header name/logo + accent colour.

This module lives on the Python side so the city-matching rule has
Python tests. The browser duplicates the same tiny membership check in
site/index.html -- the logic is small enough that duplication is
cheaper than a shared JS/Python extraction."""
from __future__ import annotations
from typing import Iterable


def _norm_city(s: str) -> str:
    """Lowercase + collapse whitespace. 'St. Thomas  ' -> 'st. thomas'.
    Punctuation stays (the registry writes 'St. Thomas' with the dot)."""
    return " ".join((s or "").lower().split())


def _job_city(job: dict) -> str:
    """Prefer `location_near` (JB-56 disambiguated), fall back to the
    first comma-split token of `location`. Returns '' if neither is
    usable so the caller can treat it as 'not in any region'."""
    near = (job.get("location_near") or "").strip()
    if near:
        return _norm_city(near)
    loc = (job.get("location") or "").strip()
    if not loc:
        return ""
    return _norm_city(loc.split(",", 1)[0])


def is_valid_tenant(tenant: dict) -> bool:
    """A usable tenant has a non-empty region_cities list. Everything
    else (name, logo_url, accent_hex, footer_html) is optional."""
    if not isinstance(tenant, dict):
        return False
    rc = tenant.get("region_cities")
    return isinstance(rc, list) and len(rc) > 0 and all(isinstance(c, str) for c in rc)


def filter_jobs(jobs: Iterable[dict], tenant: dict) -> list[dict]:
    """Keep jobs whose city is in the tenant's region_cities set.
    Case-insensitive match on the normalized city. If tenant is empty
    or invalid, returns the input unchanged (fail-open: a broken
    tenant JSON must not nuke the default board)."""
    if not is_valid_tenant(tenant):
        return list(jobs)
    allowed = {_norm_city(c) for c in tenant["region_cities"]}
    return [j for j in jobs if _job_city(j) in allowed]
