"""JB-75 job card v2 (#188). See docs/design/DESIGN_jb75_job_card.md."""
import json
import os
import re
import shutil
import subprocess

import pytest

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* CARD-PURE-BEGIN \*/(.*?)/\* CARD-PURE-END \*/", _html(), re.S)
    assert m, "CARD-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True,
                         text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_rel_age():
    now = "Date.parse('2026-10-11T12:00:00Z')"
    r = _node(f"""const n={now};console.log(JSON.stringify([
      relAge('2026-10-11',n),relAge('2026-10-10',n),relAge('2026-10-07',n),relAge('2026-10-02',n),
      relAge('2026-09-20',n),relAge('2026-07-01',n),relAge('',n),relAge('garbage',n)]))""")
    assert r == ["today", "yesterday", "4 days ago", "1 week ago", "3 weeks ago", "3 months ago", "", ""]


def test_dist_label_and_check():
    r = _node("""console.log(JSON.stringify([
      distLabel({ring:0,km:3}),distLabel({ring:2,km:79.6}),distLabel({}),
      distCheck({km:30}),distCheck({km:80}),distCheck({km:180}),distCheck({km:600}),distCheck({})]))""")
    assert r == ["in your city", "80 km away", "", "Within 50 km", "Within 100 km", "Within 200 km", "", ""]


def test_sample_why_never_says_your_cv():
    exp = ("Score 10/10 (matches): the title names hardware developer, which maps to a role you target "
           "(+4-5 base); your CV lists 30 skills that appear in the description (+3: altium, analog...).")
    r = _node(f"console.log(JSON.stringify(sampleWhy({json.dumps(exp)})))")
    assert "your CV" not in r and "Score 10/10" not in r
    assert "sample profile" in r


def test_card_expands_in_place_and_gap_button_removed():
    h = _html()
    assert "Gap check</button>" not in h
    assert "OPEN_CARDS" in h and 'class="jobhead"' in h and "jobbody" in h


def test_tailor_button_still_gated():
    h = _html()
    assert re.search(r'<button[^>]*disabled[^>]*title="Coming soon[^"]*"[^>]*>\s*✎ Tailor CV', h)


def test_hero_says_sample_profile():
    assert "sample engineering profile" in _html()


@pytest.mark.parametrize("exp", [
    "Score 2/10 (below): title names physical design(-3), which your profile flags as a gap.",
    "Score 1/10 (below): none of your CV skills appear in the description text (-2).",
    "Score 2/10 (below): description reads as power/building-services (not your embedded profile).",
])
def test_sample_why_rewrites_every_your_phrase(exp):
    r = _node(f"console.log(JSON.stringify(sampleWhy({json.dumps(exp)})))")
    assert re.search(r"\byour\b", r, re.I) is None, r
    assert "(-" not in r


def test_index_has_no_control_characters():
    bad = [c for c in _html() if ord(c) < 32 and c not in "\n\r\t"]
    assert not bad, f"control characters in site/index.html: {sorted(set(map(ord, bad)))}"
