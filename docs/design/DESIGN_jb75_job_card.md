# DESIGN: JB-75 job card v2 (#188)
_v1 · 2026-10-11 · Parent: #181 · Audit gap G3 · Labels: ✅ verified · ⚠️ inferred · ❓ unchecked_

## Problem
✅ Today's card puts everything in the header (snippet, source, skills, the raw "why" list) and hides gaps behind a separate **Gap check** button. The prototype card (`screenshots/jb72/prototype_v6_reference.png`) is **scannable** (score, title, where, when, three chips, checks, one WHY line) and **expands in place** into WHY IT FITS / GAPS TO ADDRESS. This is pattern 4 in `docs/UI_DESIGN.md`, which BT already chose.

✅ Honesty issue: without a saved profile, scores come from the **sample profile** (`jobs.json` `person` = BT's own profile), but the server explanation says "your CV lists N skills". That's false for a visitor.

## Decisions
### D1. Detail access
| Option | Pros | Cons |
|---|---|---|
| A. Separate Gap check button (today) | Simple | Two clicks; gaps feel like an add-on |
| **B. Click the card header to expand in place** (prototype) | One click; "why" and "gaps" sit together | Header clicks must not swallow link/button clicks |
| C. Side panel / detail page | Room for full JD | Heavier; breaks the scan |

**Choice: B.** Clicks on `a`/`button` inside the header are ignored by the toggle.

### D2. Lazy body
The body (gap analysis tokenises the JD) renders **only when opened**. **Why:** ✅ 700+ cards re-render on every filter change or map pan; computing gaps for all of them wastes time. Open state is kept per job key, so it survives re-renders.

### D3. Header contents (prototype order)
Score box `N /10` · title (link to posting) · company · 📍 city (+N more) · distance ("in your city" when ring 0, else "N km away") · age ("2 weeks ago") · chips: salary (or "Salary not listed"), arrangement, industry, visa sponsorship · **checks**: distance band (✓ Within 50/100/200 km) and ✓ Remote · WHY line · save (bookmark) + expand chevron.
Snippet and source **move into the body**. **Tradeoff:** less text at a glance, but faster scanning, which is the point of the list.

### D4. WHY wording
With a profile: the browser-side reasons (`scoreJob`). Without: the server explanation, rewritten to say **"the sample profile"** instead of "your CV", plus a pointer to add a CV. **Why not hide it:** the reasons explain the ranking, which is a key part of what the product offers.

### D5. Score colours
8+ green, 7 cyan, ≤6 muted (same as the map pins, DESIGN_map_v2 D8). 7 was orange before; now one scale everywhere.

## Contract (pure, Node-tested; `/* CARD-PURE-BEGIN */…END`)
```js
relAge(isoDate, nowMs) -> 'today' | 'yesterday' | 'N days ago' | '1 week ago' | 'N weeks ago' | 'N months ago' | ''
distLabel(job)         -> 'in your city' | 'N km away' | ''
distCheck(job)         -> 'Within 50 km' | 'Within 100 km' | 'Within 200 km' | ''
sampleWhy(explanation) -> short explanation with "your CV" → "the sample profile", score prefix stripped
```

## Acceptance
- [ ] Header shows the D3 fields; clicking the header toggles the body; clicking the title link, save or tailor does not.
- [ ] Body: WHY IT FITS (matched chips + reasons), GAPS TO ADDRESS (with a profile) or "Add your CV" (without), ABOUT THE ROLE snippet, source, Open posting, Tailor (still gated by `_tailorPayReady()`).
- [ ] Open state survives re-render (filter change).
- [ ] No "your CV" wording when no profile is saved.
- [ ] pytest + smoke + preprod smoke; desktop + 400 px screenshots.
