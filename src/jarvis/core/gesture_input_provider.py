"""GestureInputProvider (TASK-045). Adapts the EXISTING jarvis.hand_tracker.HandTracker
+ jarvis.gestures.GestureEngine (both untouched) to the InputProvider contract -
does not change their behavior at all, just wraps their output as GestureEvent
instances.

`poll()` needs a camera frame each cycle, which the uniform zero-arg InputProvider
contract doesn't pass in directly - resolved by injecting a `frame_source`
callable at construction time (returns `(rgb_frame, w, h)` or None if no frame is
available this cycle), so poll() itself stays a plain zero-arg call like every
other provider's, with frame acquisition an implementation detail this class owns.

NOT wired into jarvis.main.JarvisApp - that already drives HandTracker/GestureEngine
directly and works; this is an alternative access path via the new abstraction, not
a replacement. See PHASE 10 task report.
"""

import time

from jarvis.core.events import GestureEvent
from jarvis.core.input_provider import InputProvider


class GestureInputProvider(InputProvider):
    def __init__(self, tracker, gesture_engine, screen_w, screen_h, frame_source, mirrored=True):
        self._tracker = tracker
        self._engine = gesture_engine
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._frame_source = frame_source
        self.mirrored = mirrored

    @property
    def source(self):
        return "CAMERA"

    def poll(self):
        frame = self._frame_source()
        if frame is None:
            return []
        rgb_frame, w, h = frame

        hands = self._tracker.process(rgb_frame, mirrored=self.mirrored)
        _screen_xy, cam_xy, events = self._engine.process(hands, w, h, self._screen_w, self._screen_h)

        now = time.time()
        return [
            GestureEvent(
                gesture_type=event_name,
                confidence=1.0,
                timestamp=now,
                source=self.source,
                state="ACTIVE",
                position=cam_xy,
            )
            for event_name in events
        ]
