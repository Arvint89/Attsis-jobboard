"""Tests for tools/seed_ledc.py -- LEDC directory registry seeding (JB-45 v2)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import seed_ledc as sl  # noqa: E402


CSV_FIXTURE = (
    '"Company Name","Year Established",Profile,Phone,Website,'
    'Instagram,Twitter,Facebook,LinkedIn,Address,"Address Line 2",'
    '"Postal Code",City,Province,"Contact Email","Contact Name",'
    '"Contact Title",Employees,Placements,"Industry Sector",'
    '"Additional Keywords","Last Updated"\n'
    'Acme Robotics,2005,profile,,https://acme.example.com,,,,,'
    ',,,London,ON,,,,"200+",,"Advanced Manufacturing",,\n'
    'Beta Health,2010,profile,,http://beta.example.com,,,,,,,,'
    'St. Thomas,ON,,,,"50-100",,"Health",,\n'
    'TinyShop,2020,profile,,https://tiny.example.com,,,,,,,,'
    'London,ON,,,,"10-50",,"Digital Media & Tech",,\n'
    'NoWebsite Co,2019,profile,,,,,,,,,,'
    'London,ON,,,,"200+",,"Advanced Manufacturing",,\n'
    'AgriCo,1990,profile,,https://agri.example.com,,,,,,,,'
    'London,ON,,,,"200+",,"Agri-Food",,\n'
)


# --- parse_ledc_csv -----------------------------------------------------------

def test_parse_keeps_only_target_sectors_bands_and_website():
    rows = sl.parse_ledc_csv(CSV_FIXTURE)
    names = [r["Company Name"] for r in rows]
    # Kept: Acme (mfg, 200+), Beta (health, 50-100).
    # Dropped: TinyShop (10-50 band), NoWebsite (no website), AgriCo (agri-food sector).
    assert set(names) == {"Acme Robotics", "Beta Health"}


def test_parse_respects_custom_filters():
    rows = sl.parse_ledc_csv(
        CSV_FIXTURE,
        sectors=frozenset({"Digital Media & Tech"}),
        employee_bands=frozenset({"10-50"}),
    )
    assert [r["Company Name"] for r in rows] == ["TinyShop"]


# --- to_registry_entry --------------------------------------------------------

def test_to_registry_entry_shape_and_ring_for_london_metro():
    row = {
        "Company Name": "Acme Robotics",
        "Website": "https://acme.example.com",
        "City": "London",
        "Industry Sector": "Advanced Manufacturing",
    }
    entry = sl.to_registry_entry(row)
    assert set(entry.keys()) == {"name", "ring", "platform", "slug", "careers_url",
                                 "note", "flags", "industry", "sponsors", "city"}
    assert entry["name"] == "Acme Robotics"
    assert entry["platform"] == "resolve"
    assert entry["ring"] == 0        # London -> ring 0
    assert entry["city"] == "London"
    assert entry["industry"] == "manufacturing"
    assert entry["careers_url"] == "https://acme.example.com"


def test_to_registry_entry_ring_for_non_london_metro():
    row = {
        "Company Name": "Faraway Corp",
        "Website": "faraway.example.com",       # missing scheme -> tool adds http://
        "City": "Toronto",
        "Industry Sector": "Health",
    }
    entry = sl.to_registry_entry(row)
    assert entry["ring"] == 4
    assert entry["city"] == "Toronto"
    assert entry["industry"] == "health"
    assert entry["careers_url"] == "http://faraway.example.com"


# --- merge_seeds --------------------------------------------------------------

def _reg(*names):
    return {"companies": [{"name": n} for n in names]}


def test_merge_appends_new_and_skips_duplicates():
    reg = _reg("Existing Co", "Another Co Ltd")
    new = [
        {"name": "Existing Co"},                # exact dup
        {"name": "another co, ltd."},           # canonicalized dup
        {"name": "Brand New Systems"},          # keep
        {"name": "Brand New Systems Inc"},      # canonicalized dup within batch
    ]
    merged, added, skipped = sl.merge_seeds(reg, new)
    added_names = [e["name"] for e in added]
    assert added_names == ["Brand New Systems"]
    assert len(skipped) == 3
    assert len(merged["companies"]) == 3


def test_merge_drops_empty_names():
    reg = _reg("X")
    merged, added, skipped = sl.merge_seeds(reg, [{"name": ""}, {"name": "  "}])
    assert added == []
    assert len(skipped) == 2


# --- integration on the fixture ----------------------------------------------

def test_end_to_end_fixture_produces_two_valid_entries(tmp_path):
    reg_path = tmp_path / "companies.json"
    reg_path.write_text(json.dumps({"companies": [{"name": "Existing Co"}]}), encoding="utf-8")
    text = CSV_FIXTURE
    rows = sl.parse_ledc_csv(text)
    entries = [sl.to_registry_entry(r) for r in rows]
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    merged, added, skipped = sl.merge_seeds(reg, entries)
    assert {e["name"] for e in added} == {"Acme Robotics", "Beta Health"}
    for e in added:
        assert e["platform"] == "resolve"
        assert e["careers_url"]
