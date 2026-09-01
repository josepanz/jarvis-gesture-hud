"""Unit tests for GestureEngine's smoothing toggle (TASK-018).

Only covers the new `smoothing_enabled` option added for this task - not a full
GestureEngine regression suite (that's covered by ad hoc manual checks run at every
prior task in this project, see task reports).
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.gestures import GestureEngine  # noqa: E402
from jarvis.hand_tracker import Hand  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")


def _flat_hand(x=0.5, y=0.5):
    # Landmark 0 (muñeca) separado del resto para que el bbox no tenga area 0
    # (TASK-056 filtra manos por area de bbox) - ver misma nota en
    # test_gesture_engine_regression.py's flat().
    pts = [Landmark(x, y, 0) for _ in range(21)]
    pts[0] = Landmark(x - 0.08, y + 0.2, 0)
    return pts


class SmoothingToggleTests(unittest.TestCase):
    def test_default_preserves_existing_ema_behavior(self):
        engine = GestureEngine()
        self.assertTrue(engine.smoothing_enabled)
        screen_xy, _, _ = engine.process([Hand(_flat_hand(), "Right")], 640, 480, 1920, 1080)
        # EMA from prev=(0,0) toward the target: regression pin. Updated
        # 2026-08-30 for config.EMA_ALPHA's 0.35 -> 0.25 change (live-camera
        # finding: pointer felt imprecise/jittery) - was (336, 189) at 0.35.
        self.assertEqual(screen_xy, (240, 135))

    def test_disabled_smoothing_snaps_directly_to_target(self):
        engine = GestureEngine(smoothing_enabled=False)
        screen_xy, _, _ = engine.process([Hand(_flat_hand(), "Right")], 640, 480, 1920, 1080)
        self.assertEqual(screen_xy, (960, 540))  # center of a 1920x1080 screen, no lag

    def test_disabled_smoothing_tracks_every_frame_exactly(self):
        engine = GestureEngine(smoothing_enabled=False)
        engine.process([Hand(_flat_hand(0.5, 0.5), "Right")], 640, 480, 1920, 1080)
        screen_xy, _, _ = engine.process([Hand(_flat_hand(0.2, 0.5), "Right")], 640, 480, 1920, 1080)
        self.assertEqual(screen_xy[0], 240)  # no lag from the previous frame's x=0.5


if __name__ == "__main__":
    unittest.main()
