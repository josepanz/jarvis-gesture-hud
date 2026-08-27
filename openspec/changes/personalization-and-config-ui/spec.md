# JARVIS Gesture HUD — Personalization & Config UI — Technical Specification

## 1. Scope

This specification defines the required behavior for the nine phases in
`proposal.md`. Every requirement SHALL be treated as normative unless marked
optional/future. Section numbers are stable — code SHOULD reference them as
`spec.md #N`, matching this project's existing convention.

---

# PHASE 1 — Detection reliability fixes

## 1.1 Pinch-priority resolution

When more than one pinch-family condition (`PINCH_DOWN`/click,
`RIGHT_CLICK`, `SCREENSHOT`, zoom, volume — everything in `gestures.py`
gated by a `d_thumb_*` distance threshold) would independently evaluate to
true in the same frame, the system SHALL fire at most ONE of them: the one
whose thumb-to-fingertip distance is smallest (i.e. the tightest, most
likely intentional pinch). The others SHALL be suppressed for that frame,
not queued or fired on a later frame from stale state.

This SHALL NOT change the currently-correct case: a hand with only ONE
finger's tip near the thumb (all others clearly extended or clearly curled
in a way that keeps their tips far from the thumb) continues to behave
exactly as it does today.

## 1.2 Background / other-person hand filtering

Before any gesture logic runs, detected hands SHALL be filtered by
plausibility:

- A hand whose landmark bounding box occupies less than a configurable
  minimum fraction of the frame area SHALL be discarded (too small/too far
  to plausibly be the user's own hand held up to the camera).
- If more than 2 hands remain after that filter, only the 2 largest (by
  bounding-box area) SHALL be kept.
- Two-hand gestures SHALL additionally require the two candidate hands to be
  within a configurable maximum distance of each other in frame (a rough
  same-person plausibility check) — if not, two-hand gesture evaluation
  SHALL be skipped for that frame (single-hand gestures MAY still evaluate
  against the more plausible/larger of the two).

This is a plausibility heuristic, not person re-identification. It SHALL
NOT be documented or reported as eliminating all false positives from other
people in frame — only reducing the common case (a passerby's hand entering
frame at typical webcam distance, smaller/farther than the user's own hand
held up close).

## 1.3 Regression requirement

Every existing gesture's currently-passing test SHALL still pass unchanged
after this phase. This phase adds filtering/priority logic; it SHALL NOT
change any existing gesture's landmark geometry/thresholds.

---

# PHASE 2 — Landmark / quadrant visualization

## 2.1 Toggle

The overlay SHALL be off by default and toggleable independently from the
existing debug HUD (`d` key / `ContextualHudRenderer`) — reuse that same
toggle key/mechanism if practical, or a new one; either is acceptable as
long as it is documented and does not change the meaning of an existing key.

## 2.2 Content

When enabled, for each hand currently considered (post Phase-1 filtering),
the overlay SHALL draw, on the camera frame:

- the 21 hand landmarks and the standard connections between them (a
  skeleton), using plain `cv2` primitives — see `design.md` §3.2 for why
  `mp.solutions.drawing_utils` is not available here;
- a bounding quadrant/box around the hand;
- a visual distinction between the PRIMARY hand (the one driving the
  pointer/single-hand gestures, per `GestureEngine._pick_primary`) and any
  other detected hand (e.g. different box color/thickness);
- the name of the gesture currently being recognized for that hand, if any,
  positioned near the hand.

## 2.3 Non-interference

Enabling this overlay SHALL NOT change any gesture-detection behavior or
measurably regress frame rate beyond what's expected of additional drawing
calls already present for the existing debug HUD.

---

# PHASE 3 — Reference icon infrastructure

(Unchanged from the original version of this proposal.)

## 3.1 Icon generation

Every gesture entry (existing, and every one added by phases 4-7) SHALL have
an associated icon, generated procedurally (no hand-authored binary image
assets committed to the repository) and cached on disk under
`jarvis.paths.assets_dir() / "gesture_icons/"`, one PNG per gesture key,
same lazy-generate-and-cache pattern as the MediaPipe model download.

Icons SHALL be small: 48×48px or smaller.

## 3.2 Icon content

Each icon SHALL visually distinguish itself from every other icon in the
set — a stylized hand glyph (palm outline + marked extended/curled fingers,
one-hand or two-hand as appropriate) plus a small action glyph is
sufficient; photorealistic rendering is not required.

## 3.3 Legend integration

The legend panel SHALL show, for every entry, its icon next to its existing
gesture-name/action text. Existing legend behavior (toggle, opacity,
anchoring, click-through) SHALL be unaffected.

## 3.4 Requirement for every new gesture (phases 4-7)

Every task that adds a new recognizable gesture in phases 4-7 SHALL include,
as part of that same task's acceptance criteria, a working icon for that
gesture generated via this phase's infrastructure. Icons SHALL NOT be
deferred to a separate later task once phase 3 exists.

## 3.5 Deferred: animated reference

Unchanged: per-gesture animated (GIF) demonstrations remain explicitly
deferred, scoped as a future follow-up if requested.

---

# PHASE 4 — One-hand Naruto seals

## 4.1 Roster

At least the following 8 single-hand, static seals SHALL be recognized (see
`design.md` §4.1 for a starting geometric definition of each, subject to the
collision-avoidance process, §4.2):

```text
Tora   (Tiger)
Ushi   (Ox)
U      (Hare)
Uma    (Horse)
Hitsuji(Ram)
Saru   (Monkey)
Inu    (Dog)
I      (Boar)
```

## 4.2 Collision-avoidance process (normative)

Before finalizing thresholds, the implementing agent MUST execute the same
process specified in the original proposal's design: enumerate every
existing single-hand pose check (including Phase 1's changes and anything
already added by an earlier task in this same phase), write a
synthetic-landmark test per seal proving no collision either direction,
adjust/rename/drop on conflict. This applies to phases 4, 5, 6, and 7
individually AND cumulatively — a later phase's new gesture must not
collide with an earlier phase's new gesture either.

## 4.3 Assignability and dispatch

Identical mechanism to the original proposal's Naruto phase: default binding
dict, overridable via `Profile.gesture_bindings`, dispatched through the
same fixed-action-vocabulary path already used by voice
(`_dispatch_voice_action` or equivalent). No new binding mechanism.

## 4.4 Safety

Unchanged requirement: a seal bound to a `HOLD_REQUIRED`/`DESTRUCTIVE`
command SHALL NOT bypass that command's existing gating.

## 4.5 Icons

Every seal SHALL have an icon per Phase 3 §3.4.

---

# PHASE 5 — Two-hand Naruto seals

## 5.1 Roster

At least the following 5 two-hand, static seals SHALL be recognized (see
`design.md` §5.1):

```text
Ne    (Rat)
Tatsu (Dragon)
Mi    (Snake)
Tori  (Bird)
Kai   (Release — common non-zodiac seal, included as it's iconic and
       single-frame-static like the others)
```

## 5.2 Collision-avoidance

Same process as §4.2, extended to also check against the existing two-hand
gestures (`both_shaka`, `both_fists`, two-hand pinch-zoom, the anchor+finger-
count meta-menu) — this is the largest collision surface in this proposal,
since five NEW two-hand poses join four EXISTING ones.

## 5.3 Assignability, dispatch, safety, icons

Same requirements as §4.3-4.5.

---

# PHASE 6 — Jujutsu Kaisen gestures

## 6.1 Gojo

A two-hand, static "frame" gesture (both hands' thumb+index fingers forming
roughly perpendicular shapes brought together in front of the upper body/
face) SHALL be recognized as `JJK_GOJO`. See `design.md` §6.1 for a starting
geometric definition.

## 6.2 Sukuna (temporal)

A one-hand finger-snap (thumb and middle finger brought together then
rapidly separated within a short time window) SHALL be recognized as
`JJK_SUKUNA`. This requires new temporal/motion-impulse detection — see
`design.md` §6.2 for the required detector design (a reusable component,
not a one-off).

## 6.3 Megumi

ONE representative one-hand, static pose (not all 10 shikigami-specific
seals — `proposal.md` §5 non-goals) SHALL be recognized as `JJK_MEGUMI`. See
`design.md` §6.3.

## 6.4 Collision-avoidance, assignability, dispatch, safety, icons

Same requirements as §4.2-4.5, extended to also check against phases 4-5's
new seals.

---

# PHASE 7 — Common gestures

## 7.1 Clap

A two-hand, temporal gesture (both hands' centers rapidly closing distance
to near-contact, then separating, within a short time window) SHALL be
recognized as `CLAP`. SHALL reuse the temporal-impulse detector built for
Phase 6's Sukuna snap (`design.md` §6.2) rather than a second, parallel
implementation.

## 7.2 Korean finger heart

A one-hand, static pose (thumb and index finger crossed near their tips)
SHALL be recognized as `KOREAN_HEART`. Given its geometric closeness to the
existing `PINCH_DOWN`/click gesture (`design.md` §7.2 flags this as the
highest collision risk in this proposal), it SHALL require a brief hold
duration to confirm (same pattern as `LOCK_SESSION`'s Shaka-hold), NOT
fire on the same single-frame edge-trigger `PINCH_DOWN` uses. It SHALL NOT
be reachable through a bare touch-and-release of thumb+index — that
remains `PINCH_DOWN`'s exclusive behavior.

## 7.3 Collision-avoidance, assignability, dispatch, safety, icons

Same requirements as §4.2-4.5, extended to also check against phases 4-6's
new gestures. §7.2's hold-confirmation requirement is itself part of this
collision-avoidance outcome, not a separate mechanism.

---

# PHASE 8 — Settings screen

(Unchanged from the original version of this proposal, except its bindings
table (§8.2) now lists every trigger added by phases 4-7 too, not just the
original 5-seal set.)

## 8.1 Entry point

A small always-on-top gear icon (native Tkinter window, NOT click-through)
SHALL open the settings screen on click.

## 8.2 Bindings table

The settings screen SHALL list every bindable trigger known to the app:
existing camera gestures, every Phase 4-7 gesture, and registered voice
phrases — icon, name, current bound action, tooltip, per row.

## 8.3 Rebinding

Any row SHALL be reassignable to any value in the fixed action vocabulary,
a custom keyboard shortcut, or a previously-defined macro. Persists (§8.6)
and takes effect immediately.

## 8.4 Custom shortcuts and macros

### 8.4.1 Custom shortcut

Captured via focused-widget key events (not a global hook), stored as a
normalized `+`-joined string, executed via a new `HotkeyCommand` wrapping
`pyautogui.hotkey(*parts)`.

### 8.4.2 Macro

An ordered list of `press-key`/`type-text`/`wait-ms` steps, exposed as a
named `MACRO:<name>` action, executed via a new `MacroCommand` running its
steps through the same `CommandBus`. A macro's safety level SHALL be at
least as strict as its strictest step.

### 8.4.3 Physical macro keys (M1/M2/M3…)

The app SHALL NOT claim native recognition of a vendor macro key as a
distinct signal. The UI SHALL state this limitation and the workaround
(remap the key in the keyboard's own vendor software to an unused standard
combination, then bind that combination here).

## 8.5 Tooltips

Every interactive element SHALL have a hover tooltip explaining what it
does in plain language.

## 8.6 Persistence

Bindings (including custom shortcuts and macros) SHALL persist to a
per-user JSON file outside the repo/install directory. Load automatically on
next start; fail gracefully (defaults) on a missing/corrupt file; never
silently clobber a corrupt file (preserve it aside).

## 8.7 Non-blocking

Opening/using the settings screen SHALL NOT stall the camera loop.

---

# PHASE 9 — Voice model download icon

(Unchanged from the original version of this proposal.)

## 9.1 Location

Inside the settings screen (Phase 8), as a row/button.

## 9.2 Disclosure

Tooltip states approximate size (~1GB), purpose (local offline voice-command
understanding), and that `requirements-voice.txt` must be installed
separately — before any download starts.

## 9.3 Behavior

Checks dependency availability (`importlib.util.find_spec`, no real import)
first; if present, downloads the model on a background thread with progress
reported back to the UI; if the model already exists, reports ready without
re-downloading.
