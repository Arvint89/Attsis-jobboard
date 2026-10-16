"""sweep.yml runs from main's workflow file but checks out `production` code. A step that calls a
script which exists only on main fails every sweep until a release ships it (it did: #206 ->
4 failed sweeps, 2026-10-12..15, live site stuck on 2026-10-09 data)."""
import os
import re

WF = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "sweep.yml")


def _steps():
    text = open(WF, encoding="utf-8").read()
    # split the steps list on "      - " at step indentation
    return re.split(r"\n      - ", text.split("steps:", 1)[1])


def test_tools_steps_are_guarded_by_hashfiles():
    for step in _steps():
        m = re.search(r"python (tools/\S+\.py)", step)
        if m:
            assert f"hashFiles('{m.group(1)}')" in step, f"unguarded step calls {m.group(1)}:\n{step}"


def test_checkout_is_production():
    assert "ref: production" in open(WF, encoding="utf-8").read()
