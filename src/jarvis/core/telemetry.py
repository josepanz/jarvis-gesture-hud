"""TelemetryManager (TASK-034, spec.md #34/#35, design.md #19, apply.md #18).

"Telemetry SHALL capture: fps, frame_time, tracking_latency, classification_latency,
intent_latency, command_latency, end_to_end_latency, gesture_confidence,
gesture_success, gesture_failure, command_success, command_failure. Telemetry MUST
be asynchronous or lightweight enough not to block the vision loop." (spec.md #34)

"Telemetry SHALL remain local by default. No telemetry SHALL be uploaded externally
unless a future feature explicitly enables it." (spec.md #35) - there is no network
code anywhere in this project; `sink` below is local-only by construction. A caller
COULD point it at something remote, but nothing here does.

"Vision loop -> Telemetry event -> Queue -> Telemetry worker -> Local storage/log.
The camera loop MUST NOT wait for disk I/O." (design.md #19)

"Telemetry MUST NEVER become a hard dependency for normal operation. If telemetry
fails: application continues" (apply.md #18)

Design: `record()` is synchronous and O(1) (an in-memory deque append) - this alone
satisfies spec.md #34's "lightweight enough" clause, no threading required for the
common case. The optional `sink` (where real I/O would actually happen) is
dispatched on a background daemon thread draining a queue, matching the async
pattern `jarvis.voice.VoiceJarvis` already uses in this codebase - only that part
needs to be async, per design.md #19's specific concern about disk I/O.

Standalone, tested - NOT wired into `jarvis.main.JarvisApp`'s live camera loop.
See jarvis.core.performance_metrics / gesture_metrics / command_metrics for the
typed recorders built on top of this, and jarvis.core.debug_telemetry for the
rendering counterpart - none of them are wired in either (see PHASE 8 task report).
"""

import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TelemetryEvent:
    event: str
    metric: str
    timestamp: float
    value: object = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.event, str) or not self.event:
            raise ValueError(f"event must be a non-empty string, got {self.event!r}")
        if not isinstance(self.metric, str) or not self.metric:
            raise ValueError(f"metric must be a non-empty string, got {self.metric!r}")
        if self.timestamp is None or isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise ValueError(f"timestamp must be a number, got {self.timestamp!r}")
        if not isinstance(self.metadata, dict):
            raise ValueError(f"metadata must be a dict, got {self.metadata!r}")


class TelemetryManager:
    def __init__(self, sink=None, max_history=500, logger=None):
        self._history = deque(maxlen=max_history)
        self._sink = sink
        self._logger = logger or logging.getLogger("jarvis.telemetry")
        self._queue = None
        if sink is not None:
            self._queue = queue.Queue()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def record(self, event, metric, value=None, metadata=None, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        telemetry_event = TelemetryEvent(
            event=event, metric=metric, timestamp=ts, value=value, metadata=metadata or {}
        )
        self._history.append(telemetry_event)
        if self._queue is not None:
            self._queue.put(telemetry_event)
        return telemetry_event

    def _worker(self):
        while True:
            telemetry_event = self._queue.get()
            try:
                self._sink(telemetry_event)
            except Exception:
                self._logger.exception(
                    "telemetry sink failed for %s/%s", telemetry_event.event, telemetry_event.metric
                )

    def history(self, event=None, metric=None, limit=None):
        items = list(self._history)
        if event is not None:
            items = [e for e in items if e.event == event]
        if metric is not None:
            items = [e for e in items if e.metric == metric]
        if limit is not None:
            items = items[-limit:]
        return items
