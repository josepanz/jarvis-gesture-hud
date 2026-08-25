"""Unit tests for keyboard action Commands (TASK-012). pyautogui is fully mocked."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.keyboard import PressKeyCommand, TypeTextCommand  # noqa: E402


class PressKeyCommandTests(unittest.TestCase):
    @patch("jarvis.actions.keyboard.pyautogui")
    def test_execute_presses_named_key(self, mock_pyautogui):
        result = PressKeyCommand("space").execute()
        mock_pyautogui.press.assert_called_once_with("space")
        self.assertTrue(result.success)

    def test_can_execute_rejects_unknown_key_name(self):
        self.assertFalse(PressKeyCommand("F13").can_execute())

    def test_can_execute_accepts_known_key_names(self):
        self.assertTrue(PressKeyCommand("space").can_execute())
        self.assertTrue(PressKeyCommand("backspace").can_execute())


class TypeTextCommandTests(unittest.TestCase):
    @patch("jarvis.actions.keyboard.pyautogui")
    def test_execute_writes_text(self, mock_pyautogui):
        result = TypeTextCommand("n").execute()
        mock_pyautogui.write.assert_called_once_with("n")
        self.assertTrue(result.success)

    def test_can_execute_rejects_empty_text(self):
        self.assertFalse(TypeTextCommand("").can_execute())


if __name__ == "__main__":
    unittest.main()
