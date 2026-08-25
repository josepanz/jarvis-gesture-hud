# JARVIS Gesture HUD — Technical Specification

## 1. Scope

This specification defines the technical behavior required to evolve the existing JARVIS Gesture HUD application.

The specification is implementation-oriented.

Every requirement SHALL be treated as normative unless explicitly marked as future.

---

# 2. Core data models

## 2.1 GestureEvent

A GestureEvent SHALL contain at least:

```text
id
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

Example:

```text
gesture_type = PINCH
hand = RIGHT
confidence = 0.94
position = (0.63, 0.41)
velocity = (0.02, -0.01)
duration_ms = 240
source = CAMERA
state = ACTIVE
```

---

## 2.2 Intent

An Intent SHALL contain:

```text
name
source
confidence
timestamp
context
parameters
```

Example:

```text
name = SELECT
source = GESTURE
confidence = 0.91
parameters:
    target = "hud_button"
```

---

## 2.3 Command

Every command SHALL expose:

```text
execute()
can_execute()
metadata
```

Reversible commands SHOULD additionally expose:

```text
undo()
redo()
```

Commands MUST NOT depend directly on camera landmarks.

---

# 3. Gesture states

The GestureStateMachine SHALL support:

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

## State transitions

```text
IDLE
 ↓
DETECTED
 ↓
CANDIDATE
 ↓
CONFIRMED
 ↓
ACTIVE
 ↓
COMPLETED
 ↓
COOLDOWN
 ↓
IDLE
```

Failure:

```text
CANDIDATE
 ↓
CANCELLED
 ↓
IDLE
```

---

# 4. Debounce

A gesture SHALL NOT normally execute from one frame.

Default behavior SHOULD require a configurable number of consecutive matching classifications.

Initial default:

```text
confirmation_frames = 3
```

This MUST be configurable.

---

# 5. Confidence

Every classified gesture SHALL have confidence in:

```text
0.0 <= confidence <= 1.0
```

The system SHALL allow:

```text
minimum_confidence
```

configuration.

Default:

```text
minimum_confidence = 0.70
```

Commands with safety level `DESTRUCTIVE` SHOULD require a higher threshold.

---

# 6. Cooldown

After an action is executed, the same gesture SHALL NOT immediately trigger the same action repeatedly.

Configuration:

```text
cooldown_ms
```

Initial defaults MAY be:

```text
click = 300ms
system_action = 800ms
gesture_navigation = 500ms
```

Values MUST remain configurable.

---

# 7. Smoothing

Continuous values SHALL support smoothing.

The system SHOULD use exponential moving average or equivalent.

Example:

```text
smoothed = alpha * current + (1 - alpha) * previous
```

Configuration:

```text
smoothing.enabled
smoothing.alpha
```

Smoothing SHALL apply to continuous values such as:

* cursor position;
* pinch distance;
* hand position;
* gesture motion.

Classification logic SHOULD remain independently testable.

---

# 8. Mouse control

Existing mouse movement MUST remain functional.

The cursor system SHOULD support:

* smoothing;
* sensitivity;
* acceleration;
* dead zone;
* screen mapping;
* calibration.

---

# 9. Cursor acceleration

Optional acceleration SHALL allow:

```text
slow hand movement
→ precise cursor movement

fast hand movement
→ faster cursor movement
```

Acceleration MUST be configurable and disabled if it causes instability.

---

# 10. Pinch

Pinch detection SHALL use normalized hand-relative distance rather than absolute pixels where possible.

Example:

```text
pinch_ratio =
distance(thumb_tip, index_tip)
/
distance(wrist, middle_mcp)
```

This makes behavior less dependent on hand distance from the camera.

The implementation MUST preserve the existing pinch behavior unless a regression is intentionally introduced and tested.

---

# 11. Click

Click SHALL support:

```text
LEFT_CLICK
RIGHT_CLICK
```

The system SHOULD distinguish:

```text
PINCH_START
PINCH_HOLD
PINCH_RELEASE
```

to prevent accidental repeated clicks.

---

# 12. Double click

Double click SHALL require:

```text
two valid click events
+
maximum_inter_click_interval
```

Configuration:

```text
double_click.enabled
double_click.max_interval_ms
```

Default SHOULD be approximately 400–500 ms.

---

# 13. Drag

Drag SHALL follow:

```text
PINCH_START
 ↓
HOLD
 ↓
MOVE
 ↓
PINCH_RELEASE
```

Drag MUST NOT start from a single noisy pinch frame.

A configurable hold threshold SHOULD exist.

---

# 14. Scroll

Scroll SHALL support:

* vertical;
* optional horizontal.

Scrolling MUST have:

```text
sensitivity
dead_zone
smoothing
cooldown
```

---

# 15. Zoom

Zoom SHALL support continuous input.

Pinch distance changes MAY map to:

```text
zoom_in
zoom_out
```

Zoom MUST use normalized distance.

---

# 16. Swipe

The Gesture Engine SHALL detect:

```text
SWIPE_LEFT
SWIPE_RIGHT
SWIPE_UP
SWIPE_DOWN
```

Swipe recognition SHALL use:

```text
start_position
end_position
delta
duration
velocity
```

Minimum displacement and velocity MUST be configurable.

A swipe MUST NOT be triggered by slow cursor movement.

---

# 17. Dwell

Dwell is a deliberate selection mechanism.

The user points at a target and remains within a configured region for a configured duration.

Configuration:

```text
dwell.enabled
dwell.duration_ms
dwell.max_target_distance
dwell.cancel_distance
```

Default:

```text
dwell.duration_ms = 600
```

During dwell the HUD SHALL display progress:

```text
0%
25%
50%
75%
100%
```

At 100% the configured action is executed.

Movement beyond `cancel_distance` cancels dwell.

---

# 18. Gesture priority

When multiple gestures are possible, the system SHALL use deterministic priority.

Example:

```text
TWO_FINGER_AIM
    >
PINCH
    >
OPEN_PALM
    >
FIST
```

The exact priority MUST be configurable.

The system MUST prevent mutually exclusive gestures from triggering simultaneously.

---

# 19. Gesture conflicts

Example:

```text
PINCH
```

must not simultaneously become:

```text
CLICK
+
ZOOM
+
DRAG
```

unless the state machine explicitly determines the intended transition.

---

# 20. Two-hand interaction

The system SHALL preserve existing two-hand functionality.

Two-hand events SHALL contain:

```text
left_hand
right_hand
relative_distance
relative_position
gesture_combination
```

Future examples:

```text
two_hand_open
two_hand_pinch
two_hand_hold
two_hand_pause
```

---

# 21. Profiles

Profiles SHALL define:

```text
name
gesture_bindings
sensitivity
cooldowns
dwell
HUD
context_rules
```

Suggested profiles:

```text
default
coding
gaming
presentation
media
```

---

# 22. Profile inheritance

Configuration precedence:

```text
command/profile override
    >
profile configuration
    >
global configuration
    >
hardcoded safe default
```

---

# 23. Context Engine

Context SHALL contain:

```text
active_application
window_title
mode
profile
HUD_state
timestamp
```

Future providers MAY include:

```text
foreground_process
window_class
document_type
media_state
presentation_state
```

---

# 24. Contextual binding

Example:

```text
SWIPE_LEFT
```

Desktop:

```text
previous_window
```

Browser:

```text
back
```

PowerPoint:

```text
previous_slide
```

Media:

```text
previous_track
```

The gesture itself SHALL remain unchanged.

Only intent resolution changes.

---

# 25. Command Bus

The CommandBus SHALL:

1. validate the command;
2. check safety;
3. execute;
4. report result;
5. generate telemetry;
6. update history when reversible;
7. generate feedback.

Flow:

```text
Intent
 ↓
CommandResolver
 ↓
CommandBus
 ↓
can_execute()
 ↓
execute()
 ↓
Result
 ↓
Feedback
```

---

# 26. Command result

Commands SHOULD return:

```text
success
status
message
duration
metadata
error
```

Example:

```text
success = true
status = EXECUTED
message = "Volume increased"
duration_ms = 12
```

---

# 27. Command safety

Commands SHALL declare a safety category:

```text
SAFE
CONFIRM_REQUIRED
HOLD_REQUIRED
DESTRUCTIVE
```

Examples:

```text
MouseMove = SAFE
VolumeUp = SAFE
Screenshot = SAFE
CloseApplication = CONFIRM_REQUIRED
LockWorkstation = HOLD_REQUIRED
DeleteFile = DESTRUCTIVE
```

The initial implementation MUST NOT introduce destructive commands merely for demonstration.

---

# 28. Undo/Redo

Only commands that can reliably restore previous state SHALL support undo.

Example:

```text
Volume:
80 → 90

undo:
90 → 80
```

Example:

```text
OpenApplication
```

MAY be considered non-reversible unless the command owns enough state to close only the process it opened.

The system MUST NOT pretend an action is reversible when it cannot safely restore the previous state.

---

# 29. History

History SHOULD store:

```text
command_id
command_name
timestamp
parameters
result
undo_available
```

Default history size:

```text
50
```

This MUST be configurable.

---

# 30. Feedback

Feedback SHALL support:

```text
HUD
TTS
sound
silent
```

The user MAY disable individual channels.

---

# 31. HUD states

The HUD SHALL support at least:

```text
IDLE
TRACKING
GESTURE_DETECTED
CONFIRMING
EXECUTING
SUCCESS
ERROR
PAUSED
LISTENING
```

`LISTENING` is future voice support.

---

# 32. Contextual HUD

The HUD SHALL use progressive disclosure.

Idle:

```text
minimal information
```

Gesture detected:

```text
gesture
confidence
```

Action pending:

```text
gesture
target
progress
```

Executing:

```text
action
```

Debug mode:

```text
FPS
latency
confidence
tracking
```

---

# 33. Reticle

The HUD SHOULD support a target reticle for:

* dwell;
* selection;
* contextual interaction.

The reticle SHALL visually distinguish:

```text
idle
targeting
confirming
selected
```

---

# 34. Telemetry

Telemetry SHALL capture:

```text
fps
frame_time
tracking_latency
classification_latency
intent_latency
command_latency
end_to_end_latency
gesture_confidence
gesture_success
gesture_failure
command_success
command_failure
```

Telemetry MUST be asynchronous or lightweight enough not to block the vision loop.

---

# 35. Telemetry privacy

Telemetry SHALL remain local by default.

No telemetry SHALL be uploaded externally unless a future feature explicitly enables it.

---

# 36. Debug mode

Debug mode SHOULD display:

```text
FPS
Hands
Gesture
Confidence
State
Intent
Context
Command
Latency
Profile
```

Debug mode MUST be optional.

---

# 37. Input Provider

The architecture SHALL introduce a conceptual interface:

```text
InputProvider
```

Implementations:

```text
GestureInputProvider
KeyboardInputProvider
VoiceInputProvider
FutureVisionInputProvider
```

All providers SHALL generate intents or events consumed by the same pipeline.

---

# 38. Voice preparation

The initial implementation SHALL NOT require STT.

It SHALL only create the abstraction necessary for future integration.

Future flow:

```text
Microphone
 ↓
VAD
 ↓
STT
 ↓
VoiceIntentResolver
 ↓
Intent
 ↓
CommandBus
```

---

# 39. Performance

The camera loop SHALL remain responsive.

No synchronous operation that can block for significant time SHALL execute directly inside the frame-processing loop.

Target behavior:

```text
tracking
→ event
→ queue
→ command execution
```

when an operation may block.

---

# 40. Error handling

Every command execution failure SHALL produce:

* structured error;
* telemetry;
* HUD feedback;
* optional TTS feedback.

The application MUST NOT crash because one command fails.

---

# 41. Configuration

Configuration SHALL be externalized progressively.

Suggested:

```text
config/
├── default.yaml
├── profiles/
│   ├── default.yaml
│   ├── coding.yaml
│   ├── gaming.yaml
│   ├── presentation.yaml
│   └── media.yaml
```

Existing configuration mechanisms SHALL be preserved during migration.

---

# 42. Testing

Tests SHALL cover:

* gesture classification;
* gesture state transitions;
* debounce;
* cooldown;
* confidence;
* dwell;
* swipe;
* intent resolution;
* context;
* profiles;
* command execution;
* command failures;
* undo;
* telemetry.

Integration tests SHALL verify existing functionality.

---

# 43. Regression requirement

Before completing each migration task, all relevant existing tests MUST pass.

If no test exists for an existing feature, a regression test SHOULD be created before modifying that feature.
