# Commercialization Risks

_Written 2026-09-30 overnight by Claude at BT's request ("identify any problems if this were to commercialize"). Complements BUSINESS_PLAN.md, which lays out the product + pricing shape but does not catalog what breaks when real users and real money arrive. Treat this as a punch list, not a plan — each item is a thing to decide BEFORE a public launch, not after._

---

## 1. Architectural cliffs

### 1.1 The sweep is batch-static-JSON. LinkedIn is live-query.
Current model: GitHub Action runs sweep.yml on push + weekday cron → fetches every ATS + every aggregator → writes `site/data/jobs.json` (one static file) → Pages deploys. The browser downloads the whole file and filters client-side.

**Breaks at ~5 MB of jobs.json / ~2000 roles / ~500 companies.** Three failure modes come in that order:

1. **First-paint latency** — users on 4G download the whole blob before seeing anything. We have zero pagination, zero API.
2. **Sweep wall-clock** — every registry entry fetched serially per push. Already hitting 10-15 min at 209 companies on cold cache (see sweep run 36818235757, cancelled at 15 min). At 1000 companies this becomes 40-60 min, and GHA free tier caps individual jobs at 6 hours but caps *monthly* minutes at 2000 for free, 3000 for Pro.
3. **Freshness window** — weekday cron means Friday evening postings aren't seen until Monday morning. For a free seeker tool, fine. For a product someone paid $8.99/mo for, not fine.

**The commercial-grade architecture (not now):** small Postgres (or Supabase/Neon free tier for pre-revenue) + a per-user search endpoint. Writer process (crontab or Cloudflare Worker) ingests continuously; API serves filtered pages. See the icebox discussion from 2026-09-30 ("LinkedIn-style continuous ingestion"). Shelved until a user complains about staleness — but *name* the trigger explicitly so we don't drift past it.

### 1.2 No multi-tenant isolation
Every scoring pass is browser-local, so "multi-tenant" sounds solved. It isn't:
- `site/data/jobs.json` is **one** file for everyone — can't personalise the fetch set per user without a per-user build.
- The registry (`engine/companies.json`) is BT's curated list — a paying accountant in Toronto gets the same medical-device-heavy coverage.
- The 11-keyword `DEFAULT_QUERIES` in `sources.py` is BT's electronics shortlist. A warehouse-manager user searching Communitech 8936 would get the wrong 160-per-page slice.

Fix is deferred-but-identified: either (a) per-vertical builds (static shards: `/data/tech.json`, `/data/accountant.json`) or (b) real server with per-user query. (a) is the near-free path, (b) is the proper one.

### 1.3 Resolver is a per-company careers-page fetch bomb
`resolver.py MAX_LOOKUPS = 200` protects a single run. But at 500+ companies with 7-30 day recheck windows, every cold-cache run spends ~2-3 min just on resolver HTTP. The cache is published back as `data/resolver_cache.json`, so steady-state is fine — but any registry expansion event (seed 100 new companies) causes a one-time hang.

**Already causing hangs today** (JB-62 just landed per-phase logging to see this clearly). The right fix was previously called out: **split the resolver pass to its own weekly workflow** that writes `resolver_cache.json` back as its only artifact. Shelved pending the diagnostic data from the new logs.

---

## 2. Data / coverage risks

### 2.1 Getro aggregator dependency
MaRS (383), Communitech (628, 8936), Economic Dev Jobs (30254) are 4/6 of our board sources — all the same vendor. If Getro:
- Rate-limits us (none observed, but no ToS reviewed either).
- Changes the API shape (silent breaking changes are a staple of unversioned JSON APIs; we have no contract test against live Getro).
- Blocks the user-agent `bt-jobboard/1.0` (currently honest UA — commercial launch likely needs a real company UA + a `/robots.txt` check + possibly a scraping agreement).

...we lose a huge fraction of discovered roles overnight. Our coverage without Getro right now would collapse to just the 209-entry registry minus the resolve pass.

**Mitigation path:** diversify sources (more Getro-equivalent networks, direct ATS discovery via resolver, LinkedIn scout — but LinkedIn has its own ToS cliff; see 2.3).

### 2.2 Hardcoded `DEFAULT_QUERIES` is a tech-only acquisition funnel
`sources.py:51` ships 11 keywords: embedded/firmware/hardware/electronics/PCB/etc. Any user outside that domain is served Getro's top-ranked results for *electronics terms*, then our scorer tries to reject anything that doesn't match their CV. Garbage in, polite rejection out. Non-tech verticals need per-vertical query seeds AND per-vertical companies — the "domain-agnostic architecture" claim in BUSINESS_PLAN.md §1 is partly aspirational.

### 2.3 LinkedIn / Indeed are off-limits for commercial scraping
BUSINESS_PLAN.md implies competing with LinkedIn by "catching roles the big boards miss." That's true for the *free* tier shipping our own aggregator mix. But:
- **LinkedIn** actively blocks bots at IP + fingerprint level, has sued hiQ Labs (and lost on CFAA, won on contract), and their ToS forbids scraping. Our `scout.py` LinkedIn work exists for personal use only; commercial use is a legal cliff.
- **Indeed** has an official API but it's heavily rate-limited and employer-paying-for-placement centric — not a technical ingest path.
- **Workday / Greenhouse / Lever / Ashby** direct ATS fetches are OK (we're reading public job boards the companies themselves publish), but each company's `robots.txt` could legally change tomorrow.

**Launch gate:** have a lawyer read the top 10 ATS vendor ToS + the Getro ToS before paid tier opens.

### 2.4 Postings get stale between sweeps
At weekday cron + manual push triggers, the live board can be up to 72 hours behind reality (Friday close → Monday cron). Jobs filled on Friday still show on the board Monday morning, so paying users click dead links. We don't track "when did this URL first return 404" so we can't even auto-prune.

**Minimum viable fix pre-launch:** a dead-link checker (HEAD + status code) as a separate workflow, and a "verified fresh at TIMESTAMP" badge on each card.

---

## 3. Product / UX gaps for paid tier

### 3.1 No per-user state server-side
Everything's `localStorage`: profile, tracker, filters, saved roles. Three immediate problems for a paid user:
- Lose state on cache clear / incognito / device switch — no sync across devices.
- Can't do "email you when a matching role appears" (no server, no scheduler, no user record).
- Can't do churn analytics ("90% of Pro users never used tailored CV" → we'd never know).

**Minimum viable backend for Pro:** a user table + a saved_searches table + a push/email dispatcher. Supabase free tier handles 500 MAU trivially; Postgres on Fly.io ~$2/mo. The pricing in BUSINESS_PLAN.md ($8.99/mo Pro) assumes zero infra cost on BT's side — true today, false the moment server-side state exists.

### 3.2 No payment infrastructure
There is no Stripe account, no price IDs, no webhook handler, no entitlement check, no billing portal, no refund flow, no tax handling (digital services VAT in EU, GST/HST in Canada, state sales tax in US — all triggered at different revenue thresholds). The pricing table in BUSINESS_PLAN.md §5 is a spec; the implementation is a 2-4 week sprint minimum.

### 3.3 CV-only-in-browser conflicts with employer tier
The whole Pro + Career-Agent story depends on "CV scored client-side, never leaves the browser." Good for seekers, incompatible with the B2B / employer screening tier (where employers upload JDs and want to see candidate matches — which requires either (a) a CV database the employer can query, or (b) seekers opting in to appear in a reverse-search index). Both break the "CV never leaves the browser" guarantee. Decide now which side wins when they collide, because it affects data architecture, consent flows, and the privacy page copy.

### 3.4 Scoring is deterministic but opaque to users
`jobfilter.classify()` returns a verdict + reasons + matched keywords. For free, "fit score 7" is enough. Paying users will ask "WHY is this a 7 and that identical-looking role a 4" and the current `reasons` output isn't user-grade — it's debugging output. Pre-launch: write a `score_explanation(result) → human_sentence` helper or users will think the product is broken.

---

## 4. Legal / privacy / compliance

### 4.1 No Terms of Service, no Privacy Policy
Live board at arvint89.github.io is a personal project; CV is in localStorage so GDPR/PIPEDA/CCPA exposure is minimal *as long as* no server state exists. The second we take payment, we collect:
- Name, email (billing).
- IP + device fingerprint (fraud).
- Payment card last-4 + Stripe customer ID (via Stripe but we're the data controller).

...and we need both docs reviewed by a lawyer in whichever jurisdictions we take money from.

### 4.2 Right-to-be-forgotten
No `DELETE /user/me` endpoint today (because no user records). GDPR / PIPEDA both require this. Must exist on day 1 of paid tier.

### 4.3 Scraping / robots.txt compliance
We respect `robots.txt` only via the implicit "don't do it if the ATS blocks us" rule — no actual check. For personal use this is fine. For a commercial product, add a cached robots-check per domain, log every blocked fetch, and document the policy.

### 4.4 LMIA / sponsorship data accuracy
`JB-15 LMIA`-style features imply we're surfacing employer sponsorship info. If we mark a company as "sponsors foreign workers" and they don't, and a user applies based on that, the complaint path is on us. Needs a disclaimer + a last-verified timestamp per data point.

---

## 5. Operational / business risks

### 5.1 Single-maintainer / single-key-holder (BT) bus factor
Everything (git, deploy keys, domain DNS, future Stripe account, future DB credentials) in BT's hands. If BT is unreachable, nothing can be rotated or responded to. Pre-launch: at minimum a password-manager vault + a documented recovery procedure. Preferably a second maintainer or a succession doc.

### 5.2 Support load scales with users, not revenue
Free users will ask for support. At $8.99/mo Pro and a 10% conversion, every 100 free users = 1 paying + 99 asking "why doesn't this match my CV." No helpdesk, no email autoresponder, no FAQ page beyond `README.md`. Pre-launch: either a Discord/forum (community support, free) or set user expectations ("best-effort email support, 72h").

### 5.3 Fraud / abuse of free tier
Free tier includes the whole board + CV scoring + basic pipeline. Nothing stops a competitor from scraping *our* `jobs.json` daily and reselling it. The data is downstream-public (Greenhouse/Workday are public), so there's no copyright claim, but we did the aggregation work. Pre-launch: add a lightweight rate limit on the CDN layer (Cloudflare has a free one), add attribution requirements to a ToS.

### 5.4 Marketing / acquisition is unplanned
BUSINESS_PLAN.md §5 lists prices but no acquisition channel. SEO is hard against Indeed/LinkedIn. Paid ads are expensive per converted-seeker. Content marketing (BT writing "how I built a job board" posts) is the cheapest path but takes 6-12 months to compound.

---

## 6. Pre-launch checklist (ordered by must-have-ness)

1. **Legal review** — ToS, Privacy Policy, scraping defense, jurisdictions (gate to accepting money).
2. **Payment infra** — Stripe + entitlement + webhook + billing portal (gate to Pro features).
3. **Server-side user state** — minimum: user table + saved_searches + email dispatcher (gate to "notify me" features).
4. **Dead-link checker** — a separate workflow that marks stale URLs (gate to not frustrating paying users).
5. **Per-vertical query seeds + registry shards** — accountant/warehouse don't share tech's `DEFAULT_QUERIES` (gate to the "domain-agnostic" marketing claim).
6. **Succession / credential vault** — bus-factor mitigation (gate to running under a real company name).
7. **Scaling plan trigger** — define the "jobs.json too big" number explicitly (e.g. 3 MB) so we don't drift past it; have the DB migration doc half-written and ready.

Nothing here is a blocker to the current personal-use board. Everything here is a blocker to taking money.
