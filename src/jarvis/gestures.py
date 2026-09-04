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
from jarvis.temporal_gesture import ImpulseDetector

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
    # El anular curvado se agrego despues de verificar en camara real que la
    # transicion al abrir/cerrar un puno pasa, por un instante, por una forma
    # que ya cumplia esta funcion sin el chequeo de anular (menique se
    # "extiende" antes que el resto, pulgar ya arriba, indice/medio todavia
    # curvados) - eso podia sostenerse el tiempo suficiente para disparar
    # LOCK_SESSION sin que el usuario hiciera Shaka a proposito. Un Shaka real
    # (hang loose) tiene el anular curvado tambien, asi que este chequeo no
    # le saca alcance al gesto genuino.
    #
    # Hallazgo de camara real (José, 2026-08-30): el pinch de click
    # (indice+pulgar) se confundia con Shaka y disparaba LOCK_SESSION sin
    # querer. Ninguna de las 5 condiciones de arriba chequea la distancia
    # pulgar-indice - durante un pinch real el pulgar sube (pts[4].y<pts[2].y,
    # "extendido") y el menique a menudo queda relajado/extendido tambien,
    # cumpliendo las 5 por casualidad. Un Shaka genuino tiene el pulgar bien
    # separado del indice (apuntan en direcciones opuestas por construccion:
    # pulgar hacia arriba/costado, indice recogido hacia la palma) - un pinch
    # real, por definicion, los tiene juntos. Umbral razonado (no medido en
    # camara todavia): bien por encima del rango de pinch/ruido de mano
    # relajada documentado en config.py (maximo ~15.5px de indice sobre un
    # frame de 640px, ~0.024 normalizado) y bien por debajo de la separacion
    # esperable de un Shaka genuino.
    if math.hypot(pts[4].x - pts[8].x, pts[4].y - pts[8].y) < config.SHAKA_MIN_THUMB_INDEX_GAP:
        return False
    return (
        pts[20].y < pts[18].y
        and pts[4].y < pts[2].y
        and pts[8].y > pts[6].y
        and pts[12].y > pts[10].y
        and pts[16].y > pts[14].y
    )


def _extended_finger_count(pts):
    return sum(1 for i in (8, 12, 16, 20) if pts[i].y < pts[i - 2].y)


def _fingers_curled(pts, *tips):
    return all(pts[t].y > pts[t - 2].y for t in tips)


def _fingers_extended(pts, *tips):
    return all(pts[t].y < pts[t - 2].y for t in tips)


def _orientation(a, b, c):
    return (c.x - a.x) * (b.y - a.y) - (b.x - a.x) * (c.y - a.y)


def _segments_cross(p1, p2, p3, p4):
    """True si el segmento p1->p2 cruza geometricamente al segmento p3->p4
    (interseccion real, por orientacion/producto cruzado) - no solo si algun
    par de puntos quedo en un orden lateral distinto al esperado."""
    d1 = _orientation(p3, p4, p1)
    d2 = _orientation(p3, p4, p2)
    d3 = _orientation(p1, p2, p3)
    d4 = _orientation(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _fingers_crossed(pts, tip_a, mcp_a, tip_b, mcp_b):
    """True si el segmento MCP->punta de un dedo cruza geometricamente al del
    otro, DENTRO de una misma mano.

    Reemplaza una v1 que solo comparaba el ORDEN lateral de las 2 puntas
    contra el orden de los MCP - verificado en camara real (2026-08-27) que
    esa v1 daba falso positivo ~60-70% del tiempo con 2 dedos simplemente
    juntos/paralelos (Tora), porque el orden de las puntas se invierte con
    el ruido normal de landmark sin que los dedos esten realmente cruzados.
    Esta v2 exige que los 2 SEGMENTOS completos (nudillo a punta) se corten
    entre si - una condicion mucho mas especifica de un cruce real - medida
    en la misma sesion contra un intento genuino de Hitsuji: subio la
    confiabilidad de ~63% a un rango utilizable para sostener el hold."""
    return _segments_cross(pts[mcp_a], pts[tip_a], pts[mcp_b], pts[tip_b])


def _index_middle_extended_ring_pinky_curled(pts):
    return _fingers_extended(pts, 8, 12) and _fingers_curled(pts, 16, 20)


def _thumb_offset_from_palm(pts):
    """(dx lateral, dy "hacia arriba") del pulgar respecto al nudillo medio
    de la palma (landmark 9, referencia de centro de palma) - dy positivo
    significa el pulgar esta mas arriba que el centro de la palma. Separa
    "pulgar hacia arriba" de "pulgar hacia el costado" comparando cual eje
    domina, en vez de un solo chequeo vertical (ver `_is_naruto_i`/`_is_naruto_saru`)."""
    return pts[4].x - pts[9].x, pts[9].y - pts[4].y


# TASK-061/062 (Fase 4, `openspec/changes/personalization-and-config-ui`,
# design.md §4.1/§4.2): sellos Naruto de 1 mano. Censo de colision completo -
# incluyendo las 2 redefiniciones explicitas (Uma, Saru) - documentado en
# ARCHITECTURE.md. Tora/U/Hitsuji comparten la forma base "indice+medio
# extendidos, anular+menique recogidos" (identica a SCROLL) - se distinguen
# entre si y de SCROLL en `process()`, donde ya estan disponibles las
# distancias precalculadas (d_thumb_index, distancia indice-medio) y el
# chequeo de cruce de dedos; el resto de los sellos son formas propias sin
# ambiguedad, verificadas pura y unicamente por curvatura de dedos.
def _is_naruto_ushi(pts):
    # Ox: solo el indice extendido, pulgar recogido junto a los dedos (no
    # separado como en SCROLL - el pointer continuo tampoco es un chequeo
    # discreto, asi que no hay colision posible ahi, per design.md §4.1).
    return _fingers_extended(pts, 8) and _fingers_curled(pts, 12, 16, 20) and pts[4].y > pts[2].y


def _is_naruto_uma(pts):
    # Horse - REDEFINIDO POR SEGUNDA VEZ (verificado en camara real,
    # 2026-08-27): la v1 (design.md original: "las 5 extendidas y parejas")
    # colisionaba EXACTAMENTE con KEYBOARD_TOGGLE (apply.md §15). La v2
    # ("indice+medio+anular extendidos, menique recogido") pedia aislar el
    # anular junto al medio sin el menique - medido en vivo: 0% de
    # coincidencia, la mano real hizo naturalmente pulgar+indice+menique
    # extendidos con medio+anular recogidos (forma tipo "rock and roll") en
    # su lugar. Redefinido a esa forma, verificada como sostenible.
    return _fingers_extended(pts, 8, 20) and _fingers_curled(pts, 12, 16) and pts[4].y < pts[2].y


def _is_naruto_saru(pts):
    # Monkey - REDEFINIDO POR SEGUNDA VEZ (verificado en camara real,
    # 2026-08-27): la v1 (flag explicito de design.md: "pulgar+menique") ERA
    # la forma de `_is_shaka` (apply.md §15). La v2 ("pulgar+anular
    # extendidos") pedia aislar el anular solo - medido en vivo: 0% de
    # coincidencia, todos los dedos salieron extendidos (imposible aislar el
    # anular del medio/menique, comparten tendones). Redefinido a "pulgar
    # arriba": puño cerrado con el pulgar extendido HACIA ARRIBA (no hacia
    # el costado, eso es I/Boar) - distinguido de I por la DIRECCION del
    # pulgar (arriba vs costado, ver `_thumb_offset_from_palm`), no por su
    # curvatura simple.
    if not _fingers_curled(pts, 8, 12, 16, 20):
        return False
    dx, dy = _thumb_offset_from_palm(pts)
    return dy > 0.10 and dy > abs(dx)


def _is_naruto_inu(pts):
    # Dog - REDEFINIDO (verificado en camara real: la v1, "anular+menique
    # juntos extendidos", dio 0% de coincidencia - la mano quedo
    # completamente cerrada, aislar el anular sin el medio resulto
    # imposible). Redefinido a: solo el menique extendido (el menique SI
    # tiene un rango de movimiento independiente razonable, a diferencia del
    # anular), resto recogido.
    return _fingers_extended(pts, 20) and _fingers_curled(pts, 8, 12, 16) and pts[4].y > pts[2].y


def _is_naruto_i(pts):
    # Boar: puño cerrado con el pulgar extendido hacia el COSTADO (lateral),
    # no hacia arriba (eso es Saru, arriba) ni recogido.
    # FIX (verificado en camara real, 2026-08-27): la v1 media "extendido"
    # con el mismo chequeo vertical que el resto de los dedos (pts[4].y <
    # pts[2].y), pero "hacia el costado" es un movimiento LATERAL, no
    # vertical - ese chequeo nunca podia detectarlo (el pulgar real salio
    # "curvado" ~97% de las veces con esa metrica, incluso sostenido bien
    # hacia el costado). Ahora compara el desplazamiento lateral contra el
    # vertical (ver `_thumb_offset_from_palm`), igual que Saru pero
    # exigiendo que domine el eje contrario.
    # LIMITACION documentada (censo de colision, ver ARCHITECTURE.md):
    # `_is_fist()` no chequea el pulgar, asi que tanto esta forma como Saru
    # TAMBIEN cuentan como puño para la logica de 2 manos (fists[0] !=
    # fists[1]) - interaccion de fondo aceptada, no una ejecucion silenciosa
    # de una accion equivocada (arma el menu meta, no dispara nada solo).
    #
    # Umbral 0.15 (no 0.06): verificado contra `fist_hand()` (fixture de
    # puño generico reusado en todo este archivo, con el pulgar apenas
    # recogido a un costado por default, no deliberadamente extendido) -
    # con un umbral mas chico ese puño comun tambien calificaba como I por
    # accidente. 0.15 deja margen claro entre "pulgar apenas al costado de
    # un puño relajado" y "pulgar deliberadamente extendido hacia el costado".
    if not _fingers_curled(pts, 8, 12, 16, 20):
        return False
    dx, dy = _thumb_offset_from_palm(pts)
    return abs(dx) > 0.15 and abs(dx) > dy


# TASK-064/065 (Fase 5): sellos Naruto de 2 manos. design.md §5.1 advierte
# que el entrelazado fino de dedos entre 2 manos NO es detectable de forma
# confiable con los 21 puntos de MediaPipe (oclusion entre manos) y permite
# explicitamente usar un proxy mas grueso (§5.1: "both hands' centers within
# X distance, both hands' average finger curl above/below a threshold,
# relative hand orientation") - eso es lo que se usa aca, no un intento de
# replicar el entrelazado real punto por punto. Pendiente de verificar en
# camara real (a diferencia de la Fase 4, donde la primera version fallo en
# vivo la mayoria de las veces) - los umbrales son razonados, no medidos.
def _curl_ratio(pts):
    """Fraccion de los 4 dedos (no el pulgar) que leen como extendidos -
    0.0 = puño, 1.0 = mano abierta, valores intermedios = proxy de "a medio
    doblar/entrelazado"."""
    return _extended_finger_count(pts) / 4.0


def _hand_center(pts, w, h):
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (sum(xs) / len(xs)) * w, (sum(ys) / len(ys)) * h


def _hands_distance(p1, p2, w, h):
    c1x, c1y = _hand_center(p1, w, h)
    c2x, c2y = _hand_center(p2, w, h)
    return math.hypot(c2x - c1x, c2y - c1y)


def _hand_points_up(pts):
    avg_tip_y = sum(pts[t].y for t in (8, 12, 16, 20)) / 4
    return avg_tip_y < pts[0].y - 0.05


def _hand_points_down(pts):
    avg_tip_y = sum(pts[t].y for t in (8, 12, 16, 20)) / 4
    return avg_tip_y > pts[0].y + 0.05


# TASK-068 (Fase 6): JJK_GOJO_DOMAIN (2 manos, estatico, Pattern B per
# design.md §1.5 - la condicion es el angulo/posicion ENTRE las 2 manos, no
# 2 formas de una sola mano clasificadas por separado) y JJK_MEGUMI (1 mano,
# estatico). Umbrales razonados, no medidos - misma salvedad que Fase 5,
# pendiente de la prueba integral final (posposicion pedida explicitamente).
def _thumb_index_angle_deg(pts):
    """Angulo (0-180) entre el vector pulgar (MCP->punta) y el vector indice
    (MCP->punta) de una mano - la 'L' del marco de Gojo es ~90 grados."""
    tx, ty = pts[4].x - pts[2].x, pts[4].y - pts[2].y
    ix, iy = pts[8].x - pts[5].x, pts[8].y - pts[5].y
    mag_t, mag_i = math.hypot(tx, ty), math.hypot(ix, iy)
    if mag_t == 0 or mag_i == 0:
        return 0.0
    cos_angle = max(-1.0, min(1.0, (tx * ix + ty * iy) / (mag_t * mag_i)))
    return math.degrees(math.acos(cos_angle))


def _is_jjk_gojo_domain(p1, p2, w, h):
    angle1 = _thumb_index_angle_deg(p1)
    angle2 = _thumb_index_angle_deg(p2)
    l_shaped = (
        abs(angle1 - 90) <= config.JJK_GOJO_ANGLE_TOLERANCE_DEGREES
        and abs(angle2 - 90) <= config.JJK_GOJO_ANGLE_TOLERANCE_DEGREES
    )
    if not l_shaped:
        return False
    close = (_hands_distance(p1, p2, w, h) / math.hypot(w, h)) <= config.JJK_GOJO_MAX_DISTANCE_FRACTION
    raised = (p1[0].y + p2[0].y) / 2 < config.JJK_GOJO_MAX_AVG_WRIST_Y
    return close and raised


def _is_jjk_megumi(pts):
    # Invocacion de las sombras - familia visual de Hitsuji (indice+medio
    # cruzados) pero distinguida EXPLICITAMENTE por la posicion del anular
    # (extendido, no recogido) per design.md §6.3 - no puede colisionar con
    # la forma base de Tora/U/Hitsuji, que exige el anular recogido.
    if not (_fingers_extended(pts, 8, 12, 16) and _fingers_curled(pts, 20)):
        return False
    return _fingers_crossed(pts, 8, 5, 12, 9)


# TASK-071 (Fase 7): CLAP. design.md §7.1 pide el centro de PALMA (promedio
# de landmarks 0/5/9/13/17), no el centro de los 21 puntos (`_hand_center`,
# usado por los sellos de 2 manos) ni el punto medio de pellizco (usado por
# el zoom de 2 manos) - 3 nociones de "centro de mano" distintas, cada una
# ya en uso por un gesto distinto de este archivo.
def _palm_center(pts, w, h):
    idx = (0, 5, 9, 13, 17)
    xs = [pts[i].x for i in idx]
    ys = [pts[i].y for i in idx]
    return (sum(xs) / len(xs)) * w, (sum(ys) / len(ys)) * h


def _palm_centers_distance(p1, p2, w, h):
    c1x, c1y = _palm_center(p1, w, h)
    c2x, c2y = _palm_center(p2, w, h)
    return math.hypot(c2x - c1x, c2y - c1y)


def _bbox_area_fraction(landmarks, w, h):
    xs = [p.x for p in landmarks]
    ys = [p.y for p in landmarks]
    bbox_w = (max(xs) - min(xs)) * w
    bbox_h = (max(ys) - min(ys)) * h
    return (bbox_w * bbox_h) / (w * h)


def filter_plausible_hands(hands, w, h):
    """TASK-056: descarta manos cuyo bounding box es demasiado chico para ser
    la mano del usuario a distancia normal de escritorio (persona u objeto de
    fondo, mas lejos de la camara - ver config.py para la medicion real que
    justifica el umbral). Corre una vez por frame antes de toda logica de
    gestos, de 1 o 2 manos. Si quedan mas de 2 plausibles se queda con las 2
    mas grandes (HandLandmarker ya limita a config.MAX_HANDS, esto deja el
    criterio explicito sin depender de eso)."""
    plausible = [hand for hand in hands if _bbox_area_fraction(hand.landmarks, w, h) >= config.MIN_HAND_AREA_FRACTION]
    plausible.sort(key=lambda hand: _bbox_area_fraction(hand.landmarks, w, h), reverse=True)
    return plausible[:2]


def hands_plausibly_same_person(h1, h2, w, h):
    """TASK-056: especifico para elegibilidad de gestos de 2 manos (no de
    elegibilidad de mano primaria/puntero, que puede seguir usando la mas
    grande/plausible sola). Rechaza el par si los centros de ambas manos
    estan demasiado lejos entre si en el frame, relativo a la diagonal -
    las 2 manos de una misma persona en uso normal de escritorio quedan bien
    por debajo del umbral (medido en camara real, ver config.py); una
    segunda persona de fondo con una mano de tamano similar tipicamente no."""

    def _center(landmarks):
        xs = [p.x for p in landmarks]
        ys = [p.y for p in landmarks]
        return (sum(xs) / len(xs)) * w, (sum(ys) / len(ys)) * h

    c1x, c1y = _center(h1.landmarks)
    c2x, c2y = _center(h2.landmarks)
    frame_diag = math.hypot(w, h)
    return math.hypot(c2x - c1x, c2y - c1y) <= config.TWO_HAND_MAX_CENTER_DISTANCE_FRACTION * frame_diag


class GestureEngine:
    def __init__(self, smoothing_enabled=True):
        self.active = True
        self.smoothing_enabled = smoothing_enabled  # TASK-018: spec.md #7 "smoothing.enabled"

        self.prev_x, self.prev_y = 0, 0
        self.was_pinching = False
        self.was_right_pinching = False
        # TASK: rediseño de scroll (hallazgo de camara real, José, 2026-08-30:
        # "arriba/abajo se confunde"). Antes: delta cuadro-a-cuadro de
        # index.y (habia que seguir moviendo la mano para seguir scrolleando,
        # y un solo cuadro de temblor invertia el signo). Ahora: posicion
        # "base" (donde el usuario levanto la mano por primera vez en esta
        # forma) fijada al entrar al gesto - la direccion sale de cuanto se
        # aleja la punta del indice de esa base, no de un delta instantaneo.
        self.scroll_baseline = None  # (x, y) normalizado, o None si el gesto no esta activo
        self.prev_zoom_y = None
        self.prev_pinky_y = None
        self.lock_start_time = None
        self.last_click_time = 0.0
        self.last_right_click_time = 0.0
        self.last_screenshot_time = 0.0
        self.last_toggle_time = 0.0
        self.last_silence_time = 0.0

        # Cuantos frames seguidos lleva cada dedo por debajo de su umbral de pinch -
        # confirmado (config.PINCH_CONFIRM_FRAMES) recien entra a competir por
        # pinch_winner. Absorbe el ruido de un solo frame (mano relajada moviendose
        # cerca del umbral, medido en camara real - ver config.py).
        self._pinch_streak = {"index": 0, "middle": 0, "ring": 0, "pinky": 0}

        self.pause_hold_start = None
        self.close_hold_start = None
        self.prev_two_hand_pinch_dist = None
        self.meta_pose = None
        self.meta_hold_start = None
        self.meta_consumed = False

        self._primary_pos = None  # (x, y) normalizado del indice de la ultima mano "activa"
        self.last_primary_landmarks = None  # TASK-057: para que hand_visualizer distinga mano primaria

        self._naruto_hold_seal = None  # TASK-062: que sello se esta sosteniendo ahora (o None)
        self._naruto_hold_start = None
        self._naruto_miss_streak = 0  # frames seguidos sin match mientras se sostenia un sello

        self._twohand_seal_hold_name = None  # TASK-064/065: sello de 2 manos sostenido ahora (o None)
        self._twohand_seal_hold_start = None
        self._twohand_seal_miss_streak = 0

        # TASK-069 (Fase 6): snap de Sukuna - primer uso de ImpulseDetector,
        # alimentado con d_thumb_middle SIN el gate de pinch_winner (necesita
        # ver la distancia real cuadro a cuadro para reconocer el patron
        # baja-sube; el propio detector ya distingue un snap de un hold
        # sostenido, ver temporal_gesture.py).
        self._sukuna_detector = ImpulseDetector(
            config.JJK_SUKUNA_CONTACT_THRESHOLD,
            config.JJK_SUKUNA_RELEASE_THRESHOLD,
            config.JJK_SUKUNA_MAX_WINDOW_SECONDS,
        )

        # TASK-071 (Fase 7): CLAP - segunda instancia de ImpulseDetector
        # (design.md §7.1 pide explicitamente reusar el primitivo, no
        # reimplementarlo), sobre la distancia entre centros de PALMA
        # (fraccion de la diagonal del frame, mismas unidades que los
        # umbrales de 2 manos existentes).
        self._clap_detector = ImpulseDetector(
            config.CLAP_CONTACT_MAX_DISTANCE_FRACTION,
            config.CLAP_RELEASE_MIN_DISTANCE_FRACTION,
            config.CLAP_MAX_WINDOW_SECONDS,
        )

        self._korean_heart_hold_start = None  # TASK-072: mismo mecanismo que LOCK_SESSION

    @staticmethod
    def _dist(p1, p2, w, h):
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h)

    @staticmethod
    def _dist3(p1, p2, w, h):
        # TASK-055c: distancia real en 3D (no solo proyectada en pantalla) para
        # los pinch pulgar-dedo. z de MediaPipe ya viene normalizado a ~la misma
        # escala que x (relativo a la muñeca), asi que reusar `w` para escalarlo
        # es consistente con como ya se escala x - sin calibracion extra. Dos
        # puntos cerca en (x, y) pero lejos en z NO estan realmente tocandose;
        # la distancia 2D no puede distinguir eso.
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h, (p1.z - p2.z) * w)

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
        """Gestos a 2 manos. Devuelve (events, suppress_single_hand_pinch, both_shaka,
        two_hand_active). two_hand_active (TASK-055b) es la condicion geometrica cruda
        de CUALQUIER gesto de 2 manos (shaka/punos/pinch-zoom/menu meta) - no si ese
        gesto ya disparo su evento (algunos requieren sostenerlo) - para que quien
        llama pueda suprimir los 9 chequeos de 1 mano que hoy corren igual sobre la
        mano "primaria" sin importar que este haciendo la otra (ver design.md TASK-055b:
        antes solo LOCK_SESSION/PINCH_DOWN estaban protegidos, con su propia condicion
        angosta - esta queda igual sin tocar, two_hand_active es la version general
        nueva para los 7 chequeos que no tenian ninguna proteccion)."""
        events = []
        # TASK-056: ademas de requerir exactamente 2 manos, exige que sean
        # plausiblemente de la misma persona (§1.2/§3B). Si no, cada mano
        # sigue siendo elegible individualmente como primaria mas abajo -
        # solo se descarta tratarlas como UN gesto conjunto de 2 manos.
        if len(hands) != 2 or not hands_plausibly_same_person(hands[0], hands[1], w, h):
            self.pause_hold_start = None
            self.close_hold_start = None
            self.prev_two_hand_pinch_dist = None
            self.meta_pose = None
            self.meta_hold_start = None
            self.meta_consumed = False
            self._twohand_seal_hold_name = None
            self._twohand_seal_hold_start = None
            self._twohand_seal_miss_streak = 0
            return events, False, False, False

        p1, p2 = hands[0].landmarks, hands[1].landmarks
        both_shaka = _is_shaka(p1) and _is_shaka(p2)
        both_fists = _is_fist(p1) and _is_fist(p2)

        # TASK-071 (Fase 7): CLAP. Alimentado SIN gate (mismo motivo que
        # Sukuna - el detector necesita la distancia real cuadro a cuadro
        # para su maquina de estados); el EVENTO se emite mas abajo, una vez
        # conocida la jerarquia completa de gestos de 2 manos.
        _clap_dist_frac = _palm_centers_distance(p1, p2, w, h) / math.hypot(w, h)
        _clap_fired = self._clap_detector.update(_clap_dist_frac, now)

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

        # TASK-064/065 (Fase 5) + TASK-068 (Fase 6): sellos de 2 manos.
        # Excluidos si ya es otro gesto de 2 manos conocido (shaka/puños/
        # pinch) - jerarquia, no solapamiento. Orden de chequeo: Kai (mas
        # especifico, exige cruce real de dedos) -> Tatsu (asimetria de
        # curvatura) -> Ne/Mi (mismo "entrelazado" proxy, distinguidos por
        # orientacion) -> Tori (separadas y mas abiertas) -> Gojo (unica
        # familia geometrica distinta: angulo pulgar-indice, no
        # distancia/curvatura, chequeada al final para no competir con las
        # anteriores). `_twohand_seal` guarda el EVENTO completo (con
        # prefijo) para que el mismo hold-state-machine sirva para ambos
        # namespaces sin duplicar logica.
        _twohand_seal = None
        if not both_shaka and not both_fists and not both_pinching:
            dist_frac = _hands_distance(p1, p2, w, h) / math.hypot(w, h)
            ratio1, ratio2 = _curl_ratio(p1), _curl_ratio(p2)
            clasped = dist_frac <= config.NARUTO_TWOHAND_CLASP_MAX_DISTANCE_FRACTION
            fanned = (
                config.NARUTO_TWOHAND_FAN_MIN_DISTANCE_FRACTION
                < dist_frac
                <= config.NARUTO_TWOHAND_FAN_MAX_DISTANCE_FRACTION
            )
            interlaced = 0.2 <= ratio1 <= 0.8 and 0.2 <= ratio2 <= 0.8
            asymmetric = abs(_extended_finger_count(p1) - _extended_finger_count(p2)) >= 2
            kai_crossed = (
                _fingers_extended(p1, 8, 12)
                and _fingers_extended(p2, 8, 12)
                and (_segments_cross(p1[5], p1[8], p2[5], p2[8]) or _segments_cross(p1[9], p1[12], p2[9], p2[12]))
            )

            if clasped and kai_crossed:
                _twohand_seal = "NARUTO_KAI"
            elif clasped and asymmetric:
                _twohand_seal = "NARUTO_TATSU"
            elif clasped and interlaced and _hand_points_up(p1) and _hand_points_up(p2):
                _twohand_seal = "NARUTO_NE"
            elif clasped and interlaced and _hand_points_down(p1) and _hand_points_down(p2):
                _twohand_seal = "NARUTO_MI"
            elif fanned and ratio1 >= 0.75 and ratio2 >= 0.75:
                _twohand_seal = "NARUTO_TORI"
            elif _is_jjk_gojo_domain(p1, p2, w, h):
                _twohand_seal = "JJK_GOJO_DOMAIN"

        if _twohand_seal is not None:
            if self._twohand_seal_hold_name != _twohand_seal:
                self._twohand_seal_hold_name = _twohand_seal
                self._twohand_seal_hold_start = now
            elif self._twohand_seal_hold_start is None:
                self._twohand_seal_hold_start = now
            elif now - self._twohand_seal_hold_start > config.NARUTO_TWOHAND_HOLD_SECONDS:
                events.append(_twohand_seal)
                self._twohand_seal_hold_start = None
            self._twohand_seal_miss_streak = 0
        elif self._twohand_seal_hold_name is not None:
            self._twohand_seal_miss_streak += 1
            if self._twohand_seal_miss_streak > config.NARUTO_SEAL_MISS_TOLERANCE:
                self._twohand_seal_hold_name = None
                self._twohand_seal_hold_start = None
                self._twohand_seal_miss_streak = 0

        # CLAP se emite recien aca, una vez conocida la jerarquia completa de
        # gestos de 2 manos (Naruto/JJK/shaka/puños/pinch-zoom ya excluidos -
        # jerarquia, no solapamiento, mismo principio que el resto del
        # archivo). El detector ya se alimento arriba sin este gate.
        _clap_happened = _clap_fired and _twohand_seal is None and not both_shaka and not both_fists and not both_pinching
        if _clap_happened:
            events.append("CLAP")

        two_hand_active = (
            both_shaka
            or both_fists
            or both_pinching
            or (fists[0] != fists[1])
            or _twohand_seal is not None
            or _clap_happened
        )
        return events, both_pinching, both_shaka, two_hand_active

    def process(self, hands, w, h, screen_w, screen_h):
        """Devuelve (screen_xy, cam_xy, events). screen_xy/cam_xy son None si no hay
        puntero que mover (sin manos, o lectura de gestos en pausa)."""
        now = time.time()
        # TASK-056: filtro de manos implausibles (fondo/otra persona) antes de
        # CUALQUIER logica de gestos, de 1 o 2 manos - ver design.md §1.2.
        hands = filter_plausible_hands(hands, w, h)
        events, suppress_pinch, both_shaka, two_hand_active = self._process_two_hand_gestures(hands, w, h, now)

        if not self.active or not hands:
            self.last_primary_landmarks = None
            return None, None, events

        pts = self._pick_primary(hands)
        self.last_primary_landmarks = pts
        thumb, index, middle, ring, pinky = pts[4], pts[8], pts[12], pts[16], pts[20]

        raw_x = _interp(index.x, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_w)
        raw_y = _interp(index.y, config.POINTER_MARGIN, 1 - config.POINTER_MARGIN, 0, screen_h)
        screen_xy = self._smooth(raw_x, raw_y)
        cam_xy = (int(index.x * w), int(index.y * h))
        self._primary_pos = (index.x, index.y)

        d_thumb_index = self._dist3(thumb, index, w, h)
        d_thumb_middle = self._dist3(thumb, middle, w, h)
        d_thumb_ring = self._dist3(thumb, ring, w, h)
        d_thumb_pinky = self._dist3(thumb, pinky, w, h)
        d_thumb_pinky_mcp = self._dist(thumb, pts[17], w, h)  # SILENCE - no es pinch-family, queda 2D

        # TASK-069 (Fase 6): snap de Sukuna. Se alimenta con d_thumb_middle
        # SIN el gate de pinch_winner/two_hand_active (el detector necesita
        # la distancia real cuadro a cuadro para reconocer el patron
        # baja-sube; alimentarlo a medias romperia su maquina de estados).
        # Riesgo de colision CONOCIDO Y NO VERIFICADO (documentado, no
        # resuelto): un snap real pasa primero por PINCH_RIGHT_CLICK (20px,
        # mas laxo que el umbral de contacto de Sukuna, 15px) camino al
        # contacto mas ajustado - RIGHT_CLICK podria disparar en el mismo
        # gesto fisico. Pendiente de la prueba integral final (posposicion
        # pedida explicitamente, ver ARCHITECTURE.md).
        if self._sukuna_detector.update(d_thumb_middle, now) and not two_hand_active:
            events.append("JJK_SUKUNA")

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
        # TASK-055/1.5 (medido en camara real, ver config.py): un solo frame bajo el
        # umbral no alcanza - un pinch recien "confirma" tras PINCH_CONFIRM_FRAMES
        # frames seguidos, para no reaccionar al ruido de la mano relajada pasando
        # cerca del umbral en un movimiento normal.
        for _name, _dist, _threshold in _pinch_candidates:
            if _dist < _threshold:
                self._pinch_streak[_name] = min(self._pinch_streak[_name] + 1, config.PINCH_CONFIRM_FRAMES)
            else:
                self._pinch_streak[_name] = 0
        _active_pinches = [
            (name, dist)
            for name, dist, threshold in _pinch_candidates
            if dist < threshold and self._pinch_streak[name] >= config.PINCH_CONFIRM_FRAMES
        ]
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
        # TASK-055b: suprimidos mientras la otra mano esta en un gesto de 2 manos -
        # antes corrian igual sobre la mano "primaria" sin importar la otra mano.
        if not two_hand_active and fingers_extended and d_thumb_pinky_mcp < config.SILENCE_TUCK_MAX:
            if now - self.last_silence_time > config.SILENCE_COOLDOWN:
                events.append("SILENCE")
                self.last_silence_time = now
        elif not two_hand_active and fingers_extended and d_thumb_index > config.PALM_OPEN_MIN_SPREAD:
            if now - self.last_toggle_time > config.KEYBOARD_TOGGLE_COOLDOWN:
                events.append("KEYBOARD_TOGGLE")
                self.last_toggle_time = now

        # Screenshot: pulgar+anular pinch con índice y meñique recogidos
        screenshot_pinch = not two_hand_active and pinch_winner == "ring" and d_thumb_ring < config.PINCH_SCREENSHOT
        if screenshot_pinch and index.y > pts[6].y and pinky.y > pts[18].y:
            if now - self.last_screenshot_time > config.SCREENSHOT_COOLDOWN:
                events.append("SCREENSHOT")
                self.last_screenshot_time = now

        # Zoom: pulgar+anular pinch con índice extendido, dirección por movimiento vertical del anular
        elif not two_hand_active and pinch_winner == "ring" and d_thumb_ring < config.PINCH_ZOOM and index.y < pts[6].y:
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
        if not two_hand_active and pinch_winner == "pinky" and d_thumb_pinky < config.PINCH_VOLUME:
            if self.prev_pinky_y is not None:
                delta = self.prev_pinky_y - pinky.y
                if delta > config.VOLUME_DELTA_THRESHOLD:
                    events.append("VOLUME_UP")
                elif delta < -config.VOLUME_DELTA_THRESHOLD:
                    events.append("VOLUME_DOWN")
            self.prev_pinky_y = pinky.y
        else:
            self.prev_pinky_y = None

        # Scroll: índice+medio juntos extendidos, resto de los dedos recogidos
        # (anular Y meñique, no solo anular - pedido explícito para no
        # confundirse con otros gestos que solo recogen el anular), pulgar
        # separado del índice - forma sin cambios, pedida explícitamente así
        # (hallazgo de cámara real, José, 2026-08-30).
        #
        # Dirección REDISEÑADA (mismo hallazgo: "arriba/abajo se confunde,
        # que el movimiento indique el scroll... señalar hacia arriba,
        # scroll arriba... hacia abajo, scroll abajo, mismo comportamiento
        # para izquierda/derecha"). Antes: delta cuadro-a-cuadro de index.y -
        # solo scrolleaba mientras la mano seguía en movimiento activo, y un
        # solo cuadro de temblor podía invertir el signo. Ahora: se fija una
        # posición "base" en el primer cuadro que se entra a esta forma
        # (donde el usuario levantó la mano), y la dirección sale de hacia
        # dónde se alejó la punta del índice desde esa base - sostenido, no
        # instantáneo (como un joystick: alejarse de la base y mantenerse
        # ahí sigue scrolleando, un solo cuadro de temblor ya no invierte
        # nada). El eje dominante (el de mayor desplazamiento) decide
        # vertical vs horizontal, así un movimiento mayormente vertical
        # nunca dispara scroll horizontal de paso y viceversa. Umbral
        # razonado, no medido en cámara todavía.
        if (
            not two_hand_active
            and index.y < pts[6].y
            and middle.y < pts[10].y
            and ring.y > pts[14].y
            and pinky.y > pts[18].y
            and d_thumb_index > 40
        ):
            if self.scroll_baseline is None:
                self.scroll_baseline = (index.x, index.y)
            else:
                base_x, base_y = self.scroll_baseline
                dx = index.x - base_x
                dy = base_y - index.y  # positivo = el indice subio respecto a la base
                if abs(dy) >= abs(dx):
                    if dy > config.SCROLL_DIRECTION_THRESHOLD:
                        events.append("SCROLL_UP")
                    elif dy < -config.SCROLL_DIRECTION_THRESHOLD:
                        events.append("SCROLL_DOWN")
                else:
                    if dx > config.SCROLL_DIRECTION_THRESHOLD:
                        events.append("SCROLL_RIGHT")
                    elif dx < -config.SCROLL_DIRECTION_THRESHOLD:
                        events.append("SCROLL_LEFT")
        else:
            self.scroll_baseline = None

        # TASK-062 (Fase 4) + TASK-068 (Fase 6): sellos de 1 mano. Todos
        # exigen ningun pinch activo (pinch_winner is None - asi cualquier
        # forma que accidentalmente quede lo bastante cerca de un dedo como
        # para pellizcar pierde contra el pinch, nunca dispara ambos) y que
        # no haya un gesto de 2 manos en curso - ver censo de colision
        # completo en ARCHITECTURE.md. `_naruto_seal` guarda el EVENTO
        # completo (con prefijo NARUTO_/JJK_) para que el mismo
        # hold-state-machine sirva para ambos namespaces sin duplicar logica
        # (mismo truco que el bloque de 2 manos, ver arriba).
        _naruto_gate = pinch_winner is None and not two_hand_active
        _naruto_seal = None
        if _naruto_gate:
            if _index_middle_extended_ring_pinky_curled(pts):
                # Tora/U/Hitsuji comparten esta base (identica a SCROLL) -
                # se distinguen por cruce de dedos, separacion indice-medio,
                # y posicion del pulgar (igual o menor a 40px = "junto a la
                # mano", el complemento exacto del ">40" que ya exige SCROLL
                # - sin tocar la condicion de SCROLL en absoluto).
                d_index_middle = self._dist3(index, middle, w, h)
                crossed = _fingers_crossed(pts, 8, 5, 12, 9)
                if d_thumb_index <= 40:
                    if crossed:
                        _naruto_seal = "NARUTO_HITSUJI"
                    elif d_index_middle < 30:
                        _naruto_seal = "NARUTO_TORA"
                    elif d_index_middle > 50:
                        _naruto_seal = "NARUTO_U"
            elif _is_naruto_ushi(pts):
                _naruto_seal = "NARUTO_USHI"
            elif _is_naruto_uma(pts):
                _naruto_seal = "NARUTO_UMA"
            elif _is_naruto_saru(pts):
                _naruto_seal = "NARUTO_SARU"
            elif _is_naruto_inu(pts):
                _naruto_seal = "NARUTO_INU"
            elif _is_naruto_i(pts):
                _naruto_seal = "NARUTO_I"
            elif _is_jjk_megumi(pts):
                _naruto_seal = "JJK_MEGUMI"

        # TASK-062 fix (verificado en camara real, 2026-08-27): un solo
        # frame de parpadeo a "ningun sello" (ruido de landmark, no un
        # cambio real de pose) ya no reinicia el hold entero -
        # NARUTO_SEAL_MISS_TOLERANCE frames de gracia antes de tirar el
        # progreso, mismo principio que PINCH_CONFIRM_FRAMES pero para no
        # PERDER una confirmacion en curso en vez de para no adelantarla.
        if _naruto_seal is not None:
            if self._naruto_hold_seal != _naruto_seal:
                self._naruto_hold_seal = _naruto_seal
                self._naruto_hold_start = now
            elif self._naruto_hold_start is None:
                self._naruto_hold_start = now
            elif now - self._naruto_hold_start > config.NARUTO_SEAL_HOLD_SECONDS:
                events.append(_naruto_seal)
                self._naruto_hold_start = None
            self._naruto_miss_streak = 0
        elif self._naruto_hold_seal is not None:
            self._naruto_miss_streak += 1
            if self._naruto_miss_streak > config.NARUTO_SEAL_MISS_TOLERANCE:
                self._naruto_hold_seal = None
                self._naruto_hold_start = None
                self._naruto_miss_streak = 0

        # TASK-072 (Fase 7): Korean finger heart. Pulgar cerca del PRIMER
        # nudillo del indice (landmark 6), NO de la punta (eso ya es
        # PINCH_CLICK, d_thumb_index) - la distincion geometrica que
        # design.md §7.2 pide, y lo que hace que esta forma nunca pueda
        # ganar pinch_winner=="index" (`d_thumb_index >= PINCH_CLICK` es
        # estructuralmente incompatible con el umbral de PINCH_CLICK).
        # `_fingers_curled(pts, 8, 12, 16, 20)` se agrego DESPUES de que el
        # test de colision encontrara que silence_hand() (pulgar y primer
        # nudillo del indice coincidentes por construccion, sin relacion
        # alguna con este gesto) satisfacia igual las 2 condiciones de
        # arriba - SILENCE exige los 4 dedos extendidos, este gesto es un
        # puno con solo el pulgar cruzado, asi que la curvatura los separa
        # estructuralmente (mismo tipo de hallazgo que el de `fist_hand()` en
        # la Fase 4, ver ARCHITECTURE.md). Sostenido (no edge-triggered como
        # PINCH_DOWN) para que un toque-y-suelta rapido nunca resuelva a
        # KOREAN_HEART - mismo mecanismo que LOCK_SESSION/Shaka.
        d_thumb_index_pip = self._dist3(thumb, pts[6], w, h)
        korean_heart_shape = (
            pinch_winner is None
            and not two_hand_active
            and d_thumb_index_pip < config.KOREAN_HEART_CONTACT_THRESHOLD
            and d_thumb_index >= config.PINCH_CLICK
            and _fingers_curled(pts, 8, 12, 16, 20)
        )
        if korean_heart_shape:
            if self._korean_heart_hold_start is None:
                self._korean_heart_hold_start = now
            elif now - self._korean_heart_hold_start > config.KOREAN_HEART_HOLD_SECONDS:
                events.append("KOREAN_HEART")
                self._korean_heart_hold_start = None
        else:
            self._korean_heart_hold_start = None

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
        is_right_pinching = (
            not two_hand_active and pinch_winner == "middle" and d_thumb_middle < config.PINCH_RIGHT_CLICK
        )
        if (
            is_right_pinching
            and not self.was_right_pinching
            and now - self.last_right_click_time > config.RIGHT_CLICK_COOLDOWN
        ):
            events.append("RIGHT_CLICK")
            self.last_right_click_time = now
        self.was_right_pinching = is_right_pinching

        return screen_xy, cam_xy, events
