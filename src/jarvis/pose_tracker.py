"""Wrapper sobre la API 'Tasks' de MediaPipe (PoseLandmarker).

TASK-060b (`openspec/changes/personalization-and-config-ui`, design.md §3B.1):
mismo patron que `hand_tracker.py` (mismo paquete `mediapipe`, cero dependencia
nueva), pero para el cuerpo completo - se usa para saber a que persona
pertenece cada mano detectada (design.md §3B.2), no para gestos propios.

`num_poses=1` a proposito (no `MAX_HANDS`): solo el cuerpo del usuario
principal importa aca - trackear mas de 1 cuerpo reintroduciria la misma
ambiguedad que esta fase existe para eliminar (design.md §3B.1).
"""

import math
import time
import urllib.request

import mediapipe as mp
from mediapipe.tasks.python import vision

from jarvis import config
from jarvis.paths import assets_dir

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

# Indices de landmark de BlazePose (33 puntos, topologia estandar de MediaPipe
# Pose - sin cambios entre la API legacy y la API Tasks).
LEFT_WRIST = 15
RIGHT_WRIST = 16


def _ensure_model():
    model_path = assets_dir() / "pose_landmarker_lite.task"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if not model_path.exists():
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


class PoseTracker:
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        model_path = _ensure_model()
        options = vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._start_time = time.time()

    def process(self, rgb_frame):
        """Devuelve la lista de 33 NormalizedLandmark del cuerpo principal, o
        None si no se detecto ningun cuerpo en el frame (no lanza excepcion -
        design.md §3B.2: la logica de filtrado que consume esto debe poder
        caer a su heuristica anterior en ese caso, no fallar)."""
        timestamp_ms = int((time.time() - self._start_time) * 1000)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.pose_landmarks:
            return None
        return result.pose_landmarks[0]


def _near(p1, p2, w, h, max_distance_px):
    return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h) <= max_distance_px


def filter_hands_by_pose_ownership(hands, pose_landmarks, w, h):
    """TASK-060c (design.md §3B.2): una mano detectada solo se considera del
    usuario si su landmark 0 (muñeca) esta cerca de la muñeca correspondiente
    (izquierda o derecha) del cuerpo trackeado por PoseTracker. Devuelve None
    (no una lista vacia) cuando `pose_landmarks` es None, para que quien llama
    pueda distinguir "sin cuerpo trackeado, usar el heuristico de Fase 1
    (TASK-056)" de "cuerpo trackeado, ninguna mano es del usuario" - un cuerpo
    no detectado en un frame (iluminacion, encuadre) NO debe hacer que la app
    deje de responder a gestos (spec.md #3B.2)."""
    if pose_landmarks is None:
        return None
    left_wrist = pose_landmarks[LEFT_WRIST]
    right_wrist = pose_landmarks[RIGHT_WRIST]
    max_distance_px = config.POSE_MAX_WRIST_DISTANCE_FRACTION * math.hypot(w, h)
    return [
        hand
        for hand in hands
        if _near(hand.landmarks[0], left_wrist, w, h, max_distance_px)
        or _near(hand.landmarks[0], right_wrist, w, h, max_distance_px)
    ]
