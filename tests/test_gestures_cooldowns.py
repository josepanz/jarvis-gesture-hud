"""A-01 (WORKPLAN.md §9, `hardening-and-polish`): GestureEngine's cooldown-gated
events (PINCH_DOWN, RIGHT_CLICK, SCREENSHOT, KEYBOARD_TOGGLE, SILENCE) now go
through a single `jarvis.core.cooldown.CooldownRegistry` instead of 5 ad hoc
`last_*_time` fields with a `now - last_X_time > config.X_COOLDOWN` check repeated
per gesture. The regression this guards against: LEFT and RIGHT click used to
share one cooldown field, so firing one suppressed a genuine, unambiguous
different-family click shortly after (fixed separately, documented in
gestures.py's RIGHT_CLICK comment) - consolidating cooldowns into one registry
must not reintroduce that class of bug for any of the 5 actions.

Per-action "does not repeat within its own cooldown" behavior for SCREENSHOT/
SILENCE/KEYBOARD_TOGGLE is already pinned in test_gesture_engine_regression.py;
this file adds what wasn't covered there: registration against config.py's
values, cross-action independence, and re-firing once a cooldown actually
expires.
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis import config  # noqa: E402
from jarvis.gestures import (  # noqa: E402
    COOLDOWN_CLICK,
    COOLDOWN_KEYBOARD_TOGGLE,
    COOLDOWN_RIGHT_CLICK,
    COOLDOWN_SCREENSHOT,
    COOLDOWN_SILENCE,
    GestureEngine,
)

import test_gesture_engine_regression as regr  # noqa: E402

ALL_COOLDOWN_ACTIONS = {
    COOLDOWN_CLICK: config.CLICK_COOLDOWN,
    COOLDOWN_RIGHT_CLICK: config.RIGHT_CLICK_COOLDOWN,
    COOLDOWN_SCREENSHOT: config.SCREENSHOT_COOLDOWN,
    COOLDOWN_KEYBOARD_TOGGLE: config.KEYBOARD_TOGGLE_COOLDOWN,
    COOLDOWN_SILENCE: config.SILENCE_COOLDOWN,
}


def _expire_cooldown(engine, action):
    """Backdate an action's last-fired timestamp past its own cooldown - the same
    "poke the internal time-tracking field directly" pattern the rest of this
    suite already uses for hold timers (e.g. `engine.lock_start_time = ...`),
    applied to the registry's internal state instead of a per-gesture field."""
    engine.cooldowns._last_fired[action] = time.time() - 10.0


class CooldownRegistrationTests(unittest.TestCase):
    def test_all_five_actions_registered_with_their_config_values(self):
        engine = GestureEngine()
        for action, expected_seconds in ALL_COOLDOWN_ACTIONS.items():
            self.assertEqual(engine.cooldowns.get_cooldown(action), expected_seconds)

    def test_no_more_ad_hoc_last_time_fields(self):
        engine = GestureEngine()
        for stale_name in (
            "last_click_time",
            "last_right_click_time",
            "last_screenshot_time",
            "last_toggle_time",
            "last_silence_time",
        ):
            self.assertFalse(hasattr(engine, stale_name))


class ClickCooldownTests(unittest.TestCase):
    def test_second_pinch_down_within_cooldown_is_suppressed(self):
        engine = GestureEngine()
        regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        regr.process(engine, regr.pinch_click_hand(pinched=False))  # PINCH_UP
        _, _, events = regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        self.assertNotIn("PINCH_DOWN", events)

    def test_pinch_down_fires_again_once_cooldown_expires(self):
        engine = GestureEngine()
        regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        regr.process(engine, regr.pinch_click_hand(pinched=False))
        _expire_cooldown(engine, COOLDOWN_CLICK)
        _, _, events = regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        self.assertIn("PINCH_DOWN", events)


class RightClickCooldownTests(unittest.TestCase):
    def test_second_right_click_within_cooldown_is_suppressed(self):
        engine = GestureEngine()
        regr.process_confirmed_right_click(engine, regr.right_click_hand())
        # Force a fresh was_right_pinching edge without relying on some other
        # fixture's pose to "release" the middle-thumb pinch - flat() doesn't
        # (every landmark collapses to ~the same point, so it trivially still
        # reads as pinching), and most other neutral poses fire unrelated
        # gestures of their own. Directly poking the edge-tracking field is the
        # same "manipulate internal state directly" pattern already used
        # throughout this suite for hold timers.
        engine.was_right_pinching = False
        _, _, events = regr.process(engine, regr.right_click_hand())
        self.assertNotIn("RIGHT_CLICK", events)

    def test_right_click_fires_again_once_cooldown_expires(self):
        engine = GestureEngine()
        regr.process_confirmed_right_click(engine, regr.right_click_hand())
        engine.was_right_pinching = False
        _expire_cooldown(engine, COOLDOWN_RIGHT_CLICK)
        _, _, events = regr.process(engine, regr.right_click_hand())
        self.assertIn("RIGHT_CLICK", events)


class IndependentCooldownRegressionTests(unittest.TestCase):
    """Non-regression for the historical shared-cooldown bug (already pinned in
    test_gesture_engine_regression.py's ClickCooldownIndependenceTests, for the
    two families that actually collided): a fired LEFT click must not put
    RIGHT_CLICK on cooldown, or vice versa, now that both go through the same
    CooldownRegistry."""

    def test_right_click_immediately_after_left_click_is_not_suppressed(self):
        engine = GestureEngine()
        _, _, click_events = regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        self.assertIn("PINCH_DOWN", click_events)
        _, _, rc_events = regr.process_confirmed_right_click(engine, regr.right_click_hand())
        self.assertIn("RIGHT_CLICK", rc_events)

    def test_left_click_immediately_after_right_click_is_not_suppressed(self):
        engine = GestureEngine()
        _, _, rc_events = regr.process_confirmed_right_click(engine, regr.right_click_hand())
        self.assertIn("RIGHT_CLICK", rc_events)
        _, _, click_events = regr.process_confirmed(engine, regr.pinch_click_hand(pinched=True))
        self.assertIn("PINCH_DOWN", click_events)


class LevelTriggeredCooldownExpiryTests(unittest.TestCase):
    """SCREENSHOT/SILENCE/KEYBOARD_TOGGLE are level-triggered (no was_X edge to
    release): only their cooldown gates a repeat. "Doesn't repeat within
    cooldown" is already pinned elsewhere; here we confirm it's a cooldown gate
    and not a one-shot latch, by re-firing once it expires."""

    def test_screenshot_fires_again_once_cooldown_expires(self):
        engine = GestureEngine()
        _, _, first = regr.process_confirmed(engine, regr.screenshot_hand())
        self.assertIn("SCREENSHOT", first)
        _expire_cooldown(engine, COOLDOWN_SCREENSHOT)
        _, _, second = regr.process(engine, regr.screenshot_hand())
        self.assertIn("SCREENSHOT", second)

    def test_silence_fires_again_once_cooldown_expires(self):
        engine = GestureEngine()
        _, _, first = regr.process(engine, regr.silence_hand())
        self.assertIn("SILENCE", first)
        _expire_cooldown(engine, COOLDOWN_SILENCE)
        _, _, second = regr.process(engine, regr.silence_hand())
        self.assertIn("SILENCE", second)

    def test_keyboard_toggle_fires_again_once_cooldown_expires(self):
        engine = GestureEngine()
        _, _, first = regr.process(engine, regr.open_palm_hand())
        self.assertIn("KEYBOARD_TOGGLE", first)
        _expire_cooldown(engine, COOLDOWN_KEYBOARD_TOGGLE)
        _, _, second = regr.process(engine, regr.open_palm_hand())
        self.assertIn("KEYBOARD_TOGGLE", second)


if __name__ == "__main__":
    unittest.main()
