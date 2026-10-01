"""Tests for the VERSION file (JB-27).

The auto-tag Action reads VERSION on every push to main. If it's absent,
empty, or malformed, tags stop landing silently -- exactly the drift
JB-27 exists to prevent. These tests keep VERSION honest at CI time.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_PATH = os.path.join(ROOT, "VERSION")


def test_version_file_exists():
    assert os.path.exists(VERSION_PATH), f"VERSION file missing at {VERSION_PATH}"


def test_version_is_major_minor_bugs():
    with open(VERSION_PATH, encoding="utf-8") as f:
        v = f.read().strip()
    assert re.match(r"^\d+\.\d+\.\d+$", v), (
        f"VERSION must be MAJOR.MINOR.BUGS (e.g. 0.11.0); got {v!r}"
    )


def test_version_has_no_v_prefix():
    with open(VERSION_PATH, encoding="utf-8") as f:
        v = f.read().strip()
    # The Action synthesizes 'v<VERSION>' -- a leading v here would produce vv0.11.0.
    assert not v.startswith("v"), "VERSION must not include the 'v' prefix"
