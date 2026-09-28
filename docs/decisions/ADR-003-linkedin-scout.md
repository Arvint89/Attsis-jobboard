# ADR-003 — LinkedIn as a signal source, not a fetch target

- **Status:** ACCEPTED — 2026-09-28
- **Deciders:** BT (owner)
- **Related:** ADR-002 (company discovery + resolver), issues JB-46 (#79), JB-43

## 1. Context

The board can't see LinkedIn postings. Two obvious paths were considered:

1. **Add a LinkedIn adapter** — like Greenhouse/Lever/Ashby. Rejected: LinkedIn's
   ToS forbids automated scraping of the jobs surface, they aggressively rate-limit
   unauth GETs (HTTP 999), and the DOM changes often. Even if it worked today it
   would break weekly and put the entire sweep at legal risk.
2. **Use LinkedIn as a discovery signal** — treat a LinkedIn job URL the same way
   we treat a sweep-log discovery: proof that some company is hiring, therefore
   worth adding to `engine/companies.json`. Fetching then happens against the
   company's own careers page via the existing ATS/resolver machinery.

Path 2 wins because it compounds: one URL → all future roles from that company
forever, via the direct ATS. Zero ongoing scraping. One-time human review.

## 2. Decision

Build `tools/linkedin_scout.py` (Layer 4 in the coverage funnel, per plan §4b).

- **Input**: a LinkedIn `/jobs/view/{id}` URL (or a list file, or a pasted HTML
  file when LinkedIn blocks the unauth GET).
- **Behaviour**: one HTTP GET per unique URL, cached forever in
  `data/linkedin_scout_cache.json` (gitignored). Extracts the hiring company
  name and (when present) their canonical careers/website URL by parsing
  JSON-LD `hiringOrganization`, the topcard org-name anchor, and `og:title`
  fallback — in that order.
- **Output**: prints a proposed `engine/companies.json` registry line with
  `platform: "resolve"` — never edits the registry itself. The human reviews,
  pastes, opens a PR. On the next sweep, `engine/resolver.py` (JB-43) auto-detects
  the ATS from the careers page and the company is then fetched directly.
- **No LLM.** Deterministic HTML parse. No LinkedIn API. No LinkedIn auth.

## 3. Consequences

- +Coverage compounds: seeding one LinkedIn URL adds every future role from
  that company to Layer 1 (registry), permanently.
- +Zero ToS risk: no ongoing crawl, no per-job fetching from LinkedIn.
- +Human-in-the-loop: registry additions are always reviewed before merge —
  keeps false positives (people, misnamed orgs) out.
- −Latency: a new company only shows up on the next daily sweep after the
  registry PR merges. Acceptable trade for compounding coverage.
- −Fetch fragility: LinkedIn may return 999 for unauth GETs. Falls back to
  `--from-html` paste mode so the human can save the page in their browser
  (already-authenticated session) and hand the HTML to the tool.

## 4. Alternatives considered

- **RapidAPI LinkedIn mirror** — paid + also brittle. Rejected under the
  "no paid tools this cycle" constraint.
- **Full API integration** — LinkedIn's Talent Insights API requires
  partner status and money. Out of scope.
- **Automated PR generation** — the scout could open a PR directly. Deferred
  until we have >10 URLs/week; human review is currently cheap.
