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

_COUNTRY_NAME = {"us": "US", "ca": "Canada", "in": "India", "rs": "Serbia",
                 "ch": "Switzerland", "de": "Germany", "gb": "UK", "es": "Spain",
                 "fr": "France", "nl": "Netherlands", "ie": "Ireland"}

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
    code = geo._country_in(t)                       # explicit country name in the string
    if not code:                                    # else infer from a known city
        ck = geo._city_in(t)
        if ck:
            code = geo._C[ck][2]
    if code:
        return _COUNTRY_NAME.get(code, code.upper())
    if "canada" in t or any(s in t for s in (", on", ", qc", ", bc", ", ab", ", ns")):
        return "Canada"
    if "remote" in t:
        return "Canada"   # registry is Canada-first; refine if a country is named
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


# ---------------------------------------------------------------------------
# JB-6: salary from free text (for ATSs that give no structured salary field)
# ---------------------------------------------------------------------------
import re as _re

_AMT = r"(?:(CAD|USD|C\$|US\$|\$)\s?)(\d{1,3}(?:[,\u00a0 ]\d{3})+|\d+(?:\.\d{1,2})?)\s?([kK])?(?![\d.]*\s?(?:[mMbB]\b|million|billion))"
_RANGE = _re.compile(_AMT + r"(?:\s*(?:-|\u2013|\u2014|to)\s*(?:(CAD|USD|C\$|US\$|\$)\s?)?(\d{1,3}(?:[,\u00a0 ]\d{3})+|\d+(?:\.\d{1,2})?)\s?([kK])?)?")
_PAY_WORDS = _re.compile(r"salary|compensation|pay\b|pay range|base pay|wage|hourly rate|rate of pay|per hour|annual", _re.I)
_HOUR = _re.compile(r"^.{0,30}?(per hour|/\s?hour|/\s?hr\b|an hour|hourly)", _re.I | _re.S)
_YEAR = _re.compile(r"^.{0,30}?(per year|/\s?year|/\s?yr\b|a year|annually|per annum|annual)", _re.I | _re.S)
_CUR = _re.compile(r"^.{0,12}?\b(CAD|USD)\b", _re.S)


def _num(txt: str, k: str | None) -> float:
    v = float(_re.sub(r"[,\u00a0 ]", "", txt))
    return v * 1000 if k else v


def _money(v: float) -> str:
    return f"${v:,.2f}" if v != int(v) else f"${v:,.0f}"


def salary_from_text(text: str) -> str:
    """Best-effort pay range from a job description, e.g. '$100,000–$150,000 USD/year'.

    Accepts a match only if it looks like pay: a pay keyword in the 150 chars before it,
    or a per-hour / per-year marker right after it. Sanity bounds: hourly 10-300,
    annual 20,000-1,000,000. Anything else (funding rounds, budgets, 401k) -> ''.
    """
    if not text:
        return ""
    for m in _RANGE.finditer(text):
        cur1, a, ka, cur2, b, kb = m.groups()
        lo = _num(a, ka)
        hi = _num(b, kb) if b else None
        after = text[m.end():m.end() + 40]
        before = text[max(0, m.start() - 150):m.start()]
        per = "hour" if _HOUR.match(after) else ("year" if _YEAR.match(after) else "")
        if not per and not _PAY_WORDS.search(before):
            continue
        top = hi or lo
        if not per:
            per = "year" if top >= 20000 else ("hour" if 10 <= top <= 300 else "")
        if per == "hour" and not (10 <= lo <= 300 and (hi is None or 10 <= hi <= 300)):
            continue
        if per == "year" and not (20000 <= lo <= 1_000_000 and (hi is None or 20000 <= hi <= 1_000_000)):
            continue
        if not per:
            continue
        codes = {"CAD": "CAD", "C$": "CAD", "USD": "USD", "US$": "USD"}
        cur = codes.get(cur1 or "", "") or codes.get(cur2 or "", "")
        if not cur:
            mc = _CUR.match(after)
            cur = mc.group(1) if mc else ""
        span = _money(lo) + ("\u2013" + _money(hi) if hi and hi != lo else "")
        return span + (" " + cur if cur else "") + "/" + per
    return ""
