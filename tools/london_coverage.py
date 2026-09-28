"""london_coverage.py -- London CMA coverage census (JB-57).

Denominator-first coverage measurement. Reads the cached StatsCan CBC CSV
(table 33-10-1176, produced by tools/statcan_cbc_download.py), filters to
the London Census Metropolitan Area + a configurable NAICS list + an
employment-size floor, sums the business counts per NAICS, and cross-refs
engine/companies.json to report the coverage gap.

Design contract (tested in tests/test_london_coverage.py):
- parse_cbc_csv() is pure (str in, dict out); no I/O.
- naics_from_industry() extracts the code from "Label [XXXX]".
- size_lower_bound() maps "10-19 employees" -> 10 for the >=N filter.
- Report format is stable so we can diff it across periods.

Coverage math (matches JB-57 issue):
- Per NAICS the denominator is the sum across employment sizes >= min-size.
- The total denominator is the naive sum of per-NAICS counts. NAICS 5182
  is nested under 51, so the total is a sum-with-overlaps *ceiling*, not a
  unique count. This matches the issue's "~700" estimate.
- The numerator is the count of engine/companies.json entries whose city is
  in the London-CMA set. Per-NAICS numerator attribution is a JB-58 follow-up
  (registry has no NAICS tags today).

CLI:
    python tools/london_coverage.py                                   # 2026-06, defaults
    python tools/london_coverage.py --min-size 20                     # tighter denominator
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
DEFAULT_NAICS: tuple[str, ...] = ("5415", "5413", "51", "5182", "334", "3345", "3364")

# Registry cities considered inside the London CMA (matches tools/seed_ledc.py).
LONDON_METRO_CITIES = frozenset({
    "london", "st. thomas", "strathroy", "ilderton",
    "komoka", "dorchester", "putnam", "mount brydges",
})

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


def is_london_cma(geo: str) -> bool:
    """True when a GEO cell refers to the London Census Metropolitan Area.

    CBC uses several spellings across periods -- 'London, Ontario (Census
    metropolitan area)', 'London, census metropolitan area, Ontario', etc.
    We match liberally on 'london' + a CMA-ish token, and reject bare city
    rows (which duplicate CMA counts and would over-inflate)."""
    g = (geo or "").lower()
    if "london" not in g:
        return False
    return ("census metropolitan area" in g) or ("cma" in g)


def _industry_cell(row: dict) -> str:
    for k in _INDUSTRY_KEYS:
        if k in row and row[k]:
            return row[k]
    return ""


def parse_cbc_csv(text: str,
                  naics_codes=DEFAULT_NAICS,
                  min_size: int = DEFAULT_MIN_SIZE) -> dict[str, int]:
    """Sum business counts per NAICS, filtered to London CMA + size >= min_size."""
    counts: dict[str, int] = {code: 0 for code in naics_codes}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if not is_london_cma(row.get("GEO", "")):
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


def london_registry_count(registry: dict, london_cities=LONDON_METRO_CITIES) -> int:
    """Count registry entries whose city is inside the London CMA set."""
    n = 0
    for c in registry.get("companies", []):
        city = (c.get("city") or "").strip().lower()
        if city in london_cities:
            n += 1
    return n


def format_report(counts: dict[str, int],
                  registered: int,
                  period: str,
                  min_size: int) -> str:
    total = sum(counts.values())
    lines = [
        f"London CMA coverage census (CBC {period}, size >= {min_size} employees)",
        "-" * 60,
    ]
    for code, n in counts.items():
        lines.append(f"  NAICS {code:<5}  denominator: {n:>5}")
    lines.append("-" * 60)
    lines.append(f"  total denominator (sum-with-overlaps): {total}")
    lines.append(f"  registered London companies:            {registered}")
    if total > 0:
        pct = 100.0 * registered / total
        lines.append(f"  overall coverage:                       {registered} / {total} ({pct:.1f}%)")
    else:
        lines.append("  overall coverage:                       n/a (denominator=0; check cache)")
    lines.append("")
    lines.append("Note: per-NAICS numerator attribution needs NAICS-tagging of the registry")
    lines.append("(JB-58 follow-up). Current tool reports total registered count only.")
    return "\n".join(lines)


def _cache_path(period: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, f"33101176_{period}.csv")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--period", default=DEFAULT_PERIOD,
                    help=f"CBC period label (default: {DEFAULT_PERIOD})")
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--cache-dir", default=CACHE_DIR)
    ap.add_argument("--min-size", type=int, default=DEFAULT_MIN_SIZE,
                    help="employment-size lower bound (default: 10; use 1 to include solopreneurs)")
    ap.add_argument("--naics", nargs="+", default=list(DEFAULT_NAICS),
                    help="NAICS codes to include (default: tech-relevant set)")
    a = ap.parse_args(argv)

    path = _cache_path(a.period, a.cache_dir)
    if not os.path.exists(path):
        print(f"error: no cached CSV at {path}", file=sys.stderr)
        print(f"  run: python tools/statcan_cbc_download.py --period {a.period}",
              file=sys.stderr)
        return 2

    with open(path, encoding="utf-8") as f:
        text = f.read()
    counts = parse_cbc_csv(text, naics_codes=tuple(a.naics), min_size=a.min_size)
    registry = json.load(open(a.registry, encoding="utf-8"))
    registered = london_registry_count(registry)
    print(format_report(counts, registered, a.period, a.min_size))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
