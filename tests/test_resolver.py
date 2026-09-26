"""JB-43: Resolver behaviour — cache TTLs, fetch cap, failure handling, embed URLs.

All tests inject `get_text` and `now` — no network. Fixed clock keeps TTL logic deterministic.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

from datetime import datetime, timedelta, timezone

import ats_detect
import resolver as R


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _entry(det, days_ago):
    return {"det": det, "checked": (NOW - timedelta(days=days_ago)).isoformat(), "url": "x"}


def test_cache_key_normalises_host_and_first_segment():
    assert R.cache_key("https://careers.acme.io/jobs/xyz?a=1") == "careers.acme.io/jobs"
    assert R.cache_key("https://Careers.ACME.io/") == "careers.acme.io"
    assert R.cache_key("") == ""


def test_detect_ats_short_circuits_no_fetch():
    calls = []
    def boom(_):
        calls.append(1); raise AssertionError("must not fetch when URL is already an ATS")
    r = R.Resolver(get_text=boom, now=NOW)
    got = r.resolve("https://boards.greenhouse.io/tenstorrent")
    assert got == {"platform": "greenhouse", "slug": "tenstorrent", "supported": True}
    assert calls == [] and r.lookups == 0


def test_fresh_miss_returns_none_from_cache_no_fetch():
    key = "careers.acme.io/jobs"
    cache = {key: _entry(det=None, days_ago=3)}       # miss TTL = 7d, so 3d is fresh
    def boom(_): raise AssertionError("cache is fresh — must not fetch")
    r = R.Resolver(cache=cache, get_text=boom, now=NOW)
    assert r.resolve("https://careers.acme.io/jobs/anything") is None
    assert r.stats["cached"] == 1 and r.stats["fetched"] == 0 and r.lookups == 0


def test_stale_miss_refetches():
    key = "careers.acme.io/jobs"
    cache = {key: _entry(det=None, days_ago=8)}       # miss TTL = 7d, so 8d is stale
    r = R.Resolver(cache=cache, get_text=lambda _: "<a href='https://boards.greenhouse.io/acme'>x</a>", now=NOW)
    got = r.resolve("https://careers.acme.io/jobs/anything")
    assert got == {"platform": "greenhouse", "slug": "acme", "supported": True}
    assert r.stats["fetched"] == 1 and r.stats["found"] == 1 and r.lookups == 1


def test_fresh_hit_returns_cached_det_no_fetch():
    key = "careers.acme.io/jobs"
    hit = {"platform": "greenhouse", "slug": "acme", "supported": True}
    cache = {key: _entry(det=hit, days_ago=25)}       # hit TTL = 30d, so 25d is fresh
    def boom(_): raise AssertionError("cached hit — must not fetch")
    r = R.Resolver(cache=cache, get_text=boom, now=NOW)
    assert r.resolve("https://careers.acme.io/jobs/x") == hit
    assert r.stats["cached"] == 1 and r.lookups == 0


def test_stale_hit_refetches():
    key = "careers.acme.io/jobs"
    old = {"platform": "greenhouse", "slug": "old", "supported": True}
    cache = {key: _entry(det=old, days_ago=31)}       # hit TTL = 30d, so 31d is stale
    r = R.Resolver(cache=cache, get_text=lambda _: "<a href='https://boards.greenhouse.io/new'>x</a>", now=NOW)
    got = r.resolve("https://careers.acme.io/jobs/x")
    assert got["slug"] == "new" and r.stats["fetched"] == 1


def test_cap_prevents_fetch_and_bumps_skipped_stat():
    called = []
    r = R.Resolver(get_text=lambda u: called.append(u) or "", max_lookups=1, now=NOW)
    r.resolve("https://careers.a.io/jobs")            # first: fetches, cache miss stored
    r.resolve("https://careers.b.io/jobs")            # second: cap hit
    assert len(called) == 1
    assert r.stats["skipped_cap"] == 1 and r.stats["fetched"] == 1


def test_cap_falls_back_to_stale_cache_when_available():
    key = "careers.acme.io/jobs"
    stale = {"platform": "greenhouse", "slug": "acme", "supported": True}
    cache = {key: _entry(det=stale, days_ago=99)}     # very stale
    def boom(_): raise AssertionError("cap reached — must not fetch")
    r = R.Resolver(cache=cache, get_text=boom, max_lookups=0, now=NOW)
    assert r.resolve("https://careers.acme.io/jobs/x") == stale
    assert r.stats["skipped_cap"] == 1


def test_fetch_failure_caches_none_and_increments_failed():
    def bad(_): raise ConnectionError("timeout")
    r = R.Resolver(get_text=bad, now=NOW)
    assert r.resolve("https://careers.acme.io/jobs") is None
    assert r.stats["failed"] == 1 and r.stats["found"] == 0
    key = R.cache_key("https://careers.acme.io/jobs")
    assert r.cache[key]["det"] is None


def test_embed_url_resolves_to_greenhouse_slug():
    embed = "https://boards.greenhouse.io/embed/job_board?for=ecobee"
    assert ats_detect.detect_ats(embed) == {"platform": "greenhouse", "slug": "ecobee", "supported": True}


def test_html_scan_prefers_supported_ats():
    html = ('<a href="https://x.teamtailor.com/jobs">old</a>'
            '<iframe src="https://boards.greenhouse.io/embed/job_board?for=acme"></iframe>')
    assert ats_detect.detect_ats_in_html(html) == {"platform": "greenhouse", "slug": "acme", "supported": True}
