"""Unit tests for the Context model (TASK-026)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.context import Context  # noqa: E402


class ContextModelTests(unittest.TestCase):
    def test_valid_context_is_created(self):
        ctx = Context(
            timestamp=1.0,
            active_application="Code.exe",
            window_title="main.py - jarvis-gesture-hud",
            mode="coding",
            profile="coding",
        )
        self.assertEqual(ctx.active_application, "Code.exe")

    def test_optional_fields_default_to_none(self):
        ctx = Context(timestamp=1.0)
        self.assertIsNone(ctx.active_application)
        self.assertIsNone(ctx.window_title)
        self.assertIsNone(ctx.mode)
        self.assertIsNone(ctx.profile)

    def test_timestamp_required_and_numeric(self):
        with self.assertRaises(ValueError):
            Context(timestamp=None)
        with self.assertRaises(ValueError):
            Context(timestamp="not-a-number")

    def test_string_fields_reject_non_string_non_none(self):
        with self.assertRaises(ValueError):
            Context(timestamp=1.0, active_application=123)

    def test_context_is_immutable(self):
        ctx = Context(timestamp=1.0)
        with self.assertRaises(Exception):
            ctx.mode = "gaming"


if __name__ == "__main__":
    unittest.main()
