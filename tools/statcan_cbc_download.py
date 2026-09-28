"""statcan_cbc_download.py -- fetch StatsCan Canadian Business Counts (JB-57).

Downloads table **33-10-1176** (Canadian Business Counts, with employees, by
CMA/CSD/NAICS/employment-size, semiannual) as a ZIP, extracts the CSV, and
caches it under `data/statcan/33101176_YYYY-MM.csv`. That cached file is the
input to tools/london_coverage.py (and future per-region coverage tools).

Design contract:
- One HTTP GET per invocation; the cache path encodes the ref-date the caller
  wants, so re-runs of the same period are free.
- The tool NEVER modifies engine/companies.json -- coverage tools read from
  the cache to produce reports only.
- Kept intentionally boring: no argparse gymnastics, one clear function
  (`download()`) that tests can call with a fake fetcher.

CLI:
    python tools/statcan_cbc_download.py                     # latest known period
    python tools/statcan_cbc_download.py --period 2026-06    # explicit period
"""
from __future__ import annotations
import argparse
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE_DIR = os.path.join(ROOT, "data", "statcan")

# StatsCan Web Data Service full-table download endpoint. The table PID is
# 33100117601 (product 33-10-1176, view 01). See
# https://www.statcan.gc.ca/en/developers/wds for endpoint stability notes.
TABLE_PID = "33100117601"
ZIP_URL = f"https://www150.statcan.gc.ca/n1/tbl/csv/{TABLE_PID}-eng.zip"

DEFAULT_PERIOD = "2026-06"  # StatsCan CBC is semiannual (June / December).


def _default_fetcher(url: str) -> bytes:
    """Real network fetch. Overridable in tests."""
    import requests  # local import so unit tests don't need it
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; bt-jobboard-census/1.0)"},
        timeout=120,
    )
    r.raise_for_status()
    return r.content


def extract_csv_from_zip(zip_bytes: bytes) -> bytes:
    """Return the raw CSV bytes from the CBC ZIP (single .csv member, ignore metadata)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        csv_members = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csv_members:
            raise ValueError(f"no CSV in ZIP; got {z.namelist()!r}")
        # Prefer the data CSV over MetaData.csv.
        data = [n for n in csv_members if "metadata" not in n.lower()]
        pick = (data or csv_members)[0]
        return z.read(pick)


def cache_path(period: str = DEFAULT_PERIOD, cache_dir: str = CACHE_DIR) -> str:
    return os.path.join(cache_dir, f"33101176_{period}.csv")


def download(period: str = DEFAULT_PERIOD,
             fetcher=None,
             cache_dir: str = CACHE_DIR) -> str:
    """Download the CBC ZIP, extract the CSV, cache to disk, return the path."""
    fetcher = fetcher or _default_fetcher
    out_path = cache_path(period, cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    zip_bytes = fetcher(ZIP_URL)
    csv_bytes = extract_csv_from_zip(zip_bytes)
    with open(out_path, "wb") as f:
        f.write(csv_bytes)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--period", default=DEFAULT_PERIOD,
                    help=f"YYYY-MM label for the cached file (default: {DEFAULT_PERIOD})")
    ap.add_argument("--cache-dir", default=CACHE_DIR)
    a = ap.parse_args(argv)

    path = download(a.period, cache_dir=a.cache_dir)
    size_kb = os.path.getsize(path) // 1024
    print(f"wrote {path} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
