"""TASK-057 (Fase 2, design.md §2.1): overlay toggleable de landmarks +
cuadrante + distincion mano primaria/otra + etiqueta de gesto activo.

`HAND_CONNECTIONS` es la topologia estandar (publicamente documentada) de los
21 landmarks de mano - no viene de `mp.solutions` (removido de los wheels de
Windows, ver `hand_tracker.py`), asi que este modulo la declara localmente
y dibuja con `cv2` puro, sin dependencia nueva.

`hand_connection_segments()`/`bounding_quadrant()` son funciones puras
(testeables sin ventana/display real); `draw_hand_overlay()` es la unica
parte con efecto visual (dibuja sobre `frame` in-place), verificada a mano
con camara real, igual que el resto del dibujo de frame de este proyecto.
"""

import cv2

from jarvis import config

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm base
]


def hand_connection_segments(landmarks, w, h):
    """Lista de ((x1, y1), (x2, y2)) en pixeles, uno por cada HAND_CONNECTIONS."""
    return [
        ((int(landmarks[a].x * w), int(landmarks[a].y * h)), (int(landmarks[b].x * w), int(landmarks[b].y * h)))
        for a, b in HAND_CONNECTIONS
    ]


def bounding_quadrant(landmarks, w, h):
    """(x_min, y_min, x_max, y_max) en pixeles del bbox de los 21 landmarks."""
    xs = [p.x * w for p in landmarks]
    ys = [p.y * h for p in landmarks]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def draw_hand_overlay(frame, hands, primary_landmarks, active_gesture_name):
    """Dibuja, in-place sobre `frame`, el esqueleto + cuadrante de cada mano
    detectada (color primario para la mano que GestureEngine eligio como
    activa - identidad de objeto contra `primary_landmarks`, no igualdad de
    valores, ya que es la misma lista que ya trae `hands` - color secundario/
    tenue para cualquier otra), y la etiqueta del gesto activo junto a la
    mano primaria."""
    h, w = frame.shape[:2]
    for hand in hands:
        is_primary = hand.landmarks is primary_landmarks
        color = config.HAND_OVERLAY_PRIMARY_COLOR if is_primary else config.HAND_OVERLAY_OTHER_COLOR

        for (x1, y1), (x2, y2) in hand_connection_segments(hand.landmarks, w, h):
            cv2.line(frame, (x1, y1), (x2, y2), color, 2)
        for lm in hand.landmarks:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 3, color, -1)

        x_min, y_min, x_max, y_max = bounding_quadrant(hand.landmarks, w, h)
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 1)

        if is_primary and active_gesture_name:
            cv2.putText(
                frame, active_gesture_name, (x_min, max(y_min - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )
