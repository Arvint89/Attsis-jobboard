"""JB-55: discovered-companies persistence + auto-promote alerts."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import discovered as d
from company_key import company_key


def _job(company, source="getro:Communitech", url="https://x.io/j/1", location="Toronto"):
    return {"company": company, "source": source, "url": url, "location": location}


def test_merge_first_sweep_creates_entry():
    state = d.merge({}, [_job("Deep Trekker")], registry_keys=set(), now="2026-09-26T00:00:00Z")
    key = company_key("Deep Trekker")
    assert key in state
    e = state[key]
    assert e["last_name_seen"] == "Deep Trekker"
    assert e["sweep_count"] == 1
    assert e["sources_seen"] == ["getro:Communitech"]
    assert e["first_seen_iso"] == e["last_seen_iso"] == "2026-09-26T00:00:00Z"


def test_merge_second_sweep_increments_and_updates_timestamps():
    prev = d.merge({}, [_job("Deep Trekker")], set(), now="2026-09-20T00:00:00Z")
    state = d.merge(prev, [_job("Deep Trekker")], set(), now="2026-09-26T00:00:00Z")
    e = state[company_key("Deep Trekker")]
    assert e["sweep_count"] == 2
    assert e["first_seen_iso"] == "2026-09-20T00:00:00Z"   # preserved
    assert e["last_seen_iso"] == "2026-09-26T00:00:00Z"    # advanced


def test_merge_deduplicates_within_a_single_sweep():
    # Same company appearing on 5 jobs in one sweep still counts once.
    jobs = [_job("Deep Trekker", url=f"https://x.io/j/{i}") for i in range(5)]
    state = d.merge({}, jobs, set(), now="2026-09-26T00:00:00Z")
    assert state[company_key("Deep Trekker")]["sweep_count"] == 1


def test_registry_companies_are_skipped():
    reg = {company_key("Deep Trekker")}
    state = d.merge({}, [_job("Deep Trekker"), _job("New Co")], reg, now="2026-09-26T00:00:00Z")
    assert company_key("Deep Trekker") not in state
    assert company_key("New Co") in state


def test_canonicalization_collapses_soft_duplicates():
    # "Pipetel Technologies Inc." and "Pipetel Technologies" hit the same entry.
    state = d.merge({}, [_job("Pipetel Technologies Inc.")], set())
    state = d.merge(state, [_job("Pipetel Technologies")], set())
    assert len(state) == 1
    key = company_key("Pipetel Technologies")
    assert state[key]["sweep_count"] == 2


def test_sources_capped_and_deduped():
    state = {}
    for i, src in enumerate(["a", "b", "c", "d", "e", "f", "g"]):
        state = d.merge(state, [_job("X", source=src)], set(), now=f"2026-09-{20+i}T00:00:00Z")
    e = state[company_key("X")]
    assert len(e["sources_seen"]) <= d.MAX_SOURCES
    # duplicate source doesn't grow the list
    state = d.merge(state, [_job("X", source="a")], set())
    assert len(state[company_key("X")]["sources_seen"]) <= d.MAX_SOURCES


def test_auto_promote_alerts_below_and_above_threshold():
    state = {}
    for i in range(d.AUTO_PROMOTE_THRESHOLD):
        state = d.merge(state, [_job("Trudell Medical", url="https://halma.wd3.myworkdayjobs.com/x")],
                        set(), now=f"2026-09-{20+i}T00:00:00Z")
    alerts = d.auto_promote_alerts(state)
    assert len(alerts) == 1
    assert "Trudell Medical" in alerts[0]
    assert "3 sweeps" in alerts[0]
    # below threshold: no alert
    state2 = d.merge({}, [_job("New Co")], set())
    assert d.auto_promote_alerts(state2) == []


def test_record_writes_file_and_returns_alerts(tmp_path):
    # 3 sweeps of the same company -> file written + 1 alert
    state = {}
    for i in range(3):
        state = d.merge(state, [_job("Foo Corp")], set(), now=f"2026-09-{20+i}T00:00:00Z")
    # record with prev-state loaded via a stub fetcher
    def fake_fetch(url): return state
    new_state, alerts = d.record([_job("Foo Corp")], set(), str(tmp_path), live=True, fetch=fake_fetch)
    out = tmp_path / "discovered_companies.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert company_key("Foo Corp") in payload
    assert new_state[company_key("Foo Corp")]["sweep_count"] == 4   # 3 loaded + this one
    assert alerts and "Foo Corp" in alerts[0]


def test_record_demo_skips_prev_load(tmp_path):
    # Demo runs must not clobber the live-file state; they start from {}.
    def fetch_should_not_be_called(url):
        raise AssertionError("live=False must not fetch")
    state, alerts = d.record([_job("Bar")], set(), str(tmp_path), live=False,
                             fetch=fetch_should_not_be_called)
    assert list(state.keys()) == [company_key("Bar")]
    assert state[company_key("Bar")]["sweep_count"] == 1
    assert alerts == []


def test_load_previous_returns_empty_on_failure():
    def boom(url): raise RuntimeError("network down")
    assert d.load_previous(fetch=boom) == {}
    def bad_shape(url): return ["not", "a", "dict"]
    assert d.load_previous(fetch=bad_shape) == {}
