"""JB-174 observability baseline: GoatCounter pageview tracker.

Privacy-first, no cookies, GDPR-safe. Free up to 100k pageviews/month.
Setup for BT (one-time, not code):
  1. Sign up at goatcounter.com
  2. Create a site called 'attsis' (so the URL below resolves)
  3. Verify pageviews land in the GoatCounter dashboard

Until BT completes step 2, the script tag silently 404s on every page
load — zero visual impact, zero error (fetch failure is swallowed by the
async loader)."""
import os
import re

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _read():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_goatcounter_script_present():
    html = _read()
    # async + the official count.js endpoint are the signatures
    assert re.search(
        r'<script[^>]*data-goatcounter="https://attsis\.goatcounter\.com/count"[^>]*async[^>]*src="//gc\.zgo\.at/count\.js"[^>]*>',
        html,
    ), "GoatCounter script tag with the attsis URL + async + the official count.js src must be in site/index.html"


def test_goatcounter_is_in_footer_not_in_head():
    # Async in footer: no blocking, no FOUC, loads after first paint.
    html = _read()
    footer_idx = html.find("<footer")
    gc_idx = html.find("data-goatcounter")
    assert gc_idx > footer_idx, (
        "GoatCounter should load after the footer so first paint isn't held up"
    )


def test_goatcounter_async_attribute():
    # Must be async so it never blocks render even if gc.zgo.at is slow.
    html = _read()
    assert re.search(
        r'<script[^>]*data-goatcounter[^>]*async[^>]*>', html
    ), "GoatCounter script must have `async` attribute"
