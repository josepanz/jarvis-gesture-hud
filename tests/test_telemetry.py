"""Unit tests for TelemetryManager/TelemetryEvent (TASK-034)."""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.telemetry import TelemetryEvent, TelemetryManager  # noqa: E402


class TelemetryEventTests(unittest.TestCase):
    def test_valid_event(self):
        e = TelemetryEvent(event="performance", metric="fps", timestamp=1.0, value=30)
        self.assertEqual(e.value, 30)
        self.assertEqual(e.metadata, {})

    def test_event_required(self):
        with self.assertRaises(ValueError):
            TelemetryEvent(event="", metric="fps", timestamp=1.0)

    def test_metric_required(self):
        with self.assertRaises(ValueError):
            TelemetryEvent(event="performance", metric="", timestamp=1.0)

    def test_timestamp_required_and_numeric(self):
        with self.assertRaises(ValueError):
            TelemetryEvent(event="performance", metric="fps", timestamp=None)
        with self.assertRaises(ValueError):
            TelemetryEvent(event="performance", metric="fps", timestamp="now")

    def test_metadata_must_be_dict(self):
        with self.assertRaises(ValueError):
            TelemetryEvent(event="performance", metric="fps", timestamp=1.0, metadata=["nope"])

    def test_value_is_unrestricted(self):
        TelemetryEvent(event="gesture", metric="success", timestamp=1.0, value=True)
        TelemetryEvent(event="command", metric="error", timestamp=1.0, value="boom")
        TelemetryEvent(event="performance", metric="fps", timestamp=1.0, value=None)

    def test_is_immutable(self):
        e = TelemetryEvent(event="performance", metric="fps", timestamp=1.0)
        with self.assertRaises(Exception):
            e.value = 99


class TelemetryManagerRecordTests(unittest.TestCase):
    def test_record_returns_the_event_and_appends_to_history(self):
        tm = TelemetryManager()
        event = tm.record("performance", "fps", 30)
        self.assertEqual(event.metric, "fps")
        self.assertEqual(tm.history(), [event])

    def test_record_defaults_timestamp_to_now(self):
        tm = TelemetryManager()
        before = time.time()
        event = tm.record("performance", "fps", 30)
        after = time.time()
        self.assertTrue(before <= event.timestamp <= after)

    def test_record_accepts_explicit_timestamp(self):
        tm = TelemetryManager()
        event = tm.record("performance", "fps", 30, timestamp=123.0)
        self.assertEqual(event.timestamp, 123.0)

    def test_record_without_sink_does_not_start_a_thread(self):
        tm = TelemetryManager()
        self.assertIsNone(tm._queue)


class TelemetryManagerHistoryTests(unittest.TestCase):
    def test_filter_by_event(self):
        tm = TelemetryManager()
        tm.record("performance", "fps", 30)
        tm.record("gesture", "confidence", 0.9)
        result = tm.history(event="gesture")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event, "gesture")

    def test_filter_by_metric(self):
        tm = TelemetryManager()
        tm.record("gesture", "confidence", 0.9)
        tm.record("gesture", "success", True)
        result = tm.history(metric="success")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].metric, "success")

    def test_filter_by_event_and_metric(self):
        tm = TelemetryManager()
        tm.record("gesture", "success", True)
        tm.record("command", "success", True)
        result = tm.history(event="command", metric="success")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event, "command")

    def test_limit_returns_most_recent(self):
        tm = TelemetryManager()
        for i in range(5):
            tm.record("performance", "fps", i)
        result = tm.history(limit=2)
        self.assertEqual([e.value for e in result], [3, 4])

    def test_history_is_bounded_by_max_history(self):
        tm = TelemetryManager(max_history=3)
        for i in range(5):
            tm.record("performance", "fps", i)
        result = tm.history()
        self.assertEqual([e.value for e in result], [2, 3, 4])

    def test_empty_history_returns_empty_list(self):
        self.assertEqual(TelemetryManager().history(), [])


class TelemetryManagerSinkTests(unittest.TestCase):
    def test_sink_receives_recorded_events(self):
        received = []
        tm = TelemetryManager(sink=received.append)
        tm.record("performance", "fps", 30)

        for _ in range(50):
            if received:
                break
            time.sleep(0.02)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].metric, "fps")

    def test_broken_sink_does_not_raise_from_record(self):
        def bad_sink(event):
            raise RuntimeError("sink exploded")

        tm = TelemetryManager(sink=bad_sink)
        event = tm.record("performance", "fps", 30)  # must not raise
        self.assertEqual(event.metric, "fps")

    def test_broken_sink_does_not_stop_later_events_from_recording(self):
        received = []

        def flaky_sink(event):
            if event.value == "bad":
                raise RuntimeError("sink exploded")
            received.append(event)

        tm = TelemetryManager(sink=flaky_sink)
        tm.record("performance", "fps", "bad")
        tm.record("performance", "fps", "good")

        for _ in range(50):
            if received:
                break
            time.sleep(0.02)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].value, "good")
        # both still landed in local history regardless of the sink's fate
        self.assertEqual(len(tm.history()), 2)


if __name__ == "__main__":
    unittest.main()
