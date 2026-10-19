"""JB-94 feedback inbox (ADR-009): company / feedback / votes kinds, weekly FEEDBACK_WEEK rollup,
browser builders round-tripped through engine/feedback.py."""
import json, os, re, shutil, subprocess, sys
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import feedback as fb

ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX = os.path.join(ROOT, "site", "index.html")
TS = "2026-10-19T03:00:00Z"


def block(*ps):
    return "text\n" + "".join("```attsis-feedback\n" + json.dumps(p) + "\n```\n" for p in ps)


def issue(n, author, created, *ps):
    return {"number": n, "author": {"login": author}, "createdAt": created, "body": block(*ps)}


def company(name="Vital Bio", **kw):
    return {"v": 1, "kind": "company", "name": name, "ts": TS, **kw}


def feedback(text="Map is great", **kw):
    return {"v": 1, "kind": "feedback", "text": text, "ts": TS, **kw}


def votes(*vs):
    return {"v": 1, "kind": "votes", "ts": TS, "votes": list(vs)}


# --- validate ---------------------------------------------------------------------
def test_company_valid_and_optional_fields():
    c, err = fb.validate(company(careers_url="https://vital.bio/careers", city="Toronto", seen_days=3))
    assert not err and c["careers_url"].startswith("https://") and c["seen_days"] == 3


@pytest.mark.parametrize("bad,why", [
    (company(name=""), "name"),
    (company(careers_url="javascript:x"), "url"),
    (company(seen_days=999), "seen_days"),
    (company(seen_days="soon"), "seen_days"),
])
def test_company_invalid(bad, why):
    c, err = fb.validate(bad)
    assert c is None and why in err


def test_feedback_text_required_area_allowlisted_and_capped():
    assert fb.validate(feedback(text=""))[0] is None
    c, _ = fb.validate(feedback(text="x" * 3000, area="map", email="me@x.com"))
    assert len(c["text"]) == 1000 and c["area"] == "map" and "email" not in c
    assert "area" not in fb.validate(feedback(area="nonsense"))[0]


def test_votes_validated_per_item_and_capped():
    good = {"company": "Acme", "url": "https://a/1", "v": 1}
    c, err = fb.validate(votes(good, {"company": "B", "url": "javascript:1", "v": 1},
                               {"company": "C", "url": "https://c", "v": 5}, *[good] * 60))
    assert not err and len(c["votes"]) == fb.MAX_VOTES
    assert all(x["v"] in (1, -1) and x["url"].startswith("https://") for x in c["votes"])
    assert fb.validate(votes())[0] is None


# --- rollup -----------------------------------------------------------------------
def test_feedback_week_md_sections():
    issues = [
        issue(1, "a", "2026-10-18T00:00:00Z", company("Vital Bio", careers_url="https://vital.bio/careers")),
        issue(2, "b", "2026-10-18T00:00:00Z", company("vital bio inc.")),
        issue(3, "c", "2026-10-18T00:00:00Z", company("ZTR Control Systems")),
        issue(4, "a", "2026-10-18T00:00:00Z", feedback("map pins overlap", area="map")),
        issue(5, "a", "2026-10-18T00:00:00Z", votes({"company": "Acme", "url": "https://a/1", "v": -1})),
        issue(6, "b", "2026-10-18T00:00:00Z", votes({"company": "Acme", "url": "https://a/1", "v": -1},
                                                    {"company": "Beta", "url": "https://b/1", "v": 1})),
    ]
    md = fb.feedback_week_md(fb.ingest(issues), today="2026-10-19",
                             known=["ZTR Control Systems"])
    assert md.startswith("# Feedback")
    sec = md.split("## Missing-company suggestions")[1].split("##")[0]
    assert "Vital Bio" in sec and "| 2 |" in sec           # two people, names canonicalised
    assert "already tracked" in sec                          # ZTR is in the registry
    assert '"platform": "resolve"' in md                     # companies.json seed snippet
    assert "map pins overlap" in md
    worst = md.split("## Thumbs")[1]
    assert worst.index("https://a/1") < worst.index("https://b/1")


def test_a_later_vote_by_the_same_person_wins():
    issues = [issue(1, "a", "2026-10-18T00:00:00Z", votes({"company": "A", "url": "https://a/1", "v": -1})),
              issue(2, "a", "2026-10-18T05:00:00Z", votes({"company": "A", "url": "https://a/1", "v": 1}))]
    t = fb.vote_tally(fb.ingest(issues))
    assert t["https://a/1"]["up"] == 1 and t["https://a/1"]["down"] == 0


def test_ingest_tool_writes_feedback_jsonl_and_rollup(tmp_path):
    src = tmp_path / "i.json"
    src.write_text(json.dumps([issue(1, "a", "2026-10-18T00:00:00Z", feedback())]), encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "feedback_ingest.py"),
                        "--issues", str(src), "--out", str(tmp_path), "--today", "2026-10-19"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "feedback" / "2026-10-18.jsonl").exists()
    assert "Map is great" in (tmp_path / "FEEDBACK_WEEK.md").read_text(encoding="utf-8")


# --- browser -----------------------------------------------------------------------
def _html():
    return open(INDEX, encoding="utf-8").read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* FEEDBACK-PURE-BEGIN \*/(.*?)/\* FEEDBACK-PURE-END \*/", _html(), re.S)
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def _round_trip(js_payload, js_title, js_human):
    url = _node(f"const p={js_payload};console.log(fbIssueUrl({js_title},{js_human},p))")
    q = parse_qs(urlparse(url).query)
    ps = fb.parse_body(q["body"][0])
    assert len(ps) == 1
    clean, err = fb.validate(ps[0])
    assert clean and not err, err
    return clean


def test_company_payload_round_trips():
    c = _round_trip("companyPayload({name:'Vital Bio',careers_url:'https://vital.bio/careers',city:'Toronto',seen_days:'3'},'t')",
                    "'x'", "'y'")
    assert c["name"] == "Vital Bio" and c["seen_days"] == 3


def test_company_payload_rejects_blank_name():
    assert _node("console.log(JSON.stringify(companyPayload({name:'  '},'t')))") == "null"


def test_feedback_payload_round_trips():
    c = _round_trip("feedbackPayload('love the map','map','t')", "'x'", "'y'")
    assert c["text"] == "love the map" and c["area"] == "map"


def test_votes_payload_round_trips_and_caps():
    c = _round_trip("votesPayload(Array.from({length:60},(_, i)=>({company:'A'+i,url:'https://a/'+i,v:i%2?1:-1})),'t')",
                    "'x'", "'y'")
    assert len(c["votes"]) == fb.MAX_VOTES


def test_footer_entry_points_and_dialog_kinds():
    h = _html()
    for needle in ('id="feedbackLink"', 'id="suggestLink"', 'id="votesLink"',
                   "FB_BUILD", "company(ctx", "feedback(ctx", "votes(ctx"):
        assert needle in h, needle
    ui = h[h.index("/* FEEDBACK-UI-BEGIN */"):h.index("/* FEEDBACK-UI-END */")]
    assert "PROFILE" not in ui and "fetch(" not in ui
