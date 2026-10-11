"""JB-77 profile v2 (#190). See docs/design/DESIGN_jb77_profile.md."""
import os

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_profile_header_and_two_columns():
    h = _html()
    assert "What should we match you on?" in h
    assert 'class="profgrid"' in h and 'class="profleft"' in h and 'class="profright"' in h


def test_linkedin_pdf_source_feeds_extraction():
    h = _html()
    assert 'id="liFile"' in h and 'id="liText"' in h
    assert "hookFile($('#liFile'),$('#liText'))" in h
    assert "$('#liText').value" in h  # read during Analyze


def test_no_profile_shows_sources_and_editor():
    h = _html()
    assert "quick.style.display=''; saved.style.display='none'; upload.style.display='block'; review.style.display='block';" in h
    assert "#reviewPanel.noid .row .fld{display:none}" in h  # no duplicate name/home before a CV is read


def test_save_button_counts_roles():
    assert "Save and re-rank " in _html()


def test_welcome_heading_kept_for_brand_test():
    assert "Welcome to Attsis Job Board" in _html()
