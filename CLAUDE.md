# Attsis Job Board — Project Instructions
# Paste this into the Claude project's instructions field; keep this file as the working copy.
# It is the memory between sessions. Update it as things change.
# Repo: Arvint89/Attsis-jobboard · Live: https://arvint89.github.io/Attsis-jobboard/ · Version: 0.10.x

---

## WHAT THIS IS

A **product job board**: a live, reopenable website that ingests a person's CV (+ optional cover
letter), pulls real job postings deterministically, scores each against the CV, and shows a ranked
board **and a map** of who's hiring near them. Built for BT's own job search first, designed to
generalise to any user and any domain (tech now; accountant / warehouse / trades later — the
registry + facets do the filtering, the scorer is CV-driven).

**North star:** near-zero token cost. No LLM in the daily loop — deterministic Python fetch + a
rule-based scorer, run free in a GitHub Action. The CV never leaves the browser (scored client-side).

**Owner:** BT reviews, approves, directs. Claude builds, fixes, explains. BT runs all git himself
(PowerShell on Windows) by copy-pasting the commands Claude gives — **so the git blocks must always be
correct and self-contained.**

---

## ARCHITECTURE (two-tier fetch → score → board+map)

```
CV/cover (browser) ──parse──▶ keywords + home city ──┐
                                                     ▼
  TIER 1  ats.py        one registry company → its ATS JSON (Greenhouse/Lever/Ashby/BambooHR/Rippling/Workday…)
  TIER 2  sources.py    one aggregator board → MANY companies' jobs (Getro API; LEDC HTML scrape)
                                                     │  (both emit the SAME normalized job dict)
                                                     ▼
  build_board.py  ── dedupe → jobfilter.classify (rule scorer) → facets + geo(rings) → site/data/jobs.json
                                                     ▼
  site/index.html   Setup page (CV in) → Board (ranked list) + Map (Leaflet). Re-scores in-browser when a CV loads.
```

Runs in `.github/workflows/sweep.yml` (push + weekday cron): fetch live → deploy to Pages. Deploy-only,
never commits data back (that caused push conflicts). The sandbox Claude works in **cannot reach the
ATS/Getro APIs** — so live data only comes from the Action or BT's own machine; `--demo` is the offline path.

### Key files
- `engine/ats.py` — per-company ATS adapters (9 platforms). `fetch_company(entry) -> (jobs, err)`.
- `engine/sources.py` — board-source adapters. `fetch_getro(network_id)` (any Getro board by id),
  `fetch_ledc(base)` (paginated londontechjobs/londonmfgjobs scrape). Failure-safe: a dead board → [].
- `engine/companies.json` — curated registry (the fit-companies we track). `engine/sources.json` — board list.
- `engine/jobfilter.py` — the generic CV-driven scorer (single source of truth; Python + browser identical).
- `engine/geo.py` — city/country → coords → user-relative distance rings. `engine/facets.py` — arrangement/country/industry/sponsorship.
- `engine/build_board.py` — orchestrator; writes `site/data/jobs.json` (matches/below/companies/facets/home).
- `site/index.html` — the whole UI (setup + board + map), self-contained. Map recomputes company
  status from the CV-rescored pool so greens reflect the loaded CV.
- `tests/` — 41 tests. `engine/smoke_test.py` — 11 runtime checks.
- `docs/design/DESIGN_board_sources.md`, `docs/research/REGIONAL_JOB_BOARDS.md` — the coverage design + Canada-wide board landscape.

---

## HOW WE WORK (non-negotiable)

1. **This is product development — PD rules apply.** Spec/contract first, then code. Every non-trivial
   build gets a design doc with **system + flow diagrams (Mermaid)** and a buildable contract
   (exact signatures, real JSON examples, acceptance criteria, a failing test). BT likes the detailed
   contract format for build issues; one-liners are fine for chores.
2. **TDD + smoke gate.** Write the test first → red → implement → green. After every change run
   `python -m pytest tests/ -q` and `cd engine && python smoke_test.py`. Both must pass before done.
3. **Issue-first git.** For each issue: pull main → branch `feature/jb-NN-slug` → Claude edits files →
   BT commits/pushes/PRs → `Closes #NN` in the PR body auto-closes the issue on merge. Never commit the
   generated `site/data/jobs.json` or `site/board_standalone.html` (the Action regenerates them).
4. **Labels (real set only):** `type:{feature,bug,chore,docs,spike}` · `area:{engine,site,registry,ci,quality}` ·
   `priority:{P0,P1,P2}` · `phase:*`. No `type:enhancement` / `area:ui`.
5. **Versioning** MAJOR.MINOR.BUGS; VERSION file is the source of truth (JB-27 auto-tags on push).
6. **Complete existing issues before opening new ones** — unless a new one directly helps an existing one.
7. **Explain as we build.** BT is learning git/GitHub and the architecture — show the method, name the
   command, say why. Don't just hand over output.

---

## CURRENT STATE (update every session)

- ✅ Deployed live and working: ATS tier + Getro tier (`getro:MaRS` 383, `getro:Communitech` 8936).
  Board + map render; ~60 roles live (base-model until a CV is loaded).
- 🔀 **Open PRs:** #36 LEDC London scraper; the JB-26 map fix (labelled Home + CV-driven greens).
- ⚠️ Coverage reality: BT's small fit-companies (Vital Bio, Cloud DX, Nicoya, StarFish…) aren't on
  auto-probeable ATS — board-source aggregators are the fix (Getro live, LEDC in PR).
- Map greens only light up **after a CV is loaded** (CV is client-side by design).

### Open / next (see BACKLOG.md for the full kanban)
- **JB-27** auto-tag (VERSION + tag-on-push Action) — approved, next up.
- **JB-5** resolve remaining registry ATS; expand Getro regions (Ottawa/Volta/western — confirm id then one line).
- **JB-9–14** Pipeline (Saved→Applied→Interviewing→Offer→Closed).
- **JB-6** salary on cards · **JB-8** persist filters · **JB-15** LMIA · **JB-16** non-tech · **JB-18** a11y/mobile.
- **Icebox:** Product 2 — employer-facing job-posting-visibility tool that feeds this board.

---

## SETTING THIS UP AS A CLAUDE PROJECT (one-time)

1. In the Claude desktop app, create a new Project — name it **Attsis Job Board**.
2. Connect the folder `C:\Users\Namrata\Attsis-jobboard` to the project (so Claude can read/write the repo).
3. Paste this file's contents into the project's **instructions/custom-instructions** field
   (this `CLAUDE.md` stays in the repo as the working copy — edit it here, re-paste when it changes).
4. **Pin** the project in the sidebar so it stays at the top and reopens fast.
