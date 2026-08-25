"""PerformanceMetricsRecorder (TASK-035, spec.md #34).

Records: fps, frame_time, tracking_latency, classification_latency, intent_latency,
command_latency, end_to_end_latency - the exact 7 names spec.md #34 lists. Thin
wrapper over TelemetryManager (event="performance"). Standalone, not wired into the
live camera loop - see PHASE 8 task report.
"""


class PerformanceMetricsRecorder:
    def __init__(self, telemetry):
        self._telemetry = telemetry

    def record_fps(self, value):
        return self._telemetry.record("performance", "fps", value)

    def record_frame_time(self, ms):
        return self._telemetry.record("performance", "frame_time", ms)

    def record_tracking_latency(self, ms):
        return self._telemetry.record("performance", "tracking_latency", ms)

    def record_classification_latency(self, ms):
        return self._telemetry.record("performance", "classification_latency", ms)

    def record_intent_latency(self, ms):
        return self._telemetry.record("performance", "intent_latency", ms)

    def record_command_latency(self, ms):
        return self._telemetry.record("performance", "command_latency", ms)

    def record_end_to_end_latency(self, ms):
        return self._telemetry.record("performance", "end_to_end_latency", ms)
