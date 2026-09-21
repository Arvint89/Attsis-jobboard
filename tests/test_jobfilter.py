"""Unit tests for the deterministic filter/scorer. Test-first contract:
these encode the acceptance criteria from SPEC.md (FR-3). Run: pytest -q
Each rule has happy / empty / exclusion coverage per the PD rules (min 3)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import jobfilter as jf


def mk(title, desc="", loc="London, ON", posted="2026-09-15"):
    return {"title": title, "description": desc, "location": loc, "posted": posted}


# --- happy path: strong on-profile roles must score >= 7 (match) --------------
def test_core_strong_role_is_match_generic():
    # unified scorer: strong CV-keyword overlap -> match, but NO hardcoded medical boost
    j = mk("Senior Electrical Engineer",
           "Mixed-signal PCB, analog, ISO 13485, IEC 60601-1, Altium, ARM Cortex-M, "
           "embedded C, low-power battery, schematic, signal integrity.",
           loc="Oakville, ON")
    r = jf.classify(j)
    assert r["verdict"] == "match" and r["score"] >= 7
    assert "medical" not in r["flags"]   # domain relevance comes from keywords, not a bonus


def test_core_electronics_design_matches():
    j = mk("Electronics Engineer",
           "Design analog and power circuits in Altium, schematic capture, PCB "
           "layout, bring-up with oscilloscope, SPI I2C UART, firmware in C.")
    assert jf.classify(j)["verdict"] == "match"


def test_fpga_remote_matches():
    j = mk("FPGA Verification Engineer",
           "Verilog, VHDL, RTL design, Vivado, SystemVerilog, design verification.",
           loc="Remote, Canada")
    r = jf.classify(j)
    assert r["verdict"] == "match"
    assert "remote" in r["flags"]


# --- exclusions ---------------------------------------------------------------
def test_power_electrical_scores_low_not_excluded():
    # generic scorer doesn't know "power = wrong field"; it just scores low on no keyword overlap
    r = jf.classify(mk("Electrical Engineer",
           "Substation protection and control, power distribution, switchgear, "
           "transformer design, high-voltage grid."))
    assert r["verdict"] != "match" and r["score"] <= 4


def test_technician_excluded():
    assert jf.classify(mk("CNC Process Technician", "Operate machines."))["verdict"] == "excluded"


def test_pure_software_excluded():
    j = mk("Software Engineer", "Full-stack web developer, React, .NET, backend APIs.")
    assert jf.classify(j)["verdict"] == "excluded"


def test_offprofile_title_excluded():
    assert jf.classify(mk("Account Manager", "Sales quota."))["verdict"] == "excluded"


# --- edge cases ---------------------------------------------------------------
def test_empty_description_not_penalised():
    # JB-38: a source that gives no description (e.g. Getro) must not cost the job a point
    j = mk("Hardware Engineer", "")   # title hits, body empty
    r = jf.classify(j)
    assert "no skills in body" not in r["reasons"]
    assert "no description from source" in r["reasons"]


def test_long_description_without_skills_is_penalised():
    j = mk("Hardware Engineer", "We are a fast-growing company with great benefits and a friendly team. " * 4)
    assert "no skills in body" in jf.classify(j)["reasons"]


def test_stale_posting_excluded():
    j = mk("Embedded Engineer", "firmware, ARM, RTOS", posted="2026-01-01")
    assert jf.classify(j)["verdict"] == "excluded"


def test_electrical_with_electronics_body_not_excluded_as_power():
    # Canada Rocket lesson: an "Electrical" title whose body is electronics must survive
    j = mk("Electrical Design Engineer",
           "PCB schematic capture, analog circuit design, Altium, signal integrity, "
           "power supply design for avionics. Some power distribution on board.")
    assert jf.classify(j)["verdict"] != "excluded"


def test_registry_flags_carried_through():
    r = jf.classify(mk("Embedded Engineer", "firmware ARM RTOS BLE"),
                    extra_flags=["eligibility", "relocation"])
    assert "eligibility" in r["flags"] and "relocation" in r["flags"]
