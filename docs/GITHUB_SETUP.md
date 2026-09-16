# Host the board on GitHub Pages — exact steps (do once)

Result: a live URL you can bookmark, that refreshes itself on a weekday schedule,
with **zero Claude tokens** for the daily run. I can't push for you (the GitHub
connector isn't authenticated in this session), so here are the precise steps.

## What you're pushing
This whole folder (`2026-09-16_Job_Board_Website/`) is the repo root:
```
engine/   site/   tests/   .github/workflows/sweep.yml   *.md   .gitignore
```

## Option A — new dedicated repo (cleanest)
```bash
# in this folder:
cd "<path to>/2026-09-16_Job_Board_Website"
git init
git add .
git commit -m "Job board v1: setup + board + facets + gap analysis"
git branch -M main
git remote add origin https://github.com/Arvint89/bt-job-board.git   # create this empty repo on github.com first
git push -u origin main
```
Then on github.com → the repo:
1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Actions → General → Workflow permissions: Read and write.**
3. **Actions tab → “job-sweep” → Run workflow** (first run; after that it's the weekday cron).
4. Your board is live at **https://arvint89.github.io/bt-job-board/site/** (or set Pages to serve `site/`).

## Option B — inside your existing ai-empire repo
Put this folder under a subpath and push as usual; point Pages at `.../site/`.

## First run vs demo
Until the Action runs, `site/data/jobs.json` holds the **demo** data. The first
Action run replaces it with **live** roles from the resolved companies (ZTR, BinSentry,
VueReal, Tenstorrent, Canadian Solar, Canada Rocket, e-Zinc…). Companies still marked
`resolve` in `engine/companies.json` are skipped until their ATS is identified once.

## Notes
- The Setup page (CV/cover-letter input, gap analysis) runs entirely in the browser —
  it works the moment the page is hosted; no server needed.
- Your profile lives in your browser (localStorage), so it stays on your device.
- Cost: GitHub Actions + Pages are free at this usage. Model tokens/day: zero.
