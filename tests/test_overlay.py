"""Tests for TASK-078 (Fase 8): ScreenOverlay.init_gear_icon().

Ventana de Tk real (mismo patron ya establecido en test_settings_ui.py) -
overlay.py en su conjunto no tenia un test_*.py dedicado antes de esta
tarea (solo se ejercitaba indirecto via los scripts manuales de
integracion); este archivo cubre especificamente lo nuevo de la Fase 8, no
retroactivamente el resto del modulo."""

import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.overlay import ScreenOverlay  # noqa: E402


def setUpModule():
    # Confirmado en CI (macOS): la PRIMERA vez que un proceso crea un tk.Tk()
    # real, Tk-Aqua a veces manda un mensaje a NSApplication ('macOSVersion')
    # que esa build no reconoce - 'NSInvalidArgumentException' sin capturar,
    # aborta el proceso entero (no es un fallo de assert atrapable desde
    # Python). Esto es especificamente sobre la PRIMERA inicializacion de
    # Tk-Aqua en el proceso - con _AppTestCase ya no creando ventanas reales
    # (ver test_naruto_seal_dispatch.py), este archivo paso a ser el primero
    # en tocar Tk de verdad en la corrida completa de la suite. Absorber esa
    # primera inicializacion aca, en un root descartable, antes de que
    # cualquier test real dependa de que salga bien.
    tk.Tk().destroy()


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


class LegendMissingIconTests(unittest.TestCase):
    """H-14: gesture_icons.ensure_icon() puede devolver None (fallo de
    escritura) - la leyenda debe mostrar esa fila sin icono, no crashear."""

    def setUp(self):
        self.overlay = ScreenOverlay()
        self.addCleanup(self.overlay.close)

    def test_none_icon_path_does_not_crash_and_still_shows_the_row(self):
        entries = [("Gesto sin icono", "Accion", None)]
        self.overlay.init_legend(entries, title="Test")
        self.overlay.pump()
        self.assertTrue(self.overlay._legend_window.winfo_exists())
        self.assertEqual(self.overlay._legend_icons, [])


def _n_entries(n):
    return [(f"Gesto {i}", f"Accion {i}", None) for i in range(n)]


class LegendPaginationTests(unittest.TestCase):
    """H-28 (`openspec/changes/hardening-and-polish/WORKPLAN.md` §2),
    confirmado en camara real (José, 2026-09-07): con las 44 entradas reales
    el panel sin paginar ocupaba toda la mitad de pantalla del lado
    anclado - paginado a LEGEND_PAGE_SIZE por pagina en vez de todo junto."""

    def setUp(self):
        self.overlay = ScreenOverlay()
        self.addCleanup(self.overlay.close)

    def _row_count(self):
        # Cada fila de gesto es un Label de texto en la columna 1 (mas el
        # titulo, que vive en la columna 0 con columnspan=2) - contar los
        # widgets de la columna 1 no depende de si hay icono o no.
        return len(
            [
                w
                for w in self.overlay._legend_container.winfo_children()
                if int(w.grid_info().get("column", -1)) == 1
            ]
        )

    def test_only_one_page_worth_of_rows_renders_at_a_time(self):
        from jarvis.overlay import LEGEND_PAGE_SIZE

        self.overlay.init_legend(_n_entries(LEGEND_PAGE_SIZE * 3 + 5), title="Test")
        self.overlay.pump()
        self.assertEqual(self._row_count(), LEGEND_PAGE_SIZE)
        self.assertEqual(self.overlay._legend_total_pages, 4)

    def test_next_page_shows_the_next_slice_and_wraps_around(self):
        from jarvis.overlay import LEGEND_PAGE_SIZE

        entries = _n_entries(LEGEND_PAGE_SIZE + 3)
        self.overlay.init_legend(entries, title="Test")
        self.overlay.pump()
        self.assertEqual(self.overlay._legend_page, 0)

        self.overlay._legend_next_page()
        self.overlay.pump()
        self.assertEqual(self.overlay._legend_page, 1)
        self.assertEqual(self._row_count(), 3)  # ultima pagina, resto parcial

        self.overlay._legend_next_page()  # da la vuelta
        self.overlay.pump()
        self.assertEqual(self.overlay._legend_page, 0)

    def test_prev_page_wraps_backward_from_the_first_page(self):
        from jarvis.overlay import LEGEND_PAGE_SIZE

        self.overlay.init_legend(_n_entries(LEGEND_PAGE_SIZE + 3), title="Test")
        self.overlay.pump()
        self.overlay._legend_prev_page()
        self.overlay.pump()
        self.assertEqual(self.overlay._legend_page, 1)  # ultima pagina

    def test_clicking_next_page_control_advances_the_page(self):
        from jarvis.overlay import LEGEND_PAGE_SIZE

        self.overlay.init_legend(_n_entries(LEGEND_PAGE_SIZE + 3), title="Test")
        self.overlay.pump()
        # Mismo patron de test_clicking_the_gear_label_invokes_the_callback:
        # un update() completo antes del evento sintetico.
        self.overlay._legend_controls_window.update()
        next_label = self.overlay._legend_controls_window.winfo_children()[0].winfo_children()[2]
        next_label.event_generate("<Button-1>", when="now")
        self.overlay.pump()
        self.assertEqual(self.overlay._legend_page, 1)

    def test_collapse_hides_all_rows_and_expand_restores_them(self):
        from jarvis.overlay import LEGEND_PAGE_SIZE

        self.overlay.init_legend(_n_entries(LEGEND_PAGE_SIZE), title="Test")
        self.overlay.pump()
        self.assertEqual(self._row_count(), LEGEND_PAGE_SIZE)

        self.overlay._legend_toggle_collapsed()
        self.overlay.pump()
        self.assertEqual(self._row_count(), 0)
        self.assertTrue(self.overlay._legend_window.winfo_exists())  # sigue viva, solo vacia

        self.overlay._legend_toggle_collapsed()
        self.overlay.pump()
        self.assertEqual(self._row_count(), LEGEND_PAGE_SIZE)

    def test_controls_never_overlap_the_panel(self):
        # H-28, confirmado en camara real (José, 2026-09-07): las flechas
        # quedaban inclickeables porque z-order entre 2 ventanas "-topmost"
        # no esta garantizado - la ventanita de controles quedaba tapada por
        # el panel. Se resuelve con geometria que nunca se toca (franja
        # reservada), no con lift()/z-order - verificar eso directamente.
        self.overlay.init_legend(_n_entries(20), title="Test")
        self.overlay.pump()
        legend = self.overlay._legend_window
        controls = self.overlay._legend_controls_window
        lx, ly, lw, lh = legend.winfo_x(), legend.winfo_y(), legend.winfo_width(), legend.winfo_height()
        cx, cy, cw, ch = controls.winfo_x(), controls.winfo_y(), controls.winfo_width(), controls.winfo_height()
        # Overlap en 2D: si los rangos en X e Y se solapan en ambos ejes.
        x_overlap = lx < cx + cw and cx < lx + lw
        y_overlap = ly < cy + ch and cy < ly + lh
        self.assertFalse(x_overlap and y_overlap, "el panel y sus controles se superponen")

    def test_legend_panel_remains_click_through_with_controls(self):
        # H-28 no puede volver clickeable el panel en si (rompe el diseño
        # "no bloquea clicks al escritorio") - solo la ventanita de controles,
        # separada, es clickeable (mismo patron que init_gear_icon).
        self.overlay.init_legend(_n_entries(3), title="Test")
        self.overlay.pump()
        self.assertTrue(self.overlay._legend_window.winfo_exists())
        self.assertTrue(self.overlay._legend_controls_window.winfo_exists())

    def test_toggling_legend_visibility_also_hides_the_controls(self):
        self.overlay.init_legend(_n_entries(3), title="Test")
        self.overlay.pump()
        self.overlay.set_legend_visible(False)
        self.overlay.pump()
        self.assertEqual(str(self.overlay._legend_controls_window.state()), "withdrawn")


if __name__ == "__main__":
    unittest.main()
