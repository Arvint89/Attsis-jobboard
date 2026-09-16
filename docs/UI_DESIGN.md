# UI Design — options considered & the proposed listing layout
_Draft for BT review · 2026-09-16_

## The question: what UI patterns were considered?
Five common patterns for a job board, and when each wins:

1. **Scannable card list** (what's built now). One card per role: score badge + title +
   company + facet chips + why-matched. **Wins for discovery** — you skim many roles fast,
   ranked by fit. **Loses** when you want the *full* detail of one role (cards stay shallow
   to stay skimmable).
2. **Dense table / spreadsheet grid.** Columns = company, title, score, arrangement, etc.
   **Wins for sorting/comparing** many roles on the same attribute. **Loses** on readability
   (long titles, JD text don't fit a cell) and on mobile.
3. **Master–detail (list + detail pane).** A slim list on the left, full record on the right.
   **Wins** when you review roles one by one with everything visible. **Loses** screen space
   on narrow windows; heavier to build.
4. **Expandable / accordion cards.** The card list, but each card opens in place to reveal a
   full labeled record (header always visible, content below on expand). **Wins**: keeps the
   fast scan AND gives full detail on demand, one file, works on mobile. This is the natural
   upgrade of what's built.
5. **Kanban board.** Columns by stage. **Wins for the Pipeline tab** (Saved/Applied/…), not
   for discovery.

## Why the current choice, and where it's going
Discovery's job is *triage a lot, fast* → the **scannable card list** is right, and it stays.
Your ask ("headers and content below") is exactly pattern **4 — expandable cards**: keep the
skimmable header, reveal a structured record underneath when you click. So the plan is:
**card list (scan) → expand a card into a full labeled record (detail)** — no separate page,
no loss of the scan. The Pipeline tab uses pattern **5 (kanban by stage)**.

## Proposed listing layout (expandable card)
```
 ┌───────────────────────────────────────────────────────────┐
 │ [9]  Senior Electrical Engineer            ▸ expand         │  <- header (always visible)
 │      Natus Medical · Oakville · Ring 2 · hybrid · medical   │
 ├───────────────────────────────────────────────────────────┤  (below, on expand:)
 │  SNAPSHOT   arrangement · country · industry · sponsorship · salary · posted
 │  WHY IT FITS   matched skills · scoring reasons
 │  GAPS         Edge / Gap / Proof / Screen / Close     (Phase 2)
 │  JOB DESCRIPTION   captured JD text                   (Phase 2 capture)
 │  CONTACT      recruiter / hiring manager / apply link (where available)
 │  ACTIONS      Save · Mark applied · set stage         (Phase 2 pipeline)
 └───────────────────────────────────────────────────────────┘
```
Header = title · company · score, then the one-line sub (location/ring/arrangement/industry).
Everything else moves into labeled sections **below**, revealed on expand.

## Field availability (honest — some are later phases)
| Section | Source | Available |
|---|---|---|
| Title, company, location, apply URL, posted, salary | ATS JSON | **now** |
| Score, why-it-fits (matched skills, reasons) | jobfilter | **now** |
| Facets (arrangement/country/industry/sponsorship) | facets.py + registry | **now** |
| Full JD text | ATS `content` / JD capture | **Phase 2** (fetch already returns it; just store + show) |
| Gaps (Edge/Gap/Proof/Screen/Close) | CV ∩ JD analysis | **Phase 2** |
| Contact (recruiter/hiring mgr) | rarely in ATS JSON; manual/LinkedIn | **partial / manual** |
| Actions (save/stage) | pipeline (localStorage) | **Phase 2** |

## Recommendation
Ship the **expandable-card record** as part of Phase 2 (it pairs naturally with JD capture,
gaps, and the pipeline actions that fill the new sections). Building the empty shells now,
before those data sources exist, would show blank sections — so the layout lands **with** the
data that fills it. Header + facets + why-it-fits can expand today; JD/Gaps/Contact/Actions
populate as Phase 2 delivers them.
