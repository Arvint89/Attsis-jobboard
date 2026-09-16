# Global Attsis — Product Development Rules (PD Rules) v1.0
_Created 2026-09-16. First product to adopt: **BT Job Board**. Intended as a reusable Global Attsis standard._

These rules exist because BT asked that internal builds be treated as real product
development, not throwaway scripts. They are deliberately lightweight — enough
discipline to keep quality and traceability, not so much that a one-person shop
drowns in ceremony. They inherit the hard rules already in force in `ai-empire`
(TDD, smoke-test gate, permission gates, no secrets, UTF-8) and make them the
default for **any** Global Attsis product.

## The lifecycle (every product, every feature)

1. **SPEC first.** Before code, write/append `SPEC.md`: the problem, goals,
   non-goals, functional requirements (FR-n), and **acceptance criteria** that are
   testable. A change big enough to touch ≥3 files or add a subsystem needs a spec
   line before it starts.
2. **Architecture doc.** Every product ships an `ARCHITECTURE.md` with an
   **abstract** (a plain-language paragraph on how the software works) and a
   **high-level → mid-level → low-level** walk (pipeline diagram, components,
   then contracts/functions). Keep it current as the design changes.
3. **Test first (TDD).** Write the test that encodes the acceptance criterion,
   watch it fail, then implement to green. Minimum three cases per unit: happy
   path, empty/boundary input, failure/exclusion. Tests live in `tests/`.
4. **Build.** Small, readable, commented. No hardcoded secrets (`os.getenv` only).
   Every file `utf-8`. No network in unit tests.
5. **Smoke-gate.** After every phase run `smoke_test.py`. It checks **runtime
   state** ("does it work right now on this machine?"), which unit tests do not.
   A phase is not done until smoke passes. Unit-green ≠ smoke-green; both required.
6. **Visual check.** If the product renders anything (a page, a chart), look at
   the rendered output before calling it done — not just the code.
7. **Release.** Bump `CHANGELOG.md`, note the version, and record the method in a
   `Work_done/` README so the build is reproducible and BT can learn from it.

## Permission gates (never bypass, carried from ai-empire)

- Never publish/deploy anything live without an explicit go — draft/preview first.
- Never commit secrets or credentials.
- Ask before any action that touches an external system (GitHub push, Pages
  deploy, sending mail, paying for anything).
- Money, trades, transfers: never without BT's explicit confirmation.

## Definition of Done

A feature is done when: its acceptance criteria in `SPEC.md` are checked, its
tests are green, `smoke_test.py` passes, rendered output has been eyeballed, the
`CHANGELOG` and method README are updated, and nothing above was skipped silently.
If something is blocked, say why — never mark done by omission.

## Roles

BT: reviews, approves, directs, owns go/no-go on permission gates.
AI (Global Attsis): specs, tests, builds, runs the gate, reports honestly.
