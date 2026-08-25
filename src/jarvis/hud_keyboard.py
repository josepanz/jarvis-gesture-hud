"""Teclado virtual flotante (HUD) sobre el frame de camara: español, numeros/simbolos, emojis.

TASK-012: handle_click() ya no ejecuta pyautogui directamente - devuelve un KeyAction
describiendo que se toco, y quien llama (main.py) decide que Command despachar por
CommandBus. El cambio de layout (123/ABC/EMOJI) sigue siendo estado interno puro, sin
efecto de SO, asi que no se convierte en Command (ver ARCHITECTURE.md/task report)."""

from collections import namedtuple

import cv2

from jarvis import config

_WIDE_KEYS = {"SPACE", "BACKSPACE", "ABC", "123", "EMOJI"}

# kind: "key" (named pyautogui key), "text" (literal character/emoji to type),
# o "layout" (cambio de layout, ya aplicado internamente - no requiere Command).
KeyAction = namedtuple("KeyAction", "kind value")

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
        """Devuelve el KeyAction bajo el cursor, o None si no hay tecla ahi (o el
        teclado esta oculto). No ejecuta ningun efecto de SO - eso es responsabilidad
        de quien reciba el KeyAction (main.py, via Command/CommandBus)."""
        if not self.visible:
            return None
        for key, (x1, y1, x2, y2) in self._key_rects():
            if not (x1 < cursor_pt[0] < x2 and y1 < cursor_pt[1] < y2):
                continue
            if key == "SPACE":
                return KeyAction("key", "space")
            elif key == "BACKSPACE":
                return KeyAction("key", "backspace")
            elif key == "123":
                self.current_layout = "num"
                return KeyAction("layout", "num")
            elif key == "ABC":
                self.current_layout = "es"
                return KeyAction("layout", "es")
            elif key == "EMOJI":
                self.current_layout = "emoji"
                return KeyAction("layout", "emoji")
            else:
                return KeyAction("text", key)
        return None
