# JB-30b: Getro fetch — one failed query must not wipe the rest; fetch beyond page 0
Status: HIGH
Dependencies: none (JB-30a tells us how much this matters on live data)
Estimated build: 1 Aider session (small)
Run pre-code checklist: OS=Windows 11, Python 3.11+, encoding='utf-8', mental end-to-end test, simplest fix

## 2. Why this brief exists
Two defects in `fetch_getro` (engine/sources.py):
1. The whole query loop sits inside ONE `try`. If any single query fails (e.g. HTTP 429 on query 7),
   the function returns `[]` and throws away everything queries 1–6 already collected.
2. Only `page: 0` is requested, so each query returns at most `per_page` (100) jobs even when Getro
   has more (the sweep sees 233 "embedded" results on Communitech).

## 3. Exact function signatures (THE CONTRACT)
```python
def fetch_getro(name: str, network_id, queries=None, per_page: int = 100, max_pages: int = 5) -> list:
    """
    Pull a Getro board. For each query: request page 0, 1, 2 ... and stop when a page returns
    fewer than per_page jobs, or after max_pages pages. Merge all queries, dedupe by job id.
    Args: name - board label ("Communitech"); network_id - Getro collection id;
          queries - keyword list (default DEFAULT_QUERIES); per_page - hitsPerPage;
          max_pages - hard cap on pages per query.
    Returns: list of normalized job dicts (same shape as today, via _norm_getro).
    Raises: nothing. A failing request skips THAT query's remaining pages only;
            jobs already collected are kept. If every request fails -> [].
    """
```

## 4. Real data examples
Request body sent to `_post(url, body)` (unchanged except `page` now increments):
```json
{"hitsPerPage": 100, "page": 1, "query": "embedded"}
```
Response shape (captured 2026-09-17, see tests/test_sources.py `_fake`):
```json
{"results": {"count": 233, "jobs": [{"id": 111, "title": "Embedded Firmware Engineer", "...": "..."}]}}
```
Current code to change (engine/sources.py):
```python
    try:
        for q in queries:
            data = _post(url, {"hitsPerPage": per_page, "page": 0, "query": q})
            for job in (data.get("results", {}) or {}).get("jobs", []) or []:
                ...
    except Exception:
        return []          # never kill the build over one board
    return out
```

## 5. Implementation steps
1. Add `max_pages: int = 5` to the signature. Update the docstring to the contract above.
2. Replace the single outer `try` with: `for q in queries:` → `for page in range(max_pages):` →
   `try: data = _post(url, {"hitsPerPage": per_page, "page": page, "query": q})`
   `except Exception: break` (skip rest of this query only).
3. Keep the existing dedupe by `seen` and `_norm_getro(job, name)` exactly as they are.
4. After processing a page, `if len(jobs_on_page) < per_page: break`.
5. Leave `fetch_source` / `FETCH_SOURCES` unchanged (they pass name, network_id, queries — defaults apply).
6. Add the three tests in section 8 to `tests/test_sources.py`.

## 6. Constraints
- No network in pytest (monkeypatch `sources._post`, as the existing tests do).
- The 4 existing getro tests must still pass unchanged (normalize, dedupe, private salary, failure-safe).
- No sleep/retry logic in this brief. No emojis. encoding='utf-8'.

## 7. Acceptance criteria
- [ ] Signature matches exactly, `max_pages` defaults to 5
- [ ] 3 new tests pass; all existing tests pass; smoke 11/11

## 8. The failing tests
```python
def test_getro_one_failing_query_keeps_the_others(monkeypatch):
    def fake(url, body):
        if body["query"] == "bad":
            raise RuntimeError("429")
        return _fake([dict(ONE, id=body["query"])])
    monkeypatch.setattr(sources, "_post", fake)
    jobs = sources.fetch_getro("Communitech", 8936, ["firmware", "bad", "altium"])
    assert len(jobs) == 2


def test_getro_paginates_until_a_short_page(monkeypatch):
    calls = []
    def fake(url, body):
        calls.append(body["page"])
        n = 2 if body["page"] == 0 else 1
        return _fake([dict(ONE, id=f"{body['page']}-{i}") for i in range(n)])
    monkeypatch.setattr(sources, "_post", fake)
    jobs = sources.fetch_getro("Communitech", 8936, ["firmware"], per_page=2)
    assert len(jobs) == 3 and calls == [0, 1]


def test_getro_stops_at_max_pages(monkeypatch):
    calls = []
    def fake(url, body):
        calls.append(body["page"])
        return _fake([dict(ONE, id=f"{body['page']}-{i}") for i in range(2)])
    monkeypatch.setattr(sources, "_post", fake)
    sources.fetch_getro("Communitech", 8936, ["firmware"], per_page=2, max_pages=3)
    assert calls == [0, 1, 2]
```

## 9. Validation BT runs
```powershell
python -m pytest tests/test_sources.py -q        # all pass, including 3 new
python -m pytest tests/ -q
cd engine; python smoke_test.py; cd ..            # 11/11
```
Live proof comes after merge: compare `source_funnel["getro:Communitech"]["fetched"]` (JB-30a) before/after.

## 10. Out of scope
- Changing DEFAULT_QUERIES. Retry/backoff. LEDC. Anything in jobfilter.

## 11. After this ships
Watch the live funnel for one run. If Getro requests start failing at volume (429s), next brief adds a small
delay between pages.
