"""company_key.py -- deterministic company-name canonicalization.

JB-55. Pure functions, no network, no LLM. Used everywhere we compare or dedupe
by company name (registry lookups, discovered-set membership, dedupe of jobs).

Rules:
- lowercase, NFKD-fold to ASCII (so "Zurich" and "Zürich" collide)
- strip punctuation to spaces (except the internal "-" and "&" which mean something)
- drop trailing legal suffixes -- possibly stacked ("Fidus Systems Inc.", "Foo Corp Ltd")
- collapse whitespace to single spaces
- return "" for None/empty

Legal suffixes are the ones we've actually seen in Canadian/US/EU registries.
Kept intentionally small: matches that are wrong here are silent bugs, so we
only remove tokens that are unambiguously corporate designators.
"""
from __future__ import annotations
import re
import unicodedata

# Suffixes stripped from the END only. Order longest-first so "co ltd" beats "co".
# Every entry is space-separated tokens after the punctuation strip -- so
# "S.A." becomes "sa" and is matched here as "sa".
_SUFFIXES = (
    "co ltd", "pty ltd", "s a de c v",
    "incorporated", "corporation", "limited",
    "s a",                                                # "S.A." after punct strip -> "s a"
    "inc", "corp", "ltd", "llc", "llp", "lp",
    "plc", "sa", "sarl", "gmbh", "ag", "bv", "nv", "kft",
    "kk", "oy", "as", "spa", "srl", "sas", "sl", "ab",
    "co", "company", "group", "holdings",
)

_PUNCT = re.compile(r"[.,;:!?()\[\]{}/\\\"'`_]+")
_WS = re.compile(r"\s+")


def company_key(name: str) -> str:
    """Return a stable, comparable canonical form of a company name.

    Idempotent: company_key(company_key(x)) == company_key(x).
    """
    if not name:
        return ""
    t = unicodedata.normalize("NFKD", name)
    t = t.encode("ascii", "ignore").decode("ascii")   # drop diacritics
    t = t.lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    # Peel legal suffixes from the tail, possibly stacked ("Foo Corp Ltd").
    changed = True
    while changed and t:
        changed = False
        for suf in _SUFFIXES:
            if t == suf:
                t = ""
                changed = True
                break
            if t.endswith(" " + suf):
                t = t[: -(len(suf) + 1)].rstrip()
                changed = True
                break
    return t
