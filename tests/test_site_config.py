"""JB-60: site/data/config.json ships + has the editable fields the site expects.

Keeps schema drift from silently breaking features that read config.
tailor_pay_url MAY be empty (fallback to the in-app Tailor tab) but must
be a string so the browser can concat it with the job URL."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "site", "data", "config.json")


def test_config_file_exists():
    assert os.path.exists(CONFIG), f"missing {CONFIG}"


def test_config_has_tailor_pay_url_key():
    d = json.load(open(CONFIG, encoding="utf-8"))
    assert "tailor_pay_url" in d
    assert isinstance(d["tailor_pay_url"], str)


def test_tailor_pay_url_is_https_or_empty():
    d = json.load(open(CONFIG, encoding="utf-8"))
    v = d["tailor_pay_url"]
    assert v == "" or v.startswith("https://"), (
        "tailor_pay_url must be empty (dev) or https:// (prod payment link)"
    )
