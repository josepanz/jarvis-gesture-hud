"""Unit tests for VoiceInputProvider (TASK-047 - interface only, no STT)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.input_provider import InputProvider  # noqa: E402
from jarvis.core.voice_input_provider import VoiceInputProvider  # noqa: E402


class VoiceInputProviderTests(unittest.TestCase):
    def test_is_a_real_input_provider(self):
        self.assertIsInstance(VoiceInputProvider(), InputProvider)

    def test_source_is_voice(self):
        self.assertEqual(VoiceInputProvider().source, "VOICE")

    def test_poll_always_returns_empty_list(self):
        provider = VoiceInputProvider()
        self.assertEqual(provider.poll(), [])
        self.assertEqual(provider.poll(), [])  # repeatable, no hidden state/STT


if __name__ == "__main__":
    unittest.main()
