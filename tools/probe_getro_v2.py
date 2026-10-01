"""Probe candidate Getro-hosted job boards (v2 -- custom domains).

The v1 probe (tools/probe_getro_networks.py) assumed most boards would sit at
`<slug>.getro.com`. Turned out only 1/27 candidates lived there; Getro has
migrated most boards to custom domains (MaRS -> techjobs.marsdd.com,
Communitech -> jobs.communitech.ca, etc.). v2 uses a richer candidate list.

For each label we try, in order:
  1. any explicit host we know (e.g., MaRS techjobs.marsdd.com)
  2. jobs.<parent domain>          (most common Getro alias)
  3. careers.<parent domain>       (second most common alias)
  4. techjobs.<parent domain>      (specific pattern MaRS uses)
  5. <slug>.getro.com              (v1 fallback)

For each URL we fetch /jobs (falling back to /), look for the __NEXT_DATA__
script blob, and extract props.pageProps.network.{id,name}. If found we
verify with a POST to api.getro.com/api/v2/collections/{id}/search/jobs.

Sandbox blocks outbound network; runs via .github/workflows/probe-getro-v2.yml
(workflow_dispatch). Exit code is always 0.
"""
from __future__ import annotations
import json
import re
import sys
import time

import requests

TIMEOUT = 15
UA = "Mozilla/5.0 (compatible; attsis-jobboard-probe-v2/1.0; +regional coverage expansion)"

# Format: (label, parent_domain, explicit_hosts...).
# The parent_domain is used to synthesize jobs.<domain>, careers.<domain>,
# techjobs.<domain>. Explicit_hosts are tried FIRST -- they win when we
# already know the real Getro host (e.g., techjobs.marsdd.com for MaRS).
CANDIDATES: list[tuple[str, str, list[str]]] = [
    # Already-live boards -- re-probe to prove v2 finds them the same way.
    ("MaRS Discovery District",       "marsdd.com",         ["techjobs.marsdd.com"]),
    ("Communitech",                   "communitech.ca",     ["jobs.communitech.ca"]),
    # Ontario -- unresolved after v1
    ("Invest Ottawa",                 "investottawa.ca",    ["jobs.investottawa.ca"]),
    ("DMZ (TMU)",                     "dmz.to",             []),
    ("Innovation Guelph",             "innovationguelph.com", []),
    ("Creative Destruction Lab",      "creativedestructionlab.com", []),
    ("Bayview Yards Ottawa",          "bayviewyards.org",   []),
    ("Innovation Factory Hamilton",   "innovationfactory.com", []),
    ("Innovation Cluster Peterborough","innovationcluster.ca", []),
    ("NEXT Canada",                   "nextcanada.com",     []),
    ("Ontario Centre of Innovation",  "oc-innovation.ca",   []),
    ("Kanata North Tech Park",        "kanatanorth.com",    []),
    # Atlantic
    ("Volta Halifax",                 "voltaeffect.com",    ["volta.getro.com"]),
    ("Springboard Atlantic",          "springboardatlantic.ca", []),
    ("Genesis St. Johns NL",          "genesiscentre.ca",   []),
    # Prairies
    ("Platform Calgary",              "platformcalgary.com", []),
    ("Edmonton Unlimited",            "edmontonunlimited.com", []),
    ("Innovate Calgary",              "innovatecalgary.com", []),
    ("Co.Labs Saskatoon",             "co-labs.ca",         []),
    ("North Forge Winnipeg",          "northforge.ca",      []),
    # BC
    ("New Ventures BC",               "newventuresbc.com",  []),
    ("Foresight Cleantech",           "foresightcac.com",   []),
    ("Alacrity Foundation",           "alacritycanada.com", []),
    # Aggregators / national
    ("Economic Development Jobs",     "economicdevelopmentjobs.com", ["economicdevelopmentjobs.getro.com"]),
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


def _candidate_hosts(explicit: list[str], parent: str) -> list[str]:
    """Ordered candidate hostnames for one label."""
    seen = set()
    out = []
    for h in explicit:
        if h not in seen:
            out.append(h); seen.add(h)
    for tmpl in ("jobs.{p}", "careers.{p}", "techjobs.{p}"):
        h = tmpl.format(p=parent)
        if h not in seen:
            out.append(h); seen.add(h)
    slug = parent.split(".")[0]
    for h in (f"{slug}.getro.com",):
        if h not in seen:
            out.append(h); seen.add(h)
    return out


def _probe_url(url: str):
    """Return (html, err). Follows redirects; only accepts 200."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT,
                         allow_redirects=True)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if r.status_code == 200:
        return r.text, None
    return None, f"HTTP {r.status_code}"


def _probe_host(host: str):
    """Try https+/jobs, https+/ , http+/jobs, http+/ . Return (html, url, err)."""
    last = None
    for scheme in ("https", "http"):
        for path in ("/jobs", "/"):
            url = f"{scheme}://{host}{path}"
            html, err = _probe_url(url)
            if html:
                return html, url, None
            last = err
    return None, None, last


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
    print(f"Probing {len(CANDIDATES)} Getro candidates (v2, custom-domain aware)\n")

    confirmed = []     # (label, host, id, name, engineer_count)
    api_broken = []    # (label, host, id, name, api_err)
    no_getro = []      # (label, [tried_hosts], last_err)

    for label, parent, explicit in CANDIDATES:
        hosts = _candidate_hosts(explicit, parent)
        print(f"=== {label}  ({parent})")
        hit = None
        tried_notes = []
        for host in hosts:
            html, url, err = _probe_host(host)
            if not html:
                tried_notes.append(f"{host}={err}")
                print(f"    try {host}: {err}")
                continue
            nid, nname = _extract_network_id(html)
            if not nid:
                tried_notes.append(f"{host}=no __NEXT_DATA__")
                print(f"    try {host}: 200 but no Getro __NEXT_DATA__")
                continue
            print(f"    hit {host}: network_id={nid}  name={nname!r}")
            count, api_err = _verify_api(nid)
            if api_err:
                api_broken.append((label, host, nid, nname, api_err))
                print(f"    WARN network_id found but api {api_err}")
                hit = (host, nid, nname, None, "api_broken")
                break
            confirmed.append((label, host, nid, nname, count))
            print(f"    HIT+ {count} 'engineer' jobs")
            hit = (host, nid, nname, count, "ok")
            break
        if not hit:
            no_getro.append((label, hosts, tried_notes[-1] if tried_notes else "no candidates"))
        time.sleep(0.5)

    print("\n=== SUMMARY")
    print(f"  Confirmed (ready to add):        {len(confirmed)}")
    print(f"  API broken (id known, no jobs):  {len(api_broken)}")
    print(f"  Not a Getro board / unreachable: {len(no_getro)}")

    if confirmed:
        print("\n=== CONFIRMED (JSON, paste-ready for engine/sources.json)")
        promo = [
            {"platform": "getro", "name": label, "network_id": nid}
            for label, _host, nid, _name, _n in confirmed
        ]
        print(json.dumps(promo, indent=2))
        print("\n=== CONFIRMED breakdown")
        for label, host, nid, name, count in confirmed:
            print(f"  {count:>6}  {label}  (network_id={nid}, host={host})")

    if api_broken:
        print("\n=== NETWORK ID FOUND BUT API BROKEN")
        for label, host, nid, name, err in api_broken:
            print(f"  {label}  host={host}  network_id={nid}  {err}")

    if no_getro:
        print("\n=== NOT ON GETRO (or not reachable)")
        for label, tried, last in no_getro:
            print(f"  {label}  (tried {len(tried)} hosts, last: {last})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
