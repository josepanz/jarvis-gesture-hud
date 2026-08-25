"""TASK-049: verify gesture -> intent, keyboard -> intent, and voice -> intent can
all reach CommandBus - the actual end-to-end demonstration, not just an assertion
in a report. CrossPlatformOS is mocked so this never locks the real session.
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.system import LockSessionCommand  # noqa: E402
from jarvis.core.command_bus import CommandBus  # noqa: E402
from jarvis.core.gesture_input_provider import GestureInputProvider  # noqa: E402
from jarvis.core.intent_resolution import (  # noqa: E402
    IntentCommandResolver,
    gesture_event_to_intent,
    keyboard_event_to_intent,
)
from jarvis.core.keyboard_input_provider import KeyboardInputProvider  # noqa: E402
from jarvis.core.voice_intent_resolver import VoiceIntentResolver  # noqa: E402
from jarvis.gestures import GestureEngine  # noqa: E402
from jarvis.hand_tracker import Hand  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")


def _shaka_hand(cx=0.5, cy=0.5):
    """Held Shaka pose -> GestureEngine fires LOCK_SESSION after config.LOCK_HOLD_SECONDS."""
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[20] = Landmark(cx, cy - 0.1, 0)
    pts[18] = Landmark(cx, cy, 0)
    pts[4] = Landmark(cx - 0.1, cy - 0.1, 0)
    pts[2] = Landmark(cx - 0.05, cy, 0)
    pts[8] = Landmark(cx, cy + 0.05, 0)
    pts[6] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx, cy + 0.05, 0)
    pts[10] = Landmark(cx, cy, 0)
    pts[16] = Landmark(cx, cy + 0.05, 0)
    pts[14] = Landmark(cx, cy, 0)
    return pts


class FakeTracker:
    def __init__(self, hands):
        self.hands = hands

    def process(self, rgb_frame, mirrored=True):
        return self.hands


def _make_resolver():
    resolver = IntentCommandResolver()
    resolver.register("LOCK_SESSION", lambda intent: LockSessionCommand())
    return resolver


class IntentConvergenceTests(unittest.TestCase):
    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_gesture_source_reaches_command_bus(self, mock_os):
        engine = GestureEngine()
        engine.lock_start_time = __import__("time").time() - 2.0  # simulate the hold already elapsed
        tracker = FakeTracker(hands=[Hand(_shaka_hand(), "Right")])
        provider = GestureInputProvider(tracker, engine, 1920, 1080, frame_source=lambda: (object(), 640, 480))

        events = provider.poll()
        self.assertIn("LOCK_SESSION", [e.gesture_type for e in events])
        gesture_event = next(e for e in events if e.gesture_type == "LOCK_SESSION")

        intent = gesture_event_to_intent(gesture_event)
        self.assertEqual(intent.name, "LOCK_SESSION")
        self.assertEqual(intent.source, "CAMERA")

        command = _make_resolver().resolve(intent)
        result = CommandBus().dispatch(command)

        self.assertTrue(result.success)
        mock_os.lock_session.assert_called_once()

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_keyboard_source_reaches_command_bus(self, mock_os):
        provider = KeyboardInputProvider(key_source=lambda: ord("l"))
        events = provider.poll()
        keyboard_event = events[0]

        intent = keyboard_event_to_intent(keyboard_event, key_bindings={"l": "LOCK_SESSION"})
        self.assertEqual(intent.name, "LOCK_SESSION")
        self.assertEqual(intent.source, "KEYBOARD")

        command = _make_resolver().resolve(intent)
        result = CommandBus().dispatch(command)

        self.assertTrue(result.success)
        mock_os.lock_session.assert_called_once()

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_voice_source_reaches_command_bus(self, mock_os):
        voice_resolver = VoiceIntentResolver()
        voice_resolver.register("bloquear sesion", "LOCK_SESSION")

        intent = voice_resolver.resolve("bloquear sesion por favor")
        self.assertEqual(intent.name, "LOCK_SESSION")
        self.assertEqual(intent.source, "VOICE")

        command = _make_resolver().resolve(intent)
        result = CommandBus().dispatch(command)

        self.assertTrue(result.success)
        mock_os.lock_session.assert_called_once()

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_all_three_sources_produce_the_same_kind_of_command(self, mock_os):
        """The Command layer doesn't know or care which InputProvider produced the
        intent (proposal.md #5.4) - same resolver, same CommandBus, three sources."""
        resolver = _make_resolver()
        bus = CommandBus()

        gesture_intent = gesture_event_to_intent(
            type("E", (), {"gesture_type": "LOCK_SESSION", "source": "CAMERA", "confidence": 1.0,
                            "timestamp": 1.0, "position": None})()
        )
        keyboard_intent = keyboard_event_to_intent(
            KeyboardInputProvider(key_source=lambda: ord("l")).poll()[0], {"l": "LOCK_SESSION"}
        )
        voice_resolver = VoiceIntentResolver(phrase_bindings={"bloquear sesion": "LOCK_SESSION"})
        voice_intent = voice_resolver.resolve("bloquear sesion")

        results = [bus.dispatch(resolver.resolve(i)) for i in (gesture_intent, keyboard_intent, voice_intent)]

        self.assertTrue(all(r.success for r in results))
        self.assertEqual(mock_os.lock_session.call_count, 3)
        self.assertEqual({gesture_intent.source, keyboard_intent.source, voice_intent.source}, {"CAMERA", "KEYBOARD", "VOICE"})


if __name__ == "__main__":
    unittest.main()
