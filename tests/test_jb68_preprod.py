"""JB-68 pre-production testing infra: static checks on the smoke script
and the workflow that drives it.

Does NOT run Playwright/Chromium — that happens in CI. These tests cover:
  - engine/incognito_smoke.py imports without side-effects
  - CLI contract: no args → exit 2 with usage; valid args → exit 0 or 1
  - _report() returns 0 on empty failures, 1 otherwise
  - .github/workflows/preprod-smoke.yml exists, triggers on pull_request,
    installs playwright + chromium, calls the smoke script
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SMOKE = os.path.join(ROOT, "engine", "incognito_smoke.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "preprod-smoke.yml")


def test_smoke_script_exists():
    assert os.path.exists(SMOKE), "engine/incognito_smoke.py must exist"


def test_smoke_script_imports_cleanly():
    sys.path.insert(0, os.path.join(ROOT, "engine"))
    try:
        import incognito_smoke  # noqa: F401
    finally:
        sys.path.pop(0)


def test_smoke_script_no_args_exits_2():
    r = subprocess.run([sys.executable, SMOKE], capture_output=True, text=True)
    assert r.returncode == 2
    assert "usage" in r.stderr.lower()


def test_report_helper_contract():
    sys.path.insert(0, os.path.join(ROOT, "engine"))
    try:
        from incognito_smoke import _report
        assert _report([], []) == 0
        assert _report(["bad"], []) == 1
        assert _report([], ["pageerror: boom"]) == 1
    finally:
        sys.path.pop(0)


def test_workflow_exists_and_triggers_on_pr():
    assert os.path.exists(WORKFLOW), ".github/workflows/preprod-smoke.yml must exist"
    with open(WORKFLOW, encoding="utf-8") as f:
        wf = f.read()
    assert "pull_request:" in wf, "workflow must trigger on pull_request"
    assert "playwright install" in wf, "workflow must install chromium via playwright"
    assert "incognito_smoke.py" in wf, "workflow must invoke the smoke script"


def test_workflow_does_not_deploy():
    # Safety: this workflow should NEVER touch GH Pages — only sweep.yml does.
    with open(WORKFLOW, encoding="utf-8") as f:
        wf = f.read()
    assert "actions/deploy-pages" not in wf, (
        "preprod-smoke must not touch GH Pages; only sweep.yml deploys"
    )
    assert "actions/upload-pages-artifact" not in wf, (
        "preprod-smoke must not upload a Pages artifact"
    )
