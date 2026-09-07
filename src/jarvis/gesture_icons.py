"""TASK-058 (Fase 3, `openspec/changes/personalization-and-config-ui`,
spec.md #3.1-3.2): iconos de referencia generados proceduralmente (nada de
binarios dibujados a mano commiteados) para cada entrada de la leyenda de
gestos - un glifo de mano estilizado (palma + dedos extendidos/curvados,
1 o 2 manos) mas un pequeño glifo de accion cuando aplica.

Dibujado con `PIL.Image`/`PIL.ImageDraw` (dependencia nueva: Pillow, agregada
a requirements.txt) - se muestra despues via `tkinter.PhotoImage(file=...)`,
sin necesitar `PIL.ImageTk`.
"""

import logging
import math
import os

from PIL import Image, ImageDraw, ImageFont

from jarvis.paths import writable_assets_dir

_logger = logging.getLogger("jarvis.gesture_icons")

ICON_SIZE = 48

# Puntos base/punta (extendido y curvado) de cada dedo en un lienzo de 48x48,
# para UNA mano centrada en la mitad izquierda o derecha del canvas segun
# donde se dibuje (ver _draw_hand). Coordenadas relativas a esa mitad.
_FINGER_POINTS = {
    "thumb": {"base": (14, 30), "extended": (5, 21), "curled": (11, 26)},
    "index": {"base": (16, 23), "extended": (13, 5), "curled": (14, 17)},
    "middle": {"base": (22, 21), "extended": (22, 3), "curled": (22, 15)},
    "ring": {"base": (28, 21), "extended": (30, 5), "curled": (28, 16)},
    "pinky": {"base": (33, 24), "extended": (38, 9), "curled": (33, 19)},
}
_ALL_FINGERS = tuple(_FINGER_POINTS)

_EXTENDED_COLOR = (20, 20, 20, 255)
_CURLED_COLOR = (170, 170, 170, 255)
_PALM_COLOR = (60, 60, 60, 255)
_PINCH_COLOR = (220, 40, 40, 255)
_GLYPH_COLOR = (30, 90, 200, 255)
_KEY_COLOR = (30, 30, 30, 255)


# ICON_SPECS: declarativo, una entrada por cada key de icono.
#   hands: 0 (solo tecla, sin mano), 1, o 2.
#   extended: (solo si hands >= 1) set de dedos extendidos de la mano 1, o
#       (set_mano1, set_mano2) si hands == 2 - el resto se dibuja curvado.
#   pinch: None, o un par de nombres de dedo cuyas puntas se marcan como en
#       contacto (mano 1 unicamente - ningun gesto de esta app pellizca con
#       la mano 2 por separado del gesto conjunto).
#   glyph: None, o uno de GLYPH_DRAWERS - una insignia chica de accion.
#   key_label: (solo si hands == 0) el texto corto de la tecla (ASCII, sin
#       acentos - una sola letra o simbolo, evita el problema de fuentes con
#       ñ/acentos que ya tiene cv2.putText en este proyecto, ver ARCHITECTURE.md).
ICON_SPECS = {
    "pointer": {"hands": 1, "extended": {"index"}, "pinch": None, "glyph": None},
    "pinch_click": {"hands": 1, "extended": {"thumb", "index"}, "pinch": ("thumb", "index"), "glyph": None},
    "pinch_right_click": {
        "hands": 1,
        "extended": {"thumb", "middle"},
        "pinch": ("thumb", "middle"),
        "glyph": None,
    },
    "scroll": {"hands": 1, "extended": {"index", "middle"}, "pinch": None, "glyph": "arrow_up_down"},
    "pinch_zoom": {"hands": 1, "extended": {"thumb", "index", "ring"}, "pinch": ("thumb", "ring"), "glyph": "zoom"},
    "open_palm_keyboard": {
        "hands": 1,
        "extended": {"index", "middle", "ring", "pinky"},
        "pinch": None,
        "glyph": "keyboard",
    },
    "pinch_volume": {
        "hands": 1,
        "extended": {"thumb", "pinky"},
        "pinch": ("thumb", "pinky"),
        "glyph": "arrow_up_down",
    },
    "pinch_screenshot": {"hands": 1, "extended": {"thumb", "ring"}, "pinch": ("thumb", "ring"), "glyph": "camera"},
    "shaka_lock": {"hands": 1, "extended": {"thumb", "pinky"}, "pinch": None, "glyph": "lock"},
    "silence": {"hands": 1, "extended": {"index", "middle", "ring", "pinky"}, "pinch": None, "glyph": "mute"},
    "two_fist_pause": {"hands": 2, "extended": (set(), set()), "pinch": None, "glyph": "pause"},
    "two_shaka_close": {
        "hands": 2,
        "extended": ({"thumb", "pinky"}, {"thumb", "pinky"}),
        "pinch": None,
        "glyph": "close",
    },
    "key_quit": {"hands": 0, "key_label": "Q"},
    "key_toggle_legend": {"hands": 0, "key_label": "H"},
    "key_mirror": {"hands": 0, "key_label": "M"},
    "key_legend_opacity": {"hands": 0, "key_label": "+/-"},
    # Y-05 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md`): los 12 sellos
    # reales son todos de 2 MANOS (AUDIT.md) - estos 8 pasan de hands=1 a
    # hands=2 (duplicando el mismo set de dedos en ambas manos). El modelo de
    # icono no representa manos entrelazadas ni su forma real (fotografiada en
    # docs/gesture-reference/canonical/), asi que varios quedan parecidos
    # entre si - se distinguen por el glyph, mismo criterio ya aceptado para
    # naruto_ne/naruto_mi mas abajo.
    "naruto_tora": {
        "hands": 2,
        "extended": ({"index", "middle"}, {"index", "middle"}),
        "pinch": ("index", "middle"),
        "glyph": "camera",
    },
    "naruto_ushi": {"hands": 2, "extended": ({"index"}, {"index"}), "pinch": None, "glyph": "pause"},
    # naruto_u tenia el mismo set de dedos Y glyph=None que naruto_ne mas
    # abajo - dos specs byte-por-byte identicas, confirmado por
    # test_every_icon_is_structurally_distinct_from_every_other (CI, sin cache
    # local de assets/gesture_icons/, lo detecto; el cache local viejo de este
    # repo lo enmascaraba). NARUTO_U -> REDO (main.py): "arrow_right" como
    # adelante/rehacer, mismo criterio que Saru/I (glyph = tema de su propia
    # accion default).
    "naruto_u": {
        "hands": 2,
        "extended": ({"index", "middle"}, {"index", "middle"}),
        "pinch": None,
        "glyph": "arrow_right",
    },
    "naruto_uma": {
        "hands": 2,
        "extended": ({"thumb", "index", "pinky"}, {"thumb", "index", "pinky"}),
        "pinch": None,
        "glyph": "zoom",
    },
    "naruto_hitsuji": {
        "hands": 2,
        "extended": ({"index", "middle"}, {"index", "middle"}),
        "pinch": None,
        "glyph": "close",
    },
    # Saru/I: mismo set de dedos extendidos (solo el pulgar) en ambas manos -
    # se distinguen entre si por el glyph (keyboard vs lock), igual que antes
    # de Y-05 (ninguna de las 2 formas reales es representable en este modelo
    # simple de iconos).
    "naruto_saru": {"hands": 2, "extended": ({"thumb"}, {"thumb"}), "pinch": None, "glyph": "keyboard"},
    "naruto_inu": {"hands": 2, "extended": ({"pinky"}, {"pinky"}), "pinch": None, "glyph": None},
    "naruto_i": {"hands": 2, "extended": ({"thumb"}, {"thumb"}), "pinch": None, "glyph": "lock"},
    # TASK-066 (Fase 5): sellos de 2 manos - proxy grueso (design.md §5.1),
    # el modelo de icono no representa distancia entre manos ni orientacion
    # real, asi que Ne/Mi se distinguen solo por el glyph.
    "naruto_ne": {"hands": 2, "extended": ({"index", "middle"}, {"index", "middle"}), "pinch": None, "glyph": None},
    "naruto_mi": {
        "hands": 2,
        "extended": ({"index", "middle"}, {"index", "middle"}),
        "pinch": None,
        "glyph": "arrow_up_down",
    },
    "naruto_tori": {
        "hands": 2,
        "extended": ({"index", "middle", "ring", "pinky"}, {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": None,
    },
    # Y-04: naruto_kai se borro (NARUTO_KAI no es uno de los 14 sellos
    # canonicos, AUDIT.md).
    "naruto_tatsu": {
        "hands": 2,
        "extended": (set(), {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": None,
    },
    # Y-06: Gassho y Mizunoe - no son sellos del zodiaco, pero el modelo los
    # distingue igual. Gassho: palmas planas juntas en oracion, los 4 dedos
    # extendidos en ambas manos (glyph "close" reusado - mismo tema que su
    # accion default, CLOSE_APP). Mizunoe: parecido a Inu en la foto
    # (docs/gesture-reference/canonical/13_mizunoe.jpg vs. 11_inu_dog.jpg) -
    # mismo set de dedos que naruto_inu, distinguido por el glyph.
    "naruto_gassho": {
        "hands": 2,
        "extended": ({"index", "middle", "ring", "pinky"}, {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": "close",
    },
    "naruto_mizunoe": {"hands": 2, "extended": ({"pinky"}, {"pinky"}), "pinch": None, "glyph": "arrow_left"},
    # Y-07: secuencias de sellos - el modelo de icono no puede representar
    # una secuencia de poses, asi que cada uno usa un set de dedos propio +
    # un glyph tematico con la accion default (double_dot=duplicar,
    # arrow_left=deshacer/"volver", zoom=el efecto de Katon).
    "jutsu_bunshin": {"hands": 2, "extended": ({"index"}, {"index"}), "pinch": None, "glyph": "double_dot"},
    "jutsu_kawarimi": {
        "hands": 2,
        "extended": ({"thumb", "index"}, {"thumb", "index"}),
        "pinch": None,
        "glyph": "arrow_left",
    },
    "jutsu_katon": {
        "hands": 2,
        "extended": ({"index", "middle", "ring", "pinky"}, {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": "zoom",
    },
    # TASK-070 (Fase 6): sellos JJK.
    "jjk_gojo_domain": {
        # Marco en L (pulgar+indice) de ambas manos - set de dedos extendidos
        # nuevo entre los gestos de 2 manos, ya distinto sin necesitar glyph.
        "hands": 2,
        "extended": ({"thumb", "index"}, {"thumb", "index"}),
        "pinch": None,
        "glyph": None,
    },
    "jjk_sukuna": {
        # Misma forma de mano que pinch_right_click (pulgar+medio tocandose)
        # a proposito - Sukuna ES ese pellizco, solo que rapido - se
        # distingue por el glyph "snap" (lineas de movimiento), pedido
        # explicitamente para comunicar que es temporal, no una pose estatica.
        "hands": 1,
        "extended": {"thumb", "middle"},
        "pinch": ("thumb", "middle"),
        "glyph": "snap",
    },
    "jjk_megumi": {
        # indice+medio+anular extendidos - combinacion de 3 dedos nueva entre
        # los gestos de 1 mano, ya distinta sin necesitar glyph (design.md
        # §6.3: anular EXTENDIDO es justamente lo que la distingue de Hitsuji).
        "hands": 1,
        "extended": {"index", "middle", "ring"},
        "pinch": None,
        "glyph": None,
    },
    # TASK-073 (Fase 7): gestos comunes.
    "clap": {
        # Misma forma de manos que naruto_tori (ambas bien abiertas) a
        # proposito - lo unico que distingue a Clap es el glyph de impacto
        # ("clap_burst"), ya que el modelo de icono no representa
        # movimiento/distancia entre manos (Clap ES un impulso, Tori es
        # estatico sostenido).
        "hands": 2,
        "extended": ({"index", "middle", "ring", "pinky"}, {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": "clap_burst",
    },
    "korean_heart": {
        # Puño cerrado con el pulgar cerca del primer nudillo del indice (no
        # de la punta, eso es pinch_click) - unica combinacion de 1 mano con
        # el pulgar TAMBIEN recogido (extended=set() vacio), ya distinta sin
        # depender del glyph; el corazon es tematico, no el discriminador.
        "hands": 1,
        "extended": set(),
        "pinch": ("thumb", "index"),
        "glyph": "heart",
    },
    # C-01 (WORKPLAN.md §10, workflow 8): dwell-click. Misma forma que
    # "pointer" (solo el indice extendido, sin pellizco) a proposito - el
    # gesto en si no tiene forma propia, se distingue de "pointer" unicamente
    # por el glyph de anillo (la misma metafora visual que draw_dwell_progress()).
    "dwell_click": {"hands": 1, "extended": {"index"}, "pinch": None, "glyph": "dwell_ring"},
    # C-02 (WORKPLAN.md §10, workflow 8): doble click. Misma forma que
    # "pinch_click" a proposito (ES ese pellizco, x2) - se distingue por el
    # glyph de 2 puntos.
    "double_click": {"hands": 1, "extended": {"thumb", "index"}, "pinch": ("thumb", "index"), "glyph": "double_dot"},
    # C-03 (WORKPLAN.md §10, workflow 8): swipe con puño cerrado, 1 mano -
    # mismo puño (extended=set()) que korean_heart, distinguido por no tener
    # pinch marker y por el glyph de flecha (4 iconos, 1 por direccion).
    "swipe_left": {"hands": 1, "extended": set(), "pinch": None, "glyph": "arrow_left"},
    "swipe_right": {"hands": 1, "extended": set(), "pinch": None, "glyph": "arrow_right"},
    "swipe_up": {"hands": 1, "extended": set(), "pinch": None, "glyph": "arrow_up"},
    "swipe_down": {"hands": 1, "extended": set(), "pinch": None, "glyph": "arrow_down"},
}


def _draw_hand(draw, offset_x, extended):
    for finger, points in _FINGER_POINTS.items():
        is_extended = finger in extended
        base = (points["base"][0] + offset_x, points["base"][1])
        tip_point = points["extended"] if is_extended else points["curled"]
        tip = (tip_point[0] + offset_x, tip_point[1])
        color = _EXTENDED_COLOR if is_extended else _CURLED_COLOR
        width = 3 if is_extended else 2
        draw.line([base, tip], fill=color, width=width)
        draw.ellipse([tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2], fill=color)
    palm_cx = 23 + offset_x
    draw.ellipse([palm_cx - 11, 26, palm_cx + 11, 40], outline=_PALM_COLOR, width=2)


def _finger_tip(offset_x, extended_set, finger):
    key = "extended" if finger in extended_set else "curled"
    x, y = _FINGER_POINTS[finger][key]
    return x + offset_x, y


def _draw_pinch_marker(draw, offset_x, extended_set, pinch):
    if pinch is None:
        return
    f1, f2 = pinch
    p1 = _finger_tip(offset_x, extended_set, f1)
    p2 = _finger_tip(offset_x, extended_set, f2)
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    r = 3
    draw.ellipse([mid[0] - r, mid[1] - r, mid[0] + r, mid[1] + r], fill=_PINCH_COLOR)


def _draw_arrow_up_down(draw, box):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    draw.polygon([(cx, y0), (x0 + 2, y0 + 5), (x1 - 2, y0 + 5)], fill=_GLYPH_COLOR)
    draw.polygon([(cx, y1), (x0 + 2, y1 - 5), (x1 - 2, y1 - 5)], fill=_GLYPH_COLOR)


def _draw_zoom(draw, box):
    x0, y0, x1, y1 = box
    r = (x1 - x0) * 0.6
    draw.ellipse([x0, y0, x0 + r, y0 + r], outline=_GLYPH_COLOR, width=2)
    draw.line([x0 + r * 0.8, y0 + r * 0.8, x1, y1], fill=_GLYPH_COLOR, width=2)


def _draw_keyboard(draw, box):
    x0, y0, x1, y1 = box
    draw.rectangle(box, outline=_GLYPH_COLOR, width=2)
    for row in (y0 + 3, y0 + 7):
        draw.line([x0 + 2, row, x1 - 2, row], fill=_GLYPH_COLOR, width=1)


def _draw_camera(draw, box):
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0 + 2, x1, y1], outline=_GLYPH_COLOR, width=2)
    cx, cy = (x0 + x1) / 2, (y0 + 2 + y1) / 2
    r = (x1 - x0) * 0.25
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_GLYPH_COLOR, width=1)


def _draw_lock(draw, box):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    body_top = y0 + (y1 - y0) * 0.45
    draw.arc([x0 + 2, y0, x1 - 2, body_top + 4], start=180, end=360, fill=_GLYPH_COLOR, width=2)
    draw.rectangle([x0, body_top, x1, y1], fill=_GLYPH_COLOR)


def _draw_mute(draw, box):
    x0, y0, x1, y1 = box
    draw.polygon([(x0, (y0 + y1) / 2 - 2), (x0 + 4, (y0 + y1) / 2 - 2), (x1 - 2, y0), (x1 - 2, y1), (x0 + 4, (y0 + y1) / 2 + 2), (x0, (y0 + y1) / 2 + 2)], fill=_GLYPH_COLOR)
    draw.line([x0, y0, x1, y1], fill=_PINCH_COLOR, width=2)


def _draw_pause(draw, box):
    x0, y0, x1, y1 = box
    w = (x1 - x0) * 0.3
    draw.rectangle([x0, y0, x0 + w, y1], fill=_GLYPH_COLOR)
    draw.rectangle([x1 - w, y0, x1, y1], fill=_GLYPH_COLOR)


def _draw_close(draw, box):
    x0, y0, x1, y1 = box
    draw.line([x0, y0, x1, y1], fill=_GLYPH_COLOR, width=3)
    draw.line([x0, y1, x1, y0], fill=_GLYPH_COLOR, width=3)


def _draw_snap(draw, box):
    # TASK-070 (Fase 6): pequeñas lineas de "chispa"/movimiento radiando
    # desde el centro - comunica que Sukuna es temporal (un impulso), no una
    # pose estatica sostenida como el resto de los glifos de mano sola.
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r_in, r_out = (x1 - x0) * 0.2, (x1 - x0) * 0.55
    for angle in (0, 90, 180, 270):
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        draw.line(
            [cx + dx * r_in, cy + dy * r_in, cx + dx * r_out, cy + dy * r_out],
            fill=_GLYPH_COLOR,
            width=2,
        )


def _draw_clap_burst(draw, box):
    # TASK-073 (Fase 7): impacto de "aplauso" - 6 lineas cortas radiando
    # desde un punto relleno en el centro (mas denso que "snap", que usa 4
    # lineas sin relleno - visualmente distinto a proposito, mismo espiritu
    # de "esto es un impulso, no una pose").
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r_in, r_out = (x1 - x0) * 0.12, (x1 - x0) * 0.55
    for angle in (0, 60, 120, 180, 240, 300):
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        draw.line(
            [cx + dx * r_in, cy + dy * r_in, cx + dx * r_out, cy + dy * r_out],
            fill=_GLYPH_COLOR,
            width=2,
        )
    r_dot = (x1 - x0) * 0.1
    draw.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=_GLYPH_COLOR)


def _draw_heart(draw, box):
    x0, y0, x1, y1 = box
    width = x1 - x0
    cx = (x0 + x1) / 2
    r = width * 0.28
    draw.ellipse([cx - r * 2, y0, cx, y0 + r * 2], fill=_GLYPH_COLOR)
    draw.ellipse([cx, y0, cx + r * 2, y0 + r * 2], fill=_GLYPH_COLOR)
    draw.polygon([(cx - r * 2, y0 + r * 1.2), (cx + r * 2, y0 + r * 1.2), (cx, y1)], fill=_GLYPH_COLOR)


def _draw_dwell_ring(draw, box):
    # C-01: mismo lenguaje visual que draw_dwell_progress() (anillo de
    # progreso) - un anillo estatico simple, sin "progreso" real (esto es un
    # icono de referencia, no el HUD en vivo).
    x0, y0, x1, y1 = box
    draw.ellipse([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=_GLYPH_COLOR, width=2)


def _draw_double_dot(draw, box):
    # C-02: 2 puntos lado a lado - "esto pasa dos veces", mismo espiritu que
    # "snap"/"clap_burst" comunicando temporalidad en vez de una pose estatica.
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    r = (x1 - x0) * 0.16
    cx1 = x0 + (x1 - x0) * 0.3
    cx2 = x0 + (x1 - x0) * 0.7
    draw.ellipse([cx1 - r, cy - r, cx1 + r, cy + r], fill=_GLYPH_COLOR)
    draw.ellipse([cx2 - r, cy - r, cx2 + r, cy + r], fill=_GLYPH_COLOR)


def _draw_arrow_left(draw, box):
    # C-03: una sola flecha (no el par bidireccional de "arrow_up_down") -
    # cada direccion de swipe es un icono propio.
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    draw.polygon([(x0, cy), (x0 + 6, y0 + 1), (x0 + 6, y1 - 1)], fill=_GLYPH_COLOR)
    draw.line([x0 + 6, cy, x1, cy], fill=_GLYPH_COLOR, width=2)


def _draw_arrow_right(draw, box):
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    draw.polygon([(x1, cy), (x1 - 6, y0 + 1), (x1 - 6, y1 - 1)], fill=_GLYPH_COLOR)
    draw.line([x0, cy, x1 - 6, cy], fill=_GLYPH_COLOR, width=2)


def _draw_arrow_up(draw, box):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    draw.polygon([(cx, y0), (x0 + 1, y0 + 6), (x1 - 1, y0 + 6)], fill=_GLYPH_COLOR)
    draw.line([cx, y0 + 6, cx, y1], fill=_GLYPH_COLOR, width=2)


def _draw_arrow_down(draw, box):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    draw.polygon([(cx, y1), (x0 + 1, y1 - 6), (x1 - 1, y1 - 6)], fill=_GLYPH_COLOR)
    draw.line([cx, y0, cx, y1 - 6], fill=_GLYPH_COLOR, width=2)


GLYPH_DRAWERS = {
    "arrow_up_down": _draw_arrow_up_down,
    "zoom": _draw_zoom,
    "keyboard": _draw_keyboard,
    "camera": _draw_camera,
    "lock": _draw_lock,
    "mute": _draw_mute,
    "pause": _draw_pause,
    "close": _draw_close,
    "snap": _draw_snap,
    "clap_burst": _draw_clap_burst,
    "heart": _draw_heart,
    "dwell_ring": _draw_dwell_ring,
    "double_dot": _draw_double_dot,
    "arrow_left": _draw_arrow_left,
    "arrow_right": _draw_arrow_right,
    "arrow_up": _draw_arrow_up,
    "arrow_down": _draw_arrow_down,
}

_GLYPH_BOX = (ICON_SIZE - 15, 2, ICON_SIZE - 2, 15)  # esquina superior derecha


def _render_key_icon(key_label):
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = 6
    draw.rounded_rectangle([pad, pad, ICON_SIZE - pad, ICON_SIZE - pad], radius=6, outline=_KEY_COLOR, width=2)
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), key_label, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((ICON_SIZE - text_w) / 2, (ICON_SIZE - text_h) / 2 - 2), key_label, fill=_KEY_COLOR, font=font)
    return image


def _render_icon(spec):
    if spec["hands"] == 0:
        return _render_key_icon(spec["key_label"])

    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if spec["hands"] == 1:
        _draw_hand(draw, offset_x=0, extended=spec["extended"])
        _draw_pinch_marker(draw, offset_x=0, extended_set=spec["extended"], pinch=spec["pinch"])
    else:
        extended_1, extended_2 = spec["extended"]
        _draw_hand(draw, offset_x=-8, extended=extended_1)
        _draw_hand(draw, offset_x=8, extended=extended_2)

    if spec.get("glyph"):
        GLYPH_DRAWERS[spec["glyph"]](draw, _GLYPH_BOX)

    return image


def ensure_icon(key):
    """Devuelve el Path del PNG cacheado para `key`, generandolo si es la
    primera vez (spec.md #3.1: "same lazy-generate-and-cache pattern as the
    MediaPipe model download"). `None` si no se pudo generar ni cachear (H-14):
    la leyenda es una ayuda visual, un fallo de escritura (permisos, disco
    lleno, directorio de solo lectura) nunca puede impedir que la app arranque
    - los llamadores (`legend.py`, `settings_ui.py`) degradan a una entrada
    sin icono en ese caso."""
    path = writable_assets_dir() / "gesture_icons" / f"{key}.png"
    if path.exists():
        return path
    # H-15: escritura atomica (temp en el mismo directorio + os.replace),
    # mismo patron que config_store.py/downloads.py - dos procesos generando
    # el mismo icono a la vez, o un `save()` interrumpido, no dejan nunca un
    # PNG parcial ocupando el nombre final (que un `ensure_icon()` posterior
    # cachearia para siempre via el chequeo `path.exists()` de arriba).
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _render_icon(ICON_SPECS[key]).save(tmp_path, format="PNG")
        os.replace(tmp_path, path)
    except OSError:
        _logger.error("no se pudo generar/guardar el icono '%s' en %s", key, path, exc_info=True)
        tmp_path.unlink(missing_ok=True)
        return None
    return path


def generate_all_icons():
    """Genera y cachea los iconos de todas las keys conocidas. Sin uso fuera
    de `tests/test_gesture_icons.py` (H-17): utilitaria de test/build, no del
    codigo de la app en runtime (que solo pide un icono a la vez via
    `ensure_icon`, on-demand, por entrada de leyenda)."""
    return {key: ensure_icon(key) for key in ICON_SPECS}
