"""
SOS Safety System — Dataset Generator
SO1: Data Collection — Synthetic datasets for demo/prototype
Generates: social_media_posts.csv, hotel_safety_reviews.csv,
           flight_danger_zones.csv, distress_phrases.csv
Run from backend/ folder: python datasets/generate_sos_data.py
"""

import os
import sys
import csv
import random
import math
from datetime import datetime, timedelta

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.sri_lanka_geo import DISTRICT_COORDS as DISTRICTS

random.seed(42)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Sri Lanka geo data (SO1) — shared district centres (see utils/sri_lanka_geo.py)
# ---------------------------------------------------------------------------

INCIDENT_TYPES = [
    "harassment", "road_accident", "theft", "medical_emergency",
    "natural_hazard", "scam", "unsafe_transport",
]

LANGUAGES = ["en", "si", "ta", "fr", "de", "es", "zh", "ja", "ko", "ar"]

# Sample text snippets per language / incident type (SO1 — multilingual context)
TEXT_TEMPLATES = {
    "en": [
        "Feeling unsafe near {d}, someone is following me",
        "Road accident reported on the highway near {d}",
        "My bag was stolen at the market in {d}",
        "Need medical help urgently in {d}",
        "Flash flooding reported near {d}, avoid the area",
        "Tourist scam alert in {d}, watch out for tuk-tuk overcharging",
        "Unsafe bus conditions reported near {d}",
    ],
    "si": [
        "මට {d} අසල ආරක්‍ෂාව නොමැති බව දැනෙනවා",
        "{d} ළඟ මාර්ග අනතුරක් සිදු වී ඇත",
        "{d} වෙළඳ පොළේ මගේ බෑගය සොරකම් කළා",
        "{d} හිදී හදිසි ආධාර අවශ්‍යයි",
        "{d} අසල ගංවතුර — ප්‍රදේශය වළකින්න",
        "{d} හිදී සංචාරක වංචා — පරිස්සම් වන්න",
        "{d} ළඟ අනාරක්‍ෂිත බස් රථ",
    ],
    "ta": [
        "{d} அருகில் பாதுகாப்பற்றதாக உணர்கிறேன்",
        "{d} அருகில் சாலை விபத்து",
        "{d} சந்தையில் என் பை திருடப்பட்டது",
        "{d} இல் மருத்துவ உதவி தேவை",
        "{d} அருகில் வெள்ளம் — பகுதியை தவிர்க்கவும்",
        "{d} இல் சுற்றுலா மோசடி எச்சரிக்கை",
        "{d} அருகில் பாதுகாப்பற்ற பேருந்து",
    ],
    "fr": [
        "Je ne me sens pas en sécurité près de {d}",
        "Accident de la route signalé près de {d}",
        "Mon sac a été volé au marché de {d}",
    ],
    "de": [
        "Ich fühle mich unsicher in der Nähe von {d}",
        "Verkehrsunfall in der Nähe von {d} gemeldet",
    ],
    "es": [
        "Me siento inseguro cerca de {d}",
        "Accidente de tráfico reportado cerca de {d}",
    ],
    "zh": ["在{d}附近感到不安全", "在{d}发生交通事故"],
    "ja": ["{d}付近で危険を感じています", "{d}で交通事故が発生しました"],
    "ko": ["{d} 근처에서 안전하지 않다고 느낍니다", "{d}에서 교통사고 발생"],
    "ar": ["أشعر بعدم الأمان بالقرب من {d}", "تم الإبلاغ عن حادث طريق بالقرب من {d}"],
}


def jitter(coord, scale=0.05):
    return coord + random.uniform(-scale, scale)


def risk_score_for(incident, hour):
    """Rough risk heuristic (SO2 label engineering)."""
    base = {
        "harassment": 0.65, "road_accident": 0.55, "theft": 0.60,
        "medical_emergency": 0.50, "natural_hazard": 0.70,
        "scam": 0.45, "unsafe_transport": 0.55,
    }[incident]
    night_factor = 0.15 if (hour >= 22 or hour <= 5) else 0.0
    score = base + night_factor + random.uniform(-0.10, 0.10)
    return round(max(0.0, min(1.0, score)), 4)


def make_timestamp(year=2024):
    start = datetime(year, 1, 1)
    return (start + timedelta(seconds=random.randint(0, 365 * 24 * 3600))).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )


# ---------------------------------------------------------------------------
# 1. social_media_posts.csv  (SO1 — 100 K rows)
# ---------------------------------------------------------------------------
def generate_social_media_posts(n=100_000):
    path = os.path.join(OUTPUT_DIR, "social_media_posts.csv")
    fields = [
        "post_id", "district", "latitude", "longitude", "incident_type",
        "language", "hour", "day_of_week", "month", "risk_score",
        "danger_zone", "timestamp", "text_snippet",
    ]
    print(f"  Generating {n} social media posts …")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        district_names = list(DISTRICTS.keys())
        for i in range(n):
            district = random.choice(district_names)
            lat, lon = DISTRICTS[district]
            incident = random.choice(INCIDENT_TYPES)
            lang = random.choice(LANGUAGES)
            hour = random.randint(0, 23)
            rs = risk_score_for(incident, hour)
            dz = 1 if rs >= 0.60 else (1 if random.random() < 0.15 else 0)
            ts = make_timestamp()
            dt = datetime.fromisoformat(ts)
            templates = TEXT_TEMPLATES.get(lang, TEXT_TEMPLATES["en"])
            d_disp = district.replace("_", " ")
            snippet = random.choice(templates).format(d=d_disp)
            writer.writerow({
                "post_id":       f"SP{i+1:07d}",
                "district":      district,
                "latitude":      round(jitter(lat, 0.08), 6),
                "longitude":     round(jitter(lon, 0.08), 6),
                "incident_type": incident,
                "language":      lang,
                "hour":          hour,
                "day_of_week":   dt.weekday(),
                "month":         dt.month,
                "risk_score":    rs,
                "danger_zone":   dz,
                "timestamp":     ts,
                "text_snippet":  snippet,
            })
            if (i + 1) % 10_000 == 0:
                print(f"    … {i+1:,} rows written")
    print(f"  ✅  social_media_posts.csv — {n:,} rows → {path}")


# ---------------------------------------------------------------------------
# 2. hotel_safety_reviews.csv  (SO1 — 5 K rows)
# ---------------------------------------------------------------------------
HOTEL_NAMES = [
    "Lighthouse Hotel", "Cinnamon Grand", "Jetwing Blue", "Amangalla",
    "The Kandy House", "98 Acres Resort", "Tintagel Colombo", "Araliya Beach",
    "Kings Pavilion", "Villa Rosa",
]


def generate_hotel_safety_reviews(n=5_000):
    path = os.path.join(OUTPUT_DIR, "hotel_safety_reviews.csv")
    fields = [
        "hotel_id", "hotel_name", "district", "overall_safety",
        "women_safety", "family_safety", "night_safety",
        "harassment_reports", "theft_reports", "last_updated",
    ]
    print(f"  Generating {n} hotel safety reviews …")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        districts = list(DISTRICTS.keys())
        base_date = datetime(2024, 1, 1)
        for i in range(n):
            dist = random.choice(districts)
            ov = round(random.uniform(1.5, 5.0), 2)
            writer.writerow({
                "hotel_id":             f"H{i+1:05d}",
                "hotel_name":           random.choice(HOTEL_NAMES) + f" {dist}",
                "district":             dist,
                "overall_safety":       ov,
                "women_safety":         round(max(0, ov + random.uniform(-1, 1)), 2),
                "family_safety":        round(max(0, ov + random.uniform(-0.8, 0.8)), 2),
                "night_safety":         round(max(0, ov + random.uniform(-1.2, 0.5)), 2),
                "harassment_reports":   random.randint(0, 15),
                "theft_reports":        random.randint(0, 10),
                "last_updated":         (base_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            })
    print(f"  ✅  hotel_safety_reviews.csv — {n:,} rows → {path}")


# ---------------------------------------------------------------------------
# 3. flight_danger_zones.csv  (SO1 — 2 K rows)
# ---------------------------------------------------------------------------
AIRPORTS = ["CMB", "HRI", "JAF", "TRR", "BTC", "GIU", "KCT", "MNH", "SWA"]
WEATHER   = ["clear", "rain", "storm", "fog", "heavy_rain", "thunderstorm"]


def generate_flight_danger_zones(n=2_000):
    path = os.path.join(OUTPUT_DIR, "flight_danger_zones.csv")
    fields = [
        "flight_id", "flight_number", "origin", "destination",
        "arrival_hour", "passenger_count", "day_of_week", "month",
        "weather_condition", "historical_incidents_at_arrival",
        "danger_zone_risk",
    ]
    print(f"  Generating {n} flight danger zone records …")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        carriers = ["UL", "FD", "AK", "EK", "QR", "SQ"]
        for i in range(n):
            origin = random.choice(AIRPORTS)
            dest   = random.choice([a for a in AIRPORTS if a != origin])
            weather = random.choice(WEATHER)
            incidents = random.randint(0, 8)
            arr_hour  = random.randint(0, 23)
            risk = round(
                min(1.0, 0.05 * incidents
                    + (0.3 if weather in ("storm", "thunderstorm") else 0.05 if weather == "rain" else 0)
                    + (0.1 if arr_hour < 6 or arr_hour > 21 else 0)
                    + random.uniform(0, 0.15)),
                4,
            )
            writer.writerow({
                "flight_id":                    f"FL{i+1:05d}",
                "flight_number":                f"{random.choice(carriers)}{random.randint(100,999)}",
                "origin":                       origin,
                "destination":                  dest,
                "arrival_hour":                 arr_hour,
                "passenger_count":              random.randint(40, 280),
                "day_of_week":                  random.randint(0, 6),
                "month":                        random.randint(1, 12),
                "weather_condition":            weather,
                "historical_incidents_at_arrival": incidents,
                "danger_zone_risk":             risk,
            })
    print(f"  ✅  flight_danger_zones.csv — {n:,} rows → {path}")


# ---------------------------------------------------------------------------
# 4. distress_phrases.csv  (SO3 — 5 K rows)
# ---------------------------------------------------------------------------
DISTRESS_PHRASES = {
    "en": [
        "Help me please I am in danger", "Someone is following me",
        "I have been robbed call police now", "Emergency I need help immediately",
        "I am scared and lost please assist", "They harassed me near the beach",
        "I feel unsafe send help", "My friend is unconscious call ambulance",
        "Stolen passport need embassy help", "Drunk driver almost hit me",
    ],
    "si": [
        "උදව් කරන්න මට භයනක් දෙයක් වෙනවා", "කෙනෙක් මාව අනුගමනය කරනවා",
        "මාව කොල්ල කෑවා පොලිසියට කියන්න", "හදිසිය — දැනම සහාය අවශ්‍යයි",
        "මම බිය වෙලා ඉන්නවා", "මාව හිරිහැරයට ලක් කළා",
        "ආරක්‍ෂිත නෑ — සහාය යවන්න", "මිතුරා අසනීප ඇම්බියුලන්ස් කතා කරන්න",
        "දිනන ලද ගෙවීමකින් උදව් ඕනා", "මත් ධාවකයෙකු මා ඉදිරිපිට ගිහින්",
    ],
    "ta": [
        "உதவுங்கள் என்னை யாரோ பின்தொடர்கிறார்கள்", "கொள்ளை அடிக்கப்பட்டேன் போலீஸ் அழைக்கவும்",
        "அவசர நிலை உடனடி உதவி தேவை", "பயமாக இருக்கிறது",
        "தொல்லை கொடுத்தார்கள் கடற்கரையில்", "பாதுகாப்பற்று உணர்கிறேன்",
        "நண்பர் மயக்கமடைந்துள்ளார் ஆம்புலன்ஸ் அழைக்கவும்",
    ],
    "fr": ["Aidez-moi s'il vous plaît je suis en danger", "Au secours quelqu'un me suit"],
    "de": ["Hilfe bitte ich bin in Gefahr", "Jemand folgt mir"],
    "es": ["Ayúdame por favor estoy en peligro", "Alguien me está siguiendo"],
    "zh": ["救命我有危险", "有人跟踪我"],
    "ja": ["助けてください危険です", "誰かが私を追いかけています"],
    "ko": ["도와주세요 위험합니다", "누군가 저를 따라오고 있습니다"],
    "ar": ["ساعدني من فضلك أنا في خطر", "شخص ما يتبعني"],
}

NON_DISTRESS_PHRASES = {
    "en": [
        "The beach in Mirissa is beautiful today",
        "Enjoyed a great meal at a local restaurant",
        "Checking in to my hotel now",
        "Taking a tuk-tuk tour of Colombo",
        "Visited the temple in Kandy",
    ],
    "si": [
        "අද මිරිස්ස වෙරළ ඉතාම ලස්සනයි",
        "දේශීය අවන්හලක හොඳ කෑමක් ගත්තා",
    ],
    "ta": ["இன்று கடற்கரை மிகவும் அழகாக உள்ளது", "உணவகத்தில் சாப்பிட்டேன்"],
}


def _rand_entities(text):
    tl = text.lower()
    locs = []
    for d in DISTRICTS:
        disp = d.replace("_", " ")
        if disp.lower() in tl or d.lower() in tl:
            locs.append(disp)
    threats = []
    for kw in ["follow", "stolen", "harass", "emergency", "danger", "unsafe"]:
        if kw in text.lower():
            threats.append(kw)
    return f"locations={locs};threats={threats}"


def generate_distress_phrases(n=5_000):
    path = os.path.join(OUTPUT_DIR, "distress_phrases.csv")
    fields = [
        "phrase_id", "language", "text", "noise_level",
        "is_distress", "confidence_label", "detected_entities",
    ]
    print(f"  Generating {n} distress phrases …")
    rows = []
    # Build positive (distress) pool
    for lang, phrases in DISTRESS_PHRASES.items():
        for ph in phrases:
            rows.append({
                "language":         lang,
                "text":             ph,
                "noise_level":      round(random.uniform(0, 0.5), 2),
                "is_distress":      1,
                "confidence_label": round(random.uniform(0.75, 1.0), 2),
                "detected_entities": _rand_entities(ph),
            })
    # Build negative pool
    for lang, phrases in NON_DISTRESS_PHRASES.items():
        for ph in phrases:
            rows.append({
                "language":         lang,
                "text":             ph,
                "noise_level":      round(random.uniform(0, 0.2), 2),
                "is_distress":      0,
                "confidence_label": round(random.uniform(0.80, 1.0), 2),
                "detected_entities": "locations=[];threats=[]",
            })

    # Oversample to n rows
    while len(rows) < n:
        base = random.choice(rows)
        rows.append(dict(base))  # duplicate with noise variation

    random.shuffle(rows)
    rows = rows[:n]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for idx, row in enumerate(rows):
            row["phrase_id"] = f"DP{idx+1:06d}"
            writer.writerow(row)
    print(f"  ✅  distress_phrases.csv — {n:,} rows → {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("SOS Safety System — SO1 Dataset Generator")
    print("=" * 60)
    generate_social_media_posts(100_000)
    generate_hotel_safety_reviews(5_000)
    generate_flight_danger_zones(2_000)
    generate_distress_phrases(5_000)
    print("\n✅ All datasets generated successfully.")
    print(f"   Output folder: {os.path.abspath(OUTPUT_DIR)}")
