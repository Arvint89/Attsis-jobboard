"""JB-82 feedback + usage events. See docs/design/DESIGN_jb82_feedback.md."""
import os

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_track_is_guarded_noop():
    h = _html()
    assert "function track(path,title)" in h
    assert "window.goatcounter&&typeof window.goatcounter.count==='function'" in h


def test_events_wired():
    h = _html()
    for ev in ("setup/profile", "setup/quickstart", "map/used", "'click/'+slug(j.company)", "'vote/'+(v>0?'up':'down')"):
        assert ev in h, ev


def test_votes_in_card_body_and_persisted():
    h = _html()
    assert "${voteRow(j)}" in h and "jobboard_votes" in h


def test_report_link_in_footer():
    h = _html()
    assert 'id="reportLink"' in h and "issues/new?labels=type%3Abug" in h


def test_no_cv_data_in_events():
    h = _html()
    # events carry company slugs only — never profile fields
    assert "track('vote/'" in h
    for bad in ("track(PROFILE", "track(JSON.stringify(PROFILE", "track($('#cvText')"):
        assert bad not in h
