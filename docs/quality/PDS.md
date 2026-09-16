# Product Design Specification (PDS) — Attsis Job Board
PRODUCT: Attsis Job Board · VERSION: 1.0 · DATE: 2026-09-16 · OWNER: Global Attsis (BT)
STATUS: ACTIVE · Standards touched: ISO 9001:2015 (§7.5 doc control, §8.3 design), ISO/IEC 25010 (software quality)

## 1. Purpose
A low-cost, CV-driven job board that finds roles across employer ATS systems and ranks
them against the user's own CV, with no LLM in the daily loop. First user: BT (tech roles).

## 2. Scope
IN: CV/cover-letter input, keyword extraction, ATS fetch, deterministic scoring, facet
filtering, distance, JD capture + short gap analysis, static website, GitHub Pages hosting.
OUT (this version): auto-apply, sending email, tracker writes, multi-user accounts, employer side.

## 3. Design inputs (requirements source)
- User need: fewer, better-matched roles + no missed follow-ups (see REQUIREMENTS.md).
- Constraints: near-zero token cost; browser can't fetch ATS (CORS) → fetch in Python/Action;
  honest/no-overclaim; domain-agnostic (works beyond tech later).
- Standards: ISO 9001 doc control via Git; ISO/IEC 25010 quality attributes (below).

## 4. Design outputs (what is built)
- Engine: ats.py (9 ATS adapters), jobfilter.py (generic scorer — single source of truth),
  facets.py, geo.py, cv_parse.py, build_board.py; companies.json registry.
- Web: site/index.html (Setup + Board), data-embedded standalone.
- Automation: .github/workflows/sweep.yml (cron fetch → commit → Pages).

## 5. Quality attributes (ISO/IEC 25010 targets)
| Attribute | Target |
|---|---|
| Functional suitability | Ranks roles by CV fit; every score has reasons |
| Performance efficiency | Daily run = deterministic code, <500 model tokens; fetch fail-soft |
| Compatibility | Static site; any modern browser; GitHub Pages |
| Usability | Setup → board in <2 min; no dead-end (always shows closest) |
| Reliability | One bad ATS never stops a run; tests + smoke gate |
| Security/Privacy | CV parsed in-browser, never uploaded; profile in localStorage |
| Maintainability | New company = 1 registry line; new ATS = 1 adapter |
| Portability | No backend; runs on Pages, a laptop, or a cron box |

## 6. Interfaces
- Input: CV/cover letter (.docx/.pdf/.txt/paste). Output: site/data/jobs.json → website.
- External: employer ATS public JSON endpoints (read-only, no keys).

## 7. Risk summary (full: AUDIT.md §risk; method = Black-Hat + Pre-Mortem)
ATS shape drift, name-based sponsorship false match, thin extraction → low matches,
CORS forcing server-side fetch. Each has a guard (fail-soft, override, closest-fallback, Action).

## 8. Verification & validation
Verification = tests + smoke gate (CSA_Testing.md). Validation = BT uses it for a real search.

## 9. Records / traceability
Git history = document + change control. REQUIREMENTS.md IDs ↔ CSA_Testing.md test IDs ↔ code.
