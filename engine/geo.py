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
import re

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
    # JB-81 (map Phase B): cities seen in live postings without coordinates (2026-10-09 sweep),
    # plus common Canadian / US / world tech cities. Approximate city centres, city precision.
    "barrie": (44.3894, -79.6903, "ca"), "peterborough": (44.3091, -78.3197, "ca"),
    "kingston": (44.2312, -76.4860, "ca"), "windsor": (42.3149, -83.0364, "ca"),
    "sarnia": (42.9745, -82.4066, "ca"), "niagara falls": (43.0896, -79.0849, "ca"),
    "st. catharines": (43.1594, -79.2469, "ca"), "st catharines": (43.1594, -79.2469, "ca"),
    "oshawa": (43.8971, -78.8658, "ca"), "whitby": (43.8975, -78.9429, "ca"),
    "pickering": (43.8384, -79.0868, "ca"), "ajax": (43.8509, -79.0204, "ca"),
    "vaughan": (43.8361, -79.4983, "ca"), "newmarket": (44.0592, -79.4613, "ca"),
    "milton": (43.5183, -79.8774, "ca"), "sudbury": (46.4917, -80.9930, "ca"),
    "thunder bay": (48.3809, -89.2477, "ca"), "quebec city": (46.8139, -71.2080, "ca"),
    "saskatoon": (52.1332, -106.6700, "ca"), "regina": (50.4452, -104.6189, "ca"),
    "winnipeg": (49.8951, -97.1384, "ca"), "kelowna": (49.8880, -119.4960, "ca"),
    "fredericton": (45.9636, -66.6431, "ca"), "moncton": (46.0878, -64.7782, "ca"),
    "st. john's": (47.5615, -52.7126, "ca"),
    "ann arbor": (42.2808, -83.7430, "us"), "detroit": (42.3314, -83.0458, "us"),
    "atlanta": (33.7490, -84.3880, "us"), "dallas": (32.7767, -96.7970, "us"),
    "fort worth": (32.7555, -97.3308, "us"), "blacksburg": (37.2296, -80.4139, "us"),
    "fayetteville": (36.0626, -94.1574, "us"), "houston": (29.7604, -95.3698, "us"),
    "phoenix": (33.4484, -112.0740, "us"), "pittsburgh": (40.4406, -79.9959, "us"),
    "raleigh": (35.7796, -78.6382, "us"), "portland": (45.5152, -122.6784, "us"),
    "minneapolis": (44.9778, -93.2650, "us"), "salt lake city": (40.7608, -111.8910, "us"),
    "philadelphia": (39.9526, -75.1652, "us"), "miami": (25.7617, -80.1918, "us"),
    "sunnyvale": (37.3688, -122.0363, "us"), "mountain view": (37.3861, -122.0839, "us"),
    "palo alto": (37.4419, -122.1430, "us"), "redmond": (47.6740, -122.1215, "us"),
    "columbus": (39.9612, -82.9988, "us"), "cleveland": (41.4993, -81.6944, "us"),
    "buffalo": (42.8864, -78.8784, "us"), "rochester": (43.1566, -77.6088, "us"),
    "irvine": (33.6846, -117.8265, "us"), "boulder": (40.0150, -105.2705, "us"),
    "nashville": (36.1627, -86.7816, "us"), "orlando": (28.5383, -81.3792, "us"),
    "tampa": (27.9506, -82.4572, "us"), "st. louis": (38.6270, -90.1994, "us"),
    "kansas city": (39.0997, -94.5786, "us"), "indianapolis": (39.7684, -86.1581, "us"),
    "madison": (43.0731, -89.4012, "us"), "milwaukee": (43.0389, -87.9065, "us"),
    "charlotte": (35.2271, -80.8431, "us"), "baltimore": (39.2904, -76.6122, "us"),
    "las vegas": (36.1699, -115.1398, "us"), "sacramento": (38.5816, -121.4944, "us"),
    "singapore": (1.3521, 103.8198, "sg"), "katowice": (50.2649, 19.0238, "pl"),
    "krakow": (50.0647, 19.9450, "pl"), "kraków": (50.0647, 19.9450, "pl"),
    "warsaw": (52.2297, 21.0122, "pl"), "wroclaw": (51.1079, 17.0385, "pl"),
    "gdansk": (54.3520, 18.6466, "pl"), "taipei": (25.0330, 121.5654, "tw"),
    "hsinchu": (24.8138, 120.9675, "tw"), "kuala lumpur": (3.1390, 101.6869, "my"),
    "penang": (5.4164, 100.3327, "my"), "shanghai": (31.2304, 121.4737, "cn"),
    "beijing": (39.9042, 116.4074, "cn"), "shenzhen": (22.5431, 114.0579, "cn"),
    "guadalupe": (25.6767, -100.2564, "mx"), "monterrey": (25.6866, -100.3161, "mx"),
    "mexico city": (19.4326, -99.1332, "mx"), "guadalajara": (20.6597, -103.3496, "mx"),
    "bridgetown": (13.1132, -59.5988, "bb"), "christ church": (13.0700, -59.5300, "bb"),
    "hyderabad": (17.3850, 78.4867, "in"), "pune": (18.5204, 73.8567, "in"),
    "chennai": (13.0827, 80.2707, "in"), "mumbai": (19.0760, 72.8777, "in"),
    "noida": (28.5355, 77.3910, "in"), "gurugram": (28.4595, 77.0266, "in"),
    "gurgaon": (28.4595, 77.0266, "in"), "delhi": (28.7041, 77.1025, "in"),
    "tel aviv": (32.0853, 34.7818, "il"), "berlin": (52.5200, 13.4050, "de"),
    "munich": (48.1351, 11.5820, "de"), "paris": (48.8566, 2.3522, "fr"),
    "amsterdam": (52.3676, 4.9041, "nl"), "dublin": (53.3498, -6.2603, "ie"),
    "madrid": (40.4168, -3.7038, "es"), "barcelona": (41.3874, 2.1686, "es"),
    "tokyo": (35.6762, 139.6503, "jp"), "seoul": (37.5665, 126.9780, "kr"),
    "sydney": (-33.8688, 151.2093, "au"), "melbourne": (-37.8136, 144.9631, "au"),
    "stockholm": (59.3293, 18.0686, "se"), "manila": (14.5995, 120.9842, "ph"),
    "bucharest": (44.4268, 26.1025, "ro"), "cluj": (46.7712, 23.6236, "ro"),
    "prague": (50.0755, 14.4378, "cz"), "lisbon": (38.7223, -9.1393, "pt"),
}

_COUNTRY_CENTROID = {                # 'ca' intentionally absent (too large to guess)
    "us": (39.5, -98.35), "in": (22.0, 79.0), "rs": (44.0, 21.0), "ch": (46.8, 8.2),
    "de": (51.0, 10.0), "gb": (54.0, -2.0), "es": (40.0, -4.0), "fr": (46.0, 2.0),
    "nl": (52.1, 5.3), "ie": (53.4, -8.0),
    "pl": (52.0, 19.0), "sg": (1.35, 103.82), "tw": (23.7, 121.0), "my": (4.2, 101.9),
    "cn": (35.0, 103.0), "mx": (23.6, -102.5), "bb": (13.19, -59.54), "jp": (36.2, 138.25),
    "kr": (36.5, 127.9), "au": (-25.3, 133.8), "il": (31.0, 35.0), "se": (60.1, 18.6),
    "ph": (12.9, 121.8), "vn": (14.1, 108.3), "br": (-14.2, -51.9), "ro": (45.9, 24.97),
    "cz": (49.8, 15.47), "pt": (39.4, -8.2), "it": (41.9, 12.6),
}

_COUNTRY_NAMES = {
    "canada": "ca", "united states": "us", " usa": "us", "india": "in", "serbia": "rs",
    "switzerland": "ch", "germany": "de", "united kingdom": "gb", " u.k": "gb",
    "england": "gb", "spain": "es", "france": "fr", "netherlands": "nl", "ireland": "ie",
    "poland": "pl", "singapore": "sg", "taiwan": "tw", "malaysia": "my", "china": "cn",
    "mexico": "mx", "barbados": "bb", "japan": "jp", "korea": "kr", "australia": "au",
    "israel": "il", "sweden": "se", "philippines": "ph", "vietnam": "vn", "brazil": "br",
    "romania": "ro", "czech": "cz", "portugal": "pt", "italy": "it",
}
# JB-81: codes that only count as whole tokens ("TWN - Taipei", "Shanghai, cn", "USA Remote", "U.S")
_COUNTRY_TOKENS = [(re.compile(r"\b(?:usa|u\.s\.?a?)\b|\bu\.s\b"), "us"), (re.compile(r"\btwn\b"), "tw"),
                   (re.compile(r",\s*cn\b"), "cn"), (re.compile(r"\bmys\b"), "my")]
# Province / state codes are read from the ORIGINAL-case text (", MI", ", ON") so prose words don't match.
_CA_PROV = re.compile(r"(?:,|\s-)\s*(?:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE)\b")
_US_STATE = re.compile(r"(?:,|\s-)\s*(?:AL|AK|AZ|AR|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b")

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


def _country_in(t, raw=""):
    for name, code in _COUNTRY_NAMES.items():
        if name in t:
            return code
    for rx, code in _COUNTRY_TOKENS:
        if rx.search(t):
            return code
    if raw and _CA_PROV.search(raw):
        return "ca"
    if raw and _US_STATE.search(raw):
        return "us"
    return None


def _city_in(t):
    # JB-81: whole-word match, so "milton" doesn't fire inside "hamilton" or "paris" inside "comparison"
    matches = [name for name in _C if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", t)]
    return max(matches, key=len) if matches else None   # longest match wins


_AMBIGUOUS = {                                    # bare name -> [(qualifiers, target key in _C)]
    "london": [
        ((" on", " ontario"), "london"),                              # London ON (default entry)
        ((" uk", " england", " gb", " united kingdom"), "london uk"), # London UK
    ],
}


def locate(location):
    """(lat, lng, precision) where precision in {'remote','city','country',None}."""
    raw = location or ""
    t = raw.lower()
    if not t:
        return None, None, None
    country = _country_in(t, raw)
    ck = _city_in(t)
    # JB-81: "London, Ontario or Remote" / "Remote or Mississauga" name a real place — plot it.
    # Pure remote ("Remote (Canada)", "Remote - US") stays unplaced. Rings are unaffected:
    # _ring_single() still treats any "remote" posting as remote / ring 1.
    if "remote" in t and not ck:
        return None, None, "remote"
    # JB-56 (DeepTrekker fix): bare "London" is ambiguous between London ON and London UK.
    # Halma-tenant Workday postings say "London" alone but usually mean London UK; we were
    # stamping them as London ON (ring 0 from BT's home) and placing DT/other subs there
    # on the map. Require a country/state qualifier before matching, and ROUTE to the right
    # coord entry when a qualifier is present. Home resolution in _ring_single uses
    # _city_in directly, so a bare "London" home still works via that path.
    if ck in _AMBIGUOUS and country is None:
        routed = None
        for qualifiers, target in _AMBIGUOUS[ck]:
            if any(q in t for q in qualifiers):
                routed = target
                break
        ck = routed
    if ck and (country is None or _C[ck][2] == country):
        return _C[ck][0], _C[ck][1], "city"          # city matches (or no country stated)
    if country and country != "ca" and country in _COUNTRY_CENTROID:
        c = _COUNTRY_CENTROID[country]
        return c[0], c[1], "country"                  # foreign -> country centroid
    if ck:
        return _C[ck][0], _C[ck][1], "city"           # city known, country unknown
    return None, None, None


def home_coords(home):
    """JB-81: coordinates for the USER'S home. Unlike job locations, a bare ambiguous
    name ("London") resolves to its default entry (London, ON), matching _ring_single."""
    lat, lng, _ = locate(home)
    if lat is None:
        hc = _city_in((home or "").lower())
        if hc:
            lat, lng = _C[hc][0], _C[hc][1]
    return lat, lng


def coords_of(location):
    """(lat, lng) for plotting; None,None if unresolved."""
    lat, lng, _ = locate(location)
    return lat, lng


def city_key(text):   # kept for backward-compat (build_board / tests)
    t = (text or "").lower()
    if "remote" in t:
        return "remote"
    return _city_in(t)


def split_locations(location: str) -> list:
    """JB-34: "Austin, TX; Santa Clara, CA; Toronto, ON" -> ["Austin, TX", "Santa Clara, CA", "Toronto, ON"].
    Splits on ";" and "|". A single location returns a one-item list; empty -> []."""
    parts = [p.strip() for chunk in (location or "").split(";") for p in chunk.split("|")]
    return [p for p in parts if p]


def nearest_location(home: str, location: str) -> str:
    """JB-34: of a multi-location posting, the part closest to the user's home.
    Parts that can't be placed (or say remote) are skipped; if none can be placed, the first part."""
    parts = split_locations(location)
    if len(parts) <= 1:
        return parts[0] if parts else (location or "")
    best, best_km = None, None
    for p in parts:
        if "remote" in p.lower():
            continue
        ring, km, _ = _ring_single(home, p)
        if km is not None and (best_km is None or km < best_km):
            best, best_km = p, km
    return best or parts[0]


def _ring_single(home: str, location: str):
    """Return (ring:int|None, km:float|None, is_remote:bool) for a job vs the user's home."""
    if "remote" in (location or "").lower():
        return 1, None, True
    hlat, hlng = home_coords(home)
    lat, lng, _ = locate(location)
    if hlat is None or lat is None:
        return None, None, False
    km = _haversine((hlat, hlng), (lat, lng))
    for limit, ring in RING_BANDS:
        if km <= limit:
            return ring, round(km), False
    return 4, round(km), False


def ring_for(home: str, location: str):
    """Return (ring:int|None, km:float|None, is_remote:bool) for a job vs the user's home.
    JB-34: multi-location postings are measured to the location nearest home."""
    if "remote" in (location or "").lower() and len(split_locations(location)) <= 1:
        return _ring_single(home, location)
    return _ring_single(home, nearest_location(home, location))
