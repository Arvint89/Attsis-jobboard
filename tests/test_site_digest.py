"""JB-92 digest v0 (ADR-009 D6): browser-only "new since your last visit".

DIGEST-PURE runs in node: id hashing, first-visit baseline, fresh detection, cap,
visit bookkeeping. Static checks cover the wiring (#new view, card chip, re-check).
"""
import json, os, re, shutil, subprocess
import pytest

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    return open(INDEX, encoding="utf-8").read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* DIGEST-PURE-BEGIN \*/(.*?)/\* DIGEST-PURE-END \*/", _html(), re.S)
    assert m, "DIGEST-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_ids_are_short_stable_and_distinct():
    r = _node("console.log(JSON.stringify([digestId('https://a/1'),digestId('https://a/1'),digestId('https://a/2')]))")
    assert r[0] == r[1] and r[0] != r[2] and len(r[0]) <= 8


def test_first_visit_marks_nothing_new():
    r = _node("console.log(JSON.stringify(digestStep(null,['a','b'],'T1',100)))")
    assert r["fresh"] == [] and sorted(r["state"]["seen"]) == ["a", "b"]


def test_later_visit_flags_only_unseen_ids():
    r = _node("const s=digestStep(null,['a','b'],'T1',100).state;"
              "console.log(JSON.stringify(digestStep(s,['b','c','d'],'T2',100)))")
    assert r["fresh"] == ["c", "d"]
    assert set(r["state"]["seen"]) == {"a", "b", "c", "d"}


def test_seen_is_capped_keeping_newest():
    r = _node("let s=digestStep(null,['x0'],'T',5).state;"
              "s=digestStep(s,['x1','x2','x3','x4','x5','x6'],'T',5).state;console.log(JSON.stringify(s.seen))")
    assert r == ["x2", "x3", "x4", "x5", "x6"]


def test_visit_rolls_last_to_prev():
    r = _node("let s=digestStep(null,[],'T',5).state; s=digestVisit(s,'2026-10-18T10:00:00Z');"
              "s=digestVisit(s,'2026-10-19T10:00:00Z'); console.log(JSON.stringify(s))")
    assert r["prev_visit"] == "2026-10-18T10:00:00Z" and r["last_visit"] == "2026-10-19T10:00:00Z"


def test_corrupt_state_is_treated_as_first_visit():
    r = _node("console.log(JSON.stringify(digestStep({seen:'oops'},['a'],'T',5)))")
    assert r["fresh"] == [] and r["state"]["seen"] == ["a"]


def test_wiring():
    h = _html()
    assert "jobboard_seen" in h and "sessionStorage" in h
    assert "location.hash==='#new'" in h or "location.hash===\"#new\"" in h
    assert "hashchange" in h
    assert 'class="chip new"' in h
    assert 'id="newChip"' in h and 'id="freshBar"' in h
    # listFilter applies the new-only view so the list and the map agree
    lf = h[h.index("function listFilter()"):h.index("function renderBoard()")]
    assert "DIGEST_ONLY" in lf
    # periodic re-check: same-origin data only (CSP connect-src 'self')
    assert "DIGEST_RECHECK_MS=30*60*1000" in h
    ui = h[h.index("/* DIGEST-UI-BEGIN */"):h.index("/* DIGEST-UI-END */")]
    assert "fetch('./data/jobs_matches.json" in ui and "http" not in ui.replace("https://", "")
