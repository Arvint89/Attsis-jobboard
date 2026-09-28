"""Tests for tools/london_coverage.py -- London CMA coverage census (JB-57)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import london_coverage as lc  # noqa: E402


# A minimal CBC CSV fixture that exercises every filter path.
# Real CBC has ~2 dozen columns; we include just what parse_cbc_csv reads plus
# a couple of extras to prove the parser ignores unknowns.
CSV_FIXTURE = (
    'REF_DATE,GEO,Business industry,Business employment size,UOM,VALUE\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Computer systems design and related services [5415]","10-19 employees","Number","120"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Computer systems design and related services [5415]","20-49 employees","Number","70"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Computer systems design and related services [5415]","1-4 employees","Number","500"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Information and cultural industries [51]","50-99 employees","Number","40"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Aerospace product and parts manufacturing [3364]","500 or more employees","Number","3"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Agriculture, forestry, fishing and hunting [11]","10-19 employees","Number","999"\n'
    '"2026-06","Toronto, Ontario (Census metropolitan area)","Computer systems design and related services [5415]","10-19 employees","Number","5000"\n'
    '"2026-06","London, Ontario","Computer systems design and related services [5415]","10-19 employees","Number","999"\n'
    '"2026-06","London, Ontario (Census metropolitan area)","Computer systems design and related services [5415]","Total, with employees","Number","999"\n'
)


# --- naics_from_industry ------------------------------------------------------

def test_naics_extracts_bracketed_code():
    assert lc.naics_from_industry("Computer systems design [5415]") == "5415"
    assert lc.naics_from_industry("Information [51]") == "51"
    assert lc.naics_from_industry("Aerospace [3364]") == "3364"


def test_naics_ignores_hyphenated_range_and_missing():
    # Top-of-tree labels like "Manufacturing [31-33]" don't yield a leaf code.
    assert lc.naics_from_industry("Manufacturing [31-33]") == ""
    assert lc.naics_from_industry("no brackets here") == ""
    assert lc.naics_from_industry("") == ""


# --- size_lower_bound ---------------------------------------------------------

def test_size_lower_bound_known_and_unknown():
    assert lc.size_lower_bound("10-19 employees") == 10
    assert lc.size_lower_bound("500 or more employees") == 500
    assert lc.size_lower_bound("Total, with employees") == -1
    assert lc.size_lower_bound("") == -1


# --- is_london_cma ------------------------------------------------------------

def test_is_london_cma_accepts_cma_only():
    assert lc.is_london_cma("London, Ontario (Census metropolitan area)") is True
    assert lc.is_london_cma("London, census metropolitan area, Ontario") is True
    # Bare city row must be rejected -- it would double-count with CMA row.
    assert lc.is_london_cma("London, Ontario") is False
    assert lc.is_london_cma("Toronto, Ontario (Census metropolitan area)") is False


# --- parse_cbc_csv ------------------------------------------------------------

def test_parse_sums_per_naics_at_default_min_size():
    counts = lc.parse_cbc_csv(CSV_FIXTURE)
    # 5415: 120 (10-19) + 70 (20-49) = 190. The 1-4 row is dropped by min-size,
    # the Toronto row is dropped by geo, the "London, Ontario" bare-city row is
    # dropped by is_london_cma, and the "Total, with employees" row is dropped
    # because it doesn't map to a numeric bucket.
    assert counts["5415"] == 190
    assert counts["51"] == 40
    assert counts["3364"] == 3
    # NAICS 11 (agriculture) is not in the default filter -> not present.
    assert "11" not in counts
    # Codes with zero matches still appear at 0.
    assert counts["334"] == 0


def test_parse_respects_custom_min_size():
    counts = lc.parse_cbc_csv(CSV_FIXTURE, min_size=1)
    # Now the 1-4 row (500) is included.
    assert counts["5415"] == 120 + 70 + 500


def test_parse_respects_custom_naics():
    counts = lc.parse_cbc_csv(CSV_FIXTURE, naics_codes=("5415",))
    assert list(counts.keys()) == ["5415"]
    assert counts["5415"] == 190


def test_parse_empty_input():
    counts = lc.parse_cbc_csv("REF_DATE,GEO,Business industry,Business employment size,UOM,VALUE\n")
    assert all(v == 0 for v in counts.values())


# --- london_registry_count ----------------------------------------------------

def test_london_registry_count_matches_cma_cities_only():
    reg = {"companies": [
        {"name": "A", "city": "London"},
        {"name": "B", "city": "St. Thomas"},
        {"name": "C", "city": "Strathroy"},
        {"name": "D", "city": "Toronto"},
        {"name": "E", "city": ""},
        {"name": "F"},  # no city key
    ]}
    assert lc.london_registry_count(reg) == 3


# --- format_report ------------------------------------------------------------

def test_format_report_shape_and_math():
    out = lc.format_report({"5415": 190, "51": 40}, registered=5, period="2026-06", min_size=10)
    assert "London CMA coverage census" in out
    assert "2026-06" in out
    assert "size >= 10" in out
    assert "NAICS 5415" in out
    assert "denominator: " in out
    # total denominator = 190 + 40 = 230
    assert "230" in out
    # coverage 5/230 -> ~2.2%
    assert "5 / 230" in out


def test_format_report_zero_denominator_shows_na():
    out = lc.format_report({"5415": 0}, registered=0, period="2026-06", min_size=10)
    assert "n/a" in out


# --- end to end from fixture --------------------------------------------------

def test_end_to_end_against_fixture_registry(tmp_path):
    reg_path = tmp_path / "companies.json"
    reg_path.write_text(json.dumps({"companies": [
        {"name": "London Co", "city": "London"},
        {"name": "Strathroy Co", "city": "Strathroy"},
        {"name": "Faraway Co", "city": "Toronto"},
    ]}), encoding="utf-8")
    counts = lc.parse_cbc_csv(CSV_FIXTURE)
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    n = lc.london_registry_count(reg)
    out = lc.format_report(counts, n, "2026-06", 10)
    assert "registered London companies:            2" in out
