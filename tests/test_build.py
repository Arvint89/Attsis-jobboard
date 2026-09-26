"""Tests for build_board orchestration helpers. JB-20: per-company cap."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import build_board as b


def test_cap_limits_big_company_keeps_highest_scores():
    rows = [{"company": "Big", "score": s} for s in range(12)] + [{"company": "Small", "score": 5}]
    kept, dropped = b.cap_per_company(rows, n=8)
    big = [r for r in kept if r["company"] == "Big"]
    assert len(big) == 8 and dropped == 4            # 12 -> 8, 4 trimmed
    assert min(r["score"] for r in big) == 4         # kept the top-8 by score (11..4)
    assert any(r["company"] == "Small" for r in kept)  # small company untouched


def test_cap_noop_when_under_limit():
    rows = [{"company": "A", "score": 7}, {"company": "A", "score": 6}, {"company": "B", "score": 9}]
    kept, dropped = b.cap_per_company(rows, n=8)
    assert len(kept) == 3 and dropped == 0


def test_cap_empty():
    kept, dropped = b.cap_per_company([], n=8)
    assert kept == [] and dropped == 0


def test_source_funnel_counts_kept_and_excluded_by_reason():
    import build_board
    jobs = [{"source": "getro:Communitech"}] * 3 + [{"source": "greenhouse"}]
    res = [{"verdict": "below", "reasons": []},
           {"verdict": "excluded", "reasons": ["stale (45d)"]},
           {"verdict": "excluded", "reasons": ["off-profile title: sales"]},
           {"verdict": "match", "reasons": []}]
    out = build_board.source_funnel(list(zip(jobs, res)))
    assert out == {"getro:Communitech": {"fetched": 3, "kept": 1,
                                         "excluded": {"stale": 1, "off-profile title": 1}},
                   "greenhouse": {"fetched": 1, "kept": 1, "excluded": {}}}


def test_source_funnel_missing_source_and_reason():
    import build_board
    out = build_board.source_funnel([({}, {"verdict": "excluded", "reasons": []})])
    assert out == {"unknown": {"fetched": 1, "kept": 0, "excluded": {"unspecified": 1}}}


class _StubResolver:
    def __init__(self, table): self.table = table; self.calls = []
    def resolve(self, url): self.calls.append(url); return self.table.get(url)


def test_resolve_registry_entries_promotes_supported():
    r = _StubResolver({"https://careers.trudellmed.com":
                       {"platform": "greenhouse", "slug": "trudell", "supported": True}})
    entries = [{"name": "Trudell Medical", "ring": 0, "platform": "resolve", "slug": "",
                "careers_url": "https://careers.trudellmed.com", "flags": [], "industry": "medical"}]
    promoted, still = b.resolve_registry_entries(entries, r)
    assert len(promoted) == 1 and still == []
    p = promoted[0]
    assert p["platform"] == "greenhouse" and p["slug"] == "trudell"
    # registry metadata preserved for ring/flags/industry attach in gather()
    assert p["ring"] == 0 and p["industry"] == "medical"


def test_resolve_registry_entries_keeps_unsupported_and_unknown():
    r = _StubResolver({
        "https://careers.a.io": {"platform": "teamtailor", "slug": "a", "supported": False},
        "https://careers.b.io": None,
    })
    entries = [
        {"name": "A", "platform": "resolve", "careers_url": "https://careers.a.io"},
        {"name": "B", "platform": "resolve", "careers_url": "https://careers.b.io"},
        {"name": "C", "platform": "resolve"},                                        # no careers_url
    ]
    promoted, still = b.resolve_registry_entries(entries, r)
    assert promoted == []
    assert [e["name"] for e in still] == ["A", "B", "C"]
    assert r.calls == ["https://careers.a.io", "https://careers.b.io"]                # C not called


def test_build_payload_has_resolver_stats_key_and_saves_cache(monkeypatch, tmp_path):
    """JB-43 step 4: payload exposes resolver_stats + a cache file is written next to jobs.json."""
    import ats, sources, build_board
    monkeypatch.setattr(ats, "fetch_company", lambda e: ([], None))
    monkeypatch.setattr(sources, "load_sources", lambda: [])
    monkeypatch.setattr(sources, "fetch_source", lambda e: ([], None))
    monkeypatch.setattr(build_board, "DATA", str(tmp_path))
    payload = build_board.build(demo=False, min_score=0)
    assert "resolver_stats" in payload
    assert set(payload["resolver_stats"] or {}) == {"cached", "fetched", "found", "failed", "skipped_cap"}
    assert (tmp_path / "resolver_cache.json").exists()


def test_build_demo_leaves_resolver_stats_none(monkeypatch, tmp_path):
    """Demo mode doesn't run the resolver, so stats stays None (not stale from a prior run)."""
    import build_board
    build_board.LAST_RESOLVER["stats"] = {"cached": 99}   # inject stale state
    monkeypatch.setattr(build_board, "DATA", str(tmp_path))
    payload = build_board.build(demo=True, min_score=0)
    assert payload["resolver_stats"] is None
    assert not (tmp_path / "resolver_cache.json").exists()


def test_resolve_registry_entries_carries_workday_extras():
    r = _StubResolver({"https://x": {"platform": "workday", "slug": "acme", "supported": True,
                                      "tenant": "acme", "site": "External", "dc": "wd3"}})
    promoted, _ = b.resolve_registry_entries(
        [{"name": "Acme", "platform": "resolve", "careers_url": "https://x"}], r)
    assert promoted[0]["tenant"] == "acme" and promoted[0]["site"] == "External" and promoted[0]["dc"] == "wd3"
