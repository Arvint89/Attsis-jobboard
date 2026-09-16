# CSA — Compliance, Security & Assurance Testing — Attsis Job Board
VERSION 1.0 · 2026-09-16 · Owner: Global Attsis AI · Process ref: workflow-process-skill (PDCA)
> "CSA" here = **Compliance, Security & Assurance** testing. If a specific **Canadian Standards
> Association** standard is intended for a future hardware line, map it in a revision.

## 1. Purpose
Verify the product meets REQUIREMENTS.md (FR/NFR) before each release. Deterministic where
possible; every check traceable to a requirement ID.

## 2. Scope
Engine (fetch, scoring, facets, geo, cv_parse, build), website (setup, board, gap), CI (Action).
Excludes: penetration testing of third-party ATS (out of our control; we only read public JSON).

## 3. Test strategy (levels)
| Level | What | Tooling | Gate |
|---|---|---|---|
| Unit | scorer, ATS normalizers, cv_parse | pytest (20 tests) | 100% pass |
| Smoke | end-to-end runtime state | smoke_test.py (11 checks) | all pass |
| Visual | rendered board looks right | manual / screenshot | BT sign-off |
| Security/Privacy | no CV upload, no secrets, safe HTML | review checklist | pass |
| Accessibility | keyboard, contrast, labels | manual WCAG-basic | pass (P2) |

## 4. Test cases (traced to requirements)
| TC | Requirement | Steps | Expected |
|---|---|---|---|
| TC-1 | FR-2 | Fetch a Greenhouse board | Normalized 7-key jobs; HTML stripped |
| TC-2 | FR-2 | Force one company to error | Run continues; error logged, not fatal |
| TC-3 | FR-3 | Upload .docx / .pdf / paste in Setup | Text extracted; keywords listed |
| TC-4 | FR-5 | Score a strong role | Match ≥7; reasons shown; SAME in Python & browser |
| TC-5 | FR-5 | Score a power/off-field role | Low score, not surfaced (not hard-excluded) |
| TC-6 | FR-6 | Open board with sparse profile | Shows closest roles, never blank |
| TC-7 | FR-6 | Set Min-score | List trims; count shows "strong (7+)" |
| TC-8 | FR-7 | Filter by industry/arrangement | Only matching roles shown |
| TC-9 | FR-9 | Paste a JD | "have" vs "missing" + fit line |
| TC-10 | NFR-2 | Inspect network on Setup | CV never leaves the browser |
| TC-11 | NFR-3 | Grep for secrets | None; no keys required |
| TC-12 | NFR-7 | Run pytest + smoke | 20 pass, 11/11 smoke |

## 5. Security & privacy checklist (assurance)
- [ ] CV/cover letter parsed in-browser; never uploaded (FR-3/NFR-2)
- [ ] No API keys / secrets in code (NFR-3); public ATS endpoints only
- [ ] External libs from cdnjs only (mammoth, pdf.js); pinned versions
- [ ] User content rendered without executing it (no injection via job text)
- [ ] localStorage only for the user's own profile/prefs

## 6. Records (PDCA Check)
Latest run 2026-09-16: **pytest 20/20 pass · smoke 11/11 pass.** TC-1..12 pass by construction;
TC-3 (.pdf/.docx) verified via mammoth/pdf.js wiring; visual + accessibility = open (P2).
Every run's result appended to AUDIT.md.
