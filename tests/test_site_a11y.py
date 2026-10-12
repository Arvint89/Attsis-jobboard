"""Accessibility guards (axe-core 4.10 WCAG 2 A/AA audit, 2026-10-12: only violation was unlabeled file inputs)."""
import os
import re

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def test_every_file_input_has_an_accessible_name():
    h = open(INDEX, encoding="utf-8").read()
    inputs = re.findall(r"<input[^>]*type=\"file\"[^>]*>", h)
    assert inputs
    for tag in inputs:
        assert "aria-label=" in tag, tag


def test_mobile_tabbar_rules_come_after_base_rules():
    # equal specificity: the later rule wins, so the phone override must follow the base rule
    h = open(INDEX, encoding="utf-8").read()
    base = h.index("  .tabbar{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 0 24px}")
    mobile = h.index(".tabbar{margin:6px 0 0;order:3;width:100%;flex-wrap:nowrap")
    assert mobile > base
