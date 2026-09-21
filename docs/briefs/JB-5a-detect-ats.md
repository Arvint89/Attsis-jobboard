# JB-5a: detect_ats — identify a company's ATS from a URL or its careers-page HTML
Status: HIGH
Dependencies: none. First building block of the company resolver (ADR-002).
Estimated build: 1 Aider session (small, pure functions, no network)
Run pre-code checklist: OS=Windows 11, Python 3.11+, encoding='utf-8', mental end-to-end test, simplest fix

## 2. Why this brief exists
22 of 32 registry companies are `platform: "resolve"` and produce no jobs. Most have a company careers URL
(e.g. `https://kepler.space/careers`) whose page links or embeds the real ATS. Today resolving is manual.
This brief builds the deterministic core: given a URL, or the HTML of a careers page, return the
`platform` + `slug` (+ Workday fields) that `ats.FETCHERS` already knows how to fetch — or name the
unsupported ATS so we know which adapter to build next. No network, no LLM: pure functions.

## 3. Exact function signatures (THE CONTRACT)
New file `engine/ats_detect.py`:
```python
SUPPORTED = {"greenhouse", "lever", "ashby", "smartrecruiters", "recruitee",
             "workable", "bamboohr", "rippling", "workday"}   # must equal set(ats.FETCHERS)

def detect_ats(url: str) -> dict | None:
    """
    Args: url - any careers or job URL.
    Returns: {"platform": str, "slug": str, "supported": bool} plus, for workday only,
             {"tenant": str, "site": str, "dc": str}.  None if the URL is not a known ATS.
             slug is exactly what ats.fetch_<platform>() expects (see ats.py URL templates).
    Raises: nothing (bad/empty input -> None).
    """

def detect_ats_in_html(html: str) -> dict | None:
    """
    Args: html - raw HTML of a company careers page.
    Returns: result of detect_ats() for the first URL found in the HTML (href, src, or plain text)
             that is a SUPPORTED ats; if none supported, the first unsupported one; else None.
    Raises: nothing.
    """
```

## 4. Real data examples (URLs are from engine/companies.json unless marked)
| Input URL | Output |
|---|---|
| `https://ztr.bamboohr.com/careers` | `{"platform":"bamboohr","slug":"ztr","supported":true}` |
| `https://boards.greenhouse.io/tenstorrent` | `{"platform":"greenhouse","slug":"tenstorrent","supported":true}` |
| `https://job-boards.greenhouse.io/geotab/jobs/123` | `{"platform":"greenhouse","slug":"geotab","supported":true}` |
| `https://jobs.lever.co/acme/abc-123` (synthetic) | `{"platform":"lever","slug":"acme","supported":true}` |
| `https://jobs.ashbyhq.com/miovision` (synthetic) | `{"platform":"ashby","slug":"miovision","supported":true}` |
| `https://jobs.smartrecruiters.com/Acme1/744` (synthetic) | `{"platform":"smartrecruiters","slug":"Acme1","supported":true}` |
| `https://acme.recruitee.com/o/eng` (synthetic) | `{"platform":"recruitee","slug":"acme","supported":true}` |
| `https://apply.workable.com/acme/j/AB12/` (synthetic) | `{"platform":"workable","slug":"acme","supported":true}` |
| `https://ats.rippling.com/canada-rocket-company/jobs` | `{"platform":"rippling","slug":"canada-rocket-company","supported":true}` |
| `https://nokia.wd3.myworkdayjobs.com/en-US/careers` (synthetic) | `{"platform":"workday","slug":"nokia","tenant":"nokia","site":"careers","dc":"wd3","supported":true}` |
| `https://acme.wd1.myworkdayjobs.com/External` (synthetic) | `{"platform":"workday","slug":"acme","tenant":"acme","site":"External","dc":"wd1","supported":true}` |
| `https://vitalbio.na.teamtailor.com/jobs/671261` | `{"platform":"teamtailor","slug":"vitalbio","supported":false}` |
| `https://generaldynamics-ca-careers.ttcportals.com/search/jobs` | `{"platform":"ttcportals","slug":"generaldynamics-ca-careers","supported":false}` |
| `https://recruiting.ultipro.ca/STA5000/JobBoard` | `{"platform":"ultipro","slug":"STA5000","supported":false}` |
| `https://wolfadvancedtechnology.scouterecruit.net/jobs` | `{"platform":"scouterecruit","slug":"wolfadvancedtechnology","supported":false}` |
| `https://kepler.space/careers` | `None` |

Workday rule: host `{tenant}.{dc}.myworkdayjobs.com`; path segments; skip a first segment that looks like a
locale (`^[a-z]{2}-[A-Z]{2}$`); next segment is `site`.
Teamtailor: host `{slug}.teamtailor.com` or `{slug}.{region}.teamtailor.com`.

## 5. Implementation steps
1. Create `engine/ats_detect.py` with `SUPPORTED`, `detect_ats`, `detect_ats_in_html`. Use `urllib.parse.urlparse`
   and `re` only (stdlib). Match on lower-cased host; keep slug case as it appears in the URL.
2. Implement one small rule per platform (host pattern + which path segment / subdomain is the slug) — table above.
3. `detect_ats_in_html`: `re.findall(r'https?://[^\s"\'<>)]+', html)`, run `detect_ats` on each, prefer supported.
4. Create `tests/test_ats_detect.py` with the tests in section 8 (parametrize over the table in section 4).

## 6. Constraints
- Pure functions: no network, no file I/O, no LLM. stdlib only. No emojis. encoding='utf-8'.
- Do NOT modify ats.py or companies.json in this brief.
- `SUPPORTED` must equal `set(ats.FETCHERS)` — enforced by a test so a new adapter can't be forgotten.

## 7. Acceptance criteria
- [ ] every row of the section-4 table passes as a parametrized test
- [ ] HTML tests pass; SUPPORTED-matches-FETCHERS test passes
- [ ] all existing tests pass; smoke 11/11

## 8. The failing tests (tests/test_ats_detect.py)
```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import ats, ats_detect

CASES = [
    ("https://ztr.bamboohr.com/careers", {"platform": "bamboohr", "slug": "ztr", "supported": True}),
    ("https://boards.greenhouse.io/tenstorrent", {"platform": "greenhouse", "slug": "tenstorrent", "supported": True}),
    ("https://job-boards.greenhouse.io/geotab/jobs/123", {"platform": "greenhouse", "slug": "geotab", "supported": True}),
    ("https://jobs.lever.co/acme/abc-123", {"platform": "lever", "slug": "acme", "supported": True}),
    ("https://jobs.ashbyhq.com/miovision", {"platform": "ashby", "slug": "miovision", "supported": True}),
    ("https://jobs.smartrecruiters.com/Acme1/744", {"platform": "smartrecruiters", "slug": "Acme1", "supported": True}),
    ("https://acme.recruitee.com/o/eng", {"platform": "recruitee", "slug": "acme", "supported": True}),
    ("https://apply.workable.com/acme/j/AB12/", {"platform": "workable", "slug": "acme", "supported": True}),
    ("https://ats.rippling.com/canada-rocket-company/jobs", {"platform": "rippling", "slug": "canada-rocket-company", "supported": True}),
    ("https://nokia.wd3.myworkdayjobs.com/en-US/careers", {"platform": "workday", "slug": "nokia", "tenant": "nokia", "site": "careers", "dc": "wd3", "supported": True}),
    ("https://acme.wd1.myworkdayjobs.com/External", {"platform": "workday", "slug": "acme", "tenant": "acme", "site": "External", "dc": "wd1", "supported": True}),
    ("https://vitalbio.na.teamtailor.com/jobs/671261", {"platform": "teamtailor", "slug": "vitalbio", "supported": False}),
    ("https://generaldynamics-ca-careers.ttcportals.com/search/jobs", {"platform": "ttcportals", "slug": "generaldynamics-ca-careers", "supported": False}),
    ("https://recruiting.ultipro.ca/STA5000/JobBoard", {"platform": "ultipro", "slug": "STA5000", "supported": False}),
    ("https://wolfadvancedtechnology.scouterecruit.net/jobs", {"platform": "scouterecruit", "slug": "wolfadvancedtechnology", "supported": False}),
    ("https://kepler.space/careers", None),
    ("", None),
]

@pytest.mark.parametrize("url,expected", CASES)
def test_detect_ats(url, expected):
    assert ats_detect.detect_ats(url) == expected

def test_supported_matches_fetchers():
    assert ats_detect.SUPPORTED == set(ats.FETCHERS)

def test_html_prefers_supported_ats():
    html = ('<a href="https://acme.na.teamtailor.com/jobs">old</a>'
            '<iframe src="https://boards.greenhouse.io/acme?embed=1"></iframe>')
    assert ats_detect.detect_ats_in_html(html) == {"platform": "greenhouse", "slug": "acme", "supported": True}

def test_html_falls_back_to_unsupported_then_none():
    assert ats_detect.detect_ats_in_html('<a href="https://x.teamtailor.com/jobs">j</a>')["platform"] == "teamtailor"
    assert ats_detect.detect_ats_in_html("<p>no jobs here</p>") is None
```

## 9. Validation BT runs
```powershell
python -m pytest tests/test_ats_detect.py -q      # all pass
python -m pytest tests/ -q
cd engine; python smoke_test.py; cd ..            # 11/11
```

## 10. Out of scope
- Fetching careers pages over the network, LLM fallback, writing to companies.json (JB-5b, per ADR-002).
- New adapters for teamtailor/ultipro/ttcportals/scouterecruit (separate briefs once we count how many need them).

## 11. After this ships
JB-5b: a resolver script that, for each `resolve` company, downloads its careers_url, runs
`detect_ats_in_html`, verifies with one real `ats.fetch_company` call, and prints a proposed
companies.json diff for BT to review. Runs on BT's machine, never in the daily Action.
