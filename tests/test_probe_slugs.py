"""JB-5c probe_slugs: name-derived ATS slug probing with strict validation (no network)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import probe_slugs as ps  # noqa: E402


def test_slug_candidates():
    c = ps.slug_candidates("Deep Trekker")
    assert c[0] == "deeptrekker" and "deep-trekker" in c
    assert "synaptive" in ps.slug_candidates("Synaptive Medical")          # suffix word dropped
    assert "synaptivemedical" in ps.slug_candidates("Synaptive Medical")
    assert "vitalbiosciences" in ps.slug_candidates("Vital Biosciences")
    assert "vital" not in ps.slug_candidates("Vital Biosciences")          # too generic / short alone
    assert "rangle" in ps.slug_candidates("Rangle.io")
    assert ps.slug_candidates("ecobee")[0] == "ecobee"


def test_board_name_must_match():
    assert ps.same_company("Faire", "Faire")
    assert ps.same_company("Clio", "Clio - Themis Solutions Inc.")
    assert ps.same_company("Synaptive Medical", "Synaptive Medical Inc.")
    assert not ps.same_company("League", "League of Legends Esports")
    assert not ps.same_company("Article", "Articulate")
    assert not ps.same_company("Later", "Lattice")


def test_accept_rules():
    # board-name platforms (greenhouse / smartrecruiters): the name decides
    ok = ps.accept("Faire", "greenhouse", "faire", board_name="Faire", jobs=[{"location": "Kitchener, ON"}])
    assert ok
    assert not ps.accept("League", "greenhouse", "league", board_name="League of Legends Esports",
                         jobs=[{"location": "Toronto, ON"}])
    # no board name (lever / ashby / workable / bamboohr): exact full-name slug + Canada evidence
    assert ps.accept("Klue", "lever", "klue", board_name=None, jobs=[{"location": "Vancouver, BC"}])
    assert not ps.accept("Klue", "lever", "klue", board_name=None, jobs=[{"location": "Austin, TX"}])
    assert not ps.accept("Synaptive Medical", "lever", "synaptive", board_name=None,
                         jobs=[{"location": "Toronto, ON"}])      # partial slug without a board name: too weak
    assert not ps.accept("Faire", "greenhouse", "faire", board_name="Faire", jobs=[])   # empty board
