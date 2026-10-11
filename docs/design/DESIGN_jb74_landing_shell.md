# DESIGN: JB-74 landing + shell (#187)
_v1 · 2026-10-11 · Parent: #181 · Audit: `DESIGN_parity_v6.md` G1, G2, G5-bug · Labels: ✅ verified · ⚠️ inferred · ❓ unchecked_

## Problem
- ✅ A first-time visitor sees **no roles** until they type a name (`index.html` `alert('Enter your name first.')`). Every extra step loses visitors (⚠️ general web knowledge, not measured here). The prototype shows the board immediately.
- ✅ The Profile tab shows the welcome form even after setup (`showTab('profile')` never calls `renderSavedProfile()`).
- The shell (header, nav, footer) doesn't match the prototype (`screenshots/jb73/`).

## Decisions
### D1. First visit
| Option | Pros | Cons |
|---|---|---|
| A. Keep the name gate | Header can greet by initials | ✅ zero roles visible before typing; likely drop-off ⚠️ |
| **B. Board immediately on a general profile; name and home optional (Profile tab)** | 0 clicks to value; matches the prototype | No initials until set; home defaults to `JOBS.home` (London ✅) |
| C. Auto-create an anonymous profile | Board immediately | Fake data in localStorage; harder to tell "never set up" from "set up" |

**Choice: B.** Why not C: B gives the same result without storing fake state.

### D2. Hero
Shown **only while no profile is saved** (first visit). Returning users go straight to their ranked list. **Tradeoff:** returning users lose the role/employer counts, so those also go in the count line. Claims in the hero are limited to ✅ facts: direct from employer careers systems (`engine/ats.py`), scored in the browser, nothing uploaded.
Right card "Rank these against your profile": **CV, Cover letter, LinkedIn PDF**. These go to the existing upload panel, and the LinkedIn PDF goes through the same PDF parser. **GitHub / Portfolio buttons left out:** not built, and fake buttons would mislead.

### D3. Icons
| Option | Pros | Cons |
|---|---|---|
| Lucide icon font via CDN (prototype) | Exact match | Extra request; ❓ cdnjs path unchecked |
| **Inline SVG (5 icons)** | No dependency, works offline/standalone | Slightly more markup |

**Choice: inline SVG**, Lucide-style strokes.

### D4. Brand
Keep **"Attsis Job Board"** (BT's #173 rename ✅), not the prototype's "Attsis Jobs". The wordmark is white like the prototype, with a logo dot. Tenant white-label keeps "· Job Board" (`test_site_brand.py`).

## Acceptance
- [ ] Fresh browser: roles render with no input; hero visible; Profile tab shows the quickstart (name/home) + upload.
- [ ] After setup: hero hidden; Profile tab shows the saved profile (bug fixed).
- [ ] Nav: icons + labels, outlined active pill, Tracker count when > 0, CTA "Build profile" (no profile) or initials (profile).
- [ ] Footer: "ATTSIS JOB BOARD · A GLOBAL ATTSIS PRODUCT" / "PULLED FROM EMPLOYER ATS · SCORED IN YOUR BROWSER".
- [ ] Clearing the profile returns to the general board, not a gate.
- [ ] pytest + smoke + preprod incognito smoke green; desktop + 400 px screenshots.
