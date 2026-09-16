import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import cv_parse

SAMPLE = """Bharanidharan Thamizhchelvan, P.Eng. Electronics Design Engineer.
11+ years. Analog and digital mixed-signal PCB design, schematic capture, Altium,
KiCad, ARM Cortex-M STM32 Nordic, embedded C, Zephyr RTOS, BLE, SPI, oscilloscope,
Python SCPI test automation, ISO 13485, IEC 60601, bring-up and V&V."""

def test_build_profile_from_text():
    p = cv_parse.build_profile(SAMPLE, "sample.md")
    assert p["years_general"] == 11
    m = p["model"]
    assert m["skill_confirmers"]                     # non-empty
    assert "altium" in m["skill_confirmers"]         # backed by CV
    assert m["title_triggers"]["core"]               # curated titles retained
    assert "iso 13485" in p["cv_evidence"]["medical"]["backed"]

def test_read_md(tmp_path):
    f = tmp_path / "cv.md"; f.write_text(SAMPLE, encoding="utf-8")
    assert "altium" in cv_parse.read_cv(str(f)).lower()

def test_thin_cv_keeps_base_floor():
    # a CV with <8 backed confirmers must fall back to the full base set
    p = cv_parse.build_profile("Firmware engineer with analog experience.", "thin.md")
    assert len(p["model"]["skill_confirmers"]) >= 8
