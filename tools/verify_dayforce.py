"""Live verification of the Dayforce adapters (JB-47b-followup).

Reads engine/companies.json, filters to platform in {"dayforce",
"dayforce_shared"}, calls each fetcher against the real portal, and prints
a per-company diagnostic. Sandbox blocks the outbound calls, so this is
meant to run in CI (verify-dayforce.yml, workflow_dispatch) or on a
machine with network.

Exit code is always 0 -- the point is to surface data, not to fail the run.
Read the log; if a company returns 0 jobs, the subdomain or site id is
wrong and companies.json needs a correction.
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))

import ats  # noqa: E402

TARGET_PLATFORMS = ("dayforce", "dayforce_shared")


def main() -> int:
    with open(os.path.join(ROOT, "engine", "companies.json"), encoding="utf-8") as f:
        registry = json.load(f)

    targets = [c for c in registry["companies"] if c.get("platform") in TARGET_PLATFORMS]
    print(f"Checking {len(targets)} Dayforce entries against live portals\n")

    for c in targets:
        name = c["name"]
        platform = c["platform"]
        slug = c.get("slug", "")
        site = c.get("site", "")
        print(f"=== {name}")
        print(f"    platform={platform}  slug={slug!r}  site={site!r}")
        jobs, err = ats.fetch_company(c)
        print(f"    -> {len(jobs)} jobs, err={err}")
        for j in jobs[:3]:
            print(f"       - {j['title']} @ {j['location']}")
        if not jobs and not err:
            print("    HINT: 0 jobs + no error usually means the subdomain "
                  "resolves and returned an empty list -- check the slug/site "
                  "against the portal URL.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
