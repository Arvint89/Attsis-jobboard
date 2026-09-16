"""
jobfilter.py -- deterministic match / score / flag, driven by a CV profile.

The matching model (title triggers, skill confirmers, boosters, exclusions,
params) is loaded from profile.json when present (produced by cv_parse.py from
BT's CV), else from model_base.BASE. So the CV -- not this code -- decides fit.
No LLM call; every decision is explainable via reasons[].

Pipeline per job: classify() -> {verdict, score, reasons, flags, matched}
  verdict: "match" (>= report_threshold, not excluded) | "below" | "excluded"
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone

import model_base

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_model():
    if os.getenv("JOBFILTER_FORCE_BASE"):
        return model_base.BASE
    path = os.path.join(HERE, "profile.json")
    if os.path.exists(path):
        try:
            prof = json.load(open(path, encoding="utf-8"))
            m = prof.get("model", prof)
            m = dict(m); m["_home"] = (prof.get("home") or "").lower()
            return m
        except Exception:
            pass
    return model_base.BASE


_M = _load_model()
TITLE_CORE = _M["title_triggers"]["core"]
TITLE_ADJACENT = _M["title_triggers"]["adjacent"]
TITLE_FPGA = _M["title_triggers"]["fpga"]
SKILL_CONFIRMERS = _M["skill_confirmers"]
MEDICAL = _M["boosters"]["medical"]
IEC60601 = _M["boosters"]["iec60601"]
SPACE = _M["boosters"]["space"]
VERIFICATION = _M["boosters"]["verification"]
EXCL_POWER = _M["exclusions"]["power"]
EXCL_SOFTWARE = _M["exclusions"]["software"]
EXCL_LEVEL = _M["exclusions"]["level"]
POWER_CONTEXT = _M["exclusions"]["power_context"]
REPORT_THRESHOLD = _M["params"]["report_threshold"]
HOME = _M.get("_home", "")
ALL_TITLES = TITLE_CORE + TITLE_FPGA + TITLE_ADJACENT
FRESH_DAYS = _M["params"]["fresh_days"]


def _has(text, needles):
    return [n for n in needles if n in text]


def _title_hit(title):
    for n in TITLE_CORE:
        if n in title:
            return "core", n
    for n in TITLE_FPGA:
        if n in title:
            return "fpga", n
    for n in TITLE_ADJACENT:
        if n in title:
            return "adjacent", n
    return None, None


def days_old(posted):
    if not posted:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(posted, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).days
        except ValueError:
            continue
    return None


def classify(job, extra_flags=None):
    """Unified GENERIC scorer — single source of truth, mirrors the browser.
    Score comes only from the CV-derived profile (titles + skills), never from
    hardcoded domain boosts. Domain relevance rides in through the user's own
    keywords (e.g. a medical CV lists 'iso 13485' as a skill)."""
    title = (job.get("title") or "").lower()
    body = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    text = f"{title}\n{body}"
    reasons, flags, matched = [], list(extra_flags or []), []

    # hard exclusions (off-profile noise) ------------------------------------
    if _has(title, EXCL_LEVEL) or _has(f" {title} ", EXCL_LEVEL):
        bad = _has(title, EXCL_LEVEL) or _has(f" {title} ", EXCL_LEVEL)
        return {"verdict": "excluded", "score": 0, "reasons": [f"off-profile title: {bad}"], "flags": flags, "matched": []}
    if _has(text, EXCL_SOFTWARE) and not _has(text, ["embedded", "firmware"]):
        return {"verdict": "excluded", "score": 0, "reasons": ["pure-software"], "flags": flags, "matched": []}

    # relevance: a title trigger, or >=2 skill confirmers --------------------
    title_hits = [t for t in ALL_TITLES if t in title]
    conf = sorted(set(_has(body, SKILL_CONFIRMERS)))
    if not title_hits and len(conf) < 2:
        return {"verdict": "excluded", "score": 0, "reasons": ["not relevant to profile"], "flags": flags, "matched": []}

    age = days_old(job.get("posted"))
    if age is not None and age > FRESH_DAYS:
        return {"verdict": "excluded", "score": 0, "reasons": [f"stale ({age}d)"], "flags": flags, "matched": []}

    # generic scoring (identical formula to the browser) --------------------
    score = 4 if title_hits else 2
    reasons.append("title match: " + ", ".join(title_hits[:2]) if title_hits else "keyword-only match")
    matched += title_hits
    if conf:
        score += 3 if len(conf) >= 8 else 2 if len(conf) >= 4 else 1
        reasons.append(f"skills x{len(conf)}")
        matched += conf
    else:
        score -= 1
        reasons.append("no skills in body")
    if _has(title, ["senior", "lead", "principal", "staff"]):
        score += 1
        reasons.append("senior/lead(+1)")
    if (HOME and HOME in location) or "remote" in location:
        score += 1
        reasons.append("home/remote(+1)")

    if "remote" in location:
        flags.append("remote")
    if any(w in location for w in ["united states", "usa", ", us", "california"]):
        flags.append("US")
    if "c++" in body:
        flags.append("C++")

    score = max(1, min(10, score))
    verdict = "match" if score >= REPORT_THRESHOLD else "below"
    return {"verdict": verdict, "score": score, "reasons": reasons,
            "flags": sorted(set(flags)), "matched": sorted(set(m for m in matched if m))}
