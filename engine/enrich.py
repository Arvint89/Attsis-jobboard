"""JB-52: thin-JD enrichment.

The Workday CXS search endpoint returns titles with no body
(`fetch_workday` in ats.py passes "" through). The per-job detail endpoint
carries `jobPostingInfo.jobDescription` -- the real text the scorer needs
to lift a role out of `below`.

This module runs AFTER gather/dedupe and BEFORE classify. It scans the job
list, finds Workday rows whose description is below MIN_BODY, and fills
them in-place. Bounded by a per-run fetch budget so a 500-job sweep can't
accidentally hammer the ATS. Failure-safe: a dead detail call leaves the
job as title-only rather than crashing the sweep.

Follow-up ticket (JB-52b) will add Getro enrichment, which requires
threading the Getro job_id through _norm_getro first.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse

import ats   # reuse _strip_html + the shared transport


MIN_BODY = 200   # mirror jobfilter.MIN_BODY: below this, the scorer treats the job as title-only
DEFAULT_MAX_FETCHES = 50

_LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
_WORKDAY_HOST_RE = re.compile(r"^([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com$")


def _workday_detail_url(job_url: str | None) -> str | None:
    """Convert a Workday job URL into its CXS detail endpoint URL.

    e.g. https://nokia.wd3.myworkdayjobs.com/careers/job/K/PCB_R-1
      -> https://nokia.wd3.myworkdayjobs.com/wday/cxs/nokia/careers/job/K/PCB_R-1
    Returns None if the URL is not a Workday job URL we can parse.
    """
    if not job_url:
        return None
    try:
        u = urlparse(job_url)
    except Exception:
        return None
    host = (u.hostname or "").lower()
    m = _WORKDAY_HOST_RE.match(host)
    if not m:
        return None
    tenant = m.group(1)
    segs = [s for s in (u.path or "").split("/") if s]
    if not segs:
        return None
    # strip optional locale segment (en-US, fr-CA, ...) before site
    if _LOCALE_RE.match(segs[0]):
        segs = segs[1:]
    if not segs:
        return None
    site = segs[0]
    # Workday search returns externalPath already starting with /job/; the stored
    # job URL is {site}{externalPath}, so segs[1:] already begins with "job".
    external_path = "/" + "/".join(segs[1:])
    return f"https://{host}/wday/cxs/{tenant}/{site}{external_path}"


def fetch_workday_description(job_url: str, _get=None) -> str:
    """Fetch and strip the Workday jobDescription for a single posting URL.

    Failure-safe: returns "" on parse / network / shape errors. The caller
    decides whether to leave the job as title-only or try something else.
    """
    detail_url = _workday_detail_url(job_url)
    if not detail_url:
        return ""
    get = _get or (lambda u: ats._get(u))
    try:
        resp = get(detail_url)
        data = resp.json() if hasattr(resp, "json") else resp
    except Exception:
        return ""
    try:
        html_body = (data.get("jobPostingInfo") or {}).get("jobDescription") or ""
    except Exception:
        return ""
    return ats._strip_html(html_body)


def enrich_thin_descriptions(jobs: list, max_fetches: int = DEFAULT_MAX_FETCHES,
                             _get=None) -> dict:
    """Walk `jobs` and fill thin Workday descriptions in-place via the detail
    endpoint. Returns a stats dict for logging/telemetry.

    Only touches jobs where source == "workday" AND len(description) < MIN_BODY.
    Stops making network calls after `max_fetches` thin rows have been attempted
    (counts attempts, not successes -- failures still consume budget to prevent
    runaway loops against a flaky endpoint).
    """
    stats = {"enriched": 0, "attempted": 0, "failed": 0, "skipped_budget": 0}
    for job in jobs:
        if job.get("source") != "workday":
            continue
        desc = job.get("description") or ""
        if len(desc) >= MIN_BODY:
            continue
        if stats["attempted"] >= max_fetches:
            stats["skipped_budget"] += 1
            continue
        stats["attempted"] += 1
        new_desc = fetch_workday_description(job.get("url") or "", _get=_get)
        if new_desc:
            job["description"] = new_desc
            stats["enriched"] += 1
        else:
            stats["failed"] += 1
    return stats
