"""CommandMetricsRecorder (TASK-037, spec.md #34).

Records: command, success, failure, duration, error. Thin wrapper over
TelemetryManager (event="command"), splitting success/failure per spec.md #34's
command_success/command_failure split. `record_from_command_result` is shaped to
match `jarvis.core.command_bus.CommandBus`'s `on_result(command, result)` hook
exactly, the same convenience pattern already used by
`jarvis.core.feedback.FeedbackManager.notify_command_result` - NOT wired to
CommandBus automatically. Standalone, not wired into the live camera loop - see
PHASE 8 task report.
"""


class CommandMetricsRecorder:
    def __init__(self, telemetry):
        self._telemetry = telemetry

    def record_command(self, command_name, success, duration_ms=None, error=None):
        metadata = {"command": command_name}
        self._telemetry.record("command", "success" if success else "failure", True, metadata=metadata)
        if duration_ms is not None:
            self._telemetry.record("command", "duration", duration_ms, metadata=metadata)
        if error is not None:
            self._telemetry.record("command", "error", error, metadata=metadata)

    def record_from_command_result(self, command, result):
        self.record_command(command.metadata.name, result.success, result.duration_ms, result.error)
