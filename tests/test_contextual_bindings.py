"""Unit tests for resolve_contextual_intent (TASK-028)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.contextual_bindings import resolve_contextual_intent  # noqa: E402

BINDINGS_BY_APP = {
    "PowerPoint": {"SWIPE_RIGHT": "next_slide", "SWIPE_LEFT": "previous_slide"},
    "Browser": {"SWIPE_RIGHT": "forward"},
}
GLOBAL_BINDINGS = {"SWIPE_RIGHT": "next_window"}


class ResolveContextualIntentTests(unittest.TestCase):
    def test_app_specific_binding_wins(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", "PowerPoint", BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertEqual(result, "next_slide")

    def test_different_app_gets_its_own_binding(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", "Browser", BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertEqual(result, "forward")

    def test_unknown_app_falls_back_to_global(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", "Desktop", BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertEqual(result, "next_window")

    def test_no_active_application_falls_back_to_global(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", None, BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertEqual(result, "next_window")

    def test_known_app_without_this_specific_gesture_falls_back_to_global(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", "Browser", {"Browser": {}}, GLOBAL_BINDINGS)
        self.assertEqual(result, "next_window")

    def test_nothing_matches_returns_none(self):
        result = resolve_contextual_intent("PINCH", "Desktop", BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertIsNone(result)

    def test_no_global_bindings_provided_returns_none_on_miss(self):
        result = resolve_contextual_intent("SWIPE_RIGHT", "Desktop", BINDINGS_BY_APP)
        self.assertIsNone(result)

    def test_function_returns_only_a_plain_value_never_a_callable(self):
        # Structural guarantee behind "Context cannot directly execute OS commands":
        # the resolver can only ever hand back data, there is no execution path here.
        result = resolve_contextual_intent("SWIPE_RIGHT", "PowerPoint", BINDINGS_BY_APP, GLOBAL_BINDINGS)
        self.assertFalse(callable(result))


if __name__ == "__main__":
    unittest.main()
