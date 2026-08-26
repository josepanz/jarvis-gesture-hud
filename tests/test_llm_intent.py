"""Unit tests for LLMIntentResolver (mocked llama_cpp - not a hard dependency
of this project, see requirements-voice.txt)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.llm_intent import VALID_ACTIONS, LLMIntentResolver  # noqa: E402


def _fake_llama_module(reply_text):
    module = MagicMock()
    instance = MagicMock()
    instance.return_value = {"choices": [{"text": reply_text}]}
    module.Llama.return_value = instance
    return module, instance


class LLMIntentResolverTests(unittest.TestCase):
    def test_empty_text_returns_none_without_touching_the_model(self):
        fake_module, instance = _fake_llama_module('{"action": "VOLUME_UP"}')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            self.assertIsNone(resolver.resolve(""))
            self.assertIsNone(resolver.resolve("   "))
            self.assertFalse(fake_module.Llama.called)

    def test_valid_action_resolves_to_an_intent(self):
        fake_module, instance = _fake_llama_module('{"action": "VOLUME_UP"}')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            intent = resolver.resolve("sube el volumen")
            self.assertEqual(intent.name, "VOLUME_UP")
            self.assertEqual(intent.source, "VOICE_LLM")
            self.assertEqual(intent.parameters["raw_text"], "sube el volumen")

    def test_none_action_from_model_resolves_to_none(self):
        fake_module, instance = _fake_llama_module('{"action": "NONE"}')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            self.assertIsNone(resolver.resolve("que hora es"))

    def test_action_outside_the_fixed_vocabulary_is_rejected(self):
        fake_module, instance = _fake_llama_module('{"action": "DELETE_SYSTEM32"}')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            self.assertIsNone(resolver.resolve("borra todo"))

    def test_malformed_reply_from_model_is_rejected_not_raised(self):
        fake_module, instance = _fake_llama_module("no puedo ayudarte con eso")
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            self.assertIsNone(resolver.resolve("algo raro"))

    def test_json_embedded_in_extra_text_is_still_parsed(self):
        fake_module, instance = _fake_llama_module('claro, aqui esta: {"action": "SCREENSHOT"} listo')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            intent = resolver.resolve("saca una captura")
            self.assertEqual(intent.name, "SCREENSHOT")

    def test_model_is_loaded_lazily_and_reused_across_calls(self):
        fake_module, instance = _fake_llama_module('{"action": "MUTE"}')
        with patch.dict(sys.modules, {"llama_cpp": fake_module}):
            resolver = LLMIntentResolver(model_path="unused.gguf")
            self.assertFalse(fake_module.Llama.called)
            resolver.resolve("silencio")
            self.assertTrue(fake_module.Llama.called)
            resolver.resolve("silencio otra vez")
            self.assertEqual(fake_module.Llama.call_count, 1)  # reused, not reloaded

    def test_all_valid_actions_are_uppercase_strings(self):
        for action in VALID_ACTIONS:
            self.assertTrue(action.isupper())


if __name__ == "__main__":
    unittest.main()
