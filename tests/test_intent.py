"""Unit tests for Intent (TASK-002, openspec/changes/multimodal-interaction-core)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.intents import Intent  # noqa: E402


def make_intent(**overrides):
    defaults = dict(
        name="SELECT",
        source="GESTURE",
        confidence=0.91,
        timestamp=1000.0,
        context={"application": "DESKTOP"},
        parameters={"target": "hud_button"},
    )
    defaults.update(overrides)
    return Intent(**defaults)


class IntentModelTests(unittest.TestCase):
    def test_valid_intent_is_created_with_expected_fields(self):
        intent = make_intent()
        self.assertEqual(intent.name, "SELECT")
        self.assertEqual(intent.source, "GESTURE")
        self.assertEqual(intent.confidence, 0.91)
        self.assertEqual(intent.context, {"application": "DESKTOP"})
        self.assertEqual(intent.parameters, {"target": "hud_button"})

    def test_optional_fields_default_to_none_or_empty(self):
        intent = Intent(name="SELECT", source="GESTURE", confidence=0.9, timestamp=1.0)
        self.assertIsNone(intent.context)
        self.assertEqual(intent.parameters, {})
        self.assertEqual(intent.metadata, {})

    def test_intent_is_immutable(self):
        intent = make_intent()
        with self.assertRaises(Exception):
            intent.confidence = 0.5


class IntentValidationTests(unittest.TestCase):
    def test_name_required(self):
        with self.assertRaises(ValueError):
            make_intent(name="")
        with self.assertRaises(ValueError):
            make_intent(name=None)

    def test_source_required(self):
        with self.assertRaises(ValueError):
            make_intent(source="")

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            make_intent(confidence=1.5)
        with self.assertRaises(ValueError):
            make_intent(confidence=-0.1)

    def test_confidence_boundaries_accepted(self):
        make_intent(confidence=0.0)
        make_intent(confidence=1.0)

    def test_confidence_must_be_numeric(self):
        with self.assertRaises(ValueError):
            make_intent(confidence="high")
        with self.assertRaises(ValueError):
            make_intent(confidence=True)

    def test_timestamp_required_and_numeric(self):
        with self.assertRaises(ValueError):
            make_intent(timestamp=None)
        with self.assertRaises(ValueError):
            make_intent(timestamp="not-a-number")

    def test_context_must_be_dict_or_none(self):
        make_intent(context=None)
        with self.assertRaises(ValueError):
            make_intent(context="not-a-dict")

    def test_parameters_must_be_dict(self):
        with self.assertRaises(ValueError):
            make_intent(parameters=["not", "a", "dict"])

    def test_metadata_must_be_dict(self):
        with self.assertRaises(ValueError):
            make_intent(metadata=["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()
