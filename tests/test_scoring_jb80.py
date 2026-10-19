"""JB-80 (#197) option C: skill bump weights CV hits x1 and DB-only hits x0.25.

The relevance gate is unchanged (DB terms still let a job onto the board), so recall
holds; only the ranking bump becomes CV-driven. The golden set (test_scoring_golden.py)
guards that BT's known-good roles still reach 7+. The browser mirrors the formula via
the SKILLBUMP-PURE block in site/index.html; parity is checked here with node.
"""
import json, os, re, shutil, subprocess, sys
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import jobfilter as jf

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")
TODAY = date.today().isoformat()


def job(title, desc):
    return {"title": title, "location": "Vancouver, BC", "description": desc, "posted": TODAY}


@pytest.mark.parametrize("cv,db,bump", [
    (0, 0, 0), (1, 0, 1), (0, 3, 0), (0, 4, 1), (3, 4, 2), (4, 0, 2),
    (0, 16, 2), (7, 3, 2), (7, 4, 3), (8, 0, 3), (0, 31, 2), (0, 32, 3),
])
def test_skill_bump_weights(cv, db, bump):
    assert jf.skill_bump(cv, db) == bump


def test_cv_skills_are_the_profile_list_not_the_db():
    assert "schematic" in jf.CV_SKILLS
    assert len(jf.CV_SKILLS) < len(jf.SKILL_CONFIRMERS)   # the DB widened the confirmer pool


def test_cv_hits_outrank_db_only_hits():
    cv_body = ("Schematic capture, PCB layout in Altium, firmware in embedded C on STM32, "
               "I2C and SPI drivers, board bring-up with an oscilloscope. " * 3)
    db_only = [s for s in jf.SKILL_CONFIRMERS if s not in jf.CV_SKILLS and s.isalpha() and len(s) > 5][:10]
    db_body = ("Work with " + ", ".join(db_only) + ". ") * 3
    a = jf.classify(job("Hardware Engineer", cv_body))
    b = jf.classify(job("Hardware Engineer", db_body))
    assert a["verdict"] != "excluded" and b["verdict"] != "excluded"
    assert a["score"] > b["score"], (a["reasons"], b["reasons"])


def test_reason_names_cv_share_and_explanation_reads_it():
    r = jf.classify(job("Hardware Engineer", "Schematic, PCB layout, firmware, embedded C, STM32. " * 5))
    sk = [x for x in r["reasons"] if x.startswith("skills x")]
    assert sk and re.match(r"skills x\d+ \(\d+ from CV\)$", sk[0]), r["reasons"]
    assert "from your CV" in jf.score_explanation(r)


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    h = open(INDEX, encoding="utf-8").read()
    m = re.search(r"/\* SKILLBUMP-PURE-BEGIN \*/(.*?)/\* SKILLBUMP-PURE-END \*/", h, re.S)
    assert m, "SKILLBUMP-PURE block missing from index.html"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_browser_skill_bump_matches_python():
    grid = [(c, d) for c in range(0, 12) for d in range(0, 40, 3)]
    got = json.loads(_node(f"console.log(JSON.stringify({json.dumps(grid)}.map(([c,d])=>skillBump(c,d))))"))
    assert got == [jf.skill_bump(c, d) for c, d in grid]


def test_browser_scorejob_uses_weighted_bump():
    h = open(INDEX, encoding="utf-8").read()
    body = h[h.index("function scoreJob("):h.index("/* ---------- JD capture")]
    assert "skillBump(" in body
    assert "conf.length>=8?3" not in body
