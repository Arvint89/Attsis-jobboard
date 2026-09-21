# Git Workflow Audit — Attsis-jobboard
**Date:** 2026-09-21 (revised same day after re-reading HANDOFF)
**Scope:** Read-only audit of git workflow. No files edited, no writing git commands run.
**Sources cited:** `BRANCHING.md`, `CLAUDE.md`, `HANDOFF.md`, `docs/decisions/ADR-001-branching-model.md`, `.aider.conf.yml`, `.github/workflows/ci.yml`, live `git status` / `git log` / `git branch -vv` / `git stash list`.

---

## 1. Branching model
**Adopted: trunk-based (Option C from ADR-001).**

- One long-lived branch: `main`. One short-lived branch per issue: `feature/jb-NN-slug`, `bugfix/jb-NN-slug`, `hotfix/*`, branched off `main`, merged back via PR, **deleted after merge** — `docs/decisions/ADR-001-branching-model.md:200-206` and `ADR-001:229-232`.
- `develop` is **retired** — `ADR-001:233`, reinforced by `HANDOFF.md:109`.
- **Deploys:** every push to `main` triggers `.github/workflows/sweep.yml` → live site — `ADR-001:30-38`, `HANDOFF.md:39`.

## 2. Production / commercial branch
- **Does not exist yet.** Named trigger for creation: first paying user, or a second environment that must not break — `ADR-001:235-238`.
- Migration cost when triggered: **one command** — `git checkout -b production main && git push -u origin production` — `ADR-001:162-163`.
- Interim: releases marked with **tags** (VERSIONING.md policy) — `ADR-001:234`.

## 3. Who runs git + working agreement
- **BT runs all git himself** (PowerShell on Windows), copy-pasting commands Claude gives — `CLAUDE.md:19-21`, `HANDOFF.md:115`.
- **Working agreement (BT, 2026-09-18):** "Review before every action. Each step is described — what changes, which files, which commands — and approved *before* it runs. No batching of unreviewed changes." — `ADR-001:240-244`, repeated at `HANDOFF.md:114-115`.
- Issue-first git: pull main → branch → Claude edits → BT commits/pushes/PRs → `Closes #NN` — `CLAUDE.md:66-68`.

## 4. CI: what exists vs written-but-not-merged

| State | What | Evidence |
|---|---|---|
| Merged & running | `sweep.yml` — fetches jobs + deploys to Pages on push to main | `ADR-001:30-38`; git log shows PRs #24-#35 all deployed via this path |
| **Written, NOT committed** | `.github/workflows/ci.yml` — 41 tests + 11 smoke checks on every PR | File exists at `.github/workflows/ci.yml` but `git status` shows it as `??` untracked; `HANDOFF.md:132-133` says "written; not committed yet" and "← YOU ARE HERE: commit + merge CI (JB-28)" |
| Written but not enforcing | Branch protection on `main` | `ADR-001:216` lists as follow-up; `HANDOFF.md:136` shows unchecked |

## 5. Current git state (verified live)

- **Current branch:** `chore/jb-28-ci` — matches "YOU ARE HERE" in `HANDOFF.md:133`.
- **Branch tip:** `cd67561` (identical to `main`) → branch was created but **no commits made yet**.
- **Uncommitted / untracked on `chore/jb-28-ci`:**
  - Modified: `.gitignore`, `HANDOFF.md`
  - Untracked: `.aider.conf.yml`, `.github/workflows/ci.yml`, `CLAUDE.md`, `docs/AIDER_WORKFLOW.md`, `docs/decisions/` (the whole ADR folder), `docs/project/HANDOFF_2026-09-16_archived.md`, `memory/`
  - **JB-28 commit scope is deliberately narrow.** `HANDOFF.md:156` prescribes `git add .github/workflows/ci.yml docs/decisions/ADR-001-branching-model.md HANDOFF.md` — **only 3 files**. The rest (`.aider.conf.yml`, `CLAUDE.md`, `docs/AIDER_WORKFLOW.md`, `memory/`) is intentionally left untracked and will be handled in a separate PR, not folded into JB-28.
  - Recommended step-0 (per `HANDOFF.md:148`): `git stash push -m "JB-26 map fix - park before CI work"` to park dirty tree before switching to `main` and cutting the JB-28 branch.
- **Stash:** `stash@{0}: On feature/jb-3b-ledc-scraper: JB-26 map fix - park before CI work` — exactly matches `HANDOFF.md:148` + §6. The map fix was written directly into the working tree without a branch and got stranded on `feature/jb-3b-ledc-scraper`; the stash is one of two backups.

### Live branch listing
- Local: `bugfix/jb-19-bamboohr-descriptions`, `bugfix/jb-25-geocoder`, `chore/jb-28-ci` (current), `develop`, `feature/jb-20-per-company-cap`, `feature/jb-22-distance-filter`, `feature/jb-23-search-row`, `feature/jb-26-company-map`, `feature/jb-3-board-sources`, `feature/jb-3b-ledc-scraper`, `main`
- Remote: same set of branches all present on `origin/*` — nothing deleted yet.

## 6. Contradictions

| Doc / config | Claim | Reality / conflict |
|---|---|---|
| `BRANCHING.md:8-12` | Long-lived branches: `main` + `develop`; feature branches off `develop`; PR into `develop`; only release `develop → main` | **STALE.** `ADR-001:6` explicitly supersedes BRANCHING.md; `HANDOFF.md:231` marks it "⚠️ STALE" and rewrite is pending |
| `BRANCHING.md` | `feature → develop → main` | Git history shows **every recent PR (#24-#35) merged straight into main** — confirmed in `git log --oneline -15` and `ADR-001:14-17` |
| `BRANCHING.md:11` | "branch off develop" | `CLAUDE.md:66` says "pull main → branch `feature/jb-NN-slug`". ADR-001 sides with CLAUDE.md |
| `develop` branch existence | `ADR-001:233` says "retired" | `develop` still present locally AND on remote (`origin/develop`); has never been deleted. `git branch -vv` shows it at `83f3889` — the same 14-behind position `ADR-001:16` described |
| Stale feature branches | `HANDOFF.md:137` + `:188` say "7 fully-merged branches + `develop`" (8 safe to delete now); `feature/jb-3b-ledc-scraper` holds unmerged LEDC work and waits until PR #36 merges. `ADR-001:214` slightly older wording ("8 fully-merged stale branches") — HANDOFF is the current count. | All 9 branches still present locally + remote. Safe-to-delete-now (8): `bugfix/jb-19-bamboohr-descriptions`, `bugfix/jb-25-geocoder`, `feature/jb-20-per-company-cap`, `feature/jb-22-distance-filter`, `feature/jb-23-search-row`, `feature/jb-26-company-map`, `feature/jb-3-board-sources`, `develop`. **Wait for PR #36 first:** `feature/jb-3b-ledc-scraper`. |
| `.aider.conf.yml` | No branching claims; only model + auto-commit config | `auto-commits: true` at line 19 — **conflicts with the working agreement** at `ADR-001:240-244`: "Review before every action... approved *before* it is executed. This applies to Claude's file edits as well." Aider will commit without review by default. (Config drift, not a doc contradiction — flagged because it violates the human-in-loop rule.) |

## 7. Ordered remaining workflow steps before JB-5 resumes
Source: `HANDOFF.md:131-141` — the phase checklist.

1. ✅ ADR-001 written & accepted (done, but file itself is uncommitted)
2. ✅ `ci.yml` written (done, but uncommitted)
3. ← **YOU ARE HERE** — commit + merge CI (JB-28)
4. Merge PR #36 (LEDC London scraper)
5. Land the JB-26 map fix (currently stashed at `stash@{0}` — restore only `site/index.html`, per `HANDOFF.md:176-177`)
6. Enable branch protection on `main` (needs CI merged first, per `ADR-001:216`)
7. Delete 7 fully-merged branches + `develop` (local AND remote); `feature/jb-3b-ledc-scraper` only AFTER PR #36 merges — `HANDOFF.md:137`
8. Add `.gitattributes` to stop CRLF churn
9. Rewrite `BRANCHING.md` + write `WORKFLOW.md`
10. GitHub Project board
11. **THEN** JB-5 coverage (product work resumes)

## 8. Guesses / things I could not verify from disk
- **PR #36 mergeability** — HANDOFF.md says PR #36 is open, but I have no PR data on disk. Would need `gh pr list`.
- **`ci.yml` will actually pass** — file exists and tests are listed as 41/41 + 11/11 passing per `HANDOFF.md:50-51`, but I did not run them.
- **Second stash backup outside the repo** — `HANDOFF.md:172-174` mentions a file copy "outside the repo, made 2026-09-18". Its existence is unverifiable from within the repo.

---

## Summary for Claude Desktop
- Workflow: trunk-based (Option C from ADR-001). One `main`, short-lived issue branches, tags for releases, `production` branch deferred until first paying user.
- Right now BT is mid-workflow-cleanup — 8 unfinished steps before product work (JB-5) resumes. Current step: commit CI (JB-28).
- The JB-28 commit deliberately includes only 3 files (`ci.yml`, `ADR-001`, `HANDOFF.md`). `CLAUDE.md`, `.aider.conf.yml`, `docs/AIDER_WORKFLOW.md`, and `memory/` are intentionally deferred to a later PR — not lost, just staged separately.
- BRANCHING.md is stale — do not follow it. ADR-001 is the source of truth.
- Working agreement: BT reviews and approves every action before Claude runs it. BT runs git himself.
