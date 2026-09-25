# ADR-006 — Production branch activated

- **Status:** ACCEPTED
- **Date:** 2026-09-24
- **Deciders:** BT (owner)
- **Extends:** [ADR-001 §8](ADR-001-branching-model.md) — the "trunk-based now, production branch when it earns its place" trigger is now fired.

---

## 1. Context

ADR-001 (2026-09-18) chose trunk-based on `main` and specified a production
branch that would be **added at a named trigger**:

> the first time real users are served — i.e. the first paying user, or any
> second environment that must not break.

Six days later, that trigger fired for a different reason than "paying user":
the next work cycle (see `HANDOFF.md` §5 and the plan file
`atomic-chasing-aurora.md`) adds ~10 new coverage/UX build-levels — new ATS
adapters (Dayforce, Workable, Breezy), registry seeding at scale, a LinkedIn
scout, and a curated titles+skills DB. None of these are individually risky,
but landing them one at a time on a branch that deploys on merge would let a
single broken adapter blank the live site for hours.

BT ruled: **"none of this goes to the main branch and changes the existing
website till we understand how much of these affects it"** and
**"we need a separate production branch that doesn't get affected by the
build"**. That is the ADR-001 trigger — "any second environment that must not
break" — met explicitly.

---

## 2. Decision

Activate ADR-001 Option D (production branch). Effective 2026-09-24.

```
feature/jb-NN-slug ──▶  main  ──(release PR)──▶  production  ──deploys──▶  live site
       (dev)          (integration)                (stable)
```

- **`main`** = integration. All feature branches PR into main. CI runs
  (`tests + smoke`). Merging to main does **not** deploy.
- **`production`** = stable, deploys the live site. Only reachable via a PR
  from `main` (a "release PR"). Cadence: as often as we like, but each
  release is a deliberate, reviewed act.
- **Rollback**: a hotfix branches off `production`, PRs back into
  `production` (and cherry-picks or PRs into `main`).

---

## 3. What changed (migration executed 2026-09-24)

1. **Created the production branch** off main at commit `7b9e2a6` (verified
   local + remote are at the same SHA):
   ```
   git checkout -b production main && git push -u origin production
   ```
2. **Branch protection on `production`** (via `gh api PUT
   repos/Arvint89/Attsis-jobboard/branches/production/protection`):
   - Required status checks: `tests + smoke`
   - `enforce_admins: true`
   - `allow_force_pushes: false`
   - `allow_deletions: false`
   - No PR review requirement yet (BT is solo owner)
3. **Rerouted the deploy** — `.github/workflows/sweep.yml`:
   - `on.push.branches: [main]` → `[production]`
   - `actions/checkout@v4` pinned to `ref: production` so cron and manual
     `workflow_dispatch` runs also build from production, not the default
     branch
4. **ADR-001 §8** references this ADR as the trigger event.

---

## 4. Working agreement

- Feature work: `git switch main && git pull && git switch -c feature/jb-NN-slug`.
- Release: **PR from `main` into `production`** with a description of every
  merged BL since the last release. Squash-merge.
- Never push directly to `production`. Branch protection enforces this.
- The 5-min cron `sweep.yml` continues to run — it just fetches from the
  production checkout. Sweep runs are stateless (jobs.json is never
  committed), so cron never causes drift between main and production.
- `HANDOFF.md` and `BRANCHING.md` updated in the same cycle.

---

## 5. Why now, not later

The ADR-001 trigger was written as "paying user". BT's clarification made it
broader: **any second environment that must not break**. The coverage cycle
is that second environment. Waiting for a paying user first would mean
learning the release-PR workflow *while* under production pressure, instead of
while there is still slack.

---

## 6. Consequences

- **Cost:** one extra PR per release. Small; deliberate.
- **Benefit:** main can absorb broken/experimental adapters without touching
  the live site. Release PRs make what changed at each promotion explicit.
- **Follow-ups:**
  - Update `BRANCHING.md` to document `main → production` release PRs.
  - Add ADR-001 §8 cross-reference to this ADR.
  - First release PR (main → production) should be the sweep.yml routing
    change itself; from that promotion on, the model is active.
