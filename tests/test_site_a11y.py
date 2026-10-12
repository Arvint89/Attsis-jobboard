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
