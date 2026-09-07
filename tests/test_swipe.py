"""Unit tests for SwipeDetector (TASK-020)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.swipe import SwipeDetector  # noqa: E402


class SwipeDetectorTests(unittest.TestCase):
    def test_fast_rightward_movement_is_swipe_right(self):
        d = SwipeDetector(min_distance=0.15, min_velocity=0.5, max_duration_ms=600)
        d.update(0.1, 0.5, 0.0)
        result = d.update(0.4, 0.5, 0.1)  # dx=0.3 in 100ms -> 3.0 units/s
        self.assertEqual(result, "SWIPE_RIGHT")

    def test_fast_leftward_movement_is_swipe_left(self):
        d = SwipeDetector()
        d.update(0.9, 0.5, 0.0)
        result = d.update(0.6, 0.5, 0.1)
        self.assertEqual(result, "SWIPE_LEFT")

    def test_fast_downward_movement_is_swipe_down(self):
        d = SwipeDetector()
        d.update(0.5, 0.1, 0.0)
        result = d.update(0.5, 0.4, 0.1)
        self.assertEqual(result, "SWIPE_DOWN")

    def test_fast_upward_movement_is_swipe_up(self):
        d = SwipeDetector()
        d.update(0.5, 0.9, 0.0)
        result = d.update(0.5, 0.6, 0.1)
        self.assertEqual(result, "SWIPE_UP")

    def test_slow_movement_does_not_become_swipe(self):
        d = SwipeDetector(min_distance=0.15, min_velocity=0.5)
        d.update(0.1, 0.5, 0.0)
        result = d.update(0.4, 0.5, 2.0)  # same distance, but over 2s -> too slow
        self.assertIsNone(result)

    def test_small_displacement_does_not_become_swipe(self):
        d = SwipeDetector(min_distance=0.15)
        d.update(0.5, 0.5, 0.0)
        result = d.update(0.52, 0.5, 0.05)
        self.assertIsNone(result)

    def test_stale_window_restarts_after_max_duration(self):
        d = SwipeDetector(max_duration_ms=200)
        d.update(0.1, 0.5, 0.0)
        result = d.update(0.4, 0.5, 1.0)  # 1000ms later, window is stale
        self.assertIsNone(result)

    def test_detector_is_reusable_after_firing(self):
        d = SwipeDetector()
        d.update(0.1, 0.5, 0.0)
        first = d.update(0.4, 0.5, 0.1)
        self.assertEqual(first, "SWIPE_RIGHT")
        d.update(0.4, 0.5, 0.2)
        second = d.update(0.1, 0.5, 0.3)
        self.assertEqual(second, "SWIPE_LEFT")

    def test_reset_clears_tracking_window(self):
        d = SwipeDetector()
        d.update(0.1, 0.5, 0.0)
        d.reset()
        result = d.update(0.4, 0.5, 0.05)  # no start point anymore - just re-anchors
        self.assertIsNone(result)

    def test_a_successful_swipe_records_its_distance_velocity_and_duration(self):
        # V-10: diagnostico en vivo para verificar en camara real con datos
        # reales en vez de estimarlos.
        d = SwipeDetector(min_distance=0.15, min_velocity=0.5, max_duration_ms=600)
        d.update(0.1, 0.5, 0.0)
        d.update(0.4, 0.5, 0.1)  # dx=0.3 en 100ms
        self.assertAlmostEqual(d.last_distance, 0.3, places=6)
        self.assertAlmostEqual(d.last_velocity, 3.0, places=6)
        self.assertAlmostEqual(d.last_duration_ms, 100.0, places=6)

    def test_a_too_slow_attempt_still_records_its_measured_distance_and_velocity(self):
        # El candidato que llega a min_distance pero no dispara por velocidad
        # tambien queda registrado - util para confirmar "el movimiento normal
        # nunca los alcanza" con el numero real, no solo con el resultado None.
        # dt_ms (500) se mantiene DEBAJO de max_duration_ms (600, default) a
        # proposito - por encima de eso el intento ya se descarta por
        # ventana vencida antes de llegar a calcular la velocidad siquiera.
        d = SwipeDetector(min_distance=0.15, min_velocity=0.5)
        d.update(0.1, 0.5, 0.0)
        result = d.update(0.3, 0.5, 0.5)  # dx=0.2 en 500ms -> 0.4 unidades/s
        self.assertIsNone(result)
        self.assertAlmostEqual(d.last_distance, 0.2, places=6)
        self.assertAlmostEqual(d.last_velocity, 0.4, places=6)


if __name__ == "__main__":
    unittest.main()
