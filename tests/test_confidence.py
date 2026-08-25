"""Unit tests for ConfidenceFilter (TASK-016)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.confidence import ConfidenceFilter, format_confidence  # noqa: E402
from jarvis.core.events import GestureEvent  # noqa: E402


class ConfidenceFilterTests(unittest.TestCase):
    def test_default_minimum_is_070(self):
        self.assertEqual(ConfidenceFilter().minimum_confidence, 0.70)

    def test_rejects_out_of_range_minimum(self):
        with self.assertRaises(ValueError):
            ConfidenceFilter(minimum_confidence=1.5)

    def test_accepts_raw_float_above_threshold(self):
        self.assertTrue(ConfidenceFilter(0.7).accepts(0.9))

    def test_rejects_raw_float_below_threshold(self):
        self.assertFalse(ConfidenceFilter(0.7).accepts(0.5))

    def test_boundary_is_inclusive(self):
        self.assertTrue(ConfidenceFilter(0.7).accepts(0.7))

    def test_accepts_gesture_event_via_duck_typing(self):
        event = GestureEvent(
            gesture_type="PINCH", confidence=0.95, timestamp=1.0, source="CAMERA", state="ACTIVE"
        )
        self.assertTrue(ConfidenceFilter(0.7).accepts(event))

    def test_rejects_low_confidence_gesture_event(self):
        event = GestureEvent(
            gesture_type="PINCH", confidence=0.2, timestamp=1.0, source="CAMERA", state="ACTIVE"
        )
        self.assertFalse(ConfidenceFilter(0.7).accepts(event))


class FormatConfidenceTests(unittest.TestCase):
    def test_formats_as_rounded_percentage(self):
        self.assertEqual(format_confidence(0.94), "94%")
        self.assertEqual(format_confidence(1.0), "100%")
        self.assertEqual(format_confidence(0.0), "0%")


if __name__ == "__main__":
    unittest.main()
