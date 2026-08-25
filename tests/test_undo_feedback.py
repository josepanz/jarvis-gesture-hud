"""Unit tests for undo feedback rendering helpers (TASK-043)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from jarvis.core.commands import CommandResult  # noqa: E402
from jarvis.core.undo_feedback import draw_undo_feedback, format_undo_feedback  # noqa: E402


class FormatUndoFeedbackTests(unittest.TestCase):
    def test_success_shows_ok(self):
        text = format_undo_feedback("VolumeUp", CommandResult.ok())
        self.assertEqual(text, "UNDO VolumeUp: OK")

    def test_failure_shows_failed(self):
        text = format_undo_feedback("VolumeUp", CommandResult.failed(error="boom"))
        self.assertEqual(text, "UNDO VolumeUp: FAILED")

    def test_includes_command_name(self):
        text = format_undo_feedback("CanvasZoom", CommandResult.ok())
        self.assertIn("CanvasZoom", text)


class DrawUndoFeedbackTests(unittest.TestCase):
    def test_draws_onto_a_real_frame(self):
        frame = np.zeros((480, 640, 3), dtype="uint8")
        text = draw_undo_feedback(frame, "VolumeUp", CommandResult.ok())
        self.assertEqual(text, "UNDO VolumeUp: OK")
        self.assertTrue((frame != 0).any())


if __name__ == "__main__":
    unittest.main()
