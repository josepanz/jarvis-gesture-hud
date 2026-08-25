"""Unit tests for HUDStateMachine (TASK-029)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.hud_state_machine import (  # noqa: E402
    VALID_STATES,
    HUDStateMachine,
    IllegalHudTransitionError,
)


class HUDStateMachineTests(unittest.TestCase):
    def test_starts_idle(self):
        self.assertEqual(HUDStateMachine().state, "IDLE")

    def test_happy_path(self):
        hud = HUDStateMachine()
        hud.track()
        self.assertEqual(hud.state, "TRACKING")
        hud.gesture_detected()
        self.assertEqual(hud.state, "GESTURE_DETECTED")
        hud.confirming()
        self.assertEqual(hud.state, "CONFIRMING")
        hud.executing()
        self.assertEqual(hud.state, "EXECUTING")
        hud.success()
        self.assertEqual(hud.state, "SUCCESS")
        hud.reset()
        self.assertEqual(hud.state, "IDLE")

    def test_error_path_from_executing(self):
        hud = HUDStateMachine()
        hud.track()
        hud.gesture_detected()
        hud.confirming()
        hud.executing()
        hud.error()
        self.assertEqual(hud.state, "ERROR")
        hud.reset()
        self.assertEqual(hud.state, "IDLE")

    def test_pause_and_resume(self):
        hud = HUDStateMachine()
        hud.track()
        hud.pause()
        self.assertEqual(hud.state, "PAUSED")
        hud.track()
        self.assertEqual(hud.state, "TRACKING")

    def test_illegal_transition_raises(self):
        hud = HUDStateMachine()
        with self.assertRaises(IllegalHudTransitionError):
            hud.executing()  # IDLE -> EXECUTING skips everything in between

    def test_all_documented_states_present(self):
        expected = {
            "IDLE",
            "TRACKING",
            "GESTURE_DETECTED",
            "CONFIRMING",
            "EXECUTING",
            "SUCCESS",
            "ERROR",
            "PAUSED",
        }
        self.assertEqual(VALID_STATES, expected)


if __name__ == "__main__":
    unittest.main()
