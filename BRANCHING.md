# Branching & PR workflow — Attsis Job Board
_Rewritten 2026-09-21 (JB-37). Decision record: `docs/decisions/ADR-001-branching-model.md`._
_The old `develop` flow is retired — every PR since #26 went straight to `main`, so the docs now match reality._

## The model: trunk-based
```
main ──●────────●────────●──▶  deploys the live site on every merge (job-sweep Action)
        \      /  \      /
         feature/jb-NN-slug     one short-lived branch per issue, deleted after merge
```
- **`main`** is the only long-lived branch. It is **protected**: no direct pushes, every change is a PR,
  and the `tests + smoke` CI check must pass before merge. The rule applies to admins too.
- **One issue → one branch → one PR.** Branch types: `feature/`, `bugfix/`, `chore/`, `docs/`.
- **`production` branch:** not yet. Created at the first paying user (ADR-001 §5). Until then,
  releases are **tags** on `main` (`VERSIONING.md`).

## The loop (PowerShell, from the repo root)
```powershell
git checkout main; git pull origin main
gh issue list                                              # find the issue number once
gh issue develop NN --name feature/jb-NN-slug --checkout    # branch linked to the issue
git branch --show-current                                   # read it back
# ...edit...
python -m pytest tests/ -q
cd engine; python smoke_test.py; cd ..                      # also rebuilds demo data
cd site; python -m http.server 8000                         # UI changes: look at http://localhost:8000
git status --short                                          # only the files you meant to change
git add <files>
git commit -m "JB-NN: what and why"
git push -u origin feature/jb-NN-slug
gh pr create --fill --base main
gh pr merge --squash --delete-branch --auto                 # merges itself when CI is green
git checkout main; git pull origin main
```
`gh issue develop` links the branch to the issue, so merging the PR closes the issue.
Writing `Closes #NN` in the PR body does the same and is a good habit for readers.

## Rules learned the hard way
- **Branch first, then write code.** Uncommitted work follows you between branches (the JB-26 fix got stranded that way).
- **`git branch --show-current` before every commit** — a pasted block hides which branch you are on.
- **Branch names:** `jb-NN` only when open issue NN exists; the JB number is not the GitHub `#` number (JB-29 = #40).
- **PowerShell:** quote anything with `{}` `@` `$` for git: `git stash drop 'stash@{0}'`.
- **Stop at the first red line** — PowerShell keeps running the rest of a pasted block after an error.
- **Squash merges** leave local branches that `-d` refuses; confirm the PR is merged, then `-D`.
- **"Merged" is not "live"** — wait for the `job-sweep` run (`gh run list`) and Ctrl+F5.
- **Generated files** (`site/data/jobs.json`, `site/board_standalone.html`) are not tracked; build them
  locally with `cd engine; python build_board.py --demo`.
- **Local test data must exercise the feature** — add a case to `engine/fixtures.json` when needed.
