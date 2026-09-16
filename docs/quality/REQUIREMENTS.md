# Requirements Specification — Attsis Job Board
VERSION: 1.0 · DATE: 2026-09-16 · OWNER: Global Attsis (BT) · Traceability: FR/NFR IDs used by CSA_Testing.md

## Functional requirements
| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-1 | Registry maps each company to its ATS (platform, slug, industry, flags) | Must | Done |
| FR-2 | Fetch postings from each ATS public JSON; normalize to one job shape; fail-soft | Must | Done |
| FR-3 | Input CV + optional cover letter (.docx/.pdf/.txt/paste); extract keywords in-browser | Must | Done |
| FR-4 | Manual review/edit of extracted titles + skills; set name + home city | Must | Done |
| FR-5 | Score each role generically from the CV profile (single scorer, Python = browser) | Must | Done |
| FR-6 | Show ALL roles ranked; Min-score control; never a dead-end empty screen | Must | Done |
| FR-7 | Facet filters: work arrangement, country, industry (registry-driven) | Must | Done |
| FR-8 | Distance rings computed from the user's home city | Should | Done |
| FR-9 | JD capture + short gap analysis (have vs missing), free | Must | Done |
| FR-10 | Static website hostable on GitHub Pages; Action refreshes data on cron | Must | Done |
| FR-11 | Pipeline: stages Saved→Applied→Interviewing→Offer→Closed (+needs-action) | Must | Phase 2 |
| FR-12 | Deep gap analysis, tailored CV, cover letter, interview prep | Could | Phase 3–5 |
| FR-13 | Sponsorship facet backed by Canada LMIA list (quarterly + manual pull) | Could | Phase 2.5 |

## Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | Daily discovery costs <500 model tokens (deterministic code, not LLM browsing) |
| NFR-2 | CV never leaves the browser; profile stored per-device (localStorage) |
| NFR-3 | No hardcoded secrets; no keys needed (public ATS endpoints) |
| NFR-4 | UTF-8 everywhere; runs on Windows/Linux/GitHub runners |
| NFR-5 | Every score is explainable (reasons shown) — no black box |
| NFR-6 | Honest matching: no domain over-boost; works for any field (domain-agnostic) |
| NFR-7 | Tests (unit) + smoke gate must pass before release |

## Out of scope (v1)
Auto-apply, sending messages, writing to the .xlsx tracker, multi-user accounts, employer side.
