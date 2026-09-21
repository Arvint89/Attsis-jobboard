"""JB-5 / JB-38b: follow aggregator apply links to the company's own ATS.

A Getro job whose url is a supported ATS (e.g. jobs.lever.co/kepler/...) promotes that company:
its whole ATS board is fetched once (full descriptions, every role), and the Getro stubs for it
are dropped. Unsupported / failing -> keep the stubs. Companies already in the registry are not
fetched twice.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import build_board


def stub(company, url, board="MaRS"):
    return {"company": company, "title": "x", "location": "Toronto, ON", "url": url,
            "description": "", "source": f"getro:{board}"}


def test_promotes_supported_ats_and_drops_its_stubs():
    calls = []
    def fake_fetch(entry):
        calls.append((entry["platform"], entry["slug"], entry["name"]))
        return ([{"company": entry["name"], "title": t, "location": "Toronto", "url": "u" + t,
                  "description": "full JD", "source": "lever"} for t in ("A", "B", "C")], None)
    jobs, info = build_board.enrich_via_ats(
        [stub("Kepler Communications", "https://jobs.lever.co/kepler/b9df"),
         stub("Kepler Communications", "https://jobs.lever.co/kepler/2ad0"),
         stub("KPMG Canada", "https://careers.kpmg.ca/jobs/33419", "Communitech")],
        known=set(), fetch=fake_fetch)
    assert calls == [("lever", "kepler", "Kepler Communications")]          # fetched once
    titles = sorted(j["title"] for j in jobs)
    assert titles == ["A", "B", "C", "x"]                                    # 3 from Lever + KPMG stub
    lever = [j for j in jobs if j["title"] in "ABC"]
    assert all(j["source"] == "lever (via MaRS)" for j in lever)
    assert info["discovered"] == ["Kepler Communications"] and info["enriched"] == 2


def test_failed_fetch_keeps_the_stubs():
    jobs, info = build_board.enrich_via_ats(
        [stub("Gatik", "https://boards.greenhouse.io/gatikaiinc/jobs/47")],
        known=set(), fetch=lambda e: ([], "HTTPError: 404"))
    assert [j["company"] for j in jobs] == ["Gatik"] and jobs[0]["source"] == "getro:MaRS"
    assert info["errors"] and info["discovered"] == []


def test_registry_company_is_not_refetched_and_stub_dropped():
    called = []
    jobs, info = build_board.enrich_via_ats(
        [stub("Kepler Communications", "https://jobs.lever.co/kepler/b9df")],
        known={("lever", "kepler")}, fetch=lambda e: called.append(e) or ([], None))
    assert called == [] and jobs == []          # registry already fetched Kepler; no duplicate


def test_cap_limits_new_companies():
    fetched = []
    def f(e):
        fetched.append(e["slug"]); return ([], None)
    stubs = [stub(f"Co{i}", f"https://jobs.lever.co/co{i}/1") for i in range(5)]
    build_board.enrich_via_ats(stubs, known=set(), fetch=f, max_new=3)
    assert len(fetched) == 3
