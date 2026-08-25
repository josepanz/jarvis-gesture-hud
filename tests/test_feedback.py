"""Unit tests for FeedbackManager (TASK-005, multimodal-interaction-core).

Uses lightweight fakes for voice/hud/sound so this suite stays fast and
deterministic (no real TTS engine or Tk window). See
tests/test_feedback_integration.py for a manual check against the real
jarvis.voice.VoiceJarvis / jarvis.overlay.ScreenOverlay backends.
"""

import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.commands import CommandMetadata, CommandResult  # noqa: E402
from jarvis.core.feedback import FeedbackManager  # noqa: E402


class FakeVoice:
    def __init__(self):
        self.spoken = []

    def speak(self, text):
        self.spoken.append(text)


class FakeHud:
    def __init__(self):
        self.bubbles = []

    def show_bubble(self, text, x, y):
        self.bubbles.append((text, x, y))


class BrokenVoice:
    def speak(self, text):
        raise RuntimeError("tts engine crashed")


class FeedbackManagerTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.voice = FakeVoice()
        self.hud = FakeHud()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_notify_sends_to_both_default_channels(self):
        fm = FeedbackManager(voice=self.voice, hud=self.hud, default_position=(10, 20))
        results = fm.notify("hola")
        self.assertEqual(results, {"hud": "sent", "tts": "sent"})
        self.assertEqual(self.voice.spoken, ["hola"])
        self.assertEqual(self.hud.bubbles, [("hola", 10, 20)])

    def test_notify_uses_explicit_position_over_default(self):
        fm = FeedbackManager(hud=self.hud, default_position=(0, 0))
        fm.notify("hola", channels=("hud",), position=(99, 42))
        self.assertEqual(self.hud.bubbles, [("hola", 99, 42)])

    def test_notify_respects_disabled_channels(self):
        fm = FeedbackManager(voice=self.voice, hud=self.hud, default_position=(0, 0), enabled_channels={"tts"})
        results = fm.notify("hola")
        self.assertEqual(results["hud"], "disabled")
        self.assertEqual(results["tts"], "sent")
        self.assertEqual(self.hud.bubbles, [])

    def test_set_channel_enabled_toggles_channel(self):
        fm = FeedbackManager(voice=self.voice)
        self.assertTrue(fm.is_channel_enabled("tts"))
        fm.set_channel_enabled("tts", False)
        self.assertFalse(fm.is_channel_enabled("tts"))
        results = fm.notify("hola", channels=("tts",))
        self.assertEqual(results["tts"], "disabled")
        self.assertEqual(self.voice.spoken, [])

    def test_missing_backend_fails_without_raising(self):
        fm = FeedbackManager()  # no voice, no hud configured
        results = fm.notify("hola", channels=("tts", "hud"))
        self.assertEqual(results, {"tts": "failed", "hud": "failed"})

    def test_backend_exception_is_caught_and_reported_as_failed(self):
        fm = FeedbackManager(voice=BrokenVoice())
        results = fm.notify("hola", channels=("tts",))
        self.assertEqual(results["tts"], "failed")

    def test_one_channel_failing_does_not_block_the_others(self):
        fm = FeedbackManager(voice=BrokenVoice(), hud=self.hud, default_position=(1, 1))
        results = fm.notify("hola")
        self.assertEqual(results["tts"], "failed")
        self.assertEqual(results["hud"], "sent")
        self.assertEqual(self.hud.bubbles, [("hola", 1, 1)])

    def test_sound_channel_without_backend_fails_gracefully(self):
        fm = FeedbackManager()
        results = fm.notify("beep", channels=("sound",))
        self.assertEqual(results["sound"], "failed")

    def test_sound_channel_with_injected_backend_works(self):
        played = []
        fm = FeedbackManager(sound=played.append)
        results = fm.notify("beep", channels=("sound",))
        self.assertEqual(results["sound"], "sent")
        self.assertEqual(played, ["beep"])

    def test_silent_channel_is_a_no_op_and_reports_sent(self):
        fm = FeedbackManager()
        results = fm.notify("hola", channels=("silent",))
        self.assertEqual(results["silent"], "sent")

    def test_unknown_channel_fails_gracefully(self):
        fm = FeedbackManager(enabled_channels={"carrier_pigeon"})
        results = fm.notify("hola", channels=("carrier_pigeon",))
        self.assertEqual(results["carrier_pigeon"], "failed")

    def test_hud_without_position_or_default_fails_gracefully(self):
        fm = FeedbackManager(hud=self.hud)  # no default_position
        results = fm.notify("hola", channels=("hud",))
        self.assertEqual(results["hud"], "failed")
        self.assertEqual(self.hud.bubbles, [])

    def test_notify_command_result_uses_message_then_error_then_fallback(self):
        fm = FeedbackManager(voice=self.voice)
        cmd = type("Cmd", (), {"metadata": CommandMetadata(name="VolumeUp", safety="SAFE")})()

        fm.notify_command_result(cmd, CommandResult.ok(message="volume increased"), channels=("tts",))
        fm.notify_command_result(cmd, CommandResult.failed(error="device missing"), channels=("tts",))
        fm.notify_command_result(cmd, CommandResult.rejected(), channels=("tts",))

        self.assertEqual(
            self.voice.spoken,
            ["volume increased", "device missing", "VolumeUp: REJECTED"],
        )


if __name__ == "__main__":
    unittest.main()
