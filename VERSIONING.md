# Versioning policy — Attsis Job Board
Scheme: **MAJOR.MINOR.BUGS** (three numbers, e.g. `0.6.1`). Semantic-versioning style.

| Part | Bump when… | Example |
|---|---|---|
| **MAJOR** | breaking change or a big milestone shipped (e.g. multi-user, employer side) | 0.x.x → 1.0.0 |
| **MINOR** | a new feature / phase added (backwards-compatible) | 0.6.x → 0.7.0 |
| **BUGS** | only bug fixes, no new features | 0.6.0 → 0.6.1 |

Rules:
- Bumping MINOR resets BUGS to 0 (0.6.3 → 0.7.0). Bumping MAJOR resets both (0.9.2 → 1.0.0).
- Every release is **tagged on `main`**: `git tag -a v0.6.1 -m "..."` then `git push --tags`.
- The version is recorded in `CHANGELOG.md` and the site footer.
- **Current: 0.10.0** (bug-fix release: the "ble" whole-word fix). 0.6.0 was the first live release on Pages.

How it maps to work: a `type:bug` issue closing → BUGS bump; a `type:feature` issue/phase → MINOR.
