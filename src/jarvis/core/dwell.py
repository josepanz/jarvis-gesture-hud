"""DwellDetector (TASK-021, spec.md #17, design.md #18).

"The user points at a target and remains within a configured region for a
configured duration. Default: dwell.duration_ms = 600. During dwell the HUD SHALL
display progress. Movement beyond cancel_distance cancels dwell."

Standalone, tested detector + a pure `draw_dwell_progress()` rendering helper (so
"HUD progress displayed" has a real, working implementation) - NOT wired into
main.py's camera loop. No action in this app is currently bound to a dwell gesture,
so there is nothing concrete to trigger yet.
"""

import math
import time

DEFAULT_DURATION_MS = 600
DEFAULT_MAX_TARGET_DISTANCE = 0.05
DEFAULT_CANCEL_DISTANCE = 0.08


class DwellDetector:
    def __init__(
        self,
        duration_ms=DEFAULT_DURATION_MS,
        max_target_distance=DEFAULT_MAX_TARGET_DISTANCE,
        cancel_distance=DEFAULT_CANCEL_DISTANCE,
        clock=time.monotonic,
    ):
        self.duration_ms = duration_ms
        self.max_target_distance = max_target_distance
        self.cancel_distance = cancel_distance
        self._clock = clock
        self._target = None
        self._start_time = None

    def update(self, x, y, confidence=1.0, min_confidence=0.0):
        """Feed one frame's target position + optional detection confidence.
        Returns current progress in [0.0, 1.0]; 1.0 means dwell completed on this
        call (the caller should trigger its action and call reset())."""
        if confidence < min_confidence:
            self.reset()
            return 0.0

        if self._target is None:
            self._target = (x, y)
            self._start_time = self._clock()
            return 0.0

        tx, ty = self._target
        distance = math.hypot(x - tx, y - ty)
        if distance > self.cancel_distance:
            self._target = (x, y)
            self._start_time = self._clock()
            return 0.0

        return self.progress()

    def progress(self):
        if self._start_time is None:
            return 0.0
        elapsed_ms = (self._clock() - self._start_time) * 1000
        return min(1.0, elapsed_ms / self.duration_ms)

    def reset(self):
        self._target = None
        self._start_time = None


def draw_dwell_progress(frame, center, progress, radius=24, color=(0, 255, 255), track_color=(80, 80, 80)):
    """Draws a simple progress ring (progress in [0.0, 1.0]) around `center` on a
    cv2 BGR frame, in the same visual style as legend.py/hud_keyboard.py."""
    import cv2

    cx, cy = int(center[0]), int(center[1])
    cv2.circle(frame, (cx, cy), radius, track_color, 2)
    if progress > 0:
        end_angle = int(360 * min(1.0, progress))
        cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, end_angle, color, 3)
