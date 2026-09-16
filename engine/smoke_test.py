"""smoke_test.py -- runtime gate (per PD rules). Answers: does the product
actually work right now on this machine? Not unit correctness -- end-to-end.
Exit 0 = all green. Run after every build/change before calling a phase done."""
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

# 3 demo build produces valid site data
r = subprocess.run([sys.executable, os.path.join(HERE,"build_board.py"), "--demo"], capture_output=True, text=True)
check("demo build exits 0", r.returncode==0)
jobs_path = os.path.join(ROOT,"site","data","jobs.json")
check("jobs.json exists", os.path.exists(jobs_path))
d = json.load(open(jobs_path, encoding="utf-8"))
check("jobs.json has matches", d["counts"]["matches"]>=1)
check("standalone board emitted", os.path.exists(os.path.join(ROOT,"site","board_standalone.html")))

# 4 the site page references the data file
idx = open(os.path.join(ROOT,"site","index.html"), encoding="utf-8").read()
check("index.html wired to data/jobs.json", "data/jobs.json" in idx)

print(f"\n{'ALL SMOKE CHECKS PASSED' if ok else 'SMOKE TEST FAILED'} ({sum(c for _,c in checks)}/{len(checks)})")
sys.exit(0 if ok else 1)
