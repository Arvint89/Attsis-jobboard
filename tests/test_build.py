"""Tests for build_board orchestration helpers. JB-20: per-company cap."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import build_board as b


def test_cap_limits_big_company_keeps_highest_scores():
    rows = [{"company": "Big", "score": s} for s in range(12)] + [{"company": "Small", "score": 5}]
    kept, dropped = b.cap_per_company(rows, n=8)
    big = [r for r in kept if r["company"] == "Big"]
    assert len(big) == 8 and dropped == 4            # 12 -> 8, 4 trimmed
    assert min(r["score"] for r in big) == 4         # kept the top-8 by score (11..4)
    assert any(r["company"] == "Small" for r in kept)  # small company untouched


def test_cap_noop_when_under_limit():
    rows = [{"company": "A", "score": 7}, {"company": "A", "score": 6}, {"company": "B", "score": 9}]
    kept, dropped = b.cap_per_company(rows, n=8)
    assert len(kept) == 3 and dropped == 0


def test_cap_empty():
    kept, dropped = b.cap_per_company([], n=8)
    assert kept == [] and dropped == 0
