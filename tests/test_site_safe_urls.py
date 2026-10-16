"""JB-17 CSA finding: job / careers / tracker links must only ever be http(s).
A posting URL comes from third-party ATS data; a `javascript:` URL rendered as href ran on click
(✅ reproduced 2026-10-15 in Edge), and the tracker link (t.url) wasn't escaped at all."""
import json
import os
import re
import shutil
import subprocess

import pytest

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _html():
    return open(INDEX, encoding="utf-8").read()


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    m = re.search(r"/\* CARD-PURE-BEGIN \*/(.*?)/\* CARD-PURE-END \*/", _html(), re.S)
    out = subprocess.run([node, "-e", m.group(1) + "\n" + js], capture_output=True, text=True,
                         encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_http_url_allows_only_http_and_https():
    cases = ["https://jobs.lever.co/x/1", "HTTP://a.b/c", "javascript:alert(1)", " JavaScript:alert(1)",
             "data:text/html,<b>", "vbscript:x", "//evil.example/x", "/relative", "", None]
    r = _node(f"console.log(JSON.stringify({json.dumps(cases)}.map(httpUrl)))")
    assert r == ["https://jobs.lever.co/x/1", "HTTP://a.b/c", "", "", "", "", "", "", "", ""]


def test_every_data_href_goes_through_httpUrl():
    h = _html()
    raw = re.findall(r'href="\$\{(?!escH\(httpUrl\()[^}]*\}"', h)
    assert not raw, raw            # every data-driven href is escH(httpUrl(...))
