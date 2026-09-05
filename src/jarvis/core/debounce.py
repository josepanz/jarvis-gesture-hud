"""ConsecutiveFrameDebouncer (TASK-015, spec.md #4) + MissToleranceCounter
(A-02, WORKPLAN.md §9, `hardening-and-polish`).

"A gesture SHALL NOT normally execute from one frame. Default behavior SHOULD
require a configurable number of consecutive matching classifications."

Both classes are "N consecutive frames" counters, but for inverse purposes:
ConsecutiveFrameDebouncer counts consecutive HITS needed to GRANT a state
(debounce); MissToleranceCounter counts consecutive MISSES tolerated before
REVOKING one already granted (hysteresis, e.g. surviving one frame of
classification flicker mid-hold without dropping the hold's progress). Forcing
one to emulate the other is how this kind of refactor breaks - they live here
together, named, instead.
"""

DEFAULT_CONFIRMATION_FRAMES = 3


class ConsecutiveFrameDebouncer:
    def __init__(self, confirmation_frames=DEFAULT_CONFIRMATION_FRAMES):
        if confirmation_frames < 1:
            raise ValueError(f"confirmation_frames must be >= 1, got {confirmation_frames!r}")
        self.confirmation_frames = confirmation_frames
        self._key = None
        self._count = 0

    def observe(self, key):
        """Feed one frame's observation (e.g. a gesture_type string, or None for
        "nothing observed this frame"). Returns True once `key` has been observed
        on `confirmation_frames` consecutive calls (level-triggered: stays True
        while still held). A different key, or None, resets the streak."""
        if key is None or key != self._key:
            self._key = key
            self._count = 1 if key is not None else 0
        else:
            self._count += 1
        return key is not None and self._count >= self.confirmation_frames

    def reset(self):
        self._key = None
        self._count = 0


class MissToleranceCounter:
    """Counts consecutive "no match" observations while something is being held,
    without dropping it until `tolerance` misses in a row are exceeded - a single
    frame of classification flicker (landmark noise, NOT the thing being held
    disappearing) doesn't reset progress; `tolerance + 1` consecutive misses does."""

    def __init__(self, tolerance):
        if tolerance < 0:
            raise ValueError(f"tolerance must be >= 0, got {tolerance!r}")
        self.tolerance = tolerance
        self._misses = 0

    def observe(self, matched):
        """Feed one frame's observation: True if the held thing matched again
        (resets the miss streak), False if it didn't. Returns True while
        progress survives (misses still within tolerance), False once
        `tolerance` has been exceeded - the caller drops the held state then."""
        if matched:
            self._misses = 0
            return True
        self._misses += 1
        return self._misses <= self.tolerance

    def reset(self):
        self._misses = 0
