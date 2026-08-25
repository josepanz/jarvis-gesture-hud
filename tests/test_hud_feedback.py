"""Unit tests for HUD feedback rendering helpers (TASK-030/031/032)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from jarvis.core.hud_feedback import (  # noqa: E402
    draw_dwell_reticle,
    draw_gesture_feedback,
    draw_intent_feedback,
    format_gesture_feedback,
    format_intent_feedback,
    format_remaining_time,
)


def _blank_frame():
    return np.zeros((480, 640, 3), dtype="uint8")


class FormatGestureFeedbackTests(unittest.TestCase):
    def test_includes_gesture_confidence_and_state(self):
        text = format_gesture_feedback("PINCH", 0.94, "ACTIVE")
        self.assertIn("PINCH", text)
        self.assertIn("94%", text)
        self.assertIn("ACTIVE", text)


class FormatIntentFeedbackTests(unittest.TestCase):
    def test_includes_intent_target_and_action(self):
        text = format_intent_feedback("SELECT", "hud_button", "PressKey(space)")
        self.assertIn("SELECT", text)
        self.assertIn("hud_button", text)
        self.assertIn("PressKey(space)", text)

    def test_handles_missing_target_and_action_gracefully(self):
        text = format_intent_feedback("SELECT", None, None)
        self.assertEqual(text, "SELECT")


class FormatRemainingTimeTests(unittest.TestCase):
    def test_zero_progress_is_full_duration(self):
        self.assertEqual(format_remaining_time(0.0, 600), "600ms")

    def test_full_progress_is_zero_remaining(self):
        self.assertEqual(format_remaining_time(1.0, 600), "0ms")

    def test_half_progress_is_half_duration(self):
        self.assertEqual(format_remaining_time(0.5, 600), "300ms")

    def test_never_goes_negative(self):
        self.assertEqual(format_remaining_time(1.5, 600), "0ms")


class DrawingHelpersRunWithoutErrorTests(unittest.TestCase):
    def test_draw_gesture_feedback(self):
        frame = _blank_frame()
        draw_gesture_feedback(frame, "PINCH", 0.9, "ACTIVE")
        self.assertTrue((frame != 0).any())

    def test_draw_intent_feedback(self):
        frame = _blank_frame()
        draw_intent_feedback(frame, "SELECT", "hud_button", "PressKey(space)")
        self.assertTrue((frame != 0).any())

    def test_draw_dwell_reticle_all_states(self):
        for state in ("idle", "targeting", "confirming", "selected", "unknown_state"):
            frame = _blank_frame()
            draw_dwell_reticle(frame, (320, 240), 0.5, 600, hud_state=state)
            self.assertTrue((frame != 0).any())


if __name__ == "__main__":
    unittest.main()
