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
