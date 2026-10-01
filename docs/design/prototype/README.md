# Design prototype — Attsis Jobs
_Generated 2026-09-23. Design reference only — not production code._

## Put it in the repo here
```
Attsis-jobboard/
└── docs/
    └── design/
        └── prototype/          ← copy this whole folder's contents here
            ├── README.md
            ├── COMMERCIALIZATION_PLAN.md
            ├── Attsis Job Board v6.dc.html
            ├── Attsis Jobs Plan.dc.html
            ├── support.js
            ├── colors_and_type.css
            └── doc-page.js
```
Keep it under `docs/` (not `site/`) so GitHub Pages doesn't publish it.

```powershell
git checkout main; git pull origin main
git checkout -b docs/jb-55-design-prototype
# copy the folder contents into docs/design/prototype/
git add docs/design/prototype
git commit -m "JB-55: add design prototype v6 + commercialization plan"
git push -u origin docs/jb-55-design-prototype   # open PR, "Refs #55"
```

## Open it
Double-click `Attsis Job Board v6.dc.html` (or run `python -m http.server` in this folder and open it).
Needs internet for fonts, icons (Lucide) and map tiles (Esri). All data is inline demo data.

## What's in the prototype
| Tab | Feature | Plan section |
|---|---|---|
| Roles | Board-first list + map (score pins, 50/100/200 km rings, search-as-I-move), AI ask box, daily briefing, near misses, preferences ✓/✗ | §1–3, §10 |
| Tracker | Kanban, "heard back?" prompts, channel settings | §3 |
| Queue | Assisted apply with rules; submits in the user's browser | §10 |
| Prep | Mock interviewer (technical / behavioural / negotiation), company brief | §3 |
| Learn | Teardowns, sims, shorts; creator + affiliate model | §4 |
| Profile | CV, cover letter, LinkedIn PDF, GitHub, links, typed keywords, preferences, Attsis numerology | §1, §9 |
| Tailor | CV rewrites with accept/skip, cover letter, Pro unlock | §4 |

## Caveats
- Company incorporation dates are placeholders except Natus (Oakville), Kepler and Profound Medical.
- AI features (ask box, mock interviewer, tailoring) are scripted in the prototype.
- `.dc.html` files need `support.js` beside them — copy the folder as a whole.
