# Attsis Job Board
A low-cost, CV-driven **tech job board** (a Global Attsis product). It finds roles across employer
ATS systems and ranks them against your own CV — **no LLM in the daily loop**, so the recurring
cost is compute, not tokens. Static website, hostable free on GitHub Pages.

## Quick start
```bash
cd engine
pip install -r requirements.txt
python cv_parse.py <your CV.docx>      # optional: CV -> profile.json (or use the Setup page)
python build_board.py --demo           # offline demo build
python smoke_test.py                   # runtime gate (must pass)
pytest -q ../tests                     # unit tests
# open the site:
cd ../site && python -m http.server 8000   # http://localhost:8000
```
The **Setup page** (site/index.html) takes your CV + optional cover letter (.docx/.pdf/.txt/paste),
extracts keywords in the browser, and ranks the loaded roles live. Nothing uploads.

## Repo map
```
engine/    fetch + score engine (ats.py, jobfilter.py generic scorer, facets, geo, cv_parse, build_board)
site/      the website (index.html = Setup + Board) + data/
tests/     pytest (20)   ·   engine/smoke_test.py (11 checks)
.github/   workflows/sweep.yml — cron fetch → commit → Pages (zero tokens)
BACKLOG.md kanban (Now/Next/Later/Icebox/Done)
docs/
  DIAGRAMS.md            Mermaid architecture + roadmap
  project/               PROJECT_PLAN, LABELS/MILESTONES/ISSUES.csv, GITHUB_PROJECT_SETUP
  quality/               PDS, REQUIREMENTS, CSA_Testing, AUDIT
  (SPEC, ARCHITECTURE, BUSINESS_PLAN, UI_DESIGN, INPUT_AND_MODEL, SPONSORSHIP_DATA, PD rules, GITHUB_SETUP)
setup_github_project.sh  one-shot: labels + milestones + issues + Project board (needs gh CLI)
```

## Hosting + project board
- Host: `docs/GITHUB_SETUP.md`  ·  Kanban/Project: `docs/project/GITHUB_PROJECT_SETUP.md`
- Built under **PD Rules v1.0** (spec-first, test-first, smoke-gated): `docs/PRODUCT_DEVELOPMENT_RULES.md`

## Status
v0.5 — MVP built, green (20 tests, 11/11 smoke). Not yet hosted. Next: resolve company ATS → live data.
