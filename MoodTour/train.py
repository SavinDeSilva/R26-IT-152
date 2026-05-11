"""
Train the emotion model on ``dataset/`` and save to ``app/models/``.
Same as: python app/mood_tour_chatbot.py --train-only --retrain [extra args]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "app" / "mood_tour_chatbot.py"
argv = [sys.executable, str(SCRIPT), "--train-only", "--retrain", *sys.argv[1:]]
raise SystemExit(subprocess.call(argv))
