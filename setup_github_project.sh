#!/usr/bin/env bash
# One-shot: create labels, milestones, issues, and a Project board from the CSVs.
# Prereq: GitHub CLI installed + authed (`gh auth login`), run inside the repo after pushing.
# Usage:  OWNER=Arvint89 REPO=Attsis-jobboard bash setup_github_project.sh
set -euo pipefail
: "${OWNER:?set OWNER}"; : "${REPO:?set REPO}"
DIR="docs/project"

echo "== labels =="
tail -n +2 "$DIR/LABELS.csv" | while IFS=, read -r name color desc; do
  gh label create "$name" --color "$color" --description "$desc" --force
done

echo "== milestones =="
tail -n +2 "$DIR/MILESTONES.csv" | while IFS=, read -r title desc; do
  gh api "repos/$OWNER/$REPO/milestones" -f title="$title" -f description="$desc" >/dev/null 2>&1 || echo "  (milestone exists: $title)"
done

echo "== issues =="
tail -n +2 "$DIR/ISSUES.csv" | while IFS=, read -r title body labels milestone; do
  labs=$(echo "$labels" | tr ' ' ',')
  gh issue create --title "$title" --body "$body" --label "$labs" --milestone "$milestone" || true
done

echo "== project board =="
gh project create --owner "$OWNER" --title "Attsis Job Board" || echo "  (project may already exist)"
echo "Now: open the Project, add a Board view with columns Backlog/Now/Next/Done, and add the issues."
echo "== branching (product branch = main; work on develop) =="
git checkout -b develop 2>/dev/null || git checkout develop
git push -u origin develop 2>/dev/null || echo "  (develop exists)"
git checkout main
echo "Set branch protection on main in Settings > Branches (see BRANCHING.md)."
echo "Done."
