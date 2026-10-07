"""Unit tests for ATS normalizers. No network: we feed captured JSON shapes to
the parsing path by monkeypatching ats._get. Verifies the normalized contract
(FR-2 in SPEC.md): every adapter returns the same 7-key dict."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import ats

REQUIRED = {"company", "title", "location", "url", "posted", "description", "source"}


class FakeResp:
    def __init__(self, payload): self._p = payload
    def json(self): return self._p
    def raise_for_status(self): pass


def patch(monkey_payload):
    ats._get = lambda url, method="GET", **kw: FakeResp(monkey_payload)


def test_greenhouse_normalizes():
    patch({"jobs": [{"title": "Hardware Engineer",
                     "location": {"name": "Toronto"},
                     "absolute_url": "https://x/y",
                     "updated_at": "2026-09-10T00:00:00-04:00",
                     "content": "&lt;p&gt;Altium &amp; PCB&lt;/p&gt;"}]})
    jobs = ats.fetch_greenhouse("Acme", "acme")
    assert len(jobs) == 1
    j = jobs[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "Hardware Engineer"
    assert j["location"] == "Toronto"
    assert "Altium" in j["description"] and "<" not in j["description"]  # HTML stripped
    assert j["source"] == "greenhouse"


def test_lever_normalizes_and_converts_epoch():
    patch([{"text": "Firmware Engineer",
            "categories": {"location": "Ottawa"},
            "hostedUrl": "https://lever/1",
            "createdAt": 1757000000000,
            "descriptionPlain": "Embedded C, RTOS"}])
    j = ats.fetch_lever("Acme", "acme")[0]
    assert REQUIRED <= set(j)
    assert j["posted"].startswith("2025")  # epoch ms -> ISO
    assert j["source"] == "lever"


def test_bamboohr_empty_result_is_safe():
    patch({"result": []})
    assert ats.fetch_bamboohr("Acme", "acme") == []


def test_workable_normalizes():
    # JB-48: apply.workable.com/api/v3/accounts/{slug}/jobs shape
    patch({"results": [{
        "title": "Embedded Software Engineer",
        "shortcode": "AB12CD",
        "location": {"city": "Toronto", "region": "Ontario", "country": "Canada"},
        "published_on": "2026-09-20",
        "description": "&lt;p&gt;C, C++, RTOS, ARM Cortex-M&lt;/p&gt;",
    }]})
    j = ats.fetch_workable("Acme", "acme")[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "Embedded Software Engineer"
    assert j["location"] == "Toronto, Ontario, Canada"
    assert j["url"] == "https://apply.workable.com/acme/j/AB12CD/"
    assert "RTOS" in j["description"] and "<" not in j["description"]
    assert j["source"] == "workable"


def test_workable_missing_location_and_falls_back_to_created_at():
    patch({"results": [{
        "title": "Firmware Dev",
        "shortcode": "XYZ",
        "location": None,                          # missing entirely
        "created_at": "2026-09-01T00:00:00Z",      # published_on missing -> fallback
        "description": "",
    }]})
    j = ats.fetch_workable("Acme", "acme")[0]
    assert j["location"] == "n/a"                  # _norm's empty-location fallback
    assert j["posted"] == "2026-09-01T00:00:00Z"


def test_workable_empty_results_is_safe():
    patch({"results": []})
    assert ats.fetch_workable("Acme", "acme") == []


def test_workable_fetches_description_from_v2_detail():
    # JB-48b: v3 list omits description body; v2 /jobs/{shortcode} returns
    # description + requirements + benefits (all HTML). We concat + strip.
    def fake(url, method="GET", **kw):
        if "/api/v3/accounts/" in url and "/jobs" in url:
            return FakeResp({"results": [{
                "title": "FPGA Designer",
                "shortcode": "B9DA76D73F",
                "location": {"city": "Ottawa", "region": "Ontario", "country": "Canada"},
                "published_on": "2026-09-20",
                "description": "",   # list payload is thin
            }]})
        if "/api/v2/accounts/" in url and "/jobs/B9DA76D73F" in url:
            return FakeResp({
                "description":  "&lt;p&gt;Design FPGAs for ASIC prototyping.&lt;/p&gt;",
                "requirements": "&lt;p&gt;Verilog, SystemVerilog, Vivado, Quartus.&lt;/p&gt;",
                "benefits":     "&lt;p&gt;Health, dental, RRSP match.&lt;/p&gt;",
            })
        raise AssertionError("unexpected url: " + url)
    ats._get = fake
    j = ats.fetch_workable("Fidus", "fidus")[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "FPGA Designer"
    # all three sections concatenated + HTML stripped
    assert "Verilog" in j["description"]
    assert "RRSP" in j["description"]
    assert "FPGAs" in j["description"]
    assert "<" not in j["description"]


def test_workable_detail_failure_keeps_list_description():
    # JB-48b: if the v2 detail call errors, fall back to whatever the list gave us
    # (title-only if list description was also empty). Must not crash the sweep.
    def fake(url, method="GET", **kw):
        if "/api/v3/accounts/" in url and "/jobs" in url and "token" not in (kw.get("json") or {}):
            return FakeResp({"results": [{
                "title": "RF Designer", "shortcode": "XYZ",
                "location": {"city": "Ottawa"},
                "description": "",
            }]})
        raise RuntimeError("v2 detail down")
    ats._get = fake
    jobs = ats.fetch_workable("Fidus", "fidus")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "RF Designer"
    assert jobs[0]["description"] == ""   # title-only, no crash


def test_workable_follows_next_page_token():
    # JB-48b: v3 list caps at 10 results and returns a nextPage token for the rest.
    # Issue #98: Fidus has 13 jobs; reading only page 1 silently drops 3.
    calls = {"n": 0}
    def fake(url, method="GET", **kw):
        if "/api/v3/accounts/" in url and "/jobs" in url:
            calls["n"] += 1
            body = kw.get("json") or {}
            if "token" not in body:
                return FakeResp({
                    "results": [{"title": f"Job {i}", "shortcode": f"S{i}",
                                 "location": None, "description": ""}
                                for i in range(10)],
                    "nextPage": "page2tok",
                })
            if body.get("token") == "page2tok":
                return FakeResp({
                    "results": [{"title": f"Job {i}", "shortcode": f"S{i}",
                                 "location": None, "description": ""}
                                for i in range(10, 13)],
                })
            raise AssertionError("unknown token: " + str(body))
        if "/api/v2/accounts/" in url:
            return FakeResp({})   # detail returns nothing -> keep title-only
        raise AssertionError("unexpected url: " + url)
    ats._get = fake
    jobs = ats.fetch_workable("Fidus", "fidus")
    assert len(jobs) == 13
    assert calls["n"] == 2   # one page + one followup, not more


def test_breezy_normalizes():
    # JB-49: {slug}.breezy.hr/json returns a top-level list of postings
    patch([{
        "id": "d5121e75815a",
        "name": "Embedded Software Engineer",
        "location": {"city": "Montreal",
                     "state": {"id": "QC", "name": "Quebec"},
                     "country": {"id": "CA", "name": "Canada"}},
        "url": "https://sense-engineering.breezy.hr/p/d5121e75815a-embedded",
        "published_date": "2026-09-01T00:00:00Z",
        "description": "",
    }])
    j = ats.fetch_breezy("Sense", "sense-engineering")[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "Embedded Software Engineer"
    assert j["location"] == "Montreal, QC, CA"
    assert j["url"] == "https://sense-engineering.breezy.hr/p/d5121e75815a-embedded"
    assert j["posted"] == "2026-09-01T00:00:00Z"
    assert j["source"] == "breezy"


def test_breezy_missing_location_falls_back_to_creation_date():
    patch([{
        "id": "x",
        "name": "Firmware Dev",
        "location": None,
        "url": "https://acme.breezy.hr/p/x",
        "creation_date": "2026-08-15T00:00:00Z",
        "description": "",
    }])
    j = ats.fetch_breezy("Acme", "acme")[0]
    assert j["location"] == "n/a"
    assert j["posted"] == "2026-08-15T00:00:00Z"


def test_breezy_empty_list_is_safe():
    patch([])
    assert ats.fetch_breezy("Acme", "acme") == []


def test_dayforce_normalizes_string_location():
    # JB-47: {client}.dayforcehcm.com/CandidatePortal/{lang}/{client}/Posting/List
    # returns {"Postings": [...]} in the common Ceridian shape.
    patch({"Postings": [{
        "Title": "Network Engineer",
        "Location": "Toronto, ON, Canada",
        "ParentId": 12345,
        "PostingStartDate": "2026-09-15",
        "Description": "&lt;p&gt;Cisco, BGP, MPLS&lt;/p&gt;",
    }]})
    j = ats.fetch_dayforce("Rogers", "rogers", site="RogersDefault")[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "Network Engineer"
    assert j["location"] == "Toronto, ON, Canada"
    # URL synthesized when the payload doesn't provide one
    assert "rogers.dayforcehcm.com" in j["url"]
    assert "RogersDefault" in j["url"] and "12345" in j["url"]
    assert "Cisco" in j["description"] and "<" not in j["description"]
    assert j["source"] == "dayforce"


def test_dayforce_normalizes_dict_location_and_bare_list():
    # Some tenants return a bare list rather than {"Postings": [...]} and use
    # a dict for Location. Both variants must yield the same normalized shape.
    patch([{
        "title": "Cashier",
        "location": {"City": "Brampton", "State": "ON", "Country": "Canada"},
        "PostingId": 999,
        "url": "https://loblaw.dayforcehcm.com/CandidatePortal/en-CA/loblaw/Site/Retail/Posting/View/999",
        "PostedDate": "2026-09-10",
    }])
    j = ats.fetch_dayforce("Loblaw", "loblaw", site="Retail")[0]
    assert j["title"] == "Cashier"
    assert j["location"] == "Brampton, ON, Canada"
    assert j["url"].endswith("/View/999")   # explicit URL wins over synthesis
    assert j["posted"] == "2026-09-10"


def test_dayforce_empty_results_is_safe():
    patch({"Postings": []})
    assert ats.fetch_dayforce("Acme", "acme", site="Default") == []


def test_dayforce_missing_slug_returns_empty_without_network():
    # Guard against a resolve-in-flight entry (no slug filled yet). Must not
    # even try to fetch -- prevents a stray request to '..dayforcehcm.com/...'.
    called = {"n": 0}
    def sentinel(*a, **kw):
        called["n"] += 1
        raise AssertionError("should not fetch when slug is empty")
    ats._get = sentinel
    assert ats.fetch_dayforce("Acme", "", site="X") == []
    assert called["n"] == 0


def test_dayforce_registered_in_fetchers_and_recognized():
    assert "dayforce" in ats.FETCHERS
    # fetch_company must recognise platform:'dayforce' as a supported adapter
    # (returns [], None on happy fetch; here we short-circuit via missing slug).
    jobs, err = ats.fetch_company({"name": "X", "platform": "dayforce", "slug": ""})
    assert jobs == []
    assert err is None


def test_dayforce_shared_hits_jobs_host_and_normalizes():
    # JB-47b: jobs.dayforcehcm.com/CandidatePortal/{lang}/{tenant}/Posting/List?siteid={site}
    captured = {}
    def fake(url, method="GET", **kw):
        captured["url"] = url
        captured["params"] = kw.get("params")
        return FakeResp({"Postings": [{
            "Title": "Regulatory Affairs Specialist",
            "Location": "London, ON, Canada",
            "PostingId": 55,
            "PostingStartDate": "2026-09-20",
            "Description": "&lt;p&gt;medical devices&lt;/p&gt;",
        }]})
    ats._get = fake
    j = ats.fetch_dayforce_shared("Trudell", "tml", site="TMICANDIDATEPORTAL")[0]
    assert captured["url"].startswith("https://jobs.dayforcehcm.com/CandidatePortal/en-US/tml/")
    assert captured["url"].endswith("/Posting/List")
    assert captured["params"]["siteid"] == "TMICANDIDATEPORTAL"
    assert REQUIRED <= set(j)
    assert j["title"] == "Regulatory Affairs Specialist"
    # Synthesized view URL uses the shared host + tenant + site path
    assert j["url"].startswith("https://jobs.dayforcehcm.com/CandidatePortal/en-US/tml/Site/TMICANDIDATEPORTAL/")
    assert j["url"].endswith("/Posting/View/55")
    assert "medical" in j["description"] and "<" not in j["description"]
    # Source stays "dayforce" -- same ATS platform, different portal shape.
    assert j["source"] == "dayforce"


def test_dayforce_shared_handles_bare_list_and_dict_location():
    patch([{
        "title": "Design Engineer",
        "location": {"City": "London", "State": "ON", "Country": "Canada"},
        "PostingId": 7,
        "url": "https://jobs.dayforcehcm.com/en-US/tml/TMICANDIDATEPORTAL/Posting/View/7",
        "PostedDate": "2026-09-18",
    }])
    j = ats.fetch_dayforce_shared("Trudell", "tml", site="TMICANDIDATEPORTAL")[0]
    assert j["title"] == "Design Engineer"
    assert j["location"] == "London, ON, Canada"
    # Explicit URL wins over synthesis
    assert j["url"].endswith("/View/7")


def test_dayforce_shared_requires_both_tenant_and_site():
    # Both identifiers are mandatory -- without either, no request is made.
    called = {"n": 0}
    def sentinel(*a, **kw):
        called["n"] += 1
        raise AssertionError("should not fetch when tenant or site is empty")
    ats._get = sentinel
    assert ats.fetch_dayforce_shared("X", "", site="Y") == []
    assert ats.fetch_dayforce_shared("X", "tenant", site="") == []
    assert ats.fetch_dayforce_shared("X", "tenant") == []   # site default None
    assert called["n"] == 0


def test_dayforce_shared_registered_in_fetchers_and_recognized():
    assert "dayforce_shared" in ats.FETCHERS
    jobs, err = ats.fetch_company({"name": "X", "platform": "dayforce_shared", "slug": ""})
    assert jobs == []
    assert err is None


def patch_urls(router):
    """Route _get by URL substring -> payload (for adapters that make >1 call)."""
    def fake(url, method="GET", **kw):
        for frag, payload in router.items():
            if frag in url:
                return FakeResp(payload)
        raise AssertionError("unexpected url: " + url)
    ats._get = fake


def test_bamboohr_fetches_description_from_detail():
    # JB-19: list gives titles only; detail carries the description
    patch_urls({
        "/careers/list": {"result": [{"id": 42, "jobOpeningName": "Senior Firmware Developer",
                                        "location": "London, ON", "datePosted": "2026-09-01"}]},
        "/42/detail": {"result": {"jobOpening": {
            "description": "&lt;p&gt;Embedded C, ARM Cortex-M, RTOS, BLE&lt;/p&gt;",
            "datePosted": "2026-09-02",
            "jobOpeningShareUrl": "https://ztr.bamboohr.com/careers/42"}}},
    })
    j = ats.fetch_bamboohr("ZTR", "ztr")[0]
    assert REQUIRED <= set(j)
    assert j["title"] == "Senior Firmware Developer"
    assert "Embedded C" in j["description"] and "<" not in j["description"]  # description now populated + stripped
    assert j["url"].endswith("/careers/42")
    assert j["source"] == "bamboohr"


def test_bamboohr_detail_failure_keeps_title_only():
    # if the detail fetch errors, we still return the role (title-only), not crash
    def fake(url, method="GET", **kw):
        if "/careers/list" in url:
            return FakeResp({"result": [{"id": 7, "jobOpeningName": "Embedded Engineer", "location": "London"}]})
        raise RuntimeError("detail down")
    ats._get = fake
    jobs = ats.fetch_bamboohr("ZTR", "ztr")
    assert len(jobs) == 1 and jobs[0]["title"] == "Embedded Engineer" and jobs[0]["description"] == ""


def test_strip_html_helper():
    assert ats._strip_html("&lt;h2&gt;Hi&lt;/h2&gt;&lt;p&gt;A &amp; B&lt;/p&gt;").replace("\n", " ").strip().startswith("Hi")


def test_fetch_company_unresolved():
    jobs, err = ats.fetch_company({"name": "X", "platform": "resolve"})
    assert jobs == [] and err == "unresolved"


def test_fetch_company_unknown_platform():
    jobs, err = ats.fetch_company({"name": "X", "platform": "nope", "slug": "x"})
    assert jobs == [] and "no adapter" in err
