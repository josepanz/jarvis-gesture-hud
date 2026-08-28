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
import time
import unittest
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import config  # noqa: E402
from jarvis.gestures import GestureEngine  # noqa: E402
from jarvis.gestures import _is_shaka  # noqa: E402
from jarvis.hand_tracker import Hand  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")

W, H, SCREEN_W, SCREEN_H = 640, 480, 1920, 1080


def flat(x=0.5, y=0.5):
    # El landmark 0 (muñeca) se separa un poco del resto para que el bbox no
    # tenga area 0 (TASK-056 filtra manos por area de bbox de los 21 puntos;
    # una mano real nunca tiene todos sus landmarks exactamente superpuestos).
    # Ningun chequeo de gestos usa el landmark 0, asi que esto no cambia el
    # comportamiento de ningun otro fixture que parte de flat().
    pts = [Landmark(x, y, 0) for _ in range(21)]
    pts[0] = Landmark(x - 0.08, y + 0.2, 0)
    return pts


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
    pts[20] = Landmark(cx, cy + 0.1, 0)  # meñique recogido tambien - pedido explícito
    pts[18] = Landmark(cx, cy, 0)
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


def fist_opening_transition_hand(cx=0.5, cy=0.5):
    """Captured from a real DroidCam feed while closing/opening a fist
    (2026-08-27 live diagnostic): mid-transition, the pinky reads "extended"
    before the other fingers catch up, the thumb is already tip-up, and index/
    middle are still curled - the exact shape _is_shaka checked for, before it
    also required the ring finger curled. The ring stays extended here (not
    yet curled back down), same as the captured frame that produced a false
    is_shaka=True mid-motion, well before the user made any deliberate Shaka."""
    pts = flat(cx, cy)
    pts[20] = Landmark(cx, cy - 0.1, 0)  # pinky extended
    pts[18] = Landmark(cx, cy, 0)
    pts[4] = Landmark(cx - 0.1, cy - 0.1, 0)  # thumb tip above mcp
    pts[2] = Landmark(cx - 0.05, cy, 0)
    pts[8] = Landmark(cx, cy + 0.05, 0)  # index curled
    pts[6] = Landmark(cx, cy, 0)
    pts[12] = Landmark(cx, cy + 0.05, 0)  # middle curled
    pts[10] = Landmark(cx, cy, 0)
    pts[16] = Landmark(cx, cy - 0.1, 0)  # ring EXTENDED (not curled) - the fix's whole point
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


def confirm_pinch(engine, pts):
    """1.5 (measured on real camera): a pinch-family finger needs
    config.PINCH_CONFIRM_FRAMES consecutive frames under its threshold before
    it's allowed to win pinch_winner, absorbing relaxed-hand noise. Call this
    before a test's own process() calls so the FIRST of those already counts
    as "confirmed" (does CONFIRM_FRAMES - 1 warmup calls at the same pose)."""
    for _ in range(config.PINCH_CONFIRM_FRAMES - 1):
        process(engine, pts)


def process_confirmed(engine, pts):
    """confirm_pinch() then one more process() call - for tests asserting an
    edge-triggered pinch-family gesture fires on first genuine, held contact."""
    confirm_pinch(engine, pts)
    return process(engine, pts)


class PointerAndSmoothingTests(unittest.TestCase):
    def test_pointer_moves_with_smoothing(self):
        engine = GestureEngine()
        screen_xy, _, _ = process(engine, flat(0.5, 0.5))
        self.assertEqual(screen_xy, (336, 189))  # regression pin (see test_gestures_smoothing.py too)


class LeftClickDragTests(unittest.TestCase):
    def test_pinch_fires_pinch_down_once(self):
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, pinch_click_hand(pinched=True))
        self.assertEqual(events, ["PINCH_DOWN"])

    def test_holding_the_pinch_does_not_repeat_pinch_down(self):
        engine = GestureEngine()
        confirm_pinch(engine, pinch_click_hand(pinched=True))
        process(engine, pinch_click_hand(pinched=True))  # confirmed - fires here
        _, _, events = process(engine, pinch_click_hand(pinched=True))
        self.assertNotIn("PINCH_DOWN", events)

    def test_releasing_the_pinch_fires_pinch_up(self):
        engine = GestureEngine()
        process_confirmed(engine, pinch_click_hand(pinched=True))
        _, _, events = process(engine, pinch_click_hand(pinched=False))
        self.assertIn("PINCH_UP", events)


class RightClickTests(unittest.TestCase):
    def test_pinch_thumb_middle_fires_right_click(self):
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, right_click_hand())
        self.assertEqual(events, ["RIGHT_CLICK"])

    def test_does_not_repeat_within_cooldown(self):
        engine = GestureEngine()
        confirm_pinch(engine, right_click_hand())
        process(engine, right_click_hand())  # confirmed - fires here
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

    def test_pinky_extended_does_not_scroll(self):
        # Pedido explicito: el resto de los dedos (no solo el anular) tiene
        # que estar recogido para que cuente como el gesto de scroll.
        engine = GestureEngine()
        pts = scroll_hand(cy=0.5)
        pts[20] = Landmark(0.5, 0.4, 0)  # meñique extendido (tip por arriba del pip)
        pts[18] = Landmark(0.5, 0.5, 0)
        process(engine, pts)
        pts2 = scroll_hand(cy=0.35)
        pts2[20] = Landmark(0.5, 0.25, 0)
        pts2[18] = Landmark(0.5, 0.35, 0)
        _, _, events = process(engine, pts2)
        self.assertNotIn("SCROLL_UP", events)


class ZoomTests(unittest.TestCase):
    def test_ring_moving_up_zooms_in(self):
        engine = GestureEngine()
        confirm_pinch(engine, zoom_hand(ring_y=0.5))
        process(engine, zoom_hand(ring_y=0.5))  # confirmed - sets the delta baseline
        _, _, events = process(engine, zoom_hand(ring_y=0.35))
        self.assertIn("ZOOM_IN", events)

    def test_ring_moving_down_zooms_out(self):
        engine = GestureEngine()
        confirm_pinch(engine, zoom_hand(ring_y=0.35))
        process(engine, zoom_hand(ring_y=0.35))
        _, _, events = process(engine, zoom_hand(ring_y=0.5))
        self.assertIn("ZOOM_OUT", events)


class VolumeTests(unittest.TestCase):
    def test_pinky_moving_up_raises_volume(self):
        engine = GestureEngine()
        confirm_pinch(engine, volume_hand(pinky_y=0.5))
        process(engine, volume_hand(pinky_y=0.5))
        _, _, events = process(engine, volume_hand(pinky_y=0.35))
        self.assertIn("VOLUME_UP", events)

    def test_pinky_moving_down_lowers_volume(self):
        engine = GestureEngine()
        confirm_pinch(engine, volume_hand(pinky_y=0.35))
        process(engine, volume_hand(pinky_y=0.35))
        _, _, events = process(engine, volume_hand(pinky_y=0.5))
        self.assertIn("VOLUME_DOWN", events)


class ScreenshotTests(unittest.TestCase):
    def test_fires_screenshot(self):
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, screenshot_hand())
        self.assertIn("SCREENSHOT", events)

    def test_does_not_repeat_within_cooldown(self):
        engine = GestureEngine()
        confirm_pinch(engine, screenshot_hand())
        process(engine, screenshot_hand())  # confirmed - fires here
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

    def test_fist_opening_transition_is_not_read_as_shaka(self):
        # Real-camera regression: a real fist-opening motion transiently
        # matched _is_shaka before it required the ring finger curled too -
        # confirmed live (DroidCam), fixed, and pinned here so it can't
        # silently regress.
        self.assertFalse(_is_shaka(fist_opening_transition_hand()))


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
        _, _, events = process_confirmed(engine, fist_with_index_pinch_hand())
        self.assertEqual(events, ["PINCH_DOWN"])
        self.assertNotIn("RIGHT_CLICK", events)
        self.assertNotIn("SCREENSHOT", events)

    def test_fist_with_index_pinch_release_fires_pinch_up_cleanly(self):
        engine = GestureEngine()
        process_confirmed(engine, fist_with_index_pinch_hand())
        _, _, events = process(engine, pinch_click_hand(pinched=False))
        self.assertIn("PINCH_UP", events)
        self.assertNotIn("SCREENSHOT", events)

    def test_ambiguous_tie_fires_exactly_one_event_deterministically(self):
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, two_way_tie_pinch_hand())
        fired = [e for e in events if e in ("PINCH_DOWN", "SCREENSHOT")]
        self.assertEqual(len(fired), 1)
        # documented tie-break: "index" is listed before "ring" in gestures.py's
        # pinch-priority candidate list, so index wins an exact tie.
        self.assertEqual(fired, ["PINCH_DOWN"])

    def test_existing_single_pinch_fixtures_are_unaffected(self):
        # Regression: every pre-existing, unambiguous single-condition fixture
        # in this file still fires exactly as it did before TASK-055.
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, pinch_click_hand(pinched=True))
        self.assertEqual(events, ["PINCH_DOWN"])

        engine = GestureEngine()
        _, _, events = process_confirmed(engine, right_click_hand())
        self.assertEqual(events, ["RIGHT_CLICK"])

        engine = GestureEngine()
        _, _, events = process_confirmed(engine, screenshot_hand())
        self.assertIn("SCREENSHOT", events)


class PinchConfirmFrameTests(unittest.TestCase):
    """1.5 (measured on a real DroidCam feed 2026-08-27): a relaxed, non-
    pinching hand's thumb-to-fingertip distance briefly crossed the old
    threshold during ordinary movement (index dipped to 15.5px, threshold was
    30px) - "everything fires too easily" report. A single frame under
    threshold now isn't enough; config.PINCH_CONFIRM_FRAMES consecutive
    frames are required."""

    def test_single_frame_under_threshold_does_not_fire(self):
        engine = GestureEngine()
        _, _, events = process(engine, pinch_click_hand(pinched=True))
        self.assertNotIn("PINCH_DOWN", events)

    def test_confirm_frames_consecutive_frames_does_fire(self):
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, pinch_click_hand(pinched=True))
        self.assertIn("PINCH_DOWN", events)

    def test_a_brief_dip_that_never_reaches_confirm_frames_never_fires(self):
        # Simulates the measured real-world case: distance dips under threshold
        # for 1 frame, then moves back out, repeatedly - never sustained long
        # enough to confirm.
        engine = GestureEngine()
        for _ in range(5):
            _, _, events = process(engine, pinch_click_hand(pinched=True))
            self.assertNotIn("PINCH_DOWN", events)
            process(engine, pinch_click_hand(pinched=False))  # breaks the streak


class Pinch3DDistanceTests(unittest.TestCase):
    """TASK-055c: pinch-family distances use the landmark's z coordinate too,
    not just the 2D screen-projected (x, y) distance."""

    def test_close_in_xy_but_far_in_z_does_not_register_as_a_pinch(self):
        # Even held for enough consecutive frames to satisfy TASK-055/1.5's
        # confirm-streak requirement, the z gap alone must keep this from
        # registering - proves the z-distance itself is doing the work here,
        # not just the frame count.
        engine = GestureEngine()
        pts = flat(0.5, 0.5)
        pts[4] = Landmark(0.5, 0.5, 0.0)  # thumb
        pts[8] = Landmark(0.501, 0.501, 0.1)  # index: ~1px away in (x, y), but far in z
        # keep the other fingers clearly out of every pinch-family threshold
        pts[12] = Landmark(0.8, 0.2, 0.0)
        pts[16] = Landmark(0.8, 0.2, 0.0)
        pts[20] = Landmark(0.8, 0.2, 0.0)
        _, _, events = process_confirmed(engine, pts)
        self.assertNotIn("PINCH_DOWN", events)

    def test_flat_z_fixtures_behave_identically_to_before_this_task(self):
        # Every existing fixture in this file uses z=0 throughout - the 3D
        # formula must degrade exactly to the 2D one in that case. Spot-check
        # a representative few rather than re-asserting the whole file.
        engine = GestureEngine()
        _, _, events = process_confirmed(engine, pinch_click_hand(pinched=True))
        self.assertEqual(events, ["PINCH_DOWN"])

        engine = GestureEngine()
        _, _, events = process_confirmed(engine, right_click_hand())
        self.assertEqual(events, ["RIGHT_CLICK"])

        engine = GestureEngine()
        confirm_pinch(engine, volume_hand(pinky_y=0.5))
        process(engine, volume_hand(pinky_y=0.5))
        _, _, events = process(engine, volume_hand(pinky_y=0.35))
        self.assertIn("VOLUME_UP", events)


class ClickCooldownIndependenceTests(unittest.TestCase):
    """PINCH_DOWN and RIGHT_CLICK used to share one cooldown timer
    (last_click_time) - a genuine, unambiguous right-click done shortly after a
    genuine, unambiguous left-click got silently swallowed, since the left
    click's own branch (which runs first each frame) had just reset the shared
    timer. This is a different bug than TASK-055's same-frame ambiguity (which
    already prevents index/middle from both winning in one frame) - this one is
    about two clean, non-overlapping gestures shortly apart in time."""

    def test_genuine_right_click_shortly_after_a_genuine_left_click_still_fires(self):
        engine = GestureEngine()
        process_confirmed(engine, pinch_click_hand(pinched=True))
        _, _, events = process_confirmed(engine, right_click_hand())
        self.assertIn("RIGHT_CLICK", events)

    def test_genuine_left_click_shortly_after_a_genuine_right_click_still_fires(self):
        engine = GestureEngine()
        process_confirmed(engine, right_click_hand())
        _, _, events = process_confirmed(engine, pinch_click_hand(pinched=True))
        self.assertIn("PINCH_DOWN", events)


def two_hand_process(engine, primary_pts, other_pts):
    """primary_pts listed first so _pick_primary picks it on a cold-start
    engine (no established _primary_pos yet)."""
    hands = [Hand(primary_pts, "Right"), Hand(other_pts, "Left")]
    return engine.process(hands, W, H, SCREEN_W, SCREEN_H)


class TwoHandSuppressionTests(unittest.TestCase):
    """TASK-055b: the 7 single-hand checks that had no two-hand suppression
    before this task (SILENCE, KEYBOARD_TOGGLE, SCREENSHOT, single-hand
    ZOOM_IN/OUT, VOLUME_UP/DOWN, SCROLL_UP/DOWN, RIGHT_CLICK) must not fire on
    the primary hand while the OTHER hand makes it a two-hand gesture (here:
    a fist, satisfying the general fists[0] != fists[1] condition - the same
    raw geometric trigger the meta-menu itself is gated on, not the meta-menu's
    own held/confirmed event). LOCK_SESSION and PINCH_DOWN already had their
    own narrower suppression before this task and are unchanged/untested here."""

    def test_silence_suppressed(self):
        engine = GestureEngine()
        _, _, events = two_hand_process(engine, silence_hand(), fist_hand(0.8, 0.5))
        self.assertNotIn("SILENCE", events)

    def test_keyboard_toggle_suppressed(self):
        engine = GestureEngine()
        _, _, events = two_hand_process(engine, open_palm_hand(), fist_hand(0.8, 0.5))
        self.assertNotIn("KEYBOARD_TOGGLE", events)

    def test_screenshot_suppressed(self):
        engine = GestureEngine()
        _, _, events = two_hand_process(engine, screenshot_hand(), fist_hand(0.8, 0.5))
        self.assertNotIn("SCREENSHOT", events)

    def test_single_hand_zoom_suppressed(self):
        engine = GestureEngine()
        two_hand_process(engine, zoom_hand(ring_y=0.5), fist_hand(0.8, 0.5))
        _, _, events = two_hand_process(engine, zoom_hand(ring_y=0.35), fist_hand(0.8, 0.5))
        self.assertNotIn("ZOOM_IN", events)
        self.assertNotIn("ZOOM_OUT", events)

    def test_volume_suppressed(self):
        engine = GestureEngine()
        two_hand_process(engine, volume_hand(pinky_y=0.5), fist_hand(0.8, 0.5))
        _, _, events = two_hand_process(engine, volume_hand(pinky_y=0.35), fist_hand(0.8, 0.5))
        self.assertNotIn("VOLUME_UP", events)
        self.assertNotIn("VOLUME_DOWN", events)

    def test_scroll_suppressed(self):
        engine = GestureEngine()
        two_hand_process(engine, scroll_hand(cy=0.5), fist_hand(0.8, 0.5))
        _, _, events = two_hand_process(engine, scroll_hand(cy=0.35), fist_hand(0.8, 0.5))
        self.assertNotIn("SCROLL_UP", events)
        self.assertNotIn("SCROLL_DOWN", events)

    def test_right_click_suppressed(self):
        engine = GestureEngine()
        _, _, events = two_hand_process(engine, right_click_hand(), fist_hand(0.8, 0.5))
        self.assertNotIn("RIGHT_CLICK", events)

    def test_suppression_lifts_once_the_other_hand_is_no_longer_a_fist(self):
        # Regression: this isn't a permanent lockout - once the second hand
        # stops making it a two-hand gesture, the single-hand check works again.
        engine = GestureEngine()
        two_hand_process(engine, silence_hand(), fist_hand(0.8, 0.5))
        _, _, events = process(engine, silence_hand())
        self.assertIn("SILENCE", events)


def tiny_hand(cx=0.5, cy=0.5):
    """TASK-056: bbox de area muy por debajo de config.MIN_HAND_AREA_FRACTION -
    simula una mano de fondo/otra persona, mucho mas lejos de la camara que el
    usuario (a mayor distancia el area del bbox cae con el cuadrado de la
    distancia, ver config.py)."""
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx - 0.01, cy + 0.02, 0)
    return pts


class BackgroundHandFilterTests(unittest.TestCase):
    """TASK-056: filtro de manos implausibles (fondo/otra persona) antes de
    la logica de gestos - design.md §1.2."""

    def test_lone_tiny_hand_is_filtered_out_entirely(self):
        engine = GestureEngine()
        screen_xy, _, events = engine.process([Hand(tiny_hand(), "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertIsNone(screen_xy)
        self.assertEqual(events, [])

    def test_background_tiny_hand_does_not_block_the_real_hand(self):
        # Un objeto/persona de fondo detectado junto a la mano real del
        # usuario no debe impedir que la mano real siga funcionando normal.
        engine = GestureEngine()
        pts = pinch_click_hand(pinched=True)
        confirm_pinch(engine, pts)
        hands = [Hand(pts, "Right"), Hand(tiny_hand(0.1, 0.1), "Left")]
        _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        self.assertIn("PINCH_DOWN", events)

    def test_two_plausibly_sized_hands_too_far_apart_do_not_trigger_two_hand_gesture(self):
        # Ambas manos son de tamano plausible (no filtradas por area), pero
        # estan en extremos opuestos del frame - implausible para las 2 manos
        # de una misma persona a distancia normal de escritorio (medido en
        # camara real, ver config.py). No deben tratarse como UN gesto de
        # 2 manos aunque geometricamente ambas sean puños.
        import time

        engine = GestureEngine()
        hands = [Hand(fist_hand(0.05, 0.5), "Left"), Hand(fist_hand(0.95, 0.5), "Right")]
        engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        engine.pause_hold_start = time.time() - 2.0
        _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        self.assertNotIn("TOGGLE_ACTIVE", events)

    def test_two_hands_at_normal_desk_distance_still_trigger_two_hand_gesture(self):
        # Regression: el filtro de "misma persona" no debe rechazar el caso
        # normal ya cubierto por TwoHandMasterGestureTests.
        import time

        engine = GestureEngine()
        hands = [Hand(fist_hand(0.3, 0.5), "Left"), Hand(fist_hand(0.6, 0.5), "Right")]
        engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        engine.pause_hold_start = time.time() - 2.0
        _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
        self.assertIn("TOGGLE_ACTIVE", events)


# TASK-061/062 (Fase 4): sellos Naruto de 1 mano. Cada fixture fue verificado
# contra el GestureEngine real antes de aceptarse aca (mismo criterio que el
# resto de este archivo, ver docstring del modulo) - las 4 distancias
# pulgar-a-cada-dedo se calcularon explicitamente para confirmar que ninguna
# cae bajo ningun umbral de pinch (PINCH_CLICK/RIGHT_CLICK/ZOOM/SCREENSHOT/
# VOLUME), y cada fixture se corrio de punta a punta contra GestureEngine.process()
# confirmando que dispara UNICAMENTE su propio NARUTO_<NOMBRE> y ningun otro evento.
def _naruto_base(cx, cy):
    pts = flat(cx, cy)
    pts[5] = Landmark(cx - 0.06, cy, 0)  # index mcp
    pts[9] = Landmark(cx - 0.02, cy, 0)  # middle mcp
    pts[13] = Landmark(cx + 0.02, cy, 0)  # ring mcp
    pts[17] = Landmark(cx + 0.06, cy, 0)  # pinky mcp
    return pts


def naruto_tora_hand(cx=0.5, cy=0.5):
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy - 0.08, 0)
    pts[6] = Landmark(cx - 0.06, cy - 0.03, 0)
    pts[12] = Landmark(cx - 0.05, cy - 0.08, 0)  # muy cerca del indice ("juntos")
    pts[10] = Landmark(cx - 0.02, cy - 0.03, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.08, cy - 0.02, 0)  # pulgar cruzado, cerca de la palma
    pts[2] = Landmark(cx - 0.07, cy, 0)
    return pts


def naruto_u_hand(cx=0.5, cy=0.5):
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.09, cy - 0.08, 0)
    pts[6] = Landmark(cx - 0.06, cy - 0.03, 0)
    pts[12] = Landmark(cx + 0.15, cy - 0.08, 0)  # bien separado del indice ("peace sign")
    pts[10] = Landmark(cx - 0.02, cy - 0.03, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.08, cy - 0.02, 0)  # pulgar tucked
    pts[2] = Landmark(cx - 0.07, cy, 0)
    return pts


def naruto_hitsuji_hand(cx=0.5, cy=0.5):
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.02, cy - 0.08, 0)  # indice cruza a la derecha
    pts[6] = Landmark(cx - 0.06, cy - 0.03, 0)
    pts[12] = Landmark(cx - 0.09, cy - 0.08, 0)  # medio cruza a la izquierda
    pts[10] = Landmark(cx - 0.02, cy - 0.03, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.04, cy - 0.04, 0)
    pts[2] = Landmark(cx - 0.05, cy - 0.01, 0)
    return pts


def naruto_ushi_hand(cx=0.5, cy=0.5):
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy - 0.15, 0)  # solo el indice extendido
    pts[6] = Landmark(cx - 0.06, cy - 0.03, 0)
    pts[12] = Landmark(cx - 0.02, cy + 0.05, 0)
    pts[10] = Landmark(cx - 0.02, cy, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.1, cy + 0.02, 0)  # pulgar recogido junto a los dedos
    pts[2] = Landmark(cx - 0.09, cy, 0)
    return pts


def naruto_uma_hand(cx=0.5, cy=0.5):
    # REDEFINIDO POR SEGUNDA VEZ (verificado en camara real, 2026-08-27) -
    # ver ARCHITECTURE.md y el comentario de `_is_naruto_uma` en gestures.py.
    # Ahora: pulgar+indice+menique extendidos, medio+anular recogidos.
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy - 0.15, 0)  # indice extendido
    pts[6] = Landmark(cx - 0.06, cy - 0.03, 0)
    pts[12] = Landmark(cx - 0.02, cy + 0.05, 0)  # medio recogido
    pts[10] = Landmark(cx - 0.02, cy, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)  # anular recogido
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy - 0.15, 0)  # menique extendido
    pts[18] = Landmark(cx + 0.06, cy - 0.03, 0)
    pts[4] = Landmark(cx - 0.15, cy - 0.05, 0)  # pulgar extendido
    pts[2] = Landmark(cx - 0.1, cy, 0)
    return pts


def naruto_saru_hand(cx=0.5, cy=0.5):
    # REDEFINIDO POR SEGUNDA VEZ (verificado en camara real, 2026-08-27) -
    # ver ARCHITECTURE.md y el comentario de `_is_naruto_saru` en gestures.py.
    # Ahora: puño cerrado con el pulgar hacia ARRIBA (distinto de I, que es
    # hacia el costado) - pulgar alineado con el nudillo medio (landmark 9)
    # en x, bien arriba en y.
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy + 0.05, 0)
    pts[6] = Landmark(cx - 0.06, cy, 0)
    pts[12] = Landmark(cx - 0.02, cy + 0.05, 0)
    pts[10] = Landmark(cx - 0.02, cy, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.02, cy - 0.2, 0)  # pulgar recto hacia arriba desde el mcp medio
    pts[2] = Landmark(cx - 0.02, cy - 0.05, 0)
    return pts


def naruto_inu_hand(cx=0.5, cy=0.5):
    # REDEFINIDO (verificado en camara real, 2026-08-27) - ver
    # ARCHITECTURE.md y el comentario de `_is_naruto_inu` en gestures.py.
    # Ahora: solo el menique extendido, resto recogido.
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy + 0.05, 0)
    pts[6] = Landmark(cx - 0.06, cy, 0)
    pts[12] = Landmark(cx - 0.02, cy + 0.05, 0)
    pts[10] = Landmark(cx - 0.02, cy, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy - 0.15, 0)  # menique extendido
    pts[18] = Landmark(cx + 0.06, cy - 0.03, 0)
    pts[4] = Landmark(cx - 0.1, cy + 0.02, 0)  # pulgar recogido
    pts[2] = Landmark(cx - 0.09, cy, 0)
    return pts


def naruto_i_hand(cx=0.5, cy=0.5):
    # FIX (verificado en camara real, 2026-08-27) - ver ARCHITECTURE.md y el
    # comentario de `_is_naruto_i` en gestures.py. Pulgar bien lateral
    # (domina el eje x, no el y) respecto al mcp medio (landmark 9).
    pts = _naruto_base(cx, cy)
    pts[8] = Landmark(cx - 0.06, cy + 0.05, 0)
    pts[6] = Landmark(cx - 0.06, cy, 0)
    pts[12] = Landmark(cx - 0.02, cy + 0.05, 0)
    pts[10] = Landmark(cx - 0.02, cy, 0)
    pts[16] = Landmark(cx + 0.02, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.02, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.25, cy + 0.01, 0)  # pulgar lateral, mismo nivel que el mcp medio
    pts[2] = Landmark(cx - 0.15, cy, 0)
    return pts


NARUTO_SEAL_FIXTURES = {
    "TORA": naruto_tora_hand,
    "U": naruto_u_hand,
    "HITSUJI": naruto_hitsuji_hand,
    "USHI": naruto_ushi_hand,
    "UMA": naruto_uma_hand,
    "SARU": naruto_saru_hand,
    "INU": naruto_inu_hand,
    "I": naruto_i_hand,
}


def hold_naruto(engine, pts):
    """Primer process() arma el hold; se retrocede el reloj interno mas alla
    de NARUTO_SEAL_HOLD_SECONDS y se llama process() de nuevo - mismo patron
    que LockSessionTests/TwoHandMasterGestureTests usan para LOCK_SESSION/
    TOGGLE_ACTIVE/CLOSE_APP."""
    engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
    engine._naruto_hold_start = time.time() - 1.0
    return engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)


class NarutoOneHandSealTests(unittest.TestCase):
    def test_each_seal_fires_only_its_own_event_after_the_hold(self):
        for name, fixture_fn in NARUTO_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                _, _, events = hold_naruto(engine, fixture_fn())
                self.assertEqual(events, [f"NARUTO_{name}"])

    def test_no_seal_fires_before_the_hold_completes(self):
        for name, fixture_fn in NARUTO_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                _, _, events = engine.process([Hand(fixture_fn(), "Right")], W, H, SCREEN_W, SCREEN_H)
                self.assertEqual(events, [])

    def test_releasing_the_seal_past_the_miss_tolerance_resets_it(self):
        # open_palm_hand() como "sin match" en vez de flat(): flat() tiene
        # las 21 landmarks coincidentes, lo que la hace pellizcar por
        # construccion (d_thumb_index=0) y contamina el assert con un
        # PINCH_UP de paso - open_palm_hand() no matchea ningun sello NI
        # ninguna condicion de pinch.
        engine = GestureEngine()
        engine.process([Hand(naruto_tora_hand(), "Right")], W, H, SCREEN_W, SCREEN_H)
        for _ in range(config.NARUTO_SEAL_MISS_TOLERANCE + 1):  # supera la tolerancia -> reinicia de verdad
            engine.process([Hand(open_palm_hand(), "Right")], W, H, SCREEN_W, SCREEN_H)
        # Rehace el sello - el hold tiene que rearmarse desde 0, no heredar
        # ningun progreso del intento anterior.
        _, _, events = engine.process([Hand(naruto_tora_hand(), "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertEqual(events, [])

    def test_a_brief_flicker_within_the_miss_tolerance_does_not_reset_the_hold(self):
        # Verificado en camara real (2026-08-27): incluso sosteniendo la
        # forma correcta a proposito, la clasificacion parpadea a "ningun
        # sello" por 1 frame suelto de vez en cuando (ruido, no un cambio de
        # pose real) - sin esta tolerancia, el hold casi nunca llega a
        # completarse en la practica.
        engine = GestureEngine()
        pts = naruto_tora_hand()
        engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
        for _ in range(config.NARUTO_SEAL_MISS_TOLERANCE):  # exactamente en el limite, no lo supera
            engine.process([Hand(open_palm_hand(), "Right")], W, H, SCREEN_W, SCREEN_H)
        engine._naruto_hold_start = time.time() - 1.0
        _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
        self.assertEqual(events, ["NARUTO_TORA"])  # el progreso del hold sobrevivio al parpadeo

    def test_none_of_the_existing_gesture_fixtures_leak_a_naruto_event(self):
        existing_fixtures = {
            "pinch_click": pinch_click_hand(),
            "right_click": right_click_hand(),
            "scroll": scroll_hand(),
            "zoom": zoom_hand(),
            "open_palm": open_palm_hand(),
            "silence": silence_hand(),
            "volume": volume_hand(),
            "screenshot": screenshot_hand(),
            "shaka": shaka_hand(),
            "fist": fist_hand(),
            "fist_opening_transition": fist_opening_transition_hand(),
            "flat": flat(),
        }
        for name, pts in existing_fixtures.items():
            with self.subTest(fixture=name):
                engine = GestureEngine()
                for _ in range(3):
                    engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
                engine._naruto_hold_start = time.time() - 1.0
                _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
                self.assertFalse(
                    [e for e in events if e.startswith("NARUTO_")],
                    f"{name} unexpectedly produced a NARUTO_* event: {events}",
                )

    def test_no_seal_fixture_triggers_a_pinch_family_event(self):
        # La otra mitad del censo de colision: cada fixture de sello nuevo NO
        # debe disparar ningun gesto EXISTENTE (no solo lo inverso de arriba).
        for name, fixture_fn in NARUTO_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                pts = fixture_fn()
                for _ in range(3):
                    _, _, events = engine.process([Hand(pts, "Right")], W, H, SCREEN_W, SCREEN_H)
                    self.assertFalse(
                        [e for e in events if not e.startswith("NARUTO_")],
                        f"{name} unexpectedly produced a non-Naruto event: {events}",
                    )


# TASK-064/065 (Fase 5): sellos Naruto de 2 manos. design.md §5.1 permite
# explicitamente un proxy grueso (distancia entre centros + curvatura
# promedio + orientacion) en vez de intentar el entrelazado fino de dedos,
# que MediaPipe no puede ver de forma confiable entre 2 manos. Cada fixture
# fue verificado contra el GestureEngine real antes de aceptarse aca, igual
# que los de 1 mano - dispara UNICAMENTE su propio NARUTO_<NOMBRE>, y ningun
# fixture de 2 manos existente (both_fists/both_shaka/meta-menu) dispara
# ninguno de estos. Umbrales de config.py RAZONADOS, no medidos en camara
# real todavia (pendiente, ver ARCHITECTURE.md).
def ne_hand(cx=0.48, cy=0.5):
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)  # muñeca abajo -> la mano "apunta" hacia arriba
    pts[8] = Landmark(cx - 0.02, cy - 0.15, 0)
    pts[6] = Landmark(cx - 0.02, cy - 0.03, 0)
    pts[12] = Landmark(cx + 0.02, cy - 0.15, 0)
    pts[10] = Landmark(cx + 0.02, cy - 0.03, 0)
    pts[16] = Landmark(cx + 0.04, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.04, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.06, cy, 0)
    pts[2] = Landmark(cx - 0.05, cy, 0)
    return pts


def mi_hand(cx=0.48, cy=0.5):
    # Mismo "entrelazado" que Ne (2 de 4 dedos extendidos) - solo cambia la
    # muñeca, para que la mano "apunte" hacia abajo en vez de hacia arriba.
    pts = list(ne_hand(cx, cy))
    pts[0] = Landmark(cx, cy - 0.2, 0)
    return pts


def tori_hand(cx, cy=0.5):
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[tip] = Landmark(cx, cy - 0.15, 0)
        pts[pip] = Landmark(cx, cy - 0.03, 0)
    pts[4] = Landmark(cx - 0.1, cy, 0)
    pts[2] = Landmark(cx - 0.08, cy, 0)
    return pts


def kai_hand_1(cx=0.46, cy=0.5):
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)
    pts[5] = Landmark(cx - 0.02, cy, 0)
    pts[9] = Landmark(cx + 0.01, cy, 0)
    pts[8] = Landmark(cx + 0.15, cy - 0.15, 0)  # indice cruza hacia el lado de la mano 2
    pts[6] = Landmark(cx, cy - 0.05, 0)
    pts[12] = Landmark(cx + 0.12, cy - 0.18, 0)
    pts[10] = Landmark(cx + 0.01, cy - 0.05, 0)
    pts[16] = Landmark(cx + 0.04, cy + 0.05, 0)
    pts[14] = Landmark(cx + 0.04, cy, 0)
    pts[20] = Landmark(cx + 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx + 0.06, cy, 0)
    pts[4] = Landmark(cx - 0.08, cy, 0)
    pts[2] = Landmark(cx - 0.07, cy, 0)
    return pts


def kai_hand_2(cx=0.54, cy=0.5):
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)
    pts[5] = Landmark(cx + 0.02, cy, 0)
    pts[9] = Landmark(cx - 0.01, cy, 0)
    pts[8] = Landmark(cx - 0.15, cy - 0.15, 0)  # indice cruza hacia el lado de la mano 1
    pts[6] = Landmark(cx, cy - 0.05, 0)
    pts[12] = Landmark(cx - 0.12, cy - 0.18, 0)
    pts[10] = Landmark(cx - 0.01, cy - 0.05, 0)
    pts[16] = Landmark(cx - 0.04, cy + 0.05, 0)
    pts[14] = Landmark(cx - 0.04, cy, 0)
    pts[20] = Landmark(cx - 0.06, cy + 0.05, 0)
    pts[18] = Landmark(cx - 0.06, cy, 0)
    pts[4] = Landmark(cx + 0.08, cy, 0)
    pts[2] = Landmark(cx + 0.07, cy, 0)
    return pts


def tatsu_hand_1(cx=0.48, cy=0.5):
    # Una mano bien cerrada (puño)...
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[tip] = Landmark(cx, cy + 0.05, 0)
        pts[pip] = Landmark(cx, cy, 0)
    pts[4] = Landmark(cx - 0.08, cy, 0)
    pts[2] = Landmark(cx - 0.07, cy, 0)
    return pts


def tatsu_hand_2(cx=0.52, cy=0.5):
    # ...la otra bien abierta - la asimetria de curvatura es la señal de Tatsu.
    pts = [Landmark(cx, cy, 0) for _ in range(21)]
    pts[0] = Landmark(cx, cy + 0.2, 0)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[tip] = Landmark(cx, cy - 0.15, 0)
        pts[pip] = Landmark(cx, cy - 0.03, 0)
    pts[4] = Landmark(cx + 0.08, cy, 0)
    pts[2] = Landmark(cx + 0.07, cy, 0)
    return pts


TWOHAND_SEAL_FIXTURES = {
    "NE": (ne_hand, ne_hand),
    "MI": (mi_hand, mi_hand),
    "TORI": (lambda: tori_hand(0.35), lambda: tori_hand(0.65)),
    "KAI": (kai_hand_1, kai_hand_2),
    "TATSU": (tatsu_hand_1, tatsu_hand_2),
}


def hold_twohand_seal(engine, p1, p2):
    hands = [Hand(p1, "Left"), Hand(p2, "Right")]
    engine.process(hands, W, H, SCREEN_W, SCREEN_H)
    engine._twohand_seal_hold_start = time.time() - 2.0
    return engine.process(hands, W, H, SCREEN_W, SCREEN_H)


class NarutoTwoHandSealTests(unittest.TestCase):
    def test_each_seal_fires_only_its_own_event_after_the_hold(self):
        for name, (fn1, fn2) in TWOHAND_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                _, _, events = hold_twohand_seal(engine, fn1(), fn2())
                self.assertEqual(events, [f"NARUTO_{name}"])

    def test_no_seal_fires_before_the_hold_completes(self):
        for name, (fn1, fn2) in TWOHAND_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                hands = [Hand(fn1(), "Left"), Hand(fn2(), "Right")]
                _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
                self.assertEqual(events, [])

    def test_existing_two_hand_fixtures_do_not_leak_a_naruto_twohand_event(self):
        existing_pairs = {
            "both_fists": (fist_hand(0.3, 0.5), fist_hand(0.6, 0.5)),
            "both_shaka": (shaka_hand(0.3, 0.5), shaka_hand(0.6, 0.5)),
            "meta_menu": (fist_hand(0.3, 0.5), open_hand_n_fingers(1, 0.7, 0.5)),
        }
        for name, (p1, p2) in existing_pairs.items():
            with self.subTest(fixture=name):
                engine = GestureEngine()
                hands = [Hand(p1, "Left"), Hand(p2, "Right")]
                engine.process(hands, W, H, SCREEN_W, SCREEN_H)
                engine._twohand_seal_hold_start = time.time() - 2.0
                _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
                self.assertFalse(
                    [e for e in events if e.startswith("NARUTO_")],
                    f"{name} unexpectedly produced a NARUTO_* two-hand event: {events}",
                )

    def test_no_twohand_seal_fixture_triggers_an_existing_two_hand_event(self):
        for name, (fn1, fn2) in TWOHAND_SEAL_FIXTURES.items():
            with self.subTest(seal=name):
                engine = GestureEngine()
                hands = [Hand(fn1(), "Left"), Hand(fn2(), "Right")]
                engine.process(hands, W, H, SCREEN_W, SCREEN_H)
                engine.pause_hold_start = time.time() - 2.0
                engine.close_hold_start = time.time() - 2.0
                _, _, events = engine.process(hands, W, H, SCREEN_W, SCREEN_H)
                self.assertFalse(
                    [e for e in events if not e.startswith("NARUTO_")],
                    f"{name} unexpectedly produced a non-Naruto event: {events}",
                )


if __name__ == "__main__":
    unittest.main()
