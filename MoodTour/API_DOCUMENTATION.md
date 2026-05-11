# MoodTour Flask API Documentation

## Server

- **Flask Port:** `5002`
- **Base URL:** `http://127.0.0.1:5002` (or `http://localhost:5002`)

## Endpoints

- `GET /`
- `GET /health`
- `POST /detect-emotion`
- `POST /generate-itinerary`

---

## 1) `GET /`

### URL

`http://localhost:5002/`

### Input

No input.

### Example Response

```json
{
  "message": "MoodTour API running",
  "status": "ok",
  "endpoints": {
    "health": "/health",
    "detect_emotion": "/detect-emotion (POST)",
    "generate_itinerary": "/generate-itinerary (POST)"
  }
}
```

---

## 2) `GET /health`

### URL

`http://localhost:5002/health`

### Input

No input.

### Example Response

```json
{
  "status": "running"
}
```

---

## 3) `POST /detect-emotion`

### URL

`http://localhost:5002/detect-emotion`

### Input Options

#### Option A: JSON

```json
{
  "image_base64": "data:image/jpeg;base64,..."
}
```

#### Option B: multipart/form-data

- File field name: `image`

### Example Response

```json
{
  "emotion": "sad",
  "confidence": 0.394
}
```

---

## 4) `POST /generate-itinerary`

### URL

`http://localhost:5002/generate-itinerary`

### Input (JSON)

Required fields:

- `emotion` (string)
- `budget` (number)
- `days` (number, >= 1)
- `traveler_type` (string)

Optional fields:

- `attraction_preferences` (array of strings)
- `selected_places` (array of strings)

### Example Request Body

```json
{
  "emotion": "neutral",
  "budget": 30000,
  "days": 2,
  "traveler_type": "solo",
  "attraction_preferences": ["nature", "beach"],
  "selected_places": []
}
```

### Example Response

```json
{
  "recommended_places": [
    "Nuwara Eliya Tea Estates",
    "Ella Rock",
    "Coconut Tree Hill",
    "Nine Arches Bridge"
  ],
  "safety_score": 8.72,
  "estimated_budget": 25500,
  "itinerary": {
    "day1": ["Nuwara Eliya Tea Estates - scenic hike + viewpoint photography"],
    "day2": ["Ella Rock - scenic hike + viewpoint photography"]
  },
  "itinerary_days": [
    {
      "day": 1,
      "title": "DAY1",
      "region": "Central",
      "place": "Nuwara Eliya Tea Estates",
      "category": "nature",
      "activity": "scenic hike + viewpoint photography",
      "estimated_cost": 8000,
      "safety_score": 9.0
    },
    {
      "day": 2,
      "title": "DAY2",
      "region": "Uva",
      "place": "Ella Rock",
      "category": "nature",
      "activity": "scenic hike + viewpoint photography",
      "estimated_cost": 9500,
      "safety_score": 8.8
    }
  ],
  "suggested_places": [
    {
      "rank": 1,
      "name": "Nuwara Eliya Tea Estates",
      "category": "nature",
      "region": "Central",
      "estimated_cost": 8000,
      "safety_score": 9.0,
      "match_score": 0.904
    }
  ]
}
```

---

## CORS

- **Is `flask-cors` installed?** Yes (`requirements.txt` includes `flask-cors`)
- **Is CORS enabled?** Yes (`CORS(app)` is enabled in `app/flask_api.py`)
