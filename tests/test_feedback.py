"""ADR-009 back channel: payload parse/validate, dedupe, 48h suppress window, ingest (JB-93)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import feedback as fb

ROOT = os.path.join(os.path.dirname(__file__), "..")


def block(p):
    return "Human text\n\n```attsis-feedback\n" + json.dumps(p) + "\n```\n"


def rpt(reason="link_404", url="https://jobs.acme.com/1", **kw):
    p = {"v": 1, "kind": "report", "reason": reason, "url": url, "company": "Acme",
         "title": "Firmware Engineer", "ts": "2026-10-19T03:00:00Z"}
    p.update(kw)
    return p


def issue(n, author, created, p):
    return {"number": n, "author": {"login": author}, "createdAt": created, "body": block(p)}


# --- parse + validate -------------------------------------------------------------
def test_parse_body_reads_only_the_block():
    assert fb.parse_body(block(rpt())) == [rpt()]
    assert fb.parse_body("no block here") == []
    assert fb.parse_body("```attsis-feedback\n{not json}\n```") == []


@pytest.mark.parametrize("reason", sorted(fb.REASONS))
def test_every_reason_code_validates(reason):
    clean, err = fb.validate(rpt(reason))
    assert clean and not err


@pytest.mark.parametrize("bad,why", [
    (rpt(reason="nope"), "reason"),
    (rpt(url="javascript:alert(1)"), "url"),
    ({**rpt(), "v": 2}, "version"),
    ({**rpt(), "kind": "spam"}, "kind"),
    ({k: v for k, v in rpt().items() if k != "company"}, "company"),
])
def test_invalid_payloads_are_rejected(bad, why):
    clean, err = fb.validate(bad)
    assert clean is None and why in err


def test_validate_allow_lists_keys_and_caps_note():
    clean, _ = fb.validate(rpt(note="x" * 900, skills=["secret"], cv="my whole cv"))
    assert "skills" not in clean and "cv" not in clean
    assert len(clean["note"]) == 500


def test_report_without_url_needs_a_job_key():
    assert fb.validate(rpt(url=""))[0] is None
    assert fb.validate(rpt(url="", job="acme::fw::toronto"))[0] is not None


# --- ingest, dedupe, suppress -------------------------------------------------------
def test_ingest_attaches_issue_and_author_and_skips_invalid():
    recs = fb.ingest([issue(1, "a", "2026-10-19T01:00:00Z", rpt()),
                      issue(2, "b", "2026-10-19T01:00:00Z", rpt(reason="bad"))])
    assert len(recs) == 1 and recs[0]["issue"] == 1 and recs[0]["author"] == "a"
    assert recs[0]["created"] == "2026-10-19T01:00:00Z"


def test_dedupe_one_per_author_kind_target_reason():
    recs = fb.ingest([issue(1, "a", "2026-10-19T01:00:00Z", rpt()),
                      issue(2, "a", "2026-10-19T02:00:00Z", rpt()),
                      issue(3, "a", "2026-10-19T02:00:00Z", rpt(reason="already_closed"))])
    assert len(fb.dedupe(recs)) == 2


def test_suppress_needs_three_distinct_authors_within_48h():
    u = "https://jobs.acme.com/1"
    recs = fb.ingest([issue(1, "a", "2026-10-17T00:00:00Z", rpt(url=u)),
                      issue(2, "b", "2026-10-18T00:00:00Z", rpt(url=u)),
                      issue(3, "b", "2026-10-18T05:00:00Z", rpt(url=u)),     # same author: no count
                      issue(4, "c", "2026-10-18T23:00:00Z", rpt(url=u))])
    cands = fb.suppress_candidates(recs)
    assert [c["url"] for c in cands] == [u] and cands[0]["authors"] == 3


def test_suppress_window_excludes_reports_more_than_48h_apart():
    u = "https://jobs.acme.com/1"
    recs = fb.ingest([issue(1, "a", "2026-10-10T00:00:00Z", rpt(url=u)),
                      issue(2, "b", "2026-10-18T00:00:00Z", rpt(url=u)),
                      issue(3, "c", "2026-10-18T10:00:00Z", rpt(url=u))])
    assert fb.suppress_candidates(recs) == []


def test_suppress_counts_only_link_404():
    u = "https://jobs.acme.com/1"
    recs = fb.ingest([issue(i, a, "2026-10-18T00:00:00Z", rpt(reason="wrong_location", url=u))
                      for i, a in enumerate("abc")])
    assert fb.suppress_candidates(recs) == []


def test_reports_week_md_lists_top_urls_and_reasons():
    recs = fb.ingest([issue(1, "a", "2026-10-18T00:00:00Z", rpt()),
                      issue(2, "b", "2026-10-18T00:00:00Z", rpt(reason="already_closed"))])
    md = fb.reports_week_md(recs, today="2026-10-19")
    assert md.startswith("# Job reports") and "link_404" in md and "Acme" in md and "#1" in md


# --- tool + build hook ----------------------------------------------------------------
def test_ingest_tool_writes_jsonl_rollup_and_candidates(tmp_path):
    src = tmp_path / "issues.json"
    src.write_text(json.dumps([issue(1, "a", "2026-10-18T00:00:00Z", rpt()),
                               issue(2, "b", "2026-10-19T00:00:00Z", rpt())]), encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "feedback_ingest.py"),
                        "--issues", str(src), "--out", str(out), "--today", "2026-10-19"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    lines = (out / "reports" / "2026-10-18.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["reason"] == "link_404"
    assert (out / "REPORTS_WEEK.md").exists()
    assert json.loads((out / "suppress_candidates.json").read_text(encoding="utf-8")) == []


def test_build_board_drops_suppressed_urls(tmp_path, monkeypatch):
    import build_board as bb
    f = tmp_path / "suppressed.json"
    f.write_text(json.dumps({"urls": ["https://x/1"]}), encoding="utf-8")
    monkeypatch.setattr(bb, "SUPPRESSED_PATH", str(f))
    jobs = [{"url": "https://x/1", "title": "a"}, {"url": "https://x/2", "title": "b"}]
    assert [j["url"] for j in bb.drop_suppressed(jobs)] == ["https://x/2"]


def test_build_board_tolerates_missing_suppressed_file(tmp_path, monkeypatch):
    import build_board as bb
    monkeypatch.setattr(bb, "SUPPRESSED_PATH", str(tmp_path / "none.json"))
    assert len(bb.drop_suppressed([{"url": "u"}])) == 1


def test_feedback_outputs_are_gitignored():
    gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    assert "data/reports/" in gi and "data/feedback/" in gi
