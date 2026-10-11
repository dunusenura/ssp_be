"""
Geocoding utility for WorkPub platform.
Provides accurate coordinates for Sri Lankan cities, towns, and regions (especially Gampaha District),
with normalization, fuzzy matching, and fallback resolution.
"""
import re
import urllib.request
import urllib.parse
import json

# Comprehensive coordinates mapping for Sri Lankan towns & localities
LOCATION_COORDINATES = {
    # Gampaha District Towns & Cities
    "mirigama": {"lat": 7.2475, "lon": 80.1299, "name": "Mirigama"},
    "meerigama": {"lat": 7.2475, "lon": 80.1299, "name": "Mirigama"},
    "gampaha": {"lat": 7.0873, "lon": 80.0144, "name": "Gampaha"},
    "gampaha town": {"lat": 7.0873, "lon": 80.0144, "name": "Gampaha Town"},
    "gampaha city": {"lat": 7.0873, "lon": 80.0144, "name": "Gampaha City"},
    "veyangoda": {"lat": 7.1500, "lon": 80.0500, "name": "Veyangoda"},
    "minuwangoda": {"lat": 7.1668, "lon": 79.9681, "name": "Minuwangoda"},
    "yakkala": {"lat": 7.0873, "lon": 80.0382, "name": "Yakkala"},
    "kadawatha": {"lat": 7.0016, "lon": 79.9490, "name": "Kadawatha"},
    "negombo": {"lat": 7.2111, "lon": 79.8517, "name": "Negombo"},
    "ja-ela": {"lat": 7.0844, "lon": 79.8864, "name": "Ja-Ela"},
    "ja ela": {"lat": 7.0844, "lon": 79.8864, "name": "Ja-Ela"},
    "wattala": {"lat": 6.9813, "lon": 79.8913, "name": "Wattala"},
    "kelaniya": {"lat": 6.9764, "lon": 79.9064, "name": "Kelaniya"},
    "kiribathgoda": {"lat": 6.9806, "lon": 79.9272, "name": "Kiribathgoda"},
    "ragama": {"lat": 7.0250, "lon": 79.9210, "name": "Ragama"},
    "kandana": {"lat": 7.0388, "lon": 79.8710, "name": "Kandana"},
    "nittambuwa": {"lat": 7.1448, "lon": 80.1065, "name": "Nittambuwa"},
    "ganemulla": {"lat": 7.0620, "lon": 79.9575, "name": "Ganemulla"},
    "weliweriya": {"lat": 7.0333, "lon": 80.0167, "name": "Weliweriya"},
    "weliveriya": {"lat": 7.0333, "lon": 80.0167, "name": "Weliweriya"},
    "makola": {"lat": 6.9833, "lon": 79.9333, "name": "Makola"},
    "kotugoda": {"lat": 7.1147, "lon": 79.9328, "name": "Kotugoda"},
    "seeduwa": {"lat": 7.1264, "lon": 79.8881, "name": "Seeduwa"},
    "katunayake": {"lat": 7.1748, "lon": 79.8817, "name": "Katunayake"},
    "dompe": {"lat": 6.9461, "lon": 80.0543, "name": "Dompe"},
    "delgoda": {"lat": 6.9922, "lon": 80.0225, "name": "Delgoda"},
    "siyabalape": {"lat": 6.9744, "lon": 79.9667, "name": "Siyambalape"},
    "siyambalape": {"lat": 6.9744, "lon": 79.9667, "name": "Siyambalape"},
    "pasyala": {"lat": 7.0800, "lon": 80.0800, "name": "Pasyala"},
    "udugampola": {"lat": 7.1182, "lon": 80.0163, "name": "Udugampola"},
    "miriswatta": {"lat": 7.0500, "lon": 79.9800, "name": "Miriswatta"},
    "kirillawala": {"lat": 7.0376, "lon": 79.9913, "name": "Kirillawala"},
    "divulapitiya": {"lat": 7.2215, "lon": 80.0142, "name": "Divulapitiya"},
    "diulapitiya": {"lat": 7.2215, "lon": 80.0142, "name": "Divulapitiya"},
    "pugoda": {"lat": 6.9667, "lon": 80.1167, "name": "Pugoda"},
    "biyagama": {"lat": 6.9381, "lon": 79.9936, "name": "Biyagama"},
    "radawana": {"lat": 7.0500, "lon": 80.0667, "name": "Radawana"},
    "pamunugama": {"lat": 7.0833, "lon": 79.8500, "name": "Pamunugama"},
    "bopitiya": {"lat": 7.0500, "lon": 79.8667, "name": "Bopitiya"},
    "mahara": {"lat": 7.0167, "lon": 79.9333, "name": "Mahara"},
    "dalugama": {"lat": 6.9667, "lon": 79.9167, "name": "Dalugama"},
    "hunupitiya": {"lat": 6.9833, "lon": 79.8833, "name": "Hunupitiya"},
    "wattala-mabola": {"lat": 6.9813, "lon": 79.8913, "name": "Wattala"},

    # Neighboring Districts & Western Province
    "colombo": {"lat": 6.9271, "lon": 79.8612, "name": "Colombo"},
    "dehiwala": {"lat": 6.8511, "lon": 79.8653, "name": "Dehiwala"},
    "kaduwela": {"lat": 6.9333, "lon": 79.9833, "name": "Kaduwela"},
    "malabe": {"lat": 6.9038, "lon": 79.9547, "name": "Malabe"},
    "thalawathugoda": {"lat": 6.8778, "lon": 79.9297, "name": "Thalawathugoda"},
    "kurunegala": {"lat": 7.4863, "lon": 80.3623, "name": "Kurunegala"},
    "kandy": {"lat": 7.2906, "lon": 80.6337, "name": "Kandy"},
    "kalutara": {"lat": 6.5854, "lon": 79.9607, "name": "Kalutara"},
    "panadura": {"lat": 6.7132, "lon": 79.9074, "name": "Panadura"}
}

DEFAULT_LAT = 7.0873
DEFAULT_LON = 80.0144

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[,/\\_\-.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def resolve_location_coordinates(location_str, existing_lat=None, existing_lon=None):
    """
    Resolves the latitude and longitude for a location string.
    If existing_lat and existing_lon are provided and are not the default fallback (or match the location),
    they will be preserved. Otherwise, exact coordinates for the matched town will be returned.
    """
    clean_loc = normalize_text(location_str)
    
    # Check if existing coordinates are already customized and valid
    has_existing = (
        existing_lat is not None and 
        existing_lon is not None and 
        isinstance(existing_lat, (int, float)) and 
        isinstance(existing_lon, (int, float)) and
        (existing_lat != 0.0 or existing_lon != 0.0)
    )

    # Note: 7.0912 / 79.9991 was the previous static hardcoded default.
    # If the user's location is NOT Gampaha (e.g., 'mirigama', 'veyangoda', etc.),
    # we must NOT retain this incorrect static fallback!
    is_hardcoded_gampaha_default = (
        has_existing and 
        round(float(existing_lat), 3) == 7.091 and 
        round(float(existing_lon), 3) == 80.000
    ) or (
        has_existing and
        round(float(existing_lat), 4) == 7.0912 and
        round(float(existing_lon), 4) == 79.9991
    )

    is_explicit_gampaha = "gampaha" in clean_loc

    # If existing coordinates exist, aren't the erroneous static fallback on non-gampaha locations, keep them
    if has_existing and not (is_hardcoded_gampaha_default and not is_explicit_gampaha):
        # Coordinates already valid
        return float(existing_lat), float(existing_lon), location_str or "Gampaha"

    # Search in dictionary:
    # 1. Direct match
    if clean_loc in LOCATION_COORDINATES:
        match = LOCATION_COORDINATES[clean_loc]
        return match["lat"], match["lon"], match["name"]

    # 2. Key contained in location string or location string contained in key
    # Check multi-word tokens first (e.g., 'gampaha town', 'ja ela')
    for key, data in sorted(LOCATION_COORDINATES.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, clean_loc) or key in clean_loc:
            return data["lat"], data["lon"], data["name"]

    # 3. Word token intersection
    tokens = clean_loc.split()
    for token in tokens:
        if token in LOCATION_COORDINATES:
            match = LOCATION_COORDINATES[token]
            return match["lat"], match["lon"], match["name"]

    # 4. If clean_loc is empty or unable to match, fallback to Gampaha
    return DEFAULT_LAT, DEFAULT_LON, location_str or "Gampaha"
