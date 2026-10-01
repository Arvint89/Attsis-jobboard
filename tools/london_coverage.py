"""london_coverage.py -- CMA coverage census (JB-57, generalized in JB-58 follow-up).

Denominator-first coverage measurement. Reads the cached StatsCan CBC CSV
(table 33-10-1176, produced by tools/statcan_cbc_download.py), filters to a
named Census Metropolitan Area + a configurable NAICS list + an
employment-size floor, sums the business counts per NAICS, and cross-refs
engine/companies.json to report the coverage gap.

Design contract (tested in tests/test_london_coverage.py):
- parse_cbc_csv() is pure (str in, dict out); no I/O.
- naics_from_industry() extracts the code from "Label [XXXX]".
- size_lower_bound() maps "10-19 employees" -> 10 for the >=N filter.
- is_cma(geo, cma_name) accepts CMA rows only (rejects bare-city rows).
- Report format is stable so we can diff it across periods and CMAs.

Coverage math (matches JB-57 issue):
- Per NAICS the denominator is the sum across employment sizes >= min-size.
- The total denominator is the naive sum of per-NAICS counts. NAICS 5182
  is nested under 51, so the total is a sum-with-overlaps *ceiling*, not a
  unique count. This matches the issue's "~700" estimate.
- The numerator is the count of engine/companies.json entries whose city is
  in the target CMA's city set. Per-NAICS numerator attribution is a
  follow-up (registry has no NAICS tags today).

CLI:
    python tools/london_coverage.py                                   # London 2026-06 default
    python tools/london_coverage.py --cma Toronto                     # switch CMA
    python tools/london_coverage.py --cma Waterloo --min-size 20      # tighter denominator
    python tools/london_coverage.py --naics 5415 5413                 # subset
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE_DIR = os.path.join(ROOT, "data", "statcan")
REGISTRY = os.path.join(ROOT, "engine", "companies.json")

DEFAULT_PERIOD = "2026-06"
DEFAULT_MIN_SIZE = 10
DEFAULT_CMA = "London"
DEFAULT_NAICS: tuple[str, ...] = ("5415", "5413", "51", "5182", "334", "3345", "3364")

# StatsCan CMA city sets. Keys are the --cma flag value (case-insensitive
# lookup below). Values are the registry-city names (lowercased) considered
# inside that CMA. Extend by adding new keys as we onboard new regions.
# Source: StatsCan census subdivision lists for each CMA (2021 census).
CMA_CITIES: dict[str, frozenset[str]] = {
    "london": frozenset({
        "london", "st. thomas", "strathroy", "ilderton",
        "komoka", "dorchester", "putnam", "mount brydges",
    }),
    "toronto": frozenset({
        "toronto", "mississauga", "brampton", "markham", "vaughan",
        "richmond hill", "oakville", "burlington", "ajax", "pickering",
        "whitby", "aurora", "newmarket", "milton", "halton hills",
        "king", "caledon", "east gwillimbury", "whitchurch-stouffville",
    }),
    "waterloo": frozenset({
        "kitchener", "waterloo", "cambridge",
        "wilmot", "wellesley", "woolwich", "north dumfries",
    }),
    "ottawa": frozenset({
        "ottawa",  # ON side of Ottawa-Gatineau; QC subdivisions excluded
    }),
}

# Backwards-compat alias for callers that imported the London-only constant.
LONDON_METRO_CITIES = CMA_CITIES["london"]

# StatsCan CBC "Business employment size" categorical labels -> lower bound.
# Values not in this map (e.g. "Total, with employees") are excluded so they
# aren't double-counted against the per-bucket rows.
EMPLOYMENT_SIZE_LOWER_BOUND: dict[str, int] = {
    "1-4 employees": 1,
    "5-9 employees": 5,
    "10-19 employees": 10,
    "20-49 employees": 20,
    "50-99 employees": 50,
    "100-199 employees": 100,
    "200-499 employees": 200,
    "500 or more employees": 500,
    "500+ employees": 500,
}

# Possible header names for the NAICS/industry column across CBC CSV variants.
_INDUSTRY_KEYS = (
    "Business industry",
    "North American Industry Classification System (NAICS)",
    "Industry",
)


def naics_from_industry(label: str) -> str:
    """Extract the NAICS code from a CBC industry label like 'X [5415]'. '' if none."""
    m = re.search(r"\[(\d{2,6})\]\s*$", label or "")
    return m.group(1) if m else ""


def size_lower_bound(label: str) -> int:
    """Map an employment-size label to its numeric lower bound. -1 if unknown."""
    return EMPLOYMENT_SIZE_LOWER_BOUND.get((label or "").strip(), -1)


def is_cma(geo: str, cma_name: str) -> bool:
    """True when a GEO cell refers to the named CMA.

    CBC uses several spellings across periods -- 'X, Ontario (Census
    metropolitan area)', 'X, census metropolitan area, Ontario', etc.
    We match liberally on the cma name + a CMA-ish token, and reject bare
    city rows (which duplicate CMA counts and would over-inflate)."""
    g = (geo or "").lower()
    name = (cma_name or "").strip().lower()
    if not name or name not in g:
        return False
    return ("census metropolitan area" in g) or ("cma" in g)


def is_london_cma(geo: str) -> bool:
    """Backwards-compat wrapper for the London-only call site."""
    return is_cma(geo, "London")


def _industry_cell(row: dict) -> str:
    for k in _INDUSTRY_KEYS:
        if k in row and row[k]:
            return row[k]
    return ""


def parse_cbc_csv(text: str,
                  naics_codes=DEFAULT_NAICS,
                  min_size: int = DEFAULT_MIN_SIZE,
                  cma_name: str = DEFAULT_CMA) -> dict[str, int]:
    """Sum business counts per NAICS, filtered to the named CMA + size >= min_size."""
    counts: dict[str, int] = {code: 0 for code in naics_codes}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if not is_cma(row.get("GEO", ""), cma_name):
            continue
        code = naics_from_industry(_industry_cell(row))
        if code not in counts:
            continue
        lb = size_lower_bound(row.get("Business employment size", ""))
        if lb < 0 or lb < min_size:
            continue
        raw = (row.get("VALUE") or "").strip()
        if not raw:
            continue
        try:
            counts[code] += int(float(raw))
        except ValueError:
            continue
    return counts


def cma_registry_count(registry: dict, cma_name: str = DEFAULT_CMA) -> int:
    """Count registry entries whose city is inside the named CMA's city set."""
    cities = CMA_CITIES.get((cma_name or "").strip().lower(), frozenset())
    n = 0
    for c in registry.get("companies", []):
        city = (c.get("city") or "").strip().lower()
        if city in cities:
            n += 1
    return n


def london_registry_count(registry: dict, london_cities=None) -> int:
    """Backwards-compat wrapper for the London-only call site."""
    if london_cities is None:
        return cma_registry_count(registry, "London")
    n = 0
    for c in registry.get("companies", []):
        city = (c.get("city") or "").strip().lower()
        if city in london_cities:
            n += 1
    return n


def format_report(counts: dict[str, int],
                  registered: int,
                  period: str,
                  min_size: int,
                  cma_name: str = DEFAULT_CMA) -> str:
    total = sum(counts.values())
    lines = [
        f"{cma_name} CMA coverage census (CBC {period}, size >= {min_size} employees)",
        "-" * 60,
    ]
    for code, n in counts.items():
        lines.append(f"  NAICS {code:<5}  denominator: {n:>5}")
    lines.append("-" * 60)
    lines.append(f"  total denominator (sum-with-overlaps): {total}")
    lines.append(f"  registered {cma_name} companies:            {registered}")
    if total > 0:
        pct = 100.0 * registered / total
        lines.append(f"  overall coverage:                       {registered} / {total} ({pct:.1f}%)")
    else:
        lines.append("  overall coverage:                       n/a (denominator=0; check cache)")
    lines.append("")
    lines.append("Note: per-NAICS numerator attribution needs NAICS-tagging of the registry")
    lines.append("(follow-up). Current tool reports total registered count only.")
    return "\n".join(lines)


def _cache_path(period: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, f"33101176_{period}.csv")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--period", default=DEFAULT_PERIOD,
                    help=f"CBC period label (default: {DEFAULT_PERIOD})")
    ap.add_argument("--cma", default=DEFAULT_CMA,
                    help=f"CMA name (default: {DEFAULT_CMA}). "
                         f"Supported: {', '.join(sorted(CMA_CITIES))}")
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--cache-dir", default=CACHE_DIR)
    ap.add_argument("--min-size", type=int, default=DEFAULT_MIN_SIZE,
                    help="employment-size lower bound (default: 10; use 1 to include solopreneurs)")
    ap.add_argument("--naics", nargs="+", default=list(DEFAULT_NAICS),
                    help="NAICS codes to include (default: tech-relevant set)")
    a = ap.parse_args(argv)

    if (a.cma or "").strip().lower() not in CMA_CITIES:
        print(f"error: unsupported --cma '{a.cma}'. "
              f"Add its city set to CMA_CITIES in tools/london_coverage.py, "
              f"then re-run. Supported: {', '.join(sorted(CMA_CITIES))}",
              file=sys.stderr)
        return 2

    path = _cache_path(a.period, a.cache_dir)
    if not os.path.exists(path):
        print(f"error: no cached CSV at {path}", file=sys.stderr)
        print(f"  run: python tools/statcan_cbc_download.py --period {a.period}",
              file=sys.stderr)
        return 2

    with open(path, encoding="utf-8") as f:
        text = f.read()
    counts = parse_cbc_csv(text, naics_codes=tuple(a.naics),
                           min_size=a.min_size, cma_name=a.cma)
    registry = json.load(open(a.registry, encoding="utf-8"))
    registered = cma_registry_count(registry, a.cma)
    print(format_report(counts, registered, a.period, a.min_size, a.cma))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
