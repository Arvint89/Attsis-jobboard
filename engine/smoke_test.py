"""smoke_test.py -- runtime gate (per PD rules). Answers: does the product
actually work right now on this machine? Not unit correctness -- end-to-end.
Exit 0 = all green. Run after every build/change before calling a phase done.

The --demo build writes to site/data/jobs.json + site/board_standalone.html.
That's the SAME file the local dev server serves and the CI publishes, so a
smoke run used to clobber whatever real data was there with 1-role demo output.
We save+restore those artefacts around the demo build so a smoke run is a
no-op on the served files."""
import json, os, subprocess, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
checks, ok = [], True

def check(name, cond):
    global ok
    checks.append((name, cond)); ok = ok and cond
    print(("PASS " if cond else "FAIL ") + name)


def _snapshot(path):
    """Return (path, existing_bytes_or_None). Called before the demo build."""
    return (path, open(path, "rb").read() if os.path.exists(path) else None)


def _restore(snap):
    path, data = snap
    if data is None:
        if os.path.exists(path):
            os.remove(path)
    else:
        with open(path, "wb") as f:
            f.write(data)

# 1 registry loads and is non-trivial
reg = json.load(open(os.path.join(HERE, "companies.json"), encoding="utf-8"))["companies"]
check("registry loads (>=20 companies)", len(reg) >= 20)
check("every company has name+ring+platform", all({"name","ring","platform"} <= set(c) for c in reg))

# 2 filter imports and classifies the three canonical cases
sys.path.insert(0, HERE)
import jobfilter as jf
m = jf.classify({"title":"Senior Electrical Engineer","description":"mixed-signal PCB, ISO 13485, IEC 60601, Altium, ARM Cortex-M","location":"London, ON","posted":"2026-09-15"})
check("strong role -> match (generic)", m["verdict"]=="match" and m["score"]>=7)
check("power role -> low score (not surfaced)", jf.classify({"title":"Electrical Engineer","description":"substation switchgear high-voltage grid","location":"London","posted":"2026-09-15"})["verdict"]!="match")

# 2b CV parsing produces a usable profile
import cv_parse
prof = cv_parse.build_profile("Electronics design engineer, 11+ years, Altium, PCB, "
    "schematic, embedded C, ARM Cortex-M, ISO 13485, IEC 60601.", "smoke.md")
check("cv_parse -> non-empty confirmers", len(prof["model"]["skill_confirmers"]) >= 8)
check("cv_parse detects years", prof["years_general"] == 11)

# 3 demo build produces valid site data.
# Snapshot the artefacts the --demo build overwrites so a smoke run is a no-op
# on the served files (was breaking local dev servers; see JB-smoke-outdir).
jobs_path = os.path.join(ROOT, "site", "data", "jobs.json")
std_path = os.path.join(ROOT, "site", "board_standalone.html")
snaps = [_snapshot(jobs_path), _snapshot(std_path)]
try:
    r = subprocess.run([sys.executable, os.path.join(HERE,"build_board.py"), "--demo"], capture_output=True, text=True)
    check("demo build exits 0", r.returncode==0)
    check("jobs.json exists", os.path.exists(jobs_path))
    _jobs_raw = open(jobs_path, encoding="utf-8").read()
    check("jobs.json is minified (JB-71)", "\n" not in _jobs_raw)
    d = json.loads(_jobs_raw)
    check("jobs.json has matches", d["counts"]["matches"]>=1)
    _row = (d["matches"] or [{}])[0]
    check("jobs.json rows have no server reasons/matched (JB-71)",
          "reasons" not in _row and "matched" not in _row)
    check("jobs.json rows have pre-matched tokens (JB-69)",
          "tokens" in _row and "titles" in _row["tokens"] and "skills" in _row["tokens"])
    # JB-70: sharded files for fast first paint
    _matches_path = os.path.join(ROOT, "site", "data", "jobs_matches.json")
    _below_path = os.path.join(ROOT, "site", "data", "jobs_below.json")
    check("jobs_matches.json emitted (JB-70)", os.path.exists(_matches_path))
    check("jobs_below.json emitted (JB-70)", os.path.exists(_below_path))
    _m = json.load(open(_matches_path, encoding="utf-8"))
    _b = json.load(open(_below_path, encoding="utf-8"))
    check("jobs_matches.json has matches + empty below (JB-70)",
          _m.get("counts", {}).get("matches", 0) >= 1 and _m.get("below") == [])
    check("jobs_below.json has only below (JB-70)",
          "below" in _b and set(_b.keys()) == {"below"})
    check("standalone board emitted", os.path.exists(std_path))
finally:
    for s in snaps: _restore(s)
    # JB-70: clean up the sharded demo artefacts too
    for _p in (os.path.join(ROOT, "site", "data", "jobs_matches.json"),
               os.path.join(ROOT, "site", "data", "jobs_below.json")):
        if os.path.exists(_p):
            try: os.remove(_p)
            except OSError: pass

# 4 the site page references the data file
idx = open(os.path.join(ROOT,"site","index.html"), encoding="utf-8").read()
check("index.html wired to data/jobs.json", "data/jobs.json" in idx)
check("index.html wired to data/jobs_matches.json (JB-70)", "data/jobs_matches.json" in idx)

# 5 JB-62: tenant example fixture ships + round-trips through the Python filter
import tenants
_tenant_path = os.path.join(ROOT, "site", "data", "tenants", "example.json")
check("JB-62 example tenant JSON exists", os.path.exists(_tenant_path))
if os.path.exists(_tenant_path):
    _t = json.load(open(_tenant_path, encoding="utf-8"))
    check("JB-62 example tenant is valid shape", tenants.is_valid_tenant(_t))
    _demo_jobs = [{"location":"London, ON, Canada"}, {"location":"Toronto, ON, Canada"}]
    _kept = tenants.filter_jobs(_demo_jobs, _t)
    check("JB-62 tenant filter keeps London / drops Toronto",
          len(_kept) == 1 and "London" in _kept[0]["location"])
check("index.html wired to ?tenant= query param (JB-62)", "?tenant=" in idx or "'tenant='" in idx or "tenant=" in idx)

print(f"\n{'ALL SMOKE CHECKS PASSED' if ok else 'SMOKE TEST FAILED'} ({sum(c for _,c in checks)}/{len(checks)})")
sys.exit(0 if ok else 1)
