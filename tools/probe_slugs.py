"""probe_slugs.py -- JB-5c: resolve 'platform: resolve' registry entries by probing public ATS APIs
with slugs derived from the company name.

  python tools/probe_slugs.py            # probe, write docs/status/SLUG_PROBE_<date>.md
  python tools/probe_slugs.py --apply    # also update the matched entries in engine/companies.json

Why: the JB-43 resolver sniffs each careers page for an ATS link. Many pages render their job
list with JavaScript, so the sniff finds nothing (55 entries still unresolved, 2026-10-13).
The public ATS APIs answer directly for a guessed slug.

Precision rules (a wrong match imports another company's jobs):
  * Greenhouse / SmartRecruiters return the board's company name -> it must be the same company
    (same_company: equal names, or equal before a " - " / "|" / "(" separator).
  * Lever / Ashby / Workable / BambooHR / JazzHR return no name -> the slug must be the company's
    FULL name (not a shortened form), and >= 50% of the jobs that name a place must be in Canada.
  * The board must return at least one job; more than --max-jobs goes to review, not --apply.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.dirname(__file__))
import ats  # noqa: E402
from promote_discovered import canada_share  # noqa: E402

# words dropped to form a short slug ("Synaptive Medical" -> "synaptive")
_SUFFIX = {"inc", "ltd", "limited", "corp", "corporation", "co", "company", "io", "hq", "group",
           "technologies", "technology", "tech", "medical", "biosciences", "software", "systems",
           "solutions", "international", "canada", "healthcare", "advanced", "the", "of", "and"}
_LEGAL = {"inc", "ltd", "limited", "corp", "corporation", "co", "company", "io", "hq", "the"}
NAMED_PLATFORMS = ("greenhouse", "smartrecruiters")
PLATFORMS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "bamboohr", "jazzhr")


def _words(name: str) -> list:
    return re.findall(r"[a-z0-9]+", (name or "").lower().replace("&", " and "))


def slug_candidates(name: str) -> list:
    w = _words(name)
    out = ["".join(w), "-".join(w)]
    core = [x for x in w if x not in _SUFFIX]
    if core and core != w and (len(core) > 1 or len(core[0]) >= 6):   # "vital" alone is too generic
        out += ["".join(core), "-".join(core)]
    legal = [x for x in w if x not in _LEGAL]
    if legal and legal != w:
        out.append("".join(legal))
    seen, res = set(), []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            res.append(s)
    return res


def _name_tokens(s: str) -> list:
    return [x for x in _words(s) if x not in _LEGAL and x not in {"solutions", "systems"}]


def same_company(company: str, board_name: str) -> bool:
    """Exact (normalized) name match, or match of the part before ' - ' / '|' / '('."""
    if not board_name:
        return False
    head = re.split(r"\s[-|–]\s|\(|\|", board_name)[0]
    want = _name_tokens(company)
    return bool(want) and (want == _name_tokens(board_name) or want == _name_tokens(head))


def _full_slugs(name: str) -> set:
    w = _words(name)
    legal = [x for x in w if x not in _LEGAL] or w
    return {"".join(w), "-".join(w), "".join(legal), "-".join(legal)}


def accept(company, platform, slug, board_name, jobs) -> bool:
    if not jobs:
        return False
    if platform in NAMED_PLATFORMS:
        return same_company(company, board_name)
    return slug.lower() in _full_slugs(company) and canada_share(jobs) >= 0.5


def _board_name(platform: str, slug: str, jobs: list):
    if platform == "greenhouse":
        try:
            return ats._get(f"https://boards-api.greenhouse.io/v1/boards/{slug}").json().get("name")
        except Exception:
            return None
    if platform == "smartrecruiters":
        try:
            d = ats._get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1").json()
            c = (d.get("content") or [{}])[0].get("company") or {}
            return c.get("name")
        except Exception:
            return None
    return None


def probe_one(entry: dict) -> dict:
    """Try every (platform, slug) for one company; return the first accepted hit, else misses."""
    name = entry["name"]
    tried, rejected = [], None
    for platform in PLATFORMS:
        for slug in slug_candidates(name):
            jobs, err = ats.fetch_company({"name": name, "platform": platform, "slug": slug})
            tried.append(f"{platform}/{slug}")
            if err or not jobs:
                continue
            bn = _board_name(platform, slug, jobs)
            if accept(name, platform, slug, bn, jobs):
                return {"name": name, "platform": platform, "slug": slug, "board_name": bn,
                        "jobs": len(jobs), "canada_share": canada_share(jobs)}
            rejected = rejected or {"name": name, "rejected": f"{platform}/{slug}", "board_name": bn,
                                    "jobs": len(jobs), "canada_share": canada_share(jobs)}
    return rejected or {"name": name, "miss": True, "tried": len(tried)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-jobs", type=int, default=150)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    reg_path = os.path.join(ROOT, "engine", "companies.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    regl = reg if isinstance(reg, list) else reg["companies"]
    todo = [c for c in regl if c.get("platform") in (None, "", "resolve") and not c.get("skip")]
    with ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(probe_one, todo))

    hits = [r for r in results if "platform" in r]
    big = [r for r in hits if r["jobs"] > a.max_jobs]
    ok = [r for r in hits if r["jobs"] <= a.max_jobs]
    rejected = [r for r in results if "rejected" in r]
    misses = [r for r in results if r.get("miss")]

    today = _dt.date.today().isoformat()
    lines = [f"# ATS slug probe — {today}", "",
             "Generated by `tools/probe_slugs.py` (JB-5c). ✅ = live-fetched from this machine today.", "",
             f"Probed {len(todo)} `platform: resolve` entries on {', '.join(PLATFORMS)}.", "",
             "| Outcome | Count |", "|---|---|",
             f"| resolved | {len(ok)} |", f"| resolved but big (review) | {len(big)} |",
             f"| board found but rejected (name / Canada check) | {len(rejected)} |", f"| no board found | {len(misses)} |", "",
             "## Resolved ✅", "", "| Company | Platform/slug | Board name | Jobs | Canada share |", "|---|---|---|---|---|"]
    lines += [f"| {r['name']} | {r['platform']}/{r['slug']} | {r['board_name'] or '—'} | {r['jobs']} | {r['canada_share']:.0%} |"
              for r in sorted(ok, key=lambda r: -r["jobs"])]
    lines += ["", f"## Big (> {a.max_jobs} jobs): review, not applied", ""]
    lines += [f"- {r['name']}: {r['platform']}/{r['slug']} ({r['jobs']} jobs, {r['canada_share']:.0%} Canada)" for r in big]
    lines += ["", "## Rejected (a board answered, but not provably this company)", ""]
    lines += [f"- {r['name']} → `{r['rejected']}` (board name: {r['board_name'] or '—'}, {r['jobs']} jobs, "
              f"{r['canada_share']:.0%} Canada)" for r in rejected]
    lines += ["", "## No board found", "", ", ".join(r["name"] for r in misses), ""]
    os.makedirs(os.path.join(ROOT, "docs", "status"), exist_ok=True)
    out = os.path.join(ROOT, "docs", "status", f"SLUG_PROBE_{today}.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print({"resolved": len(ok), "big": len(big), "rejected": len(rejected), "miss": len(misses)}, "->", out)

    if a.apply and ok:
        by = {r["name"]: r for r in ok}
        for c in regl:
            r = by.get(c["name"])
            if r and c.get("platform") in (None, "", "resolve"):
                c["platform"], c["slug"] = r["platform"], r["slug"]
                c["careers_url"] = ats.board_url(c) or c.get("careers_url", "")
                c["flags"] = sorted(set((c.get("flags") or []) + ["slug-probed"]))
        with open(reg_path, "w", encoding="utf-8", newline="") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated {len(ok)} entries in engine/companies.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
