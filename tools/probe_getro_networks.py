"""Probe candidate Getro-hosted job boards for their network_id.

Regional expansion (JB-59). Reads a candidate list of accelerators / EDOs /
innovation hubs in Canada, fetches each board's public HTML, extracts the
network_id from the __NEXT_DATA__ JSON blob, then verifies by hitting the
public search API with a small test query. Prints per-candidate results and
a paste-ready JSON block for the promotion PR to engine/sources.json.

Sandbox can't reach the internet, so this runs via .github/workflows/probe-getro.yml
(workflow_dispatch). Exit code is always 0.

Reference: docs/research/REGIONAL_JOB_BOARDS.md -- "2-minute method".
"""
from __future__ import annotations
import json
import re
import sys
import time

import requests

TIMEOUT = 15
UA = "Mozilla/5.0 (compatible; attsis-jobboard-probe/1.0; +regional coverage expansion)"

# Candidate boards to probe. Format: (label, hostname).
# Two hostname shapes are common: `<slug>.getro.com` (hosted) and custom
# domains (proxied). The probe tries the given hostname first; if that's a
# custom domain that redirects, `_extract_network_id` still catches the id
# from the final rendered page.
CANDIDATES = [
    # Known TBD from REGIONAL_JOB_BOARDS.md
    ("DMZ (TMU) Toronto",                "dmz.getro.com"),
    ("Invest Ottawa",                    "jobs.investottawa.ca"),
    ("Invest Ottawa (getro variant)",    "investottawa.getro.com"),
    ("Volta Halifax",                    "volta.getro.com"),
    ("Platform Calgary",                 "platformcalgary.getro.com"),
    ("Edmonton Unlimited",               "edmontonunlimited.getro.com"),
    ("New Ventures BC",                  "newventuresbc.getro.com"),
    ("Foresight Cleantech",              "foresightcac.getro.com"),
    ("Co.Labs Saskatoon",                "colabs.getro.com"),
    ("North Forge Winnipeg",             "northforge.getro.com"),
    ("Getro EDO national aggregate",     "economicdevelopmentjobs.getro.com"),
    # Speculative Ontario accelerators / innovation hubs worth probing
    ("Innovation Guelph",                "innovationguelph.getro.com"),
    ("Creative Destruction Lab",         "creativedestructionlab.getro.com"),
    ("CDL (short variant)",              "cdl.getro.com"),
    ("Bayview Yards Ottawa",             "bayviewyards.getro.com"),
    ("Innovation Factory Hamilton",      "innovationfactory.getro.com"),
    ("Innovation Cluster Peterborough",  "innovationcluster.getro.com"),
    ("NEXT Canada",                      "nextcanada.getro.com"),
    ("Ontario Centre of Innovation",     "oci.getro.com"),
    # Additional Canadian tech-hub candidates
    ("Alacrity Foundation",              "alacritycanada.getro.com"),
    ("Genesis St. Johns NL",             "genesiscentre.getro.com"),
    ("Springboard Atlantic",             "springboardatlantic.getro.com"),
    ("Innovate Niagara",                 "innovateniagara.getro.com"),
    ("Ventures Nova Scotia",             "novascotiabusiness.getro.com"),
    ("Kanata North Tech Park",           "kanatanorth.getro.com"),
    ("Ontario Centre for Innovation",    "oceinnovation.getro.com"),
    ("Toronto Region Board of Trade",    "trbot.getro.com"),
]

NEXT_DATA_RE = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


def _extract_network_id(html: str):
    """Return (network_id, network_name) or (None, None) if not a Getro page."""
    m = NEXT_DATA_RE.search(html)
    if not m:
        return None, None
    try:
        blob = json.loads(m.group(1))
    except Exception:
        return None, None
    net = (
        blob.get("props", {})
        .get("pageProps", {})
        .get("network")
    )
    if not net:
        return None, None
    return net.get("id"), net.get("name")


def _probe_html(host: str):
    for scheme in ("https", "http"):
        for path in ("/jobs", "/"):
            url = f"{scheme}://{host}{path}"
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT,
                                 allow_redirects=True)
            except Exception as e:
                return None, f"{type(e).__name__}: {e}"
            if r.status_code == 200:
                return r.text, None
        # only try https then http, but both paths for each
    return None, f"HTTP {r.status_code}"


def _verify_api(network_id):
    url = f"https://api.getro.com/api/v2/collections/{network_id}/search/jobs"
    try:
        r = requests.post(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"hitsPerPage": 1, "page": 0, "query": "engineer"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    try:
        data = r.json()
    except Exception:
        return None, "not JSON"
    res = data.get("results", {}) or {}
    return res.get("count"), None


def main() -> int:
    print(f"Probing {len(CANDIDATES)} candidate Getro boards\n")

    confirmed = []   # (label, host, id, name, engineer_count)
    non_getro = []   # (label, host, http_err_or_not_next)
    api_fail = []    # (label, host, id, name, api_err)

    for label, host in CANDIDATES:
        print(f"=== {label}  ({host})")
        html, err = _probe_html(host)
        if err:
            non_getro.append((label, host, err))
            print(f"    SKIP  fetch failed: {err}")
            continue
        nid, nname = _extract_network_id(html)
        if not nid:
            non_getro.append((label, host, "no __NEXT_DATA__ network"))
            print("    SKIP  not a Getro page (no __NEXT_DATA__ network)")
            continue
        count, api_err = _verify_api(nid)
        if api_err:
            api_fail.append((label, host, nid, nname, api_err))
            print(f"    WARN  network_id={nid} name={nname!r}  API {api_err}")
            continue
        confirmed.append((label, host, nid, nname, count))
        print(f"    HIT+  network_id={nid}  name={nname!r}  {count} 'engineer' jobs")
        time.sleep(0.5)  # be polite

    print("\n=== SUMMARY")
    print(f"  Confirmed (ready to add):        {len(confirmed)}")
    print(f"  API broken (id known, no jobs):  {len(api_fail)}")
    print(f"  Not a Getro board / unreachable: {len(non_getro)}")

    if confirmed:
        print("\n=== CONFIRMED (JSON, paste-ready for engine/sources.json)")
        promo = [
            {"platform": "getro", "name": label, "network_id": nid}
            for label, _host, nid, _name, _n in confirmed
        ]
        print(json.dumps(promo, indent=2))
        print("\n=== CONFIRMED breakdown (engineer-job count per board)")
        for label, host, nid, name, count in confirmed:
            print(f"  {count:>6}  {label}  (network_id={nid}, host={host})")

    if api_fail:
        print("\n=== NETWORK ID FOUND BUT API BROKEN (needs endpoint variant work)")
        for label, host, nid, name, err in api_fail:
            print(f"  {label}  network_id={nid}  {err}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
