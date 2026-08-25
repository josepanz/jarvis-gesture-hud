"""Wrapper sobre la API 'Tasks' de MediaPipe (HandLandmarker).

La API legacy `mp.solutions.hands` fue removida de los wheels de Windows a partir
de mediapipe 0.10.30 — solo queda la API Tasks, que requiere descargar un modelo
`.task` la primera vez (se cachea en `assets/`).
"""

import sys
import time
import urllib.request
from collections import namedtuple
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

# landmarks: lista de 21 NormalizedLandmark (x, y, z en [0,1]).
# handedness: "Left" / "Right" / "Unknown", ya corregido segun si la imagen esta espejada.
Hand = namedtuple("Hand", "landmarks handedness")

_HANDEDNESS_SWAP = {"Left": "Right", "Right": "Left"}


def _assets_dir():
    # Dentro de un .exe de PyInstaller los datos empaquetados viven bajo sys._MEIPASS,
    # no junto a este archivo fuente.
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def _ensure_model():
    model_path = _assets_dir() / "hand_landmarker.task"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if not model_path.exists():
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


class HandTracker:
    def __init__(self, max_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        model_path = _ensure_model()
        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._start_time = time.time()

    def process(self, rgb_frame, mirrored=True):
        """Devuelve una lista de Hand (0-N) detectadas en el frame.

        MediaPipe estima la lateralidad (Left/Right) asumiendo que la imagen ya
        esta espejada tipo selfie. Si `mirrored=False` (camara trasera, sin flip),
        hay que invertir esa etiqueta para que corresponda a la mano real.
        """
        timestamp_ms = int((time.time() - self._start_time) * 1000)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        hands = []
        for i, landmarks in enumerate(result.hand_landmarks):
            label = "Unknown"
            if i < len(result.handedness) and result.handedness[i]:
                label = result.handedness[i][0].category_name or "Unknown"
            if not mirrored:
                label = _HANDEDNESS_SWAP.get(label, label)
            hands.append(Hand(landmarks=landmarks, handedness=label))
        return hands
