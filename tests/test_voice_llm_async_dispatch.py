"""Tests for the voice LLM-fallback async fix (real-camera finding, José,
2026-08-30): "la voz no responde". Root cause: `LLMIntentResolver.resolve()`
downloads (~1GB, first use) and loads its GGUF model SYNCHRONOUSLY, and was
being called directly from `_handle_voice_result()` on the main camera-loop
thread - the whole app (camera included) froze with zero feedback during
that download/load. Fixed by moving the LLM fallback to a background thread
(same `threading.Thread` + `queue.Queue` pattern `VoiceListener._transcribe`
already used), polled non-blockingly each frame via
`_poll_llm_intent_results()`.

Same mocking technique as test_naruto_seal_dispatch.py - reuses its
`_AppTestCase` (including the config_store real-disk isolation fix) instead
of duplicating that setup a third time.
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.core.intents import Intent  # noqa: E402

from tests.test_naruto_seal_dispatch import _AppTestCase  # noqa: E402


class PhraseMatchStaysSynchronousTests(_AppTestCase):
    def test_a_phrase_match_dispatches_immediately_without_touching_the_llm(self):
        with patch.object(self.app.llm_intent_resolver, "resolve") as mock_llm_resolve:
            self.app._handle_voice_result(("text", "subir volumen", 0.95))
        self.assertTrue(self.mock_os.volume_up.called)
        mock_llm_resolve.assert_not_called()
        self.assertFalse(self.app._llm_resolving)


class LlmFallbackAsyncTests(_AppTestCase):
    def test_an_unmatched_phrase_does_not_block_the_caller(self):
        release = threading.Event()

        def _slow_resolve(text):
            release.wait(timeout=2.0)  # simula la descarga/carga sincronica que colgaba la app
            return Intent(name="MUTE", source="VOICE_LLM", confidence=1.0, timestamp=time.time())

        with patch.object(self.app.llm_intent_resolver, "resolve", side_effect=_slow_resolve):
            started = time.perf_counter()
            self.app._handle_voice_result(("text", "una frase que no matchea nada", 0.95))
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.5, "_handle_voice_result debe volver de inmediato, sin esperar al LLM")
        self.assertTrue(self.app._llm_resolving)
        self.assertFalse(self.mock_os.volume_mute.called)  # todavia no se resolvio

        release.set()  # deja que el hilo de fondo termine
        for _ in range(50):
            if not self.app._llm_resolving:
                break
            time.sleep(0.02)
        self.app._poll_llm_intent_results()
        self.assertTrue(self.mock_os.volume_mute.called)  # recien ahora, una vez resuelto

    def test_a_second_phrase_while_still_resolving_is_a_safe_no_op(self):
        release = threading.Event()
        with patch.object(self.app.llm_intent_resolver, "resolve", side_effect=lambda text: release.wait(2.0)):
            self.app._handle_voice_result(("text", "primera frase", 0.95))
            self.assertTrue(self.app._llm_resolving)

            with patch.object(self.app.llm_intent_resolver, "resolve") as mock_second_resolve:
                self.app._handle_voice_result(("text", "segunda frase mientras la primera resuelve", 0.95))
            mock_second_resolve.assert_not_called()  # no se superpone una segunda llamada concurrente

            release.set()

    def test_an_llm_exception_is_reported_not_raised(self):
        with patch.object(self.app.llm_intent_resolver, "resolve", side_effect=RuntimeError("modelo no descargo")):
            self.app._handle_voice_result(("text", "una frase que dispara un error", 0.95))
            for _ in range(50):
                if not self.app._llm_resolving:
                    break
                time.sleep(0.02)
            self.app._poll_llm_intent_results()  # no debe lanzar
        self.assertFalse(self.app._llm_resolving)

    def test_the_llm_returning_none_reports_unrecognized_not_a_crash(self):
        with patch.object(self.app.llm_intent_resolver, "resolve", return_value=None):
            self.app._handle_voice_result(("text", "algo que ni el LLM reconoce", 0.95))
            for _ in range(50):
                if not self.app._llm_resolving:
                    break
                time.sleep(0.02)
            self.app._poll_llm_intent_results()
        self.assertFalse(self.app._llm_resolving)


if __name__ == "__main__":
    unittest.main()
