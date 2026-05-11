from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TourismPlace:
    name: str
    category: str
    estimated_cost: int
    safety_score: float
    emotion_suitability: List[str]
    region: str


# Small internal dataset for backend API usage (research prototype).
TOURISM_DATASET: List[TourismPlace] = [
    TourismPlace("Ella Rock", "nature", 9500, 8.8, ["happy", "neutral", "sad"], "Uva"),
    TourismPlace("Nine Arches Bridge", "cultural", 4500, 8.9, ["happy", "neutral", "surprise"], "Uva"),
    TourismPlace("Mirissa Beach", "beach", 12000, 8.4, ["happy", "surprise", "neutral"], "Southern"),
    TourismPlace("Coconut Tree Hill", "nature", 3500, 8.2, ["happy", "neutral"], "Southern"),
    TourismPlace("Sigiriya Rock Fortress", "cultural", 14000, 9.1, ["fear", "surprise", "neutral"], "Central"),
    TourismPlace("Yala National Park", "wildlife", 18000, 8.3, ["surprise", "fear", "happy"], "Southern"),
    TourismPlace("Nuwara Eliya Tea Estates", "nature", 8000, 9.0, ["sad", "neutral", "disgust"], "Central"),
    TourismPlace("Galle Fort", "cultural", 6500, 8.9, ["neutral", "angry", "sad"], "Southern"),
    TourismPlace("Arugam Bay", "adventure", 13000, 7.9, ["surprise", "happy"], "Eastern"),
    TourismPlace("Udawalawe National Park", "wildlife", 15000, 8.7, ["neutral", "angry", "fear"], "Sabaragamuwa"),
    TourismPlace("Bentota Water Sports", "adventure", 17000, 7.7, ["happy", "surprise", "angry"], "Western"),
]


TRAVELER_TYPE_CATEGORY_BIAS: Dict[str, List[str]] = {
    "solo": ["adventure", "nature", "cultural"],
    "couple": ["beach", "nature", "cultural"],
    "family": ["wildlife", "nature", "beach", "cultural"],
    "group": ["adventure", "beach", "wildlife"],
}


def _norm_emotion(emotion: str) -> str:
    return (emotion or "neutral").strip().lower()


def _norm_traveler_type(traveler_type: str) -> str:
    t = (traveler_type or "solo").strip().lower()
    if t not in TRAVELER_TYPE_CATEGORY_BIAS:
        return "solo"
    return t


def _budget_fit_score(place_cost: int, per_day_budget: float) -> float:
    if per_day_budget <= 0:
        return 0.0
    if place_cost <= per_day_budget:
        return 1.0 - (place_cost / per_day_budget) * 0.25
    over = (place_cost - per_day_budget) / per_day_budget
    return max(0.0, 0.6 - over)


def _place_to_card(place: TourismPlace, rank: int, score: float) -> Dict[str, object]:
    return {
        "rank": rank,
        "name": place.name,
        "category": place.category,
        "region": place.region,
        "estimated_cost": place.estimated_cost,
        "safety_score": place.safety_score,
        "match_score": round(score, 3),
    }


def _rank_places(
    emotion: str,
    budget: int,
    days: int,
    traveler_type: str,
    attraction_preferences: Optional[List[str]] = None,
) -> List[Tuple[float, TourismPlace]]:
    emotion = _norm_emotion(emotion)
    traveler_type = _norm_traveler_type(traveler_type)
    days = max(1, int(days))
    budget = max(1000, int(budget))
    per_day_budget = budget / days
    preferred_categories = TRAVELER_TYPE_CATEGORY_BIAS.get(traveler_type, [])
    pref_set = set([(x or "").strip().lower() for x in (attraction_preferences or []) if str(x).strip()])

    scored: List[Tuple[float, TourismPlace]] = []
    for p in TOURISM_DATASET:
        emotion_match = 1.0 if emotion in p.emotion_suitability else 0.35
        budget_fit = _budget_fit_score(p.estimated_cost, per_day_budget)
        traveler_fit = 1.0 if p.category in preferred_categories else 0.5
        pref_fit = 1.0 if not pref_set else (1.0 if p.category in pref_set else 0.4)
        safety_norm = p.safety_score / 10.0
        final = (
            (safety_norm * 0.40)
            + (emotion_match * 0.28)
            + (budget_fit * 0.14)
            + (traveler_fit * 0.10)
            + (pref_fit * 0.08)
        )
        scored.append((final, p))
    scored.sort(key=lambda x: (x[0], x[1].safety_score), reverse=True)
    return scored


def _activity_note(category: str, visit_no: int) -> str:
    activity_by_category: Dict[str, List[str]] = {
        "nature": [
            "scenic hike + viewpoint photography",
            "slow eco-walk + local tea stop",
            "sunrise nature immersion and rest",
        ],
        "beach": [
            "sunrise beach walk + relaxation",
            "coastal food experience + sunset",
            "light water activity and recovery",
        ],
        "cultural": [
            "heritage landmarks and storytelling tour",
            "deeper culture circuit + local market",
            "architecture photo walk + museum stop",
        ],
        "adventure": [
            "main activity session + cooldown",
            "alternate challenge route",
            "skill practice block + scenic break",
        ],
        "wildlife": [
            "early wildlife observation session",
            "alternate safari route and photo stops",
            "conservation-focused revisit",
        ],
    }
    pool = activity_by_category.get(category, ["local exploration and relaxed pacing"])
    return pool[(visit_no - 1) % len(pool)]


def _build_itinerary_from_selected(selected: List[TourismPlace], days: int) -> Dict[str, object]:
    if not selected:
        return {"itinerary": {}, "itinerary_days": []}
    n = len(selected)
    base_days = days // n
    extra = days % n
    counts = [base_days + (1 if i < extra else 0) for i in range(n)]
    day_map: Dict[str, List[str]] = {}
    day_cards: List[Dict[str, object]] = []
    day_index = 1
    for i, place in enumerate(selected):
        for visit_no in range(1, counts[i] + 1):
            line = f"{place.name} - {_activity_note(place.category, visit_no)}"
            day_key = f"day{day_index}"
            day_map[day_key] = [line]
            # Lower repeat-day spend to reflect same-place revisit.
            day_cost = place.estimated_cost if visit_no == 1 else max(2500, int(place.estimated_cost * 0.6))
            day_cards.append(
                {
                    "day": day_index,
                    "title": day_key.upper(),
                    "region": place.region,
                    "place": place.name,
                    "category": place.category,
                    "activity": _activity_note(place.category, visit_no),
                    "estimated_cost": day_cost,
                    "safety_score": place.safety_score,
                }
            )
            day_index += 1
    return {"itinerary": day_map, "itinerary_days": day_cards}


def generate_rule_based_itinerary(
    emotion: str,
    budget: int,
    days: int,
    traveler_type: str,
    attraction_preferences: Optional[List[str]] = None,
    selected_places: Optional[List[str]] = None,
) -> Dict[str, object]:
    days = max(1, int(days))
    budget = max(1000, int(budget))
    scored = _rank_places(
        emotion=emotion,
        budget=budget,
        days=days,
        traveler_type=traveler_type,
        attraction_preferences=attraction_preferences,
    )
    if not scored:
        return {
            "recommended_places": [],
            "safety_score": 0.0,
            "estimated_budget": 0,
            "itinerary": {},
            "itinerary_days": [],
            "suggested_places": [],
        }

    top_suggestions = scored[: max(6, min(len(scored), days * 2))]
    suggested_places = [_place_to_card(p, i + 1, s) for i, (s, p) in enumerate(top_suggestions)]

    if selected_places:
        selected_lookup = set([(x or "").strip().lower() for x in selected_places if str(x).strip()])
        selected = [p for _, p in scored if p.name.lower() in selected_lookup]
        if not selected:
            selected = [p for _, p in top_suggestions[: max(1, min(3, len(top_suggestions)))]]
    else:
        selected = [p for _, p in top_suggestions[: max(1, min(3, len(top_suggestions)))]]

    plan = _build_itinerary_from_selected(selected=selected, days=days)
    avg_safety = sum(p.safety_score for p in selected) / len(selected)
    est_budget = sum(d["estimated_cost"] for d in plan["itinerary_days"])
    if est_budget > budget:
        est_budget = budget

    recommended_places: List[str] = []
    seen = set()
    for p in selected:
        if p.name not in seen:
            seen.add(p.name)
            recommended_places.append(p.name)

    return {
        "recommended_places": recommended_places,
        "safety_score": round(avg_safety, 2),
        "estimated_budget": int(est_budget),
        "itinerary": plan["itinerary"],
        "itinerary_days": plan["itinerary_days"],
        "suggested_places": suggested_places,
    }
