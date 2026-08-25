"""Unit tests for DoubleClickDetector (TASK-019)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.double_click import DoubleClickDetector  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class DoubleClickDetectorTests(unittest.TestCase):
    def test_default_max_interval_is_450ms(self):
        self.assertEqual(DoubleClickDetector().max_interval_ms, 450)

    def test_first_click_is_single(self):
        self.assertEqual(DoubleClickDetector().register_click(), "single")

    def test_second_click_within_interval_is_double(self):
        clock = FakeClock()
        d = DoubleClickDetector(clock=clock)
        d.register_click()
        clock.advance(0.2)
        self.assertEqual(d.register_click(), "double")

    def test_second_click_after_interval_is_single(self):
        clock = FakeClock()
        d = DoubleClickDetector(clock=clock)
        d.register_click()
        clock.advance(0.6)
        self.assertEqual(d.register_click(), "single")

    def test_third_click_after_a_double_starts_fresh(self):
        clock = FakeClock()
        d = DoubleClickDetector(clock=clock)
        d.register_click()
        clock.advance(0.1)
        self.assertEqual(d.register_click(), "double")
        clock.advance(0.1)
        self.assertEqual(d.register_click(), "single")  # not a triple-fire

    def test_reset_clears_pending_streak(self):
        clock = FakeClock()
        d = DoubleClickDetector(clock=clock)
        d.register_click()
        d.reset()
        clock.advance(0.1)
        self.assertEqual(d.register_click(), "single")


if __name__ == "__main__":
    unittest.main()
