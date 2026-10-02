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
import history
import resolver as _resolver
import discovered as _discovered
from company_key import company_key

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
LAST_RESOLVER = {"stats": None, "cache": None}   # JB-43: exposed to build() for meta + save
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


def enrich_via_ats(source_jobs, known, fetch=None, max_new=MAX_NEW_COMPANIES, relevant=None, in_region=None,
                   resolver=None):
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
    resolver:    optional resolver.Resolver. For stubs whose URL has no detectable ATS, try to
                 discover one by fetching the careers page (JB-43). Promoted like directly-detected.
    Returns (jobs, info) with info = {"discovered": [names], "enriched": n_stubs_replaced, "errors": [...],
                                      "resolver_stats": dict or None}.
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
    if resolver is not None and keep:
        by_company, remaining = {}, []
        for j in keep:
            if ats_detect.detect_ats(j.get("url") or "") is None:
                by_company.setdefault(j.get("company") or "", []).append(j)
            else:
                remaining.append(j)
        keep = remaining
        for company, stubs in by_company.items():
            det = resolver.resolve(stubs[0].get("url") or "") if company else None
            if det and det.get("supported"):
                key = (det["platform"], det["slug"])
                groups.setdefault(key, {"det": det, "stubs": []})["stubs"] += stubs
            else:
                keep += stubs
    out, info = [], {"discovered": [], "enriched": 0, "errors": [],
                     "resolver_stats": dict(resolver.stats) if resolver is not None else None}
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


def resolve_registry_entries(entries, resolver):
    """JB-43: for platform:'resolve' registry entries, sniff their careers_url and, on a
    supported detection, return a copy carrying the detected platform/slug (ready for
    ats.fetch_company). Returns (promoted, still_unresolved).
    """
    promoted, still_unresolved = [], []
    for entry in entries:
        url = entry.get("careers_url") or ""
        det = resolver.resolve(url) if url else None
        if det and det.get("supported"):
            new_entry = dict(entry, platform=det["platform"], slug=det["slug"])
            for k in ("tenant", "site", "dc"):
                if det.get(k):
                    new_entry[k] = det[k]
            promoted.append(new_entry)
        else:
            still_unresolved.append(entry)
    return promoted, still_unresolved


def gather(demo: bool):
    """Return (all_jobs, errors, unresolved)."""
    import time as _time
    LAST_RESOLVER["stats"] = None
    LAST_RESOLVER["cache"] = None
    if demo:
        with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as f:
            return json.load(f), [], []
    jobs, errors, unresolved = [], [], []
    known = set()
    # JB-43: one resolver, shared across registry-resolve + aggregator enrich phases,
    # so cache + max_lookups cap are unified.
    _r = _resolver.Resolver(cache=_resolver.load_cache())
    registry = load_registry()
    for entry in registry:
        if entry.get("platform") not in (None, "", "resolve"):
            known.add((entry["platform"], entry.get("slug", "")))
    # JB-62: per-phase stdout so CI logs name the culprit when gather() hangs. Flush each
    # line because stdout is block-buffered under GHA until the process exits.
    def _say(msg):
        print(msg, flush=True)
    _say(f"[gather] registry: {len(registry)} entries ({sum(1 for e in registry if e.get('platform') == 'resolve')} to resolve)")
    _t_reg = _time.monotonic()
    for entry, (got, err) in zip(registry, parallel_map(ats.fetch_company, registry)):
        if err == "unresolved":
            unresolved.append(entry)
        elif err:
            errors.append({"company": entry["name"], "error": err})
        # attach registry flags so the classifier can carry them through
        for j in got:
            j["_reg_flags"] = entry.get("flags", [])
            j["_ring"] = entry.get("ring")
            j["_reg_city"] = entry.get("city")   # JB-56: per-viewer ring fallback (registry.ring is BT-baked)
            j["_industry"] = entry.get("industry", "other")
            j["_sponsors"] = entry.get("sponsors")
        jobs += got
    _say(f"[gather] registry fetch done in {_time.monotonic()-_t_reg:.1f}s "
         f"-> {len(jobs)} jobs, {len(errors)} errors, {len(unresolved)} unresolved")

    # JB-43: try to resolve registry entries whose platform is 'resolve' (sniff careers_url).
    _t_resolve = _time.monotonic()
    promoted, unresolved = resolve_registry_entries(unresolved, _r)
    _say(f"[gather] resolver sniffed {len(unresolved)+len(promoted)} careers pages in "
         f"{_time.monotonic()-_t_resolve:.1f}s -> {len(promoted)} promoted, {len(unresolved)} still unresolved "
         f"(cached={_r.stats['cached']} fetched={_r.stats['fetched']} failed={_r.stats['failed']} "
         f"capped={_r.stats['skipped_cap']})")
    _t_prom = _time.monotonic()
    for entry, (got, err) in zip(promoted, parallel_map(ats.fetch_company, promoted)):
        if err:
            errors.append({"company": entry["name"], "error": err})
        for j in got:
            j["_reg_flags"] = entry.get("flags", [])
            j["_ring"] = entry.get("ring")
            j["_reg_city"] = entry.get("city")   # JB-56
            j["_industry"] = entry.get("industry", "other")
            j["_sponsors"] = entry.get("sponsors")
        jobs += got
        known.add((entry["platform"], entry.get("slug", "")))
    _say(f"[gather] promoted-resolve fetch done in {_time.monotonic()-_t_prom:.1f}s "
         f"-> {len(jobs)} jobs cumulative")

    # JB-3: second tier -- board SOURCES (aggregators) return many companies' jobs
    # at once, covering companies that aren't on an auto-probeable ATS.
    source_jobs = []
    src = sources.load_sources()
    _say(f"[gather] sources: {len(src)} boards ({', '.join(s.get('name','?') for s in src)})")
    _t_src = _time.monotonic()
    for entry, (got, err) in zip(src, parallel_map(sources.fetch_source, src)):
        if err:
            errors.append({"company": entry["name"], "error": err})
        _say(f"[gather]   {entry.get('name','?')}: {len(got)} jobs"
             + (f"  ERR: {err}" if err else ""))
        source_jobs += got
    _say(f"[gather] sources fetch done in {_time.monotonic()-_t_src:.1f}s "
         f"-> {len(source_jobs)} source jobs")
    # JB-5: follow apply links to each company's own ATS (full descriptions + every role)
    # JB-43: resolver fetches the careers page once when the aggregator link has no detectable ATS
    _t_enrich = _time.monotonic()
    got, info = enrich_via_ats(source_jobs, known,
                               relevant=lambda j: jobfilter.classify(j)["verdict"] != "excluded",
                               in_region=lambda j: facets.country(j.get("location", "")) == "Canada",
                               resolver=_r)
    _say(f"[gather] enrich_via_ats done in {_time.monotonic()-_t_enrich:.1f}s "
         f"-> discovered {len(info['discovered'])} new companies, {info['enriched']} stubs replaced, "
         f"{len(got)} jobs after enrich")
    errors += info["errors"]
    LAST_DISCOVERY.update(info)
    # JB-56: cross-reference discovered jobs against the registry by name so that
    # shared-tenant Workday postings (e.g. Halma hosts DeepTrekker + siblings; the
    # ATS returns them all stamped with one name) still fall back to the correct
    # registered HQ city when the job's own location string is ambiguous.
    reg_by_name = {e["name"].strip().lower(): e for e in registry}
    for j in got:
        match = reg_by_name.get((j.get("company") or "").strip().lower())
        j["_reg_flags"] = match.get("flags", []) if match else []
        j["_ring"] = None                        # geo resolves ring from the real location
        j["_reg_city"] = match.get("city") if match else None
        j["_industry"] = (match.get("industry") if match else j.get("industry")) or "other"
        j["_sponsors"] = match.get("sponsors") if match else None
        j["_discovered"] = True                  # JB-55: fed to discovered.record()
    jobs += got
    LAST_RESOLVER["stats"] = dict(_r.stats)
    LAST_RESOLVER["cache"] = dict(_r.cache)
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
    """JB-55: dedupe by canonicalized company (so "Fidus Systems Inc." and "Fidus Systems"
    don't count as two roles) + normalized title/location."""
    seen, out = set(), []
    for j in jobs:
        key = (company_key(j.get("company", "")),
               j.get("title", "").strip().lower(),
               j.get("location", "").strip().lower())
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
    # JB-64: per-phase stdout for the post-gather half of build() so CI logs name
    # the slow phase. gather() already logs its own phases (JB-62); this covers
    # the ~15min tail that was invisible between enrich_via_ats finishing and the
    # deploy step starting -- most of which is classify+geo over 5k jobs and the
    # standalone-HTML json.dumps of the whole payload.
    import time as _time
    _t0 = _time.monotonic()
    def _say(msg): print(msg, flush=True)
    home, person, initials = load_home()
    raw, errors, unresolved = gather(demo)
    _t = _time.monotonic()
    raw = [ _defaults(j) for j in dedupe(raw) ]
    _say(f"[build] dedupe+defaults: {_time.monotonic()-_t:.1f}s -> {len(raw)} jobs")
    _t = _time.monotonic()
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
            # JB-56: prefer the registered HQ city (per-viewer via home) over the
            # baked-in registry.ring, which was BT-specific. Ring is now derived
            # from wherever the viewer is + the registered city — same code path
            # scales to a multi-user product.
            reg_city = j.get("_reg_city")
            if reg_city:
                ring, km, _ = geo.ring_for(home, reg_city)
            if ring is None:
                ring = j.get("_ring")   # last-resort legacy hint (single-user era)
        # JB-3: sources can supply exact coords + arrangement directly; fall back otherwise
        lat, lng = j.get("lat"), j.get("lng")
        if lat is None or lng is None:
            lat, lng = geo.coords_of(near)   # for the map (JB-26); nearest part (JB-34)
            if (lat is None or lng is None) and j.get("_reg_city"):
                lat, lng = geo.coords_of(j["_reg_city"])   # JB-56: registered HQ as map fallback
        arrangement = j.get("arrangement") or facets.arrangement(j.get("location", ""), j.get("description", ""))
        country = facets.country(near)
        industry = facets.industry(j.get("_industry", ""), j.get("description", ""))
        sponsor = facets.sponsorship(j.get("description", ""), j.get("_sponsors"))
        snippet = (j.get("description") or "").strip().replace("\n", " ")
        snippet = (snippet[:180] + "\u2026") if len(snippet) > 180 else snippet
        # JB-69: text used to be 1500 chars (title + description) to let the browser
        # run DB_SKILLS regex against the full body. Now that tokens[] carries the
        # pre-matched DB hits, text only needs to hold enough for CV-only skills
        # that aren't in the canonical DB (user's custom keywords). 500 chars keeps
        # the strong first-paragraph of the JD, which is almost always where the
        # tech stack is listed. ~1 MB saved on 1688 jobs.
        full = (j.get("title","") + ". " + (j.get("description") or "")).replace("\n", " ")
        full = full[:500]
        row = {
            "company": j["company"], "title": j["title"], "location": j["location"],
            "location_near": near, "n_locations": max(1, len(geo.split_locations(j.get("location", "")))),
            "url": j["url"], "posted": j.get("posted"), "source": j.get("source"),
            "salary": j.get("salary") or facets.salary_from_text(j.get("description") or ""), "ring": ring, "km": km, "lat": lat, "lng": lng,
            "score": res["score"], "flags": res["flags"],
            "arrangement": arrangement, "country": country,
            "industry": industry, "sponsorship": sponsor,
            # JB-71: reasons[] + matched[] dropped from payload. Browser's scoreJob()
            # recomputes both per-user during rescore(). Server-shipped values were
            # only ever a brief flash of BT's-profile reasoning before the browser
            # stomped them. Saves ~15-20% of the payload.
            "explanation": jobfilter.score_explanation(res),   # JB-63: user-grade WHY
            # JB-69: pre-matched DB_TITLES + SKILL_CONFIRMERS so scoreJob() does
            # set intersection instead of ~1340 regex per job per rescore.
            "tokens": jobfilter.tokens_for(j),
            "snippet": snippet,
            "text": full,
        }
        rows.append(row)
    _say(f"[build] classify+geo+facets loop: {_time.monotonic()-_t:.1f}s -> {len(rows)} kept of {len(raw)}")
    _t = _time.monotonic()
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
    _say(f"[build] split+facets+sort: {_time.monotonic()-_t:.1f}s -> {len(matches)} matches, {len(below)} below")
    _t = _time.monotonic()

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
    # JB-55: match by canonicalized key so "Fidus Systems Inc." doesn't get re-placed
    # next to registry entry "Fidus Systems".
    reg_names = {company_key(e["name"]) for e in load_registry()}
    placed = {company_key(c["name"]) for c in companies_map}
    for r in (matches + below):
        key = company_key(r["company"])
        if not key or key in reg_names or key in placed or r.get("lat") is None:
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
    _say(f"[build] companies_map: {_time.monotonic()-_t:.1f}s -> {len(companies_map)} entries")
    _t = _time.monotonic()

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
        "resolver_stats": LAST_RESOLVER["stats"],   # JB-43: cached/fetched/found/failed/skipped_cap
        "matches": matches,
        "below": below,
        "companies": companies_map,
        "errors": errors,
    }
    # JB-42: compare with the previous live run; alerts ride along in jobs.json + Action log
    payload["alerts"] = history.record(payload, DATA, live=not demo)
    # JB-55: persist source-discovered companies across sweeps + auto-promote alerts.
    # Feeds from raw (post-dedupe) so companies whose only role was excluded still count.
    reg_keys = {company_key(e["name"]) for e in load_registry()}
    disc_jobs = [j for j in raw if j.get("_discovered")]
    _, promote_alerts = _discovered.record(disc_jobs, reg_keys, DATA, live=not demo)
    payload["alerts"] = list(payload["alerts"]) + promote_alerts
    _say(f"[build] payload+alerts: {_time.monotonic()-_t:.1f}s")
    _t = _time.monotonic()
    with open(os.path.join(DATA, "jobs.json"), "w", encoding="utf-8") as f:
        # JB-71: minified (no indent/whitespace). ~20-25% smaller for a file
        # no one reads by hand. resolve.json stays pretty-printed (it IS read
        # by hand during resolver debugging).
        json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(DATA, "resolve.json"), "w", encoding="utf-8") as f:
        json.dump(unresolved, f, indent=2, ensure_ascii=False)
    _say(f"[build] write jobs.json+resolve.json: {_time.monotonic()-_t:.1f}s")
    _t = _time.monotonic()
    # JB-50: publish the skills DB as a static asset so the browser scorer can
    # fetch it. Source of truth is <root>/data/skills.json.
    _skills_src = os.path.join(ROOT, "data", "skills.json")
    if os.path.exists(_skills_src):
        import shutil as _shutil
        _shutil.copyfile(_skills_src, os.path.join(DATA, "skills.json"))
    # JB-43: publish the resolver cache next to jobs.json so the next run can prime it
    # (like history.json — gitignored, refreshed each build).
    if LAST_RESOLVER["cache"] is not None:
        _resolver.save_cache(LAST_RESOLVER["cache"], DATA)

    # also emit a data-embedded standalone page (double-click offline, no server)
    tpl_path = os.path.join(ROOT, "site", "index.html")
    if os.path.exists(tpl_path):
        import re as _re
        tpl = open(tpl_path, encoding="utf-8").read()
        # JB-50: embed the skills DB so the standalone works fully offline
        skills_payload = {}
        if os.path.exists(_skills_src):
            with open(_skills_src, encoding="utf-8") as _sf:
                skills_payload = json.load(_sf)
        inline = (
            "<script>window.__EMBED__ = " + json.dumps(payload, ensure_ascii=False)
            + "; window.__EMBED_SKILLS__ = " + json.dumps(skills_payload, ensure_ascii=False)
            + ";</script>\n"
        )
        # replace both fetch bootstraps with the embedded-boot variant
        std = _re.sub(r"fetch\('\./data/jobs\.json.*?\}\);",
                      "bootWithSkills(window.__EMBED__);", tpl, flags=_re.S)
        std = std.replace("<script>", inline + "<script>", 1)
        with open(os.path.join(ROOT, "site", "board_standalone.html"), "w", encoding="utf-8") as f:
            f.write(std)
    _say(f"[build] standalone HTML + skills copy: {_time.monotonic()-_t:.1f}s "
         f"(total build: {_time.monotonic()-_t0:.1f}s)")

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
