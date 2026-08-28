"""Tests for jarvis.legend (TASK-059, Fase 3, spec.md #3.3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.gesture_icons import ICON_SPECS  # noqa: E402
from jarvis.legend import ENTRIES, build_legend_entries, build_legend_text  # noqa: E402

# Snapshot tomado ANTES de TASK-059 (ver reporte de la task) - build_legend_text()
# no debe cambiar ni un caracter al agregar la icon key a cada entrada.
_EXPECTED_TEXT = (
    "JARVIS — Gestos\n"
    "\n"
    "Índice movido             →  Puntero\n"
    "Pulgar + Índice (pinch)   →  Click / Drag\n"
    "Pulgar + Medio (pinch)    →  Click derecho\n"
    "Índice + Medio arriba     →  Scroll\n"
    "Pulgar + Anular (pinch)   →  Zoom\n"
    "Palma abierta             →  Teclado HUD\n"
    "Pulgar + Meñique + mover  →  Volumen\n"
    "Pulgar + Anular cerrado   →  Captura\n"
    "Shaka 1.5s (1 mano)       →  Bloquear sesión\n"
    "Palma, pulgar a meñique   →  Silenciar voz\n"
    "2 puños juntos 1.2s       →  Pausar / Reanudar\n"
    "2 manos en Shaka 1.5s     →  Cerrar Jarvis\n"
    "Tecla q                   →  Salir\n"
    "Tecla h                   →  Mostrar/ocultar lista\n"
    "Tecla m                   →  Modo espejo on/off\n"
    "Teclas +/-                →  Transparencia"
)


class BuildLegendTextTests(unittest.TestCase):
    def test_output_is_byte_identical_to_before_task_059(self):
        self.assertEqual(build_legend_text(), _EXPECTED_TEXT)


class EntriesIconKeysTests(unittest.TestCase):
    def test_every_entry_has_an_icon_key_that_resolves_via_ensure_icon(self):
        for gesture, action, icon_key in ENTRIES:
            self.assertIn(icon_key, ICON_SPECS, f"{gesture!r}/{action!r} references unknown icon key {icon_key!r}")

    def test_build_legend_entries_returns_one_tuple_per_entry_with_a_real_icon_path(self):
        entries = build_legend_entries()
        self.assertEqual(len(entries), len(ENTRIES))
        for (gesture, action, icon_path), (expected_gesture, expected_action, _) in zip(entries, ENTRIES):
            self.assertEqual(gesture, expected_gesture)
            self.assertEqual(action, expected_action)
            self.assertTrue(icon_path.exists())


if __name__ == "__main__":
    unittest.main()
