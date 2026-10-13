"""JB-89: facets.country on real location strings from the live board (jobs.json 2026-10-09)
and the promotion run (2026-10-12)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import facets  # noqa: E402

FIXED = [
    # accents
    ("Montréal, Québec", "Canada"),
    ("Montréal, Quebec", "Canada"),
    # full province / state names
    ("Saskatchewan", "Canada"),
    ("Bedford, Nova Scotia", "Canada"),
    ("Lincolnshire, Illinois", "US"),
    ("Colorado", "US"),
    # 2-letter codes after a comma (JB-81 regexes, now reached)
    ("Washington, DC", "US"),
    ("New Haven, CT, US", "US"),
    ("Etobicoke, ON", "Canada"),
    # ISO-3 codes in their clear forms
    ("Maidenhead (GBR)", "UK"),
    ("GBR - Bristol", "UK"),
    ("GBR -Stansted", "UK"),
    ("CHE - Neuchatel", "Switzerland"),
    ("THA - Bangkok, Thailand", "TH"),
    ("KOHO (CAN)", "Canada"),
    # "<province>, CA" is Canada
    ("ON, CA", "Canada"),
    ("Toronto, ON, CA", "Canada"),
]

UNCHANGED = [
    ("London, ON", "Canada"),
    ("London, UK", "UK"),
    ("Toronto, Ontario, Canada", "Canada"),
    ("Remote", "Canada"),            # registry is Canada-first (existing rule)
    ("San Francisco, CA", "US"),     # CA after a city = California
    ("2 Locations", "?"),
    ("n/a", "?"),
    ("CA", "?"),                     # bare CA stays ambiguous
    ("Bangalore, India", "India"),
]


@pytest.mark.parametrize("loc,want", FIXED)
def test_fixed(loc, want):
    assert facets.country(loc) == want


@pytest.mark.parametrize("loc,want", UNCHANGED)
def test_unchanged(loc, want):
    assert facets.country(loc) == want


def test_prose_words_are_not_states():
    # whole-word + original-case codes only: "Indiana Jones" is a joke, "in" / "or" are words
    assert facets.country("Hybrid or remote in office") == "Canada"   # "remote" rule, not Oregon/Indiana


def test_london_uk_still_plots_in_london_not_the_uk_centroid():
    import geo
    for loc in ("London, UK", "London, England", "London, United Kingdom"):
        lat, lng, prec = geo.locate(loc)
        assert prec == "city" and abs(lat - 51.5074) < 0.01 and abs(lng + 0.1278) < 0.01, loc
    lat, lng, _ = geo.locate("London, ON")
    assert abs(lat - 42.98) < 0.01
    assert geo.locate("London")[0] is None or abs(geo.locate("London")[0] - 42.98) > 5  # bare London: not London ON
