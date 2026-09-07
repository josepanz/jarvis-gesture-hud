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
from tkinter import ttk
from unittest.mock import patch

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

    def test_a_missing_icon_does_not_crash_the_table_refresh(self):
        # H-14: ensure_icon() puede devolver None (fallo de escritura) - la
        # fila correspondiente debe construirse igual, sin icono.
        with patch("jarvis.settings_ui.ensure_icon", return_value=None):
            self.window._refresh_bindings_table()
        self.assertEqual(len(self.window._row_vars), len(GESTURE_DEFAULT_BINDINGS))
        self.assertEqual(self.window._icon_refs, [])


class SettingsWindowShortcutAndMacroTests(_RealTkTestCase):
    def setUp(self):
        super().setUp()
        self.profiles = ProfileManager()
        self.window = SettingsWindow(self.root, self.profiles, GESTURE_DEFAULT_BINDINGS)
        self.window.open()
        self.addCleanup(self.window._window.destroy)

    def test_a_captured_shortcut_becomes_available_as_a_rebind_target(self):
        self.profiles.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"
        self.assertIn("MY_SHORTCUT", self.window._rebind_target_options("SCROLL_UP"))

    def test_a_saved_macro_becomes_available_as_a_rebind_target(self):
        self.profiles.active.macros["MACRO:greeting"] = [{"kind": "type-text", "value": "hola"}]
        self.assertIn("MACRO:greeting", self.window._rebind_target_options("SCROLL_UP"))

    def test_rebind_target_options_include_every_valid_action_for_a_hold_capable_row(self):
        from jarvis.llm_intent import VALID_ACTIONS

        options = self.window._rebind_target_options("NARUTO_I")  # sello con hold propio
        for action in VALID_ACTIONS:
            self.assertIn(action, options)

    def test_rebind_target_options_exclude_hold_required_actions_for_an_instant_row(self):
        # H-10: PINCH_DOWN es instantaneo (sin hold propio) - ofrecer
        # LOCK_SESSION ahi dejaria bloquear la sesion con un pinch casual,
        # evadiendo el hold de 1.5s que GestureEngine exige para el Shaka.
        options = self.window._rebind_target_options("PINCH_DOWN")
        self.assertNotIn("LOCK_SESSION", options)
        self.assertIn("SCREENSHOT", options)  # el resto de VALID_ACTIONS sigue disponible

    def test_pinch_down_row_combobox_does_not_offer_lock_session(self):
        rows = _build_trigger_rows(GESTURE_DEFAULT_BINDINGS)
        row_index = next(i for i, (event_name, _label, _icon_key) in enumerate(rows) if event_name == "PINCH_DOWN")
        combo = self.window._table_frame.grid_slaves(row=row_index, column=2)[0]
        self.assertNotIn("LOCK_SESSION", combo.cget("values"))


class SettingsWindowContextRulesTests(_RealTkTestCase):
    """A-03b (WORKPLAN.md §9, `hardening-and-polish`): editor de
    Profile.context_rules ({app: {evento: accion}})."""

    def setUp(self):
        super().setUp()
        self.profiles = ProfileManager()
        self.on_change_calls = []
        self.window = SettingsWindow(
            self.root, self.profiles, GESTURE_DEFAULT_BINDINGS, on_change=lambda: self.on_change_calls.append(True)
        )
        self.window.open()
        self.addCleanup(self.window._window.destroy)

    def _add_rule(self, app_name, event_name, action_name):
        self.window._open_context_rule_dialog()
        dialog = self.window._window.winfo_children()[-1]
        app_entry, event_combo_var_holder = None, None
        # El dialogo se arma con widgets sueltos (no guardados como atributos
        # de instancia, a proposito - son de un solo uso) - encontrarlos por
        # tipo en el arbol de hijos es mas simple que exponer referencias
        # nuevas solo para el test.
        entries = [w for w in dialog.winfo_children() if isinstance(w, tk.Entry)]
        entries[0].insert(0, app_name)
        # Los 2 Combobox (gesto, accion) via su textvariable - seteo directo
        # en vez de simular clicks reales, mismo criterio que el resto de
        # este archivo (invocar callbacks directamente, sin event loop).
        combos = [w for w in dialog.winfo_children() if isinstance(w, ttk.Combobox)]
        event_combo, action_combo = combos
        event_combo.set(event_name)
        event_combo.event_generate("<<ComboboxSelected>>")
        action_combo.set(action_name)
        save_btn = [w for w in dialog.winfo_children() if isinstance(w, tk.Button)][-1]
        save_btn.invoke()

    def test_no_rules_shows_the_empty_placeholder(self):
        labels = [w for w in self.window._context_rules_frame.winfo_children() if isinstance(w, tk.Label)]
        self.assertEqual(len(labels), 1)
        self.assertIn("todavía", labels[0].cget("text"))

    def test_adding_a_rule_updates_the_active_profile_and_notifies(self):
        self._add_rule("notepad.exe", "NARUTO_TORA", "VOLUME_UP")
        self.assertEqual(self.profiles.active.context_rules, {"notepad.exe": {"NARUTO_TORA": "VOLUME_UP"}})
        self.assertEqual(self.on_change_calls, [True])

    def test_added_rule_appears_in_the_list(self):
        self._add_rule("notepad.exe", "NARUTO_TORA", "VOLUME_UP")
        labels = [w for w in self.window._context_rules_frame.winfo_children() if isinstance(w, tk.Label)]
        self.assertEqual(len(labels), 0)  # el placeholder desaparecio
        rows = self.window._context_rules_frame.winfo_children()
        row_labels = [w for row in rows for w in row.winfo_children() if isinstance(w, tk.Label)]
        self.assertEqual(row_labels[0].cget("text"), "notepad.exe: NARUTO_TORA → VOLUME_UP")

    def test_action_options_exclude_hold_required_for_a_non_hold_event(self):
        # H-10 (mismo gate que la tabla de bindings): PINCH_DOWN no sostiene
        # ningun hold, asi que LOCK_SESSION no puede ser una opcion aca tampoco.
        self.window._open_context_rule_dialog()
        dialog = self.window._window.winfo_children()[-1]
        combos = [w for w in dialog.winfo_children() if isinstance(w, ttk.Combobox)]
        event_combo, action_combo = combos
        event_combo.set("PINCH_DOWN")
        event_combo.event_generate("<<ComboboxSelected>>")
        self.assertNotIn("LOCK_SESSION", action_combo.cget("values"))
        dialog.destroy()

    def test_removing_a_rule_clears_it_from_the_active_profile(self):
        self._add_rule("notepad.exe", "NARUTO_TORA", "VOLUME_UP")
        self.window._remove_context_rule("notepad.exe", "NARUTO_TORA")
        self.assertEqual(self.profiles.active.context_rules, {})
        self.assertEqual(self.on_change_calls, [True, True])

    def test_removing_the_last_event_of_an_app_drops_the_app_entry_too(self):
        self._add_rule("notepad.exe", "NARUTO_TORA", "VOLUME_UP")
        self.window._remove_context_rule("notepad.exe", "NARUTO_TORA")
        self.assertNotIn("notepad.exe", self.profiles.active.context_rules)


if __name__ == "__main__":
    unittest.main()
