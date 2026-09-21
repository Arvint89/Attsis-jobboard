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
import ats_detect
import sources
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


MAX_NEW_COMPANIES = 500   # JB-5/39: bound the extra ATS fetches per run
LAST_DISCOVERY = {"discovered": [], "enriched": 0, "errors": []}
WORKERS = int(os.getenv("JB_WORKERS", "8"))   # JB-41: parallel company fetches


def parallel_map(fn, items, workers=None):
    """JB-41: run fn over items in a thread pool; results come back IN INPUT ORDER, so the
    output is identical to a sequential loop. Network-bound work, so threads are enough."""
    items = list(items)
    workers = WORKERS if workers is None else workers
    if workers <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def enrich_via_ats(source_jobs, known, fetch=None, max_new=MAX_NEW_COMPANIES, relevant=None, in_region=None):
    """JB-5 / JB-38b: follow aggregator apply links to each company's own ATS.

    source_jobs: jobs from board sources (Getro/LEDC), each with "url", "company", "source".
    known:       set of (platform, slug) already fetched from the registry.
    For every supported ATS found in a job url: fetch that company's whole board once
    (full descriptions, all roles) and drop its aggregator stubs. Registry companies are not
    refetched (their stubs are dropped as duplicates). Unsupported ATS / failed fetch -> keep stubs.
    relevant:    optional job -> bool; in_region: optional job -> bool.
                 A company is promoted if any of its stubs is relevant OR in the region (JB-39: track
                 every regional company on a readable ATS -- its hardware roles may only be on its
                 own board). Relevant companies are promoted first, so the cap never drops them.
    Returns (jobs, info) with info = {"discovered": [names], "enriched": n_stubs_replaced, "errors": [...]}.
    """
    fetch = fetch or ats.fetch_company
    groups, keep = {}, []
    for j in source_jobs:
        det = ats_detect.detect_ats(j.get("url") or "")
        if det and det["supported"]:
            key = (det["platform"], det["slug"])
            groups.setdefault(key, {"det": det, "stubs": []})["stubs"].append(j)
        else:
            keep.append(j)
    out, info = [], {"discovered": [], "enriched": 0, "errors": []}
    fetched = 0
    todo = []                                  # (entry, stubs, det) to fetch -- decided in order
    def rank(item):
        stubs = item[1]["stubs"]
        return 0 if (relevant is None or any(relevant(j) for j in stubs)) else 1
    for key, g in sorted(groups.items(), key=rank):
        gated = relevant is not None or in_region is not None
        ok = ((relevant is not None and any(relevant(j) for j in g["stubs"])) or
              (in_region is not None and any(in_region(j) for j in g["stubs"])))
        if gated and not ok:
            keep += g["stubs"]
            continue
        if key in known:                       # registry already has this company's full board
            info["enriched"] += len(g["stubs"])
            continue
        if fetched >= max_new:
            keep += g["stubs"]
            continue
        fetched += 1
        first = g["stubs"][0]
        det = g["det"]
        entry = {"name": first.get("company") or det["slug"], "platform": det["platform"], "slug": det["slug"]}
        for k in ("tenant", "site", "dc"):
            if det.get(k):
                entry[k] = det[k]
        todo.append((entry, g["stubs"], det))
    results = parallel_map(lambda t: fetch(t[0]), todo)
    for (entry, stubs, det), (got, err) in zip(todo, results):
        first = stubs[0]
        g = {"stubs": stubs}
        if err or not got:
            if err:
                info["errors"].append({"company": entry["name"], "error": err})
            keep += g["stubs"]
            continue
        via = (first.get("source") or "").split(":", 1)[-1] or "board"
        for j in got:
            j["source"] = f'{det["platform"]} (via {via})'
            j.setdefault("industry", first.get("industry"))
        out += got
        info["discovered"].append(entry["name"])
        info["enriched"] += len(g["stubs"])
    return out + keep, info


def gather(demo: bool):
    """Return (all_jobs, errors, unresolved)."""
    if demo:
        with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as f:
            return json.load(f), [], []
    jobs, errors, unresolved = [], [], []
    known = set()
    registry = load_registry()
    for entry in registry:
        if entry.get("platform") not in (None, "", "resolve"):
            known.add((entry["platform"], entry.get("slug", "")))
    for entry, (got, err) in zip(registry, parallel_map(ats.fetch_company, registry)):
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

    # JB-3: second tier -- board SOURCES (aggregators) return many companies' jobs
    # at once, covering companies that aren't on an auto-probeable ATS.
    source_jobs = []
    src = sources.load_sources()
    for entry, (got, err) in zip(src, parallel_map(sources.fetch_source, src)):
        if err:
            errors.append({"company": entry["name"], "error": err})
        source_jobs += got
    # JB-5: follow apply links to each company's own ATS (full descriptions + every role)
    got, info = enrich_via_ats(source_jobs, known,
                               relevant=lambda j: jobfilter.classify(j)["verdict"] != "excluded",
                               in_region=lambda j: facets.country(j.get("location", "")) == "Canada")
    errors += info["errors"]
    LAST_DISCOVERY.update(info)
    for j in got:
        j["_reg_flags"] = []
        j["_ring"] = None                        # geo resolves ring from the real location
        j["_industry"] = j.get("industry") or "other"
        j["_sponsors"] = None
    jobs += got
    return jobs, errors, unresolved


def _defaults(j):
    j.setdefault("_reg_flags", [])
    j.setdefault("_industry", "other")
    j.setdefault("_sponsors", None)
    return j


def source_funnel(classified):
    """JB-30a: per-source funnel. classified = list of (job, classify_result), after dedupe.
    Returns {source: {"fetched": n, "kept": n, "excluded": {reason_key: n}}}.
    reason_key = first reason, text before any ":" or "(", stripped; none -> "unspecified"."""
    out = {}
    for job, res in classified:
        src = job.get("source") or "unknown"
        s = out.setdefault(src, {"fetched": 0, "kept": 0, "excluded": {}})
        s["fetched"] += 1
        if res.get("verdict") != "excluded":
            s["kept"] += 1
            continue
        reasons = res.get("reasons") or []
        key = reasons[0].split(":")[0].split("(")[0].strip() if reasons else ""
        key = key or "unspecified"
        s["excluded"][key] = s["excluded"].get(key, 0) + 1
    return out


def dedupe(jobs):
    seen, out = set(), []
    for j in jobs:
        key = (j.get("company", "").lower(), j.get("title", "").lower(), j.get("location", "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


PER_COMPANY_CAP = 8   # JB-20: no single employer may flood the board


def cap_per_company(rows, n=PER_COMPANY_CAP):
    """Keep at most n roles per company (highest score first).

    Returns (kept_rows, dropped_count). Prevents one big employer (e.g. Tenstorrent,
    Geotab) from dominating the board — keeps their best-matched n and trims the rest.
    """
    by_co = {}
    for r in sorted(rows, key=lambda r: -r["score"]):
        by_co.setdefault(r["company"], []).append(r)
    kept, dropped = [], 0
    for rs in by_co.values():
        kept += rs[:n]
        dropped += max(0, len(rs) - n)
    return kept, dropped


def build(demo=False, min_score=jobfilter.REPORT_THRESHOLD):
    import time as _time
    _t0 = _time.monotonic()
    home, person, initials = load_home()
    raw, errors, unresolved = gather(demo)
    raw = [ _defaults(j) for j in dedupe(raw) ]
    rows = []
    classified = []
    for j in raw:
        res = jobfilter.classify(j, extra_flags=j.get("_reg_flags"))
        classified.append((j, res))
        if res["verdict"] == "excluded":
            continue
        near = geo.nearest_location(home, j.get("location", ""))   # JB-34
        ring, km, is_remote = geo.ring_for(home, j.get("location", ""))
        if ring is None:
            ring = j.get("_ring")   # registry ring only when geo can't resolve (Canadian unknown city)
        # JB-3: sources can supply exact coords + arrangement directly; fall back otherwise
        lat, lng = j.get("lat"), j.get("lng")
        if lat is None or lng is None:
            lat, lng = geo.coords_of(near)   # for the map (JB-26); nearest part (JB-34)
        arrangement = j.get("arrangement") or facets.arrangement(j.get("location", ""), j.get("description", ""))
        country = facets.country(near)
        industry = facets.industry(j.get("_industry", ""), j.get("description", ""))
        sponsor = facets.sponsorship(j.get("description", ""), j.get("_sponsors"))
        snippet = (j.get("description") or "").strip().replace("\n", " ")
        snippet = (snippet[:180] + "\u2026") if len(snippet) > 180 else snippet
        full = (j.get("title","") + ". " + (j.get("description") or "")).replace("\n", " ")
        full = full[:1500]
        row = {
            "company": j["company"], "title": j["title"], "location": j["location"],
            "location_near": near, "n_locations": max(1, len(geo.split_locations(j.get("location", "")))),
            "url": j["url"], "posted": j.get("posted"), "source": j.get("source"),
            "salary": j.get("salary") or facets.salary_from_text(j.get("description") or ""), "ring": ring, "km": km, "lat": lat, "lng": lng,
            "score": res["score"], "flags": res["flags"],
            "arrangement": arrangement, "country": country,
            "industry": industry, "sponsorship": sponsor,
            "reasons": res["reasons"], "matched": res["matched"], "snippet": snippet,
            "text": full,
        }
        rows.append(row)
    # JB-22: keep ALL roles in the data — the per-company cap is now a filter the
    # user controls on the board (default top-N/company, or "All"), not a hard drop.
    matches = [r for r in rows if r["score"] >= min_score]
    below = [r for r in rows if r["score"] < min_score]

    def opts(key):
        return sorted({r.get(key) for r in (matches + below) if r.get(key) and r.get(key) != "?"})
    facet_opts = {"arrangement": opts("arrangement"), "country": opts("country"),
                  "industry": opts("industry"), "sponsorship": opts("sponsorship")}
    matches.sort(key=lambda r: (-r["score"], r.get("ring") if r.get("ring") is not None else 9))
    below.sort(key=lambda r: -r["score"])

    # JB-26: company map — every registry company placed, coloured by hiring status
    strong, anyc = {}, {}
    for r in (matches + below):
        anyc[r["company"]] = anyc.get(r["company"], 0) + 1
        if r["score"] >= 7:
            strong[r["company"]] = strong.get(r["company"], 0) + 1
    companies_map = []
    for e in load_registry():
        lat, lng = geo.coords_of(e.get("city", ""))
        if lat is None:
            continue
        resolved = e.get("platform") not in (None, "", "resolve")
        s, a = strong.get(e["name"], 0), anyc.get(e["name"], 0)
        status = "fit" if s else ("open" if a else ("none" if resolved else "unknown"))
        companies_map.append({
            "name": e["name"], "city": e.get("city", ""), "lat": lat, "lng": lng,
            "industry": e.get("industry", "other"), "resolved": resolved,
            "roles": a, "fit_roles": s, "status": status, "careers_url": e.get("careers_url", ""),
        })

    # JB-3: also place every SOURCE-DISCOVERED company (not in the curated registry)
    # so the map/directory lists *all* companies seen this run -- refreshed every build.
    reg_names = {e["name"].strip().lower() for e in load_registry()}
    placed = {c["name"].strip().lower() for c in companies_map}
    for r in (matches + below):
        key = r["company"].strip().lower()
        if key in reg_names or key in placed or r.get("lat") is None:
            continue
        placed.add(key)
        s, a = strong.get(r["company"], 0), anyc.get(r["company"], 0)
        companies_map.append({
            "name": r["company"], "city": r.get("location", ""),
            "lat": r["lat"], "lng": r["lng"],
            "industry": r.get("industry", "other"), "resolved": True,
            "roles": a, "fit_roles": s,
            "status": "fit" if s else "open",
            "careers_url": r.get("url", ""), "discovered": True,
        })

    os.makedirs(DATA, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "mode": "demo" if demo else "live",
        "person": person, "initials": initials, "home": home,
        "home_coords": list(geo.coords_of(home)) if geo.coords_of(home)[0] else None,
        "flag_legend": FLAG_LEGEND,
        "facets": facet_opts,
        "min_score": min_score,
        "default_per_company": PER_COMPANY_CAP,   # board's default per-company view cap
        "counts": {"matches": len(matches), "below": len(below),
                   "errors": len(errors), "unresolved": len(unresolved)},
        "source_funnel": source_funnel(classified),
        "run_seconds": round(_time.monotonic() - _t0, 1),   # JB-41: compare run times
        "discovery": {"companies": sorted(LAST_DISCOVERY["discovered"]),
                      "count": len(LAST_DISCOVERY["discovered"]),
                      "stubs_replaced": LAST_DISCOVERY["enriched"]},
        "matches": matches,
        "below": below,
        "companies": companies_map,
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
          f"{len(unresolved)} ATS to resolve. -> site/data/jobs.json")
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
