"""
Backend entrypoint for React + Flask architecture.

This wraps the existing Flask API implementation under app/flask_api.py
to preserve current AI/ML logic unchanged.
"""

import os
import sys

# Ensure project root is importable when launched as:
#   python backend/flask_api.py
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.flask_api import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
