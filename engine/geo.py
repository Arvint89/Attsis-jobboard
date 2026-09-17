"""
geo.py -- user-relative distance -> rings, with country-aware resolution (JB-25).

Rings are distance from the CURRENT user's home city. Someone in London sees
Waterloo in ring 1; someone in Kitchener sees Waterloo in ring 0.

Resolution order for a job's location:
  1. remote            -> ring 1 (near everyone), flagged
  2. a known city      -> its real coordinates (city-precise)
  3. a known country   -> that country's centroid (far, correct ring) — fixes the
                          bug where foreign roles (Bengaluru, Santa Clara) inherited
                          the company's HQ ring
Canada has no centroid fallback on purpose (too large to guess from the middle);
a Canadian location with an unrecognised city returns None, and build_board then
falls back to the registry ring for it (same country, reasonable).

Deterministic + offline (no geocoding API). locate() also returns lat/lng so the
job can be plotted on a map (JB-26).
"""
from __future__ import annotations
import math

# name -> (lat, lon, country_code). Ontario/Canada + US tech hubs + world cities.
_C = {
    # Canada
    "london": (42.9849, -81.2453, "ca"), "st thomas": (42.7789, -81.1830, "ca"),
    "kitchener": (43.4516, -80.4925, "ca"), "waterloo": (43.4643, -80.5204, "ca"),
    "cambridge": (43.3616, -80.3144, "ca"), "guelph": (43.5448, -80.2482, "ca"),
    "stratford": (43.3701, -80.9820, "ca"), "woodstock": (43.1301, -80.7467, "ca"),
    "toronto": (43.6532, -79.3832, "ca"), "mississauga": (43.5890, -79.6441, "ca"),
    "oakville": (43.4675, -79.6877, "ca"), "burlington": (43.3255, -79.7990, "ca"),
    "hamilton": (43.2557, -79.8711, "ca"), "markham": (43.8561, -79.3370, "ca"),
    "brampton": (43.7315, -79.7624, "ca"), "richmond hill": (43.8828, -79.4403, "ca"),
    "aurora": (44.0065, -79.4504, "ca"), "ottawa": (45.4215, -75.6972, "ca"),
    "kanata": (45.3088, -75.8988, "ca"), "nepean": (45.3211, -75.7285, "ca"),
    "montreal": (45.5019, -73.5674, "ca"), "sherbrooke": (45.4042, -71.8929, "ca"),
    "vancouver": (49.2827, -123.1207, "ca"), "burnaby": (49.2488, -122.9805, "ca"),
    "victoria": (48.4284, -123.3656, "ca"), "richmond": (49.1666, -123.1336, "ca"),
    "calgary": (51.0447, -114.0719, "ca"), "edmonton": (53.5461, -113.4938, "ca"),
    "halifax": (44.6488, -63.5752, "ca"), "dartmouth": (44.6710, -63.5772, "ca"),
    # US
    "austin": (30.2672, -97.7431, "us"), "santa clara": (37.3541, -121.9552, "us"),
    "san jose": (37.3382, -121.8863, "us"), "san francisco": (37.7749, -122.4194, "us"),
    "seattle": (47.6062, -122.3321, "us"), "boston": (42.3601, -71.0589, "us"),
    "new york": (40.7128, -74.0060, "us"), "fort collins": (40.5853, -105.0844, "us"),
    "los angeles": (34.0522, -118.2437, "us"), "chicago": (41.8781, -87.6298, "us"),
    "denver": (39.7392, -104.9903, "us"), "san diego": (32.7157, -117.1611, "us"),
    # world
    "bengaluru": (12.9716, 77.5946, "in"), "bangalore": (12.9716, 77.5946, "in"),
    "belgrade": (44.7866, 20.4489, "rs"), "zurich": (47.3769, 8.5417, "ch"),
    "zürich": (47.3769, 8.5417, "ch"), "london uk": (51.5074, -0.1278, "gb"),
}

_COUNTRY_CENTROID = {                # 'ca' intentionally absent (too large to guess)
    "us": (39.5, -98.35), "in": (22.0, 79.0), "rs": (44.0, 21.0), "ch": (46.8, 8.2),
    "de": (51.0, 10.0), "gb": (54.0, -2.0), "es": (40.0, -4.0), "fr": (46.0, 2.0),
    "nl": (52.1, 5.3), "ie": (53.4, -8.0),
}

_COUNTRY_NAMES = {
    "canada": "ca", "united states": "us", " usa": "us", "india": "in", "serbia": "rs",
    "switzerland": "ch", "germany": "de", "united kingdom": "gb", " u.k": "gb",
    "england": "gb", "spain": "es", "france": "fr", "netherlands": "nl", "ireland": "ie",
}

CITY_COORDS = _C   # backward-compat alias (cv_parse iterates the city names)

RING_BANDS = [(30, 0), (120, 1), (250, 2), (500, 3)]  # km -> ring; else 4


def _haversine(a, b):
    R = 6371.0
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def _country_in(t):
    for name, code in _COUNTRY_NAMES.items():
        if name in t:
            return code
    return None


def _city_in(t):
    matches = [name for name in _C if name in t]
    return max(matches, key=len) if matches else None   # longest match wins


def locate(location):
    """(lat, lng, precision) where precision in {'remote','city','country',None}."""
    t = (location or "").lower()
    if not t:
        return None, None, None
    if "remote" in t:
        return None, None, "remote"
    country = _country_in(t)
    ck = _city_in(t)
    if ck and (country is None or _C[ck][2] == country):
        return _C[ck][0], _C[ck][1], "city"          # city matches (or no country stated)
    if country and country != "ca" and country in _COUNTRY_CENTROID:
        c = _COUNTRY_CENTROID[country]
        return c[0], c[1], "country"                  # foreign -> country centroid
    if ck:
        return _C[ck][0], _C[ck][1], "city"           # city known, country unknown
    return None, None, None


def coords_of(location):
    """(lat, lng) for plotting; None,None if unresolved."""
    lat, lng, _ = locate(location)
    return lat, lng


def city_key(text):   # kept for backward-compat (build_board / tests)
    t = (text or "").lower()
    if "remote" in t:
        return "remote"
    return _city_in(t)


def ring_for(home: str, location: str):
    """Return (ring:int|None, km:float|None, is_remote:bool) for a job vs the user's home."""
    if "remote" in (location or "").lower():
        return 1, None, True
    hlat, hlng, _ = locate(home)
    if hlat is None:
        hc = _city_in((home or "").lower())
        if hc:
            hlat, hlng = _C[hc][0], _C[hc][1]
    lat, lng, _ = locate(location)
    if hlat is None or lat is None:
        return None, None, False
    km = _haversine((hlat, hlng), (lat, lng))
    for limit, ring in RING_BANDS:
        if km <= limit:
            return ring, round(km), False
    return 4, round(km), False
