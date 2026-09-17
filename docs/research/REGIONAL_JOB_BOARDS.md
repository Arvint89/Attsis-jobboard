# Research — Canadian Regional / City / Province Job Boards

_Probed 2026-09-17. Purpose: find local aggregators we can pull deterministically (low token) so the
board covers companies that aren't on an auto-probeable ATS. Answers BT's "does each city/province have
its own board?"_

## The key insight

Most Canadian **innovation-hub / economic-development (EDO) job boards run on Getro** — the same
platform as Communitech. Getro's public API (`api.getro.com/api/v2/collections/{network_id}/search/jobs`)
allows cross-origin calls and needs no key. So **one adapter (`fetch_getro`) + a list of network IDs
covers many cities at once.** Getro states it powers 850+ VC/EDO/chamber boards.

⚠️ **Caveat found while probing:** the older/larger boards (MaRS, Communitech) answer the v2 POST search
cleanly; a newer board (Volta) returned HTTP 400 to the identical call — so the search API has version
variance. **Confirm each board returns jobs through the adapter before adding it to `sources.json`.**

## How to add any Getro board (2-minute method)

1. Open the board's `/jobs` page in a browser.
2. Console: `JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.network` →
   read `id` (the network_id) and `name`.
3. Confirm it answers: `POST api.getro.com/api/v2/collections/<id>/search/jobs`
   headers `{Content-Type, Accept: application/json}` body `{"hitsPerPage":1,"page":0,"query":"engineer"}`
   → expect `{results:{jobs:[…],count:N}}`.
4. If it returns jobs, add a line to `sources.json`. If 400/406/empty, note it and skip.

## Landscape by region

| Province | City | Board | URL | Platform | network_id | Status |
|---|---|---|---|---|---|---|
| ON | Toronto (corridor) | **MaRS Discovery District** | techjobs.marsdd.com | Getro | **383** | ✅ confirmed — 1,427 "engineer" |
| ON | Waterloo–KW (corridor) | **Communitech** | communitech.getro.com | Getro | **8936** | ✅ confirmed — 316 "engineer" |
| ON | **London (home)** | **LEDC — London Tech Jobs** | londontechjobs.ca | Custom ASP.NET | — | ⏳ scrape (fetch_ledc) |
| ON | **London (home)** | **LEDC — London Mfg Jobs** | londonmfgjobs.com | Custom ASP.NET | — | ⏳ scrape (fetch_ledc) |
| ON | Ottawa | Invest Ottawa | jobs.investottawa.ca | Getro | TBD | 🔎 investottawa.getro.com 502 — find live slug |
| ON | Toronto | DMZ (TMU) | dmz.getro.com | Getro (likely) | TBD | 🔎 probe |
| NS | Halifax (Atlantic) | Volta | volta.getro.com | Getro | 21693 | ⚠️ API 400 — needs endpoint variant |
| AB | Calgary | Platform Calgary | platformcalgary.getro.com | Getro (likely) | TBD | 🔎 probe |
| AB | Edmonton | Edmonton Unlimited | (getro) | Getro (likely) | TBD | 🔎 probe |
| BC | Vancouver | New Ventures BC / Foresight (cleantech) | (getro) | Getro (likely) | TBD | 🔎 probe |
| SK | Saskatoon | Co.Labs | (getro) | Getro (likely) | TBD | 🔎 probe |
| MB | Winnipeg | North Forge | (getro) | Getro (likely) | TBD | 🔎 probe |
| — | National | Getro EDO aggregate | economicdevelopmentjobs.getro.com | Getro | TBD | 🔎 broad cross-region |
| — | National | Job Bank (federal) | jobbank.gc.ca | Government feed | — | separate adapter (different API) |

## Recommendation

- **Ship now:** MaRS (383) + Communitech (8936) via `fetch_getro` — this is BT's exact commuting corridor
  (Toronto + KW), thousands of live roles, zero unknowns. Plus **LEDC scrape** for London home market.
- **Expand over time:** add Ottawa / DMZ / western boards one confirmed line at a time (method above).
  Because it's one adapter, each new region is a **data change, not a code change**.
- **Non-tech reach (BT's domain-agnostic goal):** EDO boards like LEDC and the Getro EDO aggregate are
  cross-sector (LEDC already lists healthcare, manufacturing, finance employers), so the same pipeline
  serves accountant / warehouse / trades searches — the registry facets do the filtering.

## Company database ("all companies listed, updated, filterable" — BT, 17 Sep)

Each source returns `organization.name` (+ industry tags, location) per job, so a build run *discovers*
companies, not just jobs. Plan (wired in build_board, JB-3 wiring task):
- Keep `companies.json` as the **curated** registry (the fit-companies we track deliberately).
- On each run, **merge source-discovered companies** into the board's `companies[]` output
  (dedupe by normalized name): name, city, industry, hiring status (fit/open/none), role count, last-seen.
- Result: the map + a company directory show **every company seen across all sources**, refreshed every
  run, filterable by industry / hiring / distance — without hand-maintaining hundreds of registry lines.
