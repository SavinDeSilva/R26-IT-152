"""
SOS Safety System — Flask Application Entry Point
SO4: Flask factory, CORS, logging, blueprint wiring, model preload checks.

Run from backend folder: python app.py
Port: 5005 (Windows/macOS/Linux)
"""

import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App factory (SO4)
# ---------------------------------------------------------------------------
def create_app():
    """Create Flask app with routes, CORS, folders, and ML preload."""
    base = os.path.dirname(os.path.abspath(__file__))
    for d in ("datasets", "models", "routes", "services", "utils"):
        os.makedirs(os.path.join(base, d), exist_ok=True)

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def log_request():
        app.logger.info("→ %s %s [%s]", request.method, request.path, request.remote_addr)

    @app.after_request
    def log_response(response):
        app.logger.info("← %s %s", response.status_code, request.path)
        return response

    from routes.api import api_bp, load_all_models
    from services.facilities_service import load_facility_tables

    app.register_blueprint(api_bp)

    app.logger.info("Startup: loading ML bundles from models/")
    print("\n[Startup] Loading ML models …")
    load_all_models()

    app.logger.info("Startup: loading facility CSV tables …")
    print("[Startup] Loading police_stations.csv & hospitals.csv …")
    load_facility_tables()

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"error": "Endpoint not found", "path": request.path}), 404

    @app.errorhandler(500)
    def server_error(err):
        return jsonify({"error": "Internal server error", "detail": str(err)}), 500

    return app


if __name__ == "__main__":
    app = create_app()

    print("\n" + "=" * 62)
    print("  SOS Safety System — AI Tourism Safety Platform")
    print("  Project ID : R26-IT-152")
    print("  Student    : De Silva D.S.K (IT22108654)  |  SLIIT")
    print("=" * 62)
    print("  Endpoints:")
    print("    GET  http://localhost:5005/")
    print("    GET  http://localhost:5005/health")
    print("    POST http://localhost:5005/sos/voice          [SO3+SO4]")
    print("    POST http://localhost:5005/sos/text           [SO3+SO4]")
    print("    GET  http://localhost:5005/danger-zone/predict [SO2]")
    print("    GET  http://localhost:5005/danger-zone/hotspots [SO2]")
    print("    GET  http://localhost:5005/hotel-safety/<d>   [SO1]")
    print("    GET  http://localhost:5005/geo/reverse")
    print("    GET  http://localhost:5005/facilities/nearest")
    print("    GET  http://localhost:5005/model-stats")
    print("    POST http://localhost:5005/offline/queue      [SO5]")
    print("    GET  http://localhost:5005/offline/status     [SO5]")
    print("=" * 62)
    print(f"  Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Press Ctrl+C to stop\n")

    app.run(host="0.0.0.0", port=5005, debug=True)
