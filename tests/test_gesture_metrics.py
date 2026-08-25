"""Unit tests for GestureMetricsRecorder (TASK-036)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.gesture_metrics import GestureMetricsRecorder  # noqa: E402
from jarvis.core.telemetry import TelemetryManager  # noqa: E402


class GestureMetricsRecorderTests(unittest.TestCase):
    def setUp(self):
        self.telemetry = TelemetryManager()
        self.recorder = GestureMetricsRecorder(self.telemetry)

    def test_records_confidence_with_gesture_metadata(self):
        self.recorder.record_gesture("PINCH", 0.94, success=True)
        events = self.telemetry.history(event="gesture", metric="confidence")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].value, 0.94)
        self.assertEqual(events[0].metadata, {"gesture": "PINCH"})

    def test_success_records_success_metric_not_failure(self):
        self.recorder.record_gesture("PINCH", 0.9, success=True)
        self.assertEqual(len(self.telemetry.history(event="gesture", metric="success")), 1)
        self.assertEqual(len(self.telemetry.history(event="gesture", metric="failure")), 0)

    def test_failure_records_failure_metric_not_success(self):
        self.recorder.record_gesture("PINCH", 0.9, success=False)
        self.assertEqual(len(self.telemetry.history(event="gesture", metric="failure")), 1)
        self.assertEqual(len(self.telemetry.history(event="gesture", metric="success")), 0)

    def test_duration_recorded_when_given(self):
        self.recorder.record_gesture("PINCH", 0.9, success=True, duration_ms=120)
        events = self.telemetry.history(event="gesture", metric="duration")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].value, 120)

    def test_duration_omitted_when_not_given(self):
        self.recorder.record_gesture("PINCH", 0.9, success=True)
        self.assertEqual(len(self.telemetry.history(event="gesture", metric="duration")), 0)

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            self.recorder.record_gesture("PINCH", 1.5, success=True)
        with self.assertRaises(ValueError):
            self.recorder.record_gesture("PINCH", -0.1, success=True)

    def test_confidence_must_be_numeric(self):
        with self.assertRaises(ValueError):
            self.recorder.record_gesture("PINCH", "high", success=True)


if __name__ == "__main__":
    unittest.main()
