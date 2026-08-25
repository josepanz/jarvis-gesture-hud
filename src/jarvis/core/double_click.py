"""DoubleClickDetector (TASK-019, spec.md #12).

"Double click SHALL require: two valid click events + maximum_inter_click_interval.
Default SHOULD be approximately 400-500 ms." Standalone, tested classifier - NOT
wired into GestureEngine's PINCH_DOWN/PINCH_UP handling.

Why not wired in: nothing in this app currently maps double-click to any action, and
"Single click is not duplicated" (TASK-019's own acceptance criterion) requires
holding back the FIRST click's firing until the interval window closes to see if a
second one follows - that is a real, perceptible latency regression on the single
most-used existing interaction (left click) unless done carefully. Wiring this in
is a follow-up decision, not a mechanical one.
"""

import time

DEFAULT_MAX_INTERVAL_MS = 450


class DoubleClickDetector:
    def __init__(self, max_interval_ms=DEFAULT_MAX_INTERVAL_MS, clock=time.monotonic):
        self.max_interval_ms = max_interval_ms
        self._clock = clock
        self._last_click_time = None

    def register_click(self):
        """Call once per completed single click (e.g. on PINCH_UP). Returns
        "double" if this click closes a double-click within max_interval_ms of the
        previous one, else "single". After a "double" fires, the streak resets -
        a third rapid click starts a fresh pair, it does not chain into a triple."""
        now = self._clock()
        is_double = (
            self._last_click_time is not None
            and (now - self._last_click_time) * 1000 <= self.max_interval_ms
        )
        self._last_click_time = None if is_double else now
        return "double" if is_double else "single"

    def reset(self):
        self._last_click_time = None
