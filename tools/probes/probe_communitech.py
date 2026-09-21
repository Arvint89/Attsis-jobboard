"""Probe (JB-39): find the Getro collection id behind Communitech's public
'Work In Tech' board. Run:  python tools/probes/probe_communitech.py   -> paste output. Diagnostic tool (kept in repo)."""
import re, json, requests

URL = "https://www1.communitech.ca/jobs"
h = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
print("page length:", len(h))
for label, pat in [
    ("collections/NNN", r"collections/(\d+)"),
    ("collection id", r'"collection[A-Za-z]*"\s*:\s*\{?\s*"?id"?\s*:\s*"?(\d+)'),
    ("networkId", r'"networkId"\s*:\s*"?(\d+)'),
    ("network id", r'"network"\s*:\s*\{\s*"id"\s*:\s*"?(\d+)'),
]:
    print(f"{label:16}", sorted(set(re.findall(pat, h))))

# try each candidate against the search API and report job counts
cands = sorted(set(re.findall(r"collections/(\d+)", h)) |
               set(re.findall(r'"collection[A-Za-z]*"\s*:\s*\{?\s*"?id"?\s*:\s*"?(\d+)', h)) |
               set(re.findall(r'"network"\s*:\s*\{\s*"id"\s*:\s*"?(\d+)', h)) | {"8936"})
H = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
for cid in cands:
    try:
        r = requests.post(f"https://api.getro.com/api/v2/collections/{cid}/search/jobs", headers=H,
                          json={"hitsPerPage": 1, "page": 0, "query": ""}, timeout=25)
        d = r.json()
        print(f"collection {cid}: status {r.status_code}, total jobs {(d.get('results') or {}).get('count')}")
    except Exception as e:
        print(f"collection {cid}: ERR {e}")
