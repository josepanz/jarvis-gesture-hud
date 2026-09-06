"""Tests for jarvis.legend (TASK-059, Fase 3, spec.md #3.3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.gesture_icons import ICON_SPECS  # noqa: E402
from jarvis.legend import ENTRIES, build_legend_entries, build_legend_text  # noqa: E402

# Snapshot actualizado (Y-05, `openspec/changes/hand-sign-fidelity/WORKPLAN.md`):
# las 12 descripciones de sellos pasan a describir la forma real de 2 manos
# (sacada de docs/gesture-reference/canonical/), no la forma de 1 mano
# inventada de antes. El padding (ljust) no cambio: la fila mas larga sigue
# siendo la de swipe ("Puño cerrado, movimiento rápido a la izquierda").
_EXPECTED_TEXT = (
    "JARVIS — Gestos\n"
    "\n"
    "Índice movido                                      →  Puntero\n"
    "Pulgar + Índice (pinch)                            →  Click / Drag\n"
    "Pulgar + Medio (pinch)                             →  Click derecho\n"
    "Índice + Medio arriba, mover desde el centro       →  Scroll (4 direcciones)\n"
    "Pulgar + Anular (pinch)                            →  Zoom\n"
    "Palma abierta                                      →  Teclado HUD\n"
    "Pulgar + Meñique + mover                           →  Volumen\n"
    "Pulgar + Anular cerrado                            →  Captura\n"
    "Shaka 1.5s (1 mano)                                →  Bloquear sesión\n"
    "Palma, pulgar a meñique                            →  Silenciar voz\n"
    "2 puños juntos 1.2s                                →  Pausar / Reanudar\n"
    "2 manos en Shaka 1.5s                              →  Cerrar Jarvis\n"
    "Tecla q                                            →  Salir\n"
    "Tecla h                                            →  Mostrar/ocultar lista\n"
    "Tecla m                                            →  Modo espejo on/off\n"
    "Teclas +/-                                         →  Transparencia\n"
    "Sello Tora (manos en punta, dedos entrelazados)    →  Captura\n"
    "Sello Ushi (manos en cruz, dedos entrelazados)     →  Deshacer\n"
    "Sello U (manos entrelazadas, índice al costado)    →  Rehacer\n"
    "Sello Uma (manos en techo, dedos entrelazados)     →  Zoom +\n"
    "Sello Hitsuji (manos entrelazadas, dedo asomando)  →  Silenciar sistema\n"
    "Sello Saru (mano envuelve la muñeca de la otra)    →  Teclado HUD\n"
    "Sello Inu (puño envuelto por la otra mano)         →  Volumen -\n"
    "Sello I (2 puños juntos, nudillos enfrentados)     →  Bloquear sesión\n"
    "Sello Ne (manos entrelazadas hacia arriba)         →  Zoom -\n"
    "Sello Mi (manos entrelazadas hacia abajo)          →  Scroll abajo\n"
    "Sello Tori (manos en abanico, dedos juntos)        →  Scroll arriba\n"
    "Sello Tatsu (manos en rombo, dedos curvados)       →  Volumen +\n"
    "Sello Gojo (marco en L, 2 manos arriba)            →  Click derecho\n"
    "Sello Sukuna (chasquido pulgar-medio)              →  Captura\n"
    "Sello Megumi (índice+medio+anular)                 →  Silenciar sistema\n"
    "Aplauso (2 manos, acercar y separar)               →  Teclado HUD\n"
    "Corazón coreano (pulgar+índice, sostenido)         →  Captura\n"
    "Índice quieto sobre el objetivo (dwell)            →  Click izquierdo\n"
    "Pulgar + Índice (pinch) x2 rápido                  →  Doble click\n"
    "Puño cerrado, movimiento rápido a la izquierda     →  Atrás (navegador/explorador)\n"
    "Puño cerrado, movimiento rápido a la derecha       →  Adelante (navegador/explorador)\n"
    "Puño cerrado, movimiento rápido hacia arriba       →  Sin asignar (reasignable)\n"
    "Puño cerrado, movimiento rápido hacia abajo        →  Sin asignar (reasignable)"
)


class BuildLegendTextTests(unittest.TestCase):
    def test_output_matches_current_entries(self):
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
