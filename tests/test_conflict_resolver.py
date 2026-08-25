"""Unit tests for the gesture conflict resolver (TASK-022)."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.conflict_resolver import resolve_conflict  # noqa: E402


def candidate(gesture_type, confidence):
    return SimpleNamespace(gesture_type=gesture_type, confidence=confidence)


class ResolveConflictTests(unittest.TestCase):
    def test_empty_list_returns_none(self):
        self.assertIsNone(resolve_conflict([]))

    def test_single_candidate_wins_trivially(self):
        c = candidate("PINCH", 0.5)
        self.assertIs(resolve_conflict([c]), c)

    def test_higher_priority_type_wins_over_higher_confidence(self):
        pinch = candidate("PINCH", 0.99)
        aim = candidate("TWO_FINGER_AIM", 0.51)
        winner = resolve_conflict([pinch, aim])
        self.assertIs(winner, aim)  # TWO_FINGER_AIM outranks PINCH per DEFAULT_PRIORITY

    def test_same_priority_ties_broken_by_confidence(self):
        low = candidate("PINCH", 0.4)
        high = candidate("PINCH", 0.9)
        self.assertIs(resolve_conflict([low, high]), high)

    def test_exact_tie_is_deterministic_first_wins(self):
        a = candidate("PINCH", 0.5)
        b = candidate("PINCH", 0.5)
        self.assertIs(resolve_conflict([a, b]), a)
        self.assertIs(resolve_conflict([b, a]), b)

    def test_unranked_gesture_type_loses_to_any_ranked_type(self):
        unranked = candidate("MYSTERY_GESTURE", 0.99)
        ranked = candidate("FIST", 0.01)
        self.assertIs(resolve_conflict([unranked, ranked]), ranked)

    def test_custom_priority_is_respected(self):
        pinch = candidate("PINCH", 0.5)
        fist = candidate("FIST", 0.5)
        winner = resolve_conflict([pinch, fist], priority=["FIST", "PINCH"])
        self.assertIs(winner, fist)


if __name__ == "__main__":
    unittest.main()
