"""TASK-050: comprehensive regression suite for GestureEngine - "verify every
existing capability." Every gesture in ARCHITECTURE.md's Gesture Map table gets a
dedicated, isolated test here. Before this file, most of these were only verified
ad hoc (manual Bash snippets) during earlier development turns, never captured as
a permanent, re-runnable test. Each synthetic hand fixture is deliberately built so
only ONE gesture's conditions are satisfied at a time (unrelated fingers/distances
pushed far apart) - sloppier fixtures earlier in this project's history produced
false positives from accidental overlap, so every fixture here was verified against
the real GestureEngine before being accepted into this file.
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.gestures import GestureEngine  # noqa: E402
from jarvis.hand_tracker import Hand  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")

W, H, SCREEN_W, SCREEN_H = 640, 480, 1920, 1080


def flat(x=0.5, y=0.5):
    return [Landmark(x, y, 0) for _ in range(21)]


def pinch_click_hand(cx=0.5, cy=0.5, pinched=True):
    pts = flat(cx, cy)
    pts[12] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[10] = Landmark(cx + 0.15, cy - 0.15, 0)
    pts[16] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[14] = Landmark(cx + 0.15, cy - 0.15, 0)
    pts[20] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[18] = Landmark(cx + 0.15, cy - 0.15, 0)
    if pinched:
        pts[4] = Landmark(cx, cy, 0)
        pts[8] = Landmark(cx + 0.003, cy, 0)
    else:
        pts[4] = Landmark(cx - 0.3, cy, 0)
        pts[8] = Landmark(cx, cy, 0)
    return pts


def right_click_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[8] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[6] = Landmark(cx + 0.15, cy - 0.15, 0)
    pts[16] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[14] = Landmark(cx + 0.15, cy - 0.15, 0)
    pts[20] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[18] = Landmark(cx + 0.15, cy - 0.15, 0)
    pts[4] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx + 0.003, cy, 0)
    return pts


def scroll_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx - 0.15, cy, 0)
    pts[2] = Landmark(cx - 0.07, cy, 0)
    pts[8] = Landmark(cx, cy - 0.1, 0)
    pts[6] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx, cy - 0.1, 0)
    pts[10] = Landmark(cx, cy, 0)
    pts[16] = Landmark(cx, cy + 0.1, 0)
    pts[14] = Landmark(cx, cy, 0)
    return pts


def zoom_hand(cx=0.5, cy=0.5, ring_y=None):
    # Thumb + ring move TOGETHER (both track `ring_y`), staying pinched at every
    # frame - moving only the ring away from a static thumb breaks the pinch
    # distance outright. Index is extended (not curled, so this isn't mistaken
    # for the screenshot pose) but offset far in X so it never nears the thumb
    # regardless of ring_y. Middle/pinky are genuinely curled (tip.y > pip.y),
    # not just positioned "away" - a tip merely far from the pinch point can
    # still accidentally satisfy the tip.y < pip.y "extended" check and trigger
    # SILENCE/KEYBOARD_TOGGLE, which is exactly the bug this fixture originally had.
    y = cy if ring_y is None else ring_y
    pts = flat(cx, cy)
    pts[8] = Landmark(cx + 0.3, cy - 0.1, 0)
    pts[6] = Landmark(cx + 0.3, cy, 0)
    pts[12] = Landmark(cx + 0.3, cy + 0.1, 0)
    pts[10] = Landmark(cx + 0.3, cy, 0)
    pts[20] = Landmark(cx + 0.3, cy + 0.1, 0)
    pts[18] = Landmark(cx + 0.3, cy, 0)
    pts[4] = Landmark(cx, y, 0)
    pts[16] = Landmark(cx + 0.003, y, 0)
    pts[14] = Landmark(cx, cy, 0)
    return pts


def open_palm_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx - 0.15, cy, 0)
    pts[2] = Landmark(cx - 0.07, cy, 0)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[tip] = Landmark(cx, cy - 0.1, 0)
        pts[pip] = Landmark(cx, cy, 0)
    return pts


def silence_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[tip] = Landmark(cx, cy - 0.1, 0)
        pts[pip] = Landmark(cx, cy, 0)
    pts[4] = Landmark(cx, cy, 0)
    return pts


def volume_hand(cx=0.5, cy=0.5, pinky_y=None):
    # Same fix as zoom_hand: thumb + pinky move TOGETHER (both track `pinky_y`) to
    # stay pinched every frame, and index/middle/ring are genuinely curled
    # (tip.y > pip.y), not just positioned "away" - see zoom_hand's comment for
    # why a merely-distant tip can still accidentally read as "extended."
    y = cy if pinky_y is None else pinky_y
    pts = flat(cx, cy)
    pts[4] = Landmark(cx, y, 0)
    pts[20] = Landmark(cx + 0.003, y, 0)
    pts[18] = Landmark(cx, cy, 0)
    pts[8] = Landmark(cx + 0.3, cy + 0.1, 0)
    pts[6] = Landmark(cx + 0.3, cy, 0)
    pts[12] = Landmark(cx + 0.3, cy + 0.1, 0)
    pts[10] = Landmark(cx + 0.3, cy, 0)
    pts[16] = Landmark(cx + 0.3, cy + 0.1, 0)
    pts[14] = Landmark(cx + 0.3, cy, 0)
    return pts


def screenshot_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx, cy, 0)
    pts[16] = Landmark(cx + 0.003, cy, 0)
    pts[14] = Landmark(cx, cy, 0)
    pts[8] = Landmark(cx, cy + 0.1, 0)
    pts[6] = Landmark(cx, cy, 0)
    pts[20] = Landmark(cx, cy + 0.1, 0)
    pts[18] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx + 0.3, cy - 0.3, 0)
    pts[10] = Landmark(cx + 0.15, cy - 0.15, 0)
    return pts


def shaka_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[20] = Landmark(cx, cy - 0.1, 0)
    pts[18] = Landmark(cx, cy, 0)
    pts[4] = Landmark(cx - 0.1, cy - 0.1, 0)
    pts[2] = Landmark(cx - 0.05, cy, 0)
    pts[8] = Landmark(cx, cy + 0.05, 0)
    pts[6] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx, cy + 0.05, 0)
    pts[10] = Landmark(cx, cy, 0)
    pts[16] = Landmark(cx, cy + 0.05, 0)
    pts[14] = Landmark(cx, cy, 0)
    return pts


def fist_hand(cx=0.5, cy=0.5):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx - 0.08, cy, 0)
    pts[2] = Landmark(cx - 0.04, cy, 0)
    for tip in (8, 12, 16, 20):
        pts[tip] = Landmark(cx, cy + 0.05, 0)
        pts[tip - 2] = Landmark(cx, cy, 0)
    return pts


def open_hand_n_fingers(n, cx=0.7, cy=0.5):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx - 0.08, cy, 0)
    pts[2] = Landmark(cx - 0.04, cy, 0)
    for i, tip in enumerate((8, 12, 16, 20)):
        if i < n:
            pts[tip] = Landmark(cx, cy - 0.05, 0)
        else:
            pts[tip] = Landmark(cx, cy + 0.05, 0)
        pts[tip - 2] = Landmark(cx, cy, 0)
    return pts


def pinch_hand(cx, cy):
    pts = flat(cx, cy)
    pts[4] = Landmark(cx, cy, 0)
    pts[8] = Landmark(cx + 0.005, cy, 0)
    pts[12] = Landmark(cx + 0.1, cy - 0.1, 0)
    pts[10] = Landmark(cx + 0.05, cy - 0.05, 0)
    pts[16] = Landmark(cx + 0.1, cy - 0.1, 0)
    pts[14] = Landmark(cx + 0.05, cy - 0.05, 0)
    pts[20] = Landmark(cx + 0.1, cy - 0.1, 0)
    pts[18] = Landmark(cx + 0.05, cy - 0.05, 0)
    return pts


def fist_with_index_pinch_hand(cx=0.5, cy=0.5):
    """TASK-055 regression fixture, verified against the real pre-fix behavior
    (not just assumed): thumb+index is the closest, intentional pinch; ring and
    pinky are also curled close enough to the thumb to independently satisfy
    SCREENSHOT's own condition (index-curled requirement met too - PINCH_DOWN
    never cared about index's curl state, only its distance from the thumb).

    Confirmed by directly reverting this fix and running this exact fixture:
    pre-fix this fires ['SCREENSHOT', 'PINCH_DOWN'] together - a real
    reproduction of the "se confunde" report, not a guess. (An earlier draft of
    this fixture used index-vs-middle/RIGHT_CLICK instead: that pair turned out
    to be accidentally protected by an unrelated quirk - PINCH_DOWN and
    RIGHT_CLICK share `self.last_click_time` for their cooldowns, and
    PINCH_DOWN's branch runs first each frame, so it stomps the shared timer
    before RIGHT_CLICK's own check runs, blocking it on the same frame
    regardless of this fix. SCREENSHOT uses its own independent
    `last_screenshot_time`, so no such accidental protection exists there -
    this is why that pairing was chosen instead.)
    """
    pts = flat(cx, cy)
    pts[4] = Landmark(cx, cy, 0)  # thumb
    pts[8] = Landmark(cx + 0.003, cy + 0.003, 0)  # index: closest pinch, wins priority
    pts[6] = Landmark(cx + 0.05, cy, 0)  # curled (also satisfies screenshot's index-curled check)
    pts[16] = Landmark(cx + 0.01, cy + 0.01, 0)  # ring: farther than index, still under SCREENSHOT's threshold
    pts[14] = Landmark(cx + 0.05, cy, 0)
    pts[20] = Landmark(cx + 0.01, cy + 0.01, 0)  # pinky curled (screenshot requires it)
    pts[18] = Landmark(cx + 0.05, cy, 0)
    pts[12] = Landmark(cx + 0.3, cy - 0.3, 0)  # middle out of the way
    pts[10] = Landmark(cx + 0.15, cy - 0.15, 0)
    return pts


def two_way_tie_pinch_hand(cx=0.5, cy=0.5):
    """Index (click family) and ring (screenshot family) are equidistant from
    the thumb - an intentionally ambiguous fixture for TASK-055's deterministic
    tie-break requirement. Same independent-cooldown pairing as
    fist_with_index_pinch_hand, for the same verified reason (click vs.
    right-click's shared cooldown timer would mask a click/middle tie)."""
    pts = flat(cx, cy)
    pts[4] = Landmark(cx, cy, 0)
    pts[8] = Landmark(cx + 0.01, cy + 0.01, 0)  # index: same distance as ring below
    pts[6] = Landmark(cx + 0.05, cy, 0)
    pts[16] = Landmark(cx + 0.01, cy + 0.01, 0)  # ring: tied with index
    pts[14] = Landmark(cx + 0.05, cy, 0)
    pts[20] = Landmark(cx + 0.01, cy + 0.01, 0)  # pinky curled (screenshot requires it)
    pts[18] = Landmark(cx + 0.05, cy, 0)
    pts[12] = Landmark(cx + 0.3, cy - 0.3, 0)  # middle out of the way
    pts[10] = Landmark(cx + 0.15, cy - 0.15, 0)
    return pts


def process(engine, pts):
    return engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)


class PointerAndSmoothingTests(unittest.TestCase):
    def test_pointer_moves_with_smoothing(self):
        engine = GestureEngine()
        screen_xy, _, _ = process(engine, flat(0.5, 0.5))
        self.assertEqual(screen_xy, (336, 189))  # regression pin (see test_gestures_smoothing.py too)


class LeftClickDragTests(unittest.TestCase):
    def test_pinch_fires_pinch_down_once(self):
        engine = GestureEngine()
        _, _, events = process(engine, pinch_click_hand(pinched=True))
        self.assertEqual(events, ["PINCH_DOWN"])

    def test_holding_the_pinch_does_not_repeat_pinch_down(self):
        engine = GestureEngine()
        process(engine, pinch_click_hand(pinched=True))
        _, _, events = process(engine, pinch_click_hand(pinched=True))
        self.assertNotIn("PINCH_DOWN", events)

    def test_releasing_the_pinch_fires_pinch_up(self):
        engine = GestureEngine()
        process(engine, pinch_click_hand(pinched=True))
        _, _, events = process(engine, pinch_click_hand(pinched=False))
        self.assertIn("PINCH_UP", events)


class RightClickTests(unittest.TestCase):
    def test_pinch_thumb_middle_fires_right_click(self):
        engine = GestureEngine()
        _, _, events = process(engine, right_click_hand())
        self.assertEqual(events, ["RIGHT_CLICK"])

    def test_does_not_repeat_within_cooldown(self):
        engine = GestureEngine()
        process(engine, right_click_hand())
        _, _, events = process(engine, right_click_hand())
        self.assertNotIn("RIGHT_CLICK", events)


class ScrollTests(unittest.TestCase):
    def test_index_moving_up_scrolls_up(self):
        engine = GestureEngine()
        process(engine, scroll_hand(cy=0.5))
        _, _, events = process(engine, scroll_hand(cy=0.35))
        self.assertIn("SCROLL_UP", events)

    def test_index_moving_down_scrolls_down(self):
        engine = GestureEngine()
        process(engine, scroll_hand(cy=0.35))
        _, _, events = process(engine, scroll_hand(cy=0.5))
        self.assertIn("SCROLL_DOWN", events)


class ZoomTests(unittest.TestCase):
    def test_ring_moving_up_zooms_in(self):
        engine = GestureEngine()
        process(engine, zoom_hand(ring_y=0.5))
        _, _, events = process(engine, zoom_hand(ring_y=0.35))
        self.assertIn("ZOOM_IN", events)

    def test_ring_moving_down_zooms_out(self):
        engine = GestureEngine()
        process(engine, zoom_hand(ring_y=0.35))
        _, _, events = process(engine, zoom_hand(ring_y=0.5))
        self.assertIn("ZOOM_OUT", events)


class VolumeTests(unittest.TestCase):
    def test_pinky_moving_up_raises_volume(self):
        engine = GestureEngine()
        process(engine, volume_hand(pinky_y=0.5))
        _, _, events = process(engine, volume_hand(pinky_y=0.35))
        self.assertIn("VOLUME_UP", events)

    def test_pinky_moving_down_lowers_volume(self):
        engine = GestureEngine()
        process(engine, volume_hand(pinky_y=0.35))
        _, _, events = process(engine, volume_hand(pinky_y=0.5))
        self.assertIn("VOLUME_DOWN", events)


class ScreenshotTests(unittest.TestCase):
    def test_fires_screenshot(self):
        engine = GestureEngine()
        _, _, events = process(engine, screenshot_hand())
        self.assertIn("SCREENSHOT", events)

    def test_does_not_repeat_within_cooldown(self):
        engine = GestureEngine()
        process(engine, screenshot_hand())
        _, _, events = process(engine, screenshot_hand())
        self.assertNotIn("SCREENSHOT", events)


class KeyboardToggleTests(unittest.TestCase):
    def test_open_palm_toggles_keyboard(self):
        engine = GestureEngine()
        _, _, events = process(engine, open_palm_hand())
        self.assertIn("KEYBOARD_TOGGLE", events)

    def test_silence_gesture_never_also_fires_keyboard_toggle(self):
        engine = GestureEngine()
        _, _, events = process(engine, silence_hand())
        self.assertNotIn("KEYBOARD_TOGGLE", events)


class SilenceTests(unittest.TestCase):
    def test_thumb_tucked_to_pinky_fires_silence(self):
        engine = GestureEngine()
        _, _, events = process(engine, silence_hand())
        self.assertIn("SILENCE", events)


class LockSessionTests(unittest.TestCase):
    def test_shaka_held_past_hold_duration_locks(self):
        import time

        engine = GestureEngine()
        process(engine, shaka_hand())
        engine.lock_start_time = time.time() - 2.0
        _, _, events = process(engine, shaka_hand())
        self.assertIn("LOCK_SESSION", events)

    def test_shaka_not_yet_held_long_enough_does_not_lock(self):
        engine = GestureEngine()
        _, _, events = process(engine, shaka_hand())
        self.assertNotIn("LOCK_SESSION", events)


class TwoHandMasterGestureTests(unittest.TestCase):
    def test_both_fists_held_pauses(self):
        import time

        engine = GestureEngine()
        hands = [Hand(fist_hand(0.3, 0.5), "Left"), Hand(fist_hand(0.6, 0.5), "Right")]
        engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        engine.pause_hold_start = time.time() - 2.0
        _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        self.assertEqual(events, ["TOGGLE_ACTIVE"])
        self.assertFalse(engine.active)

    def test_both_shaka_held_closes(self):
        import time

        engine = GestureEngine()
        hands = [Hand(shaka_hand(0.3, 0.5), "Left"), Hand(shaka_hand(0.6, 0.5), "Right")]
        engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        engine.close_hold_start = time.time() - 2.0
        _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        self.assertEqual(events, ["CLOSE_APP"])

    def test_two_hand_pinch_spreading_zooms_in(self):
        engine = GestureEngine()
        h1 = Hand(pinch_hand(0.3, 0.5), "Left")
        engine.process([h1, Hand(pinch_hand(0.5, 0.5), "Right")], W, H, SCREEN_W, SCREEN_H)
        _, _, events = engine.process([h1, Hand(pinch_hand(0.9, 0.5), "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertIn("ZOOM_IN", events)

    def test_meta_menu_all_four_counts(self):
        import time

        expectations = {1: "TOGGLE_LEGEND", 2: "TOGGLE_MIRROR", 3: "LEGEND_ALPHA_UP", 4: "LEGEND_ALPHA_DOWN"}
        for count, expected_event in expectations.items():
            engine = GestureEngine()
            anchor = Hand(fist_hand(0.3, 0.5), "Left")
            selector = Hand(open_hand_n_fingers(count), "Right")
            engine.process([anchor, selector], W, H, SCREEN_W, SCREEN_H)
            engine.meta_hold_start = time.time() - 1.0
            _, _, events = engine.process([anchor, selector], W, H, SCREEN_W, SCREEN_H)
            self.assertIn(expected_event, events, f"count={count}")


class PrimaryHandContinuityTests(unittest.TestCase):
    def test_pointer_keeps_tracking_the_established_hand_even_when_listed_second(self):
        engine = GestureEngine()
        # Establish the primary hand with a single-hand frame first - on a cold
        # start (no established _primary_pos yet), _pick_primary falls back to
        # hands[0] by construction (documented, correct behavior for that case,
        # not what this test is about).
        right_moving = Hand(flat(0.8, 0.5), "Right")
        engine.process([right_moving], W, H, SCREEN_W, SCREEN_H)

        # Now a second, idle hand appears and is listed FIRST. If continuity
        # didn't work, naively using hands[0] would jump the pointer to the idle
        # hand at x=0.2 instead of continuing to track the established one.
        left_idle = Hand(flat(0.2, 0.5), "Left")
        screen_xy, _, _ = engine.process(
            [left_idle, Hand(flat(0.82, 0.5), "Right")], W, H, SCREEN_W, SCREEN_H
        )

        self.assertGreater(screen_xy[0], SCREEN_W // 2)


class PinchPriorityTests(unittest.TestCase):
    """TASK-055: only the smallest-distance pinch condition fires per frame."""

    def test_fist_with_index_pinch_fires_only_pinch_down(self):
        engine = GestureEngine()
        _, _, events = process(engine, fist_with_index_pinch_hand())
        self.assertEqual(events, ["PINCH_DOWN"])
        self.assertNotIn("RIGHT_CLICK", events)
        self.assertNotIn("SCREENSHOT", events)

    def test_fist_with_index_pinch_release_fires_pinch_up_cleanly(self):
        engine = GestureEngine()
        process(engine, fist_with_index_pinch_hand())
        _, _, events = process(engine, pinch_click_hand(pinched=False))
        self.assertIn("PINCH_UP", events)
        self.assertNotIn("SCREENSHOT", events)

    def test_ambiguous_tie_fires_exactly_one_event_deterministically(self):
        engine = GestureEngine()
        _, _, events = process(engine, two_way_tie_pinch_hand())
        fired = [e for e in events if e in ("PINCH_DOWN", "SCREENSHOT")]
        self.assertEqual(len(fired), 1)
        # documented tie-break: "index" is listed before "ring" in gestures.py's
        # pinch-priority candidate list, so index wins an exact tie.
        self.assertEqual(fired, ["PINCH_DOWN"])

    def test_existing_single_pinch_fixtures_are_unaffected(self):
        # Regression: every pre-existing, unambiguous single-condition fixture
        # in this file still fires exactly as it did before TASK-055.
        engine = GestureEngine()
        _, _, events = process(engine, pinch_click_hand(pinched=True))
        self.assertEqual(events, ["PINCH_DOWN"])

        engine = GestureEngine()
        _, _, events = process(engine, right_click_hand())
        self.assertEqual(events, ["RIGHT_CLICK"])

        engine = GestureEngine()
        _, _, events = process(engine, screenshot_hand())
        self.assertIn("SCREENSHOT", events)


if __name__ == "__main__":
    unittest.main()
