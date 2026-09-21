"""JB-40: Rippling location, Workday keyword search past the 220 cap, 'engineering' titles."""
import os, sys
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import ats
import jobfilter as jf


class _R:
    def __init__(self, data): self._d = data
    def json(self): return self._d


def test_rippling_reads_worklocation_label(monkeypatch):
    # real shape, api.rippling.com/.../board/canada-rocket-company/jobs (2026-09-21)
    data = [{"uuid": "6fc9", "name": "Senior Electrical Design Engineer",
             "department": {"id": "Eng", "label": "Eng"},
             "url": "https://ats.rippling.com/canada-rocket-company/jobs/6fc9",
             "workLocation": {"label": "London, Canada", "id": "London, Canada"}}]
    monkeypatch.setattr(ats, "_get", lambda *a, **k: _R(data))
    jobs = ats.fetch_rippling("Canada Rocket Company", "canada-rocket-company")
    assert jobs[0]["location"] == "London, Canada"


def test_rippling_location_list_and_missing(monkeypatch):
    data = [{"uuid": "a", "name": "A", "workLocations": [{"label": "London, Canada"}, {"label": "Toronto, Canada"}]},
            {"uuid": "b", "name": "B"}]
    monkeypatch.setattr(ats, "_get", lambda *a, **k: _R(data))
    locs = [j["location"] for j in ats.fetch_rippling("X", "x")]
    assert locs[0] == "London, Canada; Toronto, Canada" and locs[1] in ("", "n/a")


def _fake_workday(postings_by_query):
    calls = []
    def fake(url, method="GET", **kw):
        body = kw.get("json") or {}
        q, off = body.get("searchText", ""), body.get("offset", 0)
        calls.append((q, off))
        allp = postings_by_query.get(q, [])
        return _R({"total": len(allp), "jobPostings": allp[off:off + 20]})
    return fake, calls


def test_workday_searches_by_keyword_and_dedupes(monkeypatch):
    p = lambda i, t: {"title": t, "externalPath": f"/job/{i}", "locationsText": "Mississauga, Ontario, Canada", "postedOn": "Posted Today"}
    fake, calls = _fake_workday({
        "electrical": [p(1, "Electrical Engineering Advanced"), p(2, "Electrical Designer")],
        "hardware": [p(2, "Electrical Designer"), p(3, "Hardware Engineer")],
    })
    monkeypatch.setattr(ats, "_get", fake)
    jobs = ats.fetch_workday("Zebra", "zebra", tenant="zebra", site="Zebra_careers", dc="wd501",
                             queries=["electrical", "hardware"])
    assert sorted(j["title"] for j in jobs) == ["Electrical Designer", "Electrical Engineering Advanced", "Hardware Engineer"]
    assert {q for q, _ in calls} == {"electrical", "hardware"}


def test_workday_pages_past_220_within_a_keyword(monkeypatch):
    posts = [{"title": f"Hardware Engineer {i}", "externalPath": f"/job/{i}", "locationsText": "Toronto"} for i in range(250)]
    fake, calls = _fake_workday({"hardware": posts})
    monkeypatch.setattr(ats, "_get", fake)
    jobs = ats.fetch_workday("Big", "big", queries=["hardware"])
    assert len(jobs) == 250


def test_engineering_title_variant_matches():
    r = jf.classify({"title": "Electrical Engineering Advanced", "location": "Mississauga, ON",
                     "description": "", "posted": date.today().isoformat()})
    assert r["verdict"] != "excluded" and any(x.startswith("title match") for x in r["reasons"])
