"""
SO1 — Sri Lankan districts with representative coordinates for synthetic data & map APIs.
"""

# District → (latitude, longitude) approximate district centres
DISTRICT_COORDS = {
    "Colombo": (6.9271, 79.8612),
    "Gampaha": (7.0873, 79.9999),
    "Kalutara": (6.5854, 79.9607),
    "Kandy": (7.2906, 80.6337),
    "Matale": (7.4675, 80.6234),
    "Nuwara_Eliya": (6.9497, 80.7891),
    "Galle": (6.0535, 80.2210),
    "Matara": (5.9549, 80.5550),
    "Hambantota": (6.1241, 81.1185),
    "Jaffna": (9.6615, 80.0255),
    "Kilinochchi": (9.3969, 80.3982),
    "Mannar": (8.9810, 79.9044),
    "Vavuniya": (8.7514, 80.4971),
    "Trincomalee": (8.5874, 81.2152),
    "Batticaloa": (7.7310, 81.6747),
    "Ampara": (7.2970, 81.6825),
    "Badulla": (6.9934, 81.0550),
    "Monaragala": (6.8653, 81.0461),
    "Ratnapura": (6.6828, 80.3992),
    "Kegalle": (7.2513, 80.3464),
    "Kurunegala": (7.4863, 80.3623),
    "Puttalam": (8.0362, 79.8283),
    "Anuradhapura": (8.3114, 80.4037),
    "Polonnaruwa": (7.9396, 81.0009),
    "Negombo": (7.2095, 79.8346),
    "Mirissa": (5.9483, 80.4556),
    "Ella": (6.8728, 81.0466),
    "Sigiriya": (7.9570, 80.7603),
}

DISTRICT_NAMES = list(DISTRICT_COORDS.keys())

# Approximate bounding box for Sri Lanka main island (filters noisy offshore jitter from synthetic coords)
SL_LAT_MIN = 5.78
SL_LAT_MAX = 9.92
SL_LON_MIN = 79.42
SL_LON_MAX = 81.92


def is_likely_sri_lanka_land(lat: float, lon: float) -> bool:
    """Drop obvious ocean/out-of-range points from map layers (demo dataset jitter)."""
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return SL_LAT_MIN <= la <= SL_LAT_MAX and SL_LON_MIN <= lo <= SL_LON_MAX
