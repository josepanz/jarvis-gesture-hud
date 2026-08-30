"""Tests for TASK-078 (Fase 8): ScreenOverlay.init_gear_icon().

Ventana de Tk real (mismo patron ya establecido en test_settings_ui.py) -
overlay.py en su conjunto no tenia un test_*.py dedicado antes de esta
tarea (solo se ejercitaba indirecto via los scripts manuales de
integracion); este archivo cubre especificamente lo nuevo de la Fase 8, no
retroactivamente el resto del modulo."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.overlay import ScreenOverlay  # noqa: E402


class GearIconTests(unittest.TestCase):
    def setUp(self):
        self.overlay = ScreenOverlay()
        self.addCleanup(self.overlay.close)

    def test_clicking_the_gear_label_invokes_the_callback(self):
        calls = []
        self.overlay.init_gear_icon(on_click=lambda: calls.append(True))
        # Un `update()` completo (no solo `update_idletasks()`) hace falta
        # ANTES de generar el evento sintetico - hasta que Tk procesa el
        # "map" de la ventana recien creada, un Toplevel nuevo no esta listo
        # para recibir eventos de mouse sinteticos (verificado bisectando:
        # sin este pump() previo el click nunca llega, aunque la ventana ya
        # sea visible en pantalla - un detalle de timing de este test, no de
        # produccion, donde `pump()` ya corre en cada frame de camara mucho
        # antes de que el usuario llegue a clickear de verdad).
        self.overlay.pump()
        label = self.overlay._gear_window.winfo_children()[0]
        label.event_generate("<Button-1>", when="now")
        self.overlay.pump()
        self.assertEqual(calls, [True])

    def test_gear_window_is_not_click_through(self):
        # A diferencia de la leyenda/bubbles, esta ventana debe ser
        # clickeable - no se llama a _make_click_through() en absoluto.
        self.overlay.init_gear_icon(on_click=lambda: None)
        self.assertTrue(self.overlay._gear_window.winfo_exists())

    def test_gear_window_is_positioned_in_the_bottom_right_corner(self):
        self.overlay.init_gear_icon(on_click=lambda: None)
        win = self.overlay._gear_window
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        self.assertGreater(win.winfo_x(), sw // 2)
        self.assertGreater(win.winfo_y(), sh // 2)


if __name__ == "__main__":
    unittest.main()
