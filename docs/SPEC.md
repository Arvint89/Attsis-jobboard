# BT Job Board / Job-Search Copilot — Product Spec (PRD) v0.2
_Owner: BT · Build: Global Attsis AI · Status: Phase 1 in progress (POC) · Updated 2026-09-16_

## Vision
One low-token product that runs BT's whole job search end to end: take his CV,
find roles across employer ATSes, score them against **his** profile, show the
gaps, generate a tailored CV + cover letter, capture the JD, remind him to apply,
and carry each role through interview and follow-up — with interview prep built
from the CV + JD + gap analysis. The daily discovery loop costs ~0 model tokens;
tokens are spent only on the high-value writing steps (tailoring, prep) BT chooses.

This supersedes the daily LLM sweep and folds in the tooling the project already
proved by hand (resume_builder, gap analyses, tracker, workflow).

## Principles
- **CV-driven.** The candidate's CV defines the matching model — not a hardcoded
  keyword list. Change the CV → the scoreboard changes.
- **Deterministic where possible.** Search, filter, score, reminders = code.
  Generative only where judgment is needed = tailoring, cover letters, prep.
- **Honest by construction.** Carries the project Hard Rules: no overclaim, "11+
  years" only on the general discipline, confidentiality (device categories not
  product names), resume=evidence/cover=argument, never the short-form name.
- **PD Rules v1.0**: spec-first, test-first, smoke-gated (see PRODUCT_DEVELOPMENT_RULES.md).

## Capability map (full product) & phases
| # | Capability | What it does | Phase |
|---|---|---|---|
| C1 | **CV input** | Ingest CV (.docx/.md/.txt), hold as the source profile | **P1** |
| C2 | **CV parsing** | Extract titles, skills, domains, years → `profile.json` | **P1** |
| C3 | **Job search** | Fetch postings from each company's ATS JSON (no LLM) | **P1** |
| C4 | **Filter** | Rule engine: triggers, confirmers, boosters, exclusions, freshness | **P1** |
| C5 | **Scoreboard** | Website: ranked matches vs the CV, flags, why-it-matched | **P1** |
| C6 | **Gap analysis** | Per role: CV edges vs JD asks → Edge/Gap/Proof/Screen/Close | P2 |
| C7 | **JD capture** | Save the JD text + metadata per role (offline record) | P2 |
| C8 | **Tailored CV** | Generate a role-tailored CV via resume_builder + profile | P3 |
| C9 | **Cover letter** | Argument (not evidence) tailored to the JD + gaps | P3 |
| C10 | **Apply reminders** | Due-dates, follow-up timers, EI-log nudges | P4 |
| C11 | **Interview tracking** | Stage, type (screen/tech/behavioural/panel/final), interviewers | P4 |
| C12 | **Follow-up** | Thank-you prompts, status timers, next-step tracking | P4 |
| C13 | **Interview prep** | Build a prep pack from CV + JD + gaps (drills, Q&A, stories) | P5 |

## PHASE 1 — CV input → job listing → scoreboard (this build)
### Functional requirements
- **FR-1 Registry.** `companies.json`: name, ring 0–4, ATS platform, slug/tenant/
  site, careers_url, flags. `platform:"resolve"` = ATS not yet identified.
- **FR-2 Fetchers.** One adapter per ATS (Greenhouse, Lever, Ashby, SmartRecruiters,
  Recruitee, Workable, BambooHR, Rippling, Workday) → normalized 7-key job dict; a
  failing company never kills the run.
- **FR-3 CV input + parse.** `cv_parse.py` reads a CV file and produces/updates
  `profile.json` (title triggers, skill confirmers, domain boosters, exclusions,
  years). The engine consumes `profile.json` — the CV, not code, is the model.
- **FR-4 Filter/scorer.** `jobfilter.classify()` scores each posting against
  `profile.json` per keyword-model §1–§8: verdict ∈ {match ≥7, below, excluded},
  1–10 score, reasons, flags. Deterministic, no model call.
- **FR-5 Scoreboard.** Static `index.html` reading `site/data/jobs.json`: ranked
  matches, search, filter by ring/flag, below-threshold toggle, score badge,
  why-it-matched, apply link. Hostable on GitHub Pages.
- **FR-6 Automation.** GitHub Action runs fetch on weekday cron, commits data,
  deploys Pages — zero Claude tokens.

### Acceptance criteria (→ tests/)
- AC-1 Strong medical/mixed-signal role scores ≥9, verdict=match.
- AC-2 Power/substation "Electrical Engineer" excluded.
- AC-3 Technician / pure-software / off-profile excluded.
- AC-4 Remote FPGA/verification role reaches match (remote-portable track).
- AC-5 Posting >30 days excluded.
- AC-6 "Electrical" title with electronics body NOT excluded (Canada Rocket lesson).
- AC-7 Every ATS adapter returns the normalized 7-key contract; HTML stripped.
- AC-8 `cv_parse.py` turns a CV into a `profile.json` with non-empty titles+skills,
  and the scorer runs off that produced profile.
- AC-9 `smoke_test.py` builds the demo board end-to-end and exits 0.

### Non-goals (Phase 1)
No auto-apply, no tracker writes, no sending. Gaps/tailoring/cover/reminders/
interview are Phases 2–5. Not every ATS resolved day one (`resolve` is valid).

## Phase 1 corrections (2026-09-16, see INPUT_AND_MODEL.md)
- Add a **Setup page** so users input CV + cover letter (input surface was missing).
- Matching keywords derive from CV **+ cover letter**, domain-agnostic; electronics lists
  become a default seed. Company-attribute filtering stays in the registry.

## Success metric
Daily discovery drops from ~15k tokens to <500; scoreboard ranks roles by fit to
BT's *actual CV*; match quality ≥ the current LLM sweep on the same roles.

## Later phases (summary)
- **P2 Gaps + JD capture:** per-role Edge/Gap/Proof/Screen/Close from CV∩JD; store JD.
- **P3 Tailoring:** resume_builder-driven tailored CV + cover letter, Hard-Rule-guarded.
- **P4 Pipeline ops:** reminders, interview stages/types, follow-up timers, EI log.
- **P5 Interview prep:** prep pack from CV+JD+gaps (drills, Q&A, flagship stories).
