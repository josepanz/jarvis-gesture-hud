"""TASK-058 (Fase 3, `openspec/changes/personalization-and-config-ui`,
spec.md #3.1-3.2): iconos de referencia generados proceduralmente (nada de
binarios dibujados a mano commiteados) para cada entrada de la leyenda de
gestos - un glifo de mano estilizado (palma + dedos extendidos/curvados,
1 o 2 manos) mas un pequeño glifo de accion cuando aplica.

Dibujado con `PIL.Image`/`PIL.ImageDraw` (dependencia nueva: Pillow, agregada
a requirements.txt) - se muestra despues via `tkinter.PhotoImage(file=...)`,
sin necesitar `PIL.ImageTk`.
"""

import math

from PIL import Image, ImageDraw, ImageFont

from jarvis.paths import assets_dir

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
    # TASK-063 (Fase 4): un icono por sello Naruto de 1 mano - spec.md #3.4.
    "naruto_tora": {"hands": 1, "extended": {"index", "middle"}, "pinch": ("index", "middle"), "glyph": "camera"},
    "naruto_ushi": {"hands": 1, "extended": {"index"}, "pinch": None, "glyph": "pause"},
    "naruto_u": {"hands": 1, "extended": {"index", "middle"}, "pinch": None, "glyph": None},
    "naruto_uma": {
        # Redefinido por segunda vez (verificado en camara real) - ver
        # gestures.py::_is_naruto_uma.
        "hands": 1,
        "extended": {"thumb", "index", "pinky"},
        "pinch": None,
        "glyph": "zoom",
    },
    "naruto_hitsuji": {"hands": 1, "extended": {"index", "middle"}, "pinch": None, "glyph": "close"},
    # Saru/I: mismo set de dedos extendidos (solo el pulgar) - se
    # distinguen entre si por el glyph (keyboard vs lock), la direccion real
    # del pulgar (arriba vs costado) no es representable en este modelo
    # simple de iconos.
    "naruto_saru": {"hands": 1, "extended": {"thumb"}, "pinch": None, "glyph": "keyboard"},
    "naruto_inu": {"hands": 1, "extended": {"pinky"}, "pinch": None, "glyph": None},
    "naruto_i": {"hands": 1, "extended": {"thumb"}, "pinch": None, "glyph": "lock"},
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
    "naruto_kai": {"hands": 2, "extended": ({"index", "middle"}, {"index", "middle"}), "pinch": None, "glyph": "close"},
    "naruto_tatsu": {
        "hands": 2,
        "extended": (set(), {"index", "middle", "ring", "pinky"}),
        "pinch": None,
        "glyph": None,
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
    MediaPipe model download")."""
    path = assets_dir() / "gesture_icons" / f"{key}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _render_icon(ICON_SPECS[key]).save(path)
    return path


def generate_all_icons():
    return {key: ensure_icon(key) for key in ICON_SPECS}
