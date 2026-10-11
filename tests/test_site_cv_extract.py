"""JB-79 (#195): CV keyword extraction must not build n-grams across separators,
must prefer canonical skills from data/skills.json, and must drop the person's name."""
import json
import os
import re
import shutil
import subprocess

import pytest

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")
JANE = ("Jane Doe\nSenior Firmware Engineer\nLondon, Ontario\n"
        "Skills: Altium, ARM Cortex-M, FreeRTOS, PCB design, embedded C, Python, SPI, I2C, board bring-up")
DB = ["altium", "cortex-m", "freertos", "pcb design", "embedded c", "python", "spi", "i2c",
      "board bring-up", "bring-up", "c", "go", "es", "c#"]


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    html = open(INDEX, encoding="utf-8").read()
    m = re.search(r"/\* EXTRACT-PURE-BEGIN \*/(.*?)/\* EXTRACT-PURE-END \*/", html, re.S)
    assert m, "EXTRACT-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True,
                         text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_jane_cv_gets_real_skills_not_cross_comma_bigrams():
    r = _node(f"console.log(JSON.stringify(extractSkills({json.dumps(JANE)},{json.dumps(DB)},['Jane','Doe'])))")
    for want in ["altium", "cortex-m", "freertos", "pcb design", "embedded c", "python", "spi", "i2c", "board bring-up"]:
        assert want in r, (want, r)
    for bad in ["jane doe", "ontario altium", "london ontario", "altium arm", "bring-up"]:
        assert bad not in r, (bad, r)


def test_no_db_fallback_keeps_frequent_terms_within_chunks():
    text = "Altium, Altium designer\nPython, Python scripting\nTesting"
    r = _node(f"console.log(JSON.stringify(extractSkills({json.dumps(text)},[],[])))")
    assert "altium" in r and "python" in r
    assert "altium python" not in r and "designer python" not in r


def test_short_alpha_db_forms_skipped_but_symbol_forms_kept():
    r = _node('console.log(JSON.stringify(extractSkills("I go to the es office. Built tools in C# and Go.",["go","es","c#"],[])))')
    assert "c#" in r and "go" not in r and "es" not in r


def test_title_regex_does_not_span_line_breaks():
    html = open(INDEX, encoding="utf-8").read()
    assert r'new RegExp("([a-z]+[ \\t])?([a-z]+[ \\t])?("+ROLE_WORDS.join("|")+")","g")' in html
