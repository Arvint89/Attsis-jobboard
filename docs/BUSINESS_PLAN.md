# Global Attsis Job Board — Business Plan v0.1
_2026-09-16 · applies the Global Attsis mental-model + pricing rules · Stage 0 ($0 revenue)_

## 0. Why productizing feels harder than the sweep (First Principles)
The daily sweep worked because it was scoped to **one user (BT), one field (electronics),
a hardcoded model, output = a chat message, state = a log file.** A *product* adds five new
axes at once: **many users · many fields · self-serve input · persistence · a UI someone else
can use · money.** None of that was "broken" in the sweep — it simply wasn't needed. The core
engine (fetch → filter → score) is the *same logic*; the churn was decisions on those five new
axes. Lesson: **narrow the axes.** Which is exactly the scope call below.

## 1. Scope decision — narrow to a TECH job board first
- **MVP = tech/engineering roles only.** Ship the electronics/embedded/firmware/hardware model
  we already have as the first vertical.
- **Architecture stays domain-agnostic** (keywords from CV + cover letter; registry holds
  company facts), so adding verticals later — **accountant/CA, warehouse manager, the smallest
  roles** — is a *registry + default-seed* change, not a rebuild.
- This narrowing is the single biggest reducer of "so many changes": one field, one user type
  (job seeker) for v1.

## 2. Jobs To Be Done
- **Seeker:** "Find roles that actually fit me without drowning in noise, and run my applications
  without a spreadsheet." Success = fewer, better-matched roles + never missing a follow-up.
- **Small employer / hiring manager (later):** "Screen and match candidates without a recruiter."
- **The wedge:** honest *fit scoring against your own CV* + a company-first search that catches
  roles the big boards miss (the ATS-direct trick). That's the differentiator vs Indeed/LinkedIn.

## 3. Positioning — "acting as HR" (both sides)
- **For seekers = your AI career agent / reverse-recruiter:** finds, scores, tailors, tracks,
  preps you. The things a headhunter does — for you, on your side.
- **For employers = an AI screener:** matches inbound CVs to a JD, ranks by fit, flags gaps.
- Same engine, two audiences. Seeker side first (Stage 0/1), employer side later (Stage 3+).

## 4. Product tiers & features
**Free (acquisition):** the board, CV-derived matching, facet filters, distance, basic pipeline,
**JD capture**, and a **short gap analysis** (deterministic: which JD keywords you have vs miss +
a one-line fit read). Cheap (no LLM) and the hook that shows value -> drives sign-ups.
**Pro (seeker core):** the **deep** gap analysis (Edge/Gap/Proof/Screen/Close narrative), tailored CV +
cover letter, interview-prep packs, reminders/follow-ups, unlimited pipeline, LMIA sponsorship data.
**Extras (one-time):** single tailored CV+cover pack; single interview-prep pack; "resume teardown."
**Free/paid line (BT's call, 16 Sep):** free = *sees the gap* (JD capture + short gap analysis);
paid = *closes the gap* (deep gap narrative, tailored CV, cover letter, prep). The free parts are
deterministic and near-zero cost, so giving them away is acquisition, not lost margin.

**Employer (B2B, later):** paste a JD → ranked candidate matches; JD-vs-CV gap screening.

## 5. Monetization & pricing (Global Attsis rule: digit-sum→8, end .97/.98/.99)
| Offer | Price | Digit check |
|---|---|---|
| Day Pass (Pro, 24h) | **$1.79** | 1+7+9=17→8 |
| Pro — monthly | **$8.99/mo** | →8 |
| Pro — annual | **$62.99/yr** | →8 |
| Career-Agent (Pro + all packs) monthly | **$17.99/mo** | →8 |
| Tailored CV + cover letter (one-time) | **$17.99** | →8 |
| Interview-prep pack (one-time) | **$26.99** | →8 |
| Lifetime (seeker) | **$197.99** | →8 |
| Employer screening (B2B) monthly | **$53.99/mo** | →8 |
Revenue mix: freemium subscriptions (recurring) + one-time packs (impulse) + B2B later (higher ARPU).

## 6. Second-order effects (why this compounds)
- The **company/ATS registry** grows every time we add an employer → a data asset competitors
  can't cheaply copy (and the seed for the "LMIA/sponsorship intel" upsell).
- **Low-token deterministic engine** → near-zero marginal cost per user → healthy margins at
  freemium scale; the generative bits (tailoring/prep) are paid, so cost tracks revenue.
- Every seeker who tracks a pipeline hands us **labelled outcome data** (applied→interview→offer)
  → future "what actually gets interviews" insight → a second product.

## 7. Go-to-market (Stage-appropriate, Momentum lens)
- **Stage 0→1:** launch the free tech board publicly (Reddit r/ECEjobs, r/cscareers, London/KW
  tech groups, Communitech). First paid = the one-time tailoring pack (impulse buy). Goal: first $.
- **Stage 1→2:** turn on Pro subscription once the pipeline + prep features exist.
- **Stage 3+:** employer/B2B screening; add non-tech verticals.

## 8. Pre-mortem — how this fails, and the guard
- *Fails if* we keep widening scope before shipping → **guard: freeze v1 to tech seeker board.**
- *Fails if* fit scoring is wrong → **guard: keep scoring explainable (reasons on every row).**
- *Fails if* ATS endpoints break/block → **guard: adapters fail-soft; registry + JD fallback.**
- *Fails if* nobody pays for a free board → **guard: paid = tailoring/prep/pipeline, not listings.**
- *Fails if* it needs BT's daily time → **guard: fetch runs on the Action; zero-touch.**

## 9. Moat
Company-first ATS registry (data) + honest CV-derived fit scoring + low-token economics +
the two-sided "AI HR" positioning. Big boards optimize for employer ad spend; we optimize for
the seeker's fit — a different side of the market.

## 10. Stage-gated next actions
- **Now (Stage 0):** finish v1 tech seeker board = Setup page (input) + pipeline + gaps. Launch free.
- **First $:** sell the one-time tailored CV+cover pack.
- **Then:** Pro subscription, LMIA data (2.5), employer side, non-tech verticals.
