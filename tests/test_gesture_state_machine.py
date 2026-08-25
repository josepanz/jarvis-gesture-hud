"""Unit tests for GestureStateMachine (TASK-014)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.gesture_state_machine import (  # noqa: E402
    VALID_STATES,
    GestureStateMachine,
    IllegalTransitionError,
)


class GestureStateMachineTests(unittest.TestCase):
    def test_starts_idle(self):
        self.assertEqual(GestureStateMachine().state, "IDLE")

    def test_happy_path_full_sequence(self):
        sm = GestureStateMachine()
        sm.detect()
        self.assertEqual(sm.state, "DETECTED")
        sm.candidate()
        self.assertEqual(sm.state, "CANDIDATE")
        sm.confirm()
        self.assertEqual(sm.state, "CONFIRMED")
        sm.activate()
        self.assertEqual(sm.state, "ACTIVE")
        sm.complete()
        self.assertEqual(sm.state, "COMPLETED")
        sm.cooldown()
        self.assertEqual(sm.state, "COOLDOWN")
        sm.reset()
        self.assertEqual(sm.state, "IDLE")

    def test_candidate_can_be_cancelled_back_to_idle(self):
        sm = GestureStateMachine()
        sm.detect()
        sm.candidate()
        sm.cancel()
        self.assertEqual(sm.state, "CANCELLED")
        sm.reset()
        self.assertEqual(sm.state, "IDLE")

    def test_cancel_is_legal_from_every_in_progress_state(self):
        for enter in ("detect", "candidate", "confirm", "activate"):
            sm = GestureStateMachine()
            for step in ("detect", "candidate", "confirm", "activate"):
                getattr(sm, step)()
                if step == enter:
                    break
            sm.cancel()
            self.assertEqual(sm.state, "CANCELLED")

    def test_illegal_transition_raises_and_does_not_change_state(self):
        sm = GestureStateMachine()
        with self.assertRaises(IllegalTransitionError):
            sm.activate()  # IDLE -> ACTIVE is not legal
        self.assertEqual(sm.state, "IDLE")

    def test_cannot_skip_states_in_happy_path(self):
        sm = GestureStateMachine()
        sm.detect()
        with self.assertRaises(IllegalTransitionError):
            sm.activate()  # DETECTED -> ACTIVE skips CANDIDATE/CONFIRMED

    def test_can_transition_to_reports_without_mutating_state(self):
        sm = GestureStateMachine()
        self.assertTrue(sm.can_transition_to("DETECTED"))
        self.assertFalse(sm.can_transition_to("ACTIVE"))
        self.assertEqual(sm.state, "IDLE")

    def test_all_documented_states_are_reachable_and_known(self):
        expected = {
            "IDLE",
            "DETECTED",
            "CANDIDATE",
            "CONFIRMED",
            "ACTIVE",
            "COMPLETED",
            "CANCELLED",
            "COOLDOWN",
        }
        self.assertEqual(VALID_STATES, expected)


if __name__ == "__main__":
    unittest.main()
