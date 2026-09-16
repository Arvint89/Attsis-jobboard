# HANDOFF — Job Board product (read this first to resume)
_Last updated 2026-09-16. If you're a new session: read this, then the files it points to. Everything is on disk; no transcript needed._

## What this is
A low-token, CV-driven **tech job board** for BT (Global Attsis product; BT = user #1).
Replaces the old daily-job-sweep's LLM browsing with deterministic Python over company
ATS JSON endpoints + a rule scorer. Output = a static website (Setup → Board).

## Where it lives
- **Repo / tooling:** `Work_done/2026-09-16_Job_Board_Website/` (engine/, site/, tests/, .github/)
- **Runnable copy for BT:** `Job_application/Job_Board/`

## Status — v1 built, green (20 unit tests, 11/11 smoke), NOT yet hosted
Done:
- **Setup page** (site/index.html): input CV + optional cover letter in **.docx/.pdf/.txt/paste**
  (mammoth.js + pdf.js in-browser), auto keyword extraction + manual add/remove, home city.
- **Board**: live in-browser re-scoring vs the CV; facet filters = work arrangement / country /
  industry; distance rings computed from the user's home city (geo.py).
- **Free hooks**: JD capture + short gap analysis (per-card "Gap check" + paste-any-JD tool).
- **Engine**: ats.py (Greenhouse/Lever/Ashby/SmartRecruiters/Recruitee/Workable/BambooHR/
  Rippling/Workday), jobfilter.py (scoring), facets.py, geo.py, cv_parse.py, build_board.py.
- **Registry**: engine/companies.json — 29 companies, most still `platform:"resolve"`.
- **Automation**: .github/workflows/sweep.yml (cron fetch → commit → Pages). GITHUB_SETUP.md has steps.

## Key decisions (don't relitigate)
- Scope = **tech first**, architecture stays domain-agnostic (add CA/warehouse/etc. later via registry).
- Build **for BT first** (single-user); keep multi-user *design*, don't build accounts yet.
- Free = *sees the gap* (JD capture + short gap analysis). Paid = *closes the gap* (deep gap
  narrative, tailored CV, cover letter, interview prep). Pricing in BUSINESS_PLAN.md (digit-sum→8).
- Fetch/score runs in **Python/GitHub Action** (browser can't fetch ATS — CORS); browser re-ranks
  the fetched pool against the user's profile.
- Sponsorship: JD-guess now; **LMIA employers list** (real Canada registry) = Phase 2.5, with the
  quarter labelled + a manual "pull latest" (see SPONSORSHIP_DATA.md).

## Built under PD Rules v1.0 (PRODUCT_DEVELOPMENT_RULES.md)
Spec-first, test-first, smoke-gated, ARCHITECTURE.md required. Run `python engine/smoke_test.py`
and `pytest -q tests/` before calling anything done.

## Immediate next steps (pick up here)
1. **Host on GitHub Pages** — GITHUB_SETUP.md (BT pushes; GitHub connector wasn't usable in-session).
2. **Resolve company ATS** — fill `platform`+`slug` for the `resolve` entries in companies.json so a
   live run returns real roles (one browser pass each; then free forever).
3. **Phase 2** — pipeline (Saved→Applied→Interviewing→Offer→Closed) as a second tab + expandable
   cards + JD capture storage. Spec: SPEC_Phase2_Pipeline.md. UI: UI_DESIGN.md.
4. **Phase 2.5** — LMIA-backed sponsorship.

## Repo layout (cleaned 2026-09-16)
Root: README · HANDOFF · CHANGELOG · **BACKLOG.md** (kanban) · engine/ · site/ · tests/ · .github/
docs/: ARCHITECTURE · **DIAGRAMS.md** (mermaid) · SPEC · SPEC_Phase2_Pipeline · BUSINESS_PLAN ·
UI_DESIGN · INPUT_AND_MODEL · SPONSORSHIP_DATA · PRODUCT_DEVELOPMENT_RULES · GITHUB_SETUP

## Project tracking
Backlog = BACKLOG.md (Now/Next/Later/Icebox/Done). It maps onto a **GitHub Project board**
(create after push: repo → Projects → New project → Board). Diagrams in docs/DIAGRAMS.md.
The CLEAN, push-ready repo is THIS folder (Work_done/...); Job_application/Job_Board is BT's
runnable preview (may have older duplicate docs at its root — ignore; push from here).
