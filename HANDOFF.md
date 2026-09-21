# HANDOFF — read this first to resume

_Last updated: **2026-09-18**. Everything needed to resume is on disk. No chat transcript required._
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

## 2. Where it actually stands (verified 2026-09-18)

The board is **live and healthy**. The pipeline works end to end.

| Check | Result |
|---|---|
| Live data freshness | `generated: 2026-09-18T16:42Z`, `mode: live` ✅ |
| Raw jobs fetched | **61** |
| Jobs visible on the board | **24** |
| Unit tests | **41 passed** ✅ |
| Smoke checks | **11/11 passed** ✅ |

### Why the board shows 24 when 61 were fetched — this is NOT a bug

`default_per_company: 8` caps how many roles one employer may contribute.
Tenstorrent alone posted **31**, so it is trimmed to 8:

```
Tenstorrent 8 (of 31) + Xanadu 3 + VueReal 2 + BinSentry 2 + Canada Rocket 2
+ Flosonics 1 + ZTR 1 + Geotab 1 + Myant 1 + Open Ocean 1 + NorthOne 1 + GHD 1  =  24
```

### The real problems (these ARE bugs / gaps)

1. **Only 12 distinct companies produce jobs.** `unresolved: 22` — 22 of 32 registry
   companies have no working ATS adapter, so they contribute nothing. This is the single
   biggest cause of a thin board. (→ JB-5)
2. **The Getro tier badly under-fetches.** MaRS returned 6 jobs and Communitech 1, from
   boards hosting thousands. Cause: `DEFAULT_QUERIES` in `engine/sources.py` is 11 narrow
   keywords fired at a relevance-ranked API. (→ JB-5)
3. **LEDC (London — home city) contributes nothing** because PR #36 is not merged yet.
4. **Only 1 role scores above `min_score: 7`** without a CV loaded.

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

_Updated 2026-09-21 (evening)._ Plan of record: `docs/status/ISSUE_TRIAGE_2026-09-21.md`.
ADR-002 (company resolver + LLM router) is still **PROPOSED** — needs BT's accept/change/reject.
How to work: **`BRANCHING.md`** (the loop, the rules).

### Done 2026-09-21 — friends release (v0.11.0) scope
- [x] CI on every PR (#37) · branch protection on `main` · auto-merge enabled
- [x] LEDC London scraper (#36) · map Home label + CV greens (#40)
- [x] Source funnel stats + Getro resilience/pagination (#41) — read `source_funnel` in live jobs.json
- [x] Salary from descriptions + salary chip (#6) · remember filters (#8) · initials verified (#7)
- [x] Mobile layout + map/list share one filter (#18)
- [x] Multi-location roles measured to nearest city (#53) · purple ring for multi-city companies (#56)
- [x] Repo cleanup (#58): stale branches, `.gitattributes`, generated files untracked, aider config, BRANCHING.md

### Next
- [ ] **Tag v0.11.0** (#32) and send the live link to friends for feedback
- [ ] Read the live `source_funnel` (Communitech / MaRS) — decide on jobfilter tuning if "stale"/"not relevant" dominate
- [ ] Decide ADR-002 → then JB-5a `detect_ats` (brief ready) → JB-5b resolver
- [ ] JB-35 map: multi-office companies at the office nearest the user (not yet an issue)
- [ ] Parked until friends' feedback: JB-31/32/33, pipeline #9–11, #13, #14–17

### On Aider
Groq free tier (8k tokens/minute) is too small for real edits with gpt-oss-20b — it looped and hit the
limit on a 20-line task. Options: point aider at a bigger free tier (e.g. Gemini — check current limits),
or use Claude Code with the briefs in `docs/briefs/`. Config is now lean (`map-tokens: 0`, no read files).

---

## 6. Work in flight
- Nothing stranded. `memory/` is ignored (empty, purpose unknown).

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
python -m pytest tests/ -q          # expect 41 passed
cd engine ; python smoke_test.py    # expect 11/11 PASS
```
