"""feedback_ingest.py -- ADR-009 D4: GitHub issues -> JSONL + weekly rollup + suppress candidates.

  gh issue list --state all --search "attsis-feedback in:body" --limit 1000 \
     --json number,author,createdAt,body > issues.json
  python tools/feedback_ingest.py --issues issues.json --out data
  python tools/feedback_ingest.py --from-gh --out data            # runs the gh call itself

Writes (all under --out, gitignored by default):
  reports/YYYY-MM-DD.jsonl     one valid report payload per line (+ issue, author, created)
  REPORTS_WEEK.md              weekly rollup (copy into docs/status/ via a PR to keep it)
  suppress_candidates.json     link_404 from >=3 people in 48 h (review before engine/suppressed.json)
Read-only against GitHub; never commits.
"""
import argparse, json, os, subprocess, sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import feedback as fb  # noqa: E402

GH_ARGS = ["gh", "issue", "list", "--state", "all", "--search", "attsis-feedback in:body",
           "--limit", "1000", "--json", "number,author,createdAt,body"]


def load_issues(args):
    if args.from_gh:
        return json.loads(subprocess.run(GH_ARGS, capture_output=True, text=True, check=True).stdout or "[]")
    with open(args.issues, encoding="utf-8") as f:
        return json.load(f)


def write_jsonl(recs, out_dir):
    by_day = defaultdict(list)
    for r in recs:
        by_day[(r["created"] or "unknown")[:10]].append(r)
    os.makedirs(out_dir, exist_ok=True)
    for day, rs in by_day.items():
        with open(os.path.join(out_dir, f"{day}.jsonl"), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rs)


def main(argv=None):
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--issues", help="JSON from `gh issue list --json number,author,createdAt,body`")
    src.add_argument("--from-gh", action="store_true", help="call gh issue list directly")
    ap.add_argument("--out", default="data")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args(argv)

    recs = fb.ingest(load_issues(args))
    reports = [r for r in recs if r["kind"] == "report"]
    write_jsonl(reports, os.path.join(args.out, "reports"))
    with open(os.path.join(args.out, "REPORTS_WEEK.md"), "w", encoding="utf-8") as f:
        f.write(fb.reports_week_md(recs, args.today))
    cands = fb.suppress_candidates(recs)
    with open(os.path.join(args.out, "suppress_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(cands, f, indent=2)
    print(f"[feedback] {len(recs)} valid payloads ({len(reports)} reports), "
          f"{len(cands)} suppress candidates -> {args.out}")


if __name__ == "__main__":
    main()
