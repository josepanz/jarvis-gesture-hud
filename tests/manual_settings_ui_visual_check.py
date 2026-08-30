"""Manual visual check for SettingsWindow (TASK-078/079/080) - NOT auto-discovered
(no test_ prefix). Builds a REAL window (not withdrawn) and screenshots it via
PIL.ImageGrab, since Tkinter widget layout bugs don't show up in assertions alone.

Run manually:
    python tests/manual_settings_ui_visual_check.py <output_png_path>
"""

import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.profiles import ProfileManager  # noqa: E402
from jarvis.core.voice_intent_resolver import DEFAULT_PHRASE_BINDINGS, VoiceIntentResolver  # noqa: E402
from jarvis.main import GESTURE_DEFAULT_BINDINGS  # noqa: E402
from jarvis.settings_ui import SettingsWindow  # noqa: E402


def main(out_path):
    root = tk.Tk()
    root.withdraw()

    profiles = ProfileManager()
    profiles.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"
    profiles.active.macros["MACRO:greeting"] = [{"kind": "type-text", "value": "hola"}]

    window = SettingsWindow(
        root, profiles, GESTURE_DEFAULT_BINDINGS, voice_intent_resolver=VoiceIntentResolver(DEFAULT_PHRASE_BINDINGS)
    )
    window.open()
    window._window.geometry("+80+80")
    window._window.attributes("-topmost", True)
    window._window.lift()
    window._window.focus_force()
    for _ in range(10):
        window._window.update_idletasks()
        window._window.update()

    from PIL import ImageGrab

    def _grab(win, path):
        win.geometry(f"+80+80")
        win.attributes("-topmost", True)
        win.lift()
        win.focus_force()
        for _ in range(10):
            win.update_idletasks()
            win.update()
        x, y = win.winfo_rootx(), win.winfo_rooty()
        w, h = win.winfo_width(), win.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(path)
        print(f"saved {path} ({w}x{h})")

    _grab(window._window, out_path)

    if len(sys.argv) > 2:
        window._open_shortcut_capture_dialog()
        dialog = window._window.winfo_children()[-1]
        _grab(dialog, sys.argv[2])
        dialog.destroy()

    if len(sys.argv) > 3:
        window._open_macro_builder_dialog()
        dialog = window._window.winfo_children()[-1]
        _grab(dialog, sys.argv[3])
        dialog.destroy()

    root.destroy()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "settings_window.png")
