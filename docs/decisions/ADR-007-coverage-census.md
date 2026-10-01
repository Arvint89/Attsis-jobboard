# ADR-007 — Coverage measured against a StatsCan denominator

- **Status:** ACCEPTED — 2026-09-28
- **Deciders:** BT (owner)
- **Related:** ADR-003 (LinkedIn scout as signal), issues JB-57 (#110), JB-58/59/60 (follow-ups)
- **Note on numbering:** JB-57 was filed calling this ADR-006, but that slot
  was already taken by `ADR-006-production-branch.md`. Using ADR-007 to avoid
  clobbering an accepted decision. Docs and PR body reflect the new number.

## 1. Context

Coverage of the daily sweep has been driven by reactive miss-patching: BT
spots a job that didn't surface, we add the company to the registry, and
the numerator inches up. That loop can never plateau because we don't know
how many companies *should* be in the registry — we have no denominator.

At the 2026-09-28 baseline the recall sits at 7 / 23 known-good roles
(≈30%). We can move the numerator all week and never learn whether that's
1% or 90% of the reachable universe for any given city.

We need a **ground-truth denominator per region**, and StatsCan publishes
one for free:

- Table **33-10-1176** — *Canadian Business Counts, with employees, by CMA
  and CSD, by NAICS and employment size*. Semiannual (June / December).
  Downloadable as a single ZIP-wrapped CSV, ~17 MB.

That table tells us, for any Census Metropolitan Area, exactly how many
employer businesses exist in every NAICS/size bucket. It is the closest
thing to a canonical answer that exists in Canadian public data.

## 2. Decision

Adopt StatsCan CBC (33-10-1176) as the **coverage denominator** for the
job board, starting with London CMA (BT's home region and the one with
the deepest existing registry curation).

- **Downloader**: `tools/statcan_cbc_download.py` fetches the ZIP,
  extracts the data CSV, caches it under `data/statcan/33101176_{period}.csv`
  (gitignored — 17 MB, refetchable).
- **Coverage tool**: `tools/london_coverage.py` reads the cached CSV,
  filters to the London CMA + a configurable tech-NAICS list + a
  configurable employment-size floor, sums the counts per NAICS, and
  cross-references `engine/companies.json` to produce a gap report.
- **Default tech NAICS**: 5415, 5413, 51, 5182, 334, 3345, 3364 —
  the codes BT verified as tech-relevant on 2026-09-28.
- **Default employment-size floor**: ≥ 10 employees, to skip solopreneurs
  who rarely post on ATS platforms. Configurable via `--min-size 1`.

### Coverage math and its honest limits

- Per-NAICS **denominator** = sum of business counts across the included
  employment-size buckets for that NAICS in the London CMA row.
- Total **denominator** = naive sum of per-NAICS counts. NAICS 5182 sits
  under NAICS 51 in the hierarchy, so the total is a **sum-with-overlaps
  ceiling**, not a unique-employer count. This matches the "~700" figure
  in the JB-57 issue and keeps the ceiling conservative (we'd rather
  overestimate the gap than under-report it).
- **Numerator** = count of registry entries with a city in the London
  CMA set (matches `LONDON_METRO` in `tools/seed_ledc.py`).
- Per-NAICS **numerator attribution is a JB-58 follow-up** — the registry
  has no NAICS tags today. The first cut reports overall coverage only.

## 3. Consequences

- +We can now say a concrete thing: "London CMA is at X / Y (Z%) of the
  StatsCan employer denominator." That number can be tracked over time.
- +The tool templates. A single `--period YYYY-MM` and per-CMA GEO filter
  variant will produce the same report for KW-Barrie, Toronto, Ottawa,
  eventually all 11 Ontario / 76 Canadian economic regions.
- +It reframes the roadmap: seeding decisions become "close the largest
  NAICS gaps first", not "add the company from yesterday's miss".
- −The CBC is semiannual, so the denominator lags reality by up to six
  months. Acceptable — we're measuring long-run gaps, not weekly churn.
- −StatsCan's WDS full-table endpoint changes format occasionally; the
  downloader is intentionally boring (one function, injectable fetcher)
  so a schema change is a one-line fix.

## 4. Alternatives considered

- **Reactive miss-patching** — the status quo. Rejected: no plateau, no
  measurable convergence. Every quarter feels the same as the last.
- **ONBIS / provincial corporate registries as denominator** — richer
  data (actual names) but no NAICS tagging, per-province paywalls, and no
  standardized cross-province rollup. Kept for the JB-58 *sourcing* step,
  not the *counting* step.
- **LinkedIn company-page counts** — brittle, ToS-hostile, not a
  denominator (only counts LinkedIn-active employers). Already used as a
  signal source in ADR-003; not viable as a census.
- **Statistics Canada's Business Register (BR)** direct — not public; CBC
  is the free public projection of the BR at the level of detail we need.

## 5. What this ADR does *not* decide

- Sourcing the ~700 London names. That is JB-58 (ONBIS scrape +
  LinkedIn scout at scale + ATS-detection funnel).
- NAICS-tagging the registry. That is a JB-58 pre-req and unlocks
  per-NAICS numerator attribution.
- Extending beyond CMAs. Ontario has 11 economic regions and 49 CDs;
  Canada has 76 economic regions. Templated after the London tool proves
  the shape (JB-59, JB-60).
