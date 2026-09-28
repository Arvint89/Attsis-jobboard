"""discovered.py -- JB-55: aggregator-discovered companies, persisted across sweeps.

Today: `engine/build_board.py:401` places source-discovered companies on the map,
but they never survive past the current run. If Communitech breaks tomorrow, all
that knowledge vanishes.

This module reads the previous `discovered_companies.json` (from the live site,
same pattern as history.py), merges in this run's discoveries, and emits an
AUTO-PROMOTE alert for any company seen in >=N sweeps that isn't in the registry.

Shape of the file (gitignored, refreshed each live run):
    {
      "<company_key>": {
        "last_name_seen": "Deep Trekker",
        "sources_seen": ["workday (via Communitech)"],
        "first_seen_iso": "2026-09-20T...",
        "last_seen_iso": "2026-09-26T...",
        "sweep_count": 3,
        "sample_url": "https://halma.wd3.myworkdayjobs.com/Halma/job/.../JR26_000795",
        "sample_city": "London"
      },
      ...
    }

Pure functions except load_previous(); failure-safe everywhere. No network in
build unless load_previous is called.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone

from company_key import company_key

DEFAULT_URL = os.getenv(
    "JB_DISCOVERED_URL",
    "https://arvint89.github.io/Attsis-jobboard/data/discovered_companies.json",
)
AUTO_PROMOTE_THRESHOLD = 3      # sweeps before an alert is emitted
MAX_SOURCES = 5                 # cap sources_seen (dedup by string, most-recent-last)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge(prev: dict, this_run: list, registry_keys: set, now: str | None = None) -> dict:
    """Fold this_run's discoveries into prev.

    this_run: list of dicts with at least {"company", "source", "url", "location"}.
    registry_keys: set of company_key() results for the registry; used to skip
    already-registered companies from the persistence file (keeps it small).
    Returns the new state dict keyed by company_key.
    """
    now = now or _now_iso()
    state = dict(prev or {})
    seen_this_run = set()
    for j in this_run:
        name = j.get("company") or ""
        key = company_key(name)
        if not key or key in registry_keys or key in seen_this_run:
            continue
        seen_this_run.add(key)
        entry = state.get(key) or {
            "last_name_seen": name,
            "sources_seen": [],
            "first_seen_iso": now,
            "last_seen_iso": now,
            "sweep_count": 0,
            "sample_url": "",
            "sample_city": "",
        }
        entry["last_name_seen"] = name
        entry["last_seen_iso"] = now
        entry["sweep_count"] = int(entry.get("sweep_count") or 0) + 1
        src = j.get("source") or ""
        if src and src not in entry["sources_seen"]:
            entry["sources_seen"] = (entry["sources_seen"] + [src])[-MAX_SOURCES:]
        if not entry.get("sample_url"):
            entry["sample_url"] = j.get("url") or ""
        if not entry.get("sample_city"):
            entry["sample_city"] = j.get("location") or ""
        state[key] = entry
    return state


def auto_promote_alerts(state: dict, threshold: int = AUTO_PROMOTE_THRESHOLD) -> list:
    """Emit one alert per company seen in >= threshold sweeps and not yet promoted.

    The alert is a short human-readable line the GitHub Actions log will surface
    and the site can render in the alerts panel. Once BT adds the company to the
    registry, the next merge() drops it from `state` (registry_keys filter), and
    the alert stops firing.
    """
    alerts = []
    for key, e in sorted(state.items()):
        if int(e.get("sweep_count") or 0) < threshold:
            continue
        name = e.get("last_name_seen") or key
        srcs = ", ".join(e.get("sources_seen", []) or [])
        alerts.append(
            f"AUTO-PROMOTE: {name!r} seen in {e['sweep_count']} sweeps via {srcs} "
            f"-- add to engine/companies.json (sample: {e.get('sample_url', '')})"
        )
    return alerts


def load_previous(fetch=None, url: str | None = None) -> dict:
    """Previous state from the live site; {} on any failure (first run, offline, bad JSON)."""
    try:
        if fetch is None:
            import requests
            fetch = lambda u: requests.get(u, timeout=20, headers={"Cache-Control": "no-cache"}).json()
        data = fetch(url or DEFAULT_URL)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def record(discovered_jobs: list, registry_keys: set, out_dir: str, live: bool,
           fetch=None) -> tuple[dict, list]:
    """Load previous state, merge, write to out_dir/discovered_companies.json.

    Demo runs (live=False) skip the network fetch and start from {}, so a demo
    build never mutates the published state. Returns (new_state, alerts).
    """
    prev = load_previous(fetch) if live else {}
    state = merge(prev, discovered_jobs, registry_keys)
    alerts = auto_promote_alerts(state)
    with open(os.path.join(out_dir, "discovered_companies.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
    for a in alerts:
        print(f"::warning title=Registry auto-promote candidate::{a}")
    return state, alerts
