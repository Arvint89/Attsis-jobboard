"""JB-17 CSA: every third-party script / stylesheet is version-pinned and carries an SRI hash, so a
compromised CDN can't run new code on the page that holds the user's CV. Google Fonts CSS is
generated per browser (no stable hash) -> exempt; it's CSS, not script."""
import os
import re

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _tags():
    h = open(INDEX, encoding="utf-8").read()
    return re.findall(r"<script[^>]*\ssrc=\"[^\"]+\"[^>]*>|<link[^>]*rel=\"stylesheet\"[^>]*>", h)


def test_external_assets_have_integrity():
    ext = [t for t in _tags() if re.search(r'(src|href)="(https?:)?//', t) and "fonts.googleapis.com" not in t]
    assert len(ext) >= 7, ext
    for t in ext:
        assert 'integrity="sha384-' in t and 'crossorigin="anonymous"' in t, t


def test_goatcounter_is_version_pinned():
    h = open(INDEX, encoding="utf-8").read()
    assert "gc.zgo.at/count.js" not in h            # floating "latest"
    assert "https://gc.zgo.at/count.v5.js" in h
