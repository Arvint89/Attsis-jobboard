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


# real captured LEDC card markup (londontechjobs.ca, 2026-09-17)
LEDC_HTML = '''
<div class="gm-card"> <a href="job.aspx?jid=839ce3f2-013f-4822-a795-f0d92dd8f70b" class="gm-card-link"></a>
  <div class="gm-card-text"> <h4 class="gm-card-title"> Controls Developer </h4>
  <h3 class="gm-card-subtitle">ZTR Control Systems</h3>
  <i class="fa fa-map-marker"></i>London, ON </div>
  <div class="gm-card-timestamp"><span><i class="fa fa-clock-o"></i>Sep 14, 2026 </span></div>
</div>
<div class="gm-card"> <a href="job.aspx?jid=0dee9f21-9d3b-422f-b0f8-ea3cbd933ec2"></a>
  <div class="gm-card-text"> <h4 class="gm-card-title">Embedded Engineer</h4>
  <h3 class="gm-card-subtitle">StarTech.com</h3>
  <i class="fa fa-map-marker"></i>London, ON </div></div>
'''


def test_ledc_parses_cards():
    rows = sources.parse_ledc_cards(LEDC_HTML, "https://londontechjobs.ca", "LEDC Tech")
    assert len(rows) == 2
    r = rows[0]
    assert r["title"] == "Controls Developer"
    assert r["company"] == "ZTR Control Systems"
    assert r["location"] == "London, ON"
    assert r["url"] == "https://londontechjobs.ca/job.aspx?jid=839ce3f2-013f-4822-a795-f0d92dd8f70b"
    assert r["posted"] == "Sep 14, 2026"
    assert r["source"] == "ledc:LEDC Tech"


def test_ledc_fetch_is_failure_safe(monkeypatch):
    def boom(url):
        raise RuntimeError("dns fail")
    monkeypatch.setattr(sources, "_get_text", boom)
    assert sources.fetch_ledc("LEDC Tech", "https://londontechjobs.ca") == []


def test_getro_one_failing_query_keeps_the_others(monkeypatch):
    def fake(url, body):
        if body["query"] == "bad":
            raise RuntimeError("429")
        return _fake([dict(ONE, id=body["query"])])
    monkeypatch.setattr(sources, "_post", fake)
    jobs = sources.fetch_getro("Communitech", 8936, ["firmware", "bad", "altium"])
    assert len(jobs) == 2


def _paged(total, cap):
    """Fake Getro: `total` jobs, server returns at most `cap` per page whatever is asked."""
    calls = []
    def fake(url, body):
        calls.append(body["page"])
        start = body["page"] * cap
        ids = range(start, min(start + cap, total))
        return {"results": {"count": total, "jobs": [dict(ONE, id=f"j{i}") for i in ids]}}
    return fake, calls


def test_getro_paginates_until_total_reached(monkeypatch):
    fake, calls = _paged(total=5, cap=2)
    monkeypatch.setattr(sources, "_post", fake)
    jobs = sources.fetch_getro("Communitech", 628, ["firmware"], per_page=2)
    assert len(jobs) == 5 and calls == [0, 1, 2]


def test_getro_server_page_cap_below_request_still_paginates(monkeypatch):
    # JB-39: we ask for 100 per page, Getro returns 20 -> must NOT treat page 0 as the last page
    fake, calls = _paged(total=45, cap=20)
    monkeypatch.setattr(sources, "_post", fake)
    jobs = sources.fetch_getro("Communitech", 628, ["firmware"], per_page=100)
    assert len(jobs) == 45 and calls == [0, 1, 2]


def test_getro_stops_at_max_pages(monkeypatch):
    fake, calls = _paged(total=1000, cap=2)
    monkeypatch.setattr(sources, "_post", fake)
    sources.fetch_getro("Communitech", 8936, ["firmware"], per_page=2, max_pages=3)
    assert calls == [0, 1, 2]
