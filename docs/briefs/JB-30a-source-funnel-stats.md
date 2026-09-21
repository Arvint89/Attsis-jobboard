# JB-30a: Source funnel stats — see where jobs are lost, per source
Status: HIGH
Dependencies: none
Estimated build: 1 Aider session (small)
Run pre-code checklist: OS=Windows 11, Python 3.11+, all file ops encoding='utf-8', mental end-to-end test, simplest fix

## 2. Why this brief exists
The daily sweep sees ~233 embedded + ~30 PCB results on Communitech; the live board keeps **1** Communitech job.
`gather()` reports no error, so jobs are either not fetched or silently dropped by `jobfilter.classify`
(`verdict == "excluded"`: off-profile title / pure-software / not relevant / stale). Today we cannot tell which.
Measure before fixing: record, per source, how many jobs arrived and why each was excluded.

## 3. Exact function signatures (THE CONTRACT)
Add to `engine/build_board.py`:
```python
def source_funnel(classified: list[tuple[dict, dict]]) -> dict[str, dict]:
    """
    Args: classified - list of (job, classify_result) pairs, AFTER dedupe, one per job.
          job has key "source" (e.g. "getro:Communitech", "greenhouse"); missing -> "unknown".
          classify_result has "verdict" in {"match","below","excluded"} and "reasons": list[str].
    Returns: {source: {"fetched": int, "kept": int, "excluded": {reason_key: int}}}
          kept = verdict != "excluded".
          reason_key = first reason, text before any ":" or "(", stripped.
            "stale (45d)" -> "stale"; "off-profile title: sales" -> "off-profile title"
          An excluded job with empty reasons counts under "unspecified".
    Raises: nothing.
    """
```

## 4. Real data examples
Input (shape of real rows):
```python
[({"source": "getro:Communitech", "title": "Embedded Electrical Engineer"}, {"verdict": "below", "reasons": []}),
 ({"source": "getro:Communitech", "title": "Firmware Eng"}, {"verdict": "excluded", "reasons": ["stale (45d)"]}),
 ({"source": "getro:Communitech", "title": "Sales Lead"}, {"verdict": "excluded", "reasons": ["off-profile title: sales"]}),
 ({"source": "greenhouse", "title": "PCB Layout Engineer"}, {"verdict": "match", "reasons": []})]
```
Output:
```json
{"getro:Communitech": {"fetched": 3, "kept": 1, "excluded": {"stale": 1, "off-profile title": 1}},
 "greenhouse": {"fetched": 1, "kept": 1, "excluded": {}}}
```
New key in `site/data/jobs.json` payload: `"source_funnel": { ...as above... }`.

Current shape of the loop you are changing (`build()` in engine/build_board.py):
```python
    rows = []
    for j in raw:
        res = jobfilter.classify(j, extra_flags=j.get("_reg_flags"))
        if res["verdict"] == "excluded":
            continue
```

## 5. Implementation steps
1. In `engine/build_board.py`, add `source_funnel()` exactly as specified (module level, near `dedupe`).
2. In `build()`, before the `for j in raw:` loop, create `classified = []`. Inside the loop, right after
   `res = jobfilter.classify(...)`, append `(j, res)` to `classified` (before the `continue`).
3. In the `payload` dict, add `"source_funnel": source_funnel(classified),` after `"counts"`.
4. Add the tests from section 8 to `tests/test_build.py`.

## 6. Constraints
- encoding='utf-8' on any file op; no emojis in code or commit messages.
- No network in pytest. Do not change scoring, dedupe, or which jobs are kept — this is observation only.
- Do not edit `site/data/jobs.json` or `site/board_standalone.html` by hand (generated).

## 7. Acceptance criteria
- [ ] `source_funnel` exists with the exact signature above
- [ ] both new tests pass; all existing tests still pass
- [ ] `python build_board.py --demo` writes a jobs.json containing `source_funnel`
- [ ] smoke 11/11

## 8. The failing test
```python
def test_source_funnel_counts_kept_and_excluded_by_reason():
    import build_board
    jobs = [{"source": "getro:Communitech"}] * 3 + [{"source": "greenhouse"}]
    res = [{"verdict": "below", "reasons": []},
           {"verdict": "excluded", "reasons": ["stale (45d)"]},
           {"verdict": "excluded", "reasons": ["off-profile title: sales"]},
           {"verdict": "match", "reasons": []}]
    out = build_board.source_funnel(list(zip(jobs, res)))
    assert out == {"getro:Communitech": {"fetched": 3, "kept": 1,
                                         "excluded": {"stale": 1, "off-profile title": 1}},
                   "greenhouse": {"fetched": 1, "kept": 1, "excluded": {}}}


def test_source_funnel_missing_source_and_reason():
    import build_board
    out = build_board.source_funnel([({}, {"verdict": "excluded", "reasons": []})])
    assert out == {"unknown": {"fetched": 1, "kept": 0, "excluded": {"unspecified": 1}}}
```

## 9. Validation BT runs
```powershell
python -m pytest tests/ -q                      # all pass
cd engine; python smoke_test.py; cd ..          # 11/11
cd engine; python build_board.py --demo; cd ..
python -c "import json;print(json.load(open('site/data/jobs.json',encoding='utf-8'))['source_funnel'])"
git checkout -- site/data/jobs.json site/board_standalone.html   # never commit generated files
```
After merge, the next live `job-sweep` run shows the real Communitech funnel on the live jobs.json.

## 10. Out of scope
- Fixing Getro fetching (JB-30b). Changing exclusion rules (decide after reading the funnel). Any UI.

## 11. After this ships
Read `source_funnel` from the live jobs.json → if Communitech `fetched` is small: JB-30b fixes it.
If `fetched` is large but `excluded.stale` / `not relevant to profile` dominate: new brief to tune jobfilter.
