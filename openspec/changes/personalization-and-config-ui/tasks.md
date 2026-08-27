# JARVIS Gesture HUD — Personalization & Config UI — Implementation Tasks

## Global execution rule

Tasks MUST be executed sequentially unless a task explicitly allows
parallelism. The agent MUST NOT implement future tasks automatically.
Implement only the requested task and its explicitly required dependencies.
After each task: run relevant tests, run the full regression suite, verify
acceptance criteria, report changed files, do NOT start the next task
automatically. Full protocol: `multimodal-interaction-core/apply.md`
(reused verbatim, not duplicated here).

Task numbering continues from the prior change's last task, TASK-054. This
file replaces the previous TASK-055–069 draft of this same change (nothing
in that draft was implemented) with the expanded scope from the revised
`proposal.md`/`spec.md`/`design.md`.

---

# PHASE 1 — Reliability fixes (do this first)

## TASK-055 — Pinch-priority resolution

### Objective

Fix the multi-pinch-firing bug per `design.md` §1.1: only the smallest-
distance pinch condition fires per frame.

### Requirements

Per `spec.md` #1.1. Localized to `gestures.py`'s `process()`.

### Must NOT

- Change any existing single-pinch-condition behavior.
- Change any threshold constant in `config.py`.

### Acceptance criteria

- Test: fist-with-thumb+index-pinch fixture (curled middle/ring/pinky
  landing geometrically close to the thumb) fires ONLY `PINCH_DOWN`, not
  `RIGHT_CLICK`/`SCREENSHOT`/zoom/volume.
- Test: every existing single-condition fixture in the current gesture
  regression suite still fires exactly as before (regression).
- Test: a genuinely ambiguous synthetic fixture (two conditions equally
  close) fires exactly one event, deterministically (document the
  tie-break rule chosen).

---

## TASK-055b — (Optional) Extend two-hand suppression to the remaining single-hand checks

### Objective

`design.md` §1.4 found that only `LOCK_SESSION` and `PINCH_DOWN`/`PINCH_UP`
are suppressed today when a two-hand gesture is also satisfied — the other 7
single-hand checks (SILENCE, KEYBOARD_TOGGLE, SCREENSHOT, single-hand
ZOOM_IN/OUT, VOLUME_UP/DOWN, SCROLL_UP/DOWN, RIGHT_CLICK) are not, a
pre-existing gap. This task extends the same suppression pattern to all of
them.

### Requirements

This task is OPTIONAL — it is not what the user reported as broken (TASK-055
and TASK-056 are the reported bugs). Explicitly decide and report whether to
do it now or defer it; do not silently skip without saying so. Doing it now
reduces the collision-avoidance burden on phases 5-7 (fewer existing
conditions a new two-hand gesture's individual hands can accidentally
satisfy); deferring it means phases 5-7 must still individually verify their
new two-hand gestures' hands don't trip these 7 checks (`spec.md` #5.2), so
the work isn't avoided, only postponed to be redone per-gesture instead of
once centrally.

### Must NOT

- Change single-hand-only behavior (no two-hand gesture active).

### Acceptance criteria

- Test: each of the 7 checks, when a two-hand gesture is concurrently
  satisfied on both hands, does not fire (extends the existing
  `LOCK_SESSION`/`PINCH_DOWN` pattern's own tests).
- Full regression suite green.

---

## TASK-056 — Background / other-person hand filtering

### Objective

Filter implausible hands (too small / not same-person-plausible) before
gesture logic, per `design.md` §1.2.

### Requirements

Per `spec.md` #1.2. New `config.py` constants
(`MIN_HAND_AREA_FRACTION`, `TWO_HAND_MAX_CENTER_DISTANCE_FRACTION`), chosen
and verified against a real camera, documented in the task report.

### Must NOT

- Reject the user's own two hands at normal desk-webcam distance (verify
  this manually, per the requirement above — this is the actual risk of
  this task, more than the filtering logic itself).
- Claim to eliminate all false positives (`spec.md` #1.2's honesty
  requirement) — document the limitation in `ARCHITECTURE.md`.

### Acceptance criteria

- Test: a synthetic small/background hand is filtered out (single-hand
  case).
- Test: two hands of implausible size difference or distance don't trigger
  two-hand gestures.
- Test: two normal, similarly-sized, reasonably-close hands still trigger
  two-hand gestures exactly as before (regression).
- Manual verification note in the report: real camera, user's two hands,
  both fixes together, no regression in normal use.

---

# PHASE 2 — Landmark / quadrant visualization

## TASK-057 — Hand visualizer overlay

### Objective

`src/jarvis/hand_visualizer.py` (`design.md` §2.1): skeleton + bounding
quadrant + primary/other-hand distinction + active-gesture label, toggle,
wired into `main.py`'s `run()` loop.

### Requirements

Per `spec.md` #2. Toggle documented (reused debug-HUD key or new one —
implementer's choice, must be documented either way).

### Must NOT

- Change any gesture-detection behavior when the overlay is on.
- Regress frame rate beyond what additional drawing calls already cost
  elsewhere in this project (measure, per `apply.md` §11).

### Acceptance criteria

- Unit tests (no display needed): `HAND_CONNECTIONS`-based line-segment
  generation is correct for a synthetic 21-point set; bounding-quadrant
  computation matches the synthetic set's min/max.
- Manual smoke test: overlay toggles on/off, shows skeleton + quadrant +
  primary/other distinction + gesture label on a real camera feed.
- Full regression suite still green with the toggle both on and off.

---

# PHASE 3 — Reference icon infrastructure

## TASK-058 — Icon generation module

### Objective

`src/jarvis/gesture_icons.py`: `ICON_SPECS`, `ensure_icon()`,
`generate_all_icons()` — per `design.md` §3, `spec.md` #3.1–3.2. Pillow
added to `requirements.txt`.

### Must NOT

- Add `PIL.ImageTk` as a dependency.
- Commit hand-authored binary image assets.

### Acceptance criteria

- Tests: `ensure_icon()` produces a valid ≤48×48 PNG; a second call doesn't
  regenerate; every spec'd icon is structurally distinguishable from every
  other.

---

## TASK-059 — Legend entries gain icon keys

### Objective

Extend `jarvis.legend.ENTRIES` with an icon key per entry; add
`build_legend_entries()`. Keep `build_legend_text()` unchanged.

### Acceptance criteria

- Test: every `ENTRIES` icon key resolves via `ensure_icon()`.
- Test: `build_legend_text()` output byte-identical to before this task.

---

## TASK-060 — Legend panel renders icon + text rows

### Objective

`overlay.ScreenOverlay.init_legend(entries, corner)` renders icon+text rows
per `design.md` §3 (same as the original proposal's version of this task).
`main.py` calls `build_legend_entries()`.

### Must NOT

- Start a second `Tk()` root.
- Change legend toggle/opacity keyboard bindings.

### Acceptance criteria

- Manual smoke test: icons visible, toggle/opacity/click-through unchanged.

---

# PHASE 4 — One-hand Naruto seals

## TASK-061 — One-hand roster collision census

### Objective

Execute `design.md` §4.2's process for the 8-seal roster in §4.1, resolving
the `Saru`/Shaka-collision flag explicitly.

### Must produce

Written roster note in the task report (final geometric definition per
seal, confirmation of no collision or what changed to resolve one).

### Must NOT

- Modify any existing gesture's detection logic.
- Write detector code in this task (analysis only, feeds TASK-062).

### Acceptance criteria

- Roster note exists and explicitly addresses the `Saru` flag.

---

## TASK-062 — One-hand seal detectors

### Objective

Implement `is_naruto_<name>()` for TASK-061's finalized roster, wired into
`GestureEngine.process()`, emitting `NARUTO_<NAME>` events.

### Acceptance criteria

- One positive synthetic test per seal.
- One negative test per seal against every existing gesture fixture
  (including Phase 1's fixes) and vice versa.
- Full regression suite green.

---

## TASK-063 — One-hand seal dispatch and icons

### Objective

Wire `NARUTO_<NAME>` events to actions via `Profile.gesture_bindings` +
`_dispatch_voice_action` reuse (`design.md` §4.3). Icon per seal (TASK-058's
infra).

### Acceptance criteria

- Test: default binding dispatches the right `Command`.
- Test: profile override changes the dispatched action.
- Test: unbound seal is a safe no-op.
- Test: a seal bound to a `HOLD_REQUIRED` command doesn't bypass its gating.
- Live-integration check extended with one seal end-to-end.

---

# PHASE 5 — Two-hand Naruto seals

## TASK-064 — Two-hand roster collision census

### Objective

Execute `design.md` §5.2's process for the 5-seal roster in §5.1, against
the FULL existing surface: the 4 existing two-hand gestures, the 9 existing
single-hand checks (each seal's two hands checked individually — `spec.md`
#5.2, `design.md` §1.4), AND phase 4's new one-hand seals. If TASK-055b was
done, the single-hand side of this census is already suppressed while a
two-hand gesture is active and only needs confirming, not re-fixing; if
TASK-055b was deferred, this task must still verify each new seal's
individual hands against all 9 single-hand checks directly.

### Must produce

Written roster note, same format as TASK-061, explicitly listing which of
the 4 two-hand AND 9 single-hand existing conditions each new seal was
checked against (13 total per seal, not 4), AND which `design.md` §1.5
taxonomy pattern (A/B/C/D) each seal uses — expected Pattern B for all 5,
per `spec.md` #5.2; if any seal doesn't cleanly fit, redesign or drop it
rather than shipping an ambiguous case.

### Acceptance criteria

Same as TASK-061, scaled to the larger collision surface (`design.md` §5.1
flags this as the hardest census in the proposal — budget accordingly, may
legitimately take longer/more iteration than other census tasks).

---

## TASK-065 — Two-hand seal detectors

### Objective

Implement the finalized two-hand seal checks inside
`_process_two_hand_gestures`, following the existing `both_shaka`/
`both_fists` hold-then-confirm timing pattern.

### Acceptance criteria

- Same test structure as TASK-062, extended to two-hand synthetic fixtures.
- Explicit test: each new seal does NOT also satisfy `both_shaka`,
  `both_fists`, `both_pinching`, or the meta-menu's `fists[0] != fists[1]`
  condition, and vice versa.

---

## TASK-066 — Two-hand seal dispatch and icons

Same structure as TASK-063, for the phase 5 roster.

---

# PHASE 6 — Jujutsu Kaisen gestures

## TASK-067 — Temporal impulse detector primitive

### Objective

`src/jarvis/temporal_gesture.py`: `ImpulseDetector` per `design.md` §6.2 —
the first temporal/motion-pattern primitive in this codebase (existing
gestures are single-frame-state or simple hold-timers, not
drop-then-rise-within-a-window patterns).

### Requirements

`update(distance, now) -> bool`, fires exactly once per completed impulse,
configurable contact/release thresholds and max window.

### Acceptance criteria

- Test: a synthetic distance sequence that drops below contact and rises
  above release within the window fires exactly once.
- Test: a sequence that drops but never rises within the window does not
  fire.
- Test: a sequence that stays below contact for a long time (a sustained
  pinch, not a snap) does not fire — this is the discrimination this
  primitive exists for (`design.md` §6.2).
- Test: two consecutive genuine impulses each fire once, independently.

---

## TASK-068 — Gojo and Megumi static detectors

### Objective

Implement `JJK_GOJO_DOMAIN` (two-hand static, Domain Expansion/Ryoiki Tenkai —
`design.md` §6.1, taxonomy Pattern B) and `JJK_MEGUMI`
(one-hand static, §6.3), including the collision census against phases 1,
4, 5, and each other (Megumi vs. Hitsuji explicitly, per §6.3). Report
`JJK_GOJO_DOMAIN`'s taxonomy pattern per `design.md` §1.5 — confirm it stays
Pattern B (its condition must be the relative angle/position BETWEEN the two
hands, never two independently-classified single-hand shapes) rather than
drifting into the forbidden independent-dual-action pattern during
implementation.

### Acceptance criteria

Same test structure as TASK-061/064, applied to these two gestures.

---

## TASK-069 — Sukuna snap detector

### Objective

`JJK_SUKUNA` using TASK-067's `ImpulseDetector` on `d_thumb_middle`
(`design.md` §6.2), including the temporal-discrimination test against
`RIGHT_CLICK`'s sustained pinch.

### Acceptance criteria

- Test: a snap-shaped landmark sequence fires `JJK_SUKUNA`, not
  `RIGHT_CLICK`.
- Test: a sustained right-click-pinch sequence fires `RIGHT_CLICK`, not
  `JJK_SUKUNA`.

---

## TASK-070 — JJK dispatch and icons

Same structure as TASK-063/066, for Gojo/Sukuna/Megumi. Note in the report
that Sukuna's icon should visually communicate "snap"/motion (e.g. a small
motion-line glyph), not just a static hand shape, since it's temporal.

---

# PHASE 7 — Common gestures

## TASK-071 — Clap detector

### Objective

`CLAP` via a second `ImpulseDetector` instance (TASK-067) tracking two-hand
palm-center distance, per `design.md` §7.1. Taxonomy Pattern D (`design.md`
§1.5) — one joint metric, one outcome, never two independently-classified
hands.

### Must NOT

- Reimplement impulse detection — reuse `ImpulseDetector`.
- Classify each hand's shape independently and combine two separate
  classifications into `CLAP` — the metric is inter-hand distance only.

### Acceptance criteria

- Test: a hands-closing-then-separating sequence fires `CLAP` once.
- Test: hands merely passing near each other without reaching the contact
  threshold does not fire `CLAP`.
- Collision check against phases 1/4/5/6's two-hand gestures.

---

## TASK-072 — Korean finger heart detector

### Objective

`KOREAN_HEART`, one-hand static + hold-confirmation, per `design.md` §7.2 —
the highest collision-risk gesture in this proposal (explicit geometric
closeness to `PINCH_CLICK`).

### Requirements

Hold duration required (new `config.py` constant), NOT edge-triggered like
`PINCH_DOWN`.

### Must NOT

- Make a bare touch-and-release of thumb+index ever resolve to
  `KOREAN_HEART` instead of `PINCH_DOWN`/`PINCH_UP` — this MUST remain
  impossible by construction (tested), not just unlikely.

### Acceptance criteria

- Test: a fast touch-and-release fires `PINCH_DOWN`/`PINCH_UP` only.
- Test: a sustained pose past the hold duration fires `KOREAN_HEART`, and
  does NOT also fire `PINCH_DOWN` (confirm via TASK-055's priority
  resolution, extended to include this gesture in the pinch-family
  ambiguity set if its geometry participates in it).

---

## TASK-073 — Common-gesture dispatch and icons

Same structure as TASK-063/066/070, for Clap and Korean finger heart.

---

# PHASE 8 — Settings screen

## TASK-074 — Persistence layer

`src/jarvis/core/config_store.py`, per `design.md` §9 (full detail already
specified in the original proposal — `spec.md` #8.6). Same acceptance
criteria as before: round-trip test, missing-file-safe, corrupt-file-
preserved-not-clobbered.

## TASK-075 — ProfileManager (de)serialization

`to_dict()`/`from_dict()`, per `spec.md` #8.6. Round-trip test, no second
in-memory representation.

## TASK-076 — HotkeyCommand and MacroCommand

`src/jarvis/actions/macro.py`, per `spec.md` #8.4. `MacroCommand` safety =
strictest step. No new dependency (`pyautogui.hotkey()` already covers
execution).

## TASK-077 — Tooltip helper

`Tooltip` class, manual verification only (documented as such in the
report, not silently skipped).

## TASK-078 — Gear icon window

Always-on-top, clickable (not click-through), opens the settings screen.

## TASK-079 — Settings screen: bindings table

Lists every trigger from `jarvis.legend.ENTRIES` + phases 4-7's rosters +
registered voice phrases — sourced from those existing structures, not a
hand-maintained duplicate.

## TASK-080 — Settings screen: rebind, shortcut capture, macro builder

Per `spec.md` #8.3-8.4, including the M1/M2/M3 help text (§8.4.3). No
global-hotkey dependency.

## TASK-081 — Wire persistence into the live app

Startup loads and applies bindings before the camera loop starts; save on
change; gesture/seal/voice dispatch all resolve through possibly-overridden
bindings. Extend `manual_live_integration_check.py`. Full regression suite
green. Real app boot verified.

(TASK-074–081 acceptance criteria are otherwise unchanged from the original
version of this proposal — see git history of this file if the earlier
draft's exact wording is needed; not reproduced a second time here to keep
this revision focused on what actually changed.)

---

# PHASE 9 — Voice model download icon

## TASK-082 — Voice model download row

Per `spec.md` #9, `design.md` §10 — unchanged from the original proposal.
Dependency check via `find_spec` (no real import), background-thread
download, progress reporting, idempotent on already-downloaded model. Tests:
deps-missing path, deps-present path (mocked network), already-downloaded
path.
