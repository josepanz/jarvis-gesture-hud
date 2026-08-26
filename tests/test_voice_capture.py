"""Unit tests for VoiceListener (mocked sounddevice/faster_whisper - neither is
a hard dependency of this project, see requirements-voice.txt)."""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.voice_capture import VoiceListener  # noqa: E402


def _fake_segment(text, no_speech_prob=0.0):
    segment = MagicMock()
    segment.text = text
    segment.no_speech_prob = no_speech_prob
    return segment


def _fake_faster_whisper_module(segments):
    module = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (segments, None)
    module.WhisperModel.return_value = instance
    return module, instance


def _fake_sounddevice_module():
    module = MagicMock()
    stream = MagicMock()
    module.InputStream.return_value = stream
    return module, stream


def _wait_for_result(listener, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = listener.poll_result()
        if result is not None:
            return result
        time.sleep(0.02)
    raise AssertionError("no result delivered within timeout")


class VoiceListenerTests(unittest.TestCase):
    def test_not_recording_initially(self):
        self.assertFalse(VoiceListener().recording)

    def test_poll_result_returns_none_when_nothing_ready(self):
        self.assertIsNone(VoiceListener().poll_result())

    def test_stop_without_start_is_a_safe_noop(self):
        listener = VoiceListener()
        listener.stop()  # must not raise
        self.assertIsNone(listener.poll_result())

    def test_start_opens_an_input_stream_and_sets_recording(self):
        sd_module, stream = _fake_sounddevice_module()
        with patch.dict(sys.modules, {"sounddevice": sd_module}):
            listener = VoiceListener()
            listener.start()
            self.assertTrue(listener.recording)
            self.assertTrue(stream.start.called)

    def test_start_twice_is_a_noop(self):
        sd_module, stream = _fake_sounddevice_module()
        with patch.dict(sys.modules, {"sounddevice": sd_module}):
            listener = VoiceListener()
            listener.start()
            listener.start()
            self.assertEqual(sd_module.InputStream.call_count, 1)

    def test_stop_transcribes_recorded_audio_and_delivers_text_with_confidence(self):
        sd_module, stream = _fake_sounddevice_module()
        fw_module, instance = _fake_faster_whisper_module([_fake_segment("bloquear sesion", no_speech_prob=0.1)])
        with patch.dict(sys.modules, {"sounddevice": sd_module, "faster_whisper": fw_module}):
            listener = VoiceListener()
            listener.start()
            listener._on_audio(np.zeros((10, 1), dtype="float32"), 10, None, None)
            listener.stop()
            self.assertFalse(listener.recording)
            self.assertTrue(stream.stop.called)
            self.assertTrue(stream.close.called)

            kind, text, confidence = _wait_for_result(listener)
            self.assertEqual(kind, "text")
            self.assertEqual(text, "bloquear sesion")
            self.assertAlmostEqual(confidence, 0.9)

    def test_stop_with_no_audio_captured_still_transcribes_silence(self):
        sd_module, stream = _fake_sounddevice_module()
        fw_module, instance = _fake_faster_whisper_module([])
        with patch.dict(sys.modules, {"sounddevice": sd_module, "faster_whisper": fw_module}):
            listener = VoiceListener()
            listener.start()
            listener.stop()
            kind, text, confidence = _wait_for_result(listener)
            self.assertEqual((kind, text, confidence), ("text", "", 0.0))

    def test_transcription_error_is_delivered_not_raised(self):
        sd_module, stream = _fake_sounddevice_module()
        fw_module = MagicMock()
        fw_module.WhisperModel.side_effect = RuntimeError("model load failed")
        with patch.dict(sys.modules, {"sounddevice": sd_module, "faster_whisper": fw_module}):
            listener = VoiceListener()
            listener.start()
            listener.stop()
            kind, message, confidence = _wait_for_result(listener)
            self.assertEqual((kind, message, confidence), ("error", "model load failed", 0.0))

    def test_model_is_loaded_lazily_only_on_first_transcription(self):
        sd_module, stream = _fake_sounddevice_module()
        fw_module, instance = _fake_faster_whisper_module([_fake_segment("hola")])
        with patch.dict(sys.modules, {"sounddevice": sd_module, "faster_whisper": fw_module}):
            listener = VoiceListener()
            self.assertFalse(fw_module.WhisperModel.called)
            listener.start()
            listener.stop()
            _wait_for_result(listener)
            self.assertTrue(fw_module.WhisperModel.called)


if __name__ == "__main__":
    unittest.main()
