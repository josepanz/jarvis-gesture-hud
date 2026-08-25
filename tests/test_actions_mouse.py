"""Unit tests for mouse action Commands (TASK-006/007/008/009/010/011).

pyautogui is fully mocked - these tests never move the real mouse.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.mouse import (  # noqa: E402
    CanvasZoomCommand,
    MouseButtonCommand,
    MouseMoveCommand,
    RightClickCommand,
    ScrollCommand,
)


class MouseMoveCommandTests(unittest.TestCase):
    @patch("jarvis.actions.mouse.pyautogui")
    def test_execute_moves_to_given_coordinates(self, mock_pyautogui):
        result = MouseMoveCommand(120, 340).execute()
        mock_pyautogui.moveTo.assert_called_once_with(120, 340)
        self.assertTrue(result.success)

    @patch("jarvis.actions.mouse.pyautogui")
    def test_execute_failure_is_reported_not_raised(self, mock_pyautogui):
        mock_pyautogui.moveTo.side_effect = RuntimeError("no display")
        result = MouseMoveCommand(0, 0).execute()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")


class MouseButtonCommandTests(unittest.TestCase):
    @patch("jarvis.actions.mouse.pyautogui")
    def test_pressed_true_calls_mouse_down(self, mock_pyautogui):
        MouseButtonCommand(pressed=True).execute()
        mock_pyautogui.mouseDown.assert_called_once()
        mock_pyautogui.mouseUp.assert_not_called()

    @patch("jarvis.actions.mouse.pyautogui")
    def test_pressed_false_calls_mouse_up(self, mock_pyautogui):
        MouseButtonCommand(pressed=False).execute()
        mock_pyautogui.mouseUp.assert_called_once()
        mock_pyautogui.mouseDown.assert_not_called()


class RightClickCommandTests(unittest.TestCase):
    @patch("jarvis.actions.mouse.pyautogui")
    def test_execute_calls_right_click(self, mock_pyautogui):
        result = RightClickCommand().execute()
        mock_pyautogui.rightClick.assert_called_once()
        self.assertTrue(result.success)


class ScrollCommandTests(unittest.TestCase):
    @patch("jarvis.actions.mouse.pyautogui")
    def test_execute_scrolls_by_amount(self, mock_pyautogui):
        ScrollCommand(12).execute()
        mock_pyautogui.scroll.assert_called_once_with(12)

    @patch("jarvis.actions.mouse.pyautogui")
    def test_negative_amount_scrolls_down(self, mock_pyautogui):
        ScrollCommand(-12).execute()
        mock_pyautogui.scroll.assert_called_once_with(-12)


class CanvasZoomCommandTests(unittest.TestCase):
    @patch("jarvis.actions.mouse.pyautogui")
    def test_execute_wraps_scroll_in_ctrl(self, mock_pyautogui):
        result = CanvasZoomCommand(10).execute()
        mock_pyautogui.keyDown.assert_called_once_with("ctrl")
        mock_pyautogui.scroll.assert_called_once_with(10)
        mock_pyautogui.keyUp.assert_called_once_with("ctrl")
        self.assertTrue(result.success)

    @patch("jarvis.actions.mouse.pyautogui")
    def test_ctrl_is_released_even_if_scroll_fails(self, mock_pyautogui):
        mock_pyautogui.scroll.side_effect = RuntimeError("boom")
        result = CanvasZoomCommand(10).execute()
        mock_pyautogui.keyUp.assert_called_once_with("ctrl")
        self.assertFalse(result.success)

    def test_declares_reversible(self):
        self.assertTrue(CanvasZoomCommand(10).is_reversible())

    @patch("jarvis.actions.mouse.pyautogui")
    def test_undo_scrolls_by_negative_amount(self, mock_pyautogui):
        result = CanvasZoomCommand(10).undo()
        mock_pyautogui.keyDown.assert_called_once_with("ctrl")
        mock_pyautogui.scroll.assert_called_once_with(-10)
        mock_pyautogui.keyUp.assert_called_once_with("ctrl")
        self.assertTrue(result.success)

    @patch("jarvis.actions.mouse.pyautogui")
    def test_undo_of_zoom_out_scrolls_positive(self, mock_pyautogui):
        CanvasZoomCommand(-10).undo()
        mock_pyautogui.scroll.assert_called_once_with(10)

    @patch("jarvis.actions.mouse.pyautogui")
    def test_undo_ctrl_is_released_even_if_scroll_fails(self, mock_pyautogui):
        mock_pyautogui.scroll.side_effect = RuntimeError("boom")
        result = CanvasZoomCommand(10).undo()
        mock_pyautogui.keyUp.assert_called_once_with("ctrl")
        self.assertFalse(result.success)


class OtherMouseCommandsAreNotReversibleTests(unittest.TestCase):
    def test_mouse_move_not_reversible(self):
        self.assertFalse(MouseMoveCommand(0, 0).is_reversible())

    def test_mouse_button_not_reversible(self):
        self.assertFalse(MouseButtonCommand(True).is_reversible())

    def test_right_click_not_reversible(self):
        self.assertFalse(RightClickCommand().is_reversible())

    def test_scroll_not_reversible(self):
        self.assertFalse(ScrollCommand(12).is_reversible())


if __name__ == "__main__":
    unittest.main()
