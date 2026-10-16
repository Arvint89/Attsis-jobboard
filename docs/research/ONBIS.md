# ONBIS / business-registry spike (JB-58, #137)

Run 2026-10-16 by the nightly loop. Labels: ✅ verified (how) · ⚠️ inferred · ❓ unchecked.

## Verdict
**Not usable as a company-discovery source for the board. Recommendation: abandon it** in favour of what already works, which is aggregator discovery and live verification (JB-86/JB-90 added 81 companies) plus the slug probe (JB-5c).

The reason is in the data. ✅ No open business registry carries **industry** or **employee count**. Those are exactly the two filters ADR-007 needs (≥10 employees, a relevant sector). Without them, a city pull returns every holding company, numbered company and shell.

## What I checked
| Source | Access | Fields | Verdict |
|---|---|---|---|
| **ONBIS** web search (`appmybizaccount.gov.on.ca/onbis`) | ✅ HTTP 200, a per-query web UI | ❓ the record shape wasn't inspected (it's a JS app; scraping per query isn't a deterministic bulk pull) | not a bulk source |
| data.ontario.ca: "Ontario Business Registry Partner Portal" | ✅ open CSV (OGL-Ontario), updated 2026-09-17 | ✅ a list of **intermediaries** (law firms, accountants) allowed to file. **Not businesses** | irrelevant |
| data.ontario.ca: other registry bulk data | ✅ CKAN search for "business registry" / "corporations": 9 / 42 datasets, none a business list | — | ❓ a paid OBR bulk feed may exist; not verifiable from here |
| open.canada.ca: **Federal Corporations** (Corporations Canada) | ✅ open CSV (OGL-Canada), updated daily; active CBCA file is 104 MB (last-modified 2026-10-15) | ✅ 18 columns: corporation no., BN, name, legislation, status, anniversary date, last filing, street, **city, province**, postal code, min/max directors. **No industry, no employee count** | only useful to *verify* a known company's legal name and city |

Sample record (✅ row 1 of the active CBCA file):
```json
{"Corporation number": "8660115", "Business number (BN)": "835752437", "Corporate name - form 1": "MINDANGLER CAPITAL INC.",
 "Status": "Active", "Anniversary date": "2013-10-10", "City/town": "Ottawa", "Province/territory": "ON", "Postal code": "K2K 3G4"}
```

## Answers to the spike questions
1. **Access model:** federal = free bulk CSV, updated daily ✅. Ontario = per-query web search only in the open catalogue ✅. Paid bulk ❓.
2. **Data shape:** `{name, city, province, incorporation/anniversary date, status}` ✅. **No industry, no employee count** ✅ (federal). ONBIS record ❓.
3. **Filter viability:** `min_employees >= 10` **is not possible** from these sources. StatCan's Business Register isn't public at firm level ⚠️ (from general knowledge, not checked tonight).
4. **Rate limits / ToS:** the federal CSV is under the Open Government Licence – Canada, so bulk use is allowed ✅. ONBIS scraping ❓, and it wouldn't be deterministic anyway.
5. **Update cadence:** federal daily ✅; OBR intermediary list monthly ✅.

## Cost of a Toronto / Waterloo / London seeding run
Not worth estimating. Without industry or size, a seed would add thousands of non-employers that each need an ATS probe. Compare the current pipeline: a company is only promoted after its own job board returns jobs.

## If revisited
The one useful job for the federal file is **verification**: confirm a registry company's legal name and HQ city (it's a cheap join on name + province). It's a nice-to-have, not discovery.
