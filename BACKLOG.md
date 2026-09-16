# Job Board — Backlog (kanban)
_Maps 1:1 onto a GitHub Project board. Columns = Now · Next · Later · Icebox · Done._
_Last updated 2026-09-16._

## 🟢 NOW (before GitHub)
- [ ] **Clean up repo** (docs/ folder, backlog, diagrams) — *in progress*
- [ ] **Resolve a first batch of company ATS** (ZTR/BinSentry/VueReal/Tenstorrent already known;
      probe Nicoya, Miovision, Voltera, Geotab, Profound, Kepler) so a live run returns real roles
- [ ] **Host on GitHub Pages** (docs/GITHUB_SETUP.md) + create the GitHub Project board

## 🔵 NEXT
- [ ] **Phase 2 — Pipeline**: Job Board / Pipeline tabs; stages Saved→Applied→Interviewing→Offer→Closed;
      needs-action strip; board+export to tracker (spec: docs/SPEC_Phase2_Pipeline.md)
- [ ] **Expandable job card** (header + sections: Snapshot/Why/Gaps/JD/Contact/Actions — docs/UI_DESIGN.md)
- [ ] **Resolve remaining `resolve` companies** in engine/companies.json (one ATS probe each)
- [ ] **Deep gap analysis** (Edge/Gap/Proof/Screen/Close) — Pro feature

## 🟣 LATER
- [ ] **Phase 2.5 — LMIA sponsorship** data (quarterly label + manual pull — docs/SPONSORSHIP_DATA.md)
- [ ] **Phase 3 — Tailoring**: tailored CV + cover letter (resume_builder integration)
- [ ] **Phase 4 — Pipeline ops**: reminders, interview stages/types, follow-ups, EI log
- [ ] **Phase 5 — Interview prep** pack from CV + JD + gaps
- [ ] **Non-tech verticals** (accountant/CA, warehouse, etc.) via registry + seed
- [ ] **Multi-user / accounts** (keep design ready; build only when needed)

## 🧊 ICEBOX
- [ ] Employer / B2B side (JD → ranked candidate matches)
- [ ] Data product from pipeline outcomes ("what actually gets interviews")

## 🗂️ BACKLOG — small / UX polish
- [ ] **Salary on the job board** — show salary prominently on cards / as a sortable field _(BT, 16 Sep)_
- [ ] **Initials in the top header next to "Job Board"** — verify it renders reliably _(BT, 16 Sep)_
- [ ] Persist Min-score + filter choices (localStorage)
- [ ] Mobile layout pass
- [ ] Keyword review UX: group extracted keywords, show frequency, one-click "looks good"
- [ ] Distance: handle unknown cities gracefully; let user set home from a dropdown

## ✅ DONE (v0.1 → v0.5, see CHANGELOG.md)
- [x] Deterministic ATS engine (9 platform adapters) + company registry (29 companies)
- [x] Generic CV-driven scorer — **single source of truth** (Python + browser identical)
- [x] Facets: work arrangement / country / industry / sponsorship (JD-guess)
- [x] User-relative distance rings (from CV home city)
- [x] Setup page: CV + cover letter input (.docx/.pdf/.txt/paste), keyword extract + edit, name field
- [x] Board: shows all roles ranked, Min-score control, live in-browser re-scoring
- [x] Free JD capture + short gap analysis (per-card + paste-any-JD)
- [x] GitHub Action (cron fetch → commit → Pages); demo pool of 20 roles across 13 industries
- [x] PD Rules v1.0, SPEC, ARCHITECTURE, BUSINESS_PLAN, tests (20) + smoke (11) green
