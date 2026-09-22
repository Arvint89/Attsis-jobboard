"""history.py -- JB-42: run history + regression alarm.

Each live run appends a one-line summary to site/data/history.json. The previous history is
read back from the live site (the Action never commits data), so no git writes are needed.
check_regression() compares this run with the previous one and returns human-readable alerts.
Pure functions except load_previous(); failure-safe everywhere.
"""
from __future__ import annotations
import json
import os

HISTORY_URL = os.getenv("JB_HISTORY_URL",
                        "https://arvint89.github.io/Attsis-jobboard/data/history.json")
KEEP = 180            # entries kept (~6 months of weekday runs + pushes)


def summarize(payload: dict) -> dict:
    """One compact history entry from a jobs.json payload."""
    c = payload.get("counts", {})
    funnel = payload.get("source_funnel", {}) or {}
    return {
        "generated": payload.get("generated"),
        "mode": payload.get("mode"),
        "kept": c.get("matches", 0) + c.get("below", 0),
        "matches": c.get("matches", 0),
        "errors": c.get("errors", 0),
        "unresolved": c.get("unresolved", 0),
        "discovered": (payload.get("discovery") or {}).get("count", 0),
        "run_seconds": payload.get("run_seconds"),
        "kept_by_source": {k: v.get("kept", 0) for k, v in sorted(funnel.items())},
        "companies_with_roles": len({r.get("company") for r in payload.get("matches", []) + payload.get("below", [])}),
    }


def check_regression(prev: dict | None, cur: dict, drop: float = 0.30) -> list:
    """Alerts when this run looks worse than the last. Empty list = healthy."""
    if not prev:
        return []
    alerts = []

    def fell(key, label, floor=5):
        p, n = prev.get(key) or 0, cur.get(key) or 0
        if p >= floor and n < p * (1 - drop):
            alerts.append(f"{label} fell {p} -> {n} (>{int(drop * 100)}%)")

    fell("kept", "roles kept")
    fell("matches", "strong matches (7+)", floor=3)
    fell("companies_with_roles", "companies with roles")
    fell("discovered", "discovered companies")
    pe, ne = prev.get("errors") or 0, cur.get("errors") or 0
    if ne >= pe + 3:
        alerts.append(f"fetch errors rose {pe} -> {ne}")
    for src, was in (prev.get("kept_by_source") or {}).items():
        now = (cur.get("kept_by_source") or {}).get(src, 0)
        if was >= 3 and now == 0:
            alerts.append(f"source '{src}' went from {was} kept roles to 0")
    return alerts


def append(history: list, entry: dict, keep: int = KEEP) -> list:
    return (list(history or []) + [entry])[-keep:]


def load_previous(fetch=None) -> list:
    """Previous history from the live site; [] on any failure (first run, offline, bad JSON)."""
    try:
        if fetch is None:
            import requests
            fetch = lambda url: requests.get(url, timeout=20, headers={"Cache-Control": "no-cache"}).json()
        data = fetch(HISTORY_URL)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def record(payload: dict, out_dir: str, live: bool, fetch=None) -> list:
    """Summarize this run, compare with the previous live run, write history.json.
    Returns the alerts (also printed as GitHub Actions ::warning:: annotations)."""
    entry = summarize(payload)
    history = load_previous(fetch) if live else []
    prev = next((h for h in reversed(history) if h.get("mode") == "live"), None) if live else None
    alerts = check_regression(prev, entry)
    entry["alerts"] = alerts
    history = append(history, entry)
    with open(os.path.join(out_dir, "history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=1, ensure_ascii=False)
    for a in alerts:
        print(f"::warning title=Job board regression::{a}")
    return alerts
