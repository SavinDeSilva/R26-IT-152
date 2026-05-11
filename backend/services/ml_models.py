"""
SOS Safety System — ML Model Training
SO2: Danger Zone Prediction (Random Forest, 30-min horizon)
SO3: Distress Detection Classifier (Random Forest, keyword features)
     Hotel Safety Scorer (Random Forest)

Run from backend/ folder: python services/ml_models.py
Saves to: backend/models/
"""

import os
import sys
import pickle
import json
import random

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from utils.ml_keywords import DISTRESS_KEYWORDS, SINHALA_KW, TAMIL_KW

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
MODELS_DIR   = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def _save_model(obj, filename):
    path = os.path.join(MODELS_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"   💾 Saved → {path}")
    return path


def _metrics_report(name, y_test, y_pred, y_proba=None):
    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    auc = None
    if y_proba is not None:
        try:
            # binary or multiclass
            if y_proba.ndim == 2 and y_proba.shape[1] == 2:
                auc = roc_auc_score(y_test, y_proba[:, 1])
            else:
                auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")
        except Exception:
            auc = None
    print(f"   📊 {name}: accuracy={acc:.4f}  f1={f1:.4f}" + (f"  auc={auc:.4f}" if auc else ""))
    return {"accuracy": round(acc, 4), "f1": round(f1, 4), "auc": round(auc, 4) if auc else None}


# ---------------------------------------------------------------------------
# MODEL 1 — Danger Zone Prediction  (SO2)
# ---------------------------------------------------------------------------
def train_danger_zone_model():
    print("\n[SO2] Training Danger Zone Prediction model …")
    csv_path = os.path.join(DATASETS_DIR, "social_media_posts.csv")
    df = pd.read_csv(csv_path)

    # Encode categoricals
    le_district  = LabelEncoder().fit(df["district"])
    le_incident  = LabelEncoder().fit(df["incident_type"])
    df["district_enc"]  = le_district.transform(df["district"])
    df["incident_enc"]  = le_incident.transform(df["incident_type"])

    features = ["hour", "day_of_week", "month", "risk_score", "district_enc", "incident_enc"]
    X = df[features].values
    y = df["danger_zone"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred  = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)
    metrics = _metrics_report("DangerZoneRF", y_test, y_pred, y_proba)

    bundle = {
        "model":          clf,
        "le_district":    le_district,
        "le_incident":    le_incident,
        "features":       features,
        "metrics":        metrics,
        "dataset_size":   len(df),
        "trained_at":     pd.Timestamp.now().isoformat(),
    }
    _save_model(bundle, "danger_zone_rf.pkl")
    return metrics


# ---------------------------------------------------------------------------
# MODEL 2 — Distress Detection Classifier  (SO3)
# ---------------------------------------------------------------------------
def _extract_text_features(text: str):
    """SO3 — keyword-based feature extraction for distress classifier."""
    text_lower = str(text).lower()
    feats = [int(kw in text_lower) for kw in DISTRESS_KEYWORDS]
    feats += [int(any(kw in text for kw in SINHALA_KW))]  # Sinhala flag
    feats += [int(any(kw in text for kw in TAMIL_KW))]    # Tamil flag
    feats += [min(len(text) / 200.0, 1.0)]               # normalised length
    feats += [sum(1 for c in text if c.isupper()) / max(len(text), 1)]  # caps ratio
    return feats


def train_distress_classifier():
    print("\n[SO3] Training Distress Detection Classifier …")
    csv_path = os.path.join(DATASETS_DIR, "distress_phrases.csv")
    df = pd.read_csv(csv_path)

    X = np.array([_extract_text_features(t) for t in df["text"]])
    y = df["is_distress"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred  = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)
    metrics = _metrics_report("DistressRF", y_test, y_pred, y_proba)

    feature_names = (
        DISTRESS_KEYWORDS
        + ["sinhala_kw_flag", "tamil_kw_flag", "text_length_norm", "caps_ratio"]
    )
    bundle = {
        "model":          clf,
        "features":       feature_names,
        "keywords":       DISTRESS_KEYWORDS,
        "sinhala_kw":     SINHALA_KW,
        "tamil_kw":       TAMIL_KW,
        "metrics":        metrics,
        "dataset_size":   len(df),
        "trained_at":     pd.Timestamp.now().isoformat(),
    }
    _save_model(bundle, "distress_classifier.pkl")
    return metrics


# ---------------------------------------------------------------------------
# MODEL 3 — Hotel Safety Scorer
# ---------------------------------------------------------------------------
def train_hotel_safety_model():
    print("\n[SO1/SO4] Training Hotel Safety Scorer …")
    csv_path = os.path.join(DATASETS_DIR, "hotel_safety_reviews.csv")
    df = pd.read_csv(csv_path)

    # Composite risk label: high / medium / low
    df["composite"] = (
        df["overall_safety"] * 0.3
        + df["women_safety"]  * 0.2
        + df["family_safety"] * 0.2
        + df["night_safety"]  * 0.2
        - df["harassment_reports"] * 0.05
        - df["theft_reports"]      * 0.05
    )
    df["risk_level"] = pd.cut(
        df["composite"], bins=[-999, 2.0, 3.5, 999],
        labels=["high", "medium", "low"]
    )

    le_risk = LabelEncoder().fit(df["risk_level"])
    y = le_risk.transform(df["risk_level"])

    features = [
        "overall_safety", "women_safety", "family_safety",
        "night_safety", "harassment_reports", "theft_reports",
    ]
    X = df[features].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred  = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)
    metrics = _metrics_report("HotelSafetyRF", y_test, y_pred, y_proba)

    bundle = {
        "model":      clf,
        "le_risk":    le_risk,
        "features":   features,
        "metrics":    metrics,
        "dataset_size": len(df),
        "trained_at": pd.Timestamp.now().isoformat(),
    }
    _save_model(bundle, "hotel_safety_rf.pkl")
    return metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("SOS Safety System — ML Model Training")
    print("=" * 60)

    m1 = train_danger_zone_model()
    m2 = train_distress_classifier()
    m3 = train_hotel_safety_model()

    summary = {
        "danger_zone_rf":        m1,
        "distress_classifier":   m2,
        "hotel_safety_rf":       m3,
    }
    summary_path = os.path.join(MODELS_DIR, "model_metrics.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✅  All models trained. Metrics saved → {summary_path}")
    for name, metrics in summary.items():
        print(f"   {name}: {metrics}")
