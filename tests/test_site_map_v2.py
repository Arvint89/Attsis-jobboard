"""JB-72 Map v2 (#180). See docs/design/DESIGN_map_v2.md.

Static checks on site/index.html, plus the pure map helpers executed under
Node (extracted from the MAPV2-PURE block). Node tests skip if node is absent.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX = os.path.join(ROOT, "site", "index.html")


def _html():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def _pure_block():
    m = re.search(r"/\* MAPV2-PURE-BEGIN \*/(.*?)/\* MAPV2-PURE-END \*/", _html(), re.S)
    assert m, "MAPV2-PURE block missing from site/index.html"
    return m.group(1)


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    out = subprocess.run([node, "-e", _pure_block() + "\n" + js],
                         capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ---- static ----
def test_dark_tiles_match_prototype():
    h = _html()
    assert "World_Dark_Gray_Base" in h and "World_Dark_Gray_Reference" in h
    assert "World_Light_Gray_Base" not in h


def test_markercluster_loaded_from_cdnjs():
    assert "cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/" in _html()


def test_cluster_has_fallback_when_cdn_fails():
    assert "L.markerClusterGroup" in _html() and "typeof L.markerClusterGroup" in _html()


def test_three_layout_modes_and_move_toggle():
    h = _html()
    for i in ("modeList", "modeSplit", "modeMap", "moveToggle", "placeChip", "offToggle"):
        assert f'id="{i}"' in h, i


def test_rings_50_100_200():
    assert re.search(r"\[50,\s*100,\s*200\]", _html())


# ---- pure helpers under node ----
def test_geokey_rounds_to_two_decimals():
    r = _node('console.log(JSON.stringify([geoKey(43.65321,-79.38312), geoKey(43.654,-79.384)]))')
    assert r == ["43.65,-79.38", "43.65,-79.38"]


def test_group_by_location_skips_unplaced_and_sorts_by_score():
    r = _node('''const g=groupByLocation([
      {title:"a",score:5,lat:43.651,lng:-79.381,location_near:"Toronto"},
      {title:"b",score:9,lat:43.652,lng:-79.382,location_near:"Toronto"},
      {title:"c",score:7,lat:null,lng:null},
      {title:"d",score:6,lat:42.98,lng:-81.25,location_near:"London"}]);
      console.log(JSON.stringify(g.map(x=>({k:x.key,best:x.best,n:x.jobs.length,first:x.jobs[0].title,place:x.place}))))''')
    by = {x["k"]: x for x in r}
    assert set(by) == {"43.65,-79.38", "42.98,-81.25"}
    assert by["43.65,-79.38"] == {"k": "43.65,-79.38", "best": 9, "n": 2, "first": "b", "place": "Toronto"}


def test_pin_tier():
    assert _node('console.log(JSON.stringify([pinTier(9),pinTier(8),pinTier(7),pinTier(6),pinTier(0)]))') == \
        ["strong", "strong", "good", "low", "low"]


def test_in_bounds_and_place_counts():
    r = _node('''const b={s:42,n:44,w:-82,e:-79};
      const jobs=[{lat:43,lng:-80},{lat:45,lng:-80},{lat:null,lng:null},{}];
      console.log(JSON.stringify({ib:jobs.map(j=>inBounds(j,b)),pc:placeCounts(jobs,b)}))''')
    assert r["ib"] == [True, False, False, False]
    assert r["pc"] == {"inside": 1, "outside": 1, "unplaced": 2}


def test_sal_short_labels():
    r = _node('console.log(JSON.stringify([salShort("$95,000 - $120,000"),salShort("$45/hour"),salShort("120k"),salShort(""),salShort("Competitive")]))')
    assert r == ["$95\u2013120k", "$45/h", "$120k", "", ""]
