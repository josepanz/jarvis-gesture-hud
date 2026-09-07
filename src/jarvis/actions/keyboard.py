"""Concrete Commands wrapping the pyautogui calls that HUDKeyboard used to make
directly (TASK-012). HUDKeyboard.handle_click() now returns a KeyAction descriptor
instead of executing anything itself - see jarvis.hud_keyboard.
"""

import pyautogui

from jarvis.core.commands import Command, CommandMetadata, CommandResult


class PressKeyCommand(Command):
    def __init__(self, key_name):
        self.key_name = key_name

    @property
    def metadata(self):
        return CommandMetadata(name=f"PressKey({self.key_name})", safety="SAFE")

    def can_execute(self):
        # TASK-076 (Fase 8): antes solo aceptaba {"space", "backspace"}
        # (todo lo que HUDKeyboard llegaba a necesitar como tecla con
        # NOMBRE - el resto de sus teclas son caracteres sueltos via
        # TypeTextCommand). Los pasos "press-key" de un MacroCommand
        # necesitan el vocabulario COMPLETO de pyautogui (enter, tab, esc,
        # flechas, etc.) - `pyautogui.KEYBOARD_KEYS` ya es esa lista
        # autoritativa (no una duplicada a mano), y es un superconjunto
        # estricto de las 2 teclas que HUDKeyboard usaba, asi que esto no
        # cambia ningun comportamiento existente.
        return self.key_name in pyautogui.KEYBOARD_KEYS

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
