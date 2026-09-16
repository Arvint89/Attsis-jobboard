# Phase 2 Spec — Pipeline & Status Tracking
_Product: BT Job Board · PD Rules v1.0 (spec-first) · Draft for BT review · 2026-09-16_

## Problem
The board today only shows **discovered** roles ranked by fit. Once you act on a
role (apply, interview, get rejected) there's nowhere to track it. You asked for a
simple way to see, alongside the listings, what's **applied**, **moving forward**,
and **rejected** — i.e. your pipeline.

## Naming (settled)
- **Pipeline** = every opportunity you're tracking, across all stages. (Right word.)
- **Stage / status** = where one opportunity sits now.
- **Needs action** = a filtered view of the pipeline: the ones waiting on you.

## Navigation (your question: same page or separate?)
**One page, two tabs** — recommended over a separate page:
```
   ┌─────────────────────────────────────────────┐
   │  BT · [ Job Board ]  [ Pipeline ]            │   <- tab switch, no reload
   ├─────────────────────────────────────────────┤
   │  Job Board tab  = the scoreboard you have    │
   │  Pipeline tab   = what you've acted on        │
   └─────────────────────────────────────────────┘
```
Why one page: shared data + filters, one URL to bookmark, one file to host, instant
switch. A separate `pipeline.html` would duplicate the header/filter chrome and split
the data. (If you later want a dedicated link, the tab can also deep-link via `#pipeline`.)

## The stage model (keep it to five)
```
   Saved  →  Applied  →  Interviewing  →  Offer  →  Closed
                                                     └─ reason: rejected | withdrawn | declined
```
- **Moving forward** = Interviewing or Offer.
- **Rejections** = Closed with reason=rejected.
- A board listing enters the pipeline when you hit **Save** or **Mark applied** on its card.

## Pipeline tab layout
- **Needs-action strip** (top): auto-computed items waiting on you, e.g.
  *Applied 14+ days ago, no response → follow up* · *Interview logged → send thank-you* ·
  *Interviewing, no next step → nudge*. Each links to the role.
- **Columns by stage** (Saved / Applied / Interviewing / Offer / Closed), each card
  showing company · title · stage age · next-action date · the fit score it had.
- Same facet filters (arrangement/country/industry) apply here too.

## Status storage — RECOMMENDATION (you deferred this; here's the call)
**Board + export**, with the tracker staying canonical:
- One-click stage change on a card, stored in the browser (localStorage) — fast, no backend.
- An **Export** button emits the changed rows in the tracker's column order, to paste
  into `Job_Search_and_Tax_Tracker.xlsx` (Applications sheet). The tracker remains the
  record of truth and the EI evidence, per the project rule.
- On load, the board can also **read** a `pipeline.json` (generated from the tracker) so
  a fresh device shows the real state. localStorage is per-device; the tracker is the
  durable record. (Same pattern as the Kepler progress log, which the project already blessed.)
- Rejected alternatives: *tracker-only* (every change means opening Excel — too slow);
  *two-way sync* (most convenient, most moving parts — revisit later if needed).

## Data shapes
- **pipeline entry** (localStorage + optional pipeline.json):
  `{id, company, title, url, stage, reason?, applied_on?, next_action?, next_action_on?, score, source}`
  where `id` = stable hash of company+title.
- **jobs.json** gains nothing required; a board card gets a "track" affordance that
  writes a pipeline entry.
- **Needs-action** is computed, never stored: derived from stage + dates at render time.

## Functional requirements
- **FR-P2-1** Tabs: Job Board (existing scoreboard) and Pipeline, switchable without reload.
- **FR-P2-2** Track action: Save / Mark applied on any board card creates a pipeline entry.
- **FR-P2-3** Stage control: change a role's stage (and Closed reason) from the Pipeline tab.
- **FR-P2-4** Needs-action strip: compute follow-up/thank-you/nudge items from stage + dates.
- **FR-P2-5** Persistence: localStorage; **Export** produces tracker-ready rows; optional
  read of pipeline.json on load.
- **FR-P2-6** Facet filters apply to the Pipeline tab too.

## Acceptance criteria (→ tests, deterministic parts)
- AC-P2-1 Marking a board role "applied" makes it appear under Applied in Pipeline.
- AC-P2-2 A role Applied ≥ N days with no next-action shows in Needs-action as "follow up".
- AC-P2-3 Closed+rejected appears under Closed and is countable as a rejection.
- AC-P2-4 Export yields rows matching the tracker's Applications column order.
- AC-P2-5 Stage counts (Saved/Applied/Interviewing/Offer/Closed) render correctly.
- (Pure functions — stage transitions, needs-action computation, export formatting —
  are unit-tested; the localStorage/UI wiring is smoke-checked.)

## Non-goals (Phase 2)
No auto-applying, no sending email, no writing to the .xlsx directly (export to paste
keeps the tracker under your control). Interview-prep packs = Phase 5.

## Open decisions for BT
1. Storage: confirm **Board + export** (recommended) vs tracker-only vs two-way sync.
2. Needs-action timing: follow-up after how many days applied? (default: 7.)
3. Sponsorship data: back the facet with the Canada **LMIA employers list** (real
   registry — see `SPONSORSHIP_DATA.md`) instead of JD-guessing? Engineering NOCs only?
4. Should the board read a `pipeline.json` generated from your existing tracker so the
   pipeline is pre-populated with roles already in flight (Kepler, Natus, Profound…)?
