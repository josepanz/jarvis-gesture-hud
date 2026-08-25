"""KeyboardInputProvider (TASK-046). Adapts a raw key-code source (e.g.
`cv2.waitKey(1) & 0xFF`, as jarvis.main.JarvisApp already uses) to the
InputProvider contract.

`key_source` is injected at construction (a zero-arg callable returning the next
raw key code, or None/255 for "no key this cycle" - 255/0xFF is what cv2.waitKey
returns when nothing was pressed) so this class has no hard dependency on cv2 or
real keyboard hardware, and is fully testable with a fake.

NOT wired into jarvis.main.JarvisApp - that already handles q/h/m/+/- directly and
works; this is an alternative access path via the new abstraction. See PHASE 10
task report.
"""

import time

from jarvis.core.events import GestureEvent
from jarvis.core.input_provider import InputProvider

_NO_KEY = 255  # cv2.waitKey(...) & 0xFF returns this when no key was pressed


class KeyboardInputProvider(InputProvider):
    def __init__(self, key_source):
        self._key_source = key_source

    @property
    def source(self):
        return "KEYBOARD"

    def poll(self):
        key = self._key_source()
        if key is None or key == _NO_KEY:
            return []

        try:
            char = chr(key)
        except (ValueError, OverflowError):
            char = None

        return [
            GestureEvent(
                gesture_type="KEY_PRESS",
                confidence=1.0,
                timestamp=time.time(),
                source=self.source,
                state="ACTIVE",
                metadata={"key_code": key, "char": char},
            )
        ]
