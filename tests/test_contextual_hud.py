"""Unit tests for ContextualHudRenderer (TASK-033)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from jarvis.core.contextual_hud import ContextualHudRenderer  # noqa: E402


def _blank_frame():
    return np.zeros((480, 640, 3), dtype="uint8")


class ContextualHudRendererTests(unittest.TestCase):
    def test_idle_non_debug_draws_nothing(self):
        renderer = ContextualHudRenderer(debug=False)
        frame = _blank_frame()
        drawn = renderer.render(frame, "IDLE")
        self.assertEqual(drawn, [])
        self.assertFalse((frame != 0).any())  # frame genuinely untouched

    def test_idle_in_debug_mode_still_shows_telemetry(self):
        renderer = ContextualHudRenderer(debug=True)
        frame = _blank_frame()
        drawn = renderer.render(frame, "IDLE", telemetry={"fps": 30})
        self.assertIn("telemetry", drawn)

    def test_gesture_detected_shows_gesture_but_not_intent(self):
        renderer = ContextualHudRenderer()
        frame = _blank_frame()
        drawn = renderer.render(
            frame,
            "GESTURE_DETECTED",
            gesture={"gesture_type": "PINCH", "confidence": 0.9},
            intent={"name": "SELECT"},
        )
        self.assertIn("gesture", drawn)
        self.assertNotIn("intent", drawn)  # progressive disclosure: too early for intent

    def test_confirming_shows_gesture_and_intent(self):
        renderer = ContextualHudRenderer()
        frame = _blank_frame()
        drawn = renderer.render(
            frame,
            "CONFIRMING",
            gesture={"gesture_type": "PINCH", "confidence": 0.9},
            intent={"name": "SELECT", "target": "hud_button"},
        )
        self.assertIn("gesture", drawn)
        self.assertIn("intent", drawn)

    def test_dwell_shown_whenever_provided_regardless_of_state(self):
        renderer = ContextualHudRenderer()
        frame = _blank_frame()
        drawn = renderer.render(
            frame, "TRACKING", dwell={"center": (100, 100), "progress": 0.4, "duration_ms": 600}
        )
        self.assertIn("dwell", drawn)

    def test_telemetry_hidden_outside_debug_mode(self):
        renderer = ContextualHudRenderer(debug=False)
        frame = _blank_frame()
        drawn = renderer.render(frame, "TRACKING", telemetry={"fps": 30})
        self.assertNotIn("telemetry", drawn)

    def test_non_idle_with_nothing_to_show_draws_nothing(self):
        renderer = ContextualHudRenderer()
        frame = _blank_frame()
        drawn = renderer.render(frame, "TRACKING")
        self.assertEqual(drawn, [])


if __name__ == "__main__":
    unittest.main()
