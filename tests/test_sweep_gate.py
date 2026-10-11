"""JB-83 sweep health gate (tools/sweep_gate.py)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import sweep_gate  # noqa: E402

WF = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "sweep.yml")


def _write(tmp_path, alerts, mode="live"):
    p = tmp_path / "jobs.json"
    p.write_text(json.dumps({"mode": mode, "alerts": alerts}), encoding="utf-8")
    return str(p)


def test_classify_severe_vs_other():
    sev, oth = sweep_gate.classify(["roles kept fell 1763 -> 900 (>30%)", "fetch errors rose 4 -> 9",
                                    "companies with roles fell 191 -> 80 (>30%)", "source 'x' went from 12 kept roles to 0"])
    assert len(sev) == 2 and len(oth) == 2


def test_block_severe_fails_and_allow_overrides(tmp_path, monkeypatch):
    f = _write(tmp_path, ["roles kept fell 1763 -> 900 (>30%)"])
    monkeypatch.delenv("ALLOW_REGRESSION", raising=False)
    assert sweep_gate.main([f, "--block-severe"]) == 1
    monkeypatch.setenv("ALLOW_REGRESSION", "true")
    assert sweep_gate.main([f, "--block-severe"]) == 0


def test_minor_alerts_deploy_but_report_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("ALLOW_REGRESSION", raising=False)
    f = _write(tmp_path, ["fetch errors rose 4 -> 9"])
    assert sweep_gate.main([f, "--block-severe"]) == 0
    assert sweep_gate.main([f, "--report"]) == 1


def test_healthy_and_demo_pass(tmp_path):
    assert sweep_gate.main([_write(tmp_path, []), "--report"]) == 0
    assert sweep_gate.main([_write(tmp_path, ["roles kept fell 9 -> 1"], mode="demo"), "--block-severe"]) == 0


def test_summary_written(tmp_path, monkeypatch):
    s = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(s))
    sweep_gate.main([_write(tmp_path, ["fetch errors rose 4 -> 9"]), "--report"])
    assert "fetch errors rose" in s.read_text(encoding="utf-8")


def test_workflow_wires_gate_before_deploy_and_report_after():
    wf = open(WF, encoding="utf-8").read()
    gate, upload, report = (wf.index("--block-severe"), wf.index("upload-pages-artifact"), wf.index("--report"))
    assert gate < upload < report
    assert "allow_regression" in wf
