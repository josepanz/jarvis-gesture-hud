"""Tests for TASK-067 (Fase 6, design.md §6.2): ImpulseDetector, el primer
primitivo TEMPORAL/multi-frame de este codebase."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.temporal_gesture import ImpulseDetector  # noqa: E402

CONTACT = 15
RELEASE = 50
WINDOW = 0.3


def _detector():
    return ImpulseDetector(CONTACT, RELEASE, WINDOW)


class ImpulseDetectorTests(unittest.TestCase):
    def test_a_drop_then_rise_within_the_window_fires_exactly_once(self):
        det = _detector()
        self.assertFalse(det.update(100, 0.0))  # lejos, sin contacto
        self.assertFalse(det.update(10, 0.05))  # contacto (baja de CONTACT)
        self.assertFalse(det.update(10, 0.10))  # sigue en contacto
        self.assertTrue(det.update(80, 0.15))  # sube de RELEASE, dentro de la ventana -> dispara

    def test_a_drop_that_never_rises_within_the_window_does_not_fire(self):
        det = _detector()
        self.assertFalse(det.update(10, 0.0))  # contacto
        self.assertFalse(det.update(10, 0.35))  # sigue abajo de CONTACT, ya paso la ventana (0.3)
        self.assertFalse(det.update(10, 0.40))  # todavia sin subir de RELEASE, jamas dispara

    def test_a_sustained_hold_that_eventually_releases_does_not_fire(self):
        # Un pinch/hold sostenido (RIGHT_CLICK) se queda por debajo de CONTACT
        # mucho mas alla de la ventana, y RECIEN despues se suelta - a
        # diferencia de un snap genuino, esto NO debe contar como impulso.
        det = _detector()
        self.assertFalse(det.update(10, 0.0))
        for t in (0.5, 1.0, 1.5, 2.0, 2.5):  # sostenido mucho mas alla de WINDOW
            self.assertFalse(det.update(10, t))
        self.assertFalse(det.update(80, 3.0))  # se suelta recien aca -> no dispara, no es un snap

    def test_two_consecutive_genuine_impulses_each_fire_once_independently(self):
        det = _detector()
        self.assertFalse(det.update(100, 0.0))
        self.assertFalse(det.update(10, 0.05))
        self.assertTrue(det.update(80, 0.10))  # primer impulso

        self.assertFalse(det.update(10, 0.20))
        self.assertTrue(det.update(80, 0.25))  # segundo impulso, independiente


if __name__ == "__main__":
    unittest.main()
