"""JB-88: a registry entry's careers_url must be the company's job BOARD, not one posting."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import ats  # noqa: E402
import ats_detect  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")

CASES = {   # real slugs from engine/companies.json
    "greenhouse": ({"platform": "greenhouse", "slug": "clutch"}, "https://job-boards.greenhouse.io/clutch"),
    "lever": ({"platform": "lever", "slug": "versapay"}, "https://jobs.lever.co/versapay"),
    "ashby": ({"platform": "ashby", "slug": "fellowai"}, "https://jobs.ashbyhq.com/fellowai"),
    "smartrecruiters": ({"platform": "smartrecruiters", "slug": "UniversityHealthNetwork"},
                        "https://jobs.smartrecruiters.com/UniversityHealthNetwork"),
    "recruitee": ({"platform": "recruitee", "slug": "acme"}, "https://acme.recruitee.com/"),
    "workable": ({"platform": "workable", "slug": "swtch-energy"}, "https://apply.workable.com/swtch-energy/"),
    "bamboohr": ({"platform": "bamboohr", "slug": "avidbots"}, "https://avidbots.bamboohr.com/careers"),
    "breezy": ({"platform": "breezy", "slug": "acme"}, "https://acme.breezy.hr/"),
    "jazzhr": ({"platform": "jazzhr", "slug": "myant"}, "https://myant.applytojob.com/apply"),
    "rippling": ({"platform": "rippling", "slug": "nesto"}, "https://ats.rippling.com/nesto/jobs"),
    "workday": ({"platform": "workday", "slug": "interac", "tenant": "interac", "site": "Interac", "dc": "wd3"},
                "https://interac.wd3.myworkdayjobs.com/Interac"),
    "dayforce": ({"platform": "dayforce", "slug": "acme"},
                 "https://acme.dayforcehcm.com/CandidatePortal/en-US/acme"),
    "dayforce_shared": ({"platform": "dayforce_shared", "slug": "acme", "site": "CANDIDATEPORTAL"},
                        "https://jobs.dayforcehcm.com/en-US/acme/CANDIDATEPORTAL"),
}


def test_every_platform_has_a_board_url():
    assert set(CASES) == set(ats.FETCHERS)
    for platform, (entry, want) in CASES.items():
        assert ats.board_url(entry) == want, platform


def test_board_url_round_trips_through_detect():
    # the board URL must still identify the same platform + slug (resolver / promote tools rely on it)
    for platform, (entry, url) in CASES.items():
        d = ats_detect.detect_ats(url)
        assert d and d["platform"] == platform and d["slug"].lower() == entry["slug"].lower(), (platform, d)


def test_unknown_platform_returns_empty():
    assert ats.board_url({"platform": "resolve", "slug": "x"}) == ""
    assert ats.board_url({"platform": "jazzhr", "slug": ""}) == ""


def test_no_auto_promoted_entry_links_to_a_single_job():
    reg = json.load(open(os.path.join(ROOT, "engine", "companies.json"), encoding="utf-8"))
    reg = reg if isinstance(reg, list) else reg["companies"]
    auto = [c for c in reg if "auto-promoted" in (c.get("flags") or [])]
    assert auto
    bad = [(c["name"], c["careers_url"]) for c in auto if c["careers_url"] != ats.board_url(c)]
    assert not bad, bad[:5]
