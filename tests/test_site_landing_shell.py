"""JB-74 landing + shell (#187). See docs/design/DESIGN_jb74_landing_shell.md."""
import os
import re

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_no_name_gate_on_first_visit():
    h = _html()
    assert "Enter your name first." not in h
    assert "if(PROFILE)showBoard(); else showSetup();" not in h


def test_hero_with_live_stats_and_profile_card():
    h = _html()
    for i in ("hero", "heroStats", "heroCv", "heroCover", "heroLinkedin"):
        assert f'id="{i}"' in h, i
    assert "straight from employers" in h


def test_nav_buttons_have_icons_and_tracker_count():
    h = _html()
    tabs = re.search(r'<div class="tabbar" id="topTabs".*?</div>', h, re.S).group(0)
    assert tabs.count("<svg") >= 5
    assert 'id="tabTrackerCount"' in h
    assert 'id="ctaProfile"' in h


def test_footer_matches_prototype():
    h = _html()
    assert "A GLOBAL ATTSIS PRODUCT" in h and "SCORED IN YOUR BROWSER" in h
    assert 'id="foot"' in h  # tenant footer_html still appends here


def test_profile_tab_renders_saved_profile():
    assert "if(name==='profile') renderSavedProfile();" in _html()


def test_below_roles_refresh_without_profile():
    # jobs_below.json arrives after first paint; it must reach visitors with no saved profile
    h = _html()
    assert "if(PROFILE){rescore(); if($('#boardView').style.display==='block')renderBoard();}" not in h
    assert "rescore(); if($('#boardView').style.display!=='none'){ renderBoard(); renderHero();" in h
