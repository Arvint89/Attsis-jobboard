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


def test_strip_html_helper():
    assert ats._strip_html("&lt;h2&gt;Hi&lt;/h2&gt;&lt;p&gt;A &amp; B&lt;/p&gt;").replace("\n", " ").strip().startswith("Hi")


def test_fetch_company_unresolved():
    jobs, err = ats.fetch_company({"name": "X", "platform": "resolve"})
    assert jobs == [] and err == "unresolved"


def test_fetch_company_unknown_platform():
    jobs, err = ats.fetch_company({"name": "X", "platform": "nope", "slug": "x"})
    assert jobs == [] and "no adapter" in err
