"""
facets.py -- derive the FILTERABLE facets for a job (replacing decorative flags).

Four facets a job seeker actually filters on:
  - arrangement : onsite | hybrid | remote      (from location + JD text)
  - country     : Canada | US | Other | ?        (from location)
  - industry    : from the company registry (most reliable) with a JD fallback
  - sponsorship : yes | no | unknown             (from JD text + registry override)

Pure functions, no I/O, no LLM. Kept separate from jobfilter (which scores) so the
matching model and the facets evolve independently.
"""
from __future__ import annotations
import geo

_US_HINTS = ("united states", "usa", ", us", " u.s", "california", ", ca ", ", tx",
             ", ny", ", wa", ", ma", "remote from the us")
_CA_CITIES = tuple(c for c in geo.CITY_COORDS if c and c != "remote")

# JD keyword fallback for industry when the registry doesn't say
_INDUSTRY_KEYWORDS = {
    "medical": ["medical device", "iso 13485", "iec 60601", "clinical", "patient"],
    "defence": ["defence", "defense", "itar", "controlled goods", "military"],
    "aerospace/space": ["satellite", "avionics", "aerospace", "spacecraft", "payload", "launch"],
    "semiconductor": ["asic", "fpga fabric", "tapeout", "silicon", "wafer"],
    "automotive": ["automotive", "iso 26262", "vehicle", "adas", "ev "],
    "energy/power": ["battery", "bess", "inverter", "grid", "energy storage", "solar"],
    "rail/industrial": ["rail", "locomotive", "telematics", "industrial automation"],
    "robotics": ["robot", "autonomy", "lidar", "amr", "agv"],
    "iot/connectivity": ["iot", "lorawan", "ble mesh", "connectivity"],
}


def arrangement(location: str, body: str) -> str:
    t = f"{location} {body[:600]}".lower()
    if "hybrid" in t:
        return "hybrid"
    if "remote" in t or "work from home" in t or "wfh" in t:
        # "remote-first", "fully remote", "remote (canada)"
        if "on-site" in t or "onsite" in t or "in office" in t:
            return "hybrid"
        return "remote"
    return "onsite"


def country(location: str) -> str:
    t = (location or "").lower()
    if any(h in t for h in _US_HINTS):
        return "US"
    if "canada" in t or ", on" in t or ", qc" in t or ", bc" in t or ", ab" in t \
       or ", ns" in t or any(c in t for c in _CA_CITIES):
        return "Canada"
    if "remote" in t:
        return "Canada"   # our registry is Canada-first; refine if a country is named
    return "?"


def industry(registry_industry: str, body: str) -> str:
    if registry_industry:
        return registry_industry
    low = (body or "").lower()
    for name, kws in _INDUSTRY_KEYWORDS.items():
        if any(k in low for k in kws):
            return name
    return "other"


def sponsorship(body: str, registry_sponsors) -> str:
    if registry_sponsors is True:
        return "yes"
    if registry_sponsors is False:
        return "no"
    low = (body or "").lower()
    if "no sponsorship" in low or "not able to sponsor" in low \
       or "without sponsorship" in low or "must be legally authorized" in low:
        return "no"
    if "visa sponsorship" in low or "will sponsor" in low or "sponsorship available" in low \
       or "provide sponsorship" in low:
        return "yes"
    return "unknown"
