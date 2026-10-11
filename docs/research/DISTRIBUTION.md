# DISTRIBUTION: how people find Attsis Job Board
_v1 · 2026-10-11 · Owner: BT (posting) · Claude (drafts, pages, measurement) · Labels: ✅ verified (how) · ⚠️ inferred · ❓ unchecked_
_Related: `docs/strategy/GROWTH_INVESTMENT_PLAN.md` (stage gates) · `docs/design/prototype/COMMERCIALIZATION_PLAN.md` (offers, prices)_

---

## 0. Launch gate: don't post before these are true
| Gate | Status |
|---|---|
| GoatCounter recording visits (BT signs up, creates site `attsis`) | ❌ ✅ `attsis.goatcounter.com` → HTTP 400 on 2026-10-11 |
| Map v2 live (#180) | 🔄 PR #184 (2026-10-11) → then the `main → production` release |
| Design parity pass (#181) | ❌ not started |
| Production shows the current name | ❌ ✅ live header still says "Job Board" (2026-10-11), release PR pending |

**Why wait:** each community gets roughly one launch post (⚠️). A dull map plus no analytics means we waste it and learn nothing.

---

## 1. Who it's for (positioning, ⚠️ hypothesis to test)
> **Engineers in Southwestern Ontario (hardware, embedded, med-device, software) who want to see who's hiring near them, scored against their CV, without uploading their CV anywhere.**

What we can honestly claim (✅ = checked in code/data):
- ✅ Roles come straight from employers' own careers systems (Greenhouse, Lever, Workday, Ashby…). `engine/ats.py`, 9+ adapters
- ✅ The CV is scored in the browser and never uploaded. Design rule in `CLAUDE.md`; scoring is client-side `scoreJob()`
- ✅ A map of who's hiring, with distance rings from home (Map v2, #184)
- ✅ Free, no account needed
- ⚠️ "Roles you won't find on Indeed": plausible for small employers, **not measured**. Don't claim it until we have an example.

---

## 2. Competitors (⚠️ general knowledge, no web access in session: **BT to verify ❓ items**)
| Competitor | What it is | Where we differ | Label | BT verify |
|---|---|---|---|---|
| Indeed | Biggest job board; ads + aggregation | We're regional, direct from employers, with a CV-scored map | ⚠️ | ☐ |
| LinkedIn Jobs | Jobs + network; Premium shows "match" | Our CV stays local; free fit score | ⚠️ | ☐ does LinkedIn show a free match score now? |
| Glassdoor | Jobs + company reviews | We don't have reviews (gap) | ⚠️ | ☐ |
| Talent.com | Canadian aggregator (Montreal) | Same aggregation idea, national; no CV scoring ❓ | ❓ | ☐ |
| **Eluta.ca** | Canadian; **indexes employer career sites directly** | **Closest competitor.** We add CV scoring + map + region focus. See spike #87 (JB-54) | ⚠️ | ☐ does Eluta have a map / CV match? |
| Job Bank (Gov. of Canada) | Official federal board | Free and trusted; we can't beat it on trust | ⚠️ | ☐ |
| Communitech / MaRS / LEDC boards | Regional ecosystem boards | ✅ They're our **sources** (`engine/sources.json`). We combine them in one place, so they're partners, not rivals | ✅ | — |
| Jobscan, Teal, Rezi | CV / ATS optimisers (paid tiers) | They upload your CV; ours is local. They do tailoring, which is our paid offer | ⚠️ | ☐ prices |
| Simplify, Huntr | Application trackers / autofill | We have a basic tracker; no autofill | ⚠️ | ☐ |

**Takeaway (⚠️):** don't compete on breadth. Compete on **region + map + privacy + engineering focus**, and treat the regional boards as partners.

---

## 3. Channels, in order (cheapest and most targeted first)

| # | Channel | Who posts | Cost | Stage (growth plan) | Measure |
|---|---|---|---|---|---|
| 1 | Communities: r/cscareerquestionsCAD, r/ECEjobs, r/londonontario, r/waterloo, Communitech + London tech Slack/Discord groups | BT | $0 | 1 | GoatCounter referrer |
| 2 | BT's LinkedIn ("I built…" story + map screenshot) | BT | $0 | 1 | referrer + post views |
| 3 | Short video (TikTok / Instagram Reels / YouTube Shorts): 20-second map screen-recording | BT records, Claude scripts | $0 | 1–2 | views → referrer |
| 4 | GitHub (README, topics, "Show and tell"), reaches developers | Claude | $0 | 1 | stars, referrer |
| 5 | SEO pages: "Engineering jobs in London, Ontario" etc., one per region on our site | Claude | $0 (+ domain ⚠️ ~$15–20/yr) | 2 | search referrers |
| 6 | Partners: LEDC, Invest Ottawa, Western, Fanshawe, Waterloo co-op (regional licence pilot) | BT | time | 4 | pilots signed |

**Not doing (and why):** paid ads (cost per user is high for a free tool, ⚠️); spamming many subreddits (bans and reputation risk); scraping LinkedIn for outreach (ToS risk, `COMMERCIALIZATION_RISKS.md` §2.3).

---

## 4. Drafts (BT edits voice before posting)

### 4a. Reddit: story-led, not an ad (r/cscareerquestionsCAD, r/ECEjobs)
> **Title:** I got tired of job boards full of reposts, so I built a free map of who's actually hiring engineers in SW Ontario
>
> I'm an engineer in London, ON. When I was job hunting, half of what I saw on the big boards were reposts, expired roles, or recruiters. So I built a tool that pulls roles **directly from companies' own careers pages** (Greenhouse, Workday, Lever etc.) and puts them on a map with 50/100/200 km rings around where you live.
>
> You can paste your CV and it scores every role against it. **The CV stays in your browser; nothing is uploaded.** No account, no email, free.
>
> It's strongest for hardware / embedded / med-device / software roles around London–KW–Toronto right now. I'd love feedback: what's missing, what's wrong, which companies I should add. [link]

_Rules:_ check each subreddit's self-promo rules first (❓ not checked); reply to every comment within 24 h; post on a weekday morning ET (⚠️).

### 4b. LinkedIn
> Over the last few months I built something for engineers job hunting in Southwestern Ontario: **a live map of who's hiring**, scored against your CV.
>
> Three design choices I made, and what they cost:
> 1. **Straight from employers' careers systems, not aggregators.** Fewer stale reposts, but every new company means finding its system. (Coverage is the hard part.)
> 2. **Your CV never leaves your browser.** Better privacy, but no accounts, so no alerts across devices yet.
> 3. **Rule-based scoring, no AI in the daily loop.** Near-zero running cost and explainable scores, but less "smart" than an LLM.
>
> [map screenshot] · Free, no sign-up: [link] · Feedback welcome, especially which companies are missing.

_(This doubles as interview material: it shows design choices and tradeoffs.)_

### 4c. Short videos: 5 scripts (20–30 s each; screen recording + captions)
| # | Hook (first 2 s, on-screen text) | Body | CTA |
|---|---|---|---|
| 1 | "Every company hiring engineers near London, ON. On one map." | Zoom out from the home pin, rings appear, tap a green "10" pin, the list filters | "Free, link in bio" |
| 2 | "Your CV never leaves your laptop." | Paste a CV, scores re-rank live, show the "scored in your browser" line | "Try it with yours" |
| 3 | "Stop applying to reposts." | Show a role, then click through to the employer's own careers page | "Straight from employers" |
| 4 | "How far would you commute?" | Toggle 50/100/200 km, turn on "Search as I move", pan to KW | "Find yours" |
| 5 | "I built a job board in [N] weeks, with no AI bill." | Quick architecture: Python fetch → GitHub Action → map | "Engineers: how would you improve it?" |

Tooling (⚠️): record with the Windows Snipping Tool (screen record) or OBS. Captions in CapCut. **attsis-shorts** (✅ owns `video_rendering` per `all-systems.json`) can automate this later. ✅ Its last commit was 2026-05-07, so it needs a revival first.

### 4d. Partner email (LEDC)
Draft kept **locally** at `docs/outreach/DRAFT_LEDC_partner_email.md`, **not committed**, because this repo is public (✅). BT decides whether to send or commit it. Send only after Stage 0 (§0).

---

## 5. Measurement (weekly, Monday, 10 min) → `docs/status/WEEKLY_METRICS.md`
| Metric | Source | Exists today? |
|---|---|---|
| Visits, by referrer (which post worked) | GoatCounter | ❌ needs signup |
| Setups completed (name+city or CV) | GoatCounter event `setup_completed` | ❌ to build (Stage 0) |
| Map used / pin clicked | GoatCounter event `map_used` | ❌ to build |
| 7-day return rate | GoatCounter (unique returning) | ❌ ❓ check whether GoatCounter can report this |
| 👍 / 👎 per match | GoatCounter events | ❌ Stage 1 feature |
| Tailoring orders + source | Stripe + intake form | ❌ Stage 3 |

**One post per week**, logged here: date · channel · link · visits in 48 h · comments · what we learned.

---

## 6. Open questions for BT (❓)
1. Which subreddits/groups are you already a member of? An established account matters for Reddit.
2. Are you comfortable showing your face and voice in videos, or screen-only with captions?
3. Custom domain before launch (e.g. attsisjobs.ca ⚠️ availability unchecked)?
