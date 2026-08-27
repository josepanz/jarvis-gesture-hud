"""Motor de reconocimiento de gestos: puro, sin efectos de I/O (mouse/voz/SO).

`process()` recibe la lista de manos detectadas en un frame (0-2, ver `hand_tracker.py`)
y devuelve los eventos detectados. Quien llama (`main.py`) decide que hacer con cada evento.

Gestos a 2 manos (funcionan aunque `active` este en False, salvo el pinch-zoom que
requiere estar activo para no interferir con la pausa/cierre):
- 2 puños juntos sostenidos -> "TOGGLE_ACTIVE" (pausa/reanuda TODO lo demas, incluido el puntero).
- 2 manos en Shaka sostenidas -> "CLOSE_APP".
- 2 manos pellizcando (pinch), separandolas/juntandolas -> "ZOOM_IN"/"ZOOM_OUT" (Ctrl+Scroll,
  igual que el zoom de una mano; NO escala el objeto seleccionado, hace zoom del lienzo/vista).
- Una mano en puño (ancla) + la otra mostrando 1-4 dedos, sostenido -> menu de acciones
  secundarias (mismas que hoy son solo teclas): 1=toggle leyenda, 2=toggle espejo,
  3=+transparencia, 4=-transparencia. No depende de lateralidad (no importa cual mano
  hace de ancla), asi que sigue sin usarse `Hand.handedness` en ningun gesto actual.

Todo el resto de los gestos (una sola mano) se ignora mientras `active` es False.
"""

import math
import time

from jarvis import config

META_ACTIONS = {
    1: "TOGGLE_LEGEND",
    2: "TOGGLE_MIRROR",
    3: "LEGEND_ALPHA_UP",
    4: "LEGEND_ALPHA_DOWN",
}


def _interp(value, in_min, in_max, out_min, out_max):
    value = min(max(value, in_min), in_max)
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def _is_fist(pts):
    return all(pts[i].y > pts[i - 2].y for i in (8, 12, 16, 20))


def _is_shaka(pts):
    return pts[20].y < pts[18].y and pts[4].y < pts[2].y and pts[8].y > pts[6].y and pts[12].y > pts[10].y


def _extended_finger_count(pts):
    return sum(1 for i in (8, 12, 16, 20) if pts[i].y < pts[i - 2].y)


class GestureEngine:
    def __init__(self, smoothing_enabled=True):
        self.active = True
        self.smoothing_enabled = smoothing_enabled  # TASK-018: spec.md #7 "smoothing.enabled"

        self.prev_x, self.prev_y = 0, 0
        self.was_pinching = False
        self.was_right_pinching = False
        self.prev_scroll_y = None
        self.prev_zoom_y = None
        self.prev_pinky_y = None
        self.lock_start_time = None
        self.last_click_time = 0.0
        self.last_right_click_time = 0.0
        self.last_screenshot_time = 0.0
        self.last_toggle_time = 0.0
        self.last_silence_time = 0.0

        self.pause_hold_start = None
        self.close_hold_start = None
        self.prev_two_hand_pinch_dist = None
        self.meta_pose = None
        self.meta_hold_start = None
        self.meta_consumed = False

        self._primary_pos = None  # (x, y) normalizado del indice de la ultima mano "activa"

    @staticmethod
    def _dist(p1, p2, w, h):
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h)

    def _smooth(self, target_x, target_y):
        if not self.smoothing_enabled:
            self.prev_x, self.prev_y = target_x, target_y
            return int(target_x), int(target_y)
        x = config.EMA_ALPHA * target_x + (1 - config.EMA_ALPHA) * self.prev_x
        y = config.EMA_ALPHA * target_y + (1 - config.EMA_ALPHA) * self.prev_y
        self.prev_x, self.prev_y = x, y
        return int(x), int(y)

    def _pick_primary(self, hands):
        """Con 2 manos en cuadro, elige la mas cercana a donde estaba la mano activa
        el frame anterior, para que el puntero no salte de una mano a otra sin querer
        (MediaPipe no garantiza que `hands[0]` sea siempre la misma mano fisica)."""
        if len(hands) == 1 or self._primary_pos is None:
            return hands[0].landmarks
        px, py = self._primary_pos
        best = min(hands, key=lambda hnd: math.hypot(hnd.landmarks[8].x - px, hnd.landmarks[8].y - py))
        return best.landmarks

    def _process_two_hand_gestures(self, hands, w, h, now):
        """Gestos a 2 manos. Devuelve (events, suppress_single_hand_pinch, both_shaka)."""
        events = []
        if len(hands) != 2:
            self.pause_hold_start = None
            self.close_hold_start = None
            self.prev_two_hand_pinch_dist = None
            self.meta_pose = None
            self.meta_hold_start = None
            self.meta_consumed = False
            return events, False, False

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

        # Pinch-zoom a 2 manos: ambas pellizcando (thumb+index), la distancia entre los
        # 2 puntos de pellizco escala el lienzo (Ctrl+Scroll) - no el objeto seleccionado.
        d1 = self._dist(p1[4], p1[8], w, h)
        d2 = self._dist(p2[4], p2[8], w, h)
        both_pinching = d1 < config.PINCH_CLICK and d2 < config.PINCH_CLICK
        if both_pinching:
            c1x, c1y = (p1[4].x + p1[8].x) / 2 * w, (p1[4].y + p1[8].y) / 2 * h
            c2x, c2y = (p2[4].x + p2[8].x) / 2 * w, (p2[4].y + p2[8].y) / 2 * h
            dist = math.hypot(c2x - c1x, c2y - c1y)
            if self.prev_two_hand_pinch_dist is not None:
                delta = dist - self.prev_two_hand_pinch_dist
                if delta > config.TWO_HAND_ZOOM_DELTA_PX:
                    events.append("ZOOM_IN")
                elif delta < -config.TWO_HAND_ZOOM_DELTA_PX:
                    events.append("ZOOM_OUT")
            self.prev_two_hand_pinch_dist = dist
        else:
            self.prev_two_hand_pinch_dist = None

        # Menu de acciones secundarias: una mano en puño (ancla), la otra muestra 1-4
        # dedos sostenidos config.META_HOLD_SECONDS para confirmar. No importa cual
        # mano hace de ancla - no depende de lateralidad.
        fists = (_is_fist(p1), _is_fist(p2))
        if fists[0] != fists[1] and not both_pinching:
            selector_pts = p2 if fists[0] else p1
            count = _extended_finger_count(selector_pts)
            if count in META_ACTIONS:
                if count != self.meta_pose:
                    self.meta_pose = count
                    self.meta_hold_start = now
                    self.meta_consumed = False
                elif not self.meta_consumed and now - self.meta_hold_start > config.META_HOLD_SECONDS:
                    events.append(META_ACTIONS[count])
                    self.meta_consumed = True
            else:
                self.meta_pose = None
                self.meta_hold_start = None
                self.meta_consumed = False
        else:
            self.meta_pose = None
            self.meta_hold_start = None
            self.meta_consumed = False

        return events, both_pinching, both_shaka

    def process(self, hands, w, h, screen_w, screen_h):
        """Devuelve (screen_xy, cam_xy, events). screen_xy/cam_xy son None si no hay
        puntero que mover (sin manos, o lectura de gestos en pausa)."""
        now = time.time()
        events, suppress_pinch, both_shaka = self._process_two_hand_gestures(hands, w, h, now)

        if not self.active or not hands:
            return None, None, events

        pts = self._pick_primary(hands)
        thumb, index, middle, ring, pinky = pts[4], pts[8], pts[12], pts[16], pts[20]

        raw_x = _interp(index.x, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_w)
        raw_y = _interp(index.y, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_h)
        screen_xy = self._smooth(raw_x, raw_y)
        cam_xy = (int(index.x * w), int(index.y * h))
        self._primary_pos = (index.x, index.y)

        d_thumb_index = self._dist(thumb, index, w, h)
        d_thumb_middle = self._dist(thumb, middle, w, h)
        d_thumb_ring = self._dist(thumb, ring, w, h)
        d_thumb_pinky = self._dist(thumb, pinky, w, h)
        d_thumb_pinky_mcp = self._dist(thumb, pts[17], w, h)

        # TASK-055: resolucion de prioridad entre gestos de pinch. En un puno con
        # solo pulgar+indice desplegados y pellizcando, las puntas de los demas
        # dedos curvados quedan geometricamente cerca del pulgar (consecuencia
        # natural de la forma de un puno) y pueden cumplir el umbral de OTRO pinch
        # (ej. click derecho) en el mismo frame - antes de este fix, ambos
        # disparaban juntos ("se confunde"). Gana el dedo con distancia mas chica
        # (el pellizco mas ajustado, el mas probable de ser intencional); en un
        # empate exacto gana el primero listado abajo (orden fijo, deterministico).
        _ring_pinch_threshold = max(config.PINCH_SCREENSHOT, config.PINCH_ZOOM)
        _pinch_candidates = [
            ("index", d_thumb_index, config.PINCH_CLICK),
            ("middle", d_thumb_middle, config.PINCH_RIGHT_CLICK),
            ("ring", d_thumb_ring, _ring_pinch_threshold),
            ("pinky", d_thumb_pinky, config.PINCH_VOLUME),
        ]
        _active_pinches = [(name, dist) for name, dist, threshold in _pinch_candidates if dist < threshold]
        pinch_winner = min(_active_pinches, key=lambda p: p[1])[0] if _active_pinches else None

        fingers_extended = all(pts[i].y < pts[i - 2].y for i in (8, 12, 16, 20))

        # Lock session: Shaka (pulgar+meñique extendidos, índice/medio recogidos) sostenido.
        # Suprimido si las 2 manos ya estan haciendo Shaka (eso es el gesto de cerrar, no de bloquear).
        if _is_shaka(pts) and not both_shaka:
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
        screenshot_pinch = pinch_winner == "ring" and d_thumb_ring < config.PINCH_SCREENSHOT
        if screenshot_pinch and index.y > pts[6].y and pinky.y > pts[18].y:
            if now - self.last_screenshot_time > config.SCREENSHOT_COOLDOWN:
                events.append("SCREENSHOT")
                self.last_screenshot_time = now

        # Zoom: pulgar+anular pinch con índice extendido, dirección por movimiento vertical del anular
        elif pinch_winner == "ring" and d_thumb_ring < config.PINCH_ZOOM and index.y < pts[6].y:
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
        if pinch_winner == "pinky" and d_thumb_pinky < config.PINCH_VOLUME:
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

        # Click izquierdo / drag / selección de tecla HUD (edge-triggered).
        # Suprimido mientras las 2 manos hacen el pinch-zoom, para no disparar un click
        # de paso con la mano que termina siendo "primaria".
        is_pinching = pinch_winner == "index" and d_thumb_index < config.PINCH_CLICK and not suppress_pinch
        if is_pinching and not self.was_pinching and now - self.last_click_time > config.CLICK_COOLDOWN:
            events.append("PINCH_DOWN")
            self.last_click_time = now
        elif not is_pinching and self.was_pinching:
            events.append("PINCH_UP")
        self.was_pinching = is_pinching

        # Click derecho (edge-triggered). Cooldown propio (last_right_click_time) -
        # antes compartia last_click_time con el click izquierdo, asi que un click
        # izquierdo reciente podia "tragarse" un click derecho genuino y no
        # ambiguo hecho poco despues (encontrado documentando TASK-055, arreglado
        # aparte porque es un bug distinto: temporal entre gestos, no ambiguedad
        # dentro de un mismo frame).
        is_right_pinching = pinch_winner == "middle" and d_thumb_middle < config.PINCH_RIGHT_CLICK
        if (
            is_right_pinching
            and not self.was_right_pinching
            and now - self.last_right_click_time > config.RIGHT_CLICK_COOLDOWN
        ):
            events.append("RIGHT_CLICK")
            self.last_right_click_time = now
        self.was_right_pinching = is_right_pinching

        return screen_xy, cam_xy, events
