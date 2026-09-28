"""skills_db.py -- deterministic canonical skills + titles DB with aliases.

Loads a single JSON file (data/skills.json) and exposes token-safe
resolution:

    resolve_skills(text) -> [canonical]        # canonical skill names hit
    resolve_titles(text) -> [canonical]        # canonical title names hit
    resolve(text)        -> {"skills": [...], "titles": [...]}

Matching is whole-token / whole-phrase (mirrors jobfilter._tokp), case-
insensitive, no LLM. Alias hits fold up to canonical.

Design rules:
- Additive to the CV-driven profile: the classifier keeps its authority;
  this DB widens recall by resolving aliases the CV never mentioned.
- Multi-word phrases match as bounded phrases; single tokens match as
  whole tokens (no substring hits inside longer words).
- One JSON file so it stays editable in a spreadsheet.
"""
from __future__ import annotations
import json
import os
import re
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DB_PATH = os.path.join(ROOT, "data", "skills.json")

_BOUND_L = r"(?<![a-z0-9])"
_BOUND_R = r"(?![a-z0-9])"


def _bound_re(needle: str) -> re.Pattern:
    return re.compile(_BOUND_L + re.escape(needle.lower()) + _BOUND_R, re.IGNORECASE)


@lru_cache(maxsize=4)
def load_db(path: str | None = None) -> dict:
    p = path or DEFAULT_DB_PATH
    if not os.path.exists(p):
        return {"skills": [], "titles": []}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def _compiled_index(path: str | None = None) -> tuple[tuple, tuple]:
    """Return ((skill_patterns), (title_patterns)) where each entry is
    (canonical, [compiled_regex, ...]). LRU-cached so callers may hit
    resolve() many times without paying re-compile cost."""
    db = load_db(path)
    skills = []
    for row in db.get("skills", []):
        canonical = (row.get("canonical") or "").strip()
        if not canonical:
            continue
        forms = [canonical] + [a for a in (row.get("aliases") or []) if a]
        pats = tuple(_bound_re(f) for f in forms)
        skills.append((canonical, pats))
    titles = []
    for row in db.get("titles", []):
        canonical = (row.get("canonical") or "").strip()
        if not canonical:
            continue
        forms = [canonical] + [a for a in (row.get("aliases") or []) if a]
        pats = tuple(_bound_re(f) for f in forms)
        titles.append((canonical, pats))
    return (tuple(skills), tuple(titles))


def resolve_skills(text: str, path: str | None = None) -> list[str]:
    if not text:
        return []
    skills, _titles = _compiled_index(path)
    hit = []
    for canonical, pats in skills:
        for p in pats:
            if p.search(text):
                hit.append(canonical)
                break
    return hit


def resolve_titles(text: str, path: str | None = None) -> list[str]:
    if not text:
        return []
    _skills, titles = _compiled_index(path)
    hit = []
    for canonical, pats in titles:
        for p in pats:
            if p.search(text):
                hit.append(canonical)
                break
    return hit


def resolve(text: str, path: str | None = None) -> dict:
    return {"skills": resolve_skills(text, path), "titles": resolve_titles(text, path)}


def stats(path: str | None = None) -> dict:
    db = load_db(path)
    skills = db.get("skills", [])
    titles = db.get("titles", [])
    return {
        "skills": len(skills),
        "titles": len(titles),
        "skill_aliases": sum(len(r.get("aliases") or []) for r in skills),
        "title_aliases": sum(len(r.get("aliases") or []) for r in titles),
    }
