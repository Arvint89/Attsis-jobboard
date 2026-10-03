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
import geo

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
# JB-38: an "X engineer" trigger also matches "X designer" / "X developer" titles
# (skipped for generic roots where the variant means something else, e.g. "product designer" = UX).
_VARIANT_SKIP = {"product engineer", "systems engineer", "design engineer"}


def _variants(titles):
    out = list(titles)
    for t in titles:
        if t.endswith(" engineer") and t not in _VARIANT_SKIP:
            root = t[: -len(" engineer")]
            out += [root + " designer", root + " developer", root + " engineering"]
    return list(dict.fromkeys(out))


TITLE_CORE = _variants(TITLE_CORE)
TITLE_ADJACENT = _variants(TITLE_ADJACENT)
TITLE_FPGA = _variants(TITLE_FPGA)
ALL_TITLES = TITLE_CORE + TITLE_FPGA + TITLE_ADJACENT
# JB-50: augment ALL_TITLES + SKILL_CONFIRMERS with the canonical skills DB.
# The DB is deterministic and human-curated (data/skills.json); it widens recall
# for skills/titles the CV never mentioned. The scoring formula is unchanged --
# DB hits fall into the same "keyword-only" / "confirmer bonus" paths. Core vs
# adjacent vs fpga scoring stays CV-driven because we do NOT add DB rows to
# TITLE_CORE/TITLE_FPGA/TITLE_ADJACENT.
#
# Title categories are scoped to tech-adjacent ones so a broad DB (sales, hr,
# hospitality, retail, ...) does not turn generic business roles into relevance
# hits for the current tech-focused profile. All skill categories are added --
# skills widen the confirmer pool but do not decide relevance alone (>=2 needed
# to clear gate-1, so noise stays bounded).
_TECH_TITLE_CATS = {
    "software_eng", "data", "devops_platform", "hardware", "qa_test",
    "product_pm", "design", "architect_solutions", "other_eng",
    "software_specialized", "software_by_lang", "software_by_framework",
    "additional_data_ml",
}
try:
    import skills_db as _sdb
    _db = _sdb.load_db()
    _seen_conf = set(SKILL_CONFIRMERS)
    for _row in _db.get("skills", []):
        for _form in [_row.get("canonical", "")] + list(_row.get("aliases") or []):
            _f = (_form or "").lower().strip()
            if _f and _f not in _seen_conf:
                SKILL_CONFIRMERS.append(_f)
                _seen_conf.add(_f)
    _seen_titles = set(ALL_TITLES)
    for _row in _db.get("titles", []):
        if _row.get("category") not in _TECH_TITLE_CATS:
            continue
        for _form in [_row.get("canonical", "")] + list(_row.get("aliases") or []):
            _f = (_form or "").lower().strip()
            if _f and _f not in _seen_titles:
                ALL_TITLES.append(_f)
                _seen_titles.add(_f)
except Exception:
    pass
# JB-38: profile gaps (IC/silicon) and power/building-services context lower the score
EXCL_GAP = _M["exclusions"].get("gap", ["physical design", "asic design", "analog ic", "ic design",
                                        "tapeout", "tape-out", "place and route", "standard cell"])
MIN_BODY = 200   # shorter "descriptions" (e.g. Getro skill tags) count as no description
FRESH_DAYS = _M["params"]["fresh_days"]


import re as _re

# JB-66 perf: _tokp() used to compile a fresh regex on every call. With
# ALL_TITLES ~2.8k and SKILL_CONFIRMERS ~1.3k, that's ~8k regex compilations
# per job, dominating sweep time (~363ms/job baseline, ~87% of a 1688-job sweep).
# Cache compiled patterns per needle and tokenize text once so single-token
# needles (the vast majority) do O(1) set lookups instead of regex search.
_TOKP_CACHE: dict[str, "_re.Pattern[str]"] = {}
_TOKEN_RE = _re.compile(r"[a-z0-9]+")
_SPLIT_CACHE: dict[int, tuple[set[str], list[str]]] = {}


def _tokp(text, needle):
    """whole-token match: 'ble' must not match inside 'scalable'.
    Compiled pattern cached per needle (JB-66)."""
    rx = _TOKP_CACHE.get(needle)
    if rx is None:
        rx = _re.compile(r"(?<![a-z0-9])" + _re.escape(needle) + r"(?![a-z0-9])")
        _TOKP_CACHE[needle] = rx
    return rx.search(text) is not None


def _split_needles(needles):
    """Partition needles into (single-token-set, multi-token-list).
    Multi-token = anything containing a space, punctuation, or non-alnum char
    (e.g. 'iso 13485', 'node.js', 'c++'). Memoised by object identity because
    ALL_TITLES/SKILL_CONFIRMERS are rebuilt once at module load.
    (JB-66)"""
    key = id(needles)
    cached = _SPLIT_CACHE.get(key)
    if cached is not None and len(cached[0]) + len(cached[1]) == len(needles):
        return cached
    single, multi = set(), []
    for n in needles:
        if n and n.isalnum():
            single.add(n)
        else:
            multi.append(n)
    _SPLIT_CACHE[key] = (single, multi)
    return single, multi


def _has(text, needles):
    """Return needles present in text as whole tokens, input-order preserved.
    JB-66: tokenize text once; single-token needles hit a set (O(1)), only
    multi-token needles fall through to the cached-regex path."""
    single, _multi = _split_needles(needles)
    tset = set(_TOKEN_RE.findall(text)) if single else set()
    out = []
    for n in needles:
        if n in single:
            if n in tset:
                out.append(n)
        elif _tokp(text, n):
            out.append(n)
    return out


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


def tokens_for(job):
    """JB-69: pre-compute per-job hits against the canonical DB (ALL_TITLES +
    SKILL_CONFIRMERS, both already widened by data/skills.json at module load).
    Shipped on each row of jobs.json so the browser does set intersection
    (`profile.skills.includes(s)`) instead of 1340 `new RegExp()` per job per
    rescore (~2.26M regex on cold boot for 1688 jobs).

    The token universe is the SAME for every user, so any CV scored against
    these pre-matched tokens stays correct. CV-only skills that aren't in the
    canonical DB still need regex in the browser, but that's a small loop
    (user's CV has 20-50 skills, not 828).

    JB-66: uses _has() which tokenizes once + set-intersects (O(1) per
    single-token needle) instead of compiling 2.8k+1.3k fresh regexes."""
    title = (job.get("title") or "").lower()
    body = (job.get("description") or "").lower()
    return {
        "titles": sorted(set(_has(title, ALL_TITLES))),
        "skills": sorted(set(_has(body, SKILL_CONFIRMERS))),
    }


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
    # JB-66: _has() uses tokenize-once + set-intersect, not per-needle regex
    title_hits = _has(title, ALL_TITLES)
    conf = sorted(set(_has(body, SKILL_CONFIRMERS)))
    if not title_hits and len(conf) < 2:
        return {"verdict": "excluded", "score": 0, "reasons": ["not relevant to profile"], "flags": flags, "matched": []}

    age = days_old(job.get("posted"))
    if age is not None and age > FRESH_DAYS:
        return {"verdict": "excluded", "score": 0, "reasons": [f"stale ({age}d)"], "flags": flags, "matched": []}

    # generic scoring (identical formula to the browser) --------------------
    # JB-38: core title 5, adjacent/fpga title 4, keyword-only 2
    core_hit = _has(title, TITLE_CORE)
    score = 5 if core_hit else (4 if title_hits else 2)
    reasons.append("title match: " + ", ".join(title_hits[:2]) if title_hits else "keyword-only match")
    matched += title_hits
    if conf:
        score += 3 if len(conf) >= 8 else 2 if len(conf) >= 4 else 1
        reasons.append(f"skills x{len(conf)}")
        matched += conf
    elif len(body) >= MIN_BODY:
        score -= 1
        reasons.append("no skills in body")
    else:
        reasons.append("no description from source")   # JB-38: don't punish missing data
    if _has(title, ["senior", "lead", "principal", "staff"]):
        score += 1
        reasons.append("senior/lead(+1)")
    gap = _has(title, EXCL_GAP)
    if gap:
        score -= 3
        reasons.append(f"profile gap: {gap[0]}(-3)")
    if _has(text, POWER_CONTEXT) and len(conf) < 2:
        score -= 2
        reasons.append("power/building-services(-2)")
    ring, _km, is_remote = geo.ring_for(HOME, job.get("location") or "") if HOME else (None, None, "remote" in location)
    if is_remote or "remote" in location or (ring is not None and ring <= 2):
        score += 1
        reasons.append("commutable/remote(+1)")

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


def score_explanation(result: dict) -> str:
    """JB-63: turn classify()'s reasons[] shorthand into a one-paragraph English
    sentence a non-engineer can read. Addresses COMMERCIALIZATION_RISKS.md §3.4
    ("score reasons are debug output, not user-grade").

    Deterministic. No LLM. Mirrors the exact decisions classify() made so a
    paying user can see WHY a role scored what it did -- including excluded
    jobs, so "why isn't this on my board" has an answer.
    """
    verdict = result.get("verdict", "")
    score = result.get("score", 0)
    reasons = result.get("reasons", []) or []
    matched = result.get("matched", []) or []

    if verdict == "excluded":
        # Reason strings are short tags; expand each.
        tag = reasons[0] if reasons else "excluded"
        if tag.startswith("off-profile title"):
            return f"Excluded: the title names a role outside your profile ({tag.split(':',1)[1].strip()})."
        if tag == "pure-software":
            return "Excluded: looks like a pure-software role (no embedded/firmware signal in the description)."
        if tag == "not relevant to profile":
            return "Excluded: no title triggers matched and fewer than 2 of your CV skills appear in the description."
        if tag.startswith("stale"):
            return f"Excluded: posting is {tag.split('(',1)[1].rstrip(')').strip()} old (past the freshness window)."
        return f"Excluded: {tag}."

    # Score explanation for match / below.
    parts = []
    for r in reasons:
        if r == "keyword-only match":
            parts.append("the description mentions your profile keywords but the title didn't name a role you target (+2 base)")
        elif r.startswith("title match"):
            titles = r.split(":", 1)[1].strip()
            parts.append(f"the title names {titles}, which maps to a role you target (+4-5 base)")
        elif r.startswith("skills x"):
            n = r.replace("skills x", "").strip()
            boost = "+1" if int(n) < 4 else "+2" if int(n) < 8 else "+3"
            sample = ", ".join(matched[:3])
            parts.append(f"your CV lists {n} skills that appear in the description ({boost}: {sample}{'...' if len(matched)>3 else ''})")
        elif r == "no skills in body":
            parts.append("none of your CV skills appear in the description text (-1)")
        elif r == "no description from source":
            parts.append("the source only shipped a title (no description to score against -- not penalised)")
        elif r == "senior/lead(+1)":
            parts.append("title mentions senior/lead/principal/staff (+1)")
        elif r.startswith("profile gap"):
            gap = r.split(":", 1)[1].strip()
            parts.append(f"title names {gap}, which your profile flags as a gap")
        elif r == "power/building-services(-2)":
            parts.append("description reads as power/building-services (not your embedded profile) and fewer than 2 skills matched (-2)")
        elif r == "commutable/remote(+1)":
            parts.append("role is remote or inside your inner commute rings (+1)")
        else:
            parts.append(r)

    joined = "; ".join(parts) if parts else "no scoring signal captured"
    verb = "matches" if verdict == "match" else "scored below your match threshold"
    return f"Score {score}/10 ({verb}): {joined}."
