"""JB-76 tracker v2 (#189). See docs/design/DESIGN_jb76_tracker.md."""
import json
import os
import re
import shutil
import subprocess

import pytest

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")
DAY = 86400000
NOW = 1760184000000  # fixed clock


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* TRACKER-PURE-BEGIN \*/(.*?)/\* TRACKER-PURE-END \*/", _html(), re.S)
    assert m, "TRACKER-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True,
                         text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _items():
    return [
        {"key": "a", "stage": "saved", "added": NOW - 10 * DAY, "moved": NOW - 10 * DAY},
        {"key": "b", "stage": "saved", "added": NOW - 2 * DAY, "moved": NOW - 2 * DAY},
        {"key": "c", "stage": "applied", "added": NOW - 20 * DAY, "moved": NOW - 8 * DAY},
        {"key": "d", "stage": "applied", "added": NOW - 20 * DAY, "moved": NOW - 9 * DAY, "snooze": NOW + DAY},
        {"key": "e", "stage": "interviewing", "added": NOW - 30 * DAY, "moved": NOW - 3 * DAY},
        {"key": "f", "stage": "closed", "added": NOW - 30 * DAY, "moved": NOW - 1 * DAY},
    ]


def test_tracker_stats():
    r = _node(f"console.log(JSON.stringify(trackerStats({json.dumps(_items())})))")
    assert r["total"] == 6 and r["active"] == 3 and r["interviews"] == 1
    assert abs(r["rate"] - 0.25) < 1e-9  # 1 / (2 applied + 1 interviewing + 0 offer + 1 closed)


def test_tracker_stats_empty_rate_is_null():
    assert _node("console.log(JSON.stringify(trackerStats([])))")["rate"] is None


def test_tracker_nudges_rules_and_snooze():
    r = _node(f"console.log(JSON.stringify(trackerNudges({json.dumps(_items())},{NOW})))")
    # JB-11: "e" moved to interviewing 3 days ago and hasn't sent a thank-you -> a thank-you nudge
    assert [(x["key"], x["kind"], x["days"]) for x in r] == [("a", "saved", 10), ("c", "applied", 8), ("e", "thankyou", 3)]


def test_jb11_interview_nudges():
    items = [
        {"key": "t0", "stage": "interviewing", "added": NOW - 9 * DAY, "moved": NOW - 2 * 3600000},   # same day: too early
        {"key": "t1", "stage": "interviewing", "added": NOW - 9 * DAY, "moved": NOW - 1 * DAY},        # day 1: thank-you
        {"key": "t2", "stage": "interviewing", "added": NOW - 9 * DAY, "moved": NOW - 3 * DAY, "thanked": NOW - 2 * DAY},  # sent, <7d: quiet
        {"key": "t3", "stage": "interviewing", "added": NOW - 20 * DAY, "moved": NOW - 8 * DAY, "thanked": NOW - 7 * DAY},  # sent, 8d: heard back?
        {"key": "t4", "stage": "interviewing", "added": NOW - 9 * DAY, "moved": NOW - 2 * DAY, "snooze": NOW + DAY},  # snoozed
    ]
    r = _node(f"console.log(JSON.stringify(trackerNudges({json.dumps(items)},{NOW})))")
    assert [(x["key"], x["kind"]) for x in r] == [("t3", "interviewing"), ("t1", "thankyou")]


def test_jb11_markup_and_actions():
    h = _html()
    assert "Send a thank-you" in h and "Heard back after the interview?" in h
    assert "act==='thanked'" in h            # records t.thanked, keeps the stage


def test_tracker_markup():
    h = _html()
    for i in ("trkStats", "trkNudges", "trkTitle"):
        assert f'id="{i}"' in h, i
    assert "Needs your answer" in h
