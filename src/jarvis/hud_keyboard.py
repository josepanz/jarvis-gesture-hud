"""Teclado virtual flotante (HUD) sobre el frame de camara: español, numeros/simbolos, emojis."""

import cv2
import pyautogui

from jarvis import config

_WIDE_KEYS = {"SPACE", "BACKSPACE", "ABC", "123", "EMOJI"}

LAYOUTS = {
    "es": [
        ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
        ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ñ"],
        ["z", "x", "c", "v", "b", "n", "m", "á", "é", "í"],
        ["123", "SPACE", "EMOJI", "BACKSPACE"],
    ],
    "num": [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"],
        ["-", "=", "[", "]", "{", "}", ";", ":", ",", "."],
        ["ABC", "SPACE", "EMOJI", "BACKSPACE"],
    ],
    "emoji": [
        ["😀", "😂", "😍", "👍", "🎉", "🔥", "🚀", "💡", "✨", "❤️"],
        ["👏", "🙌", "😎", "🤔", "🥳", "🌟", "⚡", "💯", "🤖", "👑"],
        ["ABC", "123", "SPACE", "BACKSPACE"],
    ],
}


class HUDKeyboard:
    def __init__(self):
        self.visible = False
        self.current_layout = "es"

    def toggle(self):
        self.visible = not self.visible
        return self.visible

    def _key_rects(self):
        layout = LAYOUTS[self.current_layout]
        for r_idx, row in enumerate(layout):
            x = 15
            y1 = config.HUD_START_Y + r_idx * (config.HUD_ROW_HEIGHT + 5)
            y2 = y1 + config.HUD_ROW_HEIGHT
            for key in row:
                kw = config.HUD_KEY_WIDTH * 2 if key in _WIDE_KEYS else config.HUD_KEY_WIDTH
                yield key, (x, y1, x + kw, y2)
                x += kw + 5

    def draw(self, frame, cursor_pt):
        if not self.visible:
            return
        for key, (x1, y1, x2, y2) in self._key_rects():
            is_hover = x1 < cursor_pt[0] < x2 and y1 < cursor_pt[1] < y2
            color = config.HUD_KEY_HOVER_COLOR if is_hover else config.HUD_KEY_COLOR
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1 if is_hover else 2)
            cv2.putText(
                frame, key, (x1 + 4, y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, config.HUD_TEXT_COLOR, 1
            )

    def handle_click(self, cursor_pt):
        """Ejecuta la tecla bajo el cursor, si hay. Devuelve True si consumio el click."""
        if not self.visible:
            return False
        for key, (x1, y1, x2, y2) in self._key_rects():
            if not (x1 < cursor_pt[0] < x2 and y1 < cursor_pt[1] < y2):
                continue
            if key == "SPACE":
                pyautogui.press("space")
            elif key == "BACKSPACE":
                pyautogui.press("backspace")
            elif key == "123":
                self.current_layout = "num"
            elif key == "ABC":
                self.current_layout = "es"
            elif key == "EMOJI":
                self.current_layout = "emoji"
            else:
                pyautogui.write(key)
            return True
        return False
