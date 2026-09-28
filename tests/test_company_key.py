"""JB-55: company_key canonicalization edge cases."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from company_key import company_key


def test_empty_and_none_are_empty_string():
    assert company_key("") == ""
    assert company_key(None) == ""


def test_lowercase_and_whitespace():
    assert company_key("Deep  Trekker  ") == "deep trekker"
    assert company_key("\tDEEP\nTREKKER\r") == "deep trekker"


def test_diacritics_collapse():
    # "Zürich" and "Zurich" must key equal so registry lookups don't split.
    assert company_key("Zürich AG") == company_key("Zurich AG")
    assert company_key("Café Corp") == "cafe"     # diacritic dropped, "corp" suffix stripped


def test_common_legal_suffixes_stripped():
    assert company_key("Fidus Systems Inc.") == "fidus systems"
    assert company_key("Fidus Systems Inc") == "fidus systems"
    assert company_key("Fidus Systems") == "fidus systems"
    assert company_key("Pipetel Technologies Inc.") == company_key("Pipetel Technologies")


def test_stacked_suffixes_all_peeled():
    # "Foo Corp Ltd" -> peel "ltd" then peel "corp"
    assert company_key("Foo Corp Ltd") == "foo"
    assert company_key("Big Co Ltd") == "big"


def test_all_the_common_suffixes():
    for suf in ["Inc", "Inc.", "Corp", "Corporation", "Ltd", "Limited",
                "LLC", "LLP", "PLC", "GmbH", "AG", "BV", "SA", "S.A.",
                "Group", "Holdings", "Company"]:
        assert company_key(f"Acme {suf}") == "acme", f"failed on suffix: {suf}"


def test_ampersand_and_hyphen_preserved():
    # These carry meaning (Johnson & Johnson vs Johnson Johnson) so we keep them.
    assert company_key("Johnson & Johnson") == "johnson & johnson"
    assert company_key("General-Dynamics") == "general-dynamics"


def test_apostrophes_and_punct_stripped():
    assert company_key("O'Brien Electronics") == "o brien electronics"
    assert company_key("Smith, Jones & Co.") == "smith jones &"     # "co" is a suffix


def test_idempotent():
    for raw in ["Deep Trekker", "Fidus Systems Inc.", "Zürich AG", "  Foo Corp Ltd  "]:
        once = company_key(raw)
        twice = company_key(once)
        assert once == twice, f"not idempotent on: {raw!r} ({once!r} != {twice!r})"


def test_pipetel_soft_duplicate_collapses():
    # The known duplicate flagged in JB-55: "Pipetel Technologies Inc." vs "Pipetel Technologies"
    assert company_key("Pipetel Technologies Inc.") == company_key("Pipetel Technologies")


def test_registry_names_do_not_collide_after_canonicalization():
    # Load the real registry, confirm no two entries share a canonical key.
    import json
    reg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engine", "companies.json"),
                        encoding="utf-8"))["companies"]
    seen = {}
    for e in reg:
        k = company_key(e["name"])
        if k in seen:
            raise AssertionError(f"collision: {e['name']!r} keys same as {seen[k]!r} -> {k!r}")
        seen[k] = e["name"]
