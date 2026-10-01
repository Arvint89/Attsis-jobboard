"""JB-25: geo resolves real distance by city/country, not the company's HQ ring."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import geo

HOME = "London"   # London, Ontario


def test_corridor_city_is_near():
    ring, km, remote = geo.ring_for(HOME, "Kitchener, ON, Canada")
    assert ring == 1 and km < 120 and not remote


def test_us_city_is_far():
    ring, km, _ = geo.ring_for(HOME, "Santa Clara, California, United States")
    assert ring == 4 and km > 3000            # ~4000 km, definitely far


def test_foreign_country_is_far_not_registry_ring():
    # the bug: Bengaluru used to inherit the company's Ring 2. Now it's Ring 4.
    ring, km, _ = geo.ring_for(HOME, "Bengaluru, Karnataka, India")
    assert ring == 4 and km > 10000


def test_unknown_foreign_city_uses_country_centroid():
    ring, km, _ = geo.ring_for(HOME, "Plano, Texas, United States")   # city not in table
    assert ring == 4 and km > 1000            # US centroid ~1479 km from London ON


def test_london_uk_is_not_london_ontario():
    ring, km, _ = geo.ring_for(HOME, "London, United Kingdom")
    assert ring == 4 and km > 4000            # UK, not the home city next door


def test_remote_is_ring_1():
    ring, km, remote = geo.ring_for(HOME, "Remote, Canada")
    assert ring == 1 and remote


def test_canadian_unknown_city_returns_none_for_registry_fallback():
    ring, km, _ = geo.ring_for(HOME, "Timbuktu-ville, Ontario, Canada")
    assert ring is None                        # -> build_board falls back to registry ring


def test_coords_of_returns_latlng_for_map():
    lat, lng = geo.coords_of("Kitchener, ON")
    assert lat and lng and 43 < lat < 44
    assert geo.coords_of("Bengaluru, India")[0] < 20   # southern latitude


# ---- JB-34: multi-location postings (real Tenstorrent strings) ----
TT3 = "Austin, Texas, United States; Santa Clara, California, United States; Toronto, Ontario, Canada"


def test_split_locations():
    assert geo.split_locations(TT3) == ["Austin, Texas, United States",
                                        "Santa Clara, California, United States",
                                        "Toronto, Ontario, Canada"]
    assert geo.split_locations("Toronto, ON") == ["Toronto, ON"]
    assert geo.split_locations("") == []


def test_nearest_location_picks_toronto_for_london():
    assert geo.nearest_location("London", TT3) == "Toronto, Ontario, Canada"
    assert geo.nearest_location("London", "Belgrade, Serbia; Toronto, Ontario, Canada") == "Toronto, Ontario, Canada"


def test_multi_location_ring_uses_nearest():
    ring, km, remote = geo.ring_for("London", TT3)
    single = geo.ring_for("London", "Toronto, Ontario, Canada")
    assert (ring, km, remote) == single and km < 250


def test_unplaceable_parts_fall_back_to_first():
    assert geo.nearest_location("London", "Atlantis; El Dorado") == "Atlantis"


def test_single_location_unchanged():
    assert geo.ring_for("London", "Toronto, Ontario, Canada") == geo._ring_single("London", "Toronto, Ontario, Canada")


# ---- JB-56: bare "London" is ambiguous (DeepTrekker via Halma-Workday sibling) ----

def test_bare_london_is_ambiguous():
    # Halma-tenant Workday postings say just "London" -- usually means London UK
    # (Halma HQ) but was matching London ON by default and giving ring 0 to jobs
    # that weren't in Ontario at all. Bare "London" must now return unresolved.
    lat, lng, precision = geo.locate("London")
    assert (lat, lng, precision) == (None, None, None)


def test_london_with_qualifier_still_resolves():
    ring_on, _, _ = geo.ring_for(HOME, "London, ON, Canada")
    assert ring_on == 0                        # same city as HOME
    ring_uk, km_uk, _ = geo.ring_for(HOME, "London, UK")
    assert ring_uk == 4 and km_uk > 4000       # UK, not the home city next door
    lat, _ = geo.coords_of("London, Ontario")
    assert lat and 42 < lat < 44               # London ON coords


def test_bare_london_home_still_works_for_backwards_compat():
    # profile.json has home="London" bare (BT); _ring_single falls back through
    # _city_in() when locate() returns None, so distances from bare "London" home
    # continue to work exactly as before.
    ring, km, _ = geo.ring_for("London", "Kitchener, ON, Canada")
    assert ring == 1 and km < 120
