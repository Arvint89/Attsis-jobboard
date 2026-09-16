# Sponsorship facet — data source design (Canada)
_Draft for BT review · 2026-09-16 · not built yet (spec-first)_

## The registry exists
**TFWP Positive LMIA Employers List** — Government of Canada Open Government Portal,
updated **quarterly** (2026Q1 available). Lists employers issued a positive Labour
Market Impact Assessment, broken out by **program stream · NOC 2021 occupation ·
business location**. Free CSV/Excel download.
Dataset: https://open.canada.ca/data/en/dataset/90fed587-1364-4f33-a9ee-208181dc0b97

Related: the **IMP** (LMIA-exempt) employer stream (offers via the IRCC Employer
Portal — less openly published in bulk), and third-party search tools (LMIAGrader,
moving2canada) that repackage the same LMIA data.

## How we'd wire it (replaces the JD-guess in facets.py)
1. A small `sponsors.py` downloads the latest quarterly LMIA CSV once (cache locally;
   refresh quarterly — this is data, not tokens).
2. Optionally filter rows to engineering NOCs (e.g. 21310 Electrical/electronics
   engineers, 21311 Computer engineers, 22310/22311 technologists) so the signal is
   relevant to this product's users.
3. Build a normalized set of employer names → `sponsor_index`.
4. In the pipeline/board build, resolve each company by fuzzy name match:
   - match on the LMIA list  → sponsorship = **"sponsored before (LMIA <quarter>)"**
   - explicit registry override (`sponsors: true/false`) wins over the list
   - JD text ("visa sponsorship available" / "no sponsorship") is a secondary signal
   - otherwise **unknown**
5. Store the match provenance on the row (which quarter, which NOC) so it's auditable.

## Honest caveats (surface these, don't hide them)
- **Historical, not a promise.** A past LMIA ≠ they'll sponsor this role. Label it as
  "sponsored before", never "will sponsor".
- **Name-only matching.** Legal entity names differ from brand names → fuzzy match with
  a confidence, and let a registry override correct misses.
- **Coverage gaps.** The list excludes person-named businesses and is TFWP-only (IMP
  offers aren't fully in it).
- For a **PR/citizen user (like BT), sponsorship is moot** — the facet should auto-hide
  or grey out when the profile says the user needs no sponsorship (from the CV/home).

## Decision for BT
- Include LMIA-backed sponsorship in Phase 2, or keep it JD-guess for now and add the
  LMIA data source as a Phase 2.5 enhancement?
- If included: filter to engineering NOCs only, or keep all (broader but noisier)?
