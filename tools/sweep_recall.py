"""sweep_recall.py -- JB-42: how many of the daily sweep's 7+ roles does the board show?

Reads the sweep log (on BT's PC) and the live jobs.json, and matches by company + title words.
  python tools/sweep_recall.py
  python tools/sweep_recall.py --log "C:\\...\\Daily_Sweep_Log.md" --runs 5
"""
import argparse, json, os, re, sys

DEFAULT_LOG = os.path.expanduser(r"~\OneDrive\Documents\Bharanidharan\Job_application\Daily_Sweep_Log.md")
BULLET = re.compile(r"^\s*-\s+\*\*(?P<company>[^*]+?)\s+[\u2014-]\s+(?P<titles>[^*]+?)\*\*")
STOP = {"and", "the", "of", "for", "a", "an", "senior", "sr", "staff", "lead", "principal", "ii", "iii", "iv"}


def parse_log(text: str, runs: int = 3) -> list:
    """[{run, company, title}] from the 'Fresh 7+' sections of the newest `runs` entries."""
    out, run, in_fresh, seen_runs = [], None, False, 0
    for line in text.splitlines():
        if line.startswith("## "):
            seen_runs += 1
            if seen_runs > runs:
                break
            run, in_fresh = line[3:13], False
            continue
        if line.startswith("### "):
            in_fresh = line.lower().startswith("### fresh 7+")
            continue
        if in_fresh:
            m = BULLET.match(line)
            if m:
                for t in re.split(r"\s+(?:AND|and|\+)\s+", m.group("titles")):
                    out.append({"run": run, "company": m.group("company").strip(), "title": t.strip()})
    return out


def _words(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP}


def _co(s):
    return re.sub(r"\b(inc|ltd|corp|corporation|technologies|technology|co)\b|[^a-z0-9]", "", (s or "").lower())


def found(role: dict, jobs: list) -> dict | None:
    """Board job for this sweep role: same company (fuzzy) and >=50% of title words shared."""
    c = _co(role["company"])
    want = _words(role["title"])
    for j in jobs:
        jc = _co(j.get("company"))
        if not c or not jc or not (c in jc or jc in c):
            continue
        if not want or len(want & _words(j.get("title"))) >= max(1, len(want) // 2):
            return j
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    roles = parse_log(open(args.log, encoding="utf-8").read(), args.runs)
    import requests
    d = requests.get("https://arvint89.github.io/Attsis-jobboard/data/jobs.json",
                     headers={"Cache-Control": "no-cache"}, timeout=30).json()
    jobs = d.get("matches", []) + d.get("below", [])
    hits = [(r, found(r, jobs)) for r in roles]
    n = sum(1 for _, j in hits if j)
    print(f"board data: {d.get('generated')} | sweep runs checked: {args.runs}")
    print(f"SWEEP RECALL: {n}/{len(roles)} = {100 * n // max(1, len(roles))}%\n")
    for r, j in hits:
        mark = "OK  " if j else "MISS"
        extra = f"-> score {j.get('score')} [{j.get('source')}]" if j else ""
        print(f"{mark} {r['run']}  {r['company']} - {r['title']} {extra}")


if __name__ == "__main__":
    sys.exit(main())
