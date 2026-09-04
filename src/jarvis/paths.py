"""Shared path resolution for model assets.

Extracted from jarvis.hand_tracker (which used this exact logic for the mediapipe
model before this) so jarvis.voice_llm can reuse it without duplicating the
PyInstaller-frozen-app path handling.

H-13: un build onefile de PyInstaller extrae `sys._MEIPASS` a un directorio
temporal en CADA arranque y lo borra al salir. Sirve para LEER assets que ya
vienen empaquetados en el .exe (p. ej. `hand_landmarker.task` si se
empaqueta), pero es el lugar equivocado para ESCRIBIR algo que deba
persistir entre arranques (iconos generados, modelos descargados en
runtime) - ahí se pierde todo y se regenera/redescarga cada vez.
`bundled_assets_dir()` es para lo primero, `writable_assets_dir()` para lo
segundo. En desarrollo ambas coinciden con el `assets/` del repo, salvo la
escribible, que usa el mismo directorio de usuario que ya usa
`jarvis.core.config_store` (`~/.jarvis-gesture-hud/`) para no depender de
dónde quedó instalado o extraído el código.
"""

import sys
from pathlib import Path

WRITABLE_ASSETS_DIR = Path.home() / ".jarvis-gesture-hud" / "assets"


def bundled_assets_dir():
    """Assets empaquetados de solo lectura (modelos incluidos en el bundle)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def writable_assets_dir():
    """Directorio persistente para lo que la app genera o descarga en runtime
    (iconos de gestos, modelos descargados). Nunca `_MEIPASS`: ese directorio
    no sobrevive al cierre de la app."""
    if getattr(sys, "frozen", False):
        return WRITABLE_ASSETS_DIR
    return Path(__file__).resolve().parents[2] / "assets"
