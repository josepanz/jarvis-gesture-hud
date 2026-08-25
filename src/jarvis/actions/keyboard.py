"""Concrete Commands wrapping the pyautogui calls that HUDKeyboard used to make
directly (TASK-012). HUDKeyboard.handle_click() now returns a KeyAction descriptor
instead of executing anything itself - see jarvis.hud_keyboard.
"""

import pyautogui

from jarvis.core.commands import Command, CommandMetadata, CommandResult

_NAMED_KEYS = {"space", "backspace"}


class PressKeyCommand(Command):
    def __init__(self, key_name):
        self.key_name = key_name

    @property
    def metadata(self):
        return CommandMetadata(name=f"PressKey({self.key_name})", safety="SAFE")

    def can_execute(self):
        return self.key_name in _NAMED_KEYS

    def execute(self):
        try:
            pyautogui.press(self.key_name)
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"PressKey({self.key_name}) failed")


class TypeTextCommand(Command):
    def __init__(self, text):
        self.text = text

    @property
    def metadata(self):
        return CommandMetadata(name="TypeText", safety="SAFE")

    def can_execute(self):
        return bool(self.text)

    def execute(self):
        try:
            pyautogui.write(self.text)
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="TypeText failed")
