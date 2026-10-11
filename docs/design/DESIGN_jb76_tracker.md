# DESIGN: JB-76 tracker v2 (#189)
_v1 · 2026-10-11 · Parent: #181 · Audit gaps G4 + G6 · Labels: ✅ verified · ⚠️ inferred · ❓ unchecked_

## Problem
✅ The live tracker is a bare kanban with an explanatory paragraph (`screenshots/jb73/live_tracker.png`). The prototype (`proto_tracker.png`) **brings people back**: a page header with stats (Active · Interviews · Response rate) and a **"Needs your answer"** list that asks one question per stale role. Bringing people back is growth Stage 2's gate (25 % 4-week retention, `GROWTH_INVESTMENT_PLAN.md`).

## Decisions
### D1. Where the nudges live
| Option | Pros | Cons |
|---|---|---|
| **A. Computed in the browser from the tracker (localStorage)** | Free, private, works today | Only shows when the user opens the site |
| B. Telegram/email reminders (prototype "Where we reach you") | Reaches people who don't come back | Needs a backend + consent; growth Stage 2+ |

**Choice: A now.** B stays in the growth plan; this view is built so B can later send the same nudge list.

### D2. Which nudges
| Nudge | Rule | Answers |
|---|---|---|
| Still interested? | stage **saved**, saved ≥ 7 days ago | Mark applied · Drop · Later |
| Heard back? | stage **applied**, applied ≥ 7 days ago | Interview booked · No reply yet (= later) · Rejected |

"Later" snoozes for 7 days (`t.snooze`). **Not copied from the prototype:** "roles like this often close within a month". ❓ We have no data for that claim, so it's left out.

### D3. Stats
- **Active** = applied + interviewing + offer.
- **Interviews** = interviewing + offer.
- **Response rate** = (interviewing + offer) ÷ (applied + interviewing + offer + closed). Shows "—" when the denominator is 0. **Tradeoff:** "closed" includes withdrawn roles, so the rate is a floor. The tile's tooltip says so.

### D4. Cards
Score badge top-right; date line ("Saved Oct 3", "Applied Oct 5") from `added` / `moved`; the posting date is stored on save from now on. ◀ ▶ buttons stay (they work on touch screens).

## Contract (pure, Node-tested: `/* TRACKER-PURE-BEGIN */…END`)
```js
trackerStats(items) -> {total, active, interviews, rate}        // rate: 0..1 or null
trackerNudges(items, nowMs) -> [{key, kind:'saved'|'applied', days}]   // days desc; snoozed excluded
```

## Acceptance
- [ ] Header: eyebrow "Tracker · N roles", title "Your applications", 3 stat tiles.
- [ ] Nudges appear with the rules in D2; each answer moves the card or snoozes it, then re-renders.
- [ ] Empty tracker: a friendly empty state pointing to Roles.
- [ ] pytest + smoke + preprod smoke; screenshots.
