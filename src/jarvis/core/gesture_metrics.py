"""GestureMetricsRecorder (TASK-036, spec.md #34).

Records: gesture, confidence, success, failure, duration. Thin wrapper over
TelemetryManager (event="gesture"), splitting success/failure into distinct metric
names per spec.md #34's gesture_success/gesture_failure split. Standalone, not
wired into the live camera loop - see PHASE 8 task report.
"""


class GestureMetricsRecorder:
    def __init__(self, telemetry):
        self._telemetry = telemetry

    def record_gesture(self, gesture_type, confidence, success, duration_ms=None):
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError(f"confidence must be a number, got {confidence!r}")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {confidence!r}")

        metadata = {"gesture": gesture_type}
        self._telemetry.record("gesture", "confidence", confidence, metadata=metadata)
        self._telemetry.record("gesture", "success" if success else "failure", True, metadata=metadata)
        if duration_ms is not None:
            self._telemetry.record("gesture", "duration", duration_ms, metadata=metadata)
