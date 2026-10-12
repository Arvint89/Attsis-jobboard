"""promote_discovered.py -- JB-86: turn AUTO-PROMOTE notices into verified registry entries.

  python tools/promote_discovered.py                 # read live jobs.json, verify, write report
  python tools/promote_discovered.py --apply         # also append verified entries to engine/companies.json
  python tools/promote_discovered.py --file site/data/jobs.json

Each sweep lists companies seen via aggregators (Getro/LEDC) that aren't in the registry
("AUTO-PROMOTE: 'X' seen in N sweeps via ... (sample: <job url>)"). For each one:
  1. detect the ATS + slug from the sample URL (engine/ats_detect.detect_ats)
  2. REJECT when the slug doesn't look like the company (the sample often points at a
     PARENT or acquirer's board: Clearpath -> rockwellautomation, Algolux -> torcrobotics),
     because promoting it would import the parent's whole global job list
  3. LIVE-FETCH the board (engine/ats.fetch_company); keep only boards that return jobs
  4. city / industry come from that company's roles already on the board
Output: docs/status/PROMOTION_<date>.md (+ engine/companies.json with --apply).
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "engine"))
import ats  # noqa: E402
import ats_detect  # noqa: E402
import geo  # noqa: E402

RX = re.compile(r"AUTO-PROMOTE: '(.+?)' seen in (\d+) sweeps via (.+?) -- add to engine/companies.json \(sample: (.+)\)$")
_STOP = {"inc", "ltd", "limited", "corp", "corporation", "company", "co", "the", "group", "technologies",
         "technology", "systems", "solutions", "canada", "labs", "lab", "software", "ai", "and", "of"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def name_matches_slug(name: str, slug: str) -> bool:
    """True when the board slug plausibly belongs to this company (not a parent/acquirer)."""
    s = _norm(slug)
    if not s:
        return False
    words = [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in _STOP]
    if not words:
        return False
    full = "".join(words)
    if s in full or full in s:
        return True
    first = words[0]
    if len(first) >= 4 and (first in s or s.startswith(first[:4])):
        return True
    initials = "".join(w[0] for w in words)
    return len(initials) >= 3 and s.startswith(initials)


def parse_alerts(alerts: list) -> list:
    out = []
    for a in alerts or []:
        m = RX.match(a)
        if m:
            name, n, via, url = m.groups()
            out.append({"name": name, "sweeps": int(n), "via": via, "sample": url.strip()})
    return out


def _company_facts(pool: list, name: str) -> tuple[str, str, int]:
    rows = [j for j in pool if (j.get("company") or "").strip().lower() == name.strip().lower()]
    cities = collections.Counter((j.get("location_near") or "").split(",")[0].strip() for j in rows if j.get("location_near"))
    inds = collections.Counter(j.get("industry") for j in rows if j.get("industry") and j.get("industry") != "other")
    city = cities.most_common(1)[0][0] if cities else ""
    return city, (inds.most_common(1)[0][0] if inds else "other"), len(rows)


def build_entry(cand: dict, det: dict, pool: list) -> dict:
    city, industry, _ = _company_facts(pool, cand["name"])
    if city and geo.coords_of(city)[0] is None and geo.home_coords(city)[0] is None:
        city = ""   # "Remote", "North America", "Canada"... aren't places; leave the HQ city unknown
    ring, _, _ = geo.ring_for("London", city) if city else (None, None, None)
    e = {"name": cand["name"], "ring": ring if ring is not None else 4, "platform": det["platform"], "slug": det.get("slug", ""),
         "careers_url": cand["sample"].split("?")[0], "flags": ["auto-promoted"], "industry": industry,
         "sponsors": None, "city": city}
    for k in ("tenant", "site", "dc"):
        if det.get(k):
            e[k] = det[k]
    return e


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-sweeps", type=int, default=3)
    ap.add_argument("--min-canada", type=float, default=0.5, help="share of the company's on-board roles in Canada")
    ap.add_argument("--max-jobs", type=int, default=150, help="bigger boards go to review instead of auto-add")
    a = ap.parse_args(argv)
    if a.file:
        payload = json.load(open(a.file, encoding="utf-8"))
    else:
        import requests
        payload = requests.get("https://arvint89.github.io/Attsis-jobboard/data/jobs.json", timeout=60).json()
    pool = (payload.get("matches") or []) + (payload.get("below") or [])
    reg_path = os.path.join(ROOT, "engine", "companies.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    regl = reg if isinstance(reg, list) else reg["companies"]
    have = {_norm(c.get("name")) for c in regl}

    rows = {"added": [], "review_big_or_foreign": [], "parent_board": [], "unsupported": [], "fetch_failed": [], "already": []}
    for c in parse_alerts(payload.get("alerts")):
        if c["sweeps"] < a.min_sweeps:
            continue
        if _norm(c["name"]) in have:
            rows["already"].append(c); continue
        det = ats_detect.detect_ats(c["sample"])
        if not det or det.get("platform") not in ats.FETCHERS:
            rows["unsupported"].append(c); continue
        if not name_matches_slug(c["name"], det.get("slug", "") or det.get("tenant", "")):
            rows["parent_board"].append({**c, "slug": det.get("slug") or det.get("tenant")}); continue
        entry = build_entry(c, det, pool)
        jobs, err = ats.fetch_company(entry)
        if err or not jobs:
            rows["fetch_failed"].append({**c, "err": err or "0 jobs"}); continue
        _, _, on_board = _company_facts(pool, c["name"])
        mine = [j for j in pool if (j.get("company") or "").strip().lower() == c["name"].strip().lower()]
        ca = sum(1 for j in mine if j.get("country") == "Canada") / len(mine) if mine else 0.0
        row = {**c, "entry": entry, "fetched": len(jobs), "on_board_now": on_board, "canada_share": round(ca, 2)}
        # Relevance guard: a Canadian-focused board, and not a giant global board that would bloat
        # the pool (e.g. Rippling 612 jobs mostly Bangalore; Georgia.gov). Those go to review.
        if ca < a.min_canada or len(jobs) > a.max_jobs:
            rows["review_big_or_foreign"].append(row); continue
        rows["added"].append(row)

    today = _dt.date.today().isoformat()
    lines = [f"# Registry promotion report — {today}", "",
             "Generated by `tools/promote_discovered.py` (JB-86). ✅ = live-fetched from this machine today.", "",
             f"| Outcome | Count |", "|---|---|"] + [f"| {k} | {len(v)} |" for k, v in rows.items()] + [""]
    lines += ["## Added (live board returned jobs)", "", "| Company | Platform/slug | City | Sweeps seen | Jobs on own board ✅ | Roles on our board now |", "|---|---|---|---|---|---|"]
    for r in sorted(rows["added"], key=lambda r: -r["fetched"]):
        e = r["entry"]
        lines.append(f"| {r['name']} | {e['platform']}/{e['slug']} | {e['city'] or '?'} | {r['sweeps']} | {r['fetched']} | {r['on_board_now']} |")
    lines += ["", f"## Review: big (> {a.max_jobs} jobs) or mostly outside Canada (not promoted)", "",
              "| Company | Platform/slug | Jobs on own board ✅ | Canada share of our roles |", "|---|---|---|---|"]
    for r in sorted(rows["review_big_or_foreign"], key=lambda r: -r["fetched"]):
        lines.append(f"| {r['name']} | {r['entry']['platform']}/{r['entry']['slug']} | {r['fetched']} | {r['canada_share']:.0%} |")
    lines += ["", f"Added total: {sum(r['fetched'] for r in rows['added'])} jobs fetched from {len(rows['added'])} boards (before scoring/filters).", ""]
    lines += ["", "## Rejected: sample points at a parent/acquirer board (not promoted)", ""]
    lines += [f"- {r['name']} → `{r['slug']}`" for r in rows["parent_board"]]
    lines += ["", "## Fetch failed (not promoted)", ""] + [f"- {r['name']}: {r['err']}" for r in rows["fetch_failed"]]
    os.makedirs(os.path.join(ROOT, "docs", "status"), exist_ok=True)
    out = os.path.join(ROOT, "docs", "status", f"PROMOTION_{today}.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print({k: len(v) for k, v in rows.items()}, "->", out)

    if a.apply and rows["added"]:
        regl.extend(r["entry"] for r in rows["added"])
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"appended {len(rows['added'])} entries to engine/companies.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
