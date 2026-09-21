import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import ats, ats_detect

CASES = [
    ("https://ztr.bamboohr.com/careers", {"platform": "bamboohr", "slug": "ztr", "supported": True}),
    ("https://boards.greenhouse.io/tenstorrent", {"platform": "greenhouse", "slug": "tenstorrent", "supported": True}),
    ("https://job-boards.greenhouse.io/geotab/jobs/123", {"platform": "greenhouse", "slug": "geotab", "supported": True}),
    ("https://jobs.lever.co/acme/abc-123", {"platform": "lever", "slug": "acme", "supported": True}),
    ("https://jobs.ashbyhq.com/miovision", {"platform": "ashby", "slug": "miovision", "supported": True}),
    ("https://jobs.smartrecruiters.com/Acme1/744", {"platform": "smartrecruiters", "slug": "Acme1", "supported": True}),
    ("https://acme.recruitee.com/o/eng", {"platform": "recruitee", "slug": "acme", "supported": True}),
    ("https://apply.workable.com/acme/j/AB12/", {"platform": "workable", "slug": "acme", "supported": True}),
    ("https://ats.rippling.com/canada-rocket-company/jobs", {"platform": "rippling", "slug": "canada-rocket-company", "supported": True}),
    ("https://nokia.wd3.myworkdayjobs.com/en-US/careers", {"platform": "workday", "slug": "nokia", "tenant": "nokia", "site": "careers", "dc": "wd3", "supported": True}),
    ("https://acme.wd1.myworkdayjobs.com/External", {"platform": "workday", "slug": "acme", "tenant": "acme", "site": "External", "dc": "wd1", "supported": True}),
    ("https://vitalbio.na.teamtailor.com/jobs/671261", {"platform": "teamtailor", "slug": "vitalbio", "supported": False}),
    ("https://generaldynamics-ca-careers.ttcportals.com/search/jobs", {"platform": "ttcportals", "slug": "generaldynamics-ca-careers", "supported": False}),
    ("https://recruiting.ultipro.ca/STA5000/JobBoard", {"platform": "ultipro", "slug": "STA5000", "supported": False}),
    ("https://wolfadvancedtechnology.scouterecruit.net/jobs", {"platform": "scouterecruit", "slug": "wolfadvancedtechnology", "supported": False}),
    ("https://kepler.space/careers", None),
    ("", None),
]

@pytest.mark.parametrize("url,expected", CASES)
def test_detect_ats(url, expected):
    assert ats_detect.detect_ats(url) == expected

def test_supported_matches_fetchers():
    assert ats_detect.SUPPORTED == set(ats.FETCHERS)

def test_html_prefers_supported_ats():
    html = ('<a href="https://acme.na.teamtailor.com/jobs">old</a>'
            '<iframe src="https://boards.greenhouse.io/acme?embed=1"></iframe>')
    assert ats_detect.detect_ats_in_html(html) == {"platform": "greenhouse", "slug": "acme", "supported": True}

def test_html_falls_back_to_unsupported_then_none():
    assert ats_detect.detect_ats_in_html('<a href="https://x.teamtailor.com/jobs">j</a>')["platform"] == "teamtailor"
    assert ats_detect.detect_ats_in_html("<p>no jobs here</p>") is None
