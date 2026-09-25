"""ats_detect.py -- identify a company's ATS (platform + slug) from a URL or careers-page HTML.

JB-5a (docs/briefs/JB-5a-detect-ats.md). Pure functions: no network, no LLM, stdlib only.
The slug is exactly what ats.fetch_<platform>() expects.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qs

SUPPORTED = {"greenhouse", "lever", "ashby", "smartrecruiters", "recruitee",
             "workable", "bamboohr", "rippling", "workday"}   # must equal set(ats.FETCHERS)

_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
_URL = re.compile(r'https?://[^\s"\'<>)]+')


def _segs(path: str) -> list:
    return [s for s in (path or "").split("/") if s]


def _res(platform: str, slug: str, **extra) -> dict | None:
    if not slug:
        return None
    out = {"platform": platform, "slug": slug, **extra, "supported": platform in SUPPORTED}
    return out


def detect_ats(url: str) -> dict | None:
    """Return {"platform", "slug", "supported"} (+ tenant/site/dc for workday) or None."""
    if not url or not isinstance(url, str):
        return None
    try:
        u = urlparse(url.strip())
    except Exception:
        return None
    host = (u.hostname or "").lower()
    seg = _segs(u.path)
    first = seg[0] if seg else ""

    if host in ("boards.greenhouse.io", "job-boards.greenhouse.io"):
        if first == "embed":        # JB-43: boards.greenhouse.io/embed/job_board?for=ecobee
            return _res("greenhouse", (parse_qs(u.query).get("for") or [""])[0])
        return _res("greenhouse", first)
    if host == "boards-api.greenhouse.io":           # /v1/boards/{slug}/...
        return _res("greenhouse", seg[2] if len(seg) > 2 and seg[:2] == ["v1", "boards"] else "")
    if host == "jobs.lever.co":
        return _res("lever", first)
    if host == "jobs.ashbyhq.com":
        return _res("ashby", first)
    if host in ("jobs.smartrecruiters.com", "careers.smartrecruiters.com"):
        return _res("smartrecruiters", first)
    if host.endswith(".recruitee.com"):
        return _res("recruitee", host.split(".")[0])
    if host == "apply.workable.com":
        return _res("workable", first)
    if host.endswith(".bamboohr.com"):
        return _res("bamboohr", host.split(".")[0])
    if host == "ats.rippling.com":
        return _res("rippling", first)
    m = re.match(r"^([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com$", host)
    if m:
        rest = seg[1:] if seg and _LOCALE.match(seg[0]) else seg
        site = rest[0] if rest else ""
        if not site:
            return None
        return _res("workday", m.group(1), tenant=m.group(1), site=site, dc=m.group(2))
    if host.endswith(".teamtailor.com"):
        return _res("teamtailor", host.split(".")[0])
    if host.endswith(".ttcportals.com"):
        return _res("ttcportals", host.split(".")[0])
    if host.startswith("recruiting.ultipro.") :
        return _res("ultipro", first)
    if host.endswith(".scouterecruit.net"):
        return _res("scouterecruit", host.split(".")[0])
    return None


def detect_ats_in_html(html: str) -> dict | None:
    """First SUPPORTED ats found in the page's URLs; else first unsupported; else None."""
    first_unsupported = None
    for url in _URL.findall(html or ""):
        r = detect_ats(url)
        if not r:
            continue
        if r["supported"]:
            return r
        first_unsupported = first_unsupported or r
    return first_unsupported
