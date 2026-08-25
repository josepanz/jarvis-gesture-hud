"""Unit tests for debug telemetry HUD helpers (TASK-038)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from jarvis.core.debug_telemetry import draw_debug_telemetry, format_debug_telemetry  # noqa: E402


def _blank_frame():
    return np.zeros((480, 640, 3), dtype="uint8")


class FormatDebugTelemetryTests(unittest.TestCase):
    def test_all_none_returns_empty_list(self):
        self.assertEqual(format_debug_telemetry(), [])

    def test_single_field(self):
        self.assertEqual(format_debug_telemetry(fps=30), ["FPS: 30"])

    def test_confidence_uses_percentage_formatting(self):
        self.assertEqual(format_debug_telemetry(confidence=0.94), ["Confidence: 94%"])

    def test_latency_gets_ms_suffix(self):
        self.assertEqual(format_debug_telemetry(latency_ms=12), ["Latency: 12ms"])

    def test_field_order_matches_spec_list(self):
        lines = format_debug_telemetry(
            fps=30, gesture="PINCH", confidence=0.9, intent="SELECT", command="VolumeUp",
            latency_ms=12, profile="gaming",
        )
        self.assertEqual(
            lines,
            [
                "FPS: 30",
                "Gesture: PINCH",
                "Confidence: 90%",
                "Intent: SELECT",
                "Command: VolumeUp",
                "Latency: 12ms",
                "Profile: gaming",
            ],
        )

    def test_subset_of_fields_skips_the_rest(self):
        lines = format_debug_telemetry(gesture="PINCH", profile="gaming")
        self.assertEqual(lines, ["Gesture: PINCH", "Profile: gaming"])


class DrawDebugTelemetryTests(unittest.TestCase):
    def test_disabled_draws_nothing_and_leaves_frame_untouched(self):
        frame = _blank_frame()
        drawn = draw_debug_telemetry(frame, enabled=False, fps=30, gesture="PINCH")
        self.assertEqual(drawn, [])
        self.assertFalse((frame != 0).any())

    def test_enabled_draws_and_returns_the_lines(self):
        frame = _blank_frame()
        drawn = draw_debug_telemetry(frame, enabled=True, fps=30, gesture="PINCH")
        self.assertEqual(drawn, ["FPS: 30", "Gesture: PINCH"])
        self.assertTrue((frame != 0).any())

    def test_enabled_with_no_fields_draws_nothing(self):
        frame = _blank_frame()
        drawn = draw_debug_telemetry(frame, enabled=True)
        self.assertEqual(drawn, [])
        self.assertFalse((frame != 0).any())


if __name__ == "__main__":
    unittest.main()
