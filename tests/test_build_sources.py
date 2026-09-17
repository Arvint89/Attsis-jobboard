"""JB-3: source jobs flow through build() into the board + the company map."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import ats, sources, build_board


def test_source_job_reaches_board_and_map(monkeypatch):
    # no ATS network in the sandbox: every registry company returns nothing
    monkeypatch.setattr(ats, "fetch_company", lambda e: ([], None))
    fake = {
        "company": "Nicoya", "title": "Embedded Firmware Engineer",
        "location": "Kitchener, ON, Canada", "url": "https://ex/1", "posted": None,
        "description": "altium stm32 firmware embedded hardware", "salary": "$120,000 CAD/year",
        "source": "getro:MaRS", "arrangement": "hybrid",
        "lat": 43.45, "lng": -80.49, "industry": "Medical Device",
    }
    monkeypatch.setattr(sources, "load_sources",
                        lambda: [{"platform": "getro", "name": "MaRS", "network_id": 383}])
    monkeypatch.setattr(sources, "fetch_source", lambda e: ([fake], None))

    payload = build_board.build(demo=False, min_score=0)
    rows = payload["matches"] + payload["below"]
    row = next((r for r in rows if r["company"] == "Nicoya"), None)
    assert row is not None                      # source job is on the board
    assert row["arrangement"] == "hybrid"       # source enrichment used, not heuristic
    assert row["lat"] == 43.45                  # source coords used

    disc = next((c for c in payload["companies"] if c["name"] == "Nicoya"), None)
    assert disc is not None and disc.get("discovered")   # placed on the map
    assert disc["status"] in ("fit", "open")
