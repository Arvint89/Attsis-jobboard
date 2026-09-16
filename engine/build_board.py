"""
build_board.py -- orchestrator. Fetch every company -> classify -> write the site data.

RUN
    python build_board.py                 # live: hit every resolved ATS
    python build_board.py --demo          # offline: load engine/fixtures.json (no network)
    python build_board.py --min-score 6   # lower the report bar

OUTPUT
    site/data/jobs.json     the board reads this (matches + below-threshold + meta)
    site/data/resolve.json  companies whose ATS is still 'resolve' (fill in once)
    prints a one-line summary (this is all the daily task needs to relay)

This is the ONLY place that touches the network. It runs wherever there is
internet -- ideally the GitHub Action (free, zero Claude tokens). The sandbox
here has no outbound net, which is exactly why --demo exists.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import ats
import jobfilter
import geo
import facets

FLAG_LEGEND = {
    'remote': 'Role is remote-friendly',
    'US': 'United States role — needs work authorization',
    'relocation': 'Outside easy commute — a move may be needed',
    'eligibility': 'Defence/controlled-goods — verify PR/CGP/ITAR eligibility',
    'medical': 'Medical-device domain (scoring boost)',
    'C++': 'JD mentions C++ (a personal no for some users)',
    'spousal-overlap': 'Same employer as a family member — weigh at apply time',
    'signed-employer': 'Current/known employer — watch only',
}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "site", "data")


def load_home():
    path = os.path.join(HERE, "profile.json")
    if os.path.exists(path):
        try:
            pr = json.load(open(path, encoding="utf-8"))
            return pr.get("home") or "London", pr.get("person") or "", pr.get("initials") or "?"
        except Exception:
            pass
    return "London", "", "?"


def load_registry():
    with open(os.path.join(HERE, "companies.json"), encoding="utf-8") as f:
        return json.load(f)["companies"]


def gather(demo: bool):
    """Return (all_jobs, errors, unresolved)."""
    if demo:
        with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as f:
            return json.load(f), [], []
    jobs, errors, unresolved = [], [], []
    for entry in load_registry():
        got, err = ats.fetch_company(entry)
        if err == "unresolved":
            unresolved.append(entry)
        elif err:
            errors.append({"company": entry["name"], "error": err})
        # attach registry flags so the classifier can carry them through
        for j in got:
            j["_reg_flags"] = entry.get("flags", [])
            j["_ring"] = entry.get("ring")
            j["_industry"] = entry.get("industry", "other")
            j["_sponsors"] = entry.get("sponsors")
        jobs += got
    return jobs, errors, unresolved


def _defaults(j):
    j.setdefault("_reg_flags", [])
    j.setdefault("_industry", "other")
    j.setdefault("_sponsors", None)
    return j


def dedupe(jobs):
    seen, out = set(), []
    for j in jobs:
        key = (j.get("company", "").lower(), j.get("title", "").lower(), j.get("location", "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


def build(demo=False, min_score=jobfilter.REPORT_THRESHOLD):
    home, person, initials = load_home()
    raw, errors, unresolved = gather(demo)
    raw = [ _defaults(j) for j in dedupe(raw) ]
    matches, below = [], []
    for j in raw:
        res = jobfilter.classify(j, extra_flags=j.get("_reg_flags"))
        if res["verdict"] == "excluded":
            continue
        ring, km, is_remote = geo.ring_for(home, j.get("location", ""))
        if ring is None:
            ring = j.get("_ring")   # fall back to registry ring if city unknown
        arrangement = facets.arrangement(j.get("location", ""), j.get("description", ""))
        country = facets.country(j.get("location", ""))
        industry = facets.industry(j.get("_industry", ""), j.get("description", ""))
        sponsor = facets.sponsorship(j.get("description", ""), j.get("_sponsors"))
        snippet = (j.get("description") or "").strip().replace("\n", " ")
        snippet = (snippet[:180] + "\u2026") if len(snippet) > 180 else snippet
        full = (j.get("title","") + ". " + (j.get("description") or "")).replace("\n", " ")
        full = full[:1500]
        row = {
            "company": j["company"], "title": j["title"], "location": j["location"],
            "url": j["url"], "posted": j.get("posted"), "source": j.get("source"),
            "salary": j.get("salary", ""), "ring": ring, "km": km,
            "score": res["score"], "flags": res["flags"],
            "arrangement": arrangement, "country": country,
            "industry": industry, "sponsorship": sponsor,
            "reasons": res["reasons"], "matched": res["matched"], "snippet": snippet,
            "text": full,
        }
        (matches if res["score"] >= min_score else below).append(row)
    def opts(key):
        return sorted({r.get(key) for r in (matches + below) if r.get(key) and r.get(key) != "?"})
    facet_opts = {"arrangement": opts("arrangement"), "country": opts("country"),
                  "industry": opts("industry"), "sponsorship": opts("sponsorship")}
    matches.sort(key=lambda r: (-r["score"], r.get("ring") if r.get("ring") is not None else 9))
    below.sort(key=lambda r: -r["score"])

    os.makedirs(DATA, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "mode": "demo" if demo else "live",
        "person": person, "initials": initials, "home": home,
        "flag_legend": FLAG_LEGEND,
        "facets": facet_opts,
        "min_score": min_score,
        "counts": {"matches": len(matches), "below": len(below),
                   "errors": len(errors), "unresolved": len(unresolved)},
        "matches": matches,
        "below": below,
        "errors": errors,
    }
    with open(os.path.join(DATA, "jobs.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(DATA, "resolve.json"), "w", encoding="utf-8") as f:
        json.dump(unresolved, f, indent=2, ensure_ascii=False)

    # also emit a data-embedded standalone page (double-click offline, no server)
    tpl_path = os.path.join(ROOT, "site", "index.html")
    if os.path.exists(tpl_path):
        import re as _re
        tpl = open(tpl_path, encoding="utf-8").read()
        inline = "<script>window.__EMBED__ = " + json.dumps(payload, ensure_ascii=False) + ";</script>\n"
        # replace the whole fetch(...) bootstrap (any form) with a direct init() call
        std = _re.sub(r"fetch\('\./data/jobs\.json.*?\}\);",
                      "init(window.__EMBED__);", tpl, flags=_re.S)
        std = std.replace("<script>", inline + "<script>", 1)
        with open(os.path.join(ROOT, "site", "board_standalone.html"), "w", encoding="utf-8") as f:
            f.write(std)

    print(f"[{payload['mode']}] {len(matches)} matches (>= {min_score}), "
          f"{len(below)} below, {len(errors)} fetch-errors, "
          f"{len(unresolved)} ATS still to resolve. -> site/data/jobs.json")
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--min-score", type=int, default=jobfilter.REPORT_THRESHOLD)
    ap.add_argument("--cv", help="parse this CV into profile.json before building")
    a = ap.parse_args()
    if a.cv:
        import cv_parse, importlib
        prof = cv_parse.build_profile(cv_parse.read_cv(a.cv), a.cv)
        json.dump(prof, open(os.path.join(HERE, "profile.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        importlib.reload(jobfilter)   # pick up the new profile
        print(f"profile <- {a.cv}: {len(prof['model']['skill_confirmers'])} active confirmers")
    build(demo=a.demo, min_score=a.min_score)
