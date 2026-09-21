"""model_base.py -- the DEFAULT matching model (single source of truth).

This is the fallback the scorer uses when no CV-derived profile.json is present.
cv_parse.py starts from this base, then marks which terms the CV actually backs
(cv_evidence) and writes profile.json. So: edit the CV -> profile changes -> the
scoreboard changes. Edit this file -> the defaults change.

Values mirror Job_Search_Keywords.md sections 1-5 and 8.
"""
BASE = {
    "title_triggers": {
        "core": [
            "electronics design engineer", "electronics engineer", "hardware engineer",
            "hardware design engineer", "embedded engineer", "embedded software",
            "firmware engineer", "firmware developer", "pcb", "mixed-signal", "mixed signal",
        ],
        "adjacent": [
            "systems engineer", "mechatronics", "product engineer", "sensor engineer",
            "rf engineer", "power electronics", "hardware test", "hardware validation",
            "design engineer", "electrical design", "avionics", "electrical engineer",
        ],
        "fpga": [
            "fpga", "verilog", "vhdl", "rtl", "asic verification", "design verification",
            "verification engineer", "digital design",
        ],
    },
    "skill_confirmers": [
        "analog", "digital", "mixed-signal", "schematic", "pcb layout", "signal integrity",
        "power supply", "dfm", "dft", "bom", "component selection",
        "embedded c", "firmware", "arm cortex", "cortex-m", "stm32", "nordic", "zephyr",
        "rtos", "microcontroller", "low-power", "low power", "battery",
        "ble", "bluetooth low energy", "i2c", "i²c", "spi", "uart", "usb",
        "oscilloscope", "logic analyzer", "vna", "impedance analyzer", "scpi",
        "bring-up", "bring up", "v&v", "altium", "kicad", "ltspice",
        "fpga", "verilog", "vhdl", "rtl", "vivado", "xilinx", "quartus",
    ],
    "boosters": {
        "medical": ["iso 13485", "design controls", "iso 14971", "medical device",
                    "iec 62304", "dhf", "nebulizer", "inhalation", "aerosol", "pulmonary",
                    "respiratory", "drug delivery", "spirometry", "eeg", "biosignal"],
        "iec60601": ["iec 60601", "60601-1", "iec 61010"],
        "space": ["satellite", "payload", "space-qualified", "gnss", "magnetometer",
                  "quantum sensor", "low-noise", "photodetector"],
        "verification": ["systemverilog", "uvm", "design verification", "functional verification"],
    },
    "exclusions": {
        "gap": ["physical design", "asic design", "analog ic", "ic design", "tapeout", "tape-out",
                "place and route", "standard cell"],
        "power": ["substation", "distribution", "high-voltage grid", "building services",
                  "hvac", "protection & control", "protection and control", "power system"],
        "software": ["full-stack", "full stack", "frontend", "front-end", "back-end",
                     "backend", ".net", "salesforce", "web developer", "data engineer",
                     "data analyst", "ui/ux", "react developer"],
        "level": ["technician", "operator", "assembler", "millwright", "welder",
                  "machinist", "cnc", "sales", "marketing", " hr ", "recruit",
                  "administrative", "receptionist", "clerk", "custodian", "driver",
                  "intern", "co-op", "co op", "student", "apprentice"],
        "power_context": ["substation", "distribution", "high-voltage grid", "building services",
                          "hvac", "protection & control", "protection and control", "power system",
                          "kv ", "megawatt", "switchgear", "transformer design"],
    },
    "params": {"report_threshold": 7, "fresh_days": 30},
}
