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

from company_key import company_key

SCHEMA_V = 1
BLOCK_RE = re.compile(r"```attsis-feedback[ \t]*\r?\n(.*?)\r?\n```", re.S)

# JB-93 reason codes (mirrored by FB_REASONS in site/index.html; parity-tested)
REASONS = frozenset({"link_404", "already_closed", "cannot_apply",
                     "wrong_title_vs_body", "wrong_location", "other"})
KEYS = {"report": frozenset({"reason", "url", "company", "title", "job", "note"}),
        "company": frozenset({"name", "careers_url", "city", "seen_days"}),       # JB-94
        "feedback": frozenset({"text", "area"}),
        "votes": frozenset({"votes"})}
CAPS = {"url": 500, "company": 120, "title": 200, "job": 240, "note": 500, "ts": 40,
        "name": 120, "city": 80, "text": 1000}
AREAS = frozenset({"board", "map", "profile", "tracker", "other"})
MAX_VOTES = 40


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


def _validate_company(p, clean):
    clean["name"] = _clip(p.get("name") or "", CAPS["name"])
    if not clean["name"]:
        return "name required"
    if p.get("careers_url"):
        if not _http(p["careers_url"]):
            return "bad careers url (http/https only)"
        clean["careers_url"] = _http(p["careers_url"])
    if p.get("city"):
        clean["city"] = _clip(p["city"], CAPS["city"])
    if "seen_days" in p:
        d = p["seen_days"]
        if isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 365:
            return "bad seen_days (0-365)"
        clean["seen_days"] = d
    return ""


def _validate_feedback(p, clean):
    clean["text"] = _clip(p.get("text") or "", CAPS["text"])
    if not clean["text"]:
        return "text required"
    if p.get("area") in AREAS:
        clean["area"] = p["area"]
    return ""


def _validate_votes(p, clean):
    good = []
    for it in p.get("votes") if isinstance(p.get("votes"), list) else []:
        if not isinstance(it, dict) or it.get("v") not in (1, -1):
            continue
        v = {"company": _clip(it.get("company") or "", CAPS["company"]), "v": it["v"]}
        if _http(it.get("url")):
            v["url"] = _http(it["url"])
        elif it.get("job"):
            v["job"] = _clip(it["job"], CAPS["job"])
        else:
            continue
        good.append(v)
    if not good:
        return "no valid votes"
    clean["votes"] = good[:MAX_VOTES]
    return ""


_VALIDATORS = {"report": _validate_report, "company": _validate_company,
               "feedback": _validate_feedback, "votes": _validate_votes}


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


def _dkey(r):
    if r["kind"] == "report":
        return (r["author"], "report", target(r), r.get("reason"))
    if r["kind"] == "company":
        return (r["author"], "company", company_key(r["name"]))
    return (r["kind"], r["issue"], id(r))           # feedback/votes: every message counts


def dedupe(recs: list) -> list:
    """One report per (author, target, reason) and one suggestion per (author, company):
    repeats by one person count once."""
    seen, out = set(), []
    for r in sorted(recs, key=lambda r: r["created"]):
        k = _dkey(r)
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


def vote_tally(recs: list) -> dict:
    """{target: {company, up, down}} from votes records; a person's latest vote on a job wins."""
    last = {}
    for r in sorted(recs, key=lambda r: r["created"]):
        if r["kind"] != "votes":
            continue
        for v in r["votes"]:
            t = v.get("url") or v.get("job")
            last[(r["author"], t)] = (v["v"], v["company"])
    out = {}
    for (_a, t), (v, co) in last.items():
        row = out.setdefault(t, {"company": co, "up": 0, "down": 0})
        row["up" if v > 0 else "down"] += 1
    return out


def feedback_week_md(recs: list, today: str, known=(), days: int = 7) -> str:
    """JB-94 weekly rollup (docs/status/FEEDBACK_WEEK.md): missing-company suggestions
    (with a companies.json seed for the new ones), feedback by area, worst thumbs-down ratio."""
    rows = dedupe(_recent(recs, today, days))
    known_keys = {company_key(n) for n in known}
    lines = [f"# Feedback: week to {today}", "",
             "Source: GitHub issues with an `attsis-feedback` block (ADR-009).", ""]

    sug = defaultdict(list)
    for r in rows:
        if r["kind"] == "company":
            sug[company_key(r["name"])].append(r)
    lines += ["## Missing-company suggestions", ""]
    seeds = []
    if sug:
        lines += ["| company | people | careers | city | status | issues |", "|---|---|---|---|---|---|"]
        for k, rs in sorted(sug.items(), key=lambda kv: (-len({r["author"] for r in kv[1]}), kv[0])):
            url = next((r["careers_url"] for r in rs if r.get("careers_url")), "")
            city = next((r["city"] for r in rs if r.get("city")), "")
            status = "already tracked" if k in known_keys else "new"
            lines.append(f"| {rs[0]['name']} | {len({r['author'] for r in rs})} | {url or '—'} | "
                         f"{city or '—'} | {status} | {' '.join('#' + str(r['issue']) for r in rs)} |")
            if status == "new":
                seeds.append({"name": rs[0]["name"], "platform": "resolve", "careers_url": url,
                              "city": city, "industry": "", "flags": []})
        if seeds:
            lines += ["", "Seed candidates for `engine/companies.json` (resolve the ATS before promoting):", "",
                      "```json", json.dumps(seeds, indent=2, ensure_ascii=False), "```"]
    else:
        lines.append("None.")

    fbk = [r for r in rows if r["kind"] == "feedback"]
    lines += ["", "## Feedback", ""]
    if fbk:
        lines += ["| area | messages |", "|---|---|"]
        lines += [f"| {k} | {n} |" for k, n in Counter(r.get("area", "other") for r in fbk).most_common()]
        lines += [""] + [f"- #{r['issue']} ({r.get('area', 'other')}): {r['text']}" for r in fbk[-20:]]
    else:
        lines.append("None.")

    tally = vote_tally(rows)
    lines += ["", "## Thumbs (worst down-ratio first)", ""]
    if tally:
        lines += ["| posting | company | 👍 | 👎 |", "|---|---|---|---|"]
        order = sorted(tally.items(), key=lambda kv: (-kv[1]["down"] / (kv[1]["up"] + kv[1]["down"]),
                                                      -kv[1]["down"], kv[0]))
        lines += [f"| {t} | {v['company']} | {v['up']} | {v['down']} |" for t, v in order[:20]]
    else:
        lines.append("None.")
    return "\n".join(lines + [""])
