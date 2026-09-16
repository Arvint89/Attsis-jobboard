# Audit Log & Checklist — Attsis Job Board
VERSION 1.0 · Owner: Global Attsis AI · Process ref: workflow-process-skill (Monthly Audit + PDCA Act)
Standards habits: ISO 9001 §7.5 (doc control via Git), §9.3 (review), §10.2 (corrective action).

## Risk register (Black-Hat + Pre-Mortem)
| # | Risk | Likelihood | Impact | Guard / corrective action | Status |
|---|---|---|---|---|---|
| R1 | ATS JSON shape drift | Med | fewer/incorrect roles | adapters fail-soft per company; normalize centrally | open (monitor) |
| R2 | Sponsorship name mismatch (LMIA) | Med | mislabeled facet | fuzzy match + registry override; label the quarter | Phase 2.5 |
| R3 | Sparse CV extraction → 0 matches | Med | bad first run | closest-fallback; manual keyword edit | mitigated |
| R4 | Browser can't fetch ATS (CORS) | Certain | no live browser fetch | fetch in Python/GitHub Action | mitigated (by design) |
| R5 | Scorer divergence (Python vs browser) | — | inconsistent numbers | unified generic scorer | closed |
| R6 | BT time squeezed by Kepler onboarding | High | slippage | AI does all build; BT only pushes/approves | managed |
| R7 | Secrets/keys leakage | Low | security | none used; public endpoints; grep-checked | closed |

## Monthly audit checklist (first Monday)
- [ ] All docs have version + date (PDS, REQUIREMENTS, CSA_Testing, this file)
- [ ] All code changes have Git commit messages (document control)
- [ ] pytest + smoke green on main
- [ ] No secrets committed; deps pinned
- [ ] Backlog + Project board reflect reality; closed issues moved to Done
- [ ] Risks reviewed; any new failure mode added with a guard
- [ ] CHANGELOG updated for the release

## Audit runs (records)
| Date | pytest | smoke | Notes |
|---|---|---|---|
| 2026-09-16 | 20 passed in 0.66s | ALL SMOKE CHECKS PASSED (11/11) | v0.5 unified scorer; repo assembled as Attsis-jobboard |
