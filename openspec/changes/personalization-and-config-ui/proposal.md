# JARVIS Gesture HUD — Personalization & Config UI

## 1. Summary

This change adds the following to the existing, shipped application:

```text
1. Two detection-reliability fixes for existing gestures (real bugs, found by
   reading the current gestures.py — see §2 below).
2. A toggleable hand-landmark / quadrant visualization overlay, showing which
   hand and which gesture currently has priority.
3. Reference icon infrastructure (one pictogram per gesture, generated, not
   hand-authored binary assets).
4. The full Naruto hand-seal set: one-hand AND two-hand static seals.
5. Jujutsu Kaisen-inspired gestures: Gojo's Domain Expansion (Ryoiki
   Tenkai), Sukuna's finger-snap, Megumi's Ten Shadows summon.
6. Common gestures: clapping, Korean finger heart.
7. A settings screen (gear icon) with tooltips to bind any of the above to
   actions, including custom shortcuts and macros (M1/M2/M3-style keys).
8. A "download voice model" control inside that settings screen.
```

Every new gesture (4, 5, 6) SHALL ship with its icon (3) as part of the same
task — icons are not a separate, later phase for anything added after this
proposal's first phase establishes the icon infrastructure.

Every two-hand gesture (existing or new) SHALL be a hierarchy, not two
hands independently interpreted as unrelated single-hand gestures that
happen to coincide — `design.md` §1.5 formalizes this into four allowed
patterns and one explicitly forbidden one. This governs phases 5-7.

This is an ADDITIVE change over the currently-shipped app (`main` as of this
writing). It follows the same incremental philosophy as
`openspec/changes/multimodal-interaction-core/`: the existing application is
the baseline, nothing existing SHALL be silently removed or renamed, and every
phase SHALL leave the application runnable. It reuses
`multimodal-interaction-core/apply.md` as its execution protocol verbatim —
not duplicated here.

This is a revision of the original, narrower version of this proposal (5
Naruto seals only, no reliability fixes, no visualization). Nothing from that
version was implemented yet, so this file replaces it rather than layering on
top of it.

---

## 2. Why the reliability fixes come first

While specifying phase 4-6, the current `src/jarvis/gestures.py` was read in
full to make sure new gestures wouldn't collide with anything existing. That
reading surfaced two real, reproducible bugs the user independently reported
from actual use, with a concrete root cause for each — see `design.md` §1 for
the full analysis. Summary:

- **Pinch confusion (fist vs. open hand):** every pinch-style gesture
  (click/drag, right-click, screenshot, zoom, volume) computes its own
  thumb-to-fingertip distance independently, with no check that the OTHER
  fingers are in a state consistent with that specific gesture. When the
  hand is a fist with only thumb+index deployed and pinching, the curled
  middle/ring/pinky fingertips end up physically close to the thumb's resting
  position too (a natural consequence of a fist's geometry), so more than one
  pinch condition can become true in the same frame — e.g. `PINCH_DOWN`
  (click) and `RIGHT_CLICK` firing together. That is exactly the "se
  confunde" behavior reported.
- **Cross-person false positives:** `HandLandmarker` is configured for up to
  2 hands with no size/plausibility filtering. Two-hand gestures
  (`_process_two_hand_gestures`) use whichever 2 hands MediaPipe returns,
  with no check that they belong to the same person, are close to the
  camera, or are even similarly sized. A second person's hand entering frame
  can combine with the user's own hand to spuriously satisfy a two-hand
  gesture (including the 1.2s-hold pause and the 1.5s-hold close-app
  gestures).

Both are contained fixes to existing code, no new dependency, directly
improve the reliability of every gesture added by this proposal too — hence
first in the order, ahead of anything new.

---

## 3. Ordering rationale (menor a mayor)

| # | Phase | What | Complexity | New deps | Why here |
|---|---|---|---|---|---|
| 1 | Reliability fixes | Pinch-priority resolution + background/other-person hand filtering | Low–Moderate | None | Fixes existing, reported bugs. Contained to `gestures.py`. Everything after this benefits from more reliable detection. |
| 2 | Landmark/quadrant visualization | Debug overlay: skeleton, bounding quadrant, primary hand + active gesture label, toggleable | Low–Moderate | None | Pure drawing/toggle, no new gesture logic. Genuinely useful WHILE building phases 4-7 (visually confirming landmark geometry beats guessing thresholds blind) — sequencing it here is a practical dependency, not just a complexity score. |
| 3 | Icon infrastructure | Procedural pictogram generation + legend rendering | Low | +Pillow | Self-contained. Every gesture added in phases 4-7 depends on this existing first. |
| 4 | One-hand Naruto seals | 8 single-hand static zodiac seals | Moderate | None | Same detection style as existing single-hand gestures (`gestures.py`'s pose checks). |
| 5 | Two-hand Naruto seals | 5 two-hand static zodiac/release seals | Moderate | None | Same style as existing `both_shaka`/`both_fists` two-hand checks — one class harder than phase 4 only because of the 2-hand collision surface (must also not collide with existing pause/close/pinch-zoom/meta-menu two-hand gestures). |
| 6 | Jujutsu Kaisen gestures | Gojo (2-hand static), Megumi (1-hand static), Sukuna (1-hand TEMPORAL snap) | Moderate–High | None | Sukuna's finger-snap needs a genuinely new capability: temporal/motion-impulse detection (thumb+finger distance drops then rises within a short window). Built once here, reused by phase 7's clap. |
| 7 | Common gestures | Clap (2-hand temporal, reuses phase 6's impulse detector), Korean finger heart (1-hand static, highest collision risk with existing pinch-click — needs a hold-confirmation like `LOCK_SESSION` already has) | Moderate | None | Reuses phase 6's new temporal-detection machinery; the Korean heart needs the most careful collision handling of any single gesture in this proposal. |
| 8 | Settings screen | Gear icon, tooltips, bindings table (now listing every trigger from phases 1-7), custom shortcuts, macros, persistence | High | None (see `design.md` §9 for why) | Same reasoning as before: only phase needing a persistence layer + new UI subsystem. Its bindings table is only meaningfully complete once phases 3-7 exist, hence it comes after them. |
| 9 | Voice model download icon | One row inside the settings screen | Low (gated) | None | Small in isolation; ordered last because it needs phase 8's screen to live in, per the user's own phrasing. |

Recommended execution order: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9**. Per
`apply.md` §26, stop after each task and report — do not auto-continue to
the next phase.

---

## 4. Goals

The system SHALL, across the nine phases:

1. No longer fire more than one pinch-family gesture from a single
   thumb-to-fingertip configuration in one frame (§ reliability, phase 1).
2. Substantially reduce (not necessarily eliminate — see `design.md` §1.2's
   honesty note) spurious two-hand gestures caused by a second person's hand
   entering frame (phase 1).
3. Offer a toggleable overlay showing hand landmarks, a bounding
   quadrant/box per detected hand, which hand is currently "primary", and
   which gesture (if any) is currently being recognized (phase 2).
4. Show a small reference icon next to every gesture entry, existing and new
   (phase 3, applied to every gesture added by phases 4-7 too).
5. Recognize the one-hand and two-hand Naruto zodiac seal poses listed in
   `design.md` §4-5, each independently assignable to an action (phases
   4-5).
6. Recognize Gojo's, Sukuna's, and Megumi's signature gestures as described
   in `design.md` §6, each independently assignable to an action (phase 6).
7. Recognize a two-hand clap and a one-hand Korean finger heart, each
   independently assignable to an action (phase 7).
8. Provide the settings screen and voice-download icon exactly as specified
   in the original proposal (phases 8-9, content unchanged from the prior
   version of this document, only their position/rationale updated).

## 5. Non-goals

Same as before, plus:

- **Authentic reproduction of every canonical seal/technique.** Real Naruto
  seals and JJK techniques vary by source panel/episode and are often
  two-hand finger-interlacing shapes too fine-grained to detect reliably
  from 21 sparse landmarks. This proposal scopes to a curated,
  MUTUALLY-DISTINGUISHABLE, recognizable-at-a-glance approximation of each,
  documented plainly as such (`design.md` §4-6) rather than promised as
  pixel-perfect canon accuracy.
- **All 10 of Megumi's shikigami-specific seals.** One representative pose
  only (`design.md` §6.3).
- **Perfect rejection of every possible false-positive hand.** The
  background/other-person filtering in phase 1 is a plausibility heuristic
  (size, position, continuity) — it reduces, not eliminates, false
  positives, and this is stated honestly rather than promised as solved.
- Everything already listed as non-goals in the original proposal (no
  gesture-authoring-via-UI, no vendor macro-key SDK integration, no runtime
  `pip install`, no global hotkey capture, no animated GIFs).

---

## 6. Compatibility requirement

Unchanged from the original proposal — no phase is complete if an existing
supported capability is silently broken, including every gesture that
already ships today.

---

## 7. Evaluated, not yet scheduled: perception robustness

Per an explicit request to evaluate (not yet commit to implementing):
MediaPipe Pose, the already-computed-but-unused landmark `z`/`visibility`/
`presence` fields, and OpenCV-based lighting normalization, as ways to
further strengthen Phase 1's reliability fixes. Full findings, verified
against this project's actual installed environment:
`design.md` Appendix A.

Short version: the z-coordinate improvement and CLAHE lighting
normalization are genuinely free (zero new dependency, zero new download)
and would rank as LOW complexity if scheduled — comparable to or below
Phase 1. MediaPipe Pose is also zero-new-dependency (same `mediapipe`
package already installed) but carries a real second-inference performance
cost that needs measuring before committing — comparable to Phase 5's
complexity if scheduled. No phase numbers are assigned to any of this yet.
