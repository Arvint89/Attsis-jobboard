# Release process — how to cut a release
Ties together VERSIONING.md (numbers), BRANCHING.md (branches), RELEASES.md (the tracker).
Uses the engineering:deploy-checklist mindset.

## Steps (every release)
1. **Decide the bump** (VERSIONING.md): bug-only → BUGS; new feature/phase → MINOR; breaking → MAJOR.
2. **Gate**: `pytest -q tests/` and `python engine/smoke_test.py` both green. (Definition of Done)
3. **Update docs**: add a `CHANGELOG.md` entry AND a new row in **`RELEASES.md`** (the tracker).
4. **Merge to product branch**: PR `develop → main` (main = live product, per BRANCHING.md).
5. **Tag it** on main:
   ```bash
   git tag -a vX.Y.Z -m "one-line summary"
   git push --tags
   ```
6. **Deploy**: pushing to `main` triggers the Action → Pages updates automatically.
7. **(Optional) GitHub Release**: turn the tag into a Release with notes:
   `gh release create vX.Y.Z --notes "…"` — this is GitHub's own release tracker, mirroring RELEASES.md.

## Definition of Done (release)
- [ ] Tests + smoke green
- [ ] CHANGELOG.md entry added
- [ ] **RELEASES.md row added**
- [ ] Merged to main
- [ ] Tagged vX.Y.Z and pushed
- [ ] Live site verified
