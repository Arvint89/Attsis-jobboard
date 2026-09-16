# Input surface + domain-agnostic model — design update
_Draft for BT review · 2026-09-16 · corrects Phase 1_

## A. Where the user inputs CV + cover letter (the missing surface)
Today input = a command (`cv_parse.py CV.docx`). No user-facing input. Fixing that.

**Why it's not just "a form on the board":** the browser can't fetch most company ATS
endpoints directly (CORS), so **fetching + scoring run in Python** (the GitHub Action or a
local run). A browser input page therefore *produces a profile* that the Python side reads —
it doesn't score by itself.

**Proposed: a Setup page (`setup.html`)** — a second tab/page beside Job Board & Pipeline:
1. Upload or paste **CV** and (optionally) **cover letter** text. (.txt/.md/paste now;
   .docx via a small in-browser parser or "paste the text".)
2. The page extracts keywords **client-side** (no LLM): lowercase, drop stopwords, rank
   terms + 2-word phrases by frequency, detect candidate **titles** (top lines), **home
   city** (from a city list), and **years**.
3. Output `profile.json` — **download it** (to commit to the repo for the Action) and/or
   keep in **localStorage** (for a local run). The board/pipeline read this profile.
4. A "review & edit" step: the user can add/remove keywords before saving (so a weak auto-
   extract is correctable).

Flow: **Setup (CV+cover → profile.json) → engine fetches+scores → Job Board / Pipeline show it.**

## B. Domain-agnostic matching (engineering AND non-engineering)
The model stops being hardcoded electronics. It comes from the user's documents:
- **skill_confirmers** = keywords extracted from CV + cover letter (any field).
- **title_triggers** = job titles the user has held / targets (from CV headings + cover letter).
- **exclusions** = a small generic set (intern/co-op/senior-mismatch) + user-added negatives.
- The current electronics lists (`model_base.py`) become a **default example seed**, used only
  if no CV is provided — not the engine.
- **Company-side filtering stays in the registry**: industry, location, size, sponsorship —
  so filtering by *company attributes* is automatic and field-independent. The registry grows
  to "all company details," the CV/cover drives *role* matching. Two independent axes:
  **role fit (from your docs)** × **company facts (from the registry)**.

Result: a nurse, an accountant, or an electronics engineer each get a board scored to *their*
CV, filtered by the same company registry.

## C. Sponsorship facet — quarterly + manual pull (LMIA in Phase 2.5)
- Phase 1/2: keep JD-text guess (yes/no/unknown).
- **Phase 2.5**: back it with Canada's **LMIA employers list** (see SPONSORSHIP_DATA.md).
  Because that data is **quarterly**, the UI must:
  - **label the quarter** on the facet/chip ("sponsored before · LMIA 2026 Q1"), so users
    see how current it is;
  - offer a **manual "Pull latest LMIA data"** action (downloads the newest quarterly file and
    rebuilds the sponsor index) — no auto-magic, user-triggered;
  - auto-hide the facet when the profile says the user needs no sponsorship (PR/citizen).

## Updated Phase 1 requirements (added)
- **FR-7 Input surface.** A Setup page to input CV + cover letter and produce `profile.json`
  (client-side extraction, review/edit, download + localStorage).
- **FR-8 Domain-agnostic model.** Keywords derived from CV + cover letter; electronics lists
  demoted to a default seed; registry drives company-attribute filtering.

## Decisions for BT
1. Build the **Setup page** next (completes Phase 1 input), then Phase 2 pipeline?
2. Auto-extract keywords with a **review/edit** step (recommended) vs fully automatic?
3. Cover letter: treated as an **optional booster** to the keyword set (recommended), or required?
