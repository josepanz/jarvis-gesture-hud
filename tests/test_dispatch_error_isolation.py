"""H-01: una macro/atajo malformado persistido en bindings.json no puede
propagar una excepcion hasta run() y tumbar el loop de camara entero.

Reusa _AppTestCase de test_naruto_seal_dispatch.py (ya aisla
config_store.load_bindings/save_bindings a un directorio temporal) en vez de
reimplementar el mismo mocking de hardware.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from test_naruto_seal_dispatch import _AppTestCase  # noqa: E402


class MalformedMacroDispatchTests(_AppTestCase):
    def test_macro_with_unknown_step_kind_does_not_raise(self):
        self.app.profiles.active.macros["MACRO:rota"] = [{"kind": "no-existe"}]
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:rota"
        # Hoy: ValueError de build_macro_step() propaga sin ser atrapada.
        self.app._dispatch_naruto_seal("NARUTO_TORA")

    def test_macro_with_non_list_steps_does_not_raise(self):
        self.app.profiles.active.macros["MACRO:rota"] = "no-soy-una-lista"
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:rota"
        self.app._dispatch_naruto_seal("NARUTO_TORA")

    def test_invalid_macro_does_not_break_dispatch_of_a_later_normal_gesture(self):
        self.app.profiles.active.macros["MACRO:rota"] = [{"kind": "no-existe"}]
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:rota"
        self.app._dispatch_naruto_seal("NARUTO_TORA")

        # PINCH_DOWN default: arranca un drag - debe seguir funcionando.
        self.app._dispatch_naruto_seal("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
        self.assertTrue(self.app.is_dragging)

    def test_valid_macro_still_executes_normally(self):
        self.app.profiles.active.macros["MACRO:ok"] = [{"kind": "press-key", "value": "a"}]
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:ok"
        self.app._dispatch_naruto_seal("NARUTO_TORA")
        self.mock_kb_pyautogui.press.assert_called_once_with("a")


if __name__ == "__main__":
    unittest.main()
