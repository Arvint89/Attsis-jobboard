# Aider + Groq Workflow — Solo Build Guide

_Last updated: 2026-09-18._
_When Claude Code is not available (subscription paused, quota out, or you just want to save it for harder work), use this workflow to keep building attsis-jobboard with aider + Groq._

---

## 0. One-time setup

```powershell
pip install aider-chat
# Verify your Groq key is set (it should already be — same key ai-empire and shorts use)
$env:GROQ_API_KEY
```

If the key comes back blank:
```powershell
$env:GROQ_API_KEY = "<paste key from .env or password manager>"
# Persist across shells:
setx GROQ_API_KEY "<paste key>"
```

Verify aider sees the config:
```powershell
cd C:\Users\Namrata\Attsis-jobboard
aider --help
# Look for: "Config file: .aider.conf.yml"
```

---

## 1. The daily loop

```powershell
cd C:\Users\Namrata\Attsis-jobboard
git checkout -b feature/JB-XX-short-name   # one branch per BL, per ADR-001
aider
```

Aider opens a REPL. It has already loaded (via `.aider.conf.yml`):
- `CLAUDE.md`, `HANDOFF.md`, `BACKLOG.md`
- `docs/PRODUCT_DEVELOPMENT_RULES.md`, `docs/ARCHITECTURE.md`

Now `/add` only the files this BL will touch. Small context = better output on Groq's 32k window.

---

## 2. Aider commands you'll actually use

| Command | What it does |
|---|---|
| `/add engine/ats.py` | Add file to editable session |
| `/read docs/SPEC.md` | Add file read-only (rules / spec) |
| `/drop engine/ats.py` | Remove file from session (free context) |
| `/ls` | Show what's in the session |
| `/tokens` | Show current context usage vs Groq 32k limit |
| `/undo` | Undo aider's last commit |
| `/diff` | Show pending changes before commit |
| `/test python -m pytest tests/` | Run tests, feed failures back to aider |
| `/commit` | Commit staged changes (if `auto-commits: false`) |
| `/help` | Full command list |
| `/exit` | Quit aider |

---

## 3. Prompt template — paste at the start of every session

```
Task: JB-XX — <one-line description>
Files in session: <list what you /add'd>

Acceptance criteria:
1. <specific check 1>
2. <specific check 2>
3. `python engine/smoke_test.py` still passes
4. All existing tests still pass

Rules from CLAUDE.md and PRODUCT_DEVELOPMENT_RULES.md:
- TDD: write the failing test first, red, then implement, green
- Do not touch files outside the ones I've added — ask if you need more
- Every commit message starts with "JB-XX:"
- Do not add an LLM to the daily loop (north star: near-zero token cost)
- Do not touch site/data/jobs.json or engine/fixtures.json (CI-managed)

Start by proposing the test.
```

---

## 4. Which BLs are safe for aider+Groq

**✅ Ideal:**
- JB-19 (BambooHR job descriptions) — single-file adapter change + test
- JB-20 (per-company cap) — engine/build_board.py change + test
- Any "add ATS adapter for X" — clear pattern in `engine/ats.py`
- Adding tests to fixtures
- Salary field on job cards (site/index.html + a scorer key)
- Persist filter choices in localStorage (site/index.html only)
- Mobile layout pass (CSS in site/index.html only)

**🟡 Careful — split into 2–3 sub-BLs first:**
- Anything touching `engine/jobfilter.py` — it's the SSOT for Python **and** browser scorer. If you change scoring in Python you MUST change the equivalent JS in `site/index.html`. Verify with the built-in parity test.
- Multi-file refactors — chunk them so Groq's 32k window doesn't blow up.

**❌ Save for Claude Code:**
- New ADR / architecture change
- Anything touching the vault (`global-attsis-vault/`) or Muninn
- Cross-repo work (jobboard ↔ shorts, ↔ ai-empire)
- Live-API debugging (sandbox and aider both can't reach ATS APIs from your dev machine — only the GitHub Action can)
- Anything that needs to reason about `all-systems.json` or repo ownership
- Rewriting the scorer strategy

---

## 5. Guardrails and gotchas

### Groq free tier — 1,000 req/day shared

Your `GROQ_API_KEY` is used by ai-empire, attsis-shorts, attsis-signal, attsis-etsy. A heavy aider day can starve those production paths → signal Telegram bot may hit 429.

**Options:**
- Get a **second Groq key** for aider-only. Set `GROQ_API_KEY_AIDER` in your shell and `$env:GROQ_API_KEY = $env:GROQ_API_KEY_AIDER` before running aider.
- Or watch `/tokens` and stop the session when you hit ~50% of daily budget.

### Auto-commits vs manual git

`auto-commits: true` in `.aider.conf.yml` means aider commits after every accepted change. That's fine — matches ADR-001's "one BL per commit" — but:
- Aider commit messages are AI-generated. If they don't match your style, edit with `git commit --amend` before pushing.
- If aider commits a mistake, `/undo` reverts the last one (or `git reset HEAD~1` manually).

### Groq context vs Claude Code habit

Claude Code can hold 100k+ tokens of context. Groq's Llama 3.3 caps at ~32k. **You must be more disciplined about which files are in the session.** Run `/tokens` after every `/add`. If you're above 20k, `/drop` something.

### The scorer parity trap

`engine/jobfilter.py` (Python) and the JS scorer embedded in `site/index.html` **must produce identical scores for the same input**. Aider will happily change one and forget the other. Always instruct: "keep Python and JS scorer in sync" and run the parity test after.

### The sandbox trap

You cannot fetch live ATS data from your dev machine or from aider. Only the GitHub Action (`.github/workflows/sweep.yml`) has network access to Greenhouse / Lever / Ashby / Getro / LEDC. When testing locally: use `--demo` mode or fixtures.

### Don't let aider add an LLM to the daily loop

North star: **near-zero token cost**. The scorer is deterministic Python. If aider suggests "call an LLM to classify the job" — say no. LLM use in this repo is build-time only (writing code) not runtime.

---

## 6. Sanity checks before pushing

Before `git push` on any aider-built branch:

```powershell
python -m pytest tests/               # 41 tests must be green
python engine/smoke_test.py           # 11 smoke checks must be green
python engine/build_board.py --demo   # site/data/jobs.json must build cleanly
```

If any fail, don't push — feed the error back to aider with `/test` and iterate.

---

## 7. When aider gets stuck

Groq's Llama 3.3 is fast but shallower than Claude. Signs it's stuck:
- Same broken diff twice in a row
- Refuses to write the test first even when asked
- Hallucinates a file path or function name

**Recovery:**
1. `/undo` its last commit
2. `/drop` everything, `/add` just the one file that matters
3. Rewrite the prompt more concretely — give it the exact function signature to write
4. If still stuck after 2 tries: quit aider, save the task for the next Claude Code session

Do **not** keep prompting aider through 5+ retries — you're burning Groq quota that ai-empire and signal need.

---

## 8. Session-end checklist

- [ ] All acceptance criteria met
- [ ] All tests + smoke green
- [ ] BACKLOG.md updated (BL moved to Done, or notes added if paused)
- [ ] Branch pushed, PR opened
- [ ] If you paused mid-BL: update HANDOFF.md section 5 ("Next action") with exactly where to resume

---

## 9. Reference

- Aider docs: https://aider.chat/docs/
- Aider config file spec: https://aider.chat/docs/config/aider_conf.html
- Groq model list: https://console.groq.com/docs/models
- ADR-001 branching model: `docs/decisions/ADR-001-branching-model.md`
- Product Dev Rules: `docs/PRODUCT_DEVELOPMENT_RULES.md`
