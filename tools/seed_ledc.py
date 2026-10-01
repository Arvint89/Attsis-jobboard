"""seed_ledc.py -- add LEDC Business Directory companies to engine/companies.json.

Layer 1 seeding at scale (plan §4c). LEDC (London Economic Development
Corporation) publishes a public CSV export of its business directory --
~2700 rows -- which we filter to tech-adjacent London-area companies and
inject into the registry as platform='resolve' entries. JB-43 resolver
then auto-detects each company's ATS on the next sweep, and Layer 1
starts fetching them directly.

Design contract (tested in tests/test_seed_ledc.py):
- parse_ledc_csv() is pure (str in, list[dict] out); no I/O.
- to_registry_entry() maps one CSV row -> one companies.json entry.
- merge_seeds() dedupes via engine.company_key so re-runs are idempotent.
- The tool prefers a local cached CSV; --fetch pulls a fresh copy from LEDC.

CLI:
    # inspect what would change, don't write:
    python tools/seed_ledc.py --csv path/to/ledc_directory.csv --dry-run

    # write back to companies.json:
    python tools/seed_ledc.py --csv path/to/ledc_directory.csv

    # fetch fresh CSV and merge:
    python tools/seed_ledc.py --fetch
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))
from company_key import company_key  # noqa: E402

CSV_URL = "https://ledc.com/business-directory?export=true"
LOCAL_CSV = os.path.join(ROOT, "data", "ledc_directory.csv")
REGISTRY = os.path.join(ROOT, "engine", "companies.json")

# Kept sectors: only ones where a CV-driven tech/eng/health search finds jobs.
DEFAULT_SECTORS = frozenset({
    "Digital Media & Tech",
    "Advanced Manufacturing",
    "Digital Creative",
    "Health",
})

# Kept employee bands: only companies big enough to post persistently. Smaller
# shops rarely have open roles at any given moment and would just add noise.
DEFAULT_EMPLOYEE_BANDS = frozenset({"50-100", "100-200", "200+"})

# Industry mapping from LEDC sector -> the string engine/facets.py understands.
SECTOR_TO_INDUSTRY = {
    "Digital Media & Tech": "software/media",
    "Digital Creative": "software/media",
    "Advanced Manufacturing": "manufacturing",
    "Health": "health",
}

# London-metro city aliases -> normalized city name. Ring is 0 for these
# (London commutable); anything else falls back to the raw city string, ring 4.
LONDON_METRO = {
    "london", "london, on", "st. thomas", "strathroy", "ilderton",
    "komoka", "dorchester", "putnam", "mount brydges",
}


def parse_ledc_csv(text: str,
                   sectors=DEFAULT_SECTORS,
                   employee_bands=DEFAULT_EMPLOYEE_BANDS,
                   require_website: bool = True) -> list[dict]:
    """Filter the LEDC CSV to seed-worthy rows. Pure function."""
    kept: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if sectors and (row.get("Industry Sector") or "").strip() not in sectors:
            continue
        if employee_bands and (row.get("Employees") or "").strip() not in employee_bands:
            continue
        if require_website and not (row.get("Website") or "").strip():
            continue
        kept.append(row)
    return kept


def _clean_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    return u


def _city_and_ring(raw_city: str) -> tuple[str, int]:
    lo = (raw_city or "").strip().lower()
    if lo in LONDON_METRO:
        return "London", 0
    # Keep raw display city; ring 4 = Canada-wide by convention (see registry).
    return (raw_city or "").strip(), 4


def to_registry_entry(row: dict) -> dict:
    """Map one LEDC CSV row to one engine/companies.json entry."""
    city, ring = _city_and_ring(row.get("City", ""))
    return {
        "name": (row.get("Company Name") or "").strip(),
        "ring": ring,
        "platform": "resolve",
        "slug": "",
        "careers_url": _clean_url(row.get("Website", "")),
        "note": "seeded from LEDC Business Directory (JB-45 v2)",
        "flags": [],
        "industry": SECTOR_TO_INDUSTRY.get(
            (row.get("Industry Sector") or "").strip(), "other"
        ),
        "sponsors": None,
        "city": city,
    }


def merge_seeds(registry: dict, entries: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """Append new entries to registry['companies'], skipping any that duplicate
    an existing name (canonicalized). Returns (merged_registry, added, skipped)."""
    existing_keys = {company_key(c.get("name", "")) for c in registry.get("companies", [])}
    added: list[dict] = []
    skipped: list[dict] = []
    seen_new_keys: set[str] = set()
    for e in entries:
        key = company_key(e.get("name", ""))
        if not key:
            skipped.append(e)
            continue
        if key in existing_keys or key in seen_new_keys:
            skipped.append(e)
            continue
        added.append(e)
        seen_new_keys.add(key)
    merged = dict(registry)
    merged["companies"] = list(registry.get("companies", [])) + added
    return merged, added, skipped


def _load_registry(path: str = REGISTRY) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_registry(reg: dict, path: str = REGISTRY) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _fetch_csv() -> str:
    import requests
    r = requests.get(
        CSV_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; bt-jobboard-seed/1.0)"},
        timeout=60,
    )
    r.raise_for_status()
    os.makedirs(os.path.dirname(LOCAL_CSV), exist_ok=True)
    with open(LOCAL_CSV, "wb") as f:
        f.write(r.content)
    return r.text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", help="path to a cached LEDC CSV export")
    ap.add_argument("--fetch", action="store_true", help=f"GET {CSV_URL} (caches to data/ledc_directory.csv)")
    ap.add_argument("--out", default=REGISTRY, help="companies.json to write (default: engine/companies.json)")
    ap.add_argument("--dry-run", action="store_true", help="print counts + first 5 additions, do not write")
    a = ap.parse_args(argv)

    if a.fetch:
        text = _fetch_csv()
    elif a.csv:
        text = open(a.csv, encoding="utf-8").read()
    elif os.path.exists(LOCAL_CSV):
        text = open(LOCAL_CSV, encoding="utf-8").read()
    else:
        ap.error("give --csv <path> or --fetch (no cached CSV at data/ledc_directory.csv)")

    rows = parse_ledc_csv(text)
    entries = [to_registry_entry(r) for r in rows]

    registry = _load_registry(a.out)
    merged, added, skipped = merge_seeds(registry, entries)

    print(f"LEDC rows kept:        {len(rows)}")
    print(f"registry before:       {len(registry.get('companies', []))}")
    print(f"registry after:        {len(merged['companies'])}")
    print(f"new additions:         {len(added)}")
    print(f"skipped (duplicates):  {len(skipped)}")
    print()
    print("first 5 additions:")
    for e in added[:5]:
        print(f"  - {e['name']:<45} ring={e['ring']} sector={e['industry']} careers={e['careers_url']}")

    if a.dry_run:
        print("\n(dry-run: no write)")
        return 0

    _write_registry(merged, a.out)
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
