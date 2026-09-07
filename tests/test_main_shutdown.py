"""H-12: salir de la app ('q') sin volver a apretar 'v' no puede dejar el
sounddevice.InputStream de voz abierto.

Reusa _AppTestCase de test_naruto_seal_dispatch.py (mismo mocking de
hardware/SO) en vez de reimplementarlo.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from test_naruto_seal_dispatch import _AppTestCase  # noqa: E402


class VoiceListenerShutdownTests(_AppTestCase):
    def _run_to_immediate_shutdown(self):
        # cap.isOpened() en False hace que el `while` de run() nunca ejecute
        # el cuerpo del loop y vaya directo al bloque de shutdown.
        self.app.cap.isOpened.return_value = False
        self.app.run()

    def test_shutdown_stops_the_voice_listener_if_it_is_recording(self):
        self.app.voice_listener = MagicMock()
        self.app.voice_listener.recording = True

        self._run_to_immediate_shutdown()

        self.app.voice_listener.stop.assert_called_once()

    def test_shutdown_does_not_stop_the_voice_listener_if_it_is_not_recording(self):
        self.app.voice_listener = MagicMock()
        self.app.voice_listener.recording = False

        self._run_to_immediate_shutdown()

        self.app.voice_listener.stop.assert_not_called()

    def test_shutdown_does_not_raise_if_the_voice_listener_is_none(self):
        self.app.voice_listener = None

        self._run_to_immediate_shutdown()  # no debe lanzar

    def test_shutdown_does_not_raise_if_stopping_the_voice_listener_fails(self):
        self.app.voice_listener = MagicMock()
        self.app.voice_listener.recording = True
        self.app.voice_listener.stop.side_effect = RuntimeError("stream ya cerrado")

        self._run_to_immediate_shutdown()  # no debe lanzar - la app tiene que poder terminar igual

    def test_no_regression_a_normal_shutdown_still_closes_the_overlay_and_camera(self):
        self.app.voice_listener = MagicMock()
        self.app.voice_listener.recording = False

        self._run_to_immediate_shutdown()

        self.app.cap.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
