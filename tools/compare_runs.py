"""compare_runs.py -- JB-42: what changed between two job-board runs?

  python tools/compare_runs.py            # last two live runs from the live site
  python tools/compare_runs.py -3 -1      # compare any two entries (Python-style indices)
  python tools/compare_runs.py --file site/data/history.json
"""
import argparse, json, sys


def load(path=None):
    if path:
        return json.load(open(path, encoding="utf-8"))
    import requests
    url = "https://arvint89.github.io/Attsis-jobboard/data/history.json"
    return requests.get(url, headers={"Cache-Control": "no-cache"}, timeout=20).json()


def diff(a: dict, b: dict) -> list:
    """Rows of (metric, before, after, change) for two history entries."""
    rows = []
    for k in ("kept", "matches", "companies_with_roles", "discovered", "errors", "unresolved", "run_seconds"):
        x, y = a.get(k), b.get(k)
        ch = (y - x) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else ""
        rows.append((k, x, y, ch))
    srcs = sorted(set(a.get("kept_by_source", {})) | set(b.get("kept_by_source", {})))
    for s in srcs:
        x, y = a.get("kept_by_source", {}).get(s, 0), b.get("kept_by_source", {}).get(s, 0)
        if x != y:
            rows.append(("  kept: " + s, x, y, y - x))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?", type=int, default=-2)
    ap.add_argument("b", nargs="?", type=int, default=-1)
    ap.add_argument("--file")
    args = ap.parse_args()
    h = [e for e in load(args.file) if e.get("mode") == "live"]
    if len(h) < 2:
        print(f"only {len(h)} live run(s) in history so far - need two to compare"); return
    A, B = h[args.a], h[args.b]
    print(f"before: {A['generated']}\nafter:  {B['generated']}\n")
    for m, x, y, ch in diff(A, B):
        sign = f"{ch:+}" if isinstance(ch, (int, float)) and ch != "" else ""
        print(f"{m:32} {str(x):>8} -> {str(y):<8} {sign}")
    if B.get("alerts"):
        print("\nALERTS:"); [print(" !", a) for a in B["alerts"]]


if __name__ == "__main__":
    sys.exit(main())
