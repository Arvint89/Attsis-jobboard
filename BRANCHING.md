# Branching strategy — Attsis Job Board
Goal: the **product (deployed) branch is separate from work branches**, so the live site is
always stable and never shows half-finished work.

## Branches
| Branch | Purpose | Deploys? | Protected? |
|---|---|---|---|
| **main** | **PRODUCT / release** — always stable & deployable | ✅ GitHub Pages deploys from here | yes (no direct pushes; PRs only) |
| **develop** | integration — where features/fixes come together | no | no |
| **feature/<name>** | one new feature; branch off `develop` | no | no |
| **bugfix/<name>** | one bug fix; branch off `develop` | no | no |
| **hotfix/<name>** | urgent fix to live product; branch off `main` | no | no |

## Flow
```
feature/x ─┐
bugfix/y  ─┼─► develop ──(release)──► main ──► Pages (live)
hotfix/z ──────────────────────────► main (+ back-merge to develop)
```
1. Work on a `feature/*` or `bugfix/*` branch off `develop`.
2. Open a Pull Request into `develop`; tests + smoke must pass; `code-review` before merge.
3. When `develop` is release-ready, PR `develop → main`, tag a version (see VERSIONING.md).
4. Pushing to `main` triggers the Action → live site updates.

## One-time setup (run once)
```bash
git checkout -b develop        # create the integration branch
git push -u origin develop
git checkout main              # go back to product branch
```
Then on GitHub: **Settings → Branches → Add branch protection rule** for `main`
(require a PR before merging; require status checks). That enforces "product branch is different."

## Everyday
```bash
git checkout develop
git checkout -b feature/salary-column     # start work
# ...edit, commit...
git push -u origin feature/salary-column  # open a PR into develop on GitHub
```
> Beginner note: you can start simple — commit to `develop`, and only merge to `main` for
> releases — and adopt full feature branches as the project grows. The key rule now:
> **`main` = live product; do daily work off `main`.**
