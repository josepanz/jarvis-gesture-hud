"""Unit tests for ConsecutiveFrameDebouncer (TASK-015) and MissToleranceCounter
(A-02, WORKPLAN.md §9, `hardening-and-polish`)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.debounce import ConsecutiveFrameDebouncer, MissToleranceCounter  # noqa: E402


class ConsecutiveFrameDebouncerTests(unittest.TestCase):
    def test_default_confirmation_frames_is_three(self):
        self.assertEqual(ConsecutiveFrameDebouncer().confirmation_frames, 3)

    def test_rejects_invalid_confirmation_frames(self):
        with self.assertRaises(ValueError):
            ConsecutiveFrameDebouncer(confirmation_frames=0)

    def test_does_not_confirm_before_threshold(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=3)
        self.assertFalse(d.observe("PINCH"))
        self.assertFalse(d.observe("PINCH"))

    def test_confirms_exactly_at_threshold(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=3)
        d.observe("PINCH")
        d.observe("PINCH")
        self.assertTrue(d.observe("PINCH"))

    def test_stays_confirmed_while_held(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=2)
        d.observe("PINCH")
        self.assertTrue(d.observe("PINCH"))
        self.assertTrue(d.observe("PINCH"))
        self.assertTrue(d.observe("PINCH"))

    def test_switching_key_resets_the_streak(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=2)
        d.observe("PINCH")
        self.assertTrue(d.observe("PINCH"))
        self.assertFalse(d.observe("FIST"))  # streak restarts for the new key
        self.assertTrue(d.observe("FIST"))

    def test_none_resets_the_streak(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=2)
        d.observe("PINCH")
        self.assertFalse(d.observe(None))
        self.assertFalse(d.observe("PINCH"))
        self.assertTrue(d.observe("PINCH"))

    def test_reset_clears_state(self):
        d = ConsecutiveFrameDebouncer(confirmation_frames=2)
        d.observe("PINCH")
        d.reset()
        self.assertFalse(d.observe("PINCH"))


class MissToleranceCounterTests(unittest.TestCase):
    def test_rejects_negative_tolerance(self):
        with self.assertRaises(ValueError):
            MissToleranceCounter(tolerance=-1)

    def test_zero_misses_survives(self):
        c = MissToleranceCounter(tolerance=3)
        self.assertTrue(c.observe(True))

    def test_survives_exactly_tolerance_consecutive_misses(self):
        c = MissToleranceCounter(tolerance=3)
        self.assertTrue(c.observe(False))
        self.assertTrue(c.observe(False))
        self.assertTrue(c.observe(False))

    def test_fails_on_the_miss_after_tolerance(self):
        c = MissToleranceCounter(tolerance=3)
        c.observe(False)
        c.observe(False)
        c.observe(False)
        self.assertFalse(c.observe(False))

    def test_a_match_resets_the_miss_streak(self):
        c = MissToleranceCounter(tolerance=1)
        c.observe(False)
        self.assertTrue(c.observe(True))  # match resets - back to 0 misses
        self.assertTrue(c.observe(False))  # 1st miss again, still within tolerance
        self.assertFalse(c.observe(False))  # 2nd miss in a row, exceeds tolerance=1

    def test_reset_clears_the_miss_streak(self):
        c = MissToleranceCounter(tolerance=1)
        c.observe(False)
        c.reset()
        self.assertTrue(c.observe(False))  # counts as the 1st miss again, not the 2nd


if __name__ == "__main__":
    unittest.main()
