# BT Job Board — Software Architecture

## Abstract
The product turns a candidate's CV into a live, self-updating job board without an
LLM in the daily loop. It works in three deterministic stages — **parse, fetch,
score** — and a thin presentation layer. A CV is parsed once into a `profile.json`
(the matching model). A registry of employers maps each company to its ATS; a set
of adapters pulls each company's public JSON feed and normalizes every posting to
one shape. A rule engine scores each posting against the profile, tags flags, and
computes distance relative to the user's home city. The result is written as a
static JSON file that a static HTML page renders as a filterable scoreboard. Because
every stage is plain Python over public endpoints, the daily refresh runs on a free
GitHub Action and costs zero model tokens; generative help (tailoring, prep) is
layered on later and invoked only on demand. The design optimizes for three things:
**low running cost** (no inference in the loop), **explainability** (every score
carries its reasons), and **portability** (one person, one CV, any home city — the
same engine serves anyone by swapping the CV).

## High level (the pipeline)
```
   CV (.docx/.md)                    companies.json (registry)
        │                                     │
        ▼                                     ▼
   cv_parse.py                          ats.py  (per-ATS adapters)
        │  writes                             │  fetch public JSON
        ▼                                     ▼
   profile.json ─────────────►  build_board.py  ◄──── geo.py (home→ring)
   (matching model)              orchestrator: dedupe, classify, rank
        ▲                                     │
        │ reads                               ▼
   jobfilter.py (score/flag) ◄───────  site/data/jobs.json  (the data)
                                              │
                                              ▼
                                    site/index.html  (the website)
                                              ▲
                        GitHub Action (cron) runs build_board.py, commits
                        jobs.json, deploys site/ to Pages — 0 tokens.
```

## Mid level (components & responsibilities)
- **cv_parse.py** — input + parsing. Reads the CV, extracts the person, initials,
  home city, years, and which model terms the CV backs; writes `profile.json`.
- **model_base.py** — the default matching model (fallback when no profile exists);
  single source of truth for the keyword vocabulary.
- **companies.json** — the registry: each employer's ATS platform + slug + flags.
- **ats.py** — one adapter per ATS platform; each returns the same normalized job
  dict; failures are contained per-company so one bad feed can't stop the run.
- **jobfilter.py** — the rule engine: title triggers, skill confirmers, domain
  boosters, exclusions, freshness, 1–10 score, flags, and the reasons behind each.
- **geo.py** — converts a job location + the user's home city into a distance ring.
- **build_board.py** — orchestrator: gather → dedupe → classify → rank → write
  `jobs.json` (+ a data-embedded standalone page).
- **site/index.html** — presentation only: fetches `jobs.json`, renders, filters.
- **.github/workflows/sweep.yml** — scheduler + host (cron fetch, commit, deploy).

## Low level (contracts & key functions)
- **Normalized job dict** (the seam every adapter honours):
  `{company, title, location, url, posted, description, salary, source}`.
- **ats.fetch_company(entry) -> (jobs, error|None)** — dispatch by `platform`;
  `"resolve"` → `(_, "unresolved")`; exceptions → `(_, "<Error>: msg")`.
- **jobfilter.classify(job, extra_flags) -> {verdict, score, reasons, flags, matched}**
  where verdict ∈ {match ≥ threshold, below, excluded}. Pure function of the job +
  the loaded model; no I/O.
- **geo.ring_for(home, location) -> (ring|None, km|None, is_remote)** — haversine
  over a city-coordinate table; remote → ring 1 + flag.
- **jobs.json** (the API between engine and site): `{generated, mode, person,
  initials, home, flag_legend, min_score, counts, matches[], below[], errors[]}`;
  each row carries `score, ring, km, flags, reasons, matched, snippet, salary, url`.
- **Extension points:** new company = one registry line; new ATS = one function in
  `ats.py` + a `FETCHERS` entry; a `resolve` company = fill its `platform`+`slug` once.

## Why this shape
- **No inference in the loop** → the recurring cost is compute, not tokens.
- **One normalized contract** → the site and the scorer never care which ATS a job
  came from; adapters absorb all platform differences.
- **Profile-as-data** → the CV drives behaviour; the same code serves any candidate.
- **Static output** → hostable anywhere (Pages), cacheable, offline-viewable.
- **Reasons on every row** → the scoreboard is auditable, not a black box.
