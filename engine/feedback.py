"""feedback.py -- ADR-009 back channel: read user reports/feedback out of GitHub issues.

The browser opens a prefilled GitHub issue whose body carries one fenced block:

    ```attsis-feedback
    {"v":1,"kind":"report","reason":"link_404","url":"https://...","company":"Acme","ts":"..."}
    ```

This module parses those blocks, validates them against an allow-list (unknown keys are
dropped, so a payload can never smuggle CV data through ingest), dedupes per reporter,
finds suppress candidates (JB-93: link_404 from >=3 distinct authors within 48 h) and
renders the weekly rollup. Deterministic, stdlib only.
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

SCHEMA_V = 1
BLOCK_RE = re.compile(r"```attsis-feedback[ \t]*\r?\n(.*?)\r?\n```", re.S)

# JB-93 reason codes (mirrored by FB_REASONS in site/index.html; parity-tested)
REASONS = frozenset({"link_404", "already_closed", "cannot_apply",
                     "wrong_title_vs_body", "wrong_location", "other"})
KEYS = {"report": frozenset({"reason", "url", "company", "title", "job", "note"})}
CAPS = {"url": 500, "company": 120, "title": 200, "job": 240, "note": 500, "ts": 40}


def _clip(v, n):
    return re.sub(r"[\x00-\x1f]+", " ", str(v)).strip()[:n]


def _http(u):
    u = str(u or "").strip()
    return u[:CAPS["url"]] if re.match(r"^https?://", u, re.I) else ""


def parse_body(body: str) -> list:
    """Every JSON object in an attsis-feedback block of an issue body ([] if none parse)."""
    out = []
    for m in BLOCK_RE.finditer(body or ""):
        try:
            p = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(p, dict):
            out.append(p)
    return out


def _validate_report(p, clean):
    if p.get("reason") not in REASONS:
        return "bad reason"
    clean["reason"] = p["reason"]
    if p.get("url"):
        if not _http(p["url"]):
            return "bad url (http/https only)"
        clean["url"] = _http(p["url"])
    for k in ("job", "title", "note"):
        if p.get(k):
            clean[k] = _clip(p[k], CAPS[k])
    if not clean.get("url") and not clean.get("job"):
        return "url or job required"
    clean["company"] = _clip(p.get("company") or "", CAPS["company"])
    if not clean["company"]:
        return "company required"
    return ""


_VALIDATORS = {"report": _validate_report}


def validate(p) -> tuple:
    """(clean_payload, "") if valid, else (None, error). clean holds allow-listed keys only."""
    if not isinstance(p, dict):
        return None, "not an object"
    if p.get("v") != SCHEMA_V:
        return None, f"unsupported version {p.get('v')!r}"
    kind = p.get("kind")
    if kind not in _VALIDATORS:
        return None, f"unknown kind {kind!r}"
    clean = {"v": SCHEMA_V, "kind": kind, "ts": _clip(p.get("ts") or "", CAPS["ts"])}
    err = _VALIDATORS[kind](p, clean)
    return (None, err) if err else (clean, "")


def ingest(issues: list) -> list:
    """Valid payloads from `gh issue list --json number,author,createdAt,body` rows,
    each tagged with the issue number, author login and created time. Oldest first."""
    recs = []
    for it in issues or []:
        author = ((it.get("author") or {}).get("login") or "ghost")
        for p in parse_body(it.get("body") or ""):
            clean, _err = validate(p)
            if clean:
                recs.append({**clean, "issue": it.get("number"), "author": author,
                             "created": it.get("createdAt") or ""})
    return sorted(recs, key=lambda r: (r["created"], r["issue"] or 0))


def target(rec) -> str:
    """What a record is about: the posting url, else the job key."""
    return rec.get("url") or rec.get("job") or ""


def dedupe(recs: list) -> list:
    """One record per (author, kind, target, reason): repeat reports by one person count once."""
    seen, out = set(), []
    for r in sorted(recs, key=lambda r: r["created"]):
        k = (r["author"], r["kind"], target(r), r.get("reason"))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def _when(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def suppress_candidates(recs: list, window_h: int = 48, min_authors: int = 3) -> list:
    """JB-93: urls with link_404 from >= min_authors distinct authors inside any window_h span.
    Candidates only -- a reviewed PR moves them into engine/suppressed.json (ADR-009 D5)."""
    by_url = defaultdict(list)
    for r in dedupe(recs):
        t = _when(r["created"])
        if r["kind"] == "report" and r.get("reason") == "link_404" and r.get("url") and t:
            by_url[r["url"]].append((t, r["author"], r["issue"]))
    out, win = [], timedelta(hours=window_h)
    for url, hits in sorted(by_url.items()):
        hits.sort()
        best = None
        for i, (t0, _a, _n) in enumerate(hits):
            inside = [h for h in hits[i:] if h[0] - t0 <= win]
            authors = {h[1] for h in inside}
            if len(authors) >= min_authors and (best is None or len(authors) > best["authors"]):
                best = {"url": url, "authors": len(authors), "issues": [h[2] for h in inside],
                        "first": inside[0][0].isoformat(), "last": inside[-1][0].isoformat()}
        if best:
            out.append(best)
    return out


def _recent(recs, today, days):
    end = datetime.fromisoformat(today).replace(tzinfo=timezone.utc) + timedelta(days=1)
    start = end - timedelta(days=days + 1)
    return [r for r in recs if (t := _when(r["created"])) and start <= t < end]


def reports_week_md(recs: list, today: str, days: int = 7) -> str:
    """Weekly rollup for docs/status/REPORTS_WEEK.md: top reported postings, reasons,
    companies (a spike for one ATS means an adapter is drifting), suppress candidates."""
    rows = [r for r in dedupe(_recent(recs, today, days)) if r["kind"] == "report"]
    lines = [f"# Job reports: week to {today}", "",
             f"{len(rows)} unique reports from {len({r['author'] for r in rows})} people "
             f"(source: GitHub issues with an `attsis-feedback` block; ADR-009).", ""]
    if not rows:
        return "\n".join(lines + ["No reports this week.", ""])
    lines += ["## By reason", "", "| reason | reports |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in Counter(r["reason"] for r in rows).most_common()]
    lines += ["", "## Most-reported postings", "", "| posting | company | reports | reasons | issues |",
              "|---|---|---|---|---|"]
    by_t = defaultdict(list)
    for r in rows:
        by_t[target(r)].append(r)
    for t, rs in sorted(by_t.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]:
        lines.append(f"| {t} | {rs[0]['company']} | {len(rs)} | "
                     f"{', '.join(sorted({r['reason'] for r in rs}))} | "
                     f"{' '.join('#' + str(r['issue']) for r in rs)} |")
    lines += ["", "## By company", "", "| company | reports |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in Counter(r["company"] for r in rows).most_common(15)]
    cands = suppress_candidates(recs)
    lines += ["", "## Suppress candidates (link_404, >=3 people in 48 h)", ""]
    lines += ([f"- {c['url']} ({c['authors']} people, issues {' '.join('#' + str(n) for n in c['issues'])})"
               for c in cands] or ["None."])
    lines += ["", "Move a candidate into `engine/suppressed.json` with a reviewed PR to drop it from the board.", ""]
    return "\n".join(lines)
