"""Tests for TASK-063 (Fase 4): dispatch de sellos Naruto de 1 mano a
comandos reales, via `JarvisApp._dispatch_naruto_seal()`.

Misma tecnica de mocking que `tests/manual_main_integration_check.py`
(cv2.VideoCapture/HandTracker/pyautogui/CrossPlatformOS mockeados) para poder
construir un `JarvisApp` real sin tocar hardware, pero como archivo
`test_*.py` de verdad (auto-descubierto), no un script manual - las
acceptance criteria de TASK-063 piden tests unitarios reales.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.core.profiles import Profile  # noqa: E402
    from jarvis.gestures import GestureEngine  # noqa: E402
    from jarvis.hand_tracker import Hand  # noqa: E402
    from jarvis.main import NARUTO_DEFAULT_BINDINGS, JarvisApp  # noqa: E402


def _make_app(mock_os):
    return JarvisApp()


class _AppTestCase(unittest.TestCase):
    """Construye un JarvisApp real por test, con toda dependencia de
    hardware/SO mockeada - mismo patron que manual_main_integration_check.py."""

    def setUp(self):
        patchers = [
            patch("jarvis.actions.mouse.pyautogui"),
            patch("jarvis.actions.keyboard.pyautogui"),
            patch("jarvis.actions.system.CrossPlatformOS"),
            patch("cv2.VideoCapture"),
            patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None),
            patch("pyautogui.size", return_value=(1920, 1080)),
            # No se necesita un motor TTS real para estos tests (a diferencia
            # de manual_main_integration_check.py, que lo mantiene real a
            # proposito) - mockearlo evita instanciar varios motores pyttsx3
            # reales en paralelo entre tests (ruido de threads en stderr).
            patch("jarvis.main.VoiceJarvis"),
        ]
        mocks = [p.start() for p in patchers]
        for p in patchers:
            self.addCleanup(p.stop)
        self.mock_mouse_pyautogui, self.mock_kb_pyautogui, self.mock_os = mocks[0], mocks[1], mocks[2]
        self.app = JarvisApp()
        self.addCleanup(self.app.overlay.close)


class DefaultBindingTests(_AppTestCase):
    def test_default_binding_dispatches_the_right_command(self):
        self.app._dispatch_naruto_seal("NARUTO_TORA")  # default: SCREENSHOT
        self.assertTrue(self.mock_os.take_screenshot.called)

    def test_twohand_seal_default_binding_dispatches_the_right_command(self):
        # TASK-066 (Fase 5): mismo _dispatch_naruto_seal, sin importar si el
        # evento vino de 1 o 2 manos (distingue solo por el prefijo NARUTO_).
        self.app._dispatch_naruto_seal("NARUTO_KAI")  # default: CLOSE_APP
        self.assertTrue(self.app.should_quit)

    def test_jjk_seal_default_binding_dispatches_the_right_command(self):
        # TASK-070 (Fase 6): mismo _dispatch_naruto_seal, extendido al
        # prefijo JJK_ en run() - la resolucion del binding en si nunca miro
        # el prefijo, asi que este test alcanza para cubrir los 3 sellos JJK.
        self.app._dispatch_naruto_seal("JJK_GOJO_DOMAIN")  # default: RIGHT_CLICK
        self.mock_mouse_pyautogui.rightClick.assert_called_once()

    def test_every_default_binding_is_a_known_dispatchable_action(self):
        # Cada valor de NARUTO_DEFAULT_BINDINGS tiene que ser algo que
        # _dispatch_voice_action realmente sepa manejar - si no, el binding
        # quedaria mudo silenciosamente.
        from jarvis.main import _MIGRATED_GESTURES

        handled = _MIGRATED_GESTURES | {"UNDO", "REDO", "MUTE", "KEYBOARD_TOGGLE", "CLOSE_APP"}
        for seal, action in NARUTO_DEFAULT_BINDINGS.items():
            self.assertIn(action, handled, f"{seal} -> {action!r} no es una accion que _dispatch_voice_action maneje")


class ProfileOverrideTests(_AppTestCase):
    def test_profile_override_changes_the_dispatched_action(self):
        override = Profile(name="custom", gesture_bindings={"NARUTO_TORA": "VOLUME_UP"})
        self.app.profiles.register(override)
        self.app.profiles.switch_to("custom")

        self.app._dispatch_naruto_seal("NARUTO_TORA")

        self.assertFalse(self.mock_os.take_screenshot.called)  # el default NO se uso
        self.assertTrue(self.mock_os.volume_up.called)  # gano el override


class UnboundSealTests(_AppTestCase):
    def test_unbound_seal_is_a_safe_no_op(self):
        # Ningun seal real se llama asi - simula un evento sin binding ni de
        # perfil ni default.
        self.app._dispatch_naruto_seal("NARUTO_DOES_NOT_EXIST")  # no debe lanzar
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
                self.app._dispatch_naruto_seal(event)
        self.assertFalse(self.mock_os.lock_session.called)  # todavia no se cumplio el hold

        engine._naruto_hold_start = time.time() - 1.0
        _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertIn("NARUTO_I", events)
        for event in events:
            if event.startswith("NARUTO_"):
                self.app._dispatch_naruto_seal(event)
        self.assertTrue(self.mock_os.lock_session.called)  # recien ahora, con el hold cumplido


if __name__ == "__main__":
    unittest.main()
