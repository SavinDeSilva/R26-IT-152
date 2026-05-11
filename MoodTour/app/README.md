# Sri Lanka Mood-Based Travel Bot (Python)

This app uses your webcam to detect facial emotion (FER2013 labels) and suggests Sri Lanka tours based on the detected mood.

## Requirements

- Python 3.9+ recommended
- Libraries:
  - `tensorflow`
  - `keras` (via `tensorflow`)
  - `opencv-python`
  - `numpy`

Tkinter is built into most Python installs on Windows.

## Dataset

### What is FER2013?

**FER2013** is a well-known facial-emotion dataset used in many tutorials/papers. It usually comes as a single file **`fer2013.csv`** with:
- a label (0–6)
- a 48×48 grayscale face image stored as pixel numbers

### What dataset are you using now?

Your current project uses **image folders** under `dataset/` (anger, contempt, disgust, fear, happy, sadness, surprise). That’s valid, but it’s usually **much smaller** than FER2013, so a simple CNN can give “confident but wrong” predictions.

Preferred (if you have it): place FER2013 CSV at:

- `dataset/fer2013.csv`

If that file is missing, the app will train from **exactly the folders you already have** under `dataset/`:

- `dataset/anger/*.png`
- `dataset/disgust/*.png`
- `dataset/fear/*.png`
- `dataset/happy/*.png`
- `dataset/sadness/*.png`
- `dataset/surprise/*.png`
- `dataset/contempt/*.png` (shown as **Contempt**; tour suggestions follow the Neutral flow)

## Run

From the project root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python app/mood_tour_chatbot.py
```

If you want to train in the console (see epoch logs clearly) before running the GUI:

```bash
python app/mood_tour_chatbot.py --train-only --retrain
python app/mood_tour_chatbot.py
```

First run may take time because it will train and save a model to:

- `app/models/fer_emotion_cnn.keras`

### If it keeps predicting Neutral

That usually happens when:
- The dataset is **imbalanced** (common when training from small folder datasets)
- Lighting/face crop makes the model uncertain

This app now uses **class weights + augmentation** and shows **Top guesses** to help debug.

To retrain with the new improvements (important if you already trained once):

```bash
python app/mood_tour_chatbot.py --retrain
```

If you want to force using FER2013-only (no folder dataset), run with:

```bash
python app/mood_tour_chatbot.py --fer-only --retrain
```

## If you get a "hash mismatch" error while installing

That usually means a corrupted cached wheel, or a proxy/mirror served a different artifact than expected.

Try:

```bash
python -m pip install --upgrade pip
pip cache purge
pip install --no-cache-dir -r requirements.txt
```


## React + Flask Web App

This project now supports a web architecture for research presentation:

- `frontend/` -> React UI (port `3000`)
- `backend/` -> Flask API entrypoint (port `5002`)
- Existing AI/ML logic remains in `app/` and is reused by the Flask backend.

### Run Web Backend

From project root:

```bash
pip install -r requirements.txt
python backend/flask_api.py
```

API endpoints:

- `GET /health`
- `POST /detect-emotion`
- `POST /generate-itinerary`

### Run React Frontend

From project root:

```bash
cd frontend
npm install
npm start
```

The React app will call Flask at `http://127.0.0.1:5002`.

