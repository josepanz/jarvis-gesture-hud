# JARVIS Gesture HUD — Personalization & Config UI — Design

## 0. Design objective

Deliver the nine phases in `proposal.md` with the smallest real
architectural footprint, fixing two real reported bugs first, adding one
reusable temporal-gesture primitive (used by two different phases instead of
twice), and reusing `Profile.gesture_bindings`/`CommandBus`/`Command`/the
existing lazy-download pattern everywhere they already fit.

---

# 1. PHASE 1 — Reliability fixes: root-cause analysis

## 1.1 Pinch confusion — confirmed by reading `gestures.py`

`gestures.py`'s `process()` computes, every frame, independently:

```python
d_thumb_index = self._dist(thumb, index, w, h)
d_thumb_middle = self._dist(thumb, middle, w, h)
d_thumb_ring = self._dist(thumb, ring, w, h)
d_thumb_pinky = self._dist(thumb, pinky, w, h)
```

...and then four SEPARATE `if d_thumb_X < THRESHOLD` checks (screenshot,
zoom, volume, click, right-click), each gating its own event, with no
cross-check that the OTHER three fingers are in a state consistent with
that specific gesture (only volume/zoom additionally check `index`'s
extended/curled state; click and right-click check only the thumb distance).

In a natural fist with just thumb+index deployed and pinching, the curled
middle/ring/pinky fingertips fold in near the palm — which, depending on
hand size/camera angle, can land close enough to the thumb's resting point
to ALSO satisfy `d_thumb_middle < PINCH_RIGHT_CLICK` (or ring/pinky
thresholds) in the same frame `d_thumb_index < PINCH_CLICK` is true. Both
`PINCH_DOWN`(click) and `RIGHT_CLICK` (or worse, `SCREENSHOT`/volume/zoom)
can fire together. `main.py`'s dispatch loop
(`for event in events: self._dispatch(...)`) executes every event in the
list, so this isn't just a detection artifact — it becomes a real, visible,
"confused" multi-action firing.

### Fix

Resolve pinch-family ambiguity BEFORE building `events`, as one explicit
step:

```python
PINCH_CANDIDATES = [
    ("SCREENSHOT_PINCH", d_thumb_ring, config.PINCH_SCREENSHOT),   # existing extra conditions still apply
    ("ZOOM_PINCH",       d_thumb_ring, config.PINCH_ZOOM),
    ("VOLUME_PINCH",     d_thumb_pinky, config.PINCH_VOLUME),
    ("CLICK_PINCH",      d_thumb_index, config.PINCH_CLICK),
    ("RIGHT_CLICK_PINCH",d_thumb_middle, config.PINCH_RIGHT_CLICK),
]
matches = [(name, dist) for name, dist, threshold in PINCH_CANDIDATES if dist < threshold]
winner = min(matches, key=lambda m: m[1])[0] if matches else None
```

Then each existing `if d_thumb_X < THRESHOLD:` branch additionally requires
`winner == "<ITS_NAME>"`. This is a minimal, localized change: it does not
touch any branch's existing extra conditions (e.g. screenshot's
`index.y > pts[6].y and pinky.y > pts[18].y`), it only adds one more
AND-condition per branch, computed once up front. The exact constant names
above are illustrative — the implementer MAY name them differently as long
as the priority-by-smallest-distance behavior is preserved and tested.

### Regression risk

Low. The ONLY behavior change is when TWO OR MORE pinch conditions were
simultaneously true before (which was always a bug, per the user's report —
never an intentional multi-fire). When only one condition is true (the
common, correct case today), `winner` is that one condition and nothing
changes.

## 1.2 Cross-person false positives — confirmed by reading `gestures.py`

`HandLandmarker` is constructed with `num_hands=config.MAX_HANDS` (2).
`_process_two_hand_gestures` uses `hands[0]`/`hands[1]` directly — whatever
MediaPipe returns as its top-2-confidence detections, with zero filtering
for hand size, position, or same-person plausibility. If a second person's
hand (or, at extreme confidence-threshold edge cases, any sufficiently
hand-like object) is detected, it becomes eligible for every two-hand
gesture: pause (1.2s hold), close-app (1.5s hold), pinch-zoom, and the
meta-action menu.

### Fix

A new filtering step, run once per frame BEFORE any gesture logic (both
single- and two-hand), in `hand_tracker.py` or a thin wrapper in
`gestures.py` (implementer's choice — keeping it in `gestures.py` avoids
changing `HandTracker`'s public contract, but `hand_tracker.py` already
knows frame dimensions and is arguably the more natural owner; document
whichever is chosen):

```python
def _bbox_area_fraction(landmarks, w, h):
    xs = [p.x for p in landmarks]; ys = [p.y for p in landmarks]
    bbox_w = (max(xs) - min(xs)) * w
    bbox_h = (max(ys) - min(ys)) * h
    return (bbox_w * bbox_h) / (w * h)

def filter_plausible_hands(hands, w, h, min_area_fraction=config.MIN_HAND_AREA_FRACTION):
    plausible = [h for h in hands if _bbox_area_fraction(h.landmarks, w, h) >= min_area_fraction]
    plausible.sort(key=lambda h: _bbox_area_fraction(h.landmarks, w, h), reverse=True)
    return plausible[:2]
```

...plus, specifically for two-hand gesture eligibility (not single-hand
pointer/gesture eligibility, which can still use the larger/more plausible
one alone):

```python
def hands_plausibly_same_person(h1, h2, w, h, max_center_distance_fraction):
    # centers of each hand's bbox; reject if too far apart relative to frame size
    ...
```

`config.py` gains `MIN_HAND_AREA_FRACTION` and
`TWO_HAND_MAX_CENTER_DISTANCE_FRACTION`, both tunable, defaulted
conservatively (permissive enough not to reject the user's own two hands at
a normal desk-webcam distance — the implementer MUST verify this against a
real camera during implementation, same practice as every existing threshold
in `config.py`, and report the chosen defaults and why in the task report).

### Explicit limitation (documented, not silently implied as solved)

This is bounding-box-size and rough-proximity heuristics, not person
re-identification or depth sensing (this project has no depth camera
input). A second person standing close to the user, at a similar distance
from the camera, holding a similarly-sized hand up, is NOT reliably
filtered by this fix. Document this plainly in `ARCHITECTURE.md`'s Known
limitations once implemented — matching this project's established honesty
about what's actually solved versus mitigated.

## 1.3 Testing

Both fixes are synthetic-landmark-testable, same style as the existing
`GestureEngine` regression suite: construct a fist-with-thumb-index-pinch
fixture, assert only `PINCH_DOWN` fires (not `RIGHT_CLICK`); construct a
2-hands-but-implausible-size-difference fixture, assert no two-hand gesture
fires; construct a normal 2-similar-hands fixture, assert two-hand gestures
still fire exactly as before (regression).

## 1.4 The full existing collision surface (corrects an undercount in an
earlier draft of this document)

`process()` does not gate the single-hand checks behind "no two-hand
gesture is active" — `pts = self._pick_primary(hands)` and every check that
follows (silence, keyboard-toggle, screenshot, single-hand zoom, volume,
scroll, click, right-click, single-hand-shaka/lock) run on the primary hand
EVERY frame, independent of whatever `_process_two_hand_gestures` decided
about the other hand. Of those 9 single-hand checks, only 2 have explicit
two-hand suppression today:

```text
LOCK_SESSION        suppressed when both_shaka        (single-hand Shaka+hold)
PINCH_DOWN/PINCH_UP suppressed when both_pinching      (suppress_pinch flag)
```

The other 7 (SILENCE, KEYBOARD_TOGGLE, SCREENSHOT, single-hand ZOOM_IN/OUT,
VOLUME_UP/DOWN, SCROLL_UP/DOWN, RIGHT_CLICK) have NO two-hand suppression —
if the primary hand's shape happens to also satisfy one of them while a
two-hand gesture is in progress on both hands, both fire together today,
pre-existing this proposal.

**Consequence for phases 4-7's collision-avoidance process:** "check against
existing two-hand gestures" (as phases 5-7 said) is necessary but not
sufficient. A NEW TWO-HAND gesture must also be checked against the full
9-check SINGLE-HAND set, because one of its two hands becomes "primary" and
gets evaluated against all of them regardless. A NEW ONE-HAND gesture was
already correctly scoped to check only against the single-hand set (phase
4's original process was right); it does not need to check against the
4 two-hand-specific checks, since a lone hand can never satisfy a check that
requires two hands' landmarks.

Restated as a table, for every phase 4-7 collision census:

```text
New ONE-HAND gesture  → must not collide with: the 9 single-hand checks
                         (+ any earlier phase's new one-hand gestures)
New TWO-HAND gesture  → must not collide with: the 4 two-hand checks
                         AND the 9 single-hand checks (each of its 2 hands,
                         evaluated individually, must not accidentally
                         satisfy a single-hand check)
                         (+ any earlier phase's new gestures, both kinds)
```

**Recommended, not required, scope addition to Phase 1:** since this gap is
real and pre-existing (not introduced by this proposal), the implementer MAY
extend TASK-055/056 (or add a small TASK-055b) to add the same suppression
pattern already used for `LOCK_SESSION`/`PINCH_DOWN` to the other 7
single-hand checks whenever ANY two-hand gesture (existing or new, from
phases 4-7) is concurrently satisfied on both hands. This is optional
because the user's original report was specifically about the pinch-family
ambiguity (§1.1) and cross-person false positives (§1.2), not this — but
leaving it undocumented would mean phases 5-7's new two-hand gestures
inherit the same latent gap the existing ones already have. Report the
decision either way (fixed now vs. explicitly deferred) rather than silently
picking one.

---

# 2. PHASE 2 — Landmark / quadrant visualization

## 2.1 New module: `src/jarvis/hand_visualizer.py`

```python
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                  # palm base
]

def draw_hand_overlay(frame, hands, primary_landmarks, active_gesture_name):
    """Pure cv2 drawing (circles for landmarks, lines for HAND_CONNECTIONS,
    a rectangle for each hand's bounding quadrant). Primary hand drawn in one
    color/thickness, any other detected hand in a dimmer one. active_gesture_name
    (or None) labeled near the primary hand via cv2.putText."""
```

`HAND_CONNECTIONS` is the standard 21-landmark hand topology — publicly
documented hand-landmark connectivity, not something pulled from the removed
`mp.solutions` module (confirmed: the Tasks API this project already
migrated to, `hand_tracker.py`'s docstring, does not ship an equivalent
`draw_landmarks()` helper — this module fills that specific, narrow gap with
plain `cv2`, zero new dependency).

## 2.2 Toggle

Reuse the existing `d` debug-HUD toggle
(`JarvisApp._toggle_debug_hud`/`ContextualHudRenderer.debug`) by adding a
second flag alongside it, OR introduce a dedicated key — either is
acceptable (`spec.md` #2.1 leaves this an implementation choice); document
whichever is chosen in `ARCHITECTURE.md` and the legend.

## 2.3 Wiring

`main.py`'s `run()` loop, right after `hands = self.tracker.process(...)`
and the Phase-1 plausibility filter, calls `draw_hand_overlay(frame, hands,
primary_landmarks, self._last_gesture_name)` when the toggle is on — same
"only when enabled, cheap no-op otherwise" pattern as the existing debug
HUD.

## 2.4 Testing

`HAND_CONNECTIONS`-based line generation and bounding-quadrant computation
are pure functions, testable without a real window/display (assert the
right number of line segments for a synthetic landmark set, assert the
bounding box matches the min/max of the synthetic coordinates). The actual
`cv2.circle`/`cv2.line`/`cv2.putText` calls are visual and stay
manually-verified, consistent with how the rest of the camera-frame drawing
in this project is validated.

---

# 3. PHASE 3 — Reference icon infrastructure

Unchanged from the original version of this proposal — see the version
history note at the top of `proposal.md`. Summary (full detail was already
specified once, repeated here only where phases 4-7 depend on it):

- `src/jarvis/gesture_icons.py`: `ICON_SPECS` (declarative, bitmask of which
  fingers extended + optional glyph name, ONE-HAND or TWO-HAND variants both
  representable), `ensure_icon(key) -> Path`, cached under
  `assets_dir()/gesture_icons/`.
- Drawing via `PIL.Image`/`PIL.ImageDraw` (new dependency: Pillow, added to
  `requirements.txt`). Display via native `tkinter.PhotoImage(file=...)` —
  no `PIL.ImageTk` needed.
- `jarvis.legend.ENTRIES` gains an icon-key field; `build_legend_entries()`
  returns the full tuples; `overlay.init_legend()` renders icon+text rows.
- Every gesture added by phases 4-7 registers one `ICON_SPECS` entry as part
  of its own task (`spec.md` #3.4) — a two-hand seal's icon MAY show two
  simplified hand glyphs side by side to distinguish it visually from a
  one-hand seal's icon (implementer's call, document the convention chosen
  so it stays consistent across ~20 new icons).

---

# 4. PHASE 4 — One-hand Naruto seals

## 4.1 Starting geometric definitions (subject to §4.2's collision process)

```text
Tora    (Tiger)  — index + middle extended together (touching), ring +
                   pinky curled, thumb crossed over the palm.
Ushi    (Ox)     — index extended, middle/ring/pinky curled, thumb resting
                   alongside the curled fingers (distinct from a plain
                   pointing pose by thumb position — verify against no
                   existing pointer-only check exists, since the pointer is
                   driven by index position continuously, not a discrete
                   pose, so this is likely safe by construction).
U       (Hare)   — index + middle extended and SPREAD apart (a "peace sign"
                   shape), ring + pinky curled, thumb tucked.
Uma     (Horse)  — all 5 fingers extended and evenly spread (distinct from
                   existing SILENCE, which specifically requires the thumb
                   tucked toward the pinky — Uma's thumb is out, spread).
Hitsuji (Ram)    — index + middle CROSSED (index over middle, forming an X
                   near the tips), ring + pinky curled.
Saru    (Monkey) — thumb + pinky extended, index/middle/ring curled (verify
                   against Shaka — Shaka today is TWO-HAND-only for
                   CLOSE_APP and single-hand for LOCK_SESSION via `_is_shaka`;
                   this pose IS `_is_shaka`'s shape. Saru MUST be dropped or
                   redefined if it collides — do not silently reuse
                   `_is_shaka`'s geometry for a different meaning, that would
                   violate `apply.md` §15 "never silently change existing
                   gesture meanings").
Inu     (Dog)    — ring + pinky extended together, index/middle curled,
                   thumb resting on the curled fingers.
I       (Boar)   — closed fist with the thumb extended outward to the side
                   (not tucked in like a plain fist, not up).
```

`Saru` is flagged above as the highest-risk one-hand entry — the
implementing agent MUST resolve that flag during §4.2's process before
writing `is_naruto_saru`, not defer it.

## 4.2 Collision-avoidance process

Identical process to the one already specified for the original 5-seal
version: enumerate every existing pose check (now including Phase 1's
fixes), write positive + negative synthetic-landmark tests per seal,
adjust/drop/rename on conflict, document the final roster and any changes
in the task report.

## 4.3-4.5 Wiring, safety, icons

Identical mechanism to the original proposal: `NARUTO_<NAME>` events from
`GestureEngine.process()`, default-binding dict, `Profile.gesture_bindings`
override, dispatch reuse via the same fixed-vocabulary path voice already
uses, icon per Phase 3.

---

# 5. PHASE 5 — Two-hand Naruto seals

## 5.1 Starting geometric definitions

```text
Ne    (Rat)    — hands clasped together, fingers interlocked, held in front
                 of the chest.
Tatsu (Dragon) — one hand's fingers wrap over the other's in a layered
                 shape, thumbs crossed.
Mi    (Snake)  — hands clasped, fingers interlocked, pointed DOWNWARD
                 (distinguish from Ne by orientation/hand-y-position, not
                 finger shape alone, since both are "clasped/interlocked").
Tori  (Bird)   — fingers interlocked, hands fanned open/spread rather than
                 clasped tight.
Kai   (Release)— palms together, fingers interlaced, EXCEPT index and
                 middle fingers extended and crossed on top.
```

These are the hardest poses in this proposal to detect reliably from sparse
landmarks (fine finger-interlacing is genuinely difficult to distinguish
combinatorially — MediaPipe's 21 points per hand don't capture inter-hand
finger occlusion well). The implementer SHOULD budget more iteration here
than phase 4, and MAY simplify a seal's exact finger-interlacing requirement
to a coarser proxy (e.g. "both hands' centers within X distance, both
hands' average finger curl above/below a threshold, relative hand
orientation") as long as the simplification is documented and the seal
remains visually recognizable and distinguishable from the other four.

## 5.2 Collision-avoidance

Same process, EXPANDED scope: must also check against `both_shaka`,
`both_fists`, the two-hand pinch-zoom (`both_pinching`), and the anchor+
finger-count meta-menu (`fists[0] != fists[1]`) — all four already live in
`_process_two_hand_gestures`. This is explicitly the largest single
collision-avoidance task in the whole proposal (`proposal.md` §3's table
already flags this).

## 5.3 Wiring, safety, icons

Same as §4.3-4.5, via `_process_two_hand_gestures`'s existing pattern
(compute `p1`/`p2` from both hands, evaluate the new pose pair, emit the
seal event, apply the standard hold-then-confirm timing pattern already used
by `both_shaka`/`both_fists` to avoid single-frame flicker).

---

# 6. PHASE 6 — Jujutsu Kaisen gestures

## 6.1 Gojo — Domain Expansion / Ryoiki Tenkai (two-hand, static)

`JJK_GOJO_DOMAIN` names this gesture specifically (not "any Gojo gesture" —
he has several iconic ones; this is the hand-frame pose associated with
opening his Domain Expansion, "Unlimited Void"/Ryoiki Tenkai).

Both hands' thumb+index fingers form roughly perpendicular L-shapes,
brought together (hand centers close, per the same proximity check style as
the two-hand pinch-zoom) in the UPPER portion of frame (both hands' y
position above some threshold — approximating "held up near the face").
Starting heuristic: angle between each hand's thumb→index vector is roughly
90°±tolerance, AND the two hands' centers are within a proximity threshold,
AND both hands' average y position is above (numerically less than, in
normalized image coordinates) a configurable threshold.

## 6.2 Sukuna (one-hand, TEMPORAL — new reusable detector)

New module `src/jarvis/temporal_gesture.py`:

```python
class ImpulseDetector:
    """Fires once when a tracked distance metric drops below `contact_threshold`
    then rises back above `release_threshold` within `max_window_seconds` of
    the drop - a "snap" or "clap" shape (fast approach + fast separation),
    NOT a sustained pinch/hold (which existing PINCH_* gestures already own).

    update(distance, now) -> bool  (True exactly once per completed impulse)
    """
    def __init__(self, contact_threshold, release_threshold, max_window_seconds):
        ...
```

`JJK_SUKUNA` = one `ImpulseDetector` instance tracking `d_thumb_middle`
(reuses the distance already computed for `RIGHT_CLICK`'s pinch — note in
§4.2-equivalent collision testing that `RIGHT_CLICK`'s SUSTAINED
below-threshold check and Sukuna's IMPULSE (drop-then-rise) check are
temporally distinguishable by construction: a sustained right-click pinch
never triggers the impulse detector's release condition quickly enough,
and a snap never stays below `RIGHT_CLICK`'s threshold long enough to
satisfy that gesture's own timing — verify this with a temporal synthetic
test, not just a single-frame one, since this is the first TEMPORAL/
multi-frame-pattern gesture check in `gestures.py` outside the existing
hold-timers).

## 6.3 Megumi (one-hand, static — ONE representative pose)

Megumi's Ten Shadows Technique canonically involves multiple distinct
shikigami (the exact count/roster shown across the source material is not
precisely pinned down here, and isn't load-bearing for this spec — see
`proposal.md` §5's non-goal: this phase does not attempt one seal per
shikigami regardless of how many there turn out to be). `JJK_MEGUMI` SHALL
be ONE stylized, representative "summon" pose standing in for the technique
as a whole.

Starting heuristic: index + middle fingers crossed (similar family to
Hitsuji's cross, but Megumi's SHALL be visually/geometrically distinguished
from Hitsuji — e.g. by ring finger position: extended vs. curled — resolve
the exact distinguishing detail during §6.4's collision process, do not ship
Megumi identical to Hitsuji with only the bound action differing).

## 6.4 Collision-avoidance, wiring, safety, icons

Same process as phases 4-5, expanded to include phases 4-5's new gestures
too. `ImpulseDetector` (§6.2) is a new primitive — document it in
`ARCHITECTURE.md`'s module list once implemented, since Phase 7 reuses it.

---

# 7. PHASE 7 — Common gestures

## 7.1 Clap (two-hand, temporal)

A second `ImpulseDetector` instance (§6.2, reused not reimplemented)
tracking the distance between the two hands' centers (same center
computation already used by the two-hand pinch-zoom,
`(p[4].x + p[8].x)/2, ...` — for clap, the relevant center is each hand's
overall palm center, e.g. the average of landmarks 0/5/9/13/17, not the
pinch-point average). Fires `CLAP` once per completed impulse (hands come
together then separate — this deliberately does NOT trigger on hands
merely passing near each other while doing something else, since the
detector requires the CONTACT threshold to actually be crossed, not just
approached).

## 7.2 Korean finger heart (one-hand, static, highest collision risk)

Thumb and index fingertips crossed at a shallow angle (not
fingertip-to-fingertip contact like `PINCH_CLICK`, but thumb laid diagonally
across/near the index's first joint) — geometrically close enough to
`PINCH_CLICK` that a bare distance threshold is not sufficient
discrimination on its own. Per `spec.md` #7.2, this gesture REQUIRES a hold
duration (same `now - hold_start > config.SOME_HOLD_SECONDS` pattern as
`LOCK_SESSION`) before firing — a fast touch-and-release stays exclusively
`PINCH_DOWN`/`PINCH_UP`, only a SUSTAINED version of the pose (past the pinch
distance's own click-cooldown window) is eligible to become
`KOREAN_HEART`. This is the cleanest available discrimination given the
geometric overlap, and mirrors an already-proven pattern in this codebase
(Shaka-hold vs. a passing Shaka-shaped frame).

## 7.3 Collision-avoidance, wiring, safety, icons

Same process as phases 4-6, expanded to include them.

---

# 8. Why phases 4-7 don't need phase 8

Same reasoning as the original proposal: `Profile.gesture_bindings` already
supports code-level assignability before any UI exists. Phase 8 later adds a
GUI on top of the exact same mechanism, it does not replace it.

---

# 9. PHASE 8 — Settings screen

Unchanged from the original version of this proposal — full detail already
specified there (persistence schema, `HotkeyCommand`/`MacroCommand`,
Tooltip helper, gear icon, non-blocking requirement, M1/M2/M3 feasibility
notes). Repeated pointer, not re-derived: `config_store.py`,
`settings_ui.py`, `actions/macro.py`, JSON schema versioned from day one,
atomic writes, `pyautogui.hotkey()` already covering shortcut/macro
execution with no new dependency.

The bindings table (`spec.md` #8.2) now additionally lists every trigger
`ICON_SPECS` key from phases 3-7 — sourced from the same data structures
those phases already build (`gesture_icons.ICON_SPECS`, the seal default-
binding dicts, `VoiceIntentResolver`'s registered phrases), not a fifth
hand-maintained list.

---

# 10. PHASE 9 — Voice model download icon

Unchanged from the original version of this proposal — a row inside the
Phase 8 settings screen, dependency check via `importlib.util.find_spec`,
background-thread download reusing `jarvis.llm_intent._ensure_model_path()`,
progress via `urlretrieve`'s `reporthook`, idempotent on an
already-downloaded model.
