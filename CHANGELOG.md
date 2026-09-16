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

## v0.6.0 — 2026-09-16 (live data on GitHub Pages + bugs it exposed)
- Repo published (Arvint89/Attsis-jobboard); GitHub Pages live; workflow now also
  deploys on push (with [skip ci] on the data-refresh commit to avoid loops).
- FIX: matcher used naive substring matching — short skills like "ble" matched inside
  "scalable/available/reliable", inflating scores. Now whole-token matching (word
  boundaries) in both the Python engine and the browser scorer. Setup label fixed
  (Word/PDF were always supported).
- Found (backlog): BambooHR returns titles but no descriptions (ZTR etc. score low);
  one big employer (Tenstorrent/Greenhouse) floods the board — needs a per-company cap.
