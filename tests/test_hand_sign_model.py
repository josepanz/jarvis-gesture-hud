"""Y-01 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md`): tests del wrapper
ONNX del modelo YOLOX-Nano de deteccion de sellos. Modelo real (3.6MB, ya
commiteado en `assets/`), sin mocks: la garantia central de esta tarea es que
las 14 fotos canonicas se auto-clasifican bien, y eso solo se puede probar con
inferencia real.
"""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hand_sign_model import CLASS_NAMES, HandSignModel, class_name_for  # noqa: E402
from jarvis.paths import bundled_assets_dir  # noqa: E402

MODEL_PATH = bundled_assets_dir() / "hand_sign_yolox_nano.onnx"
CANONICAL_DIR = Path(__file__).resolve().parents[1] / "docs" / "gesture-reference" / "canonical"

# archivo -> nombre de clase esperado (CLASS_NAMES), Mizunoe y Gassho incluidos
# aunque todavia no tengan evento propio (eso es Y-06) porque el modelo si los
# distingue.
EXPECTED_CLASS_BY_FILE = {
    "01_ne_rat.jpg": "Ne(Rat)",
    "02_ushi_ox.jpg": "Ushi(Ox)",
    "03_tora_tiger.jpg": "Tora(Tiger)",
    "04_u_hare.jpg": "U(Hare)",
    "05_tatsu_dragon.jpg": "Tatsu(Dragon)",
    "06_mi_snake.jpg": "Mi(Snake)",
    "07_uma_horse.jpg": "Uma(Horse)",
    "08_hitsuji_ram.jpg": "Hitsuji(Ram)",
    "09_saru_monkey.jpg": "Saru(Monkey)",
    "10_tori_bird.jpg": "Tori(Bird)",
    "11_inu_dog.jpg": "Inu(Dog)",
    "12_i_boar.jpg": "I(Boar)",
    "13_mizunoe.jpg": "Mizunoe",
    "14_gassho_clap.jpg": "Gassho",
}

SCORE_THRESHOLD = 0.7


class HandSignModelLoadTests(unittest.TestCase):
    def test_loads_and_exposes_expected_input_shape(self):
        model = HandSignModel(MODEL_PATH)
        self.assertEqual(model.input_shape, (416, 416))


class ClassMappingTests(unittest.TestCase):
    def test_no_class_id_raises_index_error(self):
        for class_id in range(16):
            class_name_for(class_id)  # no debe lanzar IndexError

    def test_sixteen_entries(self):
        self.assertEqual(len(CLASS_NAMES), 16)

    def test_leftover_class_maps_to_none(self):
        # Clase 16 del modelo (class_id 15): la que el demo original no podia
        # nombrar sin IndexError (ver docstring de hand_sign_model.py).
        self.assertIsNone(class_name_for(15))


class CanonicalImageClassificationTests(unittest.TestCase):
    """El test central de Y-01: las 14 fotos de referencia se auto-clasifican,
    cada una como su propio sello, con score >= 0.7 (medido: 14/14, 0.82-0.93)."""

    @classmethod
    def setUpClass(cls):
        cls.model = HandSignModel(MODEL_PATH)

    def test_each_canonical_image_classifies_as_its_own_seal(self):
        for filename, expected_class in EXPECTED_CLASS_BY_FILE.items():
            with self.subTest(filename=filename):
                image = cv2.imread(str(CANONICAL_DIR / filename))
                self.assertIsNotNone(image, f"no se pudo leer {filename}")
                detections = self.model.detect(image)
                above_threshold = [d for d in detections if d.score >= SCORE_THRESHOLD]
                self.assertTrue(
                    above_threshold,
                    f"{filename}: ninguna deteccion >= {SCORE_THRESHOLD} (top: {detections[:3]})",
                )
                best = above_threshold[0]
                self.assertEqual(
                    best.class_name,
                    expected_class,
                    f"{filename}: se esperaba {expected_class}, se detecto {best.class_name} "
                    f"(score {best.score:.2f})",
                )

    def test_random_noise_frame_has_no_confident_detection(self):
        rng = np.random.default_rng(0)
        noise = rng.integers(0, 256, size=(480, 640, 3), dtype=np.uint8)
        detections = self.model.detect(noise)
        above_threshold = [d for d in detections if d.score >= SCORE_THRESHOLD]
        self.assertEqual(above_threshold, [])


if __name__ == "__main__":
    unittest.main()
