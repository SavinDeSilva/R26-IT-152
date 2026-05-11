"""
SO3 — Shared multilingual keyword lists for distress RF features and NLP fallback.
Keep in sync between services/ml_models.py and services/nlp_pipeline.py.
"""

DISTRESS_KEYWORDS = [
    "help", "emergency", "police", "harass", "stole", "stolen",
    "lost", "unsafe", "scared", "following", "drunk", "danger",
    "robbery", "attack", "hurt", "ambulance",
]

SINHALA_KW = ["උදව්", "භයනක", "සොරකම්", "හදිසි", "බිය", "හිරිහැර"]
TAMIL_KW = ["உதவு", "அபாயம்", "கொள்ளை", "அவசர", "பயம்", "தொல்லை"]
