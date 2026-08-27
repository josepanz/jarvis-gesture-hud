"""Unit tests for GestureInputProvider (TASK-045).

Uses a fake tracker (duck-typed .process(rgb, mirrored) -> list[Hand]) and a real
GestureEngine with synthetic landmarks - same pattern used throughout this project
(e.g. tests/manual_main_integration_check.py, tests/test_gestures_smoothing.py) so
no real camera/mediapipe model is needed.
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.events import GestureEvent  # noqa: E402
from jarvis.core.gesture_input_provider import GestureInputProvider  # noqa: E402
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


class FakeTracker:
    def __init__(self, hands=None):
        self.hands = hands or []
        self.calls = []

    def process(self, rgb_frame, mirrored=True):
        self.calls.append((rgb_frame, mirrored))
        return self.hands


class GestureInputProviderTests(unittest.TestCase):
    def test_source_is_camera(self):
        provider = GestureInputProvider(FakeTracker(), GestureEngine(), 1920, 1080, frame_source=lambda: None)
        self.assertEqual(provider.source, "CAMERA")

    def test_poll_returns_empty_list_when_no_frame_available(self):
        tracker = FakeTracker()
        provider = GestureInputProvider(tracker, GestureEngine(), 1920, 1080, frame_source=lambda: None)
        self.assertEqual(provider.poll(), [])
        self.assertEqual(tracker.calls, [])  # never even touched the tracker

    def test_poll_calls_frame_source_and_runs_tracking(self):
        tracker = FakeTracker(hands=[Hand(_flat_hand(), "Right")])
        frame_source = lambda: (object(), 640, 480)  # noqa: E731
        provider = GestureInputProvider(tracker, GestureEngine(), 1920, 1080, frame_source=frame_source)
        provider.poll()
        self.assertEqual(len(tracker.calls), 1)

    def test_poll_translates_gesture_engine_events_into_gesture_events(self):
        tracker = FakeTracker(hands=[Hand(_flat_hand(), "Right")])  # a flat hand pinches by construction
        frame_source = lambda: (object(), 640, 480)  # noqa: E731
        provider = GestureInputProvider(tracker, GestureEngine(), 1920, 1080, frame_source=frame_source)

        provider.poll()  # confirm-frame warmup (gestures.py's pinch-confirm streak)
        events = provider.poll()

        self.assertTrue(len(events) >= 1)
        for event in events:
            self.assertIsInstance(event, GestureEvent)
            self.assertEqual(event.source, "CAMERA")
            self.assertEqual(event.state, "ACTIVE")
        self.assertIn("PINCH_DOWN", [e.gesture_type for e in events])

    def test_poll_with_no_hands_returns_empty_event_list(self):
        tracker = FakeTracker(hands=[])
        frame_source = lambda: (object(), 640, 480)  # noqa: E731
        provider = GestureInputProvider(tracker, GestureEngine(), 1920, 1080, frame_source=frame_source)
        self.assertEqual(provider.poll(), [])

    def test_mirrored_flag_is_forwarded_to_tracker(self):
        tracker = FakeTracker(hands=[])
        frame_source = lambda: (object(), 640, 480)  # noqa: E731
        provider = GestureInputProvider(
            tracker, GestureEngine(), 1920, 1080, frame_source=frame_source, mirrored=False
        )
        provider.poll()
        self.assertEqual(tracker.calls[0][1], False)


if __name__ == "__main__":
    unittest.main()
