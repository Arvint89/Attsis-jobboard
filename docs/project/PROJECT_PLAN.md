# Attsis Job Board — Project Plan
VERSION 1.0 · 2026-09-16 · Owner: BT · Builder: Global Attsis AI · Cadence: 1-week sprints

## Team & capacity (honest, solo founder + AI)
| Who | Role | Capacity/sprint | Notes |
|---|---|---|---|
| BT | Direction, review, approvals, the GitHub push, real-world testing | ~3–5 hrs | family boundary 16:30; Kepler starts 5 Oct |
| Global Attsis AI | Build, test, docs, fetch/scoring | high | runs the deterministic work |

> Rule (Founder-Time lens): if the AI can do it, BT shouldn't. BT's items = push, approvals, testing.

## Milestones
| ID | Milestone | Success condition | Target |
|---|---|---|---|
| M0 | **v1 Live** | Board hosted on GitHub Pages; Setup→Board works for BT | Sprint 1 |
| M1 | **Real data** | Resolved ATS for the near companies; a live run returns real roles | Sprint 2 |
| M2 | **Pipeline** | Job Board/Pipeline tabs; stages; needs-action; export to tracker | Sprint 3–4 |
| M3 | **Close-the-gap** | Deep gap analysis + tailored CV/cover (Pro) | Sprint 5–6 |
| M4 | **Breadth** | LMIA sponsorship (2.5); first non-tech vertical seed | later |

## Sprint 1 (NOW) — Goal: "Attsis Job Board is live and real for BT."
| Pri | Action item | Est | Owner | Depends on |
|---|---|---|---|---|
| P0 | JB-1 Host on GitHub Pages (push + Pages + Action) | S | BT+AI | repo uploaded |
| P0 | JB-2 Create GitHub Project board + import plan/labels/issues | S | BT+AI | repo uploaded |
| P0 | JB-3 Resolve first ATS batch (ZTR, BinSentry, VueReal, Tenstorrent + probe Nicoya, Miovision, Voltera, Geotab, Profound, Kepler) | M | AI | — |
| P0 | JB-4 First live fetch returns real roles; verify board visually | S | AI+BT | JB-1, JB-3 |
| P1 | JB-17 CSA testing pass + audit log entry | S | AI | — |

Sprint load ≈ 70% capacity (buffer for interrupts). Stretch: JB-6 salary display.

## Definition of Done (per item)
- [ ] Code reviewed; tests + smoke gate green
- [ ] Docs/CHANGELOG updated
- [ ] BT sign-off (for anything user-facing or that touches GitHub)

## Key dates
| When | Event |
|---|---|
| Sprint 1 start | On repo upload |
| Mid-sprint | Live-fetch check |
| Sprint 1 end | v1 live on Pages, demo to BT |
| Ongoing | Kepler starts 5 Oct — protect BT time around it |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| ATS endpoints block/drift | fewer live roles | fail-soft adapters; registry + JD fallback |
| BT time squeezed (Kepler onboarding) | slippage | AI does all build; BT only pushes/approves |
| Sponsorship data ambiguity | mislabeled facet | label the LMIA quarter; "sponsored before" wording |
