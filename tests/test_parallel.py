"""JB-41: parallel fetch must give exactly the sequential result, in the same order."""
import os, sys, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import build_board


def test_parallel_map_keeps_input_order():
    def slow(x):
        time.sleep(0.01 * (5 - x))          # later items finish first
        return x * 10
    assert build_board.parallel_map(slow, range(5), workers=5) == [0, 10, 20, 30, 40]


def test_parallel_map_actually_runs_concurrently():
    seen = set()
    def f(x):
        seen.add(threading.get_ident()); time.sleep(0.05); return x
    t = time.monotonic()
    build_board.parallel_map(f, range(8), workers=8)
    assert time.monotonic() - t < 0.3 and len(seen) > 1


def test_single_worker_is_sequential():
    assert build_board.parallel_map(lambda x: x + 1, [1, 2, 3], workers=1) == [2, 3, 4]


def test_enrichment_parallel_equals_sequential(monkeypatch):
    stubs = [{"company": f"Co{i}", "title": "x", "location": "Toronto, ON", "source": "getro:MaRS",
              "url": f"https://jobs.lever.co/co{i}/1", "description": ""} for i in range(6)]
    fetch = lambda e: ([{"company": e["name"], "title": t, "location": "Toronto", "url": e["slug"] + t,
                         "description": "d", "source": "lever"} for t in ("A", "B")], None)
    monkeypatch.setattr(build_board, "WORKERS", 1)
    seq = build_board.enrich_via_ats(stubs, set(), fetch=fetch)
    monkeypatch.setattr(build_board, "WORKERS", 6)
    par = build_board.enrich_via_ats(stubs, set(), fetch=fetch)
    assert seq == par
