"""JB-42: run history, regression alarm, compare_runs, sweep recall parsing."""
import os, sys, json
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import history, compare_runs, sweep_recall

PAY = {"generated": "t2", "mode": "live", "counts": {"matches": 14, "below": 151, "errors": 0, "unresolved": 27},
       "discovery": {"count": 130}, "run_seconds": 81.2,
       "source_funnel": {"workday": {"kept": 33}, "greenhouse": {"kept": 43}},
       "matches": [{"company": "A"}], "below": [{"company": "A"}, {"company": "B"}]}


def test_summarize():
    e = history.summarize(PAY)
    assert e["kept"] == 165 and e["matches"] == 14 and e["discovered"] == 130
    assert e["kept_by_source"] == {"greenhouse": 43, "workday": 33} and e["companies_with_roles"] == 2


def test_healthy_run_has_no_alerts():
    e = history.summarize(PAY)
    assert history.check_regression(e, dict(e, kept=150)) == []          # -9%: fine
    assert history.check_regression(None, e) == []                       # first run


def test_big_drop_and_dead_source_alert():
    prev = history.summarize(PAY)
    cur = dict(prev, kept=90, errors=5, kept_by_source={"greenhouse": 43, "workday": 0})
    alerts = " | ".join(history.check_regression(prev, cur))
    assert "roles kept fell 165 -> 90" in alerts and "fetch errors rose 0 -> 5" in alerts
    assert "'workday' went from 33" in alerts


def test_record_appends_to_previous_and_writes_file(tmp_path):
    old = [dict(history.summarize(PAY), generated="t1", kept=300)]
    alerts = history.record(PAY, str(tmp_path), live=True, fetch=lambda url: old)
    h = json.load(open(tmp_path / "history.json"))
    assert [x["generated"] for x in h] == ["t1", "t2"] and any("roles kept fell" in a for a in alerts)


def test_record_offline_first_run(tmp_path):
    def boom(url): raise OSError("offline")
    assert history.record(PAY, str(tmp_path), live=True, fetch=boom) == []
    assert len(json.load(open(tmp_path / "history.json"))) == 1


def test_compare_runs_diff_rows():
    a, b = history.summarize(PAY), dict(history.summarize(PAY), kept=170, kept_by_source={"greenhouse": 45, "workday": 33})
    rows = {r[0]: r for r in compare_runs.diff(a, b)}
    assert rows["kept"][3] == 5 and rows["  kept: greenhouse"][3] == 2


LOG = """# Daily Sweep Log
## 2026-09-21 (automated) - haul
### Fresh 7+ this run (all net-new)
- **Corvita Biomedical \u2014 Firmware Engineer AND Electrical Engineer** (Toronto) \u2014 ~8
- **Zebra Technologies \u2014 Electrical Engineering Advanced** (Mississauga) \u2014 ~7
### Fresh net-new \u2014 captured (sub-7)
- **Clarius Mobile Health \u2014 Embedded Firmware Engineer** (Vancouver)
## 2026-09-18 (automated)
### Fresh 7+ this run
- **Semtech \u2014 Senior PCB Design Engineer** (Burlington) \u2014 ~7.5
## 2026-09-17 old
### Fresh 7+ this run
- **Old Co \u2014 Hardware Engineer**
"""


def test_parse_log_reads_only_fresh_7plus_of_recent_runs():
    roles = sweep_recall.parse_log(LOG, runs=2)
    assert [(r["company"], r["title"]) for r in roles] == [
        ("Corvita Biomedical", "Firmware Engineer"), ("Corvita Biomedical", "Electrical Engineer"),
        ("Zebra Technologies", "Electrical Engineering Advanced"), ("Semtech", "Senior PCB Design Engineer")]


def test_found_matches_company_and_title_words():
    jobs = [{"company": "Zebra Technologies Corp", "title": "Electrical Engineering, Advanced"},
            {"company": "Semtech", "title": "Marketing Manager"}]
    assert sweep_recall.found({"company": "Zebra Technologies", "title": "Electrical Engineering Advanced"}, jobs)
    assert sweep_recall.found({"company": "Semtech", "title": "Senior PCB Design Engineer"}, jobs) is None
