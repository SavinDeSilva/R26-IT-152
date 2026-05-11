from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from .tourism_data import Attraction, SRI_LANKA_ATTRACTIONS
except ImportError:
    from tourism_data import Attraction, SRI_LANKA_ATTRACTIONS

# UI and engine both respect this upper bound so long itineraries stay coherent.
MAX_TRIP_DAYS = 31


@dataclass
class RankedAttraction:
    attraction: Attraction
    emotion_match_score: float
    budget_compatibility_score: float
    final_score: float
    # Optional UX for repeats (same place, different activities same day).
    slot_note: str = ""
    itinerary_cost_override: Optional[int] = None


def slot_line_cost(item: RankedAttraction) -> int:
    if item.itinerary_cost_override is not None:
        return item.itinerary_cost_override
    return item.attraction.estimated_cost


def repeat_visit_slice(base: RankedAttraction, nth_visit_same_calendar_day: int) -> RankedAttraction:
    """nth_visit_same_calendar_day: 0 = primary block; further slots = add-on time at same place."""
    if nth_visit_same_calendar_day <= 0:
        return RankedAttraction(
            attraction=base.attraction,
            emotion_match_score=base.emotion_match_score,
            budget_compatibility_score=base.budget_compatibility_score,
            final_score=base.final_score,
        )
    addon = max(25, base.attraction.estimated_cost // 4)
    return RankedAttraction(
        attraction=base.attraction,
        emotion_match_score=base.emotion_match_score,
        budget_compatibility_score=base.budget_compatibility_score,
        final_score=base.final_score,
        slot_note=" — different activities / longer stay at this same place",
        itinerary_cost_override=addon,
    )


ACTIVITY_VARIANTS_BY_CATEGORY: Dict[str, List[str]] = {
    "beach": [
        "sunrise coastal walk and relaxation",
        "water activity block and beach recovery",
        "local seafood + sunset leisure",
        "slow day: seaside cafes and photography",
    ],
    "nature": [
        "nature trail + scenic viewpoints",
        "guided eco-walk and quiet reflection",
        "botanical/forest exploration with rest stops",
        "slow pace nature immersion and local tea break",
    ],
    "cultural": [
        "heritage walk and monument highlights",
        "museum/temple depth visit + local market",
        "architecture photography + cultural storytelling",
        "relaxed revisit of key heritage areas",
    ],
    "adventure": [
        "main activity session + recovery block",
        "alternate route/challenge variation",
        "skill-focused repeat with lighter intensity",
        "adventure + scenic cooldown schedule",
    ],
    "wildlife": [
        "early safari window + rest period",
        "alternate trail/zone observation plan",
        "photo-focused wildlife session",
        "gentle revisit with conservation briefing",
    ],
}


def _activity_note_for_visit(attraction: Attraction, visit_no: int) -> str:
    """
    visit_no is 1-indexed for this attraction across the itinerary.
    """
    options = ACTIVITY_VARIANTS_BY_CATEGORY.get(attraction.category, [])
    if not options:
        options = [
            "local exploration and relaxed pacing",
            "deeper revisit with alternate route",
            "theme day with food and culture focus",
            "light activity day and recovery time",
        ]
    text = options[(visit_no - 1) % len(options)]
    return f" — itinerary activity: {text}"


@dataclass
class DayPlan:
    day: int
    region: str
    attractions: List[RankedAttraction]
    estimated_day_cost: int
    day_safety_score: float


@dataclass
class ItineraryResult:
    emotion: str
    budget: int
    travel_days: int
    ranked_attractions: List[RankedAttraction]
    day_plans: List[DayPlan]
    total_estimated_cost: int
    itinerary_score: float


def _normalize_emotion(emotion: str) -> str:
    return (emotion or "neutral").strip().lower()


def compute_budget_compatibility(estimated_cost: int, daily_budget_cap: float) -> float:
    if daily_budget_cap <= 0:
        return 0.0
    if estimated_cost <= daily_budget_cap:
        return 1.0 - (estimated_cost / max(daily_budget_cap, 1.0)) * 0.35
    overspend_ratio = (estimated_cost - daily_budget_cap) / daily_budget_cap
    return max(0.0, 0.5 - overspend_ratio)


def compute_final_score(safety_score: int, emotion_match_score: float, budget_score: float) -> float:
    # Research-oriented weighted score:
    # - safety priority (50%)
    # - emotion suitability (30%)
    # - budget compatibility (20%)
    safety_component = (float(safety_score) / 10.0) * 0.50
    emotion_component = float(emotion_match_score) * 0.30
    budget_component = float(budget_score) * 0.20
    return safety_component + emotion_component + budget_component


def recommend_attractions(
    emotion: str,
    user_budget: int,
    travel_days: int,
    attractions: List[Attraction] = SRI_LANKA_ATTRACTIONS,
) -> List[RankedAttraction]:
    norm_emotion = _normalize_emotion(emotion)
    days = max(min(int(travel_days), MAX_TRIP_DAYS), 1)
    total_budget = max(int(user_budget), 1)
    daily_budget_cap = total_budget / days

    ranked: List[RankedAttraction] = []
    for attraction in attractions:
        budget_score = compute_budget_compatibility(attraction.estimated_cost, daily_budget_cap)
        # Filter by budget compatibility threshold to keep results realistic.
        if budget_score < 0.15:
            continue
        emotion_match = 1.0 if norm_emotion in attraction.emotion_suitability_tags else 0.35
        final_score = compute_final_score(attraction.safety_score, emotion_match, budget_score)
        ranked.append(
            RankedAttraction(
                attraction=attraction,
                emotion_match_score=emotion_match,
                budget_compatibility_score=budget_score,
                final_score=final_score,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.final_score,
            item.attraction.safety_score,
            item.budget_compatibility_score,
        ),
        reverse=True,
    )
    return ranked


def _region_priority_map(ranked: List[RankedAttraction]) -> Dict[str, float]:
    score_map: Dict[str, float] = {}
    for item in ranked:
        score_map[item.attraction.region] = score_map.get(item.attraction.region, 0.0) + item.final_score
    return score_map


def generate_itinerary(
    emotion: str,
    user_budget: int,
    travel_days: int,
    max_locations_per_day: int = 3,
) -> ItineraryResult:
    days = max(min(int(travel_days), MAX_TRIP_DAYS), 1)
    ranked = recommend_attractions(emotion=emotion, user_budget=user_budget, travel_days=days)
    per_day_limit = min(max(max_locations_per_day, 3), 4)

    if not ranked:
        return ItineraryResult(
            emotion=emotion,
            budget=max(int(user_budget), 1),
            travel_days=days,
            ranked_attractions=[],
            day_plans=[],
            total_estimated_cost=0,
            itinerary_score=0.0,
        )

    region_scores = _region_priority_map(ranked)
    sorted_regions = sorted(region_scores.keys(), key=lambda r: region_scores[r], reverse=True)

    remaining = list(ranked)
    day_plans: List[DayPlan] = []

    for day in range(1, days + 1):
        # Fewer stops in the dataset than (days × per_day_cap): revisit top-ranked stops.
        if not remaining:
            remaining = list(ranked)

        target_region = sorted_regions[(day - 1) % len(sorted_regions)]
        day_items: List[RankedAttraction] = []

        for item in list(remaining):
            if len(day_items) >= per_day_limit:
                break
            if item.attraction.region == target_region:
                day_items.append(item)
                remaining.remove(item)

        for item in list(remaining):
            if len(day_items) >= per_day_limit:
                break
            day_items.append(item)
            remaining.remove(item)

        if not day_items:
            continue

        day_cost = sum(x.attraction.estimated_cost for x in day_items)
        day_safety = sum(x.attraction.safety_score for x in day_items) / len(day_items)
        day_plans.append(
            DayPlan(
                day=day,
                region=target_region,
                attractions=day_items,
                estimated_day_cost=day_cost,
                day_safety_score=day_safety,
            )
        )

    total_cost = sum(d.estimated_day_cost for d in day_plans)
    chosen_items = [item for d in day_plans for item in d.attractions]
    itinerary_score = 0.0 if not chosen_items else sum(i.final_score for i in chosen_items) / len(chosen_items)

    return ItineraryResult(
        emotion=emotion,
        budget=max(int(user_budget), 1),
        travel_days=days,
        ranked_attractions=ranked,
        day_plans=day_plans,
        total_estimated_cost=total_cost,
        itinerary_score=itinerary_score,
    )


def generate_itinerary_from_user_picks(
    emotion: str,
    user_budget: int,
    travel_days: int,
    picked_attractions: List[Attraction],
    max_locations_per_day: int = 4,
) -> ItineraryResult:
    """
    Build a day-wise itinerary using ONLY user-selected attractions.
    Days are assigned in contiguous blocks per selected place (A,A,A,B,B,C...).
    If trip length exceeds unique picks, the same place appears on later days with
    different activity notes (no non-selected venues are inserted).
    """
    days = max(1, min(int(travel_days), MAX_TRIP_DAYS))
    budget = max(1, int(user_budget))
    daily_cap = budget / days
    per_day_limit = min(max(max_locations_per_day, 3), 4)

    norm_emotion = _normalize_emotion(emotion)

    def rank_one(a: Attraction) -> RankedAttraction:
        bs = compute_budget_compatibility(a.estimated_cost, daily_cap)
        em = 1.0 if norm_emotion in a.emotion_suitability_tags else 0.35
        fs = compute_final_score(a.safety_score, em, bs)
        return RankedAttraction(
            attraction=a,
            emotion_match_score=em,
            budget_compatibility_score=bs,
            final_score=fs,
        )

    seen_names = set()
    ranked_picks: List[RankedAttraction] = []
    for a in picked_attractions:
        if a.name in seen_names:
            continue
        seen_names.add(a.name)
        ranked_picks.append(rank_one(a))

    ranked_picks.sort(
        key=lambda x: (x.final_score, x.attraction.safety_score, x.budget_compatibility_score),
        reverse=True,
    )

    if not ranked_picks:
        return ItineraryResult(
            emotion=emotion,
            budget=budget,
            travel_days=days,
            ranked_attractions=[],
            day_plans=[],
            total_estimated_cost=0,
            itinerary_score=0.0,
        )

    # Allocate contiguous day counts per place.
    n = len(ranked_picks)
    base_days = days // n
    extra = days % n
    days_for_place: List[int] = [base_days + (1 if i < extra else 0) for i in range(n)]

    day_plans: List[DayPlan] = []
    day_idx = 1
    for place_idx, base in enumerate(ranked_picks):
        allocated = max(1, days_for_place[place_idx])
        for visit_no in range(1, allocated + 1):
            # First day at a place = full visit. Follow-up days = lower incremental budget.
            override = None
            if visit_no > 1:
                override = max(25, int(round(base.attraction.estimated_cost * 0.60)))
            item = RankedAttraction(
                attraction=base.attraction,
                emotion_match_score=base.emotion_match_score,
                budget_compatibility_score=base.budget_compatibility_score,
                final_score=base.final_score,
                slot_note=_activity_note_for_visit(base.attraction, visit_no),
                itinerary_cost_override=override,
            )
            day_cost = slot_line_cost(item)
            day_plans.append(
                DayPlan(
                    day=day_idx,
                    region=base.attraction.region,
                    attractions=[item],
                    estimated_day_cost=day_cost,
                    day_safety_score=float(base.attraction.safety_score),
                )
            )
            day_idx += 1

    total_cost = sum(d.estimated_day_cost for d in day_plans)
    chosen = [item for d in day_plans for item in d.attractions]
    itinerary_score = 0.0 if not chosen else sum(i.final_score for i in chosen) / len(chosen)

    return ItineraryResult(
        emotion=emotion,
        budget=budget,
        travel_days=days,
        ranked_attractions=list(ranked_picks),
        day_plans=day_plans,
        total_estimated_cost=total_cost,
        itinerary_score=itinerary_score,
    )
