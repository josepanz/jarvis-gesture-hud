"""Unit tests for CooldownRegistry (TASK-017)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.cooldown import CooldownRegistry  # noqa: E402


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class CooldownRegistryTests(unittest.TestCase):
    def test_default_cooldowns_match_spec(self):
        reg = CooldownRegistry()
        self.assertEqual(reg.get_cooldown("click"), 0.3)
        self.assertEqual(reg.get_cooldown("system_action"), 0.8)
        self.assertEqual(reg.get_cooldown("gesture_navigation"), 0.5)

    def test_first_fire_always_succeeds(self):
        reg = CooldownRegistry()
        self.assertTrue(reg.try_fire("click"))

    def test_immediate_repeat_is_blocked(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("click")
        self.assertFalse(reg.try_fire("click"))

    def test_fires_again_after_cooldown_elapses(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("click")
        clock.advance(0.31)
        self.assertTrue(reg.try_fire("click"))

    def test_actions_have_independent_cooldowns(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("click")
        self.assertTrue(reg.try_fire("system_action"))

    def test_cooldown_is_configurable_per_action(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.set_cooldown("click", 5.0)
        reg.try_fire("click")
        clock.advance(0.31)
        self.assertFalse(reg.try_fire("click"))

    def test_unregistered_or_zero_cooldown_action_is_never_blocked(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("mouse_move")
        self.assertTrue(reg.try_fire("mouse_move"))  # no cooldown registered - continuous action

    def test_negative_cooldown_rejected(self):
        with self.assertRaises(ValueError):
            CooldownRegistry().set_cooldown("click", -1)

    def test_reset_specific_action(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("click")
        reg.reset("click")
        self.assertTrue(reg.try_fire("click"))

    def test_reset_all(self):
        clock = FakeClock()
        reg = CooldownRegistry(clock=clock)
        reg.try_fire("click")
        reg.try_fire("system_action")
        reg.reset()
        self.assertTrue(reg.try_fire("click"))
        self.assertTrue(reg.try_fire("system_action"))


if __name__ == "__main__":
    unittest.main()
