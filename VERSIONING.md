# Versioning policy — Attsis Job Board
Scheme: **MAJOR.MINOR.BUGS** (three numbers, e.g. `0.6.1`). Semantic-versioning style.

| Part | Bump when… | Example |
|---|---|---|
| **MAJOR** | breaking change or a big milestone shipped (e.g. multi-user, employer side) | 0.x.x → 1.0.0 |
| **MINOR** | a new feature / phase added (backwards-compatible) | 0.6.x → 0.7.0 |
| **BUGS** | only bug fixes, no new features | 0.6.0 → 0.6.1 |

Rules:
- Bumping MINOR resets BUGS to 0 (0.6.3 → 0.7.0). Bumping MAJOR resets both (0.9.2 → 1.0.0).
- **The `VERSION` file at the repo root is the source of truth.** The `auto-tag` GitHub Action (`.github/workflows/tag.yml`, JB-27) reads it on every push to `main` and creates an annotated tag `v<VERSION>` on that commit if — and only if — one doesn't already exist. Re-pushing with the same VERSION is a silent no-op.
- Bumping a release = edit `VERSION` **and** `CHANGELOG.md` in the same commit → merge to `main` → the tag appears automatically on the correct commit.
- Manual tagging is no longer needed and should be avoided (it was the source of the v0.7.0-on-wrong-commit and re-tagging incidents that motivated JB-27).
- **Current: 0.11.0** (see `VERSION`).

How it maps to work: a `type:bug` issue closing → BUGS bump; a `type:feature` issue/phase → MINOR.
