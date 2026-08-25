"""Unit tests for PerformanceMetricsRecorder (TASK-035)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.performance_metrics import PerformanceMetricsRecorder  # noqa: E402
from jarvis.core.telemetry import TelemetryManager  # noqa: E402


class PerformanceMetricsRecorderTests(unittest.TestCase):
    def setUp(self):
        self.telemetry = TelemetryManager()
        self.recorder = PerformanceMetricsRecorder(self.telemetry)

    def _assert_recorded(self, metric, value):
        events = self.telemetry.history(event="performance", metric=metric)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].value, value)

    def test_record_fps(self):
        self.recorder.record_fps(30)
        self._assert_recorded("fps", 30)

    def test_record_frame_time(self):
        self.recorder.record_frame_time(16.6)
        self._assert_recorded("frame_time", 16.6)

    def test_record_tracking_latency(self):
        self.recorder.record_tracking_latency(5.0)
        self._assert_recorded("tracking_latency", 5.0)

    def test_record_classification_latency(self):
        self.recorder.record_classification_latency(2.0)
        self._assert_recorded("classification_latency", 2.0)

    def test_record_intent_latency(self):
        self.recorder.record_intent_latency(1.0)
        self._assert_recorded("intent_latency", 1.0)

    def test_record_command_latency(self):
        self.recorder.record_command_latency(8.0)
        self._assert_recorded("command_latency", 8.0)

    def test_record_end_to_end_latency(self):
        self.recorder.record_end_to_end_latency(34.0)
        self._assert_recorded("end_to_end_latency", 34.0)

    def test_all_seven_metric_names_match_spec(self):
        self.recorder.record_fps(1)
        self.recorder.record_frame_time(1)
        self.recorder.record_tracking_latency(1)
        self.recorder.record_classification_latency(1)
        self.recorder.record_intent_latency(1)
        self.recorder.record_command_latency(1)
        self.recorder.record_end_to_end_latency(1)
        recorded_metrics = {e.metric for e in self.telemetry.history(event="performance")}
        self.assertEqual(
            recorded_metrics,
            {
                "fps",
                "frame_time",
                "tracking_latency",
                "classification_latency",
                "intent_latency",
                "command_latency",
                "end_to_end_latency",
            },
        )


if __name__ == "__main__":
    unittest.main()
