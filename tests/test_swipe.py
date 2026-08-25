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


if __name__ == "__main__":
    unittest.main()
