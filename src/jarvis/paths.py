"""Shared path resolution for downloaded model assets.

Extracted from jarvis.hand_tracker (which used this exact logic for the mediapipe
model before this) so jarvis.voice_llm can reuse it without duplicating the
PyInstaller-frozen-app path handling.
"""

import sys
from pathlib import Path


def assets_dir():
    # Dentro de un .exe de PyInstaller los datos empaquetados/descargados viven
    # bajo sys._MEIPASS, no junto a este archivo fuente.
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"
