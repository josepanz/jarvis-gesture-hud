"""InputProvider (TASK-044, spec.md #37, design.md #21).

"The architecture SHALL introduce a conceptual interface: InputProvider.
Implementations: GestureInputProvider, KeyboardInputProvider, VoiceInputProvider,
FutureVisionInputProvider. All providers SHALL generate intents or events consumed
by the same pipeline." (spec.md #37) "All providers produce compatible semantic
input." (design.md #21)

Reuses GestureEvent (TASK-001) as the shared event type every provider emits,
rather than building a second, near-duplicate event model. GestureEvent's
`gesture_type` field doubles as a general "what happened" tag (e.g. "KEY_PRESS" for
keyboard input, not just camera gestures), and every camera-specific field on it
(hand/position/velocity/duration_ms) is already optional - a keyboard or voice
event just leaves those as None and uses `metadata` instead. design.md #3's
suggested folder listing separately names a "core/events/input_event" file; this
project deliberately reuses GestureEvent instead - flagged here and in the PHASE 10
task report as an interpretation, not a literal reading of that structure sketch.

Standalone - NOT wired into jarvis.main.JarvisApp, which already drives
HandTracker/GestureEngine directly and works. See gesture_input_provider.py /
keyboard_input_provider.py / voice_input_provider.py for the three implementations,
and the PHASE 10 task report for why none of them replace main.py's existing loop.
"""

from abc import ABC, abstractmethod


class InputProvider(ABC):
    @property
    @abstractmethod
    def source(self):
        """The `source` value this provider stamps onto every GestureEvent it
        produces, e.g. "CAMERA" / "KEYBOARD" / "VOICE"."""

    @abstractmethod
    def poll(self):
        """Returns a list of GestureEvent produced since the last poll() call (may
        be empty - MUST NOT block, MUST NOT raise for "nothing happened")."""
