# GitHub Project setup — how the kanban gets created
_Claude can't reach GitHub from the session, so this is done once by you (or by Claude in a
session where the GitHub connector is authenticated)._

## Fastest: the script (needs GitHub CLI `gh`, authenticated)
```bash
gh auth login                      # once
OWNER=Arvint89 REPO=Attsis-jobboard bash setup_github_project.sh
```
This creates every **label**, **milestone**, and **issue** from the CSVs and a **Project** named
"Attsis Job Board". Then open the Project → add a **Board** view with columns **Backlog · Now ·
Next · Done** and drag issues in (or set the Status field).

## Manual (no CLI)
1. Repo → **Issues → Labels** → add the rows from `docs/project/LABELS.csv`.
2. Repo → **Issues → Milestones** → add the rows from `docs/project/MILESTONES.csv`.
3. Create issues from `docs/project/ISSUES.csv` (title, body, labels, milestone).
4. Repo → **Projects → New project → Board** → name it "Attsis Job Board" → add columns
   **Backlog / Now / Next / Done** → add the issues; put JB-1..JB-4, JB-17 in **Now**.
5. The board mirrors `BACKLOG.md` and `docs/project/PROJECT_PLAN.md`.

## Where the plan lives
- Plan / sprint / milestones: `docs/project/PROJECT_PLAN.md`
- Kanban source: `BACKLOG.md` (root)
- Diagrams: `docs/DIAGRAMS.md` (GitHub renders the Mermaid)
- Quality: `docs/quality/` (PDS, Requirements, CSA_Testing, Audit)
