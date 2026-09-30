# Attsis Jobs — Quickest Commercialization Plan
VERSION 1.0 · 2026-09-23 · Owner: BT · Builder: Global Attsis AI · Horizon: 8 weeks

> Goal: **first dollar in 10 days, 50 real users in 4 weeks, one recurring B2B deal in motion by week 8.**
> Rule: sell it by hand first, automate only what sells twice. Ranking is never for sale.

---

## 1. The three offers (in launch order)

| # | Offer | Price | Digit-sum | How it's delivered (v1) | Build needed |
|---|---|---|---|---|---|
| 1 | **Tailored CV + cover letter** for one role | **$17.99** | 1+7+9+9=26→8 | Payment link → intake form → Claude prompt → BT spot-check → email .docx within 24 h | Button on job card + payment link + form |
| 1b | **Same, reviewed by a P.Eng** | **$44.99** | 4+4+9+9=26→8 | As above, BT does a full review + comments | None extra |
| 2 | **Jobs digest in Attsis Daily bot** | existing bot tiers | — | Daily Telegram message: new roles scoring 7+ for the user's keywords | One bot menu item + keyword capture |
| 3 | **Regional board licence** (EDO / career centre) | **$197.99/mo** after a 60-day free pilot | 1+9+7+9+9=35→8 | White-label copy of the board filtered to their region + their logo | Config flag for region + branding |

Deferred (not in this plan): Pro subscription, apply queue, creator hub, WhatsApp, employer matching.

---

## 2. Week-by-week

| Week | Deliverable | Owner | Issue | Done when |
|---|---|---|---|---|
| **1** | Payments account for Global Attsis; payment links for $17.99 and $44.99 | BT | JB-45 | Test payment succeeds |
| 1 | "Tailor my CV for this role" button on each live job card (opens payment link with job URL prefilled) | AI | JB-46 | Button live on Pages, CI green |
| 1 | Intake form: name, email, CV upload, job link, target title, consent + deletion notice | AI+BT | JB-47 | Form submits to BT's inbox |
| 1 | Tailoring SOP + Claude prompt template (§3) committed to `docs/ops/` | AI | JB-48 | First internal dry run on BT's own CV |
| **2** | Attsis Daily bot: "Jobs" menu → user sets keywords → daily digest from `jobs.json` | AI | JB-49 | BT receives a digest for 3 days running |
| 2 | Launch posts: r/ECEjobs, r/cscareerquestionsCAD, Communitech + London tech groups, LinkedIn | BT | — | 5 posts live |
| **3** | Ship profile v2 basics: typed keywords + exclusions + preferences (prototype: Profile tab) | AI | JB-50 | Setup works without a CV upload |
| 3 | Pitch deck (5 slides) + one-pager for regional licence | AI | JB-51 | BT approves |
| **4** | **Decision gate A** (§5) | BT | — | Numbers recorded in `docs/status/` |
| 4 | Email 6 targets: LEDC, Communitech, Invest Ottawa, Western, Fanshawe, Waterloo co-op | BT | — | 6 sent, 2 calls booked |
| **5–6** | Automate tailoring if gate A passed: prompt runs on submit, BT approves in one click | AI | JB-52 | Turnaround < 2 h |
| 5–6 | Region + branding config for a pilot licence | AI | JB-53 | Demo URL for one EDO |
| **7–8** | First pilot live; weekly usage report to the partner | AI+BT | JB-54 | Partner has logged in 3+ times |
| 8 | **Decision gate B** (§5) | BT | — | Go/no-go on Pro build (plan §12 v1.0) |

---

## 3. Tailoring SOP (v1, manual)

1. Payment confirmed → intake form arrives.
2. Run the board's gap check on the job link (have / missing terms).
3. Run the Claude prompt (`docs/ops/tailor_prompt.md`) with CV + JD + gap output.
   - Hard rule in prompt: **reword and reorder only — never add a skill, employer, date or number not in the CV.**
4. BT spot-check (5 min) or full review for the $44.99 tier. Checklist:
   - [ ] No invented facts (diff CV vs output)
   - [ ] Top third of CV mirrors the JD's first three requirements
   - [ ] Cover letter ≤ 250 words, names the company and role, one concrete number
5. Email .docx + short note on the 2–3 gaps to address in the interview.
6. **Delete the CV and outputs within 7 days.** Log only: date, role, price, turnaround.
7. Refund policy: full refund on request within 7 days, no questions.

---

## 4. Compliance + admin checklist

- [ ] Payments under **Global Attsis** (Ontario-registered).
- [ ] HST: not required until taxable sales pass **$30,000** over four consecutive quarters (small supplier) — track monthly.
- [ ] Privacy notice on the intake form (PIPEDA): purpose, retention 7 days, contact for deletion.
- [ ] Bot digest: explicit opt-in, one-tap stop (CASL).
- [ ] Trademark search + filing for "Attsis Jobs" (start now; long lead time).
- [ ] Check Kepler employment agreement for side-business / IP clauses before any public launch.
- [ ] Ask Getro-hosted boards (MaRS, Communitech) for written OK to display their listings.

---

## 5. Decision gates

| Gate | When | Pass | Then | If not |
|---|---|---|---|---|
| **A** | End of week 4 | ≥ 5 paid tailoring orders **or** ≥ 50 digest subscribers | Automate tailoring (JB-52) | Change the offer: try interview-prep call ($98.99 → 9+8+9+9=35→8) or drop price test to $8.99 |
| **B** | End of week 8 | ≥ 15 paid orders total **or** one signed pilot | Start plan §12 v1.0 (backend + Pro) | Keep manual, focus on the licence channel only |

---

## 6. Metrics (update weekly in `docs/status/`)

- Visitors → setup completed → digest subscribers
- Tailoring orders, revenue, turnaround time, refunds
- Source of each order (which post/channel)
- Licence pipeline: contacted → call → pilot → paid

---

## 7. Start now, in parallel (long lead times)

Payments account · trademark filing · Getro permission emails · Chrome developer account (for the later apply extension) · WhatsApp Business verification (later, Pro) · one legal consult (trademark, recruiter licensing, employment contract).

---

## 8. Design references

Open these from this folder in a browser (they need internet for fonts, icons and map tiles):

| File | Shows |
|---|---|
| `Attsis Job Board v6.dc.html` | Full prototype: Roles (list + map), Tracker, Queue, Prep, Learn, Profile, Tailor, Attsis reading |
| `Attsis Jobs Plan.dc.html` | Product plan: phases, monetization, employer side, sources, clearance, AI, data, architecture, build timeline |

Screens that matter for this plan: **Roles → job card → "Tailor CV + cover letter"** (offer 1), **Tracker → "Where we reach you"** (offer 2), **Profile** (JB-50).
