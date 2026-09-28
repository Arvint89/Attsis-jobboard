"""Tests for tools/linkedin_scout.py (JB-46).

The scout is deterministic and offline-testable: extract_company() parses a
LinkedIn job page HTML string; scout() adds a cache layer around a fetcher
callable which we inject in tests (no real HTTP).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import linkedin_scout as scout  # noqa: E402


# --- extract_company ---------------------------------------------------------

JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "FPGA Engineer",
  "hiringOrganization": {
    "@type": "Organization",
    "name": "Per Vices Corporation",
    "sameAs": "https://www.pervices.com/",
    "url": "https://www.pervices.com/"
  }
}
</script>
</head><body>...</body></html>
"""


def test_extract_company_from_json_ld():
    info = scout.extract_company(JSONLD_HTML)
    assert info["company"] == "Per Vices Corporation"
    assert info["careers_url"] == "https://www.pervices.com/"


TOPCARD_HTML = """
<html><body>
<a class="topcard__org-name-link" href="https://www.linkedin.com/company/sciemetric-instruments/">
  Sciemetric Instruments
</a>
</body></html>
"""


def test_extract_company_from_topcard_anchor():
    info = scout.extract_company(TOPCARD_HTML)
    assert info["company"] == "Sciemetric Instruments"
    assert "linkedin.com/company/sciemetric-instruments" in info["company_linkedin_url"]


OG_TITLE_HTML = """
<html><head>
<meta property="og:title" content="Semtech hiring Firmware Engineer in Toronto | LinkedIn" />
</head></html>
"""


def test_extract_company_from_og_title():
    info = scout.extract_company(OG_TITLE_HTML)
    assert info["company"] == "Semtech"


def test_extract_company_empty_returns_empty_fields():
    info = scout.extract_company("")
    assert info == {"company": "", "company_linkedin_url": "", "careers_url": ""}


# --- normalize_url -----------------------------------------------------------

def test_normalize_strips_query_and_trailing_slash():
    assert scout.normalize_url(
        "https://www.linkedin.com/jobs/view/4470987790/?refId=abc&trk=xyz"
    ) == "https://www.linkedin.com/jobs/view/4470987790"


def test_normalize_leaves_bare_url_alone():
    u = "https://www.linkedin.com/jobs/view/4470987790"
    assert scout.normalize_url(u) == u


# --- scout() with injected fetcher + cache -----------------------------------

def test_scout_caches_first_fetch_and_reuses(tmp_path):
    cache = os.path.join(tmp_path, "cache.json")
    calls = {"n": 0}

    def fake_fetch(url):
        calls["n"] += 1
        return JSONLD_HTML

    url = "https://www.linkedin.com/jobs/view/4470987790?refId=x"
    first = scout.scout(url, fetcher=fake_fetch, cache_path=cache)
    assert first["info"]["company"] == "Per Vices Corporation"
    assert first["cached"] is False
    assert calls["n"] == 1

    # Second call with same (normalized) URL should hit cache -> no fetch.
    second = scout.scout(
        "https://www.linkedin.com/jobs/view/4470987790/",
        fetcher=fake_fetch, cache_path=cache,
    )
    assert calls["n"] == 1, "cache should have prevented a second fetch"
    assert second["cached"] is True
    assert second["info"]["company"] == "Per Vices Corporation"

    # Cache file exists and is valid JSON with the normalized URL as key.
    payload = json.load(open(cache, encoding="utf-8"))
    assert list(payload.keys()) == ["https://www.linkedin.com/jobs/view/4470987790"]


def test_scout_from_html_paste_fallback():
    result = scout.scout_from_html(TOPCARD_HTML)
    assert result["info"]["company"] == "Sciemetric Instruments"
    assert result["proposal"]["name"] == "Sciemetric Instruments"
    assert result["proposal"]["platform"] == "resolve"


# --- propose_registry_entry --------------------------------------------------

def test_proposal_shape_matches_companies_json_line():
    info = {"company": "Adtran", "careers_url": "https://www.adtran.com/careers"}
    entry = scout.propose_registry_entry(info, city="Ottawa", industry="networking")
    # Must have every field companies.json entries carry so it pastes cleanly.
    expected_keys = {"name", "ring", "platform", "slug", "careers_url",
                     "note", "flags", "industry", "sponsors", "city"}
    assert set(entry.keys()) == expected_keys
    assert entry["name"] == "Adtran"
    assert entry["platform"] == "resolve"
    assert entry["careers_url"] == "https://www.adtran.com/careers"
    assert entry["city"] == "Ottawa"
    assert entry["industry"] == "networking"
