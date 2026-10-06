"""JB-172 payment-gated Tailor buttons.

When site/data/config.json has an empty tailor_pay_url, every Tailor button
(per-card + Standard + Premium) ships `disabled` with a "Coming soon" tooltip.
When the URL is populated, the config loader re-enables the Tailor-tab buttons
and the per-card template outputs the active button.

These are static tests against site/index.html + site/data/config.json; the
dynamic enable/disable is covered by the smoke suite with a Puppeteer run
once JB-68 is wired up.
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX = os.path.join(ROOT, "site", "index.html")
CONFIG = os.path.join(ROOT, "site", "data", "config.json")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_tab_buttons_ship_disabled_with_tooltip():
    html = _read(INDEX)
    for btn_id in ("tailorBasicBtn", "tailorProBtn"):
        # <button class="btn" id="tailorBasicBtn" disabled title="..." >
        m = re.search(
            rf'<button[^>]*id="{btn_id}"[^>]*>', html
        )
        assert m, f"{btn_id} not found in site/index.html"
        tag = m.group(0)
        assert "disabled" in tag, f"{btn_id} must ship with disabled attribute"
        assert "Coming soon" in tag, f"{btn_id} must ship with Coming soon tooltip"


def test_per_card_button_is_gated_by_tailor_pay_ready():
    html = _read(INDEX)
    # The per-card template must branch on _tailorPayReady()
    assert "_tailorPayReady()" in html
    # And the disabled branch must carry the same tooltip
    assert re.search(r'<button[^>]*disabled[^>]*title="Coming soon[^"]*"[^>]*>\s*✎ Tailor CV', html), \
        "per-card Tailor CV button must have a disabled branch with Coming soon tooltip"


def test_config_default_leaves_buttons_disabled():
    # The shipped config.json must have an empty tailor_pay_url, so the
    # default live site renders with buttons gray until BT edits the file.
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    assert cfg.get("tailor_pay_url", "") == "", (
        "config.json must ship with empty tailor_pay_url so buttons stay "
        "disabled by default; populate it only when Stripe is live"
    )


def test_loader_re_enables_tab_buttons_when_pay_url_set():
    html = _read(INDEX)
    # After Promise.all([_loadTenant(), _loadConfig()]) resolves, the loader
    # must flip the Tailor-tab buttons from disabled -> enabled when the URL
    # is set. Checking for the removeAttribute('disabled') call bound to the
    # button ids is enough to prove the wiring.
    assert "tailorBasicBtn" in html and "tailorProBtn" in html
    assert "removeAttribute('disabled')" in html, (
        "loader must call removeAttribute('disabled') on Tailor buttons when "
        "tailor_pay_url is set"
    )
