"""JB-84 parallel boot: all downloads start together; first paint doesn't wait on skills."""
import os
import re

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_matches_start_first_and_alone():
    h = _html()
    assert "const _matchesP=" in h
    assert "_matchesP.catch(()=>{});" in h  # no unhandled-rejection console error
    # below-threshold roles are fetched only after first paint (measured: parallel was slower)
    i = h.index("_matchesP\n  .then(d=>{")
    block = h[i:i + 400]
    assert block.index("init(d);") < block.index("jobs_below.json")


def test_skills_json_is_cacheable():
    assert "fetch('./data/skills.json')" in _html()
    assert "skills.json?_=" not in _html()


def test_first_paint_does_not_wait_for_skills():
    h = _html()
    i = h.index("_matchesP\n  .then(d=>{")
    block = h[i:i + 200]
    assert block.index("init(d);") < block.index("applySkillsWhenReady();")


def test_standalone_rewrite_target_kept():
    # engine/build_board.py replaces "fetch('./data/jobs.json ... });" with bootWithSkills(window.__EMBED__)
    h = _html()
    assert "function bootWithSkills(d)" in h
    assert re.search(r"fetch\('\./data/jobs\.json.*?\}\);", h, re.S)
