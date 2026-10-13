"""JB-87: JazzHR (applytojob.com) adapter -- listing HTML + per-job JobPosting JSON-LD. No network."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import ats  # noqa: E402
import ats_detect  # noqa: E402

# Trimmed from the real https://myant.applytojob.com/apply (2026-10-12)
LISTING = """
<ul class="list-group">
  <li class="list-group-item">
    <h3 class='list-group-item-heading'>
      <a href="https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology">
        Account Executive, Cardiology                                    </a>
    </h3>
    <ul class='list-inline list-group-item-text'>
      <li><i class='fa fa-map-marker'></i>Mississauga, ON, Canada</li>
    </ul>
  </li>
  <li class="list-group-item">
    <h3 class='list-group-item-heading'>
      <a href="https://myant.applytojob.com/apply/WmsIhQNNeD/RD-Electrical-Engineer-OnSite">
        R&amp;D Electrical Engineer (On-Site)</a>
    </h3>
    <ul class='list-inline list-group-item-text'>
      <li><i class='fa fa-map-marker'></i>Toronto, ON</li>
      <li><i class='fa fa-sitemap'></i>Engineering</li>
    </ul>
  </li>
</ul>
"""

# Trimmed from the real job page: the Organization block comes first, then the JobPosting.
DETAIL = """
<script type="application/ld+json">
{ "@type": "Organization", "name": "Myant Shared Service Corp." }
</script>
<script type="application/ld+json">
{
    "@context": "http:\\/\\/schema.org\\/",
    "@type": "JobPosting",
    "url": "https:\\/\\/myant.applytojob.com\\/apply\\/teiZDWhRON\\/Account-Executive-Cardiology",
    "title": "Account Executive, Cardiology",
    "description": "<p><span>About Myant:<\\/span><\\/p><ul><li>Sell ECG wearables<\\/li><\\/ul>",
    "datePosted": "2026-10-03",
    "employmentType": "FULL_TIME",
    "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress",
        "addressLocality": "Mississauga", "addressRegion": "ON", "postalCode": "L5K 2L1"}}
}
</script>
"""


class _R:
    def __init__(self, text):
        self.text = text


def _fake(pages, calls=None):
    def get(url, *a, **k):
        if calls is not None:
            calls.append(url)
        if url in pages:
            v = pages[url]
            if isinstance(v, Exception):
                raise v
            return _R(v)
        raise RuntimeError("404 " + url)
    return get


def test_listing_plus_jsonld_detail(monkeypatch):
    pages = {"https://myant.applytojob.com/apply": LISTING,
             "https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology": DETAIL}
    monkeypatch.setattr(ats, "_get", _fake(pages))
    jobs = ats.fetch_jazzhr("Myant", "myant")
    assert [j["title"] for j in jobs] == ["Account Executive, Cardiology", "R&D Electrical Engineer (On-Site)"]
    a = jobs[0]
    assert a["source"] == "jazzhr"
    assert a["url"] == "https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology"
    assert a["posted"] == "2026-10-03"
    assert "Sell ECG wearables" in a["description"] and "<" not in a["description"]
    assert a["location"] == "Mississauga, ON, Canada"   # the listing's fuller location is kept


def test_failed_detail_keeps_listing_title_and_location(monkeypatch):
    # the 2nd job's detail page is missing -> title + location from the listing, empty description
    pages = {"https://myant.applytojob.com/apply": LISTING,
             "https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology": DETAIL}
    monkeypatch.setattr(ats, "_get", _fake(pages))
    b = ats.fetch_jazzhr("Myant", "myant")[1]
    assert b["title"] == "R&D Electrical Engineer (On-Site)"
    assert b["location"] == "Toronto, ON"
    assert b["description"] == "" and b["posted"] is None


def test_location_falls_back_to_jsonld(monkeypatch):
    listing = LISTING.replace("<li><i class='fa fa-map-marker'></i>Mississauga, ON, Canada</li>", "")
    pages = {"https://myant.applytojob.com/apply": listing,
             "https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology": DETAIL}
    monkeypatch.setattr(ats, "_get", _fake(pages))
    assert ats.fetch_jazzhr("Myant", "myant")[0]["location"] == "Mississauga, ON"


def test_empty_board(monkeypatch):
    monkeypatch.setattr(ats, "_get", _fake({"https://x.applytojob.com/apply": "<html>No openings</html>"}))
    assert ats.fetch_jazzhr("X", "x") == []


def test_detail_fetches_are_capped(monkeypatch):
    items = "".join(
        f'<li class="list-group-item"><h3><a href="https://big.applytojob.com/apply/AAAAAAAA{i:02d}/Job-{i}">Job {i}</a></h3></li>'
        for i in range(ats.JAZZHR_MAX_DETAILS + 5))
    calls = []
    monkeypatch.setattr(ats, "_get", _fake({"https://big.applytojob.com/apply": items}, calls))
    jobs = ats.fetch_jazzhr("Big", "big")
    assert len(jobs) == ats.JAZZHR_MAX_DETAILS + 5          # every job is still listed
    assert len(calls) == 1 + ats.JAZZHR_MAX_DETAILS         # but only the first N detail pages are fetched


def test_registered_and_detected():
    assert "jazzhr" in ats.FETCHERS
    d = ats_detect.detect_ats("https://myant.applytojob.com/apply/WmsIhQNNeD/RD-Electrical-Engineer-OnSite")
    assert d == {"platform": "jazzhr", "slug": "myant", "supported": True}
    # applytojobs.ca is a different platform: not claimed as JazzHR
    d2 = ats_detect.detect_ats("https://ecopiatech.applytojobs.ca/engineering/50825")
    assert not d2 or d2["platform"] != "jazzhr"


# Trimmed from a real Carbon Engineering job page (2026-10-12): NO JobPosting JSON-LD,
# only the Organization block. The description lives in div#job-description.
DETAIL_NO_JSONLD = """
<script type="application/ld+json">{ "@type": "Organization", "name": "Carbon Engineering" }</script>
<div class='page-body job-details'>
  <div class='row'>
    <div class='col col-xs-7 description' id="job-description">
      <span><b>Grow your career.&#160;</b>Direct Air Capture (DAC) process engineering co-op.</span><br><div></div>                </div>
    <div class="resumator-mobile-apply-wrapper mobile"><a id="resumator-mobile-share-button">Share</a></div>
"""


def test_html_description_fallback_when_no_jsonld(monkeypatch):
    pages = {"https://myant.applytojob.com/apply": LISTING,
             "https://myant.applytojob.com/apply/teiZDWhRON/Account-Executive-Cardiology": DETAIL_NO_JSONLD}
    monkeypatch.setattr(ats, "_get", _fake(pages))
    a = ats.fetch_jazzhr("Myant", "myant")[0]
    assert "Direct Air Capture (DAC) process engineering co-op." in a["description"]
    assert "Share" not in a["description"] and "resumator" not in a["description"]
    assert a["posted"] is None   # no date without JSON-LD
