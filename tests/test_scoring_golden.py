"""JB-38 golden set, built from the daily-sweep log (BT's own verdicts, Sep 2026).

Roles the sweep rated 7+ must score >= 7 on the board; roles the sweep called off-profile
(IC/silicon gap, power, sales, pure software) must stay below 7 or be excluded.
Descriptions are condensed from the real postings.
"""
import os, sys
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import jobfilter as jf

TODAY = date.today().isoformat()


@pytest.fixture(autouse=True)
def _home_is_london(monkeypatch):
    # conftest forces the generic base model (no home). The sweep verdicts are BT's, from London.
    monkeypatch.setattr(jf, "HOME", "london")


def job(title, loc, desc=""):
    return {"title": title, "location": loc, "description": desc, "posted": TODAY}


STRONG = [
    # Kepler, via MaRS/Getro: no description, only skill tags (the case that scored 4)
    ("Kepler stub", job("Senior Embedded Software Designer", "Toronto, ON, Canada",
        "Embedded Software Linux Device Drivers Hardware Interface Design Automated Testing Framework Systems Design")),
    ("Kepler full JD", job("Senior Embedded Software Designer", "Toronto, ON, Canada",
        "Design and ship embedded C firmware for satellite payloads on an RTOS and embedded Linux. "
        "Bring-up of new boards with the hardware team, SPI and I2C drivers, debugging with an "
        "oscilloscope and logic analyzer, STM32 and Zynq/Xilinx parts, low-power design reviews.")),
    ("Xanadu Sr EE", job("Senior Electrical Engineer", "Toronto, ON, Canada",
        "Own low-noise analog and mixed-signal PCB design for control and data acquisition: schematic "
        "capture and PCB layout in Altium, ADC/DAC front ends, bring-up and characterization with an "
        "oscilloscope and VNA, component selection and design reviews.")),
    ("BinSentry EE", job("Electronics Engineer", "Kitchener, Ontario",
        "Design low-power IoT electronics: schematic and PCB layout in Altium, BLE radios, battery "
        "systems, component selection, DFM with the contract manufacturer, board bring-up, firmware "
        "support in embedded C.")),
    ("Flosonics Sr EE", job("Senior Electrical Engineer", "Toronto, ON, Canada",
        "Medical device electronics: analog front end and mixed-signal design, schematic and PCB layout, "
        "component selection, verification testing with an oscilloscope, design documentation to ISO 13485.")),
    ("Myant R&D EE", job("R&D Electrical Engineer (On-Site)", "Mississauga, ON, Canada",
        "Textile-integrated electronics: schematic capture, PCB layout, low-power analog sensing, BLE "
        "wireless, battery management, prototype bring-up and test.")),
    ("Hitachi Rail designer", job("Hardware Electrical Designer, Senior", "Toronto, ON, Canada",
        "Board-level hardware design for rail signalling: schematic capture, PCB layout review, analog "
        "and digital circuits, component selection, DFM, hardware verification.")),
]

WEAK = [
    ("Tenstorrent physical design (IC gap)", job("Physical Design Engineer", "Toronto, Ontario, Canada",
        "RTL to GDSII, place and route, static timing analysis, DFT insertion, digital implementation "
        "flows for AI accelerator silicon, tapeout sign-off.")),
    ("Xanadu analog ASIC (IC gap)", job("Senior Analog ASIC Design Engineer", "Toronto, ON, Canada",
        "Analog and mixed-signal ASIC design, transistor-level schematic, tapeout, silicon bring-up.")),
    ("Power/substation EE", job("Electrical Engineer", "London, ON",
        "Substation protection and control, power distribution, switchgear, transformer design, "
        "high-voltage grid studies.")),
]

EXCLUDED = [
    ("Sales", job("Sales Engineer", "Toronto, ON", "Quota, CRM, customer demos.")),
    ("Full stack", job("Senior Full Stack Developer", "Toronto, ON", "React, Node, backend APIs, full-stack web.")),
]


@pytest.mark.parametrize("name,j", STRONG, ids=[n for n, _ in STRONG])
def test_sweep_strong_roles_score_7_plus(name, j):
    r = jf.classify(j)
    assert r["score"] >= 7, f"{name}: {r['score']} {r['reasons']}"


@pytest.mark.parametrize("name,j", WEAK, ids=[n for n, _ in WEAK])
def test_sweep_offprofile_roles_stay_below_7(name, j):
    r = jf.classify(j)
    assert r["verdict"] == "excluded" or r["score"] < 7, f"{name}: {r['score']} {r['reasons']}"


@pytest.mark.parametrize("name,j", EXCLUDED, ids=[n for n, _ in EXCLUDED])
def test_sweep_noise_is_excluded(name, j):
    assert jf.classify(j)["verdict"] == "excluded"


def test_missing_description_is_not_penalised():
    r = jf.classify(job("Hardware Engineer", "London, ON", ""))
    assert "no skills in body" not in r["reasons"]
    assert any("no description" in x for x in r["reasons"])


def test_designer_and_developer_variants_count_as_title_match():
    for t in ("Hardware Designer", "Embedded Developer", "Electronics Designer", "Firmware Designer"):
        r = jf.classify(job(t, "Toronto, ON", "schematic, PCB layout, firmware in embedded C"))
        assert any(x.startswith("title match") for x in r["reasons"]), (t, r["reasons"])


def test_commutable_distance_gets_the_bonus():
    near = jf.classify(job("Hardware Engineer", "Toronto, ON", "schematic, pcb layout"))
    far = jf.classify(job("Hardware Engineer", "Vancouver, BC", "schematic, pcb layout"))
    assert near["score"] == far["score"] + 1
