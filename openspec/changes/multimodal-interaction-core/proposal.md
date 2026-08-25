# JARVIS Gesture HUD — Multimodal Interaction Core

## 1. Summary

This proposal evolves the existing `JARVIS Gesture HUD` application from a gesture-driven desktop controller into a modular, extensible, local-first human-computer interaction platform.

The existing application is the functional baseline.

The new architecture SHALL be introduced incrementally around the existing implementation.

The project SHALL NOT be rewritten from scratch.

The core architectural evolution is:

```text
Current:

Camera
  ↓
Hand Tracking
  ↓
Gesture Detection
  ↓
Action


Target:

Input
  ↓
Perception
  ↓
Gesture / Voice / Vision Event
  ↓
State
  ↓
Intent
  ↓
Context
  ↓
Command
  ↓
Action
  ↓
Feedback
  ↓
HUD / TTS / Telemetry
```

---

# 2. Motivation

The current project already provides a useful gesture-controlled desktop experience.

Existing capabilities include, depending on the current implementation:

* webcam hand tracking;
* cursor movement;
* pinch interaction;
* click;
* drag;
* scrolling;
* zoom;
* virtual keyboard;
* system controls;
* screenshots;
* volume controls;
* workstation locking;
* TTS;
* master gestures;
* secondary gestures;
* two-hand gestures;
* HUD overlays;
* mirror mode;
* handedness/laterality correction;
* native desktop overlay behavior.

The current architecture is sufficient for these capabilities but becomes increasingly difficult to extend when multiple input modalities and contextual behavior are introduced.

Examples of future requirements:

```text
Voice:
"Open VS Code"

Gesture:
Swipe right

Context:
PowerPoint is active

Result:
Next slide
```

or:

```text
Gesture:
Pinch

Context:
HUD keyboard is active

Result:
Select key
```

The system therefore needs a common abstraction for intent and action execution.

---

# 3. Goals

## 3.1 Primary goals

The system SHALL:

1. Preserve all existing functionality.
2. Separate perception from action execution.
3. Introduce a reusable Gesture Engine.
4. Introduce an Intent Engine.
5. Introduce a Context Engine.
6. Introduce a Command Bus.
7. Introduce configurable profiles.
8. Introduce gesture state management.
9. Introduce dwell interaction.
10. Introduce swipe recognition.
11. Introduce contextual HUD feedback.
12. Introduce telemetry.
13. Introduce undo/redo where technically safe.
14. Prepare the architecture for voice input.
15. Prepare the architecture for additional future input providers.
16. Maintain local-first operation.
17. Avoid mandatory cloud services.
18. Maintain acceptable real-time performance.

---

# 4. Non-goals

The following SHALL NOT be part of the first implementation phase:

* rewriting the application from scratch;
* replacing the existing hand-tracking library without justification;
* replacing the current HUD framework without measurable benefit;
* mandatory cloud AI;
* mandatory LLM integration;
* mandatory STT;
* face recognition;
* biometric authentication;
* 3D holographic rendering;
* replacing working OS integrations;
* replacing existing gesture classification merely for architectural aesthetics.

These MAY be implemented later.

---

# 5. Architectural principles

## 5.1 Existing behavior is the baseline

The current behavior is considered correct unless a specific bug is identified.

New architecture SHALL wrap existing functionality before replacing it.

---

## 5.2 No big-bang rewrite

The migration SHALL happen incrementally.

Each phase MUST leave the application runnable.

---

## 5.3 Separation of concerns

The following responsibilities SHALL remain separate:

```text
Tracking
Classification
State
Intent
Context
Command
Action
Feedback
Presentation
Telemetry
```

A gesture detector MUST NOT directly contain operating-system business logic.

---

## 5.4 Input agnosticism

The Intent Engine MUST NOT care whether an intent came from:

* gesture;
* voice;
* keyboard;
* future vision;
* future external input.

Example:

```text
Gesture → Intent("open_vscode")
Voice   → Intent("open_vscode")
Keyboard → Intent("open_vscode")
```

The Command layer SHALL remain the same.

---

## 5.5 Local-first

The core gesture pipeline SHALL work without internet access.

Internet connectivity MAY be required only by explicitly optional future features.

---

## 5.6 Explicit safety

System-affecting commands SHALL define their safety level.

Example:

```text
SAFE
CONFIRM_REQUIRED
HOLD_REQUIRED
DESTRUCTIVE
```

Actions such as locking the workstation MUST NOT be accidentally triggered by one noisy frame.

---

# 6. Target architecture

```text
                       ┌─────────────────┐
                       │     CAMERA      │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ HAND TRACKER    │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ GESTURE ENGINE  │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  STATE MACHINE  │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  INTENT ENGINE  │
                       └────────┬────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌─────────────┐       ┌─────────────┐
             │   CONTEXT    │       │   PROFILE   │
             │   ENGINE     │       │   MANAGER   │
             └──────┬──────┘       └──────┬──────┘
                    └───────────┬─────────┘
                                ▼
                       ┌─────────────────┐
                       │   COMMAND BUS   │
                       └────────┬────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌──────────┐      ┌──────────┐      ┌──────────┐
        │   OS     │      │   APPS   │      │   HUD    │
        │ ACTIONS  │      │ ACTIONS  │      │ ACTIONS  │
        └──────────┘      └──────────┘      └──────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    FEEDBACK     │
                       └───────┬─────────┘
                               │
                     ┌─────────┴─────────┐
                     ▼                   ▼
                    HUD                 TTS
```

---

# 7. Target module responsibilities

## HandTracker

Responsible for:

* camera frames;
* landmark detection;
* hand presence;
* hand identity;
* raw coordinates.

It SHALL NOT execute commands.

---

## GestureClassifier

Responsible for determining:

```text
OPEN_PALM
FIST
PINCH
POINT
TWO_FINGER_AIM
etc.
```

It SHALL output classification metadata.

---

## GestureStateMachine

Responsible for:

* detected;
* candidate;
* confirmed;
* active;
* completed;
* cancelled.

It SHALL handle debounce and temporal continuity.

---

## IntentEngine

Converts events into semantic intentions.

Example:

```text
PINCH + cursor target
→ SELECT
```

---

## ContextEngine

Determines current application context.

Examples:

```text
DESKTOP
BROWSER
VS_CODE
POWERPOINT
MEDIA_PLAYER
HUD_KEYBOARD
```

---

## ProfileManager

Determines bindings and sensitivity configuration.

---

## CommandBus

The only layer responsible for dispatching executable commands.

---

## Command

Represents one executable operation.

Commands SHOULD support:

```text
execute()
can_execute()
undo()
metadata
```

---

## FeedbackManager

Centralizes:

* HUD notifications;
* TTS;
* optional sound;
* success/error state;
* command status.

---

## TelemetryManager

Records:

* performance;
* recognition;
* command execution;
* errors.

Telemetry SHALL NOT block the real-time camera pipeline.

---

# 8. Migration strategy

Existing functions SHALL first be wrapped.

Example:

```text
Existing:

volume_up()

New:

VolumeUpCommand.execute()
    ↓
existing volume_up()
```

Only after the new abstraction is stable MAY the internal implementation be refactored.

---

# 9. Future architecture

The final system MAY support:

```text
Gesture
Voice
Keyboard
Vision
External API
Plugins
      ↓
Input Providers
      ↓
Intent Engine
      ↓
Context Engine
      ↓
Command Bus
      ↓
Actions
```

This makes the project an HCI platform rather than only a gesture controller.

---

# 10. Differentiation

The primary differentiator SHALL NOT be visual similarity to fictional JARVIS interfaces.

The differentiator is:

> A local-first multimodal interaction layer capable of controlling desktop applications through gestures, voice, contextual intents and reversible commands using one unified architecture.

The HUD is an interface.

The Gesture Engine is an input system.

The Command Bus is the execution layer.

The Context Engine provides semantic awareness.

Together they form the product.

---

# 11. Compatibility requirement

At every completed migration phase:

```text
Old functionality
+
New architecture
=
Same existing behavior
+
New capability
```

No phase is complete if an existing supported capability is silently removed.

---

# 12. Definition of success

The project is considered successfully evolved when:

```text
Gesture → Intent → Context → Command → Action
```

works reliably while:

* existing gestures remain operational;
* the HUD remains functional;
* performance remains acceptable;
* new commands can be added without modifying tracking;
* future voice input can reuse existing commands;
* profiles can change behavior without modifying core code;
* telemetry can identify performance/recognition problems;
* reversible commands can be undone.
