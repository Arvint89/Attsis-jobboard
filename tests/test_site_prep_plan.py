"""JB-78 prep plan from your gaps (#191). Deterministic, no LLM."""
import os

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_prep_has_role_picker_and_plan():
    h = _html()
    assert 'id="prepRole"' in h and 'id="prepPlan"' in h
    assert "function renderPrep()" in h and "if(name==='prep') renderPrep();" in h


def test_plan_wording_is_honest_about_source_text():
    h = _html()
    assert "Expect a question on it." in h
    assert "characters of the description we have" in h


def test_templates_kept():
    h = _html()
    for t in ("Company brief template", "Technical questions", "Behavioural questions", "Salary + negotiation"):
        assert t in h, t


import json, re, shutil, subprocess
import pytest


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* GAP-PURE-BEGIN \*/(.*?)/\* GAP-PURE-END \*/", _html(), re.S)
    assert m, "GAP-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_gap_terms_use_canonical_skills_not_jd_bigrams():
    # ✅ real server tokens for "Staff, Firmware Engineer" (Tenstorrent), live jobs.json 2026-10-09
    jd = ["board bring-up", "bring-up", "c", "c++", "c/c++", "continuous integration", "ear",
          "embedded systems", "firmware", "foundation", "rtos", "v"]
    cv = ["altium", "freertos", "pcb design", "embedded c", "python", "board bring-up", "firmware"]
    r = _node(f"console.log(JSON.stringify(gapTerms({json.dumps(jd)},{json.dumps(cv)},'')))")
    assert "board bring-up" in r["have"] and "firmware" in r["have"] and "rtos" in r["have"]  # freertos covers rtos
    assert set(r["missing"]) == {"c/c++", "continuous integration", "embedded systems"}
    for noise in ("ear", "foundation", "v", "c", "bring-up"):
        assert noise not in r["missing"]
