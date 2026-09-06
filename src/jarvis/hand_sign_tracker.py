"""HandSignTracker: la politica de la app sobre `hand_sign_model.py` (Y-02,
`openspec/changes/hand-sign-fidelity/WORKPLAN.md`).

Paralelo a `hand_tracker.py`/`pose_tracker.py`: envuelve el modelo con lo que
la app necesita (umbral de score, debounce, hold, dedup) sin tocar `main.py`
todavia - eso es Y-03.

Mapea el nombre de clase del modelo a nuestro evento de siempre (tabla en
`WORKPLAN.md` §2). Y-06 agrega Gassho y Mizunoe (salian gratis del modelo,
sin geometria propia que escribir). `Unknown` y la clase 16 sin nombre
(`class_name is None`, ver `hand_sign_model.py`) siguen sin evento: una
deteccion de esas dos se trata igual que "no hay sello", no arranca ni
sostiene ningun hold.

Dedup y hold son deliberadamente distintos del `_naruto_hold_seal` de dos
manos que hoy vive en `gestures.py` (que reemite el evento cada
`NARUTO_TWOHAND_HOLD_SECONDS` mientras el sello sigue sostenido): este
tracker emite el evento UNA sola vez por sostenida (no repite mientras el
mismo sello se mantenga), y recien vuelve a emitir si el sello cambia o se
suelta y se rehace. `hold_seal` sí se comporta igual que la variable vieja
para el uso que le dan los gates de dwell/swipe (C-01/C-03): queda en el
nombre del sello mientras se sostiene, sin importar si ya emitio su evento.
"""

import time

from jarvis import config
from jarvis.core.debounce import ConsecutiveFrameDebouncer
from jarvis.hand_sign_model import HandSignModel
from jarvis.paths import bundled_assets_dir

MODEL_FILENAME = "hand_sign_yolox_nano.onnx"

# Umbral de score final (AUDIT.md: 14/14 imagenes canonicas clasifican con
# score 0.82-0.93; 0.7 deja margen debajo de eso sin acercarse al ruido de
# clasificacion). Razonado sobre datos medidos, pendiente de ajuste real en
# camara (Y-V4).
DEFAULT_MIN_SCORE = 0.7

# Los 12 sellos del zodiaco (WORKPLAN.md §2) + Gassho/Mizunoe (Y-06) - las 14
# clases nombradas que el modelo distingue, salvo "Unknown".
CLASS_NAME_TO_EVENT = {
    "Ne(Rat)": "NARUTO_NE",
    "Ushi(Ox)": "NARUTO_USHI",
    "Tora(Tiger)": "NARUTO_TORA",
    "U(Hare)": "NARUTO_U",
    "Tatsu(Dragon)": "NARUTO_TATSU",
    "Mi(Snake)": "NARUTO_MI",
    "Uma(Horse)": "NARUTO_UMA",
    "Hitsuji(Ram)": "NARUTO_HITSUJI",
    "Saru(Monkey)": "NARUTO_SARU",
    "Tori(Bird)": "NARUTO_TORI",
    "Inu(Dog)": "NARUTO_INU",
    "I(Boar)": "NARUTO_I",
    "Gassho": "NARUTO_GASSHO",
    "Mizunoe": "NARUTO_MIZUNOE",
}


def _default_model_path():
    return bundled_assets_dir() / MODEL_FILENAME


class HandSignTracker:
    def __init__(
        self,
        model=None,
        min_score=DEFAULT_MIN_SCORE,
        hold_seconds=None,
        debouncer=None,
    ):
        self._model = model if model is not None else HandSignModel(_default_model_path())
        self._min_score = min_score
        self._hold_seconds = (
            hold_seconds if hold_seconds is not None else config.NARUTO_TWOHAND_HOLD_SECONDS
        )
        self._debouncer = debouncer if debouncer is not None else ConsecutiveFrameDebouncer()

        self.hold_seal = None  # el sello sostenido ahora (nombre de evento), o None
        self._hold_start = None
        self._emitted_for_hold = False

    def _best_mapped_class(self, frame):
        """Mejor deteccion (mayor score) que supere `min_score` Y tenga un
        evento mapeado, o None. `HandSignModel.detect()` ya devuelve la lista
        ordenada de mayor a menor score."""
        for detection in self._model.detect(frame):
            if detection.score < self._min_score:
                break
            if detection.class_name in CLASS_NAME_TO_EVENT:
                return detection.class_name
        return None

    def process(self, frame, now=None):
        """Corre el modelo sobre `frame` (SIN espejar, ver Y-02 en el
        WORKPLAN) y devuelve la lista de eventos a emitir este cuadro (0 o 1
        elementos: un sello sostenido el tiempo suficiente, o nada)."""
        if now is None:
            now = time.time()

        class_name = self._best_mapped_class(frame)
        confirmed = self._debouncer.observe(class_name)

        if not confirmed:
            self.hold_seal = None
            self._hold_start = None
            self._emitted_for_hold = False
            return []

        if self.hold_seal != class_name:
            self.hold_seal = class_name
            self._hold_start = now
            self._emitted_for_hold = False
            return []

        if not self._emitted_for_hold and now - self._hold_start >= self._hold_seconds:
            self._emitted_for_hold = True
            return [CLASS_NAME_TO_EVENT[class_name]]

        return []
