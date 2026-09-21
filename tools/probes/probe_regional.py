"""Probe (JB-39): how many companies can daily regional discovery find?
Pages through ALL jobs on each Getro board, counts distinct companies, how many are
in Ontario, and how many post through an ATS the board can already read.
Run:  python tools/probes/probe_regional.py   -> paste the summary. Diagnostic tool, kept in the repo."""
import sys, os, collections, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "engine"))
import ats_detect

H = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
BOARDS = {"Communitech (628)": 628, "MaRS (383)": 383, "Communitech partners (8936)": 8936}
ONTARIO = ("ontario", ", on", "toronto", "waterloo", "kitchener", "ottawa", "london", "mississauga",
           "markham", "cambridge", "guelph", "hamilton", "burlington", "oakville", "vaughan", "kanata")

all_cos = {}
for name, cid in BOARDS.items():
    cos, page, total = {}, 0, None
    while page < 400:
        try:
            r = requests.post(f"https://api.getro.com/api/v2/collections/{cid}/search/jobs", headers=H,
                              json={"hitsPerPage": 100, "page": page, "query": ""}, timeout=30)
            d = r.json().get("results") or {}
        except Exception as e:
            print(name, "page", page, "ERR", e); break
        total = d.get("count")
        jobs = d.get("jobs") or []
        for j in jobs:
            org = ((j.get("organization") or {}).get("name") or "?").strip()
            locs = " | ".join(j.get("searchable_locations") or []).lower()
            det = ats_detect.detect_ats(j.get("url") or "")
            c = cos.setdefault(org, {"jobs": 0, "ontario": 0, "ats": collections.Counter()})
            c["jobs"] += 1
            c["ontario"] += any(k in locs for k in ONTARIO)
            c["ats"][(det["platform"] + ("" if det["supported"] else "*")) if det else "other"] += 1
        if page == 0:
            print(f"  [{name}] page size returned: {len(jobs)} (asked for 100), total {total}")
        seen = sum(v["jobs"] for v in cos.values())
        if not jobs or (total and seen >= total):
            break
        page += 1
    on = {k: v for k, v in cos.items() if v["ontario"]}
    readable = {k: v for k, v in on.items() if any(not p.endswith("*") and p != "other" for p in v["ats"])}
    plat = collections.Counter()
    for v in on.values():
        plat[v["ats"].most_common(1)[0][0]] += 1
    print(f"\n=== {name}: {total} jobs, fetched pages {page+1}")
    print(f"companies total: {len(cos)} | with Ontario jobs: {len(on)} | Ontario + readable ATS: {len(readable)}")
    print("Ontario companies by ATS (* = no adapter yet):", dict(plat.most_common(15)))
    all_cos.update({k: v for k, v in on.items()})

print(f"\n=== ALL BOARDS: distinct Ontario companies {len(all_cos)}")
