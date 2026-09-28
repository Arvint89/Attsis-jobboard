# HANDOFF — read this first to resume

_Last updated: **2026-09-28**. Everything needed to resume is on disk. No chat transcript required._
_If you are BT returning after a break, or a fresh Claude session: read this file top to bottom, then open the file it sends you to._

---

## 0. The 60-second version

We are building a **product job board** (live, real jobs, CV-scored, with a map).
It is **deployed and working**. The current work is **not** new features — it is putting a
**proper git / GitHub / CI workflow** in place first, because the old one was broken and undocumented.

- **Live site:** https://arvint89.github.io/Attsis-jobboard/
- **Repo:** https://github.com/Arvint89/Attsis-jobboard
- **Local:** `C:\Users\Namrata\Attsis-jobboard`
- **Branching decision:** `docs/decisions/ADR-001-branching-model.md` ← **read this second**
- **Next action:** section 5 below.

> **Tip:** open this folder in **VS Code** while you work. Its Source Control panel shows
> branches, staged vs unstaged files, and diffs visually — that is the fastest way to build
> a mental model of git. Use the chat to drive, VS Code to see.

---

## 1. What the product is

A CV-driven job board. Deterministic Python fetches real postings from company ATS endpoints
and aggregator boards, a rule-based scorer ranks them against a CV, and a static site shows a
ranked board plus a map of who is hiring nearby.

**North star: near-zero token cost.** No LLM in the daily loop — plain Python in a free GitHub
Action. The CV never leaves the browser (scored client-side).

Built for BT's own job search first, designed to generalise to any user and any domain.
(BT accepted a role at Kepler in Sep 2026, so this is now a **product build**, not a personal
job-hunt tool. Prioritise coverage and generalisation over tuning the scorer to one CV.)

---

## 2. Where it actually stands (verified 2026-09-28)

The board is **live and healthy**. The pipeline works end to end.

| Check | Result |
|---|---|
| Registry size | **54 companies** (was 32 at 2026-09-18) |
| Unit tests | **174 passed** ✅ (was 41) |
| Smoke checks | **11/11 passed** ✅ |
| Sweep recall baseline | **6/20 = 30%** (2026-09-21) — target 70% |

### Shipped since 2026-09-21 baseline

- **JB-43** Careers Resolver — full 4-step wire-in (PRs #88, #90, #91, #92); resolver cache published in jobs.json meta.
- **JB-45 v1** Registry seeding — 9 miss-list companies as `platform: "resolve"` (#94); Trudell Medical (Dayforce, London) via #89.
- **JB-48** Workable adapter + 2 verified Canadian seeds (#96).
- **JB-49** Breezy HR adapter + 2 seed companies (#99).
- **JB-55** Company canonicalization (`engine/company_key.py`) + discovered-company persistence (`engine/discovered.py`) + auto-promote alerts at `sweep_count >= 3` (#104).
- **JB-56** DeepTrekker ring 0 — bare "London" ambiguity resolver in `geo.py` + per-viewer ring fallback via `_reg_city` (#103).
- **Smoke fix** save+restore `site/data/jobs.json` + `board_standalone` around `--demo` (#102).
- **ADR-006 workflow** route deploy through `production` branch (#75).

### Still-open gaps (open GitHub issues)

- **JB-45 registry seeding sprint** (#78) — 54 → 200 target, only v1 landed.
- **JB-46 LinkedIn scout tool** (#79) — BT's original ask (job 4470987790).
- **JB-47 Dayforce adapter** (#80) — biggest Canadian gap (Rogers, Bell, CIBC).
- **JB-48b Workable detail fetch** (#98) — blocked by Cloudflare 1015.
- **JB-50 curated titles + skills DB** (#83) — biggest scoring-recall lever.
- **JB-51 multi-word skill extraction** (#84) — bigrams/trigrams ("power integrity").
- **JB-52 thin-JD enrichment** (#85) — Workday/Getro detail-page fetch.
- **JB-53 multi-persona CV profiles** (#86).
- **JB-54 Eluta.ca spike** (#87).

---

## 3. Architecture (unchanged — see docs/ARCHITECTURE.md)

```
CV/cover (browser) ──parse──▶ keywords + home city
        │
  TIER 1  engine/ats.py       one company → its ATS JSON (9 platforms)
  TIER 2  engine/sources.py   one aggregator → MANY companies (Getro API; LEDC scrape)
        │                     (both emit the SAME normalized job dict)
        ▼
  engine/build_board.py  ── dedupe → jobfilter.classify → facets + geo → site/data/jobs.json
        ▼
  site/index.html   Setup (CV in) → Board (ranked) + Map (Leaflet). Re-scores in-browser.
```

**Important constraint:** the sandbox Claude runs in, and BT's local VM, **cannot reach the
ATS/Getro APIs** (proxy blocks them). Live data only ever comes from the GitHub Action.
Offline, use `python build_board.py --demo`.

---

## 4. The workflow we are putting in place

**Decision: ADR-001 → Option C — trunk-based now, production branch later.**
Full reasoning in `docs/decisions/ADR-001-branching-model.md`.

```
main ──────●───────────●──────────●────▶  (deploys live on every merge)
            \         /  \       /
             feature/jb-NN-slug  bugfix/jb-NN-slug     (short-lived, deleted after merge)
```

- **One long-lived branch: `main`.** It deploys the live site on merge.
- **One short-lived branch per issue**, branched off `main`, merged by PR, **deleted after**.
- **`develop` is retired** — it was 0 ahead / 14 behind and every PR bypassed it.
- **Releases are tags** (`VERSIONING.md`). A `production` branch is added at a named trigger:
  the first paying user. Migration then is one command.

### Working agreement with Claude (BT, 2026-09-18)
> **Review before every action.** Each step is described — what changes, which files, which
> commands — and approved *before* it runs. BT runs all git himself, to learn it.

### Why the workflow had to be fixed first
`BRANCHING.md` described `feature → develop → main`. Reality was `feature → main` for every
recent PR. Docs that do not match reality train you to ignore your own documentation.

---

## 5. ⏭️ NEXT ACTION — start here

_Updated 2026-09-28, late evening._ How to work: `BRANCHING.md`. Start a **fresh chat** each session
(this repo is the memory; long chats burn the weekly usage limit fast). Use Sonnet for routine git/PR work.

### 🔁 SESSION-RESUME POINT — fresh Claude, read this block first

If you are a Claude session opening in this repo, resume the overnight autonomous run:

1. **Read** the plan file at `C:\Users\Namrata\.claude\plans\atomic-chasing-aurora.md` — this is the design context (coverage layers, LLM-where, why LinkedIn is a signal source not a scrape target).
2. **Load auto-memory** at `C:\Users\Namrata\.claude\projects\c--Users-Namrata-attsis-shorts\memory\MEMORY.md` — especially `feedback_github_process.md`, `feedback_smoke_before_merge.md`, `feedback_tag_before_work.md`, `feedback_fix_isnt_fix.md`, `project_ai_empire_obsidian_sync_deletes.md`.
3. **Confirm permission rules** by reading `.claude/settings.json` — `defaultMode: bypassPermissions`, deny rules cover all delete ops + production-branch touches + cross-repo writes + WebFetch/WebSearch.
4. **BT authorisation for the overnight run** (given 2026-09-28 late evening): full autonomy for commit / push / open PR / squash-merge to **`main` only**. Production branch is off-limits (deny rules enforce). No branch deletes. Check local server (`cd site && python -m http.server 8000`, `curl http://localhost:8000/`) after every build.
5. **Start with PR-A** below — branches `feature/jb-50-skills-db`, `feature/jb-51-multi-word-skills`, `feature/jb-46-linkedin-scout`, `feature/jb-45-ledc-seed` in that order. Each: `git tag pre-jb-NN` → branch → code+tests → `pytest tests/ -q` (≥174) → `cd engine && python smoke_test.py` (11/11) → local-server check → commit → push → PR → wait for CI → squash-merge main.
6. **Stop conditions** — surface to BT (do NOT push through): test/smoke red you can't resolve, spec ambiguity you'd have to guess at, LEDC directory HTML shape change breaking parser, CI red twice in a row, ai-empire Obsidian sync fires the Stop hook.

### Overnight autonomous plan (2026-09-28 → 2026-09-29 morning)

Claude will land **four independent PRs**, each on its own branch, tests + smoke green, opened AND
squash-merged to `main`. BT reviews the resulting main in the morning. Order and rationale:

1. **PR-A — JB-50 Skills DB v1** (#83, ~2-3h)
   `data/skills.json` with ~500 canonical tech skills + aliases; wired into `jobfilter.py` + `site/index.html`.
   Biggest single scoring-recall lever per the plan.
2. **PR-B — JB-51 Multi-word skills** (#84, ~1-2h; depends on PR-A)
   Bigrams/trigrams from skills.json (e.g. "power integrity", "signal integrity").
3. **PR-C — JB-46 LinkedIn scout tool** (#79, ~2h)
   `tools/linkedin_scout.py`: URL in → HTML GET → parse `og:site_name` + preview card → propose
   `companies.json` diff. No scraping in daily loop — human-triggered CLI only. Cache at
   `data/linkedin_scout_cache.json` (gitignored). Fallback: paste-JD-text mode.
4. **PR-D — JB-45 v2 registry seed (LEDC directory)** (#78, ~2h)
   Parse LEDC Business Directory (public) → `companies.json` additions with `platform: "resolve"`.
   Target: 54 → ~120 companies. JB-43 resolver takes over on next sweep.

**Not touched overnight** (needs BT judgment): JB-47 Dayforce (real-endpoint verification risk),
JB-52 thin-JD enrichment (rate-limit risk), ADRs 002/003/004/005, any merges.

**Morning checklist for BT:**
- Review PR-A → merge → PR-B (auto-rebase if needed) → PR-C → PR-D
- Run `python tools/sweep_recall.py` after each merge — recall should rise
- Run `python tools/compare_runs.py` — no company should drop to zero

### Tools you can run any time
`python tools/sweep_recall.py` · `python tools/compare_runs.py` · `python tools/probes/probe_communitech.py`
· `python tools/probes/probe_regional.py` (5–10 min) · `gh workflow run job-sweep` (manual refresh).

---

## 6. Work in flight
- Nothing uncommitted on `main`.
- Overnight run (see §5) will land 4 branches: `feature/jb-50-skills-db`, `feature/jb-51-multi-word-skills`, `feature/jb-46-linkedin-scout`, `feature/jb-45-ledc-seed`.

---

## 7. Known repo hygiene issues

Resolved 2026-09-21 (#58): `.gitattributes` added, generated files untracked, stale branches deleted,
issue #32 relabelled. If `git status` shows many modified files after a pull, check with
`git diff --stat --ignore-cr-at-eol` — that shows only the real changes.

---

## 8. BT's learning track

The point of this project is not only the product. Concepts covered so far, and where:

| Concept | Where it is explained |
|---|---|
| What a branch really is (a movable label) | `docs/decisions/ADR-001` §2 |
| Trunk-based vs git-flow, and what breaks each | `docs/decisions/ADR-001` §3–4 |
| Why tags beat a premature production branch | `docs/decisions/ADR-001` §5 |
| Branch protection as *enforcement* vs docs as *description* | `docs/decisions/ADR-001` §2, §8 |
| CI: what `on: pull_request` buys you | `.github/workflows/ci.yml` (commented) |
| Why a stale doc is worse than no doc | `docs/decisions/ADR-001` §1 |
| `git stash` — parking work safely | §5 above |

**Still to cover:** branch protection setup, PR review flow, squash vs merge commits,
tagging a release, GitHub Projects, and reading a CI failure.

---

## 9. Key decisions — do not relitigate

- Scope = **tech first**; architecture stays domain-agnostic (other verticals via the registry).
- Fetch/score runs in **Python / GitHub Action** (the browser cannot fetch ATS — CORS).
  The browser only re-ranks the fetched pool against the user's CV.
- Free tier = *sees the gap*. Paid = *closes the gap*. See `docs/BUSINESS_PLAN.md`.
- Sponsorship: JD-guess now; real LMIA employer list is Phase 2.5.
- **Never commit** `site/data/jobs.json` or `site/board_standalone.html`.

---

## 10. Map of the repo

```
HANDOFF.md          ← you are here; the resume point
BACKLOG.md          kanban (Now / Next / Later / Icebox / Done)
BRANCHING.md        the workflow: trunk-based loop + rules (rewritten 2026-09-21)
VERSIONING.md       MAJOR.MINOR.BUGS policy; current 0.10.0
CHANGELOG.md        release history
engine/             ats.py · sources.py · jobfilter.py · geo.py · facets.py · build_board.py
                    companies.json (registry) · sources.json (boards) · smoke_test.py
site/               index.html (the whole UI) · data/jobs.json (generated)
tests/              41 unit tests
.github/workflows/  sweep.yml (fetch + deploy) · ci.yml (tests on PR — new)
docs/               ARCHITECTURE · SPEC · BUSINESS_PLAN · DIAGRAMS · UI_DESIGN ...
docs/decisions/     ADR-001 branching model  ← the workflow decision
docs/project/       GITHUB_PROJECT_SETUP · RELEASE_PROCESS · PROJECT_PLAN
```

### How to verify everything still works
```powershell
python -m pytest tests/ -q          # expect 174 passed
cd engine ; python smoke_test.py    # expect 11/11 PASS
```
