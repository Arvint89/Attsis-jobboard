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
