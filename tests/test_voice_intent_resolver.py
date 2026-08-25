"""Unit tests for VoiceIntentResolver (TASK-048)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.voice_intent_resolver import (  # noqa: E402
    DEFAULT_PHRASE_BINDINGS,
    VoiceIntentResolver,
)


class VoiceIntentResolverTests(unittest.TestCase):
    def test_empty_registry_resolves_nothing(self):
        resolver = VoiceIntentResolver()
        self.assertIsNone(resolver.resolve("bloquear sesion"))

    def test_registered_phrase_resolves_to_an_intent(self):
        resolver = VoiceIntentResolver()
        resolver.register("bloquear sesion", "LOCK_SESSION")
        intent = resolver.resolve("bloquear sesion")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "LOCK_SESSION")
        self.assertEqual(intent.source, "VOICE")

    def test_phrase_matches_as_a_substring_of_a_longer_sentence(self):
        resolver = VoiceIntentResolver()
        resolver.register("bloquear sesion", "LOCK_SESSION")
        intent = resolver.resolve("por favor bloquear sesion ahora")
        self.assertEqual(intent.name, "LOCK_SESSION")

    def test_matching_is_case_insensitive(self):
        resolver = VoiceIntentResolver()
        resolver.register("bloquear sesion", "LOCK_SESSION")
        intent = resolver.resolve("BLOQUEAR SESION")
        self.assertEqual(intent.name, "LOCK_SESSION")

    def test_unmatched_text_returns_none(self):
        resolver = VoiceIntentResolver()
        resolver.register("bloquear sesion", "LOCK_SESSION")
        self.assertIsNone(resolver.resolve("que hora es"))

    def test_empty_text_returns_none(self):
        resolver = VoiceIntentResolver()
        resolver.register("bloquear sesion", "LOCK_SESSION")
        self.assertIsNone(resolver.resolve(""))

    def test_never_touches_audio_or_a_microphone(self):
        # structural guarantee: resolve() takes a plain string, there is no
        # microphone/audio parameter or import anywhere in this module.
        import jarvis.core.voice_intent_resolver as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in ("pyaudio", "sounddevice", "whisper", "speech_recognition"):
            self.assertNotIn(forbidden, source.lower())

    def test_constructor_accepts_initial_bindings(self):
        resolver = VoiceIntentResolver(phrase_bindings={"subir volumen": "VOLUME_UP"})
        intent = resolver.resolve("subir volumen")
        self.assertEqual(intent.name, "VOLUME_UP")

    def test_default_phrase_bindings_are_not_loaded_unless_opted_in(self):
        resolver = VoiceIntentResolver()
        self.assertIsNone(resolver.resolve("bloquear sesion"))  # empty by default

    def test_default_phrase_bindings_work_when_opted_in(self):
        resolver = VoiceIntentResolver(phrase_bindings=DEFAULT_PHRASE_BINDINGS)
        self.assertEqual(resolver.resolve("bloquear sesion").name, "LOCK_SESSION")
        self.assertEqual(resolver.resolve("sacar captura").name, "SCREENSHOT")
        self.assertEqual(resolver.resolve("subir volumen").name, "VOLUME_UP")
        self.assertEqual(resolver.resolve("bajar volumen").name, "VOLUME_DOWN")


if __name__ == "__main__":
    unittest.main()
