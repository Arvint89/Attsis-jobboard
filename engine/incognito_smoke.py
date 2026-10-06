"""JB-68 pre-production incognito smoke.

Opens a URL in headless Chromium (via Playwright) and asserts:
  - page title contains the expected brand
  - the job board renders at least one .job card (or the setup form shows)
  - no uncaught JS console errors

Exit codes:
  0 → all checks pass
  1 → at least one check failed (details on stderr)

Usage:
  python engine/incognito_smoke.py <url>
  python engine/incognito_smoke.py http://localhost:8000/
  python engine/incognito_smoke.py https://arvint89.github.io/Attsis-jobboard/

Requires: playwright + the chromium browser. In CI:
  pip install playwright
  playwright install chromium

Design note: deliberately NOT part of the pytest suite. Pytest runs on
every PR with no browser needed. This script is called from the
preprod-smoke.yml workflow and can be run locally against the live
site at any time.
"""
from __future__ import annotations
import sys


EXPECTED_TITLE_SUBSTRING = "Attsis Job Board"
BOARD_SELECTOR = ".job, #quickstartPanel, #uploadPanel"
WAIT_TIMEOUT_MS = 15000


def smoke(url: str) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    failures: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context()
            page = ctx.new_page()
            page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))
            page.on("console", lambda msg: console_errors.append(f"console.error: {msg.text}") if msg.type == "error" else None)
            try:
                page.goto(url, wait_until="load", timeout=WAIT_TIMEOUT_MS)
            except Exception as e:
                failures.append(f"page.goto({url!r}) failed: {e}")
                return _report(failures, console_errors)

            title = page.title()
            if EXPECTED_TITLE_SUBSTRING not in title:
                failures.append(f"title missing {EXPECTED_TITLE_SUBSTRING!r}: got {title!r}")

            try:
                page.wait_for_selector(BOARD_SELECTOR, timeout=WAIT_TIMEOUT_MS)
            except Exception:
                failures.append(f"neither job card nor setup form rendered within {WAIT_TIMEOUT_MS}ms")

        finally:
            browser.close()

    return _report(failures, console_errors)


def _report(failures: list[str], console_errors: list[str]) -> int:
    for e in console_errors:
        failures.append(e)
    if failures:
        print("FAIL incognito smoke:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("PASS incognito smoke")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python incognito_smoke.py <url>", file=sys.stderr)
        sys.exit(2)
    sys.exit(smoke(sys.argv[1]))
