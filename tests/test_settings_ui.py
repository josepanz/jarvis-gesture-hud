"""Tests for TASK-077/078/079/080 (Fase 8): jarvis.settings_ui.

Construye ventanas de Tkinter REALES (no mockeadas) - mismo patron ya
establecido en `tests/test_naruto_seal_dispatch.py` (`JarvisApp` real con
`ScreenOverlay` real, un `tk.Tk()` real). Tk funciona sin problema en este
entorno (Windows, sin necesidad de un display virtual). Nunca se llama
`mainloop()` - se construyen los widgets y se invocan sus callbacks
directamente, sin bucle de eventos real (igual que `overlay.py` nunca lo
necesita: `pump()` alcanza)."""

import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.profiles import ProfileManager  # noqa: E402
from jarvis.core.voice_intent_resolver import VoiceIntentResolver  # noqa: E402
from jarvis.gesture_icons import ICON_SPECS  # noqa: E402
from jarvis.main import GESTURE_DEFAULT_BINDINGS  # noqa: E402
from jarvis.settings_ui import (  # noqa: E402
    SettingsWindow,
    Tooltip,
    _build_trigger_rows,
    _event_icon_key,
    canonicalize_shortcut,
)

CTRL, ALT_X11, ALT_WIN, SHIFT = 0x0004, 0x0008, 0x20000, 0x0001


class CanonicalizeShortcutTests(unittest.TestCase):
    def test_a_single_letter_with_no_modifiers(self):
        self.assertEqual(canonicalize_shortcut(0, "t"), "t")

    def test_ctrl_alt_letter_in_fixed_order(self):
        self.assertEqual(canonicalize_shortcut(CTRL | ALT_WIN, "t"), "ctrl+alt+t")

    def test_modifier_order_is_fixed_regardless_of_bit_order(self):
        self.assertEqual(canonicalize_shortcut(SHIFT | CTRL, "z"), "ctrl+shift+z")

    def test_alt_detected_on_x11_style_mask_too(self):
        self.assertEqual(canonicalize_shortcut(ALT_X11, "f"), "alt+f")

    def test_a_bare_modifier_keypress_does_not_include_itself_as_the_base_key(self):
        # El usuario todavia esta presionando SOLO Ctrl (antes de la tecla
        # base) - el keysym en ese frame es "Control_L", no debe aparecer
        # duplicado como base.
        self.assertEqual(canonicalize_shortcut(CTRL, "Control_L"), "ctrl")

    def test_uppercase_keysym_is_lowercased(self):
        self.assertEqual(canonicalize_shortcut(0, "A"), "a")


class EventIconKeyTests(unittest.TestCase):
    def test_classic_events_use_the_hand_maintained_bridge(self):
        self.assertEqual(_event_icon_key("PINCH_DOWN"), "pinch_click")
        self.assertEqual(_event_icon_key("PINCH_UP"), "pinch_click")
        self.assertEqual(_event_icon_key("SCROLL_UP"), "scroll")

    def test_seal_and_common_events_derive_via_lowercase(self):
        self.assertEqual(_event_icon_key("NARUTO_TORA"), "naruto_tora")
        self.assertEqual(_event_icon_key("JJK_GOJO_DOMAIN"), "jjk_gojo_domain")
        self.assertEqual(_event_icon_key("CLAP"), "clap")
        self.assertEqual(_event_icon_key("KOREAN_HEART"), "korean_heart")

    def test_every_event_in_gesture_default_bindings_resolves_to_a_real_icon(self):
        for event_name in GESTURE_DEFAULT_BINDINGS:
            with self.subTest(event=event_name):
                self.assertIn(_event_icon_key(event_name), ICON_SPECS)


class BuildTriggerRowsTests(unittest.TestCase):
    def test_produces_exactly_one_row_per_default_binding_key(self):
        rows = _build_trigger_rows(GESTURE_DEFAULT_BINDINGS)
        self.assertEqual({event for event, _label, _icon_key in rows}, set(GESTURE_DEFAULT_BINDINGS))

    def test_classic_event_labels_come_from_the_legend_not_a_new_copy(self):
        from jarvis.legend import ENTRIES as LEGEND_ENTRIES

        scroll_legend_text = next(gesture for gesture, _action, icon_key in LEGEND_ENTRIES if icon_key == "scroll")
        rows_by_event = {event: label for event, label, _icon_key in _build_trigger_rows(GESTURE_DEFAULT_BINDINGS)}
        self.assertEqual(rows_by_event["SCROLL_UP"], scroll_legend_text)


class _RealTkTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self._destroy_root)

    def _destroy_root(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class TooltipTests(_RealTkTestCase):
    def test_shows_and_hides_a_toplevel_on_enter_and_leave(self):
        label = tk.Label(self.root, text="hover me")
        label.pack()
        tooltip = Tooltip(label, "explicación")
        self.assertIsNone(tooltip._tip)
        tooltip._show()
        self.assertIsNotNone(tooltip._tip)
        tooltip._hide()
        self.assertIsNone(tooltip._tip)

    def test_does_not_show_a_tooltip_with_empty_text(self):
        label = tk.Label(self.root, text="x")
        label.pack()
        tooltip = Tooltip(label, "")
        tooltip._show()
        self.assertIsNone(tooltip._tip)


class SettingsWindowBindingsTableTests(_RealTkTestCase):
    def setUp(self):
        super().setUp()
        self.profiles = ProfileManager()
        self.on_change_calls = []
        self.window = SettingsWindow(
            self.root,
            self.profiles,
            GESTURE_DEFAULT_BINDINGS,
            voice_intent_resolver=VoiceIntentResolver(phrase_bindings={"sacar captura": "SCREENSHOT"}),
            on_change=lambda: self.on_change_calls.append(True),
        )
        self.window.open()
        self.addCleanup(self.window._window.destroy)

    def test_open_builds_exactly_one_row_per_bindable_trigger(self):
        self.assertEqual(len(self.window._row_vars), len(GESTURE_DEFAULT_BINDINGS))

    def test_each_row_starts_on_its_resolved_default_binding(self):
        self.assertEqual(self.window._row_vars["NARUTO_TORA"].get(), "SCREENSHOT")
        self.assertEqual(self.window._row_vars["SCROLL_UP"].get(), "SCROLL_UP")  # identity default

    def test_rebinding_a_row_updates_the_active_profile(self):
        self.window._on_rebind("NARUTO_TORA", "VOLUME_UP")
        self.assertEqual(self.profiles.active.gesture_bindings["NARUTO_TORA"], "VOLUME_UP")
        self.assertEqual(self.on_change_calls, [True])

    def test_opening_twice_reuses_the_same_window_instead_of_building_a_second_one(self):
        first_window = self.window._window
        self.window.open()
        self.assertIs(self.window._window, first_window)


class SettingsWindowShortcutAndMacroTests(_RealTkTestCase):
    def setUp(self):
        super().setUp()
        self.profiles = ProfileManager()
        self.window = SettingsWindow(self.root, self.profiles, GESTURE_DEFAULT_BINDINGS)
        self.window.open()
        self.addCleanup(self.window._window.destroy)

    def test_a_captured_shortcut_becomes_available_as_a_rebind_target(self):
        self.profiles.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"
        self.assertIn("MY_SHORTCUT", self.window._rebind_target_options())

    def test_a_saved_macro_becomes_available_as_a_rebind_target(self):
        self.profiles.active.macros["MACRO:greeting"] = [{"kind": "type-text", "value": "hola"}]
        self.assertIn("MACRO:greeting", self.window._rebind_target_options())

    def test_rebind_target_options_include_every_valid_action(self):
        from jarvis.llm_intent import VALID_ACTIONS

        options = self.window._rebind_target_options()
        for action in VALID_ACTIONS:
            self.assertIn(action, options)


if __name__ == "__main__":
    unittest.main()
