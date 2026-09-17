"""JB-3: board-source fetchers (Getro adapter).

Getro returns jobs from MANY companies at once. These tests use a captured real
response shape (probed 2026-09-17 against Communitech/MaRS) so we test the
NORMALIZATION, not the network.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import sources


def _fake(jobs):
    return {"results": {"count": len(jobs), "jobs": jobs}}


ONE = {
    "title": "Embedded Firmware Engineer",
    "url": "https://ex.com/j/1",
    "organization": {"name": "Nicoya", "industry_tags": ["Medical Device"]},
    "searchable_locations": ["Kitchener, ON, Canada"],
    "location_details": [{"name": "Kitchener", "point": "POINT (-80.49 43.45)"}],
    "work_mode": "hybrid",
    "compensation_public": True,
    "compensation_amount_min_cents": 11000000,
    "compensation_amount_max_cents": 13000000,
    "compensation_currency": "CAD",
    "compensation_period": "year",
    "created_at": 1787210687,
    "skills": ["Altium", "STM32"],
    "seniority": "senior",
    "has_description": True,
    "id": 111,
}


def test_getro_normalizes_a_job(monkeypatch):
    monkeypatch.setattr(sources, "_post", lambda *a, **k: _fake([ONE]))
    jobs = sources.fetch_getro("Communitech", 8936, ["firmware"])
    assert len(jobs) == 1
    j = jobs[0]
    assert j["company"] == "Nicoya"
    assert j["title"] == "Embedded Firmware Engineer"
    assert j["arrangement"] == "hybrid"
    assert j["lat"] and 43 < j["lat"] < 44 and -81 < j["lng"] < -80
    assert "110,000" in j["salary"] and "CAD" in j["salary"]
    assert "altium" in j["description"].lower()          # skills → scorable text
    assert j["industry"] == "Medical Device"
    assert j["source"].startswith("getro:")


def test_getro_dedupes_across_queries(monkeypatch):
    # same job id returned by two different keyword queries → kept once
    monkeypatch.setattr(sources, "_post", lambda *a, **k: _fake([ONE]))
    jobs = sources.fetch_getro("Communitech", 8936, ["firmware", "altium"])
    assert len(jobs) == 1


def test_getro_private_salary_is_blank(monkeypatch):
    j2 = dict(ONE, id=222, compensation_public=False)
    monkeypatch.setattr(sources, "_post", lambda *a, **k: _fake([j2]))
    assert sources.fetch_getro("X", 1, ["q"])[0]["salary"] == ""


def test_getro_failure_is_safe(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(sources, "_post", boom)
    assert sources.fetch_getro("X", 1, ["q"]) == []      # never raises


def test_fetch_source_dispatches_and_is_safe():
    jobs, err = sources.fetch_source({"platform": "nope", "name": "Z"})
    assert jobs == [] and "no adapter" in err
