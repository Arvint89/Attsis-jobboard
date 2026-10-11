"""sweep_gate.py -- JB-83: make sweep regressions loud.

engine/history.py check_regression() already writes `alerts` into jobs.json, but the
sweep only printed them as ::warning:: annotations, so a broken sweep deployed silently.

  python tools/sweep_gate.py site/data/jobs.json --block-severe   # before deploy
  python tools/sweep_gate.py site/data/jobs.json --report         # after deploy

--block-severe  exit 1 when a SEVERE alert fired (total roles or companies-with-roles
                fell >30%), so the deploy step never runs and yesterday's data stays live.
                ALLOW_REGRESSION=true (manual run input) lets an intended drop through.
--report        print every REGRESSION as ::error:: + into the job summary; exit 1 if any, so
                the run is marked failed and GitHub emails the owner. Informational notices
                (AUTO-PROMOTE ...) are listed in the summary but never fail. Runs after deploy.
"""
from __future__ import annotations

import json
import os
import re
import sys

SEVERE_PREFIXES = ("roles kept fell", "companies with roles fell")
# Only these shapes (engine/history.py check_regression) are regressions. jobs.json `alerts`
# ALSO carries informational notices -- e.g. ~200 "AUTO-PROMOTE: '<co>' seen in N sweeps"
# lines (discovered companies worth adding to the registry). Those must never fail a run.
_REGRESSION = re.compile(r" fell \d| rose \d|went from \d+ kept roles to 0")


def split(alerts: list) -> tuple[list, list, list]:
    """-> (severe, regressions_other, info)."""
    regs = [a for a in alerts if _REGRESSION.search(a)]
    severe = [a for a in regs if a.startswith(SEVERE_PREFIXES)]
    other = [a for a in regs if a not in severe]
    info = [a for a in alerts if a not in regs]
    return severe, other, info


def classify(alerts: list) -> tuple[list, list]:
    severe, other, _ = split(alerts)
    return severe, other


def _summary(lines: list) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: list) -> int:
    if len(argv) < 2 or argv[1] not in ("--block-severe", "--report"):
        print(__doc__)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("mode") != "live":
        print("sweep_gate: not a live build; nothing to check")
        return 0
    alerts = list(payload.get("alerts") or [])
    severe, other, info = split(alerts)
    if argv[1] == "--block-severe":
        if not severe:
            print("sweep_gate: no severe regression")
            return 0
        allow = os.environ.get("ALLOW_REGRESSION", "").lower() == "true"
        for a in severe:
            print(f"::error title=Sweep regression::{a}")
        _summary(["### Sweep health: severe regression", *[f"- {a}" for a in severe],
                  "", "Deploy " + ("ALLOWED by ALLOW_REGRESSION=true." if allow else
                                   "BLOCKED: yesterday's data stays live. Re-run manually with "
                                   "allow_regression=true if the drop is intended.")])
        return 0 if allow else 1
    # --report
    info_lines = ([f"", f"{len(info)} informational notice(s) (not failures), first 10:", *[f"- {a}" for a in info[:10]]]
                  if info else [])
    regs = severe + other
    if not regs:
        _summary(["### Sweep health: OK (no regressions)", *info_lines])
        print(f"sweep_gate: healthy ({len(info)} informational notices)")
        return 0
    for a in regs:
        print(f"::error title=Sweep health::{a}")
    _summary(["### Sweep health: regressions", *[f"- {a}" for a in regs], *info_lines])
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
