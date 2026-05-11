import os
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from .api_emotion import EmotionDetectionService
    from .api_recommendation import generate_rule_based_itinerary
except ImportError:
    # Allows running as: python app/flask_api.py
    from api_emotion import EmotionDetectionService
    from api_recommendation import generate_rule_based_itinerary


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # Enable React frontend integration.

    app_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(app_dir)
    emotion_service = EmotionDetectionService(project_root=project_root)

    @app.get("/")
    def index():
        return jsonify(
            {
                "message": "MoodTour API running",
                "status": "ok",
                "endpoints": {
                    "health": "/health",
                    "detect_emotion": "/detect-emotion (POST)",
                    "generate_itinerary": "/generate-itinerary (POST)",
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "running"})

    @app.post("/detect-emotion")
    def detect_emotion():
        """
        Supports:
        - JSON: { "image_base64": "..." }
        - multipart/form-data: file field "image"
        """
        try:
            image_base64 = None
            image_bytes = None

            if request.is_json:
                body: Dict[str, Any] = request.get_json(silent=True) or {}
                image_base64 = body.get("image_base64")

            if image_base64 is None and "image" in request.files:
                image_bytes = request.files["image"].read()

            result = emotion_service.detect_from_payload(
                image_base64=image_base64,
                image_bytes=image_bytes,
            )
            return jsonify(
                {
                    "emotion": result["emotion"],
                    "confidence": result["confidence"],
                }
            )
        except ValueError as e:
            return _json_error(str(e), 400)
        except Exception as e:
            return _json_error(f"Emotion detection failed: {type(e).__name__}: {e}", 500)

    @app.post("/generate-itinerary")
    def generate_itinerary():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _json_error("Invalid JSON body.", 400)

        emotion = str(body.get("emotion", "neutral")).strip().lower()
        budget = body.get("budget", 30000)
        days = body.get("days", 2)
        traveler_type = str(body.get("traveler_type", "solo")).strip().lower()
        attraction_preferences = body.get("attraction_preferences", [])
        selected_places = body.get("selected_places", [])
        if attraction_preferences is None:
            attraction_preferences = []
        if selected_places is None:
            selected_places = []
        if not isinstance(attraction_preferences, list):
            return _json_error("`attraction_preferences` must be a list when provided.", 400)
        if not isinstance(selected_places, list):
            return _json_error("`selected_places` must be a list when provided.", 400)

        try:
            budget = int(budget)
            days = int(days)
        except Exception:
            return _json_error("`budget` and `days` must be numeric.", 400)

        if days < 1:
            return _json_error("`days` must be >= 1.", 400)

        try:
            data = generate_rule_based_itinerary(
                emotion=emotion,
                budget=budget,
                days=days,
                traveler_type=traveler_type,
                attraction_preferences=attraction_preferences,
                selected_places=selected_places,
            )
            return jsonify(data)
        except Exception as e:
            return _json_error(f"Itinerary generation failed: {type(e).__name__}: {e}", 500)

    return app


app = create_app()


if __name__ == "__main__":
    # Dedicated Flask backend port for React integration.
    app.run(host="127.0.0.1", port=5002, debug=False)
