"""
geo.py -- user-relative distance -> rings.

Rings are NOT absolute; they are distance from the CURRENT user's home city.
Someone in London sees Waterloo in ring 1; someone in Kitchener sees Waterloo in
ring 0 and London in ring 1. Home city comes from the CV (or a --home override).

No geocoding service (keeps it offline/zero-dependency): a small coordinate table
covers the Ontario + Canada cities in the registry. Unknown cities -> ring None,
which the board shows under "distance unknown" rather than guessing.
"""
from __future__ import annotations
import math

# lat, lon for the cities the registry touches (extend as companies are added)
CITY_COORDS = {
    "london": (42.9849, -81.2453), "st thomas": (42.7789, -81.1830),
    "kitchener": (43.4516, -80.4925), "waterloo": (43.4643, -80.5204),
    "cambridge": (43.3616, -80.3144), "guelph": (43.5448, -80.2482),
    "stratford": (43.3701, -80.9820), "woodstock": (43.1301, -80.7467),
    "toronto": (43.6532, -79.3832), "mississauga": (43.5890, -79.6441),
    "oakville": (43.4675, -79.6877), "burlington": (43.3255, -79.7990),
    "hamilton": (43.2557, -79.8711), "markham": (43.8561, -79.3370),
    "brampton": (43.7315, -79.7624), "richmond hill": (43.8828, -79.4403),
    "aurora": (44.0065, -79.4504), "ottawa": (45.4215, -75.6972),
    "kanata": (45.3088, -75.8988), "nepean": (45.3211, -75.7285),
    "montreal": (45.5019, -73.5674), "sherbrooke": (45.4042, -71.8929),
    "vancouver": (49.2827, -123.1207), "burnaby": (49.2488, -122.9805),
    "victoria": (48.4284, -123.3656), "richmond": (49.1666, -123.1336),
    "calgary": (51.0447, -114.0719), "edmonton": (53.5461, -113.4938),
    "halifax": (44.6488, -63.5752), "remote": None,
}

# distance km -> ring
RING_BANDS = [(30, 0), (120, 1), (250, 2), (500, 3)]  # else 4


def _haversine(a, b):
    R = 6371.0
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def city_key(text: str):
    """Best-effort city name from a location string like 'Kitchener, ON, Canada'."""
    if not text:
        return None
    t = text.lower()
    if "remote" in t:
        return "remote"
    for name in CITY_COORDS:
        if name and name in t:
            return name
    return None


def ring_for(home: str, location: str):
    """Return (ring:int|None, km:float|None, is_remote:bool) for a job/company."""
    ck = city_key(location)
    if ck == "remote":
        return 1, None, True          # remote is 'near' everyone -> ring 1, flagged
    home_c = CITY_COORDS.get(city_key(home) or (home or "").lower())
    comp_c = CITY_COORDS.get(ck) if ck else None
    if not home_c or not comp_c:
        return None, None, False
    km = _haversine(home_c, comp_c)
    for limit, ring in RING_BANDS:
        if km <= limit:
            return ring, round(km), False
    return 4, round(km), False
