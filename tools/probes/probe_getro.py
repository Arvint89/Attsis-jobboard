"""One-off probe (JB-38): where can we get the full job description for Getro (MaRS/Communitech) jobs?
Run on your PC:  python probe_getro.py   -> paste the output to Claude. Do NOT commit this file."""
import json, re, requests
H = {"Accept": "application/json", "Content-Type": "application/json",
     "User-Agent": "Mozilla/5.0 (compatible; bt-jobboard/1.0; +personal job search)"}
API = "https://api.getro.com/api/v2"

def get(url, accept_json=True):
    try:
        r = requests.get(url, headers=H if accept_json else {"User-Agent": H["User-Agent"]}, timeout=25)
        return r.status_code, r.text
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}"

for cid, name in ((383, "MaRS"), (8936, "Communitech")):
    print(f"\n==================== {name} ({cid}) ====================")
    st, txt = get(f"{API}/collections/{cid}")
    print("collection info:", st, txt[:300].replace("\n", " "))
    try:
        r = requests.post(f"{API}/collections/{cid}/search/jobs", headers=H,
                          json={"hitsPerPage": 3, "page": 0, "query": "embedded"}, timeout=25)
        d = r.json()
    except Exception as e:
        print("search failed:", e); continue
    jobs = (d.get("results") or {}).get("jobs") or []
    print("search status", r.status_code, "| total count", (d.get("results") or {}).get("count"))
    if not jobs:
        continue
    print("job keys:", sorted(jobs[0].keys()))
    for j in jobs[:3]:
        org = j.get("organization") or {}
        print(f"\n--- job id={j.get('id')} slug={j.get('slug')} | {j.get('title')} @ {org.get('name')}")
        print("    url:", j.get("url"), "| org slug:", org.get("slug"), "| org domain:", org.get("domain"))
        print("    has_description:", j.get("has_description"), "| skills:", (j.get("skills") or [])[:6])
        for label, u in (("detail A", f"{API}/collections/{cid}/jobs/{j.get('id')}"),
                         ("detail B", f"{API}/jobs/{j.get('id')}"),
                         ("detail C", f"{API}/collections/{cid}/organizations/{org.get('slug')}/jobs/{j.get('slug')}")):
            st, txt = get(u)
            desc = ""
            try:
                jj = json.loads(txt); s = json.dumps(jj)
                m = re.search(r'"(description|description_html|content)"\s*:\s*"(.{0,160})', s)
                desc = m.group(0) if m else "(no description key)"
            except Exception:
                desc = "(not json)"
            print(f"    {label}: {st} len={len(txt) if isinstance(txt,str) else 0} {desc[:170]}")
        if j.get("url"):
            st, txt = get(j["url"], accept_json=False)
            print(f"    apply url page: {st} len={len(txt)}  ats-hint: " +
                  ",".join(k for k in ("greenhouse", "lever.co", "ashbyhq", "workday", "bamboohr", "rippling", "smartrecruiters", "workable", "teamtailor") if k in (j['url'] + txt[:20000]).lower()))
