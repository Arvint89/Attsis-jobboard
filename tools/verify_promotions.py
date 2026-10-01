"""Live verification of the resolve->real-ATS promotions.

Reads engine/companies.json, filters to the companies promoted from
platform:"resolve" to a real ATS across JB-5 batch 1 (#125) and JB-60 batch 2
(#144), calls each fetcher against the real portal, and prints a per-company
diagnostic. Sandbox blocks the outbound calls, so this is meant to run in CI
(verify-promotions.yml, workflow_dispatch) on main -- job-sweep.yml checks out
`production` and can't be used to test main-only work.

Exit code is always 0 -- the point is to surface data, not to fail the run.
Read the log; if a company returns 0 jobs, the resolver-guessed slug is wrong
and the entry needs a manual correction (or revert to `resolve`).
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))

import ats  # noqa: E402

PROMOTED = {
    # JB-5 batch 1 (#125)
    "BOS Innovations",
    "Nicoya Lifesciences",
    "Voltera",
    "eleven-x",
    "Kraken Robotics",
    "Semtech",
    "Littelfuse",
    "Corinex",
    "Digital Extremes",
    "Big Viking Games",
    "Manitoulin Transport",
    # JB-60 batch 2 (#144)
    "1Password",
    "Wealthsimple",
    "Tulip Retail",
    "Deep Genomics",
    "Plusgrade",
    "Plooto",
    "Rewind",
    "Flipp",
    "KOHO",
    "Athennian",
}


def main() -> int:
    with open(os.path.join(ROOT, "engine", "companies.json"), encoding="utf-8") as f:
        registry = json.load(f)

    targets = [c for c in registry["companies"] if c["name"] in PROMOTED]
    print(f"Checking {len(targets)} JB-5 batch 1 promotions against live portals\n")

    ok = []
    empty = []
    errored = []

    for c in targets:
        name = c["name"]
        platform = c["platform"]
        slug = c.get("slug", "")
        print(f"=== {name}")
        print(f"    platform={platform}  slug={slug!r}")
        jobs, err = ats.fetch_company(c)
        print(f"    -> {len(jobs)} jobs, err={err}")
        for j in jobs[:3]:
            print(f"       - {j['title']} @ {j['location']}")
        if err:
            errored.append((name, platform, err))
        elif not jobs:
            empty.append((name, platform))
            print("    HINT: 0 jobs + no error -- resolver-guessed slug likely wrong; "
                  "consider reverting to platform:'resolve' with a note")
        else:
            ok.append((name, platform, len(jobs)))
        print()

    print("=== SUMMARY")
    print(f"  OK (>=1 job):    {len(ok)}")
    print(f"  Empty (0 jobs):  {len(empty)}")
    print(f"  Errored:         {len(errored)}")
    if ok:
        print("\n  Working:")
        for name, plat, n in ok:
            print(f"    - {name} ({plat}): {n} jobs")
    if empty:
        print("\n  Empty -- likely wrong slug:")
        for name, plat in empty:
            print(f"    - {name} ({plat})")
    if errored:
        print("\n  Errored:")
        for name, plat, err in errored:
            print(f"    - {name} ({plat}): {err}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
