"""JB-93 per-job report (ADR-009): card button, dialog, payload builder, outbox.

The FEEDBACK-PURE block is run in node; the issue URL it builds is decoded and parsed
back with engine/feedback.py, so browser and ingest can't drift apart.
"""
import json, os, re, shutil, subprocess, sys
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import feedback as fb

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")
JOB = {"url": "https://jobs.acme.com/1", "company": "Acme", "title": "Firmware Engineer",
       "location": "Toronto", "text": "secret jd", "score": 8}


def _html():
    return open(INDEX, encoding="utf-8").read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* FEEDBACK-PURE-BEGIN \*/(.*?)/\* FEEDBACK-PURE-END \*/", _html(), re.S)
    assert m, "FEEDBACK-PURE block missing"
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_reason_codes_match_python():
    got = json.loads(_node("console.log(JSON.stringify(Object.keys(FB_REASONS)))"))
    assert set(got) == fb.REASONS


def test_browser_url_round_trips_through_ingest():
    url = _node(f"const j={json.dumps(JOB)};"
                "const p=reportPayload(j,'link_404','dead link','2026-10-19T03:00:00Z');"
                "console.log(fbIssueUrl(reportTitle(j,'link_404'),reportHuman(j,'link_404','dead link'),p))")
    u = urlparse(url)
    assert u.netloc == "github.com" and u.path == "/Arvint89/Attsis-jobboard/issues/new"
    q = parse_qs(u.query)
    assert "Acme" in q["title"][0]
    payloads = fb.parse_body(q["body"][0])
    assert len(payloads) == 1
    clean, err = fb.validate(payloads[0])
    assert clean and not err and clean["reason"] == "link_404" and clean["note"] == "dead link"


def test_payload_never_carries_job_text_or_profile():
    p = json.loads(_node(f"console.log(JSON.stringify(reportPayload({json.dumps(JOB)},'other','n','t')))"))
    assert set(p) <= fb.KEYS["report"] | {"v", "kind", "ts"}
    assert "secret jd" not in json.dumps(p)


def test_unknown_reason_gives_null():
    assert _node(f"console.log(JSON.stringify(reportPayload({json.dumps(JOB)},'bogus','','t')))") == "null"


def test_issue_url_stays_under_github_limit():
    big = "é" * 500
    n = _node(f"const j={json.dumps({**JOB, 'title': 'T' * 400})};"
              f"const p=reportPayload(j,'other',{json.dumps(big)},'t');"
              f"console.log(fbIssueUrl(reportTitle(j,'other'),reportHuman(j,'other',{json.dumps(big)}),p).length)")
    assert int(n) <= 7500


def test_outbox_records_and_caps():
    out = _node("let ob=[];for(let i=0;i<60;i++) ob=outboxAdd(ob,{id:'r'+i,kind:'report'},'t');"
                "console.log(ob.length, ob[0].id, outboxHas(ob,'r59'), outboxHas(ob,'r0'))")
    assert out == "50 r10 true false"


def test_card_has_report_button_and_dialog_exists():
    h = _html()
    assert "${reportRow(j)}" in h
    assert '<dialog id="fbDialog"' in h
    assert "jobboard_outbox" in h
    # public-issue warning shown next to the send button
    assert "public GitHub issue" in h


def test_send_is_a_user_clicked_link_not_a_fetch():
    h = _html()
    body = h[h.index("/* FEEDBACK-UI-BEGIN */"):h.index("/* FEEDBACK-UI-END */")]
    assert "fetch(" not in body and "XMLHttpRequest" not in body
    assert "PROFILE" not in body
    assert 'id="fbSend"' in h and 'target="_blank"' in h[h.index('id="fbSend"') - 200:h.index('id="fbSend"') + 200]
