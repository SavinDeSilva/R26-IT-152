"""
Resolve where the tourist's situation is — from typed/spoken message content (SO3/SO4).
Does NOT use device GPS; coordinates come from matched place names → district centres / landmarks.
"""

from typing import Any, Dict, List

from utils.sri_lanka_geo import DISTRICT_COORDS


def resolve_situation_coordinates(text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer situation location from message + NLP entities only.

    Returns:
        label: human-readable place name
        latitude, longitude: representative coords for that situation
        source: message_entity | message_text | fallback_default
    """
    text = text or ""
    tl = text.lower().strip()
    locs: List[str] = list(entities.get("locations") or [])

    # 1) Strong match: entity strings from extract_entities (district names)
    for raw in locs:
        s = str(raw).strip()
        sl = s.lower()
        for key, (lat, lon) in DISTRICT_COORDS.items():
            disp = key.replace("_", " ")
            if sl == disp.lower() or sl in disp.lower() or disp.lower() in sl:
                return {
                    "label": disp,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "source": "message_entity",
                }

    # 2) Full-text scan for district / town names (including Sinhala/Tamil context via Latin exonyms)
    # Longer names first to prefer "Nuwara Eliya" over "Ella" substrings where ambiguous
    ranked = sorted(
        ((k, v) for k, v in DISTRICT_COORDS.items()),
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for key, (lat, lon) in ranked:
        disp = key.replace("_", " ")
        if disp.lower() in tl:
            return {
                "label": disp,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "source": "message_text",
            }
        unders = key.lower()
        if unders.replace("_", " ") in tl:
            return {
                "label": disp,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "source": "message_text",
            }

    # 3) Keyword anchors commonly used by tourists
    anchors = {
        "fort": ("Colombo", DISTRICT_COORDS["Colombo"]),
        "airport": ("Katunayake area", DISTRICT_COORDS["Gampaha"]),
        "cmb": ("Colombo / airport corridor", DISTRICT_COORDS["Gampaha"]),
        "beach": ("Coastal area", DISTRICT_COORDS["Galle"]),
        "temple of the tooth": ("Kandy", DISTRICT_COORDS["Kandy"]),
        "sigiriya rock": ("Sigiriya", DISTRICT_COORDS["Sigiriya"]),
    }
    for kw, (lab, (lat, lon)) in anchors.items():
        if kw in tl:
            return {
                "label": lab,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "source": "message_text",
            }

    lat0, lon0 = DISTRICT_COORDS["Colombo"]
    return {
        "label": "Could not infer place from message — showing Colombo reference",
        "latitude": round(lat0, 6),
        "longitude": round(lon0, 6),
        "source": "fallback_default",
    }
