from typing import List, Optional, Tuple

try:
    from .tourism_data import Attraction, SRI_LANKA_ATTRACTIONS
except ImportError:
    from tourism_data import Attraction, SRI_LANKA_ATTRACTIONS

# Longer needles first so e.g. "madu river" wins over "ella".
_CHAT_NEEDLE_TO_NAME: List[Tuple[str, str]] = sorted(
    [
        ("nuwara eliya", "Nuwara Eliya Tea Estates"),
        ("hikkaduwa", "Hikkaduwa Beach"),
        ("sigiriya rock fortress", "Sigiriya Rock Fortress"),
        ("sigiriya", "Sigiriya Rock Fortress"),
        ("bentota water sports", "Bentota Water Sports"),
        ("bentota", "Bentota Water Sports"),
        ("madu river sunset boat ride", "Madu River Boat Safari"),
        ("madu river", "Madu River Boat Safari"),
        ("madu", "Madu River Boat Safari"),
        ("nine arches", "Ella Scenic Trails"),
        ("ella", "Ella Scenic Trails"),
        ("yala national park", "Yala National Park"),
        ("yala", "Yala National Park"),
        ("udawalawe", "Udawalawe National Park"),
        ("arugam bay", "Arugam Bay Surf Point"),
        ("galle fort", "Galle Fort Heritage Walk"),
        ("galle", "Galle Fort Heritage Walk"),
        ("kandy", "Kandy Temple and Gardens"),
        ("sinharaja forest reserve", "Sinharaja Rainforest Reserve"),
        ("sinharaja", "Sinharaja Rainforest Reserve"),
        ("horton plains", "Horton Plains National Park"),
        ("dambulla cave temples", "Dambulla Cave Temples"),
        ("dambulla", "Dambulla Cave Temples"),
        ("colombo", "Colombo City Highlights"),
        ("polonnaruwa", "Polonnaruwa Ancient City"),
        ("minneriya & kaudulla", "Minneriya National Park"),
        ("minneriya national park", "Minneriya National Park"),
        ("minneriya", "Minneriya National Park"),
        ("anuradhapura", "Anuradhapura Sacred City"),
        ("ritigala forest monastery", "Ritigala Forest Monastery"),
        ("ritigala", "Ritigala Forest Monastery"),
        ("adam’s peak", "Adams Peak Sunrise Trek"),
        ("adam's peak", "Adams Peak Sunrise Trek"),
        ("adams peak", "Adams Peak Sunrise Trek"),
        ("udawattekele sanctuary", "Udawattekele Sanctuary"),
        ("udawattekele", "Udawattekele Sanctuary"),
        ("diyaluma falls", "Diyaluma Falls Excursion"),
        ("diyaluma", "Diyaluma Falls Excursion"),
        ("trincomalee", "Trincomalee Coastal Relaxation"),
        ("koggala lake", "Koggala Lake Canoeing"),
        ("koggala", "Koggala Lake Canoeing"),
        ("tangalle", "Tangalle Sunset Coast"),
        ("kalutara", "Kalutara Beach Calm"),
        ("pigeon island", "Pigeon Island Snorkeling"),
        ("kitulgala", "Kitulgala Rafting & Jungle"),
        ("mirissa", "Mirissa Whale & Beach"),
        ("knuckles mountain range", "Knuckles Mountain Range"),
        ("knuckles", "Knuckles Mountain Range"),
        ("peradeniya botanical gardens", "Peradeniya Botanical Gardens"),
        ("peradeniya", "Peradeniya Botanical Gardens"),
    ],
    key=lambda t: len(t[0]),
    reverse=True,
)


def _by_name() -> dict:
    return {a.name: a for a in SRI_LANKA_ATTRACTIONS}


def resolve_chat_pick_label(label: str) -> Optional[Attraction]:
    """
    Map a free-text chatbot suggestion line to a structured Attraction, if possible.
    """
    if not label:
        return None
    s = (
        label.strip()
        .lower()
        .replace("’", "'")
        .replace("`", "'")
    )
    index = _by_name()
    for needle, name in _CHAT_NEEDLE_TO_NAME:
        if needle in s:
            return index.get(name)
    # Fallback: any attraction name contained in the label
    for a in SRI_LANKA_ATTRACTIONS:
        if a.name.lower() in s:
            return a
    return None


def resolve_chat_pick_labels(labels: List[str]) -> Tuple[List[Attraction], List[str]]:
    resolved: List[Attraction] = []
    unresolved: List[str] = []
    seen = set()
    for raw in labels:
        a = resolve_chat_pick_label(raw)
        if a is None:
            unresolved.append(raw)
            continue
        if a.name in seen:
            continue
        seen.add(a.name)
        resolved.append(a)
    return resolved, unresolved


def resolve_selection_keys(keys: List[str]) -> Tuple[List[Attraction], List[str]]:
    """
    Map UI selection keys to attractions: keys may be canonical dataset names or chat lines.
    """
    by_name = {a.name: a for a in SRI_LANKA_ATTRACTIONS}
    resolved: List[Attraction] = []
    unresolved: List[str] = []
    for k in keys:
        if k in by_name:
            resolved.append(by_name[k])
            continue
        a = resolve_chat_pick_label(k)
        if a is None:
            unresolved.append(k)
        else:
            resolved.append(a)
    out: List[Attraction] = []
    seen = set()
    for a in resolved:
        if a.name not in seen:
            seen.add(a.name)
            out.append(a)
    return out, unresolved
