"""Motor de reconocimiento de gestos: puro, sin efectos de I/O (mouse/voz/SO).

`process()` recibe la lista de manos detectadas en un frame (0-2, ver `hand_tracker.py`)
y devuelve los eventos detectados. Quien llama (`main.py`) decide que hacer con cada evento.

Gestos maestros (a 2 manos, funcionan incluso si `active` esta en False):
- 2 puños juntos sostenidos -> "TOGGLE_ACTIVE" (pausa/reanuda TODO lo demas, incluido el puntero).
- 2 manos en Shaka sostenidas -> "CLOSE_APP".
Todo el resto de los gestos (una sola mano) se ignora mientras `active` es False.
"""

import math
import time

from jarvis import config


def _interp(value, in_min, in_max, out_min, out_max):
    value = min(max(value, in_min), in_max)
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def _is_fist(pts):
    return all(pts[i].y > pts[i - 2].y for i in (8, 12, 16, 20))


def _is_shaka(pts):
    return pts[20].y < pts[18].y and pts[4].y < pts[2].y and pts[8].y > pts[6].y and pts[12].y > pts[10].y


class GestureEngine:
    def __init__(self):
        self.active = True

        self.prev_x, self.prev_y = 0, 0
        self.was_pinching = False
        self.was_right_pinching = False
        self.prev_scroll_y = None
        self.prev_zoom_y = None
        self.prev_pinky_y = None
        self.lock_start_time = None
        self.last_click_time = 0.0
        self.last_screenshot_time = 0.0
        self.last_toggle_time = 0.0
        self.last_silence_time = 0.0

        self.pause_hold_start = None
        self.close_hold_start = None

    @staticmethod
    def _dist(p1, p2, w, h):
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h)

    def _smooth(self, target_x, target_y):
        x = config.EMA_ALPHA * target_x + (1 - config.EMA_ALPHA) * self.prev_x
        y = config.EMA_ALPHA * target_y + (1 - config.EMA_ALPHA) * self.prev_y
        self.prev_x, self.prev_y = x, y
        return int(x), int(y)

    def _process_two_hand_gestures(self, hands, now):
        """Gestos maestros a 2 manos. Devuelve la lista de eventos que disparan."""
        events = []
        if len(hands) != 2:
            self.pause_hold_start = None
            self.close_hold_start = None
            return events

        p1, p2 = hands[0].landmarks, hands[1].landmarks
        both_shaka = _is_shaka(p1) and _is_shaka(p2)
        both_fists = _is_fist(p1) and _is_fist(p2)

        if both_shaka:
            if self.close_hold_start is None:
                self.close_hold_start = now
            elif now - self.close_hold_start > config.CLOSE_APP_HOLD_SECONDS:
                events.append("CLOSE_APP")
                self.close_hold_start = None
        else:
            self.close_hold_start = None

        if both_fists and not both_shaka:
            if self.pause_hold_start is None:
                self.pause_hold_start = now
            elif now - self.pause_hold_start > config.PAUSE_HOLD_SECONDS:
                self.active = not self.active
                events.append("TOGGLE_ACTIVE")
                self.pause_hold_start = None
        else:
            self.pause_hold_start = None

        return events

    def process(self, hands, w, h, screen_w, screen_h):
        """Devuelve (screen_xy, cam_xy, events). screen_xy/cam_xy son None si no hay
        puntero que mover (sin manos, o lectura de gestos en pausa)."""
        now = time.time()
        events = self._process_two_hand_gestures(hands, now)

        if not self.active or not hands:
            return None, None, events

        pts = hands[0].landmarks
        thumb, index, middle, ring, pinky = pts[4], pts[8], pts[12], pts[16], pts[20]

        raw_x = _interp(index.x, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_w)
        raw_y = _interp(index.y, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_h)
        screen_xy = self._smooth(raw_x, raw_y)
        cam_xy = (int(index.x * w), int(index.y * h))

        d_thumb_index = self._dist(thumb, index, w, h)
        d_thumb_middle = self._dist(thumb, middle, w, h)
        d_thumb_ring = self._dist(thumb, ring, w, h)
        d_thumb_pinky = self._dist(thumb, pinky, w, h)
        d_thumb_pinky_mcp = self._dist(thumb, pts[17], w, h)

        fingers_extended = all(pts[i].y < pts[i - 2].y for i in (8, 12, 16, 20))

        # Lock session: Shaka (pulgar+meñique extendidos, índice/medio recogidos) sostenido
        if _is_shaka(pts):
            if self.lock_start_time is None:
                self.lock_start_time = now
            elif now - self.lock_start_time > config.LOCK_HOLD_SECONDS:
                events.append("LOCK_SESSION")
                self.lock_start_time = None
        else:
            self.lock_start_time = None

        # Silencio: mano abierta con pulgar recogido hacia la base del meñique.
        # Excluyente con el toggle de teclado (que exige el pulgar bien separado).
        if fingers_extended and d_thumb_pinky_mcp < config.SILENCE_TUCK_MAX:
            if now - self.last_silence_time > config.SILENCE_COOLDOWN:
                events.append("SILENCE")
                self.last_silence_time = now
        elif fingers_extended and d_thumb_index > config.PALM_OPEN_MIN_SPREAD:
            if now - self.last_toggle_time > config.KEYBOARD_TOGGLE_COOLDOWN:
                events.append("KEYBOARD_TOGGLE")
                self.last_toggle_time = now

        # Screenshot: pulgar+anular pinch con índice y meñique recogidos
        if d_thumb_ring < config.PINCH_SCREENSHOT and index.y > pts[6].y and pinky.y > pts[18].y:
            if now - self.last_screenshot_time > config.SCREENSHOT_COOLDOWN:
                events.append("SCREENSHOT")
                self.last_screenshot_time = now

        # Zoom: pulgar+anular pinch con índice extendido, dirección por movimiento vertical del anular
        elif d_thumb_ring < config.PINCH_ZOOM and index.y < pts[6].y:
            if self.prev_zoom_y is not None:
                delta = self.prev_zoom_y - ring.y
                if delta > config.VOLUME_DELTA_THRESHOLD:
                    events.append("ZOOM_IN")
                elif delta < -config.VOLUME_DELTA_THRESHOLD:
                    events.append("ZOOM_OUT")
            self.prev_zoom_y = ring.y
        else:
            self.prev_zoom_y = None

        # Volumen: pulgar+meñique pinch, dirección por movimiento vertical del meñique
        if d_thumb_pinky < config.PINCH_VOLUME:
            if self.prev_pinky_y is not None:
                delta = self.prev_pinky_y - pinky.y
                if delta > config.VOLUME_DELTA_THRESHOLD:
                    events.append("VOLUME_UP")
                elif delta < -config.VOLUME_DELTA_THRESHOLD:
                    events.append("VOLUME_DOWN")
            self.prev_pinky_y = pinky.y
        else:
            self.prev_pinky_y = None

        # Scroll: índice+medio extendidos, anular recogido, pulgar separado del índice
        if index.y < pts[6].y and middle.y < pts[10].y and ring.y > pts[14].y and d_thumb_index > 40:
            if self.prev_scroll_y is not None:
                delta = self.prev_scroll_y - index.y
                if delta > config.VOLUME_DELTA_THRESHOLD:
                    events.append("SCROLL_UP")
                elif delta < -config.VOLUME_DELTA_THRESHOLD:
                    events.append("SCROLL_DOWN")
            self.prev_scroll_y = index.y
        else:
            self.prev_scroll_y = None

        # Click izquierdo / drag / selección de tecla HUD (edge-triggered)
        is_pinching = d_thumb_index < config.PINCH_CLICK
        if is_pinching and not self.was_pinching and now - self.last_click_time > config.CLICK_COOLDOWN:
            events.append("PINCH_DOWN")
            self.last_click_time = now
        elif not is_pinching and self.was_pinching:
            events.append("PINCH_UP")
        self.was_pinching = is_pinching

        # Click derecho (edge-triggered)
        is_right_pinching = d_thumb_middle < config.PINCH_RIGHT_CLICK
        if (
            is_right_pinching
            and not self.was_right_pinching
            and now - self.last_click_time > config.RIGHT_CLICK_COOLDOWN
        ):
            events.append("RIGHT_CLICK")
            self.last_click_time = now
        self.was_right_pinching = is_right_pinching

        return screen_xy, cam_xy, events
