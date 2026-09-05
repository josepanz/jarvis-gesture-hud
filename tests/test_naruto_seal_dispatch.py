"""Tests for TASK-063 (Fase 4): dispatch de sellos Naruto de 1 mano a
comandos reales, via `JarvisApp._dispatch_bound_event()`.

Misma tecnica de mocking que `tests/manual_main_integration_check.py`
(cv2.VideoCapture/HandTracker/pyautogui/CrossPlatformOS mockeados) para poder
construir un `JarvisApp` real sin tocar hardware, pero como archivo
`test_*.py` de verdad (auto-descubierto), no un script manual - las
acceptance criteria de TASK-063 piden tests unitarios reales.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.core.profiles import Profile  # noqa: E402
    from jarvis.gestures import GestureEngine  # noqa: E402
    from jarvis.hand_tracker import Hand  # noqa: E402
    from jarvis.main import GESTURE_DEFAULT_BINDINGS, JarvisApp  # noqa: E402


def _make_app(mock_os):
    return JarvisApp()


class _AppTestCase(unittest.TestCase):
    """Construye un JarvisApp real por test, con toda dependencia de
    hardware/SO mockeada - mismo patron que manual_main_integration_check.py."""

    def setUp(self):
        # Hallazgo real (2026-08-30): estos tests construian un JarvisApp()
        # que leia/escribia el bindings.json REAL del usuario en
        # ~/.jarvis-gesture-hud/ (config_store.CONFIG_FILE, sin aislar) -
        # José reasigno JJK_GOJO_DOMAIN->REDO probando el settings screen de
        # verdad, y ese override real hizo fallar
        # test_jjk_seal_default_binding_dispatches_the_right_command (el
        # test esperaba el default, no el override de disco). Se aisla a un
        # archivo temporal por test, igual que manual_live_integration_check.py.
        self._tmp_config_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_config_dir.cleanup)
        temp_config_path = Path(self._tmp_config_dir.name) / "bindings.json"
        # `load_bindings(path=CONFIG_FILE)`'s default is bound at CONFIG_FILE's
        # import-time value, not read fresh on every call - patching the
        # module attribute alone would NOT redirect main.py's parameterless
        # `config_store.load_bindings()`/`save_bindings(data)` calls. Patch
        # the functions themselves instead (same fix already applied in
        # manual_live_integration_check.py for the same reason).
        from jarvis.core import config_store as _config_store

        _real_load, _real_save = _config_store.load_bindings, _config_store.save_bindings

        patchers = [
            patch("jarvis.actions.mouse.pyautogui"),
            patch("jarvis.actions.keyboard.pyautogui"),
            patch("jarvis.actions.macro.pyautogui"),  # TASK-076: HotkeyCommand tiene su propio import de pyautogui
            patch("jarvis.actions.system.CrossPlatformOS"),
            patch("cv2.VideoCapture"),
            patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None),
            patch("pyautogui.size", return_value=(1920, 1080)),
            # No se necesita un motor TTS real para estos tests (a diferencia
            # de manual_main_integration_check.py, que lo mantiene real a
            # proposito) - mockearlo evita instanciar varios motores pyttsx3
            # reales en paralelo entre tests (ruido de threads en stderr).
            patch("jarvis.main.VoiceJarvis"),
            patch(
                "jarvis.core.config_store.load_bindings",
                side_effect=lambda path=temp_config_path: _real_load(temp_config_path),
            ),
            patch(
                "jarvis.core.config_store.save_bindings",
                side_effect=lambda data, path=temp_config_path: _real_save(data, temp_config_path),
            ),
        ]
        mocks = [p.start() for p in patchers]
        for p in patchers:
            self.addCleanup(p.stop)
        self.mock_mouse_pyautogui, self.mock_kb_pyautogui, self.mock_macro_pyautogui, self.mock_os = mocks[:4]
        # PressKeyCommand.can_execute() (TASK-076) mira pyautogui.KEYBOARD_KEYS,
        # una lista REAL de datos, no una llamada al SO - mockear el modulo
        # entero la reemplaza por un MagicMock cuyo "in" siempre da False, asi
        # que se restaura el valor real sobre el mock (las LLAMADAS de verdad,
        # press()/write(), siguen mockeadas normalmente).
        import pyautogui as _real_pyautogui

        self.mock_kb_pyautogui.KEYBOARD_KEYS = _real_pyautogui.KEYBOARD_KEYS
        self.app = JarvisApp()
        self.addCleanup(self.app.overlay.close)


class DefaultBindingTests(_AppTestCase):
    def test_default_binding_dispatches_the_right_command(self):
        self.app._dispatch_bound_event("NARUTO_TORA")  # default: SCREENSHOT
        self.assertTrue(self.mock_os.take_screenshot.called)

    def test_twohand_seal_default_binding_dispatches_the_right_command(self):
        # TASK-066 (Fase 5): mismo _dispatch_bound_event, sin importar si el
        # evento vino de 1 o 2 manos (distingue solo por el prefijo NARUTO_).
        self.app._dispatch_bound_event("NARUTO_KAI")  # default: CLOSE_APP
        self.assertTrue(self.app.should_quit)

    def test_jjk_seal_default_binding_dispatches_the_right_command(self):
        # TASK-070 (Fase 6): mismo _dispatch_bound_event, extendido al
        # prefijo JJK_ en run() - la resolucion del binding en si nunca miro
        # el prefijo, asi que este test alcanza para cubrir los 3 sellos JJK.
        self.app._dispatch_bound_event("JJK_GOJO_DOMAIN")  # default: RIGHT_CLICK
        self.mock_mouse_pyautogui.rightClick.assert_called_once()

    def test_common_gesture_default_binding_dispatches_the_right_command(self):
        # TASK-073 (Fase 7): CLAP/KOREAN_HEART no llevan prefijo NARUTO_/JJK_
        # - run() ahora rutea por pertenencia a GESTURE_DEFAULT_BINDINGS, no
        # por prefijo (ver comentario de _dispatch_bound_event), asi que
        # _dispatch_bound_event en si los maneja identico.
        self.app._dispatch_bound_event("KOREAN_HEART")  # default: SCREENSHOT
        self.assertTrue(self.mock_os.take_screenshot.called)

    def test_every_default_binding_is_a_known_dispatchable_action(self):
        # Cada valor de GESTURE_DEFAULT_BINDINGS tiene que ser algo que
        # _dispatch() realmente sepa manejar - si no, el binding quedaria
        # mudo silenciosamente. TASK-081 (Fase 8) amplio esto mas alla del
        # vocabulario fijo: los 19 gestos "clasicos" mapean a si mismos
        # (identidad), que _dispatch() ya sabia manejar desde antes de esta
        # fase (son sus propios nombres de evento).
        from jarvis.main import _MIGRATED_GESTURES

        handled = _MIGRATED_GESTURES | {
            "UNDO",
            "REDO",
            "MUTE",
            "KEYBOARD_TOGGLE",
            "CLOSE_APP",
            "SILENCE",
            "TOGGLE_ACTIVE",
            "TOGGLE_MIRROR",
            "TOGGLE_LEGEND",
            "LEGEND_ALPHA_UP",
            "LEGEND_ALPHA_DOWN",
            "SWIPE_LEFT",
            "SWIPE_RIGHT",
        }
        # C-03 (WORKPLAN.md §10, workflow 8): SWIPE_UP/SWIPE_DOWN se
        # detectan pero quedan deliberadamente SIN binding por defecto -
        # ningun vertical natural existe para un swipe con puño. Son
        # reasignables desde el settings (identidad en GESTURE_DEFAULT_BINDINGS,
        # asi que aparecen como fila); solo con su default de identidad,
        # intacto, es un no-op seguro y silencioso a proposito.
        intentionally_unbound_by_default = {"SWIPE_UP", "SWIPE_DOWN"}
        for seal, action in GESTURE_DEFAULT_BINDINGS.items():
            if seal in intentionally_unbound_by_default and action == seal:
                continue
            self.assertIn(action, handled, f"{seal} -> {action!r} no es una accion que _dispatch() maneje")


class ProfileOverrideTests(_AppTestCase):
    def test_profile_override_changes_the_dispatched_action(self):
        override = Profile(name="custom", gesture_bindings={"NARUTO_TORA": "VOLUME_UP"})
        self.app.profiles.register(override)
        self.app.profiles.switch_to("custom")

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.assertFalse(self.mock_os.take_screenshot.called)  # el default NO se uso
        self.assertTrue(self.mock_os.volume_up.called)  # gano el override


class ClassicGestureRebindTests(_AppTestCase):
    """TASK-081 (Fase 8): antes de esta fase, un gesto "clasico" (Fases 1-3)
    iba directo a su accion, sin pasar por ProfileManager - ahora CUALQUIERA
    es reasignable, con identidad como default (spec.md #8.3)."""

    def test_an_unmodified_classic_gesture_behaves_exactly_as_before(self):
        self.app._dispatch_bound_event("VOLUME_UP")
        self.assertTrue(self.mock_os.volume_up.called)

    def test_a_classic_gesture_can_be_reassigned_to_a_different_action(self):
        override = Profile(name="custom", gesture_bindings={"SCROLL_UP": "SCREENSHOT"})
        self.app.profiles.register(override)
        self.app.profiles.switch_to("custom")

        self.app._dispatch_bound_event("SCROLL_UP", cam_xy=(1, 1), screen_xy=(2, 2))

        self.assertTrue(self.mock_os.take_screenshot.called)


class MacroAndShortcutDispatchTests(_AppTestCase):
    def test_a_gesture_bound_to_a_custom_shortcut_dispatches_a_hotkey_command(self):
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MY_SHORTCUT"
        self.app.profiles.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.mock_macro_pyautogui.hotkey.assert_called_once_with("ctrl", "alt", "t")
        self.assertFalse(self.mock_os.take_screenshot.called)  # no cayo al default

    def test_a_gesture_bound_to_a_macro_dispatches_a_macro_command(self):
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:greeting"
        self.app.profiles.active.macros["MACRO:greeting"] = [
            {"kind": "type-text", "value": "hola"},
            {"kind": "press-key", "value": "enter"},
        ]

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.mock_kb_pyautogui.write.assert_called_once_with("hola")
        self.mock_kb_pyautogui.press.assert_called_once_with("enter")
        self.assertFalse(self.mock_os.take_screenshot.called)


class UnboundSealTests(_AppTestCase):
    def test_unbound_seal_is_a_safe_no_op(self):
        # Ningun seal real se llama asi - simula un evento sin binding ni de
        # perfil ni default.
        self.app._dispatch_bound_event("NARUTO_DOES_NOT_EXIST")  # no debe lanzar
        self.assertFalse(self.mock_os.take_screenshot.called)
        self.assertFalse(self.mock_os.lock_session.called)
        self.assertFalse(self.mock_os.volume_up.called)
        self.mock_mouse_pyautogui.mouseDown.assert_not_called()


class HoldRequiredGatingTests(_AppTestCase):
    """NARUTO_I -> LOCK_SESSION (HOLD_REQUIRED) por default - el binding en si
    no re-implementa ningun hold; la garantia viene de que GestureEngine
    nunca emite NARUTO_I antes de que su propio hold
    (config.NARUTO_SEAL_HOLD_SECONDS) se cumpla (ver
    tests/test_gesture_engine_regression.py::NarutoOneHandSealTests) - este
    test verifica el pipeline COMPLETO (deteccion real + dispatch real), no
    solo una de las 2 mitades por separado."""

    def test_lock_session_is_not_dispatched_before_the_seal_hold_completes(self):
        import time

        from tests.test_gesture_engine_regression import H, SCREEN_H, SCREEN_W, W, naruto_i_hand

        engine = GestureEngine()
        pts = naruto_i_hand()

        _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
        for event in events:
            if event.startswith("NARUTO_"):
                self.app._dispatch_bound_event(event)
        self.assertFalse(self.mock_os.lock_session.called)  # todavia no se cumplio el hold

        engine._naruto_hold_start = time.time() - 1.0
        _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertIn("NARUTO_I", events)
        for event in events:
            if event.startswith("NARUTO_"):
                self.app._dispatch_bound_event(event)
        self.assertTrue(self.mock_os.lock_session.called)  # recien ahora, con el hold cumplido


class PinchUpRebindDragCleanupTests(_AppTestCase):
    """H-09: soltar el drag es un invariante del sistema (sobre el evento
    fisico), no una accion reasignable via el binding de PINCH_UP."""

    def test_reassigning_pinch_up_still_releases_the_drag(self):
        self.app.profiles.active.gesture_bindings["PINCH_UP"] = "SCREENSHOT"

        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertTrue(self.app.is_dragging)

        self.app._dispatch_bound_event("PINCH_UP", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)  # el invariante suelta el boton igual
        self.mock_mouse_pyautogui.mouseUp.assert_called_once()
        self.assertTrue(self.mock_os.take_screenshot.called)  # la accion reasignada tambien corre

    def test_reassigning_pinch_down_never_starts_a_drag(self):
        self.app.profiles.active.gesture_bindings["PINCH_DOWN"] = "SCREENSHOT"

        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)
        self.assertFalse(self.mock_mouse_pyautogui.mouseDown.called)

        self.app._dispatch_bound_event("PINCH_UP", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)  # nunca arranco, nada que soltar

    def test_both_reassigned_is_dragging_never_ends_up_true(self):
        self.app.profiles.active.gesture_bindings["PINCH_DOWN"] = "SCREENSHOT"
        self.app.profiles.active.gesture_bindings["PINCH_UP"] = "VOLUME_UP"

        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)
        self.app._dispatch_bound_event("PINCH_UP", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)

    def test_no_regression_unbound_pinch_cycle_behaves_as_before(self):
        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertTrue(self.app.is_dragging)
        self.mock_mouse_pyautogui.mouseDown.assert_called_once()

        self.app._dispatch_bound_event("PINCH_UP", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertFalse(self.app.is_dragging)
        self.mock_mouse_pyautogui.mouseUp.assert_called_once()

    def test_h11_redo_stack_is_invalidated_by_a_new_command(self):
        # H-11: ejecutar -> undo -> ejecutar OTRO (no relacionado) -> redo no
        # debe hacer nada (antes: re-ejecutaba el comando viejo deshecho).
        self.app._dispatch_bound_event("VOLUME_UP")
        self.app._trigger_undo()
        self.assertTrue(self.app.undo_redo.can_redo())

        self.app._dispatch_bound_event("NARUTO_UMA")  # default: ZOOM_IN, no relacionado

        self.assertFalse(self.app.undo_redo.can_redo())
        self.mock_os.volume_up.reset_mock()
        self.app._trigger_redo()
        self.assertFalse(self.mock_os.volume_up.called)  # no revivio el VolumeUp viejo

    def test_h11_no_regression_undo_then_immediate_redo_still_works(self):
        self.app._dispatch_bound_event("VOLUME_UP")
        self.app._trigger_undo()
        self.mock_os.volume_up.reset_mock()

        self.app._trigger_redo()

        self.assertTrue(self.mock_os.volume_up.called)

    def test_no_regression_keyboard_click_still_does_not_start_a_drag(self):
        self.app.keyboard.visible = True
        space_pt = None
        for key, (x1, y1, x2, y2) in self.app.keyboard._key_rects():
            if key == "SPACE":
                space_pt = ((x1 + x2) // 2, (y1 + y2) // 2)
        self.assertIsNotNone(space_pt)

        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=space_pt, screen_xy=(500, 400))

        self.mock_kb_pyautogui.press.assert_called_once_with("space")
        self.assertFalse(self.app.is_dragging)
        self.assertFalse(self.mock_mouse_pyautogui.mouseDown.called)


class DwellClickDispatchTests(_AppTestCase):
    """C-01 (WORKPLAN.md §10, workflow 8): DWELL_CLICK dispatch (no lo emite
    GestureEngine aca - se prueba a nivel de _dispatch_bound_event, con el
    evento ya resuelto, igual que el resto de este archivo)."""

    def test_default_binding_fires_a_full_click_not_a_drag(self):
        self.app._dispatch_bound_event("DWELL_CLICK", cam_xy=(10, 10), screen_xy=(500, 400))

        self.mock_mouse_pyautogui.mouseDown.assert_called_once()
        self.mock_mouse_pyautogui.mouseUp.assert_called_once()
        self.assertFalse(self.app.is_dragging)  # no arranca un drag - es un click completo

    def test_dwell_click_on_the_hud_keyboard_presses_the_key_instead(self):
        self.app.keyboard.visible = True
        space_pt = None
        for key, (x1, y1, x2, y2) in self.app.keyboard._key_rects():
            if key == "SPACE":
                space_pt = ((x1 + x2) // 2, (y1 + y2) // 2)
        self.assertIsNotNone(space_pt)

        self.app._dispatch_bound_event("DWELL_CLICK", cam_xy=space_pt, screen_xy=(500, 400))

        self.mock_kb_pyautogui.press.assert_called_once_with("space")
        self.assertFalse(self.mock_mouse_pyautogui.mouseDown.called)


class DoubleClickDispatchTests(_AppTestCase):
    """C-02 (WORKPLAN.md §10, workflow 8): DOUBLE_CLICK dispatch - re-anclado
    a la posicion de pantalla del PRIMER click (self._last_click_screen_xy,
    seteado por un PINCH_DOWN real, no bloqueado por cooldown)."""

    def test_double_click_moves_to_the_first_clicks_position_then_clicks(self):
        # run() mantiene self._last_screen_xy actualizado cuadro a cuadro
        # (fuera de _dispatch_bound_event) - se simula aca porque el test
        # llama _dispatch_bound_event directo, sin pasar por run().
        self.app._last_screen_xy = (100, 200)
        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(100, 200))
        self.app._dispatch_bound_event("PINCH_UP", cam_xy=(10, 10), screen_xy=(100, 200))
        self.mock_mouse_pyautogui.reset_mock()

        self.app._dispatch_bound_event("DOUBLE_CLICK", cam_xy=(12, 11), screen_xy=(101, 201))

        self.mock_mouse_pyautogui.moveTo.assert_called_once_with(100, 200)  # posicion del PRIMER click
        self.mock_mouse_pyautogui.mouseDown.assert_called_once()
        self.mock_mouse_pyautogui.mouseUp.assert_called_once()
        self.assertFalse(self.app.is_dragging)  # click completo, no un drag

    def test_double_click_with_no_prior_click_anchor_still_clicks_without_moving(self):
        self.app._dispatch_bound_event("DOUBLE_CLICK", cam_xy=(12, 11), screen_xy=(101, 201))

        self.assertFalse(self.mock_mouse_pyautogui.moveTo.called)
        self.mock_mouse_pyautogui.mouseDown.assert_called_once()
        self.mock_mouse_pyautogui.mouseUp.assert_called_once()


class SwipeDispatchTests(_AppTestCase):
    """C-03 (WORKPLAN.md §10, workflow 8): SWIPE_LEFT/RIGHT tienen accion
    propia por default (HotkeyCommand, reusado de Fase 8); SWIPE_UP/DOWN son
    un no-op seguro por default, reasignables desde el settings."""

    def test_swipe_left_default_binding_dispatches_alt_left(self):
        self.app._dispatch_bound_event("SWIPE_LEFT")
        self.mock_macro_pyautogui.hotkey.assert_called_once_with("alt", "left")

    def test_swipe_right_default_binding_dispatches_alt_right(self):
        self.app._dispatch_bound_event("SWIPE_RIGHT")
        self.mock_macro_pyautogui.hotkey.assert_called_once_with("alt", "right")

    def test_swipe_up_and_down_default_bindings_are_a_safe_no_op(self):
        self.app._dispatch_bound_event("SWIPE_UP")  # no debe lanzar
        self.app._dispatch_bound_event("SWIPE_DOWN")
        self.assertFalse(self.mock_macro_pyautogui.hotkey.called)

    def test_swipe_up_can_be_reassigned_to_a_real_action(self):
        override = Profile(name="custom", gesture_bindings={"SWIPE_UP": "VOLUME_UP"})
        self.app.profiles.register(override)
        self.app.profiles.switch_to("custom")

        self.app._dispatch_bound_event("SWIPE_UP")

        self.assertTrue(self.mock_os.volume_up.called)


if __name__ == "__main__":
    unittest.main()
