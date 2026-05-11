"""
SOS Safety System — NLP Pipeline
SO3: Voice/text distress — simulated STT, entity extraction, classifier integration,
    multilingual keyword support (en/si/ta + fr/de/es/zh/ja/ko/ar), urgency & threats.

Production note: Whisper/XLM-R would replace simulations in later milestones.
"""

import os
import pickle
import random
import time
from typing import Any, Dict, List, Optional

import numpy as np

from utils.ml_keywords import DISTRESS_KEYWORDS, SINHALA_KW, TAMIL_KW
from utils.sri_lanka_geo import DISTRICT_NAMES

# ---------------------------------------------------------------------------
# Paths & lazy model load (fallback when models missing — SO3)
# ---------------------------------------------------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
_DISTRESS_BUNDLE: Optional[Dict[str, Any]] = None


def _load_distress_model():
    """Lazy-load distress RF bundle for classify_distress."""
    global _DISTRESS_BUNDLE
    if _DISTRESS_BUNDLE is not None:
        return _DISTRESS_BUNDLE
    path = os.path.join(MODELS_DIR, "distress_classifier.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            _DISTRESS_BUNDLE = pickle.load(f)
        print("[NLP][SO3] distress_classifier.pkl loaded.")
    else:
        print("[NLP][SO3] distress_classifier.pkl missing — keyword fallback mode.")
    return _DISTRESS_BUNDLE


# ---------------------------------------------------------------------------
# SO3 — Supported languages (demo STT + NLP routing)
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {
    "en": "English",
    "si": "Sinhala",
    "ta": "Tamil",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
}

_SIMULATED_TRANSCRIPTS = {
    "en": [
        "Help me please I am in danger near Colombo",
        "Someone is following me from the market",
        "I have been robbed call the police immediately",
        "I feel unsafe send help to my location",
    ],
    "si": [
        "උදව් කරන්න, කෙනෙක් මාව හිරිහැරයට ලක් කරනවා",
        "මාව කොල්ල කෑවා — ගාල්ල ළඟ",
        "හදිසිය — දැනම සහාය අවශ්‍යයි",
        "මම ආරක්‍ෂිත නෑ — යවන්න",
    ],
    "ta": [
        "உதவுங்கள் என்னை யாரோ பின்தொடர்கிறார்கள்",
        "கொள்ளை அடிக்கப்பட்டேன் — போலீஸ் அழைக்கவும்",
        "அவசர நிலை உடனடி உதவி தேவை",
    ],
    "fr": ["Aidez-moi s'il vous plaît je suis en danger", "Au secours quelqu'un me suit"],
    "de": ["Hilfe bitte ich bin in Gefahr", "Jemand folgt mir"],
    "es": ["Ayúdame estoy en peligro", "Me robaron llamen a la policía"],
    "zh": ["救命我有危险", "有人在跟踪我"],
    "ja": ["助けてください危険です", "誰かが私を追いかけています"],
    "ko": ["도와주세요 위험합니다", "누군가 저를 따라오고 있습니다"],
    "ar": ["ساعدني من فضلك أنا في خطر", "شخص ما يتبعني"],
}


def transcribe_audio(audio_data: Any, language: str = "en") -> Dict[str, Any]:
    """
    SO3 — Audio → text (simulated Whisper-class STT for PP1).
    Supports: en, si, ta, fr, de, es, zh, ja, ko, ar.
    """
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    phrases = _SIMULATED_TRANSCRIPTS.get(lang, _SIMULATED_TRANSCRIPTS["en"])
    transcript = random.choice(phrases)

    try:
        audio_len = len(audio_data) if audio_data is not None else 100
    except TypeError:
        audio_len = 100
    time.sleep(min(audio_len / 50_000.0, 0.25))

    return {
        "text": transcript,
        "language": lang,
        "language_name": SUPPORTED_LANGUAGES[lang],
        "confidence": round(random.uniform(0.82, 0.97), 3),
        "is_simulated": True,
        "note": (
            "SO3: Simulated STT for prototype. Production would use Whisper/fine-tuned ASR "
            "with Sinhala/Tamil emphasis."
        ),
    }


# ---------------------------------------------------------------------------
# SO3 — Sri Lanka locations & multilingual threat / urgency patterns
# ---------------------------------------------------------------------------
SL_LOCATIONS = [n.replace("_", " ") for n in DISTRICT_NAMES]

THREAT_KEYWORDS: Dict[str, List[str]] = {
    "harassment": [
        "harass", "follow", "stalk", "molest",
        "හිරිහැර", "தொல்லை", "تحرش",
    ],
    "theft": [
        "rob", "steal", "stolen", "pickpocket",
        "කොල්ල", "கொள்ளை", "سرقة",
    ],
    "medical": [
        "ambulance", "injured", "unconscious", "hospital",
        "ඇම්බියුලන්ස්", "ஆம்புலன்ஸ்", "إسعاف",
    ],
    "transport": [
        "accident", "crash", "drunk driver", "unsafe bus",
        "விபத்து", "අනතුර",
    ],
    "general_distress": [
        "help", "danger", "scared", "unsafe", "lost", "emergency", "police", "sos",
        "උදව්", "හදිසි", "භය",
        "உதவு", "அபாயம்", "அவசர",
        "救命", "도와", "Hilfe", "Ayuda",
    ],
}

URGENCY_MAP = {
    "critical": [
        "ambulance", "unconscious", "dying", "murder", "rape", "gun",
        "sos", "emergency",
        "ඇම්බියුලන්ස්", "මරණය",
        "ஆம்புலன்ஸ்", "இறப்பு",
    ],
    "high": [
        "help", "police", "stolen", "robbery", "attack", "danger", "unsafe",
        "following",
        "උදව්", "පොලිස්",
        "உதவு", "போலீஸ்",
    ],
    "low": [],
}


def extract_entities(text: str) -> Dict[str, Any]:
    """
    SO3 — Location, threat, urgency extraction (keyword/phrase heuristics).
    Sinhala/Tamil keyword matching included for on-device tourism safety coverage.
    """
    text_lower = text.lower()

    found_locations = [loc for loc in SL_LOCATIONS if loc.lower() in text_lower]

    found_threats: Dict[str, bool] = {}
    for threat_type, keywords in THREAT_KEYWORDS.items():
        if any(kw.lower() in text_lower or kw in text for kw in keywords):
            found_threats[threat_type] = True

    urgency = "low"
    for level in ("critical", "high"):
        kws = URGENCY_MAP[level]
        if any(kw.lower() in text_lower or kw in text for kw in kws):
            urgency = level
            break

    return {
        "locations": found_locations,
        "threats": list(found_threats.keys()),
        "urgency": urgency,
        "raw_text": text[:500],
    }


def _keyword_distress_score(text: str) -> float:
    """SO3 — Fallback when RF model is unavailable."""
    tl = text.lower()
    hits = sum(1 for kw in DISTRESS_KEYWORDS if kw in tl)
    hits += sum(1 for kw in SINHALA_KW if kw in text)
    hits += sum(1 for kw in TAMIL_KW if kw in text)
    return min(hits / 4.0, 1.0)


def _extract_features_for_model(text: str) -> List[float]:
    """Must stay aligned with services/ml_models.py _extract_text_features."""
    tl = text.lower()
    feats = [float(kw in tl) for kw in DISTRESS_KEYWORDS]
    feats.append(float(any(kw in text for kw in SINHALA_KW)))
    feats.append(float(any(kw in text for kw in TAMIL_KW)))
    feats.append(min(len(text) / 200.0, 1.0))
    feats.append(sum(1 for c in text if c.isupper()) / max(len(text), 1))
    return feats


def classify_distress(text: str) -> Dict[str, Any]:
    """
    SO3 — Distress classification: RandomForest if present, else multilingual keywords.
    Returns is_distress, confidence, entities, recommended_action.
    """
    entities = extract_entities(text)
    bundle = _load_distress_model()

    if bundle is not None:
        model = bundle["model"]
        feats = np.array([_extract_features_for_model(text)], dtype=np.float64)
        proba = model.predict_proba(feats)[0]
        classes = list(model.classes_)
        pos_label = 1 if 1 in classes else max(classes)
        idx = classes.index(pos_label)
        confidence = float(proba[idx])
        is_distress = confidence >= 0.50
        source = "random_forest_model"
    else:
        confidence = _keyword_distress_score(text)
        is_distress = confidence >= 0.40
        source = "keyword_fallback"

    if not is_distress:
        action = "none"
    elif entities["urgency"] == "critical":
        action = "dispatch_emergency_services"
    elif entities["urgency"] == "high":
        action = "alert_nearby_police_and_hotel"
    else:
        action = "send_safety_check_notification"

    return {
        "is_distress": bool(is_distress),
        "confidence": round(confidence, 4),
        "entities": entities,
        "recommended_action": action,
        "classifier_source": source,
    }


def process_sos_audio(audio_data: Any, language: str = "en") -> Dict[str, Any]:
    """
    SO3 + SO4 — Full pipeline: transcribe → classify → optional dispatch recommendation.
    """
    from services.situation_location import resolve_situation_coordinates

    stt_result = transcribe_audio(audio_data, language)
    text = stt_result["text"]
    classification = classify_distress(text)
    situation_location = resolve_situation_coordinates(text, classification["entities"])

    dispatch = None
    if classification["is_distress"]:
        ent = classification["entities"]
        recipients = ["SLTDA_Control"]
        if ent["urgency"] in ("critical", "high"):
            recipients += ["Police_Emergency_119", "Hotel_Concierge"]
        if "medical" in ent.get("threats", []):
            recipients.append("Suwa_Seriya_Ambulance_1990")
        dispatch = {
            "should_dispatch": True,
            "recipients": recipients,
            "urgency": ent["urgency"],
            "detected_location": situation_location["label"],
            "dispatch_method": "situation_from_message",
            "situation_coordinates": {
                "latitude": situation_location["latitude"],
                "longitude": situation_location["longitude"],
            },
            "note": "SO4: Location inferred from speech/text — not device GPS.",
        }

    return {
        "transcription": stt_result,
        "classification": classification,
        "situation_location": situation_location,
        "dispatch": dispatch,
        "pipeline_steps": ["transcribe_audio", "extract_entities", "classify_distress", "dispatch_route"],
    }
