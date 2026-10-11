"""JB-81 map Phase B (DESIGN_map_v2 §7): place more roles on the map.

Facts behind each case (✅ live jobs.json 2026-10-09): 522 / 1,763 roles had no
coordinates; top misses included "London, Ontario or Remote", "Remote or
Mississauga", "Ann Arbor, MI", "Katowice, Poland", "Singapore, Singapore",
"TWN - Taipei - Taipei", and home_coords was null for home "London".
Rings/remote semantics are unchanged; only coordinates change."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import geo  # noqa: E402


def _city(loc):
    lat, lng, prec = geo.locate(loc)
    return lat is not None and prec == "city"


def test_remote_with_a_named_city_gets_that_city():
    for loc in ["London, Ontario or Remote", "Remote or Mississauga", "Canada - Toronto, Remote",
                "Remote - US, Ann Arbor, MI"]:
        assert _city(loc), loc


def test_pure_remote_and_vague_stay_unplaced():
    for loc in ["Remote", "Remote (Canada)", "Remote - United States", "n/a", "2 Locations", "Canada"]:
        assert geo.coords_of(loc) == (None, None), loc


def test_new_cities():
    for loc in ["Ann Arbor, MI", "Detroit, MI", "Atlanta, Georgia", "Dallas, TX", "Katowice, Poland",
                "Singapore, Singapore", "TWN - Taipei - Taipei", "Malaysia - Kuala Lumpur",
                "Shanghai, Shanghai, cn", "Fayetteville, AR", "Barrie, ON", "Windsor, Ontario",
                "Ottawa, ON", "Winnipeg, MB"]:
        assert _city(loc), loc


def test_unknown_us_city_with_state_code_gets_us_centroid():
    lat, lng, prec = geo.locate("Boise, ID")
    assert prec == "country" and (lat, lng) == geo._COUNTRY_CENTROID["us"]


def test_ontario_code_is_not_a_us_state():
    lat, lng, prec = geo.locate("Kitchener, ON")
    assert prec == "city" and abs(lat - 43.45) < 0.1


def test_bare_london_still_ambiguous_for_jobs_but_home_resolves():
    assert geo.coords_of("London") == (None, None)       # job side: JB-56 unchanged
    lat, lng = geo.home_coords("London")
    assert abs(lat - 42.98) < 0.05 and abs(lng + 81.25) < 0.05


def test_rings_unchanged_for_remote():
    ring, km, remote = geo.ring_for("London", "Remote or Mississauga")
    assert ring == 1 and remote
