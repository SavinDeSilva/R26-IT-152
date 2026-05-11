import base64
import os
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

try:
    from .mood_tour_chatbot import (
        canonicalize_label,
        detect_faces,
        preprocess_face,
        train_or_load_model,
    )
except ImportError:
    # Allows running when app/ is the script root.
    from mood_tour_chatbot import (
        canonicalize_label,
        detect_faces,
        preprocess_face,
        train_or_load_model,
    )


class EmotionDetectionService:
    """
    Reuses the project's existing model loading + face/emotion inference logic,
    but exposes it in a backend-friendly service class.
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.dataset_dir = os.path.join(project_root, "dataset")
        self.model_path = os.path.join(project_root, "app", "models", "fer_emotion_cnn.keras")
        self.labels_path = os.path.join(project_root, "app", "models", "labels.json")
        self.model = None
        self.class_names = None

    def _ensure_model(self) -> None:
        if self.model is not None and self.class_names is not None:
            return
        self.model, self.class_names = train_or_load_model(
            dataset_dir=self.dataset_dir,
            model_path=self.model_path,
            labels_path=self.labels_path,
            prefer_csv=True,
            epochs=25,
            batch_size=64,
            force_retrain=False,
            allow_folder_fallback=True,
            use_imagenet_weights=True,
        )

    @staticmethod
    def _decode_base64_image(image_base64: str) -> np.ndarray:
        # Accept both plain base64 and data URL format.
        if "," in image_base64 and "base64" in image_base64[:40]:
            image_base64 = image_base64.split(",", 1)[1]
        raw = base64.b64decode(image_base64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from base64 payload.")
        return img

    @staticmethod
    def _decode_bytes_image(raw: bytes) -> np.ndarray:
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode uploaded image bytes.")
        return img

    def detect_from_image(self, bgr_image: np.ndarray) -> Dict[str, Any]:
        self._ensure_model()
        if self.model is None or self.class_names is None:
            raise RuntimeError("Model is not available.")

        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        faces = list(detect_faces(gray))
        if not faces:
            raise ValueError("No face detected in the provided image.")

        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        face_box = tuple(int(v) for v in faces[0])
        face_tensor = preprocess_face(gray, face_box)
        probs = self.model.predict(face_tensor, verbose=0)[0]
        idx = int(np.argmax(probs))
        raw_label = str(self.class_names[idx])
        emotion = canonicalize_label(raw_label).lower()
        confidence = float(probs[idx])
        return {
            "emotion": emotion,
            "confidence": round(confidence, 4),
        }

    def detect_from_payload(
        self,
        image_base64: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        if image_base64:
            img = self._decode_base64_image(image_base64)
            return self.detect_from_image(img)
        if image_bytes:
            img = self._decode_bytes_image(image_bytes)
            return self.detect_from_image(img)
        raise ValueError("No image provided. Send `image_base64` or multipart `image` file.")
