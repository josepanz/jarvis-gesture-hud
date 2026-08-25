"""Unit tests for ConsecutiveFrameDebouncer (TASK-015)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.debounce import ConsecutiveFrameDebouncer  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
