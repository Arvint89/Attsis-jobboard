# DESIGN: Parity with the v6 prototype (JB-73, #181): gap audit
_v1 · 2026-10-11 · Labels: ✅ verified (how) · ⚠️ inferred · ❓ unchecked_
_Method: both rendered in Edge via Playwright at 1440×1000. Prototype = `docs/design/prototype/Attsis Job Board v6.dc.html` (inline demo data). Live = `site/index.html` on `main` after #184, served locally with the live `jobs.json` (2026-10-11). Screenshots: `docs/design/screenshots/jb73/`._

## 1. Already matching (✅ seen in screenshots)
- Colour tokens (cosmic navy `--bg #0A0E1A`, card `#141D35`, cyan `#00D4FF`, green `#00E87A`) and fonts (Syne / Inter / JetBrains Mono). Ported in #141.
- Map (List + map, score pins, rings, Fit score | Salary, search as I move), shipped in #184.
- Tracker kanban columns (Saved → Applied → Interviewing → Offer → Closed), stored in localStorage.

## 2. Gaps, screen by screen
| # | Screen | Prototype | Live | Gap | Effort ⚠️ |
|---|---|---|---|---|---|
| G1 | **Global shell** | Wordmark + logo dot; nav with **icons** + mono labels (Roles, Tracker·6, Queue·3, Prep, Learn, Profile); active = outlined pill; **"Build profile" CTA**; footer "A GLOBAL ATTSIS PRODUCT · PULLED FROM EMPLOYER ATS · SCORED IN YOUR BROWSER" (`proto_*.png`) | Gradient H1 + filled cyan pill tabs, no icons, no CTA, plain footer (`live_*.png`) | Restyle header/nav/footer; add tracker count badge | S |
| G2 | **First visit / landing** | **Board visible immediately** with a general profile; hero: LIVE badge, "Updated · N roles · N employers", display headline, privacy subline; side card "Rank these against your profile" (CV / Cover letter / LinkedIn / GitHub / Portfolio) (`proto_roles.png`) | **Gate:** name required before any role is shown (✅ `index.html:797` `alert('Enter your name first.')`) (`live_firstvisit.png`) | Remove the name gate; add hero + profile card. **Biggest growth lever:** new visitors see roles in 0 clicks | M |
| G3 | **Job card** | Score box `10 /10`; title; company · 📍 city · "in your city" · "2 weeks ago"; facet chips; ✓ checks ("Within 200 km", "On-site"); WHY line; **expand** → WHY IT FITS (skill chips + reasons) / GAPS TO ADDRESS (`proto_cards.png` in jb72) | Score box; title; sub-line; snippet; chips; why; actions bar; separate "Gap check" button (`after_split.png` jb72) | Card layout v2 with expand-in-place (matches `docs/UI_DESIGN.md` pattern 4) | M |
| G4 | **Page headers** | Eyebrow (mono caps) + large display title + stat tiles (Tracker: Active 3 · Interviews 1 · Response 50 %) | Panel with h2 + paragraph | Shared page-header component + tracker stats (computable from localStorage) | S |
| G5 | **Profile tab** | "What should we match you on?" with source cards (CV, Cover letter, LinkedIn PDF, GitHub, Portfolio) + sticky "What we'll match on" panel (titles · skills · excluded, "Save and re-rank N roles") (`proto_profile.png`) | ✅ **Bug:** shows the first-visit welcome form even after setup (`live_profile.png`); CV upload exists but on a separate panel | Fix the bug now; then Profile v2 layout. GitHub repo reading = new feature (public API, client-side ⚠️) | Bug: XS · v2: M |
| G6 | **Tracker** | "Needs your answer · 4" nudges (stale posting, interview reminder, "heard back?"); cards with score + dates + stage select; "Where we reach you" channels panel (`proto_tracker.png`) | Kanban with empty states; ◀ ▶ buttons; notes (`live_tracker.png`) | Nudges + stats are **local-only and doable now**; "Where we reach you" (Telegram/WhatsApp/email) **needs a backend**, so it's growth plan Stage 2+ | M (local) |
| G7 | **Prep** | Role-specific header + tabs (Technical / Behavioural / Negotiation / Company); "Prep plan from your gaps" (deterministic: JD terms not in CV); **AI mock interviewer** (`proto_prep.png`) | Four static template cards (`live_prep.png`) | Prep plan from gaps = deterministic, doable. Mock interviewer = LLM, which conflicts with the "no LLM in daily loop" north star, so it becomes a **paid-tier decision for BT** ❓ | M / L |
| G8 | **Queue** (assisted apply) | Rules + queued applications (`proto_queue.png`) | Not built | **Deferred** per `COMMERCIALIZATION_PLAN.md` ("Deferred: … apply queue …") | L |
| G9 | **Learn** | Teardowns, sims, shorts; creator model (`proto_learn.png`) | Not built | **Deferred** (same plan: "creator hub") | L |
| G10 | **Attsis reading** (numerology on cards) | "Life Path · compatibility" block inside the expanded card (`proto_cards.png`) | Not built | Brand decision for BT ❓. The prototype says "for reflection only, never changes the score" | S |
| G11 | **Brand name** | "Attsis **Jobs**" | "Attsis **Job Board**" (BT's rename, #173 ✅) | Keep "Attsis Job Board" (BT decision). Don't follow the prototype here | — |

## 3. Order (by effect on "more people use it")
| Step | Gaps | Child issue | Why this order |
|---|---|---|---|
| 1 | G5 bug | (fix inside step 2 PR) | Visible breakage |
| 2 | **G2 landing + G1 shell** | JB-74 | First impression for every new visitor; removing the gate = fewer drop-offs ⚠️ |
| 3 | G3 job card v2 | JB-75 | Where users spend time; shows "why" and "gaps", our differentiator |
| 4 | G4 + G6 (local) tracker v2 | JB-76 | Brings people back (Stage 2 retention) |
| 5 | G5 profile v2 | JB-77 | Better matching → better scores |
| 6 | G7 prep plan from gaps | JB-78 | Deterministic, no LLM |
| — | G7 mock interviewer, G8, G9, G10 | not filed | Need BT decisions / deferred by plan |

## 4. Decisions needed from BT (❓)
1. AI mock interviewer: build as a paid feature (breaks "no LLM in the loop" for that feature only), or drop?
2. Attsis numerology reading on job cards: in or out?
3. OK to remove the name requirement on first visit (name stays optional, used only for the header initials)?
