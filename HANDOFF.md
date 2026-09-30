# HANDOFF — read this first to resume

_Last updated: **2026-09-30** (overnight run: verify-promotions harness proved JB-5 batch 1 11/11 OK; Semtech/Littelfuse workday tenant/site/dc bug fixed both in registry and in resolve_sweep output; probe-getro harness landed + ran (1 confirmed hit, 25 skips due to Getro's custom-domain migration); coverage census templated to any CMA; design prototype landed at docs/design/prototype/; 4 commercialization + ONBIS issues filed). Everything needed to resume is on disk. No chat transcript required._
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

## 2. Where it actually stands (verified 2026-09-30, post-overnight-run)

The board is **live and healthy**. The pipeline works end to end.

| Check | Result |
|---|---|
| Registry size | **176 companies** |
| Unit tests | **246 passed** ✅ (+6 for CMA templating) |
| Smoke checks | **11/11 passed** ✅ |
| Release tagging | **Auto** — `VERSION` → `v<VERSION>` on push to main (JB-27, #116); idempotent no-op if tag exists |
| Adapter live-check | **4 CI diagnostic workflows now**: `verify-dayforce.yml`, `resolve-sweep.yml`, `verify-promotions.yml`, `probe-getro.yml` (all workflow_dispatch, read-only) |
| `platform:"resolve"` entries | **148** (11 promoted in JB-5 batch 1 #125, all 11 verified OK by verify-promotions run) |
| Sources | **6 boards** in `sources.json` (was 5; +Economic Development Jobs 30254 via #131) |
| Sweep recall | **7/23 = 30%** (2026-09-28). JB-5 batch 1 lift should show on next sweep — 11 companies now fetch directly. Target 70% |

### Shipped since 2026-09-21 baseline

- **JB-43** Careers Resolver — full 4-step wire-in (PRs #88, #90, #91, #92); resolver cache published in jobs.json meta.
- **JB-45 v1** Registry seeding — 9 miss-list companies as `platform: "resolve"` (#94); Trudell Medical (Dayforce, London) via #89.
- **JB-45 v2** LEDC directory seed — 119 London companies added as `platform: "resolve"` (#109).
- **JB-46** LinkedIn scout CLI — URL → company → registry PR proposal (#108).
- **JB-48** Workable adapter + 2 verified Canadian seeds (#96).
- **JB-49** Breezy HR adapter + 2 seed companies (#99).
- **JB-50** Canonical skills + titles DB v1 — `data/skills.json`, `engine/skills_db.py`, browser wire-in (#106).
- **JB-51** Multi-word skill extraction — bigrams/trigrams from skills.json (#107).
- **JB-55** Company canonicalization (`engine/company_key.py`) + discovered-company persistence (`engine/discovered.py`) + auto-promote alerts at `sweep_count >= 3` (#104).
- **JB-56** DeepTrekker ring 0 — bare "London" ambiguity resolver in `geo.py` + per-viewer ring fallback via `_reg_city` (#103).
- **JB-47** Dayforce (Ceridian) adapter — `fetch_dayforce` + detect rule + Loblaw/Sobeys/LCBO seeds (#114). Site IDs need manual verification (JB-47b follow-up).
- **JB-57** London CMA coverage census — `tools/london_coverage.py` + `tools/statcan_cbc_download.py` + ADR-007 (#112). Denominator-first pivot delivered.
- **JB-27** Auto-tag from VERSION — `.github/workflows/tag.yml` + VERSION file + 3 CI guards (#116). First live run on merge was the expected `tag v0.11.0 already exists; nothing to do` no-op — idempotency proven end-to-end.
- **JB-47b** Dayforce shared-portal adapter — `fetch_dayforce_shared` for `jobs.dayforcehcm.com/{lang}/{tenant}/{site}` shape + detect rule + Trudell migrated resolve→dayforce_shared (#119). Adapter code correct + tested; live URLs were guessed and turned out wrong (see JB-47b-followup).
- **JB-47b-followup** Live verification — `verify-dayforce.yml` workflow + `tools/verify_dayforce.py` (#121). Ran once against main (run 36513420813): all 4 Dayforce entries fetch against wrong URLs — Loblaw/LCBO subdomains NXDOMAIN, Sobeys 404, Trudell shared-portal API path wrong. All 4 reverted to `platform: "resolve"` via #122 with diagnostic notes so JB-47c starts armed with real failure modes.
- **JB-5 batch 1** Resolve-sweep harness + first promotion batch — `tools/resolve_sweep.py` + `.github/workflows/resolve-sweep.yml` (#124, workflow_dispatch), then promotion PR #125. Sweep classified 160 resolve entries → **12 supported hits, 4 adapter gaps, 144 misses**. Promoted 11 to their real platform+slug (2× workable, 4× bamboohr, 1× rippling, 2× workday, 1× greenhouse, 1× smartrecruiters). S L H Transport held back — sweep detected `dayforce slug='www'` but that's a resolver false positive (`www.slh.ca` misread as tenant). Adapter-gap frequency for future priority: **ttcportals: 2, ultipro: 1, scouterecruit: 1**.
- **Smoke fix** save+restore `site/data/jobs.json` + `board_standalone` around `--demo` (#102).
- **ADR-006 workflow** route deploy through `production` branch (#75).
- **Ops** Claude Code permission rules + HANDOFF refresh (#105).
- **JB-5 verify-promotions** — `tools/verify_promotions.py` + `.github/workflows/verify-promotions.yml` (#127); live-run verified 11/11 batch-1 companies fetch OK (Semtech=88, Littelfuse=102, others 1-30 jobs each).
- **JB-5 workday tenant/site/dc** — added missing tenant/site/dc fields to Semtech + Littelfuse registry entries (#128); root-cause fix in `tools/resolve_sweep.py` so future promotions preserve those fields in the paste-ready JSON (#130).
- **JB-57 CMA templating** — `tools/london_coverage.py` now takes `--cma Toronto|Waterloo|Ottawa|London`; added CMA_CITIES dict for 4 CMAs; +6 tests (#132).
- **JB-59 Getro probe** — `tools/probe_getro_networks.py` + `.github/workflows/probe-getro.yml` (#129); ran 27 candidates, confirmed **Economic Development Jobs** (network_id 30254) — added via #131. Finding: Getro migrated most boards to custom domains, so `<slug>.getro.com` blind guessing failed (24/25 skips).
- **JB-55 design prototype** — copied the design-drop zip contents into `docs/design/prototype/` (#133); design reference only, not wired to production.
- **Commercialization backlog seeded** — filed 4 GitHub issues (#134 Tailor CV button, #135 Intake form, #136 Regional licence config, #137 ONBIS spike) so the design template plan no longer lives only in the prototype markdown.

### Sweep-miss analysis (2026-09-28, 16 misses of 23 known-good roles)

Company **not in registry** (biggest lever): Nokia (2), indie.inc (3), Corvita Biomedical (2),
Sciemetric, PerkinElmer, Wellspect, Safe Fleet, Life360, Amtech, Hitachi Rail, ecobee, ASSA ABLOY.
Nokia uses Oracle Cloud (adapter not built). Everyone else is either not in the registry or in with
`platform:"resolve"` awaiting a supported ATS detection.

**Root diagnosis (BT, 2026-09-28)**: reactive miss-patching is the wrong loop. Coverage must be
measured against a **ground-truth denominator**, not the last miss you happened to see. Next cycle
switches to StatsCan-CBC-driven planning — see JB-57 (#110) and §5 below.

### Still-open gaps (open GitHub issues, ordered by leverage)

**Coverage / adapters (P0-P1):**
- **JB-58 London name sourcing** (not yet filed) — populate the ~700-employer denominator with actual company names via ONBIS / LinkedIn scout at scale; per-NAICS numerator attribution
- **JB-47c Dayforce URL research** (not yet filed) — find real Dayforce subdomains for Loblaw/Sobeys/LCBO (or confirm they're not on Dayforce), and find the shared-portal API endpoint for Trudell. Needs a browser + devtools; sandbox cannot help. Each `resolve` entry has diagnostic notes from JB-47b-followup showing exactly what failed.
- **JB-5 batch 2** (#5) — 148 `platform:"resolve"` entries still open; sweep classified them all as MISS (mostly LEDC-directory small manufacturers with no discoverable ATS via careers-page probes). Next moves either require the JB-46 LinkedIn scout at scale, or new adapters for ttcportals/ultipro/scouterecruit (2/1/1 entries respectively)
- **JB-48 Workable more seeds** (#81) — 2 of 5 done, Cloudflare-blocked
- **JB-48b Workable detail fetch** (#98) — blocked by Cloudflare 1015
- **JB-32 Adzuna spike** (#43), **JB-33 Job Bank Canada** (#44), **JB-54 Eluta spike** (#87)

**Scoring / parsing:**
- **JB-52 thin-JD enrichment** (#85) — Workday/Getro detail-page fetch
- **JB-53 multi-persona CV profiles** (#86)
- **JB-31 LLM router ADR-002** (#42)

**Data quality:** JB-15 LMIA (#15), JB-16 non-tech vertical (#16), JB-17 CSA quality (#17).

**UI Phase 2 (deferred until coverage lands):** JB-9 (#9), JB-10 (#10), JB-11 (#11), JB-13 (#13), JB-14 (#14).

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

_Updated 2026-09-30 (post-overnight-run: 5 more PRs merged — #127 verify-promotions, #128 workday tenant/site/dc fix, #129 probe-getro harness, #130 resolve_sweep field-preservation fix, #131 Economic Development Jobs source, #132 CMA templating, #133 design prototype landing; +4 issues filed: #134-137)._ How to work: `BRANCHING.md`. Start a **fresh chat** each session
(this repo is the memory; long chats burn the weekly usage limit fast).

### 🔁 SESSION-RESUME POINT — fresh Claude, read this block first

If you are a Claude session opening in this repo, resume the **denominator-first coverage cycle**:

1. **Read** the plan file at `C:\Users\Namrata\.claude\plans\atomic-chasing-aurora.md` — design context: coverage funnel (layers 1-5), why LinkedIn is a signal source not a scrape target, DB-before-ML.
2. **Load auto-memory** at `C:\Users\Namrata\.claude\projects\c--Users-Namrata-attsis-shorts\memory\MEMORY.md` — especially `feedback_github_process.md`, `feedback_smoke_before_merge.md`, `feedback_tag_before_work.md`, `feedback_fix_isnt_fix.md`, `project_ai_empire_obsidian_sync_deletes.md`.
3. **Confirm permission rules** by reading `.claude/settings.json` — `defaultMode: bypassPermissions`, deny rules cover all delete ops + production-branch touches + cross-repo writes + WebFetch/WebSearch. **Terminal launch honors bypass fully; VS Code extension has its own approval overlay that will still prompt** — run from PowerShell / bash for silent autonomous execution.
4. **BT authorisation (standing, from 2026-09-28)**: full autonomy for commit / push / open PR / squash-merge to **`main` only**. Production branch is off-limits (deny rules enforce). No branch deletes. Check local server (`cd site && python -m http.server 8000`, `curl http://localhost:8000/`) after every build. Same authorization applies to any BL you pick from §5 below unless BT overrides.
5. **Shipped 2026-09-28 → 2026-09-29** — 12 PRs to `main`:
   - ✅ PR #106 JB-50 canonical skills + titles DB v1 (closed #83)
   - ✅ PR #107 JB-51 multi-word skills bigrams/trigrams (closed #84)
   - ✅ PR #108 JB-46 LinkedIn scout tool (closed #79)
   - ✅ PR #109 JB-45 v2 seed 119 LEDC companies (closed #78)
   - ✅ PR #112 JB-57 London CMA coverage census (closed #110) — denominator-first pivot delivered
   - ✅ PR #114 JB-47 Dayforce adapter + Loblaw/Sobeys/LCBO seeds (closed #80)
   - ✅ PR #116 JB-27 auto-tag from VERSION (closed #32) — manual-tagging drift eliminated
   - ✅ PR #119 JB-47b Dayforce shared-portal adapter + Trudell migration (closed #118)
   - ✅ PR #121 JB-47b-followup verify-dayforce harness (Refs #118)
   - ✅ PR #122 revert 4 Dayforce seeds → `resolve` after live check exposed wrong URLs
   - ✅ PR #124 JB-5 resolve-sweep harness (workflow_dispatch, read-only)
   - ✅ PR #125 JB-5 batch 1 — 11 promotions (workable×2, bamboohr×4, rippling, workday×2, greenhouse, smartrecruiters)
6. **Sweep recall (2026-09-28 evening)** = **7/23 = 30%**. JB-5 batch 1 (11 companies now fetching directly instead of via resolver) should show on the next sweep — watch `python tools/sweep_recall.py` after the next Action run to confirm the lift.
7. **Stop conditions** — surface to BT: test/smoke red you can't resolve, spec ambiguity you'd have to guess at, CI red twice in a row, ai-empire Obsidian sync fires the Stop hook (restore `docs/Status/STATUS.md` from HEAD per `project_ai_empire_obsidian_sync_deletes.md`).

### Next BLs on the table

**#137 JB-58 ONBIS spike** (filed 2026-09-30) — now that the denominator lands (~700 London tech
employers, ADR-007), populate it with real company names via ONBIS. Spike answers: paid vs free
access, data-shape (does it give us name+city+size?), rate limits, adapter cost. BT to review the
spike before we build an adapter. Also NAICS-tag the registry so `tools/london_coverage.py` can
report per-NAICS numerators, not just an overall count.

**JB-47c Dayforce URL research** (not yet filed — supersedes the JB-47b-followup slot) —
JB-47b-followup #121+#122 proved the shipped subdomains and API path were all wrong via a
live workflow run. Each reverted `resolve` entry now carries a note with the exact failure.
Next step needs a browser + devtools to find real URLs, or confirm these companies aren't on
Dayforce. Not doable from sandbox.

**#5 JB-5 batch 2** — 148 `platform:"resolve"` entries remain after batch 1 (#125). Sweep proved
they don't have detectable ATS via careers-page probes — they're mostly LEDC-directory small
manufacturers using SEO-friendly marketing sites with a "Contact us" jobs page. Two productive
next moves: (a) new adapters for ttcportals/ultipro/scouterecruit (2/1/1 hits waiting) — **needs
live API discovery, sandbox can't help**, and (b) JB-46 LinkedIn scout at scale to re-classify
the 144 misses. Pick based on effort/yield.

**Commercialization backlog (from `docs/design/prototype/COMMERCIALIZATION_PLAN.md`, filed 2026-09-30):**
- **#134 JB-60 Tailor CV button** (P1, week 1 of the plan) — small `site/index.html` change, ready to build
- **#135 JB-61 Intake form** (P1, week 1) — static form + PIPEDA notice, ready to build
- **#136 JB-62 Regional licence config** (P2, week 5-6) — tenant JSON + `?tenant=slug` renderer
- Not yet filed: bot digest (offer 2), pitch deck (offer 3), tailoring SOP + prompt (week 1). Design template §2 has the full 8-week timeline.

**Next Getro probe iteration** (JB-59 v2) — first run (#129, run 36671740109) showed Getro migrated
most boards to custom domains. Need probe-v2 with real hostnames: MaRS `techjobs.marsdd.com`,
Communitech `jobs.communitech.ca`, Invest Ottawa `jobs.investottawa.ca`, DMZ, Volta, Platform
Calgary — grab actual URLs from a browser first, then re-probe.

**Not now** (deferred pending BT judgment): #85 JB-52 thin-JD enrichment (rate-limit risk),
#86 JB-53 multi-persona (touches UI Phase 2), #43/#87/#44 spikes (ADRs first), #81 JB-48 Workable
(blocked on Cloudflare 1015 for #98).

### Housekeeping notes (2026-09-28)
- Closed #82 JB-49 Breezy manually — shipped in PR #99 but PR body used `Refs #82` not `Closes #82`
  so GitHub auto-close never fired. **Future rule**: every PR body MUST use `Closes #NN` for the
  linking issue, or the ledger drifts. Consider adding a checklist item to PR template.

**Morning checklist template (after any merge):**
- Run `python tools/sweep_recall.py` — recall should rise (or at minimum, no regression)
- Run `python tools/compare_runs.py` — no company should drop to zero jobs
- Watch `sweep.yml` deploy; live board at https://arvint89.github.io/Attsis-jobboard/

### Tools you can run any time
`python tools/sweep_recall.py` · `python tools/compare_runs.py` · `python tools/probes/probe_communitech.py`
· `python tools/probes/probe_regional.py` (5–10 min) · `gh workflow run job-sweep` (manual refresh).

---

## 6. Work in flight
- Nothing uncommitted on `main`.
- 2026-09-30 overnight: 7 more PRs merged (#127, #128, #129, #130, #131, #132, #133) + 4 issues filed (#134-137). Ready for the next BL — top picks: **#134/#135 tailor button + intake form** (P1 commercialization, ready to build); **#137 ONBIS spike** (needs BT scope confirmation); **JB-5 batch 2** ttcportals adapter (needs live API discovery); **probe-getro v2** with real custom-domain URLs.
- **Release ops changed** (2026-09-29 with JB-27): to cut a release, edit `VERSION` + `CHANGELOG.md` in the same commit → merge to main → `auto-tag` workflow creates `v<VERSION>` on that commit automatically. No manual `git tag` step. See `VERSIONING.md`.
- **CI-diagnostic pattern now proven 4 times** (2026-09-29/30): `workflow_dispatch` + read-only script for live-network probes. References: `verify-dayforce.yml` (adapter validation), `resolve-sweep.yml` (bulk resolver sweep), `verify-promotions.yml` (post-promotion live check), `probe-getro.yml` (aggregator discovery). Reuse for any future sandbox-blocked probe.

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
VERSIONING.md       MAJOR.MINOR.BUGS policy; VERSION file drives auto-tag (current 0.11.0)
CHANGELOG.md        release history
engine/             ats.py · sources.py · jobfilter.py · geo.py · facets.py · build_board.py
                    companies.json (registry) · sources.json (boards) · smoke_test.py
site/               index.html (the whole UI) · data/jobs.json (generated)
tests/              41 unit tests
.github/workflows/  sweep.yml (fetch + deploy) · ci.yml (tests on PR) · tag.yml (auto-tag from VERSION, JB-27) · verify-dayforce.yml (on-demand adapter probe, JB-47b-followup)
docs/               ARCHITECTURE · SPEC · BUSINESS_PLAN · DIAGRAMS · UI_DESIGN ...
docs/decisions/     ADR-001 branching model  ← the workflow decision
docs/project/       GITHUB_PROJECT_SETUP · RELEASE_PROCESS · PROJECT_PLAN
```

### How to verify everything still works
```powershell
python -m pytest tests/ -q          # expect 246 passed
cd engine ; python smoke_test.py    # expect 11/11 PASS
```
