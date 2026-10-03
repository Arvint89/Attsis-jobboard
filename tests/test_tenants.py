"""Unit tests for JB-62 tenant region filter."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import tenants


def mk(city, location=None, location_near=None):
    j = {}
    if location is not None: j["location"] = location
    if location_near is not None: j["location_near"] = location_near
    if city is not None and location is None and location_near is None:
        j["location"] = f"{city}, ON, Canada"
    return j


LEDC = {
    "slug": "ledc",
    "name": "LEDC",
    "region_cities": ["London", "St. Thomas", "Strathroy", "Dorchester"],
}


def test_filter_keeps_in_region_jobs():
    jobs = [mk("London"), mk("St. Thomas"), mk("Toronto")]
    out = tenants.filter_jobs(jobs, LEDC)
    assert len(out) == 2
    cities = [j["location"].split(",")[0] for j in out]
    assert "Toronto" not in cities


def test_filter_is_case_insensitive():
    jobs = [mk("london"), mk("LONDON"), mk("London")]
    out = tenants.filter_jobs(jobs, LEDC)
    assert len(out) == 3


def test_filter_prefers_location_near_over_location():
    # JB-56: location_near is the disambiguated city string
    j = mk(None, location="London, ON, Canada", location_near="Strathroy")
    out = tenants.filter_jobs([j], LEDC)
    assert len(out) == 1


def test_filter_drops_jobs_with_empty_location():
    jobs = [{"title": "Something", "description": "..."}]
    out = tenants.filter_jobs(jobs, LEDC)
    assert out == []


def test_filter_fail_open_on_missing_tenant():
    # a None tenant must NOT nuke the board -- return input unchanged
    jobs = [mk("Toronto"), mk("Vancouver")]
    assert tenants.filter_jobs(jobs, None) == jobs
    assert tenants.filter_jobs(jobs, {}) == jobs


def test_filter_fail_open_on_invalid_tenant():
    jobs = [mk("Toronto")]
    assert tenants.filter_jobs(jobs, {"region_cities": "London"}) == jobs      # not a list
    assert tenants.filter_jobs(jobs, {"region_cities": []}) == jobs            # empty list
    assert tenants.filter_jobs(jobs, {"region_cities": [1, 2]}) == jobs        # non-string


def test_is_valid_tenant_shape():
    assert tenants.is_valid_tenant({"region_cities": ["London"]})
    assert tenants.is_valid_tenant({"region_cities": ["A", "B"], "name": "X"})
    assert not tenants.is_valid_tenant({})
    assert not tenants.is_valid_tenant({"region_cities": []})
    assert not tenants.is_valid_tenant(None)
    assert not tenants.is_valid_tenant("string")


def test_city_match_matches_statscan_cma_cities():
    # Smoke -- the London CMA from tools/london_coverage.py should round-trip
    cma = {"slug": "london-cma", "region_cities": [
        "London", "St. Thomas", "Strathroy", "Ilderton",
        "Komoka", "Dorchester", "Putnam", "Mount Brydges"
    ]}
    jobs = [mk(c) for c in ("London", "Ilderton", "Komoka", "Toronto", "Ottawa")]
    out = tenants.filter_jobs(jobs, cma)
    assert len(out) == 3


def test_norm_city_collapses_whitespace():
    jobs = [{"location_near": "  London  "}]
    assert len(tenants.filter_jobs(jobs, LEDC)) == 1
