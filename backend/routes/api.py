"""
SOS Safety System — Flask API Routes
SO4: REST API, GPS dispatch simulation, anonymous dispatch payloads.
SO5: Offline SOS queue in-memory with retry simulation.
"""

import json
import logging
import os
import pickle
import random
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from utils.sri_lanka_geo import DISTRICT_COORDS, is_likely_sri_lanka_land

from services.facilities_service import load_facility_tables, nearest_facilities
from services.situation_location import resolve_situation_coordinates

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blueprint (SO4)
# ---------------------------------------------------------------------------
api_bp = Blueprint("api", __name__)

# ---------------------------------------------------------------------------
# Model registry — loaded at startup via load_all_models() (SO2)
# ---------------------------------------------------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

_models: Dict[str, Any] = {
    "danger_zone_rf": None,
    "distress_classifier": None,
    "hotel_safety_rf": None,
}
_model_metrics: Dict[str, Any] = {}


def load_all_models() -> None:
    """SO2 — Load pickled bundles; graceful fallback if files missing."""
    global _model_metrics
    _model_metrics = {}
    for name in list(_models.keys()):
        path = os.path.join(MODELS_DIR, f"{name}.pkl")
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    _models[name] = pickle.load(f)
                logger.info("Loaded ML bundle: %s", name)
                print(f"  ✅ Loaded model: {name}")
            except Exception as exc:
                logger.exception("Failed loading %s: %s", name, exc)
                _models[name] = None
                print(f"  ⚠️  Corrupt or unreadable model: {name}")
        else:
            logger.warning("Model file missing (fallback mode): %s", path)
            print(f"  ⚠️  Model not found (will use fallback): {name}")

    metrics_path = os.path.join(MODELS_DIR, "model_metrics.json")
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, encoding="utf-8") as f:
                _model_metrics = json.load(f)
        except Exception as exc:
            logger.warning("Could not read model_metrics.json: %s", exc)

    try:
        load_facility_tables()
    except Exception as exc:
        logger.warning("Facilities CSV load skipped: %s", exc)


# ---------------------------------------------------------------------------
# SO5 — Offline alert queue (in-memory prototype)
# ---------------------------------------------------------------------------
_offline_queue: List[Dict[str, Any]] = []
_offline_dispatched: List[Dict[str, Any]] = []


def _simulate_offline_retries() -> None:
    """SO5 — Retry simulation: randomly flush oldest queued item as dispatched."""
    global _offline_queue
    if not _offline_queue:
        return
    if random.random() >= 0.22:
        return
    item = _offline_queue.pop(0)
    item["status"] = "dispatched_retry_simulation"
    item["dispatched_at"] = datetime.utcnow().isoformat() + "Z"
    item["note_dispatch"] = "SO5: Simulated sync after reconnect — alert forwarded to dispatch hub."
    _offline_dispatched.append(item)
    logger.info("SO5 offline retry simulation dispatched queue_id=%s", item.get("queue_id"))


# ---------------------------------------------------------------------------
# Sri Lanka districts for hotspots (SO1 / SO2)
# ---------------------------------------------------------------------------
DISTRICTS_GEO = DISTRICT_COORDS

INCIDENT_TYPES = [
    "harassment", "road_accident", "theft", "medical_emergency",
    "natural_hazard", "scam", "unsafe_transport",
]


def _normalize_district_label(name: str) -> str:
    """Map human-readable district names to keys used during training."""
    raw = (name or "").strip()
    if raw in DISTRICT_COORDS:
        return raw
    cand = raw.replace(" ", "_")
    if cand in DISTRICT_COORDS:
        return cand
    low = raw.lower()
    for k in DISTRICT_COORDS:
        if k.replace("_", " ").lower() == low:
            return k
    return cand


def _encode_district(le: Any, district: str) -> int:
    try:
        return int(le.transform([district])[0])
    except Exception:
        return len(le.classes_) // 2


def _encode_incident(le: Any, incident: str) -> int:
    try:
        return int(le.transform([incident])[0])
    except Exception:
        return len(le.classes_) // 2


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@api_bp.route("/", methods=["GET"])
def service_info():
    """SO4 — Service metadata and endpoint index."""
    return jsonify({
        "service": "SOS Safety System — AI Tourism Safety & Itinerary Platform",
        "version": "1.0.0-pp1",
        "project_id": "R26-IT-152",
        "student": "De Silva D.S.K (IT22108654)",
        "university": "SLIIT Sri Lanka",
        "description": "AI-powered tourist safety platform for Sri Lanka",
        "endpoints": {
            "GET  /": "Service info",
            "GET  /health": "Health check",
            "POST /sos/voice": "SO3+SO4 — Voice SOS pipeline",
            "POST /sos/text": "SO3+SO4 — Text SOS pipeline",
            "GET  /danger-zone/predict": "SO2 — Danger zone prediction",
            "GET  /danger-zone/hotspots": "SO2 — Danger hotspots",
            "GET  /danger-zone/social-risk-points": "SO1/SO2 — Risk posts from social_media_posts.csv for map",
            "GET  /geo/reverse": "Place name from coordinates (Nominatim proxy)",
            "GET  /hotel-safety/<district>": "SO1 — Hotel safety rankings",
            "GET  /facilities/nearest": "Nearest police & hospitals (CSV datasets)",
            "GET  /model-stats": "ML metrics",
            "POST /offline/queue": "SO5 — Queue offline SOS",
            "GET  /offline/status": "SO5 — Offline queue status",
        },
        "objectives_covered": ["SO1", "SO2", "SO3", "SO4", "SO5"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@api_bp.route("/health", methods=["GET"])
def health():
    loaded = sum(1 for v in _models.values() if v is not None)
    return jsonify({
        "status": "healthy",
        "models_loaded": loaded,
        "models_total": len(_models),
        "model_status": {k: ("loaded" if v else "fallback_mode") for k, v in _models.items()},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "offline_queue": len(_offline_queue),
        "offline_queue_depth": len(_offline_queue),
    })


# ---------------------------------------------------------------------------
# POST /sos/voice — SO3 + SO4
# ---------------------------------------------------------------------------
@api_bp.route("/sos/voice", methods=["POST"])
def sos_voice():
    """SO3 — Simulated STT + NLP; SO4 — anonymous GPS dispatch simulation."""
    try:
        from services.nlp_pipeline import process_sos_audio
    except Exception as exc:
        logger.exception("NLP import failed: %s", exc)
        return jsonify({"error": "NLP pipeline unavailable", "detail": str(exc)}), 500

    body = request.get_json(silent=True) or {}
    audio = body.get("audio_data")
    language = body.get("language", "en")
    device_location = body.get("device_location")

    try:
        result = process_sos_audio(audio, language)
    except Exception as exc:
        logger.exception("process_sos_audio failed: %s", exc)
        return jsonify({"error": "Voice SOS processing failed", "detail": str(exc)}), 500

    code = 201 if result.get("dispatch") else 200
    payload = {
        "endpoint": "sos_voice",
        "objective": "SO3 + SO4",
        **result,
    }
    if device_location is not None:
        payload["device_location"] = device_location
    return jsonify(payload), code


# ---------------------------------------------------------------------------
# POST /sos/text — SO3 + SO4
# ---------------------------------------------------------------------------
@api_bp.route("/sos/text", methods=["POST"])
def sos_text():
    """SO3 — Text distress; SO4 — dispatch routing."""
    try:
        from services.nlp_pipeline import classify_distress
    except Exception as exc:
        return jsonify({"error": "NLP pipeline unavailable", "detail": str(exc)}), 500

    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    language = body.get("language", "en")
    device_location = body.get("device_location")

    if not text:
        return jsonify({"error": "Field 'text' is required"}), 400

    classification = classify_distress(text)
    situation_location = resolve_situation_coordinates(text, classification["entities"])

    dispatch = None
    if classification["is_distress"]:
        entities = classification["entities"]
        recipients = ["SLTDA_Control"]
        if entities["urgency"] in ("critical", "high"):
            recipients += ["Police_Emergency_119", "Hotel_Concierge"]
        if "medical" in entities.get("threats", []):
            recipients.append("Suwa_Seriya_Ambulance_1990")
        dispatch = {
            "should_dispatch": True,
            "recipients": recipients,
            "urgency": entities["urgency"],
            "detected_location": situation_location["label"],
            "dispatch_method": "situation_from_message",
            "situation_coordinates": {
                "latitude": situation_location["latitude"],
                "longitude": situation_location["longitude"],
            },
        }

    code = 201 if dispatch else 200
    out = {
        "endpoint": "sos_text",
        "objective": "SO3 + SO4",
        "input_text": text,
        "language": language,
        "classification": classification,
        "situation_location": situation_location,
        "dispatch": dispatch,
    }
    if device_location is not None:
        out["device_location"] = device_location
    return jsonify(out), code


# ---------------------------------------------------------------------------
# GET /danger-zone/predict — SO2
# ---------------------------------------------------------------------------
@api_bp.route("/danger-zone/predict", methods=["GET"])
def danger_zone_predict():
    """SO2 — Danger zone RandomForest or heuristic fallback."""
    import numpy as np

    district = request.args.get("district", "Colombo")
    district_key = _normalize_district_label(district)
    hour = int(request.args.get("hour", datetime.now().hour))
    incident_type = request.args.get("incident_type", "harassment")

    bundle = _models["danger_zone_rf"]

    if bundle is not None:
        model = bundle["model"]
        le_d = bundle["le_district"]
        le_i = bundle["le_incident"]
        now = datetime.now()
        risk_score = random.uniform(0.3, 0.9)
        X = np.array([[
            hour,
            now.weekday(),
            now.month,
            risk_score,
            _encode_district(le_d, district_key),
            _encode_incident(le_i, incident_type),
        ]])
        prob_dz = float(model.predict_proba(X)[0][1])
        is_dz = prob_dz >= 0.50
        source = "random_forest_model"
    else:
        prob_dz = round(random.uniform(0.2, 0.85), 4)
        is_dz = prob_dz >= 0.55
        source = "heuristic_fallback"

    disp = district_key.replace("_", " ")
    risk_level = "high" if prob_dz >= 0.70 else ("medium" if prob_dz >= 0.40 else "low")
    warning = {
        "high": f"⚠️ DANGER ZONE ACTIVE in {disp}. Avoid area. Police alerted.",
        "medium": f"🟡 Elevated risk in {disp}. Exercise caution.",
        "low": f"✅ {disp} is currently safer on aggregate — stay situationally aware.",
    }[risk_level]

    return jsonify({
        "endpoint": "danger_zone_predict",
        "objective": "SO2",
        "district": disp,
        "district_key": district_key,
        "hour": hour,
        "incident_type": incident_type,
        "danger_zone": is_dz,
        "risk_probability": round(prob_dz, 4),
        "risk_level": risk_level,
        "warning": warning,
        "predictive_horizon": "30 minutes",
        "classifier": source,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# GET /danger-zone/hotspots — SO2
# ---------------------------------------------------------------------------
@api_bp.route("/danger-zone/hotspots", methods=["GET"])
def danger_zone_hotspots():
    """SO2 — Top danger hotspots with jittered coordinates for mapping."""
    all_districts = list(DISTRICTS_GEO.keys())
    random.shuffle(all_districts)
    hotspots = []
    for dist in all_districts[:5]:
        lat, lon = DISTRICTS_GEO[dist]
        risk = round(random.uniform(0.55, 0.95), 4)
        hotspots.append({
            "district": dist.replace("_", " "),
            "latitude": lat + random.uniform(-0.02, 0.02),
            "longitude": lon + random.uniform(-0.02, 0.02),
            "risk_probability": risk,
            "risk_level": "high" if risk >= 0.70 else "medium",
            "primary_incident": random.choice(INCIDENT_TYPES),
            "active_reports": random.randint(3, 25),
        })
    hotspots.sort(key=lambda x: x["risk_probability"], reverse=True)
    return jsonify({
        "endpoint": "danger_zone_hotspots",
        "objective": "SO2",
        "hotspots": hotspots,
        "count": len(hotspots),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# GET /danger-zone/social-risk-points — SO1/SO2 map layer from social_media_posts.csv
# ---------------------------------------------------------------------------
@api_bp.route("/danger-zone/social-risk-points", methods=["GET"])
def danger_zone_social_risk_points():
    """
    Return coordinates for risk-related social posts (dataset-driven map).
    Filters: danger_zone==1 OR risk_score >= min_risk. Large CSVs are capped for browser performance.
    """
    import pandas as pd

    max_points = request.args.get("max_points", default=10000, type=int)
    max_points = min(max(400, max_points), 25000)
    min_risk = request.args.get("min_risk", default=0.55, type=float)
    danger_only = request.args.get("danger_only", default="", type=str).lower() in ("1", "true", "yes")

    csv_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "social_media_posts.csv")
    if not os.path.exists(csv_path):
        return jsonify({
            "error": "social_media_posts.csv not found — run datasets/generate_sos_data.py",
            "points": [],
        }), 404

    try:
        df = pd.read_csv(
            csv_path,
            usecols=[
                "post_id", "district", "latitude", "longitude",
                "incident_type", "risk_score", "danger_zone", "timestamp", "text_snippet",
            ],
        )
    except Exception as exc:
        logger.exception("social_media_posts read failed: %s", exc)
        return jsonify({"error": str(exc), "points": []}), 500

    if danger_only:
        mask = df["danger_zone"].astype(int) == 1
    else:
        mask = (df["danger_zone"].astype(int) == 1) | (df["risk_score"].astype(float) >= min_risk)

    risk_df = df.loc[mask].copy()
    total_matching = int(len(risk_df))
    capped = False
    if total_matching > max_points:
        risk_df = risk_df.sample(n=max_points, random_state=42)
        capped = True

    land_only = request.args.get("land_only", default="true", type=str).lower() in ("1", "true", "yes")
    points = []
    dropped_offshore = 0
    for _, row in risk_df.iterrows():
        lat_f = float(row["latitude"])
        lon_f = float(row["longitude"])
        if land_only and not is_likely_sri_lanka_land(lat_f, lon_f):
            dropped_offshore += 1
            continue
        dist = str(row["district"])
        points.append({
            "post_id": str(row["post_id"]),
            "district": dist.replace("_", " "),
            "latitude": lat_f,
            "longitude": lon_f,
            "incident_type": str(row["incident_type"]),
            "risk_score": round(float(row["risk_score"]), 4),
            "danger_zone": int(row["danger_zone"]),
            "timestamp": str(row["timestamp"]),
            "text_snippet": str(row["text_snippet"])[:160],
        })

    return jsonify({
        "endpoint": "social_risk_points",
        "objective": "SO1 + SO2",
        "source_file": "datasets/social_media_posts.csv",
        "filter": {"danger_only": danger_only, "min_risk": min_risk, "land_only": land_only},
        "total_matching_in_dataset": total_matching,
        "dropped_offshore_bbox": dropped_offshore if land_only else 0,
        "returned": len(points),
        "capped": capped,
        "max_points_requested": max_points,
        "points": points,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# GET /geo/reverse — proxy Nominatim (browser cannot call OSM directly due to CORS)
# ---------------------------------------------------------------------------
@api_bp.route("/geo/reverse", methods=["GET"])
def geo_reverse():
    """Approximate place name for lat/lon — uses OpenStreetMap Nominatim (please use sparingly)."""
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Provide lat and lon query parameters"}), 400

    params = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "zoom": "14"})
    url = f"https://nominatim.openstreetmap.org/reverse?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SOS-Safety-Demo/1.0 (education prototype; +https://openstreetmap.org/copyright)",
            "Accept-Language": "en",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.warning("Nominatim HTTP error: %s", exc)
        return jsonify({"error": "Geocoding service unavailable", "display_name": None}), 502
    except Exception as exc:
        logger.exception("reverse geocode failed: %s", exc)
        return jsonify({"error": str(exc), "display_name": None}), 502

    addr = payload.get("address") or {}
    short_label = (
        addr.get("suburb")
        or addr.get("town")
        or addr.get("city")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
    )
    return jsonify({
        "display_name": payload.get("display_name"),
        "short_label": short_label,
        "address": addr,
    })


# ---------------------------------------------------------------------------
# GET /facilities/nearest — police_stations.csv + hospitals.csv (SO1 / SO4)
# ---------------------------------------------------------------------------
@api_bp.route("/facilities/nearest", methods=["GET"])
def facilities_nearest():
    """Nearest police stations & hospitals vs reference point (message-derived or district centre)."""
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        district_q = request.args.get("district")
        ref_label = request.args.get("label")

        if lat is None or lon is None:
            if district_q:
                dk = _normalize_district_label(district_q)
                pair = DISTRICT_COORDS.get(dk)
                if pair:
                    lat, lon = pair
                else:
                    lat, lon = DISTRICT_COORDS["Colombo"]
                ref_label = ref_label or dk.replace("_", " ")
            else:
                return jsonify({
                    "error": "Provide lat & lon (situation coordinates) or district=Colombo",
                }), 400

        data = nearest_facilities(lat, lon)
        payload = {
            "endpoint": "facilities_nearest",
            "objective": "SO1",
            "reference": {
                "latitude": float(lat),
                "longitude": float(lon),
                "label": ref_label or (district_q or "situation_reference"),
            },
            **data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if not data.get("nearest_police") and not data.get("nearest_hospitals"):
            payload["warning"] = (
                "No facility rows loaded — ensure backend/datasets/police_stations.csv "
                "and hospitals.csv exist and restart the API."
            )
        return jsonify(payload)
    except Exception as exc:
        logger.exception("facilities_nearest failed: %s", exc)
        return jsonify({"error": "facilities_nearest failed", "detail": str(exc)}), 500


# ---------------------------------------------------------------------------
# GET /hotel-safety/<district> — SO1
# ---------------------------------------------------------------------------
@api_bp.route("/hotel-safety/<district>", methods=["GET"])
def hotel_safety(district):
    """SO1 — Hotel safety listings scored via RF or heuristic."""
    import numpy as np

    try:
        bundle = _models["hotel_safety_rf"]
        features = [
            "overall_safety", "women_safety", "family_safety",
            "night_safety", "harassment_reports", "theft_reports",
        ]

        hotels = []
        hotel_names = [
            "Cinnamon Grand", "Jetwing Blue", "Lighthouse Hotel",
            "Amangalla", "The Kandy House", "98 Acres Resort",
            "Tintagel", "Araliya Beach Resort", "Kings Pavilion", "Villa Rosa",
        ]

        for i in range(5):
            ov = round(random.uniform(3.0, 5.0), 2)
            row = {
                "overall_safety": float(ov),
                "women_safety": float(round(max(0.0, ov + random.uniform(-0.5, 0.5)), 2)),
                "family_safety": float(round(max(0.0, ov + random.uniform(-0.5, 0.5)), 2)),
                "night_safety": float(round(max(0.0, ov + random.uniform(-0.8, 0.3)), 2)),
                "harassment_reports": int(random.randint(0, 3)),
                "theft_reports": int(random.randint(0, 2)),
            }

            if bundle is not None:
                model = bundle["model"]
                le = bundle["le_risk"]
                X = np.array([[row[f] for f in features]], dtype=np.float64)
                pred_raw = model.predict(X)
                pred_idx = int(np.asarray(pred_raw).ravel()[0])
                inv = le.inverse_transform(np.array([pred_idx]))
                risk_level = str(np.asarray(inv).ravel()[0])
            else:
                risk_level = "low" if ov >= 3.5 else "medium"

            row["hotel_id"] = f"H{random.randint(10000, 99999)}"
            row["hotel_name"] = f"{hotel_names[i]} {district}"
            row["district"] = str(district)
            row["risk_level"] = risk_level
            row["safety_badge"] = (
                "🟢 Safe" if risk_level == "low" else ("🟡 Moderate" if risk_level == "medium" else "🔴 Caution")
            )
            hotels.append(row)

        hotels.sort(key=lambda x: x["overall_safety"], reverse=True)
        return jsonify({
            "endpoint": "hotel_safety",
            "objective": "SO1",
            "district": str(district),
            "hotels": hotels,
            "count": len(hotels),
        })
    except Exception as exc:
        logger.exception("hotel_safety failed: %s", exc)
        return jsonify({"error": "hotel_safety failed", "detail": str(exc)}), 500


# ---------------------------------------------------------------------------
# GET /model-stats
# ---------------------------------------------------------------------------
@api_bp.route("/model-stats", methods=["GET"])
def model_stats():
    """Aggregate ML bundle availability and training metrics."""
    stats = {}
    for name, bundle in _models.items():
        if bundle:
            stats[name] = {
                "status": "loaded",
                "metrics": bundle.get("metrics", {}),
                "dataset_size": bundle.get("dataset_size", "N/A"),
                "trained_at": bundle.get("trained_at", "N/A"),
                "features": bundle.get("features", []),
            }
        else:
            stats[name] = {"status": "not_loaded", "metrics": _model_metrics.get(name, {})}

    return jsonify({
        "endpoint": "model_stats",
        "model_stats": stats,
        "models_loaded": sum(1 for v in _models.values() if v),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ---------------------------------------------------------------------------
# POST /offline/queue — SO5
# ---------------------------------------------------------------------------
@api_bp.route("/offline/queue", methods=["POST"])
def offline_queue():
    """SO5 — Queue SOS payload until connectivity returns."""
    body = request.get_json(silent=True) or {}
    tourist_id = body.get("tourist_id", "anonymous")
    location = body.get("location", {})
    distress_type = body.get("distress_type", "general")

    if not location or "lat" not in location or "lon" not in location:
        return jsonify({"error": "Field 'location' with {lat, lon} is required"}), 400

    alert = {
        "queue_id": str(uuid.uuid4()),
        "tourist_id": tourist_id,
        "location": location,
        "distress_type": distress_type,
        "queued_at": datetime.utcnow().isoformat() + "Z",
        "status": "queued",
        "note": "SO5 — Stored in local server memory for PP1 prototype.",
    }
    _offline_queue.append(alert)
    logger.info("SO5 queued offline SOS queue_id=%s", alert["queue_id"])

    return jsonify({
        "endpoint": "offline_queue",
        "objective": "SO5",
        "queue_id": alert["queue_id"],
        "status": "queued",
        "position": len(_offline_queue),
        "message": "SOS alert queued for dispatch on reconnection.",
    }), 201


# ---------------------------------------------------------------------------
# GET /offline/status — SO5
# ---------------------------------------------------------------------------
@api_bp.route("/offline/status", methods=["GET"])
def offline_status():
    """SO5 — Queue depth, recent items, simulated retries."""
    _simulate_offline_retries()
    return jsonify({
        "endpoint": "offline_status",
        "objective": "SO5",
        "queued_alerts": len(_offline_queue),
        "queue": _offline_queue[-10:],
        "recent_dispatched_simulations": _offline_dispatched[-10:],
        "dispatched_total": len(_offline_dispatched),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
