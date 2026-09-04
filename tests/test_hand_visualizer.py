"""Tests for hand_visualizer's pure functions (TASK-057, Fase 2).

`hand_connection_segments`/`bounding_quadrant` are pure (no display needed,
per spec.md #2's acceptance criteria) - `draw_hand_overlay`'s actual
`cv2.line`/`cv2.circle`/`cv2.putText` calls are visual and stay
manually-verified (same practice as the rest of this project's frame drawing).
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hand_tracker import Hand  # noqa: E402
from jarvis.hand_visualizer import HAND_CONNECTIONS, bounding_quadrant, draw_hand_overlay, hand_connection_segments  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")


def _hand(cx=0.5, cy=0.5):
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[8] = Landmark(cx + 0.1, cy - 0.2, 0)  # extremo x/y max
    pts[0] = Landmark(cx - 0.2, cy + 0.1, 0)  # extremo x/y min
    return pts


class HandConnectionSegmentsTests(unittest.TestCase):
    def test_one_segment_per_connection(self):
        segments = hand_connection_segments(_hand(), 640, 480)
        self.assertEqual(len(segments), len(HAND_CONNECTIONS))

    def test_segment_endpoints_match_the_connected_landmarks_in_pixels(self):
        pts = _hand()
        segments = hand_connection_segments(pts, 640, 480)
        # HAND_CONNECTIONS[0] == (0, 1)
        expected = ((int(pts[0].x * 640), int(pts[0].y * 480)), (int(pts[1].x * 640), int(pts[1].y * 480)))
        self.assertEqual(segments[0], expected)


class BoundingQuadrantTests(unittest.TestCase):
    def test_matches_synthetic_min_max(self):
        pts = _hand(cx=0.5, cy=0.5)
        w, h = 640, 480
        x_min, y_min, x_max, y_max = bounding_quadrant(pts, w, h)
        xs = [p.x * w for p in pts]
        ys = [p.y * h for p in pts]
        self.assertEqual((x_min, y_min, x_max, y_max), (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))))


class DrawHandOverlaySmokeTests(unittest.TestCase):
    """No hay ventana/display real en tests - solo confirma que dibujar sobre
    un frame real (numpy array) no lanza excepcion, con 1 y 2 manos."""

    def test_runs_without_raising_for_primary_and_other_hand(self):
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype="uint8")
        primary = _hand(0.5, 0.5)
        other = _hand(0.2, 0.2)
        draw_hand_overlay(frame, [Hand(primary, "Right"), Hand(other, "Left")], primary, "PINCH_DOWN")

    def test_runs_without_raising_with_no_active_gesture_label(self):
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype="uint8")
        primary = _hand(0.5, 0.5)
        draw_hand_overlay(frame, [Hand(primary, "Right")], primary, None)


if __name__ == "__main__":
    unittest.main()
