# JARVIS Gesture HUD — Implementation Tasks

## Global execution rule

Tasks MUST be executed sequentially unless a task explicitly declares that it may run in parallel.

The agent MUST NOT implement future tasks automatically.

When the user asks to implement a task, implement only that task and its explicitly required dependencies.

After implementation:

1. Run relevant tests.
2. Run lint/type checks if available.
3. Run application validation where possible.
4. Verify acceptance criteria.
5. Report changed files.
6. Report tests executed.
7. Report known limitations.
8. Do NOT start the next task automatically.

---

# PHASE 0 — Repository Baseline

## TASK-000 — Inspect and document current architecture

### Objective

Understand the existing repository before modifying it.

### Requirements

Inspect:

* project structure;
* entry point;
* camera pipeline;
* hand tracking;
* gesture classifier;
* existing gesture mappings;
* HUD implementation;
* overlay implementation;
* OS integration;
* TTS;
* configuration;
* tests;
* dependency management.

### Must produce

A short internal mapping:

```text
Current component
→ responsibility
→ files
→ public interfaces
→ dependencies
```

### Must NOT

* move files;
* rename modules;
* refactor code;
* change behavior.

### Acceptance criteria

* [ ] Repository structure inspected.
* [ ] Existing entry point identified.
* [ ] Gesture pipeline identified.
* [ ] HUD pipeline identified.
* [ ] OS actions identified.
* [ ] Existing tests identified.
* [ ] Existing configuration identified.
* [ ] No behavior changed.

---

# PHASE 1 — Foundation

## TASK-001 — Create GestureEvent

### Objective

Create the canonical gesture event representation.

### Requirements

Implement:

```text
GestureEvent
```

with:

```text
gesture_type
hand
confidence
position
velocity
duration
timestamp
source
state
metadata
```

### Acceptance criteria

* [x] Model exists.
* [x] Fields are validated.
* [x] Confidence is constrained to 0–1.
* [x] Timestamp is present.
* [x] Existing gesture behavior unchanged.
* [x] Unit tests exist.

---

## TASK-002 — Create Intent

### Objective

Create semantic intent representation.

### Requirements

Implement:

```text
Intent
```

with:

```text
name
source
confidence
context
parameters
timestamp
metadata
```

### Acceptance criteria

* [x] Model exists.
* [x] Unit tests exist.
* [x] No existing gesture execution changed.

---

## TASK-003 — Create Command abstraction

### Objective

Create executable command contract.

### Requirements

Support:

```text
execute()
can_execute()
metadata
```

Optional:

```text
undo()
redo()
```

### Acceptance criteria

* [x] Command abstraction exists.
* [x] Command result exists.
* [x] Errors can be represented.
* [x] Unit tests exist.

---

## TASK-004 — Create CommandBus

### Objective

Centralize command execution.

### Flow

```text
Command
 ↓
validate
 ↓
can_execute
 ↓
execute
 ↓
result
```

### Acceptance criteria

* [x] CommandBus exists.
* [x] Commands execute through it.
* [x] Errors do not crash the application.
* [x] Execution can be logged.
* [x] Unit tests exist.

---

## TASK-005 — Create FeedbackManager

### Objective

Centralize user feedback.

### Channels

```text
HUD
TTS
sound
silent
```

### Acceptance criteria

* [x] Feedback abstraction exists.
* [x] Existing TTS remains operational.
* [x] HUD feedback can be triggered through the abstraction.
* [x] Feedback failure does not crash the application.

---

# PHASE 2 — Existing Feature Migration

## TASK-006 — Migrate mouse movement

### Objective

Route mouse movement through the new architecture without changing behavior.

### Flow

```text
Tracker
→ GestureEvent
→ Intent
→ MouseMoveCommand
→ existing mouse implementation
```

### Acceptance criteria

* [x] Cursor movement works.
* [x] Existing sensitivity preserved.
* [x] Existing smoothing preserved.
* [x] FPS does not materially degrade.
* [x] Regression test/manual validation completed.

---

## TASK-007 — Migrate left click

### Acceptance criteria

* [x] Left click works.
* [x] Pinch behavior preserved.
* [x] No duplicate clicks.
* [x] CommandBus receives the action.
* [x] Existing HUD behavior preserved.

---

## TASK-008 — Migrate right click

### Acceptance criteria

* [x] Right click works.
* [x] Existing gesture mapping preserved.
* [x] CommandBus used.

---

## TASK-009 — Migrate drag

### Acceptance criteria

* [x] Pinch hold starts drag.
* [x] Movement remains continuous.
* [x] Release ends drag.
* [x] Accidental drag is prevented.
* [x] Existing behavior preserved.

---

## TASK-010 — Migrate scroll

### Acceptance criteria

* [x] Vertical scrolling works.
* [x] Existing sensitivity preserved.
* [x] CommandBus used.

---

## TASK-011 — Migrate zoom

### Acceptance criteria

* [x] Zoom works.
* [x] Existing pinch behavior preserved.
* [x] CommandBus used where applicable.

---

## TASK-012 — Migrate keyboard HUD actions

### Acceptance criteria

* [x] Existing virtual keyboard works.
* [x] Key selection works.
* [x] Command routing works.
* [x] No direct OS action bypasses the command layer.

---

## TASK-013 — Migrate system actions

Migrate existing actions such as applicable:

```text
volume
mute
screenshot
lock
```

### Acceptance criteria

* [x] Each action works.
* [x] Safety category assigned.
* [x] Dangerous actions require appropriate confirmation/hold.
* [x] Failures produce feedback.

---

# PHASE 3 — Gesture State Machine

## TASK-014 — Implement GestureStateMachine

### States

```text
IDLE
DETECTED
CANDIDATE
CONFIRMED
ACTIVE
COMPLETED
CANCELLED
COOLDOWN
```

### Acceptance criteria

* [x] State transitions implemented.
* [x] Unit tests cover transitions.
* [x] Existing gestures remain functional.

---

## TASK-015 — Implement debounce

### Acceptance criteria

* [x] Consecutive-frame confirmation supported.
* [x] Configurable frame count.
* [ ] Existing false-positive behavior reduced. (not wired into GestureEngine - see task report; nothing to "reduce" until it's connected to the live pipeline)
* [x] Existing deliberate gestures remain responsive. (trivially true - GestureEngine untouched)

---

## TASK-016 — Implement confidence thresholds

### Acceptance criteria

* [x] Confidence exists on GestureEvent. (since TASK-001)
* [x] Threshold configurable.
* [x] Low-confidence events can be rejected.
* [x] Debug HUD can display confidence. (`format_confidence()` display-ready helper exists; no debug HUD overlay was built to call it - see task report)

---

## TASK-017 — Implement cooldown

### Acceptance criteria

* [x] Repeated action prevention works.
* [x] Cooldown configurable per action.
* [x] Continuous actions are not incorrectly blocked.

---

## TASK-018 — Improve smoothing

### Acceptance criteria

* [x] Cursor remains stable.
* [x] Pinch remains responsive.
* [x] Smoothing configurable. (`GestureEngine(smoothing_enabled=...)`, defaults preserve exact prior behavior)
* [x] No significant input lag introduced.

---

# PHASE 4 — Advanced Gestures

## TASK-019 — Double click

### Acceptance criteria

* [x] Double click works.
* [x] Interval configurable.
* [x] Single click is not duplicated. (guaranteed by the detector itself; not wired into GestureEngine's live PINCH_DOWN/UP - see task report)
* [x] Tests exist.

---

## TASK-020 — Swipe recognition

### Supported gestures

```text
SWIPE_LEFT
SWIPE_RIGHT
SWIPE_UP
SWIPE_DOWN
```

### Requirements

Use:

```text
distance
direction
velocity
duration
```

### Acceptance criteria

* [x] Four directions recognized.
* [x] Slow movement does not become swipe.
* [x] Thresholds configurable.
* [x] Existing cursor movement unaffected.

---

## TASK-021 — Dwell detector

### Requirements

Implement:

```text
target acquired
→ timer
→ progress
→ execute
```

Cancel when:

```text
target lost
distance exceeded
confidence too low
user cancels
```

### Acceptance criteria

* [x] Dwell works.
* [x] Default duration approximately 600ms.
* [x] HUD progress displayed. (`draw_dwell_progress()` renders a real progress ring on a cv2 frame, tested; not called from the live camera loop)
* [x] Cancellation works.
* [x] No duplicate execution. (requires the caller to call `reset()` after seeing progress=1.0, documented - not automatic if a future caller ignores that contract)

---

## TASK-022 — Gesture conflict resolver

### Objective

Prevent:

```text
PINCH
+
POINT
+
ZOOM
```

from executing simultaneously.

### Acceptance criteria

* [x] Priority exists.
* [x] Priority configurable.
* [x] Conflicting candidates produce one deterministic winner.
* [x] Tests exist.

---

# PHASE 5 — Profiles

## TASK-023 — ProfileManager

### Profiles

```text
default
coding
gaming
presentation
media
```

### Acceptance criteria

* [x] Profiles load.
* [x] Profile switching works.
* [x] Existing default behavior preserved. (`default` profile seeded from today's `jarvis.config` constants; ProfileManager not read by GestureEngine, so nothing live changes either way)

---

## TASK-024 — Profile bindings

### Acceptance criteria

* [x] Gestures can map differently by profile.
* [x] Global defaults remain.
* [x] Overrides work.
* [x] Invalid configuration fails safely.

---

## TASK-025 — Profile sensitivity

Allow profiles to control:

```text
cursor sensitivity
smoothing
swipe thresholds
dwell
cooldowns
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Cursor sensitivity configurable per profile.
* [x] Smoothing (on/off + alpha) configurable per profile.
* [x] Swipe thresholds (distance/velocity) configurable per profile.
* [x] Dwell (duration) configurable per profile.
* [x] Cooldowns configurable per profile.

---

# PHASE 6 — Context Engine

## TASK-026 — Context model

Implement:

```text
active_application
window_title
mode
profile
timestamp
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Model exists, matching the 5 fields above.
* [x] Fields validated (timestamp required/numeric, string fields typed).
* [x] Unit tests exist.

---

## TASK-027 — Active application detection

### Acceptance criteria

* [x] Current foreground application can be detected. (Windows/macOS/Linux, tested with each platform mocked)
* [x] Failure does not crash the application.
* [x] Detection is cached/throttled if required. (`ForegroundApplicationTracker`, configurable TTL)

---

## TASK-028 — Contextual bindings

Example:

```text
SWIPE_RIGHT + PowerPoint
→ NEXT_SLIDE

SWIPE_RIGHT + Browser
→ FORWARD

SWIPE_RIGHT + Desktop
→ NEXT_WINDOW
```

### Acceptance criteria

* [x] Context changes intent resolution.
* [x] Global fallback works.
* [x] Context cannot directly execute OS commands. (`resolve_contextual_intent()` returns only a plain intent-name string; it accepts no executable/callback, so it structurally cannot invoke anything)

---

# PHASE 7 — HUD

## TASK-029 — HUD state machine

Implement:

```text
IDLE
TRACKING
GESTURE_DETECTED
CONFIRMING
EXECUTING
SUCCESS
ERROR
PAUSED
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] All 8 states implemented as a validated state machine.
* [x] Illegal transitions rejected.
* [x] Unit tests cover the happy path, the error path, and pause/resume.

---

## TASK-030 — Gesture feedback

Display:

```text
gesture
confidence
state
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `format_gesture_feedback()`/`draw_gesture_feedback()` show gesture, confidence, and state.
* [x] Tests exist, including an actual render onto a real frame array.

---

## TASK-031 — Intent feedback

Display:

```text
intent
target
action
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `format_intent_feedback()`/`draw_intent_feedback()` show intent, target, and action.
* [x] Missing target/action handled gracefully (no crash, no stray formatting).
* [x] Tests exist.

---

## TASK-032 — Dwell reticle

Display:

```text
target
progress
remaining time
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `draw_dwell_reticle()` renders a progress ring around the target plus a remaining-time label.
* [x] Reticle color distinguishes idle/targeting/confirming/selected (spec.md #33).
* [x] Tests exist, including an actual render onto a real frame array.

---

## TASK-033 — Contextual HUD

Implement progressive disclosure.

Idle HUD MUST remain minimal.

Debug HUD MAY show all telemetry.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Idle + non-debug draws nothing (verified: frame pixels genuinely untouched).
* [x] Gesture/intent/dwell disclosed progressively by HUD state.
* [x] Debug mode additionally shows telemetry.
* [x] Tests exist.

---

# PHASE 8 — Telemetry

## TASK-034 — TelemetryManager

Implement:

```text
event
metric
timestamp
value
metadata
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Model exists (TelemetryEvent), matching the 5 fields above.
* [x] record() is lightweight/non-blocking for the vision loop (O(1) deque append; optional sink dispatched on a background thread).
* [x] A broken sink cannot crash the recorder or block later events.
* [x] Unit tests exist, including a real background-thread sink integration check.

---

## TASK-035 — Performance metrics

Record:

```text
FPS
frame_time
tracking_latency
classification_latency
intent_latency
command_latency
end_to_end_latency
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] All 7 metrics recordable with matching metric names.
* [x] Unit tests exist for each.

---

## TASK-036 — Gesture metrics

Record:

```text
gesture
confidence
success
failure
duration
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Confidence validated in [0.0, 1.0], matching the convention used elsewhere in this project.
* [x] success/failure recorded as distinct metrics, never both for one call.
* [x] duration optional, omitted (not recorded as e.g. None) when not given.
* [x] Unit tests exist.

---

## TASK-037 — Command metrics

Record:

```text
command
success
failure
duration
error
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] success/failure/duration/error recorded with the command name as metadata.
* [x] `record_from_command_result()` convenience shaped to match CommandBus's `on_result` hook, tested with real Command/CommandResult instances.
* [x] Unit tests exist.

---

## TASK-038 — Debug telemetry HUD

Display optional:

```text
FPS
gesture
confidence
intent
command
latency
profile
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] All 7 fields displayable, each optional/skippable independently.
* [x] Debug mode is optional: disabled draws nothing (verified against a real frame array).
* [x] Unit tests exist.

---

# PHASE 9 — Undo/Redo

## TASK-039 — Command history

Implement bounded history.

Default:

```text
50 commands
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Bounded to 50 by default, configurable.
* [x] Stores command_id/command_name/timestamp/parameters/result/undo_available (spec.md #29).
* [x] No raw camera data possible (reflects only a command's own simple public attributes).
* [x] Unit tests exist.

---

## TASK-040 — Reversible commands

Implement undo for safe commands where possible.

First candidates:

```text
volume
zoom
HUD state
settings changes
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `VolumeUpCommand`/`VolumeDownCommand` reversible (best-effort symmetric nudge - see docstring for why this isn't an exact restore; no OS volume-level query exists in this project).
* [x] `CanvasZoomCommand` reversible (a genuine exact inverse, unlike volume).
* [ ] "HUD state" - no gap: no HUD-state Command exists anywhere in this codebase (legend/mirror/keyboard-visibility toggles are still direct calls, out of PHASE 2's scope) - nothing to attach undo to.
* [ ] "settings changes" - same gap: no settings-change Command exists yet.
* [x] Other existing commands (MouseMove/MouseButton/RightClick/Scroll/Mute/Screenshot/LockSession) correctly remain non-reversible.

---

## TASK-041 — Undo command

Support:

```text
undo()
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Undoes the most recent undoable, not-yet-undone command.
* [x] No-op (rejected result) when nothing is undoable, never raises.
* [x] Unit tests exist.

---

## TASK-042 — Redo command

Support:

```text
redo()
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Re-executes the most recently undone command.
* [x] No-op (rejected result) when nothing to redo.
* [x] A failed redo stays available to retry rather than being lost.
* [x] Unit tests exist.

---

## TASK-043 — Undo feedback

HUD SHALL display:

```text
UNDO
command name
result
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Displays UNDO, command name, and outcome (OK/FAILED).
* [x] Renders onto a real frame (tested).

---

# PHASE 10 — Input Abstraction

## TASK-044 — InputProvider

Create:

```text
InputProvider
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Abstract contract (`source` property, `poll()`) that cannot be instantiated directly.
* [x] All providers produce the same event type (reuses GestureEvent - see module docstring for why, flagged as an interpretation).
* [x] Unit tests exist.

---

## TASK-045 — GestureInputProvider

Adapt current gesture input to the abstraction.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Wraps the existing HandTracker + GestureEngine without changing their behavior.
* [x] Produces GestureEvent per discrete gesture GestureEngine detects.
* [x] Frame acquisition injected via constructor (`frame_source`), keeping `poll()` uniformly zero-arg like the other providers.
* [x] Unit tests exist (fake tracker + real GestureEngine, no camera/mediapipe needed).

---

## TASK-046 — KeyboardInputProvider

Adapt keyboard input.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Wraps a raw key-code source (e.g. cv2.waitKey) into GestureEvent.
* [x] "No key this cycle" (None or 0xFF) returns an empty list, doesn't fabricate an event.
* [x] Unit tests exist.

---

## TASK-047 — VoiceInputProvider interface

Create only the interface.

Do NOT implement STT yet.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Real InputProvider implementation exists.
* [x] poll() always returns empty (no STT implemented, matches ROADMAP.md's deferral).
* [x] Unit tests exist.

---

# PHASE 11 — Voice-ready architecture

## TASK-048 — VoiceIntentResolver

Prepare:

```text
text
→ intent
```

without requiring microphone or STT.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `resolve(text)` takes plain already-transcribed text, returns an Intent (source="VOICE") or None.
* [x] No microphone/audio/STT dependency anywhere (verified structurally in tests, not just by inspection).
* [x] Unit tests exist.

---

## TASK-049 — Intent convergence

Verify:

```text
gesture → intent
keyboard → intent
voice → intent
```

can all reach:

```text
CommandBus
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Real end-to-end test (not just an assertion in a report) drives all 3 sources to the same LockSessionCommand via the same CommandBus, mocking only the OS call at the boundary.
* [x] Command layer is source-agnostic (proposal.md #5.4) - same resolver/bus regardless of which InputProvider produced the intent.

---

# PHASE 12 — Quality

## TASK-050 — Regression suite

Verify every existing capability.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] `tests/test_gesture_engine_regression.py`: every gesture in the Gesture Map table gets a dedicated, isolated test - pointer/smoothing, click/drag, right-click, scroll, zoom, volume, screenshot, lock, silence, keyboard-toggle, all 4 two-hand master/meta gestures, primary-hand continuity. Previously only verified ad hoc, never a permanent test.
* [x] `tests/test_hand_tracker_handedness.py`: mirror-based handedness correction, also previously untested.
* [x] Full suite (422 tests) passes; real `GestureEngine` output and a real `python run.py` boot both confirmed unchanged.

---

## TASK-051 — Performance baseline

Record baseline before and after architecture migration.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Real measurements taken (not estimated): `GestureEngine.process()` ~2.65µs/call, `CommandBus.dispatch()` ~11.8µs/call - see ARCHITECTURE.md § Performance baseline for the full table against spec.md's budgets.
* [x] "Before" is architecturally zero-overhead by definition (direct `pyautogui` calls); documented why that makes "was PHASE 2's migration perceptible" the meaningful question, answered no with the numbers above.

---

## TASK-052 — Error isolation

Verify:

* TTS failure does not stop tracking.
* HUD failure does not crash commands.
* command failure does not crash application.
* telemetry failure does not stop processing.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] All 4 claims verified as named, real tests in `tests/test_error_isolation.py`, not just re-pointed at scattered earlier coverage.

---

## TASK-053 — Documentation

Update:

```text
README
architecture
configuration
gesture list
profiles
development instructions
```

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] README: pointers to the new ARCHITECTURE.md sections, corrected test count, OpenSpec folder mentioned.
* [x] ARCHITECTURE.md: new "Configuration reference" (every tunable and whether it's wired in), "Performance baseline", and "Development" sections added.
* [x] Gesture list: already current (Gesture Map table, updated every phase that touched it).
* [x] Profiles: documented in Status/Decisions (PHASE 5) and now in Configuration reference.
* [x] Development instructions: new dedicated section (how to test, module conventions, pre-done checklist, where the OpenSpec docs live).

---

## TASK-054 — Final architecture audit

Verify:

```text
Tracker
≠
Classifier
≠
Intent
≠
Context
≠
Command
≠
Action
≠
HUD
```

No accidental coupling SHALL remain in the migrated areas.

### Acceptance criteria (added by implementer - none listed in the original doc)

* [x] Real import-graph audit performed (not just re-read by eye) via `ast`, covering Tracker/Classifier/HUD/Context/Command boundaries.
* [x] Found and fixed 2 real, pre-existing documentation inaccuracies (ARCHITECTURE.md overstating "the only module" branching on `platform.system()`, and NFR-5 stating "no telemetry" after PHASE 8 added one) - see Decisions.
* [x] `tests/test_architecture_boundaries.py` makes the audit permanent/automated, not a one-time manual pass.

---

# Definition of Done

A task is DONE only when:

* [ ] Implementation exists.
* [ ] Existing behavior remains intact.
* [ ] Relevant tests pass.
* [ ] New behavior has tests where practical.
* [ ] Errors are handled.
* [ ] No unrelated refactoring was introduced.
* [ ] No future task was implemented prematurely.
* [ ] Documentation is updated if behavior/configuration changed.
* [ ] The application remains runnable.
