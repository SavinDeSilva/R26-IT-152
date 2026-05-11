import os
import json
import time
import threading
import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import cv2

import tensorflow as tf
from tensorflow import keras
import traceback

try:
    from .chat_pick_resolver import resolve_chat_pick_label, resolve_selection_keys
    from .recommendation_engine import (
        MAX_TRIP_DAYS,
        ItineraryResult,
        slot_line_cost,
        generate_itinerary,
        generate_itinerary_from_user_picks,
    )
    from .tourism_data import SRI_LANKA_ATTRACTIONS
except ImportError:
    from chat_pick_resolver import resolve_chat_pick_label, resolve_selection_keys
    from recommendation_engine import (
        MAX_TRIP_DAYS,
        ItineraryResult,
        slot_line_cost,
        generate_itinerary,
        generate_itinerary_from_user_picks,
    )
    from tourism_data import SRI_LANKA_ATTRACTIONS

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Tkinter is required for the GUI. On Windows it should be included with Python.\n"
        f"Original error: {e}"
    )


# =========================
# Mood-based tour content
# =========================

EMOTIONS_FER2013 = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

# For your prompt, "Excited" is effectively "Surprise" in FER2013.
TOUR_BOT: Dict[str, Dict[str, object]] = {
    "Happy": {
        "question": (
            "Feeling full of energy today? Imagine riding the waves at Hikkaduwa Beach, "
            "feeling the sun on your face and the ocean at your fingertips! 🏄"
        ),
        "primary": "Hikkaduwa Beach (surfing & beach vibes) – ride the waves and soak up the sunshine!",
        "alternatives": [
            "Kitulgala (jungle trekking & rafting) – feel your heart race with adventure!",
            "Mirissa (whale watching & beach) – witness majestic whales in crystal waters!",
            "Sigiriya Rock Fortress – climb a world wonder and be amazed by the views!",
            "Bentota Water Sports – splash into excitement and fun!",
            "Madu River Sunset Boat Ride – relax as golden hues reflect on tranquil waters!",
            "Arugam Bay (surfing) – ride legendary waves and feel the thrill!",
            "Ella (Nine Arches Bridge & waterfalls) – stroll through breathtaking landscapes!",
        ],
    },
    "Sad": {
        "question": (
            "Feeling low today? Picture yourself strolling through Nuwara Eliya tea estates, "
            "sipping warm tea and breathing fresh, crisp mountain air 💛"
        ),
        "primary": "Nuwara Eliya (tea estates & cool hills) – slow down, sip warm tea, and breathe deeply.",
        "alternatives": [
            "Kandy (spa & botanical gardens) – rejuvenate your body and soul!",
            "Horton Plains (treks & scenic views) – feel serenity and wonder at every step!",
            "Peradeniya Botanical Gardens – immerse in nature’s peaceful embrace!",
            "Diyaluma Falls – hear the soothing roar of cascading waters!",
            "Minneriya & Kaudulla (elephant safaris) – witness gentle giants in their habitat!",
            "Ella (Little Adam’s Peak & waterfalls) – recharge your spirit surrounded by beauty!",
            "Knuckles Mountain Range (gentle treks) – embrace nature’s quiet grandeur!",
        ],
    },
    "Angry": {
        "question": (
            "Feeling tense? Picture releasing all stress as you trek through Knuckles Mountains "
            "or feel the calm sea breeze at Galle 😌"
        ),
        "primary": "Knuckles Mountain Range (trek + fresh air) – let the trails drain the tension away.",
        "alternatives": [
            "Galle (fort & wellness retreat) – let history and tranquility soothe you!",
            "Kalutara (beach & relaxation) – feel your tension melt into the waves!",
            "Udawalawe (elephant safari) – connect with majestic wildlife!",
            "Bentota (yoga & beach) – harmonize body and mind!",
            "Ella (waterfalls & treks) – escape into nature’s gentle embrace!",
            "Ritigala Forest Monastery – meditate in ancient serenity!",
            "Tangalle (sunset beaches) – let colors of the sky heal you!",
        ],
    },
    "Fear": {
        "question": (
            "Feeling nervous? Imagine climbing Sigiriya Rock Fortress at your own pace, "
            "conquering fears, and witnessing the world from above 💛"
        ),
        "primary": "Sigiriya Rock Fortress – take it step-by-step and celebrate the view at the top.",
        "alternatives": [
            "Polonnaruwa (ancient ruins) – wander through history and feel awe!",
            "Minneriya National Park (elephant safari) – watch giants roam freely!",
            "Anuradhapura (temples & sacred sites) – step into sacred calm!",
            "Ritigala Forest Monastery – find peace among ancient trees!",
            "Adam’s Peak (gentle sunrise trek) – experience a life-changing sunrise!",
            "Madu River (boat ride) – glide through tranquil waters and feel serenity!",
            "Horton Plains (nature walk) – embrace wide-open vistas and fresh air!",
        ],
    },
    "Surprise": {
        "question": (
            "Feeling adventurous? Imagine spotting leopards in Yala or riding thrilling waves in Arugam Bay 😃"
        ),
        "primary": "Yala National Park (wildlife safari) – chase that adrenaline with nature’s drama.",
        "alternatives": [
            "Arugam Bay (surfing) – the thrill of perfect waves awaits!",
            "Mirissa (whale watching) – be amazed by nature’s giants!",
            "Dambulla Cave Temples – uncover mystical wonders carved in rock!",
            "Horton Plains (World’s End trek) – stand on the edge of the world!",
            "Kitulgala (rafting & jungle trekking) – feel adrenaline and freedom!",
            "Pigeon Island (snorkeling) – dive into vibrant underwater worlds!",
            "Udawalawe (wildlife safari) – connect with untamed nature!",
        ],
    },
    "Disgust": {
        "question": (
            "Feeling overwhelmed? Imagine walking peacefully in Udawattekele Sanctuary or "
            "feeling the sun on a quiet beach 💛"
        ),
        "primary": "Udawattekele Sanctuary (calm forest walk) – reset your mind with quiet greenery.",
        "alternatives": [
            "Trincomalee (Nilaveli & Uppuveli beach) – crystal waters will refresh your soul!",
            "Nuwara Eliya (tea estates & Gregory Lake) – breathe calm and serenity!",
            "Diyaluma Falls – hear nature’s pure energy cascading down!",
            "Adam’s Peak – witness a sunrise that renews your spirit!",
            "Ritigala Forest Monastery – find solace in ancient serenity!",
            "Koggala Lake (canoeing) – glide into peaceful reflections!",
            "Sinharaja Forest Reserve (peaceful trekking) – immerse in untouched nature!",
        ],
    },
    "Neutral": {
        "question": "Feeling neutral? Imagine discovering Colombo’s vibrant streets or Galle’s charming forts 🌼",
        "primary": "Colombo (city exploration & food) – wander vibrant streets and find a new favorite spot.",
        "alternatives": [
            "Bentota (beach walk & water sports) – feel the waves energize you!",
            "Dambulla (cave temples) – step into mystical wonder!",
            "Sigiriya (rock fortress) – ascend and marvel at stunning views!",
            "Nuwara Eliya (tea estate & Gregory Lake) – rejuvenate in serene hills!",
            "Horton Plains (treks) – let open vistas refresh your mind!",
            "Ella (scenic walks & waterfalls) – wander through magical landscapes!",
            "Madu River (boat ride) – glide through calm waters and feel tranquility!",
        ],
    },
}

# If the user's dataset includes "contempt", we map it to the Neutral tour flow.
TOUR_ALIASES: Dict[str, str] = {
    "Contempt": "Neutral",
    "contempt": "Neutral",
}

LABEL_CANONICAL: Dict[str, str] = {
    "angry": "Angry",
    "disgust": "Disgust",
    "fear": "Fear",
    "happy": "Happy",
    "sad": "Sad",
    "surprise": "Surprise",
    "neutral": "Neutral",
    "contempt": "Neutral",
}


def canonicalize_label(label: str) -> str:
    if label in LABEL_CANONICAL:
        return LABEL_CANONICAL[label]
    low = label.strip().lower()
    return LABEL_CANONICAL.get(low, label[:1].upper() + label[1:])


# =========================
# Dataset loading
# =========================


def _parse_fer2013_pixels(pixels_str: str) -> np.ndarray:
    # FER2013 format: space-separated ints length 2304 (48*48)
    arr = np.fromstring(pixels_str, dtype=np.uint8, sep=" ")
    if arr.size != 48 * 48:
        raise ValueError(f"Invalid FER2013 pixels length: expected {48*48}, got {arr.size}")
    return arr.reshape((48, 48))


def load_fer2013_csv(csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Loads FER2013 CSV into X, y.
    X: (N, 48, 48, 1) float32 in [0,1]
    y: (N,) int labels in [0..6] for EMOTIONS_FER2013
    """
    import csv

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # columns: emotion,pixels,Usage
            y = int(row["emotion"])
            img = _parse_fer2013_pixels(row["pixels"])
            X_list.append(img)
            y_list.append(y)

    X = np.stack(X_list).astype("float32") / 255.0
    X = np.expand_dims(X, axis=-1)
    y = np.asarray(y_list, dtype=np.int64)
    return X, y


def _list_class_folders(base_dir: str) -> Tuple[List[str], List[str]]:
    class_folders = [
        d
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith(".")
    ]
    class_folders = sorted(class_folders, key=lambda s: s.lower())
    class_names = [c.strip().replace("_", " ").title() for c in class_folders]
    return class_folders, class_names


def load_image_folder_dataset(dataset_dir: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Loads a folder-structured dataset from `dataset_dir`.

    This project uses the folders you already have:
      dataset/anger/*.png
      dataset/contempt/*.png
      dataset/disgust/*.png
      dataset/fear/*.png
      dataset/happy/*.png
      dataset/sadness/*.png
      dataset/surprise/*.png

    Returns X, y, class_names (exactly as present in the folders, Title-cased).
    """
    # Determine classes directly from folder names (no hidden mapping)
    class_folders, class_names = _list_class_folders(dataset_dir)
    class_to_idx = {name: i for i, name in enumerate(class_names)}

    per_class: Dict[int, List[np.ndarray]] = {i: [] for i in range(len(class_names))}

    for folder, cls_name in zip(class_folders, class_names):
        p = os.path.join(dataset_dir, folder)
        for fn in os.listdir(p):
            if not fn.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            img_path = os.path.join(p, fn)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            img = cv2.resize(img, (48, 48), interpolation=cv2.INTER_AREA)
            per_class[class_to_idx[cls_name]].append(img)

    total_found = sum(len(v) for v in per_class.values())
    if total_found == 0:
        raise FileNotFoundError(
            "No images found in dataset folders. Expected e.g. dataset/happy/*.png etc."
        )

    # Balance classes by downsampling to the smallest non-zero class count.
    # This is critical for small folder datasets; otherwise the model collapses to the biggest class.
    non_zero_counts = [len(v) for v in per_class.values() if len(v) > 0]
    target = min(non_zero_counts) if non_zero_counts else 0
    rng = np.random.default_rng(42)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    for cls_idx, imgs in per_class.items():
        if not imgs:
            continue
        if target > 0 and len(imgs) > target:
            sel = rng.choice(len(imgs), size=target, replace=False)
            for j in sel:
                X_list.append(imgs[int(j)])
                y_list.append(cls_idx)
        else:
            for im in imgs:
                X_list.append(im)
                y_list.append(cls_idx)

    X = np.stack(X_list).astype("float32") / 255.0
    X = np.expand_dims(X, axis=-1)
    y = np.asarray(y_list, dtype=np.int64)
    return X, y, class_names


def load_train_test_folder_dataset(dataset_dir: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Loads FER-style folder dataset:
      dataset/train/<class>/*.jpg|png
      dataset/test/<class>/*.jpg|png
    Returns X_train, y_train, X_val, y_val, class_names
    """
    train_dir = os.path.join(dataset_dir, "train")
    test_dir = os.path.join(dataset_dir, "test")
    if not (os.path.isdir(train_dir) and os.path.isdir(test_dir)):
        raise FileNotFoundError("Expected `dataset/train` and `dataset/test` folders.")

    class_folders, class_names = _list_class_folders(train_dir)
    class_to_idx = {name: i for i, name in enumerate(class_names)}

    def load_split(split_dir: str) -> Tuple[np.ndarray, np.ndarray]:
        X_list: List[np.ndarray] = []
        y_list: List[int] = []
        for folder, cls_name in zip(class_folders, class_names):
            p = os.path.join(split_dir, folder)
            if not os.path.isdir(p):
                continue
            for fn in os.listdir(p):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue
                img_path = os.path.join(p, fn)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                img = cv2.resize(img, (48, 48), interpolation=cv2.INTER_AREA)
                X_list.append(img)
                y_list.append(class_to_idx[cls_name])

        if not X_list:
            raise FileNotFoundError(f"No images found under {split_dir}")

        X = np.stack(X_list).astype("float32") / 255.0
        X = np.expand_dims(X, axis=-1)
        y = np.asarray(y_list, dtype=np.int64)
        return X, y

    X_train, y_train = load_split(train_dir)
    X_val, y_val = load_split(test_dir)
    return X_train, y_train, X_val, y_val, class_names


def load_train_test_folder_dataset_tf(
    dataset_dir: str,
    batch_size: int,
    seed: int = 42,
) -> Tuple[tf.data.Dataset, tf.data.Dataset, List[str], Dict[int, int]]:
    """
    Loads FER image-folder dataset using a streaming tf.data pipeline.
    Expects:
      dataset/train/<class>/*
      dataset/test/<class>/*

    Returns: train_ds, val_ds, class_names, train_class_counts
    """
    train_dir = os.path.join(dataset_dir, "train")
    test_dir = os.path.join(dataset_dir, "test")
    if not (os.path.isdir(train_dir) and os.path.isdir(test_dir)):
        raise FileNotFoundError("Expected `dataset/train` and `dataset/test` folders.")

    class_folders, _class_names = _list_class_folders(train_dir)

    # Count training images per class for class_weight (fast)
    train_class_counts: Dict[int, int] = {}
    for i, folder in enumerate(class_folders):
        p = os.path.join(train_dir, folder)
        if not os.path.isdir(p):
            train_class_counts[i] = 0
            continue
        n = 0
        for fn in os.listdir(p):
            if fn.lower().endswith((".png", ".jpg", ".jpeg")):
                n += 1
        train_class_counts[i] = n

    print(f"[tfdata] Loading train dataset from: {train_dir}")
    train_ds = keras.utils.image_dataset_from_directory(
        train_dir,
        labels="inferred",
        label_mode="int",
        color_mode="grayscale",
        batch_size=batch_size,
        image_size=(48, 48),
        shuffle=True,
        seed=seed,
    )

    print(f"[tfdata] Loading test/val dataset from: {test_dir}")
    val_ds = keras.utils.image_dataset_from_directory(
        test_dir,
        labels="inferred",
        label_mode="int",
        color_mode="grayscale",
        batch_size=batch_size,
        image_size=(48, 48),
        shuffle=False,
    )

    # image_dataset_from_directory infers class order from folder names;
    # since your train/test folder structure matches, this order will be consistent.
    class_names = list(getattr(train_ds, "class_names", _class_names))
    print(f"[tfdata] Class order: {class_names}")

    def norm(x, y):
        x = tf.cast(x, tf.float32) / 255.0
        return x, y

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.map(norm, num_parallel_calls=autotune).prefetch(autotune)
    val_ds = val_ds.map(norm, num_parallel_calls=autotune).prefetch(autotune)
    return train_ds, val_ds, class_names, train_class_counts


# =========================
# Model
# =========================


def build_emotion_cnn(num_classes: int = 7) -> keras.Model:
    inputs = keras.Input(shape=(48, 48, 1))
    # Light augmentation helps a lot for small / imbalanced datasets
    aug = keras.Sequential(
        [
            keras.layers.RandomFlip("horizontal"),
            keras.layers.RandomRotation(0.06),
            keras.layers.RandomZoom(0.10),
            keras.layers.RandomTranslation(0.05, 0.05),
        ],
        name="augment",
    )
    x = aug(inputs)

    x = keras.layers.Conv2D(32, (3, 3), padding="same")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.MaxPooling2D((2, 2))(x)
    x = keras.layers.Dropout(0.25)(x)

    x = keras.layers.Conv2D(64, (3, 3), padding="same")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.MaxPooling2D((2, 2))(x)
    x = keras.layers.Dropout(0.25)(x)

    x = keras.layers.Conv2D(128, (3, 3), padding="same")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.MaxPooling2D((2, 2))(x)
    x = keras.layers.Dropout(0.25)(x)

    x = keras.layers.Flatten()(x)
    x = keras.layers.Dense(256)(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.Dropout(0.5)(x)

    outputs = keras.layers.Dense(num_classes, activation="softmax")(x)
    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def build_transfer_model(num_classes: int, imagenet: bool = True) -> keras.Model:
    """
    Transfer learning model that generalizes much better on small folder datasets.
    Input stays (48,48,1) to match FER-style preprocessing, then we:
    - resize to 96x96
    - convert grayscale -> RGB
    - use MobileNetV2 backbone (ImageNet weights)
    """
    inputs = keras.Input(shape=(48, 48, 1))
    x = keras.layers.Resizing(96, 96, interpolation="bilinear")(inputs)
    # Avoid Lambda deserialization/runtime issues by using pure Keras layers.
    # This replicates the single grayscale channel into RGB channels.
    x = keras.layers.Concatenate(axis=-1, name="gray_to_rgb")([x, x, x])

    # modest augmentation
    x = keras.layers.RandomFlip("horizontal")(x)
    x = keras.layers.RandomRotation(0.06)(x)
    x = keras.layers.RandomZoom(0.10)(x)
    x = keras.layers.RandomTranslation(0.05, 0.05)(x)

    base = keras.applications.MobileNetV2(
        include_top=False,
        weights="imagenet" if imagenet else None,
        input_shape=(96, 96, 3),
    )
    base.trainable = False
    x = keras.applications.mobilenet_v2.preprocess_input(x * 255.0)
    x = base(x, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.35)(x)
    outputs = keras.layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=3e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_or_load_model(
    dataset_dir: str,
    model_path: str,
    labels_path: str,
    prefer_csv: bool = True,
    epochs: int = 8,
    batch_size: int = 64,
    force_retrain: bool = False,
    allow_folder_fallback: bool = True,
    use_imagenet_weights: bool = True,
) -> Tuple[keras.Model, List[str]]:
    def _bind_tf_in_lambda_layers(layer_or_model) -> None:
        """Inject `tf` into deserialized Lambda function globals recursively."""
        if isinstance(layer_or_model, keras.layers.Lambda):
            fn = getattr(layer_or_model, "function", None)
            if callable(fn):
                fn_globals = getattr(fn, "__globals__", None)
                if isinstance(fn_globals, dict):
                    fn_globals.setdefault("tf", tf)
        for child in getattr(layer_or_model, "layers", []):
            _bind_tf_in_lambda_layers(child)

    if (not force_retrain) and os.path.isfile(model_path) and os.path.isfile(labels_path):
        # Some Keras versions refuse to deserialize `Lambda` layers unless
        # unsafe deserialization is explicitly enabled.
        try:
            if hasattr(keras.config, "enable_unsafe_deserialization"):
                keras.config.enable_unsafe_deserialization()
        except Exception:
            pass

        # Keras 3 blocks Lambda deserialization by default (security). This
        # project uses a Lambda layer in the transfer-learning model.
        # Also, older saved models may be missing `output_shape` for the
        # Lambda layer; if loading fails, we fall back to retraining.
        # Older saved models can contain Lambda(lambda t: tf.image.grayscale_to_rgb(t));
        # when that runs at predict(), tf is not in the deserialized lambda's scope.
        # Replace Lambda with a class whose from_config returns a Lambda with tf in scope.

        class _LambdaGrayscaleToRgbReplacement(keras.layers.Layer):
            """Used only for deserializing saved Lambda(tf.image.grayscale_to_rgb)."""

            @classmethod
            def from_config(cls, config):
                return keras.layers.Lambda(
                    lambda t: tf.image.grayscale_to_rgb(t),
                    name=config.get("name"),
                )

        custom_objects = {"Lambda": _LambdaGrayscaleToRgbReplacement}
        try:
            try:
                model = keras.models.load_model(
                    model_path, compile=False, safe_mode=False, custom_objects=custom_objects
                )
            except TypeError:
                # Older TF/Keras versions may not support safe_mode=...
                model = keras.models.load_model(
                    model_path, compile=False, custom_objects=custom_objects
                )
            _bind_tf_in_lambda_layers(model)
            with open(labels_path, "r", encoding="utf-8") as f:
                class_names = json.load(f)
            # Sanity-check the loaded model with a tiny forward pass. Some
            # deserialized Lambda models load, but fail only during predict().
            _ = model.predict(np.zeros((1, 48, 48, 1), dtype="float32"), verbose=0)
            return model, class_names
        except Exception as load_e:
            print(f"[model] load_model failed; retraining instead. Reason: {type(load_e).__name__}: {load_e}")
            # Fall through to training path.

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Use FER2013 CSV if present; otherwise use folder datasets (supports train/test structure).
    fer_csv = os.path.join(dataset_dir, "fer2013.csv")
    using_fer_csv = prefer_csv and os.path.isfile(fer_csv)
    using_train_test = os.path.isdir(os.path.join(dataset_dir, "train")) and os.path.isdir(
        os.path.join(dataset_dir, "test")
    )

    if using_fer_csv:
        X, y = load_fer2013_csv(fer_csv)
        class_names = EMOTIONS_FER2013

        # Useful debug info: class distribution
        dist = np.bincount(y, minlength=len(class_names))
        dist_str = ", ".join([f"{class_names[i]}={int(dist[i])}" for i in range(len(class_names))])
        print(f"[dataset] {dist_str}")

        # Simple train/val split for CSV
        rng = np.random.default_rng(42)
        idx = np.arange(len(X))
        rng.shuffle(idx)
        X, y = X[idx], y[idx]
        split = int(0.85 * len(X))
        X_train, y_train = X[:split], y[:split]
        X_val, y_val = X[split:], y[split:]
    else:
        if not allow_folder_fallback:
            raise FileNotFoundError(f"Missing `dataset/fer2013.csv` at: {fer_csv}")
        if using_train_test:
            # Streaming pipeline (fast startup + no giant RAM spike)
            train_ds, val_ds, class_names, train_class_counts = load_train_test_folder_dataset_tf(
                dataset_dir=dataset_dir, batch_size=batch_size
            )
        else:
            X, y, class_names = load_image_folder_dataset(dataset_dir)
            dist = np.bincount(y, minlength=len(class_names))
            dist_str = ", ".join([f"{class_names[i]}={int(dist[i])}" for i in range(len(class_names))])
            print(f"[dataset] {dist_str}")

            rng = np.random.default_rng(42)
            idx = np.arange(len(X))
            rng.shuffle(idx)
            X, y = X[idx], y[idx]
            split = int(0.85 * len(X))
            X_train, y_train = X[:split], y[:split]
            X_val, y_val = X[split:], y[split:]

    # Class weights to counter imbalance
    if using_train_test and (not using_fer_csv):
        counts = np.asarray([train_class_counts.get(i, 0) for i in range(len(class_names))], dtype="float32")
        counts[counts == 0] = 1.0
        total = float(np.sum(counts))
        class_weight = {i: total / (len(class_names) * float(counts[i])) for i in range(len(class_names))}
        train_counts_str = ", ".join([f"{class_names[i]}={int(counts[i])}" for i in range(len(class_names))])
        print(f"[train] {train_counts_str}")
    else:
        dist_train = np.bincount(y_train, minlength=len(class_names))
        dist_train_str = ", ".join([f"{class_names[i]}={int(dist_train[i])}" for i in range(len(class_names))])
        print(f"[train] {dist_train_str}")
        counts = np.bincount(y_train, minlength=len(class_names)).astype("float32")
        counts[counts == 0] = 1.0
        total = float(np.sum(counts))
        class_weight = {i: total / (len(class_names) * float(counts[i])) for i in range(len(class_names))}

    # Use classic CNN for FER2013; transfer learning for folder datasets (generalizes better)
    model = (
        build_emotion_cnn(num_classes=len(class_names))
        if using_fer_csv
        else build_transfer_model(num_classes=len(class_names), imagenet=use_imagenet_weights)
    )
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=2, factor=0.5, min_lr=1e-5),
    ]

    if using_train_test and (not using_fer_csv):
        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=epochs,
            verbose=1,
            class_weight=class_weight,
        )
    else:
        model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            class_weight=class_weight,
        )

    # Optional fine-tune last layers of backbone a bit (folder datasets benefit)
    if (not using_fer_csv) and any(isinstance(l, keras.Model) and l.name.startswith("mobilenetv2") for l in model.layers):
        try:
            # Unfreeze last ~30 layers of backbone
            backbone = None
            for l in model.layers:
                if isinstance(l, keras.Model) and l.name.startswith("mobilenetv2"):
                    backbone = l
                    break
            if backbone is not None:
                backbone.trainable = True
                for layer in backbone.layers[:-30]:
                    layer.trainable = False
                model.compile(
                    optimizer=keras.optimizers.Adam(learning_rate=1e-4),
                    loss="sparse_categorical_crossentropy",
                    metrics=["accuracy"],
                )
                if using_train_test and (not using_fer_csv):
                    model.fit(
                        train_ds,
                        validation_data=val_ds,
                        epochs=max(3, epochs // 3),
                        verbose=1,
                        class_weight=class_weight,
                    )
                else:
                    model.fit(
                        X_train,
                        y_train,
                        validation_data=(X_val, y_val),
                        epochs=max(3, epochs // 3),
                        batch_size=batch_size,
                        verbose=1,
                        class_weight=class_weight,
                    )
        except Exception:
            pass

    model.save(model_path)
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)

    return model, class_names


# =========================
# Webcam + face + emotion
# =========================


def detect_faces(gray_frame: np.ndarray, scaleFactor: float = 1.2, minNeighbors: int = 5):
    face_cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(face_cascade_path)
    faces = cascade.detectMultiScale(gray_frame, scaleFactor=scaleFactor, minNeighbors=minNeighbors)
    return faces


def preprocess_face(gray_frame: np.ndarray, face_box: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = face_box
    # Add padding so we keep cheeks/forehead (improves emotion cues)
    pad = int(0.18 * max(w, h))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(gray_frame.shape[1], x + w + pad)
    y1 = min(gray_frame.shape[0], y + h + pad)
    roi = gray_frame[y0:y1, x0:x1]

    # Contrast normalization helps under poor lighting
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        roi = clahe.apply(roi)
    except Exception:
        pass
    roi = cv2.resize(roi, (48, 48), interpolation=cv2.INTER_AREA)
    roi = roi.astype("float32") / 255.0
    roi = np.expand_dims(roi, axis=-1)  # (48,48,1)
    roi = np.expand_dims(roi, axis=0)  # (1,48,48,1)
    return roi


@dataclass
class EmotionResult:
    label: str
    confidence: float


def predict_emotion(model: keras.Model, class_names: List[str], face_tensor: np.ndarray) -> EmotionResult:
    probs = model.predict(face_tensor, verbose=0)[0]
    idx = int(np.argmax(probs))
    label = class_names[idx]
    conf = float(probs[idx])
    return EmotionResult(label=label, confidence=conf)


# =========================
# GUI App
# =========================


class MoodTourApp:
    def __init__(
        self,
        root: tk.Tk,
        project_root: str,
        force_retrain: bool = False,
        allow_folder_fallback: bool = False,
        use_imagenet_weights: bool = True,
    ):
        self.root = root
        self.project_root = project_root
        self.dataset_dir = os.path.join(project_root, "dataset")
        self.model_path = os.path.join(project_root, "app", "models", "fer_emotion_cnn.keras")
        self.labels_path = os.path.join(project_root, "app", "models", "labels.json")
        self.force_retrain = force_retrain
        self.allow_folder_fallback = allow_folder_fallback
        self.use_imagenet_weights = use_imagenet_weights

        self.model: Optional[keras.Model] = None
        self.class_names: Optional[List[str]] = None

        self.cap = None
        self.running = False
        self.latest_frame = None
        self.latest_gray = None
        self.latest_faces = []

        self.current_mood: Optional[str] = None
        self.current_conf: Optional[float] = None
        self.awaiting_yes_no = False
        self.latest_itinerary: Optional[ItineraryResult] = None
        self.suggestions_inner: Optional[ttk.Frame] = None
        self.dataset_inner: Optional[ttk.Frame] = None
        self._dataset_canvas: Optional[tk.Canvas] = None
        self._dataset_win: Optional[int] = None
        self._selected_names: Set[str] = set()
        self._selection_order: List[str] = []
        self._buttons_for_attr: Dict[str, List[tk.Button]] = {}
        self._suggestion_buttons: Dict[str, tk.Button] = {}
        self._suggestion_order: List[str] = []
        self._dataset_button_refs: Dict[str, tk.Button] = {}
        self._itinerary_popup: Optional[tk.Toplevel] = None
        self.itinerary_output: Optional[tk.Text] = None

        self._build_ui()

    @staticmethod
    def _research_placeholder_text() -> str:
        return (
            "Your itinerary will appear here — nothing is generated until you click a button.\n\n"
            "Steps:\n"
            "  1. Set Budget and Travel days above.\n"
            "  2. Use Detect Mood Now (optional for chat suggestions).\n"
            "  3. Click the green 'Generate itinerary (emotion + budget + days)' button, OR\n"
            "     scroll to **Browse all places**, click rows (they turn green), then click "
            "'Generate from selected places'.\n\n"
            "This text is shown in the separate Itinerary window (not on the main screen)."
        )

    def _build_ui(self):
        self.root.title("Sri Lanka Mood-Based Travel Bot (FER2013 Emotions)")
        self.root.geometry("980x820")
        try:
            self.root.minsize(880, 640)
        except Exception:
            pass

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        # Left: Video
        left = ttk.Frame(outer)
        left.pack(side="left", fill="both", expand=False)

        self.video_label = ttk.Label(left, text="Webcam preview will appear here")
        self.video_label.pack(fill="both", expand=True)

        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=(8, 0))

        self.btn_start = ttk.Button(controls, text="Start Webcam", command=self.start_webcam)
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ttk.Button(controls, text="Stop Webcam", command=self.stop_webcam, state="disabled")
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_detect = ttk.Button(controls, text="Detect Mood Now", command=self.detect_now, state="disabled")
        self.btn_detect.pack(side="left")

        # Right: main workflow only; full itinerary text lives in a separate Toplevel window.
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        header = ttk.Label(
            right,
            text="Sri Lanka Mood-Based Travel Bot",
            font=("Segoe UI", 15, "bold"),
        )
        header.pack(anchor="w", pady=(0, 4))

        self.status_var = tk.StringVar(value="Model not loaded yet.")
        status = ttk.Label(right, textvariable=self.status_var, font=("Segoe UI", 9))
        status.pack(anchor="w", pady=(0, 6))

        trip_card = ttk.LabelFrame(right, text="Plan your trip — generate only when you click a button", padding=10)
        trip_card.pack(fill="x", pady=(0, 8))

        profile = ttk.Frame(trip_card)
        profile.pack(fill="x", pady=(0, 10))
        ttk.Label(profile, text="Budget (USD, total):", font=("Segoe UI", 9)).pack(side="left")
        self.budget_var = tk.StringVar(value="180")
        self.entry_budget = ttk.Entry(profile, width=12, textvariable=self.budget_var, font=("Segoe UI", 10))
        self.entry_budget.pack(side="left", padx=(6, 20))
        ttk.Label(profile, text="Travel days:", font=("Segoe UI", 9)).pack(side="left")
        self.days_var = tk.StringVar(value="2")
        self.spin_days = ttk.Spinbox(
            profile, from_=1, to=MAX_TRIP_DAYS, width=5, textvariable=self.days_var, font=("Segoe UI", 10)
        )
        self.spin_days.pack(side="left", padx=(6, 0))

        trip_btns = ttk.Frame(trip_card)
        trip_btns.pack(fill="x", pady=(0, 8))
        self.btn_mood_itinerary = tk.Button(
            trip_btns,
            text="Generate itinerary (emotion + budget + days)",
            font=("Segoe UI", 10, "bold"),
            bg="#1b5e20",
            fg="#ffffff",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=16,
            pady=10,
            command=self.on_generate_mood_itinerary,
        )
        self.btn_mood_itinerary.pack(side="left", padx=(0, 10))
        self.btn_generate_itinerary = tk.Button(
            trip_btns,
            text="Generate from selected places (green)",
            font=("Segoe UI", 10, "bold"),
            bg="#37474f",
            fg="#ffffff",
            activebackground="#455a64",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=16,
            pady=10,
            command=self.on_generate_itinerary_from_selections,
        )
        self.btn_generate_itinerary.pack(side="left")

        ttk.Label(
            trip_card,
            text="Mood is detected from the webcam; the itinerary is not created until you press the left button. "
            "Use the right button after toggling destinations in the list below.",
            font=("Segoe UI", 9),
            foreground="#444444",
            wraplength=820,
        ).pack(anchor="w")

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=(4, 8))

        chat_lf = ttk.LabelFrame(right, text="Chat", padding=4)
        chat_lf.pack(fill="both", expand=True, pady=(0, 6))
        self.chat = tk.Text(chat_lf, height=10, wrap="word", font=("Segoe UI", 10), relief=tk.FLAT, padx=6, pady=6)
        self.chat.pack(fill="both", expand=True)
        self.chat.configure(state="disabled")

        self.suggestions_frame = ttk.LabelFrame(
            right,
            text="Destinations — green = selected (browse list is always available)",
            padding=6,
        )
        self.suggestions_frame.pack(fill="x", pady=(6, 0))

        ttk.Label(
            self.suggestions_frame,
            text="From chat (after Yes / Maybe / More suggestions):",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        self.suggestions_inner = ttk.Frame(self.suggestions_frame)
        self.suggestions_inner.pack(fill="x")

        self.picks_bar = ttk.Frame(self.suggestions_frame)
        self.picks_bar.pack(fill="x", pady=(6, 0))
        self.selected_picks_var = tk.StringVar(value="0 places selected.")
        ttk.Label(self.picks_bar, textvariable=self.selected_picks_var, font=("Segoe UI", 9)).pack(anchor="w")

        browse_wrap = ttk.LabelFrame(
            self.suggestions_frame,
            text="Browse all places — scroll and click to select (no chat required)",
            padding=4,
        )
        browse_wrap.pack(fill="both", expand=False, pady=(8, 0))
        self._dataset_canvas = tk.Canvas(browse_wrap, height=220, highlightthickness=0)
        vsb = ttk.Scrollbar(browse_wrap, orient="vertical", command=self._dataset_canvas.yview)
        self.dataset_inner = ttk.Frame(self._dataset_canvas)
        self.dataset_inner.bind(
            "<Configure>",
            lambda e: self._dataset_canvas.configure(scrollregion=self._dataset_canvas.bbox("all")),
        )
        self._dataset_win = self._dataset_canvas.create_window((0, 0), window=self.dataset_inner, anchor="nw")

        def _dataset_canvas_configure(ev):
            try:
                self._dataset_canvas.itemconfigure(self._dataset_win, width=ev.width)
            except Exception:
                pass

        self._dataset_canvas.bind("<Configure>", _dataset_canvas_configure)
        self._dataset_canvas.configure(yscrollcommand=vsb.set)

        def _wheel_dataset(evt):
            if self._dataset_canvas is None:
                return
            delta = int(-1 * (evt.delta / 120)) if getattr(evt, "delta", 0) else 0
            if delta:
                self._dataset_canvas.yview_scroll(delta, "units")

        self._dataset_canvas.bind("<Enter>", lambda e: self._dataset_canvas.bind_all("<MouseWheel>", _wheel_dataset))
        self._dataset_canvas.bind("<Leave>", lambda e: self._dataset_canvas.unbind_all("<MouseWheel>"))

        vsb.pack(side="right", fill="y")
        self._dataset_canvas.pack(side="left", fill="both", expand=True)

        self._build_dataset_pick_buttons()

        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=(8, 0))

        self.btn_yes = ttk.Button(actions, text="Yes, let's explore!", command=lambda: self.on_yes_no("yes"), state="disabled")
        self.btn_yes.pack(side="left", padx=(0, 8))

        self.btn_maybe = ttk.Button(actions, text="Maybe something else", command=lambda: self.on_yes_no("maybe"), state="disabled")
        self.btn_maybe.pack(side="left", padx=(0, 8))

        self.btn_more = ttk.Button(actions, text="More tour suggestions", command=self.more_suggestions, state="disabled")
        self.btn_more.pack(side="left")

        footer = ttk.Frame(right)
        footer.pack(fill="x", pady=(10, 0))

        self.train_note = ttk.Label(
            footer,
            text=(
                "Tip: If `dataset/fer2013.csv` exists, it will be used. Otherwise it trains from dataset image folders."
            ),
        )
        self.train_note.pack(anchor="w")

        itin_hint = ttk.Frame(right)
        itin_hint.pack(fill="x", pady=(8, 0))
        ttk.Label(
            itin_hint,
            text="Full itinerary (day plan, costs, scores) opens in a separate window when you generate.",
            font=("Segoe UI", 9),
            foreground="#444444",
        ).pack(anchor="w")
        ttk.Button(itin_hint, text="Open itinerary window", command=self._show_itinerary_window).pack(anchor="w", pady=(4, 0))

        self._append_bot(
            "Hi! Start the webcam, then **Detect Mood Now**. "
            "Your mood is used for suggestions only — open **Plan your trip** and click "
            "**Generate itinerary (emotion + budget + days)** when you want a full plan. "
            "The detailed itinerary opens in a **separate window**."
        )

        # Load model in background so UI doesn't freeze
        threading.Thread(target=self._load_model_background, daemon=True).start()

    def _append(self, who: str, msg: str):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{who}: {msg}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _append_bot(self, msg: str):
        self._append("Bot", msg)

    def _append_user(self, msg: str):
        self._append("You", msg)

    def _add_pick_button(self, key: str, btn: tk.Button) -> None:
        self._buttons_for_attr.setdefault(key, []).append(btn)

    def _strip_pick_button(self, key: str, btn: tk.Button) -> None:
        lst = self._buttons_for_attr.get(key)
        if not lst:
            return
        lst = [b for b in lst if b is not btn]
        if lst:
            self._buttons_for_attr[key] = lst
        else:
            del self._buttons_for_attr[key]

    def _refresh_pick_highlights(self) -> None:
        for key, buttons in list(self._buttons_for_attr.items()):
            sel = key in self._selected_names
            for b in buttons:
                try:
                    b.configure(bg="#c8e6c9" if sel else "SystemButtonFace", relief=tk.RIDGE if sel else tk.GROOVE)
                except Exception:
                    pass

    def _toggle_pick(self, key: str, btn: tk.Button) -> None:
        if key in self._selected_names:
            self._selected_names.discard(key)
            try:
                self._selection_order.remove(key)
            except ValueError:
                pass
        else:
            self._selected_names.add(key)
            self._selection_order.append(key)
        self._refresh_pick_highlights()
        self._update_picks_status()

    def _clear_chat_suggestion_rows(self) -> None:
        if self.suggestions_inner is None:
            return
        for label, btn in list(self._suggestion_buttons.items()):
            att = resolve_chat_pick_label(label)
            key = att.name if att else label
            self._strip_pick_button(key, btn)
        for w in self.suggestions_inner.winfo_children():
            w.destroy()
        self._suggestion_buttons.clear()
        self._suggestion_order.clear()
        self._refresh_pick_highlights()
        self._update_picks_status()

    def _ordered_selection_keys(self) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for k in self._selection_order:
            if k in self._selected_names and k not in seen:
                seen.add(k)
                out.append(k)
        for k in self._selected_names:
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def _update_picks_status(self):
        n = len(self._selected_names)
        self.selected_picks_var.set(
            f"{n} place(s) selected — use the gray 'Generate from selected places' button under Plan your trip."
        )

    def _build_dataset_pick_buttons(self) -> None:
        if self.dataset_inner is None:
            return
        for _key, btn in list(self._dataset_button_refs.items()):
            self._strip_pick_button(_key, btn)
            try:
                btn.destroy()
            except Exception:
                pass
        self._dataset_button_refs.clear()
        for a in sorted(SRI_LANKA_ATTRACTIONS, key=lambda x: x.name.lower()):
            key = a.name
            line = f"{a.name}  ({a.category})  ·  ~${a.estimated_cost}  ·  safety {a.safety_score}/10"
            btn = tk.Button(
                self.dataset_inner,
                text=line,
                anchor="w",
                justify="left",
                wraplength=720,
                relief=tk.GROOVE,
                cursor="hand2",
                bg="SystemButtonFace",
                font=("Segoe UI", 9),
            )
            btn.configure(command=lambda k=key, b=btn: self._toggle_pick(k, b))
            btn.pack(fill="x", pady=2, padx=2)
            self._dataset_button_refs[key] = btn
            self._add_pick_button(key, btn)
        self._refresh_pick_highlights()

    def _populate_suggestion_buttons(self, items: List[str]):
        self._clear_chat_suggestion_rows()
        if not items or self.suggestions_inner is None:
            return
        for i, label in enumerate(items, start=1):
            line = f"{i}. {label}"
            att = resolve_chat_pick_label(label)
            key = att.name if att else label
            btn = tk.Button(
                self.suggestions_inner,
                text=line,
                anchor="w",
                justify="left",
                wraplength=640,
                relief=tk.GROOVE,
                cursor="hand2",
                bg="SystemButtonFace",
            )
            btn.configure(command=lambda k=key, b=btn: self._toggle_pick(k, b))
            btn.pack(fill="x", pady=2, padx=0)
            self._suggestion_buttons[label] = btn
            self._add_pick_button(key, btn)
        self._suggestion_order = list(items)
        self._refresh_pick_highlights()

    def on_generate_itinerary_from_selections(self):
        if not self._selected_names:
            messagebox.showinfo(
                "No places selected",
                "Scroll down to 'Browse all places' in the Destinations section and click rows "
                "(they turn green), or use chat suggestions after Yes / Maybe / More.\n\n"
                "Then click 'Generate from selected places' again.",
            )
            return
        budget, days = self._read_budget_days()
        mood = self.current_mood or "Neutral"
        ordered = self._ordered_selection_keys()
        resolved, unresolved = resolve_selection_keys(ordered)
        if unresolved:
            self._append_bot(
                "Note: some lines could not be matched to the research dataset and were skipped:\n"
                + "\n".join(f"- {u}" for u in unresolved[:6])
                + ("\n…" if len(unresolved) > 6 else "")
            )
        if not resolved:
            messagebox.showwarning(
                "Could not map selections",
                "None of the selected lines matched known attractions. Try different suggestions or shorten the line.",
            )
            return

        self._append_user(
            "Generate itinerary for: "
            + "; ".join(f"{a.name}" for a in resolved)
            + f" (budget ${budget}, {days} day(s), mood {mood})."
        )
        result = generate_itinerary_from_user_picks(
            emotion=mood,
            user_budget=budget,
            travel_days=days,
            picked_attractions=resolved,
            max_locations_per_day=4,
        )
        self.latest_itinerary = result
        self._append_bot(
            f"Built a pick-only itinerary (your selections only): score {result.itinerary_score:.3f}, "
            f"estimated total ${result.total_estimated_cost}. Check the Itinerary window (just opened or raised)."
        )
        self._render_itinerary_output(result, subtitle="Mode: selected places only (extras = more to do same place)")

    def on_generate_mood_itinerary(self):
        mood = self.current_mood
        if mood is None:
            if not messagebox.askyesno(
                "No mood detected yet",
                "You have not run Detect Mood Now.\n\n"
                "Choose Yes to build an itinerary using Neutral as the emotion label, "
                "or No to cancel and use the webcam first.",
            ):
                return
            mood = "Neutral"
        self._append_user(f"Generate mood-based itinerary (mood={mood}, budget/days from Plan your trip).")
        self._generate_itinerary_from_mood(mood)

    def _read_budget_days(self) -> Tuple[int, int]:
        try:
            budget = int(float(self.budget_var.get().strip()))
        except Exception:
            budget = 180
        try:
            days = int(float(self.days_var.get().strip()))
        except Exception:
            days = 2
        budget = max(50, budget)
        days = max(1, min(MAX_TRIP_DAYS, days))
        return budget, days

    def _ensure_itinerary_popup(self) -> tk.Text:
        if (
            self._itinerary_popup is not None
            and self._itinerary_popup.winfo_exists()
            and self.itinerary_output is not None
            and self.itinerary_output.winfo_exists()
        ):
            return self.itinerary_output

        win = tk.Toplevel(self.root)
        win.title("Itinerary — Sri Lanka Mood-Based Travel Bot")
        win.geometry("780x720")
        try:
            win.minsize(520, 360)
        except Exception:
            pass

        outer_f = ttk.Frame(win, padding=10)
        outer_f.pack(fill="both", expand=True)
        ttk.Label(
            outer_f,
            text="Emotion-aware safe itinerary (research prototype output)",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        lf = ttk.LabelFrame(outer_f, text="Itinerary details", padding=6)
        lf.pack(fill="both", expand=True)
        sc = ttk.Scrollbar(lf, orient="vertical")
        txt = tk.Text(
            lf,
            wrap="word",
            font=("Segoe UI", 10),
            yscrollcommand=sc.set,
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        sc.config(command=txt.yview)
        sc.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.configure(state="disabled")

        def _on_close():
            win.withdraw()

        win.protocol("WM_DELETE_WINDOW", _on_close)
        self._itinerary_popup = win
        self.itinerary_output = txt
        return txt

    def _show_itinerary_window(self) -> None:
        txt = self._ensure_itinerary_popup()
        if not txt.get("1.0", "end-1c").strip():
            self._set_research_output(self._research_placeholder_text())
        if self._itinerary_popup is not None:
            self._itinerary_popup.deiconify()
            self._itinerary_popup.lift()

    def _set_research_output(self, text: str):
        txt = self._ensure_itinerary_popup()
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("end", text)
        txt.see("1.0")
        txt.configure(state="disabled")
        if self._itinerary_popup is not None:
            self._itinerary_popup.deiconify()
            self._itinerary_popup.lift()

    def _render_itinerary_output(self, result: ItineraryResult, subtitle: str = ""):
        lines: List[str] = []
        lines.append("Research Prototype: Emotion-Aware Safe Itinerary Recommendation")
        if subtitle:
            lines.append(subtitle)
        lines.append(f"Detected Emotion: {result.emotion}")
        lines.append(f"Trip Inputs: budget=${result.budget}, days={result.travel_days} (requested trip length)")
        lines.append(f"Final Ranked Itinerary Score: {result.itinerary_score:.3f}")
        lines.append(f"Estimated Total Cost: ${result.total_estimated_cost}")
        selected_mode = bool(subtitle and "selected places only" in subtitle.lower())
        if selected_mode:
            lines.append(
                "Note: this plan uses ONLY places you picked. Days are grouped by place "
                "(e.g., A,A,A,B,B,C) with different activity plans for repeat days."
            )
        else:
            lines.append(
                "Note: day plans use every requested day; if the attraction pool is small, "
                "the same stops may appear again on later days (realistic for long trips)."
            )
        lines.append("")
        lines.append("Day-wise Itinerary Plan")
        for day in result.day_plans:
            lines.append(
                f"Day {day.day} ({day.region}) | Estimated Cost: ${day.estimated_day_cost} | "
                f"Avg Safety: {day.day_safety_score:.1f}/10"
            )
            for item in day.attractions:
                a = item.attraction
                note = item.slot_note or ""
                lc = slot_line_cost(item)
                if selected_mode:
                    lines.append(f"  Destination: {a.name} [{a.category}]")
                    lines.append(f"  Plan: {note.replace(' — ', '') if note else 'core visit plan'}")
                    lines.append(f"  Day cost: ${lc} | safety={a.safety_score}/10 | score={item.final_score:.3f}")
                else:
                    lines.append(
                        f"  - {a.name}{note} [{a.category}] | cost=${lc} | "
                        f"safety={a.safety_score}/10 | score={item.final_score:.3f}"
                    )
        lines.append("")
        show_n = min(25, len(result.ranked_attractions))
        lines.append(f"Ranked destination cards (top {show_n} of {len(result.ranked_attractions)})")
        for rank, item in enumerate(result.ranked_attractions[:show_n], start=1):
            a = item.attraction
            lines.append(
                f"#{rank} {a.name} | {a.category} | {a.region} | cost=${a.estimated_cost} | "
                f"safety={a.safety_score}/10 | emotion_match={item.emotion_match_score:.2f} | "
                f"budget_fit={item.budget_compatibility_score:.2f} | final={item.final_score:.3f}"
            )
        self._set_research_output("\n".join(lines))

    def _generate_itinerary_from_mood(self, mood: str):
        budget, days = self._read_budget_days()
        result = generate_itinerary(emotion=mood, user_budget=budget, travel_days=days, max_locations_per_day=3)
        self.latest_itinerary = result
        if not result.ranked_attractions:
            self._append_bot(
                "I could not build a safe itinerary under the current budget/day limits. "
                "Try increasing budget or reducing days."
            )
            self._set_research_output(
                "No itinerary generated with current constraints.\n"
                f"Detected emotion: {mood}\nBudget: ${budget}\nDays: {days}"
            )
            return

        self._append_bot(
            f"Generated a mood-based itinerary for {days} day(s) with budget ${budget}. "
            f"Score: {result.itinerary_score:.3f}, estimated total: ${result.total_estimated_cost}. "
            "See the separate Itinerary window."
        )
        self._render_itinerary_output(result, subtitle="Mode: emotion-aware recommendation (auto-ranked)")

    def _load_model_background(self):
        try:
            self.status_var.set("Indexing dataset + loading model (first run may take a while)...")
            model, class_names = train_or_load_model(
                dataset_dir=self.dataset_dir,
                model_path=self.model_path,
                labels_path=self.labels_path,
                prefer_csv=True,
                epochs=25,
                batch_size=64,
                force_retrain=self.force_retrain,
                allow_folder_fallback=self.allow_folder_fallback,
                use_imagenet_weights=self.use_imagenet_weights,
            )
            self.model = model
            self.class_names = class_names
            # Tk widgets must be updated from the Tk thread; schedule via `after`.
            def _on_model_ready():
                self.status_var.set("Model ready. Start webcam to begin.")
                # If the user already started the webcam, enable detection now.
                if self.running:
                    self.btn_detect.configure(state="normal")

            self.root.after(0, _on_model_ready)
        except Exception as e:
            # Capture exception text immediately. Python clears `e` after the
            # `except` block ends, but Tk callbacks run later.
            err_type = type(e).__name__
            err_msg = str(e)
            def _on_failed():
                self.status_var.set("Model load/train failed.")
                self._append_bot(
                    "I couldn't load/train the emotion model.\n"
                    f"Details: {err_type}: {err_msg}\n\n"
                    "Traceback:\n"
                    f"{traceback.format_exc()}\n"
                    "Make sure you have `dataset/fer2013.csv`."
                )

            self.root.after(0, _on_failed)

    def start_webcam(self):
        if self.running:
            return
        self.cap = self._open_any_webcam()
        if self.cap is None or (hasattr(self.cap, "isOpened") and not self.cap.isOpened()):
            messagebox.showerror(
                "Webcam Error",
                "Could not open a webcam.\n\n"
                "Try:\n"
                "- Close other apps that may be using the camera (Zoom/Teams/Camera app/browser)\n"
                "- Windows Settings → Privacy & security → Camera → allow access for Desktop apps\n"
                "- If you have an external webcam, unplug/replug it\n",
            )
            return
        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        # Make the button clickable immediately after webcam start.
        # If the model isn't ready yet, `detect_now()` will show a helpful message.
        self.btn_detect.configure(state="normal")
        self._append_bot("Webcam started. When you're ready, click **Detect Mood Now**.")
        self._video_loop()

    def _open_any_webcam(self) -> Optional[cv2.VideoCapture]:
        """
        Best-effort webcam open for Windows:
        - Try multiple indices (0..3)
        - Prefer DirectShow backend if available
        """
        # Backends to try (CAP_DSHOW helps on many Windows machines)
        backends = []
        if hasattr(cv2, "CAP_DSHOW"):
            backends.append(cv2.CAP_DSHOW)
        if hasattr(cv2, "CAP_MSMF"):
            backends.append(cv2.CAP_MSMF)
        # Fallback: default backend
        backends.append(None)

        for idx in range(0, 4):
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(idx) if backend is None else cv2.VideoCapture(idx, backend)
                    if cap is not None and cap.isOpened():
                        # Warm-up read (some drivers need 1-2 reads)
                        for _ in range(3):
                            cap.read()
                        self._append_bot(f"Opened webcam at index {idx}.")
                        return cap
                    if cap is not None:
                        cap.release()
                except Exception:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
                    continue
        return None

    def stop_webcam(self):
        self.running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_detect.configure(state="disabled")
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
        self.video_label.configure(text="Webcam stopped.")
        self._append_bot("Webcam stopped.")

    def _video_loop(self):
        if not self.running or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            self.latest_frame = frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.latest_gray = gray
            faces = detect_faces(gray)
            self.latest_faces = faces

            # draw overlay
            overlay = frame.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if self.current_mood is not None and self.current_conf is not None:
                text = f"{self.current_mood} ({self.current_conf*100:.1f}%)"
                cv2.putText(
                    overlay,
                    text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            # Convert to Tk image via PPM bytes (no Pillow dependency)
            rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            ppm_header = f"P6 {w} {h} 255\n".encode("ascii")
            ppm_data = ppm_header + rgb.tobytes()
            img = tk.PhotoImage(data=ppm_data, format="PPM")
            self.video_label.configure(image=img, text="")
            self.video_label.image = img  # keep reference

        # schedule next frame
        self.root.after(30, self._video_loop)

    def detect_now(self):
        if self.model is None or self.class_names is None:
            self._append_bot("Model isn't ready yet—give it a moment.")
            return
        if self.latest_gray is None or self.latest_frame is None:
            self._append_bot("No webcam frame yet. Please wait a second and try again.")
            return
        probs_samples: List[np.ndarray] = []
        frames_to_sample = 4 if self.running and self.cap is not None else 1
        for _ in range(frames_to_sample):
            sample_gray = self.latest_gray
            sample_faces = list(self.latest_faces) if self.latest_faces is not None else []
            if self.running and self.cap is not None:
                ok, frame = self.cap.read()
                if ok:
                    self.latest_frame = frame
                    sample_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    self.latest_gray = sample_gray
                    sample_faces = list(detect_faces(sample_gray))
                    self.latest_faces = sample_faces

            if sample_gray is None or not sample_faces:
                continue

            # pick largest face
            sample_faces = sorted(sample_faces, key=lambda b: b[2] * b[3], reverse=True)
            face_box = tuple(int(v) for v in sample_faces[0])
            face_tensor = preprocess_face(sample_gray, face_box)
            try:
                probs_samples.append(self.model.predict(face_tensor, verbose=0)[0])
            except Exception as pred_e:
                self._append_bot(
                    "Prediction failed. The saved model may be incompatible.\n"
                    f"Details: {type(pred_e).__name__}: {pred_e}\n"
                    "Please restart the app once; it will automatically retrain if loading fails."
                )
                return

        if not probs_samples:
            self._append_bot("I couldn't find a face. Please face the camera with good lighting and try again.")
            return

        probs = np.mean(np.asarray(probs_samples), axis=0)
        idx = int(np.argmax(probs))
        raw_label = self.class_names[idx]
        mood = canonicalize_label(raw_label)
        conf = float(probs[idx])
        top2 = np.argsort(probs)[-2:][::-1]
        top2_str = ", ".join([f"{canonicalize_label(self.class_names[i])} {probs[i]*100:.1f}%" for i in top2])

        self.current_mood = mood
        self.current_conf = conf
        self.awaiting_yes_no = True
        self._clear_chat_suggestion_rows()

        self._append_bot(f"Detected mood: **{mood}** (confidence {conf*100:.1f}%).")
        self._append_bot(f"Top guesses: {top2_str}")
        self._append_bot(
            "No itinerary was generated yet. Under **Plan your trip**, click "
            "**Generate itinerary (emotion + budget + days)** when you are ready. "
            "The plan will open in a separate Itinerary window."
        )
        self._ask_mood_question(mood)

        self.btn_yes.configure(state="normal")
        self.btn_maybe.configure(state="normal")
        self.btn_more.configure(state="disabled")

    def _ask_mood_question(self, mood: str):
        mood_key = TOUR_ALIASES.get(mood, mood)
        content = TOUR_BOT.get(mood_key) or TOUR_BOT["Neutral"]
        q = str(content["question"])
        self._append_bot(q)

    def on_yes_no(self, choice: str):
        if not self.awaiting_yes_no or self.current_mood is None:
            return
        self._append_user("Yes, let's explore!" if choice == "yes" else "Maybe something else")

        mood_key = TOUR_ALIASES.get(self.current_mood, self.current_mood)
        content = TOUR_BOT.get(mood_key) or TOUR_BOT["Neutral"]

        if choice == "yes":
            primary = str(content["primary"])
            self._append_bot(f"Perfect. Here’s a great match:\n- {primary}")
            self._append_bot("Want more options for this mood? Click **More tour suggestions**.")
            self.btn_more.configure(state="normal")
            self._populate_suggestion_buttons([primary])
        else:
            alts = content["alternatives"]
            lines = "\n".join([f"- {s}" for s in alts])
            self._append_bot("Absolutely. Here are some other great ideas:\n" + lines)
            self.btn_more.configure(state="normal")
            self._populate_suggestion_buttons(list(alts))

        self.awaiting_yes_no = False
        self.btn_yes.configure(state="disabled")
        self.btn_maybe.configure(state="disabled")

    def more_suggestions(self):
        if self.current_mood is None:
            self._append_bot("Detect your mood first, then I can tailor more suggestions.")
            return
        mood_key = TOUR_ALIASES.get(self.current_mood, self.current_mood)
        content = TOUR_BOT.get(mood_key) or TOUR_BOT["Neutral"]
        alts = content["alternatives"]
        # rotate suggestions
        rotated = alts[1:] + alts[:1]
        content["alternatives"] = rotated
        lines = "\n".join([f"- {s}" for s in rotated])
        self._append_bot("More ideas you might like:\n" + lines)
        self._populate_suggestion_buttons(list(rotated))


def main():
    # Find project root as parent of this file's directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(app_dir)

    parser = argparse.ArgumentParser(description="Sri Lanka Mood-Based Travel Bot (emotion detection + tours)")
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Force retraining even if a saved model exists (useful after changing datasets).",
    )
    parser.add_argument(
        "--use-folders",
        action="store_true",
        help="Allow training from `dataset/<emotion>/*.png` folders if fer2013.csv is missing (lower accuracy).",
    )
    parser.add_argument(
        "--fer-only",
        action="store_true",
        help="Require `dataset/fer2013.csv` and do not fall back to folder datasets.",
    )
    parser.add_argument(
        "--no-imagenet",
        action="store_true",
        help="Do not download/use ImageNet weights for the transfer model (useful if downloads are blocked).",
    )
    parser.add_argument(
        "--train-only",
        action="store_true",
        help="Train/prepare the model in the console only (no GUI). Useful for debugging training.",
    )
    args, _ = parser.parse_known_args()

    if bool(args.train_only):
        # Console-only training path (prints progress + errors reliably)
        dataset_dir = os.path.join(project_root, "dataset")
        model_path = os.path.join(project_root, "app", "models", "fer_emotion_cnn.keras")
        labels_path = os.path.join(project_root, "app", "models", "labels.json")
        print("[mode] train-only")
        model, class_names = train_or_load_model(
            dataset_dir=dataset_dir,
            model_path=model_path,
            labels_path=labels_path,
            prefer_csv=True,
            epochs=25,
            batch_size=64,
            force_retrain=bool(args.retrain),
            allow_folder_fallback=(not bool(args.fer_only)),
            use_imagenet_weights=(not bool(args.no_imagenet)),
        )
        print(f"[done] model saved to: {model_path}")
        print(f"[done] labels: {class_names}")
        return

    root = tk.Tk()
    # Improve default theme on Windows
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass

    MoodTourApp(
        root,
        project_root=project_root,
        force_retrain=bool(args.retrain),
        allow_folder_fallback=(not bool(args.fer_only)),
        use_imagenet_weights=(not bool(args.no_imagenet)),
    )
    root.mainloop()


if __name__ == "__main__":
    # Reduce TF logging noise
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    tf.get_logger().setLevel("ERROR")
    main()


