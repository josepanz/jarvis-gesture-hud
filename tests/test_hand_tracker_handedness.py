"""Regression test for HandTracker's mirror-based handedness correction (TASK-050).

This capability (ARCHITECTURE.md "Camera mirroring & handedness") had no automated
test anywhere in the project before this - only ad hoc manual verification during
earlier development. Uses the real HandTracker (the model is already cached under
assets/ from earlier manual runs, so this doesn't hit the network) with its
`_landmarker.detect_for_video` mocked, so no real camera frame or GPU inference is
needed - only the swap logic in `process()` itself is under test.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hand_tracker import HandTracker  # noqa: E402


def _fake_result(labels):
    """labels: list of "Left"/"Right"/"Unknown" per detected hand."""
    return SimpleNamespace(
        hand_landmarks=[[object()] * 21 for _ in labels],
        handedness=[[SimpleNamespace(category_name=label)] for label in labels],
    )


class HandTrackerHandednessTests(unittest.TestCase):
    def setUp(self):
        self.tracker = HandTracker(max_hands=2)
        self.frame = np.zeros((480, 640, 3), dtype="uint8")

    def test_mirrored_true_uses_mediapipe_label_unchanged(self):
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=_fake_result(["Right"])):
            hands = self.tracker.process(self.frame, mirrored=True)
        self.assertEqual(hands[0].handedness, "Right")

    def test_mirrored_false_swaps_the_label(self):
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=_fake_result(["Right"])):
            hands = self.tracker.process(self.frame, mirrored=False)
        self.assertEqual(hands[0].handedness, "Left")

    def test_mirrored_false_swaps_left_to_right_too(self):
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=_fake_result(["Left"])):
            hands = self.tracker.process(self.frame, mirrored=False)
        self.assertEqual(hands[0].handedness, "Right")

    def test_unknown_label_is_never_swapped(self):
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=_fake_result(["Unknown"])):
            mirrored_true = self.tracker.process(self.frame, mirrored=True)
            mirrored_false = self.tracker.process(self.frame, mirrored=False)
        self.assertEqual(mirrored_true[0].handedness, "Unknown")
        self.assertEqual(mirrored_false[0].handedness, "Unknown")

    def test_two_hands_each_swapped_independently(self):
        with patch.object(
            self.tracker._landmarker, "detect_for_video", return_value=_fake_result(["Left", "Right"])
        ):
            hands = self.tracker.process(self.frame, mirrored=False)
        self.assertEqual([h.handedness for h in hands], ["Right", "Left"])

    def test_no_hands_detected_returns_empty_list(self):
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=_fake_result([])):
            hands = self.tracker.process(self.frame, mirrored=True)
        self.assertEqual(hands, [])

    def test_missing_handedness_entry_defaults_to_unknown(self):
        result = SimpleNamespace(hand_landmarks=[[object()] * 21], handedness=[])
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=result):
            hands = self.tracker.process(self.frame, mirrored=True)
        self.assertEqual(hands[0].handedness, "Unknown")


if __name__ == "__main__":
    unittest.main()
