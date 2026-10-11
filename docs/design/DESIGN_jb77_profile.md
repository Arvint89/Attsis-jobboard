# DESIGN: JB-77 profile v2 (#190)
_v1 · 2026-10-11 · Parent: #181 · Audit gap G5 · Labels: ✅ verified · ⚠️ inferred · ❓ unchecked_

## Problem
✅ Live Profile is a sequence of separate panels (quick start → paste CV → Analyze → review) that show one at a time (`screenshots/jb73/live_profile.png`). The prototype (`proto_profile.png`) shows **all sources at once** on the left and a sticky **"What we'll match on"** panel on the right, so the user sees cause (sources) and effect (keywords) together.

## Decisions
### D1. Layout
| Option | Pros | Cons |
|---|---|---|
| A. Keep the step-by-step panels | Already works | Hides what drives matching; "where did my keywords go?" |
| **B. Two columns: sources left, live keyword panel right (sticky)** | Prototype; cause and effect on one screen | More layout code; stacks on mobile |

**Choice: B.** Existing element IDs and handlers are kept (`cvText`, `analyzeBtn`, `saveBtn`, `titleTags`…), so the extraction and scoring code is untouched.

### D2. Sources
| Source | Status |
|---|---|
| CV / résumé (paste or .docx/.pdf/.txt) | ✅ existing |
| Cover letter | ✅ existing |
| **LinkedIn PDF** (Profile → Resources → Save to PDF) | **new**: same PDF reader, its text joins the CV text for extraction |
| You: name + home city + typed titles/skills | ✅ existing quick start + the add-keyword inputs |
| GitHub repos, portfolio links | ❌ not built. Not shown, because fake cards would mislead. Separate spike if wanted. |

### D3. Right panel states
- **No profile:** the keyword editor is visible (empty), so a user can type titles/skills without any CV.
- **After Analyze / Edit:** the editor shows the draft. The button reads **"Save and re-rank N roles"** (N = roles loaded).
- **Saved:** the saved-profile summary (titles, skills, Re-parse / Edit / Clear).

## Acceptance
- [ ] Header "Your profile · read in your browser" / "What should we match you on?"
- [ ] No profile: You + CV + Cover letter + LinkedIn PDF cards on the left, editor on the right.
- [ ] Typing a title and saving with no CV creates a profile and re-ranks.
- [ ] LinkedIn PDF text is included in extraction.
- [ ] Profile saved: summary on the right; sources stay available on the left.
- [ ] pytest + smoke + preprod smoke; screenshots desktop + 400 px.
