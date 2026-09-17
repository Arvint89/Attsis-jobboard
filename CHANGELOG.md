# Changelog — BT Job Board

## v0.1.0 — 2026-09-16 (POC)
- First build under PD Rules v1.0 (spec-first, test-first, smoke-gated).
- Registry of 29 target companies across rings 0–4 (from Target_Companies_ByDistance.md).
- ATS adapters: Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable,
  BambooHR, Rippling, Workday (Greenhouse endpoint verified live via browser).
- Deterministic filter/scorer encoding Job_Search_Keywords.md §1–§8 (17 unit tests green).
- Static website (index.html + standalone) with search/ring/flag filters + why-matched.
- GitHub Action for cron fetch + Pages deploy (zero-token daily run).
- Known gaps: ~18 companies still `platform:"resolve"`; TTCportals/UKG/ScouteRecruit
  adapters not yet written; JobSpy national tier deferred to a later phase.

## v0.2.0 — 2026-09-16 (Phase 1: CV input -> listing -> scoreboard)
- SPEC widened to the full job-search copilot vision (C1–C13); Phase 1 scoped to
  CV input -> job listing -> scoreboard.
- CV input + parsing: cv_parse.py reads .md/.txt/.docx -> profile.json; the scorer
  now runs off the CV-derived model (model_base.py = fallback). Verified on BT's
  real master CV (31/48 confirmers backed, 11 years).
- Tests 20 green (added test_cv_parse); smoke 11/11 (added CV-parse check).
- build_board --cv <file> regenerates the profile before building.

## v0.3.0 — 2026-09-16 (facets replace decorative flags)
- Replaced vague "flags" with four real, filterable facets: work arrangement
  (on-site/hybrid/remote), country, industry, sponsorship (yes/no/unknown).
- New facets.py derives arrangement/country/sponsorship from location + JD text;
  industry comes from the registry (companies.json now carries industry + sponsors)
  with a JD-keyword fallback.
- Board UI: four facet dropdowns + facet chips on each card; eligibility kept as a
  real signal chip. Name, home city, and distance already user-derived from the CV.

## v0.4.0 — 2026-09-16 (Setup page + client-side re-scoring; scope → tech first)
- Added the missing INPUT surface: a Setup view (same page) — paste/upload CV +
  optional cover letter → browser keyword extraction → review/edit titles+skills →
  Save → board appears, ranked live in-browser against the profile (localStorage).
- Browser scorer mirrors jobfilter; jobs.json now carries a capped `text` field so
  the browser can re-rank the fetched pool. Fetching stays in Python (CORS).
- Domain-agnostic: matching comes from the user's own words (works beyond electronics).
- Business plan added (BUSINESS_PLAN.md); scope narrowed to a TECH board first,
  architecture kept extensible to non-tech verticals.
- Limitations documented: no live browser fetch (CORS), .docx paste-only, frequency
  (not semantic) extraction, per-device localStorage.
- Tests 20 green, smoke 11/11.

## v0.4.1 — 2026-09-16 (fixes from BT testing)
- Header initials now come from the person's NAME (was wrongly derived from the first
  job-title keyword → showed nonsense like "EHD"). Meta line shows the full name.
- No dead-end: if nothing clears the score-7 bar, the board now shows the closest roles
  with a note (instead of a blank "0 matches") — the demo pool is only 5 sample roles.

## v0.5.0 — 2026-09-16 (unified scorer + fuller registry pool + show-all board)
- Single source of truth: jobfilter.py now uses the SAME generic profile-driven
  scoring as the browser (removed hardcoded medical/IEC/space/verification boosts).
  Domain relevance now rides through the user's own CV keywords. Tests updated.
- "Electrical=power" is no longer a hard exclusion — it just scores low (shown, ranked).
- Board shows ALL roles ranked, with a Min-score control (default: show all).
- Demo pool expanded to 20 roles across 13 industries (represents the registry).

## v0.6.0 — 2026-09-16 (MINOR — first live release on GitHub Pages)
- Repo published (Arvint89/Attsis-jobboard); GitHub Pages live via the job-sweep Action.
- Workflow deploys on push (auto-deploy). Setup label fixed (Word/PDF always supported).
- First live fetch surfaced two backlog items: BambooHR returns titles-only (ZTR scores
  low); one big employer (Tenstorrent) floods the board (needs a per-company cap).

## v0.6.1 — 2026-09-16 (BUGS — bug-fix release)
- FIX BUG-001: matcher used naive substring matching — short skills like "ble" matched
  inside "scalable/available/reliable", inflating scores. Now whole-token (word-boundary)
  matching in both the Python engine and the browser scorer.
- Action is now deploy-only (no data commit-back) — stops local/remote push divergence.
- Added VERSIONING.md (MAJOR.MINOR.BUGS) and BRANCHING.md (main=product vs develop/feature).

## v0.6.2 — 2026-09-16 (data — JB-3 partial: resolved Geotab + Miovision)
- Resolved ATS for Geotab (Greenhouse, Oakville/Waterloo — 81 roles) and Miovision
  (Ashby, Kitchener — incl. VP Hardware Engineering). Registry now 8/29 resolved.
- Method: probed Greenhouse/Lever/Ashby/SmartRecruiters endpoints; verified company
  identity before adding (dropped a "profound" Greenhouse board — a Boston pharma namesake).
- Remaining 21 need individual careers-page inspection (not on the common ATS platforms).

## v0.7.0 — 2026-09-17 (MINOR — JB-20 per-company cap)
- No single employer can flood the board: cap of 8 roles per company (highest-scored
  kept). Fixes Tenstorrent (~65) + Geotab (81) dominating. build_board.cap_per_company()
  + 3 tests. jobs.json now reports `capped` and `per_company_cap`.

## v0.7.1 — 2026-09-17 (BUGS — JB-19 BambooHR descriptions)
- BambooHR adapter now fetches each job's /detail endpoint for its description.
  Was title-only, so ZTR/BinSentry/VueReal scored low ("no skills in body").
  Verified the detail endpoint shape live; failure-safe (keeps title-only if detail errors).
- Added 2 tests (detail fetch + failure fallback). 25 tests green.

## v0.8.0 — 2026-09-17 (MINOR — JB-22 distance filter, sort-by, per-company view)
- Board now keeps ALL roles in the data (no more hard per-company drop). The cap
  became a UI control: "Per company" (top 8 by default → All to see everything).
- New "Distance" filter (Ring 0–4) and "Sort by" (Score / Distance / Salary).
- build_board no longer deletes roles; payload carries default_per_company.

## v0.9.0 — 2026-09-17 (MINOR — JB-25 geo resolution: real distances + coordinates)
- Distances resolve by city, then country centroid — foreign roles (Bengaluru,
  Santa Clara, Belgrade) no longer inherit the company's HQ ring. Fixes the JB-24 bug.
- Expanded city table (US hubs + world cities); Canada keeps registry-ring fallback
  for unknown Canadian cities only.
- Every job now carries lat/lng in jobs.json (foundation for the map, JB-26).
- facets.country() names real countries (India, Serbia, Switzerland…).
- 8 geo tests added; 33 total green.

## v0.10.0 — 2026-09-17 (MINOR — JB-26 company map)
- Map view (Leaflet + Esri light tiles): every registry company plotted around your
  home, coloured by hiring status vs your CV — green (hiring, fits CV), amber (open,
  weaker fit), grey (no match), hollow (ATS not resolved). Status filter + careers popups.
- build_board emits a companies[] array (location + status) + home_coords; added a
  city to every company; added Vital Biosciences to the registry.
- Builds on JB-25's lat/lng resolution. List/Map toggle on the board.
