"""Unit tests for DwellDetector + draw_dwell_progress (TASK-021)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from jarvis.core.dwell import DwellDetector, draw_dwell_progress  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class DwellDetectorTests(unittest.TestCase):
    def test_default_duration_is_600ms(self):
        self.assertEqual(DwellDetector().duration_ms, 600)

    def test_first_update_acquires_target_with_zero_progress(self):
        d = DwellDetector(clock=FakeClock())
        self.assertEqual(d.update(0.5, 0.5), 0.0)

    def test_progress_increases_over_time_while_target_held(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, clock=clock)
        d.update(0.5, 0.5)
        clock.advance(0.3)
        progress = d.update(0.5, 0.5)
        self.assertAlmostEqual(progress, 0.5, places=2)

    def test_reaches_full_progress_at_duration(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, clock=clock)
        d.update(0.5, 0.5)
        clock.advance(0.6)
        self.assertEqual(d.update(0.5, 0.5), 1.0)

    def test_progress_does_not_exceed_one(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, clock=clock)
        d.update(0.5, 0.5)
        clock.advance(5.0)
        self.assertEqual(d.update(0.5, 0.5), 1.0)

    def test_moving_past_cancel_distance_resets_progress(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, cancel_distance=0.05, clock=clock)
        d.update(0.5, 0.5)
        clock.advance(0.4)
        progress = d.update(0.9, 0.9)  # far away - cancels
        self.assertEqual(progress, 0.0)

    def test_low_confidence_resets_progress(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, clock=clock)
        d.update(0.5, 0.5, confidence=1.0, min_confidence=0.5)
        clock.advance(0.4)
        progress = d.update(0.5, 0.5, confidence=0.1, min_confidence=0.5)
        self.assertEqual(progress, 0.0)

    def test_reset_clears_target_and_timer(self):
        clock = FakeClock()
        d = DwellDetector(duration_ms=600, clock=clock)
        d.update(0.5, 0.5)
        clock.advance(0.5)
        d.reset()
        self.assertEqual(d.progress(), 0.0)


class DrawDwellProgressTests(unittest.TestCase):
    def test_runs_without_error_on_a_real_frame(self):
        frame = np.zeros((480, 640, 3), dtype="uint8")
        draw_dwell_progress(frame, (320, 240), 0.0)
        draw_dwell_progress(frame, (320, 240), 0.5)
        draw_dwell_progress(frame, (320, 240), 1.0)
        self.assertTrue((frame != 0).any())  # something was actually drawn


if __name__ == "__main__":
    unittest.main()
