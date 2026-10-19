"""JB-95 (#254): mechanical + mechatronics coverage.

The skills DB drives both CV extraction in the browser (extractSkills over DB_SKILLS) and
JD matching, so a discipline missing from data/skills.json is invisible end to end.
"""
import json, os, re, shutil, subprocess, sys
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import jobfilter as jf
import sources

ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX = os.path.join(ROOT, "site", "index.html")
TODAY = date.today().isoformat()

MECH = ["solidworks", "gd&t", "catia", "creo", "ansys", "finite element analysis", "sheet metal",
        "injection molding", "tolerance analysis", "plc", "ros", "simulink", "servo motors",
        "motion control", "pneumatics", "robotics", "dfma", "autocad", "fusion 360", "machine design"]


def _forms():
    db = json.load(open(os.path.join(ROOT, "data", "skills.json"), encoding="utf-8"))
    return [f.lower() for r in db["skills"] for f in [r["canonical"]] + list(r.get("aliases") or [])]


def test_live_db_has_mechanical_skills():
    forms = set(_forms())
    missing = [s for s in MECH if s not in forms]
    assert not missing, missing


def test_no_bare_cad_form():
    # "CAD $95,000" is in many Canadian salary lines; a bare "cad" skill would match them all
    assert "cad" not in _forms()


def test_mechanical_rows_add_no_duplicate_forms():
    # (the DB has a few older duplicates, e.g. "can bus"; harmless, the scorer de-dupes)
    db = json.load(open(os.path.join(ROOT, "data", "skills.json"), encoding="utf-8"))
    rows = lambda pred: [f.lower() for r in db["skills"] if pred(r) for f in [r["canonical"]] + list(r.get("aliases") or [])]
    mech = rows(lambda r: r.get("category") == "mechanical")
    other = set(rows(lambda r: r.get("category") != "mechanical"))
    assert mech and len(mech) == len(set(mech)) and not (set(mech) & other), sorted(set(mech) & other)


def test_getro_queries_cover_mechanical():
    for q in ("mechanical", "mechatronics", "robotics"):
        assert q in sources.DEFAULT_QUERIES


def _node_extract(text):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    h = open(INDEX, encoding="utf-8").read()
    m = re.search(r"/\* EXTRACT-PURE-BEGIN \*/(.*?)/\* EXTRACT-PURE-END \*/", h, re.S)
    js = m.group(1) + f"\nconsole.log(JSON.stringify(extractSkills({json.dumps(text)},{json.dumps(_forms())},['Sam','Lee'])))"
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_mechanical_cv_skills_are_extracted():
    cv = ("Sam Lee\nMechanical Engineer\nSkills: SolidWorks, GD&T, ANSYS, finite element analysis, "
          "sheet metal design, injection molding, tolerance analysis, DFMA, PLC programming, ROS, Simulink")
    got = set(_node_extract(cv))
    # the extractor keeps the longest form it matched (JB-79), e.g. "plc programming" for PLC
    for forms in (("solidworks",), ("gd&t",), ("ansys",), ("injection molding",), ("tolerance analysis",),
                  ("plc", "plc programming"), ("ros",), ("simulink",), ("dfma",)):
        assert got & set(forms), (forms, sorted(got))


def _job(title, desc, loc="Toronto, ON"):
    return {"title": title, "description": desc, "location": loc, "posted": TODAY}


MECH_JD = ("Design mechanical assemblies in SolidWorks with GD&T drawings and tolerance analysis. "
           "Sheet metal and injection molding parts, DFMA with suppliers, finite element analysis in ANSYS, "
           "machine design, pneumatics and servo motors for motion control. ") * 2


def test_mechanical_cv_on_mechanical_jd_scores_7_plus(monkeypatch):
    # a mechanical profile = its own skills count x1 (JB-80)
    monkeypatch.setattr(jf, "CV_SKILLS", frozenset(MECH))
    for t in ("Mechanical Engineer", "Mechanical Design Engineer", "Mechatronics Engineer"):
        r = jf.classify(_job(t, MECH_JD))
        assert r["score"] >= 7, (t, r["score"], r["reasons"])


def test_hardware_profile_barely_moves_on_mechanical_jd():
    # BT's base profile: mechanical skills are DB-only (x0.25), so a mechanical JD stays below 7
    r = jf.classify(_job("Mechanical Engineer", MECH_JD))
    assert r["verdict"] != "excluded" and r["score"] < 7, r


def test_technicians_still_excluded_and_hvac_still_low():
    assert jf.classify(_job("Mechanical Technician", "Assemble prototypes, CNC machining. " * 5))["verdict"] == "excluded"
    r = jf.classify(_job("HVAC Mechanical Engineer", "HVAC design, building services, ductwork, AutoCAD drawings. " * 4))
    assert r["verdict"] == "excluded" or r["score"] < 7, r


def test_landing_copy_names_mechanical():
    h = open(INDEX, encoding="utf-8").read().lower()
    assert "mechanical" in h and "mechatronics" in h
