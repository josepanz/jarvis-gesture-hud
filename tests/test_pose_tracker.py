"""Tests for PoseTracker and filter_hands_by_pose_ownership (TASK-060b/060c,
`openspec/changes/personalization-and-config-ui`).

PoseTrackerTests mirrors tests/test_hand_tracker_handedness.py's pattern:
real tracker (model already cached under assets/), `_landmarker.detect_for_video`
mocked - no real camera frame or GPU inference needed, and skipped on the same
non-Windows platforms for the same documented reason (PoseLandmarker.create_from_options()
needs a working native GPU/graphics service even before any inference call).
"""

import platform
import sys
import unittest
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hand_tracker import Hand  # noqa: E402
from jarvis.pose_tracker import LEFT_WRIST, RIGHT_WRIST, PoseTracker, filter_hands_by_pose_ownership  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")


def _pose_landmarks(left_wrist_xy, right_wrist_xy):
    pts = [Landmark(0.5, 0.5, 0) for _ in range(33)]
    pts[LEFT_WRIST] = Landmark(left_wrist_xy[0], left_wrist_xy[1], 0)
    pts[RIGHT_WRIST] = Landmark(right_wrist_xy[0], right_wrist_xy[1], 0)
    return pts


def _hand_at(x, y):
    pts = [Landmark(x, y, 0) for _ in range(21)]
    return Hand(pts, "Right")


@unittest.skipUnless(
    platform.system() == "Windows",
    "PoseLandmarker.create_from_options() needs a working native GPU/graphics "
    "service even before any inference call - same documented constraint as "
    "HandLandmarker (see test_hand_tracker_handedness.py).",
)
class PoseTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = PoseTracker()
        self.frame = np.zeros((480, 640, 3), dtype="uint8")

    def test_process_returns_none_when_no_body_detected(self):
        result = SimpleNamespace(pose_landmarks=[])
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=result):
            landmarks = self.tracker.process(self.frame)
        self.assertIsNone(landmarks)

    def test_process_returns_the_first_bodys_landmarks_when_detected(self):
        fake_landmarks = [object()] * 33
        result = SimpleNamespace(pose_landmarks=[fake_landmarks])
        with patch.object(self.tracker._landmarker, "detect_for_video", return_value=result):
            landmarks = self.tracker.process(self.frame)
        self.assertIs(landmarks, fake_landmarks)


class FilterHandsByPoseOwnershipTests(unittest.TestCase):
    W, H = 640, 480

    def test_none_pose_landmarks_signals_fall_back_to_phase1_heuristic(self):
        hands = [_hand_at(0.5, 0.5)]
        self.assertIsNone(filter_hands_by_pose_ownership(hands, None, self.W, self.H))

    def test_hand_near_left_wrist_is_kept(self):
        pose = _pose_landmarks(left_wrist_xy=(0.3, 0.6), right_wrist_xy=(0.9, 0.9))
        hands = [_hand_at(0.31, 0.61)]  # cerca pero no exactamente igual a la muñeca del cuerpo
        self.assertEqual(filter_hands_by_pose_ownership(hands, pose, self.W, self.H), hands)

    def test_hand_near_right_wrist_is_kept(self):
        pose = _pose_landmarks(left_wrist_xy=(0.1, 0.1), right_wrist_xy=(0.7, 0.6))
        hands = [_hand_at(0.69, 0.59)]
        self.assertEqual(filter_hands_by_pose_ownership(hands, pose, self.W, self.H), hands)

    def test_hand_far_from_both_wrists_is_filtered_out(self):
        pose = _pose_landmarks(left_wrist_xy=(0.1, 0.1), right_wrist_xy=(0.15, 0.1))
        hands = [_hand_at(0.9, 0.9)]  # bien lejos de ambas muñecas del cuerpo trackeado
        self.assertEqual(filter_hands_by_pose_ownership(hands, pose, self.W, self.H), [])

    def test_mixed_hands_keeps_only_the_owned_one(self):
        pose = _pose_landmarks(left_wrist_xy=(0.3, 0.6), right_wrist_xy=(0.9, 0.9))
        owned = _hand_at(0.3, 0.6)
        stranger = _hand_at(0.05, 0.05)
        result = filter_hands_by_pose_ownership([owned, stranger], pose, self.W, self.H)
        self.assertEqual(result, [owned])


if __name__ == "__main__":
    unittest.main()
