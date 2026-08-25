"""Unit tests for the InputProvider ABC (TASK-044)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.input_provider import InputProvider  # noqa: E402


class _MinimalProvider(InputProvider):
    @property
    def source(self):
        return "TEST"

    def poll(self):
        return []


class InputProviderContractTests(unittest.TestCase):
    def test_cannot_instantiate_directly(self):
        with self.assertRaises(TypeError):
            InputProvider()

    def test_concrete_subclass_can_be_instantiated(self):
        provider = _MinimalProvider()
        self.assertEqual(provider.source, "TEST")
        self.assertEqual(provider.poll(), [])

    def test_missing_poll_prevents_instantiation(self):
        class NoPoll(InputProvider):
            @property
            def source(self):
                return "TEST"

        with self.assertRaises(TypeError):
            NoPoll()

    def test_missing_source_prevents_instantiation(self):
        class NoSource(InputProvider):
            def poll(self):
                return []

        with self.assertRaises(TypeError):
            NoSource()


if __name__ == "__main__":
    unittest.main()
