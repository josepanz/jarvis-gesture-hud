"""DoubleClickDetector (TASK-019, spec.md #12).

"Double click SHALL require: two valid click events + maximum_inter_click_interval.
Default SHOULD be approximately 400-500 ms." Wired into `GestureEngine`
(C-02, WORKPLAN.md §10, `hardening-and-polish`) - register_click() is called
on PINCH_UP (click completo), classifying it against the PREVIOUS completed
click rather than holding the first one back: "Single click is not
duplicated" (TASK-019's own acceptance criterion) is satisfied WITHOUT the
naive "hold back the first click to see if a second follows" design, which
would have added real, perceptible latency to the single most-used existing
interaction (left click). See gestures.py's `process()` for the gate and
main.py's `_dispatch_migrated()` for how the recognized second click is
re-anchored to the first click's screen position.
"""

import time

DEFAULT_MAX_INTERVAL_MS = 450


class DoubleClickDetector:
    def __init__(self, max_interval_ms=DEFAULT_MAX_INTERVAL_MS, clock=time.monotonic):
        self.max_interval_ms = max_interval_ms
        self._clock = clock
        self._last_click_time = None
        # V-09 (`openspec/changes/hardening-and-polish/WORKPLAN.md` §10):
        # diagnostico en vivo - el intervalo real del ultimo par de clicks
        # (entre o no dentro de max_interval_ms), para leer el numero real en
        # vez de estimarlo.
        self.last_interval_ms = None

    def register_click(self):
        """Call once per completed single click (e.g. on PINCH_UP). Returns
        "double" if this click closes a double-click within max_interval_ms of the
        previous one, else "single". After a "double" fires, the streak resets -
        a third rapid click starts a fresh pair, it does not chain into a triple."""
        now = self._clock()
        if self._last_click_time is not None:
            self.last_interval_ms = (now - self._last_click_time) * 1000
        is_double = self._last_click_time is not None and self.last_interval_ms <= self.max_interval_ms
        self._last_click_time = None if is_double else now
        return "double" if is_double else "single"

    def reset(self):
        self._last_click_time = None
