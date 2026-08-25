# JARVIS Gesture HUD — Architecture Design

## 1. Design objective

The design introduces an extensible architecture without destroying the current implementation.

The migration is evolutionary.

---

# 2. Current-to-target mapping

```text
CURRENT
=======

Camera
 ↓
Hand Tracking
 ↓
Gesture Logic
 ↓
OS / HUD Actions
```

becomes:

```text
TARGET
======

Camera
 ↓
HandTracker
 ↓
GestureClassifier
 ↓
GestureStateMachine
 ↓
IntentEngine
 ↓
ContextEngine
 ↓
CommandBus
 ↓
Action
 ↓
FeedbackManager
 ↓
HUD / TTS
```

---

# 3. Suggested project structure

The exact existing project structure MUST be inspected before moving files.

The following is the target conceptual structure:

```text
src/
├── core/
│   ├── events/
│   │   ├── gesture_event
│   │   └── input_event
│   │
│   ├── intents/
│   │   ├── intent
│   │   └── intent_engine
│   │
│   ├── commands/
│   │   ├── command
│   │   ├── command_bus
│   │   ├── command_result
│   │   └── history
│   │
│   ├── context/
│   │   ├── context
│   │   └── context_engine
│   │
│   ├── profiles/
│   │   └── profile_manager
│   │
│   └── telemetry/
│       └── telemetry_manager
│
├── vision/
│   ├── tracker
│   ├── classifier
│   └── gesture_state
│
├── actions/
│   ├── mouse
│   ├── system
│   ├── keyboard
│   └── media
│
├── hud/
│   ├── state
│   ├── feedback
│   └── overlay
│
└── input/
    ├── gesture
    ├── keyboard
    └── voice
```

This is a target architecture, NOT permission to blindly reorganize the repository.

The agent MUST inspect the current repository first.

---

# 4. Existing code migration rule

Before creating a new abstraction, identify the current implementation.

Example:

```text
Existing:
gestures.py
    ↓
pyautogui.click()
```

Target:

```text
gestures.py
    ↓
GestureEvent
    ↓
Intent
    ↓
LeftClickCommand
    ↓
existing click implementation
```

The first migration SHOULD be an adapter, not a rewrite.

---

# 5. Event architecture

Gesture processing produces events.

Example:

```text
GestureEvent(
    gesture=PINCH,
    hand=RIGHT,
    confidence=0.94,
    position=(x,y),
    timestamp=t
)
```

The event MUST be immutable after creation where practical.

---

# 6. State architecture

The state machine maintains temporal context.

Example:

```text
Frame 1:
PINCH detected

Frame 2:
PINCH detected

Frame 3:
PINCH detected

→ CONFIRMED
```

Then:

```text
PINCH
 ↓
PINCH_START
 ↓
HOLD
 ↓
PINCH_RELEASE
```

This allows the same physical gesture to produce different semantic actions.

---

# 7. Intent architecture

Intent is semantic.

Bad:

```text
gesture = PINCH
```

Good:

```text
intent = SELECT
target = volume_button
```

The same intent can be produced by:

```text
gesture
voice
keyboard
future vision
```

---

# 8. Context architecture

Context is independent from gesture.

Example:

```text
Context:
application = POWERPOINT
mode = PRESENTATION
profile = presentation
```

Then:

```text
Intent:
NAVIGATE_NEXT
```

becomes:

```text
NextSlideCommand
```

---

# 9. Profile architecture

Profiles should be data-driven.

Example conceptual YAML:

```yaml
name: presentation

gestures:
  swipe_left:
    intent: previous_slide

  swipe_right:
    intent: next_slide

  open_palm:
    intent: pointer_mode

settings:
  sensitivity: 1.2
  dwell:
    enabled: true
    duration_ms: 600
```

The exact serialization format MAY be YAML or JSON depending on existing project conventions.

---

# 10. Command architecture

Commands SHOULD be small and single-purpose.

Example:

```text
VolumeUpCommand
ScreenshotCommand
LockWorkstationCommand
NextSlideCommand
PreviousSlideCommand
OpenApplicationCommand
```

Commands SHOULD NOT know how gestures are detected.

---

# 11. Command lifecycle

```text
CREATE
 ↓
VALIDATE
 ↓
CAN_EXECUTE
 ↓
EXECUTE
 ↓
RESULT
 ↓
HISTORY
 ↓
FEEDBACK
```

If execution fails:

```text
EXECUTE
 ↓
ERROR
 ↓
TELEMETRY
 ↓
HUD ERROR
```

---

# 12. Undo architecture

Undo stores state necessary to reverse an operation.

Example:

```text
VolumeUpCommand
before = 80
after = 90
```

Undo:

```text
set_volume(80)
```

The command history SHALL NOT contain raw camera data.

---

# 13. Context resolution

Resolution priority:

```text
specific application binding
        >
profile binding
        >
global binding
        >
default binding
```

Example:

```text
SWIPE_RIGHT

PowerPoint:
next_slide

Browser:
next_page/history

Desktop:
next_window
```

---

# 14. Gesture conflict resolution

The classifier MAY identify several candidate gestures.

The state engine SHALL choose one according to:

1. confidence;
2. gesture priority;
3. current state;
4. context;
5. profile.

Example:

```text
candidate:
PINCH 0.92
POINT 0.81

winner:
PINCH
```

---

# 15. Continuous versus discrete gestures

The system SHALL distinguish:

## Discrete

```text
CLICK
FIST
SWIPE
TOGGLE
```

## Continuous

```text
CURSOR_POSITION
PINCH_DISTANCE
ZOOM
ROTATION
SCROLL
```

Continuous signals MUST NOT be forced through the same execution model as discrete gestures.

---

# 16. HUD architecture

HUD presentation SHALL consume state.

It SHALL NOT determine business logic.

Bad:

```text
HUD button
→ directly executes OS operation
```

Good:

```text
HUD interaction
→ Intent
→ CommandBus
```

---

# 17. HUD state machine

```text
IDLE
 ↓
TRACKING
 ↓
GESTURE_DETECTED
 ↓
CONFIRMING
 ↓
EXECUTING
 ↓
SUCCESS
 ↓
IDLE
```

Error:

```text
EXECUTING
 ↓
ERROR
 ↓
IDLE
```

---

# 18. Dwell UI

Dwell progress SHALL be visual.

Example:

```text
Target
  ◯
  │
  ├── 25%
  ├── 50%
  ├── 75%
  └── 100% → execute
```

Dwell SHALL not trigger if tracking confidence falls below the configured threshold.

---

# 19. Telemetry pipeline

Telemetry SHOULD use an asynchronous queue where needed.

```text
Vision loop
   ↓
Telemetry event
   ↓
Queue
   ↓
Telemetry worker
   ↓
Local storage/log
```

The camera loop MUST NOT wait for disk I/O.

---

# 20. Logging

Logs SHOULD have levels:

```text
DEBUG
INFO
WARNING
ERROR
```

Debug logs SHOULD NOT be enabled by default in production mode.

---

# 21. Input provider design

```text
InputProvider
    ├── GestureInputProvider
    ├── KeyboardInputProvider
    └── VoiceInputProvider
```

All providers produce compatible semantic input.

---

# 22. Voice future

Future voice pipeline:

```text
Microphone
 ↓
VAD
 ↓
STT
 ↓
Text
 ↓
IntentResolver
 ↓
CommandBus
```

The voice system SHALL NOT execute OS commands directly.

---

# 23. Future plugin system

Future commands MAY be loaded as plugins.

Concept:

```text
Plugin
 ├── name
 ├── version
 ├── permissions
 ├── commands
 └── contexts
```

Plugins SHALL declare permissions.

Example:

```text
filesystem.read
filesystem.write
process.launch
system.volume
```

This prevents arbitrary plugins from silently gaining unrestricted system access.

---

# 24. Security model

The application is a desktop automation tool.

Commands SHALL therefore be categorized.

A future security policy MAY require:

```text
SAFE:
automatic

SENSITIVE:
confirmation

DESTRUCTIVE:
explicit confirmation
```

---

# 25. Performance budget

Initial targets:

```text
camera pipeline:
stable real-time processing

gesture event generation:
< 1 frame of additional latency

intent resolution:
< 5ms target

local command dispatch:
< 20ms target where technically possible

HUD update:
non-blocking
```

These are engineering targets, not absolute guarantees.

Actual measurements SHALL be collected through telemetry.

---

# 26. Error isolation

A failure in:

```text
TTS
```

MUST NOT stop:

```text
gesture tracking
```

A failure in:

```text
HUD
```

MUST NOT necessarily stop:

```text
command execution
```

A command failure MUST NOT crash the entire application.

---

# 27. Backward compatibility

Existing gestures MUST remain mapped.

Migration MAY temporarily support:

```text
legacy gesture handler
+
new command handler
```

Once the new path is verified, the legacy direct execution path MAY be removed.

---

# 28. Implementation strategy

Every migration step MUST follow:

```text
Inspect
 ↓
Add abstraction
 ↓
Adapter
 ↓
Test
 ↓
Migrate one feature
 ↓
Regression test
 ↓
Commit
 ↓
Next feature
```

No task SHOULD combine unrelated architectural migrations.

---

# 29. Commit strategy

Recommended commits:

```text
feat(core): add gesture event model
feat(core): add command abstraction
feat(core): add command bus
refactor(gesture): route click through command bus
feat(gesture): add gesture state machine
feat(gesture): add dwell
feat(gesture): add swipe detection
feat(core): add profiles
feat(core): add context engine
feat(hud): add contextual feedback
feat(core): add telemetry
feat(core): add undo history
```

This makes rollback straightforward.
