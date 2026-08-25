"""Unit tests for HUDKeyboard.handle_click's KeyAction contract (TASK-012).

No pyautogui import exists anymore in jarvis.hud_keyboard - these tests would fail
to even construct KeyAction results if that regressed, since handle_click must not
execute anything itself now.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hud_keyboard import HUDKeyboard, KeyAction  # noqa: E402


def _point_for(keyboard, key_name):
    for key, (x1, y1, x2, y2) in keyboard._key_rects():
        if key == key_name:
            return ((x1 + x2) // 2, (y1 + y2) // 2)
    raise AssertionError(f"key {key_name!r} not found in current layout")


class HUDKeyboardHandleClickTests(unittest.TestCase):
    def setUp(self):
        self.kb = HUDKeyboard()
        self.kb.visible = True

    def test_hidden_keyboard_returns_none(self):
        self.kb.visible = False
        self.assertIsNone(self.kb.handle_click((0, 0)))

    def test_click_outside_any_key_returns_none(self):
        self.assertIsNone(self.kb.handle_click((-100, -100)))

    def test_space_key_returns_key_action(self):
        result = self.kb.handle_click(_point_for(self.kb, "SPACE"))
        self.assertEqual(result, KeyAction("key", "space"))

    def test_backspace_key_returns_key_action(self):
        result = self.kb.handle_click(_point_for(self.kb, "BACKSPACE"))
        self.assertEqual(result, KeyAction("key", "backspace"))

    def test_literal_character_returns_text_action(self):
        result = self.kb.handle_click(_point_for(self.kb, "q"))
        self.assertEqual(result, KeyAction("text", "q"))

    def test_accented_literal_character_returns_text_action(self):
        result = self.kb.handle_click(_point_for(self.kb, "ñ"))
        self.assertEqual(result, KeyAction("text", "ñ"))

    def test_layout_switch_updates_state_and_returns_layout_action(self):
        result = self.kb.handle_click(_point_for(self.kb, "123"))
        self.assertEqual(result, KeyAction("layout", "num"))
        self.assertEqual(self.kb.current_layout, "num")

    def test_layout_switch_back_to_abc(self):
        self.kb.current_layout = "num"
        result = self.kb.handle_click(_point_for(self.kb, "ABC"))
        self.assertEqual(result, KeyAction("layout", "es"))
        self.assertEqual(self.kb.current_layout, "es")

    def test_emoji_layout_key_returns_text_action_for_emoji(self):
        self.kb.current_layout = "emoji"
        result = self.kb.handle_click(_point_for(self.kb, "😀"))
        self.assertEqual(result, KeyAction("text", "😀"))

    def test_handle_click_has_no_side_effects_on_the_os(self):
        # If handle_click ever called pyautogui again, importing jarvis.hud_keyboard
        # would still succeed (pyautogui is a real dependency of the project), so the
        # real regression guard is structural: pyautogui must not be imported here.
        import jarvis.hud_keyboard as hud_keyboard_module

        self.assertNotIn("pyautogui", dir(hud_keyboard_module))


if __name__ == "__main__":
    unittest.main()
