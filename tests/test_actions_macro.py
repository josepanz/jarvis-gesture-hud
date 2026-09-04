"""Tests for TASK-076 (Fase 8): jarvis.actions.macro."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.macro import (  # noqa: E402
    HotkeyCommand,
    MacroCommand,
    WaitStep,
    build_macro_step,
    build_macro_steps,
)


class HotkeyCommandTests(unittest.TestCase):
    def test_execute_calls_pyautogui_hotkey_with_the_split_parts(self):
        with patch("jarvis.actions.macro.pyautogui") as mock_pyautogui:
            result = HotkeyCommand("ctrl+alt+t").execute()
        mock_pyautogui.hotkey.assert_called_once_with("ctrl", "alt", "t")
        self.assertTrue(result.success)

    def test_can_execute_rejects_an_empty_combo(self):
        self.assertFalse(HotkeyCommand("").can_execute())

    def test_execute_failure_is_converted_to_a_failed_result(self):
        with patch("jarvis.actions.macro.pyautogui") as mock_pyautogui:
            mock_pyautogui.hotkey.side_effect = RuntimeError("boom")
            result = HotkeyCommand("ctrl+z").execute()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")


class BuildMacroStepTests(unittest.TestCase):
    def test_press_key_step_builds_a_press_key_command(self):
        from jarvis.actions.keyboard import PressKeyCommand

        step = build_macro_step({"kind": "press-key", "value": "enter"})
        self.assertIsInstance(step, PressKeyCommand)
        self.assertEqual(step.key_name, "enter")
        self.assertTrue(step.can_execute())  # TASK-076 tambien ensancho esto - ver test_actions_keyboard.py

    def test_type_text_step_builds_a_type_text_command(self):
        from jarvis.actions.keyboard import TypeTextCommand

        step = build_macro_step({"kind": "type-text", "value": "hola"})
        self.assertIsInstance(step, TypeTextCommand)
        self.assertEqual(step.text, "hola")

    def test_wait_ms_step_builds_a_wait_step(self):
        step = build_macro_step({"kind": "wait-ms", "value": 300})
        self.assertIsInstance(step, WaitStep)
        self.assertEqual(step.ms, 300)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            build_macro_step({"kind": "does-not-exist", "value": None})

    def test_build_macro_steps_builds_the_whole_list_in_order(self):
        steps = build_macro_steps(
            [
                {"kind": "type-text", "value": "hola"},
                {"kind": "wait-ms", "value": 300},
                {"kind": "press-key", "value": "enter"},
            ]
        )
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0].text, "hola")
        self.assertEqual(steps[1].ms, 300)
        self.assertEqual(steps[2].key_name, "enter")


class MacroCommandTests(unittest.TestCase):
    def test_executes_every_step_in_order(self):
        # Patchea solo press()/write() - pyautogui.KEYBOARD_KEYS (una lista
        # real) tiene que seguir siendo real para que PressKeyCommand.can_execute()
        # acepte "enter" (ver test_actions_keyboard.py, TASK-076).
        with patch("jarvis.actions.keyboard.pyautogui.press") as mock_press, patch(
            "jarvis.actions.keyboard.pyautogui.write"
        ) as mock_write:
            steps = build_macro_steps(
                [
                    {"kind": "type-text", "value": "hola"},
                    {"kind": "wait-ms", "value": 1},
                    {"kind": "press-key", "value": "enter"},
                ]
            )
            result = MacroCommand("greeting", steps).execute()
        self.assertTrue(result.success)
        mock_write.assert_called_once_with("hola")
        mock_press.assert_called_once_with("enter")

    def test_can_execute_rejects_an_empty_step_list(self):
        self.assertFalse(MacroCommand("empty", []).can_execute())

    def test_metadata_safety_is_the_strictest_among_its_steps(self):
        from jarvis.core.commands import Command, CommandMetadata, CommandResult

        class _FakeDestructiveCommand(Command):
            @property
            def metadata(self):
                return CommandMetadata(name="Fake", safety="DESTRUCTIVE")

            def can_execute(self):
                return True

            def execute(self):
                return CommandResult.ok()

        steps = build_macro_steps([{"kind": "type-text", "value": "x"}]) + [_FakeDestructiveCommand()]
        self.assertEqual(MacroCommand("mixed", steps).metadata.safety, "DESTRUCTIVE")

    def test_metadata_safety_defaults_to_safe_with_only_wait_steps(self):
        steps = build_macro_steps([{"kind": "wait-ms", "value": 1}])
        self.assertEqual(MacroCommand("only_wait", steps).metadata.safety, "SAFE")

    def test_a_failing_step_stops_the_macro_and_reports_failure(self):
        with patch("jarvis.actions.keyboard.pyautogui") as mock_kb:
            mock_kb.write.side_effect = RuntimeError("boom")
            steps = build_macro_steps(
                [
                    {"kind": "type-text", "value": "hola"},
                    {"kind": "press-key", "value": "enter"},
                ]
            )
            result = MacroCommand("fails", steps).execute()
        self.assertFalse(result.success)
        mock_kb.press.assert_not_called()  # se detuvo, no siguio al paso 2


if __name__ == "__main__":
    unittest.main()
