"""JB-52: enrichment of thin descriptions by hitting the ATS detail endpoint.

Workday's CXS search endpoint returns titles with no body; the per-job detail
endpoint carries `jobPostingInfo.jobDescription` (HTML). The enricher walks
a job list, finds thin-description Workday rows, and fills them in -- bounded
by a per-run fetch budget so a 500-job sweep doesn't N+1 the server.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import enrich


class FakeResp:
    def __init__(self, payload, status=200):
        self._p = payload
        self.status_code = status
    def json(self): return self._p
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_workday_detail_url_parses_from_job_url():
    url = "https://nokia.wd3.myworkdayjobs.com/careers/job/Kanata/PCB-Designer_R-12345"
    d = enrich._workday_detail_url(url)
    assert d == "https://nokia.wd3.myworkdayjobs.com/wday/cxs/nokia/careers/job/Kanata/PCB-Designer_R-12345"


def test_workday_detail_url_with_locale_segment():
    # JB-40 pattern: Workday sometimes injects a locale (en-US) ahead of site -- strip it
    url = "https://acme.wd1.myworkdayjobs.com/en-US/External/job/Toronto/Engineer_R-9"
    d = enrich._workday_detail_url(url)
    assert d == "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/External/job/Toronto/Engineer_R-9"


def test_workday_detail_url_returns_none_for_non_workday():
    assert enrich._workday_detail_url("https://greenhouse.io/boards/acme/jobs/1") is None
    assert enrich._workday_detail_url("") is None
    assert enrich._workday_detail_url(None) is None


def test_fetch_workday_description_strips_html():
    def fake_get(url):
        return FakeResp({"jobPostingInfo": {
            "jobDescription": "&lt;p&gt;Design PCBs. Verilog, Altium.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;5y exp&lt;/li&gt;&lt;/ul&gt;"
        }})
    desc = enrich.fetch_workday_description(
        "https://nokia.wd3.myworkdayjobs.com/careers/job/Kanata/PCB_R-1",
        _get=fake_get)
    assert "Verilog" in desc
    assert "Altium" in desc
    assert "<" not in desc


def test_fetch_workday_description_failure_returns_empty():
    def fake_get(url):
        raise RuntimeError("502 bad gateway")
    assert enrich.fetch_workday_description(
        "https://x.wd1.myworkdayjobs.com/x/job/y/z", _get=fake_get) == ""


def test_enrich_thin_descriptions_fills_only_workday_below_threshold():
    jobs = [
        # workday + thin -> should be enriched
        {"source": "workday", "description": "",
         "url": "https://nokia.wd3.myworkdayjobs.com/careers/job/K/PCB_R-1"},
        # workday + already fat -> skipped
        {"source": "workday", "description": "x" * 300,
         "url": "https://nokia.wd3.myworkdayjobs.com/careers/job/K/Senior_R-2"},
        # greenhouse + thin -> skipped (not our source this PR)
        {"source": "greenhouse", "description": "",
         "url": "https://boards.greenhouse.io/x/jobs/3"},
    ]
    calls = {"n": 0}
    def fake_get(url):
        calls["n"] += 1
        return FakeResp({"jobPostingInfo": {"jobDescription": "Real body about embedded firmware."}})
    stats = enrich.enrich_thin_descriptions(jobs, max_fetches=10, _get=fake_get)
    assert calls["n"] == 1   # only the thin workday row triggers a call
    assert jobs[0]["description"].startswith("Real body")
    assert jobs[1]["description"] == "x" * 300   # untouched
    assert jobs[2]["description"] == ""          # untouched (not a supported source)
    assert stats == {"enriched": 1, "attempted": 1, "failed": 0, "skipped_budget": 0}


def test_enrich_thin_descriptions_respects_budget_cap():
    jobs = [
        {"source": "workday", "description": "",
         "url": f"https://x.wd1.myworkdayjobs.com/s/job/C/R-{i}"} for i in range(5)
    ]
    def fake_get(url):
        return FakeResp({"jobPostingInfo": {"jobDescription": "Real body text here."}})
    stats = enrich.enrich_thin_descriptions(jobs, max_fetches=2, _get=fake_get)
    assert stats["enriched"] == 2
    assert stats["skipped_budget"] == 3
    filled = [j for j in jobs if j["description"].startswith("Real")]
    assert len(filled) == 2


def test_enrich_thin_descriptions_counts_failures_without_crashing():
    jobs = [{"source": "workday", "description": "",
             "url": "https://x.wd1.myworkdayjobs.com/s/job/c/R-1"}]
    def fake_get(url): raise RuntimeError("Cloudflare 1015")
    stats = enrich.enrich_thin_descriptions(jobs, max_fetches=5, _get=fake_get)
    assert stats == {"enriched": 0, "attempted": 1, "failed": 1, "skipped_budget": 0}
    assert jobs[0]["description"] == ""   # unchanged on failure


def test_enrich_thin_descriptions_handles_empty_list():
    stats = enrich.enrich_thin_descriptions([], max_fetches=10, _get=lambda u: FakeResp({}))
    assert stats == {"enriched": 0, "attempted": 0, "failed": 0, "skipped_budget": 0}
