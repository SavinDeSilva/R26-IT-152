# Backend (Flask API)

This folder provides the Flask backend entrypoint for the web app architecture.

- Runtime entry: `backend/flask_api.py`
- Port: `http://127.0.0.1:5002`
- Uses existing AI/ML logic from the `app/` modules (model loading, emotion detection, recommendation pipeline) without changing the core model logic.

## Endpoints

- `GET /health`
- `POST /detect-emotion`
- `POST /generate-itinerary`

## Run

From project root:

```bash
pip install -r requirements.txt
python backend/flask_api.py
```
