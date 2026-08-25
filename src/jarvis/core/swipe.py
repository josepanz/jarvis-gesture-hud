"""SwipeDetector (TASK-020, spec.md #16).

"The Gesture Engine SHALL detect SWIPE_LEFT/RIGHT/UP/DOWN, using start_position,
end_position, delta, duration, velocity. Minimum displacement and velocity MUST be
configurable. A swipe MUST NOT be triggered by slow cursor movement."

Standalone, tested detector operating in the same normalized [0,1] landmark
coordinate space GestureEngine already uses - NOT wired into it. No existing
gesture or action maps to "swipe" in this app; wiring it in without a defined
target action would be guessing at scope beyond what this task asks for.
"""

import math

DEFAULT_MIN_DISTANCE = 0.15
DEFAULT_MIN_VELOCITY = 0.5  # normalized units per second
DEFAULT_MAX_DURATION_MS = 600


class SwipeDetector:
    def __init__(
        self,
        min_distance=DEFAULT_MIN_DISTANCE,
        min_velocity=DEFAULT_MIN_VELOCITY,
        max_duration_ms=DEFAULT_MAX_DURATION_MS,
    ):
        self.min_distance = min_distance
        self.min_velocity = min_velocity
        self.max_duration_ms = max_duration_ms
        self._start = None  # (x, y, timestamp)

    def update(self, x, y, timestamp):
        """Feed one frame's tracked position + timestamp (seconds). Returns
        "SWIPE_LEFT"/"SWIPE_RIGHT"/"SWIPE_UP"/"SWIPE_DOWN" or None. Restarts its
        own tracking window after firing, timing out, or losing velocity, so the
        caller doesn't need to call reset() between swipes."""
        if self._start is None:
            self._start = (x, y, timestamp)
            return None

        sx, sy, st = self._start
        dt_ms = (timestamp - st) * 1000

        if dt_ms > self.max_duration_ms:
            self._start = (x, y, timestamp)
            return None

        dx, dy = x - sx, y - sy
        distance = math.hypot(dx, dy)
        if distance < self.min_distance:
            return None  # keep the window open - might still become a swipe

        duration_s = max(dt_ms / 1000, 1e-6)
        velocity = distance / duration_s
        if velocity < self.min_velocity:
            self._start = (x, y, timestamp)  # moved far but too slowly - not a swipe
            return None

        self._start = None
        if abs(dx) >= abs(dy):
            return "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
        return "SWIPE_DOWN" if dy > 0 else "SWIPE_UP"

    def reset(self):
        self._start = None
