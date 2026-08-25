"""Unit tests for CommandMetricsRecorder (TASK-037)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.command_metrics import CommandMetricsRecorder  # noqa: E402
from jarvis.core.commands import Command, CommandMetadata, CommandResult  # noqa: E402
from jarvis.core.telemetry import TelemetryManager  # noqa: E402


class _DummyCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="VolumeUp", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return CommandResult.ok()


class CommandMetricsRecorderTests(unittest.TestCase):
    def setUp(self):
        self.telemetry = TelemetryManager()
        self.recorder = CommandMetricsRecorder(self.telemetry)

    def test_success_records_success_metric_not_failure(self):
        self.recorder.record_command("VolumeUp", success=True)
        self.assertEqual(len(self.telemetry.history(event="command", metric="success")), 1)
        self.assertEqual(len(self.telemetry.history(event="command", metric="failure")), 0)

    def test_failure_records_failure_metric_not_success(self):
        self.recorder.record_command("VolumeUp", success=False)
        self.assertEqual(len(self.telemetry.history(event="command", metric="failure")), 1)
        self.assertEqual(len(self.telemetry.history(event="command", metric="success")), 0)

    def test_duration_recorded_when_given(self):
        self.recorder.record_command("VolumeUp", success=True, duration_ms=12.0)
        events = self.telemetry.history(event="command", metric="duration")
        self.assertEqual(events[0].value, 12.0)

    def test_duration_omitted_when_not_given(self):
        self.recorder.record_command("VolumeUp", success=True)
        self.assertEqual(len(self.telemetry.history(event="command", metric="duration")), 0)

    def test_error_recorded_when_given(self):
        self.recorder.record_command("LockSession", success=False, error="no display manager")
        events = self.telemetry.history(event="command", metric="error")
        self.assertEqual(events[0].value, "no display manager")

    def test_error_omitted_when_not_given(self):
        self.recorder.record_command("VolumeUp", success=True)
        self.assertEqual(len(self.telemetry.history(event="command", metric="error")), 0)

    def test_metadata_carries_command_name(self):
        self.recorder.record_command("VolumeUp", success=True)
        events = self.telemetry.history(event="command", metric="success")
        self.assertEqual(events[0].metadata, {"command": "VolumeUp"})

    def test_record_from_command_result_success(self):
        cmd = _DummyCommand()
        result = CommandResult.ok(duration_ms=5.0)
        self.recorder.record_from_command_result(cmd, result)
        self.assertEqual(len(self.telemetry.history(event="command", metric="success")), 1)
        self.assertEqual(self.telemetry.history(event="command", metric="duration")[0].value, 5.0)

    def test_record_from_command_result_failure(self):
        cmd = _DummyCommand()
        result = CommandResult.failed(error="device missing")
        self.recorder.record_from_command_result(cmd, result)
        self.assertEqual(len(self.telemetry.history(event="command", metric="failure")), 1)
        self.assertEqual(self.telemetry.history(event="command", metric="error")[0].value, "device missing")


if __name__ == "__main__":
    unittest.main()
