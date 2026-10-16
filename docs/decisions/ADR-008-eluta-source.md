# ADR-008 — Eluta.ca as a job source: **DEFER (do not build)**

Status: PROPOSED (needs BT's OK) · Date: 2026-10-16 · Issue: #87 (JB-54)
Labels: ✅ verified (how) · ⚠️ inferred · ❓ unchecked.
(The issue asked for "ADR-007", but that number is already taken by ADR-007-coverage-census, so this is ADR-008.)

## Context
Eluta.ca indexes many Canadian employers' career pages, so one source could cover many companies, the way Getro does (#87).

## Findings (2026-10-16)
1. ✅ **robots.txt forbids the endpoints an adapter would need.** `https://www.eluta.ca/robots.txt` says, for `User-agent: *`:
   `Disallow: /search/`, `Disallow: /rss?`, `Disallow: /notify?`, `Disallow: /cache/`, `Disallow: /asp/`. (Fetched with curl.)
2. ✅ **Non-browser clients are rejected at the TLS layer.** Python `requests`/`ssl` gets `SSLV3_ALERT_HANDSHAKE_FAILURE` on every URL, while curl (Windows schannel) gets HTTP 200 with a verified certificate. ⚠️ That points to client fingerprinting or bot filtering. Either way, a GitHub Action run would be brittle.
3. ✅ The server is `Zope 2.13.22 / Python 2.7.18`. There's no public API or JSON endpoint visible from the home page headers. ❓ I didn't look for an official partner feed or API program (no web search in session).
4. ❓ ToS: not read. robots.txt alone already rules out automated search.

## Options
| | Coverage | Respects the site's rules | Fragility | Cost |
|---|---|---|---|---|
| A. Scrape `/search/` | high ⚠️ | **no** (robots.txt) | high (TLS filtering, HTML) | medium |
| B. Ask Eluta for a partner feed | high ⚠️ | yes | low | an email; their terms ❓ |
| **C. Defer: keep growing coverage from each employer's own ATS (chosen)** | already +81 companies + 8 resolved this week, each live-verified | yes | low | none |

## Decision
**C, defer.** Don't build an Eluta adapter. We fetch from each employer's own public ATS (the north star: deterministic, near-zero cost). An Eluta scrape would go against its robots.txt, and would break whenever its bot filtering changes.

**If BT wants the coverage:** B is the only clean route. Ask Eluta for a partner/API feed (draft only; BT sends it).

## Consequences
- #87's acceptance item `tools/probes/probe_eluta.py` is **not built**. A probe of `/search/` would itself break the robots rule.
- The coverage gap Eluta would fill is better measured first. `tools/london_coverage.py` (ADR-007) gives the denominator.
