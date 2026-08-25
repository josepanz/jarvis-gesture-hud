"""Unit tests for KeyboardInputProvider (TASK-046)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.events import GestureEvent  # noqa: E402
from jarvis.core.keyboard_input_provider import KeyboardInputProvider  # noqa: E402


class KeyboardInputProviderTests(unittest.TestCase):
    def test_source_is_keyboard(self):
        provider = KeyboardInputProvider(key_source=lambda: 255)
        self.assertEqual(provider.source, "KEYBOARD")

    def test_no_key_returns_empty_list(self):
        provider = KeyboardInputProvider(key_source=lambda: 255)
        self.assertEqual(provider.poll(), [])

    def test_none_from_source_returns_empty_list(self):
        provider = KeyboardInputProvider(key_source=lambda: None)
        self.assertEqual(provider.poll(), [])

    def test_a_key_press_produces_one_gesture_event(self):
        provider = KeyboardInputProvider(key_source=lambda: ord("q"))
        events = provider.poll()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, GestureEvent)
        self.assertEqual(event.gesture_type, "KEY_PRESS")
        self.assertEqual(event.source, "KEYBOARD")
        self.assertEqual(event.metadata["char"], "q")
        self.assertEqual(event.metadata["key_code"], ord("q"))

    def test_each_poll_queries_the_source_fresh(self):
        keys = iter([ord("h"), 255, ord("m")])
        provider = KeyboardInputProvider(key_source=lambda: next(keys))
        first = provider.poll()
        second = provider.poll()
        third = provider.poll()
        self.assertEqual(first[0].metadata["char"], "h")
        self.assertEqual(second, [])
        self.assertEqual(third[0].metadata["char"], "m")


if __name__ == "__main__":
    unittest.main()
