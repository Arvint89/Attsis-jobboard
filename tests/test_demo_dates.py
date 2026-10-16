"""Fixture dates must not age out: the demo build shifts them so the newest posting is yesterday."""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import build_board  # noqa: E402

HERE = os.path.join(os.path.dirname(__file__), "..", "engine")


def test_age_fixtures_keeps_relative_ages():
    jobs = [{"posted": "2026-09-10"}, {"posted": "2026-09-01"}, {"posted": "2026-06-01"}, {"posted": None}]
    out = build_board._age_fixtures(jobs, today=date(2027, 3, 1))
    assert out[0]["posted"] == "2027-02-28"                 # newest -> yesterday
    assert out[1]["posted"] == "2027-02-19"                 # 9 days older, still 9 days older
    assert out[2]["posted"] == "2026-11-19"                 # the deliberately stale one stays stale
    assert out[3]["posted"] is None


def test_demo_gather_is_fresh_today():
    jobs, _, _ = build_board.gather(demo=True)
    newest = max(j["posted"][:10] for j in jobs if j.get("posted"))
    assert newest == (date.today() - timedelta(days=1)).isoformat()
