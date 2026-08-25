"""ConsecutiveFrameDebouncer (TASK-015, spec.md #4).

"A gesture SHALL NOT normally execute from one frame. Default behavior SHOULD
require a configurable number of consecutive matching classifications." Standalone,
tested utility - not wired into GestureEngine (see gesture_state_machine.py's
docstring for why: it's a working, tested baseline, and retrofitting debounce onto
it isn't a mechanical/no-risk change).
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
