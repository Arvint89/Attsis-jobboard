# Release Tracker — Attsis Job Board
Versioning: **MAJOR.MINOR.BUGS** (see docs/VERSIONING.md). One row per release.
**Update this table on every release** (it's a step in docs/project/RELEASE_PROCESS.md).

| Version | Date | Type | Summary | Git tag |
|---|---|---|---|---|
| 0.1.0 | 2026-09-16 | POC | Engine + registry + filter + board (proof of concept) | — (pre-repo) |
| 0.2.0 | 2026-09-16 | MINOR | CV input + parsing; domain-agnostic model | — (pre-repo) |
| 0.3.0 | 2026-09-16 | MINOR | Facet filters (arrangement/country/industry/sponsorship) | — (pre-repo) |
| 0.4.0 | 2026-09-16 | MINOR | Setup page; in-browser keyword extract + re-scoring | — (pre-repo) |
| 0.4.1 | 2026-09-16 | BUGS | Name-based initials; no dead-end board | — (pre-repo) |
| 0.5.0 | 2026-09-16 | MINOR | Unified generic scorer; show-all board + min-score | — (pre-repo) |
| 0.6.0 | 2026-09-16 | MINOR | First live release on GitHub Pages; auto-deploy on push | (optional backfill) |
| 0.6.1 | 2026-09-16 | BUGS | BUG-001 "ble" whole-word matching; deploy-only Action | v0.6.1 |
| 0.6.2 | 2026-09-16 | BUGS | Data: resolved Geotab + Miovision (JB-3 partial) | v0.6.2 |
| 0.7.0 | 2026-09-17 | MINOR | Per-company cap (JB-20) — no employer floods the board | v0.7.0 |
| _next_ | | | | |

Legend: pre-repo = existed as a dev iteration before the first GitHub push (collapsed into the
initial commit — nothing distinct to tag). Tags start at v0.6.1.
