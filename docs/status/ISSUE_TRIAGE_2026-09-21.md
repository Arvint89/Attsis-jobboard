# Issue triage — 2026-09-21
_Dated snapshot. Reviewed all 16 open issues against the code, the live board (65 roles, 27 visible) and the
daily sweep log (last 3 runs). Decisions for BT to apply on GitHub. Design context: ADR-002._

## What changed our priorities today
- **The board found 1 of the sweep's 19 recent 7+ roles.** 16 of the misses are employers the board has
  never heard of → discovery + resolution (ADR-002) is the core product problem, not a side issue.
- **Communitech: sweep sees ~263 results, board keeps 1.** Cause unknown → measure first (JB-30a).
- **Salary shows on 5 of 65 roles** — the gap is extraction, not the card (#6 re-scoped).
- **LEDC is live** (3 London roles appeared after PR #36).

## Verdicts on the 16 open issues

| # | Issue | Verdict | Reason / action |
|---|---|---|---|
| #4 | JB-4 First live fetch returns real roles | **Close — done** | Live board: mode live, 65 roles, daily. Comment: "Done — live since 2026-09-17; 65 roles on 2026-09-21." |
| #5 | JB-5 Resolve remaining companies | **Keep — re-scope, P0** | Becomes the resolver (ADR-002). First brief: JB-5a detect_ats. Retitle: "JB-5 Company resolver: resolve the 22 + seeded employers". |
| #6 | JB-6 Salary on cards | **Keep — re-scope, P1** | Only Getro supplies salary. Scope: parse pay from description text (Greenhouse etc.), salary chip on card, sanity-check period (GHD "$102k/hour"), label "no salary" when sorting. |
| #7 | JB-7 Initials render reliably | **Verify, then close** | Code exists (index.html L174/297/339). Load a CV on the live site; if initials show, close. |
| #8 | JB-8 Persist filters + min-score | **Keep — Next, P2** | Only the profile is saved in localStorage; filters reset. Small, good Aider task. |
| #9 | JB-9 Board + Pipeline tabs | **Later** | Built for BT's own hunt; valuable for paying users. Park until coverage is fixed. |
| #10 | JB-10 Stage model + kanban | **Later** | Same as #9. |
| #11 | JB-11 Needs-action strip | **Later** | Same as #9. |
| #12 | JB-12 Export to xlsx tracker | **Close** | Tied to BT's personal spreadsheet. If needed, reopen as generic "Export CSV". |
| #13 | JB-13 Expandable job card | **Next, P2** | Real UX value; after coverage. |
| #14 | JB-14 Deep gap analysis (Pro) | **Later** | Paid tier; needs pricing + an LLM decision (would reuse ADR-002 router). |
| #15 | JB-15 LMIA sponsorship data | **Later — but raise value** | The LMIA employer list is also a **discovery seed** (ADR-002 §2.1). |
| #16 | JB-16 Non-tech vertical | **Later** | Depends on the resolver: a new vertical is mostly new seeds. |
| #17 | JB-17 CSA testing pass + audit | **Re-scope** | CI now does routine tests. Retitle: "Full CSA pass before v1.0 release". |
| #18 | JB-18 Accessibility + mobile | **Next, P2** | Needed before other users. |
| #32 | JB-27 auto-tag | **Keep — workflow phase** | Tags are the release mechanism (ADR-001). Fix label `enhancement` → `type:chore`. |

## New issues to create

| New | Title | Labels | Brief |
|---|---|---|---|
| JB-29 | Map: labelled Home marker + CV-driven company greens | type:bug area:site priority:P1 | code in `stash@{0}` |
| JB-30 | Sources: funnel stats + Getro resilience/pagination | type:bug area:engine priority:P1 | `docs/briefs/JB-30a-…`, `JB-30b-…` |
| JB-31 | Company discovery seeds + LLM router (ADR-002) | type:feature area:registry priority:P1 | after JB-5a/5b |
| JB-32 | Spike: Adzuna API as an aggregator source | type:spike area:engine priority:P2 | later |
| JB-33 | Job Bank Canada: channel coverage per company + access spike | type:spike area:registry priority:P2 | `docs/project/issue_bodies/JB-33.md` |

JB-5a (detect_ats) is part of #5 — use `Refs #5`, and `Closes #5` only when the resolver is done.

**BT decision (2026-09-21):** every company is in scope; "hiring" is a filter on the board, not a reason to exclude a company from the registry. Issue bodies for the new issues: `docs/project/issue_bodies/`.

## Order of work
1. Workflow phase leftovers: JB-29 map fix → branch protection → delete stale branches → `.gitattributes`
   → BRANCHING/WORKFLOW docs → JB-27 tags.
2. **JB-30a** funnel stats (measure) → **JB-30b** Getro fix.
3. **JB-5a** detect_ats → **JB-5b** deterministic resolver on the 22.
4. JB-31 seeds + router (after ADR-002 is accepted) → JB-32 Adzuna spike.
5. #6 salary → #8 filters → #13 / #18.

## Delegating to Aider
Every code task is a brief in `docs/briefs/` (contract: signature, real data, failing test). One brief =
one issue = one branch = one PR. Aider (Groq gpt-oss-20b) does best with exactly this: one small,
fully specified change. Loop:
```powershell
git checkout main; git pull origin main
git checkout -b bugfix/jb-30-source-funnel
aider engine/build_board.py tests/test_build.py --read docs/briefs/JB-30a-source-funnel-stats.md
#  in aider:  Implement docs/briefs/JB-30a-source-funnel-stats.md exactly. Add the section-8 tests first.
python -m pytest tests/ -q; cd engine; python smoke_test.py; cd ..
git diff                     # read it before committing (auto-commits are off)
git add engine/build_board.py tests/test_build.py
git commit -m "JB-30a: per-source funnel stats in jobs.json"
git push -u origin bugfix/jb-30-source-funnel      # PR with "Refs #NN", CI must be green
```
