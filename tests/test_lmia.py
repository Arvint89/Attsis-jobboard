"""JB-15: LMIA-positive employers (ESDC TFWP open data) -> registry `lmia` -> sponsorship facet. No network."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import facets  # noqa: E402
import lmia_match as lm  # noqa: E402

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")

# real rows (2026Q1 file): (province, stream, employer, address, occupation, status, lmias, positions)
ROWS = {
    "2026Q1": [
        ("Ontario", "High Wage", "Vital Biosciences Inc.", "Mississauga, ON L5L 4L4", "21101-Physicists and astronomers", "Unknown", 1, 1),
        ("Ontario", "Global Talent", "Shopify Inc.", "Ottawa, ON K2P 2L8", "21231-Software engineers and designers", "Unknown", 2, 3),
        ("Ontario", "High Wage", "Nokia", "Kanata, ON K2K 2E6", "21311-Computer engineers", "Unknown", 1, 2),
        ("Ontario", "High Wage", "Vital Signs Clinic", "Toronto, ON", "31100-Specialists", "Unknown", 1, 1),
    ],
    "2025Q4": [
        ("Ontario", "Global Talent", "SHOPIFY INC", "Ottawa, ON K2P 2L8", "21231-Software engineers and designers", "Unknown", 1, 1),
    ],
}
REG = [{"name": "Vital Biosciences", "city": "Mississauga"}, {"name": "Shopify", "city": "Ottawa"},
       {"name": "Nokia", "city": "Ottawa"}, {"name": "Vital Signs"}, {"name": "Faire", "city": "Kitchener"}]


def test_norm_drops_legal_suffixes_and_case():
    assert lm.norm("SHOPIFY INC") == lm.norm("Shopify Inc.") == "shopify"
    assert lm.norm("Zebra Technologies Corporation, ULC") == "zebra technologies"
    assert lm.norm("Vital Biosciences") != lm.norm("Vital Signs Clinic")


def test_match_exact_names_across_quarters():
    m = lm.match(ROWS, REG)
    assert set(m) == {"Vital Biosciences", "Shopify", "Nokia"}       # "Vital Signs" != "Vital Signs Clinic"
    assert m["Shopify"]["quarters"] == ["2025Q4", "2026Q1"] and m["Shopify"]["positions"] == 4
    assert m["Shopify"]["city_check"] == "ok"
    assert m["Nokia"]["city_check"] == "Kanata, ON K2K 2E6"         # differs from registry city -> flagged


def test_facet_lmia_is_its_own_value_and_the_jd_wins():
    lmia = {"quarters": ["2025Q4", "2026Q1"], "positions": 4}
    assert facets.sponsorship("Python, Go", None, lmia) == "lmia"
    assert facets.sponsorship("We are not able to sponsor visas.", None, lmia) == "no"
    assert facets.sponsorship("Visa sponsorship available.", None, lmia) == "yes"
    assert facets.sponsorship("Python", None, None) == "unknown"
    assert facets.sponsorship("Python", None) == "unknown"            # old 2-arg call still works


def test_site_chip_says_lmia_employer_not_sponsors():
    h = open(INDEX, encoding="utf-8").read()
    assert "j.sponsorship==='lmia'" in h and "LMIA employer" in h
    assert "Not a promise this role is sponsored" in h
