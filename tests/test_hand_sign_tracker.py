"""Y-02 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md`): tests de
`HandSignTracker` con el modelo mockeado (debounce/hold/dedup aislados de la
inferencia real) y, para el caso central, con el modelo real sobre las 14
imagenes canonicas.
"""

import sys
import unittest
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import config  # noqa: E402
from jarvis.core.debounce import DEFAULT_CONFIRMATION_FRAMES  # noqa: E402
from jarvis.hand_sign_model import Detection  # noqa: E402
from jarvis.hand_sign_tracker import CLASS_NAME_TO_EVENT, HandSignTracker  # noqa: E402

CANONICAL_DIR = Path(__file__).resolve().parents[1] / "docs" / "gesture-reference" / "canonical"

EXPECTED_EVENT_BY_FILE = {
    "01_ne_rat.jpg": "NARUTO_NE",
    "02_ushi_ox.jpg": "NARUTO_USHI",
    "03_tora_tiger.jpg": "NARUTO_TORA",
    "04_u_hare.jpg": "NARUTO_U",
    "05_tatsu_dragon.jpg": "NARUTO_TATSU",
    "06_mi_snake.jpg": "NARUTO_MI",
    "07_uma_horse.jpg": "NARUTO_UMA",
    "08_hitsuji_ram.jpg": "NARUTO_HITSUJI",
    "09_saru_monkey.jpg": "NARUTO_SARU",
    "10_tori_bird.jpg": "NARUTO_TORI",
    "11_inu_dog.jpg": "NARUTO_INU",
    "12_i_boar.jpg": "NARUTO_I",
    "13_mizunoe.jpg": "NARUTO_MIZUNOE",
    "14_gassho_clap.jpg": "NARUTO_GASSHO",
}


class FakeModel:
    """Modelo falso: devuelve exactamente lo que el test cargue en
    `next_detections`, ya "ordenado" como lo estaria un `HandSignModel` real
    (mayor score primero)."""

    def __init__(self):
        self.next_detections = []

    def detect(self, frame):
        return self.next_detections


def _seal(class_name, score=0.9):
    return [Detection(class_name=class_name, score=score, bbox=(0, 0, 10, 10))]


class HandSignTrackerMockedModelTests(unittest.TestCase):
    def setUp(self):
        self.model = FakeModel()
        self.tracker = HandSignTracker(model=self.model)
        self.t = 0.0

    def _tick(self, detections):
        self.model.next_detections = detections
        events = self.tracker.process(None, now=self.t)
        self.t += 0.03
        return events

    def _confirm(self, class_name):
        """Alimenta `DEFAULT_CONFIRMATION_FRAMES` cuadros seguidos de `class_name`
        (deja el hold recien arrancado, sin emitir todavia) y devuelve los
        eventos del ultimo cuadro."""
        events = []
        for _ in range(DEFAULT_CONFIRMATION_FRAMES):
            events = self._tick(_seal(class_name))
        return events

    def test_single_detection_does_not_emit(self):
        events = self._tick(_seal("Ne(Rat)"))
        self.assertEqual(events, [])
        self.assertIsNone(self.tracker.hold_seal)

    def test_last_detection_reflects_the_raw_top_detection_even_below_threshold(self):
        # Y-V1..Y-V4 (Workflow 4, WORKPLAN.md §6): diagnostico en vivo - se ve
        # la deteccion cruda (score real) aunque no llegue a min_score ni
        # tenga evento mapeado, para poder leer "cuanto falta" en camara.
        self._tick(_seal("Ne(Rat)", score=0.4))
        self.assertEqual(self.tracker.last_detection.class_name, "Ne(Rat)")
        self.assertEqual(self.tracker.last_detection.score, 0.4)
        self.assertIsNone(self.tracker.hold_seal)  # no llega a min_score, no cuenta como sello

        self._tick(_seal("Unknown", score=0.95))
        self.assertEqual(self.tracker.last_detection.class_name, "Unknown")
        self.assertEqual(self.tracker.last_detection.score, 0.95)

    def test_last_detection_is_none_when_the_model_sees_nothing(self):
        events = self._tick([])
        self.assertEqual(events, [])
        self.assertIsNone(self.tracker.last_detection)

    def test_hold_elapsed_tracks_progress_toward_hold_needed(self):
        self._confirm("Ne(Rat)")
        self.assertEqual(self.tracker.hold_elapsed, 0.0)  # el hold recien arranca

        self.t += config.NARUTO_TWOHAND_HOLD_SECONDS / 2
        self._tick(_seal("Ne(Rat)"))
        self.assertGreater(self.tracker.hold_elapsed, 0.0)
        self.assertLess(self.tracker.hold_elapsed, config.NARUTO_TWOHAND_HOLD_SECONDS)
        self.assertEqual(self.tracker.hold_needed, config.NARUTO_TWOHAND_HOLD_SECONDS)

    def test_confirmed_and_held_emits_once(self):
        events = self._confirm("Ne(Rat)")
        self.assertEqual(events, [])  # el hold recien arranca este cuadro
        self.assertEqual(self.tracker.hold_seal, "Ne(Rat)")

        self.t += config.NARUTO_TWOHAND_HOLD_SECONDS + 0.01
        events = self._tick(_seal("Ne(Rat)"))
        self.assertEqual(events, ["NARUTO_NE"])

    def test_holding_the_same_seal_does_not_repeat_the_event(self):
        self._confirm("Ne(Rat)")
        self.t += config.NARUTO_TWOHAND_HOLD_SECONDS + 0.01
        first = self._tick(_seal("Ne(Rat)"))
        self.assertEqual(first, ["NARUTO_NE"])

        # Sigue sosteniendo el mismo sello mucho mas alla del hold: no repite.
        for _ in range(10):
            self.t += config.NARUTO_TWOHAND_HOLD_SECONDS
            self.assertEqual(self._tick(_seal("Ne(Rat)")), [])

    def test_changing_seal_resets_the_hold(self):
        self._confirm("Ne(Rat)")
        self.t += config.NARUTO_TWOHAND_HOLD_SECONDS + 0.01
        self.assertEqual(self._tick(_seal("Ne(Rat)")), ["NARUTO_NE"])

        events = self._confirm("Mi(Snake)")
        self.assertEqual(events, [])  # el hold de Mi(Snake) recien arranca
        self.assertEqual(self.tracker.hold_seal, "Mi(Snake)")

        self.t += config.NARUTO_TWOHAND_HOLD_SECONDS + 0.01
        self.assertEqual(self._tick(_seal("Mi(Snake)")), ["NARUTO_MI"])

    def test_unmapped_class_never_emits(self):
        for _ in range(20):
            self.t += config.NARUTO_TWOHAND_HOLD_SECONDS
            events = self._tick(_seal("Unknown", score=0.99))
            self.assertEqual(events, [])
        self.assertIsNone(self.tracker.hold_seal)

    def test_below_score_threshold_is_discarded_before_debounce(self):
        for _ in range(DEFAULT_CONFIRMATION_FRAMES + 5):
            self.t += config.NARUTO_TWOHAND_HOLD_SECONDS
            events = self._tick(_seal("Ne(Rat)", score=0.5))
            self.assertEqual(events, [])
        self.assertIsNone(self.tracker.hold_seal)


class HandSignTrackerRealModelCanonicalImagesTests(unittest.TestCase):
    """El caso central de Y-02/Y-06: con el modelo real, cada una de las 14
    imagenes de referencia produce su evento tras el hold."""

    @classmethod
    def setUpClass(cls):
        cls.all_events_mapped = set(CLASS_NAME_TO_EVENT.values())

    def test_each_canonical_image_emits_its_event_after_hold(self):
        for filename, expected_event in EXPECTED_EVENT_BY_FILE.items():
            with self.subTest(filename=filename):
                image = cv2.imread(str(CANONICAL_DIR / filename))
                self.assertIsNotNone(image, f"no se pudo leer {filename}")

                tracker = HandSignTracker()
                t = 0.0
                events = []
                for _ in range(DEFAULT_CONFIRMATION_FRAMES):
                    events = tracker.process(image, now=t)
                    t += 0.03
                self.assertEqual(events, [], f"{filename}: no deberia emitir antes del hold")

                t += config.NARUTO_TWOHAND_HOLD_SECONDS + 0.01
                events = tracker.process(image, now=t)
                self.assertEqual(events, [expected_event])


if __name__ == "__main__":
    unittest.main()
